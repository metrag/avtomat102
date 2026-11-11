#!/usr/bin/env python3
"""MaixCAM: фото по кнопке -> UDP-датаграмма на ПК тренажёра.

Кнопка на пине A19 (к GND, внутренняя подтяжка вверх, активный низ).
По нажатию камера делает кадр, кодирует в JPEG и отправляет ОДНУ
UDP-датаграмму на ПК:

    {"type": "trigger", "frame": "<base64 JPEG>"}

Ограничение: полезная нагрузка UDP <= 65507 байт, поэтому JPEG
подбирается так, чтобы base64 + JSON влезали в лимит (при превышении
кадр уменьшается вдвое и кодируется заново).

Сеть: плата и ПК — в одной подсети (внешний роутер в режиме клиента
или AP самой платы). При target_host="auto" датаграмма уходит в
broadcast подсети wlan0 — ПК принимает её на 0.0.0.0:5001.

Запуск:  python3 /root/photo_trigger.py
Тест:    python3 /root/photo_trigger.py --test-shot [--target IP]
"""

import base64
import fcntl
import json
import logging
import os
import signal
import socket
import struct
import sys
import time

CONFIG_PATH = "/root/trainer_config.json"
LOCK_PATH = "/var/run/photo_trigger.lock"

DEFAULTS = {
    # "auto" — broadcast подсети wlan0 (работает и за внешним роутером,
    # и в AP-режиме); иначе — явный IP получателя.
    "target_host": "auto",
    # Запасной адрес, если определить подсеть wlan0 не удалось.
    "fallback_broadcast": "255.255.255.255",
    "trigger_port": 5001,
    "gpio_pin": "A19",
    "button_active_low": True,
    "debounce_ms": 50,
    "camera_width": 1280,
    "camera_height": 720,
    "jpeg_quality": 51,
    "max_datagram": 65507,
    "save_dir": "/tmp",
}

logger = logging.getLogger("photo_trigger")


def load_config() -> dict:
    """Читает /root/trainer_config.json поверх значений по умолчанию."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
        logger.info("Config loaded: %s", CONFIG_PATH)
    except FileNotFoundError:
        logger.warning("No %s, using defaults", CONFIG_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Bad config %s: %s — using defaults", CONFIG_PATH, exc)
    return cfg


def _wlan0_broadcast() -> str:
    """Broadcast-адрес подсети wlan0 (из адреса и маски через ioctl)."""
    SIOCGIFADDR = 0x8915
    SIOCGIFNETMASK = 0x891B
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        def _req(code: int) -> int:
            packed = fcntl.ioctl(
                sock.fileno(), code, struct.pack("256s", b"wlan0")
            )
            return struct.unpack("!I", packed[20:24])[0]

        addr = _req(SIOCGIFADDR)
        mask = _req(SIOCGIFNETMASK)
        return socket.inet_ntoa(struct.pack("!I", addr | ~mask & 0xFFFFFFFF))
    except OSError:
        return ""
    finally:
        sock.close()


def resolve_targets(cfg: dict) -> list:
    """Возвращает список IP получателей."""
    host = cfg.get("target_host", "auto")
    if host and host != "auto":
        return [str(host)]

    bcast = _wlan0_broadcast()
    return [bcast or cfg["fallback_broadcast"]]


class Button:
    """Кнопка на GPIO с антидребезгом и ожиданием отпускания."""

    def __init__(self, pin_name: str, active_low: bool, debounce_ms: int):
        from maix import gpio, pinmap

        pinmap.set_pin_function(pin_name, "GPIO" + pin_name)
        self._pin = gpio.GPIO("GPIO" + pin_name, gpio.Mode.IN, gpio.Pull.PULL_UP)
        self._active_low = active_low
        self._debounce_ms = debounce_ms

    def pressed(self) -> bool:
        value = self._pin.value()
        return (value == 0) if self._active_low else (value == 1)

    def wait_press(self) -> None:
        """Ждёт нажатия; после срабатывания ждёт отпускания (1 нажатие = 1 фото)."""
        while not self.pressed():
            time.sleep(0.01)
        time.sleep(self._debounce_ms / 1000.0)  # антидребезг
        while self.pressed():
            time.sleep(0.01)


class ShotCamera:
    """Камера с ленивой инициализацией и переподключением после сбоев."""

    MAX_CONSECUTIVE_ERRORS = 10

    def __init__(self, width: int, height: int, quality: int, max_datagram: int):
        self._w = width
        self._h = height
        self._quality = quality
        self._max_datagram = max_datagram
        self._cam = None
        self._errors = 0

    def _open(self) -> None:
        from maix import camera

        self.close()
        self._cam = camera.Camera(self._w, self._h)
        self._errors = 0
        logger.info("Camera opened %dx%d", self._w, self._h)

    def close(self) -> None:
        if self._cam is not None:
            try:
                self._cam.close()
            except Exception:
                pass
            self._cam = None

    def capture_jpeg(self) -> bytes:
        """Делает кадр и возвращает JPEG-байты, подобранные под лимит UDP."""
        if self._cam is None:
            self._open()

        try:
            img = self._cam.read()
            if img is None:
                raise RuntimeError("camera read failed")
        except Exception as exc:
            self._errors += 1
            logger.error("Camera read error (%d): %s", self._errors, exc)
            if self._errors >= self.MAX_CONSECUTIVE_ERRORS:
                logger.error("Too many errors — reopening camera")
                self._errors = 0
                self._open()
            raise

        self._errors = 0
        return self._encode_fit(img)

    def _encode_fit(self, img) -> bytes:
        """JPEG так, чтобы base64+JSON <= max_datagram; иначе кадр уменьшается."""
        head_room = 256  # запас под JSON-обёртку
        quality = self._quality

        cur = img
        for attempt in range(4):
            jpg = cur.to_jpeg(quality)
            raw = jpg.to_bytes()
            if 4 * ((len(raw) + 2) // 3) + head_room <= self._max_datagram:
                logger.info(
                    "JPEG %dx%d q=%d -> %d bytes (fits datagram)",
                    cur.width(), cur.height(), quality, len(raw),
                )
                return raw
            logger.warning(
                "JPEG too big (%d bytes) for limit %d, shrinking (attempt %d)",
                len(raw), self._max_datagram, attempt + 1,
            )
            cur = cur.resize(cur.width() // 2, cur.height() // 2)

        raw = cur.to_jpeg(quality).to_bytes()
        logger.warning("Falling back to %d bytes JPEG (may exceed limit)", len(raw))
        return raw


def build_packet(jpeg: bytes) -> bytes:
    # Время выстрела не передаётся: ПК фиксирует его в момент приёма.
    payload = {
        "type": "trigger",
        "frame": base64.b64encode(jpeg).decode("ascii"),
    }
    return json.dumps(payload).encode("utf-8")


def send_packet(data: bytes, targets: list, port: int) -> bool:
    """Шлёт датаграмму на все цели. Повтор при ошибке сокета."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ok = False
        for attempt in range(2):
            for host in targets:
                try:
                    sock.sendto(data, (host, port))
                    ok = True
                    logger.info("Sent %d bytes to %s:%d", len(data), host, port)
                except OSError as exc:
                    logger.error("sendto %s:%d failed: %s", host, port, exc)
            if ok:
                break
            time.sleep(0.05)
        return ok
    finally:
        sock.close()


def save_local(jpeg: bytes, save_dir: str, timestamp: float) -> str:
    """Сохраняет копию фото локально (диагностика при недоступном ПК)."""
    try:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, "shot_%.3f.jpg" % timestamp)
        with open(path, "wb") as f:
            f.write(jpeg)
        return path
    except OSError as exc:
        logger.error("Save failed: %s", exc)
        return ""


def do_shot(cfg: dict, cam: ShotCamera) -> None:
    """Полный цикл: захват -> кодирование -> отправка (+ локальная копия)."""
    timestamp = time.time()
    try:
        jpeg = cam.capture_jpeg()
    except Exception:
        logger.error("Shot aborted: no frame")
        return

    # Цель пересчитывается на каждый выстрел: адрес wlan0 может
    # появиться (смениться) после старта демона (DHCP, смена сети).
    targets = resolve_targets(cfg)

    data = build_packet(jpeg)
    if len(data) > cfg["max_datagram"]:
        logger.error("Datagram %d exceeds limit %d — not sent", len(data), cfg["max_datagram"])
    else:
        if send_packet(data, targets, cfg["trigger_port"]):
            logger.info("Shot sent OK (%d bytes datagram)", len(data))
        else:
            logger.error("Shot NOT delivered, saving locally")

    path = save_local(jpeg, cfg["save_dir"], timestamp)
    if path:
        logger.info("Local copy: %s", path)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    args = sys.argv[1:]
    test_shot = "--test-shot" in args
    target_override = None
    if "--target" in args:
        target_override = args[args.index("--target") + 1]

    cfg = load_config()
    if target_override:
        cfg["target_host"] = target_override

    # Одиночный экземпляр.
    lock_file = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logger.error("photo_trigger is already running (lock %s)", LOCK_PATH)
        return 1

    targets = resolve_targets(cfg)
    logger.info("Targets: %s:%d (recomputed per shot)", targets, cfg["trigger_port"])

    cam = ShotCamera(
        cfg["camera_width"], cfg["camera_height"],
        cfg["jpeg_quality"], cfg["max_datagram"],
    )

    def _graceful_stop(signum, _frame):
        # Мягкая остановка (SIGTERM от init-скрипта): обязательно
        # закрываем камеру — иначе драйвер не освободит буферы и
        # следующий запуск падает с "No buffer space available".
        logger.info("Signal %d — closing camera and exiting", signum)
        cam.close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _graceful_stop)

    if test_shot:
        logger.info("Test shot (no button)")
        do_shot(cfg, cam)
        cam.close()
        return 0

    button = Button(cfg["gpio_pin"], cfg["button_active_low"], cfg["debounce_ms"])
    logger.info("Ready: button %s, waiting for press...", cfg["gpio_pin"])

    try:
        while True:
            button.wait_press()
            logger.info("Button pressed")
            do_shot(cfg, cam)
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        cam.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
