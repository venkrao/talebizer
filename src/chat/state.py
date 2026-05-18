"""Typed LangGraph state for the chat workflow."""
from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict


class ChatState(TypedDict, total=False):
    user_question: str
    intent: Optional[str]
    tool_args: Dict[str, Any]
    snapshot_timestamp: str
    tool_result: Optional[Dict[str, Optional[str]]]
    final_response: Optional[str]
    error: Optional[str]
