# Pitch deck (6 slides)

Source text for the deck. The Gamma version is generated from this file; keep the two in sync.

## 1. Fasal Kavach: a crop shield for every field
- A field-level climate-risk agent for Indian farmers
- Live satellite, weather and mandi data → advice in the farmer's language, by voice
- Forge Gen AI Buildathon · Theme 2: Climate, Resource Infrastructure & Supply Resilience
- Shubham Bhatt, NIT Delhi (solo)

## 2. The problem: weekly decisions made blind
- 146 M holdings, 86% under 2 ha (Agriculture Census 2015-16)
- Every week: irrigate? spray? delay urea? harvest? sell where?
- Forecasts are district-level; mandi prices are hearsay; crop health is invisible
- The data exists, but it's spread across five portals, in English, with no "what to do"

## 3. The solution: pin, ask, act
- Pin the field, pick the crop, ask by voice in Marathi, Hindi or 7 more languages
- The agent chooses the live data it needs: forecast, Sentinel-2 NDVI of *that* field, rain vs
  20-year normal, soil, mandi prices, GDACS alerts, FAO-56 water balance
- It answers with timed actions: "Irrigate ~19 mm over 7 days in 2-3 turns", "Sell at Chandwad,
  ₹4,670/q, 23 km"
- Every number is a clickable source chip, and the answer is spoken back

## 4. How it works: the model writes, code checks
- Gemini function-calling agent → tool layer (8 tools, provider fallback chains, TTL cache)
- Evidence store: every fact has an id, provider, URL and fetch time
- Deterministic risk engine (FAO-56, IMD thresholds), private to the gate
- **Gate:** 7 checks (grounded numbers incl. Indic digits, real citations, risk agreement,
  data-gap disclosure, no chemical doses, language). It returns a diff and the model repairs
  itself (≤ 2), or a labelled engine fallback ships
- Sentinel-2 COG window reads with SCL cloud masking, no imagery download
- Eval on live data, 12 cases, 10 states, 8 languages: first pass 4/12 → 10/12 across three iterations; every failure caught and fixed by the model, 0 fallbacks
- 45 offline tests + CI; one Docker container

## 5. Why it's different
- Field-level, not district-level (10 m pixels, exact-point forecast)
- Traceable: nothing is answered from model memory
- Self-correcting on screen: hallucinations are caught before the farmer hears them
- Honest under failure: a source down means it's disclosed and confidence drops; the LLM down
  means the engine still answers
- Voice-first, in Indian languages

## 6. Roadmap and demo summary
- Next: WhatsApp and IVR, proactive alerts for watched fields, KVK escalation
- PMFBY crop-insurance evidence packs built from the NDVI history
- IMD block-level nowcasts, and an offline on-device model
- Live demo: Nashik onion field → Marathi voice question → live trace → gate repair → spoken advice
