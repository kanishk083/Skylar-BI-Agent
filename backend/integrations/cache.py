"""
cache.py — P16: TTL LRU cache
get_stale() added for Patch 2 (stale cache fallback on Monday.com 429/timeout)
"""
import time
from collections import OrderedDict
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100) -> None:
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, ts = self._store[key]
        if time.time() - ts > self.ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def get_stale(self, key: str) -> Optional[Any]:
        """Return value even if TTL expired — used as fallback on API failure (Patch 2)."""
        if key not in self._store:
            return None
        value, _ = self._store[key]
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, time.time())
        if len(self._store) > self.max_size:
            self._store.popitem(last=False)
