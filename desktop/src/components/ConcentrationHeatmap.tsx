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
import { CollapsibleSection } from "./CollapsibleSection";

/** Matches `FLAG_COLOURS` / `concentration_flag` keys from the Python metrics pipeline. */
const FLAG_HEX: Record<string, string> = {
  green: "#22c55e",
  amber: "#f59e0b",
  red: "#ef4444",
};

function hexForFlag(flag: unknown): string {
  const k = String(flag ?? "green").toLowerCase();
  return FLAG_HEX[k] ?? FLAG_HEX.green;
}

export type ConcChartRow = {
  symbol: string;
  weight_pct: number;
  concentration_flag: string;
};

export function buildConcentrationRows(
  stocksRows: Record<string, unknown>[],
): ConcChartRow[] {
  const out: ConcChartRow[] = [];
  for (const r of stocksRows) {
    const w = Number(r.weight_pct);
    if (!Number.isFinite(w)) continue;
    out.push({
      symbol: String(r.symbol ?? ""),
      weight_pct: w,
      concentration_flag: String(r.concentration_flag ?? "green"),
    });
  }
  out.sort((a, b) => a.weight_pct - b.weight_pct);
  return out;
}

/** §8.2 — horizontal concentration bars (Recharts). */
export function ConcentrationHeatmap({
  stocksRows,
}: {
  stocksRows: Record<string, unknown>[];
}) {
  const chartData = useMemo(
    () => buildConcentrationRows(stocksRows),
    [stocksRows],
  );

  const xMax = useMemo(() => {
    const maxW =
      chartData.length === 0
        ? 0
        : Math.max(...chartData.map((d) => d.weight_pct));
    return Math.max(maxW * 1.15, 30);
  }, [chartData]);

  const chartHeight = Math.max(250, chartData.length * 38);

  if (chartData.length === 0) return null;

  return (
    <CollapsibleSection title="Concentration heatmap">
      <div style={{ width: "100%", height: chartHeight }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={chartData}
                margin={{ left: 4, right: 56, top: 8, bottom: 8 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#27272a"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  domain={[0, xMax]}
                  stroke="#71717a"
                  tick={{ fill: "#a1a1aa", fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                  label={{
                    value: "Portfolio Weight (%)",
                    position: "insideBottom",
                    offset: -4,
                    fill: "#71717a",
                    fontSize: 11,
                  }}
                />
                <YAxis
                  type="category"
                  dataKey="symbol"
                  width={72}
                  stroke="#71717a"
                  tick={{ fill: "#a1a1aa", fontSize: 11 }}
                />
                <Tooltip
                  cursor={{ fill: "rgba(39,39,42,0.35)" }}
                  contentStyle={{
                    backgroundColor: "#18181b",
                    border: "1px solid #3f3f46",
                    borderRadius: "6px",
                    fontSize: "12px",
                  }}
                  labelStyle={{ color: "#e4e4e7" }}
                  formatter={(value: number) => [`${value.toFixed(2)}%`, "Weight"]}
                />
                <ReferenceLine
                  x={10}
                  stroke="rgba(150,150,150,0.5)"
                  strokeDasharray="4 4"
                  label={{
                    value: "10%",
                    position: "top",
                    fill: "#71717a",
                    fontSize: 10,
                  }}
                />
                <ReferenceLine
                  x={25}
                  stroke="rgba(150,150,150,0.5)"
                  strokeDasharray="4 4"
                  label={{
                    value: "25%",
                    position: "top",
                    fill: "#71717a",
                    fontSize: 10,
                  }}
                />
                <Bar dataKey="weight_pct" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${entry.symbol}-${index}`}
                      fill={hexForFlag(entry.concentration_flag)}
                    />
                  ))}
                  <LabelList
                    dataKey="weight_pct"
                    position="right"
                    fill="#d4d4d8"
                    fontSize={11}
                    formatter={(v: number) => `${Number(v).toFixed(1)}%`}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

      <p className="mt-3 text-[11px] text-zinc-500">
        🟢 &lt; 10% · 🟡 10–25% · 🔴 &gt; 25%
      </p>
    </CollapsibleSection>
  );
}
