import React, { useEffect, useRef, useState } from 'react';
import { FileText, FlaskConical, Search, Send, X } from 'lucide-react';
import { Streamlit } from 'streamlit-component-lib';
import {
  answerChartQuestion, applyCopilotResult, chartPatientId, chartRecords,
  suggestedQueries, welcomeMessage, type ChartMessage, type CopilotResult,
} from '../utils/chartCopilot';

export type CopilotArgs = {
  copilotHistory?: ChartMessage[];
  copilotResult?: CopilotResult | null;
};
const newId = () => `chart-${Date.now()}-${Math.random().toString(36).slice(2)}`;

export default function ChartCopilot({ args = {} }: { args?: CopilotArgs }) {
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
  const clearTimer = () => { if (timer.current) clearTimeout(timer.current); timer.current = null; };
  const source = chartRecords.find(record => record.id === sourceId);

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
  useEffect(() => { if (source) sourceRef.current?.focus(); }, [sourceId]);

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
    <section id="chart-copilot" aria-label="ARIA Chart Copilot" className="relative flex h-[760px] min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="shrink-0 bg-gradient-to-r from-[#0f3d3e] to-[#134e4a] p-4 text-white">
        <div className="flex items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-base font-semibold"><Search className="h-4 w-4" aria-hidden="true" />ARIA Chart Copilot</h2>
          <button type="button" onClick={clear} className="rounded-md border border-white/30 px-2 py-1 text-xs font-medium hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white">Clear</button>
        </div>
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-teal-200/25 bg-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"><span className="h-1.5 w-1.5 rounded-full bg-teal-200" />Chart Index · Active</div>
        <p className="mt-2 text-xs leading-relaxed text-teal-50">Ask anything across PT, OT, SLP, MD notes, labs, &amp; med history.</p>
      </header>
      <div className="shrink-0 border-b border-slate-100 bg-slate-50/60 p-3">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Quick queries · Ed Vance · MRN 482910</p>
        <div className="flex flex-wrap gap-1.5">{suggestedQueries.map(query => <button type="button" key={query} onClick={() => submit(query)} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-left text-xs leading-relaxed text-[#145b6e] transition hover:border-[#145b6e] hover:bg-[#f0f7f9] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e]">{query}</button>)}</div>
      </div>
      <div ref={scrollArea} role="log" aria-label="Chart conversation" aria-live="polite" aria-relevant="additions text" className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-4">
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm leading-relaxed text-slate-600"><p className="mb-1 text-xs font-bold text-[#145b6e]">ARIA</p>{welcomeMessage}</div>
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
      <form onSubmit={event => { event.preventDefault(); submit(input); }} className="shrink-0 border-t border-slate-200 bg-white p-3">
        <p role="status" className="mb-2 min-h-4 text-[11px] text-slate-500">{pending ? 'Chart lookup ready · Claude is reviewing the record…' : 'Answers grounded in the indexed chart. Select a source to review.'}</p>
        <label htmlFor="copilot-question" className="sr-only">Ask ARIA Chart Copilot</label>
        <div className="flex items-end gap-2">
          <textarea id="copilot-question" ref={inputRef} rows={2} maxLength={2000} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(input); } }} placeholder="Ask about dates, meds, labs, or therapy notes..." className="min-w-0 flex-1 resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm leading-relaxed outline-none focus:border-[#145b6e] focus:ring-2 focus:ring-[#145b6e]/20" />
          <button type="submit" disabled={!input.trim()} className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-lg bg-[#145b6e] px-3 text-sm font-medium text-white hover:bg-[#0f4c5c] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#145b6e] disabled:opacity-40"><Send className="h-3.5 w-3.5" aria-hidden="true" />Send</button>
        </div>
      </form>
      {source && <div ref={sourceRef} tabIndex={-1} role="region" aria-label="Selected source record" onKeyDown={event => { if (event.key === 'Escape') closeSource(); }} className="absolute inset-x-2 bottom-2 z-10 max-h-[65%] overflow-auto rounded-xl border border-slate-300 bg-white p-4 shadow-xl outline-none focus:ring-2 focus:ring-[#145b6e]">
        <div className="flex items-start justify-between gap-2"><div><h3 className="text-sm font-bold text-[#145b6e]">{source.date ?? 'Date not supplied'} · {source.title}</h3><p className="mt-1 text-xs text-slate-500">{source.author} · Indexed chart excerpt</p></div><button type="button" onClick={closeSource} aria-label="Close source record" className="rounded-md p-1 text-slate-500 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#145b6e]"><X className="h-4 w-4" /></button></div>
        <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-700">{source.entries.map(entry => <p key={entry.text}>{entry.text}</p>)}</div>
      </div>}
    </section>
  );
}
