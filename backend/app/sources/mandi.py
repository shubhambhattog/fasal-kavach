"""Today's mandi (wholesale market) prices from the Agmarknet feed on data.gov.in.

Search widens from the field's district to its state when the district has no arrivals for the
crop. Prices are ₹ per quintal (100 kg). Distances to the best markets come from geocoding the
market name (Nominatim, cached).
"""

import asyncio
import re
from statistics import median

from ..config import settings
from ..evidence import Field, ToolResult, fact
from ..http import SourceError, get_json
from . import geo

RESOURCE = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
PAGE = 10  # the public sample key caps every page at 10 records; a personal key allows more
MAX_RECORDS = 200
MAX_GEOCODE = 5


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def clean_market(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("APMC", "")).strip()


async def _page(params: dict, offset: int, limit: int):
    p = dict(params) | {"offset": offset, "limit": limit}

    def validate(d):
        if "records" not in d:
            raise ValueError(d.get("message", "no records"))

    return await get_json("data.gov.in", RESOURCE, p, ttl_s=3 * 3600, timeout_s=12, validate=validate)


async def fetch_records(state: str, commodity: str, district: str | None = None) -> tuple[list[dict], object]:
    params = {"api-key": settings.data_gov_api_key, "format": "json", "filters[state.keyword]": state, "filters[commodity]": commodity}
    if district:
        params["filters[district]"] = district
    first = await _page(params, 0, 100)
    records = list(first.data["records"])
    total = int(first.data.get("total") or 0)
    step = len(records) or PAGE
    if total > len(records) and len(records) < 100:
        offsets = range(len(records), min(total, MAX_RECORDS), step)
        pages = await asyncio.gather(*(_page(params, o, step) for o in offsets), return_exceptions=True)
        for p in pages:
            if not isinstance(p, BaseException):
                records.extend(p.data["records"])
    return records, first


def _num(v) -> float | None:
    try:
        x = float(v)
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def summarise(records: list[dict]) -> list[dict]:
    """One row per market (best variety by modal price), sorted by modal price, highest first."""
    by_market: dict[str, dict] = {}
    for r in records:
        modal = _num(r.get("modal_price"))
        if modal is None:
            continue
        name = clean_market(r.get("market", ""))
        row = {
            "market": name,
            "district": r.get("district", ""),
            "variety": r.get("variety", ""),
            "date": r.get("arrival_date", ""),
            "modal": modal,
            "min": _num(r.get("min_price")),
            "max": _num(r.get("max_price")),
        }
        if name not in by_market or modal > by_market[name]["modal"]:
            by_market[name] = row
    return sorted(by_market.values(), key=lambda r: r["modal"], reverse=True)


async def prices(f: Field, commodities: tuple[str, ...], radius: str = "district") -> ToolResult:
    tried, notes = ["data.gov.in (Agmarknet)"], []
    if not f.state:
        return ToolResult("get_mandi_prices", "unavailable", tried, [], ["The field's state is unknown, so mandi search isn't possible."])
    rows, src, scope, used = [], None, "", ""
    try:
        for commodity in commodities:
            if radius == "district" and f.district:
                recs, src = await fetch_records(f.state, commodity, f.district)
                rows, scope, used = summarise(recs), f"{f.district} district", commodity
                if rows:
                    break
                notes.append(f"No {commodity} arrivals reported in {f.district} district today; widened to {f.state}.")
            recs, src = await fetch_records(f.state, commodity)
            rows, scope, used = summarise(recs), f"{f.state} state", commodity
            if rows:
                break
    except SourceError as e:
        return ToolResult("get_mandi_prices", "unavailable", tried, [], notes + [f"{e.provider} unavailable: {e.message}"])

    if not rows:
        return ToolResult("get_mandi_prices", "unavailable", tried, [],
                          notes + [f"No arrivals of {' / '.join(commodities)} reported in {f.state} in today's feed."])

    # Distance for the top markets and any market in the farmer's own district.
    targets = rows[:MAX_GEOCODE] + [r for r in rows[MAX_GEOCODE:] if r["district"].lower() == f.district.lower()][:2]
    for r in targets:
        try:
            hits = await geo.search(f"{re.sub(r'[()]', ' ', r['market'])}, {r['district']}, {f.state}", limit=1)
            if hits:
                r["distance_km"] = round(geo.haversine_km(f.lat, f.lon, hits[0]["lat"], hits[0]["lon"]))
        except SourceError:
            pass

    facts = []
    for r in rows[:15]:
        sid = slug(r["market"])
        facts.append(fact(f"mandi.{sid}.modal", f"{r['market']} ({r['district']}) modal price, {r['variety']}, {r['date']}", r["modal"], "₹/quintal", src))
        if r.get("distance_km") is not None:
            facts.append(fact(f"mandi.{sid}.distance", f"Distance to {r['market']}", float(r["distance_km"]), "km", src))
    med = median(r["modal"] for r in rows)
    best = rows[0]
    facts += [
        fact("mandi.median_modal", f"Median modal price across {len(rows)} markets ({scope})", round(med), "₹/quintal", src),
        fact("mandi.best_market", "Highest-priced market", best["market"], "", src),
        fact("mandi.best_modal", f"Best modal price ({best['market']})", best["modal"], "₹/quintal", src),
        fact("mandi.spread_pct", "Best market above the median", round((best["modal"] - med) / med * 100, 1), "%", src),
        fact("mandi.markets_count", "Markets reporting today", float(len(rows)), "markets", src),
    ]
    nearest = min((r for r in rows if r.get("distance_km") is not None), key=lambda r: r["distance_km"], default=None)
    if nearest:
        facts.append(fact("mandi.nearest_market", "Nearest reporting market (of those located)", nearest["market"], "", src))
    notes.append(f"Commodity '{used}', scope {scope}. Prices are ₹ per quintal on the arrival date shown. Distances are straight-line.")
    model_view = {
        "commodity": used,
        "scope": scope,
        "id_pattern": "mandi.<market_slug>.modal / .distance",
        "markets": [
            {"id": f"mandi.{slug(r['market'])}", "market": r["market"], "district": r["district"], "modal": r["modal"],
             "min": r["min"], "max": r["max"], "date": r["date"], "distance_km": r.get("distance_km")}
            for r in rows[:15]
        ],
        "summary": [x.compact() for x in facts if x.id.count(".") == 1],
    }
    return ToolResult("get_mandi_prices", "ok", tried, facts, notes, series={"markets": rows, "scope": scope, "commodity": used}, model_view=model_view)
