"""
Tool management package for the Pythonium framework.

This package provides comprehensive tool management capabilities including
discovery, registration, dependency management, execution pipeline,
result caching, and performance monitoring.
"""

from .cache import (
    CacheEntry,
    CacheEvictionPolicy,
    CacheStats,
    CacheStrategy,
    ResultCache,
)
from .dependency import (
    CircularDependencyError,
    Dependency,
    DependencyError,
    DependencyManager,
    DependencyType,
    MissingDependencyError,
)
from .discovery import ToolDiscoveryManager
from .monitoring import (
    AlertLevel,
    MetricData,
    MetricType,
    PerformanceAlert,
    PerformanceMonitor,
    PerformanceStats,
    ThresholdConfig,
)
from .pipeline import (
    ExecutionContext,
    ExecutionError,
    ExecutionMode,
    ExecutionPipeline,
    ExecutionResult,
    ExecutionStatus,
    PipelineError,
)
from .registry import ToolRegistration, ToolRegistry, ToolStatus

__all__ = [
    # Discovery
    "ToolDiscoveryManager",
    # Registry
    "ToolRegistry",
    "ToolRegistration",
    "ToolStatus",
    # Dependencies
    "DependencyManager",
    "Dependency",
    "DependencyType",
    "DependencyError",
    "CircularDependencyError",
    "MissingDependencyError",
    # Pipeline
    "ExecutionPipeline",
    "ExecutionResult",
    "ExecutionContext",
    "ExecutionStatus",
    "ExecutionMode",
    "ExecutionError",
    "PipelineError",
    # Cache
    "ResultCache",
    "CacheEntry",
    "CacheStrategy",
    "CacheEvictionPolicy",
    "CacheStats",
    # Monitoring
    "PerformanceMonitor",
    "MetricData",
    "PerformanceAlert",
    "PerformanceStats",
    "MetricType",
    "AlertLevel",
    "ThresholdConfig",
]
