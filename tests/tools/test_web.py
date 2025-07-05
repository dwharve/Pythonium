"""Tests for web tools module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pythonium.common.base import Result
from pythonium.tools.std.web import HttpClientTool, WebSearchTool


class TestWebSearchTool:
    """Test WebSearchTool functionality."""

    def test_web_search_tool_initialization(self):
        """Test WebSearchTool initialization."""
        tool = WebSearchTool()
        assert tool is not None
        assert hasattr(tool, "_search_engines")

    async def test_web_search_tool_initialize(self):
        """Test tool initialization."""
        tool = WebSearchTool()
        await tool.initialize()
        # Should not raise exception

    async def test_web_search_tool_shutdown(self):
        """Test tool shutdown."""
        tool = WebSearchTool()
        await tool.shutdown()
        # Should not raise exception

    def test_web_search_tool_metadata(self):
        """Test tool metadata."""
        tool = WebSearchTool()
        metadata = tool.metadata
        assert metadata.name == "web_search"
        assert "search" in metadata.description.lower()
        assert len(metadata.parameters) > 0

    @patch("pythonium.tools.std.web.HttpService")
    async def test_web_search_execute_basic(self, mock_http_service):
        """Test basic web search execution."""
        tool = WebSearchTool()

        # Mock HTTP response
        mock_service = Mock()
        mock_http_service.return_value = mock_service
        mock_service.get.return_value = Result(
            success=True,
            data={
                "text": '<html><body><h3><a href="http://example.com">Test Result</a></h3><p>Test snippet</p></body></html>'
            },
            error=None,
        )

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"query": "test search", "search_engine": "duckduckgo", "max_results": 5},
            context,
        )

        # Should return a result
        assert isinstance(result, Result)

    def test_web_search_tool_search_engines(self):
        """Test available search engines."""
        tool = WebSearchTool()
        assert "duckduckgo" in tool._search_engines
        assert callable(tool._search_engines["duckduckgo"])


class TestHttpClientTool:
    """Test HttpClientTool functionality."""

    def test_http_client_tool_initialization(self):
        """Test HttpClientTool initialization."""
        tool = HttpClientTool()
        assert tool is not None

    async def test_http_client_tool_initialize(self):
        """Test tool initialization."""
        tool = HttpClientTool()
        await tool.initialize()
        # Should not raise exception

    async def test_http_client_tool_shutdown(self):
        """Test tool shutdown."""
        tool = HttpClientTool()
        await tool.shutdown()
        # Should not raise exception

    def test_http_client_tool_metadata(self):
        """Test tool metadata."""
        tool = HttpClientTool()
        metadata = tool.metadata
        assert metadata.name == "http_client"
        assert "http" in metadata.description.lower()
        assert len(metadata.parameters) > 0

    @patch("pythonium.tools.std.web.HttpService")
    async def test_http_client_execute_get(self, mock_http_service):
        """Test HTTP GET request execution."""
        tool = HttpClientTool()

        # Mock HTTP response
        mock_service = Mock()
        mock_http_service.return_value = mock_service
        mock_service.get.return_value = Result(
            success=True, data={"message": "success"}, error=None
        )

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"url": "https://example.com/api", "method": "GET"}, context
        )

        # Should return a result
        assert isinstance(result, Result)

    @patch("pythonium.tools.std.web.HttpService")
    async def test_http_client_execute_post(self, mock_http_service):
        """Test HTTP POST request execution."""
        tool = HttpClientTool()

        # Mock HTTP response
        mock_service = Mock()
        mock_http_service.return_value = mock_service
        mock_service.post.return_value = Result(
            success=True, data={"id": 123}, error=None
        )

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {
                "url": "https://example.com/api",
                "method": "POST",
                "data": {"name": "test"},
            },
            context,
        )

        # Should return a result
        assert isinstance(result, Result)

    def test_http_client_supported_methods(self):
        """Test supported HTTP methods."""
        tool = HttpClientTool()
        metadata = tool.metadata

        # Find method parameter
        method_param = None
        for param in metadata.parameters:
            if param.name == "method":
                method_param = param
                break

        if (
            method_param
            and hasattr(method_param, "allowed_values")
            and method_param.allowed_values is not None
        ):
            assert "GET" in method_param.allowed_values
            assert "POST" in method_param.allowed_values
        else:
            # If allowed_values is not defined, just verify the parameter exists
            assert method_param is not None
            assert method_param.description is not None


class TestWebToolsIntegration:
    """Test integration between web tools."""

    def test_both_tools_can_be_instantiated(self):
        """Test that both web tools can be created."""
        search_tool = WebSearchTool()
        http_tool = HttpClientTool()

        assert search_tool is not None
        assert http_tool is not None
        assert search_tool.metadata.name != http_tool.metadata.name
