"""
Performance tests for the Pythonium MCP server.

These tests measure and verify the performance characteristics
of the MCP server under various load conditions.
"""

import time

import pytest


@pytest.mark.performance
@pytest.mark.slow
class TestServerPerformance:
    """Performance tests for the MCP server."""

    @pytest.fixture(autouse=True)
    def setup_test(self, tmp_path):
        """Set up test environment."""
        self.tmp_path = tmp_path


@pytest.mark.performance
class TestToolPerformance:
    """Performance tests for individual tools."""

    @pytest.fixture(autouse=True)
    def setup_test(self, tmp_path):
        """Set up test environment."""
        self.tmp_path = tmp_path


class PerformanceMetrics:
    """Helper class for collecting performance metrics."""

    def __init__(self):
        self.metrics = {}

    def start_timer(self, name: str):
        """Start a timer for a metric."""
        self.metrics[name] = {"start": time.time()}

    def end_timer(self, name: str):
        """End a timer for a metric."""
        if name in self.metrics:
            self.metrics[name]["end"] = time.time()
            self.metrics[name]["duration"] = (
                self.metrics[name]["end"] - self.metrics[name]["start"]
            )

    def get_duration(self, name: str) -> float:
        """Get the duration for a metric."""
        return self.metrics.get(name, {}).get("duration", 0.0)

    def assert_duration_under(self, name: str, max_duration: float):
        """Assert that a metric duration is under the specified limit."""
        duration = self.get_duration(name)
        assert duration < max_duration, (
            f"Performance metric '{name}' took {duration:.3f}s, "
            f"expected under {max_duration:.3f}s"
        )
