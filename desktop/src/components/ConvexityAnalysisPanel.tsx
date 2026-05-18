import { useMemo } from "react";
import { CollapsibleSection } from "./CollapsibleSection";

/** Matches convexity `signal` labels from `src/convexity.py` / options frame. */
const SIGNAL_ICON: Record<string, string> = {
  HOLD: "✅ HOLD",
  MONITOR: "🔍 MONITOR",
  "MONITOR — vol edge offsets low convexity": "🟡 MONITOR — high vol edge",
  "SELL — expiring soon": "🔴 SELL — expiring soon",
  "SELL — low convexity": "🔴 SELL — low convexity",
};

function scoreColour(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#86efac";
  if (score >= 30) return "#f59e0b";
  return "#ef4444";
}

function volEdgeColour(val: number): string | undefined {
  if (val > 0) return "#22c55e";
  if (val < -5) return "#ef4444";
  return undefined;
}

function fmtPctFromUnitFraction(v: unknown, decimals = 1): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(decimals)}`;
}

function fmtConv(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(1);
}

function fmtScore(v: unknown): string {
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "—";
  return String(Math.round(n));
}

function signalLabel(raw: unknown): string {
  const s = String(raw ?? "");
  return SIGNAL_ICON[s] ?? s;
}

export function optionsRowsHaveConvexity(rows: Record<string, unknown>[]): boolean {
  return rows.length > 0 && rows.some((r) => Object.prototype.hasOwnProperty.call(r, "taleb_score"));
}

type ConvexityDisplayRow = Record<string, string | number>;

function buildDisplayRows(rows: Record<string, unknown>[]): ConvexityDisplayRow[] {
  const mapped = rows.map((r) => {
    const volEdgePct = (() => {
      const n = Number(r.vol_edge);
      return Number.isFinite(n) ? n * 100 : NaN;
    })();
    return {
      Symbol: String(r.symbol ?? ""),
      "P/C": String(r.put_call ?? ""),
      Strike: Number(r.strike),
      Expiry: String(r.expiry ?? ""),
      DTE: Number(r.dte),
      Price: Number(r.current_price),
      Intrinsic: Number(r.intrinsic_value),
      "Time Val": Number(r.time_value),
      IV: Number(r.implied_vol),
      "RV (30d)": Number(r.realized_vol),
      "Vol Edge": volEdgePct,
      "2σ Conv": Number(r.convexity_2s),
      "4σ Conv": Number(r.convexity_4s),
      "6σ Conv": Number(r.convexity_6s),
      Score: Number(r.taleb_score),
      SignalRaw: String(r.signal ?? ""),
      _volEdgeNum: volEdgePct,
    };
  });

  mapped.sort((a, b) => {
    const sa = a.Score;
    const sb = b.Score;
    const fa = Number.isFinite(sa) ? sa : -Infinity;
    const fb = Number.isFinite(sb) ? sb : -Infinity;
    return fb - fa;
  });

  return mapped.map((m) => ({
    Symbol: m.Symbol,
    "P/C": m["P/C"],
    Strike: Number.isFinite(m.Strike) ? m.Strike.toFixed(2) : "—",
    Expiry: m.Expiry,
    DTE: Number.isFinite(m.DTE) ? String(Math.round(m.DTE)) : "—",
    Price: Number.isFinite(m.Price) ? m.Price.toFixed(2) : "—",
    Intrinsic: Number.isFinite(m.Intrinsic) ? m.Intrinsic.toFixed(2) : "—",
    "Time Val": Number.isFinite(m["Time Val"]) ? m["Time Val"].toFixed(2) : "—",
    IV: fmtPctFromUnitFraction(m.IV, 1),
    "RV (30d)": fmtPctFromUnitFraction(m["RV (30d)"], 1),
    "Vol Edge": Number.isFinite(m["Vol Edge"]) ? m["Vol Edge"].toFixed(1) : "—",
    "2σ Conv": fmtConv(m["2σ Conv"]),
    "4σ Conv": fmtConv(m["4σ Conv"]),
    "6σ Conv": fmtConv(m["6σ Conv"]),
    Score: fmtScore(m.Score),
    Signal: signalLabel(m.SignalRaw),
    _scoreNum: Number.isFinite(m.Score) ? m.Score : NaN,
    _volEdgeNum: m._volEdgeNum,
  })) as ConvexityDisplayRow[];
}

const COLUMNS = [
  "Symbol",
  "P/C",
  "Strike",
  "Expiry",
  "DTE",
  "Price",
  "Intrinsic",
  "Time Val",
  "IV",
  "RV (30d)",
  "Vol Edge",
  "2σ Conv",
  "4σ Conv",
  "6σ Conv",
  "Score",
  "Signal",
] as const;

/** Convexity analysis table — parity with options frame + `compute_convexity_metrics`. */
export function ConvexityAnalysisPanel({
  optionsRows,
}: {
  optionsRows: Record<string, unknown>[];
}) {
  const hasRv = useMemo(
    () =>
      optionsRows.some((r) => {
        const v = r.realized_vol;
        if (v === null || v === undefined) return false;
        return Number.isFinite(Number(v));
      }),
    [optionsRows],
  );

  const { nHold, nSell } = useMemo(() => {
    let hold = 0;
    let sell = 0;
    for (const r of optionsRows) {
      const s = String(r.signal ?? "");
      if (s === "HOLD") hold += 1;
      if (s.startsWith("SELL")) sell += 1;
    }
    return { nHold: hold, nSell: sell };
  }, [optionsRows]);

  const tableRows = useMemo(() => buildDisplayRows(optionsRows), [optionsRows]);

  return (
    <CollapsibleSection title="Convexity analysis">
      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Positions
          </div>
          <div className="mt-1 text-xl font-semibold tabular-nums text-zinc-50">
            {optionsRows.length}
          </div>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            HOLD signals
          </div>
          <div className="mt-1 text-xl font-semibold tabular-nums text-zinc-50">{nHold}</div>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            SELL signals
          </div>
          <div className="mt-1 text-xl font-semibold tabular-nums text-zinc-50">{nSell}</div>
        </div>
      </div>

      {!hasRv ? (
        <div className="mb-4 rounded-md border border-sky-900/50 bg-sky-950/25 px-3 py-2 text-sm text-sky-100/95">
          Realized volatility data unavailable — convexity ratios require it. Ensure TWS has
          market data history enabled for your option underlyings.
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-zinc-800">
        <table className="w-max min-w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-950/80">
              {COLUMNS.map((c) => (
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
            {tableRows.map((row, ri) => {
              const scoreNum = row._scoreNum as number;
              const volEdgeNum = row._volEdgeNum as number;
              const veCol = Number.isFinite(volEdgeNum) ? volEdgeColour(volEdgeNum) : undefined;
              return (
                <tr
                  key={`${row.Symbol}-${ri}`}
                  className="border-b border-zinc-800/70 odd:bg-zinc-950/40"
                >
                  {COLUMNS.map((col) => {
                    const cell = row[col];
                    const isScore = col === "Score";
                    const isVolEdge = col === "Vol Edge";
                    let colour: string | undefined;
                    if (isScore && Number.isFinite(scoreNum)) colour = scoreColour(scoreNum);
                    if (isVolEdge && veCol) colour = veCol;
                    return (
                      <td
                        key={col}
                        className={`whitespace-nowrap px-2 py-1.5 font-mono text-zinc-200 tabular-nums ${
                          isScore ? "text-sm font-bold" : ""
                        }`}
                        style={colour ? { color: colour } : undefined}
                      >
                        {String(cell ?? "")}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-[11px] text-zinc-500">
        <span className="font-semibold text-zinc-400">Taleb Score</span> = Convexity (0–50) +
        Vol Edge (0–30) + Time (0–20) ·{" "}
        <span className="font-semibold text-zinc-400">4σ Conv</span> = tail payoff / premium at a
        4σ move using realised vol ·{" "}
        <span className="font-semibold text-zinc-400">Vol Edge</span> = RV − IV (positive =
        options may be underpriced)
      </p>
    </CollapsibleSection>
  );
}
