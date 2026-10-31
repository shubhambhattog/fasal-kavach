import type { Profile, TraceEvent } from './types'

export class ApiError extends Error {
  code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

async function errorFrom(res: Response): Promise<ApiError> {
  try {
    const body = await res.json()
    if (body?.code) return new ApiError(body.code, body.message)
    if (Array.isArray(body?.detail)) {
      const d = body.detail[0]
      return new ApiError('validation', `${(d.loc || []).slice(-1)[0] ?? 'input'}: ${d.msg}`)
    }
  } catch {
    /* fall through */
  }
  return new ApiError('http', `Request failed (HTTP ${res.status})`)
}

export async function searchPlaces(q: string): Promise<{ name: string; lat: number; lon: number }[]> {
  const res = await fetch(`/api/geocode/search?q=${encodeURIComponent(q)}`)
  if (!res.ok) throw await errorFrom(res)
  return res.json()
}

export async function reverse(lat: number, lon: number): Promise<{ place: string; district: string; state: string; display_name: string }> {
  const res = await fetch(`/api/geocode/reverse?lat=${lat}&lon=${lon}`)
  if (!res.ok) throw await errorFrom(res)
  return res.json()
}

export async function crops(): Promise<{ key: string; names: Record<string, string> }[]> {
  const res = await fetch('/api/crops')
  if (!res.ok) throw await errorFrom(res)
  return res.json()
}

/** POST /api/advise and parse the SSE stream, calling onEvent for each event. */
export async function advise(profile: Profile, question: string, onEvent: (e: TraceEvent) => void, signal: AbortSignal) {
  const res = await fetch('/api/advise', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lat: profile.lat,
      lon: profile.lon,
      crop: profile.crop,
      sowing_date: profile.sowing_date || null,
      language: profile.language,
      question,
    }),
    signal,
  })
  if (!res.ok || !res.body) throw await errorFrom(res)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const data = chunk.split('\n').find((l) => l.startsWith('data: '))
      if (data) onEvent(JSON.parse(data.slice(6)))
    }
  }
}

export async function transcribe(blob: Blob, language: string): Promise<string> {
  const form = new FormData()
  form.append('audio', blob, 'voice.wav')
  form.append('language', language)
  const res = await fetch('/api/transcribe', { method: 'POST', body: form })
  if (!res.ok) throw await errorFrom(res)
  return (await res.json()).text
}

export async function speak(text: string, language: string): Promise<Blob> {
  const res = await fetch('/api/speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  })
  if (!res.ok) throw await errorFrom(res)
  return res.blob()
}

export interface NdviMap {
  date: string
  png: string
  corners: [number, number][]
  clear_fraction: number
  mean_ndvi: number | null
}

export async function ndviMap(lat: number, lon: number): Promise<NdviMap> {
  const res = await fetch(`/api/ndvi-map?lat=${lat}&lon=${lon}`)
  if (!res.ok) throw await errorFrom(res)
  return res.json()
}
