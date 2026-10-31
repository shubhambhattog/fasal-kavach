"""Rainfall to date vs the 20-year normal for the same calendar window, at the field's coordinates.

Primary: NASA POWER (MERRA-2) for both the observed and the normal values, so the departure
compares like with like. Fallback for observed only: Open-Meteo ERA5 archive (noted as cross-source).
Categories follow IMD's departure bands.
"""

from datetime import date, timedelta

from ..evidence import Field, ToolResult, fact
from ..http import SourceError, get_json

POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
NORMAL_YEARS = range(2005, 2025)
FILL = -999.0


def imd_category(departure_pct: float) -> str:
    if departure_pct >= 60:
        return "large excess"
    if departure_pct >= 20:
        return "excess"
    if departure_pct > -20:
        return "normal"
    if departure_pct > -60:
        return "deficient"
    return "large deficient"


def _validate_power(d):
    if "PRECTOTCORR" not in d.get("properties", {}).get("parameter", {}):
        raise ValueError("no PRECTOTCORR")


async def _power_daily(f: Field, start: date, end: date, ttl_s: float):
    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "latitude": round(f.lat, 3),
        "longitude": round(f.lon, 3),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    res = await get_json("nasa-power", POWER, params, ttl_s=ttl_s, timeout_s=25, validate=_validate_power)
    series = {k: v for k, v in res.data["properties"]["parameter"]["PRECTOTCORR"].items() if v != FILL}
    return series, res


def window_normal(climatology: dict[str, float], start: date, end: date) -> float:
    """Mean over NORMAL_YEARS of the rain total between start and end's month-day (handles year wrap)."""
    totals = []
    for y in NORMAL_YEARS:
        try:
            s = start.replace(year=y)
            e = end.replace(year=y + (end.year - start.year))
        except ValueError:  # 29 Feb
            s, e = start.replace(year=y, day=28), end.replace(year=y + (end.year - start.year), day=28)
        total, d, n = 0.0, s, 0
        while d <= e:
            v = climatology.get(d.strftime("%Y%m%d"))
            if v is not None:
                total += v
                n += 1
            d += timedelta(days=1)
        if n:
            totals.append(total)
    if not totals:
        raise ValueError("no climatology")
    return sum(totals) / len(totals)


def windows(f: Field, last_obs: date) -> list[tuple[str, str, date]]:
    """(key, label, start) windows ending at the last observed day."""
    out = [("last30", "Last 30 days", last_obs - timedelta(days=29))]
    if f.sowing_date and (last_obs - f.sowing_date).days >= 14:
        out.append(("since_sowing", f"Since sowing ({f.sowing_date.isoformat()})", f.sowing_date))
    monsoon_year = last_obs.year if last_obs >= date(last_obs.year, 6, 1) else last_obs.year - 1
    out.append(("monsoon", f"Monsoon {monsoon_year} (1 Jun to 30 Sep)", date(monsoon_year, 6, 1)))
    return out


async def rainfall_anomaly(f: Field, today: date | None = None) -> ToolResult:
    today = today or date.today()
    tried, notes = ["nasa-power"], []
    start_needed = min(today - timedelta(days=150), f.sowing_date or today, date(today.year - 1, 6, 1))
    try:
        observed, obs_src = await _power_daily(f, start_needed, today, ttl_s=6 * 3600)
        clim, clim_src = await _power_daily(f, date(NORMAL_YEARS[0], 1, 1), date(NORMAL_YEARS[-1], 12, 31), 30 * 86400)
    except SourceError as e:
        notes.append(f"{e.provider} unavailable: {e.message}")
        return await _fallback(f, today, tried, notes)

    if not observed:
        notes.append("NASA POWER returned no recent observations.")
        return ToolResult("get_rainfall_anomaly", "unavailable", tried, [], notes)

    last_obs = date.fromisoformat(_iso(max(observed)))
    notes.append(f"Observed rain available up to {last_obs.isoformat()} (satellite-model lag about 3 days).")
    facts = [fact("clim.last_observed_date", "Last observed day", last_obs.isoformat(), "date", obs_src)]
    rows = []
    for key, label, start in windows(f, last_obs):
        end = last_obs if key != "monsoon" else min(last_obs, date(start.year, 9, 30))
        obs = sum(v for k, v in observed.items() if start <= date.fromisoformat(_iso(k)) <= end)
        try:
            normal = window_normal(clim, start, end)
        except ValueError:
            continue
        dep = (obs - normal) / normal * 100 if normal > 0.5 else 0.0
        cat = imd_category(dep) if normal > 0.5 else "normal (dry season)"
        facts += [
            fact(f"clim.{key}.observed", f"{label}: observed rain", round(obs, 1), "mm", obs_src),
            fact(f"clim.{key}.normal", f"{label}: 20-year normal (2005-2024)", round(normal, 1), "mm", clim_src),
            fact(f"clim.{key}.departure", f"{label}: departure from normal", round(dep), "%", clim_src),
            fact(f"clim.{key}.category", f"{label}: IMD category", cat, "", clim_src),
        ]
        rows.append({"window": key, "label": label, "start": start.isoformat(), "end": end.isoformat(),
                     "observed": round(obs, 1), "normal": round(normal, 1), "departure": round(dep), "category": cat})
    daily = [{"date": _iso(k), "rain": v} for k, v in sorted(observed.items()) if date.fromisoformat(_iso(k)) >= today - timedelta(days=90)]
    return ToolResult("get_rainfall_anomaly", "ok", tried, facts, notes,
                      series={"windows": rows, "daily": daily, "provider": obs_src.provider, "url": obs_src.url})


async def _fallback(f: Field, today: date, tried: list[str], notes: list[str]) -> ToolResult:
    """Observed rain from the ERA5 archive. There's no normal to compare against, so no departure."""
    tried.append("open-meteo-archive")
    start, end = today - timedelta(days=35), today - timedelta(days=5)
    params = {"latitude": round(f.lat, 4), "longitude": round(f.lon, 4), "start_date": start.isoformat(),
              "end_date": end.isoformat(), "daily": "precipitation_sum", "timezone": "Asia/Kolkata"}
    try:
        res = await get_json("open-meteo-archive", ARCHIVE, params, ttl_s=6 * 3600)
        vals = [v for v in res.data["daily"]["precipitation_sum"] if v is not None]
    except (SourceError, KeyError) as e:
        notes.append(f"open-meteo-archive unavailable: {getattr(e, 'message', 'bad response')}")
        return ToolResult("get_rainfall_anomaly", "unavailable", tried, [], notes)
    notes.append("Normal (20-year) unavailable, so no departure is computed.")
    facts = [fact("clim.last30.observed", f"Observed rain {start} to {end}", round(sum(vals), 1), "mm", res)]
    return ToolResult("get_rainfall_anomaly", "partial", tried, facts, notes)


def _iso(power_key: str) -> str:
    return f"{power_key[:4]}-{power_key[4:6]}-{power_key[6:]}"
