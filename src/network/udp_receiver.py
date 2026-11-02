"""UDP-приёмник видеокадров и триггерных кадров.

Принимает датаграммы в формате JSON с полями:
  type        — "video" или "trigger"
  timestamp   — метка времени (число или строка)
  frame       — JPEG-изображение, закодированное в base64

Колбэки не привязаны к PyQt и могут быть любыми вызываемыми объектами.
"""

import base64
import json
import logging
import socket
import threading
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Константы типов пакетов
VIDEO_TYPE = "video"
TRIGGER_TYPE = "trigger"


class UDPReceiver:
    """Потокобезопасный UDP-приёмник для видео и триггерных кадров.

    Attributes:
        video_port: Порт входящего видеопотока.
        trigger_port: Порт входящих триггерных кадров.
        buffer_size: Максимальный размер UDP-датаграммы.
        on_video_frame: Колбэк для видеокадров.
        on_trigger_frame: Колбэк для триггерных кадров.
    """

    def __init__(
        self,
        video_port: int = 5000,
        trigger_port: int = 5001,
        buffer_size: int = 65536,
        on_video_frame: Callable[[Any, np.ndarray], None] | None = None,
        on_trigger_frame: Callable[[Any, np.ndarray], None] | None = None,
    ):
        """Инициализация приёмника.

        Args:
            video_port: Порт для видеокадров.
            trigger_port: Порт для триггерных кадров.
            buffer_size: Размер буфера приёма.
            on_video_frame: Колбэк (timestamp, frame) для видео.
            on_trigger_frame: Колбэк (timestamp, frame) для триггера.
        """
        self.video_port = video_port
        self.trigger_port = trigger_port
        self.buffer_size = buffer_size
        self.on_video_frame = on_video_frame
        self.on_trigger_frame = on_trigger_frame

        self._sockets: list[socket.socket] = []
        self._running = False
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Запускает приём UDP-датаграмм в фоновых потоках."""
        if self._running:
            logger.warning("UDP receiver is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._sockets = []
        self._threads = []

        for port, kind, callback in (
            (self.video_port, VIDEO_TYPE, self.on_video_frame),
            (self.trigger_port, TRIGGER_TYPE, self.on_trigger_frame),
        ):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(0.2)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError as exc:
                logger.error("Failed to bind UDP port %s: %s", port, exc)
                self.stop()
                raise

            self._sockets.append(sock)
            thread = threading.Thread(
                target=self._receive_loop,
                args=(sock, kind, callback),
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

        logger.info(
            "UDP receiver started on ports video=%s trigger=%s",
            self.video_port,
            self.trigger_port,
        )

    def stop(self) -> None:
        """Останавливает приём и закрывает сокеты."""
        self._running = False
        self._stop_event.set()

        for sock in self._sockets:
            try:
                sock.close()
            except OSError as exc:
                logger.warning("Error while closing socket: %s", exc)

        self._sockets = []

        for thread in self._threads:
            thread.join(timeout=1.0)
        self._threads = []

        logger.info("UDP receiver stopped")

    def _receive_loop(
        self,
        sock: socket.socket,
        kind: str,
        callback: Callable[[Any, np.ndarray], None] | None,
    ) -> None:
        """Цикл приёма датаграмм для одного порта.

        Args:
            sock: Привязанный UDP-сокет.
            kind: Тип пакета (video/trigger).
            callback: Пользовательский колбэк.
        """
        while self._running and not self._stop_event.is_set():
            try:
                data, _ = sock.recvfrom(self.buffer_size)
            except TimeoutError:
                continue
            except OSError:
                # Сокет закрыт или произошла ошибка — выходим из цикла.
                break

            if not data:
                continue

            try:
                timestamp, frame = self._decode_packet(data)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                logger.warning("Failed to decode %s packet: %s", kind, exc)
                continue

            if frame is None:
                continue

            if callback is not None:
                try:
                    callback(timestamp, frame)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Callback error for %s: %s", kind, exc)

    @staticmethod
    def _decode_packet(data: bytes) -> tuple[Any, np.ndarray]:
        """Декодирует JSON-датаграмму с base64 JPEG в (timestamp, frame).

        Args:
            data: Сырые байты датаграммы.

        Returns:
            Кортеж (timestamp, frame), где frame — ndarray в формате BGR.

        Raises:
            ValueError: Если frame не удалось декодировать.
        """
        payload = json.loads(data.decode("utf-8"))
        timestamp = payload["timestamp"]
        encoded_frame = payload["frame"]

        jpeg_bytes = base64.b64decode(encoded_frame)
        frame_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Failed to decode JPEG frame")

        return timestamp, frame
