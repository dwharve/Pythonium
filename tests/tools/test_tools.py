"""
Tests for the tools package.
"""

import asyncio
import platform
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythonium.tools.base import ParameterType, ToolContext, ToolParameter
from pythonium.tools.std.execution import ExecuteCommandTool
from pythonium.tools.std.file_ops import (
    DeleteFileTool,
    FindFilesTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)


# Shared fixtures at module level to eliminate duplication
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tool_context():
    """Create a basic tool context."""
    return ToolContext(
        user_id="test_user",
        session_id="test_session",
        permissions={"tool_execution": True},
    )


class TestBaseTool:
    """Test the base tool framework."""

    def test_parameter_schema_generation(self):
        """Test parameter schema generation for MCP compliance."""
        # Test parameter with various constraints
        param = ToolParameter(
            name="test_param",
            type=ParameterType.STRING,
            description="Test parameter for schema generation",
            required=True,
            min_length=2,
            max_length=10,
            pattern=r"^[a-zA-Z]+$",
            allowed_values=["option1", "option2", "option3"],
        )

        # Verify parameter attributes are set correctly for schema generation
        assert param.name == "test_param"
        assert param.type == ParameterType.STRING
        assert param.required is True
        assert param.min_length == 2
        assert param.max_length == 10
        assert param.pattern == r"^[a-zA-Z]+$"
        assert param.allowed_values == ["option1", "option2", "option3"]

    def test_parameter_type_mapping(self):
        """Test parameter type mapping for JSON Schema compliance."""
        # Test different parameter types
        string_param = ToolParameter(
            name="string_param",
            type=ParameterType.STRING,
            description="String parameter",
        )
        assert string_param.type.value == "string"

        number_param = ToolParameter(
            name="number_param",
            type=ParameterType.NUMBER,
            description="Number parameter",
        )
        assert number_param.type.value == "number"

        path_param = ToolParameter(
            name="path_param",
            type=ParameterType.PATH,
            description="Path parameter",
        )
        assert path_param.type.value == "string"

        url_param = ToolParameter(
            name="url_param",
            type=ParameterType.URL,
            description="URL parameter",
        )
        assert url_param.type.value == "string"


class TestFilesystemTools:
    """Test filesystem tools."""

    @pytest.mark.asyncio
    async def test_create_file_tool(self, temp_dir, tool_context):
        """Test file creation with WriteFileTool."""
        tool = WriteFileTool()
        test_file = temp_dir / "test.txt"

        # Test basic file creation with empty content
        result = await tool.run({"path": test_file, "content": ""}, tool_context)

        assert result.success
        assert test_file.exists()
        assert result.data["path"] == str(test_file)

    @pytest.mark.asyncio
    async def test_write_file_tool(self, temp_dir, tool_context):
        """Test file writing tool."""
        tool = WriteFileTool()
        test_file = temp_dir / "write_test.txt"
        content = "Hello, World!\nThis is a test file."

        result = await tool.run(
            {"path": test_file, "content": content, "overwrite": True},
            tool_context,
        )

        assert result.success
        assert test_file.exists()
        assert test_file.read_text() == content
        assert result.metadata["lines"] == 2
        assert result.metadata["characters"] == len(content)

    @pytest.mark.asyncio
    async def test_read_file_tool(self, temp_dir, tool_context):
        """Test file reading tool."""
        # Create test file
        test_file = temp_dir / "read_test.txt"
        content = "Hello, World!\nThis is a test file."
        test_file.write_text(content)

        tool = ReadFileTool()
        result = await tool.run({"path": test_file}, tool_context)

        assert result.success
        assert result.data["content"] == content
        assert result.data["path"] == str(test_file)
        assert result.metadata["lines"] == 2
        assert result.metadata["characters"] == len(content)

    @pytest.mark.asyncio
    async def test_delete_file_tool(self, temp_dir, tool_context):
        """Test file deletion tool."""
        # Create test file
        test_file = temp_dir / "delete_test.txt"
        test_file.write_text("Test content")

        tool = DeleteFileTool()
        result = await tool.run({"path": test_file}, tool_context)

        assert result.success
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_find_files_tool(self, temp_dir, tool_context):
        """Test file finding tool."""
        # Create test structure
        (temp_dir / "test1.txt").write_text("content")
        (temp_dir / "test2.py").write_text("content")
        (temp_dir / "other.doc").write_text("content")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "test3.txt").write_text("content")

        tool = FindFilesTool()
        result = await tool.run(
            {"path": temp_dir, "name_pattern": "*.txt", "file_type": "file"},
            tool_context,
        )

        assert result.success
        txt_files = [
            item for item in result.data["results"] if item["name"].endswith(".txt")
        ]
        assert len(txt_files) >= 1  # Should find at least one .txt file

    @pytest.mark.asyncio
    async def test_search_files_tool(self, temp_dir, tool_context):
        """Test file content search tool."""
        # Create test files with searchable content
        (temp_dir / "file1.txt").write_text("Hello world\nThis is a test\nHello again")
        (temp_dir / "file2.txt").write_text("Different content\nNo matches here")
        (temp_dir / "file3.py").write_text("print('Hello world')\n# Hello comment")

        tool = SearchFilesTool()
        result = await tool.run(
            {
                "path": temp_dir,
                "pattern": "Hello",
                "include_line_numbers": True,
            },
            tool_context,
        )

        assert result.success
        assert (
            len(result.data["matches"]) >= 3
        )  # Should find multiple "Hello" instances
        assert result.metadata["files_with_matches"] >= 2

        # Check that line numbers are included
        for match in result.data["matches"]:
            assert "line_number" in match


class TestToolIntegration:
    """Test tool integration and workflows."""

    @pytest.mark.asyncio
    async def test_file_workflow(self, temp_dir, tool_context):
        """Test a complete file manipulation workflow."""
        # Step 1: Create a file with WriteFileTool
        create_tool = WriteFileTool()
        test_file = temp_dir / "workflow_test.txt"

        result = await create_tool.run({"path": test_file, "content": ""}, tool_context)
        assert result.success

        # Step 2: Write content
        write_tool = WriteFileTool()
        content = "Initial content\nLine 2\nLine 3"

        result = await write_tool.run(
            {"path": test_file, "content": content, "overwrite": True},
            tool_context,
        )
        assert result.success

        # Step 3: Read and verify
        read_tool = ReadFileTool()
        result = await read_tool.run({"path": test_file}, tool_context)
        assert result.success
        assert result.data["content"] == content

        # Step 4: Search for content
        search_tool = SearchFilesTool()
        result = await search_tool.run(
            {"path": temp_dir, "pattern": "Line 2", "file_pattern": "*.txt"},
            tool_context,
        )
        assert result.success
        assert len(result.data["matches"]) == 1

        # Step 5: Delete file
        delete_tool = DeleteFileTool()
        result = await delete_tool.run({"path": test_file}, tool_context)
        assert result.success
        assert not test_file.exists()


class TestExecuteCommandTool:
    """Test the enhanced ExecuteCommandTool with security features."""

    @pytest.mark.asyncio
    async def test_tool_initialization(self, tool_context):
        """Test tool initialization and metadata."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        # Check metadata
        metadata = tool.metadata
        assert metadata.name == "execute_command"
        assert metadata.dangerous is True
        assert "async" in metadata.tags

        # Check parameters
        param_names = [p.name for p in metadata.parameters]
        expected_params = [
            "command",
            "args",
            "working_directory",
            "timeout",
            "capture_output",
            "shell",
            "environment",
            "stdin",
        ]
        for param in expected_params:
            assert param in param_names

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_simple_command_execution(self, tool_context):
        """Test executing a simple command."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            # Use a cross-platform command
            if platform.system() == "Windows":
                command = "echo hello"
            else:
                command = "echo hello"

            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # Mock process
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"hello\n", b"")
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {
                        "command": command,
                        "timeout": 10,
                        "capture_output": True,
                        "shell": False,
                    },
                    tool_context,
                )

                assert result.success is True
                assert result.data["returncode"] == 0
                assert "hello" in result.data["stdout"]
                assert result.data["pid"] == 12345
                assert "execution_time" in result.data
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, tool_context):
        """Test command timeout handling."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # Mock process that times out
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.communicate.side_effect = asyncio.TimeoutError()
                mock_process.terminate = MagicMock()  # Synchronous method
                mock_process.wait = AsyncMock()
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {
                        "command": "sleep 100",
                        "timeout": 1,
                        "capture_output": True,
                    },
                    tool_context,
                )

                assert result.success is False
                assert "timed out" in result.error.lower()
                mock_process.terminate.assert_called_once()
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_working_directory_validation(self, tool_context):
        """Test working directory validation."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            # Test with non-existent directory
            result = await tool.execute(
                {
                    "command": "echo hello",
                    "working_directory": "/non/existent/directory",
                    "timeout": 10,
                },
                tool_context,
            )

            assert result.success is False
            assert "does not exist" in result.error
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_parameter_validation(self, tool_context):
        """Test parameter validation."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            # Test empty command
            result = await tool.execute(
                {
                    "command": "",
                    "timeout": 10,
                },
                tool_context,
            )
            assert result.success is False
            assert "empty" in result.error.lower()

            # Test invalid timeout
            result = await tool.execute(
                {
                    "command": "echo hello",
                    "timeout": 500,  # Exceeds max of 300
                },
                tool_context,
            )
            assert result.success is False
            assert "less than or equal to 300" in result.error
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_environment_variables(self, tool_context):
        """Test environment variable handling."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"test_value\n", b"")
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {
                        "command": (
                            "echo $TEST_VAR"
                            if platform.system() != "Windows"
                            else "echo %TEST_VAR%"
                        ),
                        "environment": {"TEST_VAR": "test_value"},
                        "timeout": 10,
                        "capture_output": True,
                    },
                    tool_context,
                )

                assert result.success is True
                # Check that subprocess was called with environment
                call_args = mock_subprocess.call_args
                assert "env" in call_args.kwargs
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_stdin_input(self, tool_context):
        """Test stdin input handling."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"input_received\n", b"")
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {
                        "command": "cat" if platform.system() != "Windows" else "type",
                        "stdin": "test input",
                        "timeout": 10,
                        "capture_output": True,
                    },
                    tool_context,
                )

                assert result.success is True
                # Check that communicate was called with stdin data
                mock_process.communicate.assert_called_once_with(input=b"test input")
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_output_capture_modes(self, tool_context):
        """Test different output capture modes."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        try:
            # Test with output capture
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = 0
                mock_process.communicate.return_value = (
                    b"stdout_content\n",
                    b"stderr_content\n",
                )
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {
                        "command": "echo hello",
                        "capture_output": True,
                        "timeout": 10,
                    },
                    tool_context,
                )

                assert result.success is True
                assert "stdout" in result.data
                assert "stderr" in result.data
                assert "stdout_size" in result.data
                assert "stderr_size" in result.data

            # Test without output capture
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = 0
                mock_process.wait.return_value = None
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {
                        "command": "echo hello",
                        "capture_output": False,
                        "timeout": 10,
                    },
                    tool_context,
                )

                assert result.success is True
                assert "stdout" not in result.data
                assert "stderr" not in result.data
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_process_cleanup(self, tool_context):
        """Test proper process cleanup on shutdown."""
        tool = ExecuteCommandTool()
        await tool.initialize()

        # Simulate a running process
        mock_process = AsyncMock()
        mock_process.returncode = None  # Still running
        mock_process.terminate = MagicMock()  # Synchronous method
        mock_process.kill = MagicMock()  # Synchronous method
        mock_process.wait = AsyncMock()

        tool._running_processes["test_process"] = mock_process

        # Shutdown should clean up processes
        await tool.shutdown()

        mock_process.terminate.assert_called_once()
        assert len(tool._running_processes) == 0


if __name__ == "__main__":
    pytest.main([__file__])
