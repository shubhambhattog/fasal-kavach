"""Parser and fallback tests with hand-written provider payloads (test fixtures only)."""

from datetime import date

import httpx
import pytest
import respx

from app import http as apphttp
from app.evidence import Field
from app.sources import mandi, weather
from app.sources.weather import aggregate_met_norway, hargreaves_et0

FIELD = Field(20.0868, 74.1278, "onion", date(2026, 9, 15), "en", "Niphad", "Nashik", "Maharashtra")


@pytest.fixture(autouse=True)
def fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(apphttp, "cache", apphttp.TTLCache(tmp_path / "c.sqlite"))
    monkeypatch.setattr(apphttp, "breaker", apphttp._Breaker())
    monkeypatch.setattr(apphttp, "_client", None)


def met_step(t, temp, rain1=None, rain6=None):
    data = {"instant": {"details": {"air_temperature": temp, "relative_humidity": 70, "wind_speed": 3}}}
    if rain1 is not None:
        data["next_1_hours"] = {"details": {"precipitation_amount": rain1}}
    if rain6 is not None:
        data["next_6_hours"] = {"details": {"precipitation_amount": rain6}}
    return {"time": t, "data": data}


def test_met_norway_no_double_counting():
    # Hourly steps carry both next_1h and next_6h; only the 1-hour blocks should count until 6-hourly steps start.
    series = [met_step(f"2026-11-01T{h:02d}:00:00Z", 20 + h, rain1=1.0, rain6=6.0) for h in range(0, 6)]
    series += [met_step("2026-11-01T06:00:00Z", 26, rain6=3.0), met_step("2026-11-01T12:00:00Z", 24, rain6=0.0)]
    rows = aggregate_met_norway(series, 20.0, 5)
    assert rows[0]["rain"] == 9.0  # 6 × 1 mm + 3 mm; IST day boundary keeps all steps on 1 Nov
    assert rows[0]["tmax"] == 26 and rows[0]["tmin"] == 20


def test_hargreaves_is_plausible_for_central_india():
    assert 3.0 < hargreaves_et0(31, 18, 20.0, date(2026, 11, 1)) < 5.5


@respx.mock
async def test_weather_falls_back_to_met_norway_on_429():
    respx.get(weather.OPEN_METEO).mock(return_value=httpx.Response(429, json={"error": True}))
    series = [met_step(f"2026-11-0{d}T{h:02d}:00:00Z", 22 + h % 8, rain1=0.5) for d in (1, 2) for h in range(0, 24, 3)]
    respx.get(weather.MET_NORWAY).mock(return_value=httpx.Response(200, json={"properties": {"timeseries": series}}))
    r = await weather.forecast(FIELD, 7)
    assert r.status == "partial"
    assert r.providers_tried == ["open-meteo", "met-norway"]
    assert any("rate limit" in n for n in r.notes)
    assert r.series["daily"][0]["et0"] > 0


@respx.mock
async def test_weather_all_down_is_unavailable_not_invented():
    respx.get(weather.OPEN_METEO).mock(return_value=httpx.Response(500))
    respx.get(weather.MET_NORWAY).mock(side_effect=httpx.ConnectTimeout("t"))
    r = await weather.forecast(FIELD, 7)
    assert r.status == "unavailable" and r.facts == []


@respx.mock
async def test_mandi_widens_from_district_to_state():
    def handler(request):
        if "filters[district]" in request.url.params:
            return httpx.Response(200, json={"total": 0, "records": []})
        return httpx.Response(200, json={"total": 2, "records": [
            {"market": "APMC Pune ", "district": "Pune", "variety": "Red", "arrival_date": "31/10/2026", "min_price": 2000, "max_price": 3000, "modal_price": 2500},
            {"market": "Lasalgaon ", "district": "Nashik", "variety": "Red", "arrival_date": "31/10/2026", "min_price": 3000, "max_price": 4500, "modal_price": 4100},
        ]})

    respx.get(mandi.RESOURCE).mock(side_effect=handler)
    respx.get(url__startswith="https://nominatim.openstreetmap.org").mock(return_value=httpx.Response(200, json=[]))
    r = await mandi.prices(FIELD, ("Onion",))
    assert r.status == "ok"
    assert r.series["scope"] == "Maharashtra state"
    assert r.series["markets"][0]["market"] == "Lasalgaon"
    assert any("widened" in n for n in r.notes)
