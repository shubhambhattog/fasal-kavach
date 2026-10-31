"""16-day daily forecast for the exact field coordinates.

Chain: Open-Meteo (ECMWF/GFS blend; includes FAO ET0) → MET Norway (ECMWF; we aggregate hourly
data to IST days and compute Hargreaves ET0). Fact ids: wx.<field>.<YYYY-MM-DD>, plus summary ids.
"""

import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from ..evidence import Field, ToolResult, fact
from ..http import Fetched, SourceError, get_json

IST = timezone(timedelta(hours=5, minutes=30))
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
MET_NORWAY = "https://api.met.no/weatherapi/locationforecast/2.0/complete"

FIELDS = {
    "tmax": ("Max temperature", "°C"),
    "tmin": ("Min temperature", "°C"),
    "rain": ("Rainfall", "mm"),
    "rain_prob": ("Chance of rain", "%"),
    "rh": ("Mean humidity", "%"),
    "wind": ("Max wind", "km/h"),
    "et0": ("Reference evapotranspiration", "mm"),
}


def _validate_open_meteo(d):
    if "daily" not in d or not d["daily"].get("time"):
        raise ValueError("no daily block")


async def _open_meteo(f: Field, days: int) -> tuple[list[dict], Fetched]:
    params = {
        "latitude": round(f.lat, 4),
        "longitude": round(f.lon, 4),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,"
        "relative_humidity_2m_mean,wind_speed_10m_max,et0_fao_evapotranspiration",
        "timezone": "Asia/Kolkata",
        "forecast_days": days,
    }
    res = await get_json("open-meteo", OPEN_METEO, params, ttl_s=3600, validate=_validate_open_meteo)
    d = res.data["daily"]
    keys = {
        "tmax": "temperature_2m_max",
        "tmin": "temperature_2m_min",
        "rain": "precipitation_sum",
        "rain_prob": "precipitation_probability_max",
        "rh": "relative_humidity_2m_mean",
        "wind": "wind_speed_10m_max",
        "et0": "et0_fao_evapotranspiration",
    }
    rows = []
    for i, day in enumerate(d["time"]):
        row = {"date": day}
        for k, src in keys.items():
            v = (d.get(src) or [None] * len(d["time"]))[i]
            row[k] = None if v is None else float(v)
        rows.append(row)
    return rows, res


def extraterrestrial_radiation_mm(lat_deg: float, day: date) -> float:
    """FAO-56 eq. 21, converted to mm/day of evaporation equivalent (×0.408)."""
    j = day.timetuple().tm_yday
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    delta = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    ra = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )
    return 0.408 * ra


def hargreaves_et0(tmax: float, tmin: float, lat: float, day: date) -> float:
    """FAO-56 eq. 52 (Hargreaves), used when the provider doesn't give ET0."""
    tmean = (tmax + tmin) / 2
    return 0.0023 * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0)) * extraterrestrial_radiation_mm(lat, day)


def aggregate_met_norway(timeseries: list[dict], lat: float, days: int) -> list[dict]:
    """Hourly/6-hourly MET Norway series → IST daily rows. Precipitation intervals never overlap."""
    temps: dict[str, list[float]] = defaultdict(list)
    rh: dict[str, list[float]] = defaultdict(list)
    wind: dict[str, list[float]] = defaultdict(list)
    rain: dict[str, float] = defaultdict(float)
    prob: dict[str, float] = defaultdict(float)
    covered_until: datetime | None = None
    for step in timeseries:
        t = datetime.fromisoformat(step["time"].replace("Z", "+00:00"))
        key = t.astimezone(IST).date().isoformat()
        inst = step["data"]["instant"]["details"]
        if "air_temperature" in inst:
            temps[key].append(inst["air_temperature"])
        if "relative_humidity" in inst:
            rh[key].append(inst["relative_humidity"])
        if "wind_speed" in inst:
            wind[key].append(inst["wind_speed"] * 3.6)
        if covered_until is not None and t < covered_until:
            continue
        for span, hours in (("next_1_hours", 1), ("next_6_hours", 6)):
            block = step["data"].get(span)
            if block and "precipitation_amount" in block.get("details", {}):
                rain[key] += block["details"]["precipitation_amount"]
                p = block["details"].get("probability_of_precipitation")
                if p is not None:
                    prob[key] = max(prob[key], p)
                covered_until = t + timedelta(hours=hours)
                break

    rows = []
    for key in sorted(temps)[:days]:
        if len(temps[key]) < 4:  # partial first/last day: not enough data for max/min
            continue
        tmax, tmin = max(temps[key]), min(temps[key])
        d = date.fromisoformat(key)
        rows.append(
            {
                "date": key,
                "tmax": round(tmax, 1),
                "tmin": round(tmin, 1),
                "rain": round(rain[key], 1),
                "rain_prob": round(prob[key]) if key in prob else None,
                "rh": round(sum(rh[key]) / len(rh[key])) if rh[key] else None,
                "wind": round(max(wind[key]), 1) if wind[key] else None,
                "et0": round(hargreaves_et0(tmax, tmin, lat, d), 1),
            }
        )
    return rows


async def _met_norway(f: Field, days: int) -> tuple[list[dict], Fetched]:
    params = {"lat": round(f.lat, 4), "lon": round(f.lon, 4)}

    def validate(d):
        if not d.get("properties", {}).get("timeseries"):
            raise ValueError("no timeseries")

    res = await get_json("met-norway", MET_NORWAY, params, ttl_s=3600, validate=validate)
    return aggregate_met_norway(res.data["properties"]["timeseries"], f.lat, days), res


def build_result(rows: list[dict], src: Fetched, tried: list[str], notes: list[str]) -> ToolResult:
    facts = []
    for row in rows:
        for k, (label, unit) in FIELDS.items():
            if row.get(k) is not None:
                facts.append(fact(f"wx.{k}.{row['date']}", f"{label} on {row['date']}", row[k], unit, src))

    def total(n: int) -> float:
        return round(sum(r["rain"] or 0 for r in rows[:n]), 1)

    peak = max(rows, key=lambda r: r["tmax"] if r["tmax"] is not None else -99)
    wettest = max(rows, key=lambda r: r["rain"] or 0)
    summary = [
        fact("wx.rain_total_3d", "Rain total, next 3 days", total(3), "mm", src),
        fact("wx.rain_total_7d", "Rain total, next 7 days", total(7), "mm", src),
        fact(f"wx.rain_total_{len(rows)}d", f"Rain total, next {len(rows)} days", total(len(rows)), "mm", src),
        fact("wx.tmax_peak", f"Highest max temperature (on {peak['date']})", peak["tmax"], "°C", src),
        fact("wx.rain_max_day", f"Wettest day rainfall (on {wettest['date']})", wettest["rain"] or 0.0, "mm", src),
        fact("wx.forecast_days", "Forecast length", float(len(rows)), "days", src),
    ]
    facts.extend(summary)
    cols = ["date", *FIELDS]
    model_view = {
        "id_pattern": "wx.<column>.<date>, e.g. wx.rain." + rows[0]["date"],
        "columns": cols,
        "rows": [[r.get(c) for c in cols] for r in rows],
        "summary": [s.compact() for s in summary],
        "units": {k: u for k, (_, u) in FIELDS.items()},
    }
    return ToolResult(
        "get_weather_forecast",
        "ok" if len(tried) == 1 else "partial",
        tried,
        facts,
        notes,
        series={"daily": rows, "provider": src.provider, "url": src.url, "fetched_at": src.fetched_at},
        model_view=model_view,
    )


async def forecast(f: Field, days: int = 16) -> ToolResult:
    days = max(1, min(int(days), 16))
    tried, notes = [], []
    for name, fn in (("open-meteo", _open_meteo), ("met-norway", _met_norway)):
        tried.append(name)
        try:
            rows, src = await fn(f, days)
            if not rows:
                raise SourceError(name, "empty forecast")
            if name == "met-norway":
                notes.append(
                    f"Primary source failed; using MET Norway ({len(rows)} days). ET0 estimated with Hargreaves (FAO-56 eq. 52)."
                )
            notes.append("Reference thresholds: IMD heavy rain ≥ 64.5 mm/day, rather heavy ≥ 35.6 mm/day; relative humidity ≥ 85% "
                         "on 2+ consecutive days favours fungal disease (3-4+ days: high).")
            return build_result(rows, src, tried, notes)
        except SourceError as e:
            notes.append(f"{e.provider} unavailable: {e.message}")
    return ToolResult("get_weather_forecast", "unavailable", tried, [], notes)
