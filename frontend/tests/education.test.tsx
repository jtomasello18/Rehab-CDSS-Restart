import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import EducationTab from '../src/components/EducationTab';
import { patients, sources, emptyProgress, normalizeProgress, submitAnswer, resetPatient, patientStats, overallStats } from '../src/utils/educationProgress';

assert.deepEqual(patients.map(p => p.questions.length), [4, 3, 3, 3]);
const allIds = new Set();
for (const patient of patients) for (const question of patient.questions) {
  assert.equal(question.options.length, 4);
  assert.ok(question.correct >= 0 && question.correct < 4);
  assert.ok(!allIds.has(question.id)); allIds.add(question.id);
  for (const id of question.sources) {
    const source = sources[id as keyof typeof sources];
    assert.ok(source && source.appraisal && source.tier);
    assert.match(source.url, /^https:\/\/(pubmed\.ncbi\.nlm\.nih\.gov|www\.cms\.gov)\//);
    assert.ok(source.stars === null || (source.stars >= 1 && source.stars <= 5));
    if ('pmid' in source) assert.ok(source.url.includes(source.pmid));
  }
}
const ed = patients[0], elena = patients[1], q = ed.questions[0];
let progress = emptyProgress();
assert.equal(overallStats(progress).answered, 0);
assert.equal(overallStats(progress).hours, 0);
progress = submitAnswer(progress, ed, q, { option: q.correct, confidence: 'high' });
assert.equal(overallStats(progress).accuracy, 100);
assert.equal(patientStats(progress, ed).mastery, 25);
assert.equal(overallStats(progress).hours, 0.05);
const duplicate = submitAnswer(progress, ed, q, { option: 0, confidence: 'review' });
assert.strictEqual(duplicate, progress, 'A second submission must not alter the first answer');
progress = submitAnswer(progress, ed, ed.questions[1], { option: 0, confidence: null });
assert.equal(overallStats(progress).accuracy, 50);
assert.equal(patientStats(progress, ed).mastery, 25);
assert.equal(overallStats(progress).hours, 0.10);
progress = submitAnswer(progress, elena, elena.questions[0], { option: elena.questions[0].correct, confidence: 'review' });
const restored = normalizeProgress(JSON.parse(JSON.stringify(progress)));
assert.deepEqual(restored, progress);
const reset = resetPatient(progress, ed.id);
assert.equal(overallStats(reset).answered, 1);
assert.equal(overallStats(reset).hours, 0.05);
assert.equal(patientStats(reset, elena).mastery, 33);
assert.equal(patientStats(reset, ed).mastery, 0);
assert.equal(overallStats(reset).domains.find(d => d.id === 'safety')!.answered, 0);
for (const patient of patients) for (const question of patient.questions) {
  progress = submitAnswer(progress, patient, question, { option: question.correct, confidence: null });
}
assert.equal(overallStats(progress).answered, 13);
assert.equal(overallStats(progress).correct, 12); // Earlier wrong answer stays locked.
assert.equal(overallStats(progress).completed, 4);
assert.equal(overallStats(progress).hours, 1);
assert.equal(overallStats(resetPatient(progress, 'elena')).hours, 0.75);
for (const malformed of [null, [], 'bad', {version:2, answers:{}}, {version:1,answers:[]}]) {
  assert.deepEqual(normalizeProgress(malformed), emptyProgress());
}
const clean = normalizeProgress({ version: 1, hours: 999, answers: { unknown: {fake: {}}, ed: {
  fake: {option: 0}, [q.id]: {option: true}, [ed.questions[1].id]: {option: 99},
  [ed.questions[2].id]: {option: 0, confidence: '<script>'},
} } });
assert.equal(overallStats(clean).answered, 1);
assert.equal(clean.answers.ed[ed.questions[2].id].confidence, null);
for (const patient of patients) {
  const markup = renderToStaticMarkup(<EducationTab args={{education_patient: patient.id, education_progress: progress}} />);
  assert.match(markup, /ARIA Education/);
  assert.match(markup, /no accredited CEU\/CME credit/);
  assert.match(markup, new RegExp(`${patient.name} clinical quiz`));
  assert.match(markup, /Answer Recorded/);
  assert.match(markup, /Evidence Rationale/);
  assert.equal((markup.match(/name="answer-/g) ?? []).length, 4);
}
console.log('Education: 13 questions; source integrity; locked first answers; scoring, domains, hours, reset, restore and all four rendered cases passed.');
