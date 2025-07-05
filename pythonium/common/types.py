"""
Type definitions and protocols for the Pythonium framework.

This module provides type hints, protocols, and type aliases used
throughout the Pythonium project for better type safety and documentation.
"""

from abc import abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

from pythonium.common.base import Result

# Type aliases
JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
ConfigDict = Dict[str, Any]
MetadataDict = Dict[str, Any]
ParametersDict = Dict[str, Any]
ResultData = Union[str, int, float, bool, Dict[str, Any], List[Any], None]

# Generic type variables
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


# Result types - using generic Result[T] from base


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class EventData(NamedTuple):
    """Event data structure."""

    name: str
    data: Any
    timestamp: datetime
    source: Optional[str] = None


# Event handler type aliases
EventHandler = Callable[[Any], Awaitable[None]]
EventFilter = Callable[[Any], bool]


# Tool system types
class ToolInfo(NamedTuple):
    """Tool information."""

    name: str
    category: str
    description: str
    version: str
    parameters_schema: Dict[str, Any]
    metadata: MetadataDict


class ToolExecutionContext(NamedTuple):
    """Context for tool execution."""

    tool_name: str
    parameters: ParametersDict
    user: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[MetadataDict] = None


# Generic factory types
Factory = Callable[..., T]
AsyncFactory = Callable[..., Awaitable[T]]

# Callback types
Callback = Callable[..., None]
AsyncCallback = Callable[..., Awaitable[None]]

# Filter and predicate types
Filter = Callable[[T], bool]
AsyncFilter = Callable[[T], Awaitable[bool]]
Predicate = Filter[T]

# Configuration types
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]
ConfigPath = Union[str, List[str]]

# File system types
FilePath = Union[str, Path]
FileContent = Union[str, bytes]

# Network types
URL = str
Headers = Dict[str, str]
QueryParams = Dict[str, Union[str, List[str]]]

# Time types
Timestamp = Union[datetime, float, int]
Duration = Union[int, float]  # seconds

# Identifier types
ComponentID = str
SessionID = str
RequestID = str
UserID = str

# Size and limit types
ByteSize = int
TimeLimit = Duration
CountLimit = int
