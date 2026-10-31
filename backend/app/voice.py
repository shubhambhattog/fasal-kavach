"""Speech in and out through Gemini: one key, good Indic quality, free tier.
The browser falls back to its own speech synthesis if `/api/speak` fails."""

import asyncio
import io
import wave

from google.genai import types

from .agent import LANGUAGES, LLMUnavailable, client
from .config import settings

VOICE = "Kore"


async def transcribe(audio: bytes, mime: str, language: str) -> str:
    lang = LANGUAGES.get(language, "the speaker's language")
    prompt = (f"Transcribe this farmer's voice note exactly, in {lang} using its native script. "
              "Return only the transcript text, with no notes. If there is no speech, return an empty string.")
    audio_part = types.Part.from_bytes(data=audio, mime_type=mime)
    last: Exception | None = None
    # 1. The dedicated speech model returns an `audio_transcription` part, not text.
    try:
        resp = await asyncio.wait_for(client().aio.models.generate_content(model=settings.transcribe_model, contents=[audio_part]), timeout=30)
        parts = resp.candidates[0].content.parts or []
        text = " ".join(p.audio_transcription.text for p in parts if p.audio_transcription and p.audio_transcription.text).strip()
        if text:
            return text
    except Exception as e:
        last = e
    # 2. Fallback: a general model asked to transcribe.
    try:
        resp = await asyncio.wait_for(client().aio.models.generate_content(model=settings.cheap_model, contents=[audio_part, prompt]), timeout=30)
        return (resp.text or "").strip()
    except Exception as e:
        last = e
    raise LLMUnavailable(f"transcription failed ({type(last).__name__})")


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


async def speak(text: str, language: str) -> bytes:
    try:
        resp = await asyncio.wait_for(client().aio.models.generate_content(
            model=settings.tts_model,
            # Only the advice text: the TTS model reads instruction prefixes aloud (found in testing).
            contents=text[:1500],
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE))),
            )), timeout=45)
        part = resp.candidates[0].content.parts[0]
        data = part.inline_data.data
        mime = part.inline_data.mime_type or ""
    except Exception as e:
        raise LLMUnavailable(f"speech synthesis failed ({type(e).__name__})")
    if "wav" in mime:
        return data
    rate = 24000
    if "rate=" in mime:
        try:
            rate = int(mime.split("rate=")[1].split(";")[0])
        except ValueError:
            pass
    return pcm_to_wav(data, rate)
