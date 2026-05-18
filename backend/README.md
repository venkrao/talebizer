# Talebizer API (desktop Phase 1)

Minimal **FastAPI** layer in front of the existing Python core (`get_portfolio_frames`, LangGraph chat, `SafeIB`). Binds to **loopback only** in the commands below—do not expose this service on a LAN interface without adding auth and hardening.

## Run (development)

From the **repository root** (where `.env` lives):

```bash
pip install -r requirements.txt
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

Open interactive docs: [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs)

For the minimal **React + Vite** client (port **5173**), see **[`../desktop/README.md`](../desktop/README.md)**.

## Smoke test (curl)

With **TWS / IB Gateway** running and `.env` configured:

```bash
# Liveness
curl -s http://127.0.0.1:8765/health | jq .

# Config surface (no secrets)
curl -s http://127.0.0.1:8765/environment | jq .

# IB snapshot status (before refresh: snapshot_loaded may be false)
curl -s http://127.0.0.1:8765/ibkr/status | jq .

# Pull portfolio from IBKR into API memory
curl -s -X POST http://127.0.0.1:8765/portfolio/refresh | jq .

# Frames (JSON rows)
curl -s http://127.0.0.1:8765/portfolio/summary | jq .
curl -s http://127.0.0.1:8765/portfolio/stocks | jq '.rows | length'
curl -s http://127.0.0.1:8765/portfolio/options | jq '.rows | length'
curl -s http://127.0.0.1:8765/portfolio/hedge | jq .
curl -s http://127.0.0.1:8765/portfolio/crash | jq .

# Chat (after successful refresh)
curl -s http://127.0.0.1:8765/chat/capabilities | jq .
curl -s -X POST http://127.0.0.1:8765/chat/message \
  -H 'Content-Type: application/json' \
  -d '{"message":"Summarize portfolio risk."}' | jq .
```

If you see **503** on portfolio/chat routes, call **`POST /portfolio/refresh`** first.

## PyInstaller (later)

Bundling this app into a standalone binary is a separate step (see `specs/talebizer_desktop_spec.md`). Typical pattern: PyInstaller entry targeting `backend.main:app` behind a small wrapper that runs Uvicorn, then ship that binary as a Tauri sidecar.
