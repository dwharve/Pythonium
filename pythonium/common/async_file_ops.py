"""
Async file operations utility module for improved performance.

This module provides high-performance async file operations using aiofiles.
Designed to be a drop-in replacement for synchronous file operations in tools.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import aiofiles
import aiofiles.os

from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class AsyncFileError(PythoniumError):
    """Base exception for async file operations."""

    pass


class AsyncFileService:
    """Service for async file operations with aiofiles integration."""

    def __init__(self):
        """Initialize the async file service."""

    async def read_text(
        self,
        file_path: Union[str, Path],
        encoding: str = "utf-8",
        max_size: Optional[int] = None,
    ) -> str:
        """Read text content from a file asynchronously.

        Args:
            file_path: Path to the file to read
            encoding: Text encoding to use (default: utf-8)
            max_size: Maximum file size in bytes (optional)

        Returns:
            File content as string

        Raises:
            AsyncFileError: If file operation fails
        """
        file_path = Path(file_path)

        try:
            # Check file size if limit specified
            if max_size is not None:
                stat = await aiofiles.os.stat(file_path)
                file_size = stat.st_size

                if file_size > max_size:
                    raise AsyncFileError(
                        f"File too large: {file_size} bytes > {max_size} bytes"
                    )

            # Read file content
            async with aiofiles.open(file_path, "r", encoding=encoding) as f:
                content: str = await f.read()

            return content

        except UnicodeDecodeError as e:
            raise AsyncFileError(
                f"Failed to decode file with encoding {encoding}: {e}"
            ) from e
        except PermissionError as e:
            raise AsyncFileError(f"Permission denied reading file: {file_path}") from e
        except FileNotFoundError as e:
            raise AsyncFileError(f"File not found: {file_path}") from e
        except OSError as e:
            raise AsyncFileError(f"OS error reading file: {e}") from e

    async def write_text(
        self,
        file_path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
        append: bool = False,
        create_dirs: bool = False,
    ) -> Dict[str, Any]:
        """Write text content to a file asynchronously.

        Args:
            file_path: Path where to write the file
            content: Text content to write
            encoding: Text encoding to use (default: utf-8)
            append: Whether to append to existing file (default: False)
            create_dirs: Whether to create parent directories (default: False)

        Returns:
            Dictionary with file operation results

        Raises:
            AsyncFileError: If file operation fails
        """
        file_path = Path(file_path)

        try:
            # Create parent directories if needed
            if create_dirs and not file_path.parent.exists():
                await aiofiles.os.makedirs(file_path.parent, exist_ok=True)

            # Write content to file
            mode = "a" if append else "w"
            async with aiofiles.open(str(file_path), mode=mode, encoding=encoding) as f:  # type: ignore[call-overload]
                await f.write(content)

            # Get file info
            stat = await aiofiles.os.stat(file_path)
            file_size = stat.st_size

            return {
                "path": str(file_path),
                "size": file_size,
                "encoding": encoding,
                "append": append,
                "lines": len(content.splitlines()),
                "characters": len(content),
            }

        except PermissionError as e:
            raise AsyncFileError(
                f"Permission denied writing to file: {file_path}"
            ) from e
        except OSError as e:
            raise AsyncFileError(f"OS error writing file: {e}") from e

    async def copy_file(
        self,
        src_path: Union[str, Path],
        dst_path: Union[str, Path],
        create_dirs: bool = False,
    ) -> Dict[str, Any]:
        """Copy a file asynchronously.

        Args:
            src_path: Source file path
            dst_path: Destination file path
            create_dirs: Whether to create parent directories (default: False)

        Returns:
            Dictionary with copy operation results

        Raises:
            AsyncFileError: If copy operation fails
        """
        src_path = Path(src_path)
        dst_path = Path(dst_path)

        try:
            # Create parent directories if needed
            if create_dirs and not dst_path.parent.exists():
                await aiofiles.os.makedirs(dst_path.parent, exist_ok=True)

            # Read source and write to destination
            async with aiofiles.open(src_path, "rb") as src:
                async with aiofiles.open(dst_path, "wb") as dst:
                    await dst.write(await src.read())

            # Get file info
            stat = await aiofiles.os.stat(dst_path)
            file_size = stat.st_size

            return {
                "src_path": str(src_path),
                "dst_path": str(dst_path),
                "size": file_size,
            }

        except FileNotFoundError as e:
            raise AsyncFileError(f"Source file not found: {src_path}") from e
        except PermissionError as e:
            raise AsyncFileError(
                f"Permission denied copying file: {src_path} -> {dst_path}"
            ) from e
        except OSError as e:
            raise AsyncFileError(f"OS error copying file: {e}") from e

    async def delete_file(
        self, file_path: Union[str, Path], missing_ok: bool = False
    ) -> Dict[str, Any]:
        """Delete a file asynchronously.

        Args:
            file_path: Path to the file to delete
            missing_ok: Don't raise error if file doesn't exist (default: False)

        Returns:
            Dictionary with delete operation results

        Raises:
            AsyncFileError: If delete operation fails
        """
        file_path = Path(file_path)

        try:
            # Check if file exists
            try:
                stat = await aiofiles.os.stat(file_path)
                file_size = stat.st_size
                existed = True
            except FileNotFoundError:
                if missing_ok:
                    return {"path": str(file_path), "existed": False}
                raise AsyncFileError(f"File not found: {file_path}")

            # Delete the file
            await aiofiles.os.remove(file_path)

            return {
                "path": str(file_path),
                "existed": existed,
                "size": file_size if existed else 0,
            }

        except PermissionError as e:
            raise AsyncFileError(f"Permission denied deleting file: {file_path}") from e
        except OSError as e:
            raise AsyncFileError(f"OS error deleting file: {e}") from e

    async def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get file information asynchronously.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information

        Raises:
            AsyncFileError: If getting file info fails
        """
        file_path = Path(file_path)

        try:
            stat = await aiofiles.os.stat(file_path)

            return {
                "path": str(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
                "exists": True,
            }

        except FileNotFoundError:
            return {
                "path": str(file_path),
                "exists": False,
            }
        except OSError as e:
            raise AsyncFileError(f"OS error getting file info: {e}") from e


# Global instance for easy access
async_file_service = AsyncFileService()
