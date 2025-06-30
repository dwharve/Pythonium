"""
Model Context Protocol (MCP) server implementation for Pythonium.

This package provides a fully featured MCP server that utilizes the tool
plugin framework. It includes comprehensive configuration management,
protocol implementation, and client integration capabilities.
"""

__version__ = "0.1.0"

# Import core MCP components
from . import config, handlers, protocol, server, session, transport
from .config import (
    MCPConfigManager,
    SecurityConfig,
    ServerConfig,
    TransportConfig,
)
from .handlers import MCPMessageHandler

# Import main classes for convenience
from .protocol import (
    MCPError,
    MCPMessage,
    MCPProtocol,
    MCPRequest,
    MCPResponse,
)
from .server import MCPServer
from .session import SessionManager
from .transport import HttpTransport, StdioTransport, WebSocketTransport

__all__ = [
    # Modules
    "protocol",
    "config",
    "session",
    "transport",
    "handlers",
    "server",
    # Main classes
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    "MCPProtocol",
    "ServerConfig",
    "TransportConfig",
    "SecurityConfig",
    "MCPConfigManager",
    "SessionManager",
    "StdioTransport",
    "HttpTransport",
    "WebSocketTransport",
    "MCPMessageHandler",
    "MCPServer",
]
