"""
Chat entrypoint — LangGraph orchestration + deterministic/Ollama routing.
"""
from __future__ import annotations

from typing import Any, Tuple

import pandas as pd

from .graph import invoke_chat_graph


def run_chat(
    question: str,
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
    hedge_df: pd.DataFrame,
    crash_df: pd.DataFrame,
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Run the local chat workflow over the current snapshot."""
    return invoke_chat_graph(question, stocks_df, options_df, hedge_df, crash_df, summary)


def snapshot_ready(session_state: Any) -> Tuple[bool, str]:
    """True if chat may use portfolio frames."""
    required = ("stocks_df", "options_df", "hedge_df", "crash_df", "summary")
    for k in required:
        if k not in session_state:
            return False, "Load a snapshot first — click **Refresh positions** above."
    return True, ""
