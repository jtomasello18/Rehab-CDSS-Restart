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
function documented(text: string): string[] {
  return lines(text).filter(line => !/^(?:not documented|a clinician must complete|no additional clinical conclusions)/i.test(line));
}
function positive(line: string, pattern: RegExp): boolean {
  return pattern.test(line) && !/\b(?:no|without|denies|not present|not performed)\b/i.test(line);
}

/** Labeled, repeatable documentation support using this note's findings only. */
export function addSkilledJustification(note: SoapNote, template: string): SoapNote {
  const base = baseNote(note);
  const discipline = template.startsWith('OT') ? 'occupational therapy' : template.startsWith('SLP') ? 'speech-language pathology'
    : template.startsWith('MD') ? 'physician assessment and multidisciplinary coordination' : 'physical therapy';
  const findings = documented(base.objective).slice(0, 3).join(' ');
  const impressions = documented(base.assessment).join(' ');
  const evidence = [...documented(base.objective), ...documented(base.assessment), ...documented(base.subjective)];
  if (!evidence.length) return note;
  const hasDeficits = evidence.some(line => positive(line, /\b(?:deficits?|limited|impair\w*|weakness|foot drop|near.falls?|fall risk|regression|assistance|sba|cga|aphasia|dysphagia|flexor synergy)\b/i));
  const focus = template.startsWith('OT') ? 'graded functional task performance, upper-extremity motor control, and assistance needs'
    : template.startsWith('SLP') ? 'individualized communication strategies, language-task progression, and activity tolerance'
      : template.startsWith('MD') ? 'neurological status, medication tolerability, and interdisciplinary management'
        : 'movement mechanics, task progression, and safe functional mobility';
  const rationale = hasDeficits
    ? `Skilled ${discipline} services are medically necessary to address the documented functional deficits. ${impressions}${findings ? ` Objective findings include: ${findings}` : ''} Licensed clinician judgment is required to individualize ${focus} in response to the documented limitations.`
    : `The recorded encounter describes ${discipline} findings without a characterized functional limitation requiring skilled rehabilitation. ${impressions || findings}`;
  return {
    ...note,
    assessment: block(note.assessment, AUDIT, `Skilled Justification (Medicare Part B): ${rationale}`),
  };
}

/** Coding descriptions are distinct from a claim of performed/billable services. */
export function alignCpt(note: SoapNote, template: string): SoapNote {
  const base = baseNote(note);
  const gaitPattern = /(?:ambulated|walked|gait training|overground gait|locomotor training)/i;
  const neuroPattern = /(?:neuromuscular re-education|weight.shifts?|postural (?:control|training)|balance training|proprioceptive facilitation|motor.control training|synergy re-education)/i;
  const gait = documented(base.objective).filter(line => positive(line, gaitPattern)).join(' ');
  const neuro = documented(base.objective).filter(line => positive(line, neuroPattern)).join(' ');
  const plannedGait = documented(base.plan).filter(line => positive(line, gaitPattern)).join(' ');
  const plannedNeuro = documented(base.plan).filter(line => positive(line, neuroPattern)).join(' ');
  const inScope = template.startsWith('PT') || template.startsWith('OT');
  const content = inScope ? [
    `• CPT 97116 (Gait Training): ${gait ? `Gait training involved the following mobility performance: ${gait}` : 'Gait training was not documented as a performed intervention during this encounter.'}`,
    `• CPT 97112 (Neuromuscular Re-education): ${neuro ? `Neuromuscular treatment addressed motor control through the following activities: ${neuro}` : 'Neuromuscular re-education was not documented as a performed intervention during this encounter.'}`,
  ].join('\n') : 'Gait training (CPT 97116) and neuromuscular re-education (CPT 97112) were not recorded as services provided in this SLP/physician encounter.';
  const plan = inScope ? [
    `• CPT 97116 (Gait Training): ${plannedGait ? `Planned locomotor treatment: ${plannedGait}` : 'Additional gait training is not specified in the recorded plan.'}`,
    `• CPT 97112 (Neuromuscular Re-education): ${plannedNeuro ? `Planned motor-control treatment: ${plannedNeuro}` : 'Additional neuromuscular re-education is not specified in the recorded plan.'}`,
  ].join('\n') : 'The recorded specialty plan does not include gait training (CPT 97116) or neuromuscular re-education (CPT 97112).';
  return {
    ...note,
    objective: block(note.objective, CPT, content),
    plan: block(note.plan, CPT, plan),
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
      .replace(/change of /gi, '').replace(/improved by /gi, 'improved ')
      .replace(/approximately /gi, '~')
      .replace(/\bseconds\b/g, 'sec'));
    const size = Math.max(1, Math.ceil(statements.length / 3));
    const bullets: string[] = [];
    for (let index = 0; index < statements.length; index += size) {
      bullets.push(`• ${statements.slice(index, index + size).join(' ')}`);
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
