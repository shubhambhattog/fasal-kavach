"""Agent loop with a scripted fake model and fake tools: no network, no API cost."""

from datetime import date

import pytest
from google.genai import types

from app import agent, tools
from app.evidence import Field, ToolResult

from helpers import T0, f, weather_result

FIELD = Field(20.0868, 74.1278, "onion", date(2026, 9, 15), "en", "Niphad", "Nashik", "Maharashtra")


def call(name, args=None, cid=None):
    return types.Part(function_call=types.FunctionCall(name=name, args=args or {}, id=cid or name))


def response(*parts):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))])


GOOD = {
    "headline": "Irrigate this week", "summary": "Crop needs 19.3 mm of water this week.",
    "actions": [{"when": "this_week", "action": "Irrigate 19.3 mm in 2-3 turns", "why": "dry week", "evidence": ["calc.water_deficit_7d"]}],
    "risks": [{"type": "water_deficit", "level": "moderate", "evidence": ["calc.water_deficit_7d"]}],
    "data_gaps": [], "confidence": "medium",
}


@pytest.fixture
def fake_tools(monkeypatch):
    async def wx(ctx, **_):
        return weather_result(et0=3.0, rain=0.0)

    async def wb(ctx, **_):
        return ToolResult("get_water_balance", "ok", [], [f("calc.water_deficit_7d", 19.3, "mm")])

    async def down(ctx, **_):
        return ToolResult("get_crop_health", "unavailable", ["earth-search"], [], ["earth-search unavailable: timed out"])

    async def other(ctx, **_):
        return ToolResult("x", "ok", [], [])

    dispatch = {name: other for name in tools.DISPATCH}
    dispatch.update(get_weather_forecast=wx, get_water_balance=wb, get_crop_health=down)
    monkeypatch.setattr(tools, "DISPATCH", dispatch)
    monkeypatch.setattr(agent, "_log_run", lambda record: None)


def script(monkeypatch, responses):
    calls = []

    async def fake_generate(model, contents, config):
        calls.append(contents[-1])
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(agent, "_generate", fake_generate)
    return calls


async def collect(question="what to do this week?"):
    return [ev async for ev in agent.run(agent.Request(FIELD, question), T0)]


def kinds(events, kind):
    return [e for e in events if e["event"] == kind]


async def test_clean_pass(monkeypatch, fake_tools):
    script(monkeypatch, [response(call("get_weather_forecast"), call("get_water_balance")), response(call("submit_advisory", GOOD))])
    events = await collect()
    assert [e["tool"] for e in kinds(events, "tool_end")] == ["get_weather_forecast", "get_water_balance"]
    assert kinds(events, "gate")[0]["ok"] is True
    stats = kinds(events, "done")[0]["stats"]
    assert stats["first_pass"] is True and stats["fallback"] is False
    assert "calc.water_deficit_7d" in kinds(events, "advisory")[0]["sources"]


async def test_repair_after_ungrounded_number(monkeypatch, fake_tools):
    bad = GOOD | {"summary": "Crop needs 31 mm of water this week."}
    sent = script(monkeypatch, [response(call("get_water_balance")), response(call("submit_advisory", bad)), response(call("submit_advisory", GOOD))])
    events = await collect()
    gates = kinds(events, "gate")
    assert [g["ok"] for g in gates] == [False, True]
    assert gates[0]["problems"][0]["check"] == "number_grounding"
    # The model was shown the diff, not the engine's answer.
    repair_msg = sent[2].parts[-1].function_response.response
    assert repair_msg["ok"] is False and "31" in repair_msg["problems"][0]["detail"]
    assert kinds(events, "done")[0]["stats"]["repairs"] == 1


async def test_three_failures_ship_engine_fallback(monkeypatch, fake_tools):
    bad = GOOD | {"summary": "Crop needs 31 mm."}
    script(monkeypatch, [response(call("get_weather_forecast"))] + [response(call("submit_advisory", bad)) for _ in range(3)])
    events = await collect()
    adv = kinds(events, "advisory")[0]["advisory"]
    assert adv["fallback"] is True
    assert kinds(events, "done")[0]["stats"]["fallback"] is True


async def test_llm_down_still_answers_from_engine(monkeypatch, fake_tools):
    script(monkeypatch, [agent.LLMUnavailable("model quota reached")])
    events = await collect()
    assert kinds(events, "llm_error")[0]["message"] == "model quota reached"
    assert {e["tool"] for e in kinds(events, "tool_end")} >= {"get_weather_forecast", "get_crop_health"}
    adv = kinds(events, "advisory")[0]["advisory"]
    assert adv["fallback"] and "get_crop_health unavailable" in adv["data_gaps"]


async def test_unavailable_tool_must_be_disclosed(monkeypatch, fake_tools):
    script(monkeypatch, [response(call("get_crop_health"), call("get_water_balance")), response(call("submit_advisory", GOOD)),
                         response(call("submit_advisory", GOOD | {"data_gaps": ["Satellite view unavailable today"]}))])
    events = await collect()
    assert [g["ok"] for g in kinds(events, "gate")] == [False, True]


async def test_tool_budget_forces_submission(monkeypatch, fake_tools):
    monkeypatch.setattr(agent.settings, "max_tool_calls", 2)
    seen_configs = []

    async def fake_generate(model, contents, config):
        seen_configs.append(config.tool_config.function_calling_config.allowed_function_names)
        if len(seen_configs) == 1:
            return response(call("get_weather_forecast"), call("get_water_balance"))
        return response(call("submit_advisory", GOOD))

    monkeypatch.setattr(agent, "_generate", fake_generate)
    await collect()
    assert seen_configs == [None, ["submit_advisory"]]
