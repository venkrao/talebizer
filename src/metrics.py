from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

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
        daily_theta_burn        — sum(theta * multiplier * qty) across all options (None if no Greeks)
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

        # Theta burn: sum(theta * multiplier * quantity) — negative means daily cost
        if "theta" in options_df.columns:
            t = options_df.copy()
            t["multiplier_num"] = pd.to_numeric(t.get("multiplier", 100), errors="coerce").fillna(100)
            t["theta_num"]      = pd.to_numeric(t["theta"], errors="coerce")
            t["qty_num"]        = pd.to_numeric(t["quantity"], errors="coerce").fillna(0)
            t["theta_contrib"]  = t["theta_num"] * t["multiplier_num"] * t["qty_num"]
            theta_burn: Optional[float] = float(t["theta_contrib"].sum()) if t["theta_num"].notna().any() else None
        else:
            theta_burn = None
    else:
        opt_cost = opt_mkt = opt_upnl = 0.0
        n_urgent = 0
        earliest = None
        theta_burn = None

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
        "daily_theta_burn":        round(theta_burn, 2) if theta_burn is not None else None,
    }


# ── Hedge Coverage ─────────────────────────────────────────────────────────────

def add_hedge_coverage(
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute hedge coverage ratio for every stock position (§7.2).

    For each stock, find all PUT options where underlying == stock.symbol and sum:
        option_delta_dollars = sum(abs(delta) * multiplier * qty * undPrice)

        hedge_ratio = option_delta_dollars / stock.market_value

    Classification:
        < 0.10          → "unhedged"
        0.10 – 0.25     → "light"
        0.25 – 0.50     → "partial"
        > 0.50          → "hedged"

    HIGH RISK flag: weight_pct > 10% AND hedge_ratio < 0.10

    Returns a DataFrame with one row per stock:
        symbol | equity_value | weight_pct | hedge_ratio |
        option_delta_dollars | n_puts | status | high_risk
    """
    if stocks_df.empty:
        return pd.DataFrame()

    # Build a lookup: stock symbol → current_price (fallback when undPrice is missing)
    price_lookup = {}
    if "current_price" in stocks_df.columns:
        price_lookup = dict(
            zip(stocks_df["symbol"], pd.to_numeric(stocks_df["current_price"], errors="coerce"))
        )

    # Pre-filter to puts only, coerce numeric columns once
    puts_df = pd.DataFrame()
    if not options_df.empty and "put_call" in options_df.columns:
        puts_df = options_df[
            options_df["put_call"].str.strip().str.upper().str.startswith("P")
        ].copy()
        puts_df["delta_num"]      = pd.to_numeric(puts_df.get("delta"), errors="coerce")
        puts_df["multiplier_num"] = pd.to_numeric(puts_df.get("multiplier", 100), errors="coerce").fillna(100)
        puts_df["qty_num"]        = pd.to_numeric(puts_df.get("quantity"), errors="coerce").fillna(0)
        puts_df["und_price_num"]  = pd.to_numeric(puts_df.get("und_price"), errors="coerce")

    rows = []
    for _, stock in stocks_df.iterrows():
        sym          = stock["symbol"]
        mkt_val      = float(stock.get("market_value") or 0)
        weight_pct   = float(stock.get("weight_pct") or 0)

        opt_delta_dollars = 0.0
        n_puts = 0

        if not puts_df.empty and "underlying" in puts_df.columns:
            matching = puts_df[puts_df["underlying"] == sym]
            n_puts = len(matching)

            for _, opt in matching.iterrows():
                delta   = opt["delta_num"]
                mult    = opt["multiplier_num"]
                qty     = opt["qty_num"]
                und_p   = opt["und_price_num"]

                if pd.isna(delta):
                    continue
                # und_price from modelGreeks is preferred; fall back to stock's current price
                if pd.isna(und_p) or und_p <= 0:
                    und_p = price_lookup.get(sym, 0.0) or 0.0

                opt_delta_dollars += abs(delta) * mult * qty * und_p

        hedge_ratio = (opt_delta_dollars / mkt_val) if mkt_val > 0 else 0.0

        if hedge_ratio >= 0.50:
            status = "hedged"
        elif hedge_ratio >= 0.25:
            status = "partial"
        elif hedge_ratio >= 0.10:
            status = "light"
        else:
            status = "unhedged"

        high_risk = (weight_pct > 10) and (hedge_ratio < 0.10)

        rows.append({
            "symbol":               sym,
            "equity_value":         mkt_val,
            "weight_pct":           round(weight_pct, 2),
            "n_puts":               n_puts,
            "option_delta_dollars": round(opt_delta_dollars, 0),
            "hedge_ratio":          round(hedge_ratio, 4),
            "status":               status,
            "high_risk":            high_risk,
        })

    hedge_df = pd.DataFrame(rows)

    # Sort: high-risk first, then unhedged, then by weight descending
    status_order = {"unhedged": 0, "light": 1, "partial": 2, "hedged": 3}
    hedge_df["_sort_status"] = hedge_df["status"].map(status_order)
    hedge_df = hedge_df.sort_values(
        ["high_risk", "_sort_status", "weight_pct"],
        ascending=[False, True, False],
    ).drop(columns=["_sort_status"]).reset_index(drop=True)

    return hedge_df


# ── Crash Scenario P&L ────────────────────────────────────────────────────────

def build_crash_scenarios(
    stocks_df: pd.DataFrame,
    options_df: pd.DataFrame,
    scenarios: list,
    total_portfolio_value: float,
) -> pd.DataFrame:
    """
    §7.4 — Crash Scenario P&L using delta + gamma approximation.

    For each scenario (a fractional equity move, e.g. -0.30 for -30%):

    Stocks (delta = 1):
        stock_pnl = sum(market_value) * scenario_pct

    Options (Taylor expansion — first two terms):
        For each option:
            dS = undPrice * scenario_pct
            pnl = (delta * dS  +  0.5 * gamma * dS²)  *  multiplier * qty

    undPrice preference: IB modelGreeks undPrice → stocks_df current_price fallback.

    Returns a DataFrame (one row per scenario) with columns:
        scenario_pct  — float, e.g. -0.30
        stock_pnl     — total equity P&L ($)
        options_pnl   — total options P&L ($) from delta+gamma
        net_pnl       — stock_pnl + options_pnl
        net_pct       — net_pnl / total_portfolio_value * 100
    """
    # Underlying price lookup: symbol → current stock price from portfolio
    price_lookup: dict = {}
    if not stocks_df.empty and "current_price" in stocks_df.columns:
        price_lookup = dict(
            zip(
                stocks_df["symbol"],
                pd.to_numeric(stocks_df["current_price"], errors="coerce"),
            )
        )

    total_equity = float(stocks_df["market_value"].sum()) if not stocks_df.empty else 0.0

    # Pre-extract option parameters once, skip rows missing critical values
    opt_params = []
    if not options_df.empty:
        for _, opt in options_df.iterrows():
            delta = pd.to_numeric(opt.get("delta"), errors="coerce")
            gamma = pd.to_numeric(opt.get("gamma"), errors="coerce")
            mult  = pd.to_numeric(opt.get("multiplier", 100), errors="coerce")
            qty   = pd.to_numeric(opt.get("quantity", 0), errors="coerce")
            und_p = pd.to_numeric(opt.get("und_price"), errors="coerce")

            if pd.isna(delta):
                continue  # no Greeks at all — skip

            mult  = mult  if not pd.isna(mult)  else 100.0
            qty   = qty   if not pd.isna(qty)   else 0.0
            gamma = gamma if not pd.isna(gamma) else 0.0

            # Resolve underlying price
            if pd.isna(und_p) or und_p <= 0:
                underlying = opt.get("underlying") or opt.get("symbol")
                und_p = float(price_lookup.get(underlying) or 0.0)

            if und_p <= 0:
                continue  # can't compute dS without a price

            opt_params.append((float(delta), float(gamma), float(mult), float(qty), float(und_p)))

    rows = []
    for pct in sorted(scenarios):
        stock_pnl = total_equity * pct

        options_pnl = 0.0
        for delta, gamma, mult, qty, und_p in opt_params:
            dS           = und_p * pct
            option_pnl   = (delta * dS + 0.5 * gamma * dS ** 2) * mult * qty
            options_pnl += option_pnl

        net_pnl = stock_pnl + options_pnl
        net_pct = (net_pnl / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0

        rows.append({
            "scenario_pct": pct,
            "stock_pnl":    round(stock_pnl,    0),
            "options_pnl":  round(options_pnl,  0),
            "net_pnl":      round(net_pnl,       0),
            "net_pct":      round(net_pct,        2),
        })

    return pd.DataFrame(rows)


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
