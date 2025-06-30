"""
Plugin factory and extension system for the Pythonium framework.

This module provides utilities for creating different types of plugins
and managing plugin extensions and hooks.
"""

import asyncio
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pythonium.common.exceptions import PluginError
from pythonium.common.logging import get_logger
from pythonium.common.plugins import BasePlugin, PluginConfig
from pythonium.common.types import MetadataDict

logger = get_logger(__name__)

T = TypeVar("T", bound=BasePlugin)


class PluginType(Enum):
    """Types of plugins supported by the framework."""

    TOOL = "tool"
    MANAGER = "manager"
    TRANSPORT = "transport"
    MIDDLEWARE = "middleware"
    EXTENSION = "extension"


class HookPriority(Enum):
    """Priority levels for plugin hooks."""

    LOWEST = 100
    LOW = 75
    NORMAL = 50
    HIGH = 25
    HIGHEST = 0


@dataclass
class PluginHook:
    """Represents a plugin hook."""

    name: str
    handler: Callable
    priority: HookPriority = HookPriority.NORMAL
    enabled: bool = True
    metadata: MetadataDict = field(default_factory=dict)

    def __post_init__(self):
        pass  # No longer needed since metadata has a proper default


class PluginFactory:
    """Factory for creating plugins."""

    def __init__(self):
        self._plugin_types: Dict[str, Type[BasePlugin]] = {}
        self._logger = get_logger(f"{__name__}.factory")

    def register_plugin_type(
        self, plugin_type: str, plugin_class: Type[BasePlugin]
    ) -> None:
        """Register a plugin type."""
        self._logger.info(f"Registering plugin type: {plugin_type}")
        self._plugin_types[plugin_type] = plugin_class

    def create_plugin(
        self, plugin_type: str, config: Optional[PluginConfig] = None, **kwargs
    ) -> BasePlugin:
        """Create a plugin instance."""
        if plugin_type not in self._plugin_types:
            raise PluginError(f"Unknown plugin type: {plugin_type}")

        plugin_class = self._plugin_types[plugin_type]

        try:
            if config:
                return plugin_class(config=config, **kwargs)
            else:
                return plugin_class(**kwargs)

        except Exception as e:
            raise PluginError(f"Failed to create plugin of type {plugin_type}: {e}")

    def list_plugin_types(self) -> List[str]:
        """List available plugin types."""
        return list(self._plugin_types.keys())


class ExtensionPoint:
    """Represents an extension point where plugins can hook into."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._hooks: List[PluginHook] = []
        self._logger = get_logger(f"{__name__}.extension.{name}")

    def add_hook(self, hook: PluginHook) -> None:
        """Add a hook to this extension point."""
        self._logger.debug(f"Adding hook {hook.name} to extension point {self.name}")
        self._hooks.append(hook)
        # Sort by priority
        self._hooks.sort(key=lambda h: h.priority.value)

    def remove_hook(self, hook_name: str) -> None:
        """Remove a hook from this extension point."""
        self._logger.debug(
            f"Removing hook {hook_name} from extension point {self.name}"
        )
        self._hooks = [h for h in self._hooks if h.name != hook_name]

    async def execute_hooks(self, *args, **kwargs) -> List[Any]:
        """Execute all hooks in this extension point."""
        results = []

        for hook in self._hooks:
            if not hook.enabled:
                continue

            try:
                if asyncio.iscoroutinefunction(hook.handler):
                    result = await hook.handler(*args, **kwargs)
                else:
                    result = hook.handler(*args, **kwargs)

                results.append(result)

            except Exception as e:
                self._logger.error(f"Error executing hook {hook.name}: {e}")
                # Continue with other hooks

        return results

    def get_hooks(self) -> List[PluginHook]:
        """Get all hooks in this extension point."""
        return self._hooks.copy()


class ExtensionManager:
    """Manages extension points and plugin hooks."""

    def __init__(self):
        self._extension_points: Dict[str, ExtensionPoint] = {}
        self._logger = get_logger(f"{__name__}.extension_manager")

    def create_extension_point(
        self, name: str, description: str = ""
    ) -> ExtensionPoint:
        """Create a new extension point."""
        self._logger.info(f"Creating extension point: {name}")

        if name in self._extension_points:
            raise PluginError(f"Extension point already exists: {name}")

        extension_point = ExtensionPoint(name, description)
        self._extension_points[name] = extension_point
        return extension_point

    def get_extension_point(self, name: str) -> Optional[ExtensionPoint]:
        """Get an extension point by name."""
        return self._extension_points.get(name)

    def register_hook(
        self,
        extension_point_name: str,
        hook_name: str,
        handler: Callable,
        priority: HookPriority = HookPriority.NORMAL,
        metadata: Optional[MetadataDict] = None,
    ) -> None:
        """Register a hook with an extension point."""
        extension_point = self.get_extension_point(extension_point_name)
        if not extension_point:
            raise PluginError(f"Extension point not found: {extension_point_name}")

        hook = PluginHook(
            name=hook_name,
            handler=handler,
            priority=priority,
            metadata=metadata or {},
        )

        extension_point.add_hook(hook)
        self._logger.info(
            f"Registered hook {hook_name} with extension point {extension_point_name}"
        )

    def unregister_hook(self, extension_point_name: str, hook_name: str) -> None:
        """Unregister a hook from an extension point."""
        extension_point = self.get_extension_point(extension_point_name)
        if extension_point:
            extension_point.remove_hook(hook_name)
            self._logger.info(
                f"Unregistered hook {hook_name} from extension point {extension_point_name}"
            )

    async def execute_extension_point(self, name: str, *args, **kwargs) -> List[Any]:
        """Execute all hooks in an extension point."""
        extension_point = self.get_extension_point(name)
        if not extension_point:
            self._logger.warning(f"Extension point not found: {name}")
            return []

        return await extension_point.execute_hooks(*args, **kwargs)

    def list_extension_points(self) -> List[str]:
        """List all extension points."""
        return list(self._extension_points.keys())


class ExtensiblePlugin(BasePlugin):
    """Base class for plugins that support extensions."""

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._extension_manager = ExtensionManager()
        self._setup_extension_points()

    @abstractmethod
    def _setup_extension_points(self) -> None:
        """Setup extension points for this plugin."""
        pass

    def get_extension_manager(self) -> ExtensionManager:
        """Get the extension manager."""
        return self._extension_manager

    async def execute_hooks(self, extension_point: str, *args, **kwargs) -> List[Any]:
        """Execute hooks in an extension point."""
        return await self._extension_manager.execute_extension_point(
            extension_point, *args, **kwargs
        )


class MiddlewarePlugin(BasePlugin):
    """Base class for middleware plugins."""

    @abstractmethod
    async def process_request(self, request: Any, context: Dict[str, Any]) -> Any:
        """Process an incoming request."""
        pass

    @abstractmethod
    async def process_response(self, response: Any, context: Dict[str, Any]) -> Any:
        """Process an outgoing response."""
        pass

    async def process_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Optional[Any]:
        """Process an error (optional)."""
        return None


class MiddlewareStack:
    """Manages a stack of middleware plugins."""

    def __init__(self):
        self._middleware: List[MiddlewarePlugin] = []
        self._logger = get_logger(f"{__name__}.middleware_stack")

    def add_middleware(self, middleware: MiddlewarePlugin) -> None:
        """Add middleware to the stack."""
        self._logger.info(f"Adding middleware: {middleware.plugin_name}")
        self._middleware.append(middleware)

    def remove_middleware(self, plugin_name: str) -> None:
        """Remove middleware from the stack."""
        self._logger.info(f"Removing middleware: {plugin_name}")
        self._middleware = [m for m in self._middleware if m.plugin_name != plugin_name]

    async def process_request(self, request: Any, context: Dict[str, Any]) -> Any:
        """Process request through all middleware."""
        current_request = request

        for middleware in self._middleware:
            try:
                current_request = await middleware.process_request(
                    current_request, context
                )
            except Exception as e:
                self._logger.error(f"Error in middleware {middleware.plugin_name}: {e}")
                # Try to handle the error
                error_result = await middleware.process_error(e, context)
                if error_result is not None:
                    return error_result
                raise

        return current_request

    async def process_response(self, response: Any, context: Dict[str, Any]) -> Any:
        """Process response through all middleware (in reverse order)."""
        current_response = response

        for middleware in reversed(self._middleware):
            try:
                current_response = await middleware.process_response(
                    current_response, context
                )
            except Exception as e:
                self._logger.error(f"Error in middleware {middleware.plugin_name}: {e}")
                # Try to handle the error
                error_result = await middleware.process_error(e, context)
                if error_result is not None:
                    return error_result
                raise

        return current_response


def plugin_hook(extension_point: str, priority: HookPriority = HookPriority.NORMAL):
    """Decorator for marking methods as plugin hooks."""

    def decorator(func):
        func._plugin_hook = True
        func._extension_point = extension_point
        func._hook_priority = priority
        return func

    return decorator


def create_plugin_decorator(plugin_type: str):
    """Create a decorator for registering plugin classes."""

    def decorator(cls):
        if not issubclass(cls, BasePlugin):
            raise PluginError("Plugin class must inherit from BasePlugin")

        cls._plugin_type = plugin_type
        return cls

    return decorator


# Common plugin decorators
tool_plugin = create_plugin_decorator(PluginType.TOOL.value)
manager_plugin = create_plugin_decorator(PluginType.MANAGER.value)
transport_plugin = create_plugin_decorator(PluginType.TRANSPORT.value)
middleware_plugin = create_plugin_decorator(PluginType.MIDDLEWARE.value)
extension_plugin = create_plugin_decorator(PluginType.EXTENSION.value)
