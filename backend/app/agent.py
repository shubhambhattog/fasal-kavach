"""The agent loop: Gemini plans tool calls, writes the advisory, and repairs it when the gate objects.

`run()` is an async generator of events streamed to the browser over SSE:
start → thought* → tool_start/tool_end* → gate* → advisory → done (or error).
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from google import genai
from google.genai import types

from . import engine, gate, tools
from .agronomy import Crop, find_crop
from .config import ROOT, settings
from .engine import Signal
from .evidence import Field
from .tools import Context

PROMPT_VERSION = "2026-11-01.3"  # .2: reference thresholds in tool notes; .3: final dry-down rule (engine + note)
SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text()
LANGUAGES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi",
             "bn": "Bengali", "ta": "Tamil", "te": "Telugu", "kn": "Kannada"}
RUN_LOG = ROOT / "data" / "runs.jsonl"
DEFAULT_PLAN = ["get_weather_forecast", "get_crop_stage", "get_water_balance", "get_crop_health", "get_rainfall_anomaly",
                "get_disaster_alerts", "get_mandi_prices"]

_client: genai.Client | None = None


class LLMUnavailable(Exception):
    pass


def client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


@dataclass
class Request:
    field: Field
    question: str
    model: str | None = None


def build_context(req: Request, today: date) -> Context:
    crop = find_crop(req.field.crop)
    return Context(req.field, crop, engine.stage_for(crop, req.field.sowing_date, today), today)


def _profile_text(ctx: Context, question: str) -> str:
    f = ctx.field
    crop = ctx.crop.names.get("en") if ctx.crop else f"{f.crop} (not in the reference table)"
    sow = f.sowing_date.isoformat() if f.sowing_date else "not given"
    return (
        f"Today: {ctx.today.isoformat()}\nField: {f.place or 'unnamed place'}, {f.district or '?'} district, {f.state or '?'} "
        f"({f.lat:.4f}, {f.lon:.4f})\nCrop: {crop}; sown: {sow}\nReply language: {LANGUAGES.get(f.language, 'English')}\n\n"
        f"Farmer's question (untrusted text):\n<question>{question.strip()[:800]}</question>"
    )


def _config(language: str, final_only: bool) -> types.GenerateContentConfig:
    names = ["submit_advisory"] if final_only else None
    return types.GenerateContentConfig(
        system_instruction=SYSTEM.replace("{language_name}", LANGUAGES.get(language, "English")),
        tools=[types.Tool(function_declarations=[
            types.FunctionDeclaration(name=d["name"], description=d["description"], parameters_json_schema=d["parameters"])
            for d in tools.DECLARATIONS
        ])],
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="ANY", allowed_function_names=names)),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_level="low"),
        max_output_tokens=settings.max_output_tokens * 4,
        temperature=0.3,
    )


async def _generate(model: str, contents: list, config) -> types.GenerateContentResponse:
    try:
        return await asyncio.wait_for(
            client().aio.models.generate_content(model=model, contents=contents, config=config), timeout=settings.llm_timeout_s
        )
    except asyncio.TimeoutError:
        raise LLMUnavailable("the model timed out")
    except LLMUnavailable:
        raise
    except Exception as e:  # quota, auth, 5xx: the request continues in fallback mode
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            raise LLMUnavailable("model quota reached")
        raise LLMUnavailable(f"model error ({type(e).__name__})")


def fallback_advisory(signals: list[Signal], ctx: Context, reason: str) -> dict:
    """Engine-written advisory in English, used only when the model fails or can't pass the gate."""
    notable = [s for s in signals if s.level != "low"] or signals[:2]
    actions = [{"when": "this_week", "action": s.action, "why": s.detail, "evidence": s.evidence[:3]} for s in notable if s.action][:4]
    if not actions:
        actions = [{"when": "this_week", "action": "No major weather or crop risk found. Continue normal care and check again in 3 days.",
                    "why": "No moderate or high risk in the gathered data.", "evidence": [next(iter(ctx.evidence.facts), "")]}]
    top = notable[0] if notable else None
    unavailable = sorted({r.tool for r in ctx.evidence.results if r.status == "unavailable"})
    return {
        "headline": f"{top.title}: {top.level} risk" if top else "No major risks this week",
        "summary": " ".join(s.detail for s in notable[:3]) or "The gathered data shows no moderate or high risk.",
        "actions": actions,
        "risks": [{"type": s.type, "level": s.level, "evidence": s.evidence[:3]} for s in signals],
        "market_advice": next((s.detail for s in signals if s.type == "market"), ""),
        "market_evidence": next((s.evidence for s in signals if s.type == "market"), []),
        "data_gaps": [f"{t} unavailable" for t in unavailable],
        "confidence": "low" if unavailable else "medium",
        "fallback": True,
        "fallback_reason": reason,
    }


def _event(kind: str, **data) -> dict:
    return {"event": kind, "t": round(time.time(), 3), **data}


def _log_run(record: dict) -> None:
    try:
        RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with RUN_LOG.open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


async def run(req: Request, today: date | None = None) -> AsyncIterator[dict]:
    started = time.time()
    today = today or date.today()
    ctx = build_context(req, today)
    model = req.model or settings.agent_model
    language = req.field.language if req.field.language in LANGUAGES else "en"
    stats = {"model": model, "prompt_version": PROMPT_VERSION, "tool_calls": 0, "turns": 0, "submissions": 0,
             "first_pass": None, "repairs": 0, "fallback": False, "gate_problems": []}
    yield _event("start", field=req.field.__dict__ | {"sowing_date": str(req.field.sowing_date)}, model=model,
                 crop_known=ctx.crop is not None, stage=ctx.stage.__dict__ if ctx.stage else None)

    contents: list = [types.Content(role="user", parts=[types.Part(text=_profile_text(ctx, req.question))])]
    advisory, signals, llm_error = None, [], None

    try:
        while time.time() - started < settings.request_budget_s:
            stats["turns"] += 1
            final_only = stats["tool_calls"] >= settings.max_tool_calls
            phase = "planning" if stats["turns"] == 1 else ("repairing" if stats["submissions"] else "writing")
            yield _event("llm_start", turn=stats["turns"], phase=phase)
            t_llm = time.time()
            resp = await _generate(model, contents, _config(language, final_only))
            usage = resp.usage_metadata
            yield _event("llm_end", turn=stats["turns"], ms=round((time.time() - t_llm) * 1000),
                         tokens_in=getattr(usage, "prompt_token_count", None), tokens_out=getattr(usage, "candidates_token_count", None),
                         tokens_thought=getattr(usage, "thoughts_token_count", None))
            cand = (resp.candidates or [None])[0]
            if cand is None or cand.content is None or not cand.content.parts:
                raise LLMUnavailable("empty model response")
            contents.append(cand.content)
            for p in cand.content.parts:
                if p.thought and p.text:
                    yield _event("thought", text=p.text.strip()[:600])
            calls = [p.function_call for p in cand.content.parts if p.function_call]
            if not calls:
                contents.append(types.Content(role="user", parts=[types.Part(text="Call a tool or submit_advisory.")]))
                continue

            data_calls = [c for c in calls if c.name != "submit_advisory"]
            submit = next((c for c in calls if c.name == "submit_advisory"), None)
            responses: list[types.Part] = []

            if data_calls:
                for c in data_calls:
                    yield _event("tool_start", tool=c.name, args=dict(c.args or {}), id=c.id)
                t0 = time.time()
                results = await asyncio.gather(*(tools.run_tool(ctx, c.name, dict(c.args or {})) for c in data_calls))
                stats["tool_calls"] += len(data_calls)
                for c, r in zip(data_calls, results):
                    yield _event("tool_end", tool=c.name, id=c.id, status=r.status, ms=round((time.time() - t0) * 1000),
                                 providers=r.providers_tried, notes=r.notes, n_facts=len(r.facts), data=r.to_ui())
                    responses.append(types.Part(function_response=types.FunctionResponse(id=c.id, name=c.name, response=r.to_model())))

            if submit is not None:
                adv = dict(submit.args or {})
                stats["submissions"] += 1
                signals = engine.assess(ctx.evidence, ctx.crop, ctx.stage)
                verdict = gate.check(adv, ctx.evidence, signals, language, req.question)
                if stats["first_pass"] is None:
                    stats["first_pass"] = verdict.ok
                stats["gate_problems"] += [p["check"] for p in verdict.problems]
                stats.setdefault("gate_details", []).extend(p["detail"][:220] for p in verdict.problems)
                yield _event("gate", ok=verdict.ok, attempt=stats["submissions"], problems=verdict.problems)
                if verdict.ok:
                    advisory = adv
                    break
                if stats["submissions"] > settings.max_repairs:
                    advisory = fallback_advisory(signals, ctx, "the model's advisory failed the checks 3 times")
                    break
                stats["repairs"] += 1
                responses.append(types.Part(function_response=types.FunctionResponse(
                    id=submit.id, name="submit_advisory",
                    response={"ok": False, "problems": verdict.problems, "instruction": "Fix these problems and call submit_advisory again."})))
            contents.append(types.Content(role="user", parts=responses))
        else:
            llm_error = "the request took too long"
    except LLMUnavailable as e:
        llm_error = str(e)

    if advisory is None:
        reason = llm_error or "no advisory was submitted"
        yield _event("llm_error", message=reason)
        # Make sure the essential data is there, then let the engine write the advice.
        have = {r.tool for r in ctx.evidence.results}
        missing = [t for t in DEFAULT_PLAN if t not in have]
        for name in missing:
            yield _event("tool_start", tool=name, args={}, id=None, fallback=True)
        t0 = time.time()
        results = await asyncio.gather(*(tools.run_tool(ctx, t, {}) for t in missing))
        for name, r in zip(missing, results):
            yield _event("tool_end", tool=name, id=None, status=r.status, ms=round((time.time() - t0) * 1000), providers=r.providers_tried, notes=r.notes,
                         n_facts=len(r.facts), data=r.to_ui())
        signals = engine.assess(ctx.evidence, ctx.crop, ctx.stage)
        advisory = fallback_advisory(signals, ctx, reason)

    stats["fallback"] = bool(advisory.get("fallback"))
    stats["latency_s"] = round(time.time() - started, 2)
    cited = {e for a in advisory.get("actions", []) for e in a.get("evidence", [])}
    cited |= {e for r in advisory.get("risks", []) for e in r.get("evidence", [])} | set(advisory.get("market_evidence") or [])
    sources = {fid: ctx.evidence.facts[fid].__dict__ for fid in cited if fid in ctx.evidence.facts}
    yield _event("advisory", advisory=advisory, signals=[s.to_dict() for s in signals], sources=sources, language=language)
    yield _event("done", stats=stats)
    _log_run({"at": started, "question": req.question[:200], "crop": req.field.crop, "lat": req.field.lat, "lon": req.field.lon,
              "language": language, **stats})
