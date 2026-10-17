"""
cache.py - Upstash Redis & In-Memory Fallback Caching Tier.

Provides edge-cached pre-computed daily percentile leaderboards and default team/player view payloads
to guarantee sub-50ms API response times.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryCache:
    """In-memory LRU/TTL cache fallback when remote Redis is not configured."""

    def __init__(self):
        # Key: str -> (value_str, expire_timestamp)
        self._store: Dict[str, Tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._store:
            val, expire = self._store[key]
            if expire == 0.0 or expire > time.time():
                return val
            del self._store[key]
        return None

    def set(self, key: str, value: str, ttl: int = 86400) -> None:
        expire = time.time() + ttl if ttl > 0 else 0.0
        self._store[key] = (value, expire)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class CacheClient:
    """
    Unified caching interface supporting Upstash Redis and In-Memory fallback.
    """

    def __init__(self):
        self.redis_client = None
        self.memory_cache = MemoryCache()
        self._init_redis()

    def _init_redis(self) -> None:
        redis_url = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL")
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
                self.redis_client.ping()
                logger.info("Connected to remote Redis cache: %s", redis_url.split("@")[-1])
            except Exception as e:
                logger.warning("Could not connect to Redis (%s). Using in-memory cache fallback.", e)
                self.redis_client = None
        else:
            logger.info("No remote REDIS_URL configured. Using high-performance in-memory cache tier.")

    def get_json(self, key: str) -> Optional[Any]:
        """Retrieves and deserializes JSON from cache."""
        try:
            raw = None
            if self.redis_client:
                try:
                    raw = self.redis_client.get(key)
                except Exception as e:
                    logger.debug("Redis read failed for %s: %s", key, e)
                    raw = self.memory_cache.get(key)
            else:
                raw = self.memory_cache.get(key)

            if raw is not None:
                return json.loads(raw)
        except Exception as e:
            logger.debug("Cache deserialization error for %s: %s", key, e)
        return None

    def set_json(self, key: str, value: Any, ttl: int = 86400) -> None:
        """Serializes and caches JSON value with TTL."""
        try:
            raw = json.dumps(value)
            if self.redis_client:
                try:
                    self.redis_client.set(key, raw, ex=ttl)
                except Exception as e:
                    logger.debug("Redis write failed for %s: %s", key, e)
            # Always update local memory cache for sub-millisecond local reads
            self.memory_cache.set(key, raw, ttl=ttl)
        except Exception as e:
            logger.warning("Cache serialization error for %s: %s", key, e)

    def delete(self, key: str) -> None:
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        self.memory_cache.delete(key)


# Singleton cache client instance
cache = CacheClient()
