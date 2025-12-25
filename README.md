# Logan 501

Minimal FastAPI backend for a 2-player **501 (legs + sets)** match.

## What this includes (best-of scoring apps)

- **Undo last visit** (`POST /game/undo`)
- **Checkout suggestions** (`GET /game/checkout?remaining=121`)
- **Player stats** (`GET /game/stats`) including 3-dart average, 100+/140+/180s, busts, checkout %

## API

- `GET /health`
- `GET /game` (full match state)
- `POST /game/reset`
- `POST /game/visit` (submit up to 3 darts)
- `POST /game/undo`
- `GET /game/checkout?remaining=<int>`
- `GET /game/stats`

## Run

Docker:

```bash
docker compose up --build
```

Local (example):

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```
