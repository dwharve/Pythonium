"""Simple tests for filesystem module."""

import tempfile
from pathlib import Path

import pytest

from pythonium.common.filesystem import (  # Add utility functions
    FileInfo,
    FileManager,
    FileOperation,
    calculate_file_hash,
    copy_file,
    delete_file,
    ensure_directory,
    find_files,
    get_available_space,
    get_file_manager,
    get_file_size,
    is_text_file,
    list_directory,
    move_file,
    safe_path_join,
    temporary_directory,
    temporary_file,
)


class TestFileOperation:
    """Test FileOperation enum."""

    def test_file_operation_values(self):
        """Test FileOperation enum values."""
        assert FileOperation.CREATED.value == "created"
        assert FileOperation.MODIFIED.value == "modified"
        assert FileOperation.DELETED.value == "deleted"
        assert FileOperation.MOVED.value == "moved"


class TestFileInfo:
    """Test FileInfo class functionality."""

    def test_file_info_from_existing_file(self, tmp_path):
        """Test creating FileInfo from existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        file_info = FileInfo.from_path(test_file)
        assert file_info.path == test_file
        assert file_info.is_file
        assert not file_info.is_dir
        assert file_info.size > 0
        assert file_info.name == "test.txt"

    def test_file_info_from_directory(self, tmp_path):
        """Test creating FileInfo from directory."""
        file_info = FileInfo.from_path(tmp_path)
        assert file_info.path == tmp_path
        assert not file_info.is_file
        assert file_info.is_dir
        assert file_info.name == tmp_path.name


class TestFileManager:
    """Test FileManager functionality."""

    def test_file_manager_initialization(self):
        """Test FileManager can be initialized."""
        manager = FileManager()
        assert manager is not None

    def test_file_manager_cache_size(self):
        """Test FileManager with custom cache size."""
        manager = FileManager(cache_size=500)
        assert manager is not None

    def test_get_file_info(self, tmp_path):
        """Test getting file info through FileManager."""
        manager = FileManager()
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        file_info = manager.get_file_info(test_file)
        assert file_info.path == test_file
        assert file_info.is_file

    def test_clear_cache(self):
        """Test clearing the file cache."""
        manager = FileManager()
        manager.clear_cache()
        # Should not raise exception


class TestGlobalFileManager:
    """Test global file manager functionality."""

    def test_get_global_file_manager(self):
        """Test getting global file manager instance."""
        manager1 = get_file_manager()
        manager2 = get_file_manager()
        assert manager1 is manager2  # Should be the same instance


class TestFilesystemUtilities:
    """Test filesystem utility functions."""

    def test_safe_path_join(self):
        """Test safe path joining."""
        result = safe_path_join("path1", "path2", "file.txt")
        assert isinstance(result, Path)
        assert str(result).endswith("file.txt")

    def test_ensure_directory(self, tmp_path):
        """Test directory creation."""
        new_dir = tmp_path / "new_directory"
        result = ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_copy_file(self, tmp_path):
        """Test file copying."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("test content")

        copy_file(source, dest)
        assert dest.exists()
        assert dest.read_text() == "test content"

    def test_move_file(self, tmp_path):
        """Test file moving."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("test content")

        move_file(source, dest)
        assert dest.exists()
        assert not source.exists()
        assert dest.read_text() == "test content"

    def test_delete_file(self, tmp_path):
        """Test file deletion."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("content")

        result = delete_file(test_file)
        assert result is True
        assert not test_file.exists()

    def test_delete_nonexistent_file(self, tmp_path):
        """Test deleting nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"
        result = delete_file(nonexistent, missing_ok=True)
        assert result is False

    def test_calculate_file_hash(self, tmp_path):
        """Test file hash calculation."""
        test_file = tmp_path / "hash_test.txt"
        test_file.write_text("test content for hashing")

        hash_result = calculate_file_hash(test_file, "md5")
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 hash length

    def test_get_file_size(self, tmp_path):
        """Test getting file size."""
        test_file = tmp_path / "size_test.txt"
        content = "test content"
        test_file.write_text(content)

        size = get_file_size(test_file)
        assert size == len(content.encode())

    def test_get_available_space(self, tmp_path):
        """Test getting available disk space."""
        space = get_available_space(tmp_path)
        assert isinstance(space, int)
        assert space > 0

    def test_list_directory(self, tmp_path):
        """Test directory listing."""
        # Create some test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()

        items = list_directory(tmp_path)
        assert len(items) >= 3  # At least the files and directory we created

    def test_find_files(self, tmp_path):
        """Test file finding with patterns."""
        # Create test files
        (tmp_path / "test1.txt").write_text("content")
        (tmp_path / "test2.txt").write_text("content")
        (tmp_path / "other.log").write_text("content")

        txt_files = find_files(tmp_path, pattern="*.txt")
        assert len(txt_files) >= 2

        all_files = find_files(tmp_path, pattern="*")
        assert len(all_files) >= 3

    def test_is_text_file(self, tmp_path):
        """Test text file detection."""
        # Create a text file
        text_file = tmp_path / "text.txt"
        text_file.write_text("This is a text file")

        assert is_text_file(text_file) is True

        # Create a binary file
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        assert is_text_file(binary_file) is False

    def test_temporary_directory(self):
        """Test temporary directory creation."""
        with temporary_directory() as temp_dir:
            assert temp_dir.exists()
            assert temp_dir.is_dir()

        # Directory should be cleaned up after context
        assert not temp_dir.exists()

    def test_temporary_file(self):
        """Test temporary file creation."""
        with temporary_file(suffix=".txt") as (temp_file_obj, temp_file_path):
            assert temp_file_path.exists()
            temp_file_obj.close()  # Close file object before using path
            temp_file_path.write_text("temporary content")
            assert temp_file_path.read_text() == "temporary content"

        # File should be cleaned up after context
        assert not temp_file_path.exists()


class TestFilesystemErrorHandling:
    """Test error handling in filesystem operations."""

    def test_safe_path_join_empty(self):
        """Test safe path join with empty input."""
        # Test that it raises an appropriate error for empty input
        with pytest.raises(IndexError):
            safe_path_join()

    def test_ensure_directory_existing(self, tmp_path):
        """Test ensuring existing directory."""
        result = ensure_directory(tmp_path)
        assert result == tmp_path
        assert result.exists()

    def test_get_file_size_nonexistent(self, tmp_path):
        """Test getting size of nonexistent file."""
        nonexistent = tmp_path / "nonexistent.txt"
        from pythonium.common.filesystem import (
            FileNotFoundError as PythoniumFileNotFoundError,
        )

        with pytest.raises(PythoniumFileNotFoundError):
            get_file_size(nonexistent)
