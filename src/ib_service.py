from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .config import get_ib_config
from .connection import connect_ib
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


_ib_client: Optional[SafeIB] = None


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


def get_portfolio_frames() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Public, read-only facade for the Streamlit app and other callers.

    Returns (stocks_df, options_df, hedge_df, crash_df, summary) where:
        stocks_df  — equity positions with concentration metrics
        options_df — option positions with Greeks, DTE
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

    summary   = build_portfolio_summary(stocks_df, options_df)
    hedge_df  = add_hedge_coverage(stocks_df, options_df)
    crash_df  = build_crash_scenarios(
        stocks_df, options_df,
        cfg.crash_scenarios,
        summary["total_portfolio_value"],
    )

    return stocks_df, options_df, hedge_df, crash_df, summary


