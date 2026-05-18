"""Pydantic contracts for desktop API (Phase 1)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class EnvironmentResponse(BaseModel):
    python_version: str
    platform: str
    backend: str = "talebizer-fastapi-phase1"
    ib_host: str
    ib_port: int
    chat_ollama_enabled: bool
    chat_ollama_host: str
    chat_ollama_model: str


class LLMStatusResponse(BaseModel):
    ollama_enabled: bool
    ollama_host: str
    reachable: bool
    installed_models: List[str] = Field(default_factory=list)
    detail: Optional[str] = None


class IBKRStatusResponse(BaseModel):
    snapshot_loaded: bool
    last_refresh_utc: Optional[str] = None
    last_refresh_error: Optional[str] = None
    ib_host: str
    ib_port: int


class PortfolioRefreshResponse(BaseModel):
    refreshed_at_utc: str
    n_stocks: int
    n_options: int


class PortfolioFrameResponse(BaseModel):
    refreshed_at_utc: str
    rows: List[Dict[str, Any]]


class PortfolioSummaryResponse(BaseModel):
    refreshed_at_utc: str
    summary: Dict[str, Any]


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=16_000)


class ChatMessageResponse(BaseModel):
    intent: Optional[str] = None
    final_response: str
    supporting_structured_payload: Optional[Dict[str, Optional[str]]] = None
    limitation_note: Optional[str] = None
    snapshot_timestamp: Optional[str] = None


class ChatCapabilitiesResponse(BaseModel):
    read_only: bool = True
    intents: List[str]
    examples: List[str]
