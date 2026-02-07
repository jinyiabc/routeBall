"""Local video storage with automatic file rotation."""

import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from .config import StorageConfig

logger = logging.getLogger(__name__)


class VideoStorage:
    """Saves captured frames to local MP4 files with optional rotation."""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._writer: cv2.VideoWriter | None = None
        self._current_path: Path | None = None
        self._frame_count = 0
        self._fps = 30

    def open(self, width: int, height: int, fps: int = 30) -> Path:
        """Start a new recording file.

        Returns the path to the new file.
        """
        self._fps = fps
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.filename_prefix}_{timestamp}{self.config.container}"
        self._current_path = self.config.output_dir / filename

        fourcc = cv2.VideoWriter_fourcc(*self.config.codec)
        self._writer = cv2.VideoWriter(
            str(self._current_path), fourcc, fps, (width, height)
        )

        if not self._writer.isOpened():
            raise IOError(f"Failed to open video writer: {self._current_path}")

        self._frame_count = 0
        logger.info("Recording to %s", self._current_path)
        return self._current_path

    def write_frame(self, frame: np.ndarray) -> None:
        """Write a single frame to the current recording file.

        Automatically rotates to a new file if max size is exceeded.
        """
        if self._writer is None:
            raise RuntimeError("Storage not opened. Call open() first.")

        self._writer.write(frame)
        self._frame_count += 1

        if self._should_rotate():
            h, w = frame.shape[:2]
            self.close()
            self.open(w, h, self._fps)

    def _should_rotate(self) -> bool:
        """Check if the current file exceeds the max size limit."""
        if self.config.max_file_size_mb <= 0 or self._current_path is None:
            return False
        try:
            size_mb = self._current_path.stat().st_size / (1024 * 1024)
            return size_mb >= self.config.max_file_size_mb
        except FileNotFoundError:
            return False

    def close(self) -> None:
        """Finalize and close the current recording file."""
        if self._writer is not None:
            self._writer.release()
            self._writer = None
            logger.info(
                "Recording saved: %s (%d frames)",
                self._current_path,
                self._frame_count,
            )

    @property
    def is_recording(self) -> bool:
        return self._writer is not None and self._writer.isOpened()

    @property
    def current_file(self) -> Path | None:
        return self._current_path
