"""
Redis cache service for the Python microservice.

Wraps redis-py with:
  - Graceful fallback to a plain dict if Redis is unavailable
  - Serialization via JSON
  - Typed get/set with optional TTL
  - Key namespacing: "pharmavisit:{namespace}:{hash}"
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

REDIS_URL  = os.getenv("REDIS_URL",  "redis://127.0.0.1:6379/1")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB",   1))   # DB 1 = microservice; DB 0 = Laravel

try:
    import redis as _redis_lib
    _client = _redis_lib.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    _client.ping()           # Verify connection on startup
    REDIS_AVAILABLE = True
    logger.info("[cache] Redis connected at %s:%s db=%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
except Exception as e:
    REDIS_AVAILABLE = False
    _client = None
    logger.warning("[cache] Redis unavailable (%s) — using in-memory fallback", e)

_memory_fallback: dict[str, Any] = {}


def _make_key(namespace: str, raw: str) -> str:
    h = hashlib.md5(raw.encode()).hexdigest()
    return f"pharmavisit:{namespace}:{h}"


def get(namespace: str, raw_key: str) -> Any | None:
    key = _make_key(namespace, raw_key)
    if REDIS_AVAILABLE and _client:
        try:
            val = _client.get(key)
            if val is not None:
                logger.debug("[cache] HIT  %s", key)
                return json.loads(val)
        except Exception as e:
            logger.warning("[cache] Redis GET error: %s", e)

    # In-memory fallback
    val = _memory_fallback.get(key)
    if val is not None:
        logger.debug("[cache] MEM-HIT %s", key)
    return val


def set(namespace: str, raw_key: str, value: Any, ttl_seconds: int | None = None) -> None:
    key = _make_key(namespace, raw_key)
    serialized = json.dumps(value)

    if REDIS_AVAILABLE and _client:
        try:
            if ttl_seconds:
                _client.setex(key, ttl_seconds, serialized)
            else:
                _client.set(key, serialized)
            logger.debug("[cache] SET  %s (ttl=%s)", key, ttl_seconds)
            return
        except Exception as e:
            logger.warning("[cache] Redis SET error: %s", e)

    # In-memory fallback (no TTL enforcement — OK for dev)
    _memory_fallback[key] = value


def delete(namespace: str, raw_key: str) -> None:
    key = _make_key(namespace, raw_key)
    if REDIS_AVAILABLE and _client:
        try:
            _client.delete(key)
        except Exception:
            pass
    _memory_fallback.pop(key, None)


def flush_namespace(namespace: str) -> int:
    """Delete all keys in a namespace. Returns count deleted."""
    pattern = f"pharmavisit:{namespace}:*"
    if REDIS_AVAILABLE and _client:
        try:
            keys = _client.keys(pattern)
            if keys:
                return _client.delete(*keys)
        except Exception as e:
            logger.warning("[cache] flush error: %s", e)
    # Memory fallback flush
    to_del = [k for k in _memory_fallback if k.startswith(f"pharmavisit:{namespace}:")]
    for k in to_del:
        del _memory_fallback[k]
    return len(to_del)


def status() -> dict:
    return {
        "redis_available": REDIS_AVAILABLE,
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT,
        "redis_db": REDIS_DB,
        "memory_fallback_keys": len(_memory_fallback),
    }
