# Talebizer Desktop (Phase 2 dev shell)

Minimal **React + TypeScript + Vite** UI that talks **only** to the FastAPI backend (`backend/`). No Python imports in the frontend.

## Prerequisites

1. **Backend** running on loopback (default `http://127.0.0.1:8765`):

   ```bash
   # From repository root
   PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
   ```

2. **Node.js** 18+ and npm.

## Setup

```bash
cd desktop
cp .env.example .env   # optional; defaults match backend README
npm install
```

`VITE_API_BASE_URL` must stay on **127.0.0.1** / **localhost** so it matches the backend CORS allowlist.

## Run (development)

```bash
npm run dev
```

Open **http://127.0.0.1:5173** (Vite default).

- **Portfolio** — overview metrics, **Refresh portfolio (IBKR)**, chat over the snapshot.
- **System** — API base, Python/environment, IBKR snapshot/load diagnostics, Ollama (`Reload diagnostics`).
- **Theme toggle** (header) — switches dark/light; preference is stored in `localStorage` under `talebizer-theme` (`dark` or `light`). An older `system` value is migrated once to match your OS appearance.
## Production build

```bash
npm run build
npm run preview   # serves ./dist locally
```

Full desktop packaging (Tauri + Python sidecar) is described in `specs/talebizer_desktop_spec.md` Phase 3.
