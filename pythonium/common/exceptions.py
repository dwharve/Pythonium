"""
Common exceptions for the Pythonium framework.

This module defines the exception hierarchy used throughout
the Pythonium project for consistent error handling.
"""

import asyncio
from typing import Any, Dict, Optional


class PythoniumError(Exception):
    """Base exception for all Pythonium errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(PythoniumError):
    """Raised when there's a configuration error."""

    pass


class InitializationError(PythoniumError):
    """Raised when component initialization fails."""

    pass


class ShutdownError(PythoniumError):
    """Raised when component shutdown fails."""

    pass


class LifecycleError(PythoniumError):
    """Raised when component lifecycle operation fails."""

    pass


class PluginError(PythoniumError):
    """Base exception for plugin-related errors."""

    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin cannot be found."""

    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""

    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies cannot be resolved."""

    pass


class PluginExecutionError(PluginError):
    """Raised when plugin execution fails."""

    pass


class ToolError(PythoniumError):
    """Base exception for tool-related errors."""

    pass


class ToolNotFoundError(ToolError):
    """Raised when a tool cannot be found."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    pass


class ToolValidationError(ToolError):
    """Raised when tool parameter validation fails."""

    pass


class ManagerError(PythoniumError):
    """Base exception for manager-related errors."""

    pass


class ManagerNotFoundError(ManagerError):
    """Raised when a manager cannot be found."""

    pass


class ManagerStateError(ManagerError):
    """Raised when a manager is in an invalid state."""

    pass


class MCPError(PythoniumError):
    """Base exception for MCP-related errors."""

    pass


class MCPProtocolError(MCPError):
    """Raised when there's an MCP protocol error."""

    pass


class MCPTransportError(MCPError):
    """Raised when there's an MCP transport error."""

    pass


class MCPClientError(MCPError):
    """Raised when there's an MCP client error."""

    pass


class ResourceError(PythoniumError):
    """Base exception for resource-related errors."""

    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a resource cannot be found."""

    pass


class ResourceAccessError(ResourceError):
    """Raised when resource access is denied."""

    pass


class ResourceExhaustedError(ResourceError):
    """Raised when resources are exhausted."""

    pass


class SecurityError(PythoniumError):
    """Base exception for security-related errors."""

    pass


class AuthenticationError(SecurityError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(SecurityError):
    """Raised when authorization fails."""

    pass


class RateLimitError(SecurityError):
    """Raised when rate limits are exceeded."""

    pass


class ValidationError(PythoniumError):
    """Raised when data validation fails."""

    pass


class NetworkError(PythoniumError):
    """Raised when network operations fail."""

    pass


class TimeoutError(PythoniumError):
    """Raised when operations timeout."""

    pass


def handle_exception(exc: Exception, context: str = "") -> PythoniumError:
    """Convert generic exceptions to Pythonium exceptions."""
    if isinstance(exc, PythoniumError):
        return exc

    # Map common Python exceptions to Pythonium exceptions
    exception_mapping = {
        ValueError: ValidationError,
        TypeError: ValidationError,
        KeyError: ResourceNotFoundError,
        FileNotFoundError: ResourceNotFoundError,
        PermissionError: ResourceAccessError,
        ConnectionError: NetworkError,
        asyncio.TimeoutError: TimeoutError,
    }

    error_class = exception_mapping.get(type(exc), PythoniumError)

    message = str(exc)
    if context:
        message = f"{context}: {message}"

    return error_class(
        message=message,
        details={
            "original_exception": str(exc),
            "original_type": type(exc).__name__,
        },
    )
