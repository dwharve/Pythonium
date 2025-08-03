"""import os
import tempfile
from pathlib import Path

import pytest

from pythonium.common.async_file_ops import AsyncFileService for async file operations.
"""

import os
import tempfile
from pathlib import Path

import pytest

from pythonium.common.async_file_ops import AsyncFileError, AsyncFileService


class TestAsyncFileService:
    """Test async file service functionality."""

    @pytest.mark.asyncio
    async def test_read_file_text(self):
        """Test reading text files asynchronously."""
        service = AsyncFileService()

        # Create a temporary file path
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
        temp_path = temp_file.name

        try:
            # Write test content and close the file
            test_content = "Hello, World!\nThis is a test file."
            temp_file.write(test_content)
            temp_file.close()  # Explicitly close before reading

            # Test reading the file
            content = await service.read_text(temp_path)
            assert content == test_content

        finally:
            # Clean up - with error handling
            try:
                if os.path.exists(temp_path):
                    Path(temp_path).unlink()
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not delete temporary file {temp_path}: {e}")

    @pytest.mark.asyncio
    async def test_write_file_text(self):
        """Test writing text files asynchronously."""
        service = AsyncFileService()

        # Create a temporary file path
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        temp_path = temp_file.name
        temp_file.close()  # Close immediately

        try:
            test_content = "Test content for writing"

            # Test writing to the file
            await service.write_text(temp_path, test_content)

            # Verify content was written
            with open(temp_path, "r") as read_file:
                content = read_file.read()
                assert content == test_content

        finally:
            # Clean up - with error handling
            try:
                if os.path.exists(temp_path):
                    Path(temp_path).unlink()
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not delete temporary file {temp_path}: {e}")

    @pytest.mark.asyncio
    async def test_file_info(self):
        """Test getting file info asynchronously."""
        service = AsyncFileService()

        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        temp_path = temp_file.name

        try:
            test_content = "12345"  # 5 bytes
            temp_file.write(test_content)
            temp_file.flush()
            temp_file.close()  # Close the file explicitly

            # Test getting file info
            info = await service.get_file_info(temp_path)
            assert info["size"] == 5
            assert "modified" in info
            assert "is_file" in info
            assert info["is_file"] is True

        finally:
            # Clean up - with error handling
            try:
                if os.path.exists(temp_path):
                    Path(temp_path).unlink()
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not delete temporary file {temp_path}: {e}")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in async file operations."""
        service = AsyncFileService()

        # Test reading non-existent file
        with pytest.raises(AsyncFileError):
            await service.read_text("/non/existent/file.txt")

        # Test getting info of non-existent file - this returns a dict with exists=False
        info = await service.get_file_info("/non/existent/file.txt")
        assert info["exists"] is False
