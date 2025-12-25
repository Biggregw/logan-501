from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.camera.rtsp import snapshot_jpeg_from_rtsp
from app.camera.store import Camera, InMemoryCameraStore, get_camera_store

router = APIRouter(tags=["cameras"])


class CreateCameraRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    kind: str = Field(..., description="push | rtsp")
    url: str | None = Field(default=None, description="Required for rtsp cameras")


class CameraDTO(BaseModel):
    camera_id: str
    name: str
    kind: str
    url: str | None


def _to_dto(c: Camera) -> CameraDTO:
    return CameraDTO(camera_id=c.camera_id, name=c.name, kind=c.kind, url=c.url)


def _store() -> InMemoryCameraStore:
    return get_camera_store()


@router.post("/cameras", response_model=CameraDTO)
def create_camera(req: CreateCameraRequest) -> CameraDTO:
    try:
        cam = _store().create_camera(name=req.name, kind=req.kind, url=req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _to_dto(cam)


@router.get("/cameras", response_model=list[CameraDTO])
def list_cameras() -> list[CameraDTO]:
    return [_to_dto(c) for c in _store().list_cameras()]


@router.get("/cameras/{camera_id}", response_model=CameraDTO)
def get_camera(camera_id: str) -> CameraDTO:
    cam = _store().get_camera(camera_id)
    if cam is None:
        raise HTTPException(status_code=404, detail="camera not found")
    return _to_dto(cam)


@router.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str) -> dict:
    existed = _store().delete_camera(camera_id)
    return {"deleted": existed}


@router.post("/cameras/{camera_id}/frame")
async def upload_latest_frame(camera_id: str, file: UploadFile = File(...)) -> dict:
    cam = _store().get_camera(camera_id)
    if cam is None:
        raise HTTPException(status_code=404, detail="camera not found")
    if cam.kind != "push":
        raise HTTPException(status_code=409, detail="frames can only be uploaded to push cameras")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty frame")

    try:
        _store().set_latest_frame(camera_id, content_type=file.content_type or "image/jpeg", data=data)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="camera not found") from e

    return {"ok": True, "bytes": len(data)}


@router.get("/cameras/{camera_id}/latest.jpg")
def latest_jpeg(camera_id: str) -> Response:
    cam = _store().get_camera(camera_id)
    if cam is None:
        raise HTTPException(status_code=404, detail="camera not found")

    if cam.kind == "rtsp":
        try:
            jpg = snapshot_jpeg_from_rtsp(cam.url or "")
        except Exception as e:
            raise HTTPException(status_code=504, detail=f"failed to read rtsp snapshot: {e}") from e
        return Response(content=jpg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    frame = _store().get_latest_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="no frame uploaded yet")
    # Always serve as .jpg for convenience; callers can still inspect Content-Type if they want.
    return Response(
        content=frame.data,
        media_type=frame.content_type or "image/jpeg",
        headers={"Cache-Control": "no-store"},
    )

