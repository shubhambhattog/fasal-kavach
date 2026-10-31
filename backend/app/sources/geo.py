"""Place search and reverse geocoding via OpenStreetMap Nominatim (usage policy: 1 req/s, cached 30 days)."""

import asyncio
import math
import time

from ..http import SourceError, get_json

NOMINATIM = "https://nominatim.openstreetmap.org"
DAY = 86400

# Rough bounding box of India, used before any network call.
INDIA_BBOX = (6.0, 68.0, 37.6, 97.5)  # lat_min, lon_min, lat_max, lon_max

_last_call = 0.0
_lock = asyncio.Lock()


async def _polite_get(path: str, params: dict):
    """Nominatim allows at most 1 request per second; cache hits skip the wait."""
    global _last_call
    async with _lock:
        wait = 1.05 - (time.time() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        res = await get_json("nominatim", f"{NOMINATIM}/{path}", params, ttl_s=30 * DAY)
        if not res.cached:
            _last_call = time.time()
        return res


def in_india_bbox(lat: float, lon: float) -> bool:
    return INDIA_BBOX[0] <= lat <= INDIA_BBOX[2] and INDIA_BBOX[1] <= lon <= INDIA_BBOX[3]


def clean_district(name: str) -> str:
    for suffix in (" District", " district", " Taluka", " Tahsil", " Tehsil"):
        name = name.removesuffix(suffix)
    return name.strip()


async def reverse(lat: float, lon: float) -> dict:
    """Return {place, district, state, country_code}. Raises SourceError if the point is not on land."""
    res = await _polite_get(
        "reverse", {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "format": "jsonv2", "zoom": 14, "accept-language": "en"}
    )
    data = res.data
    if "error" in data or "address" not in data:
        raise SourceError("nominatim", "no address here (water or unmapped area)")
    a = data["address"]
    place = a.get("village") or a.get("hamlet") or a.get("town") or a.get("suburb") or a.get("city") or ""
    district = clean_district(a.get("state_district") or a.get("county") or a.get("city_district") or "")
    return {
        "place": place,
        "district": district,
        "state": a.get("state", ""),
        "country_code": a.get("country_code", ""),
        "display_name": data.get("display_name", ""),
    }


async def search(query: str, limit: int = 5) -> list[dict]:
    res = await _polite_get(
        "search",
        {"q": query, "format": "jsonv2", "countrycodes": "in", "limit": limit, "accept-language": "en", "addressdetails": 1},
    )
    out = []
    for item in res.data:
        out.append(
            {
                "name": item.get("display_name", ""),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "type": item.get("type", ""),
            }
        )
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
