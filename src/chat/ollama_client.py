"""Local Ollama HTTP API — classification + optional phrasing only."""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Optional

from .intent import ALLOWED_INTENTS

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2"


def get_chat_ollama_settings() -> tuple[bool, str, str, bool, bool]:
    """
    Returns:
        enabled, host, model, use_llm_intent_fallback, use_llm_phrasing
    """
    enabled = os.getenv("CHAT_OLLAMA_ENABLED", "true").strip().lower() == "true"
    host = os.getenv("CHAT_OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")
    model = os.getenv("CHAT_OLLAMA_MODEL", DEFAULT_MODEL).strip()
    intent_fb = os.getenv("CHAT_OLLAMA_INTENT_FALLBACK", "true").strip().lower() == "true"
    phrase = os.getenv("CHAT_OLLAMA_PHRASE", "false").strip().lower() == "true"
    return enabled, host, model, intent_fb, phrase


def list_installed_models(host: str, timeout_sec: float = 5.0) -> list[str]:
    """Return installed model names from GET /api/tags (best-effort)."""
    url = f"{host.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = data.get("models") or []
        names = []
        for m in models:
            name = (m.get("name") or "").strip()
            if name:
                names.append(name)
        return sorted(names)
    except Exception as exc:
        logger.debug("Could not list Ollama models: %s", exc)
        return []


def _post_json(
    url: str,
    payload: dict,
    timeout_sec: float = 120.0,
    *,
    log_failure: bool = True,
) -> tuple[Optional[dict], Optional[str]]:
    """
    POST JSON; return (parsed_body, error_hint).

    error_hint is set on HTTP errors so callers can log actionable guidance.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            body = ""
        hint = f"HTTP {exc.code}"
        if exc.code == 404:
            hint += (
                " — often means the **model name** is wrong or not pulled "
                "(run `ollama list`, then set CHAT_OLLAMA_MODEL to an exact tag)."
            )
        if log_failure:
            logger.warning("Ollama POST %s failed: %s body=%s", url, hint, body or "(empty)")
        else:
            logger.debug("Ollama POST %s failed: %s body=%s", url, hint, body[:200] if body else "")
        return None, hint
    except urllib.error.URLError as exc:
        if log_failure:
            logger.warning("Ollama POST %s failed (network): %s", url, exc)
        return None, str(exc)
    except (TimeoutError, json.JSONDecodeError) as exc:
        if log_failure:
            logger.warning("Ollama POST %s failed: %s", url, exc)
        return None, str(exc)


def _assistant_text_from_chat_body(body: dict, *, allow_thinking_fallback: bool) -> str:
    """Read assistant output from POST /api/chat JSON (thinking models may use `thinking`)."""
    msg = body.get("message") or {}
    content = (msg.get("content") or "").strip()
    if content:
        return content
    if allow_thinking_fallback:
        return (msg.get("thinking") or "").strip()
    return ""


def _completion_text(
    host: str,
    model: str,
    user_content: str,
    *,
    extra_chat_fields: Optional[dict[str, Any]] = None,
    allow_thinking_fallback: bool = False,
) -> Optional[str]:
    """
    POST /api/chat only. Many Qwen/Ollama builds omit legacy POST /api/generate (404);
    thinking models often leave `content` empty unless `think` is disabled — we set think=false
    and optionally parse JSON from `thinking`.
    """
    host = host.rstrip("/")

    chat_payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": user_content}],
        "stream": False,
        "think": False,
    }
    if extra_chat_fields:
        chat_payload.update(extra_chat_fields)

    out, err_chat = _post_json(f"{host}/api/chat", chat_payload, log_failure=True)
    if out:
        text = _assistant_text_from_chat_body(out, allow_thinking_fallback=allow_thinking_fallback)
        if text:
            return text

    logger.warning(
        "Ollama chat completion empty or failed for model=%r on host=%s (err=%s)",
        model,
        host,
        err_chat or "empty assistant message",
    )

    if err_chat and "404" in err_chat:
        installed = list_installed_models(host)
        if installed:
            logger.warning(
                "Ollama model %r not found or not usable. Installed tags include: %s",
                model,
                ", ".join(installed[:12]) + (" …" if len(installed) > 12 else ""),
            )
        else:
            logger.warning(
                "Ollama returned 404 for model %r and /api/tags listed no models "
                "(is Ollama running on %s?).",
                model,
                host,
            )
    return None


def classify_intent_llm(question: str, host: str, model: str) -> Optional[str]:
    """
    Ask Ollama to emit JSON {\"intent\": \"...\"} from a closed label set.
    Returns None on failure or invalid output.
    """
    labels = ", ".join(sorted(ALLOWED_INTENTS))
    prompt = (
        f"Classify this user question into exactly ONE intent label.\n"
        f"Allowed labels: {labels}.\n"
        f"Rules: portfolio/stock risk questions map to concentration, hedge_coverage, "
        f"crash_scenario, or portfolio_summary. Trading or orders → unsupported. "
        f"Vague gibberish → unsupported.\n"
        f'Reply with ONLY valid JSON: {{"intent":"<label>"}}\n\n'
        f"Question: {question.strip()}"
    )
    text = _completion_text(
        host,
        model,
        prompt,
        extra_chat_fields={"format": "json"},
        allow_thinking_fallback=True,
    )
    if not text:
        return None

    m = re.search(r"\{[^}]+\}", text, re.DOTALL)
    if not m:
        logger.warning("Ollama intent: no JSON in response: %s", text[:200])
        return None
    try:
        obj = json.loads(m.group(0))
        intent = str(obj.get("intent", "")).strip()
        if intent in ALLOWED_INTENTS:
            return intent
    except json.JSONDecodeError:
        logger.warning("Ollama intent JSON parse failed: %s", m.group(0))
    return None


def phrase_response_llm(draft: str, host: str, model: str) -> Optional[str]:
    """
    Optional concise rewrite. Numbers must stay verbatim — model instructed not to invent data.
    """
    prompt = (
        "Rewrite the following assistant reply to be concise and readable for a portfolio owner. "
        "CRITICAL: Copy every dollar amount, percentage, ticker symbol, and number exactly as written. "
        "Do not add facts or numbers not in the text. If unsure, return the original wording.\n\n"
        f"{draft}"
    )
    text = _completion_text(host, model, prompt, allow_thinking_fallback=False)
    return text if text else None
