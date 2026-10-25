import React, { useRef, useState } from 'react';
import { Streamlit } from 'streamlit-component-lib';
import { ArrowLeft, ArrowRight, BookOpen, Check, ChevronDown, ExternalLink, RotateCcw, ShieldCheck, Target, X } from 'lucide-react';
import ariaLogo from '../assets/aria-logo.svg';
import { patients, sources, normalizeProgress, overallStats, patientStats, submitAnswer, resetPatient } from '../utils/educationProgress';
import type { Answer, Confidence, Patient, Progress, Question } from '../utils/educationProgress';
import '../styles/Education.css';

const filters = [
  { id: 'all', label: 'All Case Questions' },
  { id: 'clinical', label: 'Clinical Reasoning & Safety' },
  { id: 'evidence', label: 'Evidence & CPG Appraisal' },
  { id: 'billing', label: 'Medicare Part B & Billing' },
];
type Args = { education_progress?: unknown; education_patient?: string };

function Meter({ value, label }: { value: number; label: string }) {
  return <div className="edu-meter" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}>
    <span style={{ width: `${value}%` }} />
  </div>;
}

function EvidenceSource({ id }: { id: string }) {
  const source = sources[id as keyof typeof sources];
  if (!source) return null;
  return <a className="edu-source" href={source.url} target="_blank" rel="noopener noreferrer">
    <div className="edu-source-meta">
      {'pmid' in source ? <strong>PMID: {source.pmid}</strong> : <strong>CMS policy</strong>}
      {source.stars !== null && <span aria-label={`${source.stars} of 5 ARIA design stars`}>
        <span className="edu-stars">{'★'.repeat(source.stars)}</span><span className="edu-empty-stars">{'☆'.repeat(5 - source.stars)}</span> <b>{source.stars}/5</b>
      </span>}
      <span className="edu-tier">{source.tier}</span><ExternalLink size={14} aria-hidden="true" />
    </div>
    <span className="edu-source-title">{source.title}</span>
    <span className="edu-source-appraisal">{source.appraisal}</span>
  </a>;
}

function QuestionCard({ patient, question, answer, onSubmit }: {
  patient: Patient; question: Question; answer?: Answer; onSubmit: (answer: Answer) => void;
}) {
  const [choice, setChoice] = useState<number | null>(answer?.option ?? null);
  const [confidence, setConfidence] = useState<Confidence>(answer?.confidence ?? null);
  const selected = answer?.option ?? choice;
  const isCorrect = answer?.option === question.correct;
  return <>
    <div className="edu-question-heading"><span className="edu-eyebrow">{patient.name} · Case-based reasoning</span>
      <h3 id="edu-question-title">{question.title}</h3><p>{question.stem}</p>
    </div>
    <fieldset className="edu-options" aria-labelledby="edu-question-title" disabled={Boolean(answer)}>
      <legend className="edu-sr-only">Choose one answer</legend>
      {question.options.map((option, index) => {
        const correct = Boolean(answer) && index === question.correct;
        const wrong = Boolean(answer) && index === answer?.option && !correct;
        return <label key={option} className={`edu-option ${selected === index ? 'is-selected' : ''} ${correct ? 'is-correct' : ''} ${wrong ? 'is-wrong' : ''}`}>
          <input type="radio" name={`answer-${question.id}`} value={index} checked={selected === index} onChange={() => setChoice(index)} />
          <span className="edu-option-letter" aria-hidden="true">{String.fromCharCode(65 + index)}</span>
          <span>{option}{correct && <small>Correct answer</small>}{wrong && <small>Your answer</small>}</span>
          {correct && <Check size={19} aria-hidden="true" />}{wrong && <X size={19} aria-hidden="true" />}
        </label>;
      })}
    </fieldset>
    <div className="edu-submit-row">
      <div className="edu-confidence"><span>Confidence <small>(optional)</small></span>
        <div role="group" aria-label="Answer confidence">
          {([{ value: 'high', label: 'High Confidence' }, { value: 'review', label: 'Needs Review' }] as const).map(item =>
            <button key={item.value} type="button" disabled={Boolean(answer)} aria-pressed={(answer?.confidence ?? confidence) === item.value}
              onClick={() => setConfidence(confidence === item.value ? null : item.value)}>{item.label}</button>
          )}
        </div>
      </div>
      <button type="button" className="edu-primary" disabled={choice === null || Boolean(answer)} onClick={() => {
        if (choice !== null && !answer) onSubmit({ option: choice, confidence });
      }}>{answer ? 'Answer Recorded' : 'Submit Answer'}<ArrowRight size={16} aria-hidden="true" /></button>
    </div>
    <div aria-live="polite" aria-atomic="true">
      {answer && <section className="edu-feedback">
        <div className={`edu-verdict ${isCorrect ? 'correct' : 'incorrect'}`}>
          {isCorrect ? <Check size={19} /> : <X size={19} />}<strong>{isCorrect ? 'Correct' : 'Incorrect'} · Answer {String.fromCharCode(65 + question.correct)}</strong>
          {answer.confidence && <span>{answer.confidence === 'high' ? 'High confidence' : 'Marked for review'}</span>}
        </div>
        <div className="edu-rationale"><h4><BookOpen size={18} aria-hidden="true" />Why This Matters & Evidence Rationale</h4>
          <p>{question.rationale}</p>
          <div className="edu-sources">{question.sources.map(id => <EvidenceSource key={id} id={id} />)}</div>
          <details className="edu-appraisal-legend"><summary>How ARIA appraises evidence</summary>
            <p>5★ guideline/systematic review · 4★ larger randomized trial · 3★ smaller trial/cohort · 2★ observational study · 1★ expert opinion. These design-based ratings are not a formal GRADE assessment; they do not establish the certainty or applicability of every recommendation. Policy references are unscored.</p>
          </details>
        </div>
      </section>}
    </div>
  </>;
}

export default function EducationTab({ args = {} }: { args?: Args }) {
  // Streamlit restores these props after navigating away and returning. During a
  // mounted session local updates remain immediate while the host acknowledges them.
  const [progress, setProgress] = useState(() => normalizeProgress(args.education_progress));
  const progressRef = useRef(progress);
  const [patientId, setPatientId] = useState(() => patients.some(p => p.id === args.education_patient) ? args.education_patient! : 'ed');
  const [filter, setFilter] = useState('all');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [notice, setNotice] = useState('');
  const [syncError, setSyncError] = useState(false);
  const patient = patients.find(p => p.id === patientId)!;
  const questions = patient.questions.filter(q => filter === 'all' || q.focus === filter);
  const question = questions[questionIndex];
  const overall = overallStats(progress);
  const mastery = patientStats(progress, patient);

  function persist(next: Progress, selectedPatient = patientId) {
    progressRef.current = next;
    setProgress(next);
    try {
      Streamlit.setComponentValue({ type: 'education_progress', requestId: crypto.randomUUID(),
        progress: next, patientId: selectedPatient });
      setSyncError(false);
    } catch { setSyncError(true); }
  }
  function selectPatient(id: string) {
    setPatientId(id); setQuestionIndex(0); setFilter('all'); setNotice('');
    persist(progressRef.current, id);
  }
  function answerQuestion(answer: Answer) {
    if (!question) return;
    const next = submitAnswer(progressRef.current, patient, question, answer);
    if (next !== progressRef.current) persist(next);
    setNotice('');
  }

  return <main className="aria-education">
    <header className="edu-header">
      <img src={ariaLogo} alt="ARIA" className="edu-logo" />
      <div><span className="edu-eyebrow">Learn from the clinical encounter</span>
        <h1>ARIA Education <span>· Point-of-Care Clinical Mastery & CEU/CME</span></h1>
      </div>
    </header>
    <section className="edu-dashboard" aria-label="Provider performance dashboard">
      <article className="edu-stat"><span className="edu-stat-label">Overall Provider Accuracy</span>
        <strong className="edu-stat-value" data-testid="overall-accuracy">{overall.accuracy}<small>%</small></strong>
        <span>{overall.correct}/{overall.answered} correct <span className="edu-muted">· First answers</span></span>
        <Meter value={overall.accuracy} label="Overall accuracy" /><small className="edu-muted">{overall.answered ? 'Each answer counts once.' : 'Answer a question to begin.'}</small>
      </article>
      <article className="edu-stat"><span className="edu-stat-label">Selected Patient Mastery</span>
        <strong className="edu-stat-value" data-testid="patient-mastery">{mastery.mastery}<small>%</small></strong>
        <span>{patient.name} <span className="edu-muted">· {mastery.correct}/{mastery.total} correct</span></span>
        <Meter value={mastery.mastery} label={`${patient.name} mastery`} /><small className="edu-muted">{mastery.answered}/{mastery.total} questions answered</small>
      </article>
      <article className="edu-stat edu-credit-stat"><span className="edu-stat-label">Point-of-Care Credits</span>
        <strong className="edu-stat-value" data-testid="learning-hours">{overall.hours.toFixed(2)}<small> / 24.0</small></strong>
        <span>CEU / CME Hours</span><span className="edu-credit-badge">0.25 hours per completed case</span>
      </article>
      <article className="edu-stat edu-domain-stat"><span className="edu-stat-label">Competency Domain Breakdown</span>
        {overall.domains.map(domain => <div className="edu-domain" key={domain.id}>
          <div><span>{domain.label}</span><b title={`${domain.correct}/${domain.answered} correct`}>{domain.answered ? `${domain.accuracy}%` : '—'}</b></div>
          <Meter value={domain.accuracy} label={domain.label} />
        </div>)}
      </article>
    </section>
    <div className="edu-workspace">
      <aside className="edu-roster" aria-label="Provider patient roster">
        <div className="edu-roster-heading"><BookOpen size={19} aria-hidden="true" /><div><h2>Provider Patient Roster</h2><p>Seen with ARIA · Active Patient Caseload</p></div></div>
        {patients.map(item => {
          const stats = patientStats(progress, item);
          return <button type="button" key={item.id} className={`edu-patient ${item.id === patientId ? 'active' : ''}`} aria-pressed={item.id === patientId} onClick={() => selectPatient(item.id)}>
            <span className="edu-patient-top"><span className="edu-initials">{item.initials}</span><span><strong>{item.name}</strong><small>{item.demographics} · MRN {item.mrn}</small></span>{stats.complete && <Check size={18} aria-label="Module complete" />}</span>
            <span className="edu-diagnosis">{item.diagnosis}</span><span className="edu-patient-tag">{item.tag}</span>
            <span className="edu-patient-count">{stats.answered}/{stats.total} Clinical Questions<span>{stats.mastery}% mastery</span></span>
            <span className="edu-patient-progress"><span style={{ width: `${stats.completion}%` }} /></span>
          </button>;
        })}
        <div className="edu-roster-footer"><Target size={17} aria-hidden="true" /><span>Mastery = correct answers ÷ all questions in the case. Accuracy = correct ÷ answered.</span></div>
      </aside>
      <section className="edu-quiz" aria-label={`${patient.name} clinical quiz`}>
        <div className="edu-filters" role="group" aria-label="Question focus">
          {filters.map(item => <button type="button" key={item.id} aria-pressed={filter === item.id} onClick={() => { setFilter(item.id); setQuestionIndex(0); setNotice(''); }}>{item.label}</button>)}
        </div>
        <div className="edu-quiz-inner">
          <div className="edu-quiz-toolbar"><span className="edu-eyebrow">{question ? `Question ${questionIndex + 1} of ${questions.length}` : 'No questions in this focus'}</span>
            <button type="button" className="edu-reset" disabled={mastery.answered === 0} onClick={() => {
              persist(resetPatient(progressRef.current, patientId)); setQuestionIndex(0); setNotice(`${patient.name}'s quiz has been reset.`);
            }}><RotateCcw size={14} aria-hidden="true" />Reset Patient Quiz</button>
          </div>
          <details className="edu-snapshot" key={patientId}><summary><span><ShieldCheck size={17} aria-hidden="true" />Quick Chart Snapshot</span><ChevronDown size={16} aria-hidden="true" /></summary>
            <div>{patient.snapshot.map(item => <p key={item}>{item}</p>)}</div>
          </details>
          {notice && <p className="edu-notice" role="status">{notice}</p>}
          {syncError && <p className="edu-sync-error" role="alert">Your progress is visible here but could not be sent to the app. <button type="button" onClick={() => persist(progressRef.current)}>Retry saving</button></p>}
          {question ? <QuestionCard key={`${question.id}-${Boolean(progress.answers[patientId]?.[question.id])}`} patient={patient} question={question}
            answer={progress.answers[patientId]?.[question.id]} onSubmit={answerQuestion} />
            : <div className="edu-empty"><BookOpen size={28} aria-hidden="true" /><h3>No billing question in this case</h3><p>Choose another focus or open Ed Vance's billing module.</p><button type="button" className="edu-secondary" onClick={() => { setFilter('all'); setQuestionIndex(0); }}>Show All Case Questions</button></div>}
          {question && <nav className="edu-question-nav" aria-label="Quiz navigation">
            <button type="button" className="edu-secondary" disabled={questionIndex === 0} onClick={() => { setQuestionIndex(i => i - 1); setNotice(''); }}><ArrowLeft size={16} aria-hidden="true" />Previous Question</button>
            <span>{mastery.complete ? 'Case complete · Review any answer' : `${mastery.total - mastery.answered} unanswered in this case`}</span>
            <button type="button" className="edu-secondary" disabled={questionIndex >= questions.length - 1} onClick={() => { setQuestionIndex(i => i + 1); setNotice(''); }}>Next Question<ArrowRight size={16} aria-hidden="true" /></button>
          </nav>}
        </div>
      </section>
    </div>
  </main>;
}
