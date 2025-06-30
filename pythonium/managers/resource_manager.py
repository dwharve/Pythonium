"""
Resource Manager for the Pythonium MCP server.

This manager provides centralized resource management including memory monitoring,
connection pooling, resource cleanup, and resource limits enforcement.
"""

import asyncio
import gc
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
)

import psutil

from pythonium.common.exceptions import ResourceError
from pythonium.common.logging import get_logger
from pythonium.common.types import MetadataDict
from pythonium.managers.base import BaseManager, ManagerPriority
from pythonium.managers.config_manager import ConfigurationManager

logger = get_logger(__name__)


@dataclass
class ResourceLimits:
    """Resource usage limits."""

    max_memory: Optional[int] = None  # bytes
    max_cpu_percent: Optional[float] = None
    max_open_files: Optional[int] = None
    max_connections: Optional[int] = None
    max_threads: Optional[int] = None
    max_execution_time: Optional[float] = None  # seconds


@dataclass
class ResourceUsage:
    """Current resource usage statistics."""

    memory_bytes: int = 0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    open_files: int = 0
    active_connections: int = 0
    active_threads: int = 0
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PoolStats:
    """Connection pool statistics."""

    pool_size: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_created: int = 0
    total_closed: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    average_wait_time: float = 0.0


class ManagedResource(ABC):
    """Base class for managed resources."""

    def __init__(self, resource_id: str, metadata: Optional[MetadataDict] = None):
        self.resource_id = resource_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0
        self.is_active = True

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the resource."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup the resource."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if resource is healthy."""
        pass

    async def access(self) -> None:
        """Mark resource as accessed."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class ConnectionPool:
    """Generic connection pool implementation."""

    def __init__(
        self,
        name: str,
        factory: Callable[[], Any],
        max_size: int = 10,
        min_size: int = 1,
        max_idle_time: timedelta = timedelta(minutes=30),
        health_check: Optional[Callable[[Any], bool]] = None,
    ):
        self.name = name
        self.factory = factory
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time
        self.health_check = health_check

        self._pool: List[Any] = []
        self._in_use: Set[Any] = set()
        self._created_count = 0
        self._closed_count = 0
        self._hits = 0
        self._misses = 0
        self._total_wait_time = 0.0
        self._wait_count = 0
        self._lock = asyncio.Lock()
        self._available = asyncio.Condition(self._lock)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._closed = False

    async def start(self) -> None:
        """Start the connection pool."""
        # Pre-populate with minimum connections
        async with self._lock:
            for _ in range(self.min_size):
                conn = await self._create_connection()
                self._pool.append(conn)

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())

    async def stop(self) -> None:
        """Stop the connection pool."""
        self._closed = True

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            # Close all connections
            for conn in self._pool:
                await self._close_connection(conn)
            for conn in self._in_use:
                await self._close_connection(conn)

            self._pool.clear()
            self._in_use.clear()

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[Any, None]:
        """Acquire a connection from the pool."""
        if self._closed:
            raise ResourceError("Connection pool is closed")

        start_time = asyncio.get_event_loop().time()
        connection = await self._get_connection()
        wait_time = asyncio.get_event_loop().time() - start_time

        self._total_wait_time += wait_time
        self._wait_count += 1

        try:
            yield connection
        finally:
            await self._return_connection(connection)

    async def _get_connection(self) -> Any:
        """Get a connection from the pool."""
        async with self._available:
            while True:
                # Try to get from pool
                if self._pool:
                    connection = self._pool.pop()

                    # Health check if configured
                    if self.health_check and not await asyncio.to_thread(
                        self.health_check, connection
                    ):
                        await self._close_connection(connection)
                        continue

                    self._in_use.add(connection)
                    self._hits += 1
                    return connection

                # Create new connection if under limit
                if len(self._in_use) < self.max_size:
                    connection = await self._create_connection()
                    self._in_use.add(connection)
                    self._misses += 1
                    return connection

                # Wait for connection to become available
                await self._available.wait()

    async def _return_connection(self, connection: Any) -> None:
        """Return a connection to the pool."""
        async with self._available:
            if connection in self._in_use:
                self._in_use.remove(connection)

                # Health check before returning to pool
                if not self._closed and (
                    not self.health_check
                    or await asyncio.to_thread(self.health_check, connection)
                ):
                    self._pool.append(connection)
                else:
                    await self._close_connection(connection)

                self._available.notify()

    async def _create_connection(self) -> Any:
        """Create a new connection."""
        connection = await asyncio.to_thread(self.factory)
        self._created_count += 1
        return connection

    async def _close_connection(self, connection: Any) -> None:
        """Close a connection."""
        try:
            if hasattr(connection, "close"):
                if asyncio.iscoroutinefunction(connection.close):
                    await connection.close()
                else:
                    await asyncio.to_thread(connection.close)
            elif hasattr(connection, "__del__"):
                await asyncio.to_thread(connection.__del__)
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
        finally:
            self._closed_count += 1

    async def _cleanup_idle_connections(self) -> None:
        """Cleanup idle connections periodically."""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Check every minute

                if self._closed:
                    break  # type: ignore[unreachable]

                async with self._lock:
                    # Remove connections that exceed max idle time
                    to_remove = []

                    for conn in self._pool:
                        # This is a simplified check - in practice you'd track last use time
                        if len(self._pool) > self.min_size:
                            to_remove.append(conn)
                            # Only remove one connection per cleanup cycle
                            break

                    for conn in to_remove:
                        self._pool.remove(conn)
                        await self._close_connection(conn)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        avg_wait = (
            self._total_wait_time / self._wait_count if self._wait_count > 0 else 0.0
        )

        return PoolStats(
            pool_size=len(self._pool),
            active_connections=len(self._in_use),
            idle_connections=len(self._pool),
            total_created=self._created_count,
            total_closed=self._closed_count,
            pool_hits=self._hits,
            pool_misses=self._misses,
            average_wait_time=avg_wait,
        )


class ResourceManager(BaseManager):
    """Comprehensive resource management system."""

    def __init__(self):
        super().__init__(
            name="resource",
            version="1.0.0",
            description="Resource management, monitoring, and limits enforcement",
        )
        self._info.priority = ManagerPriority.HIGH

        # Resource tracking
        self._managed_resources: Dict[str, ManagedResource] = {}
        self._connection_pools: Dict[str, ConnectionPool] = {}
        self._resource_types: Dict[str, Type[ManagedResource]] = {}

        # Resource limits and monitoring
        self._limits = ResourceLimits()
        self._current_usage = ResourceUsage()
        self._process = psutil.Process()
        self._start_time = datetime.utcnow()

        # Cleanup and monitoring
        self._cleanup_callbacks: List[Callable[[], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 30.0  # seconds
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="resource-monitor"
        )

        # Alerts and thresholds
        self._alert_thresholds = {
            "memory_percent": 80.0,
            "cpu_percent": 80.0,
            "open_files": 90.0,  # percent of limit
        }
        self._alert_callbacks: List[Callable[[str, ResourceUsage], None]] = []

    async def _initialize(self) -> None:
        """Initialize the resource manager."""
        # Load configuration
        config_manager = self.get_dependency(ConfigurationManager)
        if config_manager and isinstance(config_manager, ConfigurationManager):
            await self._load_configuration(config_manager)

        # Set default limits if not configured
        if not self._limits.max_memory:
            # Default to 80% of available memory
            available_memory = psutil.virtual_memory().available
            self._limits.max_memory = int(available_memory * 0.8)

        if not self._limits.max_open_files:
            try:
                import resource

                soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
                self._limits.max_open_files = int(soft_limit * 0.9)
            except (ImportError, OSError):
                self._limits.max_open_files = 1000  # Fallback

    async def _start(self) -> None:
        """Start the resource manager."""
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_resources())

        # Start connection pools
        for pool in self._connection_pools.values():
            await pool.start()

    async def _stop(self) -> None:
        """Stop the resource manager."""
        # Stop monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        # Stop connection pools
        for pool in self._connection_pools.values():
            await pool.stop()

        # Cleanup all managed resources
        await self._cleanup_all_resources()

    async def _cleanup(self) -> None:
        """Cleanup resource manager."""
        # Shutdown executor
        self._executor.shutdown(wait=True)

        # Clear all resources
        self._managed_resources.clear()
        self._connection_pools.clear()
        self._cleanup_callbacks.clear()
        self._alert_callbacks.clear()

    async def _load_configuration(self, config_manager: ConfigurationManager) -> None:
        """Load resource manager configuration."""
        resource_config = config_manager.get("resources", {})

        # Load limits
        limits_config = resource_config.get("limits", {})
        self._limits = ResourceLimits(
            max_memory=limits_config.get("max_memory"),
            max_cpu_percent=limits_config.get("max_cpu_percent"),
            max_open_files=limits_config.get("max_open_files"),
            max_connections=limits_config.get("max_connections"),
            max_threads=limits_config.get("max_threads"),
            max_execution_time=limits_config.get("max_execution_time"),
        )

        # Load monitoring settings
        monitoring_config = resource_config.get("monitoring", {})
        self._monitoring_interval = monitoring_config.get("interval", 30.0)

        # Load alert thresholds
        alert_config = resource_config.get("alerts", {})
        self._alert_thresholds.update(alert_config.get("thresholds", {}))

    # Resource monitoring

    async def _monitor_resources(self) -> None:
        """Monitor resource usage continuously."""
        while True:
            try:
                await asyncio.sleep(self._monitoring_interval)
                await self._update_resource_usage()
                await self._check_limits()
                await self._check_alerts()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")

    async def _update_resource_usage(self) -> None:
        """Update current resource usage statistics."""
        try:
            # Get process information
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            cpu_percent = self._process.cpu_percent()

            # Get file descriptor count
            try:
                open_files = (
                    self._process.num_fds() if hasattr(self._process, "num_fds") else 0
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                open_files = 0

            # Get thread count
            try:
                thread_count = self._process.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                thread_count = threading.active_count()

            # Update usage
            self._current_usage = ResourceUsage(
                memory_bytes=memory_info.rss,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                open_files=open_files,
                active_connections=sum(
                    len(pool._in_use) for pool in self._connection_pools.values()
                ),
                active_threads=thread_count,
                uptime=datetime.utcnow() - self._start_time,
                last_updated=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error updating resource usage: {e}")

    async def _check_limits(self) -> None:
        """Check if resource limits are exceeded."""
        usage = self._current_usage

        # Check memory limit
        if self._limits.max_memory and usage.memory_bytes > self._limits.max_memory:
            await self._handle_limit_exceeded(
                "memory", usage.memory_bytes, self._limits.max_memory
            )

        # Check CPU limit
        if (
            self._limits.max_cpu_percent
            and usage.cpu_percent > self._limits.max_cpu_percent
        ):
            await self._handle_limit_exceeded(
                "cpu", usage.cpu_percent, self._limits.max_cpu_percent
            )

        # Check file descriptor limit
        if (
            self._limits.max_open_files
            and usage.open_files > self._limits.max_open_files
        ):
            await self._handle_limit_exceeded(
                "open_files", usage.open_files, self._limits.max_open_files
            )

        # Check connection limit
        if (
            self._limits.max_connections
            and usage.active_connections > self._limits.max_connections
        ):
            await self._handle_limit_exceeded(
                "connections",
                usage.active_connections,
                self._limits.max_connections,
            )

    async def _check_alerts(self) -> None:
        """Check if alert thresholds are exceeded."""
        usage = self._current_usage

        # Memory percentage alert
        if usage.memory_percent > self._alert_thresholds.get("memory_percent", 100):
            await self._trigger_alert("memory_percent", usage)

        # CPU percentage alert
        if usage.cpu_percent > self._alert_thresholds.get("cpu_percent", 100):
            await self._trigger_alert("cpu_percent", usage)

        # File descriptor percentage alert
        if self._limits.max_open_files:
            fd_percent = (usage.open_files / self._limits.max_open_files) * 100
            if fd_percent > self._alert_thresholds.get("open_files", 100):
                await self._trigger_alert("open_files", usage)

    async def _handle_limit_exceeded(
        self, resource_type: str, current: Any, limit: Any
    ) -> None:
        """Handle resource limit exceeded."""
        logger.warning(
            f"Resource limit exceeded - {resource_type}: {current} > {limit}"
        )

        # Emit event
        await self.emit_event(
            "resource_limit_exceeded",
            {
                "resource_type": resource_type,
                "current": current,
                "limit": limit,
                "usage": self._current_usage.__dict__,
            },
        )

        # Trigger cleanup if possible
        if resource_type == "memory":
            await self._emergency_memory_cleanup()

    async def _trigger_alert(self, alert_type: str, usage: ResourceUsage) -> None:
        """Trigger resource usage alert."""
        logger.warning(f"Resource alert triggered - {alert_type}")

        # Call alert callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_type, usage)
                else:
                    callback(alert_type, usage)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

        # Emit event
        await self.emit_event(
            "resource_alert",
            {"alert_type": alert_type, "usage": usage.__dict__},
        )

    async def _emergency_memory_cleanup(self) -> None:
        """Perform emergency memory cleanup."""
        logger.info("Performing emergency memory cleanup")

        # Force garbage collection
        await asyncio.to_thread(gc.collect)

        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    await asyncio.to_thread(callback)
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")

        # Close idle connections in pools
        for pool in self._connection_pools.values():
            # Reduce pool to minimum size
            async with pool._lock:
                while len(pool._pool) > pool.min_size:
                    if pool._pool:
                        conn = pool._pool.pop()
                        await pool._close_connection(conn)

    # Public API

    def register_resource_type(
        self, name: str, resource_type: Type[ManagedResource]
    ) -> None:
        """Register a managed resource type."""
        self._resource_types[name] = resource_type

    async def create_resource(
        self, resource_type: str, resource_id: str, **kwargs
    ) -> ManagedResource:
        """Create a managed resource."""
        if resource_type not in self._resource_types:
            raise ResourceError(f"Unknown resource type: {resource_type}")

        if resource_id in self._managed_resources:
            raise ResourceError(f"Resource {resource_id} already exists")

        resource_class = self._resource_types[resource_type]
        resource = resource_class(resource_id, **kwargs)

        await resource.initialize()
        self._managed_resources[resource_id] = resource

        logger.debug(f"Created managed resource: {resource_id}")
        return resource

    async def get_resource(self, resource_id: str) -> Optional[ManagedResource]:
        """Get a managed resource."""
        resource = self._managed_resources.get(resource_id)
        if resource:
            await resource.access()
        return resource

    async def remove_resource(self, resource_id: str) -> bool:
        """Remove a managed resource."""
        if resource_id not in self._managed_resources:
            return False

        resource = self._managed_resources[resource_id]
        await resource.cleanup()
        del self._managed_resources[resource_id]

        logger.debug(f"Removed managed resource: {resource_id}")
        return True

    async def _cleanup_all_resources(self) -> None:
        """Cleanup all managed resources."""
        for resource_id in list(self._managed_resources.keys()):
            await self.remove_resource(resource_id)

    # Connection pool management

    async def create_pool(
        self,
        name: str,
        factory: Callable[[], Any],
        max_size: int = 10,
        min_size: int = 1,
        **kwargs,
    ) -> ConnectionPool:
        """Create a connection pool."""
        if name in self._connection_pools:
            raise ResourceError(f"Connection pool {name} already exists")

        pool = ConnectionPool(name, factory, max_size, min_size, **kwargs)
        self._connection_pools[name] = pool

        if self.is_running:
            await pool.start()

        logger.info(f"Created connection pool: {name}")
        return pool

    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get a connection pool."""
        return self._connection_pools.get(name)

    async def remove_pool(self, name: str) -> bool:
        """Remove a connection pool."""
        if name not in self._connection_pools:
            return False

        pool = self._connection_pools[name]
        await pool.stop()
        del self._connection_pools[name]

        logger.info(f"Removed connection pool: {name}")
        return True

    # Resource usage and statistics

    def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        return self._current_usage

    def get_resource_limits(self) -> ResourceLimits:
        """Get resource limits."""
        return self._limits

    def set_resource_limits(self, limits: ResourceLimits) -> None:
        """Set resource limits."""
        self._limits = limits

    def get_pool_stats(self) -> Dict[str, PoolStats]:
        """Get statistics for all connection pools."""
        return {name: pool.get_stats() for name, pool in self._connection_pools.items()}

    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add a cleanup callback."""
        self._cleanup_callbacks.append(callback)

    def remove_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Remove a cleanup callback."""
        if callback in self._cleanup_callbacks:
            self._cleanup_callbacks.remove(callback)

    def add_alert_callback(
        self, callback: Callable[[str, ResourceUsage], None]
    ) -> None:
        """Add an alert callback."""
        self._alert_callbacks.append(callback)

    def remove_alert_callback(
        self, callback: Callable[[str, ResourceUsage], None]
    ) -> None:
        """Remove an alert callback."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
