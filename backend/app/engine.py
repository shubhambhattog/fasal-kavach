"""Deterministic agronomy risk engine.

It turns gathered evidence into risk signals using published thresholds. It never sees the model's
output, and the model never sees its signals. The gate compares the two, so the model can't
quietly drop a high risk or invent one. Each signal lists the facts it used and the source of its
threshold.
"""

from dataclasses import asdict, dataclass, field
from datetime import date

from .agronomy import FAO56, HEAT_SRC, Crop, StageInfo
from .evidence import EvidenceStore

LEVELS = ("low", "moderate", "high")
IMD_RAIN = "IMD rainfall intensity classes (rather heavy ≥ 35.6 mm/day, heavy ≥ 64.5 mm/day)"
IMD_DEPARTURE = "IMD seasonal departure categories (deficient ≤ −20%, large deficient ≤ −60%)"
DISEASE_SRC = "heuristic: RH ≥ 85% on consecutive days favours fungal diseases (blight, blast, mildew)"
NDVI_SRC = "heuristic: NDVI drop ≥ 0.10 over 3+ weeks before maturity signals crop stress"
GDACS_SRC = "GDACS alert levels (Green/Orange/Red)"


@dataclass
class Signal:
    type: str
    level: str
    title: str
    detail: str
    action: str
    evidence: list[str] = field(default_factory=list)
    numbers: dict[str, float] = field(default_factory=dict)
    threshold_source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _weather_rows(ev: EvidenceStore) -> list[dict]:
    for r in reversed(ev.results):
        if r.tool == "get_weather_forecast" and r.status != "unavailable":
            return r.series.get("daily", [])
    return []


def heat_stress(rows: list[dict], crop: Crop, stage: StageInfo | None) -> Signal | None:
    week = [r for r in rows[:7] if r.get("tmax") is not None]
    if not week:
        return None
    hot = [r for r in week if r["tmax"] >= crop.heat_c]
    very_hot = [r for r in week if r["tmax"] >= crop.heat_c + 3]
    sensitive = stage is None or stage.sensitive_to_heat
    peak = max(week, key=lambda r: r["tmax"])
    if sensitive:
        level = "high" if len(hot) >= 3 or very_hot else ("moderate" if hot else "low")
    else:
        level = "moderate" if len(very_hot) >= 2 else "low"
    ev = [f"wx.tmax.{r['date']}" for r in (hot or [peak])]
    return Signal(
        "heat_stress", level, "Heat stress",
        f"{len(hot)} of the next {len(week)} days reach {crop.heat_c:g} °C or more (peak {peak['tmax']:g} °C on {peak['date']}). "
        f"{'The crop is at its heat-sensitive stage: ' + crop.heat_stage_note if sensitive and stage else 'Sensitive stage: ' + crop.heat_stage_note}.",
        "Irrigate lightly in the evening on hot days to cool the canopy; avoid spraying in midday heat.",
        ev, {"hot_days": len(hot), "peak_tmax": peak["tmax"], "threshold": crop.heat_c}, HEAT_SRC,
    )


def water_balance(rows: list[dict], kc: float, days: int = 7) -> dict | None:
    """FAO-56 crop ET (ET0 × Kc) vs effective rain. Rain under 5 mm/day mostly evaporates (counted 0);
    heavier rain counts at 80% (a common simple effective-rain rule)."""
    week = [r for r in rows[:days] if r.get("et0") is not None]
    if len(week) < 3:
        return None
    crop_et = sum(r["et0"] * kc for r in week)
    eff = sum(0.8 * (r.get("rain") or 0) for r in week if (r.get("rain") or 0) >= 5)
    dry_days = sum(1 for r in week if (r.get("rain") or 0) < 2.5)
    return {"days": len(week), "crop_et": round(crop_et, 1), "effective_rain": round(eff, 1),
            "deficit": round(max(crop_et - eff, 0), 1), "dry_days": dry_days, "kc": kc,
            "dates": [r["date"] for r in week]}


def water_deficit(rows: list[dict], stage: StageInfo | None) -> Signal | None:
    if stage is None or stage.stage_index == 4:
        return None
    wb = water_balance(rows, stage.kc)
    if not wb:
        return None
    level = "high" if wb["deficit"] >= 25 else ("moderate" if wb["deficit"] >= 12 else "low")
    if stage.stage_index == 3 and level == "high":
        level = "moderate"  # late season: water need is falling and some stress is acceptable before harvest
    ev = [f"wx.et0.{d}" for d in wb["dates"]] + [f"wx.rain.{d}" for d in wb["dates"]]
    return Signal(
        "water_deficit", level, "Crop water need",
        f"Next {wb['days']} days: crop uses about {wb['crop_et']:g} mm (ET0 × Kc {stage.kc:g}); effective rain {wb['effective_rain']:g} mm; "
        f"shortfall {wb['deficit']:g} mm. {wb['dry_days']} dry days.",
        f"Plan about {wb['deficit']:g} mm of irrigation over the next {wb['days']} days, split into 2-3 waterings (more often on sandy soil).",
        ev, {k: wb[k] for k in ("crop_et", "effective_rain", "deficit", "dry_days")}, FAO56,
    )


def heavy_rain(rows: list[dict], crop: Crop, stage: StageInfo | None) -> Signal | None:
    week = rows[:7]
    if not week:
        return None
    wettest = max(week, key=lambda r: r.get("rain") or 0)
    peak = wettest.get("rain") or 0
    three_day = max((sum((r.get("rain") or 0) for r in week[i:i + 3]) for i in range(max(len(week) - 2, 1))), default=0)
    level = "high" if peak >= 64.5 or three_day >= 100 else ("moderate" if peak >= 35.6 else "low")
    harvest = stage is not None and stage.stage_index >= 3 and crop.harvest_rain_sensitive
    if harvest and level == "low" and peak >= 15.6:
        level = "moderate"
    detail = f"Wettest day {wettest['date']}: {peak:g} mm; wettest 3-day total {round(three_day, 1):g} mm."
    if harvest:
        detail += " The crop is near maturity, so rain can spoil the harvest."
    return Signal(
        "heavy_rain", level, "Heavy rain", detail,
        "Clear field drains before the rain; postpone fertiliser and spraying until after it; harvest mature produce early or cover it.",
        [f"wx.rain.{wettest['date']}"], {"max_day": peak, "max_3day": round(three_day, 1)}, IMD_RAIN,
    )


def disease_weather(rows: list[dict]) -> Signal | None:
    week = [r for r in rows[:7] if r.get("rh") is not None]
    if len(week) < 3:
        return None
    run, best, best_end = 0, 0, None
    for r in week:
        humid = r["rh"] >= 85 and (r.get("tmin") is None or r["tmin"] >= 12)
        run = run + 1 if humid else 0
        if run > best:
            best, best_end = run, r["date"]
    level = "high" if best >= 4 else ("moderate" if best >= 2 else "low")
    humid_days = [r["date"] for r in week if r["rh"] >= 85]
    return Signal(
        "disease_weather", level, "Disease-favourable weather",
        f"Longest humid spell (RH ≥ 85%): {best} days" + (f", ending {best_end}." if best_end else "."),
        "Scout leaves for spots and mildew every 2-3 days; ask your KVK or agri officer about a preventive spray if symptoms appear.",
        [f"wx.rh.{d}" for d in humid_days] or [f"wx.rh.{week[0]['date']}"], {"humid_run_days": best}, DISEASE_SRC,
    )


def vegetation(ev: EvidenceStore, stage: StageInfo | None) -> Signal | None:
    latest, change = ev.get("ndvi.latest"), ev.get("ndvi.change")
    if latest is None:
        return None
    level, detail, ids = "low", f"Latest NDVI {latest.value:g}.", ["ndvi.latest"]
    late = stage is not None and stage.stage_index >= 3
    if change is not None:
        ids.append("ndvi.change")
        detail += f" Change over the compared period: {change.value:+g}."
        if not late:
            level = "high" if change.value <= -0.20 else ("moderate" if change.value <= -0.10 else "low")
        elif change.value <= -0.10:
            detail += " A decline is expected as the crop matures."
    if stage is not None and stage.stage_index == 2 and latest.value < 0.3 and level == "low":
        level = "moderate"
        detail += " Canopy is sparse for the flowering stage; check the pin location and the crop stand."
    return Signal(
        "vegetation_decline", level, "Crop vigour (satellite)", detail,
        "Walk the field where it looks weakest: check for water stress, pests or nutrient deficiency.",
        ids, {"ndvi": latest.value, "change": change.value if change else 0.0}, NDVI_SRC,
    )


def rain_deficit(ev: EvidenceStore) -> Signal | None:
    for key in ("since_sowing", "last30", "monsoon"):
        dep, normal = ev.get(f"clim.{key}.departure"), ev.get(f"clim.{key}.normal")
        if dep is not None and normal is not None and normal.value >= 30:
            break
    else:
        return None
    d = float(dep.value)
    level = "high" if d <= -60 else ("moderate" if d <= -20 or d >= 60 else "low")
    return Signal(
        "rain_deficit", level, "Rainfall vs normal",
        f"{dep.label}: {d:+g}% ({ev.get(f'clim.{key}.category').value}).",
        "Rainfed fields: conserve moisture with mulch and avoid extra fertiliser; irrigated fields: rely on scheduled irrigation.",
        [f"clim.{key}.departure", f"clim.{key}.observed", f"clim.{key}.normal"], {"departure_pct": d}, IMD_DEPARTURE,
    )


def disaster(ev: EvidenceStore) -> Signal | None:
    for r in reversed(ev.results):
        if r.tool == "get_disaster_alerts" and r.status == "ok":
            events = r.series.get("events", [])
            if not events:
                return Signal("disaster", "low", "Disaster alerts", "No active GDACS alerts near the field.", "", ["alerts.count"], {}, GDACS_SRC)
            worst = max(events, key=lambda e: ("Green", "Orange", "Red").index(e["alert"]) if e["alert"] in ("Green", "Orange", "Red") else 0)
            level = {"Red": "high", "Orange": "moderate"}.get(worst["alert"], "low")
            return Signal("disaster", level, "Disaster alert", f"{worst['alert']} {worst['type']} alert '{worst['name']}', {worst['distance_km']} km away.",
                          "Follow district administration advisories; secure harvested produce and livestock.",
                          [f"alerts.{worst['id']}.distance"], {"distance_km": worst["distance_km"]}, GDACS_SRC)
    return None


def market(ev: EvidenceStore) -> Signal | None:
    spread, best = ev.get("mandi.spread_pct"), ev.get("mandi.best_market")
    if spread is None or best is None:
        return None
    return Signal("market", "moderate" if spread.value >= 10 else "low", "Market opportunity",
                  f"{best.value} pays {spread.value:g}% above the median of reporting markets.",
                  f"Compare transport cost before selling at {best.value}.", ["mandi.best_modal", "mandi.median_modal", "mandi.spread_pct"],
                  {"spread_pct": spread.value}, "data.gov.in Agmarknet daily prices")


def assess(ev: EvidenceStore, crop: Crop | None, stage: StageInfo | None) -> list[Signal]:
    rows = _weather_rows(ev)
    out: list[Signal | None] = []
    if rows and crop:
        out += [heat_stress(rows, crop, stage), water_deficit(rows, stage), heavy_rain(rows, crop, stage), disease_weather(rows)]
    elif rows:
        out += [disease_weather(rows)]
    out += [vegetation(ev, stage), rain_deficit(ev), disaster(ev), market(ev)]
    signals = [s for s in out if s is not None]
    signals.sort(key=lambda s: LEVELS.index(s.level), reverse=True)
    return signals


def stage_for(crop: Crop | None, sowing: date | None, today: date) -> StageInfo | None:
    from .agronomy import crop_stage

    if crop is None or sowing is None:
        return None
    return crop_stage(crop, sowing, today)
