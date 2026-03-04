from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .connection import connect_ib
from .data_pull import get_positions_frames as _get_positions_frames
from .metrics import add_concentration_metrics, add_dte, build_portfolio_summary
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


def get_portfolio_frames() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Public, read-only facade for the Streamlit app and other callers.

    Returns (stocks_df, options_df, summary) where summary is a dict of
    portfolio-level metrics (total values, options_book_pct, DTE flags, etc.).
    No caller ever receives a raw IB client.
    """
    ib = _get_ib()
    stocks_df, options_df = _get_positions_frames(ib)

    if not stocks_df.empty:
        stocks_df = add_concentration_metrics(stocks_df)

    if not options_df.empty:
        options_df = add_dte(options_df)

    summary = build_portfolio_summary(stocks_df, options_df)

    return stocks_df, options_df, summary


