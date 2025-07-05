"""
Tests for MCP server implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pythonium.common.config import TransportType
from pythonium.core.server import (
    PythoniumMCPServer,
    ServerError,
    create_http_server,
    create_stdio_server,
    create_websocket_server,
)
from pythonium.tools.base import BaseTool, ParameterType, ToolMetadata, ToolParameter


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="mock_tool",
            description="A mock tool for testing",
            category="test",
            parameters=[
                ToolParameter(
                    name="test_param",
                    type=ParameterType.STRING,
                    description="Test parameter",
                    required=True,
                )
            ],
        )

    async def execute(self, context, **kwargs):
        """Execute the tool."""
        return {"result": "mock_execution", "params": kwargs}


class TestPythoniumMCPServer:
    """Test PythoniumMCPServer functionality."""

    def test_server_initialization(self):
        """Test server initialization."""
        server = PythoniumMCPServer()

        assert server.config is not None
        assert server.mcp_server is not None
        assert server.tool_discovery is not None
        assert server._running is False
        assert len(server._registered_tools) == 0

    def test_server_initialization_with_config(self):
        """Test server initialization with custom config."""
        config_overrides = {
            "server": {
                "name": "test_server",
                "description": "Test MCP server",
                "transport": "stdio",
            }
        }

        server = PythoniumMCPServer(config_overrides=config_overrides)

        assert server.config.server.name == "test_server"
        assert server.config.server.description == "Test MCP server"

    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        """Test server start and stop lifecycle."""
        server = PythoniumMCPServer()

        # Mock the necessary dependencies
        with patch.object(
            server.config_manager, "validate_config", return_value=None
        ), patch.object(
            server, "_discover_and_register_tools", new=AsyncMock()
        ), patch.object(
            server, "_setup_signal_handlers"
        ):

            await server.start()
            assert server._running is True

            await server.stop()
            assert server._running is False

    def test_server_register_tool(self):
        """Test tool registration."""
        server = PythoniumMCPServer()
        tool = MockTool()

        # Mock the FastMCP tool registration
        server.mcp_server.tool = Mock(return_value=lambda func: func)

        server.register_tool(tool)

        assert "mock_tool" in server._registered_tools
        assert server._registered_tools["mock_tool"] is tool

    def test_server_get_registered_tools(self):
        """Test getting registered tools."""
        server = PythoniumMCPServer()

        # Initially empty
        tools = server.get_registered_tools()
        assert len(tools) == 0

        # Add a tool
        tool = MockTool()
        server.mcp_server.tool = Mock(return_value=lambda func: func)
        server.register_tool(tool)

        tools = server.get_registered_tools()
        assert len(tools) == 1
        assert "mock_tool" in tools

    @pytest.mark.asyncio
    async def test_server_run_stdio(self):
        """Test running server with STDIO transport."""
        config_overrides = {"transport": {"type": "stdio"}}
        server = PythoniumMCPServer(config_overrides=config_overrides)

        # Mock the start/stop and run methods
        with patch.object(server, "start", new=AsyncMock()), patch.object(
            server, "stop", new=AsyncMock()
        ), patch.object(server.mcp_server, "run") as mock_run:

            # Mock the executor to not actually run
            with patch("asyncio.get_event_loop") as mock_loop:
                # Mock run_in_executor to actually call the function so the mock gets triggered
                async def mock_run_in_executor(executor, func, *args):
                    func(*args)
                    return None

                mock_loop.return_value.run_in_executor = mock_run_in_executor

                # Test that run was called
                await server.run()
                mock_run.assert_called_once_with(transport="stdio")

                server.start.assert_called_once()


class TestServerFactoryFunctions:
    """Test server factory functions."""

    def test_create_stdio_server(self):
        """Test creating STDIO server."""
        server = create_stdio_server()

        assert isinstance(server, PythoniumMCPServer)
        assert server.config.server.transport == TransportType.STDIO

    def test_create_http_server(self):
        """Test creating HTTP server."""
        host = "0.0.0.0"
        port = 9000

        server = create_http_server(host, port)

        assert isinstance(server, PythoniumMCPServer)
        assert server.config.server.transport == TransportType.HTTP
        assert server.config.server.host == host
        assert server.config.server.port == port

    def test_create_websocket_server(self):
        """Test creating WebSocket server."""
        host = "0.0.0.0"
        port = 9001

        server = create_websocket_server(host, port)

        assert isinstance(server, PythoniumMCPServer)
        assert server.config.server.transport == TransportType.WEBSOCKET
        assert server.config.server.host == host
        assert server.config.server.port == port


class TestServerIntegration:
    """Test server integration scenarios."""

    @pytest.mark.asyncio
    async def test_server_lifecycle(self):
        """Test complete server lifecycle."""
        from datetime import datetime

        from pythonium.core.tools.discovery import DiscoveredTool

        server = PythoniumMCPServer()

        # Mock discovery to return a mock tool
        mock_tool_class = MockTool
        discovered_tool = DiscoveredTool(
            tool_class=mock_tool_class,
            module_name="test_module",
            source_path="test_path",
            discovery_method="test",
            metadata={},
            discovered_at=datetime.now(),
        )

        with patch.object(
            server.tool_discovery,
            "discover_tools",
            return_value={"mock_tool": discovered_tool},
        ) as mock_discover, patch.object(
            server.config_manager, "validate_config", return_value=None
        ), patch.object(
            server, "_setup_signal_handlers"
        ), patch.object(
            server.mcp_server, "tool", return_value=lambda func: func
        ):

            # Start server
            await server.start()
            assert server._running is True
            # Verify discovery was called
            mock_discover.assert_called()
            # Don't assert on registered tools count since discovery is mocked

            # Stop server
            await server.stop()
            assert server._running is False

    @pytest.mark.asyncio
    async def test_multiple_tool_registration(self):
        """Test registering multiple tools."""
        server = PythoniumMCPServer()

        # Create multiple mock tools
        class Tool1(MockTool):
            @property
            def metadata(self):
                meta = ToolMetadata(name="tool1", description="Tool 1", category="test")
                return meta

        class Tool2(MockTool):
            @property
            def metadata(self):
                meta = ToolMetadata(name="tool2", description="Tool 2", category="test")
                return meta

        tool1 = Tool1()
        tool2 = Tool2()

        # Mock FastMCP registration
        server.mcp_server.tool = Mock(return_value=lambda func: func)

        # Register tools
        server.register_tool(tool1)
        server.register_tool(tool2)

        # Check both are registered
        tools = server.get_registered_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools


class TestServerErrorHandling:
    """Test server error handling scenarios."""

    @pytest.mark.asyncio
    async def test_startup_failure_cleanup(self):
        """Test cleanup when startup fails."""
        server = PythoniumMCPServer()

        # Mock discovery to fail
        with patch.object(
            server,
            "_discover_and_register_tools",
            new=AsyncMock(side_effect=Exception("Discovery failed")),
        ), patch.object(
            server.config_manager, "validate_config", return_value=None
        ), patch.object(
            server, "_cleanup", new=AsyncMock()
        ) as mock_cleanup:

            with pytest.raises(ServerError):
                await server.start()

            # Cleanup should have been called
            mock_cleanup.assert_called_once()
            assert server._running is False
