function apiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL;
  return (typeof raw === "string" && raw.length > 0
    ? raw
    : "http://127.0.0.1:8765"
  ).replace(/\/$/, "");
}

function formatError(status: number, text: string): string {
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    if (j.detail === undefined) return `${status}: ${text}`;
    if (typeof j.detail === "string") return `${status}: ${j.detail}`;
    return `${status}: ${JSON.stringify(j.detail)}`;
  } catch {
    return `${status}: ${text || "(empty body)"}`;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`);
  const text = await res.text();
  if (!res.ok) throw new Error(formatError(res.status, text));
  return (text ? JSON.parse(text) : {}) as T;
}

export async function apiPostJson<T, B extends object>(
  path: string,
  body: B,
): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(formatError(res.status, text));
  return (text ? JSON.parse(text) : {}) as T;
}

/** Small probe so we can show the configured API URL in the shell. */
export function getApiBase(): string {
  return apiBase();
}
