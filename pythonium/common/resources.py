"""
Resource management utilities for the Pythonium framework.

This module provides comprehensive resource management including
lifecycle management, resource pools, and cleanup utilities.
"""

import asyncio
import threading
import weakref
from abc import ABC, abstractmethod
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    TypeVar,
)

from pythonium.common.base import BaseComponent, ComponentStatus
from pythonium.common.exceptions import PythoniumError
from pythonium.common.lifecycle import ComponentState
from pythonium.common.logging import get_logger
from pythonium.common.types import MetadataDict

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class ResourceError(PythoniumError):
    """Base exception for resource management."""

    pass


class ResourceExhaustedError(ResourceError):
    """Exception raised when resources are exhausted."""

    pass


class ResourceLeakError(ResourceError):
    """Exception raised when resource leaks are detected."""

    pass


@dataclass
class ResourceInfo:
    """Information about a resource."""

    resource_id: str
    resource_type: str
    state: ComponentState = ComponentState.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    use_count: int = 0
    metadata: MetadataDict = field(default_factory=dict)

    def touch(self) -> None:
        """Update last used time and increment use count."""
        self.last_used = datetime.utcnow()
        self.use_count += 1


class Resource(ABC, Generic[T]):
    """Abstract base class for managed resources."""

    def __init__(self, resource_id: str, resource_type: str):
        self.info = ResourceInfo(resource_id=resource_id, resource_type=resource_type)
        self._value: Optional[T] = None
        self._lock = threading.RLock()
        self._cleanup_callbacks: List[Callable[[], None]] = []

    @property
    def value(self) -> Optional[T]:
        """Get the resource value."""
        return self._value

    @property
    def is_initialized(self) -> bool:
        """Check if resource is initialized."""
        return self.info.state != ComponentState.CREATED

    @property
    def is_active(self) -> bool:
        """Check if resource is active."""
        return self.info.state == ComponentState.ACTIVE

    @property
    def is_disposed(self) -> bool:
        """Check if resource is disposed."""
        return self.info.state == ComponentState.DISPOSED

    @abstractmethod
    async def initialize(self) -> T:
        """Initialize the resource."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup the resource."""
        pass

    async def acquire(self) -> T:
        """Acquire the resource for use."""
        with self._lock:
            if self.info.state == ComponentState.DISPOSED:
                raise ResourceError(f"Resource {self.info.resource_id} is disposed")

            if not self.is_initialized:
                self._value = await self.initialize()
                self.info.state = ComponentState.INITIALIZED

            self.info.state = ComponentState.ACTIVE
            self.info.touch()

            if self._value is None:
                raise ResourceError(
                    f"Failed to initialize resource {self.info.resource_id}"
                )

            return self._value

    async def release(self) -> None:
        """Release the resource."""
        with self._lock:
            if self.info.state == ComponentState.ACTIVE:
                self.info.state = ComponentState.IDLE

    async def dispose(self) -> None:
        """Dispose of the resource."""
        with self._lock:
            if self.info.state == ComponentState.DISPOSED:
                return

            self.info.state = ComponentState.CLEANUP

            try:
                # Run cleanup callbacks
                for callback in self._cleanup_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in cleanup callback: {e}")

                # Cleanup the resource
                await self.cleanup()

                self.info.state = ComponentState.DISPOSED
                self._value = None

            except Exception as e:
                self.info.state = ComponentState.ERROR
                logger.error(f"Error disposing resource {self.info.resource_id}: {e}")
                raise

    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add a cleanup callback."""
        self._cleanup_callbacks.append(callback)

    def __del__(self):
        """Finalizer to ensure cleanup."""
        if not self.is_disposed and self._value is not None:
            logger.warning(
                f"Resource {self.info.resource_id} was not properly disposed"
            )


class ResourcePool(Generic[T]):
    """Generic resource pool for managing multiple resources."""

    def __init__(
        self,
        factory: Callable[[], Resource[T]],
        min_size: int = 0,
        max_size: int = 10,
        idle_timeout: Optional[timedelta] = None,
    ):
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout or timedelta(minutes=30)

        self._available: deque[Resource[T]] = deque()
        self._in_use: Dict[str, Resource[T]] = {}
        self._lock = asyncio.Lock()
        self._total_created = 0
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the pool with minimum resources."""
        async with self._lock:
            for _ in range(self.min_size):
                resource = self.factory()
                await resource.acquire()
                await resource.release()
                self._available.append(resource)
                self._total_created += 1

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_resources())

    async def acquire(self) -> Resource[T]:
        """Acquire a resource from the pool."""
        async with self._lock:
            # Try to get an available resource
            while self._available:
                resource = self._available.popleft()
                if not resource.is_disposed:
                    await resource.acquire()
                    self._in_use[resource.info.resource_id] = resource
                    return resource

            # Create new resource if under limit
            if self._total_created < self.max_size:
                resource = self.factory()
                await resource.acquire()
                self._in_use[resource.info.resource_id] = resource
                self._total_created += 1
                return resource

            # Pool exhausted
            raise ResourceExhaustedError(
                f"Resource pool exhausted (max_size={self.max_size})"
            )

    async def release(self, resource: Resource[T]) -> None:
        """Release a resource back to the pool."""
        async with self._lock:
            if resource.info.resource_id not in self._in_use:
                logger.warning(
                    f"Releasing resource {resource.info.resource_id} not in use"
                )
                return

            del self._in_use[resource.info.resource_id]
            await resource.release()

            # Add back to available pool if not disposed
            if not resource.is_disposed:
                self._available.append(resource)

    async def shutdown(self) -> None:
        """Shutdown the pool and dispose all resources."""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            # Dispose all resources
            all_resources = list(self._in_use.values()) + list(self._available)

            for resource in all_resources:
                try:
                    await resource.dispose()
                except Exception as e:
                    logger.error(
                        f"Error disposing resource {resource.info.resource_id}: {e}"
                    )

            self._in_use.clear()
            self._available.clear()
            self._total_created = 0

    async def _cleanup_idle_resources(self) -> None:
        """Background task to cleanup idle resources."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                async with self._lock:
                    now = datetime.utcnow()
                    to_remove = []

                    for resource in self._available:
                        if (now - resource.info.last_used) > self.idle_timeout:
                            to_remove.append(resource)

                    # Keep minimum resources
                    while (
                        len(to_remove) > 0
                        and (len(self._available) - len(to_remove)) >= self.min_size
                    ):
                        resource = to_remove.pop()
                        self._available.remove(resource)
                        self._total_created -= 1

                        # Dispose in background
                        asyncio.create_task(self._dispose_resource(resource))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource cleanup: {e}")

    async def _dispose_resource(self, resource: Resource[T]) -> None:
        """Dispose a resource in the background."""
        try:
            await resource.dispose()
        except Exception as e:
            logger.error(f"Error disposing resource {resource.info.resource_id}: {e}")

    @property
    def stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return {
            "total_created": self._total_created,
            "available": len(self._available),
            "in_use": len(self._in_use),
            "max_size": self.max_size,
            "min_size": self.min_size,
        }


class ResourceManager(BaseComponent):
    """Central resource manager for the Pythonium framework."""

    def __init__(self):
        super().__init__("resource_manager")
        self._resources: Dict[str, Resource] = {}
        self._pools: Dict[str, ResourcePool] = {}
        self._cleanup_tasks: List[asyncio.Task] = []
        self._finalizers: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the resource manager."""
        self.status = ComponentStatus.RUNNING
        logger.debug("Resource manager initialized")

    async def register_resource(self, resource: Resource) -> None:
        """Register a resource for management."""
        async with self._lock:
            if resource.info.resource_id in self._resources:
                raise ResourceError(
                    f"Resource {resource.info.resource_id} already registered"
                )

            self._resources[resource.info.resource_id] = resource

            # Set up finalizer
            self._finalizers[resource.info.resource_id] = resource

            logger.debug(f"Registered resource {resource.info.resource_id}")

    async def unregister_resource(self, resource_id: str) -> None:
        """Unregister a resource."""
        async with self._lock:
            if resource_id in self._resources:
                resource = self._resources[resource_id]
                await resource.dispose()
                del self._resources[resource_id]

                if resource_id in self._finalizers:
                    del self._finalizers[resource_id]

                logger.debug(f"Unregistered resource {resource_id}")

    async def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get a resource by ID."""
        return self._resources.get(resource_id)

    async def create_pool(
        self, name: str, factory: Callable[[], Resource], **kwargs
    ) -> ResourcePool:
        """Create a resource pool."""
        if name in self._pools:
            raise ResourceError(f"Pool {name} already exists")

        pool = ResourcePool(factory, **kwargs)
        await pool.initialize()

        self._pools[name] = pool
        logger.debug(f"Created resource pool {name}")
        return pool

    async def get_pool(self, name: str) -> Optional[ResourcePool]:
        """Get a resource pool by name."""
        return self._pools.get(name)

    async def shutdown(self) -> None:
        """Shutdown the resource manager."""
        # Cancel all cleanup tasks
        for task in self._cleanup_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._cleanup_tasks:
            await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)

        # Shutdown all pools
        for name, pool in self._pools.items():
            try:
                await pool.shutdown()
                logger.debug(f"Shutdown pool {name}")
            except Exception as e:
                logger.error(f"Error shutting down pool {name}: {e}")

        # Dispose all resources
        async with self._lock:
            for resource_id, resource in list(self._resources.items()):
                try:
                    await resource.dispose()
                    logger.debug(f"Disposed resource {resource_id}")
                except Exception as e:
                    logger.error(f"Error disposing resource {resource_id}: {e}")

            self._resources.clear()
            self._pools.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get resource manager statistics."""
        return {
            "total_resources": len(self._resources),
            "total_pools": len(self._pools),
            "pool_stats": {name: pool.stats for name, pool in self._pools.items()},
            "resource_states": {
                resource_id: resource.info.state.value
                for resource_id, resource in self._resources.items()
            },
        }


# Context managers for resource management


@contextmanager
def managed_resource(resource: Resource[T]) -> Generator[T, None, None]:
    """Context manager for resource acquisition and release."""
    try:
        value = asyncio.run(resource.acquire())
        yield value
    finally:
        asyncio.run(resource.release())


@asynccontextmanager
async def async_managed_resource(
    resource: Resource[T],
) -> AsyncGenerator[T, None]:
    """Async context manager for resource acquisition and release."""
    try:
        value = await resource.acquire()
        yield value
    finally:
        await resource.release()


@asynccontextmanager
async def pooled_resource(pool: ResourcePool[T]) -> AsyncGenerator[T, None]:
    """Async context manager for pooled resource acquisition and release."""
    resource = await pool.acquire()
    try:
        if resource.value is None:
            raise ResourceError("Resource value is None")
        yield resource.value
    finally:
        await pool.release(resource)


# Global resource manager instance
_global_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager()
    return _global_resource_manager
