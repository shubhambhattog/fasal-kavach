"""Sentinel-2 L2A NDVI for the field's own 10 m pixels.

1. STAC search (Element84 Earth Search) for scenes over the point in the lookback window.
2. For each scene (newest first, at most MAX_SCENES), read a 5×5-pixel (50 m) window of B04 (red),
   B08 (NIR) and SCL (scene classification) straight from the public cloud-optimised GeoTIFFs.
   That's a few HTTP range requests, not a full download.
3. Drop the scene if under 60% of the window is clear according to SCL (cloud, shadow, cirrus, snow).
4. NDVI = (NIR − red) / (NIR + red) on clear pixels, after the asset's scale and offset are applied.
"""

import asyncio
import os
from datetime import date, datetime, timedelta, timezone

import numpy as np

from ..config import settings
from ..evidence import Field, ToolResult, fact
from ..http import Fetched, SourceError, get_json

STAC = "https://earth-search.aws.element84.com/v1/search"
MAX_SCENES = 10
HALF = 2  # 5×5 window
CLEAR_SCL = {4, 5, 6, 7}  # vegetation, bare soil, water, unclassified
MIN_CLEAR_FRACTION = 0.6

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", str(int(settings.cog_timeout_s)))
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "1")


def _scaled(item: dict, asset: dict, raw: np.ndarray) -> np.ndarray:
    """DN → surface reflectance. Earth Search has already removed ESA's −1000 BOA offset
    (`earthsearch:boa_offset_applied`), so applying the asset's offset again would double-count it."""
    band = (asset.get("raster:bands") or [{}])[0]
    offset = 0.0 if item["properties"].get("earthsearch:boa_offset_applied") else band.get("offset", 0.0)
    return raw.astype("float32") * band.get("scale", 1e-4) + offset


def read_scene(item: dict, lon: float, lat: float) -> dict:
    """Blocking COG window read for one scene. Returns {date, ndvi, clear_fraction, cloud}."""
    import rasterio
    from rasterio.warp import transform as warp_transform
    from rasterio.windows import Window, from_bounds

    assets = item["assets"]
    epsg = item["properties"].get("proj:epsg") or int(str(item["properties"].get("proj:code", "")).split(":")[-1])
    xs, ys = warp_transform("EPSG:4326", f"EPSG:{epsg}", [lon], [lat])
    with rasterio.open(assets["red"]["href"]) as red_ds:
        row, col = red_ds.index(xs[0], ys[0])
        win = Window(col - HALF, row - HALF, 2 * HALF + 1, 2 * HALF + 1)
        red_raw = red_ds.read(1, window=win, boundless=True, fill_value=0)
        bounds = red_ds.window_bounds(win)
    with rasterio.open(assets["nir"]["href"]) as nir_ds:
        nir_raw = nir_ds.read(1, window=win, boundless=True, fill_value=0)
    with rasterio.open(assets["scl"]["href"]) as scl_ds:
        scl = scl_ds.read(
            1, window=from_bounds(*bounds, transform=scl_ds.transform), out_shape=red_raw.shape,
            boundless=True, fill_value=0, resampling=rasterio.enums.Resampling.nearest,
        )

    valid = (red_raw > 0) & (nir_raw > 0)
    clear = valid & np.isin(scl, list(CLEAR_SCL))
    clear_fraction = float(clear.sum()) / clear.size
    out = {
        "date": item["properties"]["datetime"][:10],
        "cloud": round(float(item["properties"].get("eo:cloud_cover", -1)), 1),
        "clear_fraction": round(clear_fraction, 2),
        "ndvi": None,
        "water_fraction": round(float((scl == 6).sum()) / scl.size, 2),
    }
    if clear_fraction >= MIN_CLEAR_FRACTION:
        r = _scaled(item, assets["red"], red_raw)[clear]
        n = _scaled(item, assets["nir"], nir_raw)[clear]
        denom = n + r
        ok = denom > 1e-6
        if ok.any():
            out["ndvi"] = round(float(np.mean((n[ok] - r[ok]) / denom[ok])), 3)
    return out


async def _search(f: Field, start: date, end: date) -> tuple[list[dict], Fetched]:
    body = {
        "collections": ["sentinel-2-l2a"],
        "intersects": {"type": "Point", "coordinates": [round(f.lon, 5), round(f.lat, 5)]},
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "limit": 60,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }

    def validate(d):
        if "features" not in d:
            raise ValueError("no features")

    res = await get_json("earth-search", STAC, None, ttl_s=6 * 3600, method="POST", json_body=body, validate=validate, timeout_s=15)
    best: dict[str, dict] = {}
    for it in res.data["features"]:
        day = it["properties"]["datetime"][:10]
        if day not in best or it["properties"].get("eo:cloud_cover", 100) < best[day]["properties"].get("eo:cloud_cover", 100):
            best[day] = it
    items = sorted(best.values(), key=lambda i: i["properties"]["datetime"], reverse=True)
    return items, res


async def crop_health(f: Field, lookback_days: int = 90, today: date | None = None) -> ToolResult:
    lookback_days = max(30, min(int(lookback_days), 150))
    today = today or date.today()
    tried, notes = ["earth-search"], []
    try:
        items, src = await _search(f, today - timedelta(days=lookback_days), today)
    except SourceError as e:
        return ToolResult("get_crop_health", "unavailable", tried, [], [f"{e.provider} unavailable: {e.message}"])
    if not items:
        return ToolResult("get_crop_health", "unavailable", tried, [], ["No Sentinel-2 scenes found for this point."])

    # Very cloudy scenes rarely have a clear 50 m window; skip them before any pixel read.
    candidates = [i for i in items if i["properties"].get("eo:cloud_cover", 100) <= 85][:MAX_SCENES]
    skipped_scene_cloud = len(items) - len([i for i in items if i["properties"].get("eo:cloud_cover", 100) <= 85])
    tried.append("sentinel-cogs (AWS open data)")
    results = await asyncio.gather(
        *(asyncio.wait_for(asyncio.to_thread(read_scene, i, f.lon, f.lat), timeout=settings.cog_timeout_s + 5) for i in candidates),
        return_exceptions=True,
    )
    scenes, failed = [], 0
    for r in results:
        if isinstance(r, BaseException):
            failed += 1
        else:
            scenes.append(r)
    clear = sorted([s for s in scenes if s["ndvi"] is not None], key=lambda s: s["date"])
    cloudy_windows = len(scenes) - len(clear)

    cog = Fetched(None, "sentinel-2 l2a (esa copernicus via aws)", src.url, datetime.now(timezone.utc).timestamp(), False)
    facts = [
        fact("ndvi.scenes_checked", "Sentinel-2 scenes checked", float(len(scenes)), "scenes", src),
        fact("ndvi.cloudy_skipped", "Scenes skipped for cloud over the field", float(cloudy_windows + skipped_scene_cloud), "scenes", src),
    ]
    if failed:
        notes.append(f"{failed} scene reads failed or timed out.")
    if not clear:
        notes.append(f"No cloud-free view of this field in the last {lookback_days} days.")
        return ToolResult("get_crop_health", "unavailable" if not scenes else "partial", tried, facts, notes,
                          series={"scenes": sorted(scenes, key=lambda s: s["date"])})

    for s in clear:
        facts.append(fact(f"ndvi.{s['date']}", f"NDVI on {s['date']}", s["ndvi"], "NDVI", cog))
    latest = clear[-1]
    facts.append(fact("ndvi.latest", f"Latest clear NDVI ({latest['date']})", latest["ndvi"], "NDVI", cog))
    facts.append(fact("ndvi.latest_date", "Latest clear satellite view", latest["date"], "date", cog))
    age = (today - date.fromisoformat(latest["date"])).days
    facts.append(fact("ndvi.latest_age_days", "Days since latest clear view", float(age), "days", cog))
    ref = [s for s in clear if (date.fromisoformat(latest["date"]) - date.fromisoformat(s["date"])).days >= 20]
    if ref:
        base = ref[-1]
        change = round(latest["ndvi"] - base["ndvi"], 3)
        facts.append(fact("ndvi.change", f"NDVI change {base['date']} → {latest['date']}", change, "NDVI", cog))
        facts.append(fact("ndvi.change_days", "Days between compared views", float((date.fromisoformat(latest["date"]) - date.fromisoformat(base["date"])).days), "days", cog))
    if latest.get("water_fraction", 0) > 0.5:
        notes.append("The pin looks like open water in the latest view; check the field location.")
    notes.append("NDVI guide: below 0.2 is bare soil or very sparse cover; 0.2-0.4 sparse or young crop; 0.4-0.6 moderate; above 0.6 dense healthy canopy.")
    return ToolResult("get_crop_health", "ok" if not failed else "partial", tried, facts, notes,
                      series={"scenes": sorted(scenes, key=lambda s: s["date"]), "stac_url": src.url})
