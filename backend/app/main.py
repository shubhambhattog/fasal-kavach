"""HTTP API and static frontend."""

import json
from datetime import date, timedelta

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field as PField

from . import agent, voice
from .agent import LANGUAGES, LLMUnavailable
from .agronomy import CROPS, find_crop
from .config import settings
from .evidence import Field
from .http import SourceError
from .sources import geo

app = FastAPI(title="Fasal Kavach", version="0.1.0")


class AdviseIn(BaseModel):
    lat: float = PField(ge=-90, le=90)
    lon: float = PField(ge=-180, le=180)
    crop: str = PField(min_length=2, max_length=40)
    sowing_date: date | None = None
    language: str = "en"
    question: str = PField(min_length=2, max_length=800)


class SpeakIn(BaseModel):
    text: str = PField(min_length=1, max_length=1500)
    language: str = "en"


def problem(status: int, code: str, message: str):
    raise HTTPException(status, {"code": code, "message": message})


@app.get("/api/health")
async def health():
    return {"ok": True, "model": settings.agent_model, "llm_configured": bool(settings.gemini_api_key)}


@app.get("/api/crops")
async def crops():
    return [{"key": c.key, "names": c.names, "season_days": sum(c.stages)} for c in CROPS.values()]


@app.get("/api/languages")
async def languages():
    return LANGUAGES


@app.get("/api/geocode/search")
async def geocode_search(q: str):
    if len(q.strip()) < 2:
        return []
    try:
        return await geo.search(q.strip()[:120])
    except SourceError as e:
        problem(503, "geocoder_unavailable", f"Place search is unavailable ({e.message}). Drop a pin on the map instead.")


@app.get("/api/geocode/reverse")
async def geocode_reverse(lat: float, lon: float):
    return await _locate(lat, lon)


async def _locate(lat: float, lon: float) -> dict:
    if not geo.in_india_bbox(lat, lon):
        problem(422, "outside_india", "This point is outside India. Fasal Kavach covers Indian farmland only.")
    try:
        place = await geo.reverse(lat, lon)
    except SourceError as e:
        if "no address" in e.message:
            problem(422, "not_land", "There's no land address here (sea, lake or unmapped). Move the pin onto your field.")
        # Geocoder down: carry on without place names; mandi search will report it can't run.
        return {"place": "", "district": "", "state": "", "country_code": "in", "display_name": "", "warning": e.message}
    if place.get("country_code") != "in":
        problem(422, "outside_india", "This point is outside India. Fasal Kavach covers Indian farmland only.")
    return place


@app.post("/api/advise")
async def advise(body: AdviseIn):
    today = date.today()
    if body.sowing_date and body.sowing_date > today:
        problem(422, "future_sowing", "The sowing date is in the future. Enter the date the crop was actually sown.")
    if body.sowing_date and body.sowing_date < today - timedelta(days=550):
        problem(422, "old_sowing", "That sowing date is more than 18 months ago. Enter the current crop's sowing date.")
    if body.language not in LANGUAGES:
        problem(422, "language", f"Supported languages: {', '.join(LANGUAGES)}")
    place = await _locate(body.lat, body.lon)
    crop = find_crop(body.crop)
    field = Field(body.lat, body.lon, crop.key if crop else body.crop.strip().lower(), body.sowing_date, body.language,
                  place.get("place", ""), place.get("district", ""), place.get("state", ""))
    req = agent.Request(field, body.question)

    async def stream():
        try:
            async for ev in agent.run(req, today):
                yield f"event: {ev['event']}\ndata: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
        except Exception as e:  # last-resort guard: the browser always gets a terminal event
            yield f"event: error\ndata: {json.dumps({'event': 'error', 'message': f'internal error ({type(e).__name__})'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("en")):
    data = await audio.read()
    if len(data) < 1000:
        problem(422, "too_short", "The recording is too short. Hold the mic button and speak.")
    if len(data) > 8_000_000:
        problem(413, "too_long", "The recording is too long. Keep it under a minute.")
    try:
        text = await voice.transcribe(data, (audio.content_type or "audio/webm").split(";")[0], language)
    except LLMUnavailable as e:
        problem(503, "stt_unavailable", f"Voice input is unavailable right now ({e}). Please type your question.")
    return {"text": text}


@app.post("/api/speak")
async def speak(body: SpeakIn):
    try:
        wav = await voice.speak(body.text, body.language)
    except LLMUnavailable as e:
        problem(503, "tts_unavailable", str(e))
    return Response(wav, media_type="audio/wav")


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
    return JSONResponse(detail, status_code=exc.status_code)


dist = settings.frontend_dist
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        target = dist / path
        if path and target.is_file() and dist in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(dist / "index.html")
