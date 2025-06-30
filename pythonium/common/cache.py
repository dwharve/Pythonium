"""
Caching mechanisms for the Pythonium framework.

This module provides various caching strategies and backends for
improving performance and reducing redundant operations.
"""

import asyncio
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from pythonium.common.base import BaseComponent
from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger
from pythonium.common.types import MetadataDict

logger = get_logger(__name__)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class CacheError(PythoniumError):
    """Base exception for cache operations."""

    pass


class CacheKeyError(CacheError):
    """Exception raised when cache key is invalid."""

    pass


class CacheMissError(CacheError):
    """Exception raised when cache miss occurs."""

    pass


class EvictionPolicy(Enum):
    """Cache eviction policies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL = "ttl"  # Time To Live based
    RANDOM = "random"


@dataclass
class CacheEntry(Generic[V]):
    """Represents a cache entry."""

    value: V
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl: Optional[timedelta] = None
    metadata: MetadataDict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.ttl is None:
            return False
        return datetime.utcnow() - self.created_at > self.ttl

    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100.0


class BaseCache(ABC, Generic[K, V]):
    """Abstract base class for cache implementations."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[timedelta] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._stats = CacheStats(max_size=max_size)
        self._lock = asyncio.Lock()

    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(self, key: K, value: V, ttl: Optional[timedelta] = None) -> None:
        """Set value in cache."""
        pass

    @abstractmethod
    def delete(self, key: K) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all values from cache."""
        pass

    @abstractmethod
    def keys(self) -> List[K]:
        """Get all keys in cache."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get current cache size."""
        pass

    def exists(self, key: K) -> bool:
        """Check if key exists in cache."""
        return self.get(key) is not None

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self._stats.size = self.size()
        return self._stats

    def _record_hit(self) -> None:
        """Record cache hit."""
        self._stats.hits += 1

    def _record_miss(self) -> None:
        """Record cache miss."""
        self._stats.misses += 1

    def _record_eviction(self) -> None:
        """Record cache eviction."""
        self._stats.evictions += 1


class MemoryCache(BaseCache[K, V]):
    """In-memory cache implementation with various eviction policies."""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[timedelta] = None,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
    ):
        super().__init__(max_size, default_ttl)
        self.eviction_policy = eviction_policy
        self._data: Dict[K, CacheEntry[V]] = {}
        self._access_order: OrderedDict[K, None] = OrderedDict()

    def get(self, key: K) -> Optional[V]:
        """Get value from cache."""
        if key not in self._data:
            self._record_miss()
            return None

        entry = self._data[key]

        # Check expiration
        if entry.is_expired:
            self.delete(key)
            self._record_miss()
            return None

        # Update access tracking
        entry.touch()
        if self.eviction_policy == EvictionPolicy.LRU:
            self._access_order.move_to_end(key)

        self._record_hit()
        return entry.value

    def set(self, key: K, value: V, ttl: Optional[timedelta] = None) -> None:
        """Set value in cache."""
        if ttl is None:
            ttl = self.default_ttl

        # Remove existing entry if present
        if key in self._data:
            self.delete(key)

        # Check if we need to evict
        if len(self._data) >= self.max_size:
            self._evict()

        # Add new entry
        entry = CacheEntry(value=value, ttl=ttl)
        self._data[key] = entry

        if self.eviction_policy == EvictionPolicy.LRU:
            self._access_order[key] = None

    def delete(self, key: K) -> bool:
        """Delete value from cache."""
        if key not in self._data:
            return False

        del self._data[key]
        if key in self._access_order:
            del self._access_order[key]

        return True

    def clear(self) -> None:
        """Clear all values from cache."""
        self._data.clear()
        self._access_order.clear()

    def keys(self) -> List[K]:
        """Get all keys in cache."""
        return list(self._data.keys())

    def size(self) -> int:
        """Get current cache size."""
        return len(self._data)

    def _evict(self) -> None:
        """Evict entries based on eviction policy."""
        if not self._data:
            return

        key_to_evict = None

        if self.eviction_policy == EvictionPolicy.LRU:
            key_to_evict = next(iter(self._access_order))
        elif self.eviction_policy == EvictionPolicy.LFU:
            key_to_evict = min(
                self._data.keys(), key=lambda k: self._data[k].access_count
            )
        elif self.eviction_policy == EvictionPolicy.FIFO:
            key_to_evict = min(
                self._data.keys(), key=lambda k: self._data[k].created_at
            )
        elif self.eviction_policy == EvictionPolicy.TTL:
            # Find expired entries first
            now = datetime.utcnow()
            expired_keys = [
                k
                for k, entry in self._data.items()
                if entry.ttl and (now - entry.created_at) > entry.ttl
            ]
            if expired_keys:
                key_to_evict = expired_keys[0]
            else:
                # Fall back to oldest
                key_to_evict = min(
                    self._data.keys(), key=lambda k: self._data[k].created_at
                )
        elif self.eviction_policy == EvictionPolicy.RANDOM:
            import random

            key_to_evict = random.choice(list(self._data.keys()))

        if key_to_evict is not None:
            self.delete(key_to_evict)
            self._record_eviction()


class AsyncCache(Generic[K, V]):
    """Async-safe cache implementation."""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[timedelta] = None,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._stats = CacheStats(max_size=max_size)
        self._lock = asyncio.Lock()
        self._cache = MemoryCache[K, V](max_size, default_ttl, eviction_policy)

    async def get(self, key: K) -> Optional[V]:
        """Get value from cache asynchronously."""
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: K, value: V, ttl: Optional[timedelta] = None) -> None:
        """Set value in cache asynchronously."""
        async with self._lock:
            self._cache.set(key, value, ttl)

    async def delete(self, key: K) -> bool:
        """Delete value from cache asynchronously."""
        async with self._lock:
            return self._cache.delete(key)

    async def clear(self) -> None:
        """Clear all values from cache asynchronously."""
        async with self._lock:
            self._cache.clear()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.clear())

    def keys(self) -> List[K]:
        """Get all keys in cache."""
        return self._cache.keys()

    def size(self) -> int:
        """Get current cache size."""
        return self._cache.size()

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self._stats.size = self.size()
        return self._stats


class CacheManager(BaseComponent):
    """Central cache manager for the Pythonium framework."""

    def __init__(self, default_cache_config: Optional[Dict[str, Any]] = None):
        super().__init__("cache_manager", {})
        self._caches: Dict[str, Union[BaseCache, AsyncCache]] = {}
        self._default_config = default_cache_config or {
            "max_size": 1000,
            "default_ttl": None,
            "eviction_policy": EvictionPolicy.LRU,
        }

    async def initialize(self) -> None:
        """Initialize the cache manager."""
        logger.info("Cache manager initialized")

    async def shutdown(self) -> None:
        """Shutdown the cache manager."""
        self.clear_all()
        self._caches.clear()
        logger.info("Cache manager shutdown")

    def create_cache(
        self, name: str, cache_type: str = "memory", **kwargs
    ) -> Union[BaseCache, AsyncCache]:
        """Create a new cache instance."""
        if name in self._caches:
            raise CacheError(f"Cache '{name}' already exists")

        # Merge with default config
        config = {**self._default_config, **kwargs}

        if cache_type == "memory":
            cache: Union[BaseCache, AsyncCache] = MemoryCache(**config)
        elif cache_type == "async":
            cache = AsyncCache(**config)
        else:
            raise CacheError(f"Unknown cache type: {cache_type}")

        self._caches[name] = cache
        logger.debug(f"Created cache '{name}' of type '{cache_type}'")
        return cache

    def get_cache(self, name: str) -> Optional[Union[BaseCache, AsyncCache]]:
        """Get cache by name."""
        return self._caches.get(name)

    def delete_cache(self, name: str) -> bool:
        """Delete cache by name."""
        if name not in self._caches:
            return False

        cache = self._caches[name]
        cache.clear()
        del self._caches[name]
        logger.debug(f"Deleted cache '{name}'")
        return True

    def list_caches(self) -> List[str]:
        """List all cache names."""
        return list(self._caches.keys())

    def get_all_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all caches."""
        return {name: cache.get_stats() for name, cache in self._caches.items()}

    def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self._caches.values():
            cache.clear()
        logger.debug("Cleared all caches")


def cached(
    cache_name: str = "default",
    ttl: Optional[timedelta] = None,
    key_func: Optional[Callable[..., Any]] = None,
) -> Callable:
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Get or create cache
            cache_manager = CacheManager()
            cache = cache_manager.get_cache(cache_name)
            if cache is None:
                cache = cache_manager.create_cache(cache_name)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash((args, tuple(kwargs.items())))}"

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Compute result and cache it
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# Global cache manager instance
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def get_default_cache() -> Union[BaseCache, AsyncCache]:
    """Get the default cache instance."""
    cache_manager = get_cache_manager()
    cache = cache_manager.get_cache("default")
    if cache is None:
        cache = cache_manager.create_cache("default")
    return cache
