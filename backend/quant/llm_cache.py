"""
LLM inference cache with SQLite storage.

Caches LLM analysis results based on input JSON hash to avoid
redundant API calls. Target: 2s → 50ms for cache hits.

Features:
- SHA-256 hash of Layer2 JSON input as cache key
- TTL-based expiration (default 24 hours)
- SQLite storage for persistence across restarts
- Automatic cleanup of expired entries
- Cache hit/miss statistics
"""

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# Default TTL: 24 hours
_DEFAULT_TTL_SECONDS = 86400
# Max cache entries before cleanup
_MAX_CACHE_SIZE = 10000


class LLMCache:
    """SQLite-backed LLM inference cache.

    Usage:
        cache = LLMCache()
        result = cache.get(layer2_json)
        if result is None:
            result = await call_llm(layer2_json)
            cache.set(layer2_json, result)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ):
        self._ttl = ttl_seconds
        self._db_path = db_path or str(
            Path(settings.db_path).parent / "llm_cache.db"
        )
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite cache database."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    input_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_cache_expires
                ON llm_cache (expires_at)
            """)
            conn.commit()
            conn.close()
            logger.info(f"LLM cache initialized at: {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM cache: {e}")

    def get(self, input_data: dict) -> Optional[dict]:
        """Look up cached result for given input.

        Args:
            input_data: Layer2 JSON input dict.

        Returns:
            Cached result dict if found and not expired, None otherwise.
        """
        cache_key = self._compute_key(input_data)

        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT result_json, expires_at FROM llm_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            conn.close()

            if row is None:
                self._stats["misses"] += 1
                logger.debug(f"LLM cache MISS: {cache_key[:16]}...")
                return None

            result_json, expires_at = row

            # Check expiration
            if time.time() > expires_at:
                self._stats["misses"] += 1
                self._delete_key(cache_key)
                logger.debug(f"LLM cache EXPIRED: {cache_key[:16]}...")
                return None

            # Cache hit
            self._stats["hits"] += 1
            self._increment_hits(cache_key)
            logger.debug(f"LLM cache HIT: {cache_key[:16]}...")

            return json.loads(result_json)

        except Exception as e:
            logger.error(f"LLM cache lookup failed: {e}")
            self._stats["misses"] += 1
            return None

    def set(self, input_data: dict, result: dict) -> bool:
        """Store result in cache for given input.

        Args:
            input_data: Layer2 JSON input dict.
            result: LLM analysis result to cache.

        Returns:
            True if stored successfully, False otherwise.
        """
        cache_key = self._compute_key(input_data)
        input_hash = self._compute_hash(json.dumps(input_data, sort_keys=True))
        now = time.time()
        expires_at = now + self._ttl

        try:
            # Check cache size and cleanup if needed
            self._cleanup_if_needed()

            conn = sqlite3.connect(self._db_path)
            conn.execute(
                """INSERT OR REPLACE INTO llm_cache
                   (cache_key, input_hash, result_json, created_at, expires_at, hit_count)
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (cache_key, input_hash, json.dumps(result), now, expires_at),
            )
            conn.commit()
            conn.close()

            self._stats["sets"] += 1
            logger.debug(f"LLM cache SET: {cache_key[:16]}...")
            return True

        except Exception as e:
            logger.error(f"LLM cache set failed: {e}")
            return False

    def invalidate(self, input_data: dict) -> bool:
        """Remove a specific entry from cache.

        Args:
            input_data: The input dict to invalidate.

        Returns:
            True if entry was found and removed.
        """
        cache_key = self._compute_key(input_data)
        return self._delete_key(cache_key)

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed.
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM llm_cache")
            count = cursor.fetchone()[0]
            conn.execute("DELETE FROM llm_cache")
            conn.commit()
            conn.close()
            logger.info(f"LLM cache cleared: {count} entries removed")
            return count
        except Exception as e:
            logger.error(f"LLM cache clear failed: {e}")
            return 0

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        try:
            now = time.time()
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM llm_cache WHERE expires_at < ?", (now,)
            )
            count = cursor.fetchone()[0]
            conn.execute("DELETE FROM llm_cache WHERE expires_at < ?", (now,))
            conn.commit()
            conn.close()

            self._stats["evictions"] += count
            logger.info(f"LLM cache cleanup: {count} expired entries removed")
            return count
        except Exception as e:
            logger.error(f"LLM cache cleanup failed: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM llm_cache")
            total_entries = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(*) FROM llm_cache WHERE expires_at < ?",
                (time.time(),),
            )
            expired_entries = cursor.fetchone()[0]
            conn.close()

            hit_rate = 0.0
            total_requests = self._stats["hits"] + self._stats["misses"]
            if total_requests > 0:
                hit_rate = self._stats["hits"] / total_requests * 100.0

            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "active_entries": total_entries - expired_entries,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "evictions": self._stats["evictions"],
                "hit_rate_pct": round(hit_rate, 2),
                "ttl_seconds": self._ttl,
                "db_path": self._db_path,
            }
        except Exception as e:
            logger.error(f"LLM cache stats failed: {e}")
            return {"error": str(e)}

    def _compute_key(self, input_data: dict) -> str:
        """Compute cache key from input data."""
        # Normalize JSON by sorting keys
        normalized = json.dumps(input_data, sort_keys=True, ensure_ascii=True)
        return self._compute_hash(normalized)

    @staticmethod
    def _compute_hash(data: str) -> str:
        """Compute SHA-256 hash of string data."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _delete_key(self, cache_key: str) -> bool:
        """Delete a cache entry by key."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "DELETE FROM llm_cache WHERE cache_key = ?", (cache_key,)
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"LLM cache delete failed: {e}")
            return False

    def _increment_hits(self, cache_key: str) -> None:
        """Increment hit counter for a cache entry."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "UPDATE llm_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                (cache_key,),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Non-critical operation

    def _cleanup_if_needed(self) -> None:
        """Cleanup expired entries if cache is too large."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM llm_cache")
            count = cursor.fetchone()[0]
            conn.close()

            if count >= _MAX_CACHE_SIZE:
                self.cleanup_expired()
        except Exception:
            pass


# ── Integration with llm_analyzer ───────────────────────────────────────────

_cache_instance: Optional[LLMCache] = None


def get_cache() -> LLMCache:
    """Get or create the global LLM cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache()
    return _cache_instance


async def cached_llm_analyze(data: Optional[dict] = None) -> dict:
    """LLM analysis with caching.

    Drop-in replacement for llm_analyzer.analyze() that adds caching.
    On cache hit, returns cached result in ~1ms instead of ~2s API call.

    Args:
        data: Same input as llm_analyzer.analyze()

    Returns:
        LLM analysis result dict.
    """
    if not data:
        from backend.quant.llm_analyzer import _DEFAULT_RESULT
        import copy
        return copy.deepcopy(_DEFAULT_RESULT)

    cache = get_cache()

    # Try cache first
    cached_result = cache.get(data)
    if cached_result is not None:
        cached_result["details"] = cached_result.get("details", {})
        cached_result["details"]["cache_hit"] = True
        return cached_result

    # Cache miss: call actual LLM analyzer
    from backend.quant.llm_analyzer import analyze as llm_analyze
    result = await llm_analyze(data)

    # Store in cache
    cache.set(data, result)

    return result
