# Data sources

All sources are live, public and free. Status is as verified from the build machine on 2026-10-31.

| Source | Use | Endpoint | Auth | Verified | Limits / notes | Fallback |
|---|---|---|---|---|---|---|
| Open-Meteo Forecast | 16-day daily weather, ET0, soil moisture | `api.open-meteo.com/v1/forecast` | none | **429** locally (daily per-IP limit hit) | 10k calls/day per IP on the free tier; shared host IPs may be exhausted | MET Norway |
| MET Norway Locationforecast | ~9-day forecast | `api.met.no/weatherapi/locationforecast/2.0/compact` | User-Agent header required | 200 | Hourly series; we aggregate to daily. No ET0, so we compute Hargreaves ET0 | none (disclose) |
| Open-Meteo Archive (ERA5) | Season rainfall to date | `archive-api.open-meteo.com/v1/archive` | none | 200 | About 5 days of lag | NASA POWER daily |
| NASA POWER | 20-year rainfall climatology (2005-2024), daily | `power.larc.nasa.gov/api/temporal/daily/point` | none | 200 | Slow (1-3 s); cache 30 days | none (disclose) |
| Earth Search STAC (Element84) | Sentinel-2 L2A scenes | `earth-search.aws.element84.com/v1/search` | none | 200; 20 scenes Aug-Oct 2026 over Nashik, latest 2026-10-30 | COGs on public S3 (`sentinel-cogs`, us-west-2) | Microsoft Planetary Computer STAC (200; needs SAS signing) |
| SoilGrids v2 (ISRIC) | pH, clay, sand, SOC at 0-30 cm | `rest.isric.org/soilgrids/v2.0/properties/query` | none | **503** at the time | Known to be flaky; 5 calls/min | Open-Meteo soil moisture only (disclose) |
| data.gov.in Agmarknet | Today's mandi prices | `api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070` | API key | 200, updated 2026-10-31 18:00 | The public sample key returns at most 10 records per call (the app pages through them). **Refuses foreign datacenter IPs**, so the hosted app goes through a Mumbai relay (`relay/`) | Widen the filter; disclose |
| GDACS | Active disasters (floods, cyclones, droughts) | `www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH` | none | 200 | | none (disclose) |
| Nominatim (OSM) | Village search and reverse geocode | `nominatim.openstreetmap.org` | User-Agent header | 200 | 1 request/s; cache 30 days | none |
| Esri World Imagery | Basemap tiles (display only) | `server.arcgisonline.com/.../World_Imagery` | none | n/a | Display only; attribution required | OSM tiles |
| Gemini API | Agent, STT, TTS | `generativelanguage.googleapis.com/v1beta` | API key | 200 (3.8-flash, 3.5-flash, 3.5-flash-lite) | Rate limits per key tier | Engine-only advisory |

## Reference knowledge (not data)

Agronomy constants in `agronomy.py` are published reference values, each with its citation. They
are not datasets and not mock data:

- FAO-56 (Allen et al. 1998), Tables 11-12: crop stage lengths and Kc values.
- IMD rainfall categories: heavy rain ≥ 64.5 mm/day; seasonal departure bands of Large Excess
  (≥ +60%), Excess (+20 to +59%), Normal (−19 to +19%), Deficient (−20 to −59%) and Large
  Deficient (≤ −60%).
- Crop heat-stress thresholds, e.g. wheat at anthesis > 34 °C (Porter & Gawith 1999) and rice at
  anthesis > 35 °C (Jagadish et al.), each cited inline.
- Fungal-disease-favourable weather: RH ≥ 85% for 2+ days with moderate temperature. This is a
  generic late-blight / blast heuristic, labelled as a heuristic.
