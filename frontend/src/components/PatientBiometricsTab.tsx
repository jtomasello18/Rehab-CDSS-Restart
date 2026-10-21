import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, Label, ReferenceLine,
} from 'recharts';
import ariaLogo from '../assets/aria-logo.svg';

type ChartType = 'line' | 'bar' | 'pie';
type ChartKind = 'mobility' | 'recovery';
type SeriesKey = 'berg' | 'gait' | 'pt' | 'ot' | 'slp';
type Series = { key: SeriesKey; name: string; color: string; axis: 'left' | 'right' };

// Six-point case series supplied for this outcome visualization. The discipline
// indices are descriptive case values, not a validated composite outcome scale.
const outcomeData = [
  { time: 'Wk 4', phase: 'Inpatient', fullLabel: 'Wk 4 (Inpatient)', berg: 26, gait: 0.20, pt: 46, ot: 18, slp: 48 },
  { time: 'Wk 6', phase: 'Inpatient', fullLabel: 'Wk 6 (Inpatient)', berg: 32, gait: 0.30, pt: 57, ot: 21, slp: 54 },
  { time: 'Wk 8', phase: 'Inpatient', fullLabel: 'Wk 8 (Inpatient)', berg: 38, gait: 0.40, pt: 68, ot: 24, slp: 60 },
  { time: '09/29', phase: 'Wk 10 · IRF discharge', fullLabel: '09/29 (Wk 10 · IRF Discharge)', berg: 42, gait: 0.48, pt: 75, ot: 27, slp: 64 },
  { time: '10/06', phase: 'Wk 11 · MD visit', fullLabel: '10/06 (Wk 11 · Baclofen 10mg TID)', berg: 40, gait: 0.41, pt: 71, ot: 30, slp: 68 },
  { time: '10/13', phase: 'Wk 12 · Outpatient', fullLabel: '10/13 (Wk 12 · Outpatient Eval)', berg: 38, gait: 0.35, pt: 68, ot: 33, slp: 72 },
];
const seriesByKind: Record<ChartKind, Series[]> = {
  mobility: [
    { key: 'berg', name: 'Berg Balance Scale', color: '#145b6e', axis: 'left' },
    { key: 'gait', name: '10MWT Gait Velocity', color: '#2563eb', axis: 'right' },
  ],
  recovery: [
    { key: 'pt', name: 'PT Mobility Index (Berg/10MWT)', color: '#145b6e', axis: 'left' },
    { key: 'ot', name: 'OT Upper Extremity (FMA-UE / ADL)', color: '#b45309', axis: 'left' },
    { key: 'slp', name: 'SLP Language Recovery (WAB-R / BNT)', color: '#2563eb', axis: 'left' },
  ],
};
const latest = outcomeData[outcomeData.length - 1];
const chartTitles: Record<ChartKind, string> = {
  mobility: 'Mobility & Fall-Risk Trajectory (PT Standardized Outcomes)',
  recovery: 'Multidisciplinary Functional Recovery (PT · OT · SLP Outcome Index)',
};
const chartSubtitles: Record<ChartKind, string> = {
  mobility: 'Tracks Berg Balance Scale (0–56) and 10-Meter Walk Test Velocity (m/s) from Inpatient Rehab (Wk 4) through Outpatient Eval (Wk 12). Note the functional regression following the 10/06 Baclofen increase (5mg → 10mg TID).',
  recovery: 'Standardized outcome progression across Physical Therapy (Berg/Gait), Occupational Therapy (FMA-UE Motor), and Speech-Language Pathology (WAB-R / Naming Accuracy) normalized to % of functional target.',
};
const tooltipStyle = { borderRadius: 8, border: '1px solid #cbd5e1', fontSize: 13, boxShadow: '0 4px 12px rgb(15 23 42 / 0.08)' };
const formatValue = (key: SeriesKey, value: number) => key === 'gait' ? `${value.toFixed(2)} m/s` : key === 'berg' ? `${value}/56` : `${value}%`;

function ChartToggle({ value, onChange, title }: { value: ChartType; onChange: (value: ChartType) => void; title: string }) {
  return (
    <div role="group" aria-label={`${title} chart type`} className="flex shrink-0 gap-1 rounded-lg border border-slate-300 bg-slate-50 p-1">
      {(['line', 'bar', 'pie'] as const).map(type => (
        <button key={type} type="button" aria-pressed={value === type} onClick={() => onChange(type)}
          className={`rounded-md px-4 py-2 text-xs font-semibold capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#145b6e] ${value === type ? 'bg-[#145b6e] text-white shadow-sm' : 'text-slate-600 hover:bg-white hover:text-[#145b6e]'}`}>
          {type === 'line' ? 'Line' : type === 'bar' ? 'Bar' : 'Pie'}
        </button>
      ))}
    </div>
  );
}

function TimelineTick({ x, y, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  const point = outcomeData.find(item => item.time === payload?.value);
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fill="#334155" fontSize={12} fontWeight={600} y={16}>{point?.time}</text>
      <text textAnchor="middle" fill="#64748b" fontSize={10} y={33}>{point?.phase}</text>
    </g>
  );
}

function OutcomeTrajectory({ kind, chartType }: { kind: ChartKind; chartType: 'line' | 'bar' }) {
  const Chart = chartType === 'bar' ? BarChart : LineChart;
  const mobility = kind === 'mobility';
  return (
    <div className="overflow-x-auto" tabIndex={0} aria-label={`${chartTitles[kind]} timeline; scroll horizontally on small screens`}>
      <div className="h-[340px] min-w-[680px]">
        <ResponsiveContainer width="100%" height="100%">
          <Chart data={outcomeData} margin={{ top: 14, right: mobility ? 28 : 44, left: 22, bottom: 10 }} barGap={6}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="time" tick={<TimelineTick />} interval={0} height={58} tickLine={false} axisLine={{ stroke: '#cbd5e1' }} padding={{ left: 24, right: 24 }} />
            <YAxis yAxisId="left" domain={[0, mobility ? 56 : 100]} ticks={mobility ? [0, 14, 28, 42, 56] : [0, 25, 50, 75, 100]} tick={{ fontSize: 12, fill: '#145b6e' }} tickLine={false} axisLine={false} width={48}
              tickFormatter={value => mobility ? String(value) : `${value}%`}
              label={{ value: mobility ? 'Berg Balance (points)' : 'Functional target (%)', angle: -90, position: 'insideLeft', dx: -12, style: { fill: '#145b6e', fontSize: 12 } }} />
            {mobility && <YAxis yAxisId="right" orientation="right" domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]} tickFormatter={value => value.toFixed(1)} tick={{ fontSize: 12, fill: '#2563eb' }} tickLine={false} axisLine={false} width={48}
              label={{ value: 'Gait velocity (m/s)', angle: 90, position: 'insideRight', dx: 16, style: { fill: '#2563eb', fontSize: 12 } }} />}
            <Tooltip contentStyle={tooltipStyle} labelFormatter={label => outcomeData.find(item => item.time === label)?.fullLabel ?? label}
              formatter={(value, name, item) => [formatValue(item.dataKey as SeriesKey, Number(value)), name]} />
            {mobility && <ReferenceLine yAxisId="left" y={45} stroke="#145b6e" strokeDasharray="6 5" strokeOpacity={0.45} />}
            {mobility && <ReferenceLine yAxisId="right" y={0.4} stroke="#2563eb" strokeDasharray="6 5" strokeOpacity={0.45} />}
            <ReferenceLine yAxisId="left" x="10/06" stroke="#94a3b8" strokeDasharray="3 4" />
            {seriesByKind[kind].map(series => chartType === 'bar'
              ? <Bar key={series.key} yAxisId={series.axis} dataKey={series.key} name={series.name} fill={series.color} maxBarSize={36} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              : <Line key={series.key} yAxisId={series.axis} dataKey={series.key} name={series.name} type="linear" stroke={series.color} strokeWidth={3} connectNulls={true} dot={{ r: 5, fill: series.color, stroke: '#ffffff', strokeWidth: 2 }} activeDot={{ r: 7 }} isAnimationActive={false} />)}
          </Chart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MobilityPies() {
  // Keep unlike units separate. A combined BBS/gait pie would imply that points
  // and metres/second can be added. Both rings use the trajectory axis ranges.
  return (
    <div className="grid min-h-[340px] grid-cols-1 gap-4 sm:grid-cols-2">
      {seriesByKind.mobility.map(series => {
        const maximum = series.key === 'berg' ? 56 : 1;
        const slices = [{ name: series.name, value: latest[series.key] }, { name: 'Remaining plotting range', value: maximum - latest[series.key] }];
        return (
          <div key={series.key} className="flex flex-col items-center justify-center rounded-lg bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-700">{series.name} · 10/13</p>
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={slices} dataKey="value" nameKey="name" innerRadius={60} outerRadius={85} strokeWidth={0} isAnimationActive={false}>
                    <Cell fill={series.color} /><Cell fill="#e2e8f0" />
                    <Label value={formatValue(series.key, latest[series.key])} position="center" fill={series.color} fontSize={20} fontWeight={600} />
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} formatter={value => series.key === 'gait' ? `${Number(value).toFixed(2)} m/s` : `${value} points`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <p className="text-center text-xs text-slate-500">{series.key === 'berg' ? 'High fall risk · score below 45/56' : 'Household ambulation · below 0.40 m/s'}</p>
            <p className="mt-1 text-center text-xs text-slate-500">{series.key === 'berg' ? '0–56 point scale' : '0–1.0 m/s plotting range'}</p>
          </div>
        );
      })}
    </div>
  );
}

function RecoveryPie() {
  const slices = seriesByKind.recovery.map(series => ({ name: series.name, value: latest[series.key], color: series.color }));
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  return (
    <div className="flex h-[340px] flex-col">
      <p className="text-center text-xs text-slate-500">10/13 current index breakdown · slices show relative shares of the three displayed indices, not therapy dose.</p>
      <div className="min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={slices} dataKey="value" nameKey="name" innerRadius={65} outerRadius={110} paddingAngle={3} isAnimationActive={false}>
              {slices.map(slice => <Cell key={slice.name} fill={slice.color} />)}
              <Label value="10/13" position="center" fill="#334155" fontSize={20} fontWeight={600} />
            </Pie>
            <Tooltip contentStyle={tooltipStyle} formatter={value => [`${value}% of target · ${(Number(value) / total * 100).toFixed(1)}% of displayed total`, 'Current index']} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ChartCard({ kind }: { kind: ChartKind }) {
  const [chartType, setChartType] = useState<ChartType>('line');
  const mobility = kind === 'mobility';
  const notes = { pt: 'Regressing · BBS 38/56, 10MWT 0.35 m/s', ot: 'Slow proximal gain · FMA-UE 22/66, elbow MAS Gr 2', slp: 'Progressing · 20-min fatigue window' };
  return (
    <section aria-labelledby={`${kind}-title`} className="min-w-0 rounded-xl border border-slate-300 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 p-5">
        <div className="min-w-0 flex-1 basis-[540px]">
          <h2 id={`${kind}-title`} className="text-lg font-semibold text-slate-800">{chartTitles[kind]}</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{chartSubtitles[kind]}</p>
        </div>
        <ChartToggle value={chartType} onChange={setChartType} title={chartTitles[kind]} />
      </div>
      <div className="space-y-4 p-4 sm:p-5" data-chart-kind={kind} data-chart-type={chartType}>
        {mobility && <div className="flex flex-wrap gap-2 text-xs font-medium">
          <span className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-[#145b6e]">Berg cutoff: 45/56 · Scores &lt;45 = High Fall Risk</span>
          <a href="https://pubmed.ncbi.nlm.nih.gov/17510461/" target="_blank" rel="noreferrer" className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-blue-700">Limited-community boundary: 0.40 m/s · &lt;0.40 m/s = Household Only</a>
        </div>}
        {chartType === 'pie' ? mobility ? <MobilityPies /> : <RecoveryPie /> : <OutcomeTrajectory kind={kind} chartType={chartType} />}
        <div className={`grid gap-3 ${mobility ? 'sm:grid-cols-2' : 'lg:grid-cols-3'}`} aria-label="Current outcome legend">
          {seriesByKind[kind].map(series => <div key={series.key} className="flex items-start gap-2 text-sm text-slate-600">
            <span aria-hidden="true" className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: series.color }} />
            <div><span className="font-medium text-slate-700">{series.name}: {formatValue(series.key, latest[series.key])}</span>
              {!mobility && <p className="mt-0.5 text-xs">{notes[series.key as keyof typeof notes]}</p>}
            </div>
          </div>)}
        </div>
        {mobility ? <p className="rounded-lg border border-[#c9dfe5] bg-[#f0f7f9] px-4 py-3 text-sm leading-relaxed text-[#145b6e]">
          <strong>10/06 Event: Oral Baclofen doubled (5mg → 10mg TID).</strong> From IRF discharge to outpatient evaluation, Berg dropped 4 points (42 → 38) and gait velocity declined 0.13 m/s (0.48 → 0.35 m/s). The regression may be correlated with titration.
        </p> : <p className="text-xs leading-relaxed text-slate-500">Case visualization: supplied six-point trajectories; discipline indices are descriptive percentages of functional target, not a validated composite score.</p>}
        <div className="sr-only"><table>
          <caption>{chartTitles[kind]} — six-point case series</caption>
          <thead><tr><th>Encounter</th>{seriesByKind[kind].map(series => <th key={series.key}>{series.name}</th>)}</tr></thead>
          <tbody>{outcomeData.map(point => <tr key={point.time}><th>{point.fullLabel}</th>{seriesByKind[kind].map(series => <td key={series.key}>{formatValue(series.key, point[series.key])}</td>)}</tr>)}</tbody>
        </table></div>
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
      <ChartCard kind="mobility" />
      <ChartCard kind="recovery" />
    </div>
  );
}
