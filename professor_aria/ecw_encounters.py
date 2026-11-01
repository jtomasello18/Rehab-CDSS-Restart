"""Session-backed write-back for the eCW presentation chart."""

import datetime
import html

from .vignette import ED_VANCE_ENCOUNTERS

MD_TEMPLATE = "MD Neuro Follow-up"
MD_ENCOUNTER = {
    "label": "11/02/2026 — Neurology Stroke F/U (S. Lin, MD)",
    "short": "Neurology Stroke F/U",
    "department": "Outpatient Neurology",
    "provider": "S. Lin, MD",
    "vitals": "BP 126/76 mmHg | HR 70 bpm",
    "meds": "Baclofen 10mg TID",
}
# Keep the shared historical vignette unchanged: tracker metrics still refer to 10/13.
ECW_ENCOUNTERS = [MD_ENCOUNTER, *ED_VANCE_ENCOUNTERS]
MD_SYNC_MESSAGE = (
    "Signed by S. Lin, MD & synced to eClinicalWorks Encounter "
    "(11/02/2026 — Neurology Stroke F/U)."
)
PENDING_TEXT = "[Encounter documentation pending — Launch ARIA Scribe to capture and sync note.]"


def selected_encounter_index(state):
    index = state.get("ehr_encounter_index", 0)
    if type(index) is not int or not 0 <= index < len(ECW_ENCOUNTERS):
        index = 0
    state["ehr_encounter_index"] = index
    return index


def sync_md_note(state, soap, request_id):
    """Store a reviewed snapshot once; subsequent drafts cannot alter a locked note."""
    existing = state.get("signed_md_note")
    if existing is not None and existing != soap:
        raise ValueError("The 11/02 neurology encounter is already signed and locked. Its signed note was preserved.")
    if existing is None:
        state["signed_md_note"] = dict(soap)
        state["signed_md_note_metadata"] = {
            "encounter": MD_ENCOUNTER["label"], "provider": MD_ENCOUNTER["provider"],
            "request_id": request_id,
            "signed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    state["ehr_selected_encounter"] = MD_ENCOUNTER["label"]
    state["ehr_encounter_index"] = 0
    state["ehr_encounter_selector"] = MD_ENCOUNTER["label"]


def neurology_note_html(soap=None):
    """Escape clinician text and preserve its line breaks in the chart."""
    sections = []
    for field in ("subjective", "objective", "assessment", "plan"):
        content = (f'<div class="ecw-signed-section">{html.escape(soap[field])}</div>' if soap
                   else f'<div class="ecw-pending-note">{PENDING_TEXT}</div>')
        sections.append(f'<div class="ecw-purple">{field.title()}:</div>{content}')
    signature = (
        '<div class="ecw-signature">Electronically signed by S. Lin, MD on 11/02/2026 '
        '· E/M Coding: 99214 (Level 4 Established Patient)</div>' if soap else ""
    )
    return (
        '<div class="ecw-note ecw-neurology"><div class="ecw-brown">PROVIDER / FACILITY HEADER</div>'
        '<p>Hartford Rehabilitation Associates — Outpatient Neurology | Provider: S. Lin, MD '
        '| DOS: 11/02/2026 | Patient: Vance, Ed | MRN: 482910 | Visit type: Neurology Stroke F/U</p>'
        '<div class="ecw-brown">VITALS / MA TRIAGE</div>'
        '<p>BP 126/76 mmHg | HR 70 bpm | Current Meds: Baclofen 10mg TID | Allergies: Penicillin, Latex</p>'
        + "".join(sections) + signature + '</div>'
    )
