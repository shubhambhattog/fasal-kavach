import { TOOL_LABELS } from '../i18n'
import type { TraceEvent } from '../types'

const STATUS_COLOR = { ok: 'text-accent', partial: 'text-moderate', unavailable: 'text-high' } as const

const CHECK_LABELS: Record<string, string> = {
  number_grounding: 'ungrounded number',
  citations: 'bad citation',
  risk_agreement: 'risk mismatch',
  data_gaps: 'undisclosed gap',
  safety: 'dosage given',
  language: 'wrong language',
  schema: 'format',
}

interface Row {
  key: string
  kind: 'tool' | 'thought' | 'gate' | 'error' | 'start'
  ev: TraceEvent
  end?: Extract<TraceEvent, { event: 'tool_end' }>
}

function rows(events: TraceEvent[]): Row[] {
  const out: Row[] = []
  const open = new Map<string, Row>()
  events.forEach((ev, i) => {
    if (ev.event === 'tool_start') {
      const r: Row = { key: `t${i}`, kind: 'tool', ev }
      open.set(`${ev.tool}:${ev.id}`, r)
      out.push(r)
    } else if (ev.event === 'tool_end') {
      const r = open.get(`${ev.tool}:${ev.id}`)
      if (r) r.end = ev
    } else if (ev.event === 'thought') out.push({ key: `th${i}`, kind: 'thought', ev })
    else if (ev.event === 'gate') out.push({ key: `g${i}`, kind: 'gate', ev })
    else if (ev.event === 'llm_error' || ev.event === 'error') out.push({ key: `e${i}`, kind: 'error', ev })
    else if (ev.event === 'start') out.push({ key: `s${i}`, kind: 'start', ev })
  })
  return out
}

export function Trace({ events, busy }: { events: TraceEvent[]; busy: boolean }) {
  const done = events.find((e) => e.event === 'done') as Extract<TraceEvent, { event: 'done' }> | undefined
  const list = rows(events)
  return (
    <div className="flex flex-col">
      <ol className="flex flex-col gap-1.5 font-mono text-[12px] leading-[18px]">
        {list.map((r, idx) => (
          <li key={r.key} className="enter-rise flex gap-3" style={{ ['--rise' as any]: '8px', ['--dur' as any]: '.5s' }}>
            <span className="w-4 shrink-0 text-right text-ink-4 num">{idx + 1}</span>
            <TraceRow row={r} />
          </li>
        ))}
      </ol>
      {busy && (
        <p className="mt-3 pl-7 font-mono text-[12px]">
          <span className="shimmer-text">{events.some((e) => e.event === 'gate') ? 'checking and repairing…' : 'investigating…'}</span>
        </p>
      )}
      {done && (
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-line pt-3 pl-7 font-mono text-[11px] text-ink-3 num">
          <span>{done.stats.model}</span>
          <span>{done.stats.tool_calls} tool calls</span>
          <span>{done.stats.submissions} submission{done.stats.submissions === 1 ? '' : 's'}</span>
          <span>{done.stats.repairs} repair{done.stats.repairs === 1 ? '' : 's'}</span>
          <span>{done.stats.latency_s}s</span>
          {done.stats.fallback && <span className="text-moderate">engine fallback</span>}
        </div>
      )}
    </div>
  )
}

function TraceRow({ row }: { row: Row }) {
  const ev = row.ev
  if (ev.event === 'start') {
    const st = ev.stage
    return (
      <span className="text-ink-3">
        field locked · {ev.field.place || 'pin'} {ev.field.district && `· ${ev.field.district}`} · {ev.field.crop}
        {st ? ` · day ${st.das}, ${st.stage}` : ''}
      </span>
    )
  }
  if (ev.event === 'thought') {
    const firstLine = ev.text.replace(/\*\*/g, '').split('\n').find((l) => l.trim()) ?? ''
    return (
      <details className="group min-w-0 flex-1 text-ink-3">
        <summary className="cursor-pointer list-none truncate italic hover:text-ink-2">
          <span className="not-italic text-ink-4">thinking · </span>
          {firstLine}
        </summary>
        <p className="mt-1 whitespace-pre-wrap font-sans text-[12px] text-ink-3">{ev.text.replace(/\*\*/g, '')}</p>
      </details>
    )
  }
  if (ev.event === 'tool_start') {
    const end = row.end
    return (
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${end ? STATUS_COLOR[end.status] + ' bg-current dot-glow' : 'bg-ink-4 animate-pulse'}`} />
          <span className="text-ink">{TOOL_LABELS[ev.tool] ?? ev.tool}</span>
          {ev.fallback && <span className="text-moderate">(engine)</span>}
          {end && <span className="text-ink-4 num">{end.ms ? `${(end.ms / 1000).toFixed(1)}s` : ''}</span>}
          {end && <span className={`${STATUS_COLOR[end.status]}`}>{end.status}</span>}
        </div>
        {end && (
          <div className="truncate pl-3.5 text-ink-3" title={end.notes.join(' ')}>
            {end.providers.join(' → ')}
            {end.n_facts ? ` · ${end.n_facts} facts` : ''}
            {end.status !== 'ok' && end.notes[0] ? ` · ${end.notes[0]}` : ''}
          </div>
        )}
      </div>
    )
  }
  if (ev.event === 'gate') {
    return (
      <div className="min-w-0 flex-1">
        <span className={ev.ok ? 'text-accent' : 'text-moderate'}>
          gate check #{ev.attempt}: {ev.ok ? 'passed — every number grounded, risks agree with the engine' : `${ev.problems.length} problem${ev.problems.length > 1 ? 's' : ''} → sent back to the model`}
        </span>
        {!ev.ok &&
          ev.problems.map((p, i) => (
            <div key={i} className="pl-3.5 text-ink-3">
              <span className="text-moderate">{CHECK_LABELS[p.check] ?? p.check}</span> · {p.detail}
            </div>
          ))}
      </div>
    )
  }
  if (ev.event === 'llm_error' || ev.event === 'error') {
    return <span className="text-moderate">model unavailable ({ev.message}); the engine writes the advice from the same live data</span>
  }
  return null
}
