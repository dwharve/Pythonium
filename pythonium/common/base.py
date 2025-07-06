"""
Base classes and interfaces for the Pythonium framework.

This module provides the foundational base classes and interfaces
that are used throughout the Pythonium project.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar

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


class ComponentState(Enum):
    """Unified component lifecycle states."""

    # Creation and Discovery
    CREATED = "created"
    DISCOVERED = "discovered"

    # Loading and Initialization
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"

    # Connection and Session
    CONNECTING = "connecting"

    # Operation States
    STARTING = "starting"
    RUNNING = "running"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"

    # Cleanup and Shutdown
    STOPPING = "stopping"
    STOPPED = "stopped"
    CLEANUP = "cleanup"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    DISPOSED = "disposed"

    # Error State
    ERROR = "error"


class BaseComponent(ABC):
    """Base class for all Pythonium components."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = ComponentStatus.UNINITIALIZED
        self.created_at = datetime.utcnow()
        self.last_error: Optional[Exception] = None

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

    def get_status_info(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        return {
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_error": str(self.last_error) if self.last_error else None,
            "config": self.config,
        }


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

    def get_data_or_raise(self) -> T:
        """Get data or raise exception if error."""
        if not self.success:
            raise RuntimeError(f"Result failed: {self.error}")
        if self.data is None:
            raise RuntimeError("Result success but data is None")
        return self.data
