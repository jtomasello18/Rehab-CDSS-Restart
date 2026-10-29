import re
import html
import random
import datetime
import os
import hashlib
import streamlit as st
import pandas as pd
from professor_aria.vignette import ED_VANCE_NOTE
from professor_aria.branding import (
    PAGE_ICON, inject_style, render_header, render_evidence_legend,
    render_evidence_sources, render_guidance_markdown, combined_evidence_sources, chat_avatar,
)

parse_clinician_note = None
retrieve_literature_smart = None
generate_clarifying_question = None
generate_response = None
continue_conversation = None
log_interaction = None


def _load_professor_engine():
    global parse_clinician_note, retrieve_literature_smart, generate_clarifying_question
    global generate_response, continue_conversation, log_interaction

    if parse_clinician_note is not None:
        return True
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        try:
            anthropic_key = str(st.secrets.get("ANTHROPIC_API_KEY", "")).strip()
        except Exception:
            anthropic_key = ""
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    if not anthropic_key or anthropic_key == "your_actual_api_key_here":
        return False

    from professor_aria.intake import parse_clinician_note as parse_note
    from professor_aria.rag import retrieve_literature_smart as retrieve_literature, generate_clarifying_question as ask_question
    from professor_aria.literacy_engine import generate_response as generate, continue_conversation as continue_chat
    from professor_aria.log import log_interaction as log

    parse_clinician_note = parse_note
    retrieve_literature_smart = retrieve_literature
    generate_clarifying_question = ask_question
    generate_response = generate
    continue_conversation = continue_chat
    log_interaction = log
    return True

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_CLARIFYING_ROUNDS = 3

CONFIRM_PROMPTS = [
    "This is what I understand to be the primary issues. Is this correct and complete?",
    "Here's what I'm hearing as the main picture. Does that look right, and is anything missing?",
    "This is how I'm reading the note so far. Have I captured it correctly, and is there anything to add?",
    "Here's what stands out to me as the key points. Does this match your read, and is it complete?",
    "This is my understanding of what matters most here. Is that accurate, and have I left anything out?",
    "Here's the gist of what I'm taking from this. Correct me if I've got something wrong or missed something.",
]

TIER_MAP = {
    "Let ARIA decide": None,
    "Quick check": 1,
    "Explore options": 2,
    "Deep teaching": 3,
}

LEVEL_DESCRIPTIONS = {
    "Let ARIA decide": "I'll choose the depth based on your note.",
    "Quick check": "I'll confirm the diagnosis and surface the key evidence, briefly.",
    "Explore options": "I'll walk through the main options and what the research shows.",
    "Deep teaching": "I'll give a fuller teaching response with the reasoning explained.",
}

V_INTAKE = "Evidence Query"
V_PROGRESS_NOTE = "Patient Tracker"
V_MEASURES_TRENDS = "Measures & Trends"
V_SCRIBE = "ARIA Scribe"
V_EDUCATION = "ARIA Education"
V_EVIDENCE_BRIDGE = "Evidence Bridge"
V_EVIDENCE = "Evidence & Guidance"
VIEWS = [V_PROGRESS_NOTE, V_MEASURES_TRENDS, V_EVIDENCE_BRIDGE, V_INTAKE, V_EVIDENCE, V_SCRIBE, V_EDUCATION]

ECW_CLINICAL_NOTE = ED_VANCE_NOTE
_LEGACY_NOTE_HASH = "39c47ee876da733e543d3a5182a3e86140c58a4724b258c2f790cf2124fcc996"

# Optional guided-intake questions. All skippable.
INTAKE_FIELDS = [
    ("age_sex", "Age and sex", "e.g., 67-year-old male"),
    ("diagnosis", "Primary problem or diagnosis", "e.g., left MCA ischemic stroke, right hemiparesis"),
    ("history", "Brief history / onset", "e.g., 12 weeks post-stroke, moving to outpatient"),
    ("goals", "Patient goals", "e.g., walk to the mailbox; self-feed with right hand"),
    ("precautions", "Safety concerns or precautions", "e.g., two near-falls this week; foot drop"),
    ("measures", "Key standardized measures", "e.g., BBS 38/56; 10MWT 0.35 m/s; FMA-UE 22/66"),
    ("medications", "Current medications", "e.g., Baclofen 10 mg TID"),
    ("focus", "What would you like my help with?", "e.g., prioritizing gait vs. UE work"),
]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def split_question(text: str):
    match = re.search(r"\*\*Question for you:\*\*\s*(.+)", text, re.DOTALL)
    if match:
        question = match.group(1).strip()
        main_text = text[:match.start()].strip()
        return main_text, question
    return text, None


def render_aria_question(text: str):
    """Render a question as ARIA speaking directly to the clinician."""
    st.markdown(
        f'<div class="aria-ask"><img src="{PAGE_ICON}" alt="ARIA"/>'
        f'<div class="q">{html.escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def render_aria_message(text: str, sources=None):
    main_text, question = split_question(text)
    render_guidance_markdown(main_text, sources)
    if question:
        render_aria_question(question)


def _humanize_key(k: str) -> str:
    return k.replace("_", " ").strip().capitalize()


def _format_value(v):
    if isinstance(v, (list, tuple)):
        items = [str(x).strip() for x in v if str(x).strip()]
        return ", ".join(items) if items else None
    if isinstance(v, dict):
        parts = []
        for kk, vv in v.items():
            fv = _format_value(vv)
            if fv:
                parts.append(f"{_humanize_key(kk)}: {fv}")
        return "; ".join(parts) if parts else None
    s = str(v).strip()
    if not s or s.lower() in ("none", "null", "n/a", "na", "unknown", "not specified"):
        return None
    return s


def render_clinical_summary(parsed: dict, lead: str = None):
    skip = {"error"}
    rows = []
    for k, v in (parsed or {}).items():
        if k in skip:
            continue
        fv = _format_value(v)
        if fv:
            rows.append((_humanize_key(k), fv))

    if not rows:
        st.info("I couldn't pull additional structured details from this note.")
        return

    lead_html = f'<div class="aria-sum-lead">{html.escape(lead)}</div>' if lead else ""
    row_html = "".join(
        f'<div class="aria-sum-row">'
        f'<span class="aria-sum-label">{html.escape(label)}</span>'
        f'<span class="aria-sum-val">{html.escape(value)}</span>'
        f'</div>'
        for label, value in rows
    )
    st.markdown(f'<div class="aria-summary">{lead_html}{row_html}</div>', unsafe_allow_html=True)


def render_level_selector(case):
    """Prominent, always-visible choice of how much detail ARIA gives."""
    with st.container(border=True):
        st.markdown("**How would you like ARIA to work with you?**")
        choice = st.radio(
            "ARIA level",
            list(TIER_MAP.keys()),
            key=f"tier_{case['id']}",
            horizontal=True,
            label_visibility="collapsed",
        )
        case["tier_choice_value"] = TIER_MAP[choice]
        st.caption(LEVEL_DESCRIPTIONS.get(choice, ""))


def compose_note(name, answers):
    order = [
        ("age_sex", "Age/Sex"),
        ("diagnosis", "Primary problem / diagnosis"),
        ("history", "History"),
        ("goals", "Patient goals"),
        ("precautions", "Safety / precautions"),
        ("measures", "Standardized measures"),
        ("medications", "Current medications"),
        ("focus", "Requested focus"),
    ]
    lines = []
    if name:
        lines.append(f"Patient: {name}")
    for k, label in order:
        v = (answers.get(k) or "").strip()
        if v:
            lines.append(f"{label}: {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Standardized-measure extraction (Measures & Trends tab)
# ---------------------------------------------------------------------------
def extract_metrics(text: str):
    if not text:
        return []
    def last_match(pattern, text, flags=0):
        matches = list(re.finditer(pattern, text, flags))
        return matches[-1] if matches else None

    t = text.replace("\u2013", "-").replace("\u2014", "-")
    found = []

    def add(measure, result, max_score=None, detail=""):
        pct = None
        try:
            if max_score:
                num = float(str(result).split("/")[0])
                pct = round(num / float(max_score) * 100)
        except Exception:
            pct = None
        found.append({"measure": measure, "result": str(result),
                      "max": max_score, "pct": pct, "detail": detail})

    m = last_match(r"(?:Berg Balance(?:\s*Scale)?|BBS)\D{0,20}?(\d{1,3})\s*/\s*(\d{1,3})", t, re.I)
    if m:
        add("Berg Balance Scale (BBS)", f"{m.group(1)}/{m.group(2)}", int(m.group(2)),
            "High fall risk below 45")

    m = last_match(r"(?:Fugl-?Meyer[^\d/]{0,30}|FMA[-\s]?UE\D{0,12})(\d{1,3})\s*/\s*(\d{1,3})", t, re.I)
    if m:
        add("Fugl-Meyer Upper Extremity (FMA-UE)", f"{m.group(1)}/{m.group(2)}", int(m.group(2)),
            "Lower score = more severe motor impairment")

    m = last_match(r"(?:10[-\s]?Meter Walk Test|10MWT|gait speed)\D{0,25}?(\d+(?:\.\d+)?)\s*m\s*/?\s*s", t, re.I)
    if m:
        add("10-Meter Walk Test (10MWT)", f"{m.group(1)} m/s", None,
            "Community ambulation typically >0.8 m/s")

    m = last_match(r"(?:Timed Up (?:and|&) Go|TUG)\D{0,20}?(\d+(?:\.\d+)?)\s*s", t, re.I)
    if m:
        add("Timed Up and Go (TUG)", f"{m.group(1)} s", None, "Fall risk often >13.5 s")

    m = last_match(r"(?:6[-\s]?Minute Walk Test|6MWT)\D{0,20}?(\d+(?:\.\d+)?)\s*m\b", t, re.I)
    if m:
        add("6-Minute Walk Test (6MWT)", f"{m.group(1)} m", None, "Endurance / distance")

    for gm in re.finditer(r"Grade\s*([0-4]\+?)\s*(?:in\s*)?([A-Za-z][A-Za-z /]+?)(?=[;.\n]|$)", t, re.I):
        add("Modified Ashworth", f"Grade {gm.group(1)}", None, gm.group(2).strip())

    for bm in re.finditer(r"(Right|Left)?\s*(UE|LE|Upper Extremity|Lower Extremity)[:\s]*Stage\s*([1-7])", t, re.I):
        side = (bm.group(1) or "").strip()
        limb = bm.group(2).upper().replace("UPPER EXTREMITY", "UE").replace("LOWER EXTREMITY", "LE")
        label = f"{side} {limb}".strip()
        add("Brunnstrom Stage", f"Stage {bm.group(3)}", None, label)

    return found


# ---------------------------------------------------------------------------
# Patient-case model (in-session)
# ---------------------------------------------------------------------------
def blank_case(cid, name):
    return {
        "id": cid,
        "name": name or cid,
        "created": datetime.datetime.now().strftime("%b %d, %Y %I:%M %p"),
        "edit_rev": 0,
        "note": "",
        "parsed": None,
        "metrics": [],
        "confirm_prompt": "",
        "confirmed": False,
        "tier_choice_value": None,
        "clarifications": [],
        "pending_question": None,
        "literature": None,
        "responded": False,
        "response_error": None,
        "tier_used": None,
        "tier_rationale": None,
        "conversation": [],
    }


def ensure_state():
    if "cases" not in st.session_state:
        st.session_state.cases = {}
    if "case_order" not in st.session_state:
        st.session_state.case_order = []
    if "case_counter" not in st.session_state:
        st.session_state.case_counter = 0
    if "CASE-0001" not in st.session_state.cases:
        st.session_state.cases["CASE-0001"] = blank_case("CASE-0001", "Ed Vance")
        st.session_state.case_order.insert(0, "CASE-0001")
    ed_case = st.session_state.cases["CASE-0001"]
    ed_case["name"] = "Ed Vance"
    old_seed = hashlib.sha256(str(ed_case.get("note", "")).encode()).hexdigest() == _LEGACY_NOTE_HASH
    if not ed_case.get("note") or old_seed:
        ed_case["note"] = ECW_CLINICAL_NOTE
    if old_seed:
        # Refresh only the exact previous demo seed; preserve clinician-edited notes.
        draft_key = "note_CASE-0001"
        if hashlib.sha256(str(st.session_state.get(draft_key, "")).encode()).hexdigest() == _LEGACY_NOTE_HASH:
            st.session_state[draft_key] = ECW_CLINICAL_NOTE
        for field in ("parsed", "literature", "pending_question", "response_error", "tier_used"):
            ed_case[field] = None
        ed_case.update(confirmed=False, responded=False, metrics=[], conversation=[], clarifications=[])
    if st.session_state.get("case_picker") not in st.session_state.cases:
        st.session_state.case_picker = "CASE-0001"
    legacy_views = {
        "EHR Sync & Intake": V_INTAKE,
        "EHR Sync": V_INTAKE,
        "Patient Biometrics": V_MEASURES_TRENDS,
        "Charting": V_SCRIBE,
        "ARIA Chart": V_SCRIBE,
        "Literature & Evidence": V_EVIDENCE_BRIDGE,
    }
    if st.session_state.get("view") in legacy_views:
        st.session_state.view = legacy_views[st.session_state.view]
    if st.session_state.get("view") not in VIEWS:
        st.session_state.view = V_PROGRESS_NOTE


def create_case(name):
    st.session_state.case_counter += 1
    cid = f"CASE-{st.session_state.case_counter:04d}"
    st.session_state.cases[cid] = blank_case(cid, name)
    st.session_state.case_order.append(cid)
    st.session_state.case_picker = cid
    return cid


def active_case():
    cid = st.session_state.get("case_picker")
    if cid and cid in st.session_state.cases:
        return st.session_state.cases[cid]
    return None


# ---------------------------------------------------------------------------
# Literature helpers
# ---------------------------------------------------------------------------
def advance_search(case):
    literature = retrieve_literature_smart(case["note"], case["parsed"], case["clarifications"])
    if combined_evidence_sources(literature) or literature.get("retrieval_error") or len(case["clarifications"]) >= MAX_CLARIFYING_ROUNDS:
        case["literature"] = literature
    else:
        case["pending_question"] = generate_clarifying_question(
            case["note"], case["parsed"], case["clarifications"]
        )


def finalize_response(case):
    literature = case["literature"]
    result = generate_response(case["parsed"], literature, case["note"], tier=case["tier_choice_value"])
    case["responded"] = True
    if result.get("tier_used") is None:
        case["tier_used"] = None
        case["response_error"] = result.get("response_text", "I wasn't able to generate a response.")
        return
    case["tier_used"] = result["tier_used"]
    case["tier_rationale"] = result.get("tier_rationale")
    case["conversation"] = [
        {"role": "user", "content": case["note"]},
        {"role": "assistant", "content": result["response_text"]},
    ]
    log_interaction({
        "type": "initial_response",
        "case_id": case["id"],
        "note": case["note"],
        "clarifications": case["clarifications"],
        "search_query": literature.get("query_used"),
        "tier_used": result["tier_used"],
        "tier_rationale": result.get("tier_rationale"),
        "response": result["response_text"],
    })


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    # Only Ed's chart is connected in this pilot; the other cards are read-only.
    st.session_state.case_picker = "CASE-0001"
    with st.sidebar:
        st.markdown(
            '''<section class="aria-caseload" aria-label="Active caseload">
              <div class="aria-caseload-heading">ACTIVE CASELOAD · OUTPATIENT REHAB</div>
              <p class="aria-caseload-subtitle">Synced with eClinicalWorks 11e</p>
              <article class="aria-caseload-card is-active" aria-label="Ed Vance, active chart">
                <div class="aria-caseload-card-top"><strong>Ed Vance</strong><span class="aria-caseload-badge">ACTIVE CHART</span></div>
                <p class="aria-caseload-meta">67M · MRN 482910</p>
                <p class="aria-caseload-detail">Post-L MCA Stroke · 3:00 PM Outpatient Eval</p>
              </article>
              <article class="aria-caseload-card" aria-label="Maria Chen, checked out">
                <div class="aria-caseload-card-top"><strong>Maria Chen</strong></div>
                <p class="aria-caseload-meta">58F · MRN 391044</p>
                <p class="aria-caseload-detail">Initial PT Eval · 9:00 AM · Checked Out</p>
              </article>
              <article class="aria-caseload-card" aria-label="James Wilson, signed">
                <div class="aria-caseload-card-top"><strong>James Wilson</strong></div>
                <p class="aria-caseload-meta">71M · MRN 510298</p>
                <p class="aria-caseload-detail">OT Upper Extremity Tx · 10:30 AM · Signed</p>
              </article>
            </section>''',
            unsafe_allow_html=True,
        )
        with st.container(key="aria_workflow_guide"):
            with st.expander("Clinical Workflow Guide"):
                st.markdown(
                    "- Patient chart and MA triage data are automatically synced from eClinicalWorks (eCW).\n"
                    "- **Evidence Query**: review the synced note, choose how much detail you want, "
                    "then have me read it back to confirm.\n"
                    "- **Evidence Bridge**: upload PDFs, explore the knowledge base, and ask source-grounded questions.\n"
                    "- **Evidence & Guidance**: I search PubMed and Evidence Bridge, then talk it through; reply with follow-ups.\n"
                    "- **Patient Tracker**, **Measures & Trends**, and **ARIA Scribe** open the integrated clinical views.\n"
                    "- **ARIA Education**: practice case quizzes and track simulated learning progress.\n"
                    "- Practice and synthetic data only for this pilot."
                )


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def render_intake(case):
    st.markdown(f"##### Evidence Query · {case['name']}")
    st.info("Patient chart and MA triage data automatically synced from eClinicalWorks (MRN: 482910).")

    render_level_selector(case)

    note_key = f"note_{case['id']}"
    if note_key not in st.session_state:
        st.session_state[note_key] = case.get("note") or ECW_CLINICAL_NOTE
    note_val = st.text_area("Clinical note", key=note_key, height=220)
    case["note"] = note_val

    if st.button("Read it back to me", key=f"read_{case['id']}"):
        if not note_val.strip():
            st.warning("Please add the note first.")
        else:
            with st.spinner("Reading the note..."):
                parsed = parse_clinician_note(note_val)
            if parsed.get("error"):
                st.error(parsed["error"])
            else:
                case["parsed"] = parsed
                case["metrics"] = extract_metrics(note_val)
                case["confirm_prompt"] = random.choice(CONFIRM_PROMPTS)
                case["confirmed"] = False
                case["clarifications"] = []
                case["pending_question"] = None
                case["literature"] = None
                case["responded"] = False
                case["response_error"] = None
                case["tier_used"] = None
                case["conversation"] = []
                st.rerun()

    if case["parsed"] and not case["confirmed"]:
        st.write("")
        st.markdown(f"**{case['confirm_prompt']}**")
        render_clinical_summary(case["parsed"])
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Yes, that's correct", key=f"yes_{case['id']}"):
                case["confirmed"] = True
                st.session_state._goto_view = V_EVIDENCE
                st.rerun()
        with c2:
            if st.button("No, let me adjust something", key=f"no_{case['id']}"):
                case["parsed"] = None
                st.rerun()
    elif case["confirmed"]:
        st.success("Great, I've got the picture. Open Evidence & Guidance for my take.")
        render_clinical_summary(case["parsed"])


def render_executive(case):
    st.markdown("##### Overview")
    parsed = case.get("parsed") or {}
    dx = _format_value(parsed.get("diagnosis")) or "Not yet determined"
    st.markdown(
        f'<div class="aria-patient">'
        f'<div class="pname">{html.escape(case["name"])}</div>'
        f'<div class="pmeta">{html.escape(case["id"])} &nbsp;·&nbsp; created {html.escape(case["created"])}</div>'
        f'<div class="pdx"><b>Working diagnosis:</b> {html.escape(dx)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Edit patient details"):
        enk = f"editname_{case['id']}"
        if enk not in st.session_state:
            st.session_state[enk] = case["name"]
        st.text_input("Patient name or label", key=enk)

        base_rows = [{"Field": _humanize_key(k), "Value": _format_value(v) or ""}
                     for k, v in parsed.items() if k != "error"]
        if not base_rows:
            base_rows = [{"Field": "", "Value": ""}]
        edited = st.data_editor(
            pd.DataFrame(base_rows),
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            key=f"edit_tbl_{case['id']}_{case.get('edit_rev', 0)}",
        )
        st.caption("Edit a value, rename a field, add a row, or delete one. Then save.")
        if st.button("Save changes", key=f"savep_{case['id']}"):
            case["name"] = st.session_state[enk].strip() or case["name"]
            newp = {}
            for _, r in edited.iterrows():
                fld = str(r.get("Field", "")).strip()
                val = str(r.get("Value", "")).strip()
                if fld:
                    newp[fld.lower().replace(" ", "_")] = val
            if newp:
                case["parsed"] = newp
            case["edit_rev"] = case.get("edit_rev", 0) + 1
            st.success("Saved.")
            st.rerun()

    if not case["parsed"]:
        st.info("This patient is new. Head to the Intake tab to get started.")
        return

    if case.get("metrics"):
        chips = "".join(
            f'<span class="aria-chip"><b>{html.escape(m["measure"].split("(")[0].strip())}:</b> {html.escape(m["result"])}</span>'
            for m in case["metrics"][:6]
        )
        st.markdown(f'<div class="aria-chips">{chips}</div>', unsafe_allow_html=True)

    st.markdown("**The picture so far**")
    render_clinical_summary(case["parsed"])

    aria_msgs = [t["content"] for t in case.get("conversation", []) if t["role"] == "assistant"]
    if aria_msgs:
        main, q = split_question(aria_msgs[-1])
        st.markdown("**My latest guidance**")
        render_guidance_markdown(
            main[:700] + ("..." if len(main) > 700 else ""),
            (case.get("literature") or {}).get("sources", []),
        )
        if q:
            render_aria_question(q)
    else:
        st.caption("We haven't gotten to my guidance yet. Head to Evidence & Guidance and I'll pull the evidence.")


def render_graphical(case):
    st.markdown("##### Measures & Trends")
    if not case["parsed"]:
        st.info("Add and confirm a note in the Intake tab first.")
        return

    metrics = case.get("metrics") or []
    if not metrics:
        st.info("I didn't detect standardized measures in this note. As measures are added to the record, they'll appear here as tables and charts.")
        return

    df = pd.DataFrame([
        {"Measure": m["measure"], "Result": m["result"], "Site / notes": m["detail"]}
        for m in metrics
    ])
    st.dataframe(df, hide_index=True, width="stretch")

    pct_rows = [m for m in metrics if m["pct"] is not None]
    if pct_rows:
        chart_df = pd.DataFrame(
            {"Percent of maximum": [m["pct"] for m in pct_rows]},
            index=[m["measure"] for m in pct_rows],
        )
        st.bar_chart(chart_df)
        st.caption("Scored measures shown as a percent of their maximum. As this patient is reassessed over time, this is where progress trends will appear.")


def render_literature(case):
    st.markdown("##### Evidence & Guidance")
    if not case["confirmed"]:
        st.info("Let's confirm the note in the Intake tab first, then I'll pull the evidence.")
        return

    if case["literature"] is None and not case["pending_question"]:
        render_level_selector(case)
        st.write("I'll search PubMed and the Evidence Bridge knowledge base for evidence relevant to this patient, then talk it through with you at the level you chose above.")
        if st.button("Find the evidence", key=f"search_{case['id']}"):
            with st.spinner("Searching the medical literature..."):
                advance_search(case)
            st.rerun()
        return

    if case["pending_question"]:
        st.caption(f"Let me narrow this down ({len(case['clarifications']) + 1} of {MAX_CLARIFYING_ROUNDS}).")
        render_aria_question(case["pending_question"])
        ans = st.text_input("Your answer", key=f"clar_{case['id']}_{len(case['clarifications'])}")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Send answer", key=f"clarsub_{case['id']}"):
                if ans.strip():
                    case["clarifications"].append({"question": case["pending_question"], "answer": ans})
                    case["pending_question"] = None
                    with st.spinner("Refining the search..."):
                        advance_search(case)
                    st.rerun()
                else:
                    st.warning("Type an answer, or skip.")
        with c2:
            if st.button("Skip and proceed", key=f"clarskip_{case['id']}"):
                literature = retrieve_literature_smart(case["note"], case["parsed"], case["clarifications"])
                if not combined_evidence_sources(literature):
                    literature.setdefault("note", "Evidence coverage is incomplete; I'll identify where guidance relies on clinical reasoning.")
                case["literature"] = literature
                case["pending_question"] = None
                st.rerun()
        return

    if not case["responded"]:
        with st.spinner("Putting my thoughts together..."):
            finalize_response(case)
        st.rerun()

    if case["response_error"]:
        st.error(case["response_error"])
        if st.button("Try again", key=f"retry_{case['id']}"):
            case["literature"] = None
            case["responded"] = False
            case["response_error"] = None
            st.rerun()
        return

    literature = case["literature"]
    if literature.get("note"):
        st.info(literature["note"])
    st.caption(f"Detail level: {case['tier_used']}")
    st.divider()

    for turn in case["conversation"]:
        if turn["role"] == "assistant":
            with st.chat_message("assistant", avatar=chat_avatar("assistant")):
                render_aria_message(turn["content"], combined_evidence_sources(literature))
        else:
            with st.chat_message("user", avatar=chat_avatar("user")):
                st.markdown(turn["content"])

    num_sources = len(combined_evidence_sources(literature))
    with st.expander(f"The evidence I used ({num_sources} source(s))"):
        render_evidence_legend()
        st.markdown("**Sources:** PubMed via NCBI, and matched Evidence Bridge Knowledge Base references")
        if literature.get("query_used"):
            st.markdown(f"**Search I ran:**\n```\n{literature['query_used']}\n```")
        if literature.get("rationale"):
            st.markdown(f"**Why these terms:** {literature['rationale']}")
        if case["clarifications"]:
            st.markdown("**What I asked to narrow the search:**")
            for c in case["clarifications"]:
                st.markdown(f"- *{c['question']}* -> {c['answer']}")
        if literature.get("note"):
            st.info(literature["note"])
        render_evidence_sources(combined_evidence_sources(literature), show_legend=False)

    st.divider()
    follow_up = st.text_input("Reply to me, ask a question, or share your thinking:", key=f"follow_{case['id']}")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Send", key=f"send_{case['id']}"):
            if follow_up.strip():
                case["conversation"].append({"role": "user", "content": follow_up})
                with st.spinner("Thinking..."):
                    reply = continue_conversation(case["conversation"], case["tier_used"], literature=literature)
                case["conversation"].append({"role": "assistant", "content": reply})
                log_interaction({
                    "type": "follow_up",
                    "case_id": case["id"],
                    "tier_used": case["tier_used"],
                    "clinician_message": follow_up,
                    "aria_reply": reply,
                })
                st.rerun()
            else:
                st.warning("Please type a message before sending.")
    with c2:
        if st.button("Search again", key=f"rerun_{case['id']}"):
            case["literature"] = None
            case["responded"] = False
            case["response_error"] = None
            case["clarifications"] = []
            case["pending_question"] = None
            case["conversation"] = []
            case["tier_used"] = None
            st.rerun()

    st.divider()
    st.caption("How did this go?")
    feedback = st.radio(
        "Feedback:",
        options=["Very helpful", "Somewhat helpful", "Not helpful", "Confusing"],
        horizontal=True,
        index=None,
        key=f"fb_{case['id']}",
    )
    feedback_notes = st.text_input("Anything I got wrong, or that was unclear? (optional)", key=f"fbn_{case['id']}")
    if st.button("Submit feedback", key=f"fbsub_{case['id']}"):
        if feedback:
            log_interaction({
                "type": "feedback",
                "case_id": case["id"],
                "tier_used": case["tier_used"],
                "rating": feedback,
                "notes": feedback_notes,
            })
            st.success("Thanks, that's logged.")
        else:
            st.warning("Please pick a rating first.")


def render_scribe(figma_component, role="Viewer"):
    """Consume each generation/refinement event once and return its result."""
    from professor_aria.scribe import generate_soap, refine_soap, validate_soap, SOAP_FIELDS, TEMPLATES

    provider_role = st.session_state.get("user_role", role)
    event = figma_component(
        view="scribe", role=provider_role, key="aria_charting",
        soap=st.session_state.get("charting_soap_note", {}),
        transcript=st.session_state.get("charting_transcript", ""),
        generation=st.session_state.get("charting_generation"),
        generated_at=st.session_state.get("charting_generated_at"),
        discipline=st.session_state.get("charting_discipline", "PT Skilled SOAP"),
        draft_source=st.session_state.get("charting_draft_source", "manual"),
        signed=st.session_state.get("charting_signed", False),
    )
    if provider_role != "PT" or not isinstance(event, dict):
        return
    request_id = event.get("requestId")
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        return
    if event.get("type") == "reset_scribe":
        if request_id == st.session_state.get("charting_last_request"):
            return
        st.session_state.charting_last_request = request_id
        st.session_state.charting_transcript = ""
        st.session_state.charting_soap_note = {field: "" for field in SOAP_FIELDS}
        st.session_state.charting_signed = False
        st.session_state.charting_generation = None
        st.session_state.charting_generated_at = None
        st.session_state.charting_draft_source = "manual"
        discipline = event.get("discipline")
        st.session_state.charting_discipline = discipline if isinstance(discipline, str) and discipline in TEMPLATES else "PT Skilled SOAP"
        return
    if event.get("type") in {"generate_soap", "refine_soap"}:
        if request_id == st.session_state.get("charting_last_request"):
            return
        st.session_state.charting_last_request = request_id
        transcript = event.get("transcript", "")
        if isinstance(transcript, str):
            st.session_state.charting_transcript = transcript
        st.session_state.charting_signed = False
        st.session_state.charting_discipline = event.get("discipline", "PT Skilled SOAP")
        with st.spinner("ARIA is generating the SOAP draft…"):
            try:
                if event["type"] == "refine_soap":
                    result = refine_soap(event.get("soap"), event.get("instruction"), event.get("discipline", "PT Skilled SOAP"))
                else:
                    result = generate_soap(transcript, event.get("discipline", "PT Skilled SOAP"))
                result["soap"] = validate_soap(result["soap"])
                result["error"] = result.get("error")
            except Exception:
                message = "Claude could not complete the SOAP request. Review the local draft or retry."
                result = {"soap": {field: message for field in SOAP_FIELDS}, "error": message}
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")
        # A failed edit must survive navigation with the clinician's draft intact.
        retained_refinement = False
        if event["type"] == "refine_soap" and result["error"]:
            try:
                result["soap"] = validate_soap(event.get("soap"))
                retained_refinement = True
            except ValueError:
                pass
        st.session_state.charting_soap_note = result["soap"]
        st.session_state.charting_generated_at = generated_at
        st.session_state.charting_draft_source = "manual" if retained_refinement else "claude" if not result["error"] else "error"
        st.session_state.charting_generation = {"requestId": request_id, "error": result["error"], "generated_at": generated_at}
        st.rerun()
    elif event.get("type") == "signed":
        source = event.get("draftSource", "claude")
        if (st.session_state.get("charting_generation") or {}).get("error") and source not in {"local", "manual"}:
            return
        try:
            st.session_state.charting_soap_note = validate_soap(event.get("soap"))
        except ValueError:
            return
        st.session_state.charting_signed = True
        st.session_state.charting_draft_source = source
        if event.get("discipline") in TEMPLATES:
            st.session_state.charting_discipline = event["discipline"]
        if isinstance(event.get("transcript"), str):
            st.session_state.charting_transcript = event["transcript"]


def render_professor_dashboard(figma_component, role="Viewer"):
    """Run the professor's dashboard inside the host application's ARIA stage."""
    inject_style()
    render_header()

    ensure_state()
    render_sidebar()

    case = active_case()
    if "_goto_view" in st.session_state:
        st.session_state.view = st.session_state.pop("_goto_view")
    if st.session_state.get("view") == "Literature & Evidence":
        st.session_state.view = V_EVIDENCE_BRIDGE

    view = st.radio("Workspace", VIEWS, horizontal=True, key="view", label_visibility="collapsed", width="stretch")
    if view == V_EDUCATION:
        from professor_aria.education import render_education
        render_education(figma_component, role)
        return
    if view == V_EVIDENCE_BRIDGE:
        from evidence_bridge import render_evidence_bridge
        render_evidence_bridge()
        return

    if view in (V_INTAKE, V_EVIDENCE) and not _load_professor_engine():
        st.warning(
            "ARIA's clinical reasoning engine is unavailable until ANTHROPIC_API_KEY "
            "is set in .env or Streamlit secrets. You can still upload and manage PDFs in Evidence Bridge."
        )
        return

    if case is None:
        st.markdown("#### Welcome to ARIA")
        st.write("I'm ARIA, your clinical thinking partner for rehabilitation, connected to the eCW chart.")
        st.markdown(
            "1. **Evidence Query** — review the patient chart and MA triage data synced from eClinicalWorks. "
            "This is also where you choose **how much detail you want from me**.\n"
            "2. I'll **read the note back** so you can confirm I've understood it before going further.\n"
            "3. **Evidence Bridge** — upload PDFs, explore the knowledge base, and ask source-grounded questions.\n"
            "4. **Evidence & Guidance** — I search PubMed and Evidence Bridge and talk it through as a mentor. Ask follow-up questions anytime.\n"
            "5. **Patient Tracker**, **Measures & Trends**, and **ARIA Scribe** open the integrated clinical views.\n"
            "6. **ARIA Education** — practice case-based reasoning with quizzes and simulated learning progress.\n"
        )
        st.info("This pilot uses practice and synthetic data only. Please don't enter real patient information.")
        st.write("**Open the synced Ed Vance chart on the left to begin.**")
        return

    if view == V_INTAKE:
        render_intake(case)
    elif view == V_PROGRESS_NOTE:
        from professor_aria.patient_tracker import tracker_evidence
        from professor_aria.chart_copilot import handle_copilot_event
        tracker_action = figma_component(
            view="progress_note", role=st.session_state.get("user_role", "Viewer"),
            trackerEvidence=tracker_evidence(), key="aria_patient_tracker",
            copilotHistory=st.session_state.get("copilot_history", []),
            copilotResult=st.session_state.get("copilot_result"),
        )
        if handle_copilot_event(tracker_action, st.session_state):
            st.rerun()
        if (isinstance(tracker_action, dict)
                and tracker_action.get("action") == "open_evidence_bridge"
                and tracker_action.get("requestId")
                and tracker_action["requestId"] != st.session_state.get("tracker_last_request")):
            st.session_state.tracker_last_request = tracker_action["requestId"]
            st.session_state._goto_view = V_EVIDENCE_BRIDGE
            st.rerun()
    elif view == V_MEASURES_TRENDS:
        figma_component(view="patient_biometrics", role=st.session_state.get("user_role", "Viewer"))
    elif view == V_SCRIBE:
        render_scribe(figma_component, role)
    elif view == V_EVIDENCE:
        render_literature(case)
