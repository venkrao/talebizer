"""Format tool dicts into markdown for chat."""
from __future__ import annotations

from typing import Dict, Optional


def format_tool_payload(payload: Dict[str, Optional[str]]) -> str:
    parts = [payload.get("direct_answer") or ""]
    kn = payload.get("key_numbers")
    if kn:
        parts.append(f"\n\n**Key numbers:** {kn}")
    lim = payload.get("limitation_note")
    if lim:
        parts.append(f"\n\n*Limitation:* {lim}")
    return "".join(parts).strip()
