"""
Logging utilities for the Pythonium framework.

This module provides centralized logging configuration and utilities
for consistent logging across all Pythonium components.
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from loguru import logger


class LogFormat(Enum):
    """Log format enumeration."""

    SIMPLE = "simple"
    DETAILED = "detailed"
    STRUCTURED = "structured"


def get_logger(name: str):
    """Get a logger instance for the given component."""
    return logger.bind(component=name)


def setup_logging(
    level: str = "INFO",
    format_type: Union[str, LogFormat] = LogFormat.DETAILED,
    log_file: Optional[Union[str, Path]] = None,
    verbose: bool = False,
) -> None:
    """
    Set up logging configuration for Pythonium.

    Args:
        level: Logging level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format type
        log_file: Optional log file path
        verbose: Enable verbose logging with file/line info
    """
    # Remove default loguru handler
    logger.remove()

    # Convert string format to LogFormat if needed
    if isinstance(format_type, str):
        format_type = LogFormat(format_type.lower())

    # Define formats
    formats = {
        LogFormat.SIMPLE: "{time:HH:mm:ss} | {level} | {message}",
        LogFormat.DETAILED: "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[component]: <15} | {message}",
        LogFormat.STRUCTURED: "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[component]: <15}</cyan> | <level>{message}</level>",
    }

    log_format = formats[format_type]

    # Add console handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=level,
        colorize=format_type == LogFormat.STRUCTURED,
    )

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            format=formats[LogFormat.DETAILED],  # Always use detailed format for files
            level=level,
            rotation="10 MB",
            retention="1 week",
            compression="gz",
        )

    # Add verbose debug logging if requested
    if verbose:
        logger.add(
            sys.stderr,
            format="<dim>{time:HH:mm:ss.SSS}</dim> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            level="TRACE",
            filter=lambda record: record["level"].name in ["TRACE", "DEBUG"],
        )


def audit_log(action: str, user: str = "system", **details) -> None:
    """Log audit events."""
    audit_logger = get_logger("audit")
    audit_logger.info(f"AUDIT: {action}", user=user, action=action, **details)


def performance_log(operation: str, duration: float, **metadata) -> None:
    """Log performance metrics."""
    perf_logger = get_logger("performance")
    perf_logger.info(
        f"PERFORMANCE: {operation} completed in {duration:.3f}s",
        operation=operation,
        duration=duration,
        **metadata,
    )


# Default logger instance
default_logger = get_logger("pythonium")
