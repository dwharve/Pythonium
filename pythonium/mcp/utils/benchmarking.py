"""
Performance benchmarking utilities for Pythonium MCP server.

Provides comprehensive performance testing and benchmarking capabilities
for measuring and analyzing server performance under various conditions.
"""

import asyncio
import time
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import psutil
import threading

from . import PerformanceMonitor

if TYPE_CHECKING:
    from ..server import PythoniumMCPServer


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    test_name: str
    iterations: int
    total_time: float
    average_time: float
    min_time: float
    max_time: float
    median_time: float
    std_deviation: float
    operations_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: int
    success_rate: float


@dataclass
class LoadTestResult:
    """Result of a load test."""
    test_name: str
    concurrent_users: int
    total_requests: int
    duration_seconds: float
    requests_per_second: float
    average_response_time: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_score: float


class PerformanceBenchmark:
    """
    Comprehensive performance benchmarking for the MCP server.
    """
    
    def __init__(self, server: Optional["PythoniumMCPServer"] = None):
        """
        Initialize performance benchmark.
        
        Args:
            server: Optional server instance to benchmark
        """
        if server is None:
            from ..server import PythoniumMCPServer
            server = PythoniumMCPServer("benchmark-server", "1.0.0")
        self.server = server
        self.monitor = PerformanceMonitor()
        self.results: List[BenchmarkResult] = []
        
    def benchmark_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        iterations: int = 100
    ) -> BenchmarkResult:
        """
        Benchmark tool execution performance.
        
        Args:
            tool_name: Name of tool to benchmark
            arguments: Tool arguments
            iterations: Number of iterations to run
            
        Returns:
            Benchmark results
        """
        times = []
        errors = 0
        
        # Warm up
        try:
            asyncio.run(self._execute_tool_safe(tool_name, arguments))
        except:
            pass
        
        # Measure memory and CPU before
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run benchmark
        start_time = time.time()
        
        for i in range(iterations):
            iteration_start = time.time()
            try:
                asyncio.run(self._execute_tool_safe(tool_name, arguments))
            except Exception:
                errors += 1
            iteration_time = time.time() - iteration_start
            times.append(iteration_time)
        
        total_time = time.time() - start_time
        
        # Measure memory and CPU after
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent()
        
        # Calculate statistics
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            ops_per_sec = iterations / total_time
        else:
            avg_time = min_time = max_time = median_time = std_dev = ops_per_sec = 0
        
        result = BenchmarkResult(
            test_name=f"tool_execution_{tool_name}",
            iterations=iterations,
            total_time=total_time,
            average_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_deviation=std_dev,
            operations_per_second=ops_per_sec,
            memory_usage_mb=final_memory - initial_memory,
            cpu_usage_percent=cpu_percent,
            errors=errors,
            success_rate=(iterations - errors) / iterations * 100 if iterations > 0 else 0
        )
        
        self.results.append(result)
        return result
    
    async def _execute_tool_safe(self, tool_name: str, arguments: Dict[str, Any]):
        """Safely execute a tool, handling exceptions."""
        if self.server.tool_registry.has_tool(tool_name):
            return await self.server.tool_registry.execute_tool(tool_name, arguments)
        else:
            raise ValueError(f"Tool {tool_name} not found")
    
    def benchmark_middleware_chain(self, iterations: int = 1000) -> BenchmarkResult:
        """
        Benchmark middleware chain performance.
        
        Args:
            iterations: Number of iterations to run
            
        Returns:
            Benchmark results
        """
        times = []
        errors = 0
        
        async def mock_handler(name: str, args: Dict[str, Any]):
            return [{"type": "text", "text": "mock result"}]
        
        # Warm up
        try:
            asyncio.run(
                self.server.middleware_chain.process("mock_tool", {}, mock_handler)
            )
        except:
            pass
        
        # Measure performance
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        
        for i in range(iterations):
            iteration_start = time.time()
            try:
                asyncio.run(
                    self.server.middleware_chain.process("mock_tool", {}, mock_handler)
                )
            except Exception:
                errors += 1
            iteration_time = time.time() - iteration_start
            times.append(iteration_time)
        
        total_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        # Calculate statistics
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            ops_per_sec = iterations / total_time
        else:
            avg_time = min_time = max_time = median_time = std_dev = ops_per_sec = 0
        
        result = BenchmarkResult(
            test_name="middleware_chain",
            iterations=iterations,
            total_time=total_time,
            average_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_deviation=std_dev,
            operations_per_second=ops_per_sec,
            memory_usage_mb=final_memory - initial_memory,
            cpu_usage_percent=cpu_percent,
            errors=errors,
            success_rate=(iterations - errors) / iterations * 100 if iterations > 0 else 0
        )
        
        self.results.append(result)
        return result
    
    def load_test(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        concurrent_users: int = 10,
        requests_per_user: int = 50,
        duration_seconds: Optional[int] = None
    ) -> LoadTestResult:
        """
        Perform load testing with concurrent users.
        
        Args:
            tool_name: Tool to test
            arguments: Tool arguments
            concurrent_users: Number of concurrent users
            requests_per_user: Requests per user
            duration_seconds: Test duration (overrides requests_per_user)
            
        Returns:
            Load test results
        """
        results = []
        errors = 0
        start_time = time.time()
        
        def user_simulation():
            """Simulate a user making requests."""
            user_errors = 0
            user_times = []
            
            if duration_seconds:
                end_time = start_time + duration_seconds
                while time.time() < end_time:
                    request_start = time.time()
                    try:
                        asyncio.run(self._execute_tool_safe(tool_name, arguments))
                    except Exception:
                        user_errors += 1
                    request_time = time.time() - request_start
                    user_times.append(request_time)
            else:
                for _ in range(requests_per_user):
                    request_start = time.time()
                    try:
                        asyncio.run(self._execute_tool_safe(tool_name, arguments))
                    except Exception:
                        user_errors += 1
                    request_time = time.time() - request_start
                    user_times.append(request_time)
            
            return user_times, user_errors
        
        # Measure initial system state
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Run load test with thread pool
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_simulation) for _ in range(concurrent_users)]
            
            # Collect results
            all_times = []
            total_errors = 0
            
            for future in futures:
                user_times, user_errors = future.result()
                all_times.extend(user_times)
                total_errors += user_errors
        
        test_duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        # Calculate metrics
        total_requests = len(all_times)
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        average_response_time = statistics.mean(all_times) if all_times else 0
        error_rate = (total_errors / (total_requests + total_errors)) * 100 if (total_requests + total_errors) > 0 else 0
        
        # Calculate throughput score (requests/sec weighted by success rate)
        success_rate = 100 - error_rate
        throughput_score = requests_per_second * (success_rate / 100)
        
        result = LoadTestResult(
            test_name=f"load_test_{tool_name}",
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            duration_seconds=test_duration,
            requests_per_second=requests_per_second,
            average_response_time=average_response_time,
            error_rate=error_rate,
            memory_usage_mb=final_memory - initial_memory,
            cpu_usage_percent=cpu_percent,
            throughput_score=throughput_score
        )
        
        return result
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """
        Run a comprehensive benchmark suite.
        
        Returns:
            Complete benchmark results
        """
        print("Running comprehensive benchmark suite...")
        
        # Tool execution benchmarks
        tool_results = []
        available_tools = list(self.server.tool_registry.get_registry_info()['tools'].keys())
        
        # Test a subset of tools to avoid long execution
        test_tools = available_tools[:5] if len(available_tools) > 5 else available_tools
        
        for tool_name in test_tools:
            print(f"Benchmarking tool: {tool_name}")
            try:
                # Use appropriate test arguments based on tool
                if tool_name == "list_detectors":
                    args = {}
                elif tool_name == "analyze_code":
                    args = {"path": ".", "config": {}}
                elif tool_name == "get_configuration_schema":
                    args = {}
                else:
                    args = {}
                
                result = self.benchmark_tool_execution(tool_name, args, iterations=50)
                tool_results.append(result)
            except Exception as e:
                print(f"Error benchmarking {tool_name}: {e}")
        
        # Middleware benchmark
        print("Benchmarking middleware chain...")
        middleware_result = self.benchmark_middleware_chain(iterations=500)
        
        # Load test
        print("Running load test...")
        if test_tools:
            load_result = self.load_test(
                test_tools[0], 
                {} if test_tools[0] in ["list_detectors", "get_configuration_schema"] else {"path": "."},
                concurrent_users=5,
                requests_per_user=20
            )
        else:
            load_result = None
        
        return {
            "tool_benchmarks": tool_results,
            "middleware_benchmark": middleware_result,
            "load_test": load_result,
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of all benchmark results."""
        if not self.results:
            return {"message": "No benchmark results available"}
        
        total_ops = sum(r.operations_per_second for r in self.results)
        avg_ops = total_ops / len(self.results)
        avg_success_rate = sum(r.success_rate for r in self.results) / len(self.results)
        
        return {
            "total_tests": len(self.results),
            "average_operations_per_second": avg_ops,
            "average_success_rate": avg_success_rate,
            "fastest_test": max(self.results, key=lambda r: r.operations_per_second).test_name,
            "slowest_test": min(self.results, key=lambda r: r.operations_per_second).test_name
        }
    
    def export_results(self, filepath: Path) -> None:
        """Export benchmark results to a file."""
        import json
        
        export_data = {
            "benchmark_results": [
                {
                    "test_name": r.test_name,
                    "iterations": r.iterations,
                    "total_time": r.total_time,
                    "average_time": r.average_time,
                    "operations_per_second": r.operations_per_second,
                    "success_rate": r.success_rate,
                    "memory_usage_mb": r.memory_usage_mb,
                    "cpu_usage_percent": r.cpu_usage_percent
                }
                for r in self.results
            ],
            "summary": self._generate_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Benchmark results exported to {filepath}")


def run_benchmark_suite():
    """Run the complete benchmark suite and display results."""
    print("=" * 60)
    print("Pythonium MCP Server Performance Benchmark")
    print("=" * 60)
    
    benchmark = PerformanceBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    
    # Tool benchmarks
    if results["tool_benchmarks"]:
        print("\nTool Execution Performance:")
        for result in results["tool_benchmarks"]:
            print(f"  {result.test_name}:")
            print(f"    Operations/sec: {result.operations_per_second:.2f}")
            print(f"    Avg time: {result.average_time*1000:.2f}ms")
            print(f"    Success rate: {result.success_rate:.1f}%")
    
    # Middleware benchmark
    if results["middleware_benchmark"]:
        result = results["middleware_benchmark"]
        print(f"\nMiddleware Chain Performance:")
        print(f"  Operations/sec: {result.operations_per_second:.2f}")
        print(f"  Avg time: {result.average_time*1000:.2f}ms")
        print(f"  Success rate: {result.success_rate:.1f}%")
    
    # Load test
    if results["load_test"]:
        result = results["load_test"]
        print(f"\nLoad Test Results:")
        print(f"  Concurrent users: {result.concurrent_users}")
        print(f"  Requests/sec: {result.requests_per_second:.2f}")
        print(f"  Avg response time: {result.average_response_time*1000:.2f}ms")
        print(f"  Error rate: {result.error_rate:.1f}%")
        print(f"  Throughput score: {result.throughput_score:.2f}")
    
    # Summary
    summary = results["summary"]
    print(f"\nSummary:")
    print(f"  Total tests: {summary.get('total_tests', 0)}")
    print(f"  Avg ops/sec: {summary.get('average_operations_per_second', 0):.2f}")
    print(f"  Avg success rate: {summary.get('average_success_rate', 0):.1f}%")
    
    # Export results
    export_path = Path("benchmark_results.json")
    benchmark.export_results(export_path)
    
    return results


if __name__ == "__main__":
    run_benchmark_suite()
