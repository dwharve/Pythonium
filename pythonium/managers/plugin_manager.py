"""
Plugin Manager for the Pythonium MCP server.

This manager handles plugin discovery, loading, lifecycle management,
and sandboxing using the common plugin framework.
"""

import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

from pythonium.common.base import Result
from pythonium.common.exceptions import PluginError
from pythonium.common.logging import get_logger
from pythonium.common.plugins import (
    BasePlugin,
    DependencyResolver,
    PluginDiscovery,
    PluginLoader,
    PluginRegistry,
)
from pythonium.managers.base import BaseManager, ManagerPriority
from pythonium.managers.config_manager import ConfigurationManager

logger = get_logger(__name__)


@dataclass
class PluginEnvironment:
    """Represents an isolated plugin environment."""

    name: str
    path: Path
    python_path: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    isolated: bool = True
    virtual_env: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# Type alias for plugin loading results
PluginLoadResult = Result[BasePlugin]


class PluginSandbox:
    """Provides sandboxing and isolation for plugins."""

    def __init__(self, plugin_id: str, restrictions: Optional[Dict[str, Any]] = None):
        self.plugin_id = plugin_id
        self.restrictions = restrictions or {}
        self.allowed_modules = set(self.restrictions.get("allowed_modules", []))
        self.blocked_modules = set(self.restrictions.get("blocked_modules", []))
        self.resource_limits = self.restrictions.get("resource_limits", {})
        self._original_import: Optional[Callable] = None

    def __enter__(self):
        """Enter sandbox context."""
        if self.blocked_modules or self.allowed_modules:
            import builtins

            self._original_import = builtins.__import__
            builtins.__import__ = self._sandboxed_import
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sandbox context."""
        if self._original_import:
            import builtins

            builtins.__import__ = self._original_import

    def _sandboxed_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """Sandboxed import function."""
        # Check if module is blocked
        if self.blocked_modules and any(
            name.startswith(blocked) for blocked in self.blocked_modules
        ):
            raise ImportError(f"Module '{name}' is blocked by plugin sandbox")

        # Check if module is in allowed list (if allowlist is specified)
        if self.allowed_modules and not any(
            name.startswith(allowed) for allowed in self.allowed_modules
        ):
            # Allow standard library modules by default
            if not self._is_stdlib_module(name):
                raise ImportError(f"Module '{name}' is not in allowed modules list")

        return (
            self._original_import(name, globals, locals, fromlist, level)
            if self._original_import
            else __import__(name, globals, locals, fromlist, level)
        )

    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if module is part of standard library."""
        # This is a simplified check - in production you'd want a more comprehensive list
        stdlib_prefixes = [
            "os",
            "sys",
            "json",
            "time",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "typing",
            "abc",
            "asyncio",
            "concurrent",
            "threading",
            "multiprocessing",
            "logging",
            "pathlib",
            "urllib",
            "http",
        ]
        return any(module_name.startswith(prefix) for prefix in stdlib_prefixes)


class PluginManager(BaseManager):
    """Comprehensive plugin management system."""

    def __init__(self):
        super().__init__(
            name="plugin",
            version="1.0.0",
            description="Plugin discovery, loading, and lifecycle management",
        )
        self._info.priority = ManagerPriority.HIGH

        # Core plugin components
        self._registry = PluginRegistry()
        self._loader = PluginLoader()
        self._discovery: Optional[PluginDiscovery] = None  # Will be initialized later
        self._dependency_resolver = DependencyResolver()

        # Plugin management
        self._loaded_plugins: Dict[str, BasePlugin] = {}
        self._plugin_environments: Dict[str, PluginEnvironment] = {}
        self._load_results: Dict[str, PluginLoadResult] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="plugin-loader"
        )

        # Configuration
        self._plugin_directories: List[Path] = []
        self._auto_discovery = True
        self._sandboxing_enabled = True
        self._default_sandbox_restrictions: Dict[str, Any] = {}

        # Events and callbacks
        self._lifecycle_callbacks: Dict[str, List[Callable]] = {
            "before_load": [],
            "after_load": [],
            "before_unload": [],
            "after_unload": [],
            "on_error": [],
        }

    async def _initialize(self) -> None:
        """Initialize the plugin manager."""
        # Get configuration
        config_manager = self.get_dependency(ConfigurationManager)
        if config_manager and isinstance(config_manager, ConfigurationManager):
            await self._load_configuration(config_manager)

        # Set up default plugin directories
        if not self._plugin_directories:
            self._plugin_directories = [
                Path("plugins"),
                Path("pythonium/plugins"),
                Path.home() / ".pythonium" / "plugins",
            ]

        # Initialize plugin discovery with directories that exist
        existing_directories = [d for d in self._plugin_directories if d.exists()]
        self._discovery = PluginDiscovery(existing_directories)

        # Load default sandbox restrictions
        self._default_sandbox_restrictions = {
            "blocked_modules": ["subprocess", "os.system", "eval", "exec"],
            "resource_limits": {
                "max_memory": 100 * 1024 * 1024,  # 100MB
                "max_execution_time": 30.0,  # 30 seconds
            },
        }

    async def _start(self) -> None:
        """Start the plugin manager."""
        # Discover plugins if auto-discovery is enabled
        if self._auto_discovery:
            await self.discover_plugins()

        # Auto-load plugins marked for auto-loading
        await self._auto_load_plugins()

    async def _stop(self) -> None:
        """Stop the plugin manager."""
        # Unload all plugins
        await self.unload_all_plugins()

        # Shutdown executor
        self._executor.shutdown(wait=True)

    async def _cleanup(self) -> None:
        """Cleanup plugin manager resources."""
        self._loaded_plugins.clear()
        self._plugin_environments.clear()
        self._load_results.clear()
        self._lifecycle_callbacks.clear()

    async def _load_configuration(self, config_manager: ConfigurationManager) -> None:
        """Load plugin manager configuration."""
        plugin_config = config_manager.get("plugins", {})

        # Plugin directories
        if "directories" in plugin_config:
            self._plugin_directories = [Path(d) for d in plugin_config["directories"]]

        # Discovery settings
        self._auto_discovery = plugin_config.get("auto_discovery", True)

        # Sandboxing settings
        self._sandboxing_enabled = plugin_config.get("sandboxing_enabled", True)
        if "sandbox_restrictions" in plugin_config:
            self._default_sandbox_restrictions.update(
                plugin_config["sandbox_restrictions"]
            )

    # Plugin discovery methods

    async def discover_plugins(self) -> List[str]:
        """Discover plugins in configured directories."""
        discovered = []

        try:
            if self._discovery:
                plugins = await self._discovery.discover_plugins()
                for plugin_info in plugins:
                    if (
                        plugin_info.get("id")
                        and plugin_info["id"] not in self._registry.get_all()
                    ):
                        self._registry.register(plugin_info["id"], plugin_info)
                        discovered.append(plugin_info["id"])
                        logger.debug(
                            f"Discovered plugin: {plugin_info.get('id', 'unknown')}"
                        )

        except Exception as e:
            logger.error(f"Error discovering plugins: {e}")

        logger.info(f"Discovered {len(discovered)} new plugins")
        await self.emit_event(
            "plugins_discovered",
            {"count": len(discovered), "plugins": discovered},
        )

        return discovered

    async def scan_plugin_file(self, file_path: Path) -> Optional[str]:
        """Scan a specific file for plugin definitions."""
        if not self._discovery:
            logger.warning("Plugin discovery not initialized")
            return None

        try:
            # Use the private method directly since there's no public API for single file scanning
            plugin_info = await self._discovery._analyze_python_file(file_path)
            if plugin_info:
                self._registry.register(plugin_info.get("id", "unknown"), plugin_info)
                logger.debug(f"Registered plugin from file: {file_path}")
                return plugin_info.get("id")
        except Exception as e:
            logger.error(f"Error scanning plugin file {file_path}: {e}")

        return None

    # Plugin loading and unloading

    def _resolve_plugin_dependencies(
        self, plugin_id: str, all_plugins_info: Dict[str, Any]
    ) -> List[str]:
        """Resolve dependencies for a specific plugin."""
        # Simple dependency resolution - in practice you'd want more sophisticated logic
        # For now, just return the plugin itself
        return [plugin_id]

    async def load_plugin(self, plugin_id: str, **kwargs) -> PluginLoadResult:
        """Load a specific plugin."""
        start_time = asyncio.get_event_loop().time()

        # Check if already loaded
        if plugin_id in self._loaded_plugins:
            return Result.error_result("Plugin is already loaded")

        # Get plugin info from discovery/registry
        plugin_info = self._registry.get(plugin_id)
        if not plugin_info:
            return Result.error_result("Plugin not found in registry")

        try:
            # Call before_load callbacks
            await self._call_lifecycle_callbacks("before_load", plugin_id, plugin_info)

            # For dependency resolution, we need to work with all discovered plugins
            # Get all plugin info and create a minimal dependency graph
            all_plugins_info = self._registry.get_all()
            dependency_order = self._resolve_plugin_dependencies(
                plugin_id, all_plugins_info
            )
            if plugin_id not in dependency_order:
                raise PluginError(
                    f"Dependency resolution failed for plugin {plugin_id}"
                )

            # Load dependencies first
            for dep_id in dependency_order:
                if dep_id != plugin_id and dep_id not in self._loaded_plugins:
                    dep_result = await self.load_plugin(dep_id)
                    if not dep_result.success:
                        raise PluginError(
                            f"Failed to load dependency {dep_id}: {dep_result.error}"
                        )

            # Create sandbox if enabled
            sandbox = None
            if self._sandboxing_enabled:
                restrictions = self._get_plugin_restrictions(plugin_id)
                sandbox = PluginSandbox(plugin_id, restrictions)

            # Load the plugin
            plugin_instance = await self._load_plugin_instance(plugin_info, sandbox)

            # Initialize the plugin
            await plugin_instance.initialize()

            # Store loaded plugin
            self._loaded_plugins[plugin_id] = plugin_instance

            # Calculate load time
            load_time = asyncio.get_event_loop().time() - start_time

            logger.info(f"Successfully loaded plugin: {plugin_id}")

            # Call after_load callbacks
            await self._call_lifecycle_callbacks(
                "after_load", plugin_id, plugin_instance
            )

            # Emit event
            await self.emit_event(
                "plugin_loaded",
                {"plugin_id": plugin_id, "load_time": load_time},
            )

            # Store and return success result
            result = Result.success_result(
                plugin_instance, metadata={"load_time": load_time}
            )
            self._load_results[plugin_id] = result
            return result

        except Exception as e:
            load_time = asyncio.get_event_loop().time() - start_time

            logger.error(f"Failed to load plugin {plugin_id}: {e}")

            # Call error callbacks
            await self._call_lifecycle_callbacks("on_error", plugin_id, e)

            # Store and return error result
            result = Result.error_result(str(e), metadata={"load_time": load_time})
            self._load_results[plugin_id] = result
            return result

    async def _load_plugin_instance(self, plugin_info, sandbox=None) -> BasePlugin:
        """Load plugin instance with optional sandboxing."""

        def _load():
            with sandbox if sandbox else nullcontext():
                return self._loader.load_plugin(plugin_info)

        # Load in thread pool to avoid blocking
        plugin_instance = await asyncio.to_thread(_load)
        return cast(BasePlugin, plugin_instance)

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a specific plugin."""
        if plugin_id not in self._loaded_plugins:
            logger.warning(f"Plugin {plugin_id} is not loaded")
            return False

        try:
            plugin_instance = self._loaded_plugins[plugin_id]

            # Call before_unload callbacks
            await self._call_lifecycle_callbacks(
                "before_unload", plugin_id, plugin_instance
            )

            # Check if other plugins depend on this one
            dependents = self._find_dependent_plugins(plugin_id)
            if dependents:
                logger.warning(f"Plugin {plugin_id} has dependents: {dependents}")
                # Optionally unload dependents first
                for dependent_id in dependents:
                    await self.unload_plugin(dependent_id)

            # Cleanup the plugin
            await plugin_instance.shutdown()

            # Remove from loaded plugins
            del self._loaded_plugins[plugin_id]

            logger.info(f"Successfully unloaded plugin: {plugin_id}")

            # Call after_unload callbacks
            await self._call_lifecycle_callbacks(
                "after_unload", plugin_id, plugin_instance
            )

            # Emit event
            await self.emit_event("plugin_unloaded", {"plugin_id": plugin_id})

            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            await self._call_lifecycle_callbacks("on_error", plugin_id, e)
            return False

    async def reload_plugin(self, plugin_id: str) -> PluginLoadResult:
        """Reload a plugin (unload then load)."""
        if plugin_id in self._loaded_plugins:
            await self.unload_plugin(plugin_id)

        return await self.load_plugin(plugin_id)

    async def unload_all_plugins(self) -> None:
        """Unload all loaded plugins."""
        # Unload in reverse dependency order
        plugin_ids = list(self._loaded_plugins.keys())
        for plugin_id in reversed(plugin_ids):
            await self.unload_plugin(plugin_id)

    async def _auto_load_plugins(self) -> None:
        """Auto-load plugins marked for auto-loading."""
        auto_load_plugins = []

        for plugin_id in self._registry.list_plugins():
            plugin_info = self._registry.get(plugin_id)
            if (
                plugin_info
                and isinstance(plugin_info, dict)
                and plugin_info.get("metadata", {}).get("auto_load", False)
            ):
                auto_load_plugins.append(plugin_id)

        if auto_load_plugins:
            logger.info(f"Auto-loading {len(auto_load_plugins)} plugins")

            for plugin_id in auto_load_plugins:
                result = await self.load_plugin(plugin_id)
                if not result.success:
                    logger.error(
                        f"Failed to auto-load plugin {plugin_id}: {result.error}"
                    )

    # Plugin information and status

    def list_plugins(self, loaded_only: bool = False) -> List[str]:
        """List available or loaded plugins."""
        if loaded_only:
            return list(self._loaded_plugins.keys())
        else:
            return self._registry.list_names()

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a plugin."""
        plugin_info = self._registry.get(plugin_id)
        if not plugin_info or not isinstance(plugin_info, dict):
            return None

        is_loaded = plugin_id in self._loaded_plugins
        load_result = self._load_results.get(plugin_id)

        info = {
            "id": plugin_info.get("id", plugin_id),
            "name": plugin_info.get("name", "Unknown"),
            "version": plugin_info.get("version", "Unknown"),
            "description": plugin_info.get("description", ""),
            "author": plugin_info.get("author", "Unknown"),
            "priority": plugin_info.get("priority", "normal"),
            "dependencies": plugin_info.get("dependencies", []),
            "metadata": plugin_info.get("metadata", {}),
            "is_loaded": is_loaded,
            "state": None,
            "load_result": None,
        }

        if is_loaded:
            plugin_instance = self._loaded_plugins[plugin_id]
            info["state"] = plugin_instance.state.value

        if load_result:
            info["load_result"] = {
                "success": load_result.success,
                "error": load_result.error,
                "execution_time": load_result.execution_time,
                "metadata": load_result.metadata,
            }

        return info

    def get_plugin_status(self) -> Dict[str, Any]:
        """Get overall plugin system status."""
        total_plugins = len(self._registry.list_plugins())
        loaded_plugins = len(self._loaded_plugins)
        failed_loads = len([r for r in self._load_results.values() if not r.success])

        return {
            "total_plugins": total_plugins,
            "loaded_plugins": loaded_plugins,
            "failed_loads": failed_loads,
            "plugin_directories": [str(d) for d in self._plugin_directories],
            "auto_discovery": self._auto_discovery,
            "sandboxing_enabled": self._sandboxing_enabled,
        }

    # Helper methods

    def _get_plugin_restrictions(self, plugin_id: str) -> Dict[str, Any]:
        """Get sandbox restrictions for a plugin."""
        # Start with defaults
        restrictions = self._default_sandbox_restrictions.copy()

        # Apply plugin-specific restrictions from configuration
        config_manager = self.get_dependency(ConfigurationManager)
        if config_manager and isinstance(config_manager, ConfigurationManager):
            plugin_restrictions = config_manager.get(f"plugins.{plugin_id}.sandbox", {})
            restrictions.update(plugin_restrictions)

        return restrictions

    def _find_dependent_plugins(self, plugin_id: str) -> List[str]:
        """Find plugins that depend on the given plugin."""
        dependents = []

        for loaded_id, plugin_instance in self._loaded_plugins.items():
            plugin_info = self._registry.get(loaded_id)
            if plugin_info and isinstance(plugin_info, dict):
                dependencies = plugin_info.get("dependencies", [])
                if plugin_id in dependencies:
                    dependents.append(loaded_id)

        return dependents

    async def _call_lifecycle_callbacks(
        self, event: str, plugin_id: str, data: Any
    ) -> None:
        """Call lifecycle callbacks for an event."""
        callbacks = self._lifecycle_callbacks.get(event, [])

        for callback in callbacks:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(plugin_id, data)
                else:
                    callback(plugin_id, data)
            except Exception as e:
                logger.error(f"Error in {event} callback: {e}")

    # Public API for lifecycle callbacks

    def add_lifecycle_callback(self, event: str, callback: Callable) -> None:
        """Add a lifecycle callback."""
        if event in self._lifecycle_callbacks:
            self._lifecycle_callbacks[event].append(callback)

    def remove_lifecycle_callback(self, event: str, callback: Callable) -> None:
        """Remove a lifecycle callback."""
        if (
            event in self._lifecycle_callbacks
            and callback in self._lifecycle_callbacks[event]
        ):
            self._lifecycle_callbacks[event].remove(callback)


# Context manager for null operations
class nullcontext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
