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
]

FLAG_COLOURS = {"red": "#ef4444", "amber": "#f59e0b", "green": "#22c55e"}


def _fmt_currency(val: float, decimals: int = 0) -> str:
    return f"${val:,.{decimals}f}"


def main():
    st.button("Refresh positions")

    with st.spinner("Connecting to IBKR and loading positions..."):
        try:
            stocks_df, options_df, summary = get_portfolio_frames()
        except Exception as exc:
            logger.exception("Failed to load positions from IBKR")
            st.error(
                "Could not load positions from IBKR. "
                "Please ensure TWS or IB Gateway is running, API access is enabled, "
                "and the host/port/clientId in `.env` are correct.\n\n"
                f"Error: {exc}"
            )
            return

    if stocks_df.empty and options_df.empty:
        st.warning("No positions returned from IBKR.")
        return

    # ── §8.1 Portfolio Overview strip ─────────────────────────────────────────
    _show_overview_strip(summary)

    st.divider()

    # ── §8.2 Concentration Heatmap ─────────────────────────────────────────────
    if not stocks_df.empty and "weight_pct" in stocks_df.columns:
        st.subheader("Concentration Heatmap")
        _show_concentration_heatmap(stocks_df)

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

    st.plotly_chart(fig, use_container_width=True)
    st.caption("🟢 < 10%  ·  🟡 10–25%  ·  🔴 > 25%")


def _show_positions_table(df: pd.DataFrame, cols: list[str]) -> None:
    display_df = _prep_table(df, cols)
    st.dataframe(display_df, use_container_width=True)


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

    st.dataframe(display_df, use_container_width=True)
    st.caption("⚠️ = expiring within 90 days")


def _prep_table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    display_df = df.copy()
    present_cols = [c for c in cols if c in display_df.columns]
    display_df = display_df[present_cols]

    for col in ["quantity", "avg_cost", "cost_basis", "current_price", "market_value",
                "weight_pct", "unrealized_pnl", "realized_pnl", "strike", "dte"]:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

    display_df = display_df.sort_values(by=["symbol"], ascending=True)
    return display_df


if __name__ == "__main__":
    main()
