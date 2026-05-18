"""
Whitelisted read-only tools over get_portfolio_frames() outputs.

Pure functions: no IB client, no side effects beyond optional logging via callers.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

import pandas as pd


def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def get_concentration_answer(
    stocks_df: pd.DataFrame,
    summary: Dict[str, Any],
    question: str,
    top_n: int = 5,
) -> Dict[str, Optional[str]]:
    """Largest equity positions by weight_pct."""
    if stocks_df.empty or "weight_pct" not in stocks_df.columns:
        return {
            "direct_answer": "There are no stock positions with concentration weights in the current snapshot.",
            "key_numbers": f"Total equity value: {_fmt_money(float(summary.get('total_equity_value', 0)))}.",
            "limitation_note": "Concentration uses equity (STK) market value weights only.",
        }

    m = re.search(r"\b(top|first)\s+(\d+)\b", question.lower())
    if m:
        top_n = max(1, min(20, int(m.group(2))))

    df = stocks_df.sort_values("weight_pct", ascending=False).head(top_n)
    lines = [
        f"{row['symbol']}: {row['weight_pct']:.1f}% of equity (${row['market_value']:,.0f})"
        for _, row in df.iterrows()
    ]
    teq = float(summary.get("total_equity_value", stocks_df["market_value"].sum()))
    return {
        "direct_answer": f"Your **top {len(df)}** equity positions by portfolio weight:\n\n"
        + "\n".join(f"- {ln}" for ln in lines),
        "key_numbers": f"Total equity value: {_fmt_money(teq)}; "
        f"largest weight: **{df.iloc[0]['weight_pct']:.1f}%** ({df.iloc[0]['symbol']}).",
        "limitation_note": "Weights are % of total equity market value, not full portfolio including options MV.",
    }


def _extract_ticker(question: str, hedge_symbols: set[str]) -> Optional[str]:
    q = question.upper()
    for sym in sorted(hedge_symbols, key=len, reverse=True):
        if re.search(rf"\b{re.escape(sym)}\b", q):
            return sym
    # Fallback: plausible ticker tokens (avoid matching common words)
    for m in re.finditer(r"\b([A-Z]{1,5})\b", question.upper()):
        tok = m.group(1)
        if tok in hedge_symbols:
            return tok
    return None


def get_hedge_answer(
    hedge_df: pd.DataFrame,
    options_df: pd.DataFrame,
    question: str,
) -> Dict[str, Optional[str]]:
    """Put hedge coverage from hedge_df; optional filter by underlying ticker."""
    if hedge_df.empty:
        return {
            "direct_answer": "No hedge coverage table is available (no stock rows).",
            "key_numbers": "",
            "limitation_note": "Hedge ratios use listed puts vs equity market value (delta-dollar heuristic).",
        }

    symbols = set(hedge_df["symbol"].astype(str))
    ticker = _extract_ticker(question, symbols)

    if ticker:
        row = hedge_df[hedge_df["symbol"] == ticker].iloc[0]
        puts_on_underlying = (
            len(options_df[
                (options_df.get("underlying", "").astype(str) == ticker)
                & (options_df.get("put_call", "").astype(str).str.upper().str.startswith("P"))
            ])
            if not options_df.empty
            else 0
        )
        hr = float(row["hedge_ratio"])
        od = float(row["option_delta_dollars"])
        ev = float(row["equity_value"])
        stat = str(row["status"])
        return {
            "direct_answer": (
                f"**{ticker}**: hedge ratio **{hr:.1%}** ({stat}). "
                f"Option delta-notional from puts ≈ {_fmt_money(od)} vs equity MV {_fmt_money(ev)}. "
                f"Open put legs referencing this underlying: **{puts_on_underlying}**."
            ),
            "key_numbers": f"Hedge ratio {hr:.1%}; opt Δ$ {_fmt_money(od)}; equity {_fmt_money(ev)}.",
            "limitation_note": (
                "Interpretation: day-to-day delta coupling of puts vs stock MV; deep OTM tail puts can still "
                "matter more in large crashes than this ratio suggests."
            ),
        }

    unhedged = hedge_df[hedge_df["status"] == "unhedged"]
    high_risk = hedge_df[hedge_df["high_risk"] == True]  # noqa: E712
    return {
        "direct_answer": (
            f"Across **{len(hedge_df)}** stocks: **{len(unhedged)}** are classified unhedged "
            f"(hedge ratio under 10%). **{len(high_risk)}** are flagged high-risk (over 10% weight and unhedged).\n\n"
            "Ask again naming a ticker (e.g. “hedge on NVDA”) for a single-stock breakdown."
        ),
        "key_numbers": f"Unhedged: {len(unhedged)}; high-risk: {len(high_risk)}.",
        "limitation_note": "Uses puts only; calls and multi-leg structures are not modeled here.",
    }


def _parse_scenario_pct(question: str) -> Optional[float]:
    """Return negative fractional move e.g. -0.2 for -20%."""
    q = question.lower().replace("percent", "%")
    for m in re.finditer(r"(-?\d+(?:\.\d+)?)\s*%", q):
        v = float(m.group(1))
        if v > 0:
            v = -v
        return v / 100.0
    m = re.search(r"\b(minus|down)\s+(\d+(?:\.\d+)?)\s*%", q)
    if m:
        return -float(m.group(2)) / 100.0
    return None


def get_crash_answer(crash_df: pd.DataFrame, question: str) -> Dict[str, Optional[str]]:
    """Nearest configured crash scenario from crash_df."""
    if crash_df.empty:
        return {
            "direct_answer": "Crash scenario data is not available in this snapshot.",
            "key_numbers": "",
            "limitation_note": None,
        }

    target = _parse_scenario_pct(question)
    if target is None:
        row = crash_df.iloc[len(crash_df) // 2]
    else:
        closest_idx = (crash_df["scenario_pct"] - target).abs().idxmin()
        row = crash_df.loc[closest_idx]

    pct = float(row["scenario_pct"])
    return {
        "direct_answer": (
            f"At a **{pct*100:.0f}%** equity shock (nearest match to your question): "
            f"stock P/L ≈ **{_fmt_money(float(row['stock_pnl']))}**, "
            f"options P/L ≈ **{_fmt_money(float(row['options_pnl']))}**, "
            f"net ≈ **{_fmt_money(float(row['net_pnl']))}** "
            f"({float(row['net_pct']):+.2f}% of portfolio)."
        ),
        "key_numbers": (
            f"Scenario {pct*100:.0f}%: stock {_fmt_money(float(row['stock_pnl']))}, "
            f"options {_fmt_money(float(row['options_pnl']))}, net {_fmt_money(float(row['net_pnl']))}."
        ),
        "limitation_note": (
            "Delta–gamma approximation only; vega expansion on tail options is not modeled — "
            "actual option outcomes in crises can differ materially."
        ),
    }


def get_summary_answer(
    summary: Dict[str, Any],
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
) -> Dict[str, Optional[str]]:
    """High-level numbers from summary dict."""
    tpv = float(summary.get("total_portfolio_value", 0))
    teq = float(summary.get("total_equity_value", 0))
    ocost = float(summary.get("total_options_cost", 0))
    omv = float(summary.get("total_options_mkt_value", 0))
    obook = float(summary.get("options_book_pct", 0))
    theta = summary.get("daily_theta_burn")
    ndte = summary.get("n_options_expiring_90d")
    earl = summary.get("earliest_dte")

    nstk = len(stocks_df)
    nopt = len(options_df)

    theta_s = f"{theta:,.2f}" if theta is not None else "n/a"
    lines = [
        f"- Total portfolio value: **{_fmt_money(tpv)}**",
        f"- Equity value: **{_fmt_money(teq)}** ({nstk} stock rows)",
        f"- Options: cost basis **{_fmt_money(ocost)}**, mkt value **{_fmt_money(omv)}** ({nopt} option rows)",
        f"- Options book (cost / portfolio): **{obook:.2f}%**",
        f"- Options expiring within 90d: **{ndte}**; nearest expiry DTE: **{earl if earl is not None else 'n/a'}**",
        f"- Daily theta burn (if Greeks loaded): **${theta_s}**",
    ]
    return {
        "direct_answer": "Quick risk snapshot from the latest local data:\n\n" + "\n".join(lines),
        "key_numbers": f"Portfolio {_fmt_money(tpv)}; equity {_fmt_money(teq)}; options book {obook:.2f}%.",
        "limitation_note": "Figures come directly from the IBKR-backed snapshot; no forecast or recommendation.",
    }
