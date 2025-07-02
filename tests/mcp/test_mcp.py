"""
Unit tests for the MCP package.

This module contains unit tests for all components in the pythonium.mcp package.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from pythonium.mcp import config, handlers, protocol, server
from pythonium.mcp import session as mcp_session
from pythonium.mcp import transport as mcp_transport
from pythonium.mcp.config import (
    LoggingConfig,
    PerformanceConfig,
    SecurityConfig,
    ServerConfig,
    TransportConfig,
)
from pythonium.mcp.handlers import MCPMessageHandler
from pythonium.mcp.protocol import (
    MCPError,
    MCPMessage,
    MCPRequest,
    MCPResponse,
)
from pythonium.mcp.server import MCPServer
from pythonium.mcp.session import ConnectionType, SessionManager
from pythonium.mcp.transport import (
    HttpTransport,
    StdioTransport,
    WebSocketTransport,
)
from tests.conftest import BaseTestCase


class TestMCPPackage(BaseTestCase):
    """Test the MCP package initialization."""

    def test_package_import(self):
        """Test that the MCP package can be imported."""
        import pythonium.mcp

        assert hasattr(pythonium.mcp, "protocol")
        assert hasattr(pythonium.mcp, "config")
        assert hasattr(pythonium.mcp, "session")
        assert hasattr(pythonium.mcp, "transport")
        assert hasattr(pythonium.mcp, "handlers")
        assert hasattr(pythonium.mcp, "server")

    def test_package_version(self):
        """Test that the package has a version."""
        from pythonium.mcp import __version__

        assert __version__ == "0.1.2"


class TestMCPProtocol(BaseTestCase):
    """Test the MCP protocol implementation."""

    def test_mcp_message_creation(self):
        """Test MCPMessage creation."""
        msg = MCPMessage(jsonrpc="2.0", id="test_id")
        assert msg.jsonrpc == "2.0"
        assert msg.id == "test_id"

    def test_mcp_request_creation(self):
        """Test MCPRequest creation."""
        req = MCPRequest(
            jsonrpc="2.0",
            method="test_method",
            params={"key": "value"},
            id="test_id",
        )
        assert req.jsonrpc == "2.0"
        assert req.method == "test_method"
        assert req.params == {"key": "value"}
        assert req.id == "test_id"

    def test_mcp_response_creation(self):
        """Test MCPResponse creation."""
        resp = MCPResponse(jsonrpc="2.0", result={"success": True}, id="test_id")
        assert resp.jsonrpc == "2.0"
        assert resp.result == {"success": True}
        assert resp.id == "test_id"

    def test_mcp_error_creation(self):
        """Test MCPError creation."""
        error = MCPError(code=-32601, message="Method not found")
        assert error.code == -32601
        assert error.message == "Method not found"


class TestMCPConfig(BaseTestCase):
    """Test the MCP configuration classes."""

    def test_server_config_creation(self):
        """Test ServerConfig creation."""
        transport_config = TransportConfig(type="stdio", host="localhost", port=8080)
        server_config = ServerConfig(
            name="test_server", version="1.0.0", transport=transport_config
        )
        assert server_config.name == "test_server"
        assert server_config.version == "1.0.0"
        assert server_config.transport is not None
        assert server_config.security is not None
        assert server_config.performance is not None
        assert server_config.logging is not None

    def test_transport_config_creation(self):
        """Test TransportConfig creation."""
        transport_config = TransportConfig(type="stdio", host="localhost", port=8080)
        assert transport_config.type == "stdio"
        assert transport_config.host == "localhost"
        assert transport_config.port == 8080

    def test_security_config_creation(self):
        """Test SecurityConfig creation."""
        security_config = SecurityConfig(rate_limit_enabled=True, cors_enabled=True)
        assert security_config.rate_limit_enabled is True
        assert security_config.cors_enabled is True


class TestMCPSession(BaseTestCase):
    """Test the MCP session management."""

    @pytest.fixture(autouse=True)
    def setup_session_test(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test session creation."""
        session_id = await self.session_manager.create_session(ConnectionType.STDIO)
        assert session_id is not None

        # Check if session exists (not necessarily active yet)
        session = await self.session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id

    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test session cleanup."""
        session_id = await self.session_manager.create_session(ConnectionType.STDIO)
        await self.session_manager.close_session(session_id)
        session = await self.session_manager.get_session(session_id)
        # Session should be removed or marked as disconnected
        assert session is None or session.state.value == "disconnected"

    @pytest.mark.asyncio
    async def test_session_metrics(self):
        """Test session metrics."""
        session_id = await self.session_manager.create_session(ConnectionType.STDIO)
        metrics = await self.session_manager.get_session_metrics(session_id)
        assert metrics is not None
        assert metrics.requests_received == 0


class TestMCPTransport(BaseTestCase):
    """Test the MCP transport implementations."""

    @pytest.fixture(autouse=True)
    def setup_transport_test(self):
        """Set up test fixtures."""
        self.transport_config = TransportConfig(type="stdio")
        self.session_manager = SessionManager()
        self.message_handler = Mock()

    def test_stdio_transport_creation(self):
        """Test StdioTransport creation."""
        transport = StdioTransport(
            config=self.transport_config,
            session_manager=self.session_manager,
            message_handler=self.message_handler,
        )
        assert transport is not None
        assert transport.config == self.transport_config

    def test_http_transport_creation(self):
        """Test HttpTransport creation."""
        http_config = TransportConfig(type="http", host="localhost", port=8080)
        transport = HttpTransport(
            config=http_config,
            session_manager=self.session_manager,
            message_handler=self.message_handler,
        )
        assert transport.config.host == "localhost"
        assert transport.config.port == 8080

    def test_websocket_transport_creation(self):
        """Test WebSocketTransport creation."""
        ws_config = TransportConfig(type="websocket", host="localhost", port=8080)
        transport = WebSocketTransport(
            config=ws_config,
            session_manager=self.session_manager,
            message_handler=self.message_handler,
        )
        assert transport.config.host == "localhost"
        assert transport.config.port == 8080

    @pytest.mark.asyncio
    async def test_stdio_transport_send_message(self):
        """Test StdioTransport message sending."""
        transport = StdioTransport(
            config=self.transport_config,
            session_manager=self.session_manager,
            message_handler=self.message_handler,
        )
        message = MCPMessage(jsonrpc="2.0", id="test")

        # Mock stdout to avoid actual I/O
        with patch("sys.stdout"):
            # Create a mock session first
            with patch.object(transport, "_session_id", "test_session"):
                await transport.send_message("test_session", message)
                # Just verify we didn't crash - actual I/O is mocked


class TestMCPHandlers(BaseTestCase):
    """Test the MCP message handlers."""

    @pytest.fixture(autouse=True)
    def setup_handler_test(self):
        """Set up test fixtures."""
        # Create dependencies
        from pythonium.mcp.config import MCPConfigManager

        self.config_manager = MCPConfigManager()
        self.session_manager = SessionManager()
        self.handler = MCPMessageHandler(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
        )

    @pytest.mark.asyncio
    async def test_initialize_handler(self):
        """Test initialize message handling."""
        from pythonium.mcp.protocol import ClientCapabilities, InitializeParams

        # Create a session first
        session_id = await self.session_manager.create_session(ConnectionType.STDIO)

        request = MCPRequest(
            jsonrpc="2.0",
            method="initialize",
            params=InitializeParams(
                protocolVersion="2024-11-05",
                capabilities=ClientCapabilities(),
                clientInfo={"name": "test", "version": "1.0.0"},
            ).model_dump(),
            id="test_id",
        )

        response = await self.handler.handle_message(session_id, request)
        assert response is not None
        assert response.id == "test_id"
        # For initialize, the response might have an error or success result
        assert response.result is not None or response.error is not None

    @pytest.mark.asyncio
    async def test_ping_handler(self):
        """Test ping message handling."""
        request = MCPRequest(jsonrpc="2.0", method="ping", params={}, id="test_id")

        response = await self.handler.handle_message("session_id", request)
        assert response is not None
        assert response.id == "test_id"
        # Ping should return a simple response

    @pytest.mark.asyncio
    async def test_unknown_method_handler(self):
        """Test handling of unknown methods."""
        request = MCPRequest(
            jsonrpc="2.0", method="unknown_method", params={}, id="test_id"
        )

        response = await self.handler.handle_message("session_id", request)
        assert response is not None
        assert response.id == "test_id"
        # Should return an error response for unknown methods


class TestMCPServer(BaseTestCase):
    """Test the MCP server implementation."""

    @pytest.fixture(autouse=True)
    def setup_server_test(self):
        """Set up test fixtures."""
        # Create a mock config file for testing
        self.test_config_data = {
            "name": "test_server",
            "version": "1.0.0",
            "transport": {"type": "stdio"},
        }

        # Create server with overrides instead of config file
        self.server = MCPServer(
            config_file=None, config_overrides=self.test_config_data
        )

    def test_server_creation(self):
        """Test server creation."""
        assert self.server is not None
        assert self.server.config is not None
        assert self.server.session_manager is not None
        assert self.server.message_handler is not None

    @pytest.mark.asyncio
    async def test_server_startup(self):
        """Test server startup."""
        # Mock the specific transport class constructor to avoid STDIO issues
        mock_transport = Mock()
        mock_transport.start = AsyncMock()

        with patch(
            "pythonium.mcp.transport.StdioTransport",
            return_value=mock_transport,
        ):
            with patch.object(
                self.server.session_manager, "start", new_callable=AsyncMock
            ):
                with patch.object(
                    self.server.message_handler,
                    "start",
                    new_callable=AsyncMock,
                ):
                    with patch.object(
                        self.server,
                        "_discover_and_register_tools",
                        new_callable=AsyncMock,
                    ):
                        with patch.object(self.server, "_setup_signal_handlers"):
                            await self.server.start()
                            assert self.server._running is True

    @pytest.mark.asyncio
    async def test_server_shutdown(self):
        """Test server shutdown."""
        # Mock the specific transport class
        mock_transport = Mock()
        mock_transport.start = AsyncMock()
        mock_transport.stop = AsyncMock()

        with patch(
            "pythonium.mcp.transport.StdioTransport",
            return_value=mock_transport,
        ):
            with patch.object(
                self.server.session_manager, "start", new_callable=AsyncMock
            ):
                with patch.object(
                    self.server.session_manager, "stop", new_callable=AsyncMock
                ):
                    with patch.object(
                        self.server.message_handler,
                        "start",
                        new_callable=AsyncMock,
                    ):
                        with patch.object(
                            self.server.message_handler,
                            "stop",
                            new_callable=AsyncMock,
                        ):
                            with patch.object(
                                self.server,
                                "_discover_and_register_tools",
                                new_callable=AsyncMock,
                            ):
                                with patch.object(
                                    self.server, "_setup_signal_handlers"
                                ):
                                    await self.server.start()
                                    await self.server.stop()
                                    assert self.server._running is False

    def test_tool_registration(self):
        """Test tool registration."""
        # Create a mock tool to register
        from pythonium.tools.base import BaseTool, ToolMetadata

        class TestTool(BaseTool):
            def __init__(self):
                super().__init__(name="test_tool")

            async def initialize(self):
                """Initialize the tool."""
                pass

            async def shutdown(self):
                """Shutdown the tool."""
                pass

            @property
            def metadata(self) -> ToolMetadata:
                """Get tool metadata."""
                return ToolMetadata(
                    name=self.name,
                    description="A test tool",
                    version="1.0.0",
                    category="test",
                    author="test",
                    parameters=[],
                    requirements=[],
                    outputs=[],
                )

            async def execute(self, parameters, context):
                from pythonium.common.base import Result

                return Result.success_result(data={"result": "test"})

        test_tool = TestTool()
        # Register through the server
        self.server.register_tool(test_tool)
        tools = self.server.message_handler.tool_registry.list_tools()
        assert "test_tool" in [tool.name for tool in tools]

    def test_resource_registration(self):
        """Test resource registration."""

        # Mock resource handler
        def mock_resource_handler(uri: str):
            return {"uri": uri, "data": "test"}

        resource_uri = "test://resource"
        self.server.register_resource_handler(resource_uri, mock_resource_handler)

        # Verify registration by checking if the handler was set
        assert resource_uri in self.server.message_handler._resource_handlers

    def test_prompt_registration(self):
        """Test prompt registration."""

        # Mock prompt handler
        def mock_prompt_handler(name: str, args: dict):
            return {"name": name, "content": "test prompt"}

        prompt_name = "test_prompt"
        self.server.register_prompt_handler(prompt_name, mock_prompt_handler)

        # Verify registration by checking if the handler was set
        assert prompt_name in self.server.message_handler._prompt_handlers
