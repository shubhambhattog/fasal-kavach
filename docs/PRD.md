# Fasal Kavach: PRD

**Field-level climate-risk agent for Indian farmers.**
Forge Gen AI Buildathon. Theme 2 (Climate, Resource Infrastructure & Global Supply Resilience),
merging problem 1 (Multilingual Agritech Advisory) and problem 2 (Predictive Micro-Location Risk Engine).

- Owner: Shubham Bhatt (solo)
- Build window: 2026-10-31 23:50 IST to 2026-11-01 ~23:30 IST (24 h)
- Status: draft v1, written before any code

---

## 1. Problem

India has about 146 million operational holdings. 86% of them are small or marginal, under 2 ha
(Agriculture Census 2015-16). Farmers decide what to do each week (irrigate, spray, delay
fertiliser, harvest, sell) based on:

- **District-level** forecasts (IMD Agromet bulletins), which can be 50 km or more from their plot;
- **Hearsay** about mandi prices, so they sell at the nearest mandi rather than the best one;
- **No view of their own crop's health.** Free 10 m satellite imagery (Sentinel-2) exists every
  5 days, but no farmer can read it.

Climate volatility (unseasonal rain, heat at flowering, dry spells mid-monsoon) makes these
decisions more costly every season. The data to act on exists, is public and is updated daily.
It sits in five different portals that farmers don't use.

### Target users

| Persona | Need |
|---|---|
| **Small farmer** (primary): Marathi/Hindi speaker, smartphone, low literacy | "What should I do on my field this week, and why?" by voice, in their language |
| **FPO / Krishi Sakhi / extension worker** (secondary) | Check many members' fields quickly, see who is at risk, and share advice |
| **Judges** (demo audience) | See a real agent reason over live data and correct itself |

## 2. Solution

The user drops a pin on their field (or shares GPS), names the crop and sowing date, then asks a
question by voice or text in their language. An **AI agent** chooses which live sources to query:

1. **Weather forecast** (16 days), with a backup provider
2. **Season rainfall anomaly** against a 20-year climatology
3. **Sentinel-2 NDVI** time series for *that plot* (10 m), with clouds masked
4. **Soil** properties and moisture
5. **Mandi prices** for the crop across nearby markets (data.gov.in / Agmarknet)
6. **Disaster alerts** (GDACS) near the field

A **deterministic agronomy risk engine** turns that data into risk signals (heat stress, dry spell
or water deficit, heavy rain or waterlogging, fungal-disease-favourable weather, vegetation decline,
rainfall deficit). The agent writes a short plan in the user's language. **Every number cites its
live source.** A **gate** checks the plan against the engine and the raw data before it is shown.
If a number is invented or a risk is mis-stated, the gate returns a diff and the agent corrects
itself, up to 2 times. The answer is then **spoken back** in the user's language.

### USP (what's different from a crop chatbot)

1. **Field-level, not district-level.** Satellite NDVI for the user's own 10 m pixels, and weather
   for the exact coordinates.
2. **Every claim is traceable.** Each number in the advice links to the live API response it came
   from. Nothing is answered from model memory.
3. **Self-correcting.** The model writes the advice and a code gate checks it against a
   deterministic agronomy engine. Hallucinated numbers are caught and repaired on screen.
4. **Honest about missing data.** If a source is down, the agent says so and lowers its confidence.
   It never fills the gap.
5. **Voice-first in Indian languages**, for users who can't read dashboards.
6. **Action, not information.** For example: "Delay urea until Thursday; 38 mm of rain is
   forecast." Or: "Sell at Lasalgaon (₹2,140/q, 31 km) rather than Pimpalgaon (₹1,890/q)."

## 3. Scope

### P0: must ship (the demo depends on it)

- [ ] Pin-drop map (satellite basemap) plus search by village name; profile with crop, sowing date
      and language
- [ ] 6 live data tools with caching, timeouts and fallback chains; each returns `source_id`s
- [ ] Deterministic risk engine with unit tests; thresholds cite their agronomy source
- [ ] Gemini agent loop: plans which tools to call, then calls `submit_advisory`
- [ ] Gate: schema, citation existence, number grounding, risk-level agreement and missing-data
      disclosure checks; diff-based repair, at most 2 retries, then a flagged engine fallback
- [ ] Live **agent trace** streamed to the UI over SSE: tool calls, latencies, gate verdicts, repairs
- [ ] Advisory card: actions, risk chips, source chips (click a chip to see the raw value and
      provider)
- [ ] Data panels: 16-day forecast chart, NDVI time-series chart, mandi comparison table
- [ ] Languages: English, Hindi and Marathi tested; Gemini handles others
- [ ] Voice output (Gemini TTS), falling back to the browser's speechSynthesis
- [ ] Voice input (recorded audio sent to Gemini audio understanding)
- [ ] Edge cases handled gracefully: ocean or out-of-India pin, unknown crop, future sowing date,
      every source down, cloudy satellite window, empty mandi data, prompt injection in the
      question, LLM quota or timeout
- [ ] Deployed at a public URL; README with an architecture diagram; deck; demo script

### P1: ship if time allows

- [ ] "Watch my field": saved field plus a re-check endpoint that produces proactive alerts
      (in-app inbox; Telegram bot if a token is available)
- [ ] Eval report: 12 real (location, crop, question) cases; gate first-pass rate, repairs,
      fallbacks and latency
- [ ] NDVI thumbnail of the plot (a coloured PNG of the 10 m window)
- [ ] Multi-field view for FPOs (list of fields sorted by risk)

### P2: roadmap only (in the deck, not built)

- WhatsApp / IVR channel; KVK expert escalation; crop insurance (PMFBY) claim evidence pack built
  from the NDVI history; IMD block-level nowcasts; on-device small model for offline use.

### Non-goals

- Pesticide or fertiliser **dosage** prescriptions. The agent names the action class and refers to
  the KVK or label; the gate enforces this.
- Yield prediction in tonnes; we don't have ground-truth data to validate it, so we won't claim it.
- Accounts and auth. A field profile lives in the browser (localStorage), and watched fields sit in
  server SQLite.

## 4. Hard constraints (from the Forge rules)

| Rule | How we comply |
|---|---|
| **No dummy data** (instant DQ) | Every displayed value comes from a live API call (cached up to a short TTL). No JSON fixtures in the app path. Test fixtures live only under `tests/` and are never imported by the app. Agronomy *thresholds* are reference knowledge and cite FAO-56 or IMD; they are not data. |
| Live demo must not crash (30 pts) | Fallback chains, timeouts, a circuit breaker, an engine-only fallback when the LLM fails, and a UI error boundary |
| Core logic built in the window | Fresh repo created 2026-10-31; commits timestamped |
| Must explain the code | Plain modules, one responsibility each; `docs/ARCHITECTURE.md` explains the data flow |
| Public repo, README, diagram | Mermaid diagram in the README; repo made public at submission |

## 5. Rubric mapping

| Pillar | Points | What earns it here |
|---|---|---|
| Technical depth | 20 | Sentinel-2 COG window reads with an SCL cloud mask (real geospatial work), provider fallback chains, a TTL cache, a typed tool layer and tests |
| AI reasoning & agentic | 25 | The model chooses tools for each question; the gate catches hallucinations and the model self-corrects from a diff; tool errors are handled; source attribution |
| Impact & USP | 25 | Field-level, voice in Indian languages, actions with ₹ and mm figures; the six USPs above |
| Live demo & robustness | 30 | Live trace on screen, the edge-case list above, a degraded mode that still answers |

## 6. Success metrics (measured, reported in the README)

- p50 time to a full advisory under 20 s (cold cache); to first trace event under 1 s
- Gate first-pass rate and repair success rate across the eval set; 0 ungrounded numbers shipped
- 100% of shown numbers carry a source chip
- All P0 edge cases demonstrably handled

## 7. Risks

| Risk | Mitigation |
|---|---|
| Open-Meteo per-IP daily limit (already hit locally on 2026-10-31) | MET Norway forecast as a fallback; cache; NASA POWER for history |
| SoilGrids 503s (seen 2026-10-31) | Short timeout; fall back to Open-Meteo soil moisture only; disclose it |
| Gemini free-tier rate limits during judging | Engine-only fallback advisory (flagged); cache identical requests; config-driven model choice |
| Hosting cold start | Hugging Face Spaces Docker (stays warm for 48 h); warm it up before judging |
| Cloud cover blocks NDVI in monsoon | Look back 90 days, mask with SCL, report "last clear view: date"; never interpolate silently |
| Mandi data sparse for some crops or states | Widen the search from district to state to nearby states; say what was searched |
