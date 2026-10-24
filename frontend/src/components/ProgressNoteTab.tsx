import React, { useState } from 'react';
import {
  AlertCircle, AlertTriangle, Info, BrainCircuit, Stethoscope,
  PersonStanding, Hand, MessageSquare, ChevronDown, CheckCircle2, Ban, ArrowUpRight,
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  encounters, trackerMetrics, metricValue, metricDelta, careTeam, specialtyPlans, comparisons,
  normativePanelDescription, safetyFlags,
  type Specialty, type Tone, type TrackerMetric,
} from '../data/patientTracker';

function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

const toneClasses: Record<Tone, string> = {
  danger: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  neutral: 'border-slate-200 bg-slate-50 text-slate-600',
};
const specialties = [
  { id: 'pt', label: 'Physical Therapy (PT)', icon: PersonStanding },
  { id: 'physician', label: 'Physician / Neuro (MD)', icon: Stethoscope },
  { id: 'ot', label: 'Occupational Therapy (OT)', icon: Hand },
  { id: 'slp', label: 'Speech-Language Pathology (SLP)', icon: MessageSquare },
] as const;

const Card = ({ className, children }: { className?: string; children: React.ReactNode }) => (
  <section className={cn('min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm', className)}>{children}</section>
);
const CardHeader = ({ children }: { children: React.ReactNode }) => (
  <h2 className="border-b border-slate-100 bg-slate-50/60 px-5 py-4 text-sm font-semibold text-slate-800">{children}</h2>
);
const CardContent = ({ className, children }: { className?: string; children: React.ReactNode }) => (
  <div className={cn('p-5', className)}>{children}</div>
);
const Badge = ({ tone, children }: { tone: Tone; children: React.ReactNode }) => (
  <span className={cn('inline-flex w-fit items-center rounded-lg border px-2.5 py-1.5 text-xs font-semibold leading-relaxed', toneClasses[tone])}>{children}</span>
);
function LongitudinalMetric({ metric }: { metric: TrackerMetric }) {
  const delta = metricDelta(metric);
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4" data-metric={metric.id}>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{metric.label}</h3>
      <div className="min-h-10 break-words text-2xl font-bold tracking-tight text-slate-900">{metricValue(metric, 'current')}</div>
      <Badge tone={delta.tone}>{delta.text}</Badge>
      {metric.note && <p className="text-xs leading-relaxed text-slate-600">{metric.note}</p>}
      <dl className="mt-auto grid grid-cols-3 gap-1.5 border-t border-slate-100 pt-3">
        {encounters.map(encounter => (
          <div key={encounter.key} className={cn('min-w-0 rounded-md p-2', encounter.key === 'current' ? 'bg-[#145b6e]/5' : 'bg-slate-50')}>
            <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{encounter.date}<span className="block">Wk {encounter.week}</span><span className="block normal-case tracking-normal">{encounter.label}</span></dt>
            <dd className="mt-1 break-words text-xs font-medium leading-relaxed text-slate-700">{metricValue(metric, encounter.key)}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function MetricPanel({ specialty }: { specialty: Specialty }) {
  const titles = { pt: 'Functional Metrics', physician: 'Diagnostics & Metrics', ot: 'Upper Extremity Metrics', slp: 'Cognitive-Linguistic Metrics' };
  return (
    <Card className="col-span-full">
      <CardHeader>{titles[specialty]}</CardHeader>
      <CardContent className={cn('grid grid-cols-1 gap-4 sm:grid-cols-2', 'xl:grid-cols-4')}>
        {trackerMetrics[specialty].map(metric => <LongitudinalMetric key={metric.id} metric={metric} />)}
      </CardContent>
    </Card>
  );
}

function PatientBanner() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <div className="grid grid-cols-1 items-center gap-x-8 gap-y-4 text-sm md:grid-cols-3">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#145b6e]/10 text-lg font-bold text-[#145b6e]">EV</div>
          <div><div className="font-bold text-slate-900">Vance, E.</div><div className="text-xs text-slate-500">67 y/o Male · MRN: 482910</div></div>
        </div>
        <div className="min-w-0 flex-1"><div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Primary Diagnosis</div><div className="mt-1 font-medium">12 weeks post-L MCA ischemic stroke</div><p className="mt-1 text-xs text-slate-500">IRF discharge 2 weeks ago · Outpatient evaluation today</p><p className="mt-1 text-xs text-amber-800">Mild expressive aphasia · Right dominant hemiparesis</p></div>
        <div className="min-w-0 flex-1"><div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Shared Patient Goals</div><p className="mt-1">Walk to mailbox independently · Feed self using dominant right hand</p></div>
      </div>
    </div>
  );
}

function CareTeamPulse({ activeView, onSelect }: { activeView: Specialty; onSelect: (view: Specialty) => void }) {
  return (
    <section aria-labelledby="care-team-title">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="care-team-title" className="text-sm font-bold text-slate-800">Multidisciplinary Care Team Pulse</h2>
        <p className="text-xs text-slate-500">Case snapshot · Current 10/13 · Select a specialty</p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {careTeam.map(team => {
          const Icon = specialties.find(s => s.id === team.id)!.icon;
          return (
            <button key={team.id} type="button" aria-pressed={activeView === team.id} onClick={() => onSelect(team.id)}
              className={cn('flex min-w-0 flex-col items-start gap-3 rounded-xl border bg-white p-4 text-left shadow-sm transition hover:border-[#145b6e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#145b6e] focus-visible:ring-offset-2', activeView === team.id ? 'border-[#145b6e] ring-1 ring-[#145b6e]' : 'border-slate-200')}>
              <span className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Icon className="h-4 w-4 shrink-0 text-[#145b6e]" aria-hidden="true" />{team.label}</span>
              <Badge tone={team.tone}>{team.badge}</Badge>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function ActiveAlerts({ specialty }: { specialty: Specialty }) {
  return (
    <Card className="col-span-full">
      <CardHeader>Active Alerts</CardHeader>
      <CardContent className="space-y-2">
        {safetyFlags[specialty].map(flag => {
          const Icon = flag.tone === 'danger' ? AlertCircle : flag.tone === 'warning' ? AlertTriangle : Info;
          return (
            <div key={flag.title} data-safety-flag className={cn('flex items-start gap-2.5 rounded-md border px-3 py-2.5', flag.tone === 'info' ? 'border-sky-200 bg-sky-50 text-sky-950' : toneClasses[flag.tone])}>
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p className="text-xs leading-relaxed sm:text-sm"><strong className="font-semibold">{flag.title}:</strong> {flag.text}</p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function MedicationPanel() {
  return (
    <Card className="col-span-full">
      <CardHeader>Current Medications</CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-left text-sm" aria-label="Baclofen dose history">
          <thead className="border-b text-xs uppercase text-slate-500">
            <tr><th scope="col" className="py-2 pr-3">Medication</th>{encounters.map(e => <th key={e.key} scope="col" className="px-2 py-2">{e.date}<span className="block text-[10px] font-medium">Wk {e.week} · {e.label}</span></th>)}</tr>
          </thead>
          <tbody>
            <tr className="bg-amber-50/50"><th scope="row" className="py-4 pr-3 font-semibold">Baclofen</th><td className="px-2">5mg TID</td><td className="px-2">Increased to 10mg TID</td><td className="px-2 font-semibold">10mg TID</td></tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function FeedingGoal() {
  return (
    <Card className="col-span-full">
      <CardHeader>Goal Progress: Self-Feeding (Dominant Right)</CardHeader>
      <CardContent className="grid gap-5 lg:grid-cols-2">
        <div><div className="mb-2 flex justify-between text-sm font-semibold"><span>Current Goal Completion (10/13)</span><span>25%</span></div><div role="progressbar" aria-label="Self-feeding goal completion" aria-valuenow={25} aria-valuemin={0} aria-valuemax={100} className="h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full w-1/4 rounded-full bg-[#145b6e]" /></div><p className="mt-3 text-xs leading-relaxed text-slate-500">09/29 and 10/06 goal percentages not recorded. Proximal gains coexist with persistent Grade 2 elbow tone and Stage 3 flexor synergy.</p></div>
        <ul className="space-y-2 text-sm text-slate-600"><li>Grasp adapted utensil — independent with built-up handle.</li><li>~ Scoop food — moderate assistance; spasticity limits wrist extension.</li><li>○ Bring to mouth — maximum assistance; flexor synergy limits isolation.</li></ul>
      </CardContent>
    </Card>
  );
}

export type BridgeSource = {
  document_id: string; filename: string; page_number: number; text: string; star_rating: number;
};
type BridgeEvidence = { sources?: Partial<Record<Specialty, BridgeSource[]>>; error?: string };

function CPGPanel({ specialty, evidence, onOpen }: { specialty: Specialty; evidence: BridgeEvidence; onOpen?: () => void }) {
  const plan = specialtyPlans[specialty];
  const sources = evidence.sources?.[specialty] ?? [];
  return (
    <Card className="col-span-full">
      <CardHeader><span className="flex items-center gap-2 text-[#145b6e]"><BrainCircuit className="h-4 w-4" aria-hidden="true" />ARIA Clinical Practice Guideline Alerts</span></CardHeader>
      <CardContent>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <h3 className="text-sm font-semibold text-slate-700">{plan.title}</h3>
          <span title="Recommendation grades and page labels supplied in the case reference; not verified against the retrieved PDFs." className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-500">Case reference</span>
        </div>
        {sources.length > 0 && <div className="mb-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">Matched Evidence Bridge PDF Passages</h3>
            {onOpen && <button type="button" onClick={onOpen} className="inline-flex items-center gap-1 text-xs font-medium text-[#145b6e] underline">Open Evidence Bridge<ArrowUpRight className="h-3 w-3" aria-hidden="true" /></button>}
          </div>
          <div className="space-y-2">{sources.map(source => <details key={`${source.document_id}-${source.page_number}`} className="rounded-md border border-slate-200 bg-slate-50 p-3"><summary className="cursor-pointer break-words text-xs font-semibold text-[#145b6e]">{source.filename} · Page {source.page_number} · {'★'.repeat(source.star_rating)}{'☆'.repeat(5 - source.star_rating)} {source.star_rating}/5</summary><blockquote className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-600">{source.text}</blockquote></details>)}</div>
        </div>}
        {evidence.error && <p className="mb-3 text-xs text-amber-800">{evidence.error}</p>}
        <div className="grid gap-5 md:grid-cols-2">
          {[{ title: 'Recommended Active Interventions', items: plan.recommended, Icon: CheckCircle2, color: 'text-emerald-700' }, { title: 'Discouraged / Low-Value Interventions', items: plan.discouraged, Icon: Ban, color: 'text-amber-800' }].map(group => (
            <div key={group.title}>
              <h3 className={cn('mb-3 flex items-center gap-2 text-sm font-semibold', group.color)}><group.Icon className="h-4 w-4 shrink-0" aria-hidden="true" />{group.title}</h3>
              <ul className="list-disc space-y-2 pl-4 text-xs leading-relaxed text-slate-600">
                {group.items.map(item => <li key={item.text}>{item.text} <span className="font-medium text-slate-700" title="Case-reference citation label; verify against the original guideline.">[({item.citation})]</span></li>)}
              </ul>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function NormativePanel({ specialty }: { specialty: Specialty }) {
  return (
    <Card className="col-span-full">
      <CardHeader>Normative Performance Panel</CardHeader>
      <CardContent>
        <p className="mb-5 text-xs leading-relaxed text-slate-500">{normativePanelDescription}</p>
        <div className="grid gap-6 md:grid-cols-3">
          {comparisons[specialty].map(comparison => <article key={comparison.title} className="min-w-0"><h3 className="mb-3 text-sm font-semibold text-slate-800">{comparison.title}</h3><dl className="space-y-1 text-xs">{[
            [comparison.normLabel, comparison.norm], [comparison.avgLabel, comparison.avg],
            ['Vance, E. IRF Discharge (09/29)', comparison.initial], ['Vance, E. Outpatient Eval (10/13)', comparison.current],
          ].map(([label, value], i) => <div key={label} className={cn('flex items-start justify-between gap-3 rounded-md border-b border-slate-100 px-2 py-2.5', i === 2 && 'bg-slate-50', i === 3 && 'border-[#145b6e]/10 bg-[#145b6e]/5 font-semibold text-[#145b6e]')}><dt className="max-w-[60%]">{label}</dt><dd className="break-words text-right font-medium">{value}</dd></div>)}</dl>{comparison.note && <p className="mt-2 text-xs leading-relaxed text-slate-500">{comparison.note}</p>}{comparison.reference && <a className="mt-2 inline-block text-xs text-[#145b6e] underline" href={comparison.reference.url} target="_blank" rel="noopener noreferrer">{comparison.reference.label}</a>}</article>)}
        </div>
      </CardContent>
    </Card>
  );
}

type StreamlitArgs = { role?: string; trackerEvidence?: BridgeEvidence };
export default function App({ args = {}, onOpenEvidenceBridge }: { args?: StreamlitArgs; onOpenEvidenceBridge?: () => void }) {
  const initialViews: Record<string, Specialty> = { PT: 'pt', MD: 'physician', Physician: 'physician', OT: 'ot', SLP: 'slp' };
  const [activeView, setActiveView] = useState<Specialty>(initialViews[args.role ?? ''] ?? 'physician');
  const ActiveIcon = specialties.find(s => s.id === activeView)!.icon;
  return (
    <div className="min-h-screen bg-transparent font-sans text-slate-800">
      <PatientBanner />
      <main className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 py-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div><h1 className="text-2xl font-bold tracking-tight">ARIA Patient Tracker</h1><p className="mt-1 text-sm text-slate-500">Longitudinal, multidisciplinary care · Stroke rehabilitation</p></div>
          <div className="relative"><label htmlFor="tracker-specialty" className="sr-only">Specialty view</label><select id="tracker-specialty" value={activeView} onChange={e => setActiveView(e.target.value as Specialty)} className="w-full appearance-none rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-10 text-sm font-semibold shadow-sm focus:border-[#145b6e] focus:outline-none focus:ring-2 focus:ring-[#145b6e]/25 sm:w-72">{specialties.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}</select><ActiveIcon className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-[#145b6e]" aria-hidden="true" /><ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500" aria-hidden="true" /></div>
        </div>
        <CareTeamPulse activeView={activeView} onSelect={setActiveView} />
        <section id="specialty-view" aria-label={`${specialties.find(s => s.id === activeView)!.label} details`} className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <ActiveAlerts specialty={activeView} />
          {activeView === 'physician' && <MedicationPanel />}
          <MetricPanel specialty={activeView} />
          {activeView === 'ot' && <FeedingGoal />}
          <CPGPanel specialty={activeView} evidence={args.trackerEvidence ?? {}} onOpen={onOpenEvidenceBridge} />
          <NormativePanel specialty={activeView} />
        </section>
      </main>
    </div>
  );
}
