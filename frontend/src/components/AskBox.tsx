import { useRef, useState } from 'react'
import { transcribe } from '../api'
import { t } from '../i18n'
import { toWav16k } from '../wav'

interface Props {
  language: string
  busy: boolean
  disabled: string | null
  onAsk: (question: string) => void
  onStop: () => void
}

export function AskBox({ language, busy, disabled, onAsk, onStop }: Props) {
  const s = t(language)
  const [text, setText] = useState('')
  const [rec, setRec] = useState<'idle' | 'recording' | 'transcribing'>('idle')
  const [micError, setMicError] = useState('')
  const recorder = useRef<MediaRecorder | null>(null)

  async function toggleMic() {
    setMicError('')
    if (rec === 'recording') {
      recorder.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const chunks: BlobPart[] = []
      const mr = new MediaRecorder(stream)
      mr.ondataavailable = (e) => chunks.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop())
        setRec('transcribing')
        try {
          const wav = await toWav16k(new Blob(chunks, { type: mr.mimeType || 'audio/webm' }))
          const said = await transcribe(wav, language)
          if (said) {
            setText(said)
            if (!busy && !disabled) onAsk(said)
          } else setMicError('No speech heard. Try again, closer to the mic.')
        } catch (err: any) {
          setMicError(err.message)
        } finally {
          setRec('idle')
        }
      }
      recorder.current = mr
      mr.start()
      setRec('recording')
    } catch {
      setMicError('Microphone permission is blocked. Allow it in the browser, or type your question.')
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (text.trim().length >= 2 && !busy && !disabled) onAsk(text.trim())
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label htmlFor="q" className="text-[12px] tracking-[1px] text-ink-3 uppercase">
        {s.ask}
      </label>
      <div className="flex gap-2">
        <textarea
          id="q"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) submit(e)
          }}
          rows={2}
          maxLength={800}
          placeholder={rec === 'recording' ? s.listening : rec === 'transcribing' ? s.transcribing : s.askPlaceholder}
          className="min-h-[56px] flex-1 resize-none rounded-[12px] border border-line bg-fill px-4 py-3 text-[15px] leading-[22px] text-ink placeholder:text-ink-3 outline-none transition-colors duration-300 focus:border-ink-4"
        />
        <button
          type="button"
          onClick={toggleMic}
          disabled={rec === 'transcribing'}
          aria-label={rec === 'recording' ? s.listening : 'Speak your question'}
          className={`relative grid h-[56px] w-[56px] shrink-0 place-items-center rounded-[12px] border transition-colors duration-300 active:scale-[.98] ${
            rec === 'recording' ? 'border-high/60 bg-high/15 text-high' : 'border-line bg-fill text-ink-2 hover:text-ink'
          }`}
        >
          {rec === 'recording' && <span aria-hidden className="absolute inset-0 rounded-[12px] border border-high/50" style={{ animation: 'pulse-ring 1.4s var(--ease-quart) infinite' }} />}
          {rec === 'transcribing' ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-ink-4 border-t-ink" />
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
            </svg>
          )}
        </button>
      </div>
      {micError && <p className="text-[13px] text-moderate">{micError}</p>}
      <div className="flex flex-wrap gap-2">
        {s.examples.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setText(ex)}
            className="rounded-full border border-line px-3 py-1.5 text-[12px] text-ink-3 transition-colors duration-300 hover:border-line-2 hover:text-ink-2"
          >
            {ex}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-3">
        {busy ? (
          <button type="button" onClick={onStop} className="h-11 rounded-[12px] border border-line-2 px-5 text-[14px] text-ink-2 hover:text-ink active:scale-[.98]">
            {s.stop}
          </button>
        ) : (
          <button
            type="submit"
            disabled={!!disabled || text.trim().length < 2}
            className="h-11 rounded-[12px] bg-ink px-5 text-[14px] font-medium text-[#101010] transition-opacity duration-300 hover:opacity-90 active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {s.send}
          </button>
        )}
        {disabled && !busy && <span className="text-[13px] text-ink-3">{disabled}</span>}
      </div>
    </form>
  )
}
