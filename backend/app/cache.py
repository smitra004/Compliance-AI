"""Redis cache layer. Falls back to a process-local dict when `REDIS_URL`
isn't set or Redis is unreachable, so nothing in the app hard-depends on it
— consistent with the project's zero-config demo philosophy."""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from app import config

_memory_store: dict[str, tuple[float, Any]] = {}
_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if not config.REDIS_CONFIGURED:
        return None
    try:
        import redis
        client = redis.from_url(config.REDIS_URL, socket_connect_timeout=1.5, decode_responses=True)
        client.ping()
        _redis_client = client
    except Exception as e:  # noqa: BLE001 — any Redis failure just disables caching
        print(f"[cache] Redis unavailable ({e}); falling back to in-memory cache")
        _redis_client = None
    return _redis_client


def get(key: str) -> Optional[Any]:
    r = _get_redis()
    if r is not None:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    entry = _memory_store.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if expires_at and expires_at < time.time():
        _memory_store.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    r = _get_redis()
    if r is not None:
        r.set(key, json.dumps(value), ex=ttl_seconds)
        return
    _memory_store[key] = (time.time() + ttl_seconds if ttl_seconds else 0, value)


def invalidate_prefix(prefix: str) -> None:
    r = _get_redis()
    if r is not None:
        for k in r.scan_iter(f"{prefix}*"):
            r.delete(k)
        return
    for k in [k for k in _memory_store if k.startswith(prefix)]:
        _memory_store.pop(k, None)


def backend_name() -> str:
    return "redis" if _get_redis() is not None else "in-memory"
