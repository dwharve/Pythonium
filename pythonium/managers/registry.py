"""
Manager registry and dependency injection system for Pythonium.

This module provides centralized management of all system managers,
including dependency resolution, initialization ordering, and lifecycle coordination.
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Any,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from pythonium.common.base import BaseComponent
from pythonium.common.config import PythoniumSettings
from pythonium.common.events import EventManager
from pythonium.common.exceptions import InitializationError, ManagerError
from pythonium.common.lifecycle import ComponentState
from pythonium.common.logging import get_logger
from pythonium.common.types import HealthStatus
from pythonium.managers.base import (
    BaseManager,
    ManagerPriority,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseManager)


@dataclass
class ManagerRegistration:
    """Registration information for a manager."""

    manager_type: Type[BaseManager]
    factory: Callable[[], BaseManager]
    priority: ManagerPriority = ManagerPriority.NORMAL
    auto_start: bool = True
    singleton: bool = True
    tags: Set[str] = field(default_factory=set)
    instance: Optional[BaseManager] = None
    registered_at: datetime = field(default_factory=datetime.utcnow)


class ManagerRegistry(BaseComponent):
    """Central registry for all managers in the system."""

    def __init__(self):
        super().__init__(
            "manager_registry", {}
        )  # Pass name and config to BaseComponent
        self._registrations: Dict[str, ManagerRegistration] = {}
        self._instances: Dict[str, BaseManager] = {}
        self._type_to_name: Dict[Type[BaseManager], str] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._started_managers: Set[str] = set()
        self._config_manager: Optional[PythoniumSettings] = None
        self._event_manager: Optional[EventManager] = None
        self._shutdown_order: List[str] = []
        self._lock = asyncio.Lock()

    def set_config_manager(self, config_manager: PythoniumSettings) -> None:
        """Set the configuration manager."""
        self._config_manager = config_manager

    def set_event_manager(self, event_manager: EventManager) -> None:
        """Set the event manager."""
        self._event_manager = event_manager

    def register_manager(
        self,
        name: str,
        manager_type: Type[T],
        factory: Optional[Callable[[], T]] = None,
        priority: ManagerPriority = ManagerPriority.NORMAL,
        auto_start: bool = True,
        singleton: bool = True,
        tags: Optional[Set[str]] = None,
    ) -> None:
        """Register a manager type with the registry."""

        if name in self._registrations:
            raise ManagerError(f"Manager '{name}' is already registered")

        # Default factory creates instance with no arguments
        if factory is None:
            import inspect

            # Check if constructor accepts a name parameter
            try:
                sig = inspect.signature(manager_type.__init__)
                if len(sig.parameters) > 1:  # self + at least one other parameter

                    def _create_manager_with_name():
                        return manager_type(name)

                    factory = _create_manager_with_name
                else:  # Only self parameter

                    def _create_manager_no_args():
                        return manager_type(name)

                    factory = _create_manager_no_args
            except Exception:
                # Fallback to constructor with name
                def _create_manager_fallback():
                    return manager_type(name)

                factory = _create_manager_fallback

        registration = ManagerRegistration(
            manager_type=manager_type,
            factory=factory,
            priority=priority,
            auto_start=auto_start,
            singleton=singleton,
            tags=tags or set(),
        )

        self._registrations[name] = registration
        self._type_to_name[manager_type] = name

        logger.debug(f"Registered manager '{name}' of type {manager_type.__name__}")

    def unregister_manager(self, name: str) -> None:
        """Unregister a manager."""
        if name not in self._registrations:
            raise ManagerError(f"Manager '{name}' is not registered")

        # Stop and dispose if running
        if name in self._instances:
            asyncio.create_task(self._dispose_manager(name))

        registration = self._registrations[name]
        del self._registrations[name]
        del self._type_to_name[registration.manager_type]

        # Clean up dependency graph
        self._dependency_graph.pop(name, None)
        for deps in self._dependency_graph.values():
            deps.discard(name)

        logger.debug(f"Unregistered manager '{name}'")

    def is_registered(self, name: str) -> bool:
        """Check if a manager is registered."""
        return name in self._registrations

    def get_registration(self, name: str) -> Optional[ManagerRegistration]:
        """Get registration info for a manager."""
        return self._registrations.get(name)

    def list_registrations(self, tags: Optional[Set[str]] = None) -> List[str]:
        """List registered manager names, optionally filtered by tags."""
        if tags is None:
            return list(self._registrations.keys())

        return [
            name
            for name, reg in self._registrations.items()
            if tags.intersection(reg.tags)
        ]

    async def create_manager(self, name: str) -> BaseManager:
        """Create a manager instance."""
        if name not in self._registrations:
            raise ManagerError(f"Manager '{name}' is not registered")

        registration = self._registrations[name]

        # Check if singleton and already exists
        if registration.singleton and registration.instance is not None:
            return registration.instance

        # Create new instance
        try:
            manager = registration.factory()

            # Store instance if singleton
            if registration.singleton:
                registration.instance = manager
                self._instances[name] = manager

            logger.debug(f"Created manager instance '{name}'")
            return manager

        except Exception as e:
            raise ManagerError(f"Failed to create manager '{name}': {e}") from e

    async def get_manager(self, name: str) -> Optional[BaseManager]:
        """Get a manager instance."""
        if name in self._instances:
            return self._instances[name]

        # Try to create if registered
        if name in self._registrations:
            return await self.create_manager(name)

        return None

    async def get_manager_by_type(self, manager_type: Type[T]) -> Optional[T]:
        """Get a manager instance by type."""
        name = self._type_to_name.get(manager_type)
        if name:
            manager = await self.get_manager(name)
            return manager if isinstance(manager, manager_type) else None
        return None

    def _build_dependency_graph(self) -> None:
        """Build the dependency graph for all registered managers."""
        self._dependency_graph.clear()

        for name, registration in self._registrations.items():
            # Create manager temporarily to get dependency info
            temp_manager = registration.factory()

            dependencies = set()
            for dep in temp_manager.info.dependencies:
                dep_name = self._type_to_name.get(dep.manager_type)
                if dep_name:
                    dependencies.add(dep_name)
                elif dep.required:
                    raise ManagerError(
                        f"Required dependency {dep.manager_type.__name__} not registered"
                    )

            self._dependency_graph[name] = dependencies

    def _resolve_initialization_order(self) -> List[str]:
        """Resolve the order for manager initialization based on dependencies and priorities."""
        self._build_dependency_graph()

        in_degree, managers_by_priority = self._calculate_degrees_and_priorities()
        queue = self._initialize_queue(in_degree, managers_by_priority)
        initialization_order = self._perform_topological_sort(queue, in_degree)

        self._validate_no_circular_dependencies(initialization_order)
        return initialization_order

    def _calculate_degrees_and_priorities(
        self,
    ) -> Tuple[DefaultDict[str, int], DefaultDict[int, List[str]]]:
        """Calculate in-degrees and group managers by priority."""
        in_degree: DefaultDict[str, int] = defaultdict(int)
        managers_by_priority: DefaultDict[int, List[str]] = defaultdict(list)

        for name, deps in self._dependency_graph.items():
            for dep in deps:
                in_degree[name] += 1

            registration = self._registrations[name]
            managers_by_priority[registration.priority.value].append(name)

        return in_degree, managers_by_priority

    def _initialize_queue(
        self,
        in_degree: DefaultDict[str, int],
        managers_by_priority: DefaultDict[int, List[str]],
    ) -> Deque[str]:
        """Initialize queue with managers that have no dependencies, sorted by priority."""
        queue: Deque[str] = deque()
        for priority in sorted(managers_by_priority.keys()):
            for name in managers_by_priority[priority]:
                if in_degree[name] == 0:
                    queue.append(name)
        return queue

    def _perform_topological_sort(self, queue: deque, in_degree: dict) -> List[str]:
        """Perform topological sort with priority consideration."""
        initialization_order = []

        while queue:
            current = queue.popleft()
            initialization_order.append(current)
            self._update_dependent_managers(current, queue, in_degree)

        return initialization_order

    def _update_dependent_managers(self, current: str, queue: deque, in_degree: dict):
        """Update in-degrees for dependent managers and add ready ones to queue."""
        for name, deps in self._dependency_graph.items():
            if current in deps:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    self._insert_by_priority(name, queue)

    def _insert_by_priority(self, name: str, queue: deque):
        """Insert manager into queue maintaining priority order."""
        registration = self._registrations[name]
        inserted = False
        for i, queued_name in enumerate(queue):
            queued_reg = self._registrations[queued_name]
            if registration.priority.value < queued_reg.priority.value:
                queue.insert(i, name)
                inserted = True
                break
        if not inserted:
            queue.append(name)

    def _validate_no_circular_dependencies(self, initialization_order: List[str]):
        """Check for circular dependencies and raise error if found."""
        if len(initialization_order) != len(self._registrations):
            remaining = set(self._registrations.keys()) - set(initialization_order)
            raise ManagerError(
                f"Circular dependency detected among managers: {remaining}"
            )

    async def initialize_all(self, auto_start: bool = True) -> None:
        """Initialize all registered managers in dependency order."""
        async with self._lock:
            if self._instances:
                logger.warning("Some managers are already initialized")

            initialization_order = self._resolve_initialization_order()
            logger.info(f"Initializing managers in order: {initialization_order}")

            initialized = []

            try:
                for name in initialization_order:
                    registration = self._registrations[name]

                    # Create manager instance
                    manager = await self.create_manager(name)

                    # Set up dependencies
                    for dep in manager.info.dependencies:
                        dep_name = self._type_to_name.get(dep.manager_type)
                        if dep_name and dep_name in self._instances:
                            manager.set_dependency(
                                dep.manager_type, self._instances[dep_name]
                            )

                    # Initialize manager
                    await manager.initialize(self._config_manager, self._event_manager)
                    initialized.append(name)

                    logger.info(f"Initialized manager '{name}'")

                    # Auto-start if configured
                    if auto_start and registration.auto_start:
                        await manager.start()
                        self._started_managers.add(name)
                        logger.info(f"Started manager '{name}'")

                # Store shutdown order (reverse of initialization)
                self._shutdown_order = list(reversed(initialized))

                logger.info("All managers initialized successfully")

            except Exception as e:
                # Cleanup on failure
                for name in reversed(initialized):
                    try:
                        if name in self._instances:
                            await self._instances[name].dispose()
                    except Exception as cleanup_error:
                        logger.error(
                            f"Error disposing manager '{name}' during cleanup: {cleanup_error}"
                        )

                raise InitializationError(f"Manager initialization failed: {e}") from e

    async def start_manager(self, name: str) -> None:
        """Start a specific manager."""
        if name not in self._instances:
            raise ManagerError(f"Manager '{name}' is not initialized")

        manager = self._instances[name]
        if manager.state != ComponentState.INITIALIZED:
            raise ManagerError(f"Manager '{name}' must be initialized before starting")

        await manager.start()
        self._started_managers.add(name)
        logger.info(f"Started manager '{name}'")

    async def stop_manager(self, name: str) -> None:
        """Stop a specific manager."""
        if name not in self._instances:
            logger.warning(f"Manager '{name}' is not initialized")
            return

        manager = self._instances[name]
        if manager.state == ComponentState.RUNNING:
            await manager.stop()
            self._started_managers.discard(name)
            logger.info(f"Stopped manager '{name}'")

    async def _dispose_manager(self, name: str) -> None:
        """Dispose of a specific manager."""
        if name in self._instances:
            manager = self._instances[name]
            await manager.dispose()
            del self._instances[name]
            self._started_managers.discard(name)

    async def shutdown_all(self) -> None:
        """Shutdown all managers in reverse initialization order."""
        async with self._lock:
            logger.info("Shutting down all managers")

            # Use stored shutdown order, or reverse of current instances
            shutdown_order = self._shutdown_order or list(
                reversed(self._instances.keys())
            )

            for name in shutdown_order:
                if name in self._instances:
                    try:
                        await self.stop_manager(name)
                        await self._dispose_manager(name)
                        logger.info(f"Shutdown manager '{name}'")
                    except Exception as e:
                        logger.error(f"Error shutting down manager '{name}': {e}")

            self._instances.clear()
            self._started_managers.clear()
            self._shutdown_order.clear()

            logger.info("All managers shutdown complete")

    async def get_system_health(self) -> Dict[str, Any]:
        """Get health status of all managers."""
        health_status = {}

        for name, manager in self._instances.items():
            try:
                status = await manager.get_health_status()
                health_status[name] = {
                    "status": status.value,
                    "state": manager.state.value,
                    "uptime": manager.metrics.current_uptime.total_seconds(),
                    "error_count": manager.metrics.error_count,
                    "last_error": manager.metrics.last_error,
                }
            except Exception as e:
                health_status[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(e),
                }

        # Overall system health
        overall_status = HealthStatus.HEALTHY
        if any(
            status.get("status") == HealthStatus.UNHEALTHY.value
            for status in health_status.values()
        ):
            overall_status = HealthStatus.UNHEALTHY
        elif any(
            status.get("status") == HealthStatus.DEGRADED.value
            for status in health_status.values()
        ):
            overall_status = HealthStatus.DEGRADED

        return {
            "overall_status": overall_status.value,
            "managers": health_status,
            "total_managers": len(self._instances),
            "running_managers": len(self._started_managers),
        }

    def get_manager_info(self) -> Dict[str, Any]:
        """Get information about all registered managers."""
        return {
            name: {
                "type": reg.manager_type.__name__,
                "priority": reg.priority.value,
                "auto_start": reg.auto_start,
                "singleton": reg.singleton,
                "tags": list(reg.tags),
                "registered_at": reg.registered_at.isoformat(),
                "instance_created": reg.instance is not None,
                "state": reg.instance.state.value if reg.instance else None,
            }
            for name, reg in self._registrations.items()
        }

    # BaseComponent interface implementation

    async def initialize(self) -> None:
        """Initialize method from BaseComponent interface."""
        # Manager registry is always initialized
        pass

    async def shutdown(self) -> None:
        """Shutdown method from BaseComponent interface."""
        await self.shutdown_all()


# Global manager registry instance
_global_registry: Optional[ManagerRegistry] = None


def get_manager_registry() -> ManagerRegistry:
    """Get the global manager registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ManagerRegistry()
    return _global_registry


def register_manager(name: str, manager_type: Type[BaseManager], **kwargs) -> None:
    """Register a manager with the global registry."""
    registry = get_manager_registry()
    registry.register_manager(name, manager_type, **kwargs)


async def get_manager(name: str) -> Optional[BaseManager]:
    """Get a manager from the global registry."""
    registry = get_manager_registry()
    return await registry.get_manager(name)


async def get_manager_by_type(manager_type: Type[T]) -> Optional[T]:
    """Get a manager by type from the global registry."""
    registry = get_manager_registry()
    return await registry.get_manager_by_type(manager_type)
