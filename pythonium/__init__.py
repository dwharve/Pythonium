"""
Pythonium: A modular MCP server for AI agents.

This package provides a comprehensive, plugin-based Model Context Protocol (MCP)
server designed to enable advanced capabilities for AI agents through a modular
architecture.
"""

__version__ = "0.1.2"
__author__ = "David Harvey"
__email__ = "dwh.exis@gmail.com"
__description__ = "A modular MCP server for AI agents"

# Package-level imports for convenience
from pythonium.common import (
    BaseComponent,
    ComponentStatus,
    ConfigurationError,
    EventManager,
    PluginError,
    PythoniumError,
    Registry,
)
from pythonium.managers import (
    ConfigurationManager,
    ManagerRegistry,
    PluginManager,
    ResourceManager,
    SecurityManager,
)
from pythonium.mcp import (
    MCPConfigManager,
    MCPProtocol,
    MCPServer,
    ServerConfig,
)
from pythonium.tools import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolParameter,
    ToolRegistry,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    # Common
    "BaseComponent",
    "ComponentStatus",
    "Registry",
    "EventManager",
    "PythoniumError",
    "ConfigurationError",
    "PluginError",
    # Managers
    "ManagerRegistry",
    "ConfigurationManager",
    "PluginManager",
    "ResourceManager",
    "SecurityManager",
    # MCP
    "MCPServer",
    "MCPProtocol",
    "ServerConfig",
    "MCPConfigManager",
    # Tools
    "BaseTool",
    "ToolContext",
    "ToolRegistry",
    "ToolParameter",
    "ParameterType",
]
