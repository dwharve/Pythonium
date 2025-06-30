"""
Standardized error handling framework for the Pythonium system.

This module provides decorators, utilities, and patterns for consistent
error handling across all components and tools.
"""

import asyncio
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

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


def safe_execute(
    default_return: Any = None,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    log_errors: bool = True,
    component: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator for safe execution with error handling.

    Args:
        default_return: Value to return if an exception occurs
        exceptions: Exception types to catch
        log_errors: Whether to log caught exceptions
        component: Component name for error reporting
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    get_error_reporter().report_error(
                        e,
                        context={"function": func.__name__, "args": str(args)[:100]},
                        component=component,
                    )
                return default_return

        return cast(F, wrapper)

    return decorator


def async_safe_execute(
    default_return: Any = None,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    log_errors: bool = True,
    component: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator for safe async execution with error handling.

    Args:
        default_return: Value to return if an exception occurs
        exceptions: Exception types to catch
        log_errors: Whether to log caught exceptions
        component: Component name for error reporting
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    get_error_reporter().report_error(
                        e,
                        context={"function": func.__name__, "args": str(args)[:100]},
                        component=component,
                    )
                return default_return

        return cast(F, wrapper)

    return decorator


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


def _should_retry(attempt: int, max_attempts: int) -> bool:
    """Helper function to determine if retry should continue."""
    return attempt < max_attempts - 1


def _log_retry_attempt(
    attempt: int, func_name: str, error: Exception, delay: float
) -> None:
    """Helper function to log retry attempts."""
    logger.warning(
        f"Attempt {attempt + 1} failed for {func_name}: {error}. "
        f"Retrying in {delay}s..."
    )


def _report_final_error(
    error: Exception, func_name: str, max_attempts: int, component: Optional[str]
) -> None:
    """Helper function to report final error after all retries failed."""
    get_error_reporter().report_error(
        error,
        context={
            "function": func_name,
            "attempts": max_attempts,
            "final_attempt": True,
        },
        component=component,
    )


async def _execute_with_async_retry(
    func,
    args,
    kwargs,
    max_attempts: int,
    delay: float,
    backoff_multiplier: float,
    exceptions,
    component: Optional[str],
):
    """Execute function with async retry logic."""
    current_delay = delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if _should_retry(attempt, max_attempts):
                _log_retry_attempt(attempt, func.__name__, e, current_delay)
                await asyncio.sleep(current_delay)
                current_delay *= backoff_multiplier
            else:
                _report_final_error(e, func.__name__, max_attempts, component)

    # Re-raise the last exception after all attempts failed
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("All retry attempts failed but no exception was captured")


def _execute_with_sync_retry(
    func,
    args,
    kwargs,
    max_attempts: int,
    delay: float,
    backoff_multiplier: float,
    exceptions,
    component: Optional[str],
):
    """Execute function with sync retry logic."""
    current_delay = delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if _should_retry(attempt, max_attempts):
                _log_retry_attempt(attempt, func.__name__, e, current_delay)
                import time

                time.sleep(current_delay)
                current_delay *= backoff_multiplier
            else:
                _report_final_error(e, func.__name__, max_attempts, component)

    # Re-raise the last exception after all attempts failed
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("All retry attempts failed but no exception was captured")


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    component: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying operations on error.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Exception types to trigger retries
        component: Component name for error reporting
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _execute_with_async_retry(
                func,
                args,
                kwargs,
                max_attempts,
                delay,
                backoff_multiplier,
                exceptions,
                component,
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _execute_with_sync_retry(
                func,
                args,
                kwargs,
                max_attempts,
                delay,
                backoff_multiplier,
                exceptions,
                component,
            )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


def timeout_handler(
    timeout_seconds: float,
    timeout_message: Optional[str] = None,
    component: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator for handling operation timeouts.

    Args:
        timeout_seconds: Timeout duration in seconds
        timeout_message: Custom timeout message
        component: Component name for error reporting
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                message = (
                    timeout_message or f"Operation timed out after {timeout_seconds}s"
                )
                timeout_error = TimeoutError(message)

                get_error_reporter().report_error(
                    timeout_error,
                    context={
                        "function": func.__name__,
                        "timeout_seconds": timeout_seconds,
                    },
                    component=component,
                )
                raise timeout_error

        return cast(F, wrapper)

    return decorator


class ErrorContext:
    """Context manager for error handling with automatic reporting."""

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

    def __exit__(self, exc_type, exc_value, traceback):
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


# Convenience functions for common error handling patterns
def handle_tool_error(func: F) -> F:
    """Decorator specifically for tool execute methods."""
    return result_handler(
        component="tool", default_error_message="Tool execution failed"
    )(func)


def handle_manager_error(func: F) -> F:
    """Decorator specifically for manager methods."""
    return result_handler(
        component="manager", default_error_message="Manager operation failed"
    )(func)


def handle_mcp_error(func: F) -> F:
    """Decorator specifically for MCP protocol methods."""
    return result_handler(
        component="mcp", default_error_message="MCP operation failed"
    )(func)
