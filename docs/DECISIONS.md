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
- **2026-10-31: One container** (FastAPI serves the built React app) on HF Spaces. One URL, no
  CORS, no cold-start pairing between two hosts.
- **2026-10-31: Voice through Gemini** (transcribe and TTS models on the same key), with browser
  speech as the fallback. Free, one key, good Indic quality. Sarvam and Bhashini need extra signup.
- **2026-10-31: Location and crop come from the profile, not model arguments.** This stops the
  model from querying the wrong field.

## What failed first

| # | Tried | Result | Why | Now |
|---|---|---|---|---|
| 1 | Open-Meteo forecast as the only weather source | HTTP 429 "Daily API request limit exceeded" from the build machine on day 0 | Free tier is limited per IP | MET Norway fallback; cache |
| 2 | SoilGrids as the only soil source | HTTP 503 | The service is flaky | Short timeout; fall back to soil moisture; disclose |
| 3 | Gemini model probe in zsh using `"$m:generateContent"` | 404 for every model | zsh treated `:g` as a parameter modifier and mangled the URL | Use `${m}`; the SDK avoids this in the app |
