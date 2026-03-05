"""
Greeks pull for open option positions.

Primary path : reqMktData(contract, snapshot=False) → IB sends modelGreeks
               (delta, gamma, theta, vega, impliedVol, undPrice) automatically
               for option contracts; we read them and cancel the subscription.

Fallback path : Black-Scholes with Newton-Raphson IV solver when IB returns
               empty values. Uses the option's market price from the portfolio
               and the underlying price from stocks_df — no assumed IV.
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Optional

import pandas as pd
from ib_async import IB, Option

logger = logging.getLogger(__name__)

_RISK_FREE_RATE = 0.045   # annualised, used for BS model
_MKT_DATA_WAIT  = 10      # seconds to wait for streaming snapshot (only when GREEKS_USE_IB=true)


# ── Black-Scholes core ─────────────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)


def _bs_price(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
    if T <= 0 or sigma <= 0:
        return max(0.0, (S - K) if is_call else (K - S))
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    if is_call:
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def _implied_vol(
    S: float,
    K: float,
    T: float,
    r: float,
    market_price: float,
    is_call: bool,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> Optional[float]:
    """Newton-Raphson IV solver. Returns None if it cannot converge."""
    if market_price <= 0 or S <= 0 or K <= 0 or T <= 0:
        return None

    sigma = 0.30  # initial guess
    for _ in range(max_iter):
        price = _bs_price(S, K, T, r, sigma, is_call)
        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        vega_val = S * _norm_pdf(d1) * sqrt_T  # un-scaled vega
        if abs(vega_val) < 1e-12:
            break
        sigma -= (price - market_price) / vega_val
        if sigma <= 1e-6:
            sigma = 1e-6
        if abs(price - market_price) < tol:
            return sigma

    return sigma if 0 < sigma < 20 else None


def _bs_greeks(
    S: float, K: float, T: float, r: float, sigma: float, is_call: bool
) -> dict:
    """Return delta, gamma, theta (per calendar day), vega (per 1% vol)."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"delta": None, "gamma": None, "theta": None, "vega": None}

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    phi = _norm_pdf(d1)
    gamma = phi / (S * sigma * sqrt_T)
    vega  = S * phi * sqrt_T / 100

    disc  = math.exp(-r * T)
    Nd2   = _norm_cdf(d2) if is_call else _norm_cdf(-d2)
    theta_annual = -(S * phi * sigma) / (2 * sqrt_T) - r * K * disc * Nd2
    theta = theta_annual / 365

    delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1.0

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega":  round(vega,  4),
    }


# ── Contract helpers ───────────────────────────────────────────────────────────

def _build_option_contract(row: pd.Series) -> Optional[object]:
    """
    Build an Option contract for reqMktData.

    Prefers the conId stored in the row (populated from PortfolioItem.contract.conId)
    so that qualifyContracts is never needed. Falls back to symbol+expiry+strike
    construction for any row that lacks a conId.
    """
    try:
        con_id = row.get("con_id")
        mult   = str(row.get("multiplier", "100")).strip() or "100"

        if con_id and int(con_id) > 0:
            # Already known to IB — no qualification needed.
            return Option(conId=int(con_id), exchange="SMART", multiplier=mult)

        # Fallback: build from symbology (requires qualifyContracts before use).
        expiry = str(row["expiry"]).strip()[:8]
        right  = str(row["put_call"]).strip().upper()[0]
        return Option(
            symbol=row["symbol"],
            lastTradeDateOrContractMonth=expiry,
            strike=float(row["strike"]),
            right=right,
            multiplier=mult,
            currency="USD",
            exchange="SMART",
        )
    except Exception as exc:
        logger.warning("Could not build contract for %s: %s", row.get("symbol"), exc)
        return None


def _extract_greeks_from_ticker(ticker) -> dict:
    mg = getattr(ticker, "modelGreeks", None)
    if mg is None:
        return {}

    def _safe(val) -> Optional[float]:
        if val is None:
            return None
        try:
            v = float(val)
            return None if (v == 0.0 or abs(v) > 1e10) else v
        except (TypeError, ValueError):
            return None

    return {
        "delta":       _safe(getattr(mg, "delta",      None)),
        "gamma":       _safe(getattr(mg, "gamma",      None)),
        "theta":       _safe(getattr(mg, "theta",      None)),
        "vega":        _safe(getattr(mg, "vega",       None)),
        "implied_vol": _safe(getattr(mg, "impliedVol", None)),
        "und_price":   _safe(getattr(mg, "undPrice",   None)),
    }


# ── Fallback: BS Greeks from portfolio prices ──────────────────────────────────

def _bs_greeks_from_portfolio(
    row: pd.Series,
    und_price_map: dict,
) -> dict:
    """
    Compute Greeks using Black-Scholes with implied-vol solved from the option's
    current market price and the underlying's live price (from stocks_df).

    Falls back to a 30% IV assumption only if the option has no market price.
    """
    try:
        symbol     = row.get("underlying") or row.get("symbol")
        S          = und_price_map.get(symbol)

        # Use option's current market price to solve for IV (much more accurate
        # than a fixed 30% assumption).
        opt_price  = float(row.get("current_price") or 0)
        K          = float(row.get("strike") or 0)
        right      = str(row.get("put_call", "P")).strip().upper()[0]
        is_call    = right == "C"

        expiry_raw = str(row.get("expiry", "")).strip()[:8]
        exp_date   = datetime.strptime(expiry_raw, "%Y%m%d").date()
        T          = max((exp_date - date.today()).days / 365.0, 0.0)

        if S is None or S <= 0:
            # No underlying price available; use avg_cost of the option as proxy
            logger.warning("No underlying price for %s — using avg_cost as undPrice proxy", symbol)
            S = float(row.get("avg_cost") or 0)

        iv = None
        if opt_price > 0 and S > 0 and K > 0 and T > 0:
            iv = _implied_vol(S, K, T, _RISK_FREE_RATE, opt_price, is_call)
            if iv:
                logger.info(
                    "BS IV for %s: %.1f%% (from market price $%.4f)",
                    row.get("symbol"), iv * 100, opt_price,
                )

        if iv is None:
            iv = 0.30
            logger.warning(
                "IV solve failed for %s — using 30%% default",
                row.get("symbol"),
            )

        greeks = _bs_greeks(S, K, T, _RISK_FREE_RATE, iv, is_call)
        greeks["implied_vol"] = round(iv, 4)
        greeks["und_price"]   = round(S, 4) if S else None
        return greeks

    except Exception as exc:
        logger.warning("BS fallback failed for %s: %s", row.get("symbol"), exc)
        return {
            "delta": None, "gamma": None, "theta": None,
            "vega":  None, "implied_vol": None, "und_price": None,
        }


# ── Main entry point ───────────────────────────────────────────────────────────

def fetch_greeks(
    ib: IB,
    options_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    use_ib: bool = False,
    max_rows: int = 4,
) -> pd.DataFrame:
    """
    Compute Greeks for up to `max_rows` option positions.

    When use_ib=True: tries reqMktData streaming first, falls back to BS.
    When use_ib=False (default): goes straight to BS using portfolio prices.
      This is fast (no network wait) and works without market data subscriptions.

    BS quality: uses the option's market price + underlying stock price from
    stocks_df to solve for implied volatility via Newton-Raphson, then computes
    all Greeks. For underlyings not in stocks_df, uses avg_cost as a proxy.

    Returns options_df augmented with:
        delta, gamma, theta, vega, implied_vol, und_price, greeks_source
    """
    if options_df.empty:
        return options_df

    # Build underlying price lookup from stocks_df.
    und_price_map: dict = {}
    if not stocks_df.empty and "current_price" in stocks_df.columns:
        und_price_map = dict(
            zip(stocks_df["symbol"], pd.to_numeric(stocks_df["current_price"], errors="coerce"))
        )

    df = options_df.copy()
    greeks_rows: list[dict] = []
    total = len(df)

    if use_ib:
        # Request 15-minute delayed data — free for all IBKR accounts, no subscription needed.
        # Must be called before any reqMktData. IB will automatically upgrade to live data
        # for any instrument where you do have a subscription.
        try:
            ib.reqMarketDataType(3)
            logger.info("Market data type set to 3 (delayed)")
        except Exception as exc:
            logger.warning("Could not set delayed market data type: %s", exc)

    rows_list = list(df.iterrows())

    if use_ib:
        # ── Batched IB path ────────────────────────────────────────────────────
        # Fire reqMktData for ALL eligible contracts at once, then poll a single
        # shared loop. Total wait = _MKT_DATA_WAIT regardless of how many options
        # you have, instead of N × _MKT_DATA_WAIT with the old sequential approach.
        #
        # slot: (df_idx, row, ticker_or_None, contract_or_None, within_limit)
        slots = []
        for idx, (df_idx, row) in enumerate(rows_list):
            if idx >= max_rows:
                slots.append((df_idx, row, None, None, False))
                continue

            # _build_option_contract uses conId directly when available — no
            # qualifyContracts round-trip needed, which avoids the hang on refresh.
            contract = _build_option_contract(row)

            ticker = None
            if contract is not None:
                try:
                    ticker = ib.reqMktData(contract, genericTickList="", snapshot=False)
                except Exception as exc:
                    logger.warning("reqMktData failed for %s: %s", row.get("symbol"), exc)

            slots.append((df_idx, row, ticker, contract, True))

        # Single shared polling loop — exits as soon as every active ticker has
        # a delta value, or the deadline is reached.
        active = [(df_idx, row, t, c) for df_idx, row, t, c, ok in slots if ok and t is not None]
        ib_results: dict = {}  # df_idx → greeks dict
        waited, step = 0.0, 0.25
        while waited < _MKT_DATA_WAIT and len(ib_results) < len(active):
            ib.sleep(step)
            waited += step
            for df_idx, row, ticker, _ in active:
                if df_idx in ib_results:
                    continue
                check = _extract_greeks_from_ticker(ticker)
                if check.get("delta") is not None:
                    ib_results[df_idx] = check
        logger.info(
            "IB batch: %d/%d returned Greeks in %.1fs",
            len(ib_results), len(active), waited,
        )

        # Cancel all market data subscriptions in one pass.
        for df_idx, row, ticker, contract in active:
            if ticker is not None and contract is not None:
                try:
                    ib.cancelMktData(contract)
                except Exception:
                    pass

        # Build greeks_rows in original DataFrame order.
        for df_idx, row, ticker, contract, within_limit in slots:
            symbol = row.get("symbol", "?")
            if not within_limit:
                greeks_rows.append({
                    "delta": None, "gamma": None, "theta": None,
                    "vega": None, "implied_vol": None, "und_price": None,
                    "greeks_source": "skipped",
                })
                continue

            if df_idx in ib_results:
                row_greeks = ib_results[df_idx]
                row_greeks["greeks_source"] = "ib"
                logger.info(
                    "IB Greeks for %s: delta=%.3f iv=%.1f%%",
                    symbol,
                    row_greeks.get("delta", 0),
                    (row_greeks.get("implied_vol") or 0) * 100,
                )
            else:
                row_greeks = _bs_greeks_from_portfolio(row, und_price_map)
                row_greeks["greeks_source"] = "bs_fallback"
                logger.info(
                    "BS fallback for %s: delta=%s iv=%s",
                    symbol,
                    row_greeks.get("delta"),
                    f"{(row_greeks.get('implied_vol') or 0)*100:.1f}%",
                )
            greeks_rows.append(row_greeks)

    else:
        # ── Pure BS path (no IB calls) ─────────────────────────────────────────
        for idx, (df_idx, row) in enumerate(rows_list):
            symbol = row.get("symbol", "?")
            if idx >= max_rows:
                greeks_rows.append({
                    "delta": None, "gamma": None, "theta": None,
                    "vega": None, "implied_vol": None, "und_price": None,
                    "greeks_source": "skipped",
                })
                continue
            row_greeks = _bs_greeks_from_portfolio(row, und_price_map)
            row_greeks["greeks_source"] = "bs_fallback"
            logger.info(
                "BS Greeks for %s: delta=%s iv=%s",
                symbol,
                row_greeks.get("delta"),
                f"{(row_greeks.get('implied_vol') or 0)*100:.1f}%",
            )
            greeks_rows.append(row_greeks)

    logger.info("Greeks done: %d total rows", total)

    greeks_df = pd.DataFrame(greeks_rows, index=df.index)
    for col in greeks_df.columns:
        df[col] = greeks_df[col]

    return df
