export type Specialty = 'pt' | 'physician' | 'ot' | 'slp';
export type Tone = 'danger' | 'warning' | 'success' | 'neutral';

export type TrackerMetric = {
  id: string;
  label: string;
  initial: number | string | null;
  prior: number | string | null;
  current: number | string;
  unit?: string;
  lowerIsBetter?: boolean;
  deltaUnit?: string;
  deltaNote?: string;
  status?: { tone: Tone; text: string };
  note?: string;
};

export const encounters = [
  { key: 'initial', date: '09/29', label: 'IRF Discharge', week: 10 },
  { key: 'prior', date: '10/06', label: 'MD Follow-up', week: 11 },
  { key: 'current', date: '10/13', label: 'Outpatient Eval', week: 12 },
] as const;

// The supplied Ed Vance case snapshot, not a live EHR feed. Unknown dated
// measurements remain null; an undated chart value is never backfilled here.
export const trackerMetrics: Record<Specialty, TrackerMetric[]> = {
  pt: [
    { id: 'walk', label: '10-Meter Walk Test', initial: 0.48, prior: null, current: 0.35,
      unit: 'm/s', deltaUnit: 'm/s', deltaNote: 'Regressing',
      note: 'Household ambulator. Decline from IRF discharge may be correlated with the 10/06 baclofen increase.' },
    { id: 'bbs', label: 'Berg Balance Scale', initial: 42, prior: null, current: 38,
      unit: '/56', deltaUnit: 'pts', deltaNote: 'High Fall Risk (<45)' },
    { id: 'tug', label: 'Timed Up & Go (TUG)', initial: 16.2, prior: null, current: 21.4,
      unit: 'sec', lowerIsBetter: true, deltaUnit: 's slower', deltaNote: 'Fall Risk Threshold >14s' },
    { id: 'device', label: 'Brunnstrom (Right LE) & Device', initial: null, prior: null,
      current: 'Right LE: Stage 4', status: { tone: 'warning', text: 'Hemi-walker · Standby Assist (SBA) · 50 ft' },
      note: 'Absent R heel strike, severe R swing-phase foot drop, R hip hiking/circumduction. Right ankle plantarflexors: MAS Grade 1+.' },
  ],
  physician: [
    { id: 'diagnosis', label: 'Primary ICD-10', initial: null, prior: null, current: 'I69.351',
      status: { tone: 'neutral', text: 'Prior dated diagnosis entries not recorded' },
      note: 'Hemiplegia and hemiparesis following cerebral infarction affecting right dominant side.' },
    { id: 'bp', label: 'BP (Last)', initial: '134/82', prior: null, current: '128/78', unit: 'mmHg',
      status: { tone: 'success', text: '▼ From 134/82 mmHg (09/29) — Within AHA Target <130/80' } },
    { id: 'hr', label: 'Heart Rate', initial: 74, prior: null, current: 72, unit: 'bpm',
      status: { tone: 'success', text: '▼ -2 bpm from 74 bpm (09/29) — Stable rate' } },
    { id: 'baclofen', label: 'Oral Baclofen', initial: 5, prior: 10, current: 10, unit: 'mg TID',
      status: { tone: 'danger', text: '▲ Doubled 5mg → 10mg TID on 10/06 — team safety review' },
      note: 'Current dose is recorded, not a new prescription. Review sedation, weakness, falls and functional tone with PT/OT/SLP.' },
  ],
  ot: [
    { id: 'fma', label: 'FMA-UE', initial: 18, prior: null, current: 22,
      unit: '/66', deltaUnit: 'pts', deltaNote: 'Proximal progress', note: 'Severe motor impairment.' },
    { id: 'mas', label: 'Mod. Ashworth (R Elbow Flexors)', initial: 'Grade 2', prior: null, current: 'Grade 2',
      status: { tone: 'warning', text: 'Persistent focal tone · R ankle plantarflexors: Grade 1+' } },
    { id: 'brunnstrom', label: 'Brunnstrom (Right UE)', initial: null, prior: null, current: 'Stage 3 (flexor synergy)',
      status: { tone: 'warning', text: 'Spasticity limiting distal wrist/finger extension' } },
    { id: 'grip', label: '9-Hole Peg / Grip (Right)', initial: 8, prior: null, current: 12, unit: 'lbs Grip',
      deltaUnit: 'lbs', deltaNote: 'Grip improved', note: '9-HPT: Unable due to flexor synergy.' },
  ],
  slp: [
    { id: 'naming', label: 'Boston Naming Test', initial: 37, prior: null, current: 55,
      unit: '%', deltaUnit: '%', deltaNote: 'Progressing', note: '+18 percentage points in naming accuracy.' },
    { id: 'wab', label: 'WAB-R Aphasia Quotient', initial: 64.2, prior: null, current: 71.8,
      unit: '/100', deltaUnit: 'pts', deltaNote: 'Approaching Mild >76',
      note: 'AQ 71.8 remains in the moderate severity band; improved by 7.6 points from 64.2.' },
    { id: 'fatigue', label: 'Cognitive Fatigue Threshold', initial: 30, prior: null, current: 20, unit: 'mins',
      status: { tone: 'warning', text: '▼ Down from 30 mins (09/29) — may be correlated with 10/06 Baclofen titration' },
      note: 'Coordinate the medication review with MD; schedule complex cueing early with PT/OT.' },
    { id: 'diet', label: 'Dysphagia & Diet Status', initial: null, prior: null,
      current: 'Passed · Regular Diet / Thin Liquids', status: { tone: 'success', text: 'Stable — Safe oral intake' },
      note: 'Current case status; historical swallow-screen results were not supplied.' },
  ],
};

export function metricValue(metric: TrackerMetric, key: 'initial' | 'prior' | 'current') {
  const value = metric[key];
  if (value === null) return 'Not recorded';
  return `${value}${metric.unit?.startsWith('/') || metric.unit === '%' ? '' : ' '}${metric.unit ?? ''}`.trim();
}

export function metricDelta(metric: TrackerMetric): { tone: Tone; text: string } {
  if (metric.status) return metric.status;
  if (typeof metric.initial !== 'number' || typeof metric.current !== 'number') {
    return { tone: 'neutral', text: 'No dated baseline — trend unavailable' };
  }
  const delta = Number((metric.current - metric.initial).toFixed(2));
  const improved = metric.lowerIsBetter ? delta < 0 : delta > 0;
  return {
    tone: delta === 0 ? 'neutral' : improved ? 'success' : 'danger',
    text: `${delta < 0 ? '▼' : delta > 0 ? '▲' : '—'} ${delta > 0 ? '+' : ''}${delta}${metric.deltaUnit === '%' ? '' : ' '}${metric.deltaUnit ?? ''} from ${metricValue(metric, 'initial')} (09/29) — ${metric.deltaNote ?? (delta === 0 ? 'Stable' : improved ? 'Progressing' : 'Regressing')}`,
  };
}

export const careTeam = [
  { id: 'pt', label: 'Physical Therapy (PT)', tone: 'danger', badge: 'Regressing (Last 7d)',
    summary: 'BBS: 42 → 38/56 (-4) · 10MWT: 0.48 → 0.35 m/s · 2 Near-Falls' },
  { id: 'physician', label: 'Physician / Neuro (MD)', tone: 'danger', badge: 'Medication Review Flagged',
    summary: 'Baclofen doubled (5mg → 10mg TID on 10/06) · Gait/balance decline may be correlated with titration' },
  { id: 'ot', label: 'Occupational Therapy (OT)', tone: 'warning', badge: 'Tone Barrier / ADL +',
    summary: 'FMA-UE: 18 → 22/66 (+4) · R Elbow MAS Gr 2 · R Ankle MAS Gr 1+ · Self-Feeding 25%' },
  { id: 'slp', label: 'Speech-Language (SLP)', tone: 'success', badge: 'Progressing',
    summary: 'Naming Accuracy: 37% → 55% (+18%) · 20-min Fatigue Window' },
] satisfies { id: Specialty; label: string; tone: Tone; badge: string; summary: string }[];

export const safetyFlags: Record<Specialty, { title: string; text: string; tone: 'danger' | 'warning' | 'info' }[]> = {
  pt: [
    { tone: 'danger', title: 'FALL RISK FLAG (BBS: 38/56 | 10MWT: 0.35 m/s)', text: '2 near-falls this week due to right swing-phase foot drop catching on carpet.' },
    { tone: 'warning', title: 'PHARMACOLOGICAL & TEAM FLAG', text: 'Recent Baclofen increase (5mg → 10mg TID on 10/06) may be correlated with gait/balance decline from IRF discharge. Protect R shoulder subluxation (~1 finger) and pace for 20-min aphasia fatigue.' },
  ],
  physician: [
    { tone: 'warning', title: 'PHARMACOLOGICAL FLAG (Baclofen 10mg TID)', text: 'Dose doubling on 10/06 may be correlated with subsequent PT balance drop (BBS 42 → 38/56), slower gait (0.48 → 0.35 m/s), and 2 near-falls.' },
    { tone: 'info', title: 'REHAB COORDINATION FLAG', text: 'PT/OT findings indicate persistent focal tone (R Elbow MAS Gr 2, R Ankle Gr 1+) and R foot drop; consider focal spasticity options or AFO evaluation.' },
  ],
  ot: [
    { tone: 'warning', title: 'BIOMECHANICAL FLAG (R GH Subluxation)', text: 'Palpable ~1 finger-width inferior right glenohumeral subluxation with Stage 3 flexor synergy.' },
    { tone: 'warning', title: 'PHARMACOLOGICAL FLAG', text: 'Baclofen increase (10mg TID on 10/06) may be correlated with increased daytime fatigue affecting self-feeding endurance.' },
  ],
  slp: [
    { tone: 'info', title: 'COMMUNICATION FLAG (Mild Expressive Aphasia)', text: 'Word-finding difficulty with intact multi-step auditory comprehension.' },
    { tone: 'warning', title: 'PHARMACOLOGICAL FLAG', text: 'Recent Baclofen titration (10mg TID on 10/06) may be correlated with reduced cognitive-linguistic endurance (fatigue at 20 mins).' },
  ],
};

type GuidelineItem = { text: string; citation: string };
// Citation labels are supplied by the case template. They are not verified
// against the separately retrieved PDFs; only those PDFs have physical pages.
export const specialtyPlans: Record<Specialty, { title: string; scope?: string; recommended: GuidelineItem[]; discouraged: GuidelineItem[] }> = {
  pt: {
    title: 'APTA Clinical Practice Guideline to Improve Locomotor Function Following Chronic Stroke, 2020',
    scope: 'Scope: the 2020 locomotor CPG concerns injuries >6 months old; Ed is at week 12. Review applicability before using its intensity targets.',
    recommended: [
      { text: 'Moderate-to-High Intensity Walking Training (70–85% HRmax)', citation: 'Strong Recommendation, p. 11' },
      { text: 'Task-Specific Overground Stepping Practice to Target Gait Speed', citation: 'Strong Recommendation, p. 12' },
      { text: 'Ankle-Foot Orthosis (AFO) or FES to Address Swing-Phase Foot Drop', citation: 'Moderate Recommendation, p. 19' },
    ],
    discouraged: [
      { text: 'Static or Seated Balance Training Without Dynamic Walking', citation: 'Against Use to Improve Gait Speed, p. 18' },
      { text: 'Body Weight-Supported Treadmill Prioritizing Kinematics Over Intensity', citation: 'Downgraded/Limited, p. 16' },
      { text: 'Non-Weight-Bearing Lower-Extremity Strengthening Alone for Gait', citation: 'Against Use, p. 17' },
    ],
  },
  physician: {
    title: 'AHA/ASA Guidelines for Adult Stroke Rehabilitation and Recovery, 2016 / 2021',
    recommended: [
      { text: 'Targeted Botulinum Toxin Type A for Focal Post-Stroke Limb Spasticity', citation: 'Class I, Level A Recommendation, p. e114' },
      { text: 'Gradual Reassessment/Titration of Oral Antispasmodics When Sedation/Falls Occur', citation: 'Class I, Level B, p. e115' },
      { text: 'Multidisciplinary Fall-Prevention & Orthotic (AFO) Prescription Review', citation: 'Class I, Level B, p. e121' },
    ],
    discouraged: [
      { text: 'Escalating Oral CNS Antispasmodics (Baclofen/Tizanidine) With Active Fall Risk', citation: 'Downgraded - Sedation/Weakness Risk, p. e115' },
      { text: 'Abrupt Discontinuation of Oral Baclofen Without Gradual Taper', citation: 'Against Use - Withdrawal Risk' },
    ],
  },
  ot: {
    title: 'AHA/ASA & AOTA Practice Guidelines for Adults With Stroke',
    recommended: [
      { text: 'Repetitive Task-Specific Practice for Right UE Functional Recovery (Self-Feeding)', citation: 'Strong Recommendation, p. e115' },
      { text: 'Proper GH Joint Positioning & Supportive Sling (GivMohr) for Subluxation', citation: 'Strong Recommendation, p. e124' },
      { text: 'Mental Practice / Motor Imagery Integrated With Physical UE Practice', citation: 'Moderate/Strong Recommendation, p. e118' },
    ],
    discouraged: [
      { text: 'Overhead Reciprocal Pulleys With Hemiplegic Shoulder Subluxation', citation: 'Against Use - Impingement Risk, p. e124' },
      { text: 'Passive Range of Motion Alone Without Active Motor Re-Education', citation: 'Limited/Downgraded, p. e116' },
    ],
  },
  slp: {
    title: 'ASHA / RCSLT Clinical Guidelines for Post-Stroke Aphasia, 2023',
    recommended: [
      { text: 'Individualized Functional Aphasia Therapy With Phonemic Cueing Hierarchies', citation: 'Strong Recommendation, p. 84' },
      { text: 'Structured Pacing & Front-Loaded Discourse Within 20-Minute Endurance Window', citation: 'Recommended, p. 86' },
      { text: 'Supported Conversation for Adults With Aphasia (SCA) Caregiver Training', citation: 'Strong Recommendation, p. 88' },
    ],
    discouraged: [
      { text: 'Non-Speech Oral Motor Exercises (NSOMEs) for Expressive Aphasia', citation: 'Against Use, p. 91' },
      { text: 'Unstructured Conversational Stimulation Without Targeted Cueing', citation: 'Downgraded, p. 85' },
    ],
  },
};

export type NormativeComparison = {
  title: string;
  initial: string;
  current: string;
  norm: string;
  avg: string;
  normLabel: string;
  avgLabel: string;
  note?: string;
  reference?: { label: string; url: string };
};

// Case values and benchmark numbers supplied for this Ed Vance scenario.
// Only the linked interpretation/target is verified by each reference; no
// reference is represented as validating all the configured cohort averages.
export const normativePanelDescription = 'IRF Discharge Baseline (09/29) vs. Outpatient Evaluation (10/13) — Age/Gender Matched (M, 65–70)';

export const comparisons: Record<Specialty, NormativeComparison[]> = {
  pt: [
    {
      title: '10-Meter Walk Test (Gait Velocity)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '1.25 m/s',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '0.65 m/s (Community >0.80 m/s)',
      initial: '0.48 m/s (Limited Community)',
      current: '0.35 m/s (▼ -0.13 m/s · Household Only)',
    },
    {
      title: 'Berg Balance Scale (Static & Dynamic Balance)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '54 / 56',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '45 / 56 (Fall Risk Cutoff <45)',
      initial: '42 / 56 (Moderate Fall Risk)',
      current: '38 / 56 (▼ -4 pts · High Fall Risk)',
    },
    {
      title: 'Timed Up & Go (TUG — Functional Mobility)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '8.5 sec',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '14.5 sec (Fall Cutoff >14.0s)',
      initial: '16.2 sec', current: '21.4 sec (▲ +5.2s slower · Regressing)',
    },
  ],
  physician: [
    {
      title: 'Resting Blood Pressure (Secondary Stroke Prevention)',
      normLabel: 'Healthy / AHA Target Norm', norm: '< 120/80 mmHg (Target <130/80)',
      avgLabel: 'Post-Stroke Cohort Avg', avg: '136/84 mmHg',
      initial: '134/82 mmHg', current: '128/78 mmHg (Within AHA Target)',
      reference: { label: 'AHA/ASA secondary-prevention BP target', url: 'https://doi.org/10.1161/STR.0000000000000375' },
    },
    {
      title: 'Resting Heart Rate & Autonomic Tone',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '60–75 bpm',
      avgLabel: 'Post-Stroke Cohort Avg', avg: '76 bpm',
      initial: '74 bpm', current: '72 bpm (Stable rate)',
      note: 'Heart rate alone does not establish sinus rhythm or autonomic status.',
    },
    {
      title: 'Cardiorespiratory Fitness (VO2 Peak — Submaximal Est.)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '28.0 mL/kg/min',
      avgLabel: 'Post-Stroke Cohort Avg', avg: '15.5 mL/kg/min (Independent ADL >15.0)',
      initial: '13.4 mL/kg/min', current: '11.2 mL/kg/min (▼ Fatigue limited; may be correlated with titration)',
      note: 'Submaximal estimate; fatigue may be correlated with medication titration.',
    },
  ],
  ot: [
    {
      title: 'Fugl-Meyer Upper Extremity (FMA-UE Motor Recovery)',
      normLabel: 'Healthy Norm (Intact UE)', norm: '66 / 66',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '38 / 66 (Moderate Impairment)',
      initial: '18 / 66 (Severe Impairment)', current: '22 / 66 (▲ +4 pts · Proximal Gain)',
    },
    {
      title: 'Right Elbow Modified Ashworth Scale (Spasticity / Tone)',
      normLabel: 'Healthy Norm (Normal Tone)', norm: 'Grade 0 (No tone increase)',
      avgLabel: 'Post-Stroke Spasticity Avg', avg: 'Grade 1+ to Grade 2',
      initial: 'Grade 2 (Marked tone increase)',
      current: 'Grade 2 (Persistent R elbow flexor tone)',
      reference: { label: 'Modified Ashworth scoring definitions', url: 'https://www.sralab.org/rehabilitation-measures/ashworth-scale-modified-ashworth-scale' },
    },
    {
      title: 'Right Grip Dynamometry & 9-Hole Peg Dexterity',
      normLabel: 'Healthy Norm (Dominant R, M 65–70)', norm: '88 lbs Grip · 22 sec (9-HPT)',
      avgLabel: 'Stroke Cohort Avg (Paretic UE)', avg: '32 lbs Grip · 65 sec (9-HPT)',
      initial: '8 lbs Grip · 9-HPT: >120s (Unable)',
      current: '12 lbs Grip (▲ +4 lbs) · 9-HPT: Limited by flexor synergy',
    },
  ],
  slp: [
    {
      title: 'Boston Naming Test (Confrontation Word Retrieval)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '95% Accuracy',
      avgLabel: 'Post-Stroke Aphasia Avg', avg: '65% Accuracy',
      initial: '37% Accuracy', current: '55% Accuracy (▲ +18% · Progressing)',
      note: '37% → 55% is an increase of 18 percentage points.',
    },
    {
      title: 'WAB-R Aphasia Quotient (Global Language Severity)',
      normLabel: 'Healthy Norm (Non-Aphasic Cutoff)', norm: '>= 93.8 / 100',
      avgLabel: 'Post-Stroke Aphasia Avg', avg: '68.0 / 100 (Moderate: 51–75)',
      initial: '64.2 / 100 (Moderate Expressive)',
      current: '71.8 / 100 (▲ +7.6 pts · Approaching Mild >76)',
      note: '71.8 remains in the moderate AQ severity band; the cutoff does not exclude all residual language deficits.',
    },
    {
      title: 'Cognitive-Linguistic Endurance Window (Sustained Discourse)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '> 60 mins continuous discourse',
      avgLabel: 'Post-Stroke Aphasia Avg', avg: '35 mins before word-finding decay',
      initial: '30 mins tolerance', current: '20 mins (▼ -10 mins · Fatigue may be correlated with Baclofen titration)',
      note: 'Reduced endurance may be correlated with the 10/06 Baclofen increase.',
    },
  ],
};
