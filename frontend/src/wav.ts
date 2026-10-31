/** Re-encode any browser recording (WebM/Opus, MP4/AAC…) as 16 kHz mono WAV, which every speech model accepts. */
export async function toWav16k(blob: Blob): Promise<Blob> {
  const ctx = new AudioContext()
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer())
    const rate = 16000
    const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate)
    const src = offline.createBufferSource()
    src.buffer = decoded
    src.connect(offline.destination)
    src.start()
    const pcm = (await offline.startRendering()).getChannelData(0)
    const out = new DataView(new ArrayBuffer(44 + pcm.length * 2))
    const str = (o: number, s: string) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)))
    str(0, 'RIFF')
    out.setUint32(4, 36 + pcm.length * 2, true)
    str(8, 'WAVE')
    str(12, 'fmt ')
    out.setUint32(16, 16, true)
    out.setUint16(20, 1, true) // PCM
    out.setUint16(22, 1, true) // mono
    out.setUint32(24, rate, true)
    out.setUint32(28, rate * 2, true)
    out.setUint16(32, 2, true)
    out.setUint16(34, 16, true)
    str(36, 'data')
    out.setUint32(40, pcm.length * 2, true)
    pcm.forEach((v, i) => out.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 0x7fff, true))
    return new Blob([out], { type: 'audio/wav' })
  } finally {
    ctx.close()
  }
}
