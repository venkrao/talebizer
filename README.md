## Talebizer - Phase 1 Minimal App

This is a **minimal implementation** of the Phase 1 spec: a local Python app that connects to Interactive Brokers (IBKR) via `ib_async`, pulls live positions, and shows them in a simple Streamlit dashboard so you can compare them with your actual IBKR portfolio.

This version intentionally skips metrics, charts, and CSV export. It focuses only on:

- **Connecting to IBKR** (TWS or IB Gateway must be running)
- **Pulling positions via `ib.positions()`**
- **Displaying stocks and options in a simple UI**

### 1. Setup

1. Create and activate a virtualenv (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:

```bash
IB_HOST=127.0.0.1
IB_PORT=7497          # 7497 = TWS paper; 7496 = TWS live; 4002 = Gateway
IB_CLIENT_ID=1
BASE_CURRENCY=USD
```

4. In TWS / IB Gateway:
   - Enable API access.
   - Ensure the port matches `IB_PORT`.

### 2. Running the Dashboard

From the project root:

```bash
streamlit run dashboard/app.py
```

The app will:

- Connect to IBKR using `ib_async`.
- Pull positions via `ib.positions()`.
- Split them into **stocks** and **options** and display simple tables so you can visually compare them to what you see in TWS.

If there is a connection or API error, the app will show a clear error message in the UI.

### Portfolio chat + local Ollama (optional)

The dashboard includes a **read-only** chat layer. Set these in `.env` if you use intent fallback via Ollama:

```bash
CHAT_OLLAMA_ENABLED=true
CHAT_OLLAMA_HOST=http://127.0.0.1:11434
CHAT_OLLAMA_MODEL=your-model-tag   # must match `ollama list` exactly, e.g. llama3.2:latest
```

If you see **`HTTP 404`** from **`/api/chat`**, align **`CHAT_OLLAMA_MODEL`** with an installed tag (`ollama list`). The client uses **`POST /api/chat` only** (some Ollama builds no longer expose **`/api/generate`**). For **thinking** models (e.g. Qwen 3), intent classification requests **`think: false`** and **`format: json`** so the reply lands in **`message.content`**.

