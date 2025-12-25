from __future__ import annotations

from typing import Literal

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.camera.rtsp import snapshot_jpeg_from_rtsp
from app.camera.store import get_camera_store
from app.scoring.dartboard import DartScore, DartboardCalibration, score_darts
from app.scoring.store import get_store


router = APIRouter(prefix="/scoring/dartboard", tags=["dartboard"])

_DARTBOARD_SETUP_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Dartboard scoring</title>
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
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
        background: radial-gradient(1200px 700px at 20% -10%, rgba(78, 161, 255, 0.2), transparent),
          radial-gradient(900px 600px at 90% 0%, rgba(61, 220, 151, 0.14), transparent),
          var(--bg);
        color: var(--text);
      }
      header {
        position: sticky;
        top: 0;
        backdrop-filter: blur(10px);
        background: rgba(11, 18, 32, 0.55);
        border-bottom: 1px solid var(--border);
        z-index: 5;
      }
      .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
      .row { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; }
      .grid { display: grid; gap: 14px; grid-template-columns: 1fr; }
      @media (min-width: 960px) { .grid { grid-template-columns: 1fr 1fr; } }
      .card {
        background: linear-gradient(180deg, rgba(15, 27, 51, 0.88), rgba(15, 27, 51, 0.74));
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px;
      }
      h1 { margin: 0; font-size: 18px; }
      h2 { margin: 0 0 10px; font-size: 15px; }
      .subtitle { margin-top: 6px; color: var(--muted); font-size: 13px; }
      label { font-size: 12px; color: var(--muted); }
      select, input, button {
        font: inherit;
        padding: 10px 10px;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: rgba(5, 10, 20, 0.55);
        color: var(--text);
        outline: none;
      }
      button { cursor: pointer; border-color: rgba(78, 161, 255, 0.35); background: rgba(78, 161, 255, 0.12); }
      button:hover { background: rgba(78, 161, 255, 0.18); }
      button.secondary { border-color: var(--border); background: rgba(232, 238, 252, 0.06); }
      button.secondary:hover { background: rgba(232, 238, 252, 0.10); }
      button.danger { border-color: rgba(255, 92, 122, 0.35); background: rgba(255, 92, 122, 0.14); }
      button.danger:hover { background: rgba(255, 92, 122, 0.20); }
      .field { display: grid; gap: 6px; min-width: 180px; flex: 1; }
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
      .small { font-size: 12px; color: var(--muted); }
      canvas {
        width: 100%;
        max-height: 520px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: rgba(0,0,0,0.22);
      }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
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
    </style>
  </head>
  <body>
    <header>
      <div class="wrap">
        <div class="row" style="justify-content: space-between;">
          <div>
            <h1>Dartboard scoring (starting point)</h1>
            <div class="subtitle">Click to set board center + radius, then click dart tips to get a score.</div>
          </div>
          <div class="row" style="justify-content:flex-end">
            <a class="pill" href="/camera-setup">Camera setup</a>
            <a class="pill" href="/docs" target="_blank" rel="noreferrer">API docs</a>
          </div>
        </div>
      </div>
    </header>

    <main class="wrap">
      <div class="grid">
        <section class="card">
          <h2>Camera + controls</h2>
          <div class="row">
            <div class="field" style="min-width: 320px;">
              <label for="camSelect">Camera</label>
              <select id="camSelect"></select>
            </div>
            <div class="field" style="min-width: 140px; flex: 0.4;">
              <label for="rotation">Rotation (deg)</label>
              <input id="rotation" type="number" step="0.1" value="0" />
            </div>
            <div class="row" style="gap: 8px;">
              <button id="refreshBtn" type="button">Refresh snapshot</button>
              <button id="modeCenterBtn" class="secondary" type="button">Click: center</button>
              <button id="modeRadiusBtn" class="secondary" type="button">Click: radius</button>
              <button id="clearDartsBtn" class="danger" type="button">Clear darts</button>
              <button id="scoreBtn" type="button">Score</button>
            </div>
          </div>
          <div class="small" style="margin-top:10px;">
            Current mode: <span class="mono" id="modeText">dart</span>
            &nbsp;|&nbsp; Center: <span class="mono" id="centerText">unset</span>
            &nbsp;|&nbsp; Radius: <span class="mono" id="radiusText">unset</span>
            &nbsp;|&nbsp; Darts: <span class="mono" id="dartsText">0</span>
          </div>
          <div style="margin-top: 10px;" class="row">
            <button id="saveCalibBtn" class="secondary" type="button">Save calibration</button>
            <button id="saveRefBtn" class="secondary" type="button">Save reference (empty board)</button>
            <button id="autoBtn" class="secondary" type="button">Auto-detect + score</button>
          </div>
          <div style="margin-top: 10px;" class="toast" id="msg"></div>
        </section>

        <section class="card">
          <h2>Result</h2>
          <div class="toast" id="result">No score yet.</div>
          <div class="small" style="margin-top: 10px;">
            Notes: scoring is solid; auto-detect is intentionally rough (diff vs reference) and meant only as a scaffold.
          </div>
        </section>
      </div>

      <section class="card" style="margin-top: 14px;">
        <h2>Snapshot</h2>
        <canvas id="canvas"></canvas>
        <div class="small" style="margin-top: 8px;">
          Click coordinates are in the displayed image pixel space (the backend scores in that same pixel space).
        </div>
      </section>
    </main>

    <script>
      const el = (id) => document.getElementById(id);
      const camSelect = el("camSelect");
      const rotationEl = el("rotation");
      const refreshBtn = el("refreshBtn");
      const modeCenterBtn = el("modeCenterBtn");
      const modeRadiusBtn = el("modeRadiusBtn");
      const clearDartsBtn = el("clearDartsBtn");
      const scoreBtn = el("scoreBtn");
      const saveCalibBtn = el("saveCalibBtn");
      const saveRefBtn = el("saveRefBtn");
      const autoBtn = el("autoBtn");
      const msg = el("msg");
      const result = el("result");

      const canvas = el("canvas");
      const ctx = canvas.getContext("2d");

      const modeText = el("modeText");
      const centerText = el("centerText");
      const radiusText = el("radiusText");
      const dartsText = el("dartsText");

      let img = new Image();
      let mode = "dart"; // center | radius | dart
      let center = null; // {x,y}
      let radius = null; // number
      let darts = []; // {x,y}

      function setMsg(text, kind) {
        msg.textContent = text;
        msg.classList.remove("good", "bad");
        if (kind) msg.classList.add(kind);
      }

      async function api(path, opts) {
        const r = await fetch(path, opts);
        const ct = (r.headers.get("content-type") || "").toLowerCase();
        let body = null;
        if (ct.includes("application/json")) body = await r.json().catch(() => null);
        else body = await r.text().catch(() => "");
        if (!r.ok) {
          const detail = body && body.detail ? body.detail : (typeof body === "string" ? body : "");
          throw new Error(detail || `HTTP ${r.status}`);
        }
        return body;
      }

      function updateHud() {
        modeText.textContent = mode;
        centerText.textContent = center ? `${center.x.toFixed(1)},${center.y.toFixed(1)}` : "unset";
        radiusText.textContent = radius ? radius.toFixed(1) : "unset";
        dartsText.textContent = String(darts.length);
      }

      function redraw() {
        if (!img || !img.complete) return;
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        ctx.drawImage(img, 0, 0);

        // Overlay: center/radius.
        if (center && radius) {
          ctx.strokeStyle = "rgba(78,161,255,0.85)";
          ctx.lineWidth = Math.max(2, canvas.width / 600);
          ctx.beginPath();
          ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
          ctx.stroke();
        }
        if (center) {
          ctx.fillStyle = "rgba(78,161,255,0.95)";
          ctx.beginPath();
          ctx.arc(center.x, center.y, Math.max(4, canvas.width / 220), 0, Math.PI * 2);
          ctx.fill();
        }

        // Overlay: darts.
        for (let i = 0; i < darts.length; i++) {
          const d = darts[i];
          ctx.fillStyle = "rgba(61,220,151,0.95)";
          ctx.beginPath();
          ctx.arc(d.x, d.y, Math.max(4, canvas.width / 240), 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "rgba(232,238,252,0.95)";
          ctx.font = `${Math.max(12, canvas.width / 70)}px ui-monospace, monospace`;
          ctx.fillText(String(i + 1), d.x + 8, d.y - 8);
        }
      }

      function canvasPointFromEvent(ev) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        return {
          x: (ev.clientX - rect.left) * scaleX,
          y: (ev.clientY - rect.top) * scaleY,
        };
      }

      canvas.addEventListener("click", (ev) => {
        if (!img || !img.complete) return;
        const p = canvasPointFromEvent(ev);
        if (mode === "center") {
          center = { x: p.x, y: p.y };
          if (radius && center) radius = radius; // keep
          mode = "dart";
        } else if (mode === "radius") {
          if (!center) {
            setMsg("Set center first.", "bad");
            return;
          }
          const dx = p.x - center.x;
          const dy = p.y - center.y;
          radius = Math.sqrt(dx*dx + dy*dy);
          mode = "dart";
        } else {
          darts.push({ x: p.x, y: p.y });
        }
        updateHud();
        redraw();
      });

      async function loadCameras() {
        const cams = await api("/cameras", { method: "GET" });
        camSelect.innerHTML = "";
        if (!cams.length) {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "No cameras yet — add one in /camera-setup";
          camSelect.appendChild(opt);
          return;
        }
        for (const c of cams) {
          const opt = document.createElement("option");
          opt.value = c.camera_id;
          opt.textContent = `${c.name} (${c.kind})`;
          camSelect.appendChild(opt);
        }
      }

      async function refreshSnapshot() {
        const id = camSelect.value;
        if (!id) return;
        setMsg("Loading snapshot…");
        img = new Image();
        img.onload = () => { redraw(); setMsg("Snapshot loaded.", "good"); };
        img.onerror = () => setMsg("Snapshot failed to load. Check the camera preview in /camera-setup.", "bad");
        img.src = `/cameras/${id}/latest.jpg?ts=${Date.now()}`;
      }

      async function saveCalibration() {
        const id = camSelect.value;
        if (!id) return;
        if (!center || !radius) {
          setMsg("Set both center and radius first.", "bad");
          return;
        }
        const rotation = parseFloat(rotationEl.value || "0") || 0;
        const payload = { center_x: center.x, center_y: center.y, radius_px: radius, rotation_deg: rotation };
        await api(`/scoring/dartboard/${id}/calibration`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        });
        setMsg("Calibration saved.", "good");
      }

      async function scoreManual() {
        const id = camSelect.value;
        if (!id) return;
        if (!center || !radius) {
          setMsg("Set/save calibration first (center + radius).", "bad");
          return;
        }
        await saveCalibration();
        const payload = { darts: darts.map((d) => ({ x: d.x, y: d.y, confidence: 1.0 })), max_darts: 12 };
        const r = await api(`/scoring/dartboard/${id}/score`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        });
        result.textContent = JSON.stringify(r, null, 2);
        setMsg(`Scored ${r.total} from ${r.darts.length} dart(s).`, "good");
      }

      async function saveReference() {
        const id = camSelect.value;
        if (!id) return;
        await saveCalibration();
        const r = await api(`/scoring/dartboard/${id}/reference`, { method: "POST" });
        setMsg(`Reference saved (${r.bytes} bytes).`, "good");
      }

      async function autoScore() {
        const id = camSelect.value;
        if (!id) return;
        await saveCalibration();
        const r = await api(`/scoring/dartboard/${id}/score`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ auto_detect: true, max_darts: 3 }),
        });
        result.textContent = JSON.stringify(r, null, 2);
        setMsg(`Auto-scored ${r.total} from ${r.darts.length} candidate(s).`, r.darts.length ? "good" : "bad");
      }

      modeCenterBtn.addEventListener("click", () => { mode = "center"; updateHud(); setMsg("Click the board center.", "good"); });
      modeRadiusBtn.addEventListener("click", () => { mode = "radius"; updateHud(); setMsg("Click the outer edge of the board (double ring outer).", "good"); });
      clearDartsBtn.addEventListener("click", () => { darts = []; updateHud(); redraw(); setMsg("Darts cleared."); });
      refreshBtn.addEventListener("click", () => refreshSnapshot());
      saveCalibBtn.addEventListener("click", () => saveCalibration().catch((e) => setMsg(`Save calibration failed: ${e.message || e}`, "bad")));
      scoreBtn.addEventListener("click", () => scoreManual().catch((e) => setMsg(`Score failed: ${e.message || e}`, "bad")));
      saveRefBtn.addEventListener("click", () => saveReference().catch((e) => setMsg(`Save reference failed: ${e.message || e}`, "bad")));
      autoBtn.addEventListener("click", () => autoScore().catch((e) => setMsg(`Auto-detect failed: ${e.message || e}`, "bad")));

      camSelect.addEventListener("change", () => {
        center = null; radius = null; darts = [];
        updateHud();
        refreshSnapshot();
      });

      (async () => {
        updateHud();
        try {
          await loadCameras();
          await refreshSnapshot();
          setMsg("Ready.", "good");
        } catch (e) {
          setMsg(`Init failed: ${e.message || e}`, "bad");
        }
      })();
    </script>
  </body>
</html>
"""


class CalibrationRequest(BaseModel):
    center_x: float = Field(..., description="Board center x (pixels)")
    center_y: float = Field(..., description="Board center y (pixels)")
    radius_px: float = Field(..., gt=0, description="Board radius in pixels (outer edge of double ring)")
    rotation_deg: float = Field(
        default=0.0,
        description="Rotation offset in degrees. 0 = 20 at 12 o'clock; positive rotates clockwise.",
    )


class CalibrationResponse(BaseModel):
    camera_id: str
    center_x: float
    center_y: float
    radius_px: float
    rotation_deg: float


class DartPixel(BaseModel):
    x: float
    y: float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ScoreRequest(BaseModel):
    darts: list[DartPixel] | None = Field(
        default=None,
        description="Optional dart tip pixel coordinates. If provided, these will be scored directly.",
    )
    auto_detect: bool = Field(
        default=False,
        description="If true and darts are not provided, attempt a simple diff-based detection using a saved reference frame.",
    )
    max_darts: int = Field(default=3, ge=1, le=12)


class ScoredDartDTO(BaseModel):
    x: float
    y: float
    value: int
    multiplier: int
    score: int
    ring: str
    sector: int | None
    angle_deg: float
    radius_ratio: float
    confidence: float


class ScoreResponse(BaseModel):
    camera_id: str
    source: Literal["manual", "auto"]
    total: int
    darts: list[ScoredDartDTO]


def _store():
    return get_store()


def _camera_store():
    return get_camera_store()


def _latest_jpeg_bytes(camera_id: str) -> bytes:
    cam = _camera_store().get_camera(camera_id)
    if cam is None:
        raise HTTPException(status_code=404, detail="camera not found")

    if cam.kind == "rtsp":
        try:
            return snapshot_jpeg_from_rtsp(cam.url or "")
        except Exception as e:
            raise HTTPException(status_code=504, detail=f"failed to read rtsp snapshot: {e}") from e

    frame = _camera_store().get_latest_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="no frame uploaded yet")
    return frame.data


def _decode_jpeg(jpg: bytes):
    arr = np.frombuffer(jpg, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("failed to decode jpeg")
    return img


def _auto_detect_darts(
    *,
    reference_jpg: bytes,
    current_jpg: bytes,
    calib: DartboardCalibration,
    max_darts: int,
) -> list[tuple[float, float, float]]:
    """
    Very rough starting point for dart detection:
    - Requires a reference "empty board" image per camera
    - Computes absdiff within the board circle and extracts a few biggest blobs
    - Returns blob centroids as (x,y,confidence)
    """
    ref = _decode_jpeg(reference_jpg)
    cur = _decode_jpeg(current_jpg)

    if cur.shape[:2] != ref.shape[:2]:
        cur = cv2.resize(cur, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)

    ref_g = cv2.GaussianBlur(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), (7, 7), 0)
    cur_g = cv2.GaussianBlur(cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY), (7, 7), 0)

    diff = cv2.absdiff(ref_g, cur_g)
    _, bw = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)

    # Mask to board circle (+ small margin).
    h, w = bw.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    r = int(max(1, round(calib.radius_px * 1.05)))
    cx = int(round(calib.center_x))
    cy = int(round(calib.center_y))
    cv2.circle(mask, (cx, cy), r, 255, thickness=-1)
    bw = cv2.bitwise_and(bw, mask)

    # Clean noise.
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    bw = cv2.dilate(bw, np.ones((3, 3), np.uint8), iterations=1)

    contours, _hier = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, float, float, float]] = []  # x,y,conf,area
    for c in contours:
        area = float(cv2.contourArea(c))
        if area < 35.0:
            continue
        m = cv2.moments(c)
        if m.get("m00", 0.0) == 0.0:
            continue
        x = float(m["m10"] / m["m00"])
        y = float(m["m01"] / m["m00"])
        # Keep only within the board radius.
        dx = x - calib.center_x
        dy = y - calib.center_y
        if (dx * dx + dy * dy) > (calib.radius_px * 1.02) ** 2:
            continue
        conf = max(0.15, min(0.65, area / 1500.0))
        candidates.append((x, y, conf, area))

    candidates.sort(key=lambda t: t[3], reverse=True)
    return [(x, y, conf) for (x, y, conf, _a) in candidates[:max_darts]]


@router.get("/ui", include_in_schema=False, response_class=HTMLResponse)
def dartboard_ui() -> HTMLResponse:
    return HTMLResponse(content=_DARTBOARD_SETUP_HTML)


@router.get("/{camera_id}/calibration", response_model=CalibrationResponse)
def get_calibration(camera_id: str) -> CalibrationResponse:
    calib = _store().get_dartboard_calibration(camera_id)
    if calib is None:
        raise HTTPException(status_code=404, detail="no calibration for this camera yet")
    return CalibrationResponse(
        camera_id=camera_id,
        center_x=calib.center_x,
        center_y=calib.center_y,
        radius_px=calib.radius_px,
        rotation_deg=calib.rotation_deg,
    )


@router.put("/{camera_id}/calibration", response_model=CalibrationResponse)
def set_calibration(camera_id: str, req: CalibrationRequest) -> CalibrationResponse:
    # Validate camera exists for nicer UX.
    if _camera_store().get_camera(camera_id) is None:
        raise HTTPException(status_code=404, detail="camera not found")

    try:
        calib = DartboardCalibration(
            center_x=req.center_x,
            center_y=req.center_y,
            radius_px=req.radius_px,
            rotation_deg=req.rotation_deg,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    _store().set_dartboard_calibration(camera_id, calib)
    return CalibrationResponse(
        camera_id=camera_id,
        center_x=calib.center_x,
        center_y=calib.center_y,
        radius_px=calib.radius_px,
        rotation_deg=calib.rotation_deg,
    )


@router.post("/{camera_id}/reference")
def set_reference(camera_id: str) -> dict:
    """
    Capture and store a reference snapshot (ideally an empty board).
    """
    calib = _store().get_dartboard_calibration(camera_id)
    if calib is None:
        raise HTTPException(status_code=409, detail="set calibration first")

    jpg = _latest_jpeg_bytes(camera_id)
    _store().set_dartboard_reference_jpeg(camera_id, jpg)
    return {"ok": True, "bytes": len(jpg)}


@router.delete("/{camera_id}/reference")
def clear_reference(camera_id: str) -> dict:
    _store().clear_dartboard_reference(camera_id)
    return {"ok": True}


@router.post("/{camera_id}/score", response_model=ScoreResponse)
def score_camera(camera_id: str, req: ScoreRequest) -> ScoreResponse:
    calib = _store().get_dartboard_calibration(camera_id)
    if calib is None:
        raise HTTPException(status_code=409, detail="set calibration first")

    source: Literal["manual", "auto"]
    dart_points: list[tuple[float, float, float]]

    if req.darts is not None and len(req.darts) > 0:
        source = "manual"
        dart_points = [(d.x, d.y, d.confidence) for d in req.darts[: req.max_darts]]
    else:
        if not req.auto_detect:
            raise HTTPException(status_code=422, detail="provide darts[] or set auto_detect=true")
        ref = _store().get_dartboard_reference_jpeg(camera_id)
        if ref is None:
            raise HTTPException(status_code=409, detail="auto_detect requires a saved reference frame; POST /reference first")
        cur = _latest_jpeg_bytes(camera_id)
        try:
            dart_points = _auto_detect_darts(
                reference_jpg=ref,
                current_jpg=cur,
                calib=calib,
                max_darts=req.max_darts,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        source = "auto"

    scored, total = score_darts(dart_points, calib=calib)

    def _to_dto(d: DartScore) -> ScoredDartDTO:
        return ScoredDartDTO(
            x=d.x,
            y=d.y,
            value=d.value,
            multiplier=d.multiplier,
            score=d.score,
            ring=d.ring,
            sector=d.sector,
            angle_deg=d.angle_deg,
            radius_ratio=d.radius_ratio,
            confidence=d.confidence,
        )

    return ScoreResponse(camera_id=camera_id, source=source, total=total, darts=[_to_dto(d) for d in scored])

