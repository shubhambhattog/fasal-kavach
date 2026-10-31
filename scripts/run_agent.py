"""Run one advisory from the command line and print the event stream. Dev tool, uses live APIs.

    uv run python ../scripts/run_agent.py --lat 20.0868 --lon 74.1278 --crop onion --sown 2026-09-15 --lang mr "question"
"""

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import agent  # noqa: E402
from app.evidence import Field  # noqa: E402
from app.sources import geo  # noqa: E402


async def main(a):
    place = await geo.reverse(a.lat, a.lon)
    f = Field(a.lat, a.lon, a.crop, date.fromisoformat(a.sown) if a.sown else None, a.lang, place["place"], place["district"], place["state"])
    async for ev in agent.run(agent.Request(f, a.question, a.model)):
        kind = ev["event"]
        if kind == "tool_end":
            print(f"  ← {ev['tool']} {ev['status']} {ev['ms']}ms facts={ev['n_facts']} {ev['notes'][:1]}")
        elif kind == "tool_start":
            print(f"  → {ev['tool']} {ev['args']}")
        elif kind == "llm_end":
            print(f"  LLM turn {ev['turn']} {ev['ms']}ms in={ev['tokens_in']} out={ev['tokens_out']} thought={ev['tokens_thought']}")
        elif kind == "llm_start":
            pass
        elif kind == "thought":
            print(f"  💭 {ev['text'][:200]!r}")
        elif kind == "gate":
            print(f"  GATE attempt {ev['attempt']} ok={ev['ok']} {json.dumps(ev['problems'], ensure_ascii=False)[:600]}")
        elif kind == "advisory":
            print(json.dumps(ev["advisory"], ensure_ascii=False, indent=1)[:2500])
            print("signals:", [(s["type"], s["level"]) for s in ev["signals"]])
        else:
            print(kind, {k: v for k, v in ev.items() if k not in ("event", "t", "field")})


p = argparse.ArgumentParser()
p.add_argument("question")
p.add_argument("--lat", type=float, default=20.0868)
p.add_argument("--lon", type=float, default=74.1278)
p.add_argument("--crop", default="onion")
p.add_argument("--sown", default="2026-09-15")
p.add_argument("--lang", default="en")
p.add_argument("--model", default="gemini-3.5-flash-lite")
asyncio.run(main(p.parse_args()))
