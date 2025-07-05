"""Tests for web-related tools."""

import pytest

from pythonium.tools.base import ToolContext
from pythonium.tools.std.web import HttpClientTool, WebSearchTool


class TestWebSearchTool:
    """Test cases for WebSearchTool."""

    @pytest.fixture
    def tool(self):
        """Create a WebSearchTool instance."""
        return WebSearchTool()

    @pytest.fixture
    def context(self):
        """Create a mock ToolContext."""
        return ToolContext(
            tool_name="web_search",
            execution_id="test_exec_123",
            session_id="test_session_456",
            user_id="test_user",
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_tool_initialization(self, tool):
        """Test tool initialization."""
        await tool.initialize()
        assert tool is not None
        assert hasattr(tool, "_search_engines")
        assert "duckduckgo" in tool._search_engines

    @pytest.mark.asyncio
    async def test_tool_shutdown(self, tool):
        """Test tool shutdown."""
        await tool.shutdown()
        # Should not raise any exceptions

    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = tool.metadata
        assert metadata.name == "web_search"
        assert "search" in metadata.description.lower()
        assert metadata.category == "network"
        assert "search" in metadata.tags
        assert len(metadata.parameters) > 0


class TestHttpClientTool:
    """Test cases for HttpClientTool."""

    @pytest.fixture
    def tool(self):
        """Create an HttpClientTool instance."""
        return HttpClientTool()

    @pytest.fixture
    def context(self):
        """Create a mock ToolContext."""
        return ToolContext(
            tool_name="http_client",
            execution_id="test_exec_123",
            session_id="test_session_456",
            user_id="test_user",
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_tool_initialization(self, tool):
        """Test tool initialization."""
        await tool.initialize()
        assert tool is not None
        assert hasattr(tool, "_default_headers")
        assert "User-Agent" in tool._default_headers

    @pytest.mark.asyncio
    async def test_tool_shutdown(self, tool):
        """Test tool shutdown."""
        await tool.shutdown()
        # Should not raise any exceptions

    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = tool.metadata
        assert metadata.name == "http_client"
        assert "http" in metadata.description.lower()
        assert metadata.category == "network"
        assert "http" in metadata.tags
        assert len(metadata.parameters) > 0
