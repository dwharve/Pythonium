"""
Model Context Protocol (MCP) server implementation for Pythonium.

This package provides a fully featured MCP server that utilizes the tool
plugin framework. It includes comprehensive configuration management,
protocol implementation, and client integration capabilities.
"""

__version__ = "0.1.2"

from .config import (
    MCPConfigManager,
    SecurityConfig,
    ServerConfig,
    TransportConfig,
)
from .server import PythoniumMCPServer

__all__ = [
    # Modules
    "config",
    "ServerConfig",
    "TransportConfig",
    "SecurityConfig",
    "MCPConfigManager",
    "PythoniumMCPServer"
]
