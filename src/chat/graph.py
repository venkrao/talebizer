"""
LangGraph workflow: parse → route → tool → format (Phase 2).

Ollama optional for intent fallback + phrasing (Phase 3).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from .formatting import format_tool_payload
from .intent import UNSUPPORTED_REPLY, TRADE_REFUSAL_REPLY, classify_intent
from .ollama_client import classify_intent_llm, get_chat_ollama_settings, phrase_response_llm
from .state import ChatState
from .tools import (
    get_concentration_answer,
    get_crash_answer,
    get_hedge_answer,
    get_summary_answer,
)


def _parse_question(state: ChatState) -> Dict[str, Any]:
    q = (state.get("user_question") or "").strip()
    return {
        "user_question": q,
        "tool_args": state.get("tool_args") or {},
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_route_intent():
    enabled, host, model, intent_fb, _phrase = get_chat_ollama_settings()

    def route_intent(state: ChatState) -> Dict[str, Any]:
        q = state["user_question"]
        intent = classify_intent(q)
        if intent == "unsupported" and enabled and intent_fb:
            llm_intent = classify_intent_llm(q, host, model)
            if llm_intent:
                intent = llm_intent
        return {"intent": intent}

    return route_intent


def _make_run_tool(
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
    hedge_df: pd.DataFrame,
    crash_df: pd.DataFrame,
    summary: Dict[str, Any],
):
    def run_portfolio_tool(state: ChatState) -> Dict[str, Any]:
        intent = state.get("intent")
        q = state["user_question"]

        if intent in ("trade_refusal", "unsupported"):
            return {"tool_result": None}

        if intent == "concentration":
            payload = get_concentration_answer(stocks_df, summary, q)
        elif intent == "hedge_coverage":
            payload = get_hedge_answer(hedge_df, options_df, q)
        elif intent == "crash_scenario":
            payload = get_crash_answer(crash_df, q)
        elif intent == "portfolio_summary":
            payload = get_summary_answer(summary, stocks_df, options_df)
        else:
            return {"tool_result": None}

        return {"tool_result": payload}

    return run_portfolio_tool


def _make_format_response():
    enabled, host, model, _intent_fb, phrase = get_chat_ollama_settings()

    def format_response(state: ChatState) -> Dict[str, Any]:
        intent = state.get("intent")

        if intent == "trade_refusal":
            return {"final_response": TRADE_REFUSAL_REPLY}

        if intent == "unsupported":
            return {"final_response": UNSUPPORTED_REPLY}

        payload = state.get("tool_result")
        if not payload:
            return {"final_response": UNSUPPORTED_REPLY}

        body = format_tool_payload(payload)
        if enabled and phrase:
            polished = phrase_response_llm(body, host, model)
            if polished and len(polished) > 20:
                body = polished
        return {"final_response": body}

    return format_response


def build_chat_graph(
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
    hedge_df: pd.DataFrame,
    crash_df: pd.DataFrame,
    summary: Dict[str, Any],
):
    """Compile a linear graph (no loops)."""
    g = StateGraph(ChatState)
    g.add_node("parse_question", _parse_question)
    g.add_node("route_intent", _make_route_intent())
    g.add_node("run_portfolio_tool", _make_run_tool(stocks_df, options_df, hedge_df, crash_df, summary))
    g.add_node("format_response", _make_format_response())

    g.add_edge(START, "parse_question")
    g.add_edge("parse_question", "route_intent")
    g.add_edge("route_intent", "run_portfolio_tool")
    g.add_edge("run_portfolio_tool", "format_response")
    g.add_edge("format_response", END)

    return g.compile()


def invoke_chat_graph(
    question: str,
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
    hedge_df: pd.DataFrame,
    crash_df: pd.DataFrame,
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    graph = build_chat_graph(stocks_df, options_df, hedge_df, crash_df, summary)
    out = graph.invoke({"user_question": question})
    tr = out.get("tool_result") or {}
    lim = tr.get("limitation_note") if isinstance(tr, dict) else None
    return {
        "intent": out.get("intent"),
        "tool_result": out.get("tool_result"),
        "final_response": out.get("final_response"),
        "snapshot_timestamp": out.get("snapshot_timestamp"),
        "limitation_note": lim,
    }
