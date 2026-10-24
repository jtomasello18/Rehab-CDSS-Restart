import assert from 'node:assert/strict';
import { expandClinicalAbbreviations, expandClinicalShorthand } from '../src/utils/clinicalSoap';
import { scribeTemplates } from '../src/data/scribeTemplates';
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

assert.equal(scribeTemplates.length, 4);
for (const template of scribeTemplates) {
  assert.deepEqual(Object.keys(template.soap), ['subjective', 'objective', 'assessment', 'plan']);
  const audit = addSkilledJustification(template.soap, template.label);
  assert.match(audit.assessment, /\[MEDICARE PART B SKILLED NECESSITY\]/);
  assert.match(audit.plan, /\[MEDICARE PART B SKILLED NECESSITY\]/);
  assert.deepEqual(addSkilledJustification(audit, template.label), audit, 'Repeated click updates the section, without duplicates');
  const cpt = alignCpt(audit, template.label);
  assert.match(cpt.objective, /\[CPT BILLING CODE ALIGNMENT\]/);
  assert.match(cpt.plan, /\[CPT BILLING CODE ALIGNMENT\]/);
  assert.deepEqual(alignCpt(cpt, template.label), cpt);
  assert.doesNotMatch(JSON.stringify(cpt), /30 MIN SKILLED SESSION|15 min, 1 Unit|50 ft x 2|Codes .*Verified/);
  assert.match(cpt.assessment, /MEDICARE PART B SKILLED NECESSITY/, 'CPT update retains the other action');
  const condensed = condenseSoap(template.soap);
  for (const section of Object.keys(condensed) as (keyof typeof condensed)[]) {
    const bullets = condensed[section].split('\n');
    assert.ok(bullets.length <= 3);
    assert.ok(bullets.every(bullet => bullet.startsWith(`• ${section[0].toUpperCase()}: `)));
    const sourceWithoutListNumbers = template.soap[section].replace(/^\d+\.\s/gm, '');
    for (const number of sourceWithoutListNumbers.match(/\d+(?:\.\d+)?/g) ?? []) assert.ok(condensed[section].includes(number), `Preserve measured value ${number}`);
  }
}
const pt = scribeTemplates[0].soap;
assert.match(alignCpt(pt, 'PT Skilled SOAP').objective, /No performed neuromuscular re-education activity/);
assert.match(alignCpt(scribeTemplates[2].soap, scribeTemplates[2].label).objective, /not assigned to this SLP\/physician note/);
assert.match(applyLocalInstruction(pt, 'Replace "mailbox" with "front door"', 'PT Skilled SOAP')!.subjective, /front door/);
assert.doesNotMatch(applyLocalInstruction(pt, 'Replace "mailbox" with "front door"', 'PT Skilled SOAP')!.subjective, /mailbox/);
assert.equal(applyLocalInstruction(pt, 'Emphasize the medication correlation for the attending', 'PT Skilled SOAP'), null, 'Open-ended edits require Claude, not literal request insertion');
const customAudit = addSkilledJustification(custom, 'OT Functional SOAP');
assert.doesNotMatch(JSON.stringify(customAudit), /Baclofen|38\/56|67-year-old|near-falls|mailbox/);
console.log('Specialty and refinement checks passed: grammar, repeatable blocks, coding fidelity, concise bullets and custom commands.');
