"""
File system utilities for the Pythonium framework.

This module provides comprehensive file and directory operations,
path utilities, and file watching capabilities.
"""

import asyncio
import hashlib
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)

from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger
from pythonium.common.types import MetadataDict

logger = get_logger(__name__)


class FileSystemError(PythoniumError):
    """Base exception for file system operations."""

    pass


class FileNotFoundError(FileSystemError):
    """Exception raised when file is not found."""

    pass


class PermissionError(FileSystemError):
    """Exception raised when permission is denied."""

    pass


class DiskSpaceError(FileSystemError):
    """Exception raised when disk space is insufficient."""

    pass


class FileOperation(Enum):
    """File operations for watching."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileInfo:
    """Information about a file or directory."""

    path: Path
    name: str
    size: int
    is_file: bool
    is_dir: bool
    is_symlink: bool
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    permissions: int
    owner: Optional[str] = None
    group: Optional[str] = None
    mime_type: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha256: Optional[str] = None
    metadata: MetadataDict = field(default_factory=dict)

    @classmethod
    def from_path(
        cls, path: Union[str, Path], include_hashes: bool = False
    ) -> "FileInfo":
        """Create FileInfo from a path."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        stat_result = path.stat()

        # Get timestamps
        created_at = datetime.fromtimestamp(stat_result.st_ctime)
        modified_at = datetime.fromtimestamp(stat_result.st_mtime)
        accessed_at = datetime.fromtimestamp(stat_result.st_atime)

        # Get owner/group info (Unix only)
        owner = None
        group = None
        try:
            import grp
            import pwd

            owner = pwd.getpwuid(stat_result.st_uid).pw_name
            group = grp.getgrgid(stat_result.st_gid).gr_name
        except (ImportError, KeyError):
            pass

        # Get MIME type
        mime_type = None
        try:
            import mimetypes

            mime_type, _ = mimetypes.guess_type(str(path))
        except ImportError:
            pass

        # Calculate hashes for files
        hash_md5 = None
        hash_sha256 = None
        if include_hashes and path.is_file():
            hash_md5 = calculate_file_hash(path, "md5")
            hash_sha256 = calculate_file_hash(path, "sha256")

        return cls(
            path=path,
            name=path.name,
            size=stat_result.st_size,
            is_file=path.is_file(),
            is_dir=path.is_dir(),
            is_symlink=path.is_symlink(),
            created_at=created_at,
            modified_at=modified_at,
            accessed_at=accessed_at,
            permissions=stat_result.st_mode,
            owner=owner,
            group=group,
            mime_type=mime_type,
            hash_md5=hash_md5,
            hash_sha256=hash_sha256,
        )


@dataclass
class FileEvent:
    """File system event."""

    operation: FileOperation
    path: Path
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: MetadataDict = field(default_factory=dict)


class FileWatcher(ABC):
    """Abstract base class for file watchers."""

    def __init__(self, path: Union[str, Path], recursive: bool = True):
        self.path = Path(path)
        self.recursive = recursive
        self._callbacks: List[Callable[[FileEvent], None]] = []
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start watching for file changes."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop watching for file changes."""
        pass

    def add_callback(self, callback: Callable[[FileEvent], None]) -> None:
        """Add a callback for file events."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[FileEvent], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, event: FileEvent) -> None:
        """Notify all callbacks of an event."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in file watcher callback: {e}")


class PollingFileWatcher(FileWatcher):
    """File watcher using polling (cross-platform)."""

    def __init__(
        self,
        path: Union[str, Path],
        recursive: bool = True,
        poll_interval: float = 1.0,
    ):
        super().__init__(path, recursive)
        self.poll_interval = poll_interval
        self._file_states: Dict[Path, float] = {}
        self._watch_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start polling for file changes."""
        if self._running:
            return

        self._running = True
        self._scan_initial_state()
        self._watch_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop polling."""
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

    def _scan_initial_state(self) -> None:
        """Scan initial file states."""
        self._file_states.clear()

        if self.path.is_file():
            self._file_states[self.path] = self.path.stat().st_mtime
        elif self.path.is_dir():
            for file_path in self._iter_files():
                try:
                    self._file_states[file_path] = file_path.stat().st_mtime
                except (OSError, IOError):
                    pass

    def _iter_files(self) -> Iterator[Path]:
        """Iterate over files to watch."""
        if self.recursive:
            yield from self.path.rglob("*")
        else:
            yield from self.path.iterdir()

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._check_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")

    async def _check_changes(self) -> None:
        """Check for file changes."""
        current_states = {}

        # Check existing files
        for file_path in self._iter_files():
            try:
                current_mtime = file_path.stat().st_mtime
                current_states[file_path] = current_mtime

                if file_path in self._file_states:
                    # Check for modification
                    if current_mtime != self._file_states[file_path]:
                        event = FileEvent(FileOperation.MODIFIED, file_path)
                        self._notify_callbacks(event)
                else:
                    # New file
                    event = FileEvent(FileOperation.CREATED, file_path)
                    self._notify_callbacks(event)

            except (OSError, IOError):
                # File might have been deleted
                if file_path in self._file_states:
                    event = FileEvent(FileOperation.DELETED, file_path)
                    self._notify_callbacks(event)

        # Check for deleted files
        for file_path in self._file_states:
            if file_path not in current_states:
                event = FileEvent(FileOperation.DELETED, file_path)
                self._notify_callbacks(event)

        self._file_states = current_states


def safe_path_join(*paths: Union[str, Path]) -> Path:
    """Safely join paths, preventing directory traversal attacks."""
    base_path = Path(paths[0]).resolve()

    for path_part in paths[1:]:
        # Convert to Path and resolve any relative components
        part = Path(path_part)
        if part.is_absolute():
            raise FileSystemError(f"Absolute path not allowed: {path_part}")

        # Check for directory traversal attempts
        if ".." in part.parts:
            raise FileSystemError(f"Directory traversal not allowed: {path_part}")

        base_path = base_path / part

    return base_path.resolve()


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
    """Ensure directory exists, creating it if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    return path


def copy_file(
    src: Union[str, Path],
    dst: Union[str, Path],
    preserve_metadata: bool = True,
) -> Path:
    """Copy a file with optional metadata preservation."""
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    # Ensure destination directory exists
    ensure_directory(dst_path.parent)

    # Copy file
    if preserve_metadata:
        shutil.copy2(src_path, dst_path)
    else:
        shutil.copy(src_path, dst_path)

    return dst_path


def move_file(src: Union[str, Path], dst: Union[str, Path]) -> Path:
    """Move a file or directory."""
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source not found: {src_path}")

    # Ensure destination directory exists
    ensure_directory(dst_path.parent)

    shutil.move(str(src_path), str(dst_path))
    return dst_path


def delete_file(path: Union[str, Path], missing_ok: bool = True) -> bool:
    """Delete a file or directory."""
    path = Path(path)

    if not path.exists():
        if missing_ok:
            return False
        raise FileNotFoundError(f"Path not found: {path}")

    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True
    except OSError as e:
        raise FileSystemError(f"Failed to delete {path}: {e}") from e


def calculate_file_hash(path: Union[str, Path], algorithm: str = "sha256") -> str:
    """Calculate hash of a file."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    hash_obj = hashlib.new(algorithm)

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def get_file_size(path: Union[str, Path]) -> int:
    """Get size of a file in bytes."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        total_size = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    else:
        return 0


def get_available_space(path: Union[str, Path]) -> int:
    """Get available disk space in bytes."""
    path = Path(path)

    try:
        disk_stat = shutil.disk_usage(path)
        return disk_stat.free
    except OSError as e:
        raise FileSystemError(f"Failed to get disk usage: {e}") from e


def list_directory(
    path: Union[str, Path],
    pattern: Optional[str] = None,
    recursive: bool = False,
    include_hidden: bool = False,
) -> List[FileInfo]:
    """List directory contents with filtering options."""
    path = Path(path)

    if not path.is_dir():
        raise FileSystemError(f"Path is not a directory: {path}")

    files = []

    try:
        if recursive:
            iterator = path.rglob(pattern or "*")
        else:
            iterator = path.glob(pattern or "*")

        for item in iterator:
            # Skip hidden files if not requested
            if not include_hidden and item.name.startswith("."):
                continue

            try:
                file_info = FileInfo.from_path(item)
                files.append(file_info)
            except Exception as e:
                logger.warning(f"Failed to get info for {item}: {e}")

    except OSError as e:
        raise FileSystemError(f"Failed to list directory: {e}") from e

    return files


def find_files(
    path: Union[str, Path],
    pattern: str = "*",
    file_type: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    modified_after: Optional[datetime] = None,
    modified_before: Optional[datetime] = None,
) -> List[Path]:
    """Find files matching specified criteria."""
    path = Path(path)
    matching_files = []

    for file_path in path.rglob(pattern):
        if not file_path.is_file():
            continue

        # Check file type
        if file_type:
            if file_type == "text" and not is_text_file(file_path):
                continue
            elif file_type == "binary" and is_text_file(file_path):
                continue

        # Check size constraints
        if min_size is not None or max_size is not None:
            size = file_path.stat().st_size
            if min_size is not None and size < min_size:
                continue
            if max_size is not None and size > max_size:
                continue

        # Check modification time constraints
        if modified_after is not None or modified_before is not None:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if modified_after is not None and mtime < modified_after:
                continue
            if modified_before is not None and mtime > modified_before:
                continue

        matching_files.append(file_path)

    return matching_files


def is_text_file(path: Union[str, Path], sample_size: int = 1024) -> bool:
    """Check if a file is likely a text file."""
    path = Path(path)

    if not path.is_file():
        return False

    try:
        with open(path, "rb") as f:
            sample = f.read(sample_size)

        # Check for null bytes (common in binary files)
        if b"\x00" in sample:
            return False

        # Try to decode as text
        try:
            sample.decode("utf-8")
            return True
        except UnicodeDecodeError:
            try:
                sample.decode("latin-1")
                return True
            except UnicodeDecodeError:
                return False

    except OSError:
        return False


@contextmanager
def temporary_directory(prefix: str = "pythonium_", cleanup: bool = True):
    """Context manager for temporary directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield temp_dir
    finally:
        if cleanup:
            shutil.rmtree(temp_dir, ignore_errors=True)


@contextmanager
def temporary_file(
    suffix: str = "",
    prefix: str = "pythonium_",
    mode: str = "w+b",
    delete: bool = True,
):
    """Context manager for temporary file."""
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    temp_file = None

    try:
        temp_file = open(fd, mode)
        yield temp_file, Path(temp_path)
    finally:
        if temp_file:
            temp_file.close()
        elif fd:
            os.close(fd)

        if delete:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@asynccontextmanager
async def file_lock(path: Union[str, Path], timeout: float = 10.0):
    """Async file locking context manager."""
    lock_path = Path(str(path) + ".lock")

    # Try to acquire lock
    start_time = asyncio.get_event_loop().time()
    while True:
        try:
            # Create lock file exclusively
            with open(lock_path, "x") as f:
                f.write(str(os.getpid()))
            break
        except FileExistsError:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise FileSystemError(f"Failed to acquire lock for {path}")
            await asyncio.sleep(0.1)

    try:
        yield
    finally:
        # Release lock
        try:
            lock_path.unlink()
        except OSError:
            pass


class FileManager:
    """High-level file manager with caching and monitoring."""

    def __init__(self, cache_size: int = 1000):
        self._cache: Dict[Path, FileInfo] = {}
        self._cache_size = cache_size
        self._watchers: Dict[Path, FileWatcher] = {}

    def get_file_info(self, path: Union[str, Path], use_cache: bool = True) -> FileInfo:
        """Get file information with optional caching."""
        path = Path(path)

        if use_cache and path in self._cache:
            return self._cache[path]

        file_info = FileInfo.from_path(path)

        if use_cache:
            # Implement simple LRU by removing oldest entries
            if len(self._cache) >= self._cache_size:
                # Remove 10% of oldest entries
                to_remove = len(self._cache) // 10
                for _ in range(to_remove):
                    self._cache.pop(next(iter(self._cache)))

            self._cache[path] = file_info

        return file_info

    async def watch_directory(
        self,
        path: Union[str, Path],
        callback: Callable[[FileEvent], None],
        recursive: bool = True,
    ) -> FileWatcher:
        """Start watching a directory for changes."""
        path = Path(path)

        if path in self._watchers:
            watcher = self._watchers[path]
        else:
            watcher = PollingFileWatcher(path, recursive)
            self._watchers[path] = watcher
            await watcher.start()

        watcher.add_callback(callback)
        return watcher

    async def stop_watching(self, path: Union[str, Path]) -> None:
        """Stop watching a directory."""
        path = Path(path)

        if path in self._watchers:
            watcher = self._watchers[path]
            await watcher.stop()
            del self._watchers[path]

    async def stop_all_watchers(self) -> None:
        """Stop all file watchers."""
        for watcher in self._watchers.values():
            await watcher.stop()
        self._watchers.clear()

    def clear_cache(self) -> None:
        """Clear the file info cache."""
        self._cache.clear()


# Global file manager instance
_global_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """Get the global file manager instance."""
    global _global_file_manager
    if _global_file_manager is None:
        _global_file_manager = FileManager()
    return _global_file_manager
