# Logan 501

Minimal FastAPI backend for a 2-player **501 (legs + sets)** match.

## What this includes (best-of scoring apps)

- **Undo last visit** (`POST /game/undo`)
- **Checkout suggestions** (`GET /game/checkout?remaining=121`)
- **Player stats** (`GET /game/stats`) including 3-dart average, 100+/140+/180s, busts, checkout %

## API

- `GET /health`
- Camera ingest:
  - `POST /cameras` (register a camera source)
  - `GET /cameras`
  - `GET /cameras/{camera_id}`
  - `DELETE /cameras/{camera_id}`
  - `POST /cameras/{camera_id}/frame` (phone/push cameras upload a frame)
  - `GET /cameras/{camera_id}/latest.jpg` (latest frame for push cameras, or an RTSP snapshot)
- `GET /game` (full match state)
- `POST /game/reset`
- `POST /game/visit` (submit up to 3 darts)
- `POST /game/undo`
- `GET /game/checkout?remaining=<int>`
- `GET /game/stats`

## Camera feeds (phone + security cameras)

This backend supports two camera source types:

- **push**: a phone/browser (or any client) pushes frames to the server.
- **rtsp**: the server pulls a snapshot from an RTSP URL (common for security/IP cameras).

### Phone camera (push frames)

1) Register a push camera:

```bash
curl -sS -X POST "http://localhost:8000/cameras" \
  -H "content-type: application/json" \
  -d '{"name":"Phone","kind":"push"}'
```

2) Upload a JPEG frame (example uses a local file):

```bash
curl -sS -X POST "http://localhost:8000/cameras/<camera_id>/frame" \
  -F "file=@frame.jpg;type=image/jpeg"
```

3) Fetch the latest uploaded frame:

```bash
curl -sS "http://localhost:8000/cameras/<camera_id>/latest.jpg" --output latest.jpg
```

### Security / IP camera (RTSP)

Register an RTSP camera (typical format: `rtsp://user:pass@host:554/path`):

```bash
curl -sS -X POST "http://localhost:8000/cameras" \
  -H "content-type: application/json" \
  -d '{"name":"FrontDoor","kind":"rtsp","url":"rtsp://user:pass@192.168.1.50:554/stream1"}'
```

Fetch a snapshot:

```bash
curl -sS "http://localhost:8000/cameras/<camera_id>/latest.jpg" --output snapshot.jpg
```

## Run

Docker:

```bash
docker compose up --build
```

This publishes the API on **host port 8000** (e.g. `http://<your-server-ip>:8000/health`).

Local (example):

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```
