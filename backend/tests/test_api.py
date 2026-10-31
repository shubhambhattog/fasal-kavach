"""HTTP-level validation (no network: every case fails before any data source is called)."""

import ast
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.sources.satellite import _colour

client = TestClient(app)
APP_DIR = Path(__file__).resolve().parents[1] / "app"


def test_outside_india_is_rejected():
    r = client.post("/api/advise", json={"lat": 51.5, "lon": -0.1, "crop": "onion", "question": "hello"})
    assert r.status_code == 422 and r.json()["code"] == "outside_india"


def test_future_sowing_date_is_rejected():
    future = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/api/advise", json={"lat": 20.08, "lon": 74.12, "crop": "onion", "sowing_date": future, "question": "hello"})
    assert r.json()["code"] == "future_sowing"


def test_unsupported_language_is_rejected():
    r = client.post("/api/advise", json={"lat": 20.08, "lon": 74.12, "crop": "onion", "language": "fr", "question": "hello"})
    assert r.json()["code"] == "language"


def test_risk_scan_rejects_outside_india():
    assert client.post("/api/risk", json={"lat": 40.7, "lon": -74.0, "crop": "wheat"}).status_code == 422


def test_crops_endpoint_lists_reference_table():
    keys = {c["key"] for c in client.get("/api/crops").json()}
    assert {"onion", "wheat", "rice", "cotton"} <= keys


def test_ndvi_colour_ramp_runs_bare_to_dense():
    import numpy as np

    rgb = _colour(np.array([[-0.1, 0.8]]))
    bare, dense = rgb[0, 0], rgb[0, 1]
    assert bare[0] > bare[1]  # brown: more red than green
    assert dense[1] > dense[0]  # green


def test_app_never_imports_test_fixtures_or_ships_data_files():
    """Forge rule: no hardcoded or mock data in the app path."""
    for py in APP_DIR.rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                assert not any("tests" in n or "fixture" in n for n in names), f"{py} imports test code"
    data_files = [p for p in APP_DIR.rglob("*") if p.suffix in {".json", ".csv", ".geojson", ".parquet", ".pkl"}]
    assert data_files == [], f"data files in the app package: {data_files}"
