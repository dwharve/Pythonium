"""
Plugin framework foundation for the Pythonium framework.

This module provides the core plugin system including abstract base classes,
lifecycle management, discovery mechanisms, and plugin registry.
"""

import importlib
import inspect
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

from pydantic import BaseModel, Field, field_validator

from pythonium.common.base import BaseComponent, Registry
from pythonium.common.exceptions import (
    PluginDependencyError,
    PluginExecutionError,
    PluginLoadError,
)
from pythonium.common.lifecycle import ComponentState
from pythonium.common.logging import get_logger
from pythonium.common.serialization import from_json
from pythonium.common.types import (
    PluginInfo,
)

logger = get_logger(__name__)


class PluginPriority(Enum):
    """Plugin priority levels for loading order."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class PluginDependency:
    """Represents a plugin dependency."""

    name: str
    version: Optional[str] = None
    optional: bool = False
    min_version: Optional[str] = None
    max_version: Optional[str] = None


class PluginConfig(BaseModel):
    """Plugin configuration schema."""

    name: str = Field(description="Plugin name")
    version: str = Field(default="1.0.0", description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    author: str = Field(default="", description="Plugin author")
    email: Optional[str] = Field(default=None, description="Author email")
    license: Optional[str] = Field(default=None, description="Plugin license")
    homepage: Optional[str] = Field(default=None, description="Plugin homepage")

    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list, description="Plugin dependencies"
    )
    python_requires: Optional[str] = Field(
        default=None, description="Required Python version"
    )

    # Configuration
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    priority: int = Field(
        default=PluginPriority.NORMAL.value, description="Loading priority"
    )
    auto_load: bool = Field(default=True, description="Auto-load on discovery")

    # Plugin-specific configuration
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Plugin-specific config"
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        valid_priorities = [p.value for p in PluginPriority]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v


class BasePlugin(BaseComponent, ABC):
    """Abstract base class for all plugins."""

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(name=self.plugin_name, config=config.dict() if config else {})
        self.plugin_config = config or PluginConfig(name=self.plugin_name)
        self.state = ComponentState.DISCOVERED
        self.dependencies: List[PluginDependency] = []
        self.dependents: Set[str] = set()
        self.load_time: Optional[datetime] = None
        self.error_count = 0
        self.last_error: Optional[Exception] = None

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Plugin name identifier."""
        pass

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Plugin version."""
        pass

    @property
    @abstractmethod
    def plugin_description(self) -> str:
        """Plugin description."""
        pass

    @abstractmethod
    def get_plugin_dependencies(self) -> List[PluginDependency]:
        """Get plugin dependencies."""
        pass

    @abstractmethod
    async def plugin_initialize(self) -> None:
        """Initialize the plugin."""
        pass

    @abstractmethod
    async def plugin_shutdown(self) -> None:
        """Shutdown the plugin."""
        pass

    async def initialize(self) -> None:
        """Initialize the plugin component."""
        try:
            self.state = ComponentState.INITIALIZING
            logger.info(f"Initializing plugin: {self.plugin_name}")

            await self.plugin_initialize()

            self.state = ComponentState.ACTIVE
            self.load_time = datetime.utcnow()
            logger.success(f"Plugin initialized successfully: {self.plugin_name}")

        except Exception as e:
            self.state = ComponentState.ERROR
            self.last_error = e
            self.error_count += 1
            logger.error(f"Failed to initialize plugin {self.plugin_name}: {e}")
            raise PluginExecutionError(f"Plugin initialization failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown the plugin component."""
        try:
            self.state = ComponentState.STOPPING
            logger.info(f"Shutting down plugin: {self.plugin_name}")

            await self.plugin_shutdown()

            self.state = ComponentState.STOPPED
            logger.info(f"Plugin shutdown complete: {self.plugin_name}")

        except Exception as e:
            self.state = ComponentState.ERROR
            self.last_error = e
            self.error_count += 1
            logger.error(f"Failed to shutdown plugin {self.plugin_name}: {e}")
            raise PluginExecutionError(f"Plugin shutdown failed: {e}")

    def get_plugin_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name=self.plugin_name,
            version=self.plugin_version,
            description=self.plugin_description,
            author=self.plugin_config.author,
            dependencies=[dep.name for dep in self.get_plugin_dependencies()],
        )

    def get_plugin_status(self) -> Dict[str, Any]:
        """Get comprehensive plugin status."""
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "state": self.state.value,
            "load_time": (self.load_time.isoformat() if self.load_time else None),
            "error_count": self.error_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "dependencies": [dep.name for dep in self.dependencies],
            "dependents": list(self.dependents),
            "config": self.plugin_config.dict(),
        }


class PluginDiscovery:
    """Plugin discovery mechanism."""

    def __init__(self, search_paths: List[Path]):
        self.search_paths = [Path(p) for p in search_paths]
        self.discovered_plugins: Dict[str, Dict[str, Any]] = {}
        self._logger = get_logger(f"{__name__}.discovery")

    async def discover_plugins(self) -> List[Dict[str, Any]]:
        """Discover plugins in search paths."""
        self._logger.info(f"Discovering plugins in {len(self.search_paths)} paths")

        discovered = []

        for search_path in self.search_paths:
            if not search_path.exists():
                self._logger.warning(
                    f"Plugin search path does not exist: {search_path}"
                )
                continue

            path_plugins = await self._discover_in_path(search_path)
            discovered.extend(path_plugins)

        self._logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    async def _discover_in_path(self, path: Path) -> List[Dict[str, Any]]:
        """Discover plugins in a specific path."""
        plugins = []

        try:
            # Look for Python files and packages
            for item in path.iterdir():
                if (
                    item.is_file()
                    and item.suffix == ".py"
                    and not item.name.startswith("_")
                ):
                    plugin_info = await self._analyze_python_file(item)
                    if plugin_info:
                        plugins.append(plugin_info)

                elif item.is_dir() and not item.name.startswith("."):
                    # Check if it's a Python package (has __init__.py)
                    init_file = item / "__init__.py"
                    if init_file.exists():
                        plugin_info = await self._analyze_python_package(item)
                        if plugin_info:
                            plugins.append(plugin_info)

        except Exception as e:
            self._logger.error(f"Error discovering plugins in {path}: {e}")

        return plugins

    async def _analyze_python_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a Python file for plugin classes."""
        try:
            # Read the file and check for plugin classes
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple heuristic: look for BasePlugin inheritance
            if "BasePlugin" in content and "class " in content:
                return {
                    "type": "file",
                    "path": file_path,
                    "module_name": file_path.stem,
                    "discovered_at": datetime.utcnow(),
                }

        except Exception as e:
            self._logger.debug(f"Error analyzing {file_path}: {e}")

        return None

    async def _analyze_python_package(
        self, package_path: Path
    ) -> Optional[Dict[str, Any]]:
        """Analyze a Python package for plugin classes."""
        try:
            # Look for plugin configuration file
            config_files = [
                package_path / "plugin.yaml",
                package_path / "plugin.yml",
                package_path / "plugin.json",
                package_path / "plugin.toml",
            ]

            config_file = None
            for cf in config_files:
                if cf.exists():
                    config_file = cf
                    break

            return {
                "type": "package",
                "path": package_path,
                "module_name": package_path.name,
                "config_file": config_file,
                "discovered_at": datetime.utcnow(),
            }

        except Exception as e:
            self._logger.debug(f"Error analyzing package {package_path}: {e}")

        return None


class PluginLoader:
    """Plugin loading mechanism."""

    def __init__(self):
        self.loaded_modules: Dict[str, Any] = {}
        self._logger = get_logger(f"{__name__}.loader")

    async def load_plugin(self, plugin_info: Dict[str, Any]) -> BasePlugin:
        """Load a plugin from discovery information."""
        self._logger.info(f"Loading plugin: {plugin_info['module_name']}")

        try:
            # Import the module
            module = await self._import_plugin_module(plugin_info)

            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                raise PluginLoadError(
                    f"No plugin class found in {plugin_info['module_name']}"
                )

            # Load configuration if available
            config = await self._load_plugin_config(plugin_info)

            # Instantiate plugin
            plugin = plugin_class(config=config)

            # Validate plugin
            if not isinstance(plugin, BasePlugin):
                raise PluginLoadError("Plugin class must inherit from BasePlugin")

            self._logger.success(f"Plugin loaded successfully: {plugin.plugin_name}")
            return plugin

        except Exception as e:
            self._logger.error(
                f"Failed to load plugin {plugin_info['module_name']}: {e}"
            )
            raise PluginLoadError(f"Plugin load failed: {e}")

    async def _import_plugin_module(self, plugin_info: Dict[str, Any]) -> Any:
        """Import a plugin module."""
        module_name = plugin_info["module_name"]
        plugin_path = plugin_info["path"]

        try:
            # Add plugin path to sys.path temporarily
            if plugin_path.parent not in sys.path:
                sys.path.insert(0, str(plugin_path.parent))

            # Import the module
            if module_name in self.loaded_modules:
                # Reload if already loaded
                module = importlib.reload(self.loaded_modules[module_name])
            else:
                module = importlib.import_module(module_name)
                self.loaded_modules[module_name] = module

            return module

        except Exception as e:
            raise PluginLoadError(f"Failed to import module {module_name}: {e}")

    def _find_plugin_class(self, module: Any) -> Optional[Type[BasePlugin]]:
        """Find the plugin class in a module."""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BasePlugin)
                and obj is not BasePlugin
                and not inspect.isabstract(obj)
            ):
                return obj
        return None

    async def _load_plugin_config(
        self, plugin_info: Dict[str, Any]
    ) -> Optional[PluginConfig]:
        """Load plugin configuration."""
        config_file = plugin_info.get("config_file")
        if not config_file or not config_file.exists():
            return None

        try:
            # Load configuration based on file type
            if config_file.suffix in [".yaml", ".yml"]:
                import yaml

                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
            elif config_file.suffix == ".json":
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = from_json(f.read())
            else:
                self._logger.warning(f"Unsupported config file format: {config_file}")
                return None

            return PluginConfig(**config_data)

        except Exception as e:
            self._logger.error(f"Failed to load plugin config {config_file}: {e}")
            return None


class DependencyResolver:
    """Plugin dependency resolution."""

    def __init__(self):
        self._logger = get_logger(f"{__name__}.resolver")

    def resolve_dependencies(self, plugins: Dict[str, BasePlugin]) -> List[str]:
        """Resolve plugin dependencies and return loading order."""
        self._logger.info("Resolving plugin dependencies")

        # Build dependency graph
        graph = {}
        for name, plugin in plugins.items():
            dependencies = [dep.name for dep in plugin.get_plugin_dependencies()]
            graph[name] = dependencies

        # Topological sort to determine loading order
        try:
            order = self._topological_sort(graph)
            self._logger.info(f"Dependency resolution complete. Loading order: {order}")
            return order

        except PluginDependencyError as e:
            self._logger.error(f"Dependency resolution failed: {e}")
            raise

    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph."""
        # Kahn's algorithm
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                if neighbor in in_degree:
                    in_degree[neighbor] += 1
                else:
                    raise PluginDependencyError(f"Missing dependency: {neighbor}")

        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(graph):
            raise PluginDependencyError("Circular dependency detected")

        return result


class PluginRegistry(Registry):
    """Registry for managing plugins."""

    def __init__(self):
        super().__init__()
        self._discovery = None
        self._loader = PluginLoader()
        self._resolver = DependencyResolver()
        self._logger = get_logger(f"{__name__}.registry")

    def set_discovery(self, discovery: PluginDiscovery) -> None:
        """Set the plugin discovery mechanism."""
        self._discovery = discovery

    async def discover_and_load_plugins(self, search_paths: List[Path]) -> None:
        """Discover and load all plugins from search paths."""
        if not self._discovery:
            self._discovery = PluginDiscovery(search_paths)

        # Discover plugins
        discovered = await self._discovery.discover_plugins()

        # Load plugins
        plugins = {}
        for plugin_info in discovered:
            try:
                plugin = await self._loader.load_plugin(plugin_info)
                plugins[plugin.plugin_name] = plugin
            except Exception as e:
                self._logger.error(
                    f"Failed to load plugin {plugin_info['module_name']}: {e}"
                )

        # Resolve dependencies and determine loading order
        if plugins:
            try:
                loading_order = self._resolver.resolve_dependencies(plugins)

                # Register plugins in dependency order
                for plugin_name in loading_order:
                    plugin = plugins[plugin_name]
                    self.register_plugin(plugin)

            except PluginDependencyError as e:
                self._logger.error(f"Plugin dependency resolution failed: {e}")
                # Register plugins without dependency ordering
                for plugin in plugins.values():
                    self.register_plugin(plugin)

    def register_plugin(self, plugin: BasePlugin) -> None:
        """Register a plugin."""
        self._logger.info(f"Registering plugin: {plugin.plugin_name}")

        metadata = {
            "plugin_info": plugin.get_plugin_info(),
            "registered_at": datetime.utcnow(),
            "state": plugin.state.value,
        }

        self.register(plugin.plugin_name, plugin, metadata)
        plugin.state = ComponentState.LOADED

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        self._logger.info(f"Unregistering plugin: {plugin_name}")
        self.unregister(plugin_name)

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """List all registered plugin names."""
        return self.list_names()

    def get_plugin_status(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get plugin status information."""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.get_plugin_status()
        return None

    def get_all_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all plugins."""
        status = {}
        for plugin_name in self.list_plugins():
            plugin = self.get_plugin(plugin_name)
            if plugin:
                status[plugin_name] = plugin.get_plugin_status()
        return status
