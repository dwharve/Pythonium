"""
Event system for inter-plugin communication in the Pythonium framework.

This module provides a comprehensive event system that allows plugins
and components to communicate through events and listeners.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pythonium.common.base import BaseComponent
from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger
from pythonium.common.types import EventData, EventHandler, MetadataDict

logger = get_logger(__name__)


class EventPriority(Enum):
    """Event handler priority levels."""

    LOWEST = 100
    LOW = 75
    NORMAL = 50
    HIGH = 25
    HIGHEST = 0


@dataclass
class EventSubscription:
    """Represents an event subscription."""

    event_name: str
    handler: EventHandler
    priority: EventPriority = EventPriority.NORMAL
    once: bool = False  # Execute only once
    enabled: bool = True
    metadata: MetadataDict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    call_count: int = 0
    last_called: Optional[datetime] = None


class EventFilter:
    """Filter for events."""

    def __init__(
        self,
        event_pattern: Optional[str] = None,
        source_pattern: Optional[str] = None,
        data_filter: Optional[Callable[[Any], bool]] = None,
    ):
        self.event_pattern = event_pattern
        self.source_pattern = source_pattern
        self.data_filter = data_filter

    def matches(self, event: EventData) -> bool:
        """Check if event matches this filter."""
        if self.event_pattern and not self._pattern_match(
            self.event_pattern, event.name
        ):
            return False

        if self.source_pattern and event.source:
            if not self._pattern_match(self.source_pattern, event.source):
                return False

        if self.data_filter and not self.data_filter(event.data):
            return False

        return True

    def _pattern_match(self, pattern: str, value: str) -> bool:
        """Simple pattern matching with wildcards."""
        if "*" not in pattern:
            return pattern == value

        # Convert wildcard pattern to regex-like matching
        import re

        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", value))


class EventBus:
    """Central event bus for managing events and subscriptions."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._global_subscriptions: List[EventSubscription] = []
        self._event_filters: List[EventFilter] = []
        self._event_history: List[EventData] = []
        self._max_history = 1000
        self._logger = get_logger(f"{__name__}.bus.{name}")
        self._stats = {
            "events_published": 0,
            "events_handled": 0,
            "handlers_called": 0,
            "errors": 0,
        }

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        once: bool = False,
        metadata: Optional[MetadataDict] = None,
    ) -> EventSubscription:
        """Subscribe to an event."""
        subscription = EventSubscription(
            event_name=event_name,
            handler=handler,
            priority=priority,
            once=once,
            metadata=metadata or {},
        )

        if event_name == "*":
            # Global subscription for all events
            self._global_subscriptions.append(subscription)
            self._global_subscriptions.sort(key=lambda s: s.priority.value)
        else:
            # Specific event subscription
            if event_name not in self._subscriptions:
                self._subscriptions[event_name] = []

            self._subscriptions[event_name].append(subscription)
            self._subscriptions[event_name].sort(key=lambda s: s.priority.value)

        self._logger.debug(
            f"Subscribed to event '{event_name}' with priority {priority.name}"
        )
        return subscription

    def unsubscribe(self, subscription: EventSubscription) -> bool:
        """Unsubscribe from an event."""
        event_name = subscription.event_name

        if event_name == "*":
            try:
                self._global_subscriptions.remove(subscription)
                self._logger.debug("Unsubscribed from global events")
                return True
            except ValueError:
                return False
        else:
            if event_name in self._subscriptions:
                try:
                    self._subscriptions[event_name].remove(subscription)
                    if not self._subscriptions[event_name]:
                        del self._subscriptions[event_name]
                    self._logger.debug(f"Unsubscribed from event '{event_name}'")
                    return True
                except ValueError:
                    return False

        return False

    def unsubscribe_handler(self, handler: EventHandler) -> int:
        """Unsubscribe all subscriptions for a specific handler."""
        removed_count = 0

        # Remove from global subscriptions
        self._global_subscriptions = [
            s for s in self._global_subscriptions if s.handler != handler
        ]

        # Remove from specific event subscriptions
        for event_name in list(self._subscriptions.keys()):
            original_count = len(self._subscriptions[event_name])
            self._subscriptions[event_name] = [
                s for s in self._subscriptions[event_name] if s.handler != handler
            ]

            removed_count += original_count - len(self._subscriptions[event_name])

            if not self._subscriptions[event_name]:
                del self._subscriptions[event_name]

        if removed_count > 0:
            self._logger.debug(f"Removed {removed_count} subscriptions for handler")

        return removed_count

    async def publish(
        self,
        event_name: str,
        data: Any = None,
        source: Optional[str] = None,
        metadata: Optional[MetadataDict] = None,
    ) -> int:
        """Publish an event."""
        event = EventData(
            name=event_name,
            data=data,
            timestamp=datetime.utcnow(),
            source=source,
        )

        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        self._stats["events_published"] += 1
        self._logger.debug(f"Publishing event '{event_name}' from source '{source}'")

        # Check event filters
        if self._event_filters:
            if not any(f.matches(event) for f in self._event_filters):
                self._logger.debug(f"Event '{event_name}' filtered out")
                return 0

        handlers_called = 0

        # Get subscriptions for this event
        subscriptions = []

        # Add specific event subscriptions
        if event_name in self._subscriptions:
            subscriptions.extend(self._subscriptions[event_name])

        # Add global subscriptions
        subscriptions.extend(self._global_subscriptions)

        # Sort by priority
        subscriptions.sort(key=lambda s: s.priority.value)

        # Execute handlers
        for subscription in subscriptions:
            if not subscription.enabled:
                continue

            try:
                self._logger.debug(f"Calling handler for event '{event_name}'")

                # Update subscription stats
                subscription.call_count += 1
                subscription.last_called = datetime.utcnow()

                # Call handler
                if asyncio.iscoroutinefunction(subscription.handler):
                    await subscription.handler(event)
                else:
                    subscription.handler(event)

                handlers_called += 1
                self._stats["handlers_called"] += 1

                # Remove if once-only subscription
                if subscription.once:
                    self.unsubscribe(subscription)

            except Exception as e:
                self._stats["errors"] += 1
                self._logger.error(
                    f"Error in event handler for '{event_name}': {e}",
                    exception=e,
                )
                # Continue with other handlers

        self._stats["events_handled"] += 1
        self._logger.debug(
            f"Event '{event_name}' handled by {handlers_called} handlers"
        )

        return handlers_called

    def add_filter(self, event_filter: EventFilter) -> None:
        """Add an event filter."""
        self._event_filters.append(event_filter)
        self._logger.debug("Added event filter")

    def remove_filter(self, event_filter: EventFilter) -> bool:
        """Remove an event filter."""
        try:
            self._event_filters.remove(event_filter)
            self._logger.debug("Removed event filter")
            return True
        except ValueError:
            return False

    def get_subscriptions(
        self, event_name: Optional[str] = None
    ) -> List[EventSubscription]:
        """Get subscriptions for an event or all subscriptions."""
        if event_name is None:
            # Return all subscriptions
            all_subs = []
            for subs in self._subscriptions.values():
                all_subs.extend(subs)
            all_subs.extend(self._global_subscriptions)
            return all_subs
        elif event_name == "*":
            return self._global_subscriptions.copy()
        else:
            return self._subscriptions.get(event_name, []).copy()

    def get_event_history(
        self, event_name: Optional[str] = None, limit: Optional[int] = None
    ) -> List[EventData]:
        """Get event history."""
        history = self._event_history

        if event_name:
            history = [e for e in history if e.name == event_name]

        if limit:
            history = history[-limit:]

        return history

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "name": self.name,
            "stats": self._stats.copy(),
            "subscription_count": sum(
                len(subs) for subs in self._subscriptions.values()
            )
            + len(self._global_subscriptions),
            "event_types": list(self._subscriptions.keys()),
            "filter_count": len(self._event_filters),
            "history_size": len(self._event_history),
        }

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        self._logger.debug("Event history cleared")


class EventManager(BaseComponent):
    """Manages multiple event buses."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("event_manager", config or {})
        self._buses: Dict[str, EventBus] = {}
        self._default_bus_name = "default"

        # Create default bus
        self._buses[self._default_bus_name] = EventBus(self._default_bus_name)

    async def initialize(self) -> None:
        """Initialize the event manager."""
        logger.info("Event manager initialized")

    async def shutdown(self) -> None:
        """Shutdown the event manager."""
        # Clear all subscriptions
        for bus in self._buses.values():
            bus._subscriptions.clear()
            bus._global_subscriptions.clear()

        logger.info("Event manager shutdown")

    def create_bus(self, name: str) -> EventBus:
        """Create a new event bus."""
        if name in self._buses:
            raise PythoniumError(f"Event bus already exists: {name}")

        bus = EventBus(name)
        self._buses[name] = bus
        logger.info(f"Created event bus: {name}")
        return bus

    def get_bus(self, name: Optional[str] = None) -> EventBus:
        """Get an event bus by name."""
        bus_name = name or self._default_bus_name

        if bus_name not in self._buses:
            raise PythoniumError(f"Event bus not found: {bus_name}")

        return self._buses[bus_name]

    def remove_bus(self, name: str) -> bool:
        """Remove an event bus."""
        if name == self._default_bus_name:
            raise PythoniumError("Cannot remove default event bus")

        if name in self._buses:
            del self._buses[name]
            logger.info(f"Removed event bus: {name}")
            return True

        return False

    def list_buses(self) -> List[str]:
        """List all event bus names."""
        return list(self._buses.keys())

    # Convenience methods for default bus
    def subscribe(self, *args, **kwargs) -> EventSubscription:
        """Subscribe to the default bus."""
        return self.get_bus().subscribe(*args, **kwargs)

    def unsubscribe(self, *args, **kwargs) -> bool:
        """Unsubscribe from the default bus."""
        return self.get_bus().unsubscribe(*args, **kwargs)

    async def publish(self, *args, **kwargs) -> int:
        """Publish to the default bus."""
        return await self.get_bus().publish(*args, **kwargs)

    async def emit_event(self, event_name: str, data: Any = None) -> int:
        """Emit an event (alias for publish)."""
        return await self.publish(event_name, data)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all buses."""
        return {bus_name: bus.get_stats() for bus_name, bus in self._buses.items()}


# Global event manager instance
_global_event_manager: Optional[EventManager] = None


def get_event_manager() -> EventManager:
    """Get the global event manager instance."""
    global _global_event_manager
    if _global_event_manager is None:
        _global_event_manager = EventManager()
    return _global_event_manager


def set_event_manager(manager: EventManager) -> None:
    """Set the global event manager instance."""
    global _global_event_manager
    _global_event_manager = manager


# Convenience functions for the default event bus
async def publish_event(
    event_name: str, data: Any = None, source: Optional[str] = None
) -> int:
    """Publish an event to the default bus."""
    return await get_event_manager().publish(event_name, data, source)


def subscribe_to_event(
    event_name: str, handler: EventHandler, **kwargs
) -> EventSubscription:
    """Subscribe to an event on the default bus."""
    return get_event_manager().subscribe(event_name, handler, **kwargs)


def unsubscribe_from_event(subscription: EventSubscription) -> bool:
    """Unsubscribe from an event on the default bus."""
    return get_event_manager().unsubscribe(subscription)
