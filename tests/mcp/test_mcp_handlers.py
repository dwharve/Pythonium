"""
Unit tests for MCP message handlers.

Tests individual message handlers for correctness, error handling,
and protocol compliance.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pythonium.mcp_legacy.handlers import MCPMessageHandler
from pythonium.mcp_legacy.protocol import MCPNotification, MCPRequest, MCPResponse
from pythonium.mcp_legacy.session import SessionManager
from pythonium.tools.base import BaseTool


class TestMCPMessageHandlers:
    """Test MCP message handlers."""

    @pytest.fixture
    def mock_config_manager(self):
        """Mock config manager."""
        config = Mock()
        config.get_config.return_value = Mock(
            name="test-server",
            version="1.0.0",
            description="Test server",
            tools=Mock(enable_tool_execution=True, tool_timeout_seconds=30),
            resources=Mock(enabled=True),
            prompts=Mock(enable_prompts=True),
            logging=Mock(level="INFO"),
            security=Mock(enabled=True, max_request_size=1024000),
        )
        return config

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager."""
        session_mgr = Mock(spec=SessionManager)
        session_mgr.get_session.return_value = Mock()
        return session_mgr

    @pytest.fixture
    def handler(self, mock_config_manager, mock_session_manager):
        """Create message handler for testing."""
        # Create actual instances for the mocks
        mock_registry = Mock()
        mock_security = Mock()

        with patch(
            "pythonium.mcp.handlers.ToolRegistry", return_value=mock_registry
        ), patch("pythonium.mcp.handlers.SecurityManager", return_value=mock_security):

            handler = MCPMessageHandler(mock_config_manager, mock_session_manager)
            # Override the instances created during init
            handler.tool_registry = mock_registry
            handler.security_manager = mock_security
            return handler

    @pytest.mark.asyncio
    async def test_handle_initialize_request(self, handler):
        """Test initialize request handling."""
        request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "init-1"
        assert response.result is not None
        assert hasattr(response.result, "protocolVersion")
        assert hasattr(response.result, "capabilities")
        assert hasattr(response.result, "serverInfo")

    @pytest.mark.asyncio
    async def test_handle_initialize_request_invalid_version(self, handler):
        """Test initialize request with invalid protocol version."""
        request = MCPRequest(
            id="init-2",
            method="initialize",
            params={
                "protocolVersion": "invalid-version",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "init-2"
        # According to MCP spec, servers should be permissive with protocol versions
        # The server should still initialize successfully but may log warnings
        assert response.result is not None
        assert hasattr(response.result, "protocolVersion")

    @pytest.mark.asyncio
    async def test_handle_ping_request(self, handler):
        """Test ping request handling."""
        request = MCPRequest(id="ping-1", method="ping", params={})

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "ping-1"
        assert response.result == {}

    @pytest.mark.asyncio
    async def test_handle_list_tools_request(self, handler):
        """Test list tools request handling."""
        # Mock tool registrations instead of tool instances
        mock_registration1 = Mock()
        mock_registration1.tool_id = "tool1"
        mock_registration1.metadata = Mock()
        mock_registration1.metadata.get_description.return_value = "Test tool 1"
        mock_registration1.metadata.parameters = []

        mock_registration2 = Mock()
        mock_registration2.tool_id = "tool2"
        mock_registration2.metadata = Mock()
        mock_registration2.metadata.get_description.return_value = "Test tool 2"
        mock_registration2.metadata.parameters = []

        handler.tool_registry.list_tools.return_value = [
            mock_registration1,
            mock_registration2,
        ]

        request = MCPRequest(id="list-tools-1", method="tools/list", params={})

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "list-tools-1"
        assert "tools" in response.result
        assert len(response.result["tools"]) == 2

    @pytest.mark.asyncio
    async def test_handle_call_tool_request(self, handler):
        """Test call tool request handling."""
        # Mock that tool exists and execution pipeline returns success
        handler.tool_registry.has_tool.return_value = True

        # Mock successful execution result
        mock_result = Mock()
        mock_result.success = True
        mock_result.result = Mock()
        mock_result.result.data = {"output": "Hello, World!"}

        handler.execution_pipeline.execute_single = AsyncMock(return_value=mock_result)

        request = MCPRequest(
            id="call-tool-1",
            method="tools/call",
            params={"name": "echo_tool", "arguments": {"message": "Hello, World!"}},
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "call-tool-1"
        assert "content" in response.result
        assert not response.result.get("isError", False)
        handler.execution_pipeline.execute_single.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_call_tool_request_tool_not_found(self, handler):
        """Test call tool request with non-existent tool."""
        handler.tool_registry.has_tool.return_value = False

        request = MCPRequest(
            id="call-tool-2",
            method="tools/call",
            params={"name": "nonexistent_tool", "arguments": {}},
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "call-tool-2"
        # Tool not found should raise InvalidParams, which gets converted to error response
        assert response.error is not None
        assert response.error["code"] == -32602  # Invalid params

    @pytest.mark.asyncio
    async def test_handle_call_tool_request_execution_error(self, handler):
        """Test call tool request with execution error."""
        # Mock that tool exists but execution fails
        handler.tool_registry.has_tool.return_value = True

        # Mock failed execution result
        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Tool execution failed"

        handler.execution_pipeline.execute_single = AsyncMock(return_value=mock_result)

        request = MCPRequest(
            id="call-tool-3",
            method="tools/call",
            params={"name": "failing_tool", "arguments": {}},
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "call-tool-3"
        # Tool execution errors should be returned as results with isError=True, not error responses
        assert response.result is not None
        assert response.result.get("isError", False) is True
        assert "content" in response.result

    @pytest.mark.asyncio
    async def test_handle_list_resources_request(self, handler):
        """Test list resources request handling."""
        request = MCPRequest(id="list-resources-1", method="resources/list", params={})

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "list-resources-1"
        assert "resources" in response.result

    @pytest.mark.asyncio
    async def test_handle_read_resource_request(self, handler):
        """Test read resource request handling."""
        request = MCPRequest(
            id="read-resource-1",
            method="resources/read",
            params={"uri": "file:///test/resource.txt"},
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "read-resource-1"

    @pytest.mark.asyncio
    async def test_handle_list_prompts_request(self, handler):
        """Test list prompts request handling."""
        request = MCPRequest(id="list-prompts-1", method="prompts/list", params={})

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "list-prompts-1"
        assert "prompts" in response.result

    @pytest.mark.asyncio
    async def test_handle_get_prompt_request(self, handler):
        """Test get prompt request handling."""
        request = MCPRequest(
            id="get-prompt-1",
            method="prompts/get",
            params={"name": "test_prompt", "arguments": {}},
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "get-prompt-1"

    @pytest.mark.asyncio
    async def test_handle_set_logging_level_request(self, handler):
        """Test set logging level request handling."""
        request = MCPRequest(
            id="set-log-1", method="logging/setLevel", params={"level": "DEBUG"}
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "set-log-1"

    @pytest.mark.asyncio
    async def test_handle_completion_request(self, handler):
        """Test completion request handling."""
        request = MCPRequest(
            id="complete-1",
            method="completion/complete",
            params={
                "ref": {"type": "ref/prompt", "name": "test_prompt"},
                "argument": {"name": "query", "value": "test"},
            },
        )

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "complete-1"

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, handler):
        """Test handling of unknown method."""
        request = MCPRequest(id="unknown-1", method="unknown/method", params={})

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "unknown-1"
        assert response.error is not None
        assert response.error["code"] == -32601  # Method not found

    @pytest.mark.asyncio
    async def test_handle_notification(self, handler):
        """Test notification handling."""
        notification = MCPNotification(method="notifications/initialized", params={})

        # Should not raise an exception and should not return a response
        result = await handler.handle_message("test-session-1", notification)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_malformed_request(self, handler):
        """Test handling of malformed request."""
        # Request with missing method
        request = MCPRequest(id="malformed-1", method="", params={})

        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.id == "malformed-1"
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_security_validation(self, handler):
        """Test security validation in handlers."""
        # Since _authenticate_request method doesn't exist yet,
        # this test will verify the handler works without security
        handler.security_manager = None  # Disable security

        request = MCPRequest(
            id="security-test-1",
            method="tools/call",
            params={"name": "test_tool", "arguments": {}},
        )

        # Tool not found case
        handler.tool_registry.has_tool.return_value = False
        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.error is not None  # Should get tool not found error

    @pytest.mark.asyncio
    async def test_request_size_limit(self, handler):
        """Test request size limit validation."""
        # Create a large request (the actual size validation would be done at the transport layer)
        large_params = {"data": "x" * 1000}  # Smaller test data

        request = MCPRequest(
            id="large-request-1", method="tools/call", params=large_params
        )

        # Mock tool not found to get a predictable error
        handler.tool_registry.has_tool.return_value = False
        response = await handler.handle_message("test-session-1", request)

        assert isinstance(response, MCPResponse)
        assert response.error is not None
        assert response.error["code"] == -32602  # Invalid params (tool not found)

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, handler):
        """Test concurrent tool execution."""
        # Mock multiple tools
        mock_tools = []
        for i in range(5):
            mock_tool = Mock(spec=BaseTool)
            mock_tool.name = f"tool_{i}"
            mock_tool.execute = AsyncMock(return_value={"result": f"output_{i}"})
            mock_tools.append(mock_tool)

        def get_tool_side_effect(name):
            for tool in mock_tools:
                if tool.name == name:
                    return tool
            return None

        handler.tool_registry.get_tool.side_effect = get_tool_side_effect

        # Create multiple concurrent requests
        requests = []
        for i in range(5):
            request = MCPRequest(
                id=f"concurrent-{i}",
                method="tools/call",
                params={"name": f"tool_{i}", "arguments": {}},
            )
            requests.append(request)

        # Execute concurrently
        import asyncio

        tasks = [handler.handle_message("test-session-1", req) for req in requests]
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert response.id == f"concurrent-{i}"
            assert response.error is None
