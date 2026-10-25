import assert from 'node:assert/strict';
import { expandClinicalAbbreviations, expandClinicalShorthand } from '../src/utils/clinicalSoap';
import { addSkilledJustification, alignCpt, applyLocalInstruction, condenseSoap } from '../src/utils/soapRefinements';
const source = `s: pt reports 2 near-falls catching R toe on rug; drowsy after 10/06 Baclofen increase to 10mg TID; goal mailbox.
o: amb 50ft w/ hemi-walker & SBA; 10mwt 0.35 m/s from 0.48 m/s at IRF discharge; bbs 38/56 from 42/56; tug 21.4s; R ankle MAS Gr 1+; R LE Brunnstrom Stg 4.
a: 67M 12wk s/p L MCA stroke; mobility regression temporally associated with dose escalation; high fall risk.
p: initiate PT 2x/wk x6wk; MD medication review; R AFO eval.`;
const soap = expandClinicalShorthand(source);
assert.deepEqual(Object.keys(soap), ['subjective', 'objective', 'assessment', 'plan']);
assert.match(soap.subjective, /2 near-falls/);
assert.match(soap.subjective, /10 mg three times daily \(TID\)/);
assert.match(soap.objective, /Gait & Assistive Device: Ambulated 50 feet with hemi-walker and standby assistance/);
assert.match(soap.objective, /10-Meter Walk Test \(10MWT\): 0.35 m\/s from 0.48 m\/s/);
assert.match(soap.objective, /Berg Balance Scale \(BBS\): 38\/56 from 42\/56/);
assert.match(soap.objective, /Timed Up and Go \(TUG\): 21.4 seconds/);
assert.match(soap.objective, /Modified Ashworth Scale \(MAS\) Grade 1\+/);
assert.match(soap.assessment, /67-year-old male 12 weeks following left middle cerebral artery/);
assert.match(soap.plan, /physical therapy 2 visits per week for 6 weeks/);
assert.match(soap.plan, /Physician medication review/);
assert.match(soap.plan, /ankle-foot orthosis \(AFO\) evaluation/);
assert.doesNotMatch(soap.subjective, /21.4|38\/56/);
assert.doesNotMatch(soap.plan, /10MWT|67-year-old/);
const custom = expandClinicalShorthand('S: denies shoulder pain O: R UE ROM 90 degrees A: limited overhead function P: OT follow-up', 'OT Functional SOAP');
assert.match(custom.objective, /right upper extremity range of motion 90 degrees/i);
assert.match(custom.plan, /occupational therapy follow-up/i);
assert.doesNotMatch(JSON.stringify(custom), /Baclofen|0\.35|38\/56|67-year-old|2 visits|6 weeks|stroke/i);
const simple = expandClinicalShorthand('Walked 25ft w/ SBA. Request AFO eval.');
assert.match(simple.objective, /25 feet with standby assistance/);
assert.match(simple.plan, /Request ankle-foot orthosis/);
assert.match(simple.subjective, /Not documented/);
assert.doesNotMatch(JSON.stringify(simple), /0\.35|Baclofen|mailbox|50 feet|38\/56|2 visits/);
const slp = expandClinicalShorthand('s: tired o: WAB-R 71.8/100 p: SLP 1x/wk', 'SLP Cognitive-Linguistic SOAP');
assert.match(slp.objective, /Western Aphasia Battery-Revised \(WAB-R\): 71.8\/100/);
assert.match(slp.assessment, /speech-language pathology assessment/);
assert.match(expandClinicalAbbreviations('wk 12; BP 130 over 80; R LE; TID'), /week 12; BP 130\/80; right lower extremity; three times daily/);
console.log('Local SOAP checks passed: section parsing, abbreviation expansion, clinical values and no invented case facts.');

const grammar = expandClinicalShorthand('s: pt feels tired; denies pain; reports two near-falls. o: BBS 38/56. p: reassess');
assert.match(grammar.subjective, /^Patient feels tired\. They deny pain\. They report two near-falls\./);
assert.doesNotMatch(grammar.subjective, /reports feels|reports denies|denie\b|physical therapy feels/);
const expanded = expandClinicalAbbreviations('BBS 38/56; WAB-R 71.8; AFO; 10mg TID');
assert.equal(expandClinicalAbbreviations(expanded), expanded, 'Repeated formatting must not expand an acronym inside its own label');

const fixtures = [
  { label: 'PT Skilled SOAP', soap },
  { label: 'OT Functional SOAP', soap: custom },
  { label: 'SLP Cognitive-Linguistic SOAP', soap: slp },
  { label: 'MD Neuro Follow-up', soap: expandClinicalShorthand('S: Fatigue on medication O: BP 122/78; normal strength A: Medication tolerance concern P: Review medications', 'MD Neuro Follow-up') },
];
for (const template of fixtures) {
  const audit = addSkilledJustification(template.soap, template.label);
  assert.match(audit.assessment, /\[MEDICARE PART B SKILLED NECESSITY\]/);
  assert.equal(audit.plan, template.soap.plan, 'Justification updates Assessment, without adding documentation rules to Plan');
  assert.match(audit.assessment, /Skilled Justification \(Medicare Part B\):/);
  assert.doesNotMatch(JSON.stringify(audit), /The treating clinician must|do not infer|Confirm the plan|Relate the documented plan|record skilled decisions/i);
  assert.deepEqual(addSkilledJustification(audit, template.label), audit, 'Repeated click updates the section, without duplicates');
  const cpt = alignCpt(audit, template.label);
  assert.doesNotMatch(JSON.stringify(cpt), /\[CPT BILLING CODE ALIGNMENT\]/);
  assert.deepEqual(alignCpt(cpt, template.label), cpt);
  assert.doesNotMatch(JSON.stringify(cpt), /30 MIN SKILLED SESSION|15 min, 1 Unit|50 ft x 2|Codes .*Verified/);
  assert.match(cpt.assessment, /MEDICARE PART B SKILLED NECESSITY/, 'CPT update retains the other action');
  const condensed = condenseSoap(template.soap);
  for (const section of Object.keys(condensed) as (keyof typeof condensed)[]) {
    const bullets = condensed[section].split('\n');
    assert.ok(bullets.length <= 3);
    assert.ok(bullets.every(bullet => bullet.startsWith('• ')));
    const sourceWithoutListNumbers = template.soap[section].replace(/^\d+\.\s/gm, '');
    for (const number of sourceWithoutListNumbers.match(/\d+(?:\.\d+)?/g) ?? []) assert.ok(condensed[section].includes(number), `Preserve measured value ${number}`);
  }
}
const pt = soap;
assert.doesNotMatch(alignCpt(pt, 'PT Skilled SOAP').objective, /97112/);
assert.deepEqual(alignCpt(slp, 'SLP Cognitive-Linguistic SOAP'), slp);
assert.match(applyLocalInstruction(pt, 'Replace "mailbox" with "front door"', 'PT Skilled SOAP')!.subjective, /front door/);
assert.doesNotMatch(applyLocalInstruction(pt, 'Replace "mailbox" with "front door"', 'PT Skilled SOAP')!.subjective, /mailbox/);
assert.equal(applyLocalInstruction(pt, 'Emphasize the medication correlation for the attending', 'PT Skilled SOAP'), null, 'Open-ended edits require Claude, not literal request insertion');
const customAudit = addSkilledJustification(custom, 'OT Functional SOAP');
assert.doesNotMatch(JSON.stringify(customAudit), /Baclofen|38\/56|67-year-old|near-falls|mailbox/);
console.log('Specialty and refinement checks passed: grammar, repeatable blocks, coding fidelity, concise bullets and custom commands.');

const freeText = expandClinicalShorthand('walked 50ft hemiwalker, 2 near falls, bbs 38/56, 10mwt 0.35, baclofen 10mg tid making him tired, plan gait training 2x/wk and afo');
assert.match(freeText.subjective, /2 near falls/);
assert.match(freeText.subjective, /baclofen 10 mg three times daily \(TID\) making him tired/i);
assert.match(freeText.objective, /Walked 50 feet hemi-walker/);
assert.match(freeText.objective, /Berg Balance Scale \(BBS\): 38\/56/);
assert.match(freeText.objective, /10-Meter Walk Test \(10MWT\): 0.35/);
assert.match(freeText.assessment, /walking safety concern/);
assert.match(freeText.plan, /Gait training 2 visits per week and ankle-foot orthosis/);
assert.doesNotMatch(freeText.subjective, /38\/56|0\.35|50 feet/);
assert.doesNotMatch(freeText.plan, /10 mg|38\/56/);
assert.doesNotMatch(JSON.stringify(freeText), /67-year-old|mailbox|10\/06|42\/56|taper/i);
assert.doesNotMatch(expandClinicalShorthand('walked 90ft, denies near falls').assessment, /walking safety concern/);
assert.doesNotMatch(expandClinicalShorthand('walked 90ft, 0 near falls').assessment, /walking safety concern/);
assert.deepEqual(expandClinicalShorthand(''), { subjective: '', objective: '', assessment: '', plan: '' });

const abbreviations = expandClinicalAbbreviations('pt feels tired; wk 2; sba; min a; mod a; max a; bbs; 10mwt; tug; mas; r ue; l le; r/l; ue/le; bid; tid; afo; rom; mmt; wfl; wnl');
for (const expected of ['patient feels tired','week 2','standby assistance','minimal assistance','moderate assistance','maximal assistance','Berg Balance Scale','10-Meter Walk Test','Timed Up and Go','Modified Ashworth Scale','right upper extremity','left lower extremity','right/left','upper/lower extremities','twice daily','three times daily','ankle-foot orthosis','range of motion','manual muscle testing','within functional limits','within normal limits']) assert.ok(abbreviations.includes(expected), expected);
const mixed = expandClinicalShorthand('Patient reports shoulder pain.\n• R UE ROM 80 degrees; MMT 3/5\n• Improving overhead function\n• Continue OT 1x/wk and home exercises', 'OT Functional SOAP');
assert.match(mixed.subjective, /shoulder pain/);
assert.match(mixed.objective, /manual muscle testing 3\/5/i);
assert.match(mixed.assessment, /Improving overhead function/);
assert.match(mixed.plan, /Continue occupational therapy 1 visits per week/);

const treatment = expandClinicalShorthand('S: Trouble walking O: Walked 80ft w/ CGA; dynamic weight-shifts with tactile cueing for postural control A: Impaired balance P: Continue overground gait training and balance training twice weekly');
const codedTreatment = alignCpt(treatment, 'PT Skilled SOAP');
assert.match(codedTreatment.objective, /- 97112:.*weight-shifts/);
assert.doesNotMatch(codedTreatment.objective, /97116/, 'Walking observation alone is not a skilled intervention');
assert.equal((codedTreatment.plan.match(/twice weekly/g) ?? []).length, 1);
assert.doesNotMatch(JSON.stringify(codedTreatment), /Verify|Use only|before assigning|Documented activity for clinician coding review|Do not infer|Time and units:/);
const unrelated = expandClinicalShorthand('S: No pain O: ROM WNL; independent mobility A: No functional deficits P: Discharge');
assert.doesNotMatch(addSkilledJustification(unrelated, 'PT Skilled SOAP').assessment, /services are medically necessary/);
console.log('Organic input checks passed: mixed free-text, labeled notes, all requested abbreviations, source fidelity and clinical refinement prose.');

const timed = { subjective: 'Walking is difficult.', assessment: 'Gait and balance deficits.',
  objective: 'Gait training for 15 min: overground stepping with stance cueing.\nBalance training for 10 minutes: dynamic weight-shifts.\nBBS 38/56.',
  plan: 'Progress gait velocity to >0.40 m/s, 2x/wk for 6 wks.\nImprove BBS to >45/56, 2x/wk for 6 wks.\nReview orthotic fit.' };
const aligned = alignCpt(timed, 'PT Skilled SOAP');
assert.match(aligned.objective, /- 97116 \(15 min\): Gait training overground stepping/);
assert.match(aligned.objective, /- 97112 \(10 min\): Balance training dynamic weight-shifts/);
assert.match(aligned.objective, /BBS 38\/56/);
assert.match(aligned.plan, /- 97116: Progress gait velocity to >0\.40 m\/s/);
assert.match(aligned.plan, /- 97112: Improve BBS to >45\/56/);
assert.equal((aligned.plan.match(/2x\/wk for 6 wks/g) ?? []).length, 1);
assert.match(aligned.plan, /Review orthotic fit/);
assert.deepEqual(alignCpt(aligned, 'PT Skilled SOAP'), aligned, 'Coded bullets remain repeatable without hidden markers');
const untimed = alignCpt({ ...timed, objective: 'Gait training with verbal cueing.\nBalance training with guarding.\nTotal session: 30 min.', plan: 'Progress gait training.\nContinue balance training.' }, 'PT Skilled SOAP');
assert.match(untimed.objective, /- 97116: Gait training/);
assert.doesNotMatch(untimed.objective, /971(?:16|12) \(/, 'Total time must not be allocated to individual codes');
assert.doesNotMatch(untimed.plan, /0\.40|45\/56|2x/, 'No default goals or schedule');
const combinedTime = alignCpt({ ...timed, objective: 'Gait training and home exercises, total session 30 min.\nBalance training for 10–15 min.' }, 'PT Skilled SOAP');
assert.doesNotMatch(combinedTime.objective, /971(?:16|12) \(/, 'Combined or range durations must not become a single-code exact time');
assert.match(combinedTime.objective, /10–15 min/);
const denied = alignCpt({ ...timed, objective: 'Gait training not performed.\nBalance training not performed.' }, 'PT Skilled SOAP');
assert.doesNotMatch(denied.objective, /97116|97112/);
console.log('CPT checks passed: no meta-headers, attributed minutes, distinct goals, single schedule and no fabricated services.');
