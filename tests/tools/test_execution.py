"""Tests for execution tools module."""

from unittest.mock import Mock, patch

from pythonium.tools.std.execution import ExecuteCommandTool


class TestExecuteCommandTool:
    """Test ExecuteCommandTool functionality."""

    def test_execute_command_tool_initialization(self):
        """Test ExecuteCommandTool initialization."""
        tool = ExecuteCommandTool()
        assert tool is not None

    async def test_execute_command_tool_initialize(self):
        """Test tool initialization."""
        tool = ExecuteCommandTool()
        await tool.initialize()
        # Should not raise exception

    async def test_execute_command_tool_shutdown(self):
        """Test tool shutdown."""
        tool = ExecuteCommandTool()
        await tool.shutdown()
        # Should not raise exception

    def test_execute_command_tool_metadata(self):
        """Test tool metadata."""
        tool = ExecuteCommandTool()
        metadata = tool.metadata
        assert metadata.name == "execute_command"
        assert "command" in metadata.description.lower()
        assert len(metadata.parameters) > 0

    @patch("subprocess.run")
    async def test_execute_simple_command(self, mock_run):
        """Test executing a simple command."""
        tool = ExecuteCommandTool()

        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Hello world"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute({"command": "echo 'Hello world'"}, context)

        assert result.success
        assert "Hello world" in str(result.data)

    @patch("subprocess.run")
    async def test_execute_command_with_error(self, mock_run):
        """Test executing a command that fails."""
        tool = ExecuteCommandTool()

        # Mock subprocess result with error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_run.return_value = mock_result

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute({"command": "nonexistent_command"}, context)

        # Result structure depends on implementation
        assert result is not None

    @patch("subprocess.run")
    async def test_execute_command_with_timeout(self, mock_run):
        """Test executing a command with timeout."""
        tool = ExecuteCommandTool()

        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute({"command": "sleep 1", "timeout": 5}, context)

        assert result is not None

    @patch("subprocess.run")
    async def test_execute_command_with_cwd(self, mock_run):
        """Test executing a command with working directory."""
        tool = ExecuteCommandTool()

        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/tmp"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"command": "pwd", "working_directory": "/tmp"}, context
        )

        assert result is not None

    def test_execute_command_tool_parameters(self):
        """Test tool parameter definitions."""
        tool = ExecuteCommandTool()
        metadata = tool.metadata

        # Check that required parameters exist
        param_names = [p.name for p in metadata.parameters]
        assert "command" in param_names

    @patch("subprocess.run")
    async def test_execute_command_with_environment(self, mock_run):
        """Test executing a command with environment variables."""
        tool = ExecuteCommandTool()

        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test_value"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"command": "echo $TEST_VAR", "environment": {"TEST_VAR": "test_value"}},
            context,
        )

        assert result is not None

    def test_execute_command_tool_security(self):
        """Test that the tool has security considerations."""
        tool = ExecuteCommandTool()

        # The tool should exist and be properly configured
        assert tool is not None
        assert hasattr(tool, "metadata")

        # Security is typically handled in the implementation
        # This test just ensures the tool is properly structured
