/** Source-only local SOAP formatting for disconnected or slow model responses. */
import { applyClinicalCorrections } from './clinicalCorrections';

export type SoapNote = { subjective: string; objective: string; assessment: string; plan: string };
type Section = keyof SoapNote;
const sections: Section[] = ['subjective', 'objective', 'assessment', 'plan'];
const sectionNames: Record<string, Section> = {
  s: 'subjective', subjective: 'subjective', o: 'objective', objective: 'objective',
  a: 'assessment', assessment: 'assessment', p: 'plan', plan: 'plan',
};

export function expandClinicalAbbreviations(text: string): string {
  let value = applyClinicalCorrections(text)
    .replace(/\bpt(?=\s+(?:reports|states|denies|is|presents|wants|goals?))/gi, 'patient')
    .replace(/\bw\/o\s*/gi, 'without ').replace(/\bw\/\s*/gi, 'with ')
    .replace(/\bs\/p\s*/gi, 'following ').replace(/\bc\/o\s*/gi, 'reports ')
    .replace(/\bd\/t\s*/gi, 'associated with ')
    .replace(/\b(\d+)\s*x\s*\/\s*wk\b/gi, '$1 visits per week')
    .replace(/\b(?:x|for)\s*(\d+)\s*wks?\b/gi, 'for $1 weeks')
    .replace(/\b(\d+)\s*wks?\b/gi, (_, count) => `${count} ${count === '1' ? 'week' : 'weeks'}`)
    .replace(/\b(\d+)\s*(?:yo|y\/o)\s*(?:male|m)\b/gi, '$1-year-old male')
    .replace(/\b(\d+)\s*(?:yo|y\/o)\s*(?:female|f)\b/gi, '$1-year-old female')
    .replace(/\b(\d{2,3})M\b/g, '$1-year-old male')
    .replace(/\b(\d{2,3})F\b/g, '$1-year-old female')
    .replace(/\b(?:L|left)\s+MCA\b/gi, 'left middle cerebral artery (MCA)');
  const expansions: [RegExp, string][] = [
    [/\b10[ -]?MWT\b/gi, '10-Meter Walk Test (10MWT)'],
    [/\bBBS\b/gi, 'Berg Balance Scale (BBS)'],
    [/\bTUG\b/gi, 'Timed Up and Go (TUG)'],
    [/\bFMA(?:[ -]?UE)?\b/gi, 'Fugl-Meyer Upper Extremity (FMA-UE)'],
    [/\bWAB(?:[ -]?R)?\b/gi, 'Western Aphasia Battery-Revised (WAB-R)'],
    [/\bSBA\b/gi, 'standby assistance (SBA)'],
    [/\bCGA\b/gi, 'contact guard assistance (CGA)'],
    [/\bmin\s*A\b/gi, 'minimal assistance'], [/\bmod\s*A\b/gi, 'moderate assistance'],
    [/\bmax\s*A\b/gi, 'maximal assistance'],
    [/\bMAS\b/gi, 'Modified Ashworth Scale (MAS)'],
    [/\bAFO\b/gi, 'ankle-foot orthosis (AFO)'],
    [/\bTID\b/gi, 'three times daily (TID)'],
    [/\bR\s*LE\b/gi, 'right lower extremity'], [/\bL\s*LE\b/gi, 'left lower extremity'],
    [/\bR\s*UE\b/gi, 'right upper extremity'], [/\bL\s*UE\b/gi, 'left upper extremity'],
    [/\bR\s+(?=toe|foot|ankle|elbow|heel|hip|shoulder|calf|knee|hand|arm|leg|flexor)/gi, 'right '],
    [/\bL\s+(?=toe|foot|ankle|elbow|heel|hip|shoulder|calf|knee|hand|arm|leg|flexor)/gi, 'left '],
    [/\bPT\b/gi, 'physical therapy'], [/\bOT\b/gi, 'occupational therapy'],
    [/\bSLP\b/gi, 'speech-language pathology'], [/\bMD\b/gi, 'physician'],
    [/\bIRF\b/gi, 'inpatient rehabilitation'], [/\bGr\s*(?=\d)/gi, 'Grade '],
    [/\bamb\b/gi, 'ambulated'], [/\bDF\b/g, 'dorsiflexion'],
    [/\bHEP\b/gi, 'home exercise program'], [/\bROM\b/g, 'range of motion'],
    [/\btx\b/gi, 'treatment'], [/\beval\b/gi, 'evaluation'],
    [/\bStg\b/gi, 'Stage'],
    [/\bf\/u\b/gi, 'follow-up'], [/\bfxn\b/gi, 'function'],
  ];
  for (const [pattern, replacement] of expansions) value = value.replace(pattern, replacement);
  value = value.replace(/(\d)\s*(mg|ft|lbs|sec|mins?)\b/gi, '$1 $2')
    .replace(/\bft\b/gi, 'feet').replace(/\bsec\b/gi, 'seconds')
    .replace(/\bmins?\b/gi, 'minutes').replace(/(\d)\s*s\b/g, '$1 seconds')
    .replace(/\b(\d+)\s*wk\b/gi, '$1 weeks')
    .replace(/\bwks?\s+(?=\d)/gi, 'week ')
    .replace(/\b(?:wk|wks)\b/gi, 'weeks')
    .replace(/\s*&\s*/g, ' and ')
    .replace(/\b((?:10MWT|BBS|TUG|FMA-UE|WAB-R)\))\s*(?=\d)/g, '$1: ')
    .replace(/[ \t]+/g, ' ').trim();
  return value;
}

function sentences(text: string): string[] {
  return text.split(/\n+|;\s*|(?<=[.!?])\s+(?=[A-Za-z])/)
    .map(line => line.replace(/^\s*(?:[•*-]|\d+[.)])\s*/, '').trim()).filter(Boolean);
}
function finishSentence(text: string): string {
  const expanded = text.replace(/[;,:]+$/, '').trim();
  if (!expanded) return '';
  const capitalized = expanded.charAt(0).toUpperCase() + expanded.slice(1);
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`;
}
function polished(text: string): string { return finishSentence(expandClinicalAbbreviations(text)); }
function objectiveLine(text: string): string {
  let value = polished(text);
  if (/^(?:Ambulated|Walked|Gait\b)/i.test(value)) value = `Gait & Assistive Device: ${value}`;
  else if (/\b(?:Modified Ashworth|Brunnstrom)\b/i.test(value) && !/^Tone/i.test(value)) value = `Tone & Motor Staging: ${value}`;
  return `• ${value}`;
}
function subjectiveLine(text: string): string {
  const expanded = expandClinicalAbbreviations(text);
  if (/^(?:patient|the patient)\b/i.test(expanded)) return finishSentence(expanded);
  if (/^goals?\b/i.test(expanded)) return finishSentence(`Patient-stated goal: ${expanded.replace(/^goals?\s*:?\s*/i, '')}`);
  if (/^(?:reports|states|denies)\b/i.test(expanded)) return finishSentence(`The patient ${expanded}`);
  return finishSentence(`The patient reports ${expanded}`);
}

/** Never backfill a vignette's demographics, scores, dose changes or care plan. */
export function expandClinicalShorthand(transcript: string, template = 'PT Skilled SOAP'): SoapNote {
  const source = applyClinicalCorrections(transcript).trim();
  const groups: Record<Section, string[]> = { subjective: [], objective: [], assessment: [], plan: [] };
  const markers = [...source.matchAll(/(?:^|\s)(subjective|objective|assessment|plan|s|o|a|p)\s*:\s*/gi)];
  if (markers.length) {
    const prefix = source.slice(0, markers[0].index).trim();
    if (prefix) groups.objective.push(prefix);
    markers.forEach((marker, index) => {
      const start = marker.index! + marker[0].length;
      const end = markers[index + 1]?.index ?? source.length;
      groups[sectionNames[marker[1].toLowerCase()]].push(...sentences(source.slice(start, end)));
    });
  } else {
    for (const line of sentences(source)) {
      const section: Section = /\b(?:plan|request|refer|initiate|continue|next visit|will|recommend|\d+x\/wk)\b/i.test(line) ? 'plan'
        : /\b(?:reports?|states?|denies|c\/o|near[- ]falls?|drowsy|drowsiness|sluggish|goals?|wants)\b/i.test(line) ? 'subjective'
        : /\b(?:assessment|impression|consistent with)\b/i.test(line) ? 'assessment' : 'objective';
      groups[section].push(line);
    }
  }
  const discipline = template.startsWith('OT') ? 'occupational therapy' : template.startsWith('SLP') ? 'speech-language pathology'
    : template.startsWith('MD') ? 'medical' : 'physical therapy';
  const result = Object.fromEntries(sections.map(section => [section,
    groups[section].length ? section === 'objective' ? groups[section].map(objectiveLine).join('\n')
      : section === 'plan' ? groups[section].map((line, index) => `${index + 1}. ${polished(line)}`).join('\n')
        : groups[section].map(section === 'subjective' ? subjectiveLine : polished).join(' ')
      : section === 'assessment' ? `A clinician must complete the ${discipline} assessment from the documented findings; no additional clinical conclusions were inferred.`
        : `Not documented in the source transcript; clinician completion required.`,
  ])) as SoapNote;
  return result;
}
