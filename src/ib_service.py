from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from ib_async import Stock

from .config import get_ib_config
from .connection import connect_ib
from .convexity import compute_convexity_metrics
from .data_pull import get_positions_frames as _get_positions_frames
from .greeks import fetch_greeks
from .metrics import (
    add_concentration_metrics,
    add_dte,
    add_hedge_coverage,
    build_crash_scenarios,
    build_portfolio_summary,
)
from .safe_ib import SafeIB

logger = logging.getLogger(__name__)

_ib_client: Optional[SafeIB] = None

# Realized vol changes slowly — cache for 1 hour to avoid re-fetching on every refresh
_realized_vol_cache: dict = {}
_realized_vol_fetched_at: float = 0.0
_REALIZED_VOL_TTL_SECONDS: float = 3600.0


def _get_ib() -> SafeIB:
    """
    Internal accessor for the shared SafeIB instance.

    This function is the only place that touches the underlying IB client.
    Callers should use the higher-level functions below instead.
    """
    global _ib_client

    if _ib_client is None or not _ib_client.isConnected():
        _ib_client = connect_ib()

    return _ib_client


def _fetch_realized_vols(
    ib: SafeIB,
    options_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    lookback_days: int = 30,
) -> dict:
    """
    Fetch daily OHLC history for each unique option underlying and return a
    dict of {symbol: annualised_realized_vol}.

    Uses `lookback_days` trading days of daily closes.  Failures are non-fatal:
    symbols that cannot be fetched are simply absent from the returned dict and
    the convexity module falls back to `vol_edge = None`.
    """
    if options_df.empty:
        return {}

    # Build a map of symbol → already-qualified Stock contract from the live portfolio.
    # This avoids a qualifyContracts round-trip for every underlying we hold as a stock.
    portfolio_contracts: dict = {}
    for item in ib.portfolio():
        c = item.contract
        if c.secType == "STK" and c.conId:
            portfolio_contracts[c.symbol] = c

    # Currency lookup for underlyings NOT in the portfolio
    currency_map: dict = {}
    if not stocks_df.empty and "currency" in stocks_df.columns:
        currency_map = dict(zip(stocks_df["symbol"], stocks_df["currency"]))

    underlyings = options_df["underlying"].dropna().unique()
    realized_vols: dict = {}

    for sym in underlyings:
        try:
            if sym in portfolio_contracts:
                pc = portfolio_contracts[sym]
                # Portfolio contracts have conId set but exchange is often empty,
                # which IB rejects for reqHistoricalData (Warning 321).
                # Build a fresh contract using conId + explicit exchange so IB
                # can route it without a qualifyContracts round-trip.
                contract = Stock(
                    conId=pc.conId,
                    exchange=pc.primaryExchange or "SMART",
                    currency=pc.currency or "USD",
                )
            else:
                currency = currency_map.get(sym, "USD")
                raw = Stock(symbol=sym, exchange="SMART", currency=currency)
                qualified = ib.qualifyContracts(raw)
                # Guard against empty list OR a list containing None (e.g. BABA2)
                if not qualified or qualified[0] is None:
                    logger.warning("Could not qualify stock contract for %s — skipping realized vol", sym)
                    continue
                contract = qualified[0]

            # Request 3× the lookback to guarantee enough trading days after weekends/holidays
            bars = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=f"{lookback_days * 3} D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
                keepUpToDate=False,
            )
            if not bars or len(bars) < 5:
                logger.warning("Insufficient history for %s (%d bars)", sym, len(bars) if bars else 0)
                continue

            closes = [b.close for b in bars if b.close > 0][-lookback_days:]
            if len(closes) < 5:
                continue

            log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
            n    = len(log_returns)
            mean = sum(log_returns) / n
            var  = sum((r - mean) ** 2 for r in log_returns) / max(n - 1, 1)
            annual_vol = math.sqrt(var) * math.sqrt(252)

            realized_vols[sym] = round(annual_vol, 4)
            logger.info("Realized vol %s: %.1f%% (%d days)", sym, annual_vol * 100, n)

        except Exception as exc:
            logger.warning("Failed realized vol for %s: %s", sym, exc)

    return realized_vols


def _get_realized_vols(
    ib: SafeIB,
    options_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
) -> dict:
    """
    Return realized vol map, fetching from IB only when the cache has expired.

    The cache has a 1-hour TTL so that repeated Refresh clicks don't re-run
    15+ sequential reqHistoricalData calls each time.
    """
    global _realized_vol_cache, _realized_vol_fetched_at

    age = time.monotonic() - _realized_vol_fetched_at
    if age < _REALIZED_VOL_TTL_SECONDS and _realized_vol_cache:
        logger.info(
            "Using cached realized vols (%.0f min old, TTL %.0f min)",
            age / 60, _REALIZED_VOL_TTL_SECONDS / 60,
        )
        return _realized_vol_cache

    logger.info("Fetching realized vols from IB (cache expired or empty)…")
    _realized_vol_cache = _fetch_realized_vols(ib, options_df, stocks_df)
    _realized_vol_fetched_at = time.monotonic()
    return _realized_vol_cache


def get_portfolio_frames() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Public, read-only facade for the Streamlit app and other callers.

    Returns (stocks_df, options_df, hedge_df, crash_df, summary) where:
        stocks_df  — equity positions with concentration metrics
        options_df — option positions with Greeks, DTE, and convexity metrics
        hedge_df   — one row per stock: hedge ratio, status, high-risk flag
        crash_df   — one row per scenario: stock/option/net P&L
        summary    — portfolio-level metrics dict
    No caller ever receives a raw IB client.
    """
    ib  = _get_ib()
    cfg = get_ib_config()

    stocks_df, options_df = _get_positions_frames(ib)

    if not stocks_df.empty:
        stocks_df = add_concentration_metrics(stocks_df)

    if not options_df.empty:
        options_df = add_dte(options_df)
        options_df = fetch_greeks(
            ib, options_df, stocks_df,
            use_ib=cfg.greeks_use_ib,
            max_rows=cfg.max_options_greeks,
        )
        realized_vol_map = _get_realized_vols(ib, options_df, stocks_df)
        options_df = compute_convexity_metrics(options_df, stocks_df, realized_vol_map)

    summary  = build_portfolio_summary(stocks_df, options_df)
    hedge_df = add_hedge_coverage(stocks_df, options_df)
    crash_df = build_crash_scenarios(
        stocks_df, options_df,
        cfg.crash_scenarios,
        summary["total_portfolio_value"],
    )

    return stocks_df, options_df, hedge_df, crash_df, summary


