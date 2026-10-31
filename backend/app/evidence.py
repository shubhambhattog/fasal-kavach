"""Facts gathered from live sources during one request.

Every number the agent may say must exist here as a Fact with a stable id such as
`wx.rain.2026-11-03` or `mandi.lasalgaon.modal`. The gate checks advisories against this store.
"""

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from .http import Fetched


@dataclass
class Field:
    """The farmer's plot. It comes from the request profile and the model can't change it."""

    lat: float
    lon: float
    crop: str
    sowing_date: date | None
    language: str
    place: str = ""
    district: str = ""
    state: str = ""


@dataclass
class Fact:
    id: str
    label: str
    value: float | str
    unit: str
    provider: str
    url: str
    fetched_at: float

    def compact(self) -> dict:
        v = round(self.value, 2) if isinstance(self.value, float) else self.value
        return {"id": self.id, "label": self.label, "value": v, "unit": self.unit}


@dataclass
class ToolResult:
    tool: str
    status: str  # ok | partial | unavailable
    providers_tried: list[str] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    series: dict[str, Any] = field(default_factory=dict)  # full data for UI charts, not sent to the model
    # A compact view for the model when listing every fact would waste context (e.g. a 16-day table
    # whose cells map to ids like wx.rain.<date>). All facts still go into the evidence store.
    model_view: dict[str, Any] | None = None

    def to_model(self) -> dict:
        out: dict[str, Any] = {"status": self.status, "providers_tried": self.providers_tried}
        if self.model_view is not None:
            out.update(self.model_view)
        else:
            out["facts"] = [f.compact() for f in self.facts]
        if self.notes:
            out["notes"] = self.notes
        return out

    def to_ui(self) -> dict:
        return {
            "tool": self.tool,
            "status": self.status,
            "providers_tried": self.providers_tried,
            "facts": [asdict(f) for f in self.facts],
            "notes": self.notes,
            "series": self.series,
        }


def fact(fid: str, label: str, value: float | str, unit: str, src: Fetched) -> Fact:
    return Fact(fid, label, value, unit, src.provider, src.url, src.fetched_at)


class EvidenceStore:
    def __init__(self) -> None:
        self.facts: dict[str, Fact] = {}
        self.results: list[ToolResult] = []

    def add(self, result: ToolResult) -> None:
        self.results.append(result)
        for f in result.facts:
            self.facts[f.id] = f

    def get(self, fid: str) -> Fact | None:
        return self.facts.get(fid)

    def numbers(self) -> list[tuple[str, float]]:
        return [(f.id, float(f.value)) for f in self.facts.values() if isinstance(f.value, (int, float))]

    def status_of(self, tool: str) -> str | None:
        for r in reversed(self.results):
            if r.tool == tool:
                return r.status
        return None
