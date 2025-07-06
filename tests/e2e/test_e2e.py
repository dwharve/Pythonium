"""
End-to-end tests for the Pythonium MCP server.

These tests verify the complete functionality of the MCP server
from a client perspective, testing the full request-response cycle.
"""

import pytest


@pytest.mark.e2e
class TestMCPServerE2E:
    """End-to-end tests for the MCP server."""

    @pytest.fixture(autouse=True)
    def setup_test(self, tmp_path):
        """Set up test environment."""
        self.tmp_path = tmp_path


@pytest.mark.e2e
@pytest.mark.slow
class TestMCPServerPerformance:
    """Performance tests for the MCP server."""

    @pytest.fixture(autouse=True)
    def setup_test(self, tmp_path):
        """Set up test environment."""
        self.tmp_path = tmp_path
