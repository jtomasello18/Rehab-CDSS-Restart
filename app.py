import hashlib
import hmac

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from professor_aria.branding import INTERACTION_STYLE, PAGE_ICON
import aria_dashboard

# Streamlit can retain imported modules across script/deployment reruns. Refresh
# the older navigation before importing its renderer so the tab reads ARIA Scribe.
if aria_dashboard.V_SCRIBE != "ARIA Scribe":
    import importlib
    importlib.reload(aria_dashboard)

from aria_dashboard import render_professor_dashboard
from professor_aria.vignette import ED_VANCE_ENCOUNTERS
from figma_component import render as figma_component


st.set_page_config(
    page_title="ARIA Rehab CDSS",
    page_icon=PAGE_ICON,
    layout="wide",
)


st.markdown(INTERACTION_STYLE, unsafe_allow_html=True)

# Send the schedule-cell click through Streamlit's existing connection rather
# than following an HTML link, which would create a fresh unauthenticated session.
schedule_grid = st.components.v2.component(
    "ecw_schedule_grid",
    html='<div class="ecw-schedule-grid" data-ecw-schedule-grid></div>',
    js="""
    export default function({ data, parentElement, setTriggerValue }) {
        const grid = parentElement.querySelector('[data-ecw-schedule-grid]');
        // data is trusted schedule markup built from the fixed case below.
        grid.innerHTML = data;
        const button = grid.querySelector('[data-open-ed-vance]');
        const openChart = () => setTriggerValue('open_chart', true);
        button.addEventListener('click', openChart);
        return () => button.removeEventListener('click', openChart);
    }
    """,
    isolate_styles=False,
)


def open_ed_vance_chart():
    """Navigate only within an already authenticated clinical session."""
    if st.session_state.get("authenticated", False):
        st.session_state.user_role = "PT"
        st.session_state.page = "legacy_ehr"


def render_secure_gateway():
    """Render the app's only login form; success opens the provider schedule."""
    st.markdown(
        """
        <style>
        .stApp { background: #f8fafc; }
        .st-key-aria_secure_gateway {
            background: #ffffff; border-color: #cbd5e1 !important;
            border-radius: 12px; padding: 1.5rem !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        .aria-gateway-logo { display: block; width: 56px; height: 56px; margin-bottom: 16px; }
        .st-key-aria_secure_gateway h3 { color: #145b6e; }
        .st-key-gateway_sign_in button {
            background: #145b6e !important; border-color: #145b6e !important;
            color: #ffffff !important; border-radius: 6px; font-weight: 600;
        }
        .st-key-gateway_sign_in button:hover { background: #0f4c5c !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, login_card, _ = st.columns([1, 1.4, 1])
    with login_card:
        with st.container(border=True, key="aria_secure_gateway"):
            st.markdown(f'<img class="aria-gateway-logo" src="{PAGE_ICON}" alt="ARIA">', unsafe_allow_html=True)
            st.subheader("ARIA Secure Clinical Gateway")
            st.caption("Authorized Clinical Personnel Only — eClinicalWorks 12e & ARIA Integration")
            with st.form("clinical_gateway", clear_on_submit=True, border=False):
                username = st.text_input("Username", key="gateway_username")
                password = st.text_input("Password", type="password", key="gateway_password")
                submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True, key="gateway_sign_in")
            if submitted:
                # Compare the exact, case-sensitive shared credentials on the
                # server. Keep a verifier rather than the password in source.
                username_valid = hmac.compare_digest(username.encode("utf-8"), b"ARIAprovider")
                password_valid = hmac.compare_digest(
                    hashlib.sha256(password.encode("utf-8")).hexdigest(),
                    "44b4202602eff5ee870640bc62733376914b137505ccfcf7d5ed848e34145e1d",
                )
                if username_valid and password_valid:
                    st.session_state.authenticated = True
                    st.session_state.user_role = "PT"
                    st.session_state.page = "schedule"
                    st.rerun()
                else:
                    st.error("Invalid clinical credentials. Access denied.")


def sign_out():
    """Lock the session and discard its in-memory clinical and login state."""
    st.session_state.clear()
    st.query_params.clear()
    st.session_state.authenticated = False
    st.session_state.page = "gateway"


def render_schedule():
    """Render the eClinicalWorks 11e resource schedule."""
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:#eef1f2 !important; }
        .block-container { padding-top:1.5rem !important; }
        .ecw-schedule { background:#eef1f2; color:#222; font-family:Arial,Helvetica,sans-serif; font-size:12px; margin-top:6px; }
        .ecw-topbar { background:#1b4f5c; color:#fff; border:1px solid #123943; padding:10px 10px; min-height:22px; white-space:nowrap; overflow:hidden; }
        .ecw-topbar strong { font-size:17px; margin-right:24px; }
        .ecw-jelly { display:inline-block; margin-right:15px; font-size:11px; }
        .ecw-toolbar { background:#d9ddde; border:1px solid #aab2b4; border-top:0; color:#263238; padding:6px 10px; font-size:11px; }
        .ecw-toolbar span { display:inline-block; margin-right:24px; }
        .ecw-panel { background:#f7f8f8; border:1px solid #aeb7b9; padding:7px; margin-top:8px; }
        .ecw-panel-title { background:#5b6669; color:#fff; font-weight:bold; padding:5px 6px; margin:-7px -7px 7px; font-size:11px; }
        .ecw-calendar { width:100%; border-collapse:collapse; table-layout:fixed; text-align:center; font-size:10px; }
        .ecw-calendar th { color:#596568; padding:3px 0; font-weight:bold; }
        .ecw-calendar td { padding:4px 0; border:1px solid #dfe3e4; }
        .ecw-calendar .selected { background:#e66c37; color:#fff; font-weight:bold; }
        .ecw-check { line-height:1.9; white-space:nowrap; font-size:11px; }
        .ecw-schedule-grid { font:12px Arial,Helvetica,sans-serif; color:#222; }
        .ecw-grid-title { background:#555; color:#fff; text-align:center; padding:7px; margin-top:8px; font-weight:bold; border:1px solid #444; }
        .ecw-grid { border-collapse:collapse; width:100%; table-layout:fixed; }
        .ecw-grid th, .ecw-grid td { border:1px solid #b8c4d0; height:34px; padding:2px 4px; box-sizing:border-box; }
        .ecw-grid th { background:#d4d8d9; color:#222; font-weight:bold; text-align:center; font-size:10px; height:30px; }
        .ecw-grid th:first-child, .ecw-grid td:first-child { width:10%; }
        .ecw-time { background:#eef1f2; color:#505b5e; text-align:center; font-size:10px; white-space:nowrap; }
        .ecw-cell { vertical-align:middle; }
        .ecw-morales, .ecw-reed { background:#9bb8f7; }
        .ecw-green { background:#7997f2; }
        .ecw-lin { background:#7a7a7a; }
        .ecw-lunch { background:#6e6e6e; }
        .ecw-appointment { background:#fff; border:1px solid #333; border-left:4px solid #2e6da4; color:#111; font-size:11px; line-height:1.15; padding:3px 6px; box-sizing:border-box; }
        .ecw-ed-vance { display:block; width:100%; background:#f37021; border:1px solid #b84d0d; color:#fff !important; font: bold 11px/1.15 Arial,Helvetica,sans-serif; padding:3px 6px; text-align:left; cursor:pointer; box-sizing:border-box; }
        .ecw-ed-vance:hover { background:#d96015; }
        .ecw-ed-vance:focus-visible { outline:2px solid #145b6e; outline-offset:2px; }
        .st-key-open_selected_chart button { background:#f37021 !important; border-color:#b84d0d !important; color:#fff !important; font-weight:700 !important; border-radius:2px !important; }
        </style>
        <div class="ecw-schedule">
          <div class="ecw-topbar"><strong>eClinicalWorks 11e</strong>
            <span class="ecw-jelly">P 0</span><span class="ecw-jelly">N 2</span><span class="ecw-jelly">E 0</span>
            <span class="ecw-jelly">S 0</span><span class="ecw-jelly">D 53</span><span class="ecw-jelly">R 24</span>
            <span class="ecw-jelly">T 29</span><span class="ecw-jelly">L 3</span><span class="ecw-jelly">M 1472</span>
          </div>
          <div class="ecw-toolbar"><span>1 Day ▼</span><span>15 min ▼</span><span>Facility: Outpatient Rehab Center ▼</span><span>Today</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sidebar, schedule = st.columns([1, 4.2], gap="small")
    with sidebar:
        st.markdown(
            """
            <div class="ecw-panel"><div class="ecw-panel-title">October 2026</div>
            <table class="ecw-calendar"><tr><th>Su</th><th>Mo</th><th>Tu</th><th>We</th><th>Th</th><th>Fr</th><th>Sa</th></tr>
            <tr><td></td><td></td><td></td><td></td><td>1</td><td>2</td><td>3</td></tr>
            <tr><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>10</td></tr>
            <tr><td>11</td><td>12</td><td class="selected">13</td><td>14</td><td>15</td><td>16</td><td>17</td></tr>
            <tr><td>18</td><td>19</td><td>20</td><td>21</td><td>22</td><td>23</td><td>24</td></tr>
            <tr><td>25</td><td>26</td><td>27</td><td>28</td><td>29</td><td>30</td><td>31</td></tr></table></div>
            <div class="ecw-panel"><div class="ecw-panel-title">My Providers</div>
            <div class="ecw-check">[x] Morales, J (PT)<br>[x] Green, R (OT)<br>[x] Reed, A (SLP)<br>[x] Lin, S (MD - Neuro)</div></div>
            <div class="ecw-panel"><div class="ecw-panel-title">My Resources</div><div class="ecw-check">[x] Treatment Rooms<br>[x] Outpatient Rehab Center</div></div>
            """,
            unsafe_allow_html=True,
        )

    times = [f"{hour % 12 or 12:02d}:{minute:02d} {'AM' if hour < 12 else 'PM'}" for hour in range(8, 17) for minute in (0, 30)]
    providers = ["Morales, J (PT)", "Green, R (OT)", "Reed, A (SLP)", "Lin, S (MD)"]
    appointments = {
        ("09:00 AM", 0): "[7] Chen, Maria 04/12/1968 PT Eval",
        ("10:30 AM", 1): "[7] Wilson, James 11/02/1955 OT Tx",
        ("02:00 PM", 2): "[7] Brown, Linda 08/19/1971 SLP",
        ("04:00 PM", 3): "[7] King, Robert 01/30/1950 F/U",
    }
    with schedule:
        grid_rows = [
            '<div class="ecw-grid-title">Tuesday, October 13, 2026</div>',
            '<table class="ecw-grid"><thead><tr><th>Time</th>'
            + "".join(f"<th>{provider}</th>" for provider in providers)
            + "</tr></thead><tbody>"
        ]
        for time in times:
            lunch = time in {"12:00 PM", "12:30 PM"}
            grid_rows.append(f'<tr><td class="ecw-time">{time}</td>')
            for provider_index in range(4):
                cell_class = "ecw-morales" if provider_index == 0 else "ecw-green" if provider_index == 1 else "ecw-reed" if provider_index == 2 else "ecw-lin"
                if lunch:
                    cell_class = "ecw-lunch"
                appointment = appointments.get((time, provider_index))
                if time == "03:00 PM" and provider_index == 0:
                    content = '<button type="button" class="ecw-ed-vance" data-open-ed-vance aria-label="Open Ed Vance chart, 3:00 PM outpatient evaluation">[7] Vance, Ed 05/14/1959 (67Y) — Stroke F/U / Outpatient Eval</button>'
                elif appointment:
                    content = f'<div class="ecw-appointment">{appointment}</div>'
                else:
                    content = ""
                grid_rows.append(f'<td class="ecw-cell {cell_class}">{content}</td>')
            grid_rows.append("</tr>")
        grid_rows.append("</tbody></table>")
        schedule_grid(
            data="".join(grid_rows),
            key="ecw_schedule_grid",
            on_open_chart_change=open_ed_vance_chart,
        )
        if st.button(
            "Open Selected Chart: [7] Vance, Ed — 3:00 PM (Outpatient Eval)",
            type="primary",
            use_container_width=True,
            key="open_selected_chart",
        ):
            open_ed_vance_chart()
            st.rerun()


def render_legacy_ehr():
    """Render the eCW 11e-style historical progress note workspace."""
    st.markdown(
        """
        <style>
        .st-key-ehr_launch_aria button[kind="primary"] {
            background: linear-gradient(135deg, #145b6e 0%, #0d3f4d 100%) !important;
            color: #ffffff !important;
            border: 1.5px solid #2a8a9e !important;
            border-left: 4px solid #f0b429 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            letter-spacing: 0.02em !important;
            padding: 0.5rem 1.25rem !important;
            box-shadow: 0 2px 6px rgba(15, 68, 82, 0.22) !important;
            transition: all 0.18s ease !important;
        }
        .st-key-ehr_launch_aria button[kind="primary"]:hover {
            background: linear-gradient(135deg, #196d84 0%, #145b6e 100%) !important;
            border-color: #38a3b8 !important;
            border-left-color: #f0b429 !important;
            box-shadow: 0 4px 12px rgba(20, 91, 110, 0.28) !important;
            transform: translateY(-1px);
        }
        .st-key-ehr_launch_aria button[kind="primary"]:active {
            transform: translateY(0);
            box-shadow: 0 1px 3px rgba(15, 68, 82, 0.22) !important;
        }
        .st-key-ehr_back_to_schedule button {
            background: #ffffff !important;
            color: #145b6e !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
            padding: 0.4rem 0.9rem !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            box-shadow: none !important;
            transition: all 0.18s ease !important;
        }
        .st-key-ehr_back_to_schedule button:hover {
            background: #f0f7f9 !important;
            border-color: #145b6e !important;
        }
        .st-key-ehr_launch_aria button p,
        .st-key-ehr_back_to_schedule button p {
            color: inherit !important;
            font-size: inherit !important;
            font-weight: inherit !important;
        }
        .st-key-ehr_launch_aria button:focus-visible,
        .st-key-ehr_back_to_schedule button:focus-visible {
            outline: 2px solid #145b6e !important;
            outline-offset: 3px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Back to Schedule", key="ehr_back_to_schedule"):
        st.session_state.page = "schedule"
        st.rerun()

    st.markdown(
        """
        <style>
        .ecw-page { background:#edf1f2; color:#263238; font-family:Arial,Helvetica,sans-serif; }
        .ecw-top { background:#1b4f5c; color:white; padding:7px 12px; border:1px solid #123943; font-size:12px; }
        .ecw-top strong { font-size:17px; margin-right:22px; }
        .ecw-jelly { display:inline-block; margin-right:13px; color:#f4f7f8; }
        .ecw-header { background:#f8faf9; border:1px solid #9aaeb2; padding:9px 12px; font-size:12px; }
        .ecw-avatar { display:inline-block; background:#607d8b; color:white; border-radius:50%; padding:8px; margin-right:9px; font-weight:bold; }
        .ecw-badge { background:#d7e7eb; border:1px solid #7da8b2; padding:2px 5px; margin-left:4px; font-size:9px; font-weight:bold; }
        .ecw-sticky-row { display:flex; gap:7px; padding:7px 0; }
        .ecw-sticky { flex:1; min-height:53px; padding:7px; border:1px solid #b9a76e; box-shadow:1px 2px 2px #aaa; font-size:10px; }
        .ecw-yellow { background:#fff5a8; } .ecw-green { background:#d9f0d0; border-color:#7d9b73; }
        .ecw-light { background:#fffbd1; } .ecw-pink { background:#ffdce5; border-color:#be8291; }
        .ecw-ribbon { background:#258ea6; color:white; padding:7px 10px; font-size:11px; word-spacing:8px; border:1px solid #1b6f80; }
        .ecw-small { color:#546e7a; font-size:10px; }
        .ecw-brown { color:#8b4513; font-weight:bold; border-bottom:1px solid #c8a58a; margin-top:10px; }
        .ecw-purple { color:#6a1b9a; font-weight:bold; }
        .ecw-green-text { color:#2e7d32; }
        .ecw-note { font-family:Georgia,'Times New Roman',serif; font-size:12px; line-height:1.25; }
        .ecw-note p { margin:4px 0; } .ecw-note table { border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:10px; }
        .ecw-note td,.ecw-note th { border:1px solid #cfcfcf; padding:3px 5px; text-align:left; }
        .ecw-note th { background:#eee7f4; color:#6a1b9a; }
        .ecw-actions { background:#dce7e9; border-top:2px solid #708b91; padding:7px; font:11px Arial; color:#164f5b; word-spacing:7px; }
        .ecw-rightbar { background:#174b57; color:#fff; padding:7px; font-size:10px; word-spacing:5px; }
        .ecw-alert { background:#f6c36a; border:1px solid #b77716; padding:7px; font-size:10px; font-weight:bold; }
        </style>
        <div class="ecw-page">
        <div class="ecw-top"><strong>eClinicalWorks 11e</strong>
          <span class="ecw-jelly">P 0</span><span class="ecw-jelly">N 1</span><span class="ecw-jelly">E 0</span>
          <span class="ecw-jelly">S 2</span><span class="ecw-jelly">D 4</span><span class="ecw-jelly">R 2</span>
          <span class="ecw-jelly">T 5</span><span class="ecw-jelly">L 1</span>
        </div>
        <div class="ecw-header"><span class="ecw-avatar">EV</span><strong>VANCE, ED (67 Y, M)</strong>
          &nbsp; DOB: 04/18/1959 &nbsp; | &nbsp; MRN: 482910 &nbsp; | &nbsp; 18 Oak Street, Hartford, CT
          &nbsp; | &nbsp; Primary Insurance: Medicare Part B
          <span class="ecw-badge">INFO</span><span class="ecw-badge">HUB</span><span class="ecw-badge">ASK EVA</span>
        </div>
        <div class="ecw-sticky-row">
          <div class="ecw-sticky ecw-yellow"><b>Weight / Vitals</b><br>Wt: 178 lbs | BP: 128/78 | Fall Risk: HIGH</div>
          <div class="ecw-sticky ecw-green"><b>Billing / Ins</b><br>Medicare Part B | Auth: 12/20 visits used | Copay: $0</div>
          <div class="ecw-sticky ecw-light"><b>Notes</b><br>Spouse (Martha) at bedside. Mild expressive aphasia.</div>
          <div class="ecw-sticky ecw-pink"><b>Secure / Alerts</b><br>ALLERGIES: Penicillin (Hives) | Latex (Mild)</div>
        </div>
        <div class="ecw-ribbon">Medical Summary | CDSS | Rx | Labs | DI | Procedures | Encounters | Patient Docs | Flowsheets | Notes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    encounters = ED_VANCE_ENCOUNTERS
    if "ehr_encounter_index" not in st.session_state:
        st.session_state.ehr_encounter_index = 0
    encounter_labels = [encounter["label"] for encounter in encounters]
    if st.session_state.get("ehr_encounter_selector") not in encounter_labels:
        st.session_state.pop("ehr_encounter_selector", None)
    current_index = st.session_state.ehr_encounter_index
    toolbar_left, toolbar_mid, toolbar_right = st.columns([1.2, 1.5, 2.7])
    with toolbar_left:
        if st.button("Launch ARIA", type="primary", use_container_width=True, key="ehr_launch_aria"):
            st.session_state.page = "aria_dashboard"
            st.rerun()
    with toolbar_mid:
        st.caption(f"Selected: {encounters[current_index]['short']}")
    with toolbar_right:
        previous, selector, next_button = st.columns([0.35, 3.8, 0.35])
        with previous:
            if st.button("<", key="ehr_previous", help="Previous encounter"):
                next_index = (current_index + 1) % len(encounters)
                st.session_state.ehr_encounter_index = next_index
                st.session_state.ehr_encounter_selector = encounter_labels[next_index]
                st.rerun()
        with selector:
            selected_label = st.selectbox(
                "Historical encounter",
                encounter_labels,
                index=current_index,
                key="ehr_encounter_selector",
                label_visibility="collapsed",
            )
        with next_button:
            if st.button(">", key="ehr_next", help="Next encounter"):
                next_index = (current_index - 1) % len(encounters)
                st.session_state.ehr_encounter_index = next_index
                st.session_state.ehr_encounter_selector = encounter_labels[next_index]
                st.rerun()
    if selected_label != encounter_labels[current_index]:
        st.session_state.ehr_encounter_index = encounter_labels.index(selected_label)
        st.rerun()

    encounter = encounters[st.session_state.ehr_encounter_index]
    st.caption(f"Encounter: {encounter['label']} | Department: {encounter['department']} | Status: Signed")
    note_column, right_column = st.columns([2.2, 1])
    with note_column:
        with st.container(height=520, border=True):
            st.markdown(
                f"""
                <div class="ecw-note">
                <div class="ecw-brown">PROVIDER / FACILITY HEADER</div>
                <p><b>Hartford Rehabilitation Associates — {encounter['department']}</b><br>
                Provider: {encounter['provider']} &nbsp; | &nbsp; Supervising MD: S. Lin, MD &nbsp; | &nbsp; DOS: {encounter['label'][:10]}<br>
                Patient: Vance, Ed &nbsp; | &nbsp; MRN: 482910 &nbsp; | &nbsp; Visit type: {encounter['short']}</p>
                <div class="ecw-purple">Subjective:</div>
                <p><b>Chief Complaint:</b> Right-sided weakness, gait instability, and difficulty using R hand.<br>
                <b>HPI:</b> 67yo male, {encounter['weeks_post_stroke']} weeks post left MCA ischemic stroke. {encounter['subjective']}<br>
                <b>ROS - 10 Systems Reviewed:</b> Constitutional: fatigue reported; Eyes: no acute vision change; ENT: no dysphagia today; CV: no chest pain; Resp: no SOB; GI: no nausea; GU: continent; MSK: R shoulder discomfort; Neuro: expressive aphasia, R hemiparesis; Psych: cooperative, mildly frustrated with slowed mobility. <span class="ecw-green-text">All other systems negative.</span><br>
                <b>Functional Status:</b> {encounter['mobility']}. Goal: walk to mailbox and self-feed with R hand.</p>
                <div class="ecw-purple">Current Medications:</div>
                <p>{encounter['meds']}<br><span class="ecw-green-text">Discontinued: none documented. Medication reconciliation reviewed with spouse.</span></p>
                <div class="ecw-purple">Allergies:</div><p>Penicillin — hives; Latex — mild reaction.</p>
                <div class="ecw-purple">Vitals:</div><p>{encounter['vitals']}</p>
                <div class="ecw-brown">Objective / Rehab Exam:</div>
                <p><b>ROM:</b> R shoulder flexion 0-135° with pain at end range; R ankle DF to neutral with knee extended. <b>MMT:</b> R hip flex 3+/5, knee ext 4-/5, ankle DF 3/5; LLE 5/5. <b>Spasticity:</b> {encounter['tone']}.</p>
                <table><tr><th>Spasticity Ashworth Table</th><th>Right</th><th>Left</th><th>Comment</th></tr>
                <tr><td>Elbow flexors</td><td>{'Grade 2' if 'Grade 2' in encounter['tone'] else 'Not reassessed'}</td><td>0</td><td>Flexor synergy</td></tr>
                <tr><td>Ankle plantarflexors</td><td>{'Grade 1+' if 'Grade 1+' in encounter['tone'] else 'Not reassessed'}</td><td>0</td><td>Right ankle tone</td></tr></table>
                <p><b>Standardized Outcome Measures:</b> {encounter['measurements']}<br>
                <b>Gait Analysis:</b> {encounter['gait']}<br><b>Brunnstrom:</b> {encounter['staging']}.</p>
                <div class="ecw-brown">Assessment &amp; ICD-10 Codes:</div>
                <p>{encounter['assessment']}<br><b>Codes:</b> I69.351 (hemiplegia following cerebral infarction, right dominant side); R26.89 (other abnormalities of gait); M62.838 (other muscle spasm); R26.81 (unsteadiness on feet).</p>
                <div class="ecw-brown">Plan &amp; CPT Billing Codes:</div>
                <p>{encounter['plan']} Continue HEP and caregiver education. <b>CPT:</b> 97110 therapeutic exercise; 97112 neuromuscular re-education; 97116 gait training; evaluation coding per documented complexity. Patient/spouse verbalized understanding. Electronically signed {encounter['provider']}.</p>
                <div class="ecw-actions">Send | Print | Fax | Record | Details | Templates | Claim | Letters | Ink | Attachments</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with right_column:
        st.markdown('<div class="ecw-rightbar">Overview | DRTLA | History | CDSS | Order Sets | Templates | eEHX</div>', unsafe_allow_html=True)
        st.markdown('<div class="ecw-alert">Right Panel data last modified on: 10/06/2026 04:15 PM</div>', unsafe_allow_html=True)
        with st.expander("Global Alerts", expanded=True):
            st.error("HIGH FALL RISK — 2 near-falls reported at the outpatient evaluation.")
            st.caption("Penicillin and Latex allergies. Verify before treatment.")
        with st.expander("Advance Directive"):
            st.write("Full Code. Health care proxy: Martha Vance (spouse). Document scan on file.")
        with st.expander("Problem List (SNOMED/ICD-10)"):
            st.markdown("- Left MCA ischemic stroke — I63.512 / SNOMED 432504007\n- Right hemiparesis — I69.351\n- Abnormal gait — R26.89\n- Expressive aphasia — R47.01")
        with st.expander("Allergies"):
            st.markdown("**Penicillin:** Hives &nbsp; | &nbsp; **Latex:** Mild contact reaction")
        with st.expander("Medication Summary"):
            st.markdown(f"{encounter['meds']}\n\n**Medication review:** Due after recent Baclofen adjustment.")
        with st.expander("Immunizations"):
            st.markdown("Influenza 09/15/2026 · COVID booster 09/15/2026 · Pneumococcal documented")
        with st.expander("Therapeutic Injections"):
            st.markdown("No therapeutic injections documented. Botox discussion deferred pending response to Baclofen.")


def render_aria_dashboard():
    """Render the unified eCW workflow with ARIA as the clinical overlay."""
    if st.button("← Return to eClinicalWorks Chart (MRN 482910)", key="aria_return_to_ecw"):
        st.session_state.page = "legacy_ehr"
        st.rerun()

    render_professor_dashboard(
        figma_component,
        role=st.session_state.get("user_role", "Viewer"),
    )


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.session_state.page = "gateway"
    render_secure_gateway()
    st.stop()

# The shared Gateway identity is the PT provider throughout the eCW/ARIA
# workflow, including sessions left on an obsolete internal login route.
st.session_state.user_role = "PT"

# The gate runs before URL routing or any schedule, EHR, or ARIA rendering.
st.sidebar.button("Sign Out", key="gateway_sign_out", type="tertiary", on_click=sign_out)

if "ed_vance" in st.query_params:
    # Reached only after the gate. A URL is a navigation request, never proof
    # of identity, and clearing it must not reset the authenticated session.
    open_ed_vance_chart()
    st.query_params.clear()

if st.session_state.get("page") not in {"schedule", "legacy_ehr", "aria_dashboard"}:
    st.session_state.page = "schedule"

if st.session_state.page == "schedule":
    render_schedule()
elif st.session_state.page == "legacy_ehr":
    render_legacy_ehr()
elif st.session_state.page == "aria_dashboard":
    render_aria_dashboard()
