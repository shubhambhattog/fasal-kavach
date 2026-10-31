# Decisions and what failed first

Append-only. Each entry: date, decision, why, alternatives rejected.

## Decisions

- **2026-10-31: Theme 2, merging problems 1 and 2.** Theme 2 has the richest stable, free, live
  public data in India, and the live demo is worth 30 pts. Rejected Theme 1's browser agent
  (CAPTCHAs and OTPs make the live demo fragile) and the logistics swarm (no real supplier APIs,
  so we'd risk breaking the dummy-data rule).
- **2026-10-31: Gemini** (owner's choice). Agent: `gemini-3.8-flash`; tests: `gemini-3.5-flash-lite`.
- **2026-10-31: Model writes, code checks.** A gate checks the model against a deterministic
  engine, from loadout LEARNINGS (Oct 2026 Orchestrate: a decorative LLM cost points; the winning
  gated agent first-passed 503 cases).
- **2026-10-31: One container** (FastAPI serves the built React app). One URL, no CORS, no
  cold-start pairing between two hosts. **2026-11-01: hosted on Render** (free Docker web
  service, Singapore), because HF Docker Spaces now need PRO.
- **2026-11-01: Mumbai relay for data.gov.in.** The owner chose a Vercel `bom1` function over
  leaving mandi prices unavailable on the live site. It's allow-listed to one dataset and
  secret-protected, and citations still point at data.gov.in.
- **2026-10-31: Voice through Gemini** (transcribe and TTS models on the same key), with browser
  speech as the fallback. Free, one key, good Indic quality. Sarvam and Bhashini need extra signup.
- **2026-10-31: Location and crop come from the profile, not model arguments.** This stops the
  model from querying the wrong field.
- **2026-11-01: Calculators are tools, but risk levels stay private.** Crop stage and the FAO-56
  water balance are tools, because LLM arithmetic is unreliable and farmers need exact mm. The
  engine's risk *levels* are never shown to the model, so the gate's check stays independent.
- **2026-11-01: `ANY` function-calling mode.** The model must call a tool every turn and can only
  finish through `submit_advisory`, so there are no free-text answers that bypass the gate.
- **2026-11-01: Kept `gemini-3.8-flash`.** On the same Hindi question it passed first time;
  `gemini-3.5-flash` needed one citation repair. Latency was similar (~19 s warm, ~38 s cold);
  the time goes on Sentinel-2 reads (~8 s) and the writing turn (~8 s).

## What failed first

| # | Tried | Result | Why | Now |
|---|---|---|---|---|
| 1 | Open-Meteo forecast as the only weather source | HTTP 429 "Daily API request limit exceeded" from the build machine on day 0 | Free tier is limited per IP | MET Norway fallback; cache |
| 2 | SoilGrids as the only soil source | HTTP 503 | The service is flaky | Short timeout; fall back to soil moisture; disclose |
| 3 | Gemini model probe in zsh using `"$m:generateContent"` | 404 for every model | zsh treated `:g` as a parameter modifier and mangled the URL | Use `${m}`; the SDK avoids this in the app |
| 4 | Applying the STAC asset's −0.1 BOA offset to Sentinel-2 DNs | NDVI 1.4-3.2 (impossible) | Element84 had already removed the offset (`earthsearch:boa_offset_applied: true`) | Apply the offset only when that flag is false; NDVI now 0.60-0.72 for the Niphad onion field |
| 5 | Allowing every day-of-month in the evidence as a grounded number | An invented "30 °C" would pass because 30 Oct was a date | Too permissive | Strip date and day-count phrases (en/hi/mr months) before checking; auto-allow only integers ≤ 3 |
| 6 | Mandi rows with `id: mandi.<slug>` in the model view | The model cited `mandi.lasalgaon`; the gate rejected the unknown id and a repair cost ~8 s | The id looked like a fact id but wasn't one | Explicit `price_id` / `distance_id` |
| 7 | `.on()` chained on MapLibre 6 objects | `addControl` got a Subscription and the map crashed | MapLibre 6 `.on()` returns a Subscription, not `this` | Create the control, then subscribe |
| 8 | MapLibre container with Tailwind `absolute inset-0` | Map height 0 px | MapLibre's unlayered `.maplibregl-map {position: relative}` beats Tailwind 4's layered utilities | Inline position style |
| 9 | Reading `resp.text` from `gemini-3.5-transcribe` | Empty transcript | The speech model returns an `audio_transcription` part, not text | Read `part.audio_transcription.text`; fall back to the cheap model with a transcribe prompt |
| 10 | TTS prompt "Read this aloud in Marathi, in a warm voice…: <text>" | The model *spoke the instruction*; caught when the browser voice test transcribed it back | The TTS model treats the whole prompt as speech | Send only the advice text (audio went from 14 s to 6.4 s) |
| 11 | Sending the browser's MediaRecorder WebM straight to Gemini | Not in Gemini's documented audio formats | Format risk across browsers | Decode in the browser and re-encode as 16 kHz mono WAV (`frontend/src/wav.ts`) |
| 12 | Eval v1: model not told the published thresholds | 4/12 first-pass; 6 of 8 failures were `risk_agreement` (the model under-stated a risk) | The model couldn't know where "moderate" starts | v2 adds IMD/FAO-56 reference thresholds to tool notes; the engine's verdicts stay private (see EVAL.md) |
| 13 | `python:3.12-slim` Docker image with the rasterio wheel | Every Sentinel-2 read failed in the container; the tool reported "10 scene reads failed" | The bundled GDAL needs `libexpat.so.1`, which the slim image lacks; the ImportError was swallowed per scene | `apt-get install libexpat1`; failure notes now include the exception type. Found by smoke-testing the image before deploying |
| 14 | Engine flagged water need for rice 21 days and soybean 1 day before harvest | The gate forced the model to state a risk the model had rightly left out (eval v2) | Irrigation is normally stopped 2-3 weeks before harvest | Final dry-down rule (≤ 21 days to harvest: low); a gate disagreement exposed an *engine* bug, not a model one |
| 15 | Calling data.gov.in from the hosted app (Render, Singapore) | `ConnectError: All connection attempts failed` on every call; mandi prices unavailable on the live URL | data.gov.in refuses foreign datacenter IPs (works from India) | Relay in Vercel's Mumbai region, verified egress `x-relay-region: bom1` |
| 16 | Open-Meteo from shared hosting IPs | `429 Daily API request limit exceeded` (laptop on day 0, then Render) | Free tier is limited per IP and the IP is shared | MET Norway fallback for the forecast, NASA POWER for soil wetness; both disclosed |
