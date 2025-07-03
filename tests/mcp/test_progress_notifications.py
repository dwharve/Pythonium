"""
Tests for MCP handler progress notification functionality.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythonium.mcp_legacy.config import MCPConfigManager
from pythonium.mcp_legacy.handlers import MCPMessageHandler
from pythonium.mcp_legacy.protocol import MCPNotification, MCPRequest, MCPResponse
from pythonium.mcp_legacy.session import SessionManager


class MockTransport:
    """Mock transport for testing notifications."""

    def __init__(self):
        self.sent_messages = []
        self.notifications = []

    async def send(self, message):
        """Capture sent messages."""
        self.sent_messages.append(message)
        self.notifications.append(message)

    async def send_notification(self, notification):
        """Capture sent notifications."""
        self.notifications.append(notification)
        self.sent_messages.append(notification)

    async def send_message(self, message):
        """Capture sent messages."""
        self.sent_messages.append(message)


class TestMCPProgressNotifications:
    """Test MCP handler progress notification functionality."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager."""
        config_manager = MagicMock()
        config_manager.config = MagicMock()
        config_manager.config.performance = MagicMock()
        config_manager.config.performance.request_timeout_seconds = 30
        return config_manager

    @pytest.fixture
    def session_manager(self):
        """Create a session manager."""
        return SessionManager(session_timeout_minutes=30, max_sessions=100)

    @pytest.fixture
    def security_manager(self):
        """Create a mock security manager."""
        return None

    @pytest.fixture
    def handler(self, config_manager, session_manager, security_manager):
        """Create an MCP message handler."""
        return MCPMessageHandler(
            config_manager=config_manager,
            session_manager=session_manager,
            security_manager=security_manager,
        )

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        return MockTransport()

    def test_set_transport(self, handler, mock_transport):
        """Test setting transport on handler."""
        handler.set_transport(mock_transport)
        assert handler._transport == mock_transport

    @pytest.mark.asyncio
    async def test_send_progress_notification(self, handler, mock_transport):
        """Test sending progress notifications."""
        handler.set_transport(mock_transport)

        # Send a progress notification
        await handler._send_progress_notification(
            progress_token="test-token-123", progress=50, total=100
        )

        # Check that notification was sent
        assert len(mock_transport.notifications) == 1
        notification = mock_transport.notifications[0]

        assert notification["method"] == "notifications/progress"
        assert notification["params"]["progressToken"] == "test-token-123"
        assert notification["params"]["progress"] == 50
        assert notification["params"]["total"] == 100

    @pytest.mark.asyncio
    async def test_send_progress_notification_without_transport(self, handler):
        """Test that progress notifications are silently ignored without transport."""
        # Don't set transport

        # This should not raise an exception
        await handler._send_progress_notification(
            progress_token="test-token", progress=25, total=100
        )

    @pytest.mark.asyncio
    async def test_call_tool_with_progress(self, handler, mock_transport):
        """Test that tool calls generate progress notifications."""
        handler.set_transport(mock_transport)

        # Mock the pipeline to simulate progress reporting
        mock_pipeline = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"test": "result"}
        mock_result.metadata = {}

        # Capture the progress callback passed to the pipeline
        captured_progress_callback = None

        async def mock_execute_single(
            tool_id, args=None, progress_callback=None, **kwargs
        ):
            nonlocal captured_progress_callback
            captured_progress_callback = progress_callback

            # Simulate progress reporting
            if progress_callback:
                await progress_callback("Starting tool execution")
                await progress_callback("Tool execution in progress")
                await progress_callback("Tool execution completed")

            return mock_result

        mock_pipeline.execute_single = mock_execute_single

        # Mock the tool registry to indicate the tool exists
        with patch.object(handler.tool_registry, "has_tool", return_value=True):
            with patch.object(handler, "execution_pipeline", mock_pipeline):
                # Create a tool call request
                request = MCPRequest(
                    id="test-request",
                    method="tools/call",
                    params={"name": "test_tool", "arguments": {"arg1": "value1"}},
                )

                # Handle the request
                await handler._handle_call_tool("test-session", request)

                # Check that tool was called with progress callback
                assert captured_progress_callback is not None

                # Check that progress notifications were sent
                assert len(mock_transport.notifications) >= 3

            # Verify progress notification structure
            for notification in mock_transport.notifications:
                assert notification["method"] == "notifications/progress"
                assert "progressToken" in notification["params"]
                assert "progress" in notification["params"]
                assert "total" in notification["params"]

    @pytest.mark.asyncio
    async def test_progress_token_uniqueness(self, handler, mock_transport):
        """Test that progress tokens are unique for different requests."""
        handler.set_transport(mock_transport)

        # Mock the pipeline
        mock_pipeline = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"test": "result"}
        mock_result.metadata = {}

        progress_tokens = []

        async def mock_execute_single(
            tool_id, args=None, progress_callback=None, progress_token=None, **kwargs
        ):
            if progress_token:
                progress_tokens.append(progress_token)
            if progress_callback:
                await progress_callback("Test progress")
            return mock_result

        mock_pipeline.execute_single = mock_execute_single

        with patch.object(handler.tool_registry, "has_tool", return_value=True):
            with patch.object(handler, "execution_pipeline", mock_pipeline):
                # Make multiple tool calls
                for i in range(3):
                    request = MCPRequest(
                        id=f"test-request-{i}",
                        method="tools/call",
                        params={"name": "test_tool", "arguments": {}},
                    )

                    await handler._handle_call_tool("test-session", request)

        # Check that all progress tokens are unique
        assert len(progress_tokens) == 3
        assert len(set(progress_tokens)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_progress_notification_error_handling(self, handler, mock_transport):
        """Test error handling in progress notifications."""

        # Mock transport that raises exceptions
        class FailingTransport:
            async def send_notification(self, notification):
                raise RuntimeError("Transport failed")

        failing_transport = FailingTransport()
        handler.set_transport(failing_transport)

        # This should not raise an exception
        await handler._send_progress_notification(
            progress_token="test-token", progress=30, total=100
        )

    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(self, handler, mock_transport):
        """Test that errors in progress callbacks don't break tool execution."""
        handler.set_transport(mock_transport)

        # Mock transport that fails on notification sending
        async def failing_send_notification(notification):
            raise RuntimeError("Notification sending failed")

        mock_transport.send_notification = failing_send_notification

        # Mock the pipeline
        mock_pipeline = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"test": "result"}
        mock_result.metadata = {}

        async def mock_execute_single(
            tool_id, args=None, progress_callback=None, **kwargs
        ):
            # Call progress callback which should handle transport errors gracefully
            if progress_callback:
                await progress_callback("This should not break execution")
            return mock_result

        mock_pipeline.execute_single = mock_execute_single

        with patch.object(handler.tool_registry, "has_tool", return_value=True):
            with patch.object(handler, "execution_pipeline", mock_pipeline):
                request = MCPRequest(
                    id="test-request",
                    method="tools/call",
                    params={"name": "test_tool", "arguments": {}},
                )

                # This should complete successfully despite notification failures
                response = await handler._handle_call_tool("test-session", request)
                # Check that the response has content (any content indicates success)
                assert response is not None
                assert len(response) > 0
