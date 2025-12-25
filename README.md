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

Important: **phone browser camera capture requires HTTPS** (a "secure context") on most modern mobile browsers. If you open the UI on a phone at `http://<server>:8000/camera-setup`, the browser may hide/disable `getUserMedia()` and you’ll see an error and no preview. Fix by serving this app behind HTTPS (reverse proxy / tunnel), then open the `https://.../camera-setup` URL on your phone.

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
cp .env.example .env
# Edit .env and set LOGAN_HOST to your server's LAN IP or hostname
docker compose up --build
```

This publishes:

- HTTPS UI/API on **host port 443** (recommended): `https://<LOGAN_HOST>/camera-setup`
- HTTP redirect on **host port 80**: `http://<LOGAN_HOST>/` → HTTPS
- Direct HTTP API on **host port 8000** (optional): `http://<your-server-ip>:8000/health`

### Phone browser camera note (required for streaming)

Phone browsers require HTTPS for camera access. With the Caddy proxy enabled, open:

- `https://<LOGAN_HOST>/camera-setup`

Because this uses an **internal (self-signed) TLS certificate**, your phone must trust Caddy’s local CA once.

#### Export the Caddy root CA cert

From the machine running docker:

```bash
docker compose exec caddy sh -lc 'ls -1 /data/caddy/pki/authorities/local/root.crt'
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
```

Then install/trust `caddy-root.crt` on your phone (steps differ by OS).

#### Android (quick outline)

- Copy `caddy-root.crt` to the phone.
- Settings → Security/Privacy → Encryption & credentials → Install a certificate → **CA certificate** → select the file.

#### iOS (quick outline)

- AirDrop/email the `caddy-root.crt` to the phone and open it.
- Install the profile: Settings → Profile Downloaded.
- Enable trust: Settings → General → About → Certificate Trust Settings → enable trust for the new CA.

Local (example):

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```
