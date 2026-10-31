import { useRef, useState } from 'react'
import { speak } from '../api'
import { riskLabel, SPEECH_LANG, t } from '../i18n'
import type { Advisory, Fact, Level, Signal } from '../types'
import { SourceChip } from './SourceChip'

const LEVEL_STYLE: Record<Level, string> = {
  low: 'border-line text-ink-3',
  moderate: 'border-moderate/40 text-moderate bg-moderate/10',
  high: 'border-high/50 text-high bg-high/10',
}

interface Props {
  advisory: Advisory
  signals: Signal[]
  sources: Record<string, Fact>
  language: string
}

export function AdvisoryCard({ advisory, signals, sources, language }: Props) {
  const s = t(language)
  const [audio, setAudio] = useState<'idle' | 'loading' | 'playing'>('idle')
  const player = useRef<HTMLAudioElement | null>(null)

  const spoken = [advisory.headline, advisory.summary, ...advisory.actions.map((a) => a.action), advisory.market_advice || ''].join('. ')

  async function listen() {
    if (audio === 'playing') {
      player.current?.pause()
      window.speechSynthesis?.cancel()
      setAudio('idle')
      return
    }
    setAudio('loading')
    try {
      const blob = await speak(spoken, language)
      const a = new Audio(URL.createObjectURL(blob))
      player.current = a
      a.onended = () => setAudio('idle')
      await a.play()
      setAudio('playing')
    } catch {
      // Gemini TTS unavailable: use the browser's own voice.
      if ('speechSynthesis' in window) {
        const u = new SpeechSynthesisUtterance(spoken)
        u.lang = SPEECH_LANG[language] ?? 'en-IN'
        u.rate = 0.95
        u.onend = () => setAudio('idle')
        window.speechSynthesis.speak(u)
        setAudio('playing')
      } else setAudio('idle')
    }
  }

  const risks = [...advisory.risks].sort((a, b) => ['high', 'moderate', 'low'].indexOf(a.level) - ['high', 'moderate', 'low'].indexOf(b.level))

  return (
    <article className="flex flex-col gap-6">
      {advisory.fallback && (
        <p className="rounded-[12px] border border-moderate/30 bg-moderate/10 px-4 py-3 text-[13px] leading-[19px] text-moderate">
          Written by the rule engine from the same live data, because {advisory.fallback_reason}. Every value is still sourced.
        </p>
      )}
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h2
            className={
              /^[\x00-\x7F₹°–—’‘“”…]*$/.test(advisory.headline)
                ? 'font-serif text-[30px] leading-[1.1] tracking-[-0.5px] text-ink italic sm:text-[36px]'
                : 'text-[24px] leading-[1.35] font-medium text-ink sm:text-[28px]' /* no fake italics on Indic scripts */
            }
          >
            {advisory.headline}
          </h2>
          <p className="max-w-[65ch] text-[15px] leading-[24px] text-ink-2">{advisory.summary}</p>
        </div>
        <button
          onClick={listen}
          aria-label={s.speak}
          className="flex h-11 shrink-0 items-center gap-2 rounded-full border border-line-2 px-4 text-[13px] text-ink-2 transition-colors duration-300 hover:text-ink active:scale-[.98]"
        >
          {audio === 'loading' ? (
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-4 border-t-ink" />
          ) : audio === 'playing' ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden><path d="M11 5 6 9H3v6h3l5 4V5zM15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" /></svg>
          )}
          {s.speak}
        </button>
      </header>

      <ol className="flex flex-col gap-3">
        {advisory.actions.map((a, i) => (
          <li key={i} className="enter-rise rounded-[14px] border border-line bg-fill p-4" style={{ ['--delay' as any]: `${0.08 * i}s`, ['--rise' as any]: '12px' }}>
            <div className="flex flex-col gap-1.5 sm:flex-row sm:gap-4">
              <span className="w-[108px] shrink-0 pt-0.5 text-[11px] tracking-[1px] text-accent uppercase">{s.when[a.when] ?? a.when}</span>
              <div className="flex min-w-0 flex-col gap-2">
                <p className="text-[16px] leading-[24px] text-ink">{a.action}</p>
                <p className="text-[13px] leading-[20px] text-ink-3">{a.why}</p>
                <div className="flex flex-wrap gap-1.5">
                  {a.evidence.map((id) => (
                    <SourceChip key={id} id={id} fact={sources[id]} />
                  ))}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ol>

      {advisory.market_advice && (
        <div className="flex flex-col gap-2 rounded-[14px] border border-line p-4">
          <span className="text-[11px] tracking-[1px] text-ink-3 uppercase">{riskLabel('market', language)}</span>
          <p className="text-[15px] leading-[23px] text-ink-2">{advisory.market_advice}</p>
          <div className="flex flex-wrap gap-1.5">
            {(advisory.market_evidence || []).map((id) => (
              <SourceChip key={id} id={id} fact={sources[id]} />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <span className="text-[11px] tracking-[1px] text-ink-3 uppercase">{s.risks}</span>
        <div className="flex flex-wrap gap-2">
          {risks.map((r) => {
            const sig = signals.find((x) => x.type === r.type)
            return (
              <span key={r.type} title={sig ? `${sig.detail}\nThreshold: ${sig.threshold_source}` : undefined} className={`rounded-full border px-3 py-1.5 text-[12px] ${LEVEL_STYLE[r.level]}`}>
                {riskLabel(r.type, language)} · {s.level[r.level]}
              </span>
            )
          })}
          <span className="rounded-full border border-line px-3 py-1.5 text-[12px] text-ink-3">
            {s.confidence}: {advisory.confidence}
          </span>
        </div>
      </div>

      {advisory.data_gaps.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-[11px] tracking-[1px] text-ink-3 uppercase">{s.gaps}</span>
          <ul className="flex flex-col gap-1 text-[13px] leading-[19px] text-ink-3">
            {advisory.data_gaps.map((g, i) => (
              <li key={i}>— {g}</li>
            ))}
          </ul>
        </div>
      )}
    </article>
  )
}
