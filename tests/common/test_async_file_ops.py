"""
Tests for async file operations.
"""

import asyncio
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

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_content = "Hello, World!\nThis is a test file."
            f.write(test_content)
            f.flush()

            # Test reading the file
            content = await service.read_text(f.name)
            assert content == test_content

            # Clean up
            Path(f.name).unlink()

    @pytest.mark.asyncio
    async def test_write_file_text(self):
        """Test writing text files asynchronously."""
        service = AsyncFileService()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            test_content = "Test content for writing"

            # Test writing to the file
            await service.write_text(f.name, test_content)

            # Verify content was written
            with open(f.name, "r") as read_file:
                content = read_file.read()
                assert content == test_content

            # Clean up
            Path(f.name).unlink()

    @pytest.mark.asyncio
    async def test_file_info(self):
        """Test getting file info asynchronously."""
        service = AsyncFileService()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_content = "12345"  # 5 bytes
            f.write(test_content)
            f.flush()

            # Test getting file info
            info = await service.get_file_info(f.name)
            assert info["size"] == 5
            assert "modified" in info
            assert "is_file" in info
            assert info["is_file"] is True

            # Clean up
            Path(f.name).unlink()

    @pytest.mark.asyncio
    async def test_copy_file(self):
        """Test copying files asynchronously."""
        service = AsyncFileService()

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as src:
            test_content = "Content to copy"
            src.write(test_content)
            src.flush()

            with tempfile.NamedTemporaryFile(delete=False) as dst:
                dst_path = dst.name

            # Remove destination file (we just wanted the name)
            Path(dst_path).unlink()

            # Test copying file
            await service.copy_file(src.name, dst_path)

            # Verify copy was successful
            assert Path(dst_path).exists()
            with open(dst_path, "r") as f:
                copied_content = f.read()
                assert copied_content == test_content

            # Clean up
            Path(src.name).unlink()
            Path(dst_path).unlink()

    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test deleting files asynchronously."""
        service = AsyncFileService()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = f.name

            # Verify file exists
            assert Path(file_path).exists()

            # Test deleting file
            await service.delete_file(file_path)
            assert not Path(file_path).exists()

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
