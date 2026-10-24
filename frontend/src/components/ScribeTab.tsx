import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, FileSignature, Mic, MicOff, Send } from 'lucide-react';
import { Streamlit } from 'streamlit-component-lib';
import ariaLogo from '../assets/aria-logo.svg';
import '../styles/ChartingWorkspace.css';
import { applyClinicalCorrections } from '../utils/clinicalCorrections';
import { expandClinicalShorthand, type SoapNote } from '../utils/clinicalSoap';
import { addSkilledJustification, alignCpt, applyLocalInstruction, condenseSoap } from '../utils/soapRefinements';

type DraftSource = 'claude' | 'local' | 'manual' | 'error';
type GenerationResult = { requestId: string; error: string | null; generated_at?: string };
type ScribeArgs = { role?: string; soap?: SoapNote; signed?: boolean; transcript?: string; generation?: GenerationResult; generated_at?: string; draft_source?: DraftSource; discipline?: string };

const SOAP_SECTIONS = ['subjective', 'objective', 'assessment', 'plan'] as const;
const DISCIPLINES = ['PT Skilled SOAP', 'OT Functional SOAP', 'SLP Cognitive-Linguistic SOAP', 'MD Neuro Follow-up'];
const emptySoap = (): SoapNote => ({ subjective: '', objective: '', assessment: '', plan: '' });
const isSoapNote = (value?: SoapNote): value is SoapNote => !!value && SOAP_SECTIONS.every(section => typeof value[section] === 'string' && value[section].trim().length > 0);
const requestId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const responseToken = (args: ScribeArgs) => args.generation ? `${args.generation.requestId}:${args.generated_at ?? args.generation.generated_at ?? ''}` : args.generated_at ?? null;

export default function ScribeTab({ args = {} }: { args?: ScribeArgs }) {
  const canEdit = args.role === 'PT';
  const [mode, setMode] = useState<'ambient' | 'dictation'>('ambient');
  const [discipline, setDiscipline] = useState(args.discipline && DISCIPLINES.includes(args.discipline) ? args.discipline : DISCIPLINES[0]);
  // Every newly opened workspace starts a fresh encounter. Server results are
  // accepted only for a request initiated by this mounted editor.
  const [rawInput, setRawInput] = useState('');
  const [soap, setSoap] = useState<SoapNote>(emptySoap);
  const [draftSource, setDraftSource] = useState<DraftSource>('manual');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [captureStatus, setCaptureStatus] = useState('Ready for a clinician-entered transcript or shorthand.');
  const [smartEditPrompt, setSmartEditPrompt] = useState('');
  const [refinementStatus, setRefinementStatus] = useState('');
  const [condensedSnapshot, setCondensedSnapshot] = useState<SoapNote | null>(null);
  const [signed, setSigned] = useState(false);
  const recognitionRef = useRef<any>(null);
  const pendingRequestRef = useRef<string | null>(null);
  const appliedResponseRef = useRef<string | null>(responseToken(args));
  const generationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const localDraftRef = useRef<{ requestId: string; soap: SoapNote } | null>(null);
  const fallbackAppliedRef = useRef<string | null>(null);
  const draftEditedRef = useRef(false);
  const retiredRequestsRef = useRef(new Set<string>());
  const pendingKindRef = useRef<'generation' | 'refinement'>('generation');
  const hasNote = SOAP_SECTIONS.every(section => soap[section].trim().length > 0);
  const canRefine = canEdit && !isGenerating && !generationError && hasNote;

  useEffect(() => { Streamlit.setFrameHeight(); });
  useEffect(() => {
    if (canEdit) {
      try { Streamlit.setComponentValue({ type: 'reset_scribe', requestId: requestId(), discipline }); }
      catch { /* Opening a fresh editor does not depend on server availability. */ }
    }
  }, []);
  const clearGenerationTimer = () => {
    if (generationTimerRef.current !== null) clearTimeout(generationTimerRef.current);
    generationTimerRef.current = null;
  };
  const applyLocalDraft = (id: string, message: string) => {
    const draft = localDraftRef.current;
    if (!draft || draft.requestId !== id) return;
    clearGenerationTimer();
    if (fallbackAppliedRef.current !== id && !draftEditedRef.current) {
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
    if (retiredRequestsRef.current.has(result.requestId)) return;
    if (!pendingRequestRef.current || result.requestId !== pendingRequestRef.current) return;
    appliedResponseRef.current = token;
    clearGenerationTimer();
    pendingRequestRef.current = null;
    setIsGenerating(false);
    if (draftEditedRef.current) {
      setCaptureStatus('Claude finished. Your local edits have been preserved.');
      return;
    }
    if (result.error || !isSoapNote(args.soap)) {
      if (localDraftRef.current?.requestId === result.requestId) {
        applyLocalDraft(result.requestId, pendingKindRef.current === 'refinement'
          ? 'Claude could not apply the refinement. The existing note has been retained.'
          : 'Local shorthand draft retained. Claude was unavailable; review every section.');
        if (pendingKindRef.current === 'refinement') setRefinementStatus('Refinement unavailable — existing note retained. Retry or use an action chip.');
      } else {
        setGenerationError(result.error || 'Claude returned an incomplete SOAP draft. Please retry.');
      }
      return;
    }
    setSoap(args.soap);
    setCondensedSnapshot(null);
    setDraftSource('claude');
    setGenerationError(null);
    setSigned(false);
    setCaptureStatus('Claude SOAP draft received. Review all four sections before signing.');
    if (pendingKindRef.current === 'refinement') setRefinementStatus('Refinement applied by Claude — review the updated SOAP sections.');
  }, [args.generation, args.generated_at, args.soap]);

  const updateSoap = (section: keyof SoapNote, value: string) => {
    draftEditedRef.current = true;
    setDraftSource('manual');
    setGenerationError(null);
    setSoap(current => ({ ...current, [section]: value }));
    setCondensedSnapshot(null);
    setRefinementStatus('');
    setSigned(false);
  };

  const selectTemplate = (label: string) => {
    recognitionRef.current?.stop?.();
    setIsListening(false);
    clearGenerationTimer();
    if (pendingRequestRef.current) retiredRequestsRef.current.add(pendingRequestRef.current);
    pendingRequestRef.current = null;
    setDiscipline(label);
    setRawInput('');
    setSoap(emptySoap());
    setDraftSource('manual');
    setSigned(false);
    setCondensedSnapshot(null);
    setGenerationError(null);
    setRefinementStatus('');
    setSmartEditPrompt('');
    draftEditedRef.current = true;
    setCaptureStatus('New specialty encounter ready for your notes or dictation.');
    try {
      Streamlit.setComponentValue({ type: 'reset_scribe', requestId: requestId(), discipline: label });
    } catch { /* The editor is already cleared locally if the connection drops. */ }
  };

  const startVoiceDictation = () => {
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition) {
      setCaptureStatus('Voice recognition is unavailable in this browser. Enter the encounter transcript manually.');
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
      draftEditedRef.current = true;
      setCaptureStatus('Live transcript captured. Review before structuring.');
    };
    recognition.onerror = () => {
      setIsListening(false);
      setCaptureStatus('Microphone permission was not available. Enter the encounter transcript manually.');
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
    if (pendingRequestRef.current) retiredRequestsRef.current.add(pendingRequestRef.current);
    pendingRequestRef.current = id;
    pendingKindRef.current = 'generation';
    localDraftRef.current = { requestId: id, soap: expandClinicalShorthand(corrected, discipline) };
    fallbackAppliedRef.current = null;
    draftEditedRef.current = false;
    setIsGenerating(true);
    setGenerationError(null);
    setSigned(false);
    setRefinementStatus('');
    setCondensedSnapshot(null);
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
    if (!canRefine) return;
    draftEditedRef.current = true;
    setDraftSource('manual');
    if (kind === 'concise') {
      setSoap(condensedSnapshot ?? condenseSoap(soap));
      setCondensedSnapshot(condensedSnapshot ? null : soap);
      setRefinementStatus(condensedSnapshot ? 'Full narrative restored.' : 'Condensed summary applied to all four SOAP sections.');
    } else {
      const base = condensedSnapshot ?? soap;
      setSoap(kind === 'audit' ? addSkilledJustification(base, discipline) : alignCpt(base, discipline));
      setCondensedSnapshot(null);
      setRefinementStatus(kind === 'audit' ? 'Clinical skilled justification updated in Assessment.' : 'Clinical CPT alignment updated in Objective and Plan.');
    }
    setSigned(false);
  };

  const submitSmartEdit = () => {
    const request = smartEditPrompt.trim();
    if (!request || !canRefine) return;
    const transformed = applyLocalInstruction(soap, request, discipline);
    if (transformed) {
      draftEditedRef.current = true;
      setDraftSource('manual');
      setSoap(transformed);
      setCondensedSnapshot(null);
      setRefinementStatus(JSON.stringify(transformed) === JSON.stringify(soap) ? 'The note already matches this refinement.' : 'Refinement applied — review the updated SOAP sections.');
      setSigned(false);
    } else {
      const id = requestId();
      clearGenerationTimer();
      if (pendingRequestRef.current) retiredRequestsRef.current.add(pendingRequestRef.current);
      pendingRequestRef.current = id;
      pendingKindRef.current = 'refinement';
      localDraftRef.current = { requestId: id, soap };
      fallbackAppliedRef.current = null;
      draftEditedRef.current = false;
      setIsGenerating(true);
      setSigned(false);
      setRefinementStatus('Applying your refinement with Claude…');
      generationTimerRef.current = setTimeout(() => {
        if (pendingRequestRef.current === id) {
          applyLocalDraft(id, 'The existing note remains editable while Claude processes the refinement.');
          setRefinementStatus('Awaiting Claude — existing note retained. You can keep editing.');
        }
      }, 2000);
      try {
        Streamlit.setComponentValue({ type: 'refine_soap', requestId: id, soap, instruction: request, discipline, transcript: rawInput });
      } catch {
        applyLocalDraft(id, 'The server connection is unavailable. The existing note has been retained.');
        setRefinementStatus('Refinement unavailable — existing note retained.');
        pendingRequestRef.current = null;
      }
    }
    setSmartEditPrompt('');
  };

  const signAndSync = () => {
    if (!canRefine) return;
    draftEditedRef.current = true;
    setSigned(true);
    Streamlit.setComponentValue({ type: 'signed', requestId: requestId(), soap, draftSource, discipline, transcript: rawInput });
  };

  return (
    <div className="aria-charting min-h-screen bg-transparent text-slate-900 flex flex-col font-sans">
      <main className="w-full max-w-[1600px] mx-auto px-0 py-6 space-y-5">
        <section className="bg-white border border-slate-300 rounded-xl shadow-sm p-5 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3"><img src={ariaLogo} alt="ARIA" className="h-11 w-11 shrink-0 rounded-xl" /><div><h1 className="text-xl font-semibold tracking-tight">ARIA Scribe</h1><p className="text-sm text-slate-500 mt-1">Clinical Documentation &amp; Encounter Structuring</p></div></div>
            </div>
            <select aria-label="Clinical documentation template" value={discipline} onChange={event => selectTemplate(event.target.value)} disabled={!canEdit || isGenerating} className="max-w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium bg-white">
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
              <button type="button" onClick={generateSoap} disabled={!canEdit || isGenerating || !rawInput.trim()} className="scribe-button scribe-button-primary">{isGenerating ? pendingKindRef.current === 'refinement' ? 'Applying Refinement…' : 'Generating SOAP Note…' : 'Generate Structured SOAP Note'}</button>
            </div>
            <textarea aria-label="Encounter transcript" value={rawInput} onChange={event => { draftEditedRef.current = true; setRawInput(event.target.value); setSigned(false); }} onBlur={event => setRawInput(applyClinicalCorrections(event.target.value))} disabled={!canEdit || isGenerating} placeholder="Type clinical shorthand, free-text notes, or dictate the encounter here (just like Heidi AI)..." className="w-full min-h-[90px] rounded-lg border border-slate-300 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100 disabled:text-slate-500" />
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
            <button type="button" aria-pressed={!!condensedSnapshot} disabled={!canRefine} onClick={() => applySmartEdit('concise')} className="scribe-action-chip">{condensedSnapshot ? 'Restore Full Narrative' : 'Condense Narrative'}</button>
          </div>
          <div className="flex gap-2">
            <input aria-label="Documentation refinement request" value={smartEditPrompt} onChange={event => setSmartEditPrompt(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && canRefine) submitSmartEdit(); }} disabled={!canRefine} placeholder="Ask ARIA to edit or format your note..." className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100" />
            <button type="button" onClick={submitSmartEdit} disabled={!canRefine || !smartEditPrompt.trim()} className="scribe-button scribe-button-primary"><Send className="h-4 w-4 shrink-0" aria-hidden="true" />Apply</button>
          </div>
          {refinementStatus && <p role="status" className="inline-flex items-center gap-2 rounded-md border border-[#145b6e]/20 bg-[#f0f7f9] px-3 py-2 text-xs font-medium text-[#145b6e]"><CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />{refinementStatus}</p>}
        </section>
      </main>

      <footer className="sticky bottom-0 z-10 border-t border-slate-300 bg-white/95 backdrop-blur p-4 shadow-[0_-4px_8px_-4px_rgb(15,23,42,0.2)]">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          {signed ? <div role="status" className="scribe-sign-confirmation"><CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden="true" /><span>Draft marked reviewed for eCW handoff. Live chart transmission and billing verification are not configured.</span></div> : <span className="text-xs text-slate-500">Review the complete note before preparing it for eClinicalWorks.</span>}
          <button type="button" onClick={signAndSync} disabled={!canRefine} className="scribe-button scribe-button-primary"><FileSignature className="h-4 w-4 shrink-0" aria-hidden="true" />Sign &amp; Sync to eClinicalWorks (eCW)</button>
        </div>
      </footer>
    </div>
  );
}
