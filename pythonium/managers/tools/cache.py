"""
Tool result caching system.

This module provides functionality to cache tool execution results to improve
performance and reduce redundant computations.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategy types."""

    MEMORY_ONLY = "memory_only"
    DISK_ONLY = "disk_only"
    MEMORY_DISK = "memory_disk"  # Memory first, disk fallback
    DISABLED = "disabled"


class CacheEvictionPolicy(Enum):
    """Cache eviction policies."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In, First Out


@dataclass
class CacheEntry:
    """Cache entry containing result and metadata."""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheStats:
    """Cache statistics tracking."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size_bytes = 0
        self.entry_count = 0
        self._lock = threading.Lock()

    def record_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.misses += 1

    def record_eviction(self) -> None:
        """Record a cache eviction."""
        with self._lock:
            self.evictions += 1

    def update_size(self, delta_bytes: int, delta_entries: int = 0) -> None:
        """Update cache size statistics."""
        with self._lock:
            self.size_bytes += delta_bytes
            self.entry_count += delta_entries

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "size_bytes": self.size_bytes,
            "entry_count": self.entry_count,
        }


class ResultCache:
    """
    Advanced caching system for tool execution results.

    Features:
    - Multiple cache strategies (memory, disk, hybrid)
    - Various eviction policies (LRU, LFU, TTL, FIFO)
    - Configurable size limits and TTL
    - Cache statistics and monitoring
    - Async and thread-safe operations
    """

    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.MEMORY_DISK,
        eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU,
        max_memory_size: int = 100 * 1024 * 1024,  # 100MB
        max_disk_size: int = 1024 * 1024 * 1024,  # 1GB
        max_entries: int = 10000,
        default_ttl: Optional[float] = None,
        cache_dir: Optional[str] = None,
        enable_compression: bool = True,
    ):
        self.strategy = strategy
        self.eviction_policy = eviction_policy
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.enable_compression = enable_compression

        # Cache storage
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU
        self._access_frequency: Dict[str, int] = {}  # For LFU

        # Disk cache
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir
            else Path(tempfile.gettempdir()) / "pythonium_cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Statistics and synchronization
        self.stats = CacheStats()
        self._lock = asyncio.Lock()
        self._disk_lock = threading.Lock()

        logger.debug(
            f"Initialized ResultCache with strategy={strategy.value}, policy={eviction_policy.value}"
        )

    def _generate_key(
        self,
        tool_id: str,
        args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a cache key from tool ID and arguments."""
        # Create a deterministic hash of the inputs
        data = {"tool_id": tool_id, "args": args, "metadata": metadata or {}}

        # Sort keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _get_entry_size(self, value: Any) -> int:
        """Estimate the size of a cache entry in bytes."""
        try:
            if self.enable_compression:
                import gzip

                return len(gzip.compress(pickle.dumps(value)))
            else:
                return len(pickle.dumps(value))
        except Exception:
            # Fallback to string representation
            return len(str(value).encode("utf-8"))

    async def get(
        self,
        tool_id: str,
        args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Get a cached result.

        Args:
            tool_id: Tool identifier
            args: Tool arguments
            metadata: Additional metadata for key generation

        Returns:
            Cached result or None if not found/expired
        """
        if self.strategy == CacheStrategy.DISABLED:
            return None

        key = self._generate_key(tool_id, args, metadata)

        async with self._lock:
            # Try memory cache first
            if key in self._memory_cache:
                entry = self._memory_cache[key]

                if entry.is_expired:
                    await self._remove_from_memory(key)
                    self.stats.record_miss()
                    return None

                # Update access statistics
                entry.touch()
                self._update_access_order(key)
                self.stats.record_hit()

                logger.debug(f"Cache hit (memory): {key[:16]}...")
                return entry.value

            # Try disk cache if enabled
            if self.strategy in [
                CacheStrategy.DISK_ONLY,
                CacheStrategy.MEMORY_DISK,
            ]:
                result = await self._get_from_disk(key)
                if result is not None:
                    # Promote to memory cache if using hybrid strategy
                    if self.strategy == CacheStrategy.MEMORY_DISK:
                        await self._store_in_memory(key, result, self.default_ttl)

                    self.stats.record_hit()
                    logger.debug(f"Cache hit (disk): {key[:16]}...")
                    return result

        self.stats.record_miss()
        return None

    async def put(
        self,
        tool_id: str,
        args: Dict[str, Any],
        result: Any,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a result in the cache.

        Args:
            tool_id: Tool identifier
            args: Tool arguments
            result: Result to cache
            ttl: Time to live in seconds
            metadata: Additional metadata
        """
        if self.strategy == CacheStrategy.DISABLED:
            return

        key = self._generate_key(tool_id, args, metadata)
        ttl = ttl or self.default_ttl

        async with self._lock:
            # Store in memory cache
            if self.strategy in [
                CacheStrategy.MEMORY_ONLY,
                CacheStrategy.MEMORY_DISK,
            ]:
                await self._store_in_memory(key, result, ttl, metadata)

            # Store in disk cache
            if self.strategy in [
                CacheStrategy.DISK_ONLY,
                CacheStrategy.MEMORY_DISK,
            ]:
                await self._store_on_disk(key, result, ttl, metadata)

        logger.debug(f"Cached result: {key[:16]}...")

    async def _store_in_memory(
        self,
        key: str,
        value: Any,
        ttl: Optional[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an entry in memory cache."""
        size_bytes = self._get_entry_size(value)

        # Check if we need to evict entries
        await self._ensure_memory_capacity(size_bytes)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl_seconds=ttl,
            size_bytes=size_bytes,
            metadata=metadata or {},
        )

        self._memory_cache[key] = entry
        self._update_access_order(key)
        self.stats.update_size(size_bytes, 1)

    async def _store_on_disk(
        self,
        key: str,
        value: Any,
        ttl: Optional[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an entry on disk."""

        def _write_to_disk():
            try:
                file_path = self.cache_dir / f"{key}.cache"

                entry_data = {
                    "value": value,
                    "created_at": datetime.now().isoformat(),
                    "ttl_seconds": ttl,
                    "metadata": metadata or {},
                }

                with open(file_path, "wb") as f:
                    if self.enable_compression:
                        import gzip

                        f.write(gzip.compress(pickle.dumps(entry_data)))
                    else:
                        pickle.dump(entry_data, f)

                logger.debug(f"Stored to disk: {key[:16]}...")

            except Exception as e:
                logger.error(f"Failed to store cache entry on disk: {e}")

        # Run disk I/O in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_to_disk)

    async def _get_from_disk(self, key: str) -> Optional[Any]:
        """Get an entry from disk cache."""

        def _read_from_disk():
            try:
                file_path = self.cache_dir / f"{key}.cache"

                if not file_path.exists():
                    return None

                with open(file_path, "rb") as f:
                    if self.enable_compression:
                        import gzip

                        entry_data = pickle.loads(gzip.decompress(f.read()))
                    else:
                        entry_data = pickle.load(f)

                # Check TTL
                if entry_data.get("ttl_seconds"):
                    created_at = datetime.fromisoformat(entry_data["created_at"])
                    if (datetime.now() - created_at).total_seconds() > entry_data[
                        "ttl_seconds"
                    ]:
                        # Entry expired, remove file
                        file_path.unlink(missing_ok=True)
                        return None

                return entry_data["value"]

            except Exception as e:
                logger.error(f"Failed to read cache entry from disk: {e}")
                return None

        # Run disk I/O in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_from_disk)

    async def _ensure_memory_capacity(self, required_bytes: int) -> None:
        """Ensure there's enough memory capacity for a new entry."""
        # Check entry count limit
        while len(self._memory_cache) >= self.max_entries:
            await self._evict_memory_entry()

        # Check memory size limit
        while self.stats.size_bytes + required_bytes > self.max_memory_size:
            await self._evict_memory_entry()

    async def _evict_memory_entry(self) -> None:
        """Evict an entry from memory cache based on eviction policy."""
        if not self._memory_cache:
            return

        key_to_evict = None

        if self.eviction_policy == CacheEvictionPolicy.LRU:
            # Remove least recently used
            key_to_evict = (
                self._access_order[0]
                if self._access_order
                else next(iter(self._memory_cache))
            )

        elif self.eviction_policy == CacheEvictionPolicy.LFU:
            # Remove least frequently used
            min_frequency = (
                min(self._access_frequency.values()) if self._access_frequency else 0
            )
            key_to_evict = next(
                (
                    k
                    for k, freq in self._access_frequency.items()
                    if freq == min_frequency
                ),
                next(iter(self._memory_cache)),
            )

        elif self.eviction_policy == CacheEvictionPolicy.TTL:
            # Remove expired entries first, then oldest
            expired_keys = [
                k for k, entry in self._memory_cache.items() if entry.is_expired
            ]
            if expired_keys:
                key_to_evict = expired_keys[0]
            else:
                oldest_key = min(
                    self._memory_cache.keys(),
                    key=lambda k: self._memory_cache[k].created_at,
                )
                key_to_evict = oldest_key

        elif self.eviction_policy == CacheEvictionPolicy.FIFO:
            # Remove first inserted (oldest)
            key_to_evict = next(iter(self._memory_cache))

        if key_to_evict:
            await self._remove_from_memory(key_to_evict)
            self.stats.record_eviction()

    async def _remove_from_memory(self, key: str) -> None:
        """Remove an entry from memory cache."""
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            del self._memory_cache[key]

            # Update access tracking
            if key in self._access_order:
                self._access_order.remove(key)
            if key in self._access_frequency:
                del self._access_frequency[key]

            self.stats.update_size(-entry.size_bytes, -1)

    def _update_access_order(self, key: str) -> None:
        """Update access order for LRU tracking."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        # Update frequency for LFU
        self._access_frequency[key] = self._access_frequency.get(key, 0) + 1

    async def invalidate(
        self,
        tool_id: str,
        args: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            tool_id: Tool identifier
            args: Tool arguments (if None, invalidates all entries for tool)
            metadata: Additional metadata

        Returns:
            True if entry was removed, False if not found
        """
        if args is not None:
            # Invalidate specific entry
            key = self._generate_key(tool_id, args, metadata)
            return await self._invalidate_key(key)
        else:
            # Invalidate all entries for tool
            keys_to_remove = []
            for key, entry in self._memory_cache.items():
                # This is a simplified approach - in a real implementation,
                # you might want to store tool_id in the entry metadata
                keys_to_remove.append(key)

            removed_count = 0
            for key in keys_to_remove:
                if await self._invalidate_key(key):
                    removed_count += 1

            return removed_count > 0

    async def _invalidate_key(self, key: str) -> bool:
        """Invalidate a specific cache key."""
        async with self._lock:
            removed = False

            # Remove from memory
            if key in self._memory_cache:
                await self._remove_from_memory(key)
                removed = True

            # Remove from disk
            if self.strategy in [
                CacheStrategy.DISK_ONLY,
                CacheStrategy.MEMORY_DISK,
            ]:

                def _remove_from_disk():
                    try:
                        file_path = self.cache_dir / f"{key}.cache"
                        if file_path.exists():
                            file_path.unlink()
                            return True
                    except Exception as e:
                        logger.error(f"Failed to remove disk cache entry: {e}")
                    return False

                loop = asyncio.get_event_loop()
                disk_removed = await loop.run_in_executor(None, _remove_from_disk)
                removed = removed or disk_removed

            return removed

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            # Clear memory cache
            self._memory_cache.clear()
            self._access_order.clear()
            self._access_frequency.clear()

            # Clear disk cache
            if self.strategy in [
                CacheStrategy.DISK_ONLY,
                CacheStrategy.MEMORY_DISK,
            ]:

                def _clear_disk():
                    try:
                        for file_path in self.cache_dir.glob("*.cache"):
                            file_path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to clear disk cache: {e}")

                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _clear_disk)

            # Reset stats
            self.stats = CacheStats()

            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.stats.to_dict()
        stats.update(
            {
                "strategy": self.strategy.value,
                "eviction_policy": self.eviction_policy.value,
                "memory_entries": len(self._memory_cache),
                "cache_dir": str(self.cache_dir),
            }
        )
        return stats

    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        removed_count = 0

        async with self._lock:
            # Clean memory cache
            removed_count += await self._cleanup_memory_cache()

            # Clean disk cache
            if self.strategy in [CacheStrategy.DISK_ONLY, CacheStrategy.MEMORY_DISK]:
                removed_count += await self._cleanup_disk_cache()

        if removed_count > 0:
            logger.debug(f"Cleaned up {removed_count} expired cache entries")

        return removed_count

    async def _cleanup_memory_cache(self) -> int:
        """Clean expired entries from memory cache."""
        expired_keys = [
            k for k, entry in self._memory_cache.items() if entry.is_expired
        ]
        for key in expired_keys:
            await self._remove_from_memory(key)
        return len(expired_keys)

    async def _cleanup_disk_cache(self) -> int:
        """Clean expired entries from disk cache."""

        def _cleanup_disk():
            count = 0
            try:
                for file_path in self.cache_dir.glob("*.cache"):
                    if self._is_disk_entry_expired(file_path):
                        file_path.unlink(missing_ok=True)
                        count += 1
            except Exception as e:
                logger.error(f"Failed to cleanup disk cache: {e}")
            return count

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _cleanup_disk)

    def _is_disk_entry_expired(self, file_path: Path) -> bool:
        """Check if a disk cache entry is expired."""
        try:
            with open(file_path, "rb") as f:
                if self.enable_compression:
                    import gzip

                    entry_data = pickle.loads(gzip.decompress(f.read()))
                else:
                    entry_data = pickle.load(f)

            if entry_data.get("ttl_seconds"):
                created_at = datetime.fromisoformat(entry_data["created_at"])
                elapsed = (datetime.now() - created_at).total_seconds()
                ttl_seconds: float = entry_data["ttl_seconds"]
                return elapsed > ttl_seconds
            return False
        except Exception:
            # Corrupted files should be removed
            return True
