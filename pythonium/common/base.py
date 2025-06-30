"""
Base classes and interfaces for the Pythonium framework.

This module provides the foundational base classes and interfaces
that are used throughout the Pythonium project.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ComponentStatus(Enum):
    """Component status enumeration."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseComponent(ABC):
    """Base class for all Pythonium components."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = ComponentStatus.UNINITIALIZED
        self.created_at = datetime.utcnow()
        self.last_error: Optional[Exception] = None
        self._initialization_lock = asyncio.Lock()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the component."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the component."""
        pass

    async def health_check(self) -> bool:
        """Perform a health check on the component."""
        return self.status == ComponentStatus.RUNNING

    async def safe_initialize(self) -> None:
        """Safely initialize the component with error handling."""
        async with self._initialization_lock:
            if self.status != ComponentStatus.UNINITIALIZED:
                return

            try:
                self.status = ComponentStatus.INITIALIZING
                await self.initialize()
                self.status = ComponentStatus.RUNNING
                self.last_error = None
            except Exception as e:
                self.status = ComponentStatus.ERROR
                self.last_error = e
                raise

    async def safe_shutdown(self) -> None:
        """Safely shutdown the component with error handling."""
        if self.status in [
            ComponentStatus.STOPPED,
            ComponentStatus.UNINITIALIZED,
        ]:
            return

        try:
            self.status = ComponentStatus.STOPPING
            await self.shutdown()
            self.status = ComponentStatus.STOPPED
        except Exception as e:
            self.status = ComponentStatus.ERROR
            self.last_error = e
            raise

    def get_status_info(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        return {
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_error": str(self.last_error) if self.last_error else None,
            "config": self.config,
        }


class ConfigurableComponent(BaseComponent):
    """Base class for components that need configuration validation."""

    @abstractmethod
    def get_config_schema(self) -> type[BaseModel]:
        """Get the configuration schema for this component."""
        pass

    def validate_config(self) -> None:
        """Validate the component configuration."""
        schema = self.get_config_schema()
        try:
            schema(**self.config)
        except Exception as e:
            raise ValueError(f"Invalid configuration for {self.name}: {e}")


class AsyncIterable(ABC):
    """Base class for async iterable components."""

    @abstractmethod
    async def __aiter__(self):
        """Return async iterator."""
        pass

    @abstractmethod
    async def __anext__(self):
        """Return next item."""
        pass


class Singleton(type):
    """Singleton metaclass for ensuring single instances."""

    _instances: Dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Result(BaseModel, Generic[T]):
    """Generic result container with type safety."""

    success: bool = Field(description="Whether the operation was successful")
    data: Optional[T] = Field(default=None, description="Result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    execution_time: Optional[float] = Field(
        default=None, description="Execution time in seconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Result timestamp"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def success_result(
        cls,
        data: Optional[T] = None,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
    ) -> "Result[T]":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            metadata=metadata or {},
            execution_time=execution_time,
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
    ) -> "Result[T]":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {},
            execution_time=execution_time,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.success

    def is_error(self) -> bool:
        """Check if result is an error."""
        return not self.success

    def get_data_or_raise(self) -> T:
        """Get data or raise exception if error."""
        if not self.success:
            raise RuntimeError(f"Result failed: {self.error}")
        if self.data is None:
            raise RuntimeError("Result success but data is None")
        return self.data


class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    async def handle(self, event: Dict[str, Any]) -> None:
        """Handle an event."""
        pass


class Provider(ABC):
    """Base class for providers."""

    @abstractmethod
    async def provide(self, identifier: str) -> Any:
        """Provide a resource or service."""
        pass

    @abstractmethod
    async def can_provide(self, identifier: str) -> bool:
        """Check if this provider can handle the identifier."""
        pass


class Registry:
    """Generic registry for managing collections of items."""

    def __init__(self):
        self._items: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self, name: str, item: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an item."""
        self._items[name] = item
        self._metadata[name] = metadata or {}

    def unregister(self, name: str) -> None:
        """Unregister an item."""
        self._items.pop(name, None)
        self._metadata.pop(name, None)

    def get(self, name: str) -> Optional[Any]:
        """Get an item by name."""
        return self._items.get(name)

    def get_all(self) -> Dict[str, Any]:
        """Get all registered items."""
        return self._items.copy()

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Get metadata for an item."""
        return self._metadata.get(name, {})

    def list_names(self) -> List[str]:
        """List all registered item names."""
        return list(self._items.keys())

    def contains(self, name: str) -> bool:
        """Check if an item is registered."""
        return name in self._items
