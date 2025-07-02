"""
Performance tests for MCP server.

Tests server performance under various loads, concurrent requests,
memory usage, and response times.
"""

import asyncio
import statistics
import time
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest

from pythonium.mcp.config import MCPConfigManager
from pythonium.mcp.protocol import MCPRequest, MCPResponse
from pythonium.mcp.server import MCPServer


class TestMCPServerPerformance:
    """Performance tests for MCP server."""

    @pytest.fixture
    def performance_config(self):
        """Create config optimized for performance testing."""
        config_overrides = {
            "server": {"name": "perf-test-server", "version": "1.0.0"},
            "transport": {"type": "stdio", "timeout": 60},
            "performance": {
                "enabled": True,
                "max_concurrent_requests": 100,
                "request_timeout": 30,
            },
            "security": {"enabled": False},  # Disable for performance testing
        }
        return config_overrides

    @pytest.fixture
    def perf_server(self, performance_config):
        """Create server optimized for performance testing."""
        with patch("pythonium.mcp.server.PluginManager"), patch(
            "pythonium.mcp.server.SecurityManager"
        ), patch("pythonium.mcp.server.ToolDiscoveryManager"):

            server = MCPServer(config_overrides=performance_config)
            return server

    @pytest.mark.asyncio
    async def test_request_response_latency(self, perf_server):
        """Test request-response latency."""
        latencies = []

        # Test ping requests for baseline latency
        for i in range(100):
            request = MCPRequest(id=f"latency-test-{i}", method="ping", params={})

            start_time = time.perf_counter()
            response = await perf_server.message_handler.handle_message(
                "test-session", request
            )
            end_time = time.perf_counter()

            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)

            assert response.id == f"latency-test-{i}"
            assert response.error is None

        # Analyze latency statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)

        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"95th percentile latency: {p95_latency:.2f}ms")
        print(f"Maximum latency: {max_latency:.2f}ms")

        # Performance assertions
        assert avg_latency < 10.0  # Average should be under 10ms
        assert p95_latency < 50.0  # 95% of requests under 50ms
        assert max_latency < 100.0  # No request over 100ms

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, perf_server):
        """Test concurrent request handling performance."""
        num_concurrent = 50

        # Create concurrent requests
        requests = []
        for i in range(num_concurrent):
            request = MCPRequest(id=f"concurrent-{i}", method="ping", params={})
            requests.append(request)

        start_time = time.perf_counter()

        # Execute all requests concurrently
        tasks = [
            perf_server.message_handler.handle_message("test-session", req)
            for req in requests
        ]
        responses = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify all requests completed successfully
        assert len(responses) == num_concurrent
        for i, response in enumerate(responses):
            assert response.id == f"concurrent-{i}"
            assert response.error is None

        # Performance metrics
        requests_per_second = num_concurrent / total_time
        avg_time_per_request = total_time / num_concurrent * 1000

        print(f"Concurrent requests: {num_concurrent}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Requests per second: {requests_per_second:.2f}")
        print(f"Average time per request: {avg_time_per_request:.2f}ms")

        # Performance assertions
        assert requests_per_second > 100  # Should handle >100 RPS
        assert avg_time_per_request < 20  # Average time under 20ms

    @pytest.mark.asyncio
    async def test_tool_execution_performance(self, perf_server):
        """Test tool execution performance."""
        # Mock a fast tool
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = {"result": "success"}

        with patch.object(
            perf_server.message_handler.execution_pipeline, "execute_single"
        ) as mock_execute, patch.object(
            perf_server.message_handler.tool_registry, "has_tool"
        ) as mock_has_tool:

            mock_has_tool.return_value = True
            mock_execute.return_value = mock_result

            execution_times = []

            # Execute tool multiple times
            for i in range(50):
                request = MCPRequest(
                    id=f"tool-perf-{i}",
                    method="tools/call",
                    params={"name": "fast_tool", "arguments": {"input": f"test-{i}"}},
                )

                start_time = time.perf_counter()
                response = await perf_server.message_handler.handle_message(
                    "test-session", request
                )
                end_time = time.perf_counter()

                execution_time = (end_time - start_time) * 1000
                execution_times.append(execution_time)

                assert response.error is None

            # Analyze execution time statistics
            avg_execution = statistics.mean(execution_times)
            p95_execution = statistics.quantiles(execution_times, n=20)[18]

            print(f"Average tool execution time: {avg_execution:.2f}ms")
            print(f"95th percentile execution time: {p95_execution:.2f}ms")

            # Tool execution should be fast
            assert avg_execution < 15.0  # Under 15ms average
            assert p95_execution < 30.0  # 95% under 30ms

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, perf_server):
        """Test memory usage under sustained load."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Sustained load test
        num_rounds = 10
        requests_per_round = 20

        memory_samples = [initial_memory]

        for round_num in range(num_rounds):
            # Create batch of requests
            requests = []
            for i in range(requests_per_round):
                request = MCPRequest(
                    id=f"memory-test-{round_num}-{i}",
                    method="ping",
                    params={"data": "x" * 1000},  # Add some data
                )
                requests.append(request)

            # Execute batch
            tasks = [
                perf_server.message_handler.handle_message("test-session", req)
                for req in requests
            ]
            responses = await asyncio.gather(*tasks)

            # Verify responses
            assert len(responses) == requests_per_round

            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)

            # Small delay to allow garbage collection
            await asyncio.sleep(0.1)

        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory
        peak_memory = max(memory_samples)

        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Memory growth: {memory_growth:.2f}MB")
        print(f"Peak memory: {peak_memory:.2f}MB")

        # Memory growth should be reasonable
        assert memory_growth < 50.0  # Less than 50MB growth
        assert peak_memory < initial_memory + 100.0  # Peak under +100MB

    @pytest.mark.asyncio
    async def test_high_frequency_requests(self, perf_server):
        """Test handling of high-frequency requests."""
        duration = 5.0  # Test for 5 seconds
        start_time = time.perf_counter()
        request_count = 0
        error_count = 0

        while time.perf_counter() - start_time < duration:
            request = MCPRequest(
                id=f"freq-test-{request_count}", method="ping", params={}
            )

            try:
                response = await perf_server.message_handler.handle_message(
                    "test-session", request
                )
                if response.error:
                    error_count += 1
                request_count += 1
            except Exception:
                error_count += 1
                request_count += 1

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.001)

        end_time = time.perf_counter()
        actual_duration = end_time - start_time
        requests_per_second = request_count / actual_duration
        error_rate = error_count / request_count if request_count > 0 else 0

        print(f"Duration: {actual_duration:.2f}s")
        print(f"Total requests: {request_count}")
        print(f"Requests per second: {requests_per_second:.2f}")
        print(f"Error rate: {error_rate:.2%}")

        # Performance expectations
        assert requests_per_second > 200  # Should handle >200 RPS
        assert error_rate < 0.01  # Error rate under 1%

    @pytest.mark.asyncio
    async def test_large_message_handling(self, perf_server):
        """Test handling of large messages."""
        sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB

        for size in sizes:
            large_data = "x" * size

            request = MCPRequest(
                id=f"large-msg-{size}", method="ping", params={"data": large_data}
            )

            start_time = time.perf_counter()
            response = await perf_server.message_handler.handle_message(
                "test-session", request
            )
            end_time = time.perf_counter()

            processing_time = (end_time - start_time) * 1000

            print(
                f"Message size: {size} bytes, Processing time: {processing_time:.2f}ms"
            )

            assert response.error is None
            assert processing_time < 100  # Should process under 100ms

    @pytest.mark.asyncio
    async def test_session_scaling(self, perf_server):
        """Test server performance with multiple sessions."""
        num_sessions = 10
        requests_per_session = 20

        # Create multiple mock sessions
        sessions = []
        for i in range(num_sessions):
            session_id = f"perf-session-{i}"
            sessions.append(session_id)

        start_time = time.perf_counter()

        # Execute requests from all sessions concurrently
        all_tasks = []
        for session_idx, session_id in enumerate(sessions):
            session_tasks = []
            for req_idx in range(requests_per_session):
                request = MCPRequest(
                    id=f"session-{session_idx}-req-{req_idx}",
                    method="ping",
                    params={"session": session_id},
                )
                task = perf_server.message_handler.handle_message(
                    "test-session", request
                )
                session_tasks.append(task)

            all_tasks.extend(session_tasks)

        # Wait for all requests to complete
        responses = await asyncio.gather(*all_tasks)

        end_time = time.perf_counter()
        total_time = end_time - start_time
        total_requests = len(responses)

        # Verify all requests succeeded
        success_count = sum(1 for r in responses if r.error is None)
        success_rate = success_count / total_requests

        print(f"Sessions: {num_sessions}")
        print(f"Total requests: {total_requests}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Requests per second: {total_requests / total_time:.2f}")

        # Performance expectations
        assert success_rate > 0.99  # >99% success rate
        assert total_requests / total_time > 50  # >50 RPS with multiple sessions

    @pytest.mark.asyncio
    async def test_resource_cleanup_performance(self, perf_server):
        """Test resource cleanup performance."""
        # Create many short-lived resources
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        for batch in range(10):
            # Create batch of requests with temporary data
            requests = []
            for i in range(50):
                request = MCPRequest(
                    id=f"cleanup-{batch}-{i}",
                    method="ping",
                    params={"temp_data": "x" * 10000},  # 10KB per request
                )
                requests.append(request)

            # Process batch
            tasks = [
                perf_server.message_handler.handle_message("test-session", req)
                for req in requests
            ]
            await asyncio.gather(*tasks)

            # Force garbage collection
            import gc

            gc.collect()

            # Check memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_growth = current_memory - start_memory

            # Memory growth should be bounded
            assert memory_growth < 100  # Less than 100MB growth per batch

        # Final cleanup check
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_growth = final_memory - start_memory

        print(f"Start memory: {start_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Total growth: {total_growth:.2f}MB")

        # Should not leak significant memory
        assert total_growth < 50  # Less than 50MB total growth
