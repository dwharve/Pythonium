"""
Async file operation utilities for the Pythonium framework.

This module provides async file I/O utilities using aiofiles for better performance
in async environments and non-blocking file operations.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import aiofiles  # type: ignore
    import aiofiles.os  # type: ignore

    HAS_AIOFILES = True
except ImportError:
    aiofiles = None
    HAS_AIOFILES = False

from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class AsyncFileError(PythoniumError):
    """Base exception for async file operations."""

    pass


class AsyncFileNotFoundError(AsyncFileError):
    """Exception raised when file is not found."""

    pass


class AsyncFilePermissionError(AsyncFileError):
    """Exception raised when file permission is denied."""

    pass


class AsyncFileUtils:
    """Async file operation utilities."""

    @staticmethod
    async def read_text(
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        max_size: Optional[int] = None,
    ) -> str:
        """
        Read text content from a file asynchronously.

        Args:
            file_path: Path to the file to read
            encoding: Text encoding to use
            max_size: Maximum file size in bytes (None for no limit)

        Returns:
            File content as string

        Raises:
            AsyncFileNotFoundError: If file doesn't exist
            AsyncFilePermissionError: If permission denied
            AsyncFileError: For other file operation errors
        """
        file_path = Path(file_path)

        try:
            # Check file exists and is readable
            if not file_path.exists():
                raise AsyncFileNotFoundError(f"File does not exist: {file_path}")

            if not file_path.is_file():
                raise AsyncFileError(f"Path is not a file: {file_path}")

            # Check file size if limit specified
            if max_size is not None:
                file_size = file_path.stat().st_size
                if file_size > max_size:
                    raise AsyncFileError(
                        f"File too large: {file_size} bytes > {max_size} bytes"
                    )

            # Use aiofiles if available, fallback to sync
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, mode="r", encoding=encoding) as f:
                    content: str = await f.read()
            else:
                # Fallback to synchronous read
                logger.warning("aiofiles not available, using synchronous file read")
                content = file_path.read_text(encoding=encoding)

            return content

        except FileNotFoundError:
            raise AsyncFileNotFoundError(f"File does not exist: {file_path}")
        except PermissionError:
            raise AsyncFilePermissionError(
                f"Permission denied reading file: {file_path}"
            )
        except UnicodeDecodeError as e:
            raise AsyncFileError(f"Failed to decode file with encoding {encoding}: {e}")
        except OSError as e:
            raise AsyncFileError(f"OS error reading file: {e}")

    @staticmethod
    async def write_text(
        file_path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
        append: bool = False,
        create_dirs: bool = False,
    ) -> Dict[str, Any]:
        """
        Write text content to a file asynchronously.

        Args:
            file_path: Path to the file to write
            content: Text content to write
            encoding: Text encoding to use
            append: Whether to append to existing file
            create_dirs: Whether to create parent directories

        Returns:
            Dictionary with operation details

        Raises:
            AsyncFilePermissionError: If permission denied
            AsyncFileError: For other file operation errors
        """
        file_path = Path(file_path)

        try:
            # Create parent directories if requested
            if create_dirs and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            elif not file_path.parent.exists():
                raise AsyncFileError(
                    f"Parent directory does not exist: {file_path.parent}"
                )

            # Determine write mode
            mode = "a" if append else "w"

            # Use aiofiles if available, fallback to sync
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, mode=mode, encoding=encoding) as f:
                    await f.write(content)
            else:
                # Fallback to synchronous write
                logger.warning("aiofiles not available, using synchronous file write")
                if append:
                    with open(file_path, "a", encoding=encoding) as f:
                        f.write(content)
                else:
                    file_path.write_text(content, encoding=encoding)

            # Get file stats
            file_size = file_path.stat().st_size

            return {
                "path": str(file_path),
                "size": file_size,
                "encoding": encoding,
                "append_mode": append,
                "created_dirs": create_dirs,
            }

        except PermissionError:
            raise AsyncFilePermissionError(
                f"Permission denied writing file: {file_path}"
            )
        except OSError as e:
            raise AsyncFileError(f"OS error writing file: {e}")

    @staticmethod
    async def read_bytes(
        file_path: Union[str, Path], max_size: Optional[int] = None
    ) -> bytes:
        """
        Read binary content from a file asynchronously.

        Args:
            file_path: Path to the file to read
            max_size: Maximum file size in bytes (None for no limit)

        Returns:
            File content as bytes

        Raises:
            AsyncFileNotFoundError: If file doesn't exist
            AsyncFilePermissionError: If permission denied
            AsyncFileError: For other file operation errors
        """
        file_path = Path(file_path)

        try:
            # Check file exists and is readable
            if not file_path.exists():
                raise AsyncFileNotFoundError(f"File does not exist: {file_path}")

            if not file_path.is_file():
                raise AsyncFileError(f"Path is not a file: {file_path}")

            # Check file size if limit specified
            if max_size is not None:
                file_size = file_path.stat().st_size
                if file_size > max_size:
                    raise AsyncFileError(
                        f"File too large: {file_size} bytes > {max_size} bytes"
                    )

            # Use aiofiles if available, fallback to sync
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, mode="rb") as f:
                    content: bytes = await f.read()
            else:
                # Fallback to synchronous read
                logger.warning("aiofiles not available, using synchronous file read")
                content = file_path.read_bytes()

            return content

        except FileNotFoundError:
            raise AsyncFileNotFoundError(f"File does not exist: {file_path}")
        except PermissionError:
            raise AsyncFilePermissionError(
                f"Permission denied reading file: {file_path}"
            )
        except OSError as e:
            raise AsyncFileError(f"OS error reading file: {e}")

    @staticmethod
    async def write_bytes(
        file_path: Union[str, Path],
        content: bytes,
        append: bool = False,
        create_dirs: bool = False,
    ) -> Dict[str, Any]:
        """
        Write binary content to a file asynchronously.

        Args:
            file_path: Path to the file to write
            content: Binary content to write
            append: Whether to append to existing file
            create_dirs: Whether to create parent directories

        Returns:
            Dictionary with operation details

        Raises:
            AsyncFilePermissionError: If permission denied
            AsyncFileError: For other file operation errors
        """
        file_path = Path(file_path)

        try:
            # Create parent directories if requested
            if create_dirs and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            elif not file_path.parent.exists():
                raise AsyncFileError(
                    f"Parent directory does not exist: {file_path.parent}"
                )

            # Determine write mode
            mode = "ab" if append else "wb"

            # Use aiofiles if available, fallback to sync
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, mode=mode) as f:
                    await f.write(content)
            else:
                # Fallback to synchronous write
                logger.warning("aiofiles not available, using synchronous file write")
                if append:
                    with open(file_path, "ab") as f:
                        f.write(content)
                else:
                    file_path.write_bytes(content)

            # Get file stats
            file_size = file_path.stat().st_size

            return {
                "path": str(file_path),
                "size": file_size,
                "append_mode": append,
                "created_dirs": create_dirs,
            }

        except PermissionError:
            raise AsyncFilePermissionError(
                f"Permission denied writing file: {file_path}"
            )
        except OSError as e:
            raise AsyncFileError(f"OS error writing file: {e}")

    @staticmethod
    async def file_exists(file_path: Union[str, Path]) -> bool:
        """Check if a file exists asynchronously."""
        if HAS_AIOFILES:
            try:
                result: bool = await aiofiles.os.path.exists(file_path)
                return result
            except Exception:
                # Fallback to sync check
                return Path(file_path).exists()
        else:
            return Path(file_path).exists()

    @staticmethod
    async def file_stats(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get file statistics asynchronously."""
        file_path = Path(file_path)

        try:
            if HAS_AIOFILES:
                stat_result = await aiofiles.os.stat(file_path)
            else:
                stat_result = file_path.stat()

            return {
                "size": stat_result.st_size,
                "modified": stat_result.st_mtime,
                "created": stat_result.st_ctime,
                "mode": stat_result.st_mode,
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
            }

        except FileNotFoundError:
            raise AsyncFileNotFoundError(f"File does not exist: {file_path}")
        except PermissionError:
            raise AsyncFilePermissionError(
                f"Permission denied accessing file: {file_path}"
            )
        except OSError as e:
            raise AsyncFileError(f"OS error getting file stats: {e}")


# Convenience functions for easy access
async def read_file_async(
    file_path: Union[str, Path], encoding: str = "utf-8", max_size: Optional[int] = None
) -> str:
    """Convenience function for async text file reading."""
    return await AsyncFileUtils.read_text(file_path, encoding, max_size)


async def write_file_async(
    file_path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    append: bool = False,
    create_dirs: bool = False,
) -> Dict[str, Any]:
    """Convenience function for async text file writing."""
    return await AsyncFileUtils.write_text(
        file_path, content, encoding, append, create_dirs
    )


async def read_bytes_async(
    file_path: Union[str, Path], max_size: Optional[int] = None
) -> bytes:
    """Convenience function for async binary file reading."""
    return await AsyncFileUtils.read_bytes(file_path, max_size)


async def write_bytes_async(
    file_path: Union[str, Path],
    content: bytes,
    append: bool = False,
    create_dirs: bool = False,
) -> Dict[str, Any]:
    """Convenience function for async binary file writing."""
    return await AsyncFileUtils.write_bytes(file_path, content, append, create_dirs)
