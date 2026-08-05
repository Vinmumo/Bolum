"""Tiny in-process TTL cache + per-key throttle.

For a single-user personal tool an in-memory cache is plenty and keeps us off
the provider's rate limit: team stats don't change hour to hour, so re-fetching
them on every page load would just burn quota. Swap for Redis later if this ever
runs multi-process (the interface is deliberately small).
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._last_call: dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if time.time() >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def get_or_set(self, key: str, ttl: int, producer: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = producer()
        self.set(key, value, ttl)
        return value

    def throttle(self, throttle_key: str, min_interval: float) -> None:
        """Block just long enough that calls under `throttle_key` are spaced
        at least `min_interval` seconds apart. Cheap politeness for the API."""
        if min_interval <= 0:
            return
        with self._lock:
            now = time.time()
            last = self._last_call.get(throttle_key, 0.0)
            wait = (last + min_interval) - now
            if wait > 0:
                time.sleep(wait)
            self._last_call[throttle_key] = time.time()

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._last_call.clear()


# Process-wide singleton.
cache = TTLCache()
