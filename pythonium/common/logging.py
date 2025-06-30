"""
Logging utilities for the Pythonium framework.

This module provides centralized logging configuration and utilities
for consistent logging across all Pythonium components.
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger as loguru_logger


class LogLevel(Enum):
    """Log level enumeration."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Log format enumeration."""

    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"


class PythoniumLogger:
    """Enhanced logger wrapper for Pythonium."""

    def __init__(self, name: str):
        self.name = name
        self._logger = loguru_logger.bind(component=name)

    def trace(self, message: str, **kwargs):
        """Log trace message."""
        self._logger.trace(message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)

    def success(self, message: str, **kwargs):
        """Log success message."""
        self._logger.success(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message."""
        if exception:
            self._logger.error(f"{message}: {exception}", **kwargs)
        else:
            self._logger.error(message, **kwargs)

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message."""
        if exception:
            self._logger.critical(f"{message}: {exception}", **kwargs)
        else:
            self._logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, **kwargs)

    def bind(self, **kwargs) -> "PythoniumLogger":
        """Bind additional context to logger."""
        bound_logger = PythoniumLogger(self.name)
        bound_logger._logger = self._logger.bind(**kwargs)
        return bound_logger


def get_logger(name: str) -> PythoniumLogger:
    """Get a logger instance for the given name."""
    return PythoniumLogger(name)


def setup_logging(
    level: Union[str, LogLevel] = LogLevel.INFO,
    format_type: Union[str, LogFormat] = LogFormat.DETAILED,
    log_file: Optional[Union[str, Path]] = None,
    verbose: bool = False,
    component_filters: Optional[Dict[str, str]] = None,
) -> None:
    """
    Set up logging configuration for Pythonium.

    Args:
        level: Logging level
        format_type: Log format type
        log_file: Optional log file path
        verbose: Enable verbose logging
        component_filters: Component-specific log level filters
    """
    # Remove default loguru handler
    loguru_logger.remove()

    # Convert string level to LogLevel if needed
    if isinstance(level, str):
        level = LogLevel(level.upper())

    # Convert string format to LogFormat if needed
    if isinstance(format_type, str):
        format_type = LogFormat(format_type.lower())

    # Define formats
    formats = {
        LogFormat.SIMPLE: "{time:HH:mm:ss} | {level} | {message}",
        LogFormat.DETAILED: "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[component]: <15} | {message}",
        LogFormat.JSON: "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {extra[component]} | {message} | {extra}",
        LogFormat.STRUCTURED: "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[component]: <15}</cyan> | <level>{message}</level>",
    }

    log_format = formats[format_type]

    # Add console handler
    loguru_logger.add(
        sys.stderr,
        format=log_format,
        level=level.value,
        colorize=format_type == LogFormat.STRUCTURED,
        filter=(
            _create_component_filter(component_filters) if component_filters else None
        ),
    )

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        loguru_logger.add(
            str(log_path),
            format=formats[LogFormat.DETAILED],  # Always use detailed format for files
            level=level.value,
            rotation="10 MB",
            retention="1 week",
            compression="gz",
            filter=(
                _create_component_filter(component_filters)
                if component_filters
                else None
            ),
        )

    # Add verbose debug logging if requested
    if verbose:
        loguru_logger.add(
            sys.stderr,
            format="<dim>{time:HH:mm:ss.SSS}</dim> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            level="TRACE",
            filter=lambda record: record["level"].name in ["TRACE", "DEBUG"],
        )


def _create_component_filter(component_filters: Dict[str, str]):
    """Create a filter function for component-specific log levels."""

    def filter_func(record):
        component = record.get("extra", {}).get("component", "")
        if component in component_filters:
            required_level = component_filters[component]
            return record["level"].name >= required_level
        return True

    return filter_func


def configure_component_logging(
    component_name: str, level: Union[str, LogLevel]
) -> None:
    """Configure logging for a specific component."""
    # This would be used to set component-specific log levels
    # Implementation depends on how we want to manage component-specific settings
    pass


class LoggingContextManager:
    """Context manager for temporary logging configuration."""

    def __init__(
        self,
        level: Optional[Union[str, LogLevel]] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ):
        self.level = level
        self.extra_context = extra_context or {}
        self.original_handlers: List[Any] = []

    def __enter__(self):
        """Enter logging context."""
        # Store current handlers
        self.original_handlers = list(loguru_logger._core.handlers.copy())  # type: ignore

        if self.level:
            # Temporarily change log level
            level_value = (
                self.level.value if isinstance(self.level, LogLevel) else self.level
            )
            loguru_logger.level(level_value)

        # Bind extra context
        if self.extra_context:
            return loguru_logger.bind(**self.extra_context)

        return loguru_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logging context."""
        # Restore original handlers
        loguru_logger.configure(handlers=self.original_handlers)


def audit_log(
    action: str, user: str = "system", details: Optional[Dict[str, Any]] = None
) -> None:
    """Log audit events."""
    audit_logger = get_logger("audit")
    audit_logger.info(
        f"AUDIT: {action}", user=user, action=action, details=details or {}
    )


def performance_log(
    operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Log performance metrics."""
    perf_logger = get_logger("performance")
    perf_logger.info(
        f"PERFORMANCE: {operation} completed in {duration:.3f}s",
        operation=operation,
        duration=duration,
        metadata=metadata or {},
    )


# Default logger instance
logger = get_logger("pythonium")
