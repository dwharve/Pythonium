"""
Performance monitoring and metrics collection for Pythonium MCP server.

Provides comprehensive performance monitoring, metrics collection,
and resource usage tracking for improved observability.
"""

import time
import psutil
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from statistics import mean, median


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    name: str
    value: Union[int, float]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


@dataclass
class ToolExecutionMetrics:
    """Metrics for tool execution."""
    tool_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    success: bool
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "tool_name": self.tool_name,
            "execution_time": self.execution_time,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "success": self.success,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat()
        }


class MetricsCollector:
    """
    Collects and aggregates performance metrics.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of metrics to keep in history
        """
        self.max_history = max_history
        self._metrics = deque(maxlen=max_history)
        self._tool_metrics = defaultdict(lambda: deque(maxlen=100))
        self._counters = defaultdict(int)
        self._gauges = {}
        self._histograms = defaultdict(list)
        self._lock = threading.RLock()
    
    def record_metric(
        self, 
        name: str, 
        value: Union[int, float], 
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
        """
        with self._lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self._metrics.append(metric)
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value
            self.record_metric(f"{name}_total", self._counters[name], tags)
    
    def set_gauge(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        with self._lock:
            self._gauges[name] = value
            self.record_metric(name, value, tags)
    
    def record_histogram(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Record a value in a histogram."""
        with self._lock:
            self._histograms[name].append(value)
            # Keep only recent values
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]
            self.record_metric(name, value, tags)
    
    def record_tool_execution(self, metrics: ToolExecutionMetrics) -> None:
        """Record tool execution metrics."""
        with self._lock:
            self._tool_metrics[metrics.tool_name].append(metrics)
            
            # Record individual metrics
            self.record_histogram(
                "tool_execution_time", 
                metrics.execution_time,
                {"tool": metrics.tool_name, "success": str(metrics.success)}
            )
            self.record_histogram(
                "tool_memory_usage", 
                metrics.memory_usage,
                {"tool": metrics.tool_name}
            )
            self.increment_counter(
                "tool_executions", 
                1, 
                {"tool": metrics.tool_name, "success": str(metrics.success)}
            )
    
    def get_metrics_summary(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get summary of collected metrics.
        
        Args:
            since: Only include metrics since this timestamp
            
        Returns:
            Dictionary with metrics summary
        """
        with self._lock:
            if since is None:
                since = datetime.now() - timedelta(hours=1)
            
            # Filter metrics by timestamp
            recent_metrics = [m for m in self._metrics if m.timestamp >= since]
            
            summary = {
                "total_metrics": len(recent_metrics),
                "time_range": {
                    "start": since.isoformat(),
                    "end": datetime.now().isoformat()
                },
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {}
            }
            
            # Calculate histogram statistics
            for name, values in self._histograms.items():
                if values:
                    summary["histograms"][name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": mean(values),
                        "median": median(values),
                        "recent_values": values[-10:]  # Last 10 values
                    }
            
            return summary
    
    def get_tool_metrics_summary(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of tool execution metrics.
        
        Args:
            tool_name: Specific tool to get metrics for, or all tools if None
            
        Returns:
            Dictionary with tool metrics summary
        """
        with self._lock:
            if tool_name:
                tools_to_analyze = {tool_name: self._tool_metrics[tool_name]}
            else:
                tools_to_analyze = dict(self._tool_metrics)
            
            summary = {}
            
            for tool, metrics_list in tools_to_analyze.items():
                if not metrics_list:
                    continue
                
                execution_times = [m.execution_time for m in metrics_list]
                memory_usage = [m.memory_usage for m in metrics_list]
                success_count = sum(1 for m in metrics_list if m.success)
                total_count = len(metrics_list)
                
                summary[tool] = {
                    "total_executions": total_count,
                    "success_rate": success_count / total_count if total_count > 0 else 0,
                    "execution_time": {
                        "min": min(execution_times) if execution_times else 0,
                        "max": max(execution_times) if execution_times else 0,
                        "mean": mean(execution_times) if execution_times else 0,
                        "median": median(execution_times) if execution_times else 0
                    },
                    "memory_usage": {
                        "min": min(memory_usage) if memory_usage else 0,
                        "max": max(memory_usage) if memory_usage else 0,
                        "mean": mean(memory_usage) if memory_usage else 0,
                        "median": median(memory_usage) if memory_usage else 0
                    },
                    "recent_errors": [
                        m.error_type for m in list(metrics_list)[-10:] 
                        if not m.success and m.error_type
                    ]
                }
            
            return summary
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        with self._lock:
            self._metrics.clear()
            self._tool_metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


class PerformanceMonitor:
    """
    Performance monitor with system resource tracking.
    """
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize performance monitor.
        
        Args:
            metrics_collector: Metrics collector to use, creates new one if None
        """
        self.metrics = metrics_collector or MetricsCollector()
        self._monitoring_active = False
        self._monitoring_thread = None
        self._system_process = psutil.Process()
    
    def start_monitoring(self, interval: float = 5.0) -> None:
        """
        Start continuous system monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitor_system_resources,
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop continuous system monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=1.0)
    
    def _monitor_system_resources(self, interval: float) -> None:
        """Monitor system resources in background thread."""
        while self._monitoring_active:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.metrics.set_gauge("system_cpu_percent", cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.metrics.set_gauge("system_memory_percent", memory.percent)
                self.metrics.set_gauge("system_memory_used_mb", memory.used / 1024 / 1024)
                
                # Process-specific metrics
                try:
                    process_memory = self._system_process.memory_info()
                    self.metrics.set_gauge("process_memory_rss_mb", process_memory.rss / 1024 / 1024)
                    self.metrics.set_gauge("process_memory_vms_mb", process_memory.vms / 1024 / 1024)
                    
                    process_cpu = self._system_process.cpu_percent()
                    self.metrics.set_gauge("process_cpu_percent", process_cpu)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                # Disk usage for current directory
                try:
                    disk_usage = psutil.disk_usage('.')
                    disk_percent = (disk_usage.used / disk_usage.total) * 100
                    self.metrics.set_gauge("disk_usage_percent", disk_percent)
                except:
                    pass
                
                time.sleep(interval)
                
            except Exception:
                # Continue monitoring even if individual metrics fail
                time.sleep(interval)
    
    def measure_execution(self, func: Callable, *args, **kwargs) -> Any:
        """
        Measure execution time and resource usage of a function.
        
        Args:
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error_type = None
        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            end_cpu = self._get_cpu_usage()
            
            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory
            cpu_delta = end_cpu - start_cpu
            
            # Record execution metrics
            self.metrics.record_histogram("execution_time", execution_time)
            self.metrics.record_histogram("memory_delta", memory_delta)
            self.metrics.record_histogram("cpu_delta", cpu_delta)
        
        return result
    
    def measure_tool_execution(
        self, 
        tool_name: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Measure tool execution with detailed metrics.
        
        Args:
            tool_name: Name of the tool being executed
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        success = False
        error_type = None
        result = None
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            error_type = type(e).__name__
            raise
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            metrics = ToolExecutionMetrics(
                tool_name=tool_name,
                execution_time=end_time - start_time,
                memory_usage=end_memory - start_memory,
                cpu_usage=self._get_cpu_usage() - start_cpu,
                success=success,
                error_type=error_type
            )
            
            self.metrics.record_tool_execution(metrics)
        
        return result
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self._system_process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return self._system_process.cpu_percent()
        except:
            return 0.0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Returns:
            Dictionary with performance report
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self._monitoring_active,
            "metrics_summary": self.metrics.get_metrics_summary(),
            "tool_metrics": self.metrics.get_tool_metrics_summary(),
            "system_status": self._get_system_status()
        }
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / 1024 / 1024 / 1024,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                "disk_percent": (disk.used / disk.total) * 100
            }
        except Exception as e:
            return {"error": str(e)}
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()
