"""
End-to-end integration test for the progress notification feature.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pythonium.managers.tools.pipeline import ExecutionPipeline
from pythonium.managers.tools.registry import ToolRegistry
from pythonium.mcp.handlers import MCPMessageHandler
from pythonium.mcp.protocol import MCPRequest
from pythonium.tools.filesystem.search import FindFilesTool


class TestProgressFeatureIntegration:
    """Integration test for the complete progress notification feature."""

    @pytest.mark.asyncio
    async def test_end_to_end_progress_flow(self):
        """Test complete progress flow from MCP request to tool execution."""
        # Setup: Mock transport to capture progress notifications
        progress_notifications = []

        async def capture_notification(notification):
            progress_notifications.append(notification)

        mock_transport = AsyncMock()
        mock_transport.send.side_effect = capture_notification

        # Setup: Create MCP handler and configure it
        config_manager = MagicMock()
        config_manager.get_config.return_value = MagicMock()
        config_manager.get_config.return_value.tools.enable_tool_execution = True
        config_manager.get_config.return_value.tools.tool_timeout_seconds = 30

        session_manager = MagicMock()

        handler = MCPMessageHandler(config_manager, session_manager)
        handler.set_transport(mock_transport)

        # Setup: Register a tool that reports progress
        registry = ToolRegistry()
        registry.register_tool(FindFilesTool)

        # Replace the handler's tool registry
        handler.tool_registry = registry
        # Also update the pipeline's tool registry
        handler.execution_pipeline.tool_registry = registry

        # Setup: Create a tool call request
        request = MCPRequest(
            id="test-progress-integration",
            method="tools/call",
            params={
                "name": "find_files",
                "arguments": {
                    "path": "/tmp",
                    "name_pattern": "*.txt",
                    "max_depth": 1,
                    "limit": 5,
                },
            },
        )

        # Execute: Call the tool through the MCP handler
        response = await handler._handle_call_tool("test-session", request)

        # Verify: Tool execution succeeded
        assert "result" in response or "error" not in response

        # Verify: Progress notifications were sent
        assert len(progress_notifications) > 0

        # Verify: All notifications have correct structure
        for notification in progress_notifications:
            assert notification["method"] == "notifications/progress"
            assert "params" in notification
            assert "progressToken" in notification["params"]
            assert "progress" in notification["params"]
            assert "total" in notification["params"]

    @pytest.mark.asyncio
    async def test_progress_pipeline_with_tool_registry(self):
        """Test progress reporting through the execution pipeline with ToolRegistry."""
        # Setup: Create pipeline with tool registry
        registry = ToolRegistry()
        registry.register_tool(FindFilesTool)

        pipeline = ExecutionPipeline(tool_registry=registry)

        # Setup: Progress callback to capture messages
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Execute: Run tool through pipeline with progress callback
        result = await pipeline.execute_single(
            tool_id="find_files",
            args={"path": "/tmp", "name_pattern": "*.py", "max_depth": 1, "limit": 3},
            progress_callback=progress_callback,
        )

        # Verify: Tool execution completed
        assert result.success

        # Verify: Progress messages were generated
        assert len(progress_messages) > 0

        # Verify: Progress messages contain tool prefix
        tool_prefixed_messages = [
            msg for msg in progress_messages if "[find_files]" in msg
        ]
        assert len(tool_prefixed_messages) > 0

    @pytest.mark.asyncio
    async def test_progress_feature_error_resilience(self):
        """Test that progress feature handles errors gracefully."""
        # Setup: Pipeline with registry
        registry = ToolRegistry()
        registry.register_tool(FindFilesTool)

        pipeline = ExecutionPipeline(tool_registry=registry)

        # Setup: Failing progress callback
        callback_calls = []

        def failing_progress_callback(message: str):
            callback_calls.append(message)
            if len(callback_calls) > 2:  # Fail after a few calls
                raise RuntimeError("Progress callback failed")

        # Execute: Run tool with failing progress callback
        result = await pipeline.execute_single(
            tool_id="find_files",
            args={"path": "/tmp", "name_pattern": "*.txt", "max_depth": 1, "limit": 2},
            progress_callback=failing_progress_callback,
        )

        # Verify: Tool execution still succeeded despite callback failures
        assert result.success

        # Verify: Some progress callbacks were made before failure
        assert len(callback_calls) > 0

    def test_progress_feature_documentation(self):
        """Test that progress feature is properly documented and accessible."""
        # Verify pipeline has progress support
        pipeline = ExecutionPipeline()
        assert hasattr(pipeline, "execute_single")

        # Verify MCP handler has progress support
        handler = MCPMessageHandler(MagicMock(), MagicMock())
        assert hasattr(handler, "set_transport")
        assert hasattr(handler, "_send_progress_notification")

        # Verify tools support progress callbacks
        tool = FindFilesTool()
        assert hasattr(tool, "execute")

        # Verify progress types are available
        from pythonium.managers.tools.pipeline import ProgressCallbackType

        assert ProgressCallbackType is not None
