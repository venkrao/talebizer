# Phase 1 Spec: Portfolio Risk Dashboard
Version: 0.1 | Author: TBD | Date: March 2026

---

## 1. Purpose

A local Python application that connects to Interactive Brokers (IBKR) via the TWS API,
pulls live portfolio data, and produces a daily risk dashboard that answers three questions:

1. Where is my real concentration risk?
2. How well are my equity positions hedged by my open options?
3. What would a market crash cost me, position by position?

This is a decision-support tool for personal use only. It does not execute trades.

---

## 2. Scope

### In Scope
- Pull live positions (stocks + options) from IBKR via ib_async
- Calculate per-position and portfolio-level risk metrics
- Display a local dashboard (Streamlit)
- Export daily snapshot to CSV
- Run entirely locally — no cloud, no external services beyond IBKR connection

### Out of Scope (Phase 2+)
- Options screener / tail cheapness scoring
- Trade execution
- Non-IBKR data sources (yfinance, IVolatility)
- Backtesting

---

## 3. Architecture

    [TWS / IB Gateway]
           |
           | TCP socket (localhost:7497)
           |
      [ib_async client]
           |
      [data layer]        -- pulls + normalizes positions, Greeks
           |
      [metrics engine]    -- calculates risk metrics
           |
      [Streamlit dashboard]  -- local browser UI
           |
      [CSV exporter]      -- daily snapshot

All components run locally. TWS or IB Gateway must be running and logged in.

---

## 4. Dependencies

    Python          >= 3.11
    ib_async        >= 2.1.0      # IBKR API wrapper
    pandas          >= 2.0
    numpy           >= 1.26
    streamlit       >= 1.32
    plotly          >= 5.20       # charts within Streamlit
    python-dotenv                 # config (port, clientId)
    schedule                      # optional: auto-refresh

Install:
    pip install ib_async pandas numpy streamlit plotly python-dotenv schedule

---

## 5. Configuration

File: .env (never committed to git)

    IB_HOST=127.0.0.1
    IB_PORT=7497          # 7497 = TWS paper; 7496 = TWS live; 4002 = Gateway live
    IB_CLIENT_ID=1
    BASE_CURRENCY=USD
    CRASH_SCENARIOS=-0.10,-0.20,-0.30,-0.40,-0.50   # comma-separated % moves

---

## 6. Data Layer

### 6.1 Connection
- Connect to IBKR via ib_async on startup
- Graceful reconnect on disconnect (retry 3x with 5s backoff)
- Read-only mode enforced — no order submission methods exposed

### 6.2 Position Pull
Pull all positions using:

    positions = ib.positions()

For each position, extract:
- symbol, asset class (STK / OPT), quantity, avg cost, current price, market value
- For OPT: strike, expiry, put/call, underlying symbol, multiplier

### 6.3 Greeks Pull
For each open option position, request live Greeks via:

    ib.reqMktData(contract, genericTickList='106', snapshot=True)

Extract: delta, gamma, theta, vega, impliedVol, undPrice

If snapshot fails (no subscription), fall back to Black-Scholes calculated Greeks
using current underlying price + implied vol from last known data.

### 6.4 Data Normalisation
Produce two clean DataFrames:

    stocks_df  columns: symbol, qty, avg_cost, current_price, market_value,
                        weight_pct, sector (manual lookup table)

    options_df columns: symbol, underlying, qty, strike, expiry, put_call,
                        avg_cost, current_price, market_value, multiplier,
                        delta, gamma, theta, vega, implied_vol, dte,
                        cost_basis_total, unrealized_pnl, return_pct,
                        category (Hedge / Active Bet — manual tag or auto-infer)

Auto-infer category rule:
    If underlying is in stocks_df.symbol → "Hedge"
    Else → "Active Bet"

---

## 7. Metrics Engine

### 7.1 Concentration Metrics (per stock)
- market_value
- weight_pct = market_value / total_equity_value
- delta_dollars = market_value  (stocks have delta=1)

### 7.2 Hedge Coverage Ratio (per stock)
For each stock that has one or more puts:

    option_delta_dollars = sum(abs(delta) * multiplier * qty * undPrice)
                           for all puts where underlying == stock.symbol

    hedge_ratio = option_delta_dollars / stock.market_value

Interpretation:
    < 0.10  → effectively unhedged
    0.10–0.25 → lightly hedged
    0.25–0.50 → partially hedged
    > 0.50  → well hedged (rare for tail puts)

Flag: if stock weight_pct > 10% and hedge_ratio < 0.10 → HIGH RISK warning

### 7.3 Portfolio Delta
    total_stock_delta  = sum of all stock market values
    total_option_delta = sum(delta * multiplier * qty * undPrice) for all options
    net_portfolio_delta = total_stock_delta + total_option_delta

### 7.4 Crash Scenario P&L
For each scenario in CRASH_SCENARIOS (e.g. -10%, -20%, -30%, -40%, -50%):

For stocks:
    stock_pnl(s) = market_value(s) * scenario_pct

For options (simplified — use delta + gamma approximation):
    option_pnl(o) = (delta * undPrice * scenario_pct
                    + 0.5 * gamma * (undPrice * scenario_pct)^2)
                    * multiplier * qty

    total_scenario_pnl = sum(stock_pnl) + sum(option_pnl)
    portfolio_survival_pct = total_scenario_pnl / total_portfolio_value

Note: This is a first-order approximation. It will underestimate option gains
in extreme moves (vega expansion not modelled in Phase 1 — add in Phase 2).

### 7.5 Options Book Health
- Total cost basis of options book
- Total current market value
- Unrealized P&L and return %
- Theta burn per day (sum of theta * multiplier * qty across all positions)
- Days until next expiry (earliest DTE)
- Positions expiring within 90 days (flagged for review)

### 7.6 Talebian Discipline Metrics
These enforce strategy rules:

    options_book_pct = options_cost_basis / total_portfolio_value
    Target: 1–5%. Flag if > 7%.

    max_single_position_pct = max(position_cost_basis) / options_cost_basis
    Target: < 10% per position. Flag if > 15%.

    correlated_exposure: count positions where underlying is in same sector
    Flag if > 3 positions in same sector.

    short_dated_count: count options with DTE < 300 at entry
    Flag any. (Enforce long-dated discipline.)

---

## 8. Dashboard (Streamlit)

Single-page local app. Five sections:

### 8.1 Portfolio Overview (top of page)
- Total portfolio value (equity + options)
- Net portfolio delta
- Daily theta burn (cost of holding options today)
- Options book as % of total portfolio
- Last refresh timestamp + Refresh button

### 8.2 Concentration Heatmap
- Horizontal bar chart: each stock, bar length = weight %
- Color: green (< 10%), amber (10–25%), red (> 25%)
- TSLA will immediately appear red given current portfolio

### 8.3 Hedge Coverage Table
Columns: Symbol | Equity Value | Weight % | Hedge Ratio | Status
Status values: ✅ Hedged | ⚠️ Light | ❌ Unhedged
Sortable. Unhedged positions float to top by default.

### 8.4 Crash Scenario Matrix
Table: rows = scenarios (-10% to -50%), columns = [Stock P&L, Options P&L, Net P&L, Net %]
Color: red to green gradient on Net % column.
Beneath table: bar chart showing net P&L per scenario.

### 8.5 Options Book Detail
Full table of open options positions:
Columns: Option | Category | Cost Basis | Market Value | P&L | Return % | DTE | Delta | Theta | IV
Flagged rows: DTE < 90 (amber), Return < -80% (grey — likely going to zero)
Summary row at bottom: totals + daily theta burn.

---

## 9. CSV Export

On each run, write:

    exports/snapshot_YYYYMMDD_HHMMSS.csv

Two sheets (or two files):
- portfolio_snapshot.csv  — stocks_df at time of export
- options_snapshot.csv    — options_df at time of export

Enables manual historical tracking until Phase 2 adds a proper database.

---

## 10. Project Structure

    /taleb-dashboard
    ├── .env                    # secrets, never commit
    ├── .gitignore
    ├── requirements.txt
    ├── README.md
    │
    ├── src/
    │   ├── connection.py       # ib_async connect/reconnect logic
    │   ├── data_pull.py        # positions + Greeks fetch
    │   ├── normalise.py        # raw IBKR data → clean DataFrames
    │   ├── metrics.py          # all calculations (section 7)
    │   ├── export.py           # CSV writer
    │   └── config.py           # loads .env, constants
    │
    ├── dashboard/
    │   └── app.py              # Streamlit app (section 8)
    │
    ├── exports/                # auto-created, gitignored
    └── tests/
        ├── test_metrics.py     # unit tests for metrics engine
        └── mock_data.py        # hardcoded mock positions for offline dev

---

## 11. Development Approach

### Offline-First
Build and test the entire metrics engine and dashboard using mock_data.py
before connecting to live IBKR. This means:
- Day 1–3: mock data → metrics engine → dashboard rendering
- Day 4–5: IBKR connection → swap mock for live data
- Day 6–7: reconcile live data format with assumptions, fix edge cases

### Mock Data
mock_data.py should replicate your exact current portfolio
(stocks + open options from the CSV files provided).
This lets you validate that the dashboard correctly identifies:
- TSLA as a red concentration risk
- AMZN as unhedged
- NVDA 18DEC26 75P as near-expiry and deeply underwater

### Testing
metrics.py must have unit tests for:
- hedge_ratio calculation with known inputs
- crash scenario P&L with delta=1 stock (should equal market_value * scenario)
- options_book_pct flag triggers correctly at 7% threshold

---

## 12. Acceptance Criteria

Phase 1 is complete when:

- [ ] Dashboard loads in browser showing live IBKR data within 30 seconds of TWS being open
- [ ] Concentration heatmap correctly flags TSLA as red (>25% weight)
- [ ] Hedge coverage table correctly shows AMZN, BRK.B, BYD, COST as ❌ Unhedged
- [ ] Crash scenario matrix shows correct net P&L for -30% scenario (manually verified)
- [ ] Daily CSV export writes correctly on each run
- [ ] App runs stably for 8 hours without memory leak or disconnect crash
- [ ] All metrics unit tests pass

---

## 13. Known Limitations (to address in Phase 2)

- Crash scenarios use delta+gamma approximation only — vega expansion on tail options
  will cause underestimation of options gains in extreme moves
- Sector tags are a manual lookup table — not auto-populated
- No historical tracking beyond flat CSV files
- Greeks fallback (Black-Scholes) is less accurate than live IBKR Greeks
- No currency conversion (BYD is HKD-denominated — Phase 1 uses approximate USD value)
- Category auto-inference (Hedge vs Active Bet) is naive — MSTR puts will be
  misclassified as Active Bets even if intended as hedges; manual override needed

---

END OF SPEC v0.1
