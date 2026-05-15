"""
Convexity analysis for open option positions (convexity_v1_spec.md v0.2).

Pure-computation module — no IB client dependency.
All inputs come from options_df (with Greeks + DTE), stocks_df (undPrice fallback),
and a realized_vol_map {underlying_symbol: annualised_float}.

Outputs (added as columns to options_df):
    intrinsic_value     — option's intrinsic value at current price
    time_value          — premium above intrinsic
    realized_vol        — annualised realised vol of the underlying
    vol_edge            — σ_realized − σ_implied  (positive = underpriced options)
    convexity_2s        — payoff / premium at 2σ tail move
    convexity_4s        — payoff / premium at 4σ tail move  (primary metric)
    convexity_6s        — payoff / premium at 6σ tail move
    taleb_score         — 0–100 composite score (convexity + vol_edge + time)
    signal              — HOLD / SELL / MONITOR
"""
from __future__ import annotations

import math
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_TAIL_MULTIPLIERS = (2, 4, 6)


# ── Tail price & payoff ────────────────────────────────────────────────────────

def _tail_price(S: float, sigma: float, T: float, multiplier: int, is_call: bool) -> float:
    """
    Lognormal tail price.
    Calls use an upward tail (+σ), puts use a downward tail (−σ).
    S_tail = S * exp(±σ * √T * multiplier)
    """
    direction = 1 if is_call else -1
    return S * math.exp(direction * sigma * math.sqrt(T) * multiplier)


def _tail_payoff(S_tail: float, K: float, is_call: bool) -> float:
    if is_call:
        return max(S_tail - K, 0.0)
    return max(K - S_tail, 0.0)


def _convexity_ratio(
    S: float, K: float, T: float, C: float,
    sigma: float, multiplier: int, is_call: bool,
) -> Optional[float]:
    """payoff_tail / option_premium.  Returns None when inputs are invalid."""
    if C <= 0 or sigma <= 0 or T <= 0 or S <= 0:
        return None
    S_t   = _tail_price(S, sigma, T, multiplier, is_call)
    payoff = _tail_payoff(S_t, K, is_call)
    return round(payoff / C, 2)


# ── Scoring sub-components ─────────────────────────────────────────────────────

def _convexity_score(ratio: Optional[float]) -> int:
    if ratio is None or ratio < 5:
        return 5
    if ratio < 10:
        return 15
    if ratio < 20:
        return 30
    if ratio < 40:
        return 40
    return 50


def _vol_score(vol_edge: Optional[float]) -> int:
    """vol_edge in fractional units (e.g. 0.05 = 5%)."""
    if vol_edge is None:
        return 10          # neutral when no realized vol data
    pct = vol_edge * 100
    if pct < -5:
        return 5
    if pct < 0:
        return 10
    if pct < 5:
        return 20
    return 30


def _time_score(dte: Optional[float]) -> int:
    if dte is None or dte < 30:
        return 5
    if dte < 90:
        return 10
    if dte < 180:
        return 15
    return 20


def _compute_taleb_score(
    convexity_4s: Optional[float],
    vol_edge: Optional[float],
    dte: Optional[float],
) -> int:
    return _convexity_score(convexity_4s) + _vol_score(vol_edge) + _time_score(dte)


def _compute_signal(
    convexity_4s: Optional[float],
    dte: Optional[float],
    vol_edge: Optional[float],
) -> str:
    """
    Signal logic (convexity_v1_spec.md §5 / §6), with vol_edge override.

    SELL conditions (§6):
        - DTE < 30 (expiring soon, unconditional)
        - convexity_4s < 5 AND vol_edge is not meaningfully positive
          (if vol_edge > 20%, options are cheap enough to justify holding
           even when structural convexity is limited by the premium level)

    HOLD condition (§5):
        - convexity_4s > 20 AND DTE > 90

    Everything else → MONITOR.
    """
    if dte is not None and dte < 30:
        return "SELL — expiring soon"

    # Low structural convexity — but override if vol edge is strongly favourable
    vol_edge_pct = (vol_edge * 100) if vol_edge is not None else None
    if convexity_4s is not None and convexity_4s < 5:
        if vol_edge_pct is not None and vol_edge_pct > 20:
            # Premium is high relative to strike cap, but realized vol dwarfs implied —
            # market is still mispricing the tail. Downgrade to MONITOR rather than SELL.
            return "MONITOR — vol edge offsets low convexity"
        return "SELL — low convexity"

    if convexity_4s is not None and convexity_4s > 20 and dte is not None and dte > 90:
        return "HOLD"

    return "MONITOR"


# ── Main entry point ───────────────────────────────────────────────────────────

def compute_convexity_metrics(
    options_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    realized_vol_map: dict,
) -> pd.DataFrame:
    """
    Enrich options_df with convexity metrics.

    realized_vol_map: {underlying_symbol: annualised_float}
                      e.g. {"AAPL": 0.28, "TSLA": 0.61}

    Returns options_df with new columns added.
    """
    if options_df.empty:
        return options_df

    # Underlying price lookup: IB's undPrice is most accurate; fall back to
    # stock's current market price when not available.
    und_price_lookup: dict = {}
    if not stocks_df.empty and "current_price" in stocks_df.columns:
        und_price_lookup = dict(
            zip(stocks_df["symbol"], pd.to_numeric(stocks_df["current_price"], errors="coerce"))
        )

    df = options_df.copy()
    rows: list[dict] = []

    for _, opt in df.iterrows():
        symbol     = opt.get("symbol", "?")
        underlying = opt.get("underlying") or symbol

        # --- Core inputs ---
        S = pd.to_numeric(opt.get("und_price"), errors="coerce")
        if pd.isna(S) or S <= 0:
            S = float(und_price_lookup.get(underlying) or 0.0)

        K        = float(pd.to_numeric(opt.get("strike"),        errors="coerce") or 0)
        C        = float(pd.to_numeric(opt.get("current_price"), errors="coerce") or 0)
        dte_raw  = pd.to_numeric(opt.get("dte"), errors="coerce")
        dte      = float(dte_raw) if not pd.isna(dte_raw) else None
        T        = (dte / 365.0) if dte is not None and dte > 0 else None

        right    = str(opt.get("put_call", "P")).strip().upper()[:1]
        is_call  = right == "C"

        # --- Intrinsic & time value ---
        if S > 0 and K > 0:
            intrinsic = max(K - S, 0.0) if not is_call else max(S - K, 0.0)
        else:
            intrinsic = None
        time_val = (C - intrinsic) if (intrinsic is not None and C > 0) else None

        # --- Volatility ---
        sigma_r  = realized_vol_map.get(underlying)    # may be None
        sigma_iv = float(pd.to_numeric(opt.get("implied_vol"), errors="coerce") or 0) or None
        vol_edge = round(sigma_r - sigma_iv, 4) if (sigma_r and sigma_iv) else None

        # --- Convexity ratios at 2σ / 4σ / 6σ ---
        conv: dict[str, Optional[float]] = {}
        for m in _TAIL_MULTIPLIERS:
            key = f"convexity_{m}s"
            if sigma_r and T and S > 0 and K > 0 and C > 0:
                conv[key] = _convexity_ratio(S, K, T, C, sigma_r, m, is_call)
            else:
                conv[key] = None

        # --- Scores & signal ---
        taleb_score = _compute_taleb_score(conv.get("convexity_4s"), vol_edge, dte)
        signal      = _compute_signal(conv.get("convexity_4s"), dte, vol_edge)

        rows.append({
            "intrinsic_value": round(intrinsic, 4) if intrinsic is not None else None,
            "time_value":      round(time_val,  4) if time_val  is not None else None,
            "realized_vol":    round(sigma_r, 4)   if sigma_r   is not None else None,
            "vol_edge":        vol_edge,
            "convexity_2s":    conv.get("convexity_2s"),
            "convexity_4s":    conv.get("convexity_4s"),
            "convexity_6s":    conv.get("convexity_6s"),
            "taleb_score":     taleb_score,
            "signal":          signal,
        })

        logger.debug(
            "Convexity %s: 4σ=%.1f score=%d signal=%s",
            symbol,
            conv.get("convexity_4s") or 0,
            taleb_score,
            signal,
        )

    conv_df = pd.DataFrame(rows, index=df.index)
    for col in conv_df.columns:
        df[col] = conv_df[col]

    return df
