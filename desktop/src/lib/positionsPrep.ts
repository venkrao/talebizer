import { OPTION_COLS, STOCK_COLS } from "./positionsColumns";

function rowHasCol(rows: Record<string, unknown>[], col: string): boolean {
  return rows.some((r) => Object.prototype.hasOwnProperty.call(r, col));
}

/** Column presence + sort-by-symbol for raw frames (aligned with backend position tables). */
export function presentStockColumns(rows: Record<string, unknown>[]): string[] {
  if (rows.length === 0) return [...STOCK_COLS];
  return STOCK_COLS.filter((c) => rowHasCol(rows, c));
}

export function sortRowsBySymbol(
  rows: Record<string, unknown>[],
): Record<string, unknown>[] {
  return [...rows].sort((a, b) =>
    String(a.symbol ?? "").localeCompare(String(b.symbol ?? ""), undefined, {
      sensitivity: "base",
    }),
  );
}

export function presentOptionColumns(rows: Record<string, unknown>[]): string[] {
  const base =
    rows.length === 0
      ? [...OPTION_COLS]
      : OPTION_COLS.filter((c) => rowHasCol(rows, c));

  const needsFlag =
    base.includes("dte") &&
    rows.length > 0 &&
    rowHasCol(rows, "expiry_flag");

  if (!needsFlag) return base;

  const i = base.indexOf("dte");
  return [...base.slice(0, i + 1), "dte_flag", ...base.slice(i + 1)];
}

export function dteFlagFromExpiry(expiryFlag: unknown): string {
  if (expiryFlag === "urgent") return "⚠️";
  if (expiryFlag === "expired") return "🕐";
  return "";
}
