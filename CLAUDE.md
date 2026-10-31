# Fasal Kavach

Field-level climate-risk agent for Indian farmers (Forge buildathon, Theme 2). Start with
`docs/PRD.md`, then `docs/ARCHITECTURE.md`, `docs/AGENT.md` and `docs/PLAN.md` (the build loop
works through its checklist).

## Hard rules
- **No dummy data in the app path.** Every displayed value comes from a live API (cached is fine).
  Fixtures live only in `tests/fixtures/` and are never imported by `backend/app`. Breaking this
  disqualifies the entry.
- When a source fails, return `status: unavailable` and disclose it. Never invent or interpolate
  values.
- The model writes the advisory and `gate.py` checks it. Don't let code silently overwrite model
  output except through the flagged fallback.
- Use the cheapest model (`gemini-3.5-flash-lite`) for tests and dev runs; prefer the fake-model
  tests (zero API cost).
- Keep code plain and explainable: the owner must defend every module in judging.
- Commit at milestones (allowed by the owner). Never commit `.env`.
- Log decisions and failed first attempts in `docs/DECISIONS.md`.

## Run
```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm i && pnpm dev          # proxies /api to :8000
cd backend && uv run pytest -q
```

## Machine notes
- git needs `DEVELOPER_DIR=/Library/Developer/CommandLineTools` (Xcode licence not accepted).
- In zsh, brace variables before a colon: `${m}:generateContent`.
