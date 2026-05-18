/** Canonical stock/option column lists for raw position tables (backend frame keys). */

export const STOCK_COLS = [
  "symbol",
  "quantity",
  "avg_cost",
  "cost_basis",
  "current_price",
  "market_value",
  "weight_pct",
  "unrealized_pnl",
  "realized_pnl",
] as const;

export const OPTION_COLS = [
  "symbol",
  "underlying",
  "put_call",
  "strike",
  "expiry",
  "dte",
  "multiplier",
  "quantity",
  "avg_cost",
  "cost_basis",
  "current_price",
  "market_value",
  "unrealized_pnl",
  "realized_pnl",
  "delta",
  "gamma",
  "theta",
  "vega",
  "implied_vol",
  "und_price",
  "greeks_source",
] as const;
