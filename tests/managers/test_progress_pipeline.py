"""
Tests for progress notification functionality in the execution pipeline.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythonium.common.base import Result
from pythonium.managers.tools.pipeline import ExecutionContext, ExecutionPipeline
from pythonium.managers.tools.registry import ToolRegistry
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


class MockProgressTool(BaseTool):
    """Mock tool that reports progress during execution."""

    def __init__(self):
        super().__init__()
        self.progress_messages = []

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock_progress_tool",
            description="Mock tool for testing progress notifications",
            brief_description="Mock tool for testing",
            detailed_description="A mock tool that simulates progress reporting",
            category="test",
            tags=["mock", "test"],
            parameters=[
                ToolParameter(
                    name="steps",
                    type=ParameterType.INTEGER,
                    description="Number of progress steps to simulate",
                    default=3,
                )
            ],
        )

    async def execute(self, parameters, context: ToolContext) -> Result:
        """Execute with progress reporting."""
        steps = getattr(parameters, "steps", 3)
        progress_callback = getattr(context, "progress_callback", None)

        if progress_callback:
            progress_callback("Starting mock tool execution")

        for i in range(steps):
            await asyncio.sleep(0.01)  # Simulate work
            if progress_callback:
                progress_callback(f"Step {i+1}/{steps} completed")

        if progress_callback:
            progress_callback("Mock tool execution completed")

        return Result.success_result(
            {"steps_completed": steps, "message": "Mock execution successful"}
        )


class TestProgressPipeline:
    """Test progress functionality in the execution pipeline."""

    @pytest.fixture
    def registry(self):
        """Create a tool registry with mock tools."""
        registry = ToolRegistry()
        registry.register_tool(MockProgressTool)
        return registry

    @pytest.fixture
    def pipeline(self, registry):
        """Create an execution pipeline."""
        return ExecutionPipeline(registry)

    @pytest.mark.asyncio
    async def test_progress_callback_forwarding(self, pipeline):
        """Test that progress callbacks are forwarded to tools."""
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Execute tool with progress callback
        result = await pipeline.execute_single(
            tool_id="mock_progress_tool",
            args={"steps": 3},
            progress_callback=progress_callback,
        )

        # Check that execution was successful
        assert result.success
        assert result.data["steps_completed"] == 3

        # Check that progress messages were captured
        assert len(progress_messages) >= 4  # start + 3 steps + completion
        assert "[mock_progress_tool] Starting mock tool execution" in progress_messages
        assert "[mock_progress_tool] Step 1/3 completed" in progress_messages
        assert "[mock_progress_tool] Step 2/3 completed" in progress_messages
        assert "[mock_progress_tool] Step 3/3 completed" in progress_messages
        assert "[mock_progress_tool] Mock tool execution completed" in progress_messages

    @pytest.mark.asyncio
    async def test_progress_callback_none(self, pipeline):
        """Test that tools work correctly when no progress callback is provided."""
        # Execute tool without progress callback
        result = await pipeline.execute_single(
            tool_id="mock_progress_tool", args={"steps": 2}
        )

        # Check that execution was successful
        assert result.success
        assert result.data["steps_completed"] == 2

    @pytest.mark.asyncio
    async def test_progress_token_generation(self, pipeline):
        """Test progress token generation and tracking."""
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Execute with custom progress token
        result = await pipeline.execute_single(
            tool_id="mock_progress_tool",
            args={"steps": 2},
            progress_callback=progress_callback,
            progress_token="test-token-123",
        )

        assert result.success
        assert result.progress_token == "test-token-123"

    @pytest.mark.asyncio
    async def test_progress_with_tool_error(self, pipeline):
        """Test that progress callbacks work even when tools fail."""

        class FailingProgressTool(BaseTool):
            async def initialize(self):
                pass

            async def shutdown(self):
                pass

            @property
            def metadata(self):
                return ToolMetadata(
                    name="failing_progress_tool",
                    description="Tool that fails after reporting progress",
                    brief_description="Failing tool",
                    detailed_description="Tool for testing error handling",
                    category="test",
                    tags=["test"],
                )

            async def execute(self, parameters, context):
                progress_callback = getattr(context, "progress_callback", None)
                if progress_callback:
                    progress_callback("Starting failing tool")
                    progress_callback("About to fail")

                raise RuntimeError("Simulated tool failure")

        # Register the failing tool
        pipeline.tool_registry.register_tool(FailingProgressTool)

        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Execute failing tool
        result = await pipeline.execute_single(
            tool_id="failing_progress_tool",
            args={},
            progress_callback=progress_callback,
        )

        # Check that execution failed
        assert not result.success
        assert "Simulated tool failure" in str(result.error)

        # Check that progress messages were still captured
        assert len(progress_messages) == 2
        assert "[failing_progress_tool] Starting failing tool" in progress_messages
        assert "[failing_progress_tool] About to fail" in progress_messages

    @pytest.mark.asyncio
    async def test_progress_callback_exception_handling(self, pipeline):
        """Test that exceptions in progress callbacks don't break tool execution."""

        def failing_progress_callback(message: str):
            raise RuntimeError("Progress callback failed")

        # Execute tool with failing progress callback
        result = await pipeline.execute_single(
            tool_id="mock_progress_tool",
            args={"steps": 2},
            progress_callback=failing_progress_callback,
        )

        # Tool execution should still succeed despite callback failures
        assert result.success
        assert result.data["steps_completed"] == 2
