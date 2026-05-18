# Talebizer MVP Software Specification

## Overview

Talebizer MVP is a **local-only, read-only** natural-language chat interface over an IBKR portfolio snapshot. It extends the current Talebizer application by adding a simple chat panel that answers a narrow set of portfolio-risk questions using the existing Python analytics pipeline and a small LangGraph workflow, while keeping all processing on the user’s machine through a local Ollama model runtime.[cite:1][cite:2][cite:3]

The MVP is intentionally narrow. Its goal is to validate that a conversational layer is a useful interface for portfolio inspection before introducing broader agentic behavior, retrieval, or more complex orchestration.[cite:1]

## Product Goals

The MVP must:

- Let a user ask plain-English questions about the current portfolio snapshot.[cite:2]
- Answer using existing Talebizer outputs such as concentration, hedge coverage, crash scenarios, and summary metrics.[cite:1]
- Run entirely locally with no OpenAI, Gemini, or other hosted model APIs.[cite:3]
- Preserve Talebizer’s read-only posture and never place, modify, or cancel orders.[cite:1]
- Be simple enough to build quickly and easy to inspect, debug, and extend.[cite:1]

## Non-Goals

The MVP will not include:

- Trade execution, order staging, or broker-side mutation of any kind.[cite:1]
- Autonomous multi-step planning beyond a single short workflow.[cite:1]
- Retrieval-augmented generation over specs, docs, or codebase content.[cite:1]
- Long-term memory, user profiling, or historical portfolio journaling.[cite:1]
- Cloud deployment, hosted inference, or remote databases.[cite:3]

## Users and Use Cases

The primary user is a single local user running IBKR TWS or IB Gateway and Talebizer on the same machine or trusted local network.[cite:1]

The MVP supports questions in four categories:

1. **Concentration** — e.g. “What are my largest positions?” or “How concentrated is my equity book?”[cite:1]
2. **Hedge coverage** — e.g. “How much put hedge do I have on SPY?”[cite:1]
3. **Crash scenarios** — e.g. “What happens at -20%?” using the existing \(\Delta\)–\(\Gamma\) scenario outputs.[cite:1]
4. **Portfolio summary** — e.g. “Give me a quick portfolio risk summary.”[cite:1]

Unsupported questions must receive a bounded response stating what the MVP can answer.[cite:1]

## Functional Requirements

### FR1. Local chat interface

The app must add a chat area to the existing Streamlit UI using Streamlit chat components such as `st.chat_input` and `st.chat_message`.[cite:2]

The UI must support:

- user message entry,
- assistant responses,
- a refresh action for the latest portfolio snapshot,
- a visible “local / read-only” status indicator,
- and a small “supported questions” hint panel.[cite:1][cite:2]

### FR2. Portfolio snapshot source

The only supported source of portfolio data for the chat layer is `src/ib_service.py:get_portfolio_frames()`, which returns `(stocks_df, options_df, hedge_df, crash_df, summary)`.[cite:1]

The chat layer must not access raw IB client objects directly.[cite:1]

### FR3. LangGraph workflow

The MVP must use LangGraph as a lightweight orchestration layer for a short stateful workflow. LangGraph is a low-level orchestration framework for stateful workflows, which fits a narrow, inspectable routing graph.[cite:1]

The initial graph should contain these nodes:

1. `parse_question`
2. `route_intent`
3. `run_portfolio_tool`
4. `format_response`[cite:1]

The graph should not contain loops, retries with autonomous replanning, or multi-agent branches in the MVP.[cite:1]

### FR4. Intent routing

The system must classify each user question into one of these intents:

- `concentration`
- `hedge_coverage`
- `crash_scenario`
- `portfolio_summary`
- `unsupported`[cite:1]

Routing should be deterministic-first. Keyword and pattern matching should be attempted before invoking the local LLM. The local LLM may be used as a fallback classifier when the wording is ambiguous.[cite:1][cite:3]

### FR5. Tool execution

Each supported intent must map to one whitelisted tool function operating on the current portfolio frames:

- `get_concentration_answer(stocks_df, summary, question)`
- `get_hedge_answer(hedge_df, options_df, question)`
- `get_crash_answer(crash_df, question)`
- `get_summary_answer(summary, stocks_df, options_df)`[cite:1]

These tools must be pure read-only functions with no side effects outside logging and rendering.[cite:1]

### FR6. Local model runtime

The MVP must use a local model served through Ollama. Ollama provides local model execution on the user’s machine and is suitable for fully local inference flows.[cite:3]

The LLM is used only for:

- fallback intent classification,
- concise response wording,
- and optionally normalizing user phrasing into structured parameters such as shock magnitude or ticker mention.[cite:1][cite:3]

The LLM must not be treated as the source of truth for portfolio values.[cite:1]

### FR7. Answer format

Each response must include:

- a direct answer,
- the key numbers used,
- and a short limitation note when relevant, such as that crash outputs are local \(\Delta\)–\(\Gamma\) approximations.[cite:1]

If the user asks for something unsupported, the system should respond with a short list of supported question types rather than improvising.[cite:1]

## Non-Functional Requirements

### NFR1. Local-only execution

All application logic, inference, and portfolio processing must run locally. No portfolio content or prompts may be sent to hosted third-party model APIs.[cite:3]

### NFR2. Read-only safety

Talebizer’s existing read-only safeguards remain authoritative. The MVP must preserve the `SafeIB` boundary and must not expose any code path that can place, modify, or cancel orders.[cite:1]

### NFR3. Simplicity

The MVP should favor minimal moving parts over extensibility. It should remain a single local Python application with no required frontend-backend split.[cite:1]

### NFR4. Transparency

Answers should be explainable back to a concrete dataframe, summary field, or existing calculation path. The UI should make it clear that the assistant is grounded in the latest local snapshot.[cite:1]

### NFR5. Performance

A normal supported question should return in a few seconds on a typical local machine once the portfolio snapshot is already loaded. Streamlit supports conversational UI elements suitable for this local interaction pattern.[cite:2]

## System Architecture

### Components

1. **Streamlit UI** — hosts the dashboard and chat surface using chat elements.[cite:2]
2. **Talebizer analytics layer** — existing Python modules for data pull, metrics, Greeks, convexity, and summary generation.[cite:1]
3. **LangGraph workflow** — routes a user prompt through a small stateful execution graph.[cite:1]
4. **Ollama local model runtime** — serves the local LLM used for fallback classification and response wording.[cite:3]
5. **IBKR connectivity layer** — current read-only `SafeIB` + connection/orchestration modules.[cite:1]

### Data flow

1. User opens the local dashboard and refreshes portfolio data.[cite:1]
2. Talebizer obtains `(stocks_df, options_df, hedge_df, crash_df, summary)` from `get_portfolio_frames()`.[cite:1]
3. User submits a chat question through Streamlit chat input.[cite:2]
4. LangGraph receives the message and state, routes to one whitelisted portfolio tool, and passes the result to response formatting.[cite:1]
5. If needed, the Ollama-hosted LLM helps classify or phrase the response, but portfolio values come from Talebizer data structures.[cite:1][cite:3]
6. The final answer is rendered in the chat panel.[cite:2]

## State Model

The LangGraph state should be minimal and typed. Suggested fields:

- `user_question: str`
- `intent: str | None`
- `tool_args: dict`
- `snapshot_timestamp: str`
- `tool_result: dict | None`
- `final_response: str | None`
- `error: str | None`[cite:1]

No long-term memory is required in the MVP.[cite:1]

## UI Specification

The MVP UI extends the current dashboard rather than replacing it.[cite:1]

### Required UI elements

- Existing portfolio tables/charts remain available.[cite:1]
- New chat panel on the same page.[cite:2]
- “Refresh portfolio snapshot” control.[cite:1]
- Small note: “Local-only. Read-only. No order execution.”[cite:1]
- Example prompts, such as:
  - “What are my top 5 positions?”
  - “How much downside hedge do I have?”
  - “What happens at -20%?”
  - “Summarize the portfolio risk.”[cite:1]

### UI behavior

If there is no current snapshot, the chat should block portfolio questions and instruct the user to refresh first.[cite:1]

If TWS / IB Gateway is unavailable, the app should show a bounded connection error and avoid partial or invented answers.[cite:1]

## API and Module Design

Suggested new modules:

- `src/chat/state.py` — LangGraph state definition
- `src/chat/router.py` — deterministic intent parsing + fallback LLM classification
- `src/chat/tools.py` — whitelisted read-only portfolio answer functions
- `src/chat/graph.py` — LangGraph graph assembly
- `src/chat/ollama_client.py` — local model invocation wrapper
- `dashboard/chat_panel.py` — Streamlit chat rendering and interaction glue[cite:1]

Suggested integration rule: the chat layer may depend on `ib_service.py` outputs, but portfolio analytics modules must not depend on the chat layer.[cite:1]

## Security and Safety

The application must enforce these constraints:

- No order methods callable from the chat flow.[cite:1]
- No free-form tool execution outside a hardcoded whitelist.[cite:1]
- No shell access, file writes outside app logs/state, or arbitrary code execution from prompts.[cite:1]
- No cloud inference endpoints.[cite:3]
- All prompts and answers treated as local session data.[cite:3]

The assistant should refuse requests to trade, rebalance automatically, or send broker instructions.[cite:1]

## Error Handling

The MVP must handle at least these cases:

- **No IB connection** — explain that TWS/IB Gateway is unavailable.[cite:1]
- **No portfolio snapshot yet** — ask user to refresh first.[cite:1]
- **Unsupported question** — list supported categories.[cite:1]
- **Missing data field** — say the metric is unavailable rather than guessing.[cite:1]
- **Local model unavailable** — continue with deterministic routing where possible and degrade gracefully.[cite:3]

## Dependencies

### Required

- Python 3.11+
- Streamlit
- pandas
- numpy
- plotly
- ib_async
- langgraph
- ollama or an Ollama-compatible Python client[cite:3]

### Existing Talebizer dependencies retained

Current Talebizer dependencies remain in place for IBKR connectivity, analytics, and dashboard rendering.[cite:1]

## Delivery Scope

### In scope for MVP

- Chat UI embedded in existing Streamlit dashboard.[cite:2]
- Local-only question answering for four supported intents.[cite:1]
- Tiny LangGraph workflow.[cite:1]
- Ollama integration for optional fallback classification/phrasing.[cite:3]
- Read-only safety preserved end to end.[cite:1]

### Out of scope for MVP

- LlamaIndex
- RAG over docs/code/specs
- historical comparisons across dates
- user-specific memory
- execution simulation
- alerting engine
- portfolio optimization recommendations[cite:1]

## Implementation Plan

### Phase 1

- Add `chat_panel.py` with Streamlit chat UI.[cite:2]
- Add direct deterministic router over supported question patterns.[cite:1]
- Connect router to existing portfolio outputs.[cite:1]
- Return plain text answers with numbers and limitations.[cite:1]

### Phase 2

- Wrap routing in a minimal LangGraph `StateGraph`.[cite:1]
- Add small typed state and node separation.[cite:1]
- Preserve identical external behavior.[cite:1]

### Phase 3

- Add Ollama fallback for ambiguous intent classification and answer phrasing.[cite:3]
- Add graceful degradation if Ollama is unavailable.[cite:3]

This sequencing keeps the MVP buildable even if LangGraph or Ollama integration takes longer than expected, while preserving the target architecture.[cite:1][cite:3]

## Acceptance Criteria

The MVP is complete when all of the following are true:

- The app runs fully locally and does not send prompts or data to hosted model APIs.[cite:3]
- A user can refresh the portfolio snapshot and ask at least one question in each supported category.[cite:1]
- Answers are grounded in the latest `get_portfolio_frames()` output.[cite:1]
- The app refuses unsupported or trading-related prompts safely.[cite:1]
- The chat interface is integrated into the existing Streamlit dashboard using Streamlit chat components.[cite:2]
- LangGraph is present but limited to a small transparent orchestration graph.[cite:1]
- LlamaIndex is not required for MVP delivery.[cite:1]

## Future Extensions

After MVP validation, the next sensible additions are:

- richer parameter extraction from questions,
- methodology explanations,
- optional retrieval over local specs/docs,
- historical snapshot comparison,
- and more nuanced risk dialogues over existing Talebizer analytics.[cite:1]
