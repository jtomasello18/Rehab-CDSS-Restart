"""Shared Ed Vance presentation case: discharge, MD review, outpatient evaluation."""

ED_VANCE_NOTE = (
    "ARIA synced Ed Vance's three eClinicalWorks encounters. "
    "09/29/2026 (Wk 10 · IRF Discharge): 10 weeks post-left MCA ischemic stroke; "
    "Berg Balance Scale 42/56, 10MWT 0.48 m/s, TUG 16.2s, FMA-UE 18/66; "
    "right elbow flexors Modified Ashworth Grade 2; Baclofen 5mg TID. "
    "10/06/2026 (Wk 11 · MD Follow-up): persistent focal tone; Baclofen increased "
    "from 5mg TID to 10mg TID. Monitor daytime fatigue, sedation and weakness. "
    "10/13/2026 (Wk 12 · Outpatient Eval): Ed Vance is a 67-year-old male, "
    "12 weeks post-left MCA ischemic stroke, discharged from inpatient rehabilitation "
    "2 weeks ago and transitioning to outpatient therapy today. Goals: walk to the "
    "mailbox and self-feed with the right hand. Current Berg Balance Scale 38/56 "
    "(high fall risk below 45), 10MWT 0.35 m/s (household ambulator), TUG 21.4s, "
    "FMA-UE 22/66 (severe motor impairment), and Sit-to-Stand x5 21s. "
    "Modified Ashworth Grade 2 in right elbow flexors; Grade 1+ in right ankle "
    "plantarflexors. Brunnstrom Right UE: Stage 3 (flexor synergy); Right LE: Stage 4. "
    "Ambulates 50 ft with a hemi-walker and Standby Assist (SBA): absent right heel "
    "strike, severe right swing-phase foot drop, right hip hiking/circumduction. "
    "Two near-falls at home this week from right foot catching on carpet; mild "
    "expressive aphasia with intact multi-step auditory comprehension and fatigue "
    "after 20 minutes. Right inferior glenohumeral subluxation approximately "
    "1 finger-width. Current medication: Baclofen 10mg TID. Gait/balance decline "
    "and fatigue may be correlated with the 10/06 Baclofen increase; causation is "
    "not established. Focus: safe gait progression and multidisciplinary coordination."
)

ED_VANCE_ENCOUNTERS = [
    {
        "label": "10/13/2026 — Wk 12 · Outpatient Eval (J. Morales, PT)",
        "short": "Wk 12 · Outpatient Eval", "weeks_post_stroke": 12,
        "department": "Outpatient Rehabilitation", "provider": "J. Morales, PT",
        "vitals": "BP 128/78 mmHg | HR 72 bpm",
        "subjective": "Discharged from IRF 2 weeks ago; transitioning to outpatient therapy today. Reports 2 near-falls this week from right foot catching on carpet, mild expressive aphasia and fatigue after 20 minutes.",
        "measurements": "Berg Balance Scale: 38/56 (IRF discharge 42/56; high fall risk <45) | 10MWT: 0.35 m/s (IRF discharge 0.48 m/s; household ambulator) | FMA-UE: 22/66 (IRF discharge 18/66; severe motor impairment) | TUG: 21.4s | Sit-to-Stand x5: 21s",
        "tone": "Modified Ashworth: Grade 2 in right elbow flexors; Grade 1+ in right ankle plantarflexors",
        "mobility": "Hemi-walker with Standby Assist (SBA) · 50 ft",
        "gait": "Absent R heel strike, severe R swing-phase foot drop, R hip hiking/circumduction.",
        "staging": "Right UE: Stage 3 (flexor synergy) · Right LE: Stage 4",
        "meds": "Baclofen 10mg TID",
        "assessment": "Post-stroke right hemiparesis, high fall risk, focal tone and severe right foot drop. Gait/balance decline from IRF discharge may be correlated with the 10/06 Baclofen increase.",
        "plan": "Evaluate for safe outpatient gait progression, AFO/FES assessment, shoulder protection and fatigue pacing; coordinate findings with MD, OT and SLP.",
    },
    {
        "label": "10/06/2026 — Wk 11 · MD Follow-up (S. Lin, MD)",
        "short": "Wk 11 · MD Follow-up", "weeks_post_stroke": 11,
        "department": "Neurology", "provider": "S. Lin, MD",
        "vitals": "Repeat vital signs not supplied for the MD follow-up.",
        "subjective": "One week after IRF discharge, persistent right upper-limb tightness and gait-initiation difficulty. No new focal weakness, seizure or acute visual change reported.",
        "measurements": "IRF discharge comparison: Berg Balance Scale 42/56 | 10MWT 0.48 m/s | FMA-UE 18/66. No new standardized motor scores documented at this MD visit.",
        "tone": "Persistent focal right-limb tone; repeat joint-specific MAS scores not documented at this MD visit",
        "mobility": "Mobility device, assistance and distance not reassessed in the MD note.",
        "gait": "Persistent gait-initiation difficulty; detailed gait reassessment deferred to outpatient therapy.",
        "staging": "Not reassessed at MD follow-up",
        "meds": "Baclofen increased from 5mg TID to 10mg TID on 10/06",
        "assessment": "Subacute post-stroke right hemiparesis with persistent focal tone.",
        "plan": "Coordinate outpatient PT/OT/SLP; monitor daytime fatigue, sedation, weakness and falls after titration.",
    },
    {
        "label": "09/29/2026 — Wk 10 · IRF Discharge (J. Morales, PT)",
        "short": "Wk 10 · IRF Discharge", "weeks_post_stroke": 10,
        "department": "Inpatient Rehabilitation", "provider": "J. Morales, PT",
        "vitals": "BP 134/82 mmHg | HR 74 bpm",
        "subjective": "Discharge from inpatient rehabilitation 10 weeks after left MCA ischemic stroke. Goals: walk to mailbox and self-feed with the right hand.",
        "measurements": "IRF discharge baseline Berg Balance Scale: 42/56 | 10MWT: 0.48 m/s | FMA-UE: 18/66 | TUG: 16.2s | Sit-to-Stand x5: 17s",
        "tone": "Modified Ashworth Grade 2 in right elbow flexors",
        "mobility": "Baseline walking speed 0.48 m/s; discharge device, assistance and distance not specified in the supplied vignette.",
        "gait": "Impaired gait following stroke; current detailed gait findings are recorded at the 10/13 outpatient evaluation.",
        "staging": "Not separately documented at IRF discharge",
        "meds": "Baclofen 5mg TID",
        "assessment": "Right hemiparesis, impaired balance and gait, severe right UE motor impairment and persistent focal elbow tone.",
        "plan": "Discharge from IRF; arrange MD follow-up and transition to outpatient multidisciplinary therapy.",
    },
]
