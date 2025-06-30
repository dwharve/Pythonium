"""
Management systems for the Pythonium MCP server.

This package provides complete management systems in an object-oriented
focused plugin framework including configuration, plugin, resource,
and security managers.
"""

__version__ = "0.1.0"

# Core manager framework
from pythonium.common.lifecycle import ComponentState

from .base import (
    BaseManager,
    ConfigurableManager,
    HealthCheck,
    ManagerDependency,
    ManagerInfo,
    ManagerMetrics,
    ManagerPriority,
)

# Specific managers
from .config_manager import (
    ConfigurationChange,
    ConfigurationManager,
    ConfigurationSource,
    ConfigurationWatcher,
)
from .plugin_manager import (
    PluginEnvironment,
    PluginLoadResult,
    PluginManager,
    PluginSandbox,
)

# Manager registry and dependency injection
from .registry import (
    ManagerRegistration,
    ManagerRegistry,
    get_manager,
    get_manager_by_type,
    get_manager_registry,
    register_manager,
)
from .resource_manager import (
    ConnectionPool,
    ManagedResource,
    PoolStats,
    ResourceLimits,
    ResourceManager,
    ResourceUsage,
)
from .security_manager import (
    APIKey,
    APIKeyAuthenticator,
    AuditLogEntry,
    AuthenticationMethod,
    AuthenticationResult,
    Authenticator,
    BasicAuthenticator,
    PermissionLevel,
    RateLimiter,
    RateLimitInfo,
    SecurityManager,
    User,
)

__all__ = [
    # Core framework
    "BaseManager",
    "ConfigurableManager",
    "ComponentState",
    "ManagerPriority",
    "ManagerDependency",
    "ManagerMetrics",
    "ManagerInfo",
    "HealthCheck",
    # Registry
    "ManagerRegistry",
    "ManagerRegistration",
    "get_manager_registry",
    "register_manager",
    "get_manager",
    "get_manager_by_type",
    # Configuration Manager
    "ConfigurationManager",
    "ConfigurationSource",
    "ConfigurationChange",
    "ConfigurationWatcher",
    # Plugin Manager
    "PluginManager",
    "PluginEnvironment",
    "PluginLoadResult",
    "PluginSandbox",
    # Resource Manager
    "ResourceManager",
    "ManagedResource",
    "ConnectionPool",
    "ResourceLimits",
    "ResourceUsage",
    "PoolStats",
    # Security Manager
    "SecurityManager",
    "APIKey",
    "User",
    "AuthenticationResult",
    "AuthenticationMethod",
    "PermissionLevel",
    "RateLimitInfo",
    "AuditLogEntry",
    "Authenticator",
    "APIKeyAuthenticator",
    "BasicAuthenticator",
    "RateLimiter",
]
