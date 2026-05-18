import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtCurrency } from "../lib/formatCurrency";
import { chartPalettes } from "../theme/chartPalette";
import { useTheme } from "../theme/ThemeContext";
import { CollapsibleSection } from "./CollapsibleSection";

type CrashRow = {
  scenario_pct: number;
  stock_pnl: number;
  options_pnl: number;
  net_pnl: number;
  net_pct: number;
};

function parseCrashRows(rows: Record<string, unknown>[]): CrashRow[] {
  const out: CrashRow[] = [];
  for (const r of rows) {
    const scenario_pct = Number(r.scenario_pct);
    const stock_pnl = Number(r.stock_pnl);
    const options_pnl = Number(r.options_pnl);
    const net_pnl = Number(r.net_pnl);
    const net_pct = Number(r.net_pct);
    if (!Number.isFinite(scenario_pct)) continue;
    out.push({
      scenario_pct,
      stock_pnl: Number.isFinite(stock_pnl) ? stock_pnl : 0,
      options_pnl: Number.isFinite(options_pnl) ? options_pnl : 0,
      net_pnl: Number.isFinite(net_pnl) ? net_pnl : 0,
      net_pct: Number.isFinite(net_pct) ? net_pct : 0,
    });
  }
  return out;
}

function scenarioLabel(pct: number): string {
  return `${Math.round(pct * 100)}%`;
}

/** Net % cell colour for crash scenarios (same rule as former Streamlit styling). */
function netPctColor(netPct: number): string {
  if (netPct >= 0) return "#22c55e";
  const intensity = Math.min(Math.round((Math.abs(netPct) / 50) * 200) + 55, 255);
  return `rgb(${intensity}, 50, 50)`;
}

/** §8.4 — Crash scenario table + net P&L bar chart. */
export function CrashScenarioMatrix({
  crashRows,
}: {
  crashRows: Record<string, unknown>[];
}) {
  const { resolved } = useTheme();
  const cp = chartPalettes[resolved];

  const data = useMemo(() => parseCrashRows(crashRows), [crashRows]);

  if (data.length === 0) return null;

  const chartData = data.map((d) => ({
    scenario: scenarioLabel(d.scenario_pct),
    net_pnl: d.net_pnl,
    fill: d.net_pnl >= 0 ? "#22c55e" : "#ef4444",
  }));

  const displayCols = [
    { key: "scenario", header: "Scenario" },
    { key: "stock", header: "Stock P&L" },
    { key: "options", header: "Options P&L" },
    { key: "net", header: "Net P&L" },
    { key: "netPct", header: "Net %" },
  ] as const;

  const tableRows = data.map((d) => ({
    scenario: scenarioLabel(d.scenario_pct),
    stock: fmtCurrency(d.stock_pnl, 0),
    options: fmtCurrency(d.options_pnl, 0),
    net: fmtCurrency(d.net_pnl, 0),
    netPct: `${d.net_pct >= 0 ? "+" : ""}${d.net_pct.toFixed(2)}%`,
    netPctNum: d.net_pct,
  }));

  return (
    <CollapsibleSection title="Crash scenario matrix">
      <div className="mb-4 overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
        <table className="w-max min-w-full border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-950/80">
              {displayCols.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  className="whitespace-nowrap px-2 py-2 font-semibold text-zinc-600 dark:text-zinc-400"
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, ri) => (
              <tr
                key={`${row.scenario}-${ri}`}
                className="border-b border-zinc-200/90 odd:bg-zinc-50 dark:border-zinc-800/70 dark:odd:bg-zinc-950/40"
              >
                <td className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-800 tabular-nums dark:text-zinc-200">
                  {row.scenario}
                </td>
                <td className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-800 tabular-nums dark:text-zinc-200">
                  {row.stock}
                </td>
                <td className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-800 tabular-nums dark:text-zinc-200">
                  {row.options}
                </td>
                <td className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-800 tabular-nums dark:text-zinc-200">
                  {row.net}
                </td>
                <td
                  className="whitespace-nowrap px-2 py-1.5 font-mono text-sm font-bold tabular-nums"
                  style={{ color: netPctColor(row.netPctNum) }}
                >
                  {row.netPct}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mb-4 text-[11px] text-zinc-500">
        Options P&amp;L uses delta + gamma approximation (first-order Taylor expansion).
        Vega expansion not modelled — actual tail-option gains in extreme moves will be
        higher.
      </p>

      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ left: 8, right: 12, top: 28, bottom: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={cp.grid} vertical={false} />
            <XAxis
              dataKey="scenario"
              stroke={cp.axisStroke}
              tick={{ fill: cp.tickFill, fontSize: 11 }}
              label={{
                value: "Scenario (equity move)",
                position: "insideBottom",
                offset: -2,
                fill: cp.axisLabelFill,
                fontSize: 11,
              }}
            />
            <YAxis
              stroke={cp.axisStroke}
              tick={{ fill: cp.tickFill, fontSize: 11 }}
              tickFormatter={(v) =>
                typeof v === "number" ? `$${Math.round(v).toLocaleString("en-US")}` : String(v)
              }
              label={{
                value: "Net P&L ($)",
                angle: -90,
                position: "insideLeft",
                fill: cp.axisLabelFill,
                fontSize: 11,
              }}
            />
            <Tooltip
              cursor={{ fill: cp.cursorFill }}
              contentStyle={{
                backgroundColor: cp.tooltipBg,
                border: `1px solid ${cp.tooltipBorder}`,
                borderRadius: "6px",
                fontSize: "12px",
              }}
              labelStyle={{ color: cp.tooltipLabel }}
              formatter={(value: number) => [fmtCurrency(value, 0), "Net P&L"]}
            />
            <ReferenceLine y={0} stroke="rgba(150,150,150,0.5)" strokeDasharray="4 4" />
            <Bar dataKey="net_pnl" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${entry.scenario}-${index}`} fill={entry.fill} />
              ))}
              <LabelList
                dataKey="net_pnl"
                position="top"
                fill={cp.barLabelFill}
                fontSize={11}
                formatter={(v: number) =>
                  Number.isFinite(v) ? `$${Math.round(v).toLocaleString("en-US")}` : ""
                }
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CollapsibleSection>
  );
}
