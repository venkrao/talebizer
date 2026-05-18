import { fmtCurrency } from "./formatCurrency";

const MONEY = new Set([
  "avg_cost",
  "cost_basis",
  "current_price",
  "market_value",
  "unrealized_pnl",
  "realized_pnl",
  "und_price",
]);

/** Dollar and numeric columns use `fmtCurrency` / simple numeric formatting. */
export function formatPositionCell(col: string, val: unknown): string {
  if (col === "dte_flag") {
    return val === null || val === undefined ? "" : String(val);
  }
  if (val === null || val === undefined) return "—";

  const n = typeof val === "number" ? val : Number(val);

  if (MONEY.has(col) && Number.isFinite(n)) {
    return fmtCurrency(n, 2);
  }
  if (col === "weight_pct" && Number.isFinite(n)) {
    return `${n.toFixed(2)}`;
  }
  if (
    (col === "delta" ||
      col === "gamma" ||
      col === "theta" ||
      col === "vega") &&
    Number.isFinite(n)
  ) {
    return n.toFixed(4);
  }
  if (col === "implied_vol" && Number.isFinite(n)) {
    return n.toFixed(4);
  }
  if (col === "strike" && Number.isFinite(n)) {
    return String(n);
  }
  if (col === "dte" && Number.isFinite(n)) {
    return String(Math.round(n));
  }
  if (typeof val === "number" && Number.isFinite(val)) {
    return Number.isInteger(val) ? String(val) : String(val);
  }
  return String(val);
}
