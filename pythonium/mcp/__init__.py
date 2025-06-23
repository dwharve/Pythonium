"""
MCP Server module for Pythonium code health analysis.

This module provides a comprehensive MCP server implementation that allows AI agents 
to perform sophisticated Python code analysis using Pythonium's suite of detectors.

The server implementation features:
- Service layer with dependency injection
- Tool registry for dynamic tool management
- Middleware chain for cross-cutting concerns
- Robust error handling and validation
"""

"""Expose :class:`PythoniumMCPServer`."""

from .server import PythoniumMCPServer

__all__ = ["PythoniumMCPServer"]
