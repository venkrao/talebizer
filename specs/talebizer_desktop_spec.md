# Talebizer Desktop App Specification

## Overview

Talebizer Desktop is an installable local application for macOS and Windows that packages a native desktop shell, a bundled Python backend, and a local model runtime into a single user-installable product.[cite:133][cite:139][cite:145] The application replaces the long-term Streamlit UI path with a desktop architecture designed for `.app`, `.dmg`, and `.exe` style distribution while preserving Talebizer’s local-only, read-only connection to IBKR through TWS or IB Gateway.[cite:1][cite:133]

The desktop architecture is intended to let users install Talebizer like a normal desktop product rather than launching a local web server manually in a browser.[cite:127][cite:133]

## Goals

The desktop product must:

- install cleanly on macOS and Windows as a native desktop application.[cite:133]
- run all portfolio processing locally with no hosted inference APIs.[cite:1][cite:144]
- preserve the current Python analytics core, including IBKR connectivity, `SafeIB`, metrics, crash scenarios, and convexity logic.[cite:1]
- support an evolvable chat interface over portfolio state using a dedicated frontend and a Python service boundary.[cite:17][cite:133]
- create a migration path away from Streamlit without rewriting the core analytics engine.[cite:124][cite:127]

## Non-Goals

The initial desktop architecture does not require:

- a cloud backend or hosted database.[cite:144]
- broker-side order placement or any execution capability.[cite:1]
- a browser-based public web application.[cite:127]
- a Rust rewrite of the existing Python analytics code.[cite:1]
- Linux packaging in the first release.[cite:133]

## Technology Choices

### Desktop shell

The desktop shell should use **Tauri v2** as the long-term application container. Tauri supports bundling and running external binaries as sidecars, which is the key mechanism needed to package a Python backend into a desktop app.[cite:133][cite:136]

Tauri is preferred over a browser-first Streamlit distribution path because Streamlit is fundamentally a web server plus browser interface rather than a native desktop packaging model.[cite:124][cite:127]

### Frontend

The desktop UI should be built as a **React + TypeScript** single-page frontend running inside Tauri’s WebView.[cite:133] The frontend will eventually replace Streamlit entirely for shipped desktop builds.[cite:124][cite:127]

Recommended frontend stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- a small component system such as shadcn/ui or equivalent
- TanStack Query for backend request/state management
- Plotly or ECharts for portfolio charts[cite:133]

The frontend should be designed as a local client to the Python API, not as a container for business logic.[cite:1][cite:133]

### Backend service

The backend should be a **FastAPI** service packaged as a local Python executable. FastAPI is suitable as a local application service boundary and can be run manually via Uvicorn during development.[cite:144][cite:147]

The backend service will own:

- IBKR connectivity and read-only enforcement
- portfolio snapshot refresh
- chat orchestration and LangGraph workflow
- Ollama integration
- serialization of analytics results to frontend-safe JSON[cite:1][cite:17]

### Python packaging

The Python backend should be bundled into a platform-specific executable using **PyInstaller** for the first packaging path. PyInstaller can bundle Python apps into standalone executables on macOS and Windows.[cite:139][cite:145]

This backend executable will be packaged by Tauri as an external sidecar binary.[cite:133][cite:136]

### LLM runtime

The product should continue using **Ollama** as the local model runtime in the near term. For the first desktop releases, Talebizer should assume Ollama is installed locally or provide a setup check and install guidance.[cite:56]

A later release may bundle or manage model runtime more tightly, but the initial architecture should not depend on that complexity.[cite:56]

## Target Architecture

The desktop architecture should be:

```text
[Tauri Desktop Shell]
        │
        ▼
[React + TypeScript Frontend]
        │  HTTP on localhost / loopback only
        ▼
[FastAPI Python Sidecar]
  ├── Talebizer analytics core
  ├── LangGraph chat workflow
  ├── SafeIB / ib_async integration
  └── Ollama client
        │
        ▼
[TWS / IB Gateway via local socket API]
```

Tauri supports packaging sidecar binaries and spawning them with explicit permissions, which makes this architecture appropriate for a bundled Python backend.[cite:133][cite:136]

## Architecture Principles

### Principle 1: Preserve the Python core

The existing analytics modules should remain the source of truth for portfolio logic. The desktop migration should add a service boundary and a new frontend, not rewrite portfolio analytics into JavaScript or Rust.[cite:1]

### Principle 2: Separate UI from domain logic

The frontend should render state and send user actions, but all brokerage access, analytics, and chat reasoning should remain in Python.[cite:1]

### Principle 3: Bundle the backend as a sidecar

The Python service should be treated as an embedded application component, not as a separately installed developer dependency. Tauri’s sidecar support is the mechanism for this.[cite:133][cite:136]

### Principle 4: Local loopback only

All frontend-backend communication must happen over localhost / loopback only. The Python API is an internal application API, not a network-exposed service.[cite:144]

## Module Boundaries

### Frontend responsibilities

The desktop frontend must handle:

- window layout and navigation
- local portfolio dashboard rendering
- chat UI rendering
- loading states, error states, and onboarding
- calling backend endpoints
- local display preferences and UI-only state

The frontend must not contain IBKR logic, option analytics, or intent routing rules.[cite:1]

### Backend responsibilities

The backend must handle:

- lifecycle of the IBKR connection
- snapshot refresh and caching
- all portfolio and option analytics
- LangGraph chat orchestration
- deterministic intent routing
- Ollama model calls
- output contracts returned to the frontend[cite:1][cite:17]

## API Specification

The FastAPI boundary should be added now, even if the first shipped UI remains limited. Suggested endpoints:

### Health and environment

- `GET /health`
- `GET /environment`
- `GET /llm/status`
- `GET /ibkr/status`[cite:144]

### Portfolio

- `POST /portfolio/refresh`
- `GET /portfolio/summary`
- `GET /portfolio/stocks`
- `GET /portfolio/options`
- `GET /portfolio/hedge`
- `GET /portfolio/crash`

These should all derive from the existing `get_portfolio_frames()` orchestration path.[cite:1]

### Chat

- `POST /chat/message`
- `GET /chat/capabilities`

The chat endpoint should call the existing LangGraph workflow and return:

- intent
- final_response
- supporting structured payload
- limitation note
- snapshot timestamp[cite:85][cite:86][cite:87][cite:88]

## Packaging Strategy

### Development mode

During development:

- run the Python backend with Uvicorn locally.[cite:147]
- run the React frontend with Vite.
- run Tauri in development mode pointing at the frontend dev server.[cite:133]

### Production packaging

For production:

1. Build the Python backend into a platform-specific executable with PyInstaller.[cite:139][cite:145]
2. Place the executable in the Tauri sidecar binaries path for the target platform.[cite:133][cite:136]
3. Configure Tauri `externalBin` to bundle the backend sidecar.[cite:136]
4. Configure Tauri permissions/capabilities to allow spawning the sidecar binary.[cite:133]
5. Build platform-specific desktop installers via Tauri for macOS and Windows.[cite:133]

## Repository Structure

Recommended structure:

```text
talebizer/
  backend/
    app/
      api/
      chat/
      core/
      services/
      schemas/
    main.py
    pyproject.toml
  desktop/
    src/
    src-tauri/
    package.json
  shared/
    api-contracts/
  docs/
```

### Backend folder guidance

- `api/` — FastAPI routers
- `chat/` — LangGraph state, graph, routing, formatting
- `core/` — config, logging, lifecycle
- `services/` — portfolio refresh, IBKR, Ollama, analytics orchestration
- `schemas/` — Pydantic request/response models[cite:144][cite:85][cite:86]

## Migration Plan

### Phase 1: Service boundary now

Start immediately by inserting a FastAPI layer in front of the current Python code. The legacy Streamlit browser UI has been removed; the **React desktop client** plus API is the supported surface.[cite:124][cite:127][cite:144]

Deliverables:

- FastAPI app with health and portfolio endpoints
- chat endpoint wrapping the existing LangGraph flow
- JSON schemas for all frontend-facing payloads
- no direct UI-to-module imports outside the API layer[cite:144][cite:85]

### Phase 2: Desktop frontend

Build a React + TypeScript frontend that consumes the FastAPI endpoints and reproduces the core Talebizer views plus chat.[cite:133]

Deliverables:

- dashboard shell
- positions and hedge views
- crash and concentration charts
- chat interface
- connection and setup screens

### Phase 3: Tauri packaging

Wrap the frontend in Tauri and package the Python backend as a sidecar binary.[cite:133][cite:136]

Deliverables:

- local sidecar startup on app launch
- healthcheck and retry loop
- signed macOS app bundle
- Windows installer

## Security Model

Talebizer Desktop must maintain the current read-only guarantee. The desktop packaging work must not create any execution path for order placement.[cite:1]

Security requirements:

- keep `SafeIB` as the only broker client surface.[cite:1]
- no order endpoints in the API.[cite:1]
- no generic code-execution or shell-execution routes.[cite:1]
- sidecar only bound to loopback interface.[cite:144]
- frontend cannot call arbitrary OS commands through Tauri shell features.[cite:133]
- model prompts and portfolio data remain local to the machine.[cite:56]

## Development Recommendations

To avoid future rewrites, make these choices now:

- The legacy Streamlit UI is removed — extend the **desktop SPA + FastAPI** only.[cite:124][cite:127]
- Put all new business logic behind Python service functions and FastAPI endpoints.[cite:144]
- Define explicit Pydantic schemas for every response returned to the UI.[cite:144]
- Keep LangGraph and intent logic fully backend-resident.[cite:85][cite:88]
- Keep frontend state presentation-only wherever possible.[cite:1]

## Acceptance Criteria

This architecture is correctly in place when:

- the Python backend can be started independently as a FastAPI app.[cite:147]
- the backend exposes stable JSON endpoints for portfolio data and chat.[cite:144][cite:85]
- the frontend depends only on those endpoints, not direct Python imports.[cite:133]
- the backend can be packaged as a standalone executable with PyInstaller.[cite:139][cite:145]
- Tauri can spawn the backend as a bundled sidecar.[cite:133][cite:136]
- the application remains local-only and read-only with respect to IBKR.[cite:1]

## Recommended Immediate Next Step

The next implementation step should be **Phase 1 only**: add FastAPI in front of the current backend now. That is the single most leverage-rich move because it preserves the existing Python core, unlocks Tauri later, and stops further investment in a frontend stack that is not suitable for the final installable desktop product.[cite:124][cite:127][cite:133][cite:144]
