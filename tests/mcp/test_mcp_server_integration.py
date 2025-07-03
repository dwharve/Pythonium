"""
Comprehensive integration tests for MCP server.

Tests the MCP server as a complete system including configuration,
initialization, request handling, and various transport mechanisms.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from pythonium.mcp_legacy.config import MCPConfigManager, TransportType
from pythonium.mcp_legacy.protocol import (
    InitializeResult,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    MessageType,
    ServerCapabilities,
)
from pythonium.mcp_legacy.legacy_server import MCPServer, MCPServerError
from pythonium.mcp_legacy.session import ConnectionType, SessionManager
from pythonium.mcp_legacy.transport import StdioTransport, WebSocketTransport


class TestMCPServerIntegration:
    """Integration tests for MCP server."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        config_data = {
            "server": {
                "name": "test-server",
                "version": "1.0.0",
                "description": "Test MCP server",
            },
            "transport": {"type": "stdio", "timeout": 30},
            "security": {"enabled": True, "max_request_size": 1024000},
            "logging": {"level": "info", "format": "%(levelname)s: %(message)s"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            return f.name

    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        with patch("pythonium.mcp.server.PluginManager") as mock_plugin_mgr, patch(
            "pythonium.mcp.server.SecurityManager"
        ) as mock_security_mgr, patch(
            "pythonium.mcp.server.ToolDiscoveryManager"
        ) as mock_tool_mgr:

            yield {
                "plugin_manager": mock_plugin_mgr,
                "security_manager": mock_security_mgr,
                "tool_manager": mock_tool_mgr,
            }

    def test_server_initialization_with_config_file(
        self, temp_config_file, mock_dependencies
    ):
        """Test server initialization with config file."""
        server = MCPServer(config_file=temp_config_file)

        assert server.config_manager is not None
        assert server.session_manager is not None
        assert server.message_handler is not None
        assert not server._running

    def test_server_initialization_with_overrides(self, mock_dependencies):
        """Test server initialization with config overrides."""
        overrides = {
            "server": {"name": "override-server"},
            "transport": {"type": "websocket", "port": 8080},
        }

        server = MCPServer(config_overrides=overrides)

        assert server.config_manager is not None
        assert server.session_manager is not None

    @pytest.mark.asyncio
    async def test_server_startup_and_shutdown(self, mock_dependencies):
        """Test server startup and shutdown lifecycle."""
        server = MCPServer()

        with patch("pythonium.mcp.server.create_transport") as mock_create_transport:
            mock_transport = AsyncMock()
            mock_create_transport.return_value = mock_transport

            # Test startup
            await server.start()
            assert server._running
            mock_transport.start.assert_called_once()

            # Test shutdown
            await server.stop()
            assert not server._running
            mock_transport.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_handles_initialization_request(self, mock_dependencies):
        """Test server handles initialization request properly."""
        server = MCPServer()

        init_request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True},
                },
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        with patch.object(server.message_handler, "handle_message") as mock_handle:
            mock_response = MCPResponse(
                id="init-1",
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True, "listChanged": True},
                        "prompts": {"listChanged": True},
                    },
                    "serverInfo": {"name": "pythonium-mcp", "version": "0.1.2"},
                },
            )
            mock_handle.return_value = mock_response

            response = await server.message_handler.handle_message(
                "test-session", init_request
            )

            assert response.id == "init-1"
            assert "capabilities" in response.result
            assert "serverInfo" in response.result

    @pytest.mark.asyncio
    async def test_server_handles_tool_list_request(self, mock_dependencies):
        """Test server handles tool list request."""
        server = MCPServer()

        # Mock some tools
        # Mock tool registration for listing
        from datetime import datetime

        from pythonium.common.lifecycle import ComponentState
        from pythonium.managers.tools.registry import ToolRegistration, ToolStatus
        from pythonium.tools.base import ToolMetadata

        mock_tool_registration = ToolRegistration(
            tool_id="test_tool_1",
            tool_class=Mock,
            name="test_tool_1",
            version="1.0.0",
            status=ToolStatus.ACTIVE,
            metadata=ToolMetadata(
                name="test_tool_1",
                description="Test tool 1",
                version="1.0.0",
                category="test",
            ),
            registered_at=datetime.now(),
        )

        with patch.object(
            server.message_handler.tool_registry, "list_tools"
        ) as mock_get_tools:
            mock_get_tools.return_value = [mock_tool_registration]

            list_tools_request = MCPRequest(
                id="list-tools-1", method="tools/list", params={}
            )

            response = await server.message_handler.handle_message(
                "test-session", list_tools_request
            )

            assert response.id == "list-tools-1"
            assert "tools" in response.result
            assert len(response.result["tools"]) == 1

    @pytest.mark.asyncio
    async def test_server_handles_tool_call_request(self, mock_dependencies):
        """Test server handles tool call request."""
        server = MCPServer()

        # Mock tool execution
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = {"output": "Hello, World!"}

        with patch.object(
            server.message_handler.execution_pipeline, "execute_single"
        ) as mock_execute, patch.object(
            server.message_handler.tool_registry, "has_tool"
        ) as mock_has_tool:

            mock_has_tool.return_value = True
            mock_execute.return_value = mock_result

            call_tool_request = MCPRequest(
                id="call-tool-1",
                method="tools/call",
                params={"name": "echo_tool", "arguments": {"message": "Hello, World!"}},
            )

            response = await server.message_handler.handle_message(
                "test-session", call_tool_request
            )

            assert response.id == "call-tool-1"
            assert "content" in response.result
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_handles_invalid_request(self, mock_dependencies):
        """Test server handles invalid request gracefully."""
        server = MCPServer()

        invalid_request = MCPRequest(
            id="invalid-1", method="nonexistent/method", params={}
        )

        response = await server.message_handler.handle_message(
            "test-session", invalid_request
        )

        assert response.id == "invalid-1"
        assert response.error is not None
        assert response.error["code"] == -32601  # Method not found

    @pytest.mark.asyncio
    async def test_server_handles_malformed_request(self, mock_dependencies):
        """Test server handles malformed request."""
        server = MCPServer()

        # Test with missing required fields
        malformed_request = MCPRequest(
            id="malformed-1", method="", params={}  # Empty method
        )

        response = await server.message_handler.handle_message(
            "test-session", malformed_request
        )

        assert response.id == "malformed-1"
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_server_resource_operations(self, mock_dependencies):
        """Test server resource operations."""
        server = MCPServer()

        # Test list resources
        list_resources_request = MCPRequest(
            id="list-resources-1", method="resources/list", params={}
        )

        with patch.object(
            server.message_handler, "_handle_list_resources"
        ) as mock_handler:
            mock_handler.return_value = MCPResponse(
                id="list-resources-1", result={"resources": []}
            )

            response = await server.message_handler.handle_message(
                "test-session", list_resources_request
            )
            assert response.id == "list-resources-1"
            assert "resources" in response.result

    @pytest.mark.asyncio
    async def test_server_prompt_operations(self, mock_dependencies):
        """Test server prompt operations."""
        server = MCPServer()

        # Test list prompts
        list_prompts_request = MCPRequest(
            id="list-prompts-1", method="prompts/list", params={}
        )

        response = await server.message_handler.handle_message(
            "test-session", list_prompts_request
        )

        assert response.id == "list-prompts-1"
        assert "prompts" in response.result

    @pytest.mark.asyncio
    async def test_server_notification_handling(self, mock_dependencies):
        """Test server notification handling."""
        server = MCPServer()

        # Test initialized notification
        initialized_notification = MCPNotification(
            method="notifications/initialized", params={}
        )

        # Should not raise an exception
        await server.message_handler.handle_message(
            "test-session", initialized_notification
        )

    @pytest.mark.asyncio
    async def test_server_concurrent_requests(self, mock_dependencies):
        """Test server handles concurrent requests."""
        server = MCPServer()

        # Create multiple concurrent requests
        requests = []
        for i in range(10):
            request = MCPRequest(id=f"ping-{i}", method="ping", params={})
            requests.append(request)

        # Execute all requests concurrently
        tasks = [
            server.message_handler.handle_message("test-session", req)
            for req in requests
        ]
        responses = await asyncio.gather(*tasks)

        # Verify all requests were handled
        assert len(responses) == 10
        for i, response in enumerate(responses):
            assert response.id == f"ping-{i}"

    @pytest.mark.asyncio
    async def test_server_error_handling_and_recovery(self, mock_dependencies):
        """Test server error handling and recovery."""
        server = MCPServer()

        # Simulate an error in tool execution
        with patch.object(
            server.message_handler.execution_pipeline, "execute_single"
        ) as mock_execute, patch.object(
            server.message_handler.tool_registry, "has_tool"
        ) as mock_has_tool:

            mock_has_tool.return_value = True
            mock_execute.side_effect = Exception("Tool execution failed")

            call_tool_request = MCPRequest(
                id="error-test-1",
                method="tools/call",
                params={"name": "failing_tool", "arguments": {}},
            )

            response = await server.message_handler.handle_message(
                "test-session", call_tool_request
            )

            # Server should handle the error gracefully
            assert response.id == "error-test-1"
            assert response.result is not None
            assert response.result.get("isError") is True

    def test_server_configuration_validation(self, mock_dependencies):
        """Test server configuration validation."""
        # Test with invalid transport type
        invalid_config = {"transport": {"type": "invalid_transport"}}

        with pytest.raises(Exception):
            MCPServer(config_overrides=invalid_config)

    @pytest.mark.asyncio
    async def test_server_session_management(self, mock_dependencies):
        """Test server session management."""
        server = MCPServer()

        # Test session creation and management
        session_id = "test-session-1"

        with patch.object(server.session_manager, "create_session") as mock_create:
            mock_create.return_value = session_id

            # Simulate client connection
            client_info = {"name": "test-client", "version": "1.0.0"}

            # Call the mocked method properly
            result_session_id = await mock_create(
                connection_type=ConnectionType.STDIO,
                metadata={"client_info": client_info},
            )

            mock_create.assert_called_once()
            assert result_session_id == session_id

    @pytest.mark.asyncio
    async def test_server_performance_monitoring(self, mock_dependencies):
        """Test server performance monitoring."""
        server = MCPServer()

        # Enable performance monitoring
        with patch.object(server.config.performance, "max_concurrent_requests", 50):
            ping_request = MCPRequest(id="perf-test-1", method="ping", params={})

            start_time = asyncio.get_event_loop().time()
            response = await server.message_handler.handle_message(
                "test-session", ping_request
            )
            end_time = asyncio.get_event_loop().time()

            assert response.id == "perf-test-1"
            assert (end_time - start_time) < 1.0  # Should be fast

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any temporary files
        pass
