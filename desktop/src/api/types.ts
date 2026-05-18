/** Mirrors backend/schemas.py (subset used by UI). */

export interface EnvironmentResponse {
  python_version: string;
  platform: string;
  backend: string;
  ib_host: string;
  ib_port: number;
  chat_ollama_enabled: boolean;
  chat_ollama_host: string;
  chat_ollama_model: string;
}

export interface IBKRStatusResponse {
  snapshot_loaded: boolean;
  last_refresh_utc: string | null;
  last_refresh_error: string | null;
  ib_host: string;
  ib_port: number;
}

export interface LLMStatusResponse {
  ollama_enabled: boolean;
  ollama_host: string;
  reachable: boolean;
  installed_models: string[];
  detail: string | null;
}

export interface PortfolioRefreshResponse {
  refreshed_at_utc: string;
  n_stocks: number;
  n_options: number;
}

export interface PortfolioSummaryResponse {
  refreshed_at_utc: string;
  summary: Record<string, unknown>;
}

export interface PortfolioFrameResponse {
  refreshed_at_utc: string;
  rows: Record<string, unknown>[];
}

export interface ChatCapabilitiesResponse {
  read_only: boolean;
  intents: string[];
  examples: string[];
}

export interface ChatMessageResponse {
  intent: string | null;
  final_response: string;
  supporting_structured_payload: Record<string, string | null | undefined> | null;
  limitation_note: string | null;
  snapshot_timestamp: string | null;
}
