from __future__ import annotations

import cv2


def snapshot_jpeg_from_rtsp(url: str) -> bytes:
    """
    Grab a single frame from an RTSP source and return it as JPEG bytes.

    Notes:
    - This assumes ffmpeg is available (installed in the Dockerfile).
    - RTSP auth is typically embedded in the URL (rtsp://user:pass@host:port/stream).
    """
    cap = cv2.VideoCapture(url)
    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("failed to read frame from RTSP stream")

        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            raise RuntimeError("failed to encode jpeg")
        return buf.tobytes()
    finally:
        cap.release()

