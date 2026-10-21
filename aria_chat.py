"""Ask ARIA integration for the professor's clinical AI/RAG engine."""

import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from professor_aria.branding import (
    render_evidence_legend, render_evidence_sources, render_guidance_markdown, combined_evidence_sources, chat_avatar,
)


load_dotenv()

_DEFAULT_NOTE = (
    "67-year-old male, 12 weeks post left MCA ischemic stroke with right foot drop, "
    "Berg Balance Scale 38/56, and two near-falls this week."
)


def _secret_or_env(name: str) -> str:
    """Read a setting from Streamlit secrets first, then the local environment."""
    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None
    return str(secret_value or os.getenv(name, "")).strip()


def _load_professor_engine() -> dict[str, Any] | None:
    """Load the professor modules only after the Claude key is available."""
    anthropic_key = _secret_or_env("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return None

    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    from professor_aria.intake import parse_clinician_note
    from professor_aria.literacy_engine import continue_conversation, generate_response
    from professor_aria.log import log_interaction
    from professor_aria.rag import retrieve_literature_smart

    return {
        "parse_clinician_note": parse_clinician_note,
        "retrieve_literature_smart": retrieve_literature_smart,
        "generate_response": generate_response,
        "continue_conversation": continue_conversation,
        "log_interaction": log_interaction,
    }


def _ensure_state() -> None:
    defaults = {
        "aria_note": _DEFAULT_NOTE,
        "aria_parsed": None,
        "aria_literature": None,
        "aria_conversation": [],
        "aria_tier": 2,
        "aria_response_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value


def _render_sources(literature: dict[str, Any]) -> None:
    sources = combined_evidence_sources(literature)
    with st.expander(f"The evidence I used ({len(sources)} source(s))"):
        render_evidence_legend()
        st.caption("Sources: PubMed via NCBI and matched Evidence Bridge Knowledge Base references")
        if literature.get("note"):
            st.info(literature["note"])
        if literature.get("query_used"):
            st.code(literature["query_used"], language="text")
        if literature.get("rationale"):
            st.write(literature["rationale"])
        render_evidence_sources(sources, show_legend=False)


def render_ask_aria() -> None:
    """Render the integrated note-to-evidence-to-chat ARIA workflow."""
    _ensure_state()

    st.subheader("Ask ARIA")
    st.caption("Clinical reasoning support powered by the integrated literature retrieval engine.")

    engine = _load_professor_engine()
    if engine is None:
        st.info(
            "Ask ARIA needs an Anthropic API key to activate the professor's Claude-powered engine. "
            "Add ANTHROPIC_API_KEY to a project .env file or Streamlit secrets, then restart the app."
        )
        st.caption("NCBI_API_KEY is optional; without it, PubMed will use the public endpoint limits.")
        return

    note = st.text_area(
        "Clinical note or question",
        key="aria_note",
        height=150,
        help="Paste a note or describe the clinical question ARIA should investigate.",
    )
    tier = st.select_slider(
        "Response depth",
        options=[1, 2, 3],
        value=st.session_state.aria_tier,
        format_func=lambda value: {1: "Quick check", 2: "Explore options", 3: "Deep teaching"}[value],
    )
    st.session_state.aria_tier = tier

    if st.button("Analyze note", type="primary", key="aria_analyze"):
        if not note.strip():
            st.warning("Add a clinical note or question first.")
        else:
            with st.spinner("Reading the clinical note..."):
                try:
                    parsed = engine["parse_clinician_note"](note)
                    st.session_state.aria_parsed = parsed
                    st.session_state.aria_literature = None
                    st.session_state.aria_conversation = []
                    st.session_state.aria_response_error = None
                except Exception as exc:
                    st.error(f"ARIA could not parse this note: {exc}")

    parsed = st.session_state.aria_parsed
    if parsed:
        st.markdown("#### Structured clinical summary")
        if parsed.get("error"):
            st.warning(parsed["error"])
        else:
            st.json(parsed)

        if st.button("Search evidence and generate guidance", key="aria_generate"):
            with st.spinner("Searching PubMed and Evidence Bridge, then preparing ARIA's guidance..."):
                try:
                    literature = engine["retrieve_literature_smart"](note, parsed, [])
                    result = engine["generate_response"](
                        parsed,
                        literature,
                        note,
                        tier=st.session_state.aria_tier,
                    )
                    st.session_state.aria_literature = literature
                    st.session_state.aria_response_error = result.get("response_text") if result.get("tier_used") is None else None
                    if result.get("tier_used") is not None:
                        st.session_state.aria_conversation = [
                            {"role": "user", "content": note},
                            {"role": "assistant", "content": result["response_text"]},
                        ]
                        engine["log_interaction"]({
                            "type": "initial_response",
                            "note": note,
                            "search_query": literature.get("query_used"),
                            "tier_used": result.get("tier_used"),
                            "response": result.get("response_text"),
                        })
                except Exception as exc:
                    st.session_state.aria_response_error = f"ARIA could not complete the search: {exc}"

    literature = st.session_state.aria_literature
    if literature:
        _render_sources(literature)

    if st.session_state.aria_response_error:
        st.error(st.session_state.aria_response_error)

    for turn in st.session_state.aria_conversation:
        with st.chat_message(turn["role"], avatar=chat_avatar(turn["role"])):
            if turn["role"] == "assistant":
                render_guidance_markdown(turn["content"], combined_evidence_sources(literature))
            else:
                st.markdown(turn["content"])

    if st.session_state.aria_conversation:
        follow_up = st.text_input(
            "Reply to ARIA or ask a follow-up question",
            key="aria_follow_up",
        )
        if st.button("Send follow-up", key="aria_send_follow_up"):
            if not follow_up.strip():
                st.warning("Type a follow-up question first.")
            else:
                with st.spinner("ARIA is thinking..."):
                    try:
                        st.session_state.aria_conversation.append(
                            {"role": "user", "content": follow_up}
                        )
                        reply = engine["continue_conversation"](
                            st.session_state.aria_conversation,
                            st.session_state.aria_tier,
                            literature=st.session_state.aria_literature,
                        )
                        st.session_state.aria_conversation.append(
                            {"role": "assistant", "content": reply}
                        )
                        engine["log_interaction"]({
                            "type": "follow_up",
                            "clinician_message": follow_up,
                            "aria_reply": reply,
                            "tier_used": st.session_state.aria_tier,
                        })
                        st.rerun()
                    except Exception as exc:
                        st.error(f"ARIA could not answer the follow-up: {exc}")
