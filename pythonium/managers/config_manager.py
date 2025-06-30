"""
Configuration Manager for the Pythonium MCP server.

This manager provides centralized configuration management with support for
multiple formats, environment variables, hot-reload, and configuration validation.
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

# Optional watchdog imports
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    ObserverType = Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    ObserverType = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore

from pythonium.common.base import Result
from pythonium.common.config import get_settings
from pythonium.common.exceptions import ConfigurationError
from pythonium.common.logging import get_logger
from pythonium.common.serialization import SerializationFormat
from pythonium.managers.base import BaseManager, ManagerPriority

logger = get_logger(__name__)


@dataclass
class ConfigurationSource:
    """Configuration source information."""

    path: Path
    format: SerializationFormat
    priority: int = 0  # Higher priority overrides lower
    watch: bool = True
    required: bool = True
    last_modified: Optional[datetime] = None
    last_loaded: Optional[datetime] = None
    load_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
@dataclass
class ConfigurationChange:
    """Configuration change notification."""

    source: Optional[ConfigurationSource]
    old_value: Any
    new_value: Any
    key_path: str
    change_type: str  # 'added', 'modified', 'removed'
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConfigurationWatcher(FileSystemEventHandler):
    """File system watcher for configuration files."""

    def __init__(self, config_manager: "ConfigurationManager"):
        self.config_manager = config_manager
        self.debounce_delay = 1.0  # seconds
        self._pending_reloads: Set[Path] = set()
        self._reload_tasks: Dict[Path, asyncio.Task] = {}

    def on_modified(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)

            # Check if this is a configuration file we're watching
            if self.config_manager._is_watched_file(file_path):
                asyncio.create_task(self._schedule_reload(file_path))

    async def _schedule_reload(self, file_path: Path):
        """Schedule a debounced reload of the configuration file."""
        # Cancel existing reload task for this file
        if file_path in self._reload_tasks:
            self._reload_tasks[file_path].cancel()

        # Schedule new reload after debounce delay
        self._reload_tasks[file_path] = asyncio.create_task(
            self._debounced_reload(file_path)
        )

    async def _debounced_reload(self, file_path: Path):
        """Perform debounced reload of configuration file."""
        await asyncio.sleep(self.debounce_delay)

        try:
            await self.config_manager._reload_source(file_path)
        finally:
            self._reload_tasks.pop(file_path, None)


class ConfigurationManager(BaseManager):
    """Advanced configuration manager with hot-reload and validation."""

    def __init__(self):
        super().__init__(
            name="configuration",
            version="1.0.0",
            description="Configuration management with hot-reload support",
        )
        self._info.priority = ManagerPriority.CRITICAL

        self._settings = get_settings()
        self._sources: Dict[str, ConfigurationSource] = {}
        self._fs_observer: Optional[Any] = None  # Observer instance when available
        self._fs_handler: Optional[Any] = None  # ConfigurationWatcher instance
        self._change_callbacks: List[Callable[[ConfigurationChange], None]] = []
        self._validation_schemas: Dict[str, Dict[str, Any]] = {}
        self._environment_prefix = "PYTHONIUM_"
        self._current_config: Dict[str, Any] = {}

        # Default configuration paths
        self._default_config_paths = [
            Path("pythonium.yaml"),
            Path("pythonium.yml"),
            Path("pythonium.json"),
            Path("pythonium.toml"),
            Path("config/pythonium.yaml"),
            Path("config/pythonium.yml"),
            Path("config/pythonium.json"),
            Path("config/pythonium.toml"),
        ]

    async def _initialize(self) -> None:
        """Initialize the configuration manager."""
        # Load default configuration schema
        await self._load_default_schema()

        # Discover and load configuration files
        await self._discover_config_files()

        # Load environment variables
        await self._load_environment_variables()

        # Set up file watching if enabled
        if self.get_config("hot_reload", True):
            await self._setup_file_watching()

    async def _start(self) -> None:
        """Start the configuration manager."""
        # Start file watching
        if self._fs_observer:
            self._fs_observer.start()

        # Emit initial configuration loaded event
        await self.emit_event(
            "configuration_loaded",
            {
                "sources": len(self._sources),
                "total_keys": len(self._current_config),
            },
        )

    async def _stop(self) -> None:
        """Stop the configuration manager."""
        # Stop file watching
        if self._fs_observer:
            self._fs_observer.stop()
            self._fs_observer.join()

    async def _cleanup(self) -> None:
        """Cleanup configuration manager resources."""
        # Stop file system observer
        if self._fs_observer:
            self._fs_observer.stop()
            self._fs_observer.join()

        self._sources.clear()
        self._change_callbacks.clear()

    async def _load_default_schema(self) -> None:
        """Load default configuration schema."""
        # This would load the default Pythonium configuration schema
        # For now, we'll use the PythoniumConfig model
        pass

    async def _discover_config_files(self) -> None:
        """Discover and load configuration files."""
        for config_path in self._default_config_paths:
            if config_path.exists():
                await self.add_configuration_source(str(config_path))

    async def _load_environment_variables(self) -> None:
        """Load configuration from environment variables."""
        env_config: Dict[str, Any] = {}

        for key, value in os.environ.items():
            if key.startswith(self._environment_prefix):
                # Convert environment variable to nested dict
                config_key = key[len(self._environment_prefix) :].lower()
                config_path = config_key.split("_")

                # Build nested structure
                current = env_config
                for part in config_path[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set the value (try to parse as JSON first, then as string)
                try:
                    import json

                    current[config_path[-1]] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    current[config_path[-1]] = value

        if env_config:
            # Merge environment configuration
            self._merge_configuration(env_config, "environment")

    async def _setup_file_watching(self) -> None:
        """Set up file system watching for configuration files."""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog package not available, file watching disabled")
            return

        try:
            self._fs_handler = ConfigurationWatcher(self)
            assert (
                ObserverType is not None
            ), "ObserverType should not be None when WATCHDOG_AVAILABLE is True"
            self._fs_observer = ObserverType()

            # Watch directories containing configuration files
            watched_dirs = set()
            for source in self._sources.values():
                if source.watch:
                    dir_path = source.path.parent
                    if dir_path not in watched_dirs:
                        self._fs_observer.schedule(
                            self._fs_handler, str(dir_path), recursive=False
                        )
                        watched_dirs.add(dir_path)

            logger.info(f"Set up file watching for {len(watched_dirs)} directories")

        except Exception as e:
            logger.warning(f"Failed to set up file watching: {e}")

    def _is_watched_file(self, file_path: Path) -> bool:
        """Check if a file path is being watched for configuration changes."""
        return any(source.path == file_path for source in self._sources.values())

    async def add_configuration_source(
        self,
        path: Union[str, Path],
        priority: int = 0,
        watch: bool = True,
        required: bool = True,
        source_name: Optional[str] = None,
    ) -> None:
        """Add a configuration source."""
        file_path = Path(path)

        if not file_path.exists() and required:
            raise ConfigurationError(
                f"Required configuration file not found: {file_path}"
            )

        if not file_path.exists():
            logger.warning(f"Optional configuration file not found: {file_path}")
            return

        # Determine format from file extension
        ext = file_path.suffix.lower()
        if ext in [".yaml", ".yml"]:
            format = SerializationFormat.YAML
        elif ext == ".json":
            format = SerializationFormat.JSON
        elif ext == ".toml":
            # Note: Would need to add TOML support to serialization module
            format = SerializationFormat.JSON  # Fallback for now
        else:
            raise ConfigurationError(f"Unsupported configuration format: {ext}")

        # Create source entry
        source_name = source_name or str(file_path)
        source = ConfigurationSource(
            path=file_path,
            format=format,
            priority=priority,
            watch=watch,
            required=required,
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

        self._sources[source_name] = source

        # Load the configuration
        await self._load_source(source_name)

        logger.info(f"Added configuration source: {source_name}")

    async def remove_configuration_source(self, source_name: str) -> None:
        """Remove a configuration source."""
        if source_name not in self._sources:
            raise ConfigurationError(f"Configuration source not found: {source_name}")

        del self._sources[source_name]

        # Reload configuration without this source
        await self._reload_all_sources()

        logger.info(f"Removed configuration source: {source_name}")

    async def _load_source(self, source_name: str) -> None:
        """Load configuration from a specific source."""
        source = self._sources[source_name]

        try:
            # Load configuration using common serialization utilities
            from pythonium.common.serialization import deserialize_from_file

            config_data = deserialize_from_file(source.path, source.format)

            # Merge into current configuration
            old_config = self._current_config.copy()
            self._merge_configuration(config_data, source_name)

            # Update source metadata
            source.last_loaded = datetime.utcnow()
            source.load_count += 1
            source.last_error = None

            # Notify of changes
            await self._notify_configuration_changes(
                old_config, self._current_config, source
            )

            logger.debug(f"Loaded configuration from source: {source_name}")

        except Exception as e:
            source.error_count += 1
            source.last_error = str(e)
            logger.error(f"Failed to load configuration from {source_name}: {e}")

            if source.required:
                raise ConfigurationError(
                    f"Failed to load required configuration: {e}"
                ) from e

    async def _reload_source(self, file_path: Path) -> None:
        """Reload configuration from a specific file."""
        source_name = None
        for name, source in self._sources.items():
            if source.path == file_path:
                source_name = name
                break

        if source_name:
            logger.info(f"Reloading configuration source: {source_name}")
            await self._load_source(source_name)

            await self.emit_event(
                "configuration_reloaded",
                {"source": source_name, "path": str(file_path)},
            )

    async def _reload_all_sources(self) -> None:
        """Reload configuration from all sources."""
        self._current_config.clear()

        # Sort sources by priority
        sorted_sources = sorted(self._sources.items(), key=lambda x: x[1].priority)

        for source_name, _ in sorted_sources:
            await self._load_source(source_name)

    def _merge_configuration(
        self, new_config: Dict[str, Any], source_name: str
    ) -> None:
        """Merge configuration data into current configuration."""

        def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            """Deep merge two dictionaries."""
            result = base.copy()

            for key, value in update.items():
                if (
                    key in result
                    and isinstance(result[key], dict)
                    and isinstance(value, dict)
                ):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value

            return result

        self._current_config = deep_merge(self._current_config, new_config)

    async def _notify_configuration_changes(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        source: ConfigurationSource,
    ) -> None:
        """Notify listeners of configuration changes."""
        # Compare configurations and identify changes
        changes = self._detect_changes(old_config, new_config)

        for change in changes:
            change.source = source

            # Call change callbacks
            for callback in self._change_callbacks:
                try:
                    callback(change)
                except Exception as e:
                    logger.error(f"Error in configuration change callback: {e}")

    def _detect_changes(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        prefix: str = "",
    ) -> List[ConfigurationChange]:
        """Detect changes between two configuration dictionaries."""
        changes = []

        # Check for additions and modifications
        for key, new_value in new_config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if key not in old_config:
                # Addition
                changes.append(
                    ConfigurationChange(
                        source=None,  # Will be set by caller
                        old_value=None,
                        new_value=new_value,
                        key_path=full_key,
                        change_type="added",
                    )
                )
            elif old_config[key] != new_value:
                if isinstance(old_config[key], dict) and isinstance(new_value, dict):
                    # Recursive check for nested changes
                    changes.extend(
                        self._detect_changes(old_config[key], new_value, full_key)
                    )
                else:
                    # Modification
                    changes.append(
                        ConfigurationChange(
                            source=None,  # Will be set by caller
                            old_value=old_config[key],
                            new_value=new_value,
                            key_path=full_key,
                            change_type="modified",
                        )
                    )

        # Check for removals
        for key, old_value in old_config.items():
            if key not in new_config:
                full_key = f"{prefix}.{key}" if prefix else key
                changes.append(
                    ConfigurationChange(
                        source=None,  # Will be set by caller
                        old_value=old_value,
                        new_value=None,
                        key_path=full_key,
                        change_type="removed",
                    )
                )

        return changes

    # Public interface methods

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key path."""
        keys = key.split(".")
        current = self._current_config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key path."""
        keys = key.split(".")
        current = self._current_config

        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        old_value = current.get(keys[-1])
        current[keys[-1]] = value

        # Notify of change
        change = ConfigurationChange(
            source=None,
            old_value=old_value,
            new_value=value,
            key_path=key,
            change_type="modified" if old_value is not None else "added",
        )

        for callback in self._change_callbacks:
            try:
                callback(change)
            except Exception as e:
                logger.error(f"Error in configuration change callback: {e}")

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration data."""
        return self._current_config.copy()

    def add_change_callback(
        self, callback: Callable[[ConfigurationChange], None]
    ) -> None:
        """Add a callback for configuration changes."""
        self._change_callbacks.append(callback)

    def remove_change_callback(
        self, callback: Callable[[ConfigurationChange], None]
    ) -> None:
        """Remove a configuration change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    async def validate_configuration(self) -> Result[Dict[str, Any]]:
        """Validate the current configuration against schemas."""
        # This would validate against registered schemas
        # For now, return a basic validation
        return Result.success_result({"is_valid": True, "errors": [], "warnings": []})

    def get_source_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all configuration sources."""
        return {
            name: {
                "path": str(source.path),
                "format": source.format.value,
                "priority": source.priority,
                "watch": source.watch,
                "required": source.required,
                "last_modified": (
                    source.last_modified.isoformat() if source.last_modified else None
                ),
                "last_loaded": (
                    source.last_loaded.isoformat() if source.last_loaded else None
                ),
                "load_count": source.load_count,
                "error_count": source.error_count,
                "last_error": source.last_error,
            }
            for name, source in self._sources.items()
        }

    async def reload_configuration(self) -> None:
        """Manually reload all configuration sources."""
        logger.info("Manually reloading configuration")
        await self._reload_all_sources()

        await self.emit_event(
            "manual_reload",
            {
                "sources": len(self._sources),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
