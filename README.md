## Talebizer

**Talebizer** is a **local, read-only** portfolio dashboard for **Interactive Brokers (IBKR)**. It connects through **TWS** or **IB Gateway**, pulls a consolidated snapshot of your positions, and turns it into **risk-oriented views**—not predictions and never trades.

The philosophy is simple: brokerage UIs show balances and line items well, but **cross-cutting risk** (concentration, how puts couple to equity, what a crude shock implies, whether option premium buys meaningful convexity) is easy to scatter or eyeball wrong. Talebizer exists so you can reason about **tail asymmetry and discipline** on your own machine: **one refresh → one snapshot → several complementary lenses**, with **no order placement** by design (`SafeIB` blocks trading APIs).

What it emphasizes:

- **Concentration** — equity weights and concentration flags.
- **Hedge coverage** — put delta-dollars versus equity market value per underlying (day-to-day delta coupling; deep OTM tails need interpretation alongside other views).
- **Crash scenarios** — a **Δ–Γ** stylized shock table for stocks + options (approximation; not a full tail model).
- **Convexity / “Taleb” lens** — realized vs implied vol, stylized tail payoff per premium, and a compact score / signal hints (structure vs premium, not forecast accuracy).
- **Optional chat** — read-only Q&A over the same snapshot (LangGraph + optional local **Ollama** for intent), still **no execution**.

What it is **not**: not a broker, not a cloud service, not a substitute for IBKR’s own risk systems—and not a claim about calibrated probabilities for rare events.

Specifications and design notes live under **`specs/`** (e.g. phase 1, convexity, chat MVP). For architecture diagrams, module map, and operational caveats, see **`thewhy.md`**.

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

### 2. Running the app

The supported UI is the **desktop shell** (**React + Vite** under **`desktop/`**) talking to the **FastAPI** layer under **`backend/`** (same analytics core as `src/ib_service.py`).

1. Start the API on loopback — see **[`backend/README.md`](backend/README.md)** (`uvicorn`).
2. From **`desktop/`**: `npm install` then **`npm run dev`** (default **http://localhost:5173**).

Environment variables for IBKR and optional Ollama apply to the Python backend; **`desktop/README.md`** covers **`VITE_API_BASE_URL`**.

### Portfolio chat + local Ollama (optional)

The app includes a **read-only** chat layer over the loaded snapshot. Set these in `.env` if you use intent fallback via Ollama:

```bash
CHAT_OLLAMA_ENABLED=true
CHAT_OLLAMA_HOST=http://127.0.0.1:11434
CHAT_OLLAMA_MODEL=your-model-tag   # must match `ollama list` exactly, e.g. llama3.2:latest
```

If you see **`HTTP 404`** from **`/api/chat`**, align **`CHAT_OLLAMA_MODEL`** with an installed tag (`ollama list`). The client uses **`POST /api/chat` only** (some Ollama builds no longer expose **`/api/generate`**). For **thinking** models (e.g. Qwen 3), intent classification requests **`think: false`** and **`format: json`** so the reply lands in **`message.content`**.

