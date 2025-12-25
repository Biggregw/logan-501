from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import time
from uuid import uuid4


@dataclass(frozen=True)
class Camera:
    camera_id: str
    name: str
    kind: str  # "push" | "rtsp"
    url: str | None = None


@dataclass(frozen=True)
class StoredFrame:
    content_type: str
    data: bytes
    received_at_epoch_s: float


class InMemoryCameraStore:
    """
    Minimal in-memory store for camera sources and their most recent frame.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._cameras: dict[str, Camera] = {}
        self._latest_frames: dict[str, StoredFrame] = {}

    def clear(self) -> None:
        with self._lock:
            self._cameras.clear()
            self._latest_frames.clear()

    def create_camera(self, *, name: str, kind: str, url: str | None) -> Camera:
        if kind not in {"push", "rtsp"}:
            raise ValueError("kind must be 'push' or 'rtsp'")
        if kind == "rtsp" and not url:
            raise ValueError("rtsp cameras require a url")
        if kind == "push" and url:
            raise ValueError("push cameras must not include a url")

        camera_id = str(uuid4())
        cam = Camera(camera_id=camera_id, name=name, kind=kind, url=url)
        with self._lock:
            self._cameras[camera_id] = cam
        return cam

    def list_cameras(self) -> list[Camera]:
        with self._lock:
            return list(self._cameras.values())

    def get_camera(self, camera_id: str) -> Camera | None:
        with self._lock:
            return self._cameras.get(camera_id)

    def delete_camera(self, camera_id: str) -> bool:
        with self._lock:
            existed = camera_id in self._cameras
            self._cameras.pop(camera_id, None)
            self._latest_frames.pop(camera_id, None)
            return existed

    def set_latest_frame(self, camera_id: str, *, content_type: str, data: bytes) -> None:
        with self._lock:
            if camera_id not in self._cameras:
                raise KeyError("camera not found")
            self._latest_frames[camera_id] = StoredFrame(
                content_type=content_type or "application/octet-stream",
                data=data,
                received_at_epoch_s=time(),
            )

    def get_latest_frame(self, camera_id: str) -> StoredFrame | None:
        with self._lock:
            return self._latest_frames.get(camera_id)


_STORE: InMemoryCameraStore | None = None


def get_camera_store() -> InMemoryCameraStore:
    global _STORE
    if _STORE is None:
        _STORE = InMemoryCameraStore()
    return _STORE

