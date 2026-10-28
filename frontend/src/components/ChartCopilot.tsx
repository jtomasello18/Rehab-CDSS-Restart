import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, FileText, FlaskConical, Sparkles, X } from 'lucide-react';
import { Streamlit } from 'streamlit-component-lib';
import {
  answerChartQuestion, applyCopilotResult, chartPatientId, chartRecords,
  suggestedQueries, type ChartMessage, type CopilotResult,
} from '../utils/chartCopilot';
import { useFrameViewport } from '../utils/useFrameViewport';

export type CopilotArgs = {
  copilotHistory?: ChartMessage[];
  copilotResult?: CopilotResult | null;
};
const newId = () => `chart-${Date.now()}-${Math.random().toString(36).slice(2)}`;
const quickQueries = [
  'When did Baclofen change?', 'Timeline of 10MWT & BBS',
  'Recent CMP & Labs?', 'OT & SLP fatigue notes?',
];

export default function ChartCopilot({ args = {}, open, onClose }: { args?: CopilotArgs; open: boolean; onClose: () => void }) {
  const [messages, setMessages] = useState<ChartMessage[]>(args.copilotHistory ?? []);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const pendingId = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollArea = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sourceRef = useRef<HTMLDivElement>(null);
  const sourceButton = useRef<HTMLButtonElement | null>(null);
  const lastScrolledQuestion = useRef<string | null>(null);
  const panelRef = useRef<HTMLDialogElement>(null);
  const [entered, setEntered] = useState(false);
  const viewport = useFrameViewport(open);
  const hasMessages = messages.length > 0;
  const clearTimer = () => { if (timer.current) clearTimeout(timer.current); timer.current = null; };
  const source = chartRecords.find(record => record.id === sourceId);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    let animationFrame = 0;
    let closeTimer: ReturnType<typeof setTimeout> | undefined;
    if (open) {
      if (!panel.open) panel.showModal();
      animationFrame = requestAnimationFrame(() => {
        setEntered(true);
        inputRef.current?.focus({ preventScroll: true });
      });
    } else {
      setEntered(false);
      // Keep the dialog mounted through its exit animation and preserve chat.
      if (panel.open) closeTimer = setTimeout(() => panel.close(), 300);
    }
    return () => { cancelAnimationFrame(animationFrame); clearTimeout(closeTimer); };
  }, [open]);
  useEffect(() => () => clearTimer(), []);
  useEffect(() => {
    const result = args.copilotResult;
    if (!result || result.requestId !== pendingId.current) return;
    clearTimer();
    pendingId.current = null;
    setPending(false);
    // A service failure leaves the already-visible instant chart lookup intact.
    if (result.mode === 'claude') setMessages(current => applyCopilotResult(current, result));
  }, [args.copilotResult]);
  useEffect(() => {
    const area = scrollArea.current;
    const question = [...messages].reverse().find(message => message.role === 'user');
    if (!area || !question || lastScrolledQuestion.current === question.id) return;
    const item = area.querySelector(`[data-chat-message="${CSS.escape(question.id)}"]`);
    if (item) area.scrollTop += item.getBoundingClientRect().top - area.getBoundingClientRect().top - 16;
    lastScrolledQuestion.current = question.id;
  }, [messages]);
  useEffect(() => { if (source && open) sourceRef.current?.focus({ preventScroll: true }); }, [sourceId, open]);

  const submit = (question: string) => {
    const text = question.trim().slice(0, 2000);
    if (!text) return;
    const id = newId();
    const previousQuestion = [...messages].reverse().find(message => message.role === 'user')?.answer ?? '';
    const local = answerChartQuestion(text, previousQuestion);
    const additions: ChartMessage[] = [
      { id: `${id}:question`, role: 'user', answer: text, sourceIds: [], mode: 'local' },
      { ...local, id: `${id}:answer`, role: 'assistant' },
    ];
    setMessages(current => [...current, ...additions].slice(-20));
    setInput('');
    setSourceId(null);
    clearTimer();
    pendingId.current = id;
    setPending(true);
    // The local answer is immediate and remains available even without Python.
    timer.current = setTimeout(() => { pendingId.current = null; setPending(false); }, 14000);
    try { Streamlit.setComponentValue({ action: 'chart_copilot_query', requestId: id, patientId: chartPatientId, question: text }); }
    catch { clearTimer(); pendingId.current = null; setPending(false); }
  };
  const clear = () => {
    clearTimer(); pendingId.current = null;
    setMessages([]); setInput(''); setSourceId(null); setPending(false);
    try { Streamlit.setComponentValue({ action: 'chart_copilot_clear', requestId: newId(), patientId: chartPatientId }); }
    catch { /* Local clearing remains available offline. */ }
    inputRef.current?.focus();
  };
  const closeSource = () => { setSourceId(null); sourceButton.current?.focus(); };

  return (
    <dialog ref={panelRef} id="ask-aria-panel" aria-labelledby="ask-aria-title" aria-modal="true" data-entered={entered} style={viewport} className="ask-aria-panel" onCancel={event => { event.preventDefault(); if (source) closeSource(); else onClose(); }} onClick={event => {
      if (event.target !== event.currentTarget) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
    }}>
      <header className="flex shrink-0 items-center justify-between gap-3 px-5 pb-3 pt-5">
        <h2 id="ask-aria-title" className="flex items-center gap-2 text-sm font-semibold text-[#145b6e]"><Sparkles className="h-4 w-4" aria-hidden="true" />Ask ARIA</h2>
        <div className="flex items-center gap-1">
          <button type="button" onClick={clear} disabled={!hasMessages && !input} className="rounded-full px-3 py-2 text-xs font-medium text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e] disabled:opacity-40">Clear</button>
          <button type="button" onClick={onClose} aria-label="Close Ask ARIA" className="rounded-full p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e]"><X className="h-5 w-5" aria-hidden="true" /></button>
        </div>
      </header>
      <div className={`ask-aria-content relative min-h-0 flex-1 ${hasMessages ? 'is-chatting' : ''}`}>
        <div className="ask-aria-welcome absolute inset-0 flex flex-col items-center justify-center overflow-y-auto px-6 py-6 text-center" aria-hidden={hasMessages}>
          <div className="mb-5 flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#f0f7f9] text-[#145b6e]"><Sparkles className="h-7 w-7" aria-hidden="true" /></div>
          <h3 className="text-3xl font-semibold tracking-tight text-slate-800">What's next?</h3>
          <p className="mt-3 text-xs text-slate-500">Ed Vance · MRN 482910</p>
          <div className="mt-8 flex shrink-0 flex-col items-center gap-3">{quickQueries.map((label, index) => <button type="button" key={label} tabIndex={hasMessages ? -1 : 0} onClick={() => submit(suggestedQueries[index])} className="max-w-full rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-600 transition hover:border-[#145b6e]/50 hover:bg-[#f0f7f9] hover:text-[#145b6e] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e]">{label}</button>)}</div>
        </div>
      <div ref={scrollArea} role="log" aria-label="Chart conversation" aria-live="polite" aria-relevant="additions text" className="ask-aria-thread h-full space-y-4 overflow-y-auto overscroll-contain px-5 py-4">
        {messages.map(message => <div key={message.id} data-chat-message={message.id} className={message.role === 'user' ? 'ml-5 rounded-xl bg-[#145b6e] p-3 text-white' : 'rounded-xl border border-sky-100 bg-[#eef6ff] p-3 text-slate-700'}>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide">{message.role === 'user' ? 'Clinician' : `ARIA · ${message.mode === 'claude' ? 'Chart synthesis' : 'Chart lookup'}`}</p>
          <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">{message.answer}</div>
          {message.role === 'assistant' && message.sourceIds.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5 border-t border-sky-100 pt-2" aria-label="Source records">
            {message.sourceIds.map(id => {
              const record = chartRecords.find(item => item.id === id);
              if (!record) return null;
              const Icon = record.kind === 'labs' ? FlaskConical : FileText;
              return <button type="button" key={id} aria-label={`Open source: ${record.date ?? 'Undated'} · ${record.author} · ${record.title}`} onClick={event => { sourceButton.current = event.currentTarget; setSourceId(id); }} className="inline-flex items-start gap-1 rounded-md border border-sky-200 bg-white px-2 py-1 text-left text-[10px] leading-relaxed text-[#145b6e] hover:border-[#145b6e] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e]"><Icon className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" /><span>{record.date ?? 'Undated'} · {record.kind === 'labs' ? record.title : record.author}</span></button>;
            })}
          </div>}
        </div>)}
      </div>
      </div>
      <form onSubmit={event => { event.preventDefault(); submit(input); }} className="ask-aria-input shrink-0 bg-white px-4 pb-4 pt-2">
        <p role="status" className="mb-2 min-h-4 px-1 text-[11px] text-slate-500">{pending ? 'Chart lookup ready · Reviewing the record…' : hasMessages ? 'Select a source to review the chart excerpt.' : ''}</p>
        <label htmlFor="copilot-question" className="sr-only">Ask ARIA</label>
        <div className="flex items-end gap-2 rounded-3xl border border-slate-200 bg-slate-50 p-2 pl-4 transition focus-within:border-[#145b6e] focus-within:ring-2 focus-within:ring-[#145b6e]/10">
          <textarea id="copilot-question" ref={inputRef} rows={1} maxLength={2000} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(input); } }} placeholder="Ask ARIA..." className="max-h-32 min-w-0 flex-1 resize-none bg-transparent py-2 text-sm leading-5 text-slate-800 outline-none placeholder:text-slate-400" />
          <button type="submit" aria-label="Send message" disabled={!input.trim()} className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#145b6e] text-white transition hover:bg-[#0f4c5c] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#145b6e] disabled:opacity-40"><ArrowUp className="h-4 w-4" aria-hidden="true" /></button>
        </div>
      </form>
      {source && <div ref={sourceRef} tabIndex={-1} role="region" aria-label="Selected source record" onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeSource(); } }} className="absolute inset-x-2 bottom-2 z-10 max-h-[65%] overflow-auto rounded-xl border border-slate-300 bg-white p-4 shadow-xl outline-none focus:ring-2 focus:ring-[#145b6e]">
        <div className="flex items-start justify-between gap-2"><div><h3 className="text-sm font-bold text-[#145b6e]">{source.date ?? 'Date not supplied'} · {source.title}</h3><p className="mt-1 text-xs text-slate-500">{source.author} · Indexed chart excerpt</p></div><button type="button" onClick={closeSource} aria-label="Close source record" className="rounded-md p-1 text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e]"><X className="h-4 w-4" /></button></div>
        <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-700">{source.entries.map(entry => <p key={entry.text}>{entry.text}</p>)}</div>
      </div>}
    </dialog>
  );
}
