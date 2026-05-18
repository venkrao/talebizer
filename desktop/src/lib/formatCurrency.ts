/** Currency formatting for desktop tables (USD, grouped thousands). */

export function fmtCurrency(val: unknown, decimals = 0): string {
  const n = typeof val === "number" ? val : Number(val);
  if (!Number.isFinite(n)) return "—";
  return `$${n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}
