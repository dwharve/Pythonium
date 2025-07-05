from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pythonium.common.config import (
    AuthenticationMethod,
    LoggingSettings,
    PythoniumSettings,
    SecuritySettings,
    ServerSettings,
    ToolSettings,
    TransportType,
)


class ConfigurationManager:
    """
    Configuration manager for Pythonium.

    Provides a simple interface to access configuration values
    using dot notation and supports environment variable overrides.
    """

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ):
        self._settings = self._load_settings(config_file, config_overrides)

    def _load_settings(
        self,
        config_file: Optional[Union[str, Path]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> PythoniumSettings:
        """Load settings from file or environment."""
        if config_file:
            settings = PythoniumSettings.load_from_file(config_file)
        else:
            settings = PythoniumSettings()

        # Apply config overrides if provided
        if config_overrides:
            # Create new settings with the overrides merged in
            base_data = settings.model_dump()

            # Deep merge the config overrides
            def deep_merge(
                base: Dict[str, Any], override: Dict[str, Any]
            ) -> Dict[str, Any]:
                for key, value in override.items():
                    if (
                        key in base
                        and isinstance(base[key], dict)
                        and isinstance(value, dict)
                    ):
                        base[key] = deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base

            merged_data = deep_merge(base_data, config_overrides)
            settings = PythoniumSettings(**merged_data)

        return settings

    def get_settings(self) -> PythoniumSettings:
        """Get the underlying settings object."""
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split(".")
        current = self._settings.model_dump()

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def reload_config(
        self, config_file: Optional[Union[str, Path]] = None
    ) -> PythoniumSettings:
        """Reload configuration from file."""
        self._settings = self._load_settings(config_file)
        return self._settings

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Validate transport settings
        if self._settings.server.transport in [
            TransportType.HTTP,
            TransportType.WEBSOCKET,
        ]:
            if not self._settings.server.host:
                issues.append("Host is required for HTTP/WebSocket transport")
            if not self._settings.server.port:
                issues.append("Port is required for HTTP/WebSocket transport")

        # Validate security settings
        if (
            self._settings.security.authentication_method
            == AuthenticationMethod.API_KEY
        ):
            if not self._settings.security.api_keys:
                issues.append("API keys are required when using API key authentication")

        return issues

    # Convenience methods for common configuration access
    def get_server_config(self) -> ServerSettings:
        """Get server configuration."""
        return self._settings.server

    def get_security_config(self) -> SecuritySettings:
        """Get security configuration."""
        return self._settings.security

    def get_logging_config(self) -> LoggingSettings:
        """Get logging configuration."""
        return self._settings.logging

    def get_tool_config(self) -> ToolSettings:
        """Get tool configuration."""
        return self._settings.tools

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self._settings.debug_mode

    def are_experimental_features_enabled(self) -> bool:
        """Check if experimental features are enabled."""
        return self._settings.enable_experimental_features


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def set_config_manager(config_manager: ConfigurationManager) -> None:
    """Set the global configuration manager instance."""
    global _config_manager
    _config_manager = config_manager
