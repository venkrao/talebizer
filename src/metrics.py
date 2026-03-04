from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict

import pandas as pd


# ── Options helpers ────────────────────────────────────────────────────────────

def _parse_expiry(expiry_raw) -> date | None:
    """Parse IBKR expiry strings like '20271217' or '20271217 15:00:00'."""
    if not expiry_raw:
        return None
    try:
        s = str(expiry_raw).strip()[:8]   # keep YYYYMMDD part only
        return datetime.strptime(s, "%Y%m%d").date()
    except (ValueError, TypeError):
        return None


def add_dte(options_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'dte' (days-to-expiry) column and an 'expiry_flag' column.

    expiry_flag:
        "urgent" → DTE < 90   (amber in UI — review soon)
        "ok"     → DTE >= 90
        "expired"→ DTE <= 0
    """
    df = options_df.copy()
    today = date.today()

    def _dte(raw) -> int | None:
        exp = _parse_expiry(raw)
        if exp is None:
            return None
        return (exp - today).days

    def _flag(dte_val) -> str:
        if dte_val is None:
            return "unknown"
        if dte_val <= 0:
            return "expired"
        if dte_val < 90:
            return "urgent"
        return "ok"

    df["dte"] = df["expiry"].apply(_dte)
    df["expiry_flag"] = df["dte"].apply(_flag)
    return df


# ── Portfolio summary ──────────────────────────────────────────────────────────

def build_portfolio_summary(
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Compute top-level portfolio summary metrics for the overview strip.

    Returns a dict with:
        total_equity_value      — sum of stock market values
        total_options_cost      — sum of options cost_basis
        total_options_mkt_value — sum of options market_value
        total_portfolio_value   — equity + options market value
        options_book_pct        — options cost_basis / total_portfolio_value * 100
        options_book_flag       — "ok" / "warning" (>7% threshold from spec §7.6)
        options_unrealized_pnl  — sum of options unrealized_pnl
        n_options_expiring_90d  — count of options with DTE < 90
        earliest_dte            — smallest DTE across all options (None if no options)
    """
    equity_val = float(stocks_df["market_value"].sum()) if not stocks_df.empty else 0.0

    if not options_df.empty:
        opt_cost  = float(options_df["cost_basis"].sum())
        opt_mkt   = float(options_df["market_value"].sum())
        opt_upnl  = float(options_df["unrealized_pnl"].sum()) if "unrealized_pnl" in options_df.columns else 0.0

        if "dte" in options_df.columns:
            valid_dte = options_df["dte"].dropna()
            n_urgent   = int((valid_dte < 90).sum())
            earliest   = int(valid_dte.min()) if len(valid_dte) else None
        else:
            n_urgent = 0
            earliest = None
    else:
        opt_cost = opt_mkt = opt_upnl = 0.0
        n_urgent = 0
        earliest = None

    total = equity_val + opt_mkt
    options_book_pct = (opt_cost / total * 100) if total > 0 else 0.0

    return {
        "total_equity_value":      equity_val,
        "total_options_cost":      opt_cost,
        "total_options_mkt_value": opt_mkt,
        "total_portfolio_value":   total,
        "options_book_pct":        round(options_book_pct, 2),
        "options_book_flag":       "warning" if options_book_pct > 7 else "ok",
        "options_unrealized_pnl":  opt_upnl,
        "n_options_expiring_90d":  n_urgent,
        "earliest_dte":            earliest,
    }


# ── Concentration ──────────────────────────────────────────────────────────────

def add_concentration_metrics(stocks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds weight_pct and concentration_flag to stocks_df.

    weight_pct = stock market_value / total equity market_value
    concentration_flag:
        "red"   → weight_pct > 25%
        "amber" → 10% < weight_pct <= 25%
        "green" → weight_pct <= 10%
    """
    df = stocks_df.copy()

    total = df["market_value"].sum()
    if total == 0:
        df["weight_pct"] = 0.0
        df["concentration_flag"] = "green"
        return df

    df["weight_pct"] = (df["market_value"] / total * 100).round(2)

    def _flag(w: float) -> str:
        if w > 25:
            return "red"
        if w > 10:
            return "amber"
        return "green"

    df["concentration_flag"] = df["weight_pct"].apply(_flag)
    return df
