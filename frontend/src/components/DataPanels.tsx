import { Area, Bar, CartesianGrid, ComposedChart, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ToolData } from '../types'

const AXIS = { stroke: '#f2f2f24d', fontSize: 11, tickLine: false, axisLine: false } as const
const TIP = {
  contentStyle: { background: '#141414f2', border: '1px solid #f2f2f233', borderRadius: 12, fontSize: 12, color: '#f2f2f2' },
  labelStyle: { color: '#f2f2f2cc' },
  cursor: { fill: '#f2f2f20a' },
}

function shortDate(d: string) {
  const dt = new Date(d + 'T00:00:00')
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export function Panel({ title, meta, children }: { title: string; meta?: string; children: React.ReactNode }) {
  return (
    <section className="frame">
      <div className="card flex h-full flex-col gap-4 p-5">
        <span className="glare" aria-hidden />
        <header className="flex items-baseline justify-between gap-3">
          <h3 className="text-[14px] font-medium text-ink">{title}</h3>
          {meta && <span className="truncate font-mono text-[10px] text-ink-3">{meta}</span>}
        </header>
        {children}
      </div>
    </section>
  )
}

export function Unavailable({ data }: { data?: ToolData }) {
  if (!data) return <p className="text-[13px] text-ink-3">Not fetched for this question. The agent decided it wasn't needed.</p>
  return (
    <div className="flex flex-col gap-1 text-[13px] leading-[19px] text-ink-3">
      <p className="text-moderate">Unavailable right now.</p>
      {data.notes.map((n, i) => (
        <p key={i}>{n}</p>
      ))}
    </div>
  )
}

export function ForecastPanel({ title, data }: { title: string; data?: ToolData }) {
  const rows = data?.series?.daily as any[] | undefined
  return (
    <Panel title={title} meta={data?.series?.provider ? `${data.series.provider}` : undefined}>
      {!rows?.length ? (
        <Unavailable data={data} />
      ) : (
        <div className="h-[220px]">
          <ResponsiveContainer>
            <ComposedChart data={rows.map((r) => ({ ...r, label: shortDate(r.date) }))} margin={{ top: 8, right: 0, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#f2f2f20f" vertical={false} />
              <XAxis dataKey="label" {...AXIS} interval={2} />
              <YAxis yAxisId="t" {...AXIS} width={48} allowDecimals={false} tickFormatter={(v: number) => `${Math.round(v)}°`} domain={[(min: number) => Math.floor(min - 2), (max: number) => Math.ceil(max + 2)]} />
              <YAxis yAxisId="r" orientation="right" {...AXIS} width={44} allowDecimals={false} tickFormatter={(v: number) => `${Math.round(v)}mm`} />
              <Tooltip {...TIP} />
              <Bar yAxisId="r" dataKey="rain" name="Rain (mm)" fill="#6fb3ff" fillOpacity={0.55} radius={[4, 4, 0, 0]} />
              <Area yAxisId="t" dataKey="tmax" name="Max °C" stroke="#ff9a6b" fill="#ff9a6b" fillOpacity={0.08} strokeWidth={1.6} dot={false} />
              <Line yAxisId="t" dataKey="tmin" name="Min °C" stroke="#f2f2f280" strokeWidth={1.2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  )
}

export function NdviPanel({ title, data }: { title: string; data?: ToolData }) {
  const scenes = (data?.series?.scenes as any[] | undefined) ?? []
  const clear = scenes.filter((s) => s.ndvi != null)
  const cloudy = scenes.length - clear.length
  return (
    <Panel title={title} meta={scenes.length ? `Sentinel-2 L2A · ${clear.length} clear · ${cloudy} cloudy` : undefined}>
      {!clear.length ? (
        <Unavailable data={data} />
      ) : (
        <div className="h-[220px]">
          <ResponsiveContainer>
            <LineChart data={clear.map((s) => ({ ...s, label: shortDate(s.date) }))} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="#f2f2f20f" vertical={false} />
              <ReferenceArea y1={0.6} y2={1} fill="#9fd67a" fillOpacity={0.06} />
              <ReferenceArea y1={0} y2={0.2} fill="#e9b44c" fillOpacity={0.05} />
              <XAxis dataKey="label" {...AXIS} />
              <YAxis {...AXIS} domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]} />
              <Tooltip {...TIP} formatter={(v: any) => [v, 'NDVI']} />
              <Line dataKey="ndvi" stroke="#9fd67a" strokeWidth={2} dot={{ r: 3, fill: '#9fd67a', strokeWidth: 0 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="text-[11px] leading-[16px] text-ink-3">Your field's own 10 m pixels. Above 0.6 is a dense, healthy canopy; below 0.2 is bare soil.</p>
    </Panel>
  )
}

export function MandiPanel({ title, data }: { title: string; data?: ToolData }) {
  const markets = (data?.series?.markets as any[] | undefined) ?? []
  return (
    <Panel title={title} meta={data?.series?.scope ? `Agmarknet · ${data.series.commodity} · ${data.series.scope}` : undefined}>
      {!markets.length ? (
        <Unavailable data={data} />
      ) : (
        <div className="max-h-[240px] overflow-auto">
          <table className="w-full table-fixed text-[13px] num">
            <thead className="sticky top-0 bg-[#1a1a1a] text-left text-[11px] tracking-[0.5px] text-ink-3 uppercase">
              <tr>
                <th className="w-[55%] py-2 font-normal">Market</th>
                <th className="py-2 text-right font-normal">₹ / quintal</th>
                <th className="w-12 py-2 text-right font-normal">km</th>
              </tr>
            </thead>
            <tbody>
              {markets.slice(0, 12).map((m, i) => (
                <tr key={m.market} className="border-t border-line">
                  <td className="py-2 pr-2">
                    <span className={`block truncate ${i === 0 ? 'text-ink' : 'text-ink-2'}`}>{m.market}</span>
                    <span className="block text-[11px] text-ink-3">{m.district} · {m.variety}</span>
                  </td>
                  <td className="py-2 text-right">
                    <span className={i === 0 ? 'text-accent' : 'text-ink'}>{Math.round(m.modal).toLocaleString('en-IN')}</span>
                    {m.min && m.max && (
                      <span className="block text-[11px] text-ink-3">
                        {Math.round(m.min).toLocaleString('en-IN')}–{Math.round(m.max).toLocaleString('en-IN')}
                      </span>
                    )}
                  </td>
                  <td className="py-2 text-right text-ink-3">{m.distance_km ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
