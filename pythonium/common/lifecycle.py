"""
Unified lifecycle management framework for the Pythonium system.

This module provides a consolidated approach to component lifecycle management,
state tracking, and event handling across all system components.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar

from pythonium.common.events import EventManager, get_event_manager
from pythonium.common.exceptions import LifecycleError
from pythonium.common.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ComponentState(Enum):
    """Unified component lifecycle states."""

    # Creation and Discovery
    CREATED = "created"
    DISCOVERED = "discovered"

    # Loading and Initialization
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"

    # Connection and Session
    CONNECTING = "connecting"

    # Operation States
    STARTING = "starting"
    RUNNING = "running"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"

    # Cleanup and Shutdown
    STOPPING = "stopping"
    STOPPED = "stopped"
    CLEANUP = "cleanup"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    DISPOSED = "disposed"

    # Error State
    ERROR = "error"


class LifecycleEvent(Enum):
    """Lifecycle events that can be emitted."""

    STATE_CHANGED = "state_changed"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR_OCCURRED = "error_occurred"
    DISPOSED = "disposed"


class LifecycleMixin(ABC):
    """
    Mixin class providing unified lifecycle management capabilities.

    This mixin standardizes state management, event handling, and lifecycle
    transitions across all components in the system.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state = ComponentState.CREATED
        self._state_history: List[tuple[ComponentState, datetime]] = [
            (ComponentState.CREATED, datetime.utcnow())
        ]
        self._lifecycle_lock = asyncio.Lock()
        self._lifecycle_callbacks: Dict[ComponentState, List[Callable]] = {}
        self._event_manager: Optional[EventManager] = None
        self._shutdown_callbacks: List[Callable[[], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []

    @property
    def state(self) -> ComponentState:
        """Get current component state."""
        return self._state

    @property
    def state_history(self) -> List[tuple[ComponentState, datetime]]:
        """Get component state history."""
        return self._state_history.copy()

    def get_time_in_state(self) -> timedelta:
        """Get time spent in current state."""
        if not self._state_history:
            return timedelta(0)
        last_transition = self._state_history[-1][1]
        return datetime.utcnow() - last_transition

    async def transition_to(self, new_state: ComponentState, **kwargs) -> None:
        """
        Transition to a new state with proper validation and event handling.

        Args:
            new_state: Target state to transition to
            **kwargs: Additional context for the transition
        """
        async with self._lifecycle_lock:
            old_state = self._state

            # Validate transition
            if not self._is_valid_transition(old_state, new_state):
                raise LifecycleError(
                    f"Invalid state transition from {old_state.value} to {new_state.value}"
                )

            # Update state
            self._state = new_state
            self._state_history.append((new_state, datetime.utcnow()))

            # Emit state change event
            await self._emit_lifecycle_event(
                LifecycleEvent.STATE_CHANGED,
                {"old_state": old_state.value, "new_state": new_state.value, **kwargs},
            )

            # Execute state-specific callbacks
            await self._execute_state_callbacks(new_state)

            logger.debug(
                f"Component {getattr(self, 'name', 'unknown')} "
                f"transitioned from {old_state.value} to {new_state.value}"
            )

    def add_state_callback(
        self, state: ComponentState, callback: Callable[[], None]
    ) -> None:
        """Add a callback to be executed when entering a specific state."""
        if state not in self._lifecycle_callbacks:
            self._lifecycle_callbacks[state] = []
        self._lifecycle_callbacks[state].append(callback)

    def add_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to be executed during shutdown."""
        self._shutdown_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Add a callback to be executed when an error occurs."""
        self._error_callbacks.append(callback)

    def _is_valid_transition(
        self, from_state: ComponentState, to_state: ComponentState
    ) -> bool:
        """
        Validate if a state transition is allowed.

        Override this method in subclasses to implement custom transition logic.
        """
        # Default validation - allow most transitions except invalid ones
        invalid_transitions = {
            # Can't go from disposed to anything
            ComponentState.DISPOSED: set(ComponentState) - {ComponentState.DISPOSED},
            # Can't skip initialization steps
            ComponentState.CREATED: {
                ComponentState.RUNNING,
                ComponentState.ACTIVE,
                ComponentState.READY,
            },
        }

        return to_state not in invalid_transitions.get(from_state, set())

    async def _execute_state_callbacks(self, state: ComponentState) -> None:
        """Execute callbacks for the given state."""
        callbacks = self._lifecycle_callbacks.get(state, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error executing state callback for {state.value}: {e}")

    async def _emit_lifecycle_event(
        self, event: LifecycleEvent, data: Dict[str, Any]
    ) -> None:
        """Emit a lifecycle event."""
        if not self._event_manager:
            self._event_manager = get_event_manager()

        if self._event_manager:
            await self._event_manager.emit_event(
                f"lifecycle.{event.value}",
                {
                    "component": getattr(self, "name", "unknown"),
                    "component_type": type(self).__name__,
                    "timestamp": datetime.utcnow().isoformat(),
                    **data,
                },
            )

    async def _handle_error(self, error: Exception) -> None:
        """Handle lifecycle errors."""
        # Transition to error state
        try:
            await self.transition_to(ComponentState.ERROR, error=str(error))
        except Exception as transition_error:
            logger.error(f"Failed to transition to error state: {transition_error}")

        # Execute error callbacks
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as callback_error:
                logger.error(f"Error callback failed: {callback_error}")

        # Emit error event
        await self._emit_lifecycle_event(
            LifecycleEvent.ERROR_OCCURRED,
            {"error": str(error), "error_type": type(error).__name__},
        )

    # Standard lifecycle methods with default implementations
    async def initialize_lifecycle(self) -> None:
        """Initialize the component lifecycle."""
        try:
            await self.transition_to(ComponentState.INITIALIZING)
            await self._do_initialize()
            await self.transition_to(ComponentState.INITIALIZED)
        except Exception as e:
            await self._handle_error(e)
            raise

    async def start_lifecycle(self) -> None:
        """Start the component lifecycle."""
        try:
            await self.transition_to(ComponentState.STARTING)
            await self._do_start()
            await self.transition_to(ComponentState.RUNNING)
        except Exception as e:
            await self._handle_error(e)
            raise

    async def stop_lifecycle(self) -> None:
        """Stop the component lifecycle."""
        try:
            await self.transition_to(ComponentState.STOPPING)
            await self._do_stop()
            await self.transition_to(ComponentState.STOPPED)
        except Exception as e:
            await self._handle_error(e)
            raise

    async def dispose_lifecycle(self) -> None:
        """Dispose the component lifecycle."""
        try:
            await self.transition_to(ComponentState.CLEANUP)

            # Execute shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Shutdown callback failed: {e}")

            await self._do_dispose()
            await self.transition_to(ComponentState.DISPOSED)
        except Exception as e:
            await self._handle_error(e)
            raise

    # Abstract methods for subclasses to implement
    @abstractmethod
    async def _do_initialize(self) -> None:
        """Perform component-specific initialization."""
        pass

    @abstractmethod
    async def _do_start(self) -> None:
        """Perform component-specific startup."""
        pass

    @abstractmethod
    async def _do_stop(self) -> None:
        """Perform component-specific shutdown."""
        pass

    @abstractmethod
    async def _do_dispose(self) -> None:
        """Perform component-specific disposal."""
        pass


class LifecycleManager:
    """
    Manager for coordinating lifecycle operations across multiple components.
    """

    def __init__(self):
        self._components: Dict[str, LifecycleMixin] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    def register_component(
        self,
        name: str,
        component: LifecycleMixin,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """Register a component with optional dependencies."""
        self._components[name] = component
        self._dependencies[name] = set(dependencies or [])

    async def initialize_all(self) -> None:
        """Initialize all components in dependency order."""
        async with self._lock:
            order = self._get_initialization_order()
            for name in order:
                component = self._components[name]
                logger.info(f"Initializing component: {name}")
                await component.initialize_lifecycle()

    async def start_all(self) -> None:
        """Start all components in dependency order."""
        async with self._lock:
            order = self._get_initialization_order()
            for name in order:
                component = self._components[name]
                logger.info(f"Starting component: {name}")
                await component.start_lifecycle()

    async def stop_all(self) -> None:
        """Stop all components in reverse dependency order."""
        async with self._lock:
            order = list(reversed(self._get_initialization_order()))
            for name in order:
                component = self._components[name]
                logger.info(f"Stopping component: {name}")
                try:
                    await component.stop_lifecycle()
                except Exception as e:
                    logger.error(f"Failed to stop component {name}: {e}")

    async def dispose_all(self) -> None:
        """Dispose all components in reverse dependency order."""
        async with self._lock:
            order = list(reversed(self._get_initialization_order()))
            for name in order:
                component = self._components[name]
                logger.info(f"Disposing component: {name}")
                try:
                    await component.dispose_lifecycle()
                except Exception as e:
                    logger.error(f"Failed to dispose component {name}: {e}")

    def _get_initialization_order(self) -> List[str]:
        """Get component initialization order based on dependencies."""
        # Simple topological sort
        order = []
        visited = set()
        temp_visited = set()

        def visit(name: str):
            if name in temp_visited:
                raise LifecycleError(f"Circular dependency detected involving {name}")
            if name in visited:
                return

            temp_visited.add(name)
            for dep in self._dependencies.get(name, set()):
                if dep in self._components:
                    visit(dep)
            temp_visited.remove(name)
            visited.add(name)
            order.append(name)

        for name in self._components:
            if name not in visited:
                visit(name)

        return order


# Global lifecycle manager instance
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get the global lifecycle manager instance."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager
