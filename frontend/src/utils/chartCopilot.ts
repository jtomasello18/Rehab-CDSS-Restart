import chart from '../data/chartRecord.json';

export type ChartRecord = typeof chart.records[number];
export type ChartAnswer = { answer: string; sourceIds: string[]; mode: 'local' | 'claude' };
export type ChartMessage = ChartAnswer & { id: string; role: 'user' | 'assistant' };
export type CopilotResult = ChartAnswer & { requestId: string; patientId: string };
export const chartPatientId = chart.patientId;
export const chartRecords = chart.records;
export const suggestedQueries = [
  'When did Baclofen change & how did gait respond?',
  'Timeline of 10MWT, BBS & TUG across all visits',
  'Recent labs, renal function & MRI findings?',
  'What did OT and SLP note about fatigue & R UE?',
];
export const welcomeMessage = 'Ed Vance’s supplied 12-week chart is indexed: acute admission, inpatient discharge, PT, OT, SLP, neurology, labs, and medication history. Ask a question or choose a quick query. Open a source badge to inspect the dated record.';

const concepts: Record<string, RegExp> = {
  baclofen: /\bbaclofen\b/i, medications: /\b(medications?|meds?|drugs?|prescriptions?)\b/i,
  dose: /\b(dose|dosage|titration|doubled|increase)\b/i,
  gait: /\b(gait|walking|walk|ambulat\w*|10\s*-?\s*mwt|10\s*-?meter)\b/i,
  '10mwt': /\b(10\s*-?\s*mwt|10\s*-?meter|gait speed|gait velocity)\b/i,
  bbs: /\b(bbs|berg|balance)\b/i, tug: /\b(tug|timed up|functional mobility)\b/i,
  fma: /\b(fma(?:-ue)?|fugl|motor recovery)\b/i, wab: /\b(wab(?:-r)?|aphasia quotient)\b/i,
  ot: /\b(ot|occupational)\b/i, slp: /\b(slp|speech|language)\b/i,
  pt: /\b(pt|physical therapy)\b/i, md: /\b(md|physician|neuro(?:logy|logist)?)\b/i,
  'upper extremity': /\b(r\s*ue|right arm|upper extremity|upper limb|right hand)\b/i,
  fatigue: /\b(fatigue|tired|sluggish\w*|sedation|sleepy|drows\w*)\b/i,
  falls: /\b(falls?|near-falls?|fall risk)\b/i, labs: /\b(labs?|laboratory|bloodwork|cmp|metabolic panel)\b/i,
  renal: /\b(renal|kidney|egfr|creatinine|clearance|uremi\w*)\b/i,
  ldl: /\b(ldl|cholesterol|lipids?)\b/i, hba1c: /\b(hba1c|a1c|diabetes|glucose)\b/i,
  sodium: /\b(sodium|na)\b/i, potassium: /\b(potassium|k)\b/i,
  imaging: /\b(mri|imaging|scan|brain|infarct|localization|lesion)\b/i,
  vitals: /\b(vitals?|vital signs)\b/i, bp: /\b(bp|blood pressure)\b/i,
  hr: /\b(hr|heart rate|pulse)\b/i, vo2: /\b(vo2|fitness|cardiorespiratory|aerobic)\b/i,
  allergies: /\b(allerg\w*|penicillin|latex)\b/i,
  insurance: /\b(insurance|medicare|coverage|visits? (?:used|left|remaining))\b/i,
  swallow: /\b(swallow\w*|diet|dysphagia|fois|liquids?|solids?)\b/i,
  peg: /\b(peg|9\s*-?hpt|dexterity)\b/i, box: /\b(box|blocks?)\b/i,
  afo: /\b(afo|orthos\w*|brace|foot drop|toe drag)\b/i,
  mas: /\b(mas|ashworth|spasticity|tone)\b/i,
  shoulder: /\b(shoulder|subluxation|sling|givmohr|traction)\b/i,
  feeding: /\b(feeding|utensils?|adl)\b/i, discharge: /\b(discharge|irf)\b/i,
  home: /\b(home|spouse|martha|lives?|caregiver)\b/i,
  goals: /\b(goals?|mailbox)\b/i, stroke: /\b(stroke|nihss|admission|onset)\b/i,
};
const stopWords = new Set('what when where why how did does do is are was were the a an and or of to in on at from about for with his her their all visits across recent entire record chart patient ed vance please show tell me any can you have has had find noted note notes findings'.split(' '));
const tokens = (text: string) => text.toLowerCase().match(/[a-z0-9]+/g)?.filter(t => t.length > 2 && !stopWords.has(t)) ?? [];

function requestedDates(question: string): string[] {
  const dates = [...question.matchAll(/\b(0?[1-9]|1[0-2])\/(0?[1-9]|[12]\d|3[01])(?:\/(\d{4}))?\b/g)]
    .map(match => `${match[1].padStart(2, '0')}/${match[2].padStart(2, '0')}/${match[3] ?? '2026'}`);
  for (const [month, number] of [['july', '07'], ['september', '09'], ['october', '10']]) {
    for (const match of question.toLowerCase().matchAll(new RegExp(`\\b${month}\\s+(\\d{1,2})(?:st|nd|rd|th)?\\b`, 'g'))) {
      dates.push(`${number}/${match[1].padStart(2, '0')}/2026`);
    }
  }
  for (const match of question.matchAll(/\b(\d{4})-(\d{2})-(\d{2})\b/g)) dates.push(`${match[2]}/${match[3]}/${match[1]}`);
  return [...new Set(dates)];
}

/** Offline lookup quotes recorded facts; it never invents missing encounters. */
export function answerChartQuestion(question: string, previousQuestion = ''): ChartAnswer {
  const empty = (answer: string): ChartAnswer => ({ answer, sourceIds: [], mode: 'local' });
  if (!question.trim()) return empty('Enter a question about Ed Vance’s chart.');
  if (/\bmrn\s*#?\s*(\d+)/i.test(question) && question.match(/\bmrn\s*#?\s*(\d+)/i)?.[1] !== chartPatientId) {
    return empty('This index contains Ed Vance, MRN 482910 only. No other patient record is available.');
  }
  const followUp = /\b(that|those|then|it|his dose|what about|and (?:on|at))\b/i.test(question);
  const query = followUp ? `${previousQuestion} ${question}` : question;
  const topics = Object.entries(concepts).filter(([, pattern]) => pattern.test(query)).map(([topic]) => topic);
  const words = new Set(tokens(query));
  const dates = requestedDates(question);
  const broad = /\b(summary|summarize|overview|entire record|all encounters|all medications)\b/i.test(question);
  const hits = chart.records.flatMap(record => {
    if (dates.length && (!record.date || !dates.includes(record.date))) return [];
    return record.entries.map(entry => {
      const entryWords = new Set(tokens(entry.text));
      const score = entry.topics.reduce((sum, topic) => sum + (topics.includes(topic) ? 5 : 0), 0)
        + [...words].filter(word => entryWords.has(word)).length;
      return { record, entry, score: score || (broad || (dates.length && !topics.length) ? 1 : 0) };
    });
  }).filter(hit => hit.score > 0).sort((a, b) => b.score - a.score);
  if (!hits.length) return empty('That detail is not documented in the indexed record. Try a visit date, medication, lab, imaging finding, or therapy measure.');
  // Reserve one result per relevant source before filling remaining places.
  const selected = hits.filter((hit, index) => hits.findIndex(other => other.record.id === hit.record.id) === index).slice(0, 8);
  for (const hit of hits) if (selected.length < 12 && !selected.includes(hit)) selected.push(hit);
  selected.sort((a, b) => chart.records.indexOf(a.record) - chart.records.indexOf(b.record));
  const lines = selected.map(({ record, entry }) => `${record.date ?? 'Undated chart profile'} · ${entry.text}`);
  if (topics.includes('baclofen') && topics.some(topic => ['gait', 'fatigue', 'falls', 'bbs'].includes(topic))) {
    lines.push('The sequence shows a temporal association; it does not establish baclofen as the cause of decline.');
  }
  const conflicts = chart.reconciliation.filter(item => item.topics.some(topic => topics.includes(topic)));
  lines.push(...conflicts.map(item => `Chart reconciliation: ${item.text}`));
  return { answer: lines.join('\n\n'), sourceIds: [...new Set(selected.map(hit => hit.record.id))], mode: 'local' };
}

export function applyCopilotResult(messages: ChartMessage[], result: CopilotResult): ChartMessage[] {
  if (result.patientId !== chartPatientId || !result.answer.trim()
    || !result.sourceIds.every(id => chart.records.some(record => record.id === id))) return messages;
  return messages.map(message => message.id === `${result.requestId}:answer`
    ? { ...message, answer: result.answer, sourceIds: result.sourceIds, mode: result.mode } : message);
}
