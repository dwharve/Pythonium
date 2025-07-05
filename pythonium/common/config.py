"""
Unified configuration management using pydantic-settings.

This module provides a standardized configuration system that replaces
the previous custom implementation with pydantic-settings for better
reliability, validation, and environment variable handling.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class TransportType(str, Enum):
    """Supported transport types."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class AuthenticationMethod(str, Enum):
    """Authentication methods."""

    NONE = "none"
    API_KEY = "api_key"


class ServerSettings(BaseSettings):
    """Server configuration with environment variable support."""

    host: str = Field(default="localhost", description="Server host address")
    port: int = Field(default=8080, ge=1, le=65535, description="Server port")
    transport: TransportType = Field(
        default=TransportType.STDIO,
        description="Transport protocol (stdio, http, websocket)",
    )
    workers: int = Field(default=1, ge=1, description="Number of worker processes")

    # MCP specific settings
    name: str = Field(default="Pythonium MCP Server", description="Server name")
    description: str = Field(
        default="A modular MCP server for AI agents", description="Server description"
    )
    version: str = Field(default="0.1.2", description="Server version")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_SERVER_",
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

    # MCP specific tool settings
    enable_tool_execution: bool = Field(
        default=True, description="Enable tool execution"
    )
    tool_timeout_seconds: int = Field(
        default=300, ge=1, description="Tool execution timeout"
    )
    max_tool_output_size_bytes: int = Field(
        default=10 * 1024 * 1024, description="Max tool output size"
    )

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_TOOL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("tool_timeout_seconds")
    @classmethod
    def validate_tool_timeout(cls, v):
        if v < 1:
            raise ValueError("tool_timeout_seconds must be at least 1")
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration with environment variable support."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file: Optional[str] = Field(default=None, description="Log file path")
    max_size: int = Field(default=10485760, description="Max log file size")
    backup_count: int = Field(default=5, description="Number of backup files")

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_LOGGING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class SecuritySettings(BaseSettings):
    """Security configuration with environment variable support."""

    enable_auth: bool = Field(default=False, description="Enable authentication")
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")
    rate_limit: int = Field(default=100, ge=1, description="Rate limit per minute")
    cors_enabled: bool = Field(default=False, description="Enable CORS")
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"], description="Allowed CORS origins"
    )

    # MCP specific security settings
    authentication_method: AuthenticationMethod = Field(
        default=AuthenticationMethod.NONE, description="Authentication method"
    )

    model_config = SettingsConfigDict(
        env_prefix="PYTHONIUM_SECURITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, v, info):
        if (
            info.data.get("authentication_method") == AuthenticationMethod.API_KEY
            and not v
        ):
            raise ValueError("API keys required when using API key authentication")
        return v


class PythoniumSettings(BaseSettings):
    """Main Pythonium configuration with environment variable support."""

    # Sub-configurations
    server: ServerSettings = Field(default_factory=ServerSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # Global settings
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")
    version: str = Field(default="1.0.0", description="Application version")

    # MCP server specific settings
    debug_mode: bool = Field(default=False, description="Enable MCP debug mode")
    enable_experimental_features: bool = Field(
        default=False, description="Enable experimental features"
    )

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
