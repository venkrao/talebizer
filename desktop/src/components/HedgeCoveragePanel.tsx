import { fmtCurrency } from "../lib/formatCurrency";
import { CollapsibleSection } from "./CollapsibleSection";

const STATUS_ICON: Record<string, string> = {
  hedged: "✅ Hedged",
  partial: "🟡 Partial",
  light: "⚠️ Light",
  unhedged: "❌ Unhedged",
};

function truthyHighRisk(v: unknown): boolean {
  return v === true || v === 1 || v === "true";
}

function fmtOptDelta(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n) || n <= 0) return "—";
  return fmtCurrency(n, 0);
}

function fmtHedgeRatio(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtPuts(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n) || n <= 0) return "—";
  return String(Math.round(n));
}

/** §8.3 — Hedge coverage table + metrics (Python `hedge_df` / IB service). */
export function HedgeCoveragePanel({
  hedgeRows,
}: {
  hedgeRows: Record<string, unknown>[];
}) {
  if (hedgeRows.length === 0) return null;

  const nTotal = hedgeRows.length;
  const nUnhedged = hedgeRows.filter(
    (r) => String(r.status ?? "") === "unhedged",
  ).length;
  const nHighRisk = hedgeRows.filter((r) => truthyHighRisk(r.high_risk)).length;

  const tableRows = hedgeRows.map((r) => {
    const status = String(r.status ?? "");
    const statusLabel = STATUS_ICON[status] ?? status;
    return {
      Symbol: String(r.symbol ?? ""),
      "Equity Value": fmtCurrency(r.equity_value ?? 0, 0),
      "Weight %": `${Number(r.weight_pct ?? 0).toFixed(1)}%`,
      Puts: fmtPuts(r.n_puts),
      "Opt Δ$": fmtOptDelta(r.option_delta_dollars),
      "Hedge Ratio": fmtHedgeRatio(r.hedge_ratio),
      Status: statusLabel,
      "⚠": truthyHighRisk(r.high_risk) ? "HIGH RISK" : "",
    };
  });

  const columns = [
    "Symbol",
    "Equity Value",
    "Weight %",
    "Puts",
    "Opt Δ$",
    "Hedge Ratio",
    "Status",
    "⚠",
  ] as const;

  return (
    <CollapsibleSection title="Hedge coverage">
      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Stocks
          </div>
          <div className="mt-1 text-xl font-semibold tabular-nums text-zinc-50">
            {nTotal}
          </div>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Unhedged
          </div>
          <div className="mt-1 text-xl font-semibold tabular-nums text-zinc-50">
            {nUnhedged}
          </div>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            High risk (&gt;10% weight, unhedged)
          </div>
          <div className="mt-1 text-xl font-semibold tabular-nums text-zinc-50">
            {nHighRisk}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-zinc-800">
        <table className="w-max min-w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-950/80">
              {columns.map((c) => (
                <th
                  key={c}
                  scope="col"
                  className="whitespace-nowrap px-2 py-2 font-semibold text-zinc-400"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, ri) => (
              <tr
                key={`${row.Symbol}-${ri}`}
                className="border-b border-zinc-800/70 odd:bg-zinc-950/40"
              >
                {columns.map((c) => (
                  <td
                    key={c}
                    className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-200 tabular-nums"
                  >
                    {row[c as keyof typeof row]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] text-zinc-500">
        Hedge Ratio = option delta-dollars / equity market value · ✅ &gt; 50% · 🟡
        25–50% · ⚠️ 10–25% · ❌ &lt; 10%
      </p>
    </CollapsibleSection>
  );
}
