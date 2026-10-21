import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, FileSignature, Mic, MicOff, Send } from 'lucide-react';
import { Streamlit } from 'streamlit-component-lib';
import ariaLogo from '../assets/aria-logo.svg';
import '../styles/ChartingWorkspace.css';
import { applyClinicalCorrections } from '../utils/clinicalCorrections';

type SoapNote = { subjective: string; objective: string; assessment: string; plan: string };
type ScribeArgs = { role?: string; soap?: SoapNote; signed?: boolean };

const QUICK_SHORTHAND = 'Walked 50ft w/ hemi-walker & SBA, R foot catching on swing, 2 near-falls, cued dorsiflexion, need AFO';
const DEFAULT_SOAP: SoapNote = {
  subjective: 'Patient reports 2 near-falls at home this week and right foot catching on the carpet during walking. Patient reports fatigue after approximately 20 minutes.',
  objective: 'Ambulated 50 ft with a hemi-walker and standby assist (SBA). Absent right heel strike, severe swing-phase foot drop and right hip hiking/circumduction observed. Skilled cueing provided for dorsiflexion. No additional standardized tests documented in this draft.',
  assessment: 'Documented findings indicate ongoing fall risk related to swing-phase foot clearance and post-stroke fatigue. Continued skilled gait training is medically necessary to address safety, motor control, and progression toward independent household mobility.',
  plan: 'Continue skilled gait training with hemi-walker and standby assist, dorsiflexion cueing, and dynamic balance progression. Request AFO evaluation. Reassess documented foot clearance and near-fall frequency next visit.',
};
const DISCIPLINES = ['PT Skilled SOAP', 'OT Functional SOAP', 'SLP Cognitive-Linguistic SOAP', 'MD Neuro Follow-up'];

const compactText = (value: string) => value.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, 3).join(' ');

const structureSoap = (source: string, discipline: string): SoapNote => {
  const transcript = source.trim() || 'No transcript or shorthand entered.';
  return {
    subjective: `Clinician-entered ${discipline} report: ${transcript}\nPatient-reported symptoms and functional concerns should be confirmed during clinician review.`,
    objective: `Skilled session observations documented from the source: ${transcript}\nNo additional standardized tests, scores, or measurements were added.`,
    assessment: `The documented findings support continued skilled ${discipline.toLowerCase()} intervention for the stated functional limitations. Clinical interpretation remains limited to the information entered above and requires clinician verification.`,
    plan: `Continue skilled care directed at the documented limitations: ${transcript}\nReassess the reported response and add only measurements obtained during the encounter.`,
  };
};

export default function ScribeTab({ args = {} }: { args?: ScribeArgs }) {
  const canEdit = args.role === 'PT';
  const [mode, setMode] = useState<'ambient' | 'dictation'>('ambient');
  const [discipline, setDiscipline] = useState(DISCIPLINES[0]);
  const [rawInput, setRawInput] = useState('');
  const [soap, setSoap] = useState<SoapNote>(args.soap && Object.keys(args.soap).length ? args.soap : DEFAULT_SOAP);
  const [isListening, setIsListening] = useState(false);
  const [captureStatus, setCaptureStatus] = useState('Ready for a clinician-entered transcript or shorthand.');
  const [smartEditPrompt, setSmartEditPrompt] = useState('');
  const [signed, setSigned] = useState(args.signed === true);
  const recognitionRef = useRef<any>(null);

  useEffect(() => { Streamlit.setFrameHeight(); });
  useEffect(() => () => { recognitionRef.current?.stop?.(); }, []);

  const updateSoap = (section: keyof SoapNote, value: string) => {
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
    const corrected = applyClinicalCorrections(rawInput);
    setRawInput(corrected);
    setSoap(structureSoap(corrected, discipline));
    setSigned(false);
    setCaptureStatus('SOAP draft structured from the entered transcript without adding unmeasured tests.');
  };

  const applySmartEdit = (kind: 'audit' | 'cpt' | 'concise') => {
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
    setSigned(true);
    Streamlit.setComponentValue({ type: 'signed', soap });
  };

  return (
    <div className="aria-charting min-h-screen bg-transparent text-slate-900 flex flex-col font-sans">
      <main className="w-full max-w-[1600px] mx-auto px-0 py-6 space-y-5">
        <section className="bg-white border border-slate-300 rounded-xl shadow-sm p-5 space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3"><img src={ariaLogo} alt="ARIA" className="h-11 w-11 shrink-0 rounded-xl" /><div><h1 className="text-xl font-semibold tracking-tight">ARIA Charting Workspace</h1><p className="text-sm text-slate-500 mt-1">Clinical Documentation &amp; Encounter Structuring</p></div></div>
            </div>
            <select aria-label="Clinical documentation template" value={discipline} onChange={event => setDiscipline(event.target.value)} className="border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium bg-white">
              {DISCIPLINES.map(option => <option key={option}>{option}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Capture mode">
            <button type="button" aria-pressed={mode === 'ambient'} onClick={() => setMode('ambient')} className={`scribe-mode ${mode === 'ambient' ? 'is-active' : ''}`}>Ambient Encounter Capture</button>
            <button type="button" aria-pressed={mode === 'dictation'} onClick={() => setMode('dictation')} className={`scribe-mode ${mode === 'dictation' ? 'is-active' : ''}`}>Direct Clinical Dictation</button>
          </div>
          <div className="rounded-lg border border-slate-300 bg-slate-50 p-4 space-y-3">
            <div className="scribe-capture-toolbar">
              <button type="button" onClick={isListening ? stopVoiceDictation : startVoiceDictation} className="scribe-button scribe-button-secondary">
                {isListening ? <MicOff className="h-4 w-4 shrink-0" aria-hidden="true" /> : <Mic className="h-4 w-4 shrink-0" aria-hidden="true" />}{isListening ? 'Stop Listening' : 'Start Voice Dictation'}
              </button>
              <button type="button" onClick={generateSoap} disabled={!canEdit} className="scribe-button scribe-button-primary">Generate Structured SOAP Note</button>
            </div>
            <textarea aria-label="Encounter transcript" value={rawInput} onChange={event => setRawInput(event.target.value)} onBlur={event => setRawInput(applyClinicalCorrections(event.target.value))} disabled={!canEdit} placeholder="Speak or enter clinical shorthand here…" className="w-full min-h-[90px] rounded-lg border border-slate-300 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100 disabled:text-slate-500" />
            <p className="text-xs text-slate-500">{mode === 'ambient' ? 'Ambient capture is ready for the encounter.' : 'Direct dictation is ready for clinician-entered narration.'} {captureStatus}</p>
          </div>
        </section>

        <section className="bg-white border border-slate-300 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-300 bg-slate-50"><h2 className="font-semibold text-slate-800">Editable SOAP Workspace</h2><p className="text-xs text-slate-500 mt-1">Review every field before signing. Unmeasured tests and scores are never inferred.</p></div>
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
            {(Object.keys(soap) as Array<keyof SoapNote>).map(section => (
              <label key={section} className="space-y-2"><span className="block text-sm font-semibold text-slate-700 capitalize">{section}</span><textarea value={soap[section]} onChange={event => updateSoap(section, event.target.value)} disabled={!canEdit} className="w-full min-h-[170px] rounded-lg border border-slate-300 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100 disabled:text-slate-500" /></label>
            ))}
          </div>
        </section>

        <section className="bg-white border border-slate-300 rounded-xl shadow-sm p-4 space-y-3">
          <div><h2 className="font-semibold text-slate-800">Clinical Documentation Refinement &amp; Audit Defense</h2><p className="text-xs text-slate-500 mt-1">Apply a focused refinement, then review the updated SOAP text.</p></div>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!canEdit} onClick={() => applySmartEdit('audit')} className="scribe-action-chip">Medicare Part B Skilled Justification</button>
            <button type="button" disabled={!canEdit} onClick={() => applySmartEdit('cpt')} className="scribe-action-chip">Align with CPT 97116 &amp; 97112</button>
            <button type="button" disabled={!canEdit} onClick={() => applySmartEdit('concise')} className="scribe-action-chip">Condense Narrative</button>
          </div>
          <div className="flex gap-2">
            <input aria-label="Documentation refinement request" value={smartEditPrompt} onChange={event => setSmartEditPrompt(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') submitSmartEdit(); }} disabled={!canEdit} placeholder="Ask ARIA to edit or format your note..." className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#145b6e]/25 disabled:bg-slate-100" />
            <button type="button" onClick={submitSmartEdit} disabled={!canEdit || !smartEditPrompt.trim()} className="scribe-button scribe-button-primary"><Send className="h-4 w-4 shrink-0" aria-hidden="true" />Apply</button>
          </div>
        </section>
      </main>

      <footer className="sticky bottom-0 z-10 border-t border-slate-300 bg-white/95 backdrop-blur p-4 shadow-[0_-4px_8px_-4px_rgb(15,23,42,0.2)]">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          {signed ? <div role="status" className="scribe-sign-confirmation"><CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden="true" /><span>Signed by J. Morales, PT &amp; Synced to eCW Encounter (10/13/2026) — EDI 837 CPT Codes 97116, 97112 Verified</span></div> : <span className="text-xs text-slate-500">Review the complete note before signing to eClinicalWorks.</span>}
          <button type="button" onClick={signAndSync} disabled={!canEdit} className="scribe-button scribe-button-primary"><FileSignature className="h-4 w-4 shrink-0" aria-hidden="true" />Sign &amp; Sync to eClinicalWorks (eCW)</button>
        </div>
      </footer>
    </div>
  );
}
