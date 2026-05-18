"""Deterministic intent classification (keyword-first)."""
from __future__ import annotations

import re

_TRADING_HINTS = re.compile(
    r"\b(buy|sell|short|cover|place order|cancel order|market order|limit order|"
    r"execute|trade|trading|bracket|oca)\b",
    re.I,
)

UNSUPPORTED_REPLY = (
    "I can only answer **read-only** questions about your **current snapshot**: "
    "**concentration** (largest equity weights), **hedge coverage** (puts vs equity), "
    "**crash scenarios** (configured Δ–Γ shocks), or a **portfolio summary**. "
    "I cannot trade, rebalance, or access historical dates.\n\n"
    "Try:\n"
    "- “What are my top 5 positions?”\n"
    "- “How much put hedge on NVDA?”\n"
    "- “What happens at -20%?”\n"
    "- “Summarize portfolio risk.”"
)

TRADE_REFUSAL_REPLY = (
    "This assistant is **read-only** and cannot place, modify, or cancel orders — "
    "use Trader Workstation or another approved workflow for trading."
)


def classify_intent(question: str) -> str:
    """Keyword-first routing. Returns intent slug."""
    q = question.strip().lower()
    if not q:
        return "unsupported"

    if _TRADING_HINTS.search(q):
        return "trade_refusal"

    if re.search(r"-?\d+\s*%", q) or re.search(
        r"\b(crash|scenario|shock|drawdown|what happens if|what happens at)\b", q
    ):
        return "crash_scenario"

    if re.search(
        r"\b(hedge|hedging|put hedge|puts|downside protection|unhedged|covered)\b", q
    ):
        return "hedge_coverage"

    if re.search(
        r"\b(concentrat|largest|biggest|top\s+\d+|weight|how much\s+\w+\s+do i hold)\b", q
    ):
        return "concentration"

    if re.search(
        r"\b(summary|summarize|overview|snapshot|quick\s+risk|risk summary)\b", q
    ):
        return "portfolio_summary"

    return "unsupported"


ALLOWED_INTENTS = frozenset({
    "concentration",
    "hedge_coverage",
    "crash_scenario",
    "portfolio_summary",
    "unsupported",
})
