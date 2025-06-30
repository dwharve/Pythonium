"""
Unified configuration management using pydantic-settings.

This module provides a standardized configuration system that replaces
the previous custom implementation with pydantic-settings for better
reliability, validation, and environment variable handling.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class ServerSettings(BaseSettings):
    """Server configuration with environment variable support."""

    host: str = Field(default="localhost", description="Server host address")
    port: int = Field(default=8080, ge=1, le=65535, description="Server port")
    transport: str = Field(
        default="stdio",
        description="Transport protocol (stdio, http, websocket)",
    )
    workers: int = Field(default=1, ge=1, description="Number of worker processes")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_SERVER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate transport protocol."""
        allowed = ["stdio", "http", "websocket"]
        if v not in allowed:
            raise ValueError(f"Transport must be one of {allowed}")
        return v


class PluginSettings(BaseSettings):
    """Plugin configuration with environment variable support."""

    enabled: bool = Field(default=True, description="Enable plugin system")
    auto_load: bool = Field(default=True, description="Auto-load plugins")
    directories: List[str] = Field(
        default_factory=lambda: ["plugins"], description="Plugin directories"
    )
    blacklist: List[str] = Field(
        default_factory=list, description="Blacklisted plugins"
    )

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_PLUGIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class ToolSettings(BaseSettings):
    """Tool configuration with environment variable support."""

    enabled: bool = Field(default=True, description="Enable tool system")
    timeout: int = Field(default=30, ge=1, description="Default tool timeout")
    max_concurrent: int = Field(
        default=10, ge=1, description="Max concurrent tool executions"
    )
    categories: List[str] = Field(
        default_factory=lambda: ["system", "network", "filesystem", "data_processing"],
        description="Enabled tool categories",
    )

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_TOOL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class LoggingSettings(BaseSettings):
    """Logging configuration with environment variable support."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="structured",
        description="Log format (simple, detailed, json, structured)",
    )
    file: Optional[str] = Field(default=None, description="Log file path")
    verbose: bool = Field(default=False, description="Enable verbose logging")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate log format."""
        allowed = ["simple", "detailed", "json", "structured"]
        if v not in allowed:
            raise ValueError(f"Log format must be one of {allowed}")
        return v


class SecuritySettings(BaseSettings):
    """Security configuration with environment variable support."""

    enable_auth: bool = Field(default=False, description="Enable authentication")
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")
    rate_limit: int = Field(default=100, ge=1, description="Rate limit per minute")
    cors_enabled: bool = Field(default=False, description="Enable CORS")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"], description="Allowed CORS origins"
    )

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class DatabaseSettings(BaseSettings):
    """Database configuration with environment variable support."""

    url: Optional[str] = Field(default=None, description="Database URL")
    pool_size: int = Field(default=10, ge=1, description="Connection pool size")
    timeout: int = Field(default=30, ge=1, description="Query timeout")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class CacheSettings(BaseSettings):
    """Cache configuration with environment variable support."""

    enabled: bool = Field(default=True, description="Enable caching")
    backend: str = Field(default="memory", description="Cache backend")
    ttl: int = Field(default=300, ge=0, description="Default TTL in seconds")
    max_size: int = Field(default=1000, ge=1, description="Max cache size")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_CACHE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        """Validate cache backend."""
        allowed = ["memory", "redis", "memcached"]
        if v not in allowed:
            raise ValueError(f"Cache backend must be one of {allowed}")
        return v


class PythoniumSettings(BaseSettings):
    """Main Pythonium configuration with environment variable support."""

    # Sub-configurations
    server: ServerSettings = Field(default_factory=ServerSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)

    # Global settings
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")
    version: str = Field(default="1.0.0", description="Application version")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow additional configuration
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment name."""
        allowed = ["development", "testing", "staging", "production"]
        if v not in allowed:
            logger.warning(f"Unknown environment '{v}', using custom environment")
        return v

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self.model_dump()

    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        # Create new instance with updated values
        updated_data = {**self.model_dump(), **config_dict}

        # Update each field
        for key, value in updated_data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        import json

        import yaml

        file_path = Path(file_path)
        config_dict = self.model_dump()

        if file_path.suffix.lower() == ".json":
            with open(file_path, "w") as f:
                json.dump(config_dict, f, indent=2, default=str)
        elif file_path.suffix.lower() in [".yml", ".yaml"]:
            with open(file_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        logger.info(f"Configuration saved to {file_path}")

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "PythoniumSettings":
        """Load configuration from file."""
        import json

        import yaml

        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"Configuration file {file_path} not found, using defaults")
            return cls()

        try:
            if file_path.suffix.lower() == ".json":
                with open(file_path, "r") as f:
                    config_dict = json.load(f)
            elif file_path.suffix.lower() in [".yml", ".yaml"]:
                with open(file_path, "r") as f:
                    config_dict = yaml.safe_load(f) or {}
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")

            logger.info(f"Configuration loaded from {file_path}")
            return cls(**config_dict)

        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            logger.info("Using default configuration")
            return cls()


# Global settings instance
_settings: Optional[PythoniumSettings] = None


def get_settings() -> PythoniumSettings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = PythoniumSettings()
    return _settings


def load_settings_from_file(file_path: Union[str, Path]) -> PythoniumSettings:
    """Load settings from file and set as global instance."""
    global _settings
    _settings = PythoniumSettings.load_from_file(file_path)
    return _settings
