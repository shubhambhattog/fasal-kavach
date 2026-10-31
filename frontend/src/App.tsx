import { useEffect, useMemo, useRef, useState } from 'react'
import { advise, crops as fetchCrops, reverse } from './api'
import { AdvisoryCard } from './components/AdvisoryCard'
import { AskBox } from './components/AskBox'
import { ForecastPanel, MandiPanel, NdviPanel } from './components/DataPanels'
import { FieldMap } from './components/FieldMap'
import { FieldsPanel, type Watched } from './components/FieldsPanel'
import { Trace } from './components/Trace'
import { LANGUAGES, t } from './i18n'
import type { Profile, ToolData, TraceEvent } from './types'

const STORE = 'fasal-kavach.profile.v1'
const EMPTY: Profile = { lat: null, lon: null, place: '', crop: 'onion', sowing_date: '', language: 'en' }

function loadProfile(): Profile {
  try {
    return { ...EMPTY, ...JSON.parse(localStorage.getItem(STORE) || '{}') }
  } catch {
    return EMPTY
  }
}

const today = new Date().toISOString().slice(0, 10)

export default function App() {
  const [profile, setProfile] = useState<Profile>(loadProfile)
  const [cropList, setCropList] = useState<{ key: string; names: Record<string, string> }[]>([])
  const [placeError, setPlaceError] = useState('')
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [busy, setBusy] = useState(false)
  const [runError, setRunError] = useState('')
  const abort = useRef<AbortController | null>(null)
  const s = t(profile.language)

  useEffect(() => localStorage.setItem(STORE, JSON.stringify(profile)), [profile])
  useEffect(() => {
    fetchCrops().then(setCropList).catch(() => setCropList([]))
  }, [])

  async function pick(lat: number, lon: number) {
    setPlaceError('')
    setProfile((p) => ({ ...p, lat, lon, place: '' }))
    try {
      const r = await reverse(lat, lon)
      setProfile((p) => ({ ...p, place: [r.place, r.district, r.state].filter(Boolean).join(', ') }))
    } catch (err: any) {
      setPlaceError(err.message)
    }
  }

  function openWatched(f: Watched) {
    setEvents([])
    setPlaceError('')
    setProfile((p) => ({ ...p, lat: f.lat, lon: f.lon, crop: f.crop, sowing_date: f.sowing_date, place: f.label }))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function ask(question: string) {
    abort.current?.abort()
    const ctl = new AbortController()
    abort.current = ctl
    setEvents([])
    setRunError('')
    setBusy(true)
    try {
      await advise(profile, question, (e) => setEvents((prev) => [...prev, e]), ctl.signal)
    } catch (err: any) {
      if (err.name !== 'AbortError') setRunError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const toolData = useMemo(() => {
    const m: Record<string, ToolData> = {}
    for (const e of events) if (e.event === 'tool_end' && e.data) m[e.tool] = e.data
    return m
  }, [events])
  const result = events.find((e) => e.event === 'advisory') as Extract<TraceEvent, { event: 'advisory' }> | undefined
  const streamError = events.find((e) => e.event === 'error') as Extract<TraceEvent, { event: 'error' }> | undefined

  const blocked = profile.lat == null ? s.dropPin : placeError ? placeError : null

  return (
    <div className="relative min-h-svh">
      <div className="grain" aria-hidden />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] bg-[radial-gradient(ellipse_55%_70%_at_50%_0,#f2f2f214,#0000)]" aria-hidden />

      <div className="relative mx-auto flex max-w-[1280px] flex-col gap-8 px-4 pt-6 pb-16 sm:px-6 lg:pt-10">
        <header className="enter-rise flex flex-wrap items-end justify-between gap-4" style={{ ['--rise' as any]: '24px' }}>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
                <path d="M16 5c5.5 3.2 8.5 7.5 8.5 12.5a8.5 8.5 0 0 1-17 0C7.5 12.5 10.5 8.2 16 5z" fill="none" stroke="#9fd67a" strokeWidth="1.8" />
                <path d="M16 11v16" stroke="#9fd67a" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
              <h1 className="text-[28px] leading-none font-medium tracking-[-0.8px] sm:text-[34px]">
                Fasal <span className="font-serif font-normal italic">Kavach</span>
              </h1>
            </div>
            <p className="max-w-[60ch] text-[14px] leading-[20px] text-ink-3">{s.tagline}</p>
          </div>
          <label className="flex items-center gap-2 text-[12px] text-ink-3">
            {s.language}
            <select
              value={profile.language}
              onChange={(e) => setProfile((p) => ({ ...p, language: e.target.value }))}
              className="h-10 rounded-[10px] border border-line-2 bg-fill px-3 text-[14px] text-ink outline-none"
            >
              {Object.entries(LANGUAGES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        </header>

        <main className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <section className="frame enter-rise self-start" style={{ ['--delay' as any]: '.1s', ['--rise' as any]: '40px' }}>
            <div className="card flex flex-col gap-0">
              <span className="glare" aria-hidden />
              <div className="h-[340px] p-2 sm:h-[400px]">
                <FieldMap autoNdvi={!!toolData.get_crop_health && toolData.get_crop_health.status !== 'unavailable'} lat={profile.lat} lon={profile.lon} placeholder={s.searchPlaceholder} hint={s.dropPin} onPick={pick} />
              </div>
              <div className="flex flex-col gap-4 p-5 pt-3">
                <div className="flex min-h-[20px] items-center gap-2 text-[13px]">
                  <span className="shrink-0 text-ink-3">{s.field}:</span>
                  {placeError ? (
                    <span className="text-moderate">{placeError}</span>
                  ) : profile.lat != null ? (
                    <span className="truncate text-ink-2">
                      {profile.place || '…'} <span className="font-mono text-[11px] text-ink-4 num">{profile.lat.toFixed(4)}, {profile.lon!.toFixed(4)}</span>
                    </span>
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex flex-col gap-1.5 text-[12px] text-ink-3">
                    {s.crop}
                    <select
                      value={profile.crop}
                      onChange={(e) => setProfile((p) => ({ ...p, crop: e.target.value }))}
                      className="h-11 rounded-[10px] border border-line bg-fill px-3 text-[14px] text-ink outline-none focus:border-ink-4"
                    >
                      {(cropList.length ? cropList : [{ key: profile.crop, names: { en: profile.crop } }]).map((c) => (
                        <option key={c.key} value={c.key}>
                          {c.names[profile.language] ?? c.names.en}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5 text-[12px] text-ink-3">
                    {s.sown}
                    <input
                      type="date"
                      max={today}
                      value={profile.sowing_date}
                      onChange={(e) => setProfile((p) => ({ ...p, sowing_date: e.target.value }))}
                      className="h-11 rounded-[10px] border border-line bg-fill px-3 text-[14px] text-ink outline-none focus:border-ink-4"
                    />
                  </label>
                </div>
              </div>
            </div>
          </section>

          <section className="flex min-w-0 flex-col gap-6">
            <div className="frame enter-rise" style={{ ['--delay' as any]: '.2s', ['--rise' as any]: '40px' }}>
              <div className="card p-5">
                <span className="glare" aria-hidden />
                <AskBox language={profile.language} busy={busy} disabled={blocked} onAsk={ask} onStop={() => abort.current?.abort()} />
              </div>
            </div>

            {(events.length > 0 || runError) && (
              <div className="frame enter-rise" style={{ ['--rise' as any]: '24px' }}>
                <div className="card flex flex-col gap-3 p-5">
                  <span className="glare" aria-hidden />
                  <h2 className="text-[12px] tracking-[1px] text-ink-3 uppercase">{s.agent}</h2>
                  {runError ? <p className="text-[14px] text-moderate">{runError}</p> : <Trace events={events} busy={busy} />}
                  {streamError && <p className="text-[14px] text-moderate">{streamError.message}. Please try again.</p>}
                </div>
              </div>
            )}

            {result ? (
              <div className="frame enter-rise" style={{ ['--rise' as any]: '32px' }}>
                <div className="card p-5 sm:p-7">
                  <span className="glare" aria-hidden />
                  <AdvisoryCard advisory={result.advisory} signals={result.signals} sources={result.sources} language={result.language} />
                </div>
              </div>
            ) : (
              !events.length && (
                <div className="grid gap-3 px-1 sm:grid-cols-3">
                  {s.steps.map(([h, d], i) => [String(i + 1), h, d]).map(([n, h, d]) => (
                    <div key={n} className="flex flex-col gap-1">
                      <span className="font-mono text-[11px] text-ink-4">{n}</span>
                      <span className="text-[14px] text-ink-2">{h}</span>
                      <span className="text-[13px] leading-[19px] text-ink-3">{d}</span>
                    </div>
                  ))}
                </div>
              )
            )}
          </section>
        </main>

        {events.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            <ForecastPanel title={s.forecast} data={toolData.get_weather_forecast} />
            <NdviPanel title={s.ndvi} data={toolData.get_crop_health} />
            <MandiPanel title={s.mandi} data={toolData.get_mandi_prices} />
          </div>
        )}

        <FieldsPanel profile={profile} onOpen={openWatched} />

        <footer className="flex flex-wrap justify-between gap-3 border-t border-line pt-6 text-[12px] leading-[18px] text-ink-3">
          <span>Live data: Open-Meteo · MET Norway · NASA POWER · ESA Sentinel-2 · ISRIC SoilGrids · data.gov.in Agmarknet · GDACS · OpenStreetMap</span>
          <span>Advice, not a guarantee. For chemical doses, follow the label or ask your KVK.</span>
        </footer>
      </div>
    </div>
  )
}
