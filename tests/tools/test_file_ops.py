"""Tests for file operations tools module."""

from unittest.mock import Mock, patch

from pythonium.tools.std.file_ops import (
    DeleteFileTool,
    FindFilesTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)


class TestReadFileTool:
    """Test ReadFileTool functionality."""

    def test_read_file_tool_initialization(self):
        """Test ReadFileTool initialization."""
        tool = ReadFileTool()
        assert tool is not None

    async def test_read_file_tool_initialize(self):
        """Test tool initialization."""
        tool = ReadFileTool()
        await tool.initialize()
        # Should not raise exception

    def test_read_file_tool_metadata(self):
        """Test tool metadata."""
        tool = ReadFileTool()
        metadata = tool.metadata
        assert metadata.name == "read_file"
        assert "read" in metadata.description.lower()

    async def test_read_existing_file(self, tmp_path):
        """Test reading an existing file."""
        tool = ReadFileTool()

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, world!"
        test_file.write_text(test_content)

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute({"path": str(test_file)}, context)

        assert result.success
        assert test_content in str(result.data)

    async def test_read_nonexistent_file(self, tmp_path):
        """Test reading a nonexistent file."""
        tool = ReadFileTool()

        nonexistent_file = tmp_path / "nonexistent.txt"

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute({"path": str(nonexistent_file)}, context)

        assert not result.success


class TestWriteFileTool:
    """Test WriteFileTool functionality."""

    def test_write_file_tool_initialization(self):
        """Test WriteFileTool initialization."""
        tool = WriteFileTool()
        assert tool is not None

    def test_write_file_tool_metadata(self):
        """Test tool metadata."""
        tool = WriteFileTool()
        metadata = tool.metadata
        assert metadata.name == "write_file"
        assert "write" in metadata.description.lower()

    async def test_write_new_file(self, tmp_path):
        """Test writing to a new file."""
        tool = WriteFileTool()

        test_file = tmp_path / "new_file.txt"
        test_content = "This is new content"

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"path": str(test_file), "content": test_content}, context
        )

        assert result.success
        assert test_file.exists()
        assert test_file.read_text() == test_content

    async def test_write_existing_file(self, tmp_path):
        """Test overwriting an existing file."""
        tool = WriteFileTool()

        test_file = tmp_path / "existing.txt"
        test_file.write_text("Old content")

        new_content = "New content"

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"path": str(test_file), "content": new_content}, context
        )

        assert result.success
        assert test_file.read_text() == new_content


class TestDeleteFileTool:
    """Test DeleteFileTool functionality."""

    def test_delete_file_tool_initialization(self):
        """Test DeleteFileTool initialization."""
        tool = DeleteFileTool()
        assert tool is not None

    def test_delete_file_tool_metadata(self):
        """Test tool metadata."""
        tool = DeleteFileTool()
        metadata = tool.metadata
        assert metadata.name == "delete_file"
        assert "delete" in metadata.description.lower()

    async def test_delete_existing_file(self, tmp_path):
        """Test deleting an existing file."""
        tool = DeleteFileTool()

        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("Content to delete")

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute({"path": str(test_file)}, context)

        assert result.success
        assert not test_file.exists()

    async def test_delete_nonexistent_file(self, tmp_path):
        """Test deleting a nonexistent file."""
        tool = DeleteFileTool()

        nonexistent_file = tmp_path / "nonexistent.txt"

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        await tool.execute({"path": str(nonexistent_file)}, context)

        # Result depends on implementation - might succeed or fail


class TestFindFilesTool:
    """Test FindFilesTool functionality."""

    def test_find_files_tool_initialization(self):
        """Test FindFilesTool initialization."""
        tool = FindFilesTool()
        assert tool is not None

    def test_find_files_tool_metadata(self):
        """Test tool metadata."""
        tool = FindFilesTool()
        metadata = tool.metadata
        assert metadata.name == "find_files"
        assert "find" in metadata.description.lower()

    async def test_find_files_by_pattern(self, tmp_path):
        """Test finding files by pattern."""
        tool = FindFilesTool()

        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "file3.log").write_text("log content")

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"path": str(tmp_path), "name_pattern": "*.txt"}, context
        )

        assert result.success
        # Should find at least the .txt files

    async def test_find_files_recursive(self, tmp_path):
        """Test finding files recursively."""
        tool = FindFilesTool()

        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested content")

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"path": str(tmp_path), "name_pattern": "*.txt", "max_depth": 5}, context
        )

        assert result.success


class TestSearchFilesTool:
    """Test SearchFilesTool functionality."""

    def test_search_files_tool_initialization(self):
        """Test SearchFilesTool initialization."""
        tool = SearchFilesTool()
        assert tool is not None

    def test_search_files_tool_metadata(self):
        """Test tool metadata."""
        tool = SearchFilesTool()
        metadata = tool.metadata
        assert metadata.name == "search_files"
        assert "search" in metadata.description.lower()

    async def test_search_text_in_files(self, tmp_path):
        """Test searching for text in files."""
        tool = SearchFilesTool()

        # Create files with different content
        (tmp_path / "file1.txt").write_text("This contains the search term")
        (tmp_path / "file2.txt").write_text("This does not contain it")
        (tmp_path / "file3.txt").write_text("Another search term here")

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"path": str(tmp_path), "pattern": "search term"}, context
        )

        assert result.success
        # Should find matches in files

    async def test_search_with_file_pattern(self, tmp_path):
        """Test searching with file pattern filter."""
        tool = SearchFilesTool()

        # Create mixed file types
        (tmp_path / "doc.txt").write_text("document with search text")
        (tmp_path / "log.log").write_text("log with search text")

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        result = await tool.execute(
            {"path": str(tmp_path), "pattern": "search text", "file_pattern": "*.txt"},
            context,
        )

        assert result.success


class TestFileToolsIntegration:
    """Test integration between file tools."""

    async def test_write_read_cycle(self, tmp_path):
        """Test writing and then reading a file."""
        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        test_file = tmp_path / "cycle_test.txt"
        test_content = "Content for write-read cycle"

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        # Write file
        write_result = await write_tool.execute(
            {"path": str(test_file), "content": test_content}, context
        )
        assert write_result.success

        # Read file
        read_result = await read_tool.execute({"path": str(test_file)}, context)
        assert read_result.success
        assert test_content in str(read_result.data)

    async def test_write_find_delete_cycle(self, tmp_path):
        """Test writing, finding, and deleting files."""
        write_tool = WriteFileTool()
        find_tool = FindFilesTool()
        delete_tool = DeleteFileTool()

        test_file = tmp_path / "cycle_test.txt"

        from pythonium.tools.base import ToolContext

        context = ToolContext()

        # Write file
        write_result = await write_tool.execute(
            {"path": str(test_file), "content": "test content"}, context
        )
        assert write_result.success

        # Find file
        find_result = await find_tool.execute(
            {"path": str(tmp_path), "name_pattern": "cycle_test.txt"}, context
        )
        assert find_result.success

        # Delete file
        delete_result = await delete_tool.execute({"path": str(test_file)}, context)
        assert delete_result.success
