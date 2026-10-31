from datetime import date

from app import engine
from app.agronomy import CROPS, crop_stage
from app.evidence import EvidenceStore, ToolResult
from app.sources.climate import imd_category, window_normal

from helpers import T0, f, weather_result

ONION = CROPS["onion"]
WHEAT = CROPS["wheat"]


def store(*results):
    ev = EvidenceStore()
    for r in results:
        ev.add(r)
    return ev


def by_type(signals):
    return {s.type: s for s in signals}


def test_crop_stage_boundaries():
    assert crop_stage(ONION, date(2026, 10, 25), T0).stage_index == 0  # 7 DAS < 15
    s = crop_stage(ONION, date(2026, 9, 15), T0)  # 47 DAS: 15 + 25 = 40 → mid
    assert (s.das, s.stage_index, s.kc, s.sensitive_to_heat) == (47, 2, 1.05, True)
    assert crop_stage(ONION, date(2026, 3, 1), T0).stage_index == 4


def test_kc_interpolates_in_development():
    s = crop_stage(ONION, date(2026, 10, 1), T0)  # 31 DAS: 16/25 into development
    assert 0.7 < s.kc < 1.05


def test_heat_stress_levels_depend_on_stage():
    rows = weather_result(tmax=33.0, overrides={0: {"tmax": 35.5}}).series["daily"]
    mid = crop_stage(ONION, date(2026, 9, 15), T0)
    young = crop_stage(ONION, date(2026, 10, 25), T0)
    assert engine.heat_stress(rows, ONION, mid).level == "moderate"  # 1 day ≥ 35 at the sensitive stage
    assert engine.heat_stress(rows, ONION, young).level == "low"
    hot = weather_result(tmax=36.0).series["daily"]
    assert engine.heat_stress(hot, ONION, mid).level == "high"


def test_water_balance_counts_only_effective_rain():
    rows = weather_result(et0=4.0, rain=3.0, overrides={2: {"rain": 20.0}}).series["daily"]
    wb = engine.water_balance(rows, kc=1.0)
    assert wb["crop_et"] == 28.0
    assert wb["effective_rain"] == 16.0  # only the 20 mm day counts, at 80%
    assert wb["deficit"] == 12.0


def test_heavy_rain_imd_thresholds():
    stage = crop_stage(ONION, date(2026, 9, 15), T0)
    assert engine.heavy_rain(weather_result(overrides={1: {"rain": 70.0}}).series["daily"], ONION, stage).level == "high"
    assert engine.heavy_rain(weather_result(overrides={1: {"rain": 40.0}}).series["daily"], ONION, stage).level == "moderate"
    assert engine.heavy_rain(weather_result(rain=5.0).series["daily"], ONION, stage).level == "low"


def test_rain_near_harvest_is_a_risk_for_sensitive_crops():
    late = crop_stage(ONION, date(2026, 6, 15), T0)  # 139 DAS → late season
    rows = weather_result(overrides={2: {"rain": 20.0}}).series["daily"]
    assert engine.heavy_rain(rows, ONION, late).level == "moderate"


def test_disease_weather_needs_consecutive_humid_days():
    two = weather_result(rh=60, overrides={1: {"rh": 90}, 2: {"rh": 88}}).series["daily"]
    gap = weather_result(rh=60, overrides={1: {"rh": 90}, 3: {"rh": 88}}).series["daily"]
    assert engine.disease_weather(two).level == "moderate"
    assert engine.disease_weather(gap).level == "low"


def test_ndvi_decline_is_expected_at_maturity():
    ndvi = ToolResult("get_crop_health", "ok", [], [f("ndvi.latest", 0.45), f("ndvi.change", -0.22)])
    mid = crop_stage(WHEAT, date(2026, 9, 1), T0)
    late = crop_stage(WHEAT, date(2026, 7, 20), T0)
    assert engine.vegetation(store(ndvi), mid).level == "high"
    assert engine.vegetation(store(ndvi), late).level == "low"


def test_rain_deficit_uses_imd_bands():
    clim = ToolResult("get_rainfall_anomaly", "ok", [], [
        f("clim.last30.departure", -65.0), f("clim.last30.normal", 70.0), f("clim.last30.observed", 24.5), f("clim.last30.category", "large deficient")])
    assert engine.rain_deficit(store(clim)).level == "high"
    assert imd_category(-19) == "normal" and imd_category(-20) == "deficient" and imd_category(60) == "large excess"


def test_dry_season_normal_too_small_for_departure():
    clim = ToolResult("get_rainfall_anomaly", "ok", [], [f("clim.last30.departure", -100.0), f("clim.last30.normal", 4.0)])
    assert engine.rain_deficit(store(clim)) is None


def test_window_normal_averages_years():
    clim = {f"{y}1001": 10.0 for y in range(2005, 2025)} | {f"{y}1002": 5.0 for y in range(2005, 2025)}
    assert window_normal(clim, date(2026, 10, 1), date(2026, 10, 2)) == 15.0


def test_assess_sorts_high_first():
    wx = weather_result(tmax=37.0)
    sig = engine.assess(store(wx), ONION, crop_stage(ONION, date(2026, 9, 15), T0))
    assert sig[0].level == "high"
    assert by_type(sig)["heat_stress"].evidence[0].startswith("wx.tmax.")
