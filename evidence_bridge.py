"""The live, native Streamlit workspace for ARIA's local evidence library."""

from __future__ import annotations

import hashlib
import html
import re

import streamlit as st

from professor_aria.branding import (
    EVIDENCE_STYLE, PAGE_ICON, chat_avatar, _star_html,
)
from professor_aria.knowledge_base import (
    KnowledgeBaseError, get_document_bytes, ingest_pdf, list_documents, remove_document,
)


BRIDGE_STYLE = """
<style>
.aria-bridge-header {margin:4px 0 28px; color:#0f172a;}
.aria-bridge-title {display:flex; align-items:center; gap:12px; font-size:25px;
    font-weight:650; letter-spacing:-.5px;}
.aria-bridge-icon {display:flex; align-items:center; justify-content:center;
    background:#e0f2fe; color:#0284c7; border-radius:10px; width:43px; height:43px;}
.aria-bridge-subtitle {color:#64748b; font-size:16px; line-height:1.6; margin:7px 0 0 55px;}
.aria-bridge-label {font-size:14px; font-weight:700; color:#334155; text-transform:uppercase;
    letter-spacing:1.2px; margin:0 0 14px;}
.st-key-bridge_ingestion, .st-key-bridge_library, .st-key-bridge_query {
    background:#fff; border:1px solid #e2e8f0 !important; border-radius:17px !important;
    padding:24px !important; box-shadow:0 2px 5px rgba(15,23,42,.025); margin-bottom:18px;}
.st-key-bridge_ingestion [data-testid="stFileUploaderDropzone"] {border:2px dashed #cbd5e1;
    border-radius:13px; background:#f8fafc; padding:30px 20px;}
.st-key-bridge_ingestion [data-testid="stFileUploaderDropzone"]:hover {background:#f0f9ff;}
.st-key-bridge_ingestion [data-testid="stFileUploaderDropzone"] button {
    background:#0284c7 !important; color:white !important; border:0 !important; border-radius:8px;}
.st-key-bridge_ingestion [data-testid="stWidgetLabel"] {color:#0f172a; font-weight:600;}
.aria-bridge-document {display:flex; align-items:flex-start; gap:11px; min-height:104px;
    padding:17px; border:1px solid #e2e8f0; background:#f8fafc; border-radius:12px;}
.aria-bridge-document.uploaded {background:#f0f9ff; border-color:#bae6fd;}
.aria-bridge-document-icon {font-size:20px; color:#10b981; line-height:1.3; flex-shrink:0;}
.uploaded .aria-bridge-document-icon {color:#0284c7;}
.aria-bridge-document-title {font-size:17px; font-weight:600; color:#0f172a; overflow-wrap:anywhere;}
.aria-bridge-document-meta {font-size:12px; color:#64748b; margin-top:5px; line-height:1.6;}
.uploaded .aria-bridge-document-meta {color:#0369a1;}
.aria-bridge-document .aria-evidence-stars {font-size:14px; letter-spacing:.5px;}
.st-key-bridge_library .stButton > button {background:transparent !important; color:#64748b !important;
    font-size:12px !important; padding:5px 9px !important; box-shadow:none !important;}
.st-key-bridge_library .stButton > button:hover {background:#f1f5f9 !important; color:#b91c1c !important;}
.st-key-bridge_library .stDownloadButton > button {background:#fff !important; color:#0369a1 !important;
    border:1px solid #bae6fd !important; font-size:12px !important; padding:5px 9px !important;}
.aria-bridge-answer {background:#eef6ff; border-radius:12px; padding:16px 18px;
    color:#334155; font-size:17px; line-height:1.6;}
.aria-bridge-answer p {margin:0;}
.aria-bridge-citation {background:#fff; border:1px solid #fff;
    border-radius:8px; padding:10px 13px; margin:12px 0 0; color:#334155; font-size:16px; line-height:1.6;}
.aria-bridge-citation strong {color:#075985;}
.st-key-bridge_query [data-testid="stChatMessage"] {background:transparent; border-radius:13px;}
.st-key-bridge_query [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background:transparent;}
.st-key-bridge_query [data-testid="stChatInput"] {border-color:#cbd5e1; border-radius:12px;}
@media (max-width:640px) {.st-key-bridge_ingestion, .st-key-bridge_library,
    .st-key-bridge_query {padding:16px !important;} .aria-bridge-title {font-size:21px;}}
.aria-bridge-icon {background:transparent;}
.aria-bridge-icon img {display:block; border-radius:10px;}
.st-key-bridge_query [data-testid="stMarkdownContainer"] p,
.st-key-bridge_query [data-testid="stMarkdownContainer"] li,
.st-key-bridge_query [data-testid="stChatInputTextArea"],
.st-key-bridge_ingestion [data-testid="stWidgetLabel"] p {
    font-size:17px !important; line-height:1.6 !important;
}
.st-key-bridge_library [data-testid="stMarkdownContainer"] p {font-size:16px; line-height:1.6;}
.aria-bridge-document-meta {font-size:16px; line-height:1.6;}
.aria-bridge-citation {font-size:16px; line-height:1.6;}
</style>
"""



def _ensure_state():
    for key, value in (("bridge_upload_generation", 0), ("bridge_seen_uploads", set()),
                       ("bridge_history", []), ("bridge_notices", [])):
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.get("bridge_format_version") != 2:
        # Discard old answers citing retired summaries or using the essay layout.
        st.session_state.bridge_history = []
        st.session_state.bridge_format_version = 2


def _ingest_uploads(uploaded_files):
    """Ingest each selected file once; reruns never repeat an ingestion or its toast."""
    for uploaded in uploaded_files or []:
        data = uploaded.getvalue()
        fingerprint = hashlib.sha256(uploaded.name.encode() + b"\0" + data).hexdigest()
        if fingerprint in st.session_state.bridge_seen_uploads:
            continue
        st.session_state.bridge_seen_uploads.add(fingerprint)
        try:
            document = ingest_pdf(uploaded.name, data)
        except KnowledgeBaseError as exc:
            st.session_state.bridge_notices.append(("error", f"{uploaded.name}: {exc}"))
            continue
        st.session_state.bridge_history = []
        pages = document.get("page_count", 0)
        st.toast(f"Added {document.get('filename', uploaded.name)} · {pages} page(s)")
        for warning in document.get("extraction_warnings", document.get("warnings", [])):
            st.session_state.bridge_notices.append(("warning", str(warning)))


def _document_card_html(document):
    title = html.escape(str(document.get("filename") or "Untitled PDF"))
    pages = int(document.get("page_count", 0))
    metadata = ("Not indexed · PDF text extraction needs attention" if document.get("extraction_error") else
                f"• Active (User Uploaded · {pages} pages · {_star_html(document.get('star_rating', 1))})")
    return (
        '<div class="aria-bridge-document uploaded">'
        '<span class="aria-bridge-document-icon" aria-hidden="true">▤</span>'
        f'<div><div class="aria-bridge-document-title">{title}</div>'
        f'<div class="aria-bridge-document-meta">{metadata}</div></div></div>'
    )


def _citation_box_html(citation):
    """One compact exact quote; its document is named in the answer above."""
    passage = citation.get("passage", {})
    page = passage.get("page_number")
    return (
        '<div class="aria-bridge-citation"><strong>Citation:</strong> &quot;'
        + html.escape(str(citation.get("quote", "")))
        + '&quot; (Pg. ' + html.escape(str(page if page is not None else "unknown")) + ')</div>'
    )


def _answer_bubble_html(answer, citations):
    from professor_aria.knowledge_chat import compact_answer, _compact_quote

    citation = next(iter(citations or []), None)
    text = html.escape(compact_answer(answer, citation))
    # Permit bold text only; model/PDF HTML and all other Markdown stay inert.
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    quote_box = _citation_box_html({**citation, "quote": _compact_quote(citation.get("quote", ""))}) if citation else ""
    return f'<div class="aria-bridge-answer"><p>{text}</p>{quote_box}</div>'


def _render_library():
    documents = list_documents()
    if not documents:
        st.markdown("No Active Documents — Upload a clinical study or CPG PDF above to populate the knowledge base.")
        return
    columns = st.columns(2, gap="medium")
    for index, document in enumerate(documents):
        with columns[index % 2]:
            st.markdown(_document_card_html(document), unsafe_allow_html=True)
            if document.get("source_type") == "uploaded_pdf":
                if document.get("extraction_error"):
                    st.error(document["extraction_error"])
                for warning in document.get("extraction_warnings", []):
                    st.caption(warning)
                document_id = str(document.get("document_id") or document["id"])
                download_column, remove_column = st.columns(2)
                with download_column:
                    try:
                        data = get_document_bytes(document_id)
                    except KnowledgeBaseError:
                        data = None
                    if data is not None:
                        st.download_button("Download PDF", data, file_name=document.get("filename", "reference.pdf"),
                                           mime="application/pdf", key=f"bridge_download_{document_id}")
                with remove_column:
                    if st.button("Remove PDF", key=f"bridge_remove_{document_id}", type="tertiary"):
                        try:
                            remove_document(document_id)
                        except KnowledgeBaseError as exc:
                            st.error(str(exc))
                        else:
                            # A fresh uploader key prevents the still-selected PDF from reappearing.
                            st.session_state.bridge_upload_generation += 1
                            st.session_state.bridge_seen_uploads = set()
                            st.session_state.bridge_history = []
                            st.session_state.bridge_notices.append(("success", "PDF removed from the knowledge base."))
                            st.rerun()
            st.write("")


def _render_query():
    from professor_aria.knowledge_chat import answer_evidence_question

    if not st.session_state.bridge_history:
        st.caption("Ask about a study, compare recommendations, or find an exact passage in your uploaded PDFs.")
    for turn in st.session_state.bridge_history:
        with st.chat_message(turn["role"], avatar=chat_avatar(turn["role"])):
            if turn["role"] == "assistant":
                if turn["content"]:
                    st.markdown(_answer_bubble_html(turn["content"], turn.get("citations", [])), unsafe_allow_html=True)
                if turn.get("error"):
                    st.warning(turn["error"])
            else:
                st.markdown(turn["content"])

    question = st.chat_input("Ask ARIA about your uploaded studies and CPG PDFs...", key="bridge_question")
    if question and question.strip():
        history = [{"role": turn["role"], "content": turn["content"]}
                   for turn in st.session_state.bridge_history]
        st.session_state.bridge_history.append({"role": "user", "content": question.strip()})
        with st.spinner("Cross-referencing the knowledge base..."):
            result = answer_evidence_question(question.strip(), history=history)
        st.session_state.bridge_history.append({
            "role": "assistant", "content": result.get("answer", ""),
            "sources": result.get("sources", []), "citations": result.get("citations", []),
            "error": result.get("error"), "citation_notes": result.get("citation_notes", []),
        })
        st.rerun()


def render_evidence_bridge():
    """Render real upload, disk-scanned library, and grounded question answering."""
    _ensure_state()
    st.markdown(EVIDENCE_STYLE, unsafe_allow_html=True)
    st.markdown(BRIDGE_STYLE, unsafe_allow_html=True)
    st.markdown(
        '<div class="aria-bridge-header"><div class="aria-bridge-title">'
        f'<span class="aria-bridge-icon"><img src="{PAGE_ICON}" alt="ARIA" width="43" height="43"/></span>ARIA - Evidence Bridge</div>'
        '<div class="aria-bridge-subtitle">Dynamic PDF Ingestion &amp; Retrieval-Augmented Decision Support</div></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True, key="bridge_ingestion"):
        st.markdown('<div class="aria-bridge-label">Knowledge Base Ingestion</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload Recent Clinical Studies & Whitepapers", type=["pdf"], accept_multiple_files=True,
            key=f"bridge_upload_{st.session_state.bridge_upload_generation}",
            help="PDFs persist in the project's knowledge_base folder. Text is extracted page by page; scanned image PDFs require OCR before upload.",
        )
        _ingest_uploads(uploaded_files)
        for kind, message in st.session_state.bridge_notices:
            getattr(st, kind)(message)
        st.session_state.bridge_notices = []
        st.caption("Drag and drop clinical studies or CPG PDFs to query and cross-reference their exact text.")
    with st.container(border=True, key="bridge_library"):
        st.markdown('<div class="aria-bridge-label">Active Knowledge Base</div>', unsafe_allow_html=True)
        try:
            _render_library()
        except KnowledgeBaseError as exc:
            st.error(f"The knowledge base could not be read: {exc}")
    with st.container(border=True, key="bridge_query"):
        st.markdown('<div class="aria-bridge-label">Evidence Query</div>', unsafe_allow_html=True)
        _render_query()
