"""Shared HTTP access for every data source: timeouts, a per-provider circuit breaker and the TTL cache.

Retries are deliberately off: each source module owns its fallback chain, so a failing provider
costs one timeout, not three.
"""

import time
from dataclasses import dataclass
from typing import Any

import httpx

from .cache import TTLCache
from .config import settings

_client: httpx.AsyncClient | None = None
cache = TTLCache(settings.cache_path)

BREAKER_THRESHOLD = 3
BREAKER_COOLDOWN_S = 300


class SourceError(Exception):
    """An upstream provider failed. The message is safe to show to the user and the model."""

    def __init__(self, provider: str, message: str):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.message = message


@dataclass
class Fetched:
    data: Any
    provider: str
    url: str
    fetched_at: float
    cached: bool


class _Breaker:
    def __init__(self) -> None:
        self.failures: dict[str, int] = {}
        self.open_until: dict[str, float] = {}

    def check(self, provider: str) -> None:
        if self.open_until.get(provider, 0) > time.time():
            raise SourceError(provider, "temporarily skipped after repeated failures")

    def ok(self, provider: str) -> None:
        self.failures[provider] = 0

    def fail(self, provider: str) -> None:
        n = self.failures.get(provider, 0) + 1
        self.failures[provider] = n
        if n >= BREAKER_THRESHOLD:
            self.open_until[provider] = time.time() + BREAKER_COOLDOWN_S
            self.failures[provider] = 0


breaker = _Breaker()


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20),
        )
    return _client


def display_url(url: str, params: dict | list | None) -> str:
    """URL shown as a source link. Strips API keys."""
    if not params:
        return url
    items = params.items() if isinstance(params, dict) else params
    safe = [(k, v) for k, v in items if "key" not in k.lower()]
    return str(httpx.URL(url, params=safe))


async def get_json(
    provider: str,
    url: str,
    params: dict | list[tuple[str, str]] | None = None,  # a list allows repeated keys
    ttl_s: float = 3600,
    timeout_s: float | None = None,
    method: str = "GET",
    json_body: Any = None,
    validate=None,
    headers: dict | None = None,  # not part of the cache key; never put data-changing values here
) -> Fetched:
    """Fetch JSON with cache and breaker. `validate(data)` may raise ValueError to reject a 200 response."""
    key = TTLCache.key(provider, method, url, params, json_body)
    hit = cache.get(key)
    shown = display_url(url, params)
    if hit is not None:
        return Fetched(hit[0], provider, shown, hit[1], True)

    breaker.check(provider)
    try:
        resp = await client().request(
            method, url, params=params, json=json_body, headers=headers, timeout=timeout_s or settings.http_timeout_s
        )
    except httpx.TimeoutException:
        breaker.fail(provider)
        raise SourceError(provider, "timed out")
    except httpx.HTTPError as e:
        breaker.fail(provider)
        detail = str(e).strip()[:90]
        raise SourceError(provider, f"network error ({type(e).__name__}{': ' + detail if detail else ''})")

    if resp.status_code != 200:
        breaker.fail(provider)
        detail = "rate limit reached" if resp.status_code == 429 else f"HTTP {resp.status_code}"
        raise SourceError(provider, detail)
    try:
        data = resp.json()
        if validate:
            validate(data)
    except ValueError as e:
        breaker.fail(provider)
        raise SourceError(provider, f"unexpected response ({e})" if str(e) else "unexpected response")

    breaker.ok(provider)
    fetched_at = cache.set(key, data, ttl_s)
    return Fetched(data, provider, shown, fetched_at, False)
