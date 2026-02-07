"""Video capture from Android-based wearable glasses.

Supports two capture modes:
- ADB: Captures via Android Debug Bridge (USB or WiFi ADB)
- RTSP: Connects to an RTSP stream from the glasses' camera app
"""

import logging
import subprocess
import threading
from typing import Callable

import cv2
import numpy as np

from .config import CaptureConfig

logger = logging.getLogger(__name__)


class GlassCapture:
    """Captures video frames from Android-based smart glasses."""

    def __init__(self, config: CaptureConfig):
        self.config = config
        self._cap: cv2.VideoCapture | None = None
        self._running = False
        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None

    def start(self) -> None:
        """Open the video capture source."""
        if self.config.mode == "rtsp":
            self._start_rtsp()
        elif self.config.mode == "adb":
            self._start_adb()
        else:
            raise ValueError(f"Unknown capture mode: {self.config.mode}")

        self._running = True
        logger.info("Capture started (mode=%s)", self.config.mode)

    def _start_rtsp(self) -> None:
        """Connect to the glasses via RTSP stream."""
        self._cap = cv2.VideoCapture(self.config.rtsp_url)
        if not self._cap.isOpened():
            raise ConnectionError(
                f"Cannot connect to RTSP stream: {self.config.rtsp_url}"
            )

    def _start_adb(self) -> None:
        """Connect to the glasses via ADB screencast.

        Uses `adb exec-out screenrecord --output-format=h264 -` to pipe
        raw H.264 frames from the device into an ffmpeg-backed OpenCV reader.
        """
        serial_args = []
        if self.config.adb_serial:
            serial_args = ["-s", self.config.adb_serial]

        # Verify device is connected
        result = subprocess.run(
            ["adb", *serial_args, "devices"],
            capture_output=True,
            text=True,
        )
        if "device" not in result.stdout.split("\n", 1)[-1]:
            raise ConnectionError(
                "No ADB device found. Connect glasses via USB or WiFi ADB."
            )

        # Build the ADB screenrecord pipeline
        adb_cmd = [
            "adb",
            *serial_args,
            "exec-out",
            "screenrecord",
            "--output-format=h264",
            f"--size={self.config.width}x{self.config.height}",
            "-",
        ]

        # OpenCV can read from an ffmpeg pipe fed by ADB
        pipeline = (
            f"{' '.join(adb_cmd)} | "
            f"ffmpeg -i pipe:0 -f rawvideo -pix_fmt bgr24 "
            f"-s {self.config.width}x{self.config.height} pipe:1"
        )
        self._cap = cv2.VideoCapture(pipeline, cv2.CAP_FFMPEG)

        if not self._cap.isOpened():
            raise ConnectionError("Failed to open ADB capture pipeline.")

    def read_frame(self) -> np.ndarray | None:
        """Read a single frame from the capture source.

        Returns None if no frame is available.
        """
        if self._cap is None or not self._running:
            return None

        ret, frame = self._cap.read()
        if not ret:
            logger.warning("Failed to read frame")
            return None

        with self._lock:
            self._latest_frame = frame
        return frame

    @property
    def latest_frame(self) -> np.ndarray | None:
        """Return the most recently captured frame (thread-safe)."""
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def run_loop(self, on_frame: Callable[[np.ndarray], None] | None = None) -> None:
        """Continuously capture frames until stopped.

        Args:
            on_frame: Optional callback invoked with each captured frame.
        """
        while self._running:
            frame = self.read_frame()
            if frame is not None and on_frame:
                on_frame(frame)

    def stop(self) -> None:
        """Release the capture source."""
        self._running = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        logger.info("Capture stopped")

    @property
    def is_running(self) -> bool:
        return self._running
