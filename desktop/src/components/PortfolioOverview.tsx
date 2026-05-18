import { fmtCurrency } from "../lib/formatCurrency";

function num(s: Record<string, unknown>, key: string): number | null {
  const v = s[key];
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

function str(s: Record<string, unknown>, key: string): string | undefined {
  const v = s[key];
  return typeof v === "string" ? v : undefined;
}

function MetricTile({
  label,
  value,
  delta,
  deltaClassName,
  title,
}: {
  label: string;
  value: string;
  delta?: string;
  deltaClassName?: string;
  title?: string;
}) {
  return (
    <div
      className="rounded-lg border border-zinc-800/90 bg-zinc-950/50 px-3 py-3"
      title={title}
    >
      <div className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums text-zinc-50">
        {value}
      </div>
      {delta ? (
        <div
          className={`mt-0.5 text-xs font-medium tabular-nums ${deltaClassName ?? "text-zinc-400"}`}
        >
          {delta}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Portfolio overview metrics strip — driven by `/portfolio/summary` (Python `summary` dict).
 */
export function PortfolioOverview({
  summary,
}: {
  summary: Record<string, unknown>;
}) {
  const totalPortfolio = num(summary, "total_portfolio_value");
  const equity = num(summary, "total_equity_value");
  const optCost = num(summary, "total_options_cost");
  const optMkt = num(summary, "total_options_mkt_value");
  const optUpnl = num(summary, "options_unrealized_pnl");
  const bookPct = num(summary, "options_book_pct");
  const bookFlag = str(summary, "options_book_flag");
  const nExp90 = num(summary, "n_options_expiring_90d");
  const earliestDte = num(summary, "earliest_dte");
  const theta = num(summary, "daily_theta_burn");

  let bookLabel =
    bookPct !== null ? `${bookPct.toFixed(2)}%` : "—";
  if (bookFlag === "warning") bookLabel += " ⚠️";

  let dteLabel =
    earliestDte !== null ? `${Math.round(earliestDte)}d` : "—";
  if (earliestDte !== null && earliestDte < 90) dteLabel += " ⚠️";

  const nearestTitle =
    nExp90 !== null
      ? `${nExp90} option(s) expiring within 90 days.`
      : "Nearest option expiry (days).";

  const optionsBookTitle =
    "Target: 1–5%. Flag if > 7%.";

  let deltaLine: string | undefined;
  let deltaClass = "text-zinc-400";
  if (optUpnl !== null) {
    deltaLine = fmtCurrency(optUpnl, 0);
    if (optUpnl > 0) deltaClass = "text-emerald-400";
    else if (optUpnl < 0) deltaClass = "text-red-400";
  }

  const localRefresh = new Date();
  const lastRefreshedStr = localRefresh.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (
    <div>
      <h2 className="mb-3 text-base font-semibold text-zinc-100">
        Portfolio Overview
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricTile
          label="Total Portfolio"
          value={fmtCurrency(totalPortfolio, 0)}
        />
        <MetricTile label="Equity Value" value={fmtCurrency(equity, 0)} />
        <MetricTile
          label="Options Cost Basis"
          value={fmtCurrency(optCost, 0)}
        />
        <MetricTile
          label="Options Mkt Value"
          value={fmtCurrency(optMkt, 0)}
          delta={deltaLine}
          deltaClassName={deltaClass}
        />
        <MetricTile
          label="Options Book %"
          value={bookLabel}
          title={optionsBookTitle}
        />
        <MetricTile
          label="Nearest Expiry"
          value={dteLabel}
          title={nearestTitle}
        />
      </div>

      {theta !== null ? (
        <p className="mt-3 text-xs text-zinc-500">
          <span aria-hidden>📉</span> Daily theta burn:{" "}
          <span className="font-semibold text-zinc-300">
            {fmtCurrency(theta, 2)}
          </span>{" "}
          (cost of holding all options for one more day)
        </p>
      ) : null}

      <p className="mt-2 text-xs text-zinc-500">
        Last refreshed: {lastRefreshedStr}
      </p>
    </div>
  );
}
