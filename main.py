"""routeBall - Record video through wearable Android-based glasses.

Usage:
    python main.py                      # Default: ADB capture, save + stream
    python main.py --mode rtsp --rtsp-url rtsp://192.168.1.100:8554/camera
    python main.py --no-stream          # Record only, no live server
    python main.py --no-save            # Stream only, no local recording
"""

import argparse
import logging
import signal
import sys
import threading

import uvicorn

from routeball.capture import GlassCapture
from routeball.config import AppConfig, CaptureConfig, StorageConfig, StreamConfig
from routeball.storage import VideoStorage
from routeball.stream import app, set_frame_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("routeball")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="routeBall - Wearable glass video recorder")
    parser.add_argument(
        "--mode", choices=["adb", "rtsp"], default="adb",
        help="Capture mode (default: adb)",
    )
    parser.add_argument("--rtsp-url", default="rtsp://192.168.1.100:8554/camera")
    parser.add_argument("--adb-serial", default=None, help="ADB device serial")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--output-dir", default="recordings")
    parser.add_argument("--stream-port", type=int, default=8000)
    parser.add_argument("--no-save", action="store_true", help="Disable local recording")
    parser.add_argument("--no-stream", action="store_true", help="Disable live streaming")
    return parser.parse_args()


def main():
    args = parse_args()

    config = AppConfig(
        capture=CaptureConfig(
            mode=args.mode,
            rtsp_url=args.rtsp_url,
            adb_serial=args.adb_serial,
            width=args.width,
            height=args.height,
            fps=args.fps,
        ),
        storage=StorageConfig(output_dir=args.output_dir),
        stream=StreamConfig(port=args.stream_port),
        save_locally=not args.no_save,
        enable_streaming=not args.no_stream,
    )

    # Initialize capture
    capture = GlassCapture(config.capture)

    # Initialize storage
    storage = None
    if config.save_locally:
        storage = VideoStorage(config.storage)

    # Graceful shutdown
    def shutdown(sig, frame):
        logger.info("Shutting down...")
        capture.stop()
        if storage:
            storage.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start capture
    try:
        capture.start()
    except ConnectionError as e:
        logger.error("Failed to connect: %s", e)
        sys.exit(1)

    # Open local recording
    if storage:
        storage.open(config.capture.width, config.capture.height, config.capture.fps)

    # Start streaming server in background thread
    if config.enable_streaming:
        set_frame_source(capture)
        server_thread = threading.Thread(
            target=uvicorn.run,
            args=(app,),
            kwargs={"host": config.stream.host, "port": config.stream.port, "log_level": "info"},
            daemon=True,
        )
        server_thread.start()
        logger.info("Streaming at http://0.0.0.0:%d/stream", config.stream.port)

    # Frame callback
    def on_frame(frame):
        if storage:
            storage.write_frame(frame)

    logger.info("Recording started. Press Ctrl+C to stop.")
    capture.run_loop(on_frame=on_frame)


if __name__ == "__main__":
    main()
