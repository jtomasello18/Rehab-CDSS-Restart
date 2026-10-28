export type ScribeQuickAction = { label: string; prompt: string };

const skilledJustification: ScribeQuickAction = {
  label: 'Medicare Part B Skilled Justification',
  prompt: 'Refine the Assessment with a concise Medicare Part B skilled-justification paragraph for the selected therapy specialty. Connect the documented functional deficits and goals to the skilled services actually described. Write finished clinical prose, not instructions. Do not invent services, caregiver limitations, treatment time, or coverage eligibility.',
};
const condense: ScribeQuickAction = { label: 'Condense Narrative', prompt: 'Condense Narrative' };

const actions: Record<string, readonly ScribeQuickAction[]> = {
  'PT Skilled SOAP': [
    skilledJustification,
    {
      label: 'Align with CPT 97116 (Gait) & 97112 (Neuro)',
      prompt: 'Align the documented PT interventions with CPT 97116 (gait training) and 97112 (neuromuscular re-education), only where supported. Use clean Objective bullets with each supported code and only explicitly documented intervention-specific minutes. In Plan, connect each code to its distinct documented future goal; state general frequency/duration only once. Do not invent services, minutes, goals, or billing eligibility, and do not add billing meta-headers.',
    },
    condense,
  ],
  'OT Functional SOAP': [
    skilledJustification,
    {
      label: 'Align with CPT 97530 (Therapeutic Act)',
      prompt: 'Refine the OT Objective and Plan to clarify documented therapeutic activities relevant to CPT 97530. Connect the actual activities to documented functional performance and ADL goals. Keep performed activities separate from planned care; include minutes only when explicitly attributed to the activity. Do not invent interventions, scores, time, or billing eligibility. Write finished clinical documentation without billing meta-headers.',
    },
    {
      label: 'Highlight ADL & FMA-UE Deficits',
      prompt: 'Refine the OT note to highlight documented ADL limitations and FMA-UE findings, including functional consequences and progress when supported by dated measurements. Connect these findings to the existing Assessment and Plan. Preserve all scores, assistance levels, and dates; do not invent an FMA-UE measurement or an ADL deficit.',
    },
  ],
  'SLP Cognitive-Linguistic SOAP': [
    skilledJustification,
    {
      label: 'Align with CPT 92507 (Speech/Cognitive)',
      prompt: 'Refine the SLP Objective and Plan to clarify the documented speech/language treatment relevant to CPT 92507, only where supported. Describe cognitive-linguistic findings in their documented communication context; do not assume every cognitive intervention qualifies for this code. Preserve actual services, goals, and time. Do not invent treatment, minutes, or billing eligibility, and do not add billing meta-headers.',
    },
    {
      label: 'Highlight Aphasia/Fatigue Impact',
      prompt: 'Refine the SLP note to highlight the documented impact of aphasia and cognitive-linguistic fatigue on communication and participation. Preserve recorded scores and endurance limits and connect them to existing goals and pacing plans. Do not invent deficits, fatigue thresholds, or medication causation. Write finished clinical prose.',
    },
  ],
  'MD Neuro Follow-up': [
    {
      label: 'Align with E/M Level 4 (99214) Complexity',
      prompt: 'Organize the physician follow-up note to clearly describe the documented encounter complexity for E/M 99214 review. Use only documented problems, data reviewed, management decisions, and risk; retain time only when explicitly recorded. Do not invent complexity, assign an E/M level, or assert that 99214 requirements are met. Do not add therapy Medicare skilled-necessity language. Write finished physician documentation.',
    },
    {
      label: 'Highlight Medical Decision Making (MDM)',
      prompt: 'Refine the physician Assessment and Plan to clearly express documented medical decision making: problems addressed, relevant data reviewed, treatment decisions, and risk considerations. Preserve uncertainty and the actual rationale for medication or follow-up decisions. Do not invent data review, discussions, diagnoses, risk, or an E/M level. Write finished clinical documentation rather than instructions.',
    },
    condense,
  ],
};

export function getScribeQuickActions(template: string): readonly ScribeQuickAction[] {
  return actions[template] ?? actions['PT Skilled SOAP'];
}
