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
  { id: 'pt', label: 'Physical Therapy (PT)', tone: 'danger', badge: 'Regressing' },
  { id: 'physician', label: 'Physician / Neuro (MD)', tone: 'danger', badge: 'Medication Review Flagged' },
  { id: 'ot', label: 'Occupational Therapy (OT)', tone: 'success', badge: 'Progressing' },
  { id: 'slp', label: 'Speech-Language (SLP)', tone: 'success', badge: 'Progressing' },
] satisfies { id: Specialty; label: string; tone: Tone; badge: string }[];

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

export type NormativeComparison = {
  title: string;
  initial: string;
  current: string;
  norm: string;
  avg: string;
  normLabel: string;
  avgLabel: string;
  note?: string;
  citations: { label: string; url: string }[];
  citationScope: string;
};

// Case values and benchmark numbers supplied for this Ed Vance scenario.
// Only the linked interpretation/target is verified by each reference; no
// reference is represented as validating all the configured cohort averages.
export const normativePanelDescription = 'Age/Gender Matched Reference Values (M, 65–70)';

const strokeRehab2026 = 'https://doi.org/10.1161/STR.0000000000000536';
const locomotor2020 = 'https://doi.org/10.1097/NPT.0000000000000303';
const neuroCore2018 = 'https://doi.org/10.1097/NPT.0000000000000229';
const steffen2002 = 'https://pubmed.ncbi.nlm.nih.gov/11856064/';

export const comparisons: Record<Specialty, NormativeComparison[]> = {
  pt: [
    {
      title: '10-Meter Walk Test (Gait Velocity)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '1.25 m/s',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '0.65 m/s (Community >0.80 m/s)',
      initial: '0.48 m/s (Limited Community)',
      current: '0.35 m/s (▼ -0.13 m/s · Household Only)',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Table 4, p. e550: <0.4, 0.4–0.8, >0.8 m/s ambulation categories; Sec. 5.7, p. e573: walking-aid context)', url: strokeRehab2026 },
        { label: 'APTA Locomotor CPG (Hornby et al., 2020, p. 56: training parameters)', url: locomotor2020 },
        { label: 'Age/sex normative study: Steffen et al., 2002', url: steffen2002 },
      ],
      citationScope: 'Steffen reports decade-based age groups, not a specific M 65–70 group. The displayed healthy and cohort comparators are configured case benchmarks.',
    },
    {
      title: 'Berg Balance Scale (Static & Dynamic Balance)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '54 / 56',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '45 / 56 (Fall Risk Cutoff <45)',
      initial: '42 / 56 (Moderate Fall Risk)',
      current: '38 / 56 (▼ -4 pts · High Fall Risk)',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 4.2, Table 4, p. e550: balance assessment)', url: strokeRehab2026 },
        { label: 'APTA Neuro Core Set CPG (Moore et al., 2018, Table 7, p. 192: BBS measurement evidence)', url: neuroCore2018 },
        { label: 'Age/sex normative study: Steffen et al., 2002', url: steffen2002 },
      ],
      citationScope: 'These citations do not establish 54/56 as an exact M 65–70 mean or <45 as a universal stroke fall cutoff. Displayed comparator values are case benchmarks.',
    },
    {
      title: 'Timed Up & Go (TUG — Functional Mobility)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '8.5 sec',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '14.5 sec (Fall Cutoff >14.0s)',
      initial: '16.2 sec', current: '21.4 sec (▲ +5.2s slower · Regressing)',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 4.2, pp. e549–e550, Table 4: TUG assessment)', url: strokeRehab2026 },
        { label: 'TUG normative meta-analysis: Bohannon, 2006 (ages 60–69: mean 8.1 sec)', url: 'https://pubmed.ncbi.nlm.nih.gov/16914068/' },
        { label: 'Age/sex normative study: Steffen et al., 2002', url: steffen2002 },
      ],
      citationScope: 'The displayed 8.5-sec and cohort comparators are case benchmarks. Moore 2018 does not establish a >14-sec stroke fall cutoff.',
    },
  ],
  physician: [
    {
      title: 'Resting Blood Pressure (Secondary Stroke Prevention)',
      normLabel: 'Healthy / AHA Target Norm', norm: '< 120/80 mmHg (Target <130/80)',
      avgLabel: 'Post-Stroke Cohort Avg', avg: '136/84 mmHg',
      initial: '134/82 mmHg', current: '128/78 mmHg (Within AHA Target)',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 5.8, p. e575: secondary-prevention context)', url: strokeRehab2026 },
        { label: 'AHA/ASA Secondary Stroke Prevention CPG (Kleindorfer et al., 2021, hypertension recommendations: <130/80 mmHg for most patients with hypertension)', url: 'https://doi.org/10.1161/STR.0000000000000375' },
      ],
      citationScope: 'The prevention target is a treatment goal, not an age/sex population mean; 136/84 mmHg is a configured cohort comparator.',
    },
    {
      title: 'Resting Heart Rate & Autonomic Tone',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '60–75 bpm',
      avgLabel: 'Post-Stroke Cohort Avg', avg: '76 bpm',
      initial: '74 bpm', current: '72 bpm (Stable rate)',
      note: 'Heart rate alone does not establish sinus rhythm or autonomic status.',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 5.5, supportive text 3, p. e564: poststroke resting HR and HRR dosing)', url: strokeRehab2026 },
        { label: 'APTA Locomotor CPG (Hornby et al., 2020, Action Statement 1, p. 63: exercise intensity and monitoring)', url: locomotor2020 },
      ],
      citationScope: 'Exercise-dosing guidance does not establish the displayed 60–75 bpm healthy range or 76 bpm cohort mean; these are case comparators.',
    },
    {
      title: 'Cardiorespiratory Fitness (VO2 Peak — Submaximal Est.)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '28.0 mL/kg/min',
      avgLabel: 'Post-Stroke Cohort Avg', avg: '15.5 mL/kg/min (Independent ADL >15.0)',
      initial: '13.4 mL/kg/min', current: '11.2 mL/kg/min (▼ Fatigue limited; may be correlated with titration)',
      note: 'Submaximal estimate; fatigue may be correlated with medication titration.',
      citations: [
        { label: 'APTA Locomotor CPG (Hornby et al., 2020, Action Statement 1, pp. 63–64: exercise intensity and %VO2 peak protocols)', url: locomotor2020 },
        { label: 'AHA/ASA Stroke Exercise Statement (Billinger et al., 2014)', url: 'https://pubmed.ncbi.nlm.nih.gov/24846875/' },
        { label: 'AHA/ASA Stroke Rehab CPG (Winstein et al., 2016, Deconditioning and Fitness: 15–18 mL/kg/min independent-living context)', url: 'https://doi.org/10.1161/STR.0000000000000098' },
      ],
      citationScope: 'This is not a universal >15.0 ADL cutoff. The displayed 28.0 healthy and 15.5 cohort values are configured comparators, not verified ACSM age/sex norms.',
    },
  ],
  ot: [
    {
      title: 'Fugl-Meyer Upper Extremity (FMA-UE Motor Recovery)',
      normLabel: 'Healthy Norm (Intact UE)', norm: '66 / 66',
      avgLabel: 'Stroke Cohort Avg (12 wk)', avg: '38 / 66 (Moderate Impairment)',
      initial: '18 / 66 (Severe Impairment)', current: '22 / 66 (▲ +4 pts · Proximal Gain)',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Table 4, p. e550: UE motor scale 0–66)', url: strokeRehab2026 },
        { label: 'Fugl-Meyer et al., 1975, pp. 13–31: original motor assessment', url: 'https://pubmed.ncbi.nlm.nih.gov/1135616/' },
      ],
      citationScope: '66 is the scale maximum, not an age-matched mean. The 38/66 cohort comparator is a configured case benchmark.',
    },
    {
      title: 'Right Elbow Modified Ashworth Scale (Spasticity / Tone)',
      normLabel: 'Healthy Norm (Normal Tone)', norm: 'Grade 0 (No tone increase)',
      avgLabel: 'Post-Stroke Spasticity Avg', avg: 'Grade 1+ to Grade 2',
      initial: 'Grade 2 (Marked tone increase)',
      current: 'Grade 2 (Persistent R elbow flexor tone)',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Table 4, p. e550; Sec. 5.3, p. e559: tone assessment and management)', url: strokeRehab2026 },
        { label: 'Bohannon & Smith, 1987, pp. 206–207: Modified Ashworth Scale', url: 'https://pubmed.ncbi.nlm.nih.gov/3809245/' },
      ],
      citationScope: 'Grade 0 describes no tone increase. Grade 1+ to 2 is a case comparator, not an established average for all stroke survivors.',
    },
    {
      title: 'Right Grip Dynamometry & 9-Hole Peg Dexterity',
      normLabel: 'Healthy Norm (Dominant R, M 65–70)', norm: '88 lbs Grip · 22 sec (9-HPT)',
      avgLabel: 'Stroke Cohort Avg (Paretic UE)', avg: '32 lbs Grip · 65 sec (9-HPT)',
      initial: '8 lbs Grip · 9-HPT: >120s (Unable)',
      current: '12 lbs Grip (▲ +4 lbs) · 9-HPT: Limited by flexor synergy',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Table 4, p. e550: grip/pinch dynamometry)', url: strokeRehab2026 },
        { label: 'Mathiowetz et al., 1985, pp. 69–74: adult grip and pinch norms', url: 'https://pubmed.ncbi.nlm.nih.gov/3970660/' },
        { label: 'Mathiowetz et al., 1985, pp. 24–38: adult Nine-Hole Peg Test norms', url: 'https://doi.org/10.1177/153944928500500102' },
      ],
      citationScope: 'Norms depend on age band, tested hand and protocol. The displayed grip/peg comparators are case benchmarks, not exact M 65–70 values verified from these papers.',
    },
  ],
  slp: [
    {
      title: 'Boston Naming Test (Confrontation Word Retrieval)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '95% Accuracy',
      avgLabel: 'Post-Stroke Aphasia Avg', avg: '65% Accuracy',
      initial: '37% Accuracy', current: '55% Accuracy (▲ +18% · Progressing)',
      note: '37% → 55% is an increase of 18 percentage points.',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 4.3, p. e551; Sec. 6.2, p. e588: communication assessment and treatment)', url: strokeRehab2026 },
        { label: 'Tombaugh & Hubley, 1997, pp. 922–932: 60-item Boston Naming Test age/education norms', url: 'https://pubmed.ncbi.nlm.nih.gov/9524887/' },
      ],
      citationScope: 'BNT norms depend on test version, age and education. The 95% healthy and 65% aphasia values are configured comparators, not universal norms.',
    },
    {
      title: 'WAB-R Aphasia Quotient (Global Language Severity)',
      normLabel: 'Healthy Norm (Non-Aphasic Cutoff)', norm: '>= 93.8 / 100',
      avgLabel: 'Post-Stroke Aphasia Avg', avg: '68.0 / 100 (Moderate: 51–75)',
      initial: '64.2 / 100 (Moderate Expressive)',
      current: '71.8 / 100 (▲ +7.6 pts · Approaching Mild >76)',
      note: '71.8 remains in the moderate AQ severity band; the cutoff does not exclude all residual language deficits.',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 4.3, p. e551; Sec. 6.2, p. e588)', url: strokeRehab2026 },
        { label: 'WAB-R (Kertesz, 2007): publisher assessment information', url: 'https://www.pearsonassessments.com/content/dam/school/global/clinical/us/assets/wab-r/wabr-brochure.pdf' },
        { label: 'Discourse Characteristics in Aphasia Beyond the Western Aphasia Battery Cutoff: limitations of the 93.8 threshold', url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5829792/' },
      ],
      citationScope: 'AQ 93.8 is a classification threshold, not an age/sex normative mean. The 68.0 cohort value is a configured comparator.',
    },
    {
      title: 'Cognitive-Linguistic Endurance Window (Sustained Discourse)',
      normLabel: 'Healthy Norm (M, 65–70)', norm: '> 60 mins continuous discourse',
      avgLabel: 'Post-Stroke Aphasia Avg', avg: '35 mins before word-finding decay',
      initial: '30 mins tolerance', current: '20 mins (▼ -10 mins · Fatigue may be correlated with Baclofen titration)',
      note: 'Reduced endurance may be correlated with the 10/06 Baclofen increase.',
      citations: [
        { label: '2026 AHA/ASA Stroke Rehab CPG (Richards et al., Sec. 3.9, pp. e544–e545: poststroke fatigue)', url: strokeRehab2026 },
        { label: 'ASHA Aphasia Practice Portal, Assessment: account for endurance and fatigue during testing', url: 'https://www.asha.org/practice-portal/clinical-topics/aphasia/' },
      ],
      citationScope: 'These sources do not define a standardized discourse-duration norm. The >60-min healthy and 35-min cohort entries are case comparators, not published cutoffs.',
    },
  ],
};
