"""
Tool performance monitoring system.

This module provides functionality to monitor tool performance, collect metrics,
and provide insights for optimization.
"""

import asyncio
import logging
import statistics
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pythonium.common.serialization import to_json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""

    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUEUE_TIME = "queue_time"
    CUSTOM = "custom"


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """Individual metric data point."""

    timestamp: datetime
    value: float
    tool_id: str
    metric_type: MetricType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert information."""

    tool_id: str
    metric_type: MetricType
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""

    tool_id: str
    metric_type: MetricType
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    window_start: datetime
    window_end: datetime


class ThresholdConfig:
    """Configuration for performance thresholds."""

    def __init__(
        self,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        comparison: str = "greater",  # greater, less, equal
        window_size: int = 10,  # Number of measurements to consider
        consecutive_violations: int = 3,  # Consecutive violations needed for alert
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.comparison = comparison
        self.window_size = window_size
        self.consecutive_violations = consecutive_violations


class PerformanceMonitor:
    """
    Advanced performance monitoring system for tools.

    Features:
    - Real-time metric collection and aggregation
    - Configurable alerting with thresholds
    - Statistical analysis and reporting
    - Performance trend analysis
    - Custom metric support
    - Export capabilities
    """

    def __init__(
        self,
        max_history: int = 10000,
        aggregation_window: int = 60,  # seconds
        enable_system_metrics: bool = True,
    ):
        self.max_history = max_history
        self.aggregation_window = aggregation_window
        self.enable_system_metrics = enable_system_metrics

        # Storage
        self._metrics: Dict[str, Dict[MetricType, deque]] = defaultdict(
            lambda: defaultdict(deque)
        )
        self._alerts: List[PerformanceAlert] = []
        self._thresholds: Dict[str, Dict[MetricType, ThresholdConfig]] = defaultdict(
            dict
        )
        self._violation_counts: Dict[str, Dict[MetricType, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Statistics cache
        self._stats_cache: Dict[str, PerformanceStats] = {}
        self._cache_expires: Dict[str, datetime] = {}

        # Event handlers
        self._alert_handlers: List[Callable] = []
        self._metric_handlers: List[Callable] = []

        # Synchronization
        self._lock = threading.RLock()

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.debug("Initialized PerformanceMonitor")

    def start_monitoring(self) -> None:
        """Start background monitoring tasks."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Started performance monitoring")

    def stop_monitoring(self) -> None:
        """Stop background monitoring tasks."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        logger.info("Stopped performance monitoring")

    def record_metric(
        self,
        tool_id: str,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a performance metric.

        Args:
            tool_id: Tool identifier
            metric_type: Type of metric
            value: Metric value
            metadata: Additional metadata
        """
        metric = MetricData(
            timestamp=datetime.now(),
            value=value,
            tool_id=tool_id,
            metric_type=metric_type,
            metadata=metadata or {},
        )

        with self._lock:
            # Add to storage
            tool_metrics = self._metrics[tool_id][metric_type]
            tool_metrics.append(metric)

            # Limit history size
            if len(tool_metrics) > self.max_history:
                tool_metrics.popleft()

            # Check thresholds
            self._check_thresholds(tool_id, metric_type, value)

            # Invalidate stats cache
            cache_key = f"{tool_id}:{metric_type.value}"
            if cache_key in self._stats_cache:
                del self._stats_cache[cache_key]
                del self._cache_expires[cache_key]

        # Notify handlers
        for handler in self._metric_handlers:
            try:
                handler(metric)
            except Exception as e:
                logger.error(f"Metric handler failed: {e}")

        logger.debug(f"Recorded metric: {tool_id} {metric_type.value} = {value}")

    def record_execution_time(
        self,
        tool_id: str,
        duration_ms: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record tool execution time and success rate."""
        self.record_metric(tool_id, MetricType.EXECUTION_TIME, duration_ms, metadata)
        self.record_metric(
            tool_id, MetricType.SUCCESS_RATE, 1.0 if success else 0.0, metadata
        )

    def record_throughput(self, tool_id: str, operations_per_second: float) -> None:
        """Record tool throughput."""
        self.record_metric(tool_id, MetricType.THROUGHPUT, operations_per_second)

    def record_error(self, tool_id: str, error_type: str) -> None:
        """Record an error occurrence."""
        self.record_metric(
            tool_id, MetricType.ERROR_RATE, 1.0, {"error_type": error_type}
        )

    def record_custom_metric(
        self,
        tool_id: str,
        name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a custom metric."""
        custom_metadata = {"custom_name": name}
        if metadata:
            custom_metadata.update(metadata)

        self.record_metric(tool_id, MetricType.CUSTOM, value, custom_metadata)

    def set_threshold(
        self, tool_id: str, metric_type: MetricType, config: ThresholdConfig
    ) -> None:
        """
        Set performance threshold for alerts.

        Args:
            tool_id: Tool identifier
            metric_type: Metric type
            config: Threshold configuration
        """
        with self._lock:
            self._thresholds[tool_id][metric_type] = config

        logger.debug(f"Set threshold for {tool_id} {metric_type.value}")

    def get_statistics(
        self,
        tool_id: str,
        metric_type: MetricType,
        window_minutes: Optional[int] = None,
    ) -> Optional[PerformanceStats]:
        """
        Get performance statistics for a tool and metric type.

        Args:
            tool_id: Tool identifier
            metric_type: Metric type
            window_minutes: Time window in minutes (None for all data)

        Returns:
            PerformanceStats or None if no data
        """
        cache_key = f"{tool_id}:{metric_type.value}:{window_minutes}"

        # Check cache
        if (
            cache_key in self._stats_cache
            and cache_key in self._cache_expires
            and datetime.now() < self._cache_expires[cache_key]
        ):
            return self._stats_cache[cache_key]

        with self._lock:
            if (
                tool_id not in self._metrics
                or metric_type not in self._metrics[tool_id]
            ):
                return None

            metrics = list(self._metrics[tool_id][metric_type])

            if not metrics:
                return None

            # Filter by time window
            if window_minutes:
                cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
                metrics = [m for m in metrics if m.timestamp >= cutoff_time]

            if not metrics:
                return None

            # Calculate statistics
            values = [m.value for m in metrics]
            stats = PerformanceStats(
                tool_id=tool_id,
                metric_type=metric_type,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                mean_value=statistics.mean(values),
                median_value=statistics.median(values),
                std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
                percentile_95=self._percentile(values, 95),
                percentile_99=self._percentile(values, 99),
                window_start=min(m.timestamp for m in metrics),
                window_end=max(m.timestamp for m in metrics),
            )

            # Cache result
            self._stats_cache[cache_key] = stats
            self._cache_expires[cache_key] = datetime.now() + timedelta(minutes=5)

            return stats

    def get_alerts(
        self,
        tool_id: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        since: Optional[datetime] = None,
    ) -> List[PerformanceAlert]:
        """
        Get performance alerts with optional filtering.

        Args:
            tool_id: Filter by tool ID
            level: Filter by alert level
            since: Filter by timestamp

        Returns:
            List of matching alerts
        """
        with self._lock:
            alerts = self._alerts.copy()

        # Apply filters
        if tool_id:
            alerts = [a for a in alerts if a.tool_id == tool_id]

        if level:
            alerts = [a for a in alerts if a.level == level]

        if since:
            alerts = [a for a in alerts if a.timestamp >= since]

        return alerts

    def get_tool_summary(self, tool_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive performance summary for a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            Dictionary containing performance summary
        """
        summary: Dict[str, Any] = {
            "tool_id": tool_id,
            "metrics": {},
            "alerts": self.get_alerts(tool_id=tool_id),
            "last_updated": datetime.now().isoformat(),
        }

        # Get statistics for each metric type
        for metric_type in MetricType:
            stats = self.get_statistics(tool_id, metric_type)
            if stats:
                summary["metrics"][metric_type.value] = {
                    "count": stats.count,
                    "mean": stats.mean_value,
                    "min": stats.min_value,
                    "max": stats.max_value,
                    "std_dev": stats.std_dev,
                    "p95": stats.percentile_95,
                    "p99": stats.percentile_99,
                }

        return summary

    def get_all_tools_summary(self) -> Dict[str, Any]:
        """Get performance summary for all monitored tools."""
        with self._lock:
            tool_ids = list(self._metrics.keys())

        return {tool_id: self.get_tool_summary(tool_id) for tool_id in tool_ids}

    def add_alert_handler(self, handler: Callable[[PerformanceAlert], None]) -> None:
        """Add an alert handler function."""
        self._alert_handlers.append(handler)
        logger.debug("Added alert handler")

    def add_metric_handler(self, handler: Callable[[MetricData], None]) -> None:
        """Add a metric handler function."""
        self._metric_handlers.append(handler)
        logger.debug("Added metric handler")

    def clear_metrics(self, tool_id: Optional[str] = None) -> None:
        """
        Clear metrics for a tool or all tools.

        Args:
            tool_id: Tool to clear metrics for, or None for all tools
        """
        with self._lock:
            if tool_id:
                if tool_id in self._metrics:
                    del self._metrics[tool_id]
                if tool_id in self._thresholds:
                    del self._thresholds[tool_id]
                if tool_id in self._violation_counts:
                    del self._violation_counts[tool_id]
            else:
                self._metrics.clear()
                self._thresholds.clear()
                self._violation_counts.clear()

            # Clear caches
            self._stats_cache.clear()
            self._cache_expires.clear()

        logger.info(f"Cleared metrics for {tool_id or 'all tools'}")

    def export_metrics(
        self, tool_id: Optional[str] = None, format_type: str = "json"
    ) -> str:
        """
        Export metrics in the specified format.

        Args:
            tool_id: Tool to export metrics for, or None for all tools
            format_type: Export format ("json", "csv")

        Returns:
            Exported data as string
        """
        if format_type.lower() == "json":
            return self._export_json(tool_id)
        elif format_type.lower() == "csv":
            return self._export_csv(tool_id)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def _export_json(self, tool_id: Optional[str] = None) -> str:
        """Export metrics as JSON."""
        data: Dict[str, Any] = {
            "export_timestamp": datetime.now().isoformat(),
            "tools": {},
        }

        with self._lock:
            tools_to_export = [tool_id] if tool_id else list(self._metrics.keys())

            for tid in tools_to_export:
                if tid in self._metrics:
                    tool_data: Dict[str, Any] = {"metrics": {}}

                    for metric_type, metric_deque in self._metrics[tid].items():
                        tool_data["metrics"][metric_type.value] = [
                            {
                                "timestamp": m.timestamp.isoformat(),
                                "value": m.value,
                                "metadata": m.metadata,
                            }
                            for m in metric_deque
                        ]

                    data["tools"][tid] = tool_data

        return to_json(data, pretty=True)

    def _export_csv(self, tool_id: Optional[str] = None) -> str:
        """Export metrics as CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["tool_id", "metric_type", "timestamp", "value", "metadata"])

        with self._lock:
            tools_to_export = [tool_id] if tool_id else list(self._metrics.keys())

            for tid in tools_to_export:
                if tid in self._metrics:
                    for metric_type, metric_deque in self._metrics[tid].items():
                        for metric in metric_deque:
                            writer.writerow(
                                [
                                    tid,
                                    metric_type.value,
                                    metric.timestamp.isoformat(),
                                    metric.value,
                                    (
                                        to_json(metric.metadata)
                                        if metric.metadata
                                        else ""
                                    ),
                                ]
                            )

        return output.getvalue()

    def _is_threshold_configured(self, tool_id: str, metric_type: MetricType) -> bool:
        """Check if thresholds are configured for this tool and metric."""
        return tool_id in self._thresholds and metric_type in self._thresholds[tool_id]

    def _check_violation_level(
        self, config: ThresholdConfig, value: float
    ) -> tuple[bool, Optional[AlertLevel], Optional[float]]:
        """Check if value violates thresholds and return violation details."""
        if config.comparison == "greater":
            if config.critical_threshold and value > config.critical_threshold:
                return True, AlertLevel.CRITICAL, config.critical_threshold
            elif config.warning_threshold and value > config.warning_threshold:
                return True, AlertLevel.WARNING, config.warning_threshold
        elif config.comparison == "less":
            if config.critical_threshold and value < config.critical_threshold:
                return True, AlertLevel.CRITICAL, config.critical_threshold
            elif config.warning_threshold and value < config.warning_threshold:
                return True, AlertLevel.WARNING, config.warning_threshold

        return False, None, None

    def _should_create_alert(
        self, tool_id: str, metric_type: MetricType, config: ThresholdConfig
    ) -> bool:
        """Check if enough consecutive violations occurred to create an alert."""
        return (
            self._violation_counts[tool_id][metric_type]
            >= config.consecutive_violations
        )

    def _create_and_send_alert(
        self,
        tool_id: str,
        metric_type: MetricType,
        level: AlertLevel,
        value: float,
        threshold: float,
        config: ThresholdConfig,
    ) -> None:
        """Create and send performance alert."""
        alert = PerformanceAlert(
            tool_id=tool_id,
            metric_type=metric_type,
            level=level,
            message=f"{metric_type.value} threshold violated: {value} {config.comparison} {threshold}",
            value=value,
            threshold=threshold,
            timestamp=datetime.now(),
        )

        self._alerts.append(alert)

        # Notify handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

        logger.warning(f"Performance alert: {alert.message}")

    def _check_thresholds(
        self, tool_id: str, metric_type: MetricType, value: float
    ) -> None:
        """Check if a metric value violates configured thresholds."""
        if not self._is_threshold_configured(tool_id, metric_type):
            return

        config = self._thresholds[tool_id][metric_type]
        violated, level, threshold = self._check_violation_level(config, value)

        if violated:
            # Check consecutive violations
            self._violation_counts[tool_id][metric_type] += 1

            if self._should_create_alert(tool_id, metric_type, config):
                assert (
                    level is not None
                ), "level should not be None when violated is True"
                assert (
                    threshold is not None
                ), "threshold should not be None when violated is True"
                self._create_and_send_alert(
                    tool_id, metric_type, level, value, threshold, config
                )
        else:
            # Reset violation count
            self._violation_counts[tool_id][metric_type] = 0

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.aggregation_window)

                # Perform periodic tasks
                if self.enable_system_metrics:
                    await self._collect_system_metrics()

                # Clean old alerts
                await self._cleanup_old_alerts()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                # Clean old metrics
                cutoff_time = datetime.now() - timedelta(hours=24)

                with self._lock:
                    for tool_id in list(self._metrics.keys()):
                        for metric_type in list(self._metrics[tool_id].keys()):
                            metric_deque = self._metrics[tool_id][metric_type]

                            # Remove old metrics
                            while (
                                metric_deque and metric_deque[0].timestamp < cutoff_time
                            ):
                                metric_deque.popleft()

                            # Remove empty deques
                            if not metric_deque:
                                del self._metrics[tool_id][metric_type]

                        # Remove empty tool entries
                        if not self._metrics[tool_id]:
                            del self._metrics[tool_id]

                logger.debug("Completed metric cleanup")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _collect_system_metrics(self) -> None:
        """Collect system-wide performance metrics."""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent()
            self.record_custom_metric("system", "cpu_usage_percent", cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.record_custom_metric("system", "memory_usage_percent", memory.percent)
            self.record_custom_metric(
                "system", "memory_available_mb", memory.available / 1024 / 1024
            )

            # Disk usage for cache directory (if exists)
            if hasattr(self, "cache_dir"):
                disk_usage = psutil.disk_usage(str(self.cache_dir))
                self.record_custom_metric(
                    "system",
                    "disk_usage_percent",
                    (disk_usage.used / disk_usage.total) * 100,
                )

        except ImportError:
            logger.debug("psutil not available, skipping system metrics")
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    async def _cleanup_old_alerts(self) -> None:
        """Remove old alerts to prevent memory growth."""
        cutoff_time = datetime.now() - timedelta(days=7)

        with self._lock:
            self._alerts = [a for a in self._alerts if a.timestamp >= cutoff_time]
