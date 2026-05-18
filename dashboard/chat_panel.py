"""
Streamlit chat panel — MVP Phase 1 (deterministic router).

Depends only on session_state snapshot + src.chat.router.run_chat.
"""
from __future__ import annotations

import logging

import streamlit as st

from src.chat.router import run_chat, snapshot_ready

logger = logging.getLogger(__name__)


def render_chat_panel() -> None:
    """Portfolio Q&A chat; requires Refresh-loaded snapshot in session_state."""
    with st.container(border=True):
        st.markdown("#### Portfolio chat")

        if st.button("Clear chat", key="chat_clear_btn", use_container_width=True):
            st.session_state.pop("chat_messages", None)
            st.rerun()

        st.caption(
            "**Local · Read-only** · LangGraph over your snapshot · optional **Ollama** intent "
            "via `CHAT_OLLAMA_*` in `.env`."
        )

        with st.expander("Examples", expanded=False):
            st.markdown(
                """
- **Concentration** — *Top positions?* · *How concentrated is my equity book?*
- **Hedge coverage** — *Put hedge on NVDA?* · *Am I hedged?*
- **Crash scenarios** — *What happens at -20%?*
- **Portfolio summary** — *Summarize portfolio risk*

Trading or broker-action requests are refused.
"""
            )

        ok, hint = snapshot_ready(st.session_state)
        if not ok:
            st.info(hint)
            return

        stocks_df = st.session_state["stocks_df"]
        options_df = st.session_state["options_df"]
        hedge_df = st.session_state["hedge_df"]
        crash_df = st.session_state["crash_df"]
        summary = st.session_state["summary"]

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Ask about concentration, hedging, crash scenarios…")
        if not prompt:
            return

        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        try:
            result = run_chat(prompt, stocks_df, options_df, hedge_df, crash_df, summary)
            reply = result.get("final_response") or "No response."
            logger.info("chat intent=%s", result.get("intent"))
        except Exception as exc:  # pragma: no cover
            logger.exception("chat handler failed")
            reply = f"Something went wrong while answering (details logged locally): `{exc}`"

        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()
