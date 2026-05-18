# Why Talebizer Exists

## Purpose

**Talebizer** is a **local, read-only** portfolio dashboard that connects to **Interactive Brokers (IBKR)** through **Trader Workstation (TWS)** or **IB Gateway** and turns live positions into **risk-oriented summaries**.

It is built for **personal decision support**, not for prediction or execution:

- Answer questions such as **where concentration sits**, **how equity might be hedged by listed puts**, **what simplified crash shocks imply**, and **how asymmetric (“tail”) option convexity looks versus premium paid**.
- **No trades**: any attempt to place, modify, or cancel orders is blocked in code (`SafeIB`).

---

## What Problem It Solves

Traditional brokerage UIs show balances and positions well but scatter **cross-cutting risk views** across panels.

This project pulls **one consolidated snapshot** per refresh:

| Lens | Question |
|------|-----------|
| **Concentration** | Which stocks dominate equity exposure by weight? |
| **Hedge coverage** | For puts referencing each underlying, how much **delta-dollar** protection exists versus equity market value? (Interpret as day-to-day delta coupling — deep OTM tail puts remain informative elsewhere.) |
| **Crash scenarios (Δ–Γ)** | Under hypothetical equity moves, what is a **first-order + second-order** P&amp;L estimate from stocks plus options? |
| **Convexity / Talebian** | Given **realized** volatility versus **implied**, how large is **tail payoff per dollar of premium** in stylized σ-moves, and a simple **composite score** for hold vs monitor vs sell hints |

Specifications guiding behaviour live in `phase1_spec.md`, `convexity_spec.md`, and `convexity_v1_spec.md`.

---

## Technical Stack

| Layer | Choice |
|--------|--------|
| Language | Python ≥ 3.11 |
| IB API wrapper | **`ib_async`** (async core with synchronous helpers such as `ib.connect`, `ib.sleep`) |
| UI | **Streamlit** (`dashboard/app.py`) |
| Tables / numerics | **pandas**, **numpy** |
| Charts | **plotly** (concentration bars, crash scenario bars) |
| Config | **`python-dotenv`** → `.env` (never commit secrets) |

---

## Architecture (How Data Flows)

```
[TWS / IB Gateway : socket API]
        │
        ▼
   SafeIB (read-only subclass of ib_async.IB)
        │
        ▼
   connection.connect_ib()   ← retries, primary account + extra reqAccountUpdates
        │
        ▼
   data_pull.get_positions_frames()
        └→ ib.portfolio(account) per managed account → PortfolioItem rows
             (marketPrice / marketValue vs bare Position objects)
        │
        ▼
   metrics.add_concentration_metrics()   ← weight % on stocks
   metrics.add_dte()                     ← option DTE + urgency flags
        │
        ▼
   greeks.fetch_greeks()
        └→ optional IB path: reqMarketDataType(delayed), batch reqMktData,
             modelGreeks; else Black–Scholes fallback from portfolio prices
        │
        ▼
   convexity.compute_convexity_metrics()
        └→ uses IB historical daily bars per underlying for ~30d realized vol
             (cached ~1h in ib_service to limit repeated HMDS traffic)
        │
        ▼
   metrics.add_hedge_coverage(), build_crash_scenarios(), build_portfolio_summary()
        │
        ▼
   Streamlit session cache + tables / charts
```

The **only** supported entry point for the UI is **`src/ib_service.py:get_portfolio_frames()`**, which returns `(stocks_df, options_df, hedge_df, crash_df, summary)` so callers never hold a raw IB client.

---

## Key Modules

| File | Role |
|------|------|
| `src/safe_ib.py` | **`SafeIB`**: overrides order-related IB methods to raise — belt-and-suspenders read-only guard |
| `src/connection.py` | Connect with **`readonly=True`**, pass primary `account=` so portfolio streaming fills in; subscribe extra accounts |
| `src/config.py` | Loads host/port/client id, accounts list, Greeks flags, crash scenario list, etc. |
| `src/data_pull.py` | Normalizes **`PortfolioItem`** → rows; treats **0.0** as missing for some IB fields; adds **`currency`**, option **`con_id`** |
| `src/greeks.py` | **`reqMktData`** batch + **`modelGreeks`** / BS fallback |
| `src/metrics.py` | Concentration, DTE, hedge ratios, crash Δ–Γ matrix, portfolio summary (theta burn, options book %, …) |
| `src/convexity.py` | Tail scenarios from **realized vol**, convexity ratios, vol edge, deterministic **Taleb score**, signals |
| `src/ib_service.py` | Singleton-ish IB handle, orchestrates pipeline + **realized vol cache** + historical fetch fixes |
| `dashboard/app.py` | Overview strip, collapsible concentration heatmap, hedge table, crash matrix, convexity table, raw position tables |

---

## Configuration Highlights (`.env`)

Typical knobs (exact names in `src/config.py`):

- **`IB_HOST` / `IB_PORT` / `IB_CLIENT_ID`** — must match TWS **Global Configuration → API → Socket port** (e.g. paper often **7497**, live **7496**).
- **`IB_ACCOUNTS`** — comma-separated; first account used at connect; others get **`reqAccountUpdates`**.
- **`GREEKS_USE_IB`** — use streaming IB Greeks vs BS-only path.
- **`MAX_OPTIONS_GREEKS`** — cap IB Greeks rows if needed for debugging.
- **`CRASH_SCENARIOS`** — comma-separated fractions (e.g. `-0.10,-0.20,…`).

---

## Operational Constraints & Caveats

1. **TWS must listen on the configured port** with **socket clients enabled**. “Connection refused” means wrong port or API socket off — not an application bug.
2. **Market data entitlements** affect Greeks quality (e.g. US options often need **OPRA**); missing data yields BS fallback or empty fields.
3. **Historical data (`reqHistoricalData`)** drives realized vol; pacing, permissions, and symbol qualification (e.g. portfolio **`conId` + `primaryExchange`**) matter for latency and reliability.
4. **Crash matrix** is explicitly a **Δ–Γ local approximation** — no vega jump in Phase 1; tail puts can look modest at small shocks and stronger at large ones only within that model.
5. **Hedge ratio** uses **put deltas × multiplier × qty × undPrice** vs equity MV — interpret alongside convexity/crash views for tail hedges.

---

## What This Project Is Not

- Not a broker, not an order router, not a cloud service.
- Not a substitute for IBKR’s own risk systems or regulatory reporting.
- Not claiming calibrated probabilities for rare events; convexity tooling stresses **payoff structure vs premium**, not forecast accuracy.

---

## One-Line Summary

**Talebizer reads your IBKR portfolio locally, blocks trading by design, and surfaces concentration, hedge coverage, crash shocks, and Talebian-style convexity so you can reason about tail asymmetry and discipline without leaving your machine.**
