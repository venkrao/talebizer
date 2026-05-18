"""Talebizer FastAPI entrypoint — bind loopback only."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from backend.routers import chat, health, portfolio  # noqa: E402

app = FastAPI(
    title="Talebizer API",
    description="Local read-only portfolio service (desktop Phase 1).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
