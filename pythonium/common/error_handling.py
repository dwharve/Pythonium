"""
Standardized error handling framework for the Pythonium system.

This module provides decorators and utilities for consistent error handling
across all components. It focuses on the patterns actually used in the codebase:
- Tools use @handle_tool_error for standardized Result objects
- Managers should use @handle_manager_error for consistent error reporting
- Core error reporting and tracking via ErrorReporter
"""

import asyncio
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from pythonium.common.base import Result
from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class ErrorReporter:
    """Centralized error reporting and tracking."""

    def __init__(self):
        self._error_count: Dict[str, int] = {}
        self._error_history: List[Dict[str, Any]] = []
        self._max_history = 1000

    def report_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
    ) -> None:
        """Report an error with context information."""
        error_type = type(error).__name__
        self._error_count[error_type] = self._error_count.get(error_type, 0) + 1

        error_info = {
            "timestamp": asyncio.get_event_loop().time(),
            "error_type": error_type,
            "error_message": str(error),
            "component": component,
            "context": context or {},
            "traceback": traceback.format_exc(),
        }

        self._error_history.append(error_info)

        # Keep history size manageable
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history :]

        logger.error(
            f"Error in {component or 'unknown'}: {error_type}: {error}",
            extra={"context": context},
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": sum(self._error_count.values()),
            "error_count_by_type": self._error_count.copy(),
            "recent_errors": self._error_history[-10:],
        }


# Global error reporter instance
_error_reporter: Optional[ErrorReporter] = None


def get_error_reporter() -> ErrorReporter:
    """Get the global error reporter instance."""
    global _error_reporter
    if _error_reporter is None:
        _error_reporter = ErrorReporter()
    return _error_reporter


def _handle_exception_in_result(
    e: Exception, func_name: str, component: Optional[str], default_error_message: str
) -> Result:
    """Helper function to handle exceptions and return Result objects."""
    if isinstance(e, PythoniumError):
        get_error_reporter().report_error(
            e, context={"function": func_name}, component=component
        )
        return Result.error_result(error=str(e))
    else:
        get_error_reporter().report_error(
            e, context={"function": func_name}, component=component
        )
        return Result.error_result(error=f"{default_error_message}: {str(e)}")


def _wrap_result_if_needed(result) -> Result:
    """Helper function to wrap result in Result object if needed."""
    if isinstance(result, Result):
        return result
    return Result.success_result(data=result)


def result_handler(
    component: Optional[str] = None, default_error_message: str = "Operation failed"
) -> Callable[[F], F]:
    """
    Decorator that automatically wraps return values in Result objects.

    This standardizes the error handling pattern across tools and components
    by ensuring all exceptions are caught and converted to Result.error().
    Currently used by tools through handle_tool_error decorator.

    Args:
        component: Component name for error reporting
        default_error_message: Default error message if none provided
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Result:
            try:
                result = await func(*args, **kwargs)
                return _wrap_result_if_needed(result)
            except Exception as e:
                return _handle_exception_in_result(
                    e, func.__name__, component, default_error_message
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Result:
            try:
                result = func(*args, **kwargs)
                return _wrap_result_if_needed(result)
            except Exception as e:
                return _handle_exception_in_result(
                    e, func.__name__, component, default_error_message
                )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


class ErrorContext:
    """Context manager for error handling with automatic reporting.

    Useful for manager methods and other areas where decorator-based
    error handling is not suitable.
    """

    def __init__(
        self,
        component: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True,
    ):
        self.component = component
        self.operation = operation
        self.context = context or {}
        self.reraise = reraise
        self.exception: Optional[Exception] = None

    def __enter__(self):
        return self

    def __exit__(self, _, exc_value, __):
        if exc_value:
            self.exception = exc_value
            get_error_reporter().report_error(
                exc_value,
                context={"operation": self.operation, **self.context},
                component=self.component,
            )

            if not self.reraise:
                return True  # Suppress the exception

        return False  # Let the exception propagate


# Convenience decorators for common error handling patterns
def handle_tool_error(func: F) -> F:
    """Decorator specifically for tool execute methods.

    This is the primary decorator used by all standard tools.
    """
    return result_handler(
        component="tool", default_error_message="Tool execution failed"
    )(func)
