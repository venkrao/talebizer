import type { UseQueryResult } from "@tanstack/react-query";
import type { PortfolioFrameResponse } from "../api/types";
import { formatPositionCell } from "../lib/formatPositionCell";
import {
  dteFlagFromExpiry,
  presentOptionColumns,
  presentStockColumns,
  sortRowsBySymbol,
} from "../lib/positionsPrep";
import { CollapsibleSection } from "./CollapsibleSection";

function DataTable({
  columns,
  rows,
  emptyHint,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
  emptyHint: string;
}) {
  if (columns.length === 0) {
    return <p className="text-sm text-zinc-500">{emptyHint}</p>;
  }

  return (
    <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
      <table className="w-max min-w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-950/80">
            {columns.map((c) => (
              <th
                key={c}
                scope="col"
                className="whitespace-nowrap px-2 py-2 font-semibold text-zinc-600 dark:text-zinc-400"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-2 py-6 text-center text-zinc-500"
              >
                {emptyHint}
              </td>
            </tr>
          ) : (
            rows.map((row, ri) => (
              <tr
                key={`${ri}-${String(row.symbol ?? ri)}`}
                className="border-b border-zinc-200/90 odd:bg-zinc-50 dark:border-zinc-800/70 dark:odd:bg-zinc-950/40"
              >
                {columns.map((c) => (
                  <td
                    key={c}
                    className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-800 tabular-nums dark:text-zinc-200"
                  >
                    {formatPositionCell(c, row[c])}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function Panel({
  title,
  query,
  kind,
}: {
  title: string;
  query: UseQueryResult<PortfolioFrameResponse, Error>;
  kind: "stock" | "option";
}) {
  const raw = query.data?.rows ?? [];
  const sorted = sortRowsBySymbol(raw);

  const columns =
    kind === "stock"
      ? presentStockColumns(sorted)
      : presentOptionColumns(sorted);

  const displayRows: Record<string, unknown>[] = sorted.map((r) => {
    if (kind === "option") {
      const row: Record<string, unknown> = { ...r };
      if (columns.includes("dte_flag")) {
        row.dte_flag = dteFlagFromExpiry(r.expiry_flag);
      }
      return row;
    }
    return r;
  });

  return (
    <CollapsibleSection title={title}>
      {query.isLoading ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : query.isError ? (
        <p className="text-sm text-amber-800 dark:text-amber-300/90">
          {(query.error as Error).message}
        </p>
      ) : (
        <DataTable
          columns={columns}
          rows={displayRows}
          emptyHint={
            kind === "stock" ? "No stock positions." : "No option positions."
          }
        />
      )}
      {kind === "option" && query.isSuccess ? (
        <p className="mt-2 text-[11px] text-zinc-500">
          ⚠️ = expiring within 90 days
        </p>
      ) : null}
    </CollapsibleSection>
  );
}

export function PositionsTables({
  stocksQ,
  optionsQ,
}: {
  stocksQ: UseQueryResult<PortfolioFrameResponse, Error>;
  optionsQ: UseQueryResult<PortfolioFrameResponse, Error>;
}) {
  return (
    <div className="grid grid-cols-1 gap-4">
      <Panel title="Stock Positions (STK)" query={stocksQ} kind="stock" />
      <Panel title="Option Positions (OPT)" query={optionsQ} kind="option" />
    </div>
  );
}
