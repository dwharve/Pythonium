"""
Tests for tool-level progress notification functionality.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pythonium.common.parameter_validation import (
    ExecuteCommandParams,
)
from pythonium.tools.base import ToolContext
from pythonium.tools.std import FindFilesTool, SearchFilesTool
from pythonium.tools.std.execution import ExecuteCommandTool
from pythonium.tools.std.parameters import FindFilesParams, SearchTextParams


class TestToolProgressNotifications:
    """Test progress notifications at the tool level."""

    def test_find_files_tool_progress(self):
        """Test that FindFilesTool reports progress during execution."""
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create many test files to trigger progress reporting
            for i in range(120):  # Enough to trigger progress (needs >100)
                test_file = temp_path / f"test_file_{i}.py"
                test_file.write_text(f"# Test file {i}\n")

            # Create subdirectories
            for i in range(3):
                subdir = temp_path / f"subdir_{i}"
                subdir.mkdir()
                for j in range(10):
                    test_file = subdir / f"sub_test_{j}.py"
                    test_file.write_text(f"# Sub test file {i}.{j}\n")

            # Test the tool directly
            tool = FindFilesTool()

            # Create search parameters
            search_params = {
                "max_depth": 5,
                "limit": None,
                "include_hidden": False,
                "file_type": "both",
                "name_pattern": "*.py",
                "regex_compiled": None,
                "case_sensitive": True,
                "min_size": None,
                "max_size": None,
                "progress_callback": progress_callback,
            }

            results = []

            # Call the internal search method
            tool._search_directory(temp_path, search_params, results)

            # Check that progress messages were generated
            assert len(progress_messages) > 0

            # Check for expected progress message patterns
            dir_messages = [
                msg for msg in progress_messages if "Searching directory:" in msg
            ]
            assert len(dir_messages) > 0

            # Check for periodic progress messages
            periodic_messages = [
                msg
                for msg in progress_messages
                if "Processed" in msg and "items" in msg
            ]
            assert len(periodic_messages) > 0

    def test_search_files_tool_progress(self):
        """Test that SearchFilesTool reports progress during content search."""
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with searchable content
            for i in range(30):  # Enough to trigger progress
                test_file = temp_path / f"test_file_{i}.py"
                test_file.write_text(
                    f"# Test file {i}\nfunction test_{i}():\n    return 'search_target'\n"
                )

            # Create subdirectories
            for i in range(3):
                subdir = temp_path / f"subdir_{i}"
                subdir.mkdir()
                for j in range(10):
                    test_file = subdir / f"sub_test_{j}.py"
                    test_file.write_text(
                        f"# Sub test file {i}.{j}\ndef sub_function():\n    return 'search_target'\n"
                    )

            # Test the tool directly
            tool = SearchFilesTool()

            # Create search parameters
            search_params = {
                "pattern": "search_target",
                "search_pattern": None,
                "use_regex": False,
                "case_sensitive": True,
                "file_pattern": "*.py",
                "max_file_size": 10 * 1024 * 1024,
                "max_depth": 5,
                "include_line_numbers": True,
                "context_lines": 0,
                "limit": None,
                "progress_callback": progress_callback,
            }

            results = []
            counters = {"files_searched": 0, "files_with_matches": 0}

            # Call the internal search method
            tool._search_directory_for_content(
                temp_path, search_params, results, counters
            )

            # Check that progress messages were generated
            assert len(progress_messages) > 0

            # Check for expected progress message patterns
            dir_messages = [
                msg
                for msg in progress_messages
                if "Searching content in directory:" in msg
            ]
            assert len(dir_messages) > 0

    @pytest.mark.asyncio
    async def test_execute_command_tool_progress(self):
        """Test that ExecuteCommandTool reports progress during execution."""
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Create a ToolContext with progress callback
        context = ToolContext()
        context.progress_callback = progress_callback

        # Test parameters as dict (required by validation decorator)
        params = {
            "command": "echo",
            "args": ["Hello", "World"],
            "timeout": 10,
            "capture_output": True,
        }

        # Execute the tool
        tool = ExecuteCommandTool()
        await tool.initialize()

        result = await tool.execute(params, context)

        await tool.shutdown()

        # Check execution was successful
        assert result.success

        # Check that progress messages were generated
        assert len(progress_messages) >= 3

        # Check for expected progress messages
        start_messages = [
            msg for msg in progress_messages if "Starting command execution:" in msg
        ]
        assert len(start_messages) > 0

        executing_messages = [
            msg
            for msg in progress_messages
            if "Creating subprocess" in msg or "Process started" in msg
        ]
        assert len(executing_messages) > 0

        completed_messages = [
            msg for msg in progress_messages if "Command completed" in msg
        ]
        assert len(completed_messages) > 0

    def test_progress_callback_access_from_context(self):
        """Test that tools can properly access progress callback from context."""
        progress_messages = []

        def progress_callback(message: str):
            progress_messages.append(message)

        # Create context with progress callback
        context = ToolContext()
        context.progress_callback = progress_callback

        # Test that callback can be retrieved
        retrieved_callback = getattr(context, "progress_callback", None)
        assert retrieved_callback is not None
        assert callable(retrieved_callback)

        # Test calling the callback
        retrieved_callback("Test message")
        assert len(progress_messages) == 1
        assert progress_messages[0] == "Test message"

    def test_progress_callback_none_handling(self):
        """Test that tools handle missing progress callback gracefully."""
        # Create context without progress callback
        context = ToolContext()

        # Test that None is returned when no callback is set
        retrieved_callback = getattr(context, "progress_callback", None)
        assert retrieved_callback is None

        # Verify this doesn't break tool execution (should not raise exception)
        if retrieved_callback:
            retrieved_callback("This should not be called")

    def test_tool_context_extensibility(self):
        """Test that ToolContext can be extended with progress callback."""
        context = ToolContext()

        # Progress callback should be settable
        def test_callback(message):
            pass

        context.progress_callback = test_callback

        # Should be retrievable
        assert hasattr(context, "progress_callback")
        assert context.progress_callback == test_callback
