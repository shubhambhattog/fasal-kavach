# Build plan (24 h)

The build loop works top to bottom: pick the first unchecked item, build it, test it, tick it, and
commit at each milestone. Deploy early, and redeploy at each milestone.
Times are targets in IST, starting 2026-10-31 23:50.

## M0: Foundations (to 01:30)
- [ ] Docs: PRD, ARCHITECTURE, AGENT, DATA_SOURCES, PLAN, DEMO, DECISIONS, CLAUDE.md
- [ ] `git init`, private GitHub repo, first commit
- [ ] Backend scaffold (uv, FastAPI, config, cache, http client, `/api/health`)
- [ ] Frontend scaffold (Vite, React, TS, Tailwind, shadcn) served by FastAPI
- [ ] Dockerfile builds and runs locally

## M1: Live data tools (to 06:00)
- [ ] geo: search, reverse, India land check
- [ ] weather: Open-Meteo, then MET Norway (with Hargreaves ET0)
- [ ] climate: season rain vs NASA POWER normal, IMD category
- [ ] satellite: STAC, COG window, SCL mask, NDVI series (+ PNG thumbnail, P1)
- [ ] soil: SoilGrids, then Open-Meteo soil moisture
- [ ] mandi: data.gov.in, district → state widening, ranking
- [ ] disasters: GDACS radius filter
- [ ] Evidence store; pytest for parsers and fallbacks using recorded responses under `tests/fixtures`
      (tests only); one live smoke script

## M2: Agronomy and engine (to 08:30)
- [ ] Crop table (wheat, rice, cotton, soybean, onion, tomato, sugarcane, maize, chickpea, groundnut) with citations
- [ ] Growth stage from sowing date
- [ ] Signals: heat, dry spell / water deficit, heavy rain, disease weather, NDVI decline, rain deficit, disaster, market spread
- [ ] Unit tests for each threshold edge

## M3: Agent and gate (to 13:00)
- [ ] Tool declarations and dispatch
- [ ] Gemini loop with budgets and SSE events
- [ ] Gate: 7 checks plus diff
- [ ] Engine fallback advisory
- [ ] Tests with a fake model: clean pass, ungrounded-number repair, bad citation, hallucinated risk, injection, tool down, LLM down
- [ ] Live run on 3 locations with the cheap model

## M4: Frontend (to 17:00)
- [ ] Map (satellite basemap, pin, search), profile form
- [ ] Ask box, language picker
- [ ] Live agent trace panel
- [ ] Advisory card with risk and source chips (popover showing the raw fact)
- [ ] Forecast chart, NDVI chart, mandi table
- [ ] Error and empty states for every panel; mobile layout

## M5: Voice (to 18:30)
- [ ] Mic record, then `/api/transcribe`
- [ ] `/api/speak` (Gemini TTS to WAV), with browser speechSynthesis as fallback

## M6: Hardening and deploy (to 21:00)
- [ ] Edge-case sweep (PRD §3 list), fixing each one
- [ ] Eval: 12 cases, then `docs/EVAL.md` (first-pass rate, repairs, fallbacks, latency)
- [ ] Deploy to HF Spaces; smoke test the public URL
- [ ] P1: watch field and alerts inbox

## M7: Submission (to 23:00)
- [ ] README: problem, solution, architecture diagram, setup, data sources, what failed first, limits
- [ ] Pitch deck (6 slides)
- [ ] Demo script; the owner records a 2-3 min video
- [ ] Make the repo public; fill in the submission form

## Owner actions (only Shubham can do these)
- [ ] data.gov.in personal API key (free, instant at data.gov.in → sign up → My Account → API key)
- [ ] Hugging Face account and write token (for the Space)
- [ ] Record the demo video; submit the form
