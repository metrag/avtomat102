"""Эмуляция камеры для локальной отладки тренажёра.

MockCamera умеет генерировать синтетические кадры или читать их из файла,
а также отправлять кадры по UDP на порты, указанные в конфигурации.
"""

import base64
import json
import logging
import socket
import time
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class MockCamera:
    """Имитатор видеокамеры и триггера.

    Attributes:
        video_source: Путь к видеофайлу или None для синтетического потока.
        video_size: Размер видеокадров (ширина, высота).
        trigger_size: Размер триггерных кадров (ширина, высота).
    """

    VIDEO_SIZE = (640, 480)
    TRIGGER_SIZE = (1920, 1080)

    def __init__(
        self,
        video_source: str | Path | None = None,
        target_host: str = "127.0.0.1",
        video_port: int = 5000,
        trigger_port: int = 5001,
    ):
        """Инициализация имитатора камеры.

        Args:
            video_source: Путь к видеофайлу. Если None — генерируются
                синтетические кадры.
            target_host: Адрес получателя UDP-датаграмм.
            video_port: Порт для видеопотока.
            trigger_port: Порт для триггерных кадров.
        """
        self.video_source = video_source
        self.target_host = target_host
        self.video_port = video_port
        self.trigger_port = trigger_port

        self._cap: cv2.VideoCapture | None = None
        self._frame_counter = 0

    def _open_capture(self) -> cv2.VideoCapture:
        """Открывает видеопоток из файла или создаёт пустой захват."""
        if self.video_source is not None:
            cap = cv2.VideoCapture(str(self.video_source))
            if cap.isOpened():
                return cap
            logger.warning(
                "Could not open video source %s, falling back to synthetic frames",
                self.video_source,
            )
        return cv2.VideoCapture()

    def get_video_frame(self) -> np.ndarray:
        """Возвращает очередной видеокадр размером 640×480.

        Returns:
            Кадр в формате BGR (HxWx3).
        """
        if self._cap is None:
            self._cap = self._open_capture()

        if self.video_source is not None and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None:
                return cv2.resize(frame, self.VIDEO_SIZE)

        # Синтетический кадр: меняющийся цветной градиент.
        self._frame_counter += 1
        width, height = self.VIDEO_SIZE
        hue = self._frame_counter % 180
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (hue, 200, 200)
        return cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

    def get_trigger_frame(self) -> np.ndarray:
        """Возвращает полноразмерный триггерный кадр.

        Returns:
            Кадр в формате BGR (HxWx3).
        """
        width, height = self.TRIGGER_SIZE
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Рисуем белый прямоугольник по центру для визуальной разметки.
        cx, cy = width // 2, height // 2
        cv2.rectangle(
            frame,
            (cx - 100, cy - 100),
            (cx + 100, cy + 100),
            (255, 255, 255),
            thickness=-1,
        )
        return frame

    def send_trigger_frame(self) -> None:
        """Отправляет один триггерный кадр по UDP."""
        frame = self.get_trigger_frame()
        self._send_frame(frame, self.trigger_port, frame_type="trigger")

    def run_local_emulation(
        self,
        duration_seconds: float = 10.0,
        fps: float = 10.0,
    ) -> None:
        """Эмулирует поток видео и периодически отправляет триггерные кадры.

        Args:
            duration_seconds: Продолжительность эмуляции в секундах.
            fps: Частота кадров видеопотока.
        """
        logger.info(
            "Starting local UDP emulation: host=%s video_port=%s trigger_port=%s",
            self.target_host,
            self.video_port,
            self.trigger_port,
        )

        period = 1.0 / fps
        start = time.monotonic()
        trigger_counter = 0

        try:
            while time.monotonic() - start < duration_seconds:
                frame = self.get_video_frame()
                self._send_frame(frame, self.video_port, frame_type="video")

                trigger_counter += 1
                if trigger_counter % int(fps) == 0:
                    self.send_trigger_frame()

                time.sleep(period)
        except KeyboardInterrupt:
            logger.info("Local emulation interrupted by user")
        finally:
            self.release()
            logger.info("Local emulation finished")

    def release(self) -> None:
        """Освобождает ресурсы видеозахвата."""
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    def _send_frame(
        self,
        frame: np.ndarray,
        port: int,
        frame_type: str = "video",
    ) -> None:
        """Кодирует и отправляет один кадр по UDP.

        Args:
            frame: Кадр в формате BGR.
            port: Порт получателя.
            frame_type: Тип кадра (video/trigger).
        """
        success, encoded = cv2.imencode(".jpg", frame)
        if not success:
            logger.warning("Failed to encode %s frame", frame_type)
            return

        payload = {
            "type": frame_type,
            "timestamp": time.time(),
            "frame": base64.b64encode(encoded.tobytes()).decode("ascii"),
        }
        data = json.dumps(payload).encode("utf-8")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (self.target_host, port))

        logger.debug("Sent %s frame to %s:%s", frame_type, self.target_host, port)
