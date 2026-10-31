"""SQLite TTL cache for upstream API responses.

A cache hit is still real data: the original fetch time is stored and shown in the UI.
"""

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class TTLCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, fetched_at REAL, expires_at REAL)"
            )
            self._conn.commit()

    @staticmethod
    def key(*parts: Any) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> tuple[Any, float] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value, fetched_at, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if not row or row[2] < time.time():
            return None
        return json.loads(row[0]), row[1]

    def set(self, key: str, value: Any, ttl_s: float) -> float:
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)",
                (key, json.dumps(value), now, now + ttl_s),
            )
            self._conn.commit()
        return now
