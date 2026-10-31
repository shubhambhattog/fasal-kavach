"""Active disaster alerts near the field from GDACS (UN/EC Global Disaster Alert and Coordination System)."""

from datetime import date, timedelta

from ..evidence import Field, ToolResult, fact
from ..http import SourceError, get_json
from .geo import haversine_km

GDACS = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
TYPES = {"FL": "flood", "TC": "tropical cyclone", "DR": "drought", "EQ": "earthquake", "WF": "wildfire", "VO": "volcano"}


async def alerts(f: Field, radius_km: float = 500, today: date | None = None) -> ToolResult:
    radius_km = max(50, min(float(radius_km), 1500))
    today = today or date.today()
    params = {
        "eventlist": "FL;TC;DR;EQ;WF",
        "alertlevel": "Green;Orange;Red",
        "fromDate": (today - timedelta(days=30)).isoformat(),
        "toDate": today.isoformat(),
    }
    try:
        res = await get_json("gdacs", GDACS, params, ttl_s=1800, timeout_s=12, validate=lambda d: d["features"])
    except SourceError as e:
        return ToolResult("get_disaster_alerts", "unavailable", ["gdacs"], [], [f"{e.provider} unavailable: {e.message}"])

    events = []
    for feat in res.data["features"]:
        p = feat["properties"]
        if str(p.get("iscurrent", "true")).lower() != "true":
            continue
        lon, lat = feat["geometry"]["coordinates"][:2]
        dist = haversine_km(f.lat, f.lon, lat, lon)
        # Droughts and big cyclones cover large areas, so their point location understates exposure.
        reach = radius_km * (2 if p.get("eventtype") in ("DR", "TC") else 1)
        if dist <= reach:
            events.append({
                "id": p.get("eventid"), "type": TYPES.get(p.get("eventtype"), p.get("eventtype")), "name": p.get("name"),
                "alert": p.get("alertlevel"), "distance_km": round(dist), "from": p.get("fromdate", "")[:10],
                "to": p.get("todate", "")[:10], "severity": (p.get("severitydata") or {}).get("severitytext", ""),
            })
    events.sort(key=lambda e: e["distance_km"])
    facts = [fact("alerts.count", f"Active GDACS alerts within {round(radius_km)} km", float(len(events)), "alerts", res)]
    for e in events[:5]:
        facts.append(fact(f"alerts.{e['id']}.distance", f"{e['alert']} {e['type']} alert: {e['name']} ({e['severity']})", float(e["distance_km"]), "km", res))
    return ToolResult("get_disaster_alerts", "ok", ["gdacs"], facts, [], series={"events": events})
