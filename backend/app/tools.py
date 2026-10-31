"""Tools the agent can call. All are read-only; `submit_advisory` is terminal and goes to the gate.

Location and crop come from the request context, never from model arguments, so the model can
only ever query the farmer's own field.
"""

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from . import engine
from .agronomy import FAO56, STAGE_NAMES, Crop, StageInfo
from .evidence import EvidenceStore, Fact, Field, ToolResult
from .sources import climate, disasters, mandi, satellite, soil, weather


@dataclass
class Context:
    field: Field
    crop: Crop | None
    stage: StageInfo | None
    today: date
    evidence: EvidenceStore = field(default_factory=EvidenceStore)


def _calc_fact(fid: str, label: str, value: float | str, unit: str) -> Fact:
    return Fact(fid, label, value, unit, "Fasal Kavach calculator (FAO-56)", "https://www.fao.org/4/x0490e/x0490e00.htm", time.time())


async def get_crop_stage(ctx: Context, **_) -> ToolResult:
    if ctx.crop is None:
        return ToolResult("get_crop_stage", "unavailable", ["agronomy table"], [], ["Crop not in the reference table; stage-specific advice isn't possible."])
    if ctx.stage is None:
        return ToolResult("get_crop_stage", "unavailable", ["agronomy table"], [_calc_fact("crop.heat_threshold", "Heat damage threshold at flowering", ctx.crop.heat_c, "°C")],
                          ["Sowing date not given, so the growth stage is unknown."])
    s, c = ctx.stage, ctx.crop
    ini, dev, mid, late = c.stages
    facts = [
        _calc_fact("crop.das", "Days after sowing", float(s.das), "days"),
        _calc_fact("crop.stage", "Growth stage", s.stage, ""),
        _calc_fact("crop.kc", "Crop coefficient Kc", s.kc, ""),
        _calc_fact("crop.season_days", "Typical season length", float(ini + dev + mid + late), "days"),
        _calc_fact("crop.heat_threshold", "Heat damage threshold at the sensitive stage", c.heat_c, "°C"),
    ]
    if s.days_to_harvest is not None:
        facts.append(_calc_fact("crop.days_to_harvest", "Approximate days to harvest", float(s.days_to_harvest), "days"))
    notes = [f"Stages (days): {', '.join(f'{n} {d}' for n, d in zip(STAGE_NAMES, c.stages))}. Sensitive stage note: {c.heat_stage_note}. Source: {FAO56}."]
    return ToolResult("get_crop_stage", "ok", ["agronomy table"], facts, notes)


async def get_water_balance(ctx: Context, days: int = 7, **_) -> ToolResult:
    if ctx.stage is None:
        return ToolResult("get_water_balance", "unavailable", [], [], ["Needs the sowing date (for Kc)."])
    wx = await weather.forecast(ctx.field, 16)
    if wx.status == "unavailable":
        return ToolResult("get_water_balance", "unavailable", wx.providers_tried, [], wx.notes)
    ctx.evidence.add(wx)  # the balance cites forecast facts, so they must be in the store
    wb = engine.water_balance(wx.series["daily"], ctx.stage.kc, max(3, min(int(days), 14)))
    if not wb:
        return ToolResult("get_water_balance", "unavailable", wx.providers_tried, [], ["Forecast has no ET0."])
    n = wb["days"]
    facts = [
        _calc_fact(f"calc.crop_et_{n}d", f"Crop water use, next {n} days (ET0 × Kc {wb['kc']})", wb["crop_et"], "mm"),
        _calc_fact(f"calc.effective_rain_{n}d", f"Effective rain, next {n} days", wb["effective_rain"], "mm"),
        _calc_fact(f"calc.water_deficit_{n}d", f"Irrigation need, next {n} days", wb["deficit"], "mm"),
        _calc_fact(f"calc.dry_days_{n}d", f"Dry days (< 2.5 mm), next {n} days", float(wb["dry_days"]), "days"),
    ]
    notes = ["Effective rain counts 80% of days with ≥ 5 mm. 1 mm over 1 acre ≈ 4,047 litres.",
             "A 7-day shortfall of 12 mm or more is a moderate water need; 25 mm or more is high (moderate at most in the late season)."]
    return ToolResult("get_water_balance", "ok", wx.providers_tried, facts, notes)


async def get_weather_forecast(ctx: Context, days: int = 16, **_) -> ToolResult:
    return await weather.forecast(ctx.field, days)


async def get_rainfall_anomaly(ctx: Context, **_) -> ToolResult:
    return await climate.rainfall_anomaly(ctx.field, ctx.today)


async def get_crop_health(ctx: Context, lookback_days: int = 90, **_) -> ToolResult:
    return await satellite.crop_health(ctx.field, lookback_days, ctx.today)


async def get_soil_profile(ctx: Context, **_) -> ToolResult:
    return await soil.soil_profile(ctx.field)


async def get_mandi_prices(ctx: Context, scope: str = "district", **_) -> ToolResult:
    if ctx.crop is None:
        return ToolResult("get_mandi_prices", "unavailable", [], [], ["Crop not in the reference table, so its mandi commodity name is unknown."])
    return await mandi.prices(ctx.field, ctx.crop.agmarknet, "state" if scope == "state" else "district")


async def get_disaster_alerts(ctx: Context, radius_km: float = 500, **_) -> ToolResult:
    return await disasters.alerts(ctx.field, radius_km, ctx.today)


DISPATCH = {
    "get_weather_forecast": get_weather_forecast,
    "get_rainfall_anomaly": get_rainfall_anomaly,
    "get_crop_health": get_crop_health,
    "get_soil_profile": get_soil_profile,
    "get_mandi_prices": get_mandi_prices,
    "get_disaster_alerts": get_disaster_alerts,
    "get_crop_stage": get_crop_stage,
    "get_water_balance": get_water_balance,
}

RISK_TYPES = ["heat_stress", "water_deficit", "heavy_rain", "disease_weather", "vegetation_decline", "rain_deficit", "disaster", "market"]
EVIDENCE = {"type": "array", "items": {"type": "string"}, "description": "Fact ids from tool results that support this item"}

DECLARATIONS: list[dict[str, Any]] = [
    {"name": "get_weather_forecast", "description": "Daily forecast for the farmer's field: max/min temperature, rain, chance of rain, humidity, wind, reference evapotranspiration (ET0).",
     "parameters": {"type": "object", "properties": {"days": {"type": "integer", "description": "1-16, default 16"}}}},
    {"name": "get_rainfall_anomaly", "description": "Rain observed at the field (last 30 days, since sowing, this monsoon) vs the 2005-2024 normal, with the IMD category.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "get_crop_health", "description": "Sentinel-2 satellite NDVI (crop vigour) time series for the field's own 10 m pixels, with cloudy views removed. Takes about 10 s.",
     "parameters": {"type": "object", "properties": {"lookback_days": {"type": "integer", "description": "30-150, default 90"}}}},
    {"name": "get_soil_profile", "description": "Soil pH, texture, organic carbon (0-30 cm) and today's soil moisture at the field.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "get_mandi_prices", "description": "Today's wholesale mandi prices (₹/quintal) for the farmer's crop, by market, with distance from the field.",
     "parameters": {"type": "object", "properties": {"scope": {"type": "string", "enum": ["district", "state"], "description": "Start with district; it widens automatically if empty"}}}},
    {"name": "get_disaster_alerts", "description": "Active flood, cyclone, drought and other GDACS disaster alerts near the field.",
     "parameters": {"type": "object", "properties": {"radius_km": {"type": "number", "description": "50-1500, default 500"}}}},
    {"name": "get_crop_stage", "description": "Growth stage of the crop from its sowing date (days after sowing, stage, crop coefficient, heat threshold, days to harvest).",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "get_water_balance", "description": "Calculator: crop water use (FAO-56 ET0 × Kc) vs effective forecast rain, i.e. how much irrigation the crop needs.",
     "parameters": {"type": "object", "properties": {"days": {"type": "integer", "description": "3-14, default 7"}}}},
    {"name": "submit_advisory", "description": "Submit the final advisory for the farmer. Call exactly once when ready; it is checked, and you may be asked to fix problems.",
     "parameters": {
         "type": "object",
         "properties": {
             "headline": {"type": "string", "description": "One line, under 120 characters, in the farmer's language"},
             "summary": {"type": "string", "description": "2-4 short sentences in the farmer's language"},
             "actions": {"type": "array", "items": {"type": "object", "properties": {
                 "when": {"type": "string", "enum": ["today", "next_3_days", "this_week", "before_harvest"]},
                 "action": {"type": "string"}, "why": {"type": "string"}, "evidence": EVIDENCE},
                 "required": ["when", "action", "why", "evidence"]}},
             "risks": {"type": "array", "items": {"type": "object", "properties": {
                 "type": {"type": "string", "enum": RISK_TYPES}, "level": {"type": "string", "enum": ["low", "moderate", "high"]},
                 "evidence": EVIDENCE}, "required": ["type", "level", "evidence"]}},
             "market_advice": {"type": "string", "description": "Where/when to sell, or empty"},
             "market_evidence": EVIDENCE,
             "data_gaps": {"type": "array", "items": {"type": "string"}, "description": "Sources that were unavailable and what that means"},
             "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
         },
         "required": ["headline", "summary", "actions", "risks", "data_gaps", "confidence"],
     }},
]


async def run_tool(ctx: Context, name: str, args: dict) -> ToolResult:
    fn = DISPATCH.get(name)
    if fn is None:
        return ToolResult(name, "unavailable", [], [], [f"Unknown tool '{name}'."])
    try:
        result = await fn(ctx, **(args or {}))
    except Exception as e:  # a tool bug must not end the request; the model sees it and adapts
        result = ToolResult(name, "unavailable", [], [], [f"Tool error: {type(e).__name__}"])
    ctx.evidence.add(result)
    return result
