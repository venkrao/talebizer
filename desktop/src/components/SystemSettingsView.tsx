import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, Row } from "./Card";
import { apiGet, getApiBase } from "../api/client";
import type {
  EnvironmentResponse,
  IBKRStatusResponse,
  LLMStatusResponse,
} from "../api/types";

export function SystemSettingsView({ active }: { active: boolean }) {
  const qc = useQueryClient();

  const envQ = useQuery({
    queryKey: ["environment"],
    queryFn: () => apiGet<EnvironmentResponse>("/environment"),
    enabled: active,
  });

  const ibkrQ = useQuery({
    queryKey: ["ibkr", "status"],
    queryFn: () => apiGet<IBKRStatusResponse>("/ibkr/status"),
    enabled: active,
  });

  const llmQ = useQuery({
    queryKey: ["llm", "status"],
    queryFn: () => apiGet<LLMStatusResponse>("/llm/status"),
    enabled: active,
  });

  const reloadStatus = () => {
    void qc.invalidateQueries({ queryKey: ["environment"] });
    void qc.invalidateQueries({ queryKey: ["ibkr", "status"] });
    void qc.invalidateQueries({ queryKey: ["llm", "status"] });
  };

  return (
    <div className="w-full px-4 py-8 pb-24 sm:px-6 lg:px-8">
      <header className="mb-8 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
          Configuration & diagnostics
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-zinc-900 dark:text-white">
          System & connection
        </h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          API base:{" "}
          <code className="rounded bg-zinc-200 px-1.5 py-0.5 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
            {getApiBase()}
          </code>
        </p>
        <button
          type="button"
          className="mt-4 rounded-md bg-zinc-200 px-3 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-300 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700"
          onClick={() => reloadStatus()}
        >
          Reload diagnostics
        </button>
      </header>

      <div className="grid gap-4">
        <Card title="Environment">
          {!active ? null : envQ.isLoading ? (
            <p className="text-zinc-500">Loading…</p>
          ) : envQ.isError ? (
            <p className="text-red-600 dark:text-red-400">
              {(envQ.error as Error).message}
            </p>
          ) : envQ.data ? (
            <>
              <Row label="Backend" value={envQ.data.backend} />
              <Row label="Python" value={envQ.data.python_version} />
              <Row label="Platform" value={envQ.data.platform} />
              <Row label="IB socket" value={`${envQ.data.ib_host}:${envQ.data.ib_port}`} />
              <Row
                label="Ollama"
                value={
                  envQ.data.chat_ollama_enabled
                    ? `${envQ.data.chat_ollama_model} @ ${envQ.data.chat_ollama_host}`
                    : "disabled"
                }
              />
            </>
          ) : null}
        </Card>

        <Card title="IBKR snapshot">
          {!active ? null : ibkrQ.isLoading ? (
            <p className="text-zinc-500">Loading…</p>
          ) : ibkrQ.isError ? (
            <p className="text-red-600 dark:text-red-400">
              {(ibkrQ.error as Error).message}
            </p>
          ) : ibkrQ.data ? (
            <>
              <Row
                label="Loaded"
                value={ibkrQ.data.snapshot_loaded ? "yes" : "no"}
              />
              <Row label="Last refresh (UTC)" value={ibkrQ.data.last_refresh_utc ?? "—"} />
              <Row
                label="Last error"
                value={ibkrQ.data.last_refresh_error ?? "—"}
              />
              <Row
                label="Configured host"
                value={`${ibkrQ.data.ib_host}:${ibkrQ.data.ib_port}`}
              />
            </>
          ) : null}
        </Card>

        <Card title="LLM / Ollama">
          {!active ? null : llmQ.isLoading ? (
            <p className="text-zinc-500">Loading…</p>
          ) : llmQ.isError ? (
            <p className="text-red-600 dark:text-red-400">
              {(llmQ.error as Error).message}
            </p>
          ) : llmQ.data ? (
            <>
              <Row label="Enabled" value={String(llmQ.data.ollama_enabled)} />
              <Row label="Reachable" value={String(llmQ.data.reachable)} />
              <Row label="Host" value={llmQ.data.ollama_host} />
              <Row
                label="Models"
                value={
                  llmQ.data.installed_models.length
                    ? llmQ.data.installed_models.join(", ")
                    : "(none listed)"
                }
              />
              {llmQ.data.detail ? (
                <Row label="Detail" value={llmQ.data.detail} />
              ) : null}
            </>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
