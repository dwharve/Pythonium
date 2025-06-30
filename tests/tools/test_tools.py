"""
Tests for the tools package.
"""

import tempfile
from pathlib import Path

import pytest

from pythonium.tools import (
    CreateFileTool,
    DeleteFileTool,
    FindFilesTool,
    ParameterType,
    ReadFileTool,
    SearchFilesTool,
    ToolContext,
    ToolParameter,
    ToolValidationError,
    WriteFileTool,
)


class TestBaseTool:
    """Test the base tool framework."""

    def test_parameter_validation(self):
        """Test parameter validation."""
        # String parameter
        param = ToolParameter(
            name="test_str",
            type=ParameterType.STRING,
            description="Test string parameter",
            required=True,
            min_length=2,
            max_length=10,
        )

        # Valid value
        assert param.validate_value("hello") == "hello"

        # Too short
        with pytest.raises(ToolValidationError):
            param.validate_value("a")

        # Too long
        with pytest.raises(ToolValidationError):
            param.validate_value("a" * 11)

        # Missing required
        with pytest.raises(ToolValidationError):
            param.validate_value(None)

    def test_number_validation(self):
        """Test number parameter validation."""
        param = ToolParameter(
            name="test_num",
            type=ParameterType.INTEGER,
            description="Test number parameter",
            min_value=0,
            max_value=100,
        )

        assert param.validate_value(50) == 50
        assert param.validate_value("25") == 25

        with pytest.raises(ToolValidationError):
            param.validate_value(-1)

        with pytest.raises(ToolValidationError):
            param.validate_value(101)

    def test_boolean_validation(self):
        """Test boolean parameter validation."""
        param = ToolParameter(
            name="test_bool",
            type=ParameterType.BOOLEAN,
            description="Test boolean parameter",
        )

        assert param.validate_value(True) is True
        assert param.validate_value("true") is True
        assert param.validate_value("false") is False
        assert param.validate_value(0) is False
        assert param.validate_value(1) is True

    def test_allowed_values(self):
        """Test allowed values constraint."""
        param = ToolParameter(
            name="test_choice",
            type=ParameterType.STRING,
            description="Test choice parameter",
            allowed_values=["option1", "option2", "option3"],
        )

        assert param.validate_value("option1") == "option1"

        with pytest.raises(ToolValidationError):
            param.validate_value("invalid")


class TestFilesystemTools:
    """Test filesystem tools."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def tool_context(self):
        """Create a basic tool context."""
        return ToolContext(
            user_id="test_user",
            session_id="test_session",
            permissions={"tool_execution": True},
        )

    @pytest.mark.asyncio
    async def test_create_file_tool(self, temp_dir, tool_context):
        """Test file creation tool."""
        tool = CreateFileTool()
        test_file = temp_dir / "test.txt"

        # Test basic file creation
        result = await tool.run({"path": test_file}, tool_context)

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

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def tool_context(self):
        """Create a basic tool context."""
        return ToolContext(
            user_id="test_user",
            session_id="test_session",
            permissions={"tool_execution": True},
        )

    @pytest.mark.asyncio
    async def test_file_workflow(self, temp_dir, tool_context):
        """Test a complete file manipulation workflow."""
        # Step 1: Create a file
        create_tool = CreateFileTool()
        test_file = temp_dir / "workflow_test.txt"

        result = await create_tool.run({"path": test_file}, tool_context)
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


if __name__ == "__main__":
    pytest.main([__file__])
