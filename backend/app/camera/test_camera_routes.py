from __future__ import annotations

from fastapi.testclient import TestClient

from app.camera.store import get_camera_store
from app.main import app


def test_root_redirects_browsers_to_camera_setup() -> None:
    client = TestClient(app)
    r = client.get("/", headers={"accept": "text/html"}, follow_redirects=False)
    assert r.status_code in {302, 307}, r.text
    assert r.headers["location"] == "/camera-setup"


def test_camera_setup_page_loads() -> None:
    client = TestClient(app)
    r = client.get("/camera-setup", headers={"accept": "text/html"})
    assert r.status_code == 200, r.text
    assert "Camera setup" in r.text


def test_push_camera_upload_and_fetch_latest_jpeg() -> None:
    get_camera_store().clear()
    client = TestClient(app)

    r = client.post("/cameras", json={"name": "Phone", "kind": "push"})
    assert r.status_code == 200, r.text
    camera_id = r.json()["camera_id"]

    jpg = b"\xff\xd8\xff" + b"\x00" * 10 + b"\xff\xd9"  # minimal-ish jpeg marker payload
    r = client.post(
        f"/cameras/{camera_id}/frame",
        files={"file": ("frame.jpg", jpg, "image/jpeg")},
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/cameras/{camera_id}/latest.jpg")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/")
    assert r.content == jpg

