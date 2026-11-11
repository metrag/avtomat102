"""Тесты декодирования UDP-пакетов (время фиксируется на ПК)."""

import base64
import json
import time

import cv2
import numpy as np

from src.network.udp_receiver import UDPReceiver


def _jpeg_b64() -> str:
    """Кодирует маленький чёрный кадр в base64 JPEG."""
    ok, buffer = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
    assert ok
    return base64.b64encode(buffer.tobytes()).decode("ascii")


class TestDecodePacket:
    """Проверка разбора датаграммы."""

    def test_with_timestamp(self):
        """Метка времени из пакета сохраняется."""
        packet = json.dumps(
            {"type": "trigger", "timestamp": 123.5, "frame": _jpeg_b64()}
        ).encode("utf-8")

        timestamp, frame = UDPReceiver._decode_packet(packet)

        assert timestamp == 123.5
        assert frame.shape == (16, 16, 3)

    def test_without_timestamp_uses_receipt_time(self):
        """Без метки в пакете подставляется время приёма на ПК."""
        packet = json.dumps({"type": "trigger", "frame": _jpeg_b64()}).encode("utf-8")

        before = time.time()
        timestamp, frame = UDPReceiver._decode_packet(packet)
        after = time.time()

        assert before <= timestamp <= after
        assert frame.shape == (16, 16, 3)
