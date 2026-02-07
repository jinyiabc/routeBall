"""Live MJPEG streaming server using FastAPI."""

import logging

import cv2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .config import StreamConfig

logger = logging.getLogger(__name__)

app = FastAPI(title="routeBall Stream")

# Global reference set by main.py before starting the server
_frame_source = None


def set_frame_source(source):
    """Set the frame source (GlassCapture instance) for the stream."""
    global _frame_source
    _frame_source = source


def _generate_mjpeg(quality: int):
    """Yield MJPEG frames as a multipart HTTP response."""
    while True:
        if _frame_source is None:
            continue

        frame = _frame_source.latest_frame
        if frame is None:
            continue

        ret, jpeg = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        )


@app.get("/")
def index():
    return {
        "app": "routeBall",
        "endpoints": {
            "/stream": "Live MJPEG video stream",
            "/snapshot": "Single JPEG snapshot",
            "/status": "Capture status",
        },
    }


@app.get("/stream")
def video_stream():
    """Live MJPEG stream from the glasses."""
    return StreamingResponse(
        _generate_mjpeg(quality=80),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/snapshot")
def snapshot():
    """Capture a single JPEG frame."""
    if _frame_source is None:
        return {"error": "No capture source available"}

    frame = _frame_source.latest_frame
    if frame is None:
        return {"error": "No frame available"}

    ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ret:
        return {"error": "Failed to encode frame"}

    return StreamingResponse(
        iter([jpeg.tobytes()]),
        media_type="image/jpeg",
    )


@app.get("/status")
def status():
    return {
        "capturing": _frame_source is not None and _frame_source.is_running,
    }
