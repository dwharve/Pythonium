"""
Common exceptions for the Pythonium framework.

This module defines the exception hierarchy used throughout
the Pythonium project for consistent error handling.
"""

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


class InitializationError(PythoniumError):
    """Raised when component initialization fails."""

    pass


class ToolError(PythoniumError):
    """Base exception for tool-related errors."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    pass


class ManagerError(PythoniumError):
    """Base exception for manager-related errors."""

    pass
