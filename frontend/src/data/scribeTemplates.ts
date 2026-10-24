import type { SoapNote } from '../utils/clinicalSoap';
export type ScribeTemplate = { label: string; shorthand: string; soap: SoapNote };

// Explicit synthetic Ed Vance samples. Custom transcripts never inherit these facts.
export const scribeTemplates: ScribeTemplate[] = [
  {
    label: 'PT Skilled SOAP',
    shorthand: `s: 67M, 12wk post-L MCA ischemic stroke, outpatient PT evaluation. Reports 2 near-falls at home this week catching R toe on living room rug. Feels drowsy/sluggish since Baclofen increased 5mg to 10mg TID on 10/06. R calf tightness. Goal: independent walking to mailbox.
o: Gait 50ft w/ hemi-walker and SBA; absent R heel strike, severe swing-phase R foot drop, R hip hiking/circumduction. 10MWT 0.35 m/s from 0.48 m/s at IRF discharge. BBS 38/56 from 42/56. TUG 21.4s from 16.2s. R ankle plantarflexors MAS Gr 1+; R LE Brunnstrom Stg 4. Verbal DF cueing provided.
a: Mobility regression temporally correlated with Baclofen increase; sedation may contribute. High fall risk and impaired swing clearance; candidate for R AFO trial.
p: Skilled outpatient PT 2x/wk for 6wk: task-specific overground gait, obstacle clearance, dynamic balance. Flag MD for Baclofen review given drowsiness and near-falls. Request R AFO evaluation.`,
    soap: {
      subjective: "Patient is a 67-year-old male, 12 weeks post-left MCA ischemic stroke, presenting for outpatient physical therapy evaluation. He reports two near-falls at home this week after catching his right toe on the living room rug. He endorses daytime drowsiness and sluggishness since oral Baclofen increased from 5 mg to 10 mg three times daily on 10/06, with persistent right calf tightness. His primary functional goal is to walk independently to his mailbox.",
      objective: '• Gait & Ambulation: Ambulated 50 ft with a hemi-walker and standby assistance (SBA). Kinematic deviations include absent right heel strike, severe right swing-phase foot drop, and compensatory right hip hiking/circumduction. Verbal dorsiflexion cueing provided.\n• 10-Meter Walk Test (10MWT): 0.35 m/s; change of -0.13 m/s from 0.48 m/s at inpatient rehabilitation discharge.\n• Berg Balance Scale (BBS): 38/56; change of -4 points from 42/56.\n• Timed Up & Go (TUG): 21.4 seconds; +5.2 seconds from 16.2 seconds.\n• Tone & Motor Staging: Right ankle plantarflexors MAS Grade 1+; right LE Brunnstrom Stage 4.',
      assessment: 'Patient demonstrates functional mobility regression in gait velocity (-0.13 m/s) and Berg Balance (-4 points), temporally correlated with the 10/06 Baclofen dose escalation. Right swing-phase foot drop limits foot clearance and contributes to fall risk; medication-related sedation may also contribute. Findings support a right ankle-foot orthosis (AFO) trial to improve swing clearance and initial contact, with interdisciplinary medication review.',
      plan: '1. Skilled outpatient PT twice weekly for six weeks, focusing on task-specific overground gait training, obstacle clearance, and dynamic balance.\n2. Interdisciplinary Care Coordination: Flag the attending physician for oral Baclofen review given drowsiness and recent near-falls.\n3. Orthotic Evaluation: Request evaluation for a right AFO trial.',
    },
  },
  {
    label: 'OT Functional SOAP',
    shorthand: `s: Goal to feed self with dominant R hand. Reports daytime fatigue since Baclofen increase on 10/06.
o: FMA-UE 22/66 from 18/66 at IRF discharge. R elbow flexors MAS Gr 2; R UE Brunnstrom Stg 3 flexor synergy. Approximately 1-finger R GH subluxation. R grip 12lb from 8lb; 9-HPT unable due to flexor synergy. Self-feeding goal 25%; built-up utensil grasp independent, scooping mod A, bring-to-mouth max A. GivMohr sling for upright activity.
a: Proximal UE gain with persistent distal flexor synergy and shoulder instability limiting safe self-feeding.
p: Repetitive task-specific self-feeding practice with built-up utensils, graded assistance, shoulder positioning and GivMohr support during upright mobility. Coordinate fatigue and medication concerns with PT/MD.`,
    soap: {
      subjective: 'Patient identifies independent self-feeding with his dominant right hand as a primary goal. He reports daytime fatigue following the 10/06 Baclofen increase.',
      objective: '• Upper-Extremity Motor Recovery: FMA-UE 22/66, improved by four points from 18/66 at inpatient rehabilitation discharge.\n• Tone & Motor Staging: Right elbow flexors MAS Grade 2; right UE Brunnstrom Stage 3 with flexor synergy.\n• Shoulder Integrity: Approximately one-finger right glenohumeral subluxation; GivMohr sling used for upright activity.\n• Hand Function: Right grip 12 lb, increased from 8 lb; unable to complete the 9-Hole Peg Test due to flexor synergy.\n• Self-Feeding: Goal completion 25%. Independent grasp with a built-up utensil, moderate assistance for scooping, and maximal assistance to bring the utensil to the mouth.',
      assessment: 'Proximal right upper-extremity gains are present, while persistent Grade 2 elbow tone, Stage 3 flexor synergy, and glenohumeral instability limit distal control and safe self-feeding. Fatigue may be associated with recent medication titration and warrants team review.',
      plan: '1. Continue repetitive, task-specific self-feeding practice with built-up utensils and graded assistance.\n2. Maintain shoulder positioning and GivMohr support during upright activity; avoid traction on the right upper extremity.\n3. Coordinate fatigue management and medication concerns with PT and the attending physician.',
    },
  },
  {
    label: 'SLP Cognitive-Linguistic SOAP',
    shorthand: `s: Wants better word finding for daily conversation; fatigue after 20 minutes, previously 30 minutes.
o: WAB-R AQ 71.8/100 from 64.2. Boston Naming accuracy 55% from 37%. Mild expressive aphasia; multi-step auditory comprehension intact. Regular diet and thin liquids; passed swallow screen. Cognitive-linguistic endurance 20min.
a: Improved language scores with persistent word-finding difficulty and reduced sustained discourse tolerance.
p: Functional naming with phonemic cueing and supported conversation, front-load complex tasks in first 15min, schedule rest before 20min fatigue, teach caregiver communication strategies. Coordinate Baclofen/fatigue review with MD/PT/OT.`,
    soap: {
      subjective: 'Patient wants to improve word finding during daily conversation. He reports fatigue after approximately 20 minutes, compared with a previous 30-minute tolerance.',
      objective: '• Language Severity: WAB-R Aphasia Quotient 71.8/100, improved by 7.6 points from 64.2.\n• Confrontation Naming: Boston Naming accuracy 55%, improved from 37%.\n• Communication: Mild expressive aphasia is described in the case; multi-step auditory comprehension is intact.\n• Endurance: Cognitive-linguistic fatigue occurs after approximately 20 minutes.\n• Diet: Passed swallow screen; regular diet with thin liquids.',
      assessment: 'Naming accuracy and WAB-R scores demonstrate progress, with persistent word-finding difficulty and reduced sustained discourse tolerance. The WAB-R quotient remains in the moderate severity range despite the case description of mild expressive symptoms. Earlier fatigue may be associated with medication titration and should be reviewed with the care team.',
      plan: '1. Provide functional naming practice using phonemic cueing and supported conversation.\n2. Front-load complex language tasks during the first 15 minutes and schedule rest before the 20-minute fatigue threshold.\n3. Teach caregiver communication strategies and coordinate fatigue/medication review with MD, PT, and OT.',
    },
  },
  {
    label: 'MD Neuro Follow-up',
    shorthand: `s: Post-L MCA stroke spasticity/fall-risk review. Drowsiness after Baclofen increased 5mg to 10mg TID on 10/06; 2 near-falls reported by PT.
o: Baclofen 10mg TID (30mg/day). Team measures: BBS 42 to 38/56, 10MWT 0.48 to 0.35 m/s. R elbow MAS Gr 2, R ankle plantarflexors MAS Gr 1+. R UE Stg 3 flexor synergy; R LE Stg 4. R foot drop; approximately 1-finger R GH subluxation.
a: Persistent focal spasticity with mobility decline and drowsiness temporally associated with oral Baclofen escalation; reassess other causes of decline.
p: Review oral Baclofen and consider gradual taper if appropriate; do not abruptly discontinue. Evaluate focal RUE Botulinum Toxin A. Co-sign PT right AFO evaluation request. Coordinate safety, shoulder protection and fatigue pacing with PT/OT/SLP.`,
    soap: {
      subjective: 'Patient presents for attending-physician review of post-left MCA stroke spasticity and fall risk. Daytime drowsiness followed the 10/06 increase in Baclofen from 5 mg to 10 mg three times daily. PT reports two near-falls.',
      objective: '• Current Medication: Oral Baclofen 10 mg three times daily, totaling 30 mg/day.\n• Multidisciplinary Findings: Berg Balance decreased from 42 to 38/56; gait velocity decreased from 0.48 to 0.35 m/s.\n• Focal Tone: Right elbow flexors MAS Grade 2; right ankle plantarflexors MAS Grade 1+.\n• Motor Staging: Right UE Stage 3 flexor synergy; right LE Stage 4.\n• Additional Team Findings: Right swing-phase foot drop and approximately one-finger right glenohumeral subluxation.',
      assessment: 'Persistent focal post-stroke spasticity coexists with drowsiness and functional mobility decline temporally associated with oral Baclofen escalation. Medication effects may contribute; reassess other causes before attributing the decline to sedation alone.',
      plan: '1. Review the oral Baclofen regimen and consider a gradual taper if clinically appropriate; avoid abrupt discontinuation.\n2. Evaluate focal right upper-extremity Botulinum Toxin type A treatment.\n3. Co-sign PT request for a right AFO evaluation.\n4. Coordinate fall prevention, shoulder protection, and fatigue pacing across PT, OT, and SLP.',
    },
  },
];
export function scribeTemplate(label: string): ScribeTemplate {
  return scribeTemplates.find(template => template.label === label) ?? scribeTemplates[0];
}
