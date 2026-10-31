import { useEffect, useState } from 'react'
import { RISK_LABELS } from '../i18n'
import type { Level, Profile, Signal } from '../types'
import { Panel } from './DataPanels'

const STORE = 'fasal-kavach.fields.v1'
const RANK: Record<Level, number> = { high: 2, moderate: 1, low: 0 }

export interface Watched {
  id: string
  label: string
  lat: number
  lon: number
  crop: string
  sowing_date: string
  scan?: { signals: Signal[]; unavailable: string[]; checked_at: number; error?: string }
}

function load(): Watched[] {
  try {
    return JSON.parse(localStorage.getItem(STORE) || '[]')
  } catch {
    return []
  }
}

async function scan(f: Watched): Promise<Watched['scan']> {
  try {
    const res = await fetch('/api/risk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat: f.lat, lon: f.lon, crop: f.crop, sowing_date: f.sowing_date || null }),
    })
    if (!res.ok) throw new Error((await res.json()).message ?? `HTTP ${res.status}`)
    return await res.json()
  } catch (err: any) {
    return { signals: [], unavailable: [], checked_at: Date.now() / 1000, error: err.message }
  }
}

function worst(f: Watched): number {
  return Math.max(-1, ...(f.scan?.signals ?? []).filter((s) => s.type !== 'market').map((s) => RANK[s.level]))
}

/** Several fields (a family's plots, or an FPO's members), each checked by the rule engine on live data. No LLM, so it's cheap. */
export function FieldsPanel({ profile, onOpen }: { profile: Profile; onOpen: (f: Watched) => void }) {
  const [fields, setFields] = useState<Watched[]>(load)
  const [checking, setChecking] = useState(false)
  useEffect(() => localStorage.setItem(STORE, JSON.stringify(fields)), [fields])

  const current = profile.lat != null ? fields.find((f) => Math.abs(f.lat - profile.lat!) < 1e-4 && Math.abs(f.lon - profile.lon!) < 1e-4) : undefined

  async function checkAll(list = fields) {
    setChecking(true)
    for (const f of list) {
      const result = await scan(f)
      setFields((prev) => prev.map((x) => (x.id === f.id ? { ...x, scan: result } : x)))
    }
    setChecking(false)
  }

  async function watch() {
    if (profile.lat == null || profile.lon == null || current) return
    const f: Watched = {
      id: `${Date.now()}`,
      label: profile.place.split(',')[0] || `${profile.lat.toFixed(3)}, ${profile.lon.toFixed(3)}`,
      lat: profile.lat,
      lon: profile.lon,
      crop: profile.crop,
      sowing_date: profile.sowing_date,
    }
    setFields((prev) => [...prev, f])
    checkAll([f])
  }

  const sorted = [...fields].sort((a, b) => worst(b) - worst(a))

  return (
    <Panel title="My fields: weekly risk watch" meta="rule engine on live data · no AI cost">
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={watch}
          disabled={profile.lat == null || !!current}
          className="h-9 rounded-full border border-line-2 px-4 text-[12px] text-ink-2 transition-colors duration-300 hover:text-ink active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {current ? 'This field is watched' : '+ Watch this field'}
        </button>
        {fields.length > 0 && (
          <button onClick={() => checkAll()} disabled={checking} className="h-9 rounded-full border border-line px-4 text-[12px] text-ink-3 hover:text-ink-2 disabled:opacity-40">
            {checking ? <span className="shimmer-text">Checking fields…</span> : 'Check all now'}
          </button>
        )}
      </div>
      {fields.length === 0 ? (
        <p className="text-[13px] leading-[19px] text-ink-3">
          Save the fields you look after: your own plots, or every member of an FPO. Each one is checked against the week's forecast, its own satellite view and disaster alerts, and sorted with the riskiest first.
        </p>
      ) : (
        <ul className="flex flex-col">
          {sorted.map((f) => {
            const notable = (f.scan?.signals ?? []).filter((s) => s.level !== 'low' && s.type !== 'market')
            return (
              <li key={f.id} className="flex items-start justify-between gap-3 border-t border-line py-3">
                <button onClick={() => onOpen(f)} className="min-w-0 text-left">
                  <span className="block truncate text-[14px] text-ink hover:underline">{f.label}</span>
                  <span className="block text-[11px] text-ink-3">
                    {f.crop}
                    {f.sowing_date ? ` · sown ${f.sowing_date}` : ''}
                    {f.scan && !f.scan.error ? ` · checked ${new Date(f.scan.checked_at * 1000).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}` : ''}
                  </span>
                  {f.scan?.error && <span className="block text-[11px] text-moderate">{f.scan.error}</span>}
                </button>
                <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                  {!f.scan ? (
                    <span className="skeleton h-6 w-20" />
                  ) : notable.length ? (
                    notable.slice(0, 3).map((s) => (
                      <span key={s.type} title={s.detail} className={`rounded-full border px-2.5 py-1 text-[11px] ${s.level === 'high' ? 'border-high/50 bg-high/10 text-high' : 'border-moderate/40 bg-moderate/10 text-moderate'}`}>
                        {RISK_LABELS[s.type] ?? s.type}
                      </span>
                    ))
                  ) : (
                    !f.scan.error && <span className="rounded-full border border-line px-2.5 py-1 text-[11px] text-ink-3">No major risk</span>
                  )}
                  <button aria-label={`Remove ${f.label}`} onClick={() => setFields((prev) => prev.filter((x) => x.id !== f.id))} className="grid h-6 w-6 place-items-center rounded-full text-ink-4 hover:text-ink-2">
                    ×
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
