"""
Manager registry and dependency injection system for Pythonium.

This module provides centralized management of all system managers,
including dependency resolution, initialization ordering, and lifecycle coordination.
This is core infrastructure, not a modular manager capability.
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
from pythonium.common.logging import get_logger

logger = get_logger(__name__)

# Forward declaration for manager types
T = TypeVar("T")


@dataclass
class ManagerRegistration:
    """Registration information for a manager."""

    manager_type: Type[Any]  # Changed from BaseManager to Any to avoid circular import
    factory: Callable[[], Any]
    priority: int = 50  # Default priority (was ManagerPriority.NORMAL)
    auto_start: bool = True
    singleton: bool = True
    tags: Set[str] = field(default_factory=set)
    instance: Optional[Any] = None
    registered_at: datetime = field(default_factory=datetime.utcnow)


class ManagerRegistry(BaseComponent):
    """Central registry for all managers in the system."""

    def __init__(self):
        super().__init__(
            "manager_registry", {}
        )  # Pass name and config to BaseComponent
        self._registrations: Dict[str, ManagerRegistration] = {}
        self._instances: Dict[str, Any] = {}
        self._type_to_name: Dict[Type[Any], str] = {}
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
        priority: Any = 50,  # Changed to Any to handle both int and enum
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
            sig = inspect.signature(manager_type.__init__)
            params = list(sig.parameters.keys())

            # If the constructor is overridden and doesn't accept 'name' parameter
            if len(params) == 1 and params[0] == "self":  # Only self parameter

                def _create_manager_no_args():
                    # For managers that override __init__ and don't take name parameter
                    return manager_type()

                factory = _create_manager_no_args
            else:  # Constructor accepts name parameter (BaseManager default)

                def _create_manager_with_name():
                    return manager_type(name)  # type: ignore[call-arg]

                factory = _create_manager_with_name

        registration = ManagerRegistration(
            manager_type=manager_type,
            factory=factory,
            priority=(
                priority.value if hasattr(priority, "value") else priority
            ),  # Handle both enum and int
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

    async def create_manager(self, name: str) -> Any:
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

    async def get_manager(self, name: str) -> Optional[Any]:
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

            # Check if manager has dependency info
            if hasattr(temp_manager, "info") and hasattr(
                temp_manager.info, "dependencies"
            ):
                for dep in temp_manager.info.dependencies:
                    dep_name = self._type_to_name.get(dep.manager_type)
                    if dep_name:
                        dependencies.add(dep_name)
                    elif getattr(dep, "required", True):
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
            managers_by_priority[registration.priority].append(name)

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

        # Find the correct position to maintain priority order
        temp_queue: deque = deque()
        while queue and not inserted:
            other_name = queue.popleft()
            other_reg = self._registrations[other_name]

            if registration.priority <= other_reg.priority:
                temp_queue.append(name)
                temp_queue.append(other_name)
                inserted = True
            else:
                temp_queue.append(other_name)

        if not inserted:
            temp_queue.append(name)

        # Restore queue
        queue.extend(temp_queue)

    def _validate_no_circular_dependencies(self, order: List[str]):
        """Validate that no circular dependencies exist."""
        if len(order) != len(self._registrations):
            missing_managers = set(self._registrations.keys()) - set(order)
            raise ManagerError(
                f"Circular dependency detected involving: {missing_managers}"
            )

    async def start_all_managers(self) -> None:
        """Start all auto-start managers in dependency order."""
        async with self._lock:
            logger.info("Starting all managers...")

            initialization_order = self._resolve_initialization_order()
            self._shutdown_order = list(reversed(initialization_order))

            for name in initialization_order:
                registration = self._registrations[name]
                if registration.auto_start:
                    try:
                        await self.start_manager(name)
                        logger.info(f"Started manager '{name}'")
                    except Exception as e:
                        logger.error(f"Failed to start manager '{name}': {e}")
                        raise InitializationError(
                            f"Manager startup failed: {name}"
                        ) from e

            logger.info("All managers started successfully")

    async def start_manager(self, name: str) -> None:
        """Start a specific manager."""
        if name in self._started_managers:
            return  # Already started

        manager = await self.get_manager(name)
        if manager is None:
            raise ManagerError(f"Manager '{name}' not found")

        # Initialize the manager with dependencies
        if hasattr(manager, "initialize"):
            await manager.initialize(
                settings=self._config_manager,
                event_manager=self._event_manager,
            )

        # Start the manager
        if hasattr(manager, "start"):
            await manager.start()

        self._started_managers.add(name)

    async def stop_manager(self, name: str) -> None:
        """Stop a specific manager."""
        if name not in self._started_managers:
            return  # Not started

        manager = self._instances.get(name)
        if manager and hasattr(manager, "stop"):
            await manager.stop()

        self._started_managers.discard(name)

    async def _dispose_manager(self, name: str) -> None:
        """Dispose of a specific manager."""
        if name in self._instances:
            manager = self._instances[name]
            if hasattr(manager, "dispose"):
                await manager.dispose()
            elif hasattr(manager, "cleanup"):
                await manager.cleanup()
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
                # Try to get health status if manager supports it
                if hasattr(manager, "get_health_status"):
                    status = await manager.get_health_status()
                    health_status[name] = {
                        "status": (
                            status.value if hasattr(status, "value") else str(status)
                        ),
                        "state": (
                            manager.state.value
                            if hasattr(manager, "state")
                            else "unknown"
                        ),
                        "uptime": getattr(manager.metrics, "current_uptime", 0),
                        "error_count": (
                            getattr(manager.metrics, "error_count", 0)
                            if hasattr(manager, "metrics")
                            else 0
                        ),
                        "last_error": (
                            getattr(manager.metrics, "last_error", None)
                            if hasattr(manager, "metrics")
                            else None
                        ),
                    }
                else:
                    health_status[name] = {
                        "status": "healthy",
                        "state": (
                            "running" if name in self._started_managers else "stopped"
                        ),
                    }
            except Exception as e:
                health_status[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        # Overall system health
        overall_status = "healthy"
        if any(
            status.get("status") == "unhealthy" for status in health_status.values()
        ):
            overall_status = "unhealthy"
        elif any(
            status.get("status") == "degraded" for status in health_status.values()
        ):
            overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "managers": health_status,
            "total_managers": len(self._instances),
            "running_managers": len(self._started_managers),
        }

    def get_manager_info(self) -> Dict[str, Any]:
        """Get information about all registered managers."""
        return {
            name: {
                "type": reg.manager_type.__name__,
                "priority": reg.priority,
                "auto_start": reg.auto_start,
                "singleton": reg.singleton,
                "tags": list(reg.tags),
                "registered_at": reg.registered_at.isoformat(),
                "instance_created": reg.instance is not None,
                "state": getattr(reg.instance, "state", None),
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

    async def initialize_all(self) -> None:
        """Initialize all registered managers - alias for start_all_managers."""
        await self.start_all_managers()


# Global manager registry instance
_global_registry: Optional[ManagerRegistry] = None


def get_manager_registry() -> ManagerRegistry:
    """Get the global manager registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ManagerRegistry()
    return _global_registry


def register_manager(name: str, manager_type: Type[Any], **kwargs) -> None:
    """Register a manager with the global registry."""
    registry = get_manager_registry()
    registry.register_manager(name, manager_type, **kwargs)


async def get_manager(name: str) -> Optional[Any]:
    """Get a manager from the global registry."""
    registry = get_manager_registry()
    return await registry.get_manager(name)


async def get_manager_by_type(manager_type: Type[T]) -> Optional[T]:
    """Get a manager by type from the global registry."""
    registry = get_manager_registry()
    return await registry.get_manager_by_type(manager_type)
