"""Health, environment, IBKR and LLM status endpoints."""
from __future__ import annotations

import platform
import sys
import urllib.request

from fastapi import APIRouter, Depends

from backend.schemas import EnvironmentResponse, HealthResponse, IBKRStatusResponse, LLMStatusResponse
from backend.services.snapshot import SnapshotStore, get_snapshot_store
from src.chat.ollama_client import get_chat_ollama_settings, list_installed_models
from src.config import get_ib_config

router = APIRouter(tags=["health"])


def _ollama_tags_reachable(host: str, timeout_sec: float = 3.0) -> bool:
    url = f"{host.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status == 200
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/environment", response_model=EnvironmentResponse)
def environment() -> EnvironmentResponse:
    enabled, ollama_host, model, _, _ = get_chat_ollama_settings()
    cfg = get_ib_config()
    return EnvironmentResponse(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        ib_host=str(cfg.host),
        ib_port=int(cfg.port),
        chat_ollama_enabled=enabled,
        chat_ollama_host=ollama_host,
        chat_ollama_model=model,
    )


@router.get("/llm/status", response_model=LLMStatusResponse)
def llm_status() -> LLMStatusResponse:
    enabled, host, _, _, _ = get_chat_ollama_settings()
    if not enabled:
        return LLMStatusResponse(
            ollama_enabled=False,
            ollama_host=host,
            reachable=False,
            installed_models=[],
            detail="CHAT_OLLAMA_ENABLED is false",
        )
    reachable = _ollama_tags_reachable(host)
    models = list_installed_models(host) if reachable else []
    detail = None if reachable else "Cannot reach Ollama GET /api/tags (is Ollama running?)"
    return LLMStatusResponse(
        ollama_enabled=True,
        ollama_host=host,
        reachable=reachable,
        installed_models=models,
        detail=detail,
    )


@router.get("/ibkr/status", response_model=IBKRStatusResponse)
def ibkr_status(store: SnapshotStore = Depends(get_snapshot_store)) -> IBKRStatusResponse:
    cfg = get_ib_config()
    snap = store.get_optional()
    return IBKRStatusResponse(
        snapshot_loaded=snap is not None,
        last_refresh_utc=snap.refreshed_at_utc.isoformat() if snap else None,
        last_refresh_error=store.last_error(),
        ib_host=str(cfg.host),
        ib_port=int(cfg.port),
    )
