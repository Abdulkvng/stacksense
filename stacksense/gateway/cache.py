"""
Semantic Cache - Intelligent Response Caching

Caches LLM responses with semantic similarity matching:
- Hash-based exact match caching
- Semantic similarity for near-matches
- TTL-based expiration
- Cache hit tracking
"""

from typing import Dict, Any, Optional, List
import hashlib
import json
import time
from collections import OrderedDict

from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class SemanticCache:
    """
    Intelligent caching for LLM responses.

    Features:
    - Exact match caching (hash-based)
    - Semantic similarity matching (optional)
    - LRU eviction policy
    - TTL-based expiration
    - Cache statistics
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize semantic cache.

        Args:
            max_size: Maximum number of cached entries
            default_ttl: Default time-to-live in seconds (1 hour default)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl

        # Cache storage: key -> {"response": ..., "expires_at": ..., "created_at": ...}
        self.cache = OrderedDict()

        # Cache statistics
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "total_requests": 0}

        logger.info(f"Semantic Cache initialized (max_size={max_size}, ttl={default_ttl}s)")

    def get(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached response.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached response or None if not found/expired
        """
        self.stats["total_requests"] += 1

        # Check if key exists
        if cache_key not in self.cache:
            self.stats["misses"] += 1
            return None

        # Check if expired
        entry = self.cache[cache_key]
        if time.time() > entry["expires_at"]:
            # Expired, remove it
            del self.cache[cache_key]
            self.stats["misses"] += 1
            logger.debug(f"Cache miss (expired): {cache_key[:16]}...")
            return None

        # Cache hit - move to end (LRU)
        self.cache.move_to_end(cache_key)
        self.stats["hits"] += 1

        logger.debug(f"Cache hit: {cache_key[:16]}...")
        return entry["response"]

    def set(self, cache_key: str, response: Any, ttl: Optional[int] = None):
        """
        Store response in cache.

        Args:
            cache_key: Cache key
            response: Response to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl

        # Check if we need to evict
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            # Evict oldest (first item in OrderedDict)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.stats["evictions"] += 1
            logger.debug(f"Cache eviction: {oldest_key[:16]}...")

        # Store in cache
        self.cache[cache_key] = {
            "response": response,
            "expires_at": expires_at,
            "created_at": time.time(),
        }

        # Move to end (most recently used)
        self.cache.move_to_end(cache_key)

        logger.debug(f"Cache set: {cache_key[:16]}... (ttl={ttl}s)")

    def generate_key(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        """
        Generate cache key from request parameters.

        Creates deterministic hash from:
        - Messages content
        - Model name
        - Additional parameters (temperature, etc.)

        Args:
            messages: Chat messages
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Cache key (hex string)
        """
        # Create deterministic representation
        cache_input = {
            "messages": [{"role": m.get("role"), "content": m.get("content")} for m in messages],
            "model": model,
            "params": {
                k: v
                for k, v in kwargs.items()
                if k in ["temperature", "max_tokens", "top_p", "frequency_penalty"]
            },
        }

        # Generate hash
        cache_str = json.dumps(cache_input, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()

        return cache_hash

    def invalidate(self, cache_key: str) -> bool:
        """
        Remove specific entry from cache.

        Args:
            cache_key: Key to invalidate

        Returns:
            True if key was present, False otherwise
        """
        if cache_key in self.cache:
            del self.cache[cache_key]
            logger.debug(f"Cache invalidated: {cache_key[:16]}...")
            return True
        return False

    def clear(self):
        """Clear all cached entries."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared ({count} entries)")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: {
                "size": int,
                "max_size": int,
                "hits": int,
                "misses": int,
                "hit_rate": float,
                "evictions": int,
                "total_requests": int
            }
        """
        hit_rate = (
            self.stats["hits"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0
            else 0.0
        )

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.stats["evictions"],
            "total_requests": self.stats["total_requests"],
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items() if current_time > entry["expires_at"]
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def find_similar(
        self, messages: List[Dict[str, str]], model: str, similarity_threshold: float = 0.95
    ) -> Optional[Any]:
        """
        Find cached response with similar prompt.

        This is a placeholder for semantic similarity matching.
        In production, use embeddings + vector similarity.

        Args:
            messages: Query messages
            model: Model name
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Cached response if similar match found, None otherwise
        """
        # TODO: Implement with embeddings
        # For now, just do exact match via generate_key
        cache_key = self.generate_key(messages, model)
        return self.get(cache_key)

    def get_top_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recently used cache entries.

        Args:
            limit: Maximum number of entries

        Returns:
            List of cache entries with metadata
        """
        entries = []

        for i, (key, entry) in enumerate(reversed(list(self.cache.items()))):
            if i >= limit:
                break

            age = time.time() - entry["created_at"]
            ttl_remaining = max(0, entry["expires_at"] - time.time())

            entries.append(
                {
                    "key": key[:16] + "...",
                    "age_seconds": int(age),
                    "ttl_remaining": int(ttl_remaining),
                    "created_at": entry["created_at"],
                }
            )

        return entries
