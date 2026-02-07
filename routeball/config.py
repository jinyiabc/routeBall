import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CaptureConfig:
    """Configuration for video capture from Android glasses."""

    # Connection mode: "adb" for USB/WiFi ADB, "rtsp" for RTSP stream
    mode: str = "adb"

    # RTSP URL when using RTSP mode (glasses must be streaming)
    rtsp_url: str = "rtsp://192.168.1.100:8554/camera"

    # ADB device serial (None = auto-detect first device)
    adb_serial: str | None = None

    # Video resolution
    width: int = 1280
    height: int = 720
    fps: int = 30


@dataclass
class StorageConfig:
    """Configuration for local video storage."""

    output_dir: Path = field(default_factory=lambda: Path("recordings"))
    filename_prefix: str = "routeball"
    # Max file size in MB before rotating (0 = no limit)
    max_file_size_mb: int = 500
    codec: str = "mp4v"
    container: str = ".mp4"


@dataclass
class StreamConfig:
    """Configuration for the live streaming server."""

    host: str = "0.0.0.0"
    port: int = 8000
    # MJPEG stream quality (1-100)
    jpeg_quality: int = 80


@dataclass
class AppConfig:
    """Top-level application configuration."""

    capture: CaptureConfig = field(default_factory=CaptureConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    stream: StreamConfig = field(default_factory=StreamConfig)

    # Enable local recording
    save_locally: bool = True
    # Enable live streaming server
    enable_streaming: bool = True
