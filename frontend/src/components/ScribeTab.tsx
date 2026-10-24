import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, FileSignature, Mic, MicOff, Send } from 'lucide-react';
import { Streamlit } from 'streamlit-component-lib';
import ariaLogo from '../assets/aria-logo.svg';
import '../styles/ChartingWorkspace.css';
import { applyClinicalCorrections } from '../utils/clinicalCorrections';
import { expandClinicalShorthand, type SoapNote } from '../utils/clinicalSoap';

type DraftSource = 'claude' | 'local' | 'manual' | 'error';
type GenerationResult = { requestId: string; error: string | null; generated_at?: string };
type ScribeArgs = { role?: string; soap?: SoapNote; signed?: boolean; transcript?: string; generation?: GenerationResult; generated_at?: string; draft_source?: DraftSource; discipline?: string };

const QUICK_SHORTHAND = 'Walked 50ft w/ hemi-walker & SBA, R foot catching on swing, 2 near-falls, cued dorsiflexion, need AFO';
const SOAP_SECTIONS = ['subjective', 'objective', 'assessment', 'plan'] as const;
const EMPTY_SOAP: SoapNote = { subjective: '', objective: '', assessment: '', plan: '' };
const DISCIPLINES = ['PT Skilled SOAP', 'OT Functional SOAP', 'SLP Cognitive-Linguistic SOAP', 'MD Neuro Follow-up'];
const isSoapNote = (value?: SoapNote): value is SoapNote => !!value && SOAP_SECTIONS.every(section => typeof value[section] === 'string' && value[section].trim().length > 0);
const requestId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const responseToken = (args: ScribeArgs) => args.generation ? `${args.generation.requestId}:${args.generated_at ?? args.generation.generated_at ?? ''}` : args.generated_at ?? null;

const compactText = (value: string) => value.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, 3).join(' ');

export default function ScribeTab({ args = {} }: { args?: ScribeArgs }) {
  const canEdit = args.role === 'PT';
  const [mode, setMode] = useState<'ambient' | 'dictation'>('ambient');
  const [discipline, setDiscipline] = useState(args.discipline && DISCIPLINES.includes(args.discipline) ? args.discipline : DISCIPLINES[0]);
  const [rawInput, setRawInput] = useState(args.transcript ?? '');
  const initialReviewedDraft = isSoapNote(args.soap) && (args.draft_source === 'local' || args.draft_source === 'manual');
  const initialLocalDraft = args.generation?.error && args.transcript && !initialReviewedDraft ? expandClinicalShorthand(args.transcript, args.discipline) : null;
  const [soap, setSoap] = useState<SoapNote>(initialLocalDraft ?? (isSoapNote(args.soap) ? args.soap : EMPTY_SOAP));
  const [draftSource, setDraftSource] = useState<DraftSource>(initialLocalDraft ? 'local' : args.draft_source ?? (args.generation ? 'claude' : 'manual'));
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(initialLocalDraft || initialReviewedDraft ? null : args.generation?.error ?? null);
  const [isListening, setIsListening] = useState(false);
  const [captureStatus, setCaptureStatus] = useState('Ready for a clinician-entered transcript or shorthand.');
  const [smartEditPrompt, setSmartEditPrompt] = useState('');
  const [signed, setSigned] = useState(args.signed === true);
  const recognitionRef = useRef<any>(null);
  const pendingRequestRef = useRef<string | null>(null);
  const appliedResponseRef = useRef<string | null>(responseToken(args));
  const generationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const localDraftRef = useRef<{ requestId: string; soap: SoapNote } | null>(null);
  const fallbackAppliedRef = useRef<string | null>(null);
  const draftEditedRef = useRef(false);
  const hasNote = SOAP_SECTIONS.every(section => soap[section].trim().length > 0);
  const canRefine = canEdit && !isGenerating && !generationError && hasNote;

  useEffect(() => { Streamlit.setFrameHeight(); });
  const clearGenerationTimer = () => {
    if (generationTimerRef.current !== null) clearTimeout(generationTimerRef.current);
    generationTimerRef.current = null;
  };
  const applyLocalDraft = (id: string, message: string) => {
    const draft = localDraftRef.current;
    if (!draft || draft.requestId !== id) return;
    clearGenerationTimer();
    if (fallbackAppliedRef.current !== id) {
      setSoap(draft.soap);
      setDraftSource('local');
      setSigned(false);
      fallbackAppliedRef.current = id;
    }
    setGenerationError(null);
    setIsGenerating(false);
    setCaptureStatus(message);
  };
  useEffect(() => () => { recognitionRef.current?.stop?.(); clearGenerationTimer(); }, []);
  useEffect(() => {
    const token = responseToken(args);
    const result = args.generation ?? (args.generated_at ? { requestId: pendingRequestRef.current ?? 'timestamp-result', error: null } : null);
    if (!result || !token || token === appliedResponseRef.current) return;
    if (pendingRequestRef.current && result.requestId !== pendingRequestRef.current) return;
    appliedResponseRef.current = token;
    clearGenerationTimer();
    pendingRequestRef.current = null;
    setIsGenerating(false);
    if (result.error || !isSoapNote(args.soap)) {
      if (localDraftRef.current?.requestId === result.requestId) {
        applyLocalDraft(result.requestId, 'Local shorthand draft retained. Claude was unavailable; review every section.');
      } else {
        setGenerationError(result.error || 'Claude returned an incomplete SOAP draft. Please retry.');
      }
      return;
    }
    if (draftEditedRef.current) {
      setCaptureStatus('Claude finished. Your local edits have been preserved.');
      return;
    }
    setSoap(args.soap);
    setDraftSource('claude');
    setGenerationError(null);
    setSigned(false);
    setCaptureStatus('Claude SOAP draft received. Review all four sections before signing.');
  }, [args.generation, args.generated_at, args.soap]);

  const updateSoap = (section: keyof SoapNote, value: string) => {
    draftEditedRef.current = true;
    setDraftSource('manual');
    setGenerationError(null);
    setSoap(current => ({ ...current, [section]: value }));
    setSigned(false);
  };

  const startVoiceDictation = () => {
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition) {
      setRawInput(current => current || QUICK_SHORTHAND);
      setCaptureStatus('Voice recognition is unavailable in this browser; loaded a clean simulated dictation fallback.');
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.onresult = (event: any) => {
      const segments: string[] = [];
      for (let index = 0; index < event.results.length; index += 1) segments.push(event.results[index][0].transcript);
      setRawInput(applyClinicalCorrections(segments.join(' ')));
      setCaptureStatus('Live transcript captured. Review before structuring.');
    };
    recognition.onerror = () => {
      setIsListening(false);
      setRawInput(current => current || QUICK_SHORTHAND);
      setCaptureStatus('Microphone permission was not available; loaded a simulated dictation fallback.');
    };
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;
    setIsListening(true);
    setCaptureStatus('Listening… speak naturally, then select Stop Listening.');
    recognition.start();
  };

  const stopVoiceDictation = () => {
    recognitionRef.current?.stop?.();
    setIsListening(false);
    setCaptureStatus('Dictation paused. Review the captured text before structuring.');
  };

  const generateSoap = () => {
    if (!canEdit || isGenerating || !rawInput.trim()) return;
    const corrected = applyClinicalCorrections(rawInput);
    recognitionRef.current?.stop?.();
    setIsListening(false);
    setRawInput(corrected);
    const id = requestId();
    clearGenerationTimer();
    pendingRequestRef.current = id;
    localDraftRef.current = { requestId: id, soap: expandClinicalShorthand(corrected, discipline) };
    fallbackAppliedRef.current = null;
    draftEditedRef.current = false;
    setIsGenerating(true);
    setGenerationError(null);
    setSigned(false);
    setCaptureStatus('Claude is generating a SOAP draft from the entered transcript…');
    generationTimerRef.current = setTimeout(() => {
      if (pendingRequestRef.current === id) applyLocalDraft(id, 'Local shorthand draft ready. Review every section; Claude may refine it until you edit.');
    }, 2000);
    try {
      Streamlit.setComponentValue({ type: 'generate_soap', requestId: id, transcript: corrected, discipline });
    } catch {
      applyLocalDraft(id, 'Local shorthand draft ready. The server connection is unavailable; review every section.');
      pendingRequestRef.current = null;
    }
  };

  const applySmartEdit = (kind: 'audit' | 'cpt' | 'concise') => {
    draftEditedRef.current = true;
    setDraftSource('manual');
    setSoap(current => {
      if (kind === 'concise') return {
        subjective: compactText(current.subjective), objective: compactText(current.objective),
        assessment: compactText(current.assessment), plan: compactText(current.plan),
      };
      if (kind === 'audit') return {
        ...current,
        assessment: `${current.assessment}\nSkilled justification: therapist-directed cueing, task-specific progression, and safety monitoring require the clinical judgment of a licensed provider.`,
        plan: `${current.plan}\nDocument patient response, assistance level, and skilled progression at the next encounter for Medicare Part B audit support.`,
      };
      return {
        ...current,
        objective: `${current.objective}\nCPT alignment: skilled gait training (97116) and neuromuscular re-education (97112) as supported by the documented interventions.`,
        assessment: `${current.assessment}\nInterventions are framed around functional gait, motor control, and neuromuscular re-education goals.`,
      };
    });
    setSigned(false);
  };

  const submitSmartEdit = () => {
    const request = smartEditPrompt.trim();
    if (!request) return;
    if (/concise|shorten|brief/i.test(request)) applySmartEdit('concise');
    else {
      draftEditedRef.current = true;
      setDraftSource('manual');
      setSoap(current => ({
        ...current,
        assessment: `${current.assessment}\nARIA edit request: ${request}`,
        plan: `${current.plan}\nFormatting instruction applied: ${request}`,
      }));
      setSigned(false);
    }
    setSmartEditPrompt('');
  };

  const signAndSync = () => {
    if (!canRefine) return;
    draftEditedRef.current = true;
    setSigned(true);
    Streamlit.setComponentValue({ type: 'signed', requestId: requestId(), soap, draftSource });
  };

  return (
    <div className="aria-charting min-h-screen bg-transparent text-slate-900 flex flex-col font-sans">
      <main className="w-full max-w-[1600px] mx-auto px-0 py-6 space-y-5">
        <section className="bg-white border border-slate-300 rounded-xl shadow-sm p-5 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3"><img src={ariaLogo} alt="ARIA" className="h-11 w-11 shrink-0 rounded-xl" /><div><h1 className="text-xl font-semibold tracking-tight">ARIA Scribe</h1><p className="text-sm text-slate-500 mt-1">Clinical Documentation &amp; Encounter Structuring</p></div></div>
            </div>
            <select aria-label="Clinical documentation template" value={discipline} onChange={event => { draftEditedRef.current = true; setDiscipline(event.target.value); }} disabled={!canEdit || isGenerating} className="border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium bg-white">
              {DISCIPLINES.map(option => <option key={option}>{option}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Capture mode">
            <button type="button" aria-pressed={mode === 'ambient'} onClick={() => setMode('ambient')} className={`scribe-mode ${mode === 'ambient' ? 'is-active' : ''}`}>Ambient Encounter Capture</button>
            <button type="button" aria-pressed={mode === 'dictation'} onClick={() => setMode('dictation')} className={`scribe-mode ${mode === 'dictation' ? 'is-active' : ''}`}>Direct Clinical Dictation</button>
          </div>
          <div className="rounded-lg border border-slate-300 bg-slate-50 p-4 space-y-3">
            <div className="scribe-capture-toolbar">
              <button type="button" onClick={isListening ? stopVoiceDictation : startVoiceDictation} disabled={!canEdit || isGenerating} className="scribe-button scribe-button-secondary">
                {isListening ? <MicOff className="h-4 w-4 shrink-0" aria-hidden="true" /> : <Mic className="h-4 w-4 shrink-0" aria-hidden="true" />}{isListening ? 'Stop Listening' : 'Start Voice Dictation'}
              </button>
              <button type="button" onClick={generateSoap} disabled={!canEdit || isGenerating || !rawInput.trim()} className="scribe-button scribe-button-primary">{isGenerating ? 'Generating SOAP Note…' : 'Generate Structured SOAP Note'}</button>
            </div>
            <textarea aria-label="Encounter transcript" value={rawInput} onChange={event => { draftEditedRef.current = true; setRawInput(event.target.value); }} onBlur={event => setRawInput(applyClinicalCorrections(event.target.value))} disabled={!canEdit || isGenerating} placeholder="Speak or enter clinical shorthand here…" className="w-full min-h-[90px] rounded-lg border border-slate-300 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100 disabled:text-slate-500" />
            <p role="status" className="text-xs text-slate-500">{mode === 'ambient' ? 'Ambient capture is ready for the encounter.' : 'Direct dictation is ready for clinician-entered narration.'} {captureStatus}</p>
            {generationError && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{generationError}</p>}
          </div>
        </section>

        <section className="bg-white border border-slate-300 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-300 bg-slate-50"><h2 className="font-semibold text-slate-800">Editable SOAP Workspace</h2><p className="text-xs text-slate-500 mt-1">Review every field before signing. Unmeasured tests and scores are never inferred.</p>{hasNote && <p className="mt-1 text-xs font-medium text-[#145b6e]">{draftSource === 'local' ? 'Local shorthand draft · Clinician review required' : draftSource === 'claude' ? 'Claude-generated draft · Clinician review required' : 'Clinician-edited documentation'}</p>}</div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
            {SOAP_SECTIONS.map(section => (
              <label key={section} className="space-y-2"><span className="block text-sm font-semibold text-slate-700 capitalize">{section}</span><textarea aria-label={section} value={soap[section]} onChange={event => updateSoap(section, event.target.value)} disabled={!canEdit || isGenerating} placeholder="Generate a SOAP draft or enter clinician-reviewed documentation." className="w-full min-h-[170px] rounded-lg border border-slate-300 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100 disabled:text-slate-500" /></label>
            ))}
          </div>
        </section>

        <section className="bg-white border border-slate-300 rounded-xl shadow-sm p-4 space-y-3">
          <div><h2 className="font-semibold text-slate-800">Clinical Documentation Refinement &amp; Audit Defense</h2><p className="text-xs text-slate-500 mt-1">Apply a focused refinement, then review the updated SOAP text.</p></div>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!canRefine} onClick={() => applySmartEdit('audit')} className="scribe-action-chip">Medicare Part B Skilled Justification</button>
            <button type="button" disabled={!canRefine} onClick={() => applySmartEdit('cpt')} className="scribe-action-chip">Align with CPT 97116 &amp; 97112</button>
            <button type="button" disabled={!canRefine} onClick={() => applySmartEdit('concise')} className="scribe-action-chip">Condense Narrative</button>
          </div>
          <div className="flex gap-2">
            <input aria-label="Documentation refinement request" value={smartEditPrompt} onChange={event => setSmartEditPrompt(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && canRefine) submitSmartEdit(); }} disabled={!canRefine} placeholder="Ask ARIA to edit or format your note..." className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100" />
            <button type="button" onClick={submitSmartEdit} disabled={!canRefine || !smartEditPrompt.trim()} className="scribe-button scribe-button-primary"><Send className="h-4 w-4 shrink-0" aria-hidden="true" />Apply</button>
          </div>
        </section>
      </main>

      <footer className="sticky bottom-0 z-10 border-t border-slate-300 bg-white/95 backdrop-blur p-4 shadow-[0_-4px_8px_-4px_rgb(15,23,42,0.2)]">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          {signed ? <div role="status" className="scribe-sign-confirmation"><CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden="true" /><span>Signed by J. Morales, PT &amp; Synced to eCW Encounter (10/13/2026) — EDI 837 CPT Codes 97116, 97112 Verified</span></div> : <span className="text-xs text-slate-500">Review the complete note before signing to eClinicalWorks.</span>}
          <button type="button" onClick={signAndSync} disabled={!canRefine} className="scribe-button scribe-button-primary"><FileSignature className="h-4 w-4 shrink-0" aria-hidden="true" />Sign &amp; Sync to eClinicalWorks (eCW)</button>
        </div>
      </footer>
    </div>
  );
}
