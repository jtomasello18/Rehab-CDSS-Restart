"""
ARIA branding
=============
Self-contained visual identity for ARIA. No external image files needed:
the ARIA mark is embedded directly below. app.py imports three things from
here: PAGE_ICON, inject_style, and render_header.
"""

import base64
import html
import hashlib
import re
from urllib.parse import urlsplit

import streamlit as st

# ARIA mark, embedded as a data URI (used for the browser tab icon and header).
PAGE_ICON = "data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMjU2IDI1NiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiByb2xlPSJpbWciIGFyaWEtbGFiZWw9IkFSSUEiPgogIDxkZWZzPgogICAgPGxpbmVhckdyYWRpZW50IGlkPSJ0aWxlIiB4MT0iMCIgeTE9IjAiIHgyPSIxIiB5Mj0iMSI+CiAgICAgIDxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iIzBFM0E0NiIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjAuNTUiIHN0b3AtY29sb3I9IiMxNTVDNkIiLz4KICAgICAgPHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjMUU3QThDIi8+CiAgICA8L2xpbmVhckdyYWRpZW50PgogICAgPGxpbmVhckdyYWRpZW50IGlkPSJzdHJva2UiIHgxPSIwIiB5MT0iMSIgeDI9IjEiIHkyPSIwIj4KICAgICAgPHN0b3Agb2Zmc2V0PSIwIiBzdG9wLWNvbG9yPSIjNTdDNEM5Ii8+CiAgICAgIDxzdG9wIG9mZnNldD0iMSIgc3RvcC1jb2xvcj0iI0VBRjdGNyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxyYWRpYWxHcmFkaWVudCBpZD0ic3BhcmsiIGN4PSIwLjUiIGN5PSIwLjUiIHI9IjAuNSI+CiAgICAgIDxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iI0ZCRTZBRSIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjAuNTUiIHN0b3AtY29sb3I9IiNFOEIwNEIiLz4KICAgICAgPHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjRThCMDRCIiBzdG9wLW9wYWNpdHk9IjAiLz4KICAgIDwvcmFkaWFsR3JhZGllbnQ+CiAgPC9kZWZzPgoKICA8cmVjdCB4PSIwIiB5PSIwIiB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgcng9IjYwIiBmaWxsPSJ1cmwoI3RpbGUpIi8+CgogIDxjaXJjbGUgY3g9IjEyOCIgY3k9IjEyOCIgcj0iODYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzU3QzRDOSIgc3Ryb2tlLW9wYWNpdHk9IjAuMTYiIHN0cm9rZS13aWR0aD0iOCIvPgoKICA8cGF0aCBkPSJNIDc4IDE5MiBMIDEzMiA3OCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ1cmwoI3N0cm9rZSkiIHN0cm9rZS13aWR0aD0iMTUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgoKICA8cGF0aCBkPSJNIDE3OCAxOTIgQyAxNzYgMTUwLCAxNjggMTE2LCAxNTAgODQiIGZpbGw9Im5vbmUiIHN0cm9rZT0idXJsKCNzdHJva2UpIiBzdHJva2Utd2lkdGg9IjE1IiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KCiAgPHBhdGggZD0iTSAxMDIgMTUwIEwgMTY4IDE1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRUFGN0Y3IiBzdHJva2Utb3BhY2l0eT0iMC43IiBzdHJva2Utd2lkdGg9IjExIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KCiAgPGNpcmNsZSBjeD0iMTQxIiBjeT0iNzQiIHI9IjM0IiBmaWxsPSJ1cmwoI3NwYXJrKSIvPgogIDxjaXJjbGUgY3g9IjE0MSIgY3k9Ijc0IiByPSIxMi41IiBmaWxsPSIjRjRDODYzIi8+CiAgPGNpcmNsZSBjeD0iMTQxIiBjeT0iNzQiIHI9IjEyLjUiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI0ZCRTZBRSIgc3Ryb2tlLXdpZHRoPSIyLjUiLz4KPC9zdmc+Cg=="


PT_AVATAR = "data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
    b'<rect width="64" height="64" rx="16" fill="#145b6e"/>'
    b'<text x="32" y="41" text-anchor="middle" font-family="Arial,sans-serif" '
    b'font-size="25" font-weight="700" fill="white">PT</text></svg>'
).decode("ascii")


def chat_avatar(role):
    """Use the official ARIA emblem and an accessible teal clinician badge."""
    return PAGE_ICON if role in {"assistant", "ai", "ARIA"} else PT_AVATAR


INTERACTION_STYLE = """
<style>
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="base-input"]:focus-within,
.stTextInput input:focus, .stTextArea textarea:focus,
input:focus, textarea:focus,
[data-testid="stChatInput"]:focus-within {
    border-color:#145b6e !important;
    box-shadow:0 0 0 2px rgba(20, 91, 110, 0.25) !important;
    outline:none !important;
}
[data-testid="stChatMessageAvatarAssistant"], [data-testid="stChatMessageAvatarUser"] {
    background:transparent !important;
}
[data-testid="stChatMessageAvatarAssistant"] img, [data-testid="stChatMessageAvatarUser"] img {
    border-radius:9px; object-fit:contain;
}
/* Reset default borders and backgrounds for all chat and text inputs */
div[data-testid="stChatInput"] > div,
div[data-testid="stTextInput"] div[data-baseweb="input"] {
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    background-color: #ffffff !important;
}

/* Apply ARIA Teal (#145b6e) on focus, completely overriding Streamlit's red */
div[data-testid="stChatInput"] > div:focus-within,
div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
    border-color: #145b6e !important;
    box-shadow: 0 0 0 2px rgba(20, 91, 110, 0.25) !important;
    outline: none !important;
}

/* Clean up the input field background itself */
div[data-testid="stChatInput"] textarea,
div[data-testid="stTextInput"] input {
    background-color: transparent !important;
}
</style>
"""

WORKSPACE_STYLE = """
<style>
/* Scope the tab treatment to Workspace; clinical radio inputs stay native. */
.st-key-view div[role="radiogroup"] {
    display:flex !important; flex-wrap:nowrap !important; gap:6px !important;
    width:100%; box-sizing:border-box; overflow-x:auto;
    background:#ffffff; padding:6px; border-radius:10px;
    border:1px solid #cbd5e1; box-shadow:0 1px 3px rgba(15,23,42,.06);
}
.st-key-view div[role="radiogroup"] label > div:first-child {
    display:none !important;
}
/* Newer Streamlit uses React Aria: a hidden-input span precedes the label row. */
.st-key-view [data-testid="stRadioOption"] > span + div > div:first-child:not([data-testid="stMarkdownContainer"]) {
    display:none !important;
}
.st-key-view div[role="radiogroup"] label {
    display:flex; align-items:center; justify-content:center;
    flex:1 0 auto; white-space:nowrap; min-height:42px;
    padding:9px 16px !important; border-radius:7px !important;
    font-weight:600 !important; font-size:13.5px !important;
    color:#334155 !important; margin:0 !important;
    border:1px solid transparent !important;
    transition:all .15s ease; cursor:pointer;
}
.st-key-view div[role="radiogroup"] label p {
    color:inherit !important; font-size:13.5px !important; font-weight:600 !important;
}
.st-key-view div[role="radiogroup"] label:hover {
    background:#f0f7f9; color:#145b6e !important;
}
.st-key-view div[role="radiogroup"] label:has(input:checked),
.st-key-view div[role="radiogroup"] label[data-checked="true"] {
    background:linear-gradient(135deg,#145b6e 0%,#0e4352 100%) !important;
    color:#ffffff !important; border-bottom:2px solid #f0b429 !important;
    box-shadow:0 2px 5px rgba(20,91,110,.25) !important;
}
.st-key-view div[role="radiogroup"] label:has(input:checked) p,
.st-key-view div[role="radiogroup"] label[data-checked="true"] p {
    color:#ffffff !important;
}
.st-key-view div[role="radiogroup"] label:has(input:focus-visible) {
    outline:2px solid #145b6e; outline-offset:2px;
}
.st-key-view { margin-bottom:2px; }
.aria-hero { margin-bottom:8px; }
/* Style-only Markdown elements have no visual content and need no layout gap. */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] [data-testid="stMarkdownContainer"] > style:only-child) {
    display:none;
}

/* Read-only pilot caseload cards, with one connected active chart. */
[data-testid="stSidebar"] { background:#f8fafc !important; border-right:1px solid #cbd5e1; }
.aria-caseload-heading {
    color:#334155; font-size:11.5px; font-weight:750; letter-spacing:.07em; line-height:1.6;
}
.aria-caseload-subtitle { color:#64748b; font-size:12px; margin:4px 0 20px; }
.aria-caseload-card {
    background:#ffffff; border:1px solid #cbd5e1; border-radius:10px;
    padding:15px; margin:0 0 12px; box-shadow:0 1px 3px rgba(15,23,42,.03);
}
.aria-caseload-card.is-active { border:2px solid #145b6e; background:#f0f7f9; padding:14px; }
.aria-caseload-card-top { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }
.aria-caseload-card-top strong { color:#1e293b; font-size:16px; font-weight:700; }
.aria-caseload-card.is-active strong { color:#145b6e; }
.aria-caseload-badge {
    color:#145b6e; background:#e0eef1; border:1px solid #b9d5dc; border-radius:4px;
    padding:3px 6px; font-size:9px; font-weight:750; letter-spacing:.06em;
}
.aria-caseload-card .aria-caseload-meta { color:#64748b; font-size:12px; margin:7px 0 0; line-height:1.6; }
.aria-caseload-card .aria-caseload-detail { color:#475569; font-size:12px; margin:7px 0 0; line-height:1.65; }
.st-key-aria_workflow_guide [data-testid="stExpander"] details {
    background:#ffffff; border:1px solid #cbd5e1; border-radius:10px;
    box-shadow:0 1px 3px rgba(15,23,42,.03);
}
.st-key-aria_workflow_guide summary { color:#145b6e; padding:13px 14px; }
.st-key-aria_workflow_guide summary:hover { background:#f0f7f9; border-radius:10px; }
.st-key-aria_workflow_guide summary p { color:#145b6e !important; font-size:13px !important; font-weight:600; }
.st-key-aria_workflow_guide p, .st-key-aria_workflow_guide li { font-size:12px; line-height:1.7; }

/* The host application's return action, above the ARIA banner. */
.st-key-aria_return_to_ecw button {
    background:#ffffff !important; color:#145b6e !important;
    border:1px solid #cbd5e1 !important; border-radius:999px !important;
    padding:7px 14px !important; min-height:36px;
    font-size:13px !important; font-weight:650 !important;
    box-shadow:0 1px 3px rgba(15,23,42,.07) !important;
    transition:background-color .15s ease,border-color .15s ease,box-shadow .15s ease;
}
.st-key-aria_return_to_ecw button p { color:inherit !important; font-size:inherit !important; font-weight:inherit !important; }
.st-key-aria_return_to_ecw button:hover {
    background:#f0f7f9 !important; border-color:#145b6e !important;
    box-shadow:0 2px 5px rgba(20,91,110,.12) !important;
}
.st-key-aria_return_to_ecw button:focus-visible { outline:2px solid #145b6e !important; outline-offset:3px; }
@media (max-width:640px) {
    .st-key-view div[role="radiogroup"] label { padding:9px 12px !important; }
    .st-key-aria_return_to_ecw button { text-align:left; }
}
</style>
"""

PALETTE = {
    "petrol": "#0E3A46", "teal": "#1E7A8C", "aqua": "#57C4C9",
    "gold": "#E8B04B", "ink": "#12262B", "mist": "#E8F1F2",
}

# Shared card styling is also used by Ask ARIA without the dashboard theme.
# The interaction rules appended below deliberately unify input focus globally.
EVIDENCE_STYLE = """
<style>
.aria-evidence-card { background:#fff; border:1px solid #dbe7e9; border-radius:14px;
    padding:18px 20px; margin:12px 0; box-shadow:0 2px 7px rgba(14,58,70,.04); }
.aria-evidence-heading { display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px; }
.aria-evidence-rating { display:inline-flex; align-items:center; gap:9px; white-space:nowrap; }
.aria-evidence-stars { font-size:20px; line-height:1.25; letter-spacing:1px; white-space:nowrap; }
.aria-evidence-filled { color:#f59e0b; }
.aria-evidence-empty { color:#cbd5e1; }
.aria-evidence-score { color:#334155; font-size:13px; font-weight:700; }
.aria-evidence-pill { display:inline-block; color:#155c6b; background:#eaf4f5;
    border:1px solid #d3e6e8; border-radius:999px; padding:4px 10px;
    font-size:12px; line-height:1.4; font-weight:600; }
.aria-evidence-title { color:#0e3a46; font-weight:650; font-size:16px; line-height:1.5; margin:6px 0; }
.aria-evidence-title a { color:#0e3a46; text-decoration:none; }
.aria-evidence-title a:hover { text-decoration:underline; }
.aria-evidence-meta { color:#64748b; font-size:12px; margin:5px 0 12px; }
.aria-evidence-appraisal { background:#f6fafb; border-left:3px solid #1e7a8c;
    border-radius:0 7px 7px 0; padding:10px 12px; color:#334155; font-size:13px; line-height:1.65; }
.aria-evidence-appraisal strong { color:#155c6b; }
.aria-evidence-limitations { color:#64748b; font-size:12px; line-height:1.55; margin:9px 0; }
.aria-evidence-abstract { color:#334155; font-size:13px; line-height:1.7; margin-top:12px; }
.aria-evidence-abstract summary { color:#155c6b; cursor:pointer; font-weight:600; }
.aria-evidence-abstract p { white-space:pre-line; margin:9px 0 0; }
.aria-evidence-legend { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
    padding:12px 15px; margin:0 0 14px; color:#475569; font-size:12px; line-height:1.7; }
.aria-evidence-legend summary { cursor:pointer; color:#0e3a46; font-weight:650; font-size:13px; }
.aria-evidence-legend-row { display:flex; gap:12px; align-items:baseline; margin-top:6px; }
.aria-evidence-legend .aria-evidence-stars { font-size:15px; flex:0 0 90px; }
.aria-evidence-legend p { margin:9px 0 0; }
.aria-evidence-citation { display:inline; font-size:.91em; line-height:1.8; color:#475569;
    background:#fffaf0; border:1px solid #f5e5c5; border-radius:6px; padding:2px 5px;
    -webkit-box-decoration-break:clone; box-decoration-break:clone; }
.aria-evidence-citation a { color:#155c6b; font-weight:600; text-decoration:none; }
.aria-evidence-citation a:hover { text-decoration:underline; }
.aria-evidence-citation .aria-evidence-stars { font-size:1em; letter-spacing:.3px; }
.aria-evidence-citation .aria-evidence-score { font-size:.95em; }
.aria-evidence-source { background:#eff6ff; border-color:#bfdbfe; color:#0369a1; }
.aria-evidence-citation.knowledge { background:#f0f9ff; border-color:#bae6fd; }
.aria-evidence-passage { border-left:3px solid #7dd3fc; padding:8px 12px; margin:9px 0;
    background:#f0f9ff; white-space:pre-wrap; font-size:13px; line-height:1.7; color:#334155; }
.aria-evidence-passage strong { color:#075985; }
.aria-evidence-primary { color:#64748b; font-size:12px; line-height:1.6; margin:10px 0 0; }
.aria-evidence-primary strong { color:#075985; }
.aria-evidence-primary ul { margin:5px 0 0; padding-left:18px; }
.aria-evidence-primary li { margin:3px 0; }
.aria-evidence-primary a { color:#0369a1; text-decoration:none; overflow-wrap:anywhere; }
.aria-evidence-primary a:hover { text-decoration:underline; }
@media (max-width:640px) { .aria-evidence-card { padding:14px; } }
</style>
"""

EVIDENCE_STYLE += INTERACTION_STYLE


def _evidence_helpers():
    # Support both the package integration and `streamlit run professor_aria/app.py`.
    if __package__:
        from .evidence_appraisal import appraise_article, appraise_articles
        from .evidence_citations import canonicalize_citations, format_citation
    else:
        from evidence_appraisal import appraise_article, appraise_articles
        from evidence_citations import canonicalize_citations, format_citation
    return appraise_article, appraise_articles, canonicalize_citations, format_citation


def _star_html(rating):
    """Only controlled markup goes into the HTML rendering paths below."""
    rating = min(5, max(1, int(rating)))
    return (
        f'<span class="aria-evidence-stars" role="img" aria-label="{rating} out of 5 stars">'
        f'<span class="aria-evidence-filled">{"★" * rating}</span>'
        f'<span class="aria-evidence-empty">{"☆" * (5 - rating)}</span></span>'
    )


def combined_evidence_sources(literature):
    """One catalog for source counts, citations, and cards in all ARIA views."""
    literature = literature or {}
    return list(literature.get("sources") or []) + list(literature.get("knowledge_sources") or [])


def _knowledge_helpers():
    if __package__:
        from .knowledge_citations import canonicalize_knowledge_citations, knowledge_citation_catalog
    else:
        from knowledge_citations import canonicalize_knowledge_citations, knowledge_citation_catalog
    return canonicalize_knowledge_citations, knowledge_citation_catalog


def _knowledge_anchor(source):
    identifier = str(source.get("document_id") or source.get("id") or source.get("filename") or source.get("title"))
    return "aria-kb-" + hashlib.sha256(identifier.encode()).hexdigest()[:16]


_PRIMARY_REFERENCE_HOSTS = frozenset({
    "professional.heart.org", "neuropt.org", "www.neuropt.org",
    "neuropt-website-documents.s3.amazonaws.com", "www.asha.org", "journals.sagepub.com",
})


def _safe_primary_reference_url(url):
    """Only the curated library's primary publishers can supply outbound links."""
    if not isinstance(url, str) or any(ord(char) < 33 or char in '<>"\'\\' for char in url):
        return ""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in _PRIMARY_REFERENCE_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)):
            return ""
    except ValueError:
        return ""
    return url


def _primary_reference_links_html(source, passage=None, *, include_all=True):
    """Link curated summaries back to their original primary source material."""
    if source.get("source_type") != "builtin_reference":
        return ""
    references = [ref for ref in source.get("references", []) if isinstance(ref, dict)]
    by_url = {ref.get("url"): ref for ref in references if isinstance(ref.get("url"), str)}
    candidates = []
    if passage and passage.get("url"):
        reference = by_url.get(passage["url"], {})
        candidates.append((passage["url"], reference.get("title") or passage.get("section") or "Read the primary source"))
    if include_all:
        candidates.extend((ref.get("url"), ref.get("title") or ref.get("publisher") or "Read the primary source")
                          for ref in references)
    if not candidates and source.get("url"):
        reference = by_url.get(source["url"], {})
        candidates.append((source["url"], reference.get("title") or "Read the primary source"))
    links, seen = [], set()
    for url, title in candidates:
        url = _safe_primary_reference_url(url)
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(
            '<li><a href="' + html.escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">'
            + html.escape(str(title), quote=True) + '</a></li>'
        )
    if not links:
        return ""
    return ('<div class="aria-evidence-primary"><strong>Primary source material:</strong><ul>'
            + "".join(links) + "</ul></div>")


def _evidence_card_html(source):
    appraise_article, _, _, _ = _evidence_helpers()
    source = appraise_article(source)
    escape = lambda value: html.escape(str(value), quote=True)
    score = source["star_rating"]
    pmid = str(source.get("pmid", "")).strip()
    local_source = source.get("source_type") in {"uploaded_pdf", "builtin_reference"}
    title = escape(source.get("title") or source.get("filename") or "Untitled article")
    if not local_source and re.fullmatch(r"\d+", pmid):
        title = f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" rel="noopener noreferrer">{title}</a>'
    design = str(source["study_design"])
    sample = source.get("sample_size")
    design_detail = design + (f" · N={sample}" if sample is not None else "")
    if local_source:
        meta = (str(source.get("filename") or "Uploaded PDF") + f" · {source.get('page_count', 0)} pages"
                if source.get("source_type") == "uploaded_pdf" else "Fixed CPG reference · curated summary, not an original guideline PDF")
    else:
        meta = "PMID: " + (pmid or "unavailable")
    if source.get("facets"):
        meta += " · Search dimensions: " + ", ".join(str(f).replace("_", " ") for f in source["facets"])
    limitations = source.get("appraisal_limitations") or []
    limits_html = (
        '<div class="aria-evidence-limitations"><strong>Appraisal limits:</strong> '
        + escape(" ".join(str(item) for item in limitations)) + "</div>"
        if limitations else ""
    )
    if local_source:
        passages_html = ""
        for passage in source.get("passages", []):
            page = passage.get("page_number")
            location = f"Page {page}" if page is not None else passage.get("section") or "Curated reference summary"
            passages_html += (
                '<div class="aria-evidence-passage"><strong>' + escape(location) + ":</strong> "
                + escape(passage.get("text", ""))
                + _primary_reference_links_html(source, passage, include_all=False) + "</div>"
            )
        detail_html = ('<details class="aria-evidence-abstract"><summary>Read retrieved passages</summary>'
                       + passages_html + "</details>") if passages_html else ""
    else:
        detail_html = ('<details class="aria-evidence-abstract"><summary>Read abstract</summary><p>'
                       + escape(source.get("abstract") or "No abstract available.") + "</p></details>")
    source_badge = ('<span class="aria-evidence-pill aria-evidence-source">Source: Evidence Bridge Knowledge Base</span>'
                    if local_source else "")
    anchor = f' id="{_knowledge_anchor(source)}"' if local_source else ""
    return (
        f'<article class="aria-evidence-card"{anchor}>'
        '<div class="aria-evidence-heading"><span class="aria-evidence-rating">'
        + _star_html(score)
        + f'<span class="aria-evidence-score">{score}/5</span></span>'
        + f'<span class="aria-evidence-pill">{escape(source["evidence_level"])} · {escape(design)}</span>'
        + source_badge + '</div>'
        + f'<div class="aria-evidence-title">{title}</div>'
        + f'<div class="aria-evidence-meta">{escape(meta)}</div>'
        + '<div class="aria-evidence-appraisal"><strong>Methodological Appraisal:</strong> '
        + escape(design_detail) + " — " + escape(source["appraisal_rationale"]) + "</div>"
        + limits_html
        + _primary_reference_links_html(source)
        + detail_html + "</article>"
    )


def render_evidence_legend():
    """A compact explanation of the automated design/sample-size appraisal."""
    rows = (
        (5, "Level I-A · CPGs, systematic reviews, meta-analyses, Cochrane reviews"),
        (4, "Level I-B · Larger randomized trials (N ≥ 50) or multicenter RCTs"),
        (3, "Level II · Small RCTs (N < 50), prospective cohorts, clinical trials"),
        (2, "Level III–IV · Retrospective, case-control, cross-sectional, single-group studies"),
        (1, "Level V · Case reports, narrative reviews, opinion, animal or bench research"),
    )
    st.markdown(EVIDENCE_STYLE, unsafe_allow_html=True)
    content = "".join(
        f'<div class="aria-evidence-legend-row">{_star_html(score)}<span>{html.escape(label)}</span></div>'
        for score, label in rows
    )
    st.markdown(
        '<details class="aria-evidence-legend"><summary>ARIA Evidence Appraisal Scale '
        '(Design + Sample Size + Rigor)</summary>' + content
        + '<p>Automated design/sample appraisal; not a full GRADE certainty or PEDro assessment. '
        'Study quality, bias, and relevance still require clinical review.</p></details>',
        unsafe_allow_html=True,
    )


def render_evidence_card(source):
    """Render one source; all external metadata is escaped before HTML use."""
    st.markdown(EVIDENCE_STYLE, unsafe_allow_html=True)
    st.markdown(_evidence_card_html(source), unsafe_allow_html=True)


def render_evidence_sources(sources, *, show_legend=True):
    """Order cached as well as fresh evidence by grade and render source cards."""
    _, appraise_articles, _, _ = _evidence_helpers()
    if show_legend:
        render_evidence_legend()
    else:
        st.markdown(EVIDENCE_STYLE, unsafe_allow_html=True)
    for source in appraise_articles(sources or []):
        st.markdown(_evidence_card_html(source), unsafe_allow_html=True)


def _guidance_markup(text, sources=None):
    """Keep Markdown, escape model HTML, and style only source-verified citations."""
    _, appraise_articles, canonicalize_citations, format_citation = _evidence_helpers()
    appraised_sources = appraise_articles(sources or [])
    sources_by_pmid = {str(s["pmid"]): s for s in appraised_sources if s.get("pmid")}
    knowledge_sources = [s for s in appraised_sources if s.get("source_type") in {"uploaded_pdf", "builtin_reference"}]
    knowledge_catalog = {}
    if sources is not None:
        text = canonicalize_citations(text, list(sources_by_pmid.values()))
        if knowledge_sources or any(marker in text for marker in ("[KB:", "(Uploaded PDF:", "(Fixed CPG:", "(Fixed CPG Reference:")):
            canonicalize_knowledge_citations, knowledge_citation_catalog = _knowledge_helpers()
            text = canonicalize_knowledge_citations(text, knowledge_sources)
            knowledge_catalog = knowledge_citation_catalog(knowledge_sources)
    # A bare '>' remains safe without '<' and retains Markdown blockquotes.
    escaped = html.escape(str(text), quote=False).replace("&gt;", ">")
    citation_pattern = re.compile(r"\(PMID:\s*(\d+)\s*·\s*[★☆]{5}\s+\d/5\s*·\s*[^)\n]+\)")

    def badge(match):
        source = sources_by_pmid.get(match.group(1))
        if source is None:
            return match.group(0)
        score = source["star_rating"]
        label = format_citation(source).split(" · ", 2)[-1].removesuffix(")")
        return (
            '<span class="aria-evidence-citation">('
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{match.group(1)}/" target="_blank" rel="noopener noreferrer">PMID: {match.group(1)}</a>'
            + " · " + _star_html(score)
            + f' <span class="aria-evidence-score">{score}/5</span>'
            + " · " + html.escape(label) + ")</span>"
        )

    local_badges = {}
    for citation, (source, _passage) in knowledge_catalog.items():
        escaped_citation = html.escape(citation, quote=False).replace("&gt;", ">")
        score = source["star_rating"]
        citation_html = re.sub(
            r"[★☆]{5}\s+\d/5", _star_html(score) + f' <span class="aria-evidence-score">{score}/5</span>',
            escaped_citation, count=1,
        )
        local_badges[escaped_citation] = '<span class="aria-evidence-citation knowledge">' + citation_html + "</span>"
    local_pattern = (re.compile("|".join(re.escape(key) for key in sorted(local_badges, key=len, reverse=True)))
                     if local_badges else None)
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]*`)", escaped)
    def style_part(part):
        part = citation_pattern.sub(badge, part)
        return local_pattern.sub(lambda match: local_badges[match.group(0)], part) if local_pattern else part
    return "".join(part if index % 2 else style_part(part) for index, part in enumerate(parts))


def render_guidance_markdown(text, sources=None):
    """Guidance retains its normal Markdown with matching inline evidence badges."""
    st.markdown(EVIDENCE_STYLE, unsafe_allow_html=True)
    st.markdown(_guidance_markup(text, sources), unsafe_allow_html=True)


def inject_style():
    """Fonts, colors, and header styling. Call once, right after
    st.set_page_config()."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', -apple-system, Segoe UI, sans-serif; }

        /* Page background — aimed at the app container so it actually takes,
           with a tint that is clearly not white. */
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        .stApp,
        body { background-color: #E8F1F2 !important; }
        [data-testid="stHeader"] { background: transparent !important; }
        iframe { background-color: transparent !important; border: none !important; }

        h1, h2, h3, h4 { color: #0E3A46 !important; font-weight: 700; letter-spacing: 0.2px; }
        a { color: #155C6B; }

        /* teal buttons (covers normal buttons and form submit buttons) */
        .stButton > button, .stFormSubmitButton > button {
            background-color: #1E7A8C !important; color: #FFFFFF !important; border: none !important;
            border-radius: 8px !important; font-weight: 600 !important; padding: 0.45rem 1.1rem !important;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover { background-color: #155C6B !important; }

        /* cleaner product feel: hide the default menu + footer.
           Delete these two lines if you ever want them back. */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* ARIA note-summary card */
        .aria-summary {
            background:#FFFFFF; border:1px solid #CBDEDE; border-left:4px solid #1E7A8C;
            border-radius:10px; padding:14px 18px;
        }
        .aria-sum-lead { color:#0E3A46; font-weight:600; margin-bottom:10px; }
        .aria-sum-row { display:flex; gap:14px; padding:6px 0; border-top:1px solid #EEF4F4; }
        .aria-sum-row:first-of-type { border-top:none; }
        .aria-sum-label { flex:0 0 160px; color:#155C6B; font-weight:600; font-size:13.5px; }
        .aria-sum-val { color:#12262B; font-size:14px; line-height:1.5; }

        /* ARIA header band */
        .aria-hero {
            display: flex; align-items: center; gap: 18px;
            background: linear-gradient(105deg, #0E3A46 0%, #155C6B 55%, #1E7A8C 100%);
            border-radius: 16px; padding: 22px 30px; margin: 0 0 16px 0;
            border-bottom: 3px solid #E8B04B;
            box-shadow: 0 6px 20px rgba(14,58,70,0.18);
        }
        .aria-hero img { width: 78px; height: 78px; flex: 0 0 auto; }
        .aria-hero .word { font-weight: 700; font-size: 46px; letter-spacing: 5px; color: #FFFFFF; line-height: 1.02; }
        .aria-hero .tag { font-size: 18.5px; font-weight: 500; color: #9FD9DC; margin-top: 4px; }
        .aria-hero .val { font-size: 14px; color: #CDEBEC; margin-top: 6px; opacity: 0.92; }
        /* patient header card (Executive Chart) */
        .aria-patient { background:#FFFFFF; border:1px solid #CBDEDE; border-left:4px solid #E8B04B;
            border-radius:12px; padding:16px 20px; margin-bottom:14px; }
        .aria-patient .pname { font-size:20px; font-weight:700; color:#0E3A46; }
        .aria-patient .pmeta { font-size:13px; color:#5A7A80; margin-top:2px; }
        .aria-patient .pdx { font-size:14px; color:#12262B; margin-top:10px; }
        .aria-patient .pdx b { color:#155C6B; }
        /* metric chips */
        .aria-chips { display:flex; flex-wrap:wrap; gap:10px; margin:4px 0 12px; }
        .aria-chip { background:#EAF3F4; border:1px solid #CBDEDE; border-radius:999px;
            padding:6px 14px; font-size:13px; color:#12262B; }
        .aria-chip b { color:#155C6B; }
        /* input contrast: make fields stand out from the tinted page */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            background-color:#FFFFFF !important; border:1px solid #A9C9CD !important;
            border-radius:8px !important; box-shadow:0 1px 2px rgba(14,58,70,0.06) !important;
        }
        [data-baseweb="select"] > div { background-color:#FFFFFF !important; border-color:#A9C9CD !important; }
        [data-baseweb="base-input"] { background-color:#FFFFFF !important; }
        /* ARIA speaking directly to the user */
        .aria-ask { display:flex; align-items:flex-start; gap:12px; background:#FFFFFF;
            border:1px solid #CBDEDE; border-left:4px solid #1E7A8C; border-radius:10px;
            padding:14px 16px; margin:6px 0; }
        .aria-ask img { width:34px; height:34px; flex:0 0 auto; margin-top:1px; }
        .aria-ask .q { color:#0E3A46; font-size:15px; font-weight:600; line-height:1.5; }

        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(INTERACTION_STYLE, unsafe_allow_html=True)
    st.markdown(WORKSPACE_STYLE, unsafe_allow_html=True)


def render_header(value_line="Your clinical thinking partner for rehabilitation decisions."):
    """The ARIA header band. Call once, near the top of the page."""
    st.markdown(
        f'''
        <div class="aria-hero">
            <img src="{PAGE_ICON}" alt="ARIA"/>
            <div>
                <div class="word">ARIA</div>
                <div class="tag">Adaptive Rehabilitation Intelligence Assistant</div>
                <div class="val">{value_line}</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
