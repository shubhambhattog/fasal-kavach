"""Test-only builders. Nothing here is imported by the app."""

import time
from datetime import date, timedelta

from app.evidence import Fact, ToolResult

T0 = date(2026, 11, 1)


def f(fid, value, unit="", label=None):
    return Fact(fid, label or fid, value, unit, "test", "https://example.test", time.time())


def weather_result(tmax=30.0, tmin=20.0, rain=0.0, rh=60.0, et0=4.0, days=7, overrides=None):
    rows = []
    for i in range(days):
        d = (T0 + timedelta(days=i)).isoformat()
        row = {"date": d, "tmax": tmax, "tmin": tmin, "rain": rain, "rain_prob": 10.0, "rh": rh, "wind": 10.0, "et0": et0}
        row.update((overrides or {}).get(i, {}))
        rows.append(row)
    facts = [f(f"wx.{k}.{r['date']}", r[k]) for r in rows for k in ("tmax", "tmin", "rain", "rh", "et0", "wind")]
    facts.append(f("wx.rain_total_7d", round(sum(r["rain"] for r in rows), 1), "mm"))
    return ToolResult("get_weather_forecast", "ok", ["test"], facts, [], series={"daily": rows})
