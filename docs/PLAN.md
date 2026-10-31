# Build plan (24 h)

The build loop works top to bottom: pick the first unchecked item, build it, test it, tick it, and
commit at each milestone. Deploy early, and redeploy at each milestone.
Times are targets in IST, starting 2026-10-31 23:50.

## M0: Foundations (to 01:30)
- [x] Docs: PRD, ARCHITECTURE, AGENT, DATA_SOURCES, PLAN, DEMO, DECISIONS, CLAUDE.md
- [x] `git init`, private GitHub repo, first commit
- [x] Backend scaffold (uv, FastAPI, config, cache, http client, `/api/health`)
- [x] Frontend scaffold (Vite, React, TS, Tailwind) served by FastAPI
- [x] Dockerfile builds and runs locally

## M1: Live data tools (to 06:00)
- [x] geo: search, reverse, India land check
- [x] weather: Open-Meteo, then MET Norway (with Hargreaves ET0)
- [x] climate: season rain vs NASA POWER normal, IMD category
- [x] satellite: STAC, COG window, SCL mask, NDVI series (+ PNG thumbnail, P1)
- [x] soil: SoilGrids, then Open-Meteo soil moisture
- [x] mandi: data.gov.in, district → state widening, ranking
- [x] disasters: GDACS radius filter
- [x] Evidence store; pytest for parsers and fallbacks using recorded responses under `tests/fixtures`
      (tests only); one live smoke script

## M2: Agronomy and engine (to 08:30)
- [x] Crop table (wheat, rice, cotton, soybean, onion, tomato, sugarcane, maize, chickpea, groundnut) with citations
- [x] Growth stage from sowing date
- [x] Signals: heat, dry spell / water deficit, heavy rain, disease weather, NDVI decline, rain deficit, disaster, market spread
- [x] Unit tests for each threshold edge

## M3: Agent and gate (to 13:00)
- [x] Tool declarations and dispatch
- [x] Gemini loop with budgets and SSE events
- [x] Gate: 7 checks plus diff
- [x] Engine fallback advisory
- [x] Tests with a fake model: clean pass, ungrounded-number repair, bad citation, hallucinated risk, injection, tool down, LLM down
- [x] Live run on 3 locations with the cheap model

## M4: Frontend (to 17:00)
- [x] Map (satellite basemap, pin, search), profile form
- [x] Ask box, language picker
- [x] Live agent trace panel
- [x] Advisory card with risk and source chips (popover showing the raw fact)
- [x] Forecast chart, NDVI chart, mandi table
- [x] Error and empty states for every panel; mobile layout

## M5: Voice (to 18:30)
- [x] Mic record, then `/api/transcribe`
- [x] `/api/speak` (Gemini TTS to WAV), with browser speechSynthesis as fallback

## M6: Hardening and deploy (to 21:00)
- [x] Edge-case sweep (PRD §3 list), fixing each one
- [x] Eval: 12 cases (v1 4/12 → v3 10/12 first pass), then `docs/EVAL.md` (first-pass rate, repairs, fallbacks, latency)
- [x] Deploy (Render + Mumbai relay); smoke test the public URL
- [x] P1: watch fields (engine-only risk scan, sorted by risk) + NDVI map overlay

## M7: Submission (to 23:00)
- [x] README: problem, solution, architecture diagram, setup, data sources, what failed first, limits
- [x] Pitch deck (6 slides): https://gamma.app/docs/5ea2xftoiysvl5r
- [x] Demo script (docs/DEMO.md); the owner records a 2-3 min video
- [ ] Make the repo public; fill in the submission form

## Owner actions (only Shubham can do these)
- [ ] (optional) data.gov.in personal API key; the sample key works but pages 10 records at a time
- [x] Hosting: Render (live) + Vercel Mumbai relay
- [ ] Record the demo video; submit the form
