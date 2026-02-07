# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

routeBall is a Python application that captures video from Android-based wearable smart glasses (via ADB or RTSP), saves recordings locally as MP4 files, and optionally streams live video over HTTP as MJPEG.

## Running the Application

```bash
# Install dependencies (use the existing venv)
source venv/bin/activate
pip install -r requirements.txt

# Default: ADB capture, save + stream
python main.py

# RTSP mode
python main.py --mode rtsp --rtsp-url rtsp://192.168.1.100:8554/camera

# Record only (no live streaming)
python main.py --no-stream

# Stream only (no local recording)
python main.py --no-save
```

No tests, linter, or formatter are currently configured.

## Architecture

The app has four modules orchestrated by `main.py`:

- **capture.py** (`GlassCapture`) - Acquires frames from glasses via two modes: ADB (pipes `adb exec-out screenrecord` through ffmpeg into OpenCV) or RTSP (direct OpenCV `VideoCapture`). Provides a thread-safe `latest_frame` property and a blocking `run_loop(on_frame=...)` callback loop.
- **storage.py** (`VideoStorage`) - Writes frames to timestamped MP4 files using OpenCV `VideoWriter`. Automatically rotates files when `max_file_size_mb` is exceeded.
- **stream.py** (FastAPI app) - Serves live MJPEG at `/stream`, single JPEG at `/snapshot`, and status at `/status`. Reads frames from a global `GlassCapture` reference set via `set_frame_source()`.
- **config.py** - Dataclasses (`CaptureConfig`, `StorageConfig`, `StreamConfig`, `AppConfig`) for all settings.

**Data flow:** Glasses → `GlassCapture.read_frame()` → frame callback in main loop → `VideoStorage.write_frame()` for recording; simultaneously, the streaming server reads `GlassCapture.latest_frame` for HTTP clients.

**Threading model:** The capture loop runs on the main thread. The uvicorn/FastAPI streaming server runs on a daemon thread. Frame access between threads is protected by a `threading.Lock`.

## Key Dependencies

- **opencv-python** - Video capture, encoding/decoding, VideoWriter
- **fastapi + uvicorn** - MJPEG streaming HTTP server
- **numpy** - Frame array operations

## Code Conventions

- Python 3.10+ (uses `X | None` union syntax)
- Type hints throughout
- Google-style docstrings
- Dataclasses for configuration (no pydantic)
