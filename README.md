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
docker compose up --build
```

This publishes the backend on:

- HTTP UI/API on **host port 8000**: `http://<your-server-ip>:8000/health`

Local (example):

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

### Phone browser camera note (required for streaming)

Phone browsers require **HTTPS** for camera access. For production use, put this app behind a real HTTPS reverse proxy (recommended: Nginx Proxy Manager) and open:

- `https://<your-domain>/camera-setup`

## Production HTTPS Setup (DuckDNS + Nginx Proxy Manager)

This setup uses your existing **Nginx Proxy Manager (NPM)** to terminate TLS with a free **Let’s Encrypt** certificate, so phone browsers can access `/camera-setup` with valid HTTPS.

This **eliminates the need for any Caddy self-signed certificate / “trust this CA on your phone”** workflow.

### 1) Get a free domain with DuckDNS.org and point it at your server

1. Create an account at DuckDNS and add a subdomain (example): `logan501.duckdns.org`
2. From the DuckDNS dashboard, copy your **token**
3. Keep DuckDNS updated with your current public IP (pick one approach):

- Option A (simple cron job on the server):

```bash
# Replace SUBDOMAIN and TOKEN, then run periodically (e.g. every 5 minutes)
curl -fsS "https://www.duckdns.org/update?domains=SUBDOMAIN&token=TOKEN&ip="
```

- Option B (DuckDNS “install” script / client):
  - Use the DuckDNS site’s install instructions to run their updater on your server.

After DNS updates, verify your domain resolves to your server’s public IP:

- `logan501.duckdns.org` → your server

Important for Let’s Encrypt:

- Your router/firewall must allow inbound **80/443** to the machine running NPM.
- If your ISP uses CGNAT (no public inbound ports), Let’s Encrypt HTTP validation may fail without an alternative setup.

### 2) Configure Nginx Proxy Manager (NPM) to proxy Logan-501 and request SSL

Pre-reqs:

- NPM is already listening on **ports 80/443** on the server
- The Logan-501 backend is reachable from NPM at `http://<server-ip>:8000`
  - Most commonly this is your server’s **LAN IP** (example: `192.168.1.10`) and port `8000`
  - In this repo’s `docker-compose.yml`, the container’s port `8000` is published on the host as `8000:8000`, so NPM can forward to the host’s port `8000`.
  - If your NPM container is on the same Docker network as this app, you can also use **Forward Hostname** = `logan501` and **Forward Port** = `8000`.

#### Create a Proxy Host

In the NPM admin UI:

1. Go to **Hosts → Proxy Hosts**
2. Click **Add Proxy Host**
3. Fill in the fields like this (example values shown):

**Screenshot 1: “Add Proxy Host” → Details tab**

- **Domain Names**: `logan501.duckdns.org`
- **Scheme**: `http`
- **Forward Hostname / IP**: `<YOUR_SERVER_LAN_IP>` (example: `192.168.1.10`)
- **Forward Port**: `8000`
- **Cache Assets**: off (optional)
- **Block Common Exploits**: on (recommended)
- **Websockets Support**: off (optional)

**Screenshot 1b: “Add Proxy Host” → Advanced tab (optional)**

If you upload larger JPEG frames and see `413 Request Entity Too Large`, add:

```nginx
client_max_body_size 20m;
```

#### Request a Let’s Encrypt certificate

Still in the same “Add Proxy Host” modal:

1. Open the **SSL** tab
2. Select **Request a new SSL Certificate**
3. Toggle:
   - **Force SSL**: on
   - **HTTP/2 Support**: on (recommended)
   - **HSTS Enabled**: optional (recommended once you’re confident things work)
4. Agree to the Let’s Encrypt TOS
5. Click **Save**

**Screenshot 2: “Add Proxy Host” → SSL tab**

- **SSL Certificate**: “Request a new SSL Certificate”
- **Email Address**: your email (used by Let’s Encrypt)
- **Force SSL**: enabled
- **HTTP/2 Support**: enabled
- **HSTS Enabled**: optional

**Screenshot 3: “Proxy Hosts” list after saving**

- You should see an entry for `logan501.duckdns.org` showing it forwards to `<YOUR_SERVER_LAN_IP>:8000`, with SSL enabled.

### 3) Validate from your phone

On your phone (on cellular or Wi‑Fi), open:

- `https://logan501.duckdns.org/camera-setup`

Quick checks:

- `https://logan501.duckdns.org/health` should return `{"ok":true,...}` (or similar)
- The camera preview should load without “HTTPS / secure context” errors

### Notes / troubleshooting

- **Port 8000 exposure**: Ideally keep `8000` accessible only on your LAN (or only from the NPM host) and expose **only 80/443** to the internet.
- **NPM → backend connectivity**: If NPM is running in Docker and cannot reach the host via `127.0.0.1`, use the server’s LAN IP (recommended) or your Docker host gateway address.
