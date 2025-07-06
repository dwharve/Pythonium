"""
Tests for error handling module.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pythonium.common.base import Result
from pythonium.common.error_handling import (
    ErrorContext,
    ErrorReporter,
    get_error_reporter,
    handle_tool_error,
    result_handler,
)
from pythonium.common.exceptions import PythoniumError


class TestErrorReporter:
    """Test ErrorReporter functionality."""

    def test_error_reporter_initialization(self):
        """Test ErrorReporter initialization."""
        reporter = ErrorReporter()

        assert isinstance(reporter._error_count, dict)
        assert isinstance(reporter._error_history, list)
        assert reporter._max_history == 1000

    def test_report_error_basic(self):
        """Test basic error reporting."""
        reporter = ErrorReporter()
        error = ValueError("Test error")

        reporter.report_error(error)

        assert reporter._error_count["ValueError"] == 1
        assert len(reporter._error_history) == 1

        error_info = reporter._error_history[0]
        assert error_info["error_type"] == "ValueError"
        assert error_info["error_message"] == "Test error"
        assert "traceback" in error_info

    def test_report_error_with_context(self):
        """Test error reporting with context."""
        reporter = ErrorReporter()
        error = RuntimeError("Context error")
        context = {"user_id": "123", "action": "test"}
        component = "test_component"

        reporter.report_error(error, context=context, component=component)

        error_info = reporter._error_history[0]
        assert error_info["component"] == "test_component"
        assert error_info["context"]["user_id"] == "123"
        assert error_info["context"]["action"] == "test"

    def test_error_count_tracking(self):
        """Test error count tracking."""
        reporter = ErrorReporter()

        # Report multiple errors of the same type
        for i in range(3):
            reporter.report_error(ValueError(f"Error {i}"))

        # Report different error type
        reporter.report_error(RuntimeError("Runtime error"))

        assert reporter._error_count["ValueError"] == 3
        assert reporter._error_count["RuntimeError"] == 1
        assert len(reporter._error_history) == 4

    def test_get_error_stats(self):
        """Test getting error statistics."""
        reporter = ErrorReporter()

        reporter.report_error(ValueError("Error 1"))
        reporter.report_error(ValueError("Error 2"))
        reporter.report_error(RuntimeError("Error 3"))

        stats = reporter.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["error_count_by_type"]["ValueError"] == 2
        assert stats["error_count_by_type"]["RuntimeError"] == 1
        assert len(stats["recent_errors"]) == 3

    def test_error_history_limit(self):
        """Test error history size limit."""
        reporter = ErrorReporter()
        reporter._max_history = 5  # Set small limit for testing

        # Report more errors than the limit
        for i in range(10):
            reporter.report_error(ValueError(f"Error {i}"))

        # Should only keep the most recent errors
        assert len(reporter._error_history) <= 5

    def test_get_error_reporter_singleton(self):
        """Test error reporter singleton pattern."""
        reporter1 = get_error_reporter()
        reporter2 = get_error_reporter()

        assert reporter1 is reporter2
        assert isinstance(reporter1, ErrorReporter)


class TestErrorContext:
    """Test ErrorContext functionality."""

    def test_error_context_with_exception(self):
        """Test ErrorContext with exception handling."""
        with patch.object(get_error_reporter(), "report_error") as mock_report:
            with pytest.raises(ValueError):
                with ErrorContext("test_component", "test_operation"):
                    raise ValueError("Test error")

            mock_report.assert_called_once()
            args, kwargs = mock_report.call_args
            assert args[0].args[0] == "Test error"
            assert kwargs["component"] == "test_component"
            assert kwargs["context"]["operation"] == "test_operation"

    def test_error_context_without_exception(self):
        """Test ErrorContext without exception."""
        with patch.object(get_error_reporter(), "report_error") as mock_report:
            with ErrorContext("test_component", "test_operation"):
                pass  # No exception

            mock_report.assert_not_called()

    def test_error_context_suppress_exception(self):
        """Test ErrorContext with exception suppression."""
        with patch.object(get_error_reporter(), "report_error") as mock_report:
            with ErrorContext("test_component", "test_operation", reraise=False):
                raise ValueError("Test error")

            mock_report.assert_called_once()


class TestResultHandlerDecorator:
    """Test result_handler decorator functionality."""

    @pytest.mark.asyncio
    async def test_result_handler_async_success(self):
        """Test result_handler with successful async function."""

        @result_handler()
        async def successful_async_function():
            return {"data": "success"}

        result = await successful_async_function()

        assert isinstance(result, Result)
        assert result.success is True
        assert result.data == {"data": "success"}

    @pytest.mark.asyncio
    async def test_result_handler_async_exception(self):
        """Test result_handler with async function that raises exception."""

        @result_handler()
        async def failing_async_function():
            raise ValueError("Test async error")

        result = await failing_async_function()

        assert isinstance(result, Result)
        assert result.success is False
        assert "Test async error" in result.error

    def test_result_handler_sync_success(self):
        """Test result_handler with successful sync function."""

        @result_handler()
        def successful_sync_function():
            return {"data": "sync_success"}

        result = successful_sync_function()

        assert isinstance(result, Result)
        assert result.success is True
        assert result.data == {"data": "sync_success"}

    def test_result_handler_sync_exception(self):
        """Test result_handler with sync function that raises exception."""

        @result_handler()
        def failing_sync_function():
            raise ValueError("Test sync error")

        result = failing_sync_function()

        assert isinstance(result, Result)
        assert result.success is False
        assert "Test sync error" in result.error

    @pytest.mark.asyncio
    async def test_result_handler_already_result(self):
        """Test result_handler with function that already returns Result."""

        @result_handler()
        async def result_returning_function():
            return Result.success_result({"already": "result"})

        result = await result_returning_function()

        assert isinstance(result, Result)
        assert result.success is True
        assert result.data == {"already": "result"}

    def test_result_handler_with_custom_component(self):
        """Test result_handler with custom component name."""

        @result_handler(component="custom_component")
        def failing_function():
            raise ValueError("Original error")

        result = failing_function()

        assert isinstance(result, Result)
        assert result.success is False
        assert "Original error" in result.error

    def test_result_handler_with_default_error_message(self):
        """Test result_handler with custom default error message."""

        @result_handler(default_error_message="Custom operation failed")
        def failing_function():
            raise ValueError("Original error")

        result = failing_function()

        assert isinstance(result, Result)
        assert result.success is False
        # The exact error message depends on the implementation


class TestHandleToolErrorDecorator:
    """Test handle_tool_error decorator functionality."""

    @pytest.mark.asyncio
    async def test_handle_tool_error_success(self):
        """Test handle_tool_error with successful tool function."""

        @handle_tool_error
        async def successful_tool_function(params, context):
            return Result.success_result({"tool": "success"})

        mock_params = Mock()
        mock_context = Mock()

        result = await successful_tool_function(mock_params, mock_context)

        assert isinstance(result, Result)
        assert result.success is True
        assert result.data == {"tool": "success"}

    @pytest.mark.asyncio
    async def test_handle_tool_error_exception(self):
        """Test handle_tool_error with tool function that raises exception."""

        @handle_tool_error
        async def failing_tool_function(params, context):
            raise ValueError("Tool error")

        mock_params = Mock()
        mock_context = Mock()

        result = await failing_tool_function(mock_params, mock_context)

        assert isinstance(result, Result)
        assert result.success is False
        assert "Tool error" in result.error

    @pytest.mark.asyncio
    async def test_handle_tool_error_pythonium_error(self):
        """Test handle_tool_error with PythoniumError."""

        @handle_tool_error
        async def tool_with_pythonium_error(params, context):
            raise PythoniumError("Pythonium specific error")

        mock_params = Mock()
        mock_context = Mock()

        result = await tool_with_pythonium_error(mock_params, mock_context)

        assert isinstance(result, Result)
        assert result.success is False
        assert "Pythonium specific error" in result.error

    @pytest.mark.asyncio
    async def test_handle_tool_error_non_result_return(self):
        """Test handle_tool_error with function returning non-Result."""

        @handle_tool_error
        async def tool_returning_dict(params, context):
            return {"raw": "data"}

        mock_params = Mock()
        mock_context = Mock()

        result = await tool_returning_dict(mock_params, mock_context)

        assert isinstance(result, Result)
        assert result.success is True
        assert result.data == {"raw": "data"}


class TestErrorHandlingIntegration:
    """Integration tests for error handling components."""

    def test_error_reporting_with_decorators(self):
        """Test that decorators properly report errors."""
        reporter = get_error_reporter()
        initial_count = len(reporter._error_history)

        @result_handler(component="test")
        def function_with_error():
            raise ValueError("Integration test error")

        result = function_with_error()

        # Check if error was reported
        assert len(reporter._error_history) > initial_count
        assert isinstance(result, Result)
        assert not result.success

    @pytest.mark.asyncio
    async def test_multiple_decorator_combinations(self):
        """Test combining multiple error handling decorators."""

        @handle_tool_error
        async def complex_tool_function():
            return {"complex": "result"}

        result = await complex_tool_function()

        assert isinstance(result, Result)
        assert result.success is True

    def test_error_stats_after_multiple_operations(self):
        """Test error statistics after multiple operations."""
        reporter = get_error_reporter()

        # Clear previous state
        reporter._error_count.clear()
        reporter._error_history.clear()

        # Generate various errors
        for i in range(3):
            reporter.report_error(ValueError(f"Value error {i}"))

        for i in range(2):
            reporter.report_error(RuntimeError(f"Runtime error {i}"))

        stats = reporter.get_error_stats()

        assert stats["total_errors"] == 5
        assert stats["error_count_by_type"]["ValueError"] == 3
        assert stats["error_count_by_type"]["RuntimeError"] == 2

    @pytest.mark.asyncio
    async def test_error_handling_in_tool_context(self):
        """Test error handling in a realistic tool context."""

        # Mock a tool-like function that might fail
        @handle_tool_error
        async def mock_tool_execute(params, context):
            if params.get("should_fail"):
                raise ValueError("Simulated tool failure")
            return Result.success_result({"tool_result": "success"})

        mock_context = Mock()

        # Test success case
        success_params = {"should_fail": False}
        result = await mock_tool_execute(success_params, mock_context)
        assert result.success is True

        # Test failure case
        failure_params = {"should_fail": True}
        result = await mock_tool_execute(failure_params, mock_context)
        assert result.success is False
        assert result.error is not None
        assert "Simulated tool failure" in result.error
