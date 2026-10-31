import { useEffect, useRef, useState } from 'react'
import type { Fact } from '../types'

function ago(ts: number) {
  const s = Math.max(0, Date.now() / 1000 - ts)
  if (s < 90) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}

export function fmtValue(f: Fact) {
  if (typeof f.value === 'number') {
    const v = Math.abs(f.value) >= 100 ? Math.round(f.value).toLocaleString('en-IN') : String(Math.round(f.value * 100) / 100)
    return `${v}${f.unit && !['scenes', 'alerts', 'markets'].includes(f.unit) ? ' ' + f.unit : ''}`
  }
  return String(f.value)
}

/** A cited fact: click to see the raw value, its provider and when it was fetched. */
export function SourceChip({ id, fact }: { id: string; fact?: Fact }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', esc)
    }
  }, [open])
  const short = fact ? fmtValue(fact) : id
  return (
    <span ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-line bg-fill px-2.5 py-1 font-mono text-[11px] text-ink-2 transition-colors duration-200 hover:border-line-2 hover:text-ink"
      >
        <span className="h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />
        <span className="truncate num">{short}</span>
      </button>
      {open && (
        <span className="enter-rise absolute bottom-full left-0 z-30 mb-2 block w-[290px] rounded-[12px] border border-line-2 bg-[#141414f2] p-3 text-left shadow-[0_20px_50px_#000a] backdrop-blur-[20px]" style={{ ['--rise' as any]: '6px', ['--dur' as any]: '.3s' }}>
          {fact ? (
            <>
              <span className="block text-[13px] leading-[18px] text-ink">{fact.label}</span>
              <span className="mt-1 block font-mono text-[15px] text-ink num">{fmtValue(fact)}</span>
              <span className="mt-2 block font-mono text-[10px] leading-[15px] text-ink-3">
                {fact.provider} · fetched {ago(fact.fetched_at)}
                <br />
                id {fact.id}
              </span>
              {fact.url.startsWith('http') && (
                <a href={fact.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-[11px] text-ink-2 underline decoration-ink-4 underline-offset-2 hover:text-ink">
                  Open source request ↗
                </a>
              )}
            </>
          ) : (
            <span className="font-mono text-[11px] text-ink-3">{id}</span>
          )}
        </span>
      )}
    </span>
  )
}
