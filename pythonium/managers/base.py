"""
Core manager framework for the Pythonium MCP server.

This module provides the abstract base classes, lifecycle management,
and dependency injection system for all managers in the system.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    cast,
)

from pythonium.common.base import BaseComponent
from pythonium.common.config import PythoniumSettings, get_settings
from pythonium.common.events import EventManager, get_event_manager
from pythonium.common.exceptions import (
    InitializationError,
    ManagerError,
)
from pythonium.common.lifecycle import ComponentState
from pythonium.common.logging import get_logger
from pythonium.common.types import HealthStatus, MetadataDict

if TYPE_CHECKING:
    from pythonium.managers.config_manager import ConfigurationManager

logger = get_logger(__name__)

T = TypeVar("T")


class ManagerPriority(Enum):
    """Manager initialization priority levels."""

    CRITICAL = 0  # Core system managers (e.g., configuration, logging)
    HIGH = 10  # Essential managers (e.g., security, events)
    NORMAL = 50  # Standard managers (e.g., plugins, tools)
    LOW = 100  # Optional managers (e.g., metrics, monitoring)


@dataclass
class ManagerDependency:
    """Represents a dependency between managers."""

    manager_type: Type["BaseManager"]
    required: bool = True
    minimum_version: Optional[str] = None
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class ManagerMetrics:
    """Manager performance and health metrics."""

    start_time: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None
    initialization_time: float = 0.0
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    health_check_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_uptime(self) -> timedelta:
        """Calculate current uptime."""
        return datetime.utcnow() - self.start_time


@dataclass
class ManagerInfo:
    """Information about a manager."""

    name: str
    version: str
    description: str
    manager_type: Type["BaseManager"]
    priority: ManagerPriority = ManagerPriority.NORMAL
    dependencies: List["ManagerDependency"] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    metadata: MetadataDict = field(default_factory=dict)


class HealthCheck:
    """Health check configuration and state."""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], bool],
        interval: timedelta = timedelta(minutes=5),
        timeout: timedelta = timedelta(seconds=30),
        critical: bool = False,
    ):
        self.name = name
        self.check_func = check_func
        self.interval = interval
        self.timeout = timeout
        self.critical = critical
        self.last_check: Optional[datetime] = None
        self.last_result: Optional[bool] = None
        self.last_error: Optional[str] = None
        self.consecutive_failures = 0


class BaseManager(BaseComponent, ABC):
    """Abstract base class for all managers in the Pythonium system."""

    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        super().__init__(name, {})  # Pass name and empty config to BaseComponent
        self._info = ManagerInfo(
            name=name,
            version=version,
            description=description,
            manager_type=type(self),
        )
        self._state = ComponentState.CREATED
        self._metrics = ManagerMetrics()
        self._dependencies: Dict[Type["BaseManager"], "BaseManager"] = {}
        self._health_checks: Dict[str, HealthCheck] = {}
        self._settings: Optional[PythoniumSettings] = None
        self._event_manager: Optional[EventManager] = None
        self._config_manager: Optional["ConfigurationManager"] = None
        self._shutdown_callbacks: List[Callable[[], None]] = []
        self._lock = asyncio.Lock()

    @property
    def info(self) -> ManagerInfo:
        """Get manager information."""
        return self._info

    @property
    def state(self) -> ComponentState:
        """Get current manager state."""
        return self._state

    @property
    def metrics(self) -> ManagerMetrics:
        """Get manager metrics."""
        self._metrics.uptime = self._metrics.current_uptime
        return self._metrics

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._state == ComponentState.RUNNING

    @property
    def is_healthy(self) -> bool:
        """Check if manager is healthy."""
        return self._state == ComponentState.RUNNING and all(
            hc.last_result is not False for hc in self._health_checks.values()
        )

    # Abstract methods that subclasses must implement

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize the manager. Subclasses must implement this."""
        pass

    @abstractmethod
    async def _start(self) -> None:
        """Start the manager. Subclasses must implement this."""
        pass

    @abstractmethod
    async def _stop(self) -> None:
        """Stop the manager. Subclasses must implement this."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Cleanup manager resources. Subclasses must implement this."""
        pass

    # Lifecycle management

    async def initialize(
        self,
        settings: Optional[PythoniumSettings] = None,
        event_manager: Optional[EventManager] = None,
    ) -> None:
        """Initialize the manager with dependencies."""
        async with self._lock:
            if self._state != ComponentState.CREATED:
                raise ManagerError(f"Manager {self._info.name} is already initialized")

            self._state = ComponentState.INITIALIZING
            start_time = time.time()

            try:
                # Set up core dependencies
                self._settings = settings or get_settings()
                self._event_manager = event_manager or get_event_manager()

                # Validate dependencies
                await self._validate_dependencies()

                # Call subclass initialization
                await self._initialize()

                # Register default health checks
                await self._register_default_health_checks()

                self._state = ComponentState.INITIALIZED
                self._metrics.initialization_time = time.time() - start_time

                logger.info(f"Manager {self._info.name} initialized successfully")

            except Exception as e:
                self._state = ComponentState.ERROR
                self._metrics.error_count += 1
                self._metrics.last_error = str(e)
                logger.error(f"Failed to initialize manager {self._info.name}: {e}")
                raise InitializationError(f"Manager initialization failed: {e}") from e

    async def start(self) -> None:
        """Start the manager."""
        async with self._lock:
            if self._state != ComponentState.INITIALIZED:
                raise ManagerError(
                    f"Manager {self._info.name} must be initialized before starting"
                )

            self._state = ComponentState.STARTING

            try:
                # Call subclass start method
                await self._start()

                # Start health check monitoring
                await self._start_health_monitoring()

                self._state = ComponentState.RUNNING
                self._metrics.start_time = datetime.utcnow()

                # Emit started event
                if self._event_manager:
                    await self._event_manager.emit_event(
                        f"manager.{self._info.name}.started",
                        {
                            "manager": self._info.name,
                            "state": self._state.value,
                        },
                    )

                logger.info(f"Manager {self._info.name} started successfully")

            except Exception as e:
                self._state = ComponentState.ERROR
                self._metrics.error_count += 1
                self._metrics.last_error = str(e)
                logger.error(f"Failed to start manager {self._info.name}: {e}")
                raise ManagerError(f"Manager start failed: {e}") from e

    async def stop(self) -> None:
        """Stop the manager."""
        async with self._lock:
            if self._state not in [ComponentState.RUNNING, ComponentState.ERROR]:
                logger.warning(f"Manager {self._info.name} is not running")
                return

            self._state = ComponentState.STOPPING

            try:
                # Stop health monitoring
                await self._stop_health_monitoring()

                # Run shutdown callbacks
                for callback in self._shutdown_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in shutdown callback: {e}")

                # Call subclass stop method
                await self._stop()

                self._state = ComponentState.STOPPED

                # Emit stopped event
                if self._event_manager:
                    await self._event_manager.emit_event(
                        f"manager.{self._info.name}.stopped",
                        {
                            "manager": self._info.name,
                            "state": self._state.value,
                        },
                    )

                logger.info(f"Manager {self._info.name} stopped successfully")

            except Exception as e:
                self._state = ComponentState.ERROR
                self._metrics.error_count += 1
                self._metrics.last_error = str(e)
                logger.error(f"Failed to stop manager {self._info.name}: {e}")
                raise ManagerError(f"Manager stop failed: {e}") from e

    async def dispose(self) -> None:
        """Dispose of the manager and clean up resources."""
        if self._state == ComponentState.DISPOSED:
            return

        if self._state == ComponentState.RUNNING:
            await self.stop()

        try:
            await self._cleanup()
            self._state = ComponentState.DISPOSED
            logger.info(f"Manager {self._info.name} disposed successfully")
        except Exception as e:
            self._state = ComponentState.ERROR
            logger.error(f"Failed to dispose manager {self._info.name}: {e}")
            raise

    # BaseComponent interface implementation

    async def shutdown(self) -> None:
        """Shutdown method from BaseComponent interface."""
        await self.dispose()

    # Dependency management

    def add_dependency(self, dependency: ManagerDependency) -> None:
        """Add a dependency to this manager."""
        self._info.dependencies.append(dependency)

    def set_dependency(
        self, manager_type: Type["BaseManager"], manager: "BaseManager"
    ) -> None:
        """Set a dependency manager instance."""
        self._dependencies[manager_type] = manager

    def get_dependency(
        self, manager_type: Type["BaseManager"]
    ) -> Optional["BaseManager"]:
        """Get a dependency manager instance."""
        return self._dependencies.get(manager_type)

    async def _validate_dependencies(self) -> None:
        """Validate that all required dependencies are available."""
        for dep in self._info.dependencies:
            if dep.required and dep.manager_type not in self._dependencies:
                raise ManagerError(
                    f"Required dependency {dep.manager_type.__name__} not available"
                )

    # Health monitoring

    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add a health check."""
        self._health_checks[health_check.name] = health_check

    def remove_health_check(self, name: str) -> None:
        """Remove a health check."""
        self._health_checks.pop(name, None)

    async def _register_default_health_checks(self) -> None:
        """Register default health checks."""
        # Basic state check
        self.add_health_check(
            HealthCheck(
                name="state_check",
                check_func=lambda: self._state
                in [ComponentState.RUNNING, ComponentState.INITIALIZED],
                critical=True,
            )
        )

    async def _start_health_monitoring(self) -> None:
        """Start health check monitoring."""
        # This would start background tasks for periodic health checks
        # Implementation depends on specific requirements
        pass

    async def _stop_health_monitoring(self) -> None:
        """Stop health check monitoring."""
        # Stop background health check tasks
        pass

    async def run_health_checks(self) -> Dict[str, bool]:
        """Run all health checks and return results."""
        results = {}

        for name, health_check in self._health_checks.items():
            try:
                # Run the health check with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(health_check.check_func),
                    timeout=health_check.timeout.total_seconds(),
                )

                health_check.last_result = result
                health_check.last_check = datetime.utcnow()
                health_check.last_error = None

                if not result:
                    health_check.consecutive_failures += 1
                else:
                    health_check.consecutive_failures = 0

                results[name] = result

            except Exception as e:
                health_check.last_result = False
                health_check.last_check = datetime.utcnow()
                health_check.last_error = str(e)
                health_check.consecutive_failures += 1
                results[name] = False

                logger.error(f"Health check {name} failed: {e}")

        self._metrics.health_check_count += 1
        self._metrics.last_health_check = datetime.utcnow()

        return results

    async def get_health_status(self) -> HealthStatus:
        """Get comprehensive health status."""
        health_results = await self.run_health_checks()

        # Determine overall health
        critical_failures = [
            name
            for name, result in health_results.items()
            if not result and self._health_checks[name].critical
        ]

        if critical_failures:
            status = HealthStatus.UNHEALTHY
        elif not all(health_results.values()):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return status

    # Configuration access

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        if self._config_manager:
            return self._config_manager.get(
                f"managers.{self._info.name}.{key}", default
            )
        return default

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        if self._config_manager:
            self._config_manager.set(f"managers.{self._info.name}.{key}", value)

    # Event handling

    async def emit_event(self, event_name: str, data: Any = None) -> None:
        """Emit an event."""
        if self._event_manager:
            full_event_name = f"manager.{self._info.name}.{event_name}"
            await self._event_manager.emit_event(full_event_name, data)

    def add_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to be called during shutdown."""
        self._shutdown_callbacks.append(callback)

    def remove_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """Remove a shutdown callback."""
        if callback in self._shutdown_callbacks:
            self._shutdown_callbacks.remove(callback)

    # Utility methods

    def update_metric(self, name: str, value: Any) -> None:
        """Update a custom metric."""
        self._metrics.custom_metrics[name] = value

    def get_metric(self, name: str, default: Any) -> Any:
        """Get a custom metric value."""
        return self._metrics.custom_metrics.get(name, default)

    def __str__(self) -> str:
        return f"{self._info.name} ({self._state.value})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._info.name} [{self._state.value}]>"


class ConfigurableManager(BaseManager):
    """Base class for managers that support configuration."""

    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        super().__init__(name, version, description)
        self._config_section = f"managers.{name}"

    def get_manager_config(
        self, default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get the entire configuration section for this manager."""
        if self._config_manager:
            return cast(
                Dict[str, Any],
                self._config_manager.get(self._config_section, default or {}),
            )
        return default or {}

    def reload_config(self) -> None:
        """Reload configuration from the config manager."""
        if self._config_manager:
            # Trigger configuration reload
            pass  # Implementation depends on specific manager needs


# Manager registry and dependency injection will be in a separate module
