"""Soil at the field: texture/chemistry from ISRIC SoilGrids (250 m) and current surface wetness.

SoilGrids is often slow or down (HTTP 503 seen on 2026-10-31), so it gets a short timeout and a
long cache. Wetness comes from Open-Meteo soil moisture, with NASA POWER GWETTOP as the fallback.
"""

from datetime import date, timedelta

from ..evidence import Field, ToolResult, fact
from ..http import SourceError, get_json

SOILGRIDS = "https://rest.isric.org/soilgrids/v2.0/properties/query"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"

# property → (label, unit, divisor to convert SoilGrids' mapped units)
PROPS = {
    "phh2o": ("Soil pH (water)", "pH", 10),
    "clay": ("Clay", "%", 10),
    "sand": ("Sand", "%", 10),
    "soc": ("Organic carbon", "%", 100),
}
DEPTHS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}


def texture_class(clay: float, sand: float) -> str:
    """Coarse USDA-style grouping, enough for irrigation advice."""
    if clay >= 40:
        return "clayey (heavy, holds water, drains slowly)"
    if sand >= 70:
        return "sandy (drains fast, needs frequent light irrigation)"
    if clay >= 27:
        return "clay loam"
    return "loamy"


async def _soilgrids(f: Field):
    params = [("lon", f"{f.lon:.4f}"), ("lat", f"{f.lat:.4f}"), ("value", "mean")]
    params += [("property", p) for p in PROPS] + [("depth", d) for d in DEPTHS]
    return await get_json("soilgrids", SOILGRIDS, params, ttl_s=30 * 86400, timeout_s=6)


async def soil_profile(f: Field) -> ToolResult:
    tried, notes, facts = [], [], []
    series: dict = {}

    tried.append("soilgrids")
    try:
        res = await _soilgrids(f)
        values: dict[str, float] = {}
        for layer in res.data["properties"]["layers"]:
            name = layer["name"]
            if name not in PROPS:
                continue
            total, weight = 0.0, 0
            for d in layer["depths"]:
                v = d["values"].get("mean")
                if v is not None and d["label"] in DEPTHS:
                    total += v * DEPTHS[d["label"]]
                    weight += DEPTHS[d["label"]]
            if weight:
                values[name] = total / weight / PROPS[name][2]
        if not values:
            raise SourceError("soilgrids", "no soil data for this point (water, urban or unmapped)")
        for k, v in values.items():
            label, unit, _ = PROPS[k]
            facts.append(fact(f"soil.{k}", f"{label}, 0-30 cm", round(v, 2), unit, res))
        if "clay" in values and "sand" in values:
            facts.append(fact("soil.texture", "Texture class", texture_class(values["clay"], values["sand"]), "", res))
        series["soilgrids"] = values
    except (SourceError, KeyError, TypeError) as e:
        notes.append(f"soilgrids unavailable: {getattr(e, 'message', 'unexpected response')}")

    tried.append("open-meteo")
    try:
        params = {"latitude": round(f.lat, 4), "longitude": round(f.lon, 4), "hourly": "soil_moisture_0_to_1cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",
                  "forecast_days": 1, "timezone": "Asia/Kolkata"}
        res = await get_json("open-meteo", OPEN_METEO, params, ttl_s=3 * 3600)
        h = res.data["hourly"]
        idx = min(12, len(h["time"]) - 1)
        for key, label in (("soil_moisture_0_to_1cm", "0-1 cm"), ("soil_moisture_3_to_9cm", "3-9 cm"), ("soil_moisture_9_to_27cm", "9-27 cm")):
            v = h[key][idx]
            if v is not None:
                facts.append(fact(f"soil.moisture_{label.replace(' ', '').replace('-', '_')}", f"Soil moisture {label} (today)", round(v, 3), "m³/m³", res))
    except (SourceError, KeyError, TypeError) as e:
        notes.append(f"open-meteo soil moisture unavailable: {getattr(e, 'message', 'unexpected response')}")
        tried.append("nasa-power")
        try:
            end = date.today()
            params = {"parameters": "GWETTOP,GWETROOT", "community": "AG", "latitude": round(f.lat, 3), "longitude": round(f.lon, 3),
                      "start": (end - timedelta(days=10)).strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON"}
            res = await get_json("nasa-power", POWER, params, ttl_s=6 * 3600, timeout_s=20)
            p = res.data["properties"]["parameter"]
            for key, label in (("GWETTOP", "Surface soil wetness (0-5 cm)"), ("GWETROOT", "Root-zone soil wetness")):
                vals = [(k, v) for k, v in sorted(p[key].items()) if v != -999.0]
                if vals:
                    k, v = vals[-1]
                    facts.append(fact(f"soil.{key.lower()}", f"{label} on {k[:4]}-{k[4:6]}-{k[6:]} (0 dry, 1 saturated)", v, "fraction", res))
        except (SourceError, KeyError, TypeError) as e2:
            notes.append(f"nasa-power soil wetness unavailable: {getattr(e2, 'message', 'unexpected response')}")

    status = "ok" if facts and not notes else ("partial" if facts else "unavailable")
    return ToolResult("get_soil_profile", status, tried, facts, notes, series=series)

