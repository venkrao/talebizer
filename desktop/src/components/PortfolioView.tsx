import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ConcentrationHeatmap } from "./ConcentrationHeatmap";
import { CollapsibleSection } from "./CollapsibleSection";
import { ConvexityAnalysisPanel, optionsRowsHaveConvexity } from "./ConvexityAnalysisPanel";
import { CrashScenarioMatrix } from "./CrashScenarioMatrix";
import { HedgeCoveragePanel } from "./HedgeCoveragePanel";
import { PortfolioOverview } from "./PortfolioOverview";
import { PositionsTables } from "./PositionsTables";
import { apiGet, apiPostJson } from "../api/client";
import type {
  ChatCapabilitiesResponse,
  ChatMessageResponse,
  PortfolioFrameResponse,
  PortfolioRefreshResponse,
  PortfolioSummaryResponse,
} from "../api/types";

export function PortfolioView() {
  const qc = useQueryClient();
  const [chatInput, setChatInput] = useState("");
  const [chatLog, setChatLog] = useState<
    { role: "user" | "assistant"; text: string }[]
  >([]);

  const capabilitiesQ = useQuery({
    queryKey: ["chat", "capabilities"],
    queryFn: () => apiGet<ChatCapabilitiesResponse>("/chat/capabilities"),
  });

  const summaryQ = useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: () => apiGet<PortfolioSummaryResponse>("/portfolio/summary"),
    retry: false,
  });

  const snapshotReady = summaryQ.isSuccess;

  const stocksQ = useQuery({
    queryKey: ["portfolio", "stocks"],
    queryFn: () => apiGet<PortfolioFrameResponse>("/portfolio/stocks"),
    retry: false,
    enabled: snapshotReady,
  });

  const optionsQ = useQuery({
    queryKey: ["portfolio", "options"],
    queryFn: () => apiGet<PortfolioFrameResponse>("/portfolio/options"),
    retry: false,
    enabled: snapshotReady,
  });

  const hedgeQ = useQuery({
    queryKey: ["portfolio", "hedge"],
    queryFn: () => apiGet<PortfolioFrameResponse>("/portfolio/hedge"),
    retry: false,
    enabled: snapshotReady,
  });

  const crashQ = useQuery({
    queryKey: ["portfolio", "crash"],
    queryFn: () => apiGet<PortfolioFrameResponse>("/portfolio/crash"),
    retry: false,
    enabled: snapshotReady,
  });

  const refreshM = useMutation({
    mutationFn: () =>
      apiPostJson<PortfolioRefreshResponse, Record<string, never>>(
        "/portfolio/refresh",
        {},
      ),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["portfolio", "summary"] });
      await qc.invalidateQueries({ queryKey: ["portfolio", "stocks"] });
      await qc.invalidateQueries({ queryKey: ["portfolio", "options"] });
      await qc.invalidateQueries({ queryKey: ["portfolio", "hedge"] });
      await qc.invalidateQueries({ queryKey: ["portfolio", "crash"] });
      await qc.invalidateQueries({ queryKey: ["ibkr", "status"] });
    },
  });

  const chatM = useMutation({
    mutationFn: (message: string) =>
      apiPostJson<ChatMessageResponse, { message: string }>("/chat/message", {
        message,
      }),
    onSuccess: (data, message) => {
      setChatLog((prev) => [
        ...prev,
        { role: "user", text: message },
        {
          role: "assistant",
          text:
            data.final_response +
            (data.intent ? `\n\n_(intent: ${data.intent})_` : ""),
        },
      ]);
      setChatInput("");
    },
  });

  return (
    <div className="w-full px-4 py-8 pb-24 sm:px-6 lg:px-8 lg:pb-10">
      <header className="mb-8 border-b border-zinc-800 pb-6">
        <p className="text-xs font-medium uppercase tracking-widest text-emerald-500">
          Portfolio
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-white">
          Talebizer Desktop
        </h1>
        <p className="mt-2 max-w-xl text-sm text-zinc-400">
          Live snapshot from Interactive Brokers — refresh to update positions and
          Greeks. Connection details and Ollama live under{" "}
          <span className="text-zinc-300">System</span>.
        </p>
        <button
          type="button"
          disabled={refreshM.isPending}
          className="mt-4 rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
          onClick={() => refreshM.mutate()}
        >
          {refreshM.isPending ? "Refreshing…" : "Refresh portfolio (IBKR)"}
        </button>
        {refreshM.isError ? (
          <p className="mt-3 rounded border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
            {(refreshM.error as Error).message}
          </p>
        ) : null}
      </header>

      <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:gap-6 xl:gap-8">
        <main className="min-w-0 flex-1 space-y-4">
          <CollapsibleSection title="Portfolio overview">
            {summaryQ.isLoading ? (
              <p className="text-sm text-zinc-500">Loading…</p>
            ) : summaryQ.isError ? (
              <p className="text-sm text-amber-300/90">
                {(summaryQ.error as Error).message}
                <span className="mt-2 block text-xs text-zinc-500">
                  Call “Refresh portfolio (IBKR)” if you have not loaded a snapshot yet.
                </span>
              </p>
            ) : summaryQ.data ? (
              <>
                <PortfolioOverview summary={summaryQ.data.summary} />
                <p className="mt-3 border-t border-zinc-800/80 pt-2 text-[11px] text-zinc-600">
                  Snapshot UTC (API): {summaryQ.data.refreshed_at_utc}
                </p>
              </>
            ) : null}
          </CollapsibleSection>

          {snapshotReady && stocksQ.isSuccess ? (
            <ConcentrationHeatmap stocksRows={stocksQ.data.rows} />
          ) : null}

          {snapshotReady && hedgeQ.isLoading ? (
            <CollapsibleSection title="Hedge coverage">
              <p className="text-sm text-zinc-500">Loading hedge coverage…</p>
            </CollapsibleSection>
          ) : null}
          {snapshotReady && hedgeQ.isError ? (
            <CollapsibleSection title="Hedge coverage">
              <p className="text-sm text-red-300">
                {(hedgeQ.error as Error).message}
              </p>
            </CollapsibleSection>
          ) : null}
          {snapshotReady && hedgeQ.isSuccess ? (
            <HedgeCoveragePanel hedgeRows={hedgeQ.data.rows} />
          ) : null}

          {snapshotReady && crashQ.isLoading ? (
            <CollapsibleSection title="Crash scenario matrix">
              <p className="text-sm text-zinc-500">Loading crash scenarios…</p>
            </CollapsibleSection>
          ) : null}
          {snapshotReady && crashQ.isError ? (
            <CollapsibleSection title="Crash scenario matrix">
              <p className="text-sm text-red-300">
                {(crashQ.error as Error).message}
              </p>
            </CollapsibleSection>
          ) : null}
          {snapshotReady && crashQ.isSuccess ? (
            <CrashScenarioMatrix crashRows={crashQ.data.rows} />
          ) : null}

          {snapshotReady &&
          optionsQ.isSuccess &&
          optionsRowsHaveConvexity(optionsQ.data.rows) ? (
            <ConvexityAnalysisPanel optionsRows={optionsQ.data.rows} />
          ) : null}

          {summaryQ.isSuccess ? (
            <PositionsTables stocksQ={stocksQ} optionsQ={optionsQ} />
          ) : null}
        </main>

        <aside
          className={
            "w-full shrink-0 lg:w-[22rem] xl:w-96 " +
            "lg:sticky lg:top-4 lg:self-start " +
            "flex flex-col overflow-hidden rounded-xl border border-zinc-700/90 bg-zinc-900/90 shadow-xl shadow-black/30 " +
            "lg:max-h-[calc(100dvh-5.5rem)]"
          }
          aria-label="Portfolio chat"
        >
          <div className="shrink-0 border-b border-zinc-800 px-4 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
              Portfolio chat
            </h2>
            <p className="mt-1 text-[11px] leading-snug text-zinc-500">
              Read-only · answers use your current IBKR snapshot
            </p>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
            {capabilitiesQ.data ? (
              <details className="shrink-0 rounded-md bg-black/25 p-2 text-xs text-zinc-400">
                <summary className="cursor-pointer text-zinc-300">
                  Examples ({capabilitiesQ.data.intents.length} intents)
                </summary>
                <ul className="mt-2 max-h-28 list-inside list-disc space-y-1 overflow-y-auto">
                  {capabilitiesQ.data.examples.map((ex) => (
                    <li key={ex}>{ex}</li>
                  ))}
                </ul>
              </details>
            ) : capabilitiesQ.isError ? (
              <p className="shrink-0 text-xs text-red-400">
                {(capabilitiesQ.error as Error).message}
              </p>
            ) : (
              <p className="shrink-0 text-xs text-zinc-500">Loading capabilities…</p>
            )}

            <div className="min-h-[12rem] flex-1 overflow-y-auto rounded-md bg-black/35 p-2 lg:min-h-0">
              {chatLog.length === 0 ? (
                <p className="text-xs text-zinc-500">No messages yet.</p>
              ) : (
                chatLog.map((m, i) => (
                  <div
                    key={`${i}-${m.role}`}
                    className={`mb-2 rounded px-2 py-1.5 text-xs last:mb-0 ${
                      m.role === "user"
                        ? "ml-4 bg-emerald-950/55 text-emerald-100"
                        : "mr-4 bg-zinc-800/90 text-zinc-200"
                    }`}
                  >
                    <span className="font-semibold text-zinc-500">
                      {m.role === "user" ? "You" : "Assistant"}
                    </span>
                    <div className="mt-1 whitespace-pre-wrap">{m.text}</div>
                  </div>
                ))
              )}
            </div>

            {chatM.isError ? (
              <p className="shrink-0 text-sm text-red-400">
                {(chatM.error as Error).message}
              </p>
            ) : null}

            <form
              className="shrink-0 border-t border-zinc-800 pt-3"
              onSubmit={(e) => {
                e.preventDefault();
                const t = chatInput.trim();
                if (!t || chatM.isPending) return;
                chatM.mutate(t);
              }}
            >
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  className="min-w-0 flex-1 rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-700 focus:outline-none"
                  placeholder="Ask about the portfolio…"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={chatM.isPending}
                />
                <button
                  type="submit"
                  disabled={chatM.isPending || !chatInput.trim()}
                  className="shrink-0 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-40"
                >
                  Send
                </button>
              </div>
            </form>
          </div>
        </aside>
      </div>
    </div>
  );
}
