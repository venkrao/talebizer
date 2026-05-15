from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd
from ib_async import IB

logger = logging.getLogger(__name__)


def _is_missing(val) -> bool:
    """
    IBKR often uses 0.0 (not None) when a field like marketValue/marketPrice
    is not populated yet. Treat both None and 0.0 as "missing".
    """
    return val is None or val == 0.0


def _portfolio_item_to_dict(item) -> dict:
    """
    Convert an ib_async PortfolioItem or Position into a plain dict with
    common fields, with sensible fallbacks when live marks are missing.
    """
    contract = item.contract

    asset_class = contract.secType  # 'STK', 'OPT', etc.
    symbol = contract.symbol

    position = getattr(item, "position", 0)
    avg_cost = getattr(item, "avgCost", getattr(item, "averageCost", 0.0))

    # Prefer live valuation fields when present (PortfolioItem), otherwise
    # fall back to cost-based approximations so the UI stays comparable to IBKR.
    market_price = getattr(item, "marketPrice", None)
    market_value = getattr(item, "marketValue", None)

    logger.info(f"Item raw: {item}")

    if _is_missing(market_price) and not _is_missing(market_value) and position:
        market_price = market_value / position
    elif not _is_missing(market_price) and _is_missing(market_value):
        market_value = market_price * position
    elif _is_missing(market_price) and _is_missing(market_value):
        # Genuine fallback: no live market data at all, use avg_cost as proxy.
        logger.warning("No live market data for %s, falling back to avg_cost", symbol)
        market_price = avg_cost or 0.0
        market_value = (avg_cost or 0.0) * position

    cost_basis = (avg_cost or 0.0) * position

    unrealized_pnl = getattr(item, "unrealizedPNL", None)
    realized_pnl = getattr(item, "realizedPNL", None)

    # If unrealized P&L not provided by IBKR, derive it from market value - cost basis.
    if _is_missing(unrealized_pnl) and not _is_missing(market_value):
        unrealized_pnl = (market_value or 0.0) - cost_basis

    base = {
        "symbol":       symbol,
        "asset_class":  asset_class,
        "currency":     getattr(contract, "currency", "USD"),
        "quantity":     position,
        "avg_cost":     avg_cost,
        "cost_basis":   cost_basis,
        "current_price": market_price,
        "market_value": market_value or 0.0,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl":   realized_pnl,
    }

    if asset_class == "OPT":
        # Options-specific attributes (ids may differ slightly between setups; be defensive)
        base.update(
            {
                "con_id":     getattr(contract, "conId", None),
                "strike":     getattr(contract, "strike", None),
                "expiry":     getattr(contract, "lastTradeDateOrContractMonth", None),
                "put_call":   getattr(contract, "right", None),
                "underlying": getattr(contract, "symbol", None),
                "multiplier": getattr(contract, "multiplier", None),
            }
        )

    return base


def get_positions_frames(ib: IB) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch all positions from IBKR and split into simple stock and option DataFrames.

    This is a minimal version for visual comparison with the IBKR UI.
    It does not pull Greeks yet and does not compute derived metrics.
    """
    # Collect PortfolioItem objects across all managed accounts. Each account
    # must have had reqAccountUpdates() called (done at connect time) for
    # its items to be present. ib.portfolio(account) is a cheap cache read.
    managed_accounts = ib.managedAccounts()
    if not managed_accounts:
        managed_accounts = []

    items = []
    for account in managed_accounts:
        account_items = ib.portfolio(account)
        if account_items:
            logger.info("Account %s: %d portfolio items", account, len(account_items))
            items.extend(account_items)
        else:
            logger.warning(
                "Account %s: portfolio() returned no items "
                "(updatePortfolio not received yet — check IB_ACCOUNTS in .env)",
                account,
            )

    # Last resort: try without account filter in case ib_async aggregated them
    if not items:
        items = ib.portfolio()

    if not items:
        logger.warning(
            "No portfolio items found for any account. "
            "Ensure IB_ACCOUNTS in .env lists all your account IDs."
        )
        return pd.DataFrame(), pd.DataFrame()

    for item in items:
        logger.info(f"Position: {item}")

    rows = [_portfolio_item_to_dict(p) for p in items]
    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    stocks_df = df[df["asset_class"] == "STK"].reset_index(drop=True)
    options_df = df[df["asset_class"] == "OPT"].reset_index(drop=True)

    return stocks_df, options_df


