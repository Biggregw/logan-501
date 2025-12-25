from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from app.camera.rtsp import snapshot_jpeg_from_rtsp
from app.camera.store import Camera, InMemoryCameraStore, get_camera_store

router = APIRouter(tags=["cameras"])

_CAMERA_SETUP_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Camera setup</title>
    <style>
      :root {
        --bg: #0b1220;
        --panel: #0f1b33;
        --muted: #9db0d0;
        --text: #e8eefc;
        --border: rgba(232, 238, 252, 0.12);
        --accent: #4ea1ff;
        --good: #3ddc97;
        --bad: #ff5c7a;
        --warn: #ffd166;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji",
          "Segoe UI Emoji";
        background: radial-gradient(1200px 700px at 20% -10%, rgba(78, 161, 255, 0.2), transparent),
          radial-gradient(900px 600px at 90% 0%, rgba(61, 220, 151, 0.14), transparent),
          var(--bg);
        color: var(--text);
      }
      a { color: var(--accent); text-decoration: none; }
      a:hover { text-decoration: underline; }
      header {
        position: sticky;
        top: 0;
        backdrop-filter: blur(10px);
        background: rgba(11, 18, 32, 0.55);
        border-bottom: 1px solid var(--border);
        z-index: 5;
      }
      .wrap { max-width: 1100px; margin: 0 auto; padding: 16px; }
      .titleRow { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      h1 { margin: 0; font-size: 20px; letter-spacing: 0.2px; }
      .subtitle { margin: 6px 0 0; color: var(--muted); font-size: 13px; }
      .grid { display: grid; gap: 14px; grid-template-columns: 1fr; padding-bottom: 24px; }
      @media (min-width: 960px) { .grid { grid-template-columns: 1fr 1fr; } }
      .card {
        background: linear-gradient(180deg, rgba(15, 27, 51, 0.88), rgba(15, 27, 51, 0.74));
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px;
      }
      .card h2 { margin: 0 0 10px; font-size: 15px; }
      .row { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; }
      .field { display: grid; gap: 6px; min-width: 210px; flex: 1; }
      label { font-size: 12px; color: var(--muted); }
      input, select, button, textarea {
        font: inherit;
        padding: 10px 10px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: rgba(5, 10, 20, 0.55);
        color: var(--text);
        outline: none;
      }
      input::placeholder { color: rgba(157, 176, 208, 0.55); }
      button {
        cursor: pointer;
        border-color: rgba(78, 161, 255, 0.35);
        background: rgba(78, 161, 255, 0.12);
      }
      button:hover { background: rgba(78, 161, 255, 0.18); }
      button.secondary { border-color: var(--border); background: rgba(232, 238, 252, 0.06); }
      button.secondary:hover { background: rgba(232, 238, 252, 0.10); }
      button.danger { border-color: rgba(255, 92, 122, 0.35); background: rgba(255, 92, 122, 0.14); }
      button.danger:hover { background: rgba(255, 92, 122, 0.20); }
      button:disabled { opacity: 0.55; cursor: not-allowed; }
      .pill {
        display: inline-flex;
        gap: 6px;
        align-items: center;
        font-size: 12px;
        padding: 3px 8px;
        border-radius: 999px;
        border: 1px solid var(--border);
        color: var(--muted);
        background: rgba(232, 238, 252, 0.05);
      }
      .pill.good { border-color: rgba(61, 220, 151, 0.35); color: rgba(61, 220, 151, 0.95); }
      .pill.warn { border-color: rgba(255, 209, 102, 0.35); color: rgba(255, 209, 102, 0.98); }
      .pill.bad { border-color: rgba(255, 92, 122, 0.35); color: rgba(255, 92, 122, 0.98); }
      .divider { height: 1px; background: var(--border); margin: 12px 0; }
      .help { font-size: 13px; color: var(--muted); line-height: 1.35; }
      .small { font-size: 12px; color: var(--muted); }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
      .list { display: grid; gap: 10px; }
      .cam {
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 10px;
        background: rgba(5, 10, 20, 0.28);
        display: grid;
        gap: 10px;
      }
      .camTop { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; align-items: center; }
      .camName { font-weight: 600; }
      .camMeta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
      .camActions { display: flex; gap: 8px; flex-wrap: wrap; }
      img.preview {
        width: 100%;
        max-height: 300px;
        object-fit: contain;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: rgba(0,0,0,0.22);
      }
      .statusBar {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
      }
      .toast {
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 10px 12px;
        background: rgba(5, 10, 20, 0.35);
        color: var(--muted);
        white-space: pre-wrap;
      }
      .toast.good { border-color: rgba(61, 220, 151, 0.35); color: rgba(61, 220, 151, 0.95); }
      .toast.bad { border-color: rgba(255, 92, 122, 0.35); color: rgba(255, 92, 122, 0.98); }
      video {
        width: 100%;
        max-height: 260px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: rgba(0,0,0,0.22);
      }
    </style>
  </head>
  <body>
    <header>
      <div class="wrap">
        <div class="titleRow">
          <div>
            <h1>Camera setup</h1>
            <div class="subtitle">Register cameras, preview frames, and (optionally) stream frames from a phone browser.</div>
          </div>
          <div class="row" style="justify-content:flex-end">
            <a class="pill" href="/docs" target="_blank" rel="noreferrer">API docs</a>
            <button class="secondary" id="refreshBtn" type="button">Refresh</button>
          </div>
        </div>
      </div>
    </header>

    <main class="wrap">
      <div class="grid">
        <section class="card">
          <h2>Add a camera</h2>
          <div class="help">
            <div><span class="pill">push</span> = phone/browser uploads frames to the server.</div>
            <div><span class="pill">rtsp</span> = server grabs snapshots from an RTSP URL.</div>
          </div>
          <div class="divider"></div>
          <form id="createForm">
            <div class="row">
              <div class="field">
                <label for="camName">Name</label>
                <input id="camName" name="name" placeholder="e.g. Oche / Board / Room" required maxlength="100" />
              </div>
              <div class="field" style="min-width: 160px; flex: 0.6;">
                <label for="camKind">Kind</label>
                <select id="camKind" name="kind">
                  <option value="push">push (phone/browser)</option>
                  <option value="rtsp">rtsp (security/IP cam)</option>
                </select>
              </div>
              <div class="field" id="rtspField" style="display:none;">
                <label for="camUrl">RTSP URL</label>
                <input id="camUrl" name="url" placeholder="rtsp://user:pass@192.168.1.50:554/stream1" />
              </div>
              <div style="min-width: 140px;">
                <button id="createBtn" type="submit">Add camera</button>
              </div>
            </div>
          </form>
          <div class="divider"></div>
          <div id="createMsg" class="toast" style="display:none;"></div>
          <div class="small">
            Tip: If you’re setting up from a phone, open this page on the phone’s browser and use the “Phone push streaming” panel.
          </div>
        </section>

        <section class="card">
          <h2>Phone push streaming (optional)</h2>
          <div class="help">
            Use this if you want a quick “phone camera” feed without building a separate uploader app.
            Works best on a phone using the rear camera. Frames are uploaded as JPEG.
          </div>
          <div class="divider"></div>
          <div class="row">
            <div class="field" style="min-width: 280px;">
              <label for="pushCamSelect">Push camera target</label>
              <select id="pushCamSelect"></select>
            </div>
            <div class="field" style="min-width: 180px; flex: 0.6;">
              <label for="fpsSelect">Upload rate</label>
              <select id="fpsSelect">
                <option value="2000">0.5 fps (2s)</option>
                <option value="1000" selected>1 fps (1s)</option>
                <option value="500">2 fps (0.5s)</option>
              </select>
            </div>
            <div class="camActions">
              <button id="startPhoneBtn" type="button">Start</button>
              <button id="stopPhoneBtn" class="secondary" type="button" disabled>Stop</button>
            </div>
          </div>
          <div style="margin-top: 10px;">
            <video id="phoneVideo" playsinline muted autoplay></video>
            <canvas id="phoneCanvas" style="display:none;"></canvas>
          </div>
          <div class="divider"></div>
          <div id="phoneMsg" class="toast" style="display:none;"></div>
          <div class="small mono" id="phoneEndpoints" style="margin-top: 6px;"></div>
        </section>
      </div>

      <section class="card">
        <div class="statusBar">
          <h2 style="margin:0;">Cameras</h2>
          <div class="small" id="statusText">Loading…</div>
        </div>
        <div class="divider"></div>
        <div id="cameraList" class="list"></div>
      </section>
    </main>

    <script>
      const el = (id) => document.getElementById(id);
      const statusText = el("statusText");
      const cameraList = el("cameraList");
      const createForm = el("createForm");
      const camKind = el("camKind");
      const rtspField = el("rtspField");
      const camUrl = el("camUrl");
      const createMsg = el("createMsg");
      const refreshBtn = el("refreshBtn");

      const pushCamSelect = el("pushCamSelect");
      const phoneVideo = el("phoneVideo");
      const phoneCanvas = el("phoneCanvas");
      const phoneMsg = el("phoneMsg");
      const phoneEndpoints = el("phoneEndpoints");
      const startPhoneBtn = el("startPhoneBtn");
      const stopPhoneBtn = el("stopPhoneBtn");
      const fpsSelect = el("fpsSelect");

      let cameras = [];
      let phoneStream = null;
      let phoneTimer = null;

      function showToast(node, text, kind) {
        node.textContent = text;
        node.classList.remove("good", "bad");
        if (kind) node.classList.add(kind);
        node.style.display = "block";
      }
      function hideToast(node) {
        node.style.display = "none";
        node.textContent = "";
        node.classList.remove("good", "bad");
      }

      function maskRtsp(url) {
        if (!url) return "";
        try {
          const u = new URL(url);
          if (u.username || u.password) {
            u.username = u.username ? "****" : "";
            u.password = u.password ? "****" : "";
          }
          return u.toString();
        } catch {
          // If it isn't parseable, return something safer.
          return url.replace(/:\\/\\/([^@]+)@/, "://****:****@");
        }
      }

      async function api(path, opts) {
        const r = await fetch(path, opts);
        const ct = (r.headers.get("content-type") || "").toLowerCase();
        let body = null;
        if (ct.includes("application/json")) {
          body = await r.json().catch(() => null);
        } else {
          body = await r.text().catch(() => "");
        }
        if (!r.ok) {
          const detail = body && body.detail ? body.detail : (typeof body === "string" ? body : "");
          throw new Error(detail || `HTTP ${r.status}`);
        }
        return body;
      }

      function renderPushSelector() {
        const pushCams = cameras.filter((c) => c.kind === "push");
        pushCamSelect.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = pushCams.length ? "Select a push camera…" : "No push cameras yet — add one above";
        pushCamSelect.appendChild(placeholder);
        for (const c of pushCams) {
          const opt = document.createElement("option");
          opt.value = c.camera_id;
          opt.textContent = `${c.name} (${c.camera_id.slice(0, 8)}…)`;
          pushCamSelect.appendChild(opt);
        }
      }

      function updatePhoneEndpoints() {
        const id = pushCamSelect.value;
        if (!id) {
          phoneEndpoints.textContent = "";
          return;
        }
        phoneEndpoints.textContent =
          `Upload: POST /cameras/${id}/frame    Preview: GET /cameras/${id}/latest.jpg`;
      }

      function cameraCard(cam) {
        const root = document.createElement("div");
        root.className = "cam";

        const top = document.createElement("div");
        top.className = "camTop";

        const left = document.createElement("div");
        left.style.minWidth = "260px";
        left.style.flex = "1";

        const name = document.createElement("div");
        name.className = "camName";
        name.textContent = cam.name;

        const meta = document.createElement("div");
        meta.className = "camMeta";

        const kindPill = document.createElement("span");
        kindPill.className = "pill";
        kindPill.textContent = cam.kind;
        meta.appendChild(kindPill);

        const idPill = document.createElement("span");
        idPill.className = "pill mono";
        idPill.textContent = cam.camera_id;
        meta.appendChild(idPill);

        if (cam.kind === "rtsp") {
          const urlPill = document.createElement("span");
          urlPill.className = "pill mono";
          urlPill.title = cam.url || "";
          urlPill.textContent = maskRtsp(cam.url);
          meta.appendChild(urlPill);
        }

        left.appendChild(name);
        left.appendChild(meta);

        const actions = document.createElement("div");
        actions.className = "camActions";

        const refresh = document.createElement("button");
        refresh.type = "button";
        refresh.className = "secondary";
        refresh.textContent = "Refresh preview";

        const del = document.createElement("button");
        del.type = "button";
        del.className = "danger";
        del.textContent = "Delete";

        actions.appendChild(refresh);
        actions.appendChild(del);

        top.appendChild(left);
        top.appendChild(actions);

        const img = document.createElement("img");
        img.className = "preview";
        img.alt = `Preview for ${cam.name}`;

        const msg = document.createElement("div");
        msg.className = "toast";
        msg.style.display = "none";

        function setPreview() {
          hideToast(msg);
          img.src = `/cameras/${cam.camera_id}/latest.jpg?ts=${Date.now()}`;
        }

        img.addEventListener("error", () => {
          showToast(
            msg,
            cam.kind === "push"
              ? "No frame yet. If this is a phone/push camera, start streaming (or upload a frame) then refresh."
              : "Preview failed. Check RTSP URL / camera connectivity, then refresh.",
            "bad"
          );
        });
        img.addEventListener("load", () => {
          showToast(
            msg,
            cam.kind === "push" ? "Frame received OK." : "Snapshot received OK.",
            "good"
          );
        });

        refresh.addEventListener("click", () => setPreview());
        del.addEventListener("click", async () => {
          if (!confirm(`Delete camera “${cam.name}”?`)) return;
          try {
            await api(`/cameras/${cam.camera_id}`, { method: "DELETE" });
            await load();
          } catch (e) {
            alert(`Delete failed: ${e.message || e}`);
          }
        });

        root.appendChild(top);
        root.appendChild(img);
        root.appendChild(msg);

        // Try to load a preview immediately, but don't spam RTSP fetches.
        setTimeout(setPreview, cam.kind === "rtsp" ? 250 : 50);
        return root;
      }

      async function load() {
        statusText.textContent = "Loading…";
        hideToast(createMsg);
        try {
          cameras = await api("/cameras", { method: "GET" });
          renderPushSelector();
          updatePhoneEndpoints();
          cameraList.innerHTML = "";
          if (!cameras.length) {
            const empty = document.createElement("div");
            empty.className = "toast";
            empty.textContent = "No cameras yet. Add one above to get started.";
            cameraList.appendChild(empty);
          } else {
            for (const cam of cameras) cameraList.appendChild(cameraCard(cam));
          }
          statusText.textContent = `${cameras.length} camera(s)`;
        } catch (e) {
          statusText.textContent = "Error";
          cameraList.innerHTML = "";
          const err = document.createElement("div");
          err.className = "toast bad";
          err.textContent = `Failed to load cameras: ${e.message || e}`;
          cameraList.appendChild(err);
        }
      }

      camKind.addEventListener("change", () => {
        const isRtsp = camKind.value === "rtsp";
        rtspField.style.display = isRtsp ? "" : "none";
        camUrl.required = isRtsp;
        if (!isRtsp) camUrl.value = "";
      });

      createForm.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        hideToast(createMsg);
        const name = el("camName").value.trim();
        const kind = camKind.value;
        const url = camUrl.value.trim();
        const payload = { name, kind };
        if (kind === "rtsp") payload.url = url;
        try {
          const created = await api("/cameras", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(payload),
          });
          showToast(createMsg, `Added: ${created.name} (${created.kind})`, "good");
          el("camName").value = "";
          camUrl.value = "";
          await load();
        } catch (e) {
          showToast(createMsg, `Could not add camera: ${e.message || e}`, "bad");
        }
      });

      refreshBtn.addEventListener("click", () => load());

      pushCamSelect.addEventListener("change", () => {
        updatePhoneEndpoints();
        hideToast(phoneMsg);
      });

      async function startPhone() {
        hideToast(phoneMsg);
        const cameraId = pushCamSelect.value;
        if (!cameraId) {
          showToast(phoneMsg, "Pick a push camera target first (or add one above).", "bad");
          return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          showToast(phoneMsg, "This browser doesn’t support getUserMedia(). Try a modern mobile browser.", "bad");
          return;
        }

        try {
          phoneStream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: { ideal: "environment" } },
          });
          phoneVideo.srcObject = phoneStream;
        } catch (e) {
          showToast(phoneMsg, `Camera permission failed: ${e.message || e}`, "bad");
          return;
        }

        const intervalMs = parseInt(fpsSelect.value, 10) || 1000;
        startPhoneBtn.disabled = true;
        stopPhoneBtn.disabled = false;

        showToast(
          phoneMsg,
          "Streaming started. Leave this tab open. If preview doesn’t update, try increasing the interval or refreshing the camera preview.",
          "good"
        );

        phoneTimer = setInterval(async () => {
          try {
            const w = phoneVideo.videoWidth || 1280;
            const h = phoneVideo.videoHeight || 720;
            phoneCanvas.width = w;
            phoneCanvas.height = h;
            const ctx = phoneCanvas.getContext("2d");
            ctx.drawImage(phoneVideo, 0, 0, w, h);
            const blob = await new Promise((resolve) => phoneCanvas.toBlob(resolve, "image/jpeg", 0.75));
            if (!blob) throw new Error("failed to encode jpeg");
            const fd = new FormData();
            fd.append("file", blob, "frame.jpg");
            const r = await fetch(`/cameras/${cameraId}/frame`, { method: "POST", body: fd });
            if (!r.ok) {
              let detail = "";
              try {
                const j = await r.json();
                detail = j.detail || "";
              } catch {}
              throw new Error(detail || `HTTP ${r.status}`);
            }
          } catch (e) {
            showToast(phoneMsg, `Upload error: ${e.message || e}`, "bad");
          }
        }, intervalMs);
      }

      function stopPhone() {
        if (phoneTimer) clearInterval(phoneTimer);
        phoneTimer = null;
        if (phoneStream) {
          for (const t of phoneStream.getTracks()) t.stop();
        }
        phoneStream = null;
        phoneVideo.srcObject = null;
        startPhoneBtn.disabled = false;
        stopPhoneBtn.disabled = true;
        showToast(phoneMsg, "Streaming stopped.", "warn");
      }

      startPhoneBtn.addEventListener("click", () => startPhone());
      stopPhoneBtn.addEventListener("click", () => stopPhone());

      // Initial load
      load();
    </script>
  </body>
</html>
"""


@router.get("/camera-setup", include_in_schema=False, response_class=HTMLResponse)
def camera_setup_page() -> HTMLResponse:
    return HTMLResponse(content=_CAMERA_SETUP_HTML)


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

