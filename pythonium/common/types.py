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


class ComponentType(Enum):
    """Types of components in the Pythonium system."""

    MANAGER = "manager"
    TOOL = "tool"
    PLUGIN = "plugin"
    SERVER = "server"
    CLIENT = "client"


class Priority(Enum):
    """Priority levels for operations."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TransportType(Enum):
    """Types of transport protocols."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


# Result types - using generic Result[T] from base


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


# Protocol definitions
@runtime_checkable
class Configurable(Protocol):
    """Protocol for configurable components."""

    @abstractmethod
    def configure(self, config: ConfigDict) -> None:
        """Configure the component."""
        ...

    @abstractmethod
    def get_config(self) -> ConfigDict:
        """Get current configuration."""
        ...


@runtime_checkable
class Initializable(Protocol):
    """Protocol for components that can be initialized."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the component."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the component."""
        ...


@runtime_checkable
class HealthCheckable(Protocol):
    """Protocol for components that support health checks."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Perform health check."""
        ...


@runtime_checkable
class Discoverable(Protocol):
    """Protocol for discoverable components."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Component name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Component version."""
        ...

    @abstractmethod
    def get_metadata(self) -> MetadataDict:
        """Get component metadata."""
        ...


@runtime_checkable
class Executable(Protocol):
    """Protocol for executable components like tools."""

    @abstractmethod
    async def execute(self, **kwargs) -> Result[Any]:
        """Execute the component."""
        ...


@runtime_checkable
class Pluggable(Protocol):
    """Protocol for plugin components."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Plugin name."""
        ...

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Plugin version."""
        ...

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Get plugin dependencies."""
        ...


@runtime_checkable
class EventEmitter(Protocol):
    """Protocol for event emitting components."""

    @abstractmethod
    async def emit(self, event: str, data: Any = None) -> None:
        """Emit an event."""
        ...


@runtime_checkable
class EventListener(Protocol):
    """Protocol for event listening components."""

    @abstractmethod
    async def on(self, event: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """Register event handler."""
        ...

    @abstractmethod
    async def off(self, event: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """Unregister event handler."""
        ...


@runtime_checkable
class Serializable(Protocol):
    """Protocol for serializable objects."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
        """Create from dictionary."""
        ...


@runtime_checkable
class Cacheable(Protocol):
    """Protocol for cacheable objects."""

    @abstractmethod
    def get_cache_key(self) -> str:
        """Get cache key."""
        ...

    @abstractmethod
    def get_cache_ttl(self) -> int:
        """Get cache TTL in seconds."""
        ...


@runtime_checkable
class Loggable(Protocol):
    """Protocol for components that support logging context."""

    @abstractmethod
    def get_log_context(self) -> Dict[str, Any]:
        """Get logging context."""
        ...


# Manager protocols
@runtime_checkable
class Manager(Configurable, Initializable, HealthCheckable, Discoverable, Protocol):
    """Protocol for manager components."""

    @property
    @abstractmethod
    def manager_type(self) -> str:
        """Manager type identifier."""
        ...


@runtime_checkable
class PluginManager(Manager, Protocol):
    """Protocol for plugin managers."""

    @abstractmethod
    async def load_plugin(self, plugin_name: str) -> Pluggable:
        """Load a plugin."""
        ...

    @abstractmethod
    async def unload_plugin(self, plugin_name: str) -> None:
        """Unload a plugin."""
        ...

    @abstractmethod
    def list_plugins(self) -> List[str]:
        """List available plugins."""
        ...


@runtime_checkable
class ResourceManager(Manager, Protocol):
    """Protocol for resource managers."""

    @abstractmethod
    async def acquire(self, resource_type: str, **kwargs) -> Any:
        """Acquire a resource."""
        ...

    @abstractmethod
    async def release(self, resource: Any) -> None:
        """Release a resource."""
        ...


# Tool protocols
@runtime_checkable
class Tool(Discoverable, Executable, Configurable, Protocol):
    """Protocol for tool components."""

    @property
    @abstractmethod
    def category(self) -> str:
        """Tool category."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        ...

    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get parameters schema."""
        ...


@runtime_checkable
class AsyncTool(Tool, Protocol):
    """Protocol for asynchronous tools."""

    @abstractmethod
    async def execute_async(self, **kwargs) -> Result[Any]:
        """Execute tool asynchronously."""
        ...


# MCP protocols
@runtime_checkable
class MCPTransport(Protocol):
    """Protocol for MCP transport implementations."""

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message."""
        ...

    @abstractmethod
    async def receive(self) -> Dict[str, Any]:
        """Receive a message."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""
        ...


@runtime_checkable
class MCPServer(Initializable, HealthCheckable, Protocol):
    """Protocol for MCP server implementations."""

    @abstractmethod
    async def serve(self, transport: MCPTransport) -> None:
        """Start serving with the given transport."""
        ...

    @abstractmethod
    def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        ...


# Event system types
EventHandler = Callable[[Any], Awaitable[None]]
EventFilter = Callable[[Any], bool]


class EventData(NamedTuple):
    """Event data structure."""

    name: str
    data: Any
    timestamp: datetime
    source: Optional[str] = None


# Plugin system types
class PluginInfo(NamedTuple):
    """Plugin information."""

    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    config_schema: Optional[Dict[str, Any]] = None


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
