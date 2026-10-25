import React, { useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import ariaLogo from '../assets/aria-logo.svg';
import '../styles/MeasuresTrends.css';

type ChartType = 'line' | 'bar';
type MetricKey = 'berg' | 'fma' | 'wab' | 'baclofen';
type SpecialtyChart = {
  key: MetricKey; specialty: string; title: string; range: string;
  color: string; maximum: number; ticks: number[]; badge: string; badgeClass: string;
};

// Four-point series supplied for the Ed Vance case visualization.
const outcomes = [
  { time: 'Wk 6', phase: ['Inpatient'], label: 'Wk 6 Inpatient', berg: 32, fma: 14, wab: 58.0, baclofen: 15 },
  { time: '09/29', phase: ['IRF', 'Discharge'], label: '09/29 IRF Discharge', berg: 42, fma: 18, wab: 64.2, baclofen: 15 },
  { time: '10/06', phase: ['MD Visit'], label: '10/06 MD Visit', berg: 40, fma: 20, wab: 68.0, baclofen: 30 },
  { time: '10/13', phase: ['Outpatient', 'Eval'], label: '10/13 Outpatient Eval', berg: 38, fma: 22, wab: 71.8, baclofen: 30 },
];
const charts: SpecialtyChart[] = [
  { key: 'berg', specialty: 'Physical Therapy (PT)', title: 'Berg Balance Scale', range: '0–56',
    color: '#145b6e', maximum: 56, ticks: [0, 14, 28, 42, 56],
    badge: 'Current: 38/56 · Regressing (Fall-Risk Cutoff: 45/56)', badgeClass: 'border-red-200 bg-red-50 text-red-800' },
  { key: 'fma', specialty: 'Occupational Therapy (OT)', title: 'Fugl-Meyer Upper Extremity', range: 'FMA-UE 0–66',
    color: '#0d9488', maximum: 66, ticks: [0, 22, 44, 66],
    badge: 'Current: 22/66 · Progressing (+4 pts from IRF Discharge)', badgeClass: 'border-emerald-200 bg-emerald-50 text-emerald-800' },
  { key: 'wab', specialty: 'Speech-Language (SLP)', title: 'WAB-R Aphasia Quotient', range: '0–100',
    color: '#2563eb', maximum: 100, ticks: [0, 25, 50, 75, 100],
    badge: 'Current: 71.8 / 100 · Progressing (+7.6 pts from IRF Discharge)', badgeClass: 'border-emerald-200 bg-emerald-50 text-emerald-800' },
  { key: 'baclofen', specialty: 'Attending Physician (MD)', title: 'Oral Baclofen Total Daily Dose', range: 'mg/day',
    color: '#b45309', maximum: 40, ticks: [0, 10, 20, 30, 40],
    badge: 'Current: 30 mg/day (10mg TID) · Doubled on 10/06', badgeClass: 'border-amber-200 bg-amber-50 text-amber-900' },
];
const formatValue = (key: MetricKey, value: number) => key === 'baclofen'
  ? `${value} mg/day (${value / 3}mg TID)`
  : key === 'wab' ? `${value.toFixed(1)} / 100` : `${value}/${key === 'berg' ? 56 : 66}`;

function TimelineTick({ x, y, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  const point = outcomes.find(item => item.time === payload?.value);
  return (
    <g transform={`translate(${x},${y})`} textAnchor="middle">
      <text fill="#334155" fontSize={11} fontWeight={600} y={16}>{point?.time}</text>
      <text fill="#64748b" fontSize={10} y={31}>
        {point?.phase.map((line, index) => <tspan key={line} x={0} dy={index ? 12 : 0}>{line}</tspan>)}
      </text>
    </g>
  );
}

function OutcomeCard({ chart }: { chart: SpecialtyChart }) {
  const [chartType, setChartType] = useState<ChartType>('line');
  const Chart = chartType === 'line' ? LineChart : BarChart;
  return (
    <section aria-labelledby={`${chart.key}-title`} className="min-w-0 rounded-xl border border-slate-300 bg-white shadow-sm" data-outcome-card={chart.key}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 p-5">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-[#145b6e]">{chart.specialty}</p>
          <h2 id={`${chart.key}-title`} className="mt-1 text-base font-semibold text-slate-800">{chart.title}</h2>
          <p className="mt-1 text-xs text-slate-500">{chart.range}</p>
        </div>
        <div role="group" aria-label={`${chart.specialty} chart type`} className="flex shrink-0 gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
          {(['line', 'bar'] as const).map(type => <button key={type} type="button" aria-pressed={chartType === type} onClick={() => setChartType(type)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#145b6e] ${chartType === type ? 'bg-[#145b6e] text-white shadow-sm' : 'text-slate-600 hover:bg-white hover:text-[#145b6e]'}`}>
            {type === 'line' ? 'Line' : 'Bar'}
          </button>)}
        </div>
      </div>
      <div className="p-4 sm:p-5">
        <p className={`mb-4 w-fit rounded-md border px-3 py-2 text-xs font-semibold leading-relaxed ${chart.badgeClass}`}>{chart.badge}</p>
        <div className="h-[250px] min-w-0" data-chart-type={chartType}>
          <ResponsiveContainer width="100%" height="100%">
            <Chart data={outcomes} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" tick={<TimelineTick />} interval={0} height={58} tickLine={false} axisLine={{ stroke: '#cbd5e1' }} padding={{ left: 24, right: 30 }} />
              <YAxis domain={[0, chart.maximum]} ticks={chart.ticks} width={44} tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #cbd5e1', fontSize: 12 }}
                labelFormatter={label => outcomes.find(point => point.time === label)?.label ?? label}
                formatter={value => [formatValue(chart.key, Number(value)), chart.title]} />
              {chart.key === 'berg' && <ReferenceLine y={45} stroke="#dc2626" strokeDasharray="6 4" strokeOpacity={0.65} />}
              {chartType === 'line'
                ? <Line dataKey={chart.key} name={chart.title} type={chart.key === 'baclofen' ? 'stepAfter' : 'linear'} stroke={chart.color} strokeWidth={3} connectNulls={true} dot={{ r: 5, fill: chart.color, stroke: '#ffffff', strokeWidth: 2 }} activeDot={{ r: 7 }} isAnimationActive={false} />
                : <Bar dataKey={chart.key} name={chart.title} fill={chart.color} maxBarSize={44} radius={[4, 4, 0, 0]} isAnimationActive={false} />}
            </Chart>
          </ResponsiveContainer>
        </div>
        <div className="sr-only"><table>
          <caption>{chart.specialty}: {chart.title}</caption>
          <thead><tr><th>Encounter</th><th>{chart.title}</th></tr></thead>
          <tbody>{outcomes.map(point => <tr key={point.time}><th>{point.label}</th><td>{formatValue(chart.key, point[chart.key])}</td></tr>)}</tbody>
        </table></div>
      </div>
    </section>
  );
}

function BrainMap() {
  return (
    <figure className="min-w-0">
      <div className="rounded-xl border border-slate-200 bg-[#f8fafc] p-4">
        <div className="flex justify-between text-[10px] font-semibold uppercase tracking-widest text-slate-500"><span>Territory schematic · Superior view</span><span>Anterior</span></div>
        <svg viewBox="0 0 360 260" role="img" aria-labelledby="mca-map-title mca-map-description" className="mx-auto h-[240px] w-full max-w-[380px]">
          <title id="mca-map-title">Left MCA Territory Infarction (Motor Cortex &amp; Basal Ganglia)</title>
          <desc id="mca-map-description">Anatomical schematic, not patient imaging. The left hemisphere is on the viewer's left. Red shading and a pulsing dot mark the left middle cerebral artery territory; the deeper basal ganglia and internal capsule are shown as an inset overlay.</desc>
          <defs>
            <radialGradient id="mca-lesion-glow"><stop offset="0%" stopColor="#ef4444" stopOpacity="0.6" /><stop offset="100%" stopColor="#ef4444" stopOpacity="0" /></radialGradient>
          </defs>
          <text x="77" y="22" fill="#145b6e" fontSize="12" fontWeight="700">LEFT</text>
          <text x="254" y="22" fill="#64748b" fontSize="12" fontWeight="700">RIGHT</text>
          <path d="M173 37 C151 24 115 28 95 43 C64 52 44 81 45 105 C26 130 35 158 47 177 C44 203 69 225 92 226 C112 244 147 237 169 222 C181 190 168 165 177 143 C169 110 182 69 173 37Z" fill="#dce8eb" stroke="#145b6e" strokeWidth="2.5" />
          <path d="M187 37 C209 24 245 28 265 43 C296 52 316 81 315 105 C334 130 325 158 313 177 C316 203 291 225 268 226 C248 244 213 237 191 222 C179 190 192 165 183 143 C191 110 178 69 187 37Z" fill="#e8eef2" stroke="#64748b" strokeWidth="2.5" />
          <path d="M95 52 C64 65 47 91 49 110 C32 135 43 161 54 180 C57 201 78 219 98 220 L127 191 L119 148 L133 108 L119 75Z" fill="#ef4444" fillOpacity="0.19" stroke="#ef4444" strokeOpacity="0.45" strokeWidth="1.5" />
          <g fill="none" stroke="#5d8691" strokeWidth="2" strokeLinecap="round">
            <path d="M147 48 Q114 44 105 69 Q77 66 69 91 M160 76 Q136 72 128 92 Q99 83 90 105 Q65 104 57 122 M156 108 Q146 130 125 130 Q101 117 89 138 Q65 133 54 151 M158 157 Q138 148 127 164 Q102 151 85 170 Q68 160 58 182 M154 194 Q133 179 117 196 Q96 184 81 207 M113 57 Q122 62 121 78 M71 91 Q82 85 90 96 M88 138 Q97 145 94 157 M127 164 Q136 173 132 185" />
            <path d="M213 48 Q246 44 255 69 Q283 66 291 91 M200 76 Q224 72 232 92 Q261 83 270 105 Q295 104 303 122 M204 108 Q214 130 235 130 Q259 117 271 138 Q295 133 306 151 M202 157 Q222 148 233 164 Q258 151 275 170 Q292 160 302 182 M206 194 Q227 179 243 196 Q264 184 279 207 M247 57 Q238 62 239 78 M289 91 Q278 85 270 96 M272 138 Q263 145 266 157 M233 164 Q224 173 228 185" />
          </g>
          <path d="M147 67 Q132 87 119 101 Q107 117 106 137" fill="none" stroke="#145b6e" strokeWidth="7" strokeLinecap="round" strokeOpacity="0.7" />
          <ellipse cx="143" cy="149" rx="16" ry="23" fill="#145b6e" fillOpacity="0.2" stroke="#145b6e" strokeDasharray="3 3" />
          <path d="M137 136 Q146 148 137 162" fill="none" stroke="#145b6e" strokeWidth="3" />
          <circle cx="82" cy="119" r="33" fill="url(#mca-lesion-glow)" />
          <circle cx="82" cy="119" r="14" fill="#ef4444" className="aria-mca-pulse" />
          <circle cx="82" cy="119" r="6.5" fill="#ef4444" stroke="#ffffff" strokeWidth="2.5" />
          <path d="M82 101 L73 68 L39 46" fill="none" stroke="#ef4444" strokeWidth="1.5" />
          <text x="5" y="42" fill="#b91c1c" fontSize="11" fontWeight="700">Left MCA</text>
          <text x="180" y="255" textAnchor="middle" fill="#64748b" fontSize="10">Posterior · Deep structures shown as overlay</text>
        </svg>
        <figcaption className="text-center text-sm font-semibold text-[#145b6e]">Left MCA Territory Infarction (Motor Cortex &amp; Basal Ganglia)</figcaption>
      </div>
      <dl className="mt-4 space-y-3 text-xs leading-relaxed">
        {[
          ['Left Motor Strip (Precentral Gyrus)', 'Right Hemiparesis (UE Stage 3, LE Stage 4)'],
          ['Left Basal Ganglia / Internal Capsule', 'Right Flexor Synergy & Tone (Elbow MAS Gr 2)'],
          ["Left Dominant Perisylvian / Broca’s Area", 'Mild Expressive Aphasia'],
        ].map(([area, finding]) => <div key={area} className="rounded-md border border-slate-200 bg-white px-3 py-2"><dt className="font-semibold text-slate-700">{area}</dt><dd className="mt-0.5 text-slate-600">→ {finding}</dd></div>)}
      </dl>
    </figure>
  );
}

function NeuroPrognosis() {
  return (
    <section aria-labelledby="neuro-prognosis-title" className="min-w-0 overflow-hidden rounded-xl border border-slate-300 bg-white shadow-sm">
      <h2 id="neuro-prognosis-title" className="border-b border-slate-200 px-5 py-4 text-lg font-semibold text-slate-800">Anatomical Localization of Injury &amp; Prognosis</h2>
      <div className="grid gap-6 p-5 lg:grid-cols-2 lg:gap-8">
        <BrainMap />
        <div className="flex flex-col justify-center gap-5">
          {[
            { number: '01', title: 'Motor & Language Trajectory', text: 'OT (FMA-UE 18 → 22/66) and SLP (WAB-R 64.2 → 71.8) show measured gains, supporting continued subacute rehabilitation potential at Week 12.' },
            { number: '02', title: 'Mobility Regression & Medication Review', text: 'PT gait (0.48 → 0.35 m/s) and balance (BBS 42 → 38/56) declined following the 10/06 Baclofen increase (5mg → 10mg TID). Sedation or weakness may contribute; reassess for other causes of decline.' },
            { number: '03', title: 'Prognosis & Team Action Plan', text: 'Goals remain limited community ambulation (≥0.40 m/s) and independent self-feeding. Coordinate MD medication review, a gradual taper if clinically appropriate, focal spasticity assessment, and a right AFO evaluation for swing-phase foot drop.' },
          ].map(item => <article key={item.number} className="flex gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#145b6e]/10 text-xs font-bold text-[#145b6e]">{item.number}</span>
            <div><h3 className="text-sm font-semibold text-slate-800">{item.title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{item.text}</p></div>
          </article>)}
        </div>
      </div>
    </section>
  );
}

export default function PatientBiometricsTab() {
  return (
    <div className="flex min-w-0 flex-col gap-6 py-4">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-slate-900"><img src={ariaLogo} alt="ARIA" className="h-11 w-11 shrink-0 rounded-xl" />Measures &amp; Trends</h1>
          <p className="mt-2 text-sm text-slate-600">Longitudinal Outcome Visualization · Ed Vance (12 Weeks Post-L MCA Stroke)</p>
        </div>
        <div className="self-start rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-sm">Ed Vance, 67M <span className="mx-2 text-slate-300">|</span> MRN #482910</div>
      </header>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2" data-outcome-grid>
        {charts.map(chart => <OutcomeCard key={chart.key} chart={chart} />)}
      </div>
      <NeuroPrognosis />
    </div>
  );
}
