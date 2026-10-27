import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import PatientTracker from '../src/components/ProgressNoteTab';
import { trackerMetrics, metricDelta, encounters, safetyFlags, comparisons } from '../src/data/patientTracker';

// Regressions in outcome direction must not turn a slower TUG green or round
// small gait changes away. Unknown encounters must not become interpolations.
const walk = metricDelta(trackerMetrics.pt[0]);
assert.equal(walk.tone, 'danger');
assert.match(walk.text, /-0\.13 m\/s/);
const tug = metricDelta(trackerMetrics.pt[2]);
assert.equal(tug.tone, 'danger');
assert.match(tug.text, /\+5\.2 s slower/);
assert.equal(metricDelta({ ...trackerMetrics.pt[2], current: 12 }).tone, 'success');
assert.equal(metricDelta(trackerMetrics.ot[0]).tone, 'success');
assert.match(metricDelta(trackerMetrics.slp[1]).text, /\+7\.6 pts/);
assert.equal(metricDelta(trackerMetrics.physician[1]).tone, 'success');
assert.equal(trackerMetrics.physician[1].initial, '134/82');
assert.equal(trackerMetrics.physician[2].initial, 74);
assert.ok(Object.values(trackerMetrics).flat().every(metric => metric.prior === null || metric.id === 'baclofen'));

for (const role of ['PT', 'MD', 'OT', 'SLP', 'Viewer']) {
  // Old server sessions may still supply matched PDFs. They must not restore
  // the removed CPG card for any specialty.
  const markup = renderToStaticMarkup(<PatientTracker args={{ role, trackerEvidence: {
    sources: { pt: [{ document_id: 'pdf-real', filename: 'Old Guideline.pdf', page_number: 119,
      text: 'Previously matched guideline passage.', star_rating: 4 }] },
    error: 'Old guideline retrieval status',
  } }} />);
  assert.equal((markup.match(/aria-pressed=/g) ?? []).length, 4);
  assert.equal((markup.match(/aria-pressed="true"/g) ?? []).length, 1);
  assert.equal((markup.match(/data-metric=/g) ?? []).length, 4);
  assert.match(markup, /Vance, E\. IRF Discharge \(09\/29\)/);
  assert.match(markup, /Vance, E\. Outpatient Eval \(10\/13\)/);
  const normativePanel = markup.slice(markup.indexOf('Normative Performance Panel'));
  const normativeCards = normativePanel.match(/<article\b[\s\S]*?<\/article>/g) ?? [];
  assert.equal(normativeCards.length, 3);
  for (const card of normativeCards) {
    assert.equal((card.match(/data-normative-citation/g) ?? []).length, 1);
    assert.ok(card.indexOf('</dl>') < card.indexOf('<footer'), 'Citations sit directly below the comparison rows');
    assert.match(card, /Source: /);
    assert.match(card, /text-xs text-slate-500 mt-2 leading-relaxed/);
    assert.match(card, /href="https:\/\//);
    assert.match(card, /rel="noopener noreferrer"/);
    assert.doesNotMatch(card, /<p[ >]|mt-1 block/);
    assert.match(card, /<\/footer><\/article>$/);
  }
  assert.doesNotMatch(normativePanel, /Not supplied|Not recorded|Not re-measured|missing reference values and measurements/);
  assert.match(normativePanel, /Age\/Gender Matched Reference Values \(M, 65–70\)/);
  assert.doesNotMatch(normativePanel, /IRF Discharge Baseline \(09\/29\) vs\. Outpatient Evaluation \(10\/13\)/);
  if (role === 'OT') {
    assert.match(normativePanel, /Grade 2 \(Persistent R elbow flexor tone\)/);
    assert.doesNotMatch(normativePanel, /Rigid in flexion/);
  }
  if (role === 'MD') {
    assert.match(normativePanel, /134\/82 mmHg/);
    assert.match(normativePanel, /13\.4 mL\/kg\/min/);
    assert.doesNotMatch(normativePanel, /Stable Sinus Rhythm/);
  }
  assert.doesNotMatch(markup, /Matched Evidence Bridge PDF Passages/);
  assert.doesNotMatch(markup, /ARIA Clinical Practice Guideline Alerts|Recommended Active Interventions|Discouraged \/ Low-Value Interventions/);
  assert.doesNotMatch(markup, /APTA Clinical Practice Guideline|ASHA \/ RCSLT Clinical Guidelines|Case reference|Old Guideline\.pdf|Old guideline retrieval status|Open Evidence Bridge/);
  assert.doesNotMatch(markup, /Patient-Specific Action|Missing dated measurements|Clopidogrel|Atorvastatin|Lisinopril|Grade 3|Gr 3/);
  assert.equal((markup.match(/data-safety-flag/g) ?? []).length, 2);
  assert.doesNotMatch(markup, /Current objective exam|10\/13 exam:|<strong>Gait:|Clinical timeline|Scope:|Regressing \(Last 7d\)|Tone Barrier \/ ADL \+/);
  const pulse = markup.slice(markup.indexOf('aria-labelledby="care-team-title"'), markup.indexOf('id="specialty-view"'));
  assert.equal((pulse.match(/>Regressing<\/span>/g) ?? []).length, 1);
  assert.equal((pulse.match(/>Progressing<\/span>/g) ?? []).length, 2);
  assert.match(pulse, /Medication Review Flagged/);
  assert.doesNotMatch(pulse, /BBS:|Baclofen doubled|FMA-UE:|Naming Accuracy:/);
  assert.equal((pulse.match(/bg-emerald-50/g) ?? []).length, 2);
  if (role === 'PT') {
    assert.match(markup, /Hemi-walker · Standby Assist \(SBA\) · 50 ft/);
  }
  const metricCards = markup.match(/<article[^>]*data-metric="[^"]+"[\s\S]*?<\/article>/g)!;
  assert.equal(metricCards.length, 4);
  for (const card of metricCards) {
    assert.doesNotMatch(card, /<p[ >]/);
    assert.equal((card.match(/<dt[ >]/g) ?? []).length, 3);
  }
  if (role === 'MD') {
    const table = markup.match(/<table[^>]*>[\s\S]*?<\/table>/)![0];
    assert.equal((table.match(/<tr/g) ?? []).length, 2);
    assert.match(table, /Increased to 10mg TID/);
  }
  assert.doesNotMatch(markup, /<select[^>]*disabled/);
  assert.doesNotMatch(markup, /Bayesian|Systemic Risk Profile|<svg[^>]*recharts/);
  assert.match(markup, role === 'PT' ? /data-metric="tug"/ : role === 'OT' ? /data-metric="mas"/ : role === 'SLP' ? /data-metric="wab"/ : /data-metric="baclofen"/);
}

assert.deepEqual(encounters.map(e => [e.date, e.week, e.label]), [
  ['09/29', 10, 'IRF Discharge'], ['10/06', 11, 'MD Follow-up'], ['10/13', 12, 'Outpatient Eval'],
]);
for (const flags of Object.values(safetyFlags)) {
  const medicationFlag = flags.find(flag => /PHARMACOLOGICAL/.test(flag.title))!;
  assert.match(medicationFlag.text, /may be correlated with/);
  assert.ok(flags.every(flag => flag.text.split(/(?<=[.!?])\s+/).length <= 2));
}

assert.equal(Object.values(comparisons).flat().length, 12);
for (const comparison of Object.values(comparisons).flat()) {
  assert.ok(comparison.citations.length >= 2);
  assert.ok(comparison.citationScope.length > 0);
  assert.ok(comparison.citations.every(source => source.url.startsWith('https://')));
}
assert.match(comparisons.pt[0].citations[0].label, /Table 4, p\. e550/);
assert.match(comparisons.pt[1].citations[1].label, /Table 7, p\. 192/);
assert.match(comparisons.pt[2].citations[1].label, /8\.1 sec/);
assert.match(comparisons.slp[2].citationScope, /do not define a standardized discourse-duration norm/);
console.log('Patient Tracker checks passed: clinical values, 12 linked citation footers across all specialties, and no CPG Alerts, including stale evidence payloads.');
