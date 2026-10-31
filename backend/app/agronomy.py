"""Crop reference knowledge: stage lengths, crop coefficients and stress thresholds.

These are published agronomy constants, not data about any field. Each value carries its source.
Stage lengths and Kc: FAO Irrigation & Drainage Paper 56 (Allen et al., 1998), Tables 11 and 12,
using the India or closest-climate row where one exists. Heat thresholds at the sensitive stage
(flowering or fruit set) follow Hatfield & Prueger (2015), "Temperature extremes: effect on plant
growth and development", Weather and Climate Extremes 10:4-10, and ICAR crop production guides.
Values marked `heuristic` are rules of thumb, and the UI labels them that way.
"""

from dataclasses import dataclass
from datetime import date

FAO56 = "FAO-56 (Allen et al. 1998), Tables 11-12"
HEAT_SRC = "Hatfield & Prueger 2015 (Weather Clim. Extremes 10:4-10); ICAR crop guides"


@dataclass(frozen=True)
class Crop:
    key: str
    names: dict[str, str]  # display names by language
    agmarknet: tuple[str, ...]  # commodity names in the data.gov.in mandi feed, best match first
    stages: tuple[int, int, int, int]  # initial, development, mid-season, late (days), FAO-56 Table 11
    kc: tuple[float, float, float]  # Kc ini, mid, end, FAO-56 Table 12
    heat_c: float  # Tmax above which the sensitive (mid) stage is damaged
    heat_stage_note: str
    harvest_rain_sensitive: bool  # rain at maturity spoils the produce (lodging, rot, sprouting, lint damage)


CROPS: dict[str, Crop] = {
    c.key: c
    for c in [
        Crop("wheat", {"en": "Wheat", "hi": "गेहूं", "mr": "गहू"}, ("Wheat",), (15, 25, 50, 30), (0.3, 1.15, 0.3), 32.0,
             "heat after heading shrivels grain (terminal heat)", True),
        Crop("rice", {"en": "Rice (paddy)", "hi": "धान", "mr": "भात"}, ("Paddy(Dhan)(Common)", "Paddy(Dhan)(Basmati)", "Rice"),
             (30, 30, 60, 30), (1.05, 1.2, 0.75), 35.0, "heat at anthesis causes spikelet sterility", True),
        Crop("cotton", {"en": "Cotton", "hi": "कपास", "mr": "कापूस"}, ("Cotton",), (30, 50, 60, 55), (0.35, 1.15, 0.6), 38.0,
             "heat at flowering causes square and boll shedding", True),
        Crop("soybean", {"en": "Soybean", "hi": "सोयाबीन", "mr": "सोयाबीन"}, ("Soyabean",), (20, 30, 60, 25), (0.4, 1.15, 0.5), 35.0,
             "heat at flowering and pod fill reduces pod set", True),
        Crop("onion", {"en": "Onion", "hi": "प्याज", "mr": "कांदा"}, ("Onion",), (15, 25, 70, 40), (0.7, 1.05, 0.75), 35.0,
             "heat during bulbing forces early maturity and small bulbs", True),
        Crop("tomato", {"en": "Tomato", "hi": "टमाटर", "mr": "टोमॅटो"}, ("Tomato",), (30, 40, 40, 25), (0.6, 1.15, 0.8), 32.0,
             "heat above about 32 °C at flowering causes flower drop and poor fruit set", False),
        Crop("sugarcane", {"en": "Sugarcane", "hi": "गन्ना", "mr": "ऊस"}, ("Sugarcane",), (35, 60, 190, 120), (0.4, 1.25, 0.75), 40.0,
             "extreme heat slows cane growth", False),
        Crop("maize", {"en": "Maize", "hi": "मक्का", "mr": "मका"}, ("Maize",), (20, 35, 40, 30), (0.3, 1.2, 0.35), 35.0,
             "heat at tasseling and silking kills pollen and cuts kernel set", True),
        Crop("chickpea", {"en": "Chickpea (gram)", "hi": "चना", "mr": "हरभरा"}, ("Bengal Gram(Gram)(Whole)", "Kabuli Chana(Chickpeas-White)"),
             (20, 30, 40, 20), (0.4, 1.0, 0.35), 32.0, "heat at flowering causes flower and pod abortion", True),
        Crop("groundnut", {"en": "Groundnut", "hi": "मूंगफली", "mr": "भुईमूग"}, ("Groundnut",), (25, 35, 45, 25), (0.4, 1.15, 0.6), 35.0,
             "heat at pegging and pod fill reduces pod set", True),
    ]
}

STAGE_NAMES = ("initial (establishment)", "crop development (vegetative)", "mid-season (flowering / yield formation)", "late season (maturity)")


@dataclass
class StageInfo:
    das: int  # days after sowing
    stage_index: int  # 0-3, or 4 when past the expected season
    stage: str
    kc: float
    days_to_harvest: int | None
    sensitive_to_heat: bool


def crop_stage(crop: Crop, sowing: date, today: date) -> StageInfo:
    """Growth stage from days after sowing, with Kc interpolated as in FAO-56 Fig. 25."""
    das = (today - sowing).days
    ini, dev, mid, late = crop.stages
    kc_ini, kc_mid, kc_end = crop.kc
    total = ini + dev + mid + late
    if das < ini:
        return StageInfo(das, 0, STAGE_NAMES[0], kc_ini, total - das, False)
    if das < ini + dev:
        frac = (das - ini) / dev
        return StageInfo(das, 1, STAGE_NAMES[1], round(kc_ini + frac * (kc_mid - kc_ini), 2), total - das, False)
    if das < ini + dev + mid:
        return StageInfo(das, 2, STAGE_NAMES[2], kc_mid, total - das, True)
    if das <= total:
        frac = (das - ini - dev - mid) / late
        return StageInfo(das, 3, STAGE_NAMES[3], round(kc_mid + frac * (kc_end - kc_mid), 2), total - das, False)
    return StageInfo(das, 4, "past expected harvest", kc_end, 0, False)


def find_crop(name: str) -> Crop | None:
    n = name.strip().lower()
    if n in CROPS:
        return CROPS[n]
    for c in CROPS.values():
        if any(n == v.lower() for v in c.names.values()) or n in (a.lower() for a in c.agmarknet):
            return c
    return None
