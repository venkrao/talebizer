export type ChartPalette = {
  grid: string;
  axisStroke: string;
  tickFill: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipLabel: string;
  cursorFill: string;
  axisLabelFill: string;
  barLabelFill: string;
};

export const chartPalettes: Record<"light" | "dark", ChartPalette> = {
  dark: {
    grid: "#27272a",
    axisStroke: "#71717a",
    tickFill: "#a1a1aa",
    tooltipBg: "#18181b",
    tooltipBorder: "#3f3f46",
    tooltipLabel: "#e4e4e7",
    cursorFill: "rgba(39,39,42,0.35)",
    axisLabelFill: "#71717a",
    barLabelFill: "#d4d4d8",
  },
  light: {
    grid: "#e4e4e7",
    axisStroke: "#a1a1aa",
    tickFill: "#52525b",
    tooltipBg: "#ffffff",
    tooltipBorder: "#d4d4d8",
    tooltipLabel: "#18181b",
    cursorFill: "rgba(161,161,170,0.2)",
    axisLabelFill: "#71717a",
    barLabelFill: "#3f3f46",
  },
};
