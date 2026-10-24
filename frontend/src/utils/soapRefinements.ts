import { expandClinicalAbbreviations, type SoapNote } from './clinicalSoap';

const sections = ['subjective', 'objective', 'assessment', 'plan'] as const;
const AUDIT = 'MEDICARE PART B SKILLED NECESSITY';
const CPT = 'CPT BILLING CODE ALIGNMENT';

function withoutBlock(text: string, label: string): string {
  return text.replace(new RegExp(`\\n?\\[${label}\\]:?[\\s\\S]*?(?=\\n\\[|$)`, 'g'), '').trim();
}
function block(text: string, label: string, content: string): string {
  return `${withoutBlock(text, label)}\n\n[${label}]:\n${content}`.trim();
}
function lines(text: string): string[] {
  return text.split(/\n+|(?<=[.!?])\s+(?=[A-Z])/).map(line => line.replace(/^\s*(?:[•*-]|\d+[.)])\s*/, '').trim()).filter(Boolean);
}
function baseNote(note: SoapNote): SoapNote {
  return Object.fromEntries(sections.map(section => [section, withoutBlock(withoutBlock(note[section], AUDIT), CPT)])) as SoapNote;
}

/** Labeled, repeatable documentation support using this note's findings only. */
export function addSkilledJustification(note: SoapNote, template: string): SoapNote {
  const base = baseNote(note);
  const discipline = template.startsWith('OT') ? 'occupational therapy' : template.startsWith('SLP') ? 'speech-language pathology'
    : template.startsWith('MD') ? 'physician assessment and multidisciplinary coordination' : 'physical therapy';
  const findings = lines(base.objective).slice(0, 3).join(' ');
  const safety = lines(base.subjective).filter(line => /near.falls?|drows|fatigue|sluggish/i.test(line)).slice(0, 2).join(' ');
  const focus = template.startsWith('OT') ? 'task grading, upper-extremity positioning, assistance needs, and response to functional activity'
    : template.startsWith('SLP') ? 'individualized language cueing, communication task progression, and fatigue-related performance'
      : template.startsWith('MD') ? 'medication tolerability, neurological findings, and interdisciplinary safety concerns'
        : 'gait mechanics, assistance and cueing needs, balance-related safety, and response to task progression';
  return {
    ...note,
    assessment: block(note.assessment, AUDIT, `Documented findings supporting skilled ${discipline} review: ${findings}${safety ? ` Reported safety concerns: ${safety}` : ''}\nClinical rationale: The documented deficits require individualized assessment of ${focus}. The treating clinician must confirm the services actually provided and why they require professional skill; this draft does not establish coverage.`),
    plan: block(note.plan, AUDIT, `Relate the documented plan to functional goals and record skilled decisions, assistance/cueing, patient response, and progression or modification at each visit. Confirm the plan of care, frequency, and duration from the encounter; do not infer treatment minutes or caregiver limitations.`),
  };
}

/** Coding descriptions are distinct from a claim of performed/billable services. */
export function alignCpt(note: SoapNote, template: string): SoapNote {
  const objective = baseNote(note).objective;
  const gait = lines(objective).filter(line => /(?:ambulated|walked|gait training|overground gait)/i.test(line)).join(' ');
  const neuro = lines(objective).filter(line => /(?:neuromuscular re-education|weight.shifts?|postural training|balance training|motor.control training)/i.test(line)).join(' ');
  const inScope = template.startsWith('PT') || template.startsWith('OT');
  const content = inScope ? [
    `• CPT 97116 — Gait Training: ${gait ? `Documented activity for clinician coding review: ${gait}` : 'No performed gait-training activity is explicitly documented in Objective.'}`,
    `• CPT 97112 — Neuromuscular Re-education: ${neuro ? `Documented activity for clinician coding review: ${neuro}` : 'No performed neuromuscular re-education activity is explicitly documented in Objective. A balance score or motor-stage finding alone is not a performed intervention.'}`,
    '• Time and units: Use only actual, code-specific skilled treatment minutes documented in this encounter and applicable payer rules. No minutes or units are assigned by this action.',
  ].join('\n') : 'CPT 97116 describes gait training; CPT 97112 describes neuromuscular re-education. These codes are not assigned to this SLP/physician note. Select codes appropriate to the documented specialty services; no therapy activities, minutes, or units have been inferred.';
  return {
    ...note,
    objective: block(note.objective, CPT, content),
    plan: block(note.plan, CPT, 'Distinguish planned care from performed services. Verify activity descriptions, actual timed treatment, discipline, and payer requirements before assigning codes or units. This is documentation alignment, not billing verification.'),
  };
}

/** Group all source statements into at most three bullets; retain the full facts. */
export function condenseSoap(note: SoapNote): SoapNote {
  const source = baseNote(note);
  return Object.fromEntries(sections.map(section => {
    const statements = lines(source[section]).map(line => line
      .replace(/^(?:The patient|Patient|He|She|They)\s+(?:reports|endorses|identifies|demonstrates)\s+/i, '')
      .replace(/^Patient is a\s+/i, '')
      .replace(/inpatient rehabilitation discharge/gi, 'IRF discharge')
      .replace(/three times daily/gi, 'TID')
      .replace(/Berg Balance Scale \(BBS\)/g, 'BBS')
      .replace(/10-Meter Walk Test \(10MWT\)/g, '10MWT')
      .replace(/Timed Up & Go \(TUG\)/g, 'TUG')
      .replace(/standby assistance \(SBA\)/g, 'SBA')
      .replace(/Kinematic deviations include /g, '')
      .replace(/(?:change of |improved by )/gi, '')
      .replace(/approximately /gi, '~')
      .replace(/\bseconds\b/g, 'sec'));
    const size = Math.max(1, Math.ceil(statements.length / 3));
    const bullets: string[] = [];
    for (let index = 0; index < statements.length; index += size) {
      bullets.push(`• ${section[0].toUpperCase()}: ${statements.slice(index, index + size).join(' ')}`);
    }
    return [section, bullets.join('\n')];
  })) as SoapNote;
}

export function polishSoap(note: SoapNote): SoapNote {
  return Object.fromEntries(sections.map(section => [section, expandClinicalAbbreviations(note[section])
    .replace(/\b(?:the )?patient reports feels\b/gi, 'The patient feels')
    .replace(/\b(?:the )?patient reports denies\b/gi, 'The patient denies')])) as SoapNote;
}

/** Narrow local commands; open-ended clinical edits go to the server-side LLM. */
export function applyLocalInstruction(note: SoapNote, instruction: string, template: string): SoapNote | null {
  const request = instruction.trim().replace(/[.!]+$/, '');
  if (/^(?:please\s+)?(?:condense(?: narrative)?|shorten(?: (?:the )?note)?|make (?:it |the note )?(?:concise|brief)|use bullets|convert to bullets)$/i.test(request)) return condenseSoap(note);
  if (/^(?:please\s+)?(?:fix|improve|polish) (?:the )?(?:grammar|wording)$/i.test(request)) return polishSoap(note);
  if (/^(?:add |apply )?(?:medicare part b skilled justification|skilled justification)$/i.test(request)) return addSkilledJustification(note, template);
  if (/^(?:align with |add )?cpt 97116 (?:&|and) 97112$/i.test(request)) return alignCpt(note, template);
  if (/^(?:please\s+)?(?:number|use numbered steps (?:in|for)) (?:the )?plan$/i.test(request)) return { ...note, plan: lines(note.plan).map((line, index) => `${index + 1}. ${line}`).join('\n') };
  const replacement = request.match(/^replace\s+"([^"]+)"\s+with\s+"([^"]*)"$/i);
  if (replacement) return Object.fromEntries(sections.map(section => [section, note[section].split(replacement[1]).join(replacement[2])])) as SoapNote;
  return null;
}
