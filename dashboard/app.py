import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure project root (parent of this file's directory) is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ib_service import get_portfolio_frames


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Talebizer – Risk Dashboard", layout="wide")
st.title("Talebizer – Portfolio Risk Dashboard")

STOCK_COLS = [
    "symbol", "quantity",
    "avg_cost", "cost_basis",
    "current_price", "market_value",
    "weight_pct",
    "unrealized_pnl", "realized_pnl",
]
OPTION_COLS = [
    "symbol", "underlying", "put_call", "strike", "expiry", "dte", "multiplier",
    "quantity",
    "avg_cost", "cost_basis",
    "current_price", "market_value",
    "unrealized_pnl", "realized_pnl",
    "delta", "gamma", "theta", "vega", "implied_vol", "und_price",
    "greeks_source",
]

FLAG_COLOURS = {"red": "#ef4444", "amber": "#f59e0b", "green": "#22c55e"}


def _fmt_currency(val: float, decimals: int = 0) -> str:
    return f"${val:,.{decimals}f}"


def main():
    refresh_clicked = st.button("Refresh positions")

    # Load data on first visit or when Refresh is explicitly clicked.
    # Between refreshes, the cached values in session_state are shown instantly.
    needs_load = (
        refresh_clicked
        or "stocks_df" not in st.session_state
        or "options_df" not in st.session_state
    )

    if needs_load:
        with st.spinner("Fetching positions and Greeks from IBKR…"):
            try:
                stocks_df, options_df, hedge_df, crash_df, summary = get_portfolio_frames()
            except Exception as exc:
                logger.exception("Failed to load positions from IBKR")
                st.error(
                    "Could not load positions from IBKR. "
                    "Please ensure TWS or IB Gateway is running, API access is enabled, "
                    "and the host/port/clientId in `.env` are correct.\n\n"
                    f"Error: {exc}"
                )
                return
            st.session_state["stocks_df"] = stocks_df
            st.session_state["options_df"] = options_df
            st.session_state["hedge_df"]   = hedge_df
            st.session_state["crash_df"]   = crash_df
            st.session_state["summary"]    = summary
    else:
        stocks_df = st.session_state["stocks_df"]
        options_df = st.session_state["options_df"]
        hedge_df   = st.session_state["hedge_df"]
        crash_df   = st.session_state["crash_df"]
        summary    = st.session_state["summary"]

    if stocks_df.empty and options_df.empty:
        st.warning("No positions returned from IBKR.")
        return

    # ── §8.1 Portfolio Overview strip ─────────────────────────────────────────
    _show_overview_strip(summary)

    st.divider()

    # ── §8.2 Concentration Heatmap ─────────────────────────────────────────────
    if not stocks_df.empty and "weight_pct" in stocks_df.columns:
        with st.expander("Concentration Heatmap", expanded=False):
            _show_concentration_heatmap(stocks_df)

    st.divider()

    # ── §8.3 Hedge Coverage Table ──────────────────────────────────────────────
    if not hedge_df.empty:
        st.subheader("Hedge Coverage")
        _show_hedge_coverage_table(hedge_df)
        st.divider()

    # ── §8.4 Crash Scenario Matrix ─────────────────────────────────────────────
    if not crash_df.empty:
        st.subheader("Crash Scenario Matrix")
        _show_crash_scenario_matrix(crash_df)
        st.divider()

    # ── Raw positions tables ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Stock Positions (STK)")
        if stocks_df.empty:
            st.write("No stock positions.")
        else:
            _show_positions_table(stocks_df, STOCK_COLS)

    with col2:
        st.subheader("Option Positions (OPT)")
        if options_df.empty:
            st.write("No option positions.")
        else:
            _show_options_table(options_df, OPTION_COLS)


def _show_overview_strip(s: dict) -> None:
    st.subheader("Portfolio Overview")

    cols = st.columns(6)

    cols[0].metric(
        "Total Portfolio",
        _fmt_currency(s["total_portfolio_value"]),
    )
    cols[1].metric(
        "Equity Value",
        _fmt_currency(s["total_equity_value"]),
    )
    cols[2].metric(
        "Options Cost Basis",
        _fmt_currency(s["total_options_cost"]),
    )
    cols[3].metric(
        "Options Mkt Value",
        _fmt_currency(s["total_options_mkt_value"]),
        delta=_fmt_currency(s["options_unrealized_pnl"]),
        delta_color="normal",
    )

    # Options book % with warning colour
    book_pct = s["options_book_pct"]
    book_label = f"{book_pct:.2f}%"
    if s["options_book_flag"] == "warning":
        book_label += " ⚠️"
    cols[4].metric("Options Book %", book_label, help="Target: 1–5%. Flag if > 7%.")

    # Earliest DTE
    dte_val = s["earliest_dte"]
    dte_str = f"{dte_val}d" if dte_val is not None else "—"
    dte_label = dte_str
    if dte_val is not None and dte_val < 90:
        dte_label += " ⚠️"
    cols[5].metric(
        "Nearest Expiry",
        dte_label,
        help=f"{s['n_options_expiring_90d']} option(s) expiring within 90 days.",
    )

    # Second row: theta burn (only shown when Greeks are available)
    theta = s.get("daily_theta_burn")
    if theta is not None:
        st.caption(
            f"📉 Daily theta burn: **${theta:,.2f}** "
            f"(cost of holding all options for one more day)"
        )

    st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def _show_concentration_heatmap(stocks_df: pd.DataFrame) -> None:
    df = stocks_df[["symbol", "weight_pct", "concentration_flag"]].copy()
    df = df.sort_values("weight_pct", ascending=True)

    colours = df["concentration_flag"].map(FLAG_COLOURS).fillna(FLAG_COLOURS["green"])

    fig = go.Figure(go.Bar(
        x=df["weight_pct"],
        y=df["symbol"],
        orientation="h",
        marker_color=colours,
        text=df["weight_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        xaxis_title="Portfolio Weight (%)",
        yaxis_title=None,
        xaxis=dict(range=[0, max(df["weight_pct"].max() * 1.15, 30)]),
        height=max(250, len(df) * 38),
        margin=dict(l=10, r=60, t=10, b=30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    for threshold, label in [(10, "10%"), (25, "25%")]:
        fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color="rgba(150,150,150,0.5)",
            annotation_text=label,
            annotation_position="top",
        )

    st.plotly_chart(fig, width="stretch")
    st.caption("🟢 < 10%  ·  🟡 10–25%  ·  🔴 > 25%")


def _show_crash_scenario_matrix(crash_df: pd.DataFrame) -> None:
    """§8.4 — Crash Scenario Matrix: table + bar chart."""
    df = crash_df.copy()

    # ── Formatted display table ──
    display = pd.DataFrame()
    display["Scenario"]    = df["scenario_pct"].apply(lambda v: f"{v*100:.0f}%")
    display["Stock P&L"]   = df["stock_pnl"].apply(_fmt_currency)
    display["Options P&L"] = df["options_pnl"].apply(_fmt_currency)
    display["Net P&L"]     = df["net_pnl"].apply(_fmt_currency)
    display["Net %"]       = df["net_pct"].apply(lambda v: f"{v:+.2f}%")

    # Colour the Net % column: deeper red = worse loss, green = gain
    def _colour_net(val: str) -> str:
        try:
            v = float(val.replace("%", "").replace("+", ""))
        except ValueError:
            return ""
        if v >= 0:
            return "color: #22c55e; font-weight: bold"
        intensity = min(int(abs(v) / 50 * 200) + 55, 255)
        return f"color: rgb({intensity}, 50, 50); font-weight: bold"

    styled = display.style.map(_colour_net, subset=["Net %"])
    st.dataframe(styled, width="stretch", hide_index=True)
    st.caption(
        "Options P&L uses delta + gamma approximation (first-order Taylor expansion). "
        "Vega expansion not modelled — actual tail-option gains in extreme moves will be higher."
    )

    # ── Bar chart ──
    colours = ["#22c55e" if v >= 0 else "#ef4444" for v in df["net_pnl"]]
    fig = go.Figure(go.Bar(
        x=df["scenario_pct"].apply(lambda v: f"{v*100:.0f}%"),
        y=df["net_pnl"],
        marker_color=colours,
        text=df["net_pnl"].apply(lambda v: f"${v:,.0f}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Net P&L: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Scenario (equity move)",
        yaxis_title="Net P&L ($)",
        height=320,
        margin=dict(l=10, r=10, t=10, b=30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(150,150,150,0.5)")
    st.plotly_chart(fig, width="stretch")


_HEDGE_STATUS_ICON = {
    "hedged":   "✅ Hedged",
    "partial":  "🟡 Partial",
    "light":    "⚠️ Light",
    "unhedged": "❌ Unhedged",
}


def _show_hedge_coverage_table(hedge_df: pd.DataFrame) -> None:
    """§8.3 — Hedge Coverage Table. Unhedged high-risk positions float to top."""
    df = hedge_df.copy()

    df["Status"] = df["status"].map(_HEDGE_STATUS_ICON).fillna(df["status"])
    df["Equity Value"] = df["equity_value"].apply(lambda v: _fmt_currency(v))
    df["Weight %"] = df["weight_pct"].apply(lambda v: f"{v:.1f}%")
    df["Opt Δ$"] = df["option_delta_dollars"].apply(
        lambda v: _fmt_currency(v) if v > 0 else "—"
    )
    df["Hedge Ratio"] = df["hedge_ratio"].apply(
        lambda v: f"{v:.1%}" if v > 0 else "—"
    )
    df["Puts"] = df["n_puts"].apply(lambda v: str(v) if v > 0 else "—")
    df["⚠"] = df["high_risk"].apply(lambda v: "HIGH RISK" if v else "")

    display_cols = ["symbol", "Equity Value", "Weight %", "Puts", "Opt Δ$", "Hedge Ratio", "Status", "⚠"]
    present = [c for c in display_cols if c in df.columns]
    display_df = df[present].rename(columns={"symbol": "Symbol"})

    n_high_risk  = int(df["high_risk"].sum())
    n_unhedged   = int((df["status"] == "unhedged").sum())
    n_total      = len(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Stocks", n_total)
    col2.metric("Unhedged", n_unhedged, delta=None)
    col3.metric("High Risk (>10% weight, unhedged)", n_high_risk)

    st.dataframe(display_df, width="stretch", hide_index=True)
    st.caption(
        "Hedge Ratio = option delta-dollars / equity market value  ·  "
        "✅ > 50%  ·  🟡 25–50%  ·  ⚠️ 10–25%  ·  ❌ < 10%"
    )


def _show_positions_table(df: pd.DataFrame, cols: list[str]) -> None:
    display_df = _prep_table(df, cols)
    st.dataframe(display_df, width="stretch")


def _show_options_table(df: pd.DataFrame, cols: list[str]) -> None:
    """Options table with row highlighting for near-expiry positions."""
    display_df = _prep_table(df, cols)

    # Append a simple text flag so near-expiry rows are visually obvious
    if "dte" in display_df.columns and "expiry_flag" in df.columns:
        flag_map = df["expiry_flag"].values
        display_df = display_df.copy()
        # Streamlit doesn't support row colouring natively; surface the flag as a column
        display_df.insert(
            display_df.columns.get_loc("dte") + 1 if "dte" in display_df.columns else len(display_df.columns),
            "dte_flag",
            ["⚠️" if f == "urgent" else ("🕐" if f == "expired" else "") for f in flag_map],
        )

    st.dataframe(display_df, width="stretch")
    st.caption("⚠️ = expiring within 90 days")


def _prep_table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    display_df = df.copy()
    present_cols = [c for c in cols if c in display_df.columns]
    display_df = display_df[present_cols]

    for col in ["quantity", "avg_cost", "cost_basis", "current_price", "market_value",
                "weight_pct", "unrealized_pnl", "realized_pnl", "strike", "dte",
                "delta", "gamma", "theta", "vega", "implied_vol", "und_price"]:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

    display_df = display_df.sort_values(by=["symbol"], ascending=True)
    return display_df


if __name__ == "__main__":
    main()
