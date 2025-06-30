"""
MCP server configuration management.

This module handles configuration for the MCP server including transport
settings, security options, and performance tuning.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransportType(str, Enum):
    """Supported transport types."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"
    TCP = "tcp"


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuthenticationMethod(str, Enum):
    """Authentication methods."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    CUSTOM = "custom"


class TransportConfig(BaseModel):
    """Transport layer configuration."""

    type: TransportType
    host: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None
    ssl_enabled: bool = False
    ssl_cert_file: Optional[str] = None
    ssl_key_file: Optional[str] = None
    ssl_ca_file: Optional[str] = None

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if v is not None and (v < 1 or v > 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""

    authentication_method: AuthenticationMethod = AuthenticationMethod.NONE
    api_keys: List[str] = Field(default_factory=list)
    allowed_origins: List[str] = Field(default_factory=list)
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    require_tls: bool = False
    cors_enabled: bool = True

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, v, info):
        if (
            info.data.get("authentication_method") == AuthenticationMethod.API_KEY
            and not v
        ):
            raise ValueError("API keys required when using API key authentication")
        return v


class PerformanceConfig(BaseModel):
    """Performance tuning configuration."""

    max_concurrent_requests: int = 100
    request_timeout_seconds: int = 300
    keepalive_timeout_seconds: int = 60
    max_request_size_bytes: int = 10 * 1024 * 1024  # 10MB
    max_response_size_bytes: int = 50 * 1024 * 1024  # 50MB
    enable_compression: bool = True
    compression_threshold_bytes: int = 1024

    @field_validator("max_concurrent_requests")
    @classmethod
    def validate_max_concurrent_requests(cls, v):
        if v < 1:
            raise ValueError("max_concurrent_requests must be at least 1")
        return v

    @field_validator("request_timeout_seconds")
    @classmethod
    def validate_request_timeout(cls, v):
        if v < 1:
            raise ValueError("request_timeout_seconds must be at least 1")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = LogLevel.INFO
    enable_request_logging: bool = True
    enable_performance_logging: bool = False
    log_file: Optional[str] = None
    max_log_file_size_mb: int = 100
    log_file_backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("max_log_file_size_mb")
    @classmethod
    def validate_max_log_file_size(cls, v):
        if v < 1:
            raise ValueError("max_log_file_size_mb must be at least 1")
        return v


class ResourceConfig(BaseModel):
    """Resource management configuration."""

    enable_resource_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_entries: int = 1000
    max_cache_size_mb: int = 100
    allowed_resource_schemes: List[str] = Field(
        default_factory=lambda: ["file", "http", "https"]
    )
    resource_timeout_seconds: int = 30

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl(cls, v):
        if v < 0:
            raise ValueError("cache_ttl_seconds cannot be negative")
        return v


class ToolConfig(BaseModel):
    """Tool execution configuration."""

    enable_tool_execution: bool = True
    tool_timeout_seconds: int = 300
    max_tool_output_size_bytes: int = 10 * 1024 * 1024  # 10MB
    enable_tool_result_caching: bool = True
    tool_cache_ttl_seconds: int = 300
    dangerous_tools_enabled: bool = False
    allowed_tool_categories: List[str] = Field(default_factory=list)

    @field_validator("tool_timeout_seconds")
    @classmethod
    def validate_tool_timeout(cls, v):
        if v < 1:
            raise ValueError("tool_timeout_seconds must be at least 1")
        return v


class PromptConfig(BaseModel):
    """Prompt template configuration."""

    enable_prompts: bool = True
    prompt_cache_enabled: bool = True
    prompt_cache_ttl_seconds: int = 1800
    max_prompt_length: int = 100000
    enable_prompt_validation: bool = True


class ServerConfig(BaseModel):
    """Complete MCP server configuration."""

    name: str = "Pythonium MCP Server"
    version: str = "0.1.0"
    description: str = "A modular MCP server for AI agents"

    # Core configuration sections
    transport: TransportConfig
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    prompts: PromptConfig = Field(default_factory=PromptConfig)

    # Additional settings
    debug_mode: bool = False
    enable_experimental_features: bool = False
    custom_settings: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class MCPConfigManager:
    """
    MCP server configuration manager.

    Handles loading, validation, and management of MCP server configuration
    from various sources including files, environment variables, and defaults.
    """

    def __init__(self):
        self._config: Optional[ServerConfig] = None
        self._config_file_path: Optional[Path] = None

    def load_config(
        self,
        config_file: Optional[Union[str, Path]] = None,
        override_values: Optional[Dict[str, Any]] = None,
    ) -> ServerConfig:
        """
        Load MCP server configuration.

        Args:
            config_file: Path to configuration file
            override_values: Values to override in configuration

        Returns:
            Loaded and validated configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Start with default configuration
        config_data = self._get_default_config()

        # Load from file if provided
        if config_file:
            config_file = Path(config_file)
            if config_file.exists():
                file_config = self._load_config_file(config_file)
                config_data = self._merge_config(config_data, file_config)
                self._config_file_path = config_file

        # Apply environment variable overrides
        env_config = self._load_environment_config()
        config_data = self._merge_config(config_data, env_config)

        # Apply explicit overrides
        if override_values:
            config_data = self._merge_config(config_data, override_values)

        # Validate and create configuration
        try:
            self._config = ServerConfig(**config_data)
            return self._config
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

    def get_config(self) -> ServerConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def reload_config(self) -> ServerConfig:
        """Reload configuration from file."""
        if self._config_file_path and self._config_file_path.exists():
            return self.load_config(self._config_file_path)
        else:
            return self.load_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "name": "Pythonium MCP Server",
            "version": "0.1.0",
            "description": "A modular MCP server for AI agents",
            "transport": {"type": "stdio"},
            "security": {},
            "performance": {},
            "logging": {},
            "resources": {},
            "tools": {},
            "prompts": {},
            "debug_mode": False,
            "enable_experimental_features": False,
            "custom_settings": {},
        }

    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        import json

        import yaml

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                if config_file.suffix.lower() in [".yml", ".yaml"]:
                    return yaml.safe_load(f) or {}
                elif config_file.suffix.lower() == ".json":
                    return json.load(f) or {}
                else:
                    raise ValueError(
                        f"Unsupported config file format: {config_file.suffix}"
                    )
        except Exception as e:
            raise ValueError(f"Failed to load config file {config_file}: {e}")

    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config: Dict[str, Any] = {}

        # Map environment variables to config paths
        env_mappings = {
            "PYTHONIUM_MCP_TRANSPORT_TYPE": "transport.type",
            "PYTHONIUM_MCP_TRANSPORT_HOST": "transport.host",
            "PYTHONIUM_MCP_TRANSPORT_PORT": "transport.port",
            "PYTHONIUM_MCP_SECURITY_AUTH_METHOD": "security.authentication_method",
            "PYTHONIUM_MCP_SECURITY_API_KEYS": "security.api_keys",
            "PYTHONIUM_MCP_LOGGING_LEVEL": "logging.level",
            "PYTHONIUM_MCP_LOGGING_FILE": "logging.log_file",
            "PYTHONIUM_MCP_DEBUG": "debug_mode",
            "PYTHONIUM_MCP_EXPERIMENTAL": "enable_experimental_features",
        }

        for env_var, config_path in env_mappings.items():
            raw_value = os.getenv(env_var)
            if raw_value is not None:
                # Convert value to appropriate type
                value: Union[int, bool, List[str], str] = raw_value
                if config_path.endswith(".port"):
                    try:
                        value = int(raw_value)
                    except ValueError:
                        continue
                elif config_path in [
                    "debug_mode",
                    "enable_experimental_features",
                ]:
                    value = raw_value.lower() in ("true", "1", "yes", "on")
                elif config_path == "security.api_keys":
                    value = [key.strip() for key in raw_value.split(",") if key.strip()]
                else:
                    value = raw_value

                # Set nested configuration value
                self._set_nested_value(env_config, config_path, value)

        return env_config

    def _merge_config(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested configuration value using dot notation."""
        keys = path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def validate_config(self, config: Optional[ServerConfig] = None) -> List[str]:
        """
        Validate configuration and return list of issues.

        Args:
            config: Configuration to validate (uses current if None)

        Returns:
            List of validation issues (empty if valid)
        """
        if config is None:
            config = self.get_config()

        issues = []
        issues.extend(self._validate_transport(config.transport))
        issues.extend(self._validate_security(config.security, config.transport))
        issues.extend(self._validate_ssl(config.transport))
        issues.extend(self._validate_performance(config.performance))

        return issues

    def _validate_transport(self, transport: TransportConfig) -> List[str]:
        """Validate transport configuration."""
        issues = []
        if transport.type in [
            TransportType.HTTP,
            TransportType.WEBSOCKET,
            TransportType.TCP,
        ]:
            if not transport.host:
                issues.append("Host is required for HTTP/WebSocket/TCP transport")
            if not transport.port:
                issues.append("Port is required for HTTP/WebSocket/TCP transport")
        return issues

    def _validate_security(
        self, security: SecurityConfig, transport: TransportConfig
    ) -> List[str]:
        """Validate security configuration."""
        issues = []
        if security.authentication_method == AuthenticationMethod.API_KEY:
            if not security.api_keys:
                issues.append("API keys are required when using API key authentication")

        if security.require_tls and not transport.ssl_enabled:
            issues.append("TLS is required but SSL is not enabled in transport")

        return issues

    def _validate_ssl(self, transport: TransportConfig) -> List[str]:
        """Validate SSL configuration."""
        issues = []
        if transport.ssl_enabled:
            if not transport.ssl_cert_file:
                issues.append("SSL certificate file is required when SSL is enabled")
            if not transport.ssl_key_file:
                issues.append("SSL key file is required when SSL is enabled")

            # Check if files exist
            if transport.ssl_cert_file and not Path(transport.ssl_cert_file).exists():
                issues.append(
                    f"SSL certificate file not found: {transport.ssl_cert_file}"
                )
            if transport.ssl_key_file and not Path(transport.ssl_key_file).exists():
                issues.append(f"SSL key file not found: {transport.ssl_key_file}")
        return issues

    def _validate_performance(self, perf: PerformanceConfig) -> List[str]:
        """Validate performance configuration."""
        issues = []
        if perf.request_timeout_seconds < 1:
            issues.append("Request timeout must be at least 1 second")
        return issues

    def get_transport_config(self) -> TransportConfig:
        """Get transport configuration."""
        return self.get_config().transport

    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self.get_config().security

    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration."""
        return self.get_config().performance

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.get_config().logging

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_config().debug_mode

    def are_experimental_features_enabled(self) -> bool:
        """Check if experimental features are enabled."""
        return self.get_config().enable_experimental_features
