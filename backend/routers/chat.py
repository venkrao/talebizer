"""Chat API wrapping LangGraph."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.deps import require_snapshot
from backend.schemas import ChatCapabilitiesResponse, ChatMessageRequest, ChatMessageResponse
from backend.services.snapshot import LoadedSnapshot
from src.chat.intent import ALLOWED_INTENTS
from src.chat.router import run_chat

router = APIRouter()


_INTENT_LIST = sorted(ALLOWED_INTENTS | {"trade_refusal"})


_EXAMPLES = [
    "What are my top 5 positions?",
    "How concentrated is my equity book?",
    "How much put hedge on NVDA?",
    "What happens at -20% on the market?",
    "Summarize portfolio risk.",
]


@router.get("/capabilities", response_model=ChatCapabilitiesResponse)
def chat_capabilities() -> ChatCapabilitiesResponse:
    return ChatCapabilitiesResponse(intents=_INTENT_LIST, examples=_EXAMPLES)


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(
    body: ChatMessageRequest,
    snap: LoadedSnapshot = Depends(require_snapshot),
) -> ChatMessageResponse:
    q = body.message.strip()
    result = run_chat(q, snap.stocks_df, snap.options_df, snap.hedge_df, snap.crash_df, snap.summary)
    return ChatMessageResponse(
        intent=result.get("intent"),
        final_response=result.get("final_response") or "",
        supporting_structured_payload=result.get("tool_result"),
        limitation_note=result.get("limitation_note"),
        snapshot_timestamp=result.get("snapshot_timestamp"),
    )
