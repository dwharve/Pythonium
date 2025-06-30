"""
File operation tools for basic file manipulation with async support.
"""

import os
from pathlib import Path
from typing import Any

from pythonium.common.async_file_ops import AsyncFileError, async_file_service
from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.parameter_validation import (
    CreateFileParams,
    DeleteFileParams,
    ReadFileParams,
    WriteFileParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)


class ReadFileTool(BaseTool):
    """Tool for reading file contents."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read and return the complete contents of a text file. Handles various file encodings and supports reading code files (Python, JavaScript, etc.), configuration files, documentation, logs, and other text-based files. Includes safety limits to prevent reading extremely large files.",
            brief_description="Read the contents of a text file",
            detailed_description="Read and return the complete contents of a text file. Handles various file encodings and supports reading code files (Python, JavaScript, etc.), configuration files, documentation, logs, and other text-based files. Includes safety limits to prevent reading extremely large files. Supports encoding detection and provides detailed error messages for common issues like permission denied, file not found, or binary files.",
            category="filesystem",
            tags=["file", "read", "content", "text", "code", "config", "logs"],
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.PATH,
                    description="Path to the file to read (absolute or relative path)",
                    required=True,
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="Text encoding of the file (utf-8, ascii, latin-1, etc.)",
                    default="utf-8",
                ),
                ToolParameter(
                    name="max_size",
                    type=ParameterType.INTEGER,
                    description="Maximum file size to read in bytes (default 10MB for safety)",
                    default=10 * 1024 * 1024,  # 10MB
                    min_value=1,
                ),
            ],
        )

    @validate_parameters(ReadFileParams)
    @handle_tool_error
    async def execute(
        self, params: ReadFileParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file read operation with async support."""
        file_path = Path(params.path)
        encoding = params.encoding
        max_size = params.max_size

        try:
            # Check if file exists
            if not file_path.exists():
                raise ToolExecutionError(f"File does not exist: {file_path}")

            # Check if it's a file (not directory)
            if not file_path.is_file():
                raise ToolExecutionError(f"Path is not a file: {file_path}")

            # Use async file service for improved performance
            content = await async_file_service.read_text(
                file_path, encoding=encoding, max_size=max_size
            )

            # Get file info
            file_info = await async_file_service.get_file_info(file_path)

            return Result[Any].success_result(
                data={
                    "content": content,
                    "path": str(file_path),
                    "size": file_info["size"],
                    "encoding": encoding,
                },
                metadata={
                    "lines": len(content.splitlines()),
                    "characters": len(content),
                    "modified": file_info["modified"],
                },
            )

        except AsyncFileError as e:
            # Convert async file errors to tool execution errors
            raise ToolExecutionError(str(e)) from e
            raise ToolExecutionError(f"OS error reading file: {e}")


class WriteFileTool(BaseTool):
    """Tool for writing content to a file."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write text content to a file, creating it if it doesn't exist or overwriting existing content. Useful for creating new files, saving generated code, writing configuration files, creating documentation, or updating existing files. Creates parent directories if they don't exist.",
            brief_description="Write text content to a file",
            detailed_description="Write text content to a file, creating it if it doesn't exist or overwriting existing content. Useful for creating new files, saving generated code, writing configuration files, creating documentation, or updating existing files. Creates parent directories if they don't exist. Supports various text encodings, optional backup creation, and permission handling. Provides detailed error messages for common issues like permission denied, disk full, or invalid paths.",
            category="filesystem",
            tags=["file", "write", "create", "save", "generate", "update"],
            dangerous=True,  # File modification is potentially dangerous
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.PATH,
                    description="Path where the file will be written (absolute or relative path)",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="Text content to write to the file",
                    required=True,
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="File encoding",
                    default="utf-8",
                ),
                ToolParameter(
                    name="create_dirs",
                    type=ParameterType.BOOLEAN,
                    description="Create parent directories if they don't exist",
                    default=False,
                ),
                ToolParameter(
                    name="overwrite",
                    type=ParameterType.BOOLEAN,
                    description="Overwrite file if it exists",
                    default=False,
                ),
            ],
        )

    @validate_parameters(WriteFileParams)
    @handle_tool_error
    async def execute(
        self, params: WriteFileParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file write operation with async support."""
        file_path = Path(params.path)
        content = params.content
        encoding = params.encoding
        append_mode = params.append
        overwrite = params.overwrite
        create_dirs = params.create_dirs

        try:
            # Check if file exists and overwrite/append mode
            if file_path.exists() and not overwrite and not append_mode:
                raise ToolExecutionError(
                    f"File already exists and overwrite=False: {file_path}"
                )

            # Use async file service for improved performance
            result = await async_file_service.write_text(
                file_path,
                content,
                encoding=encoding,
                append=append_mode,
                create_dirs=create_dirs,
            )

            return Result[Any].success_result(
                data={
                    "path": result["path"],
                    "size": result["size"],
                    "encoding": result["encoding"],
                    "append": result["append"],
                },
                metadata={
                    "lines": result["lines"],
                    "characters": result["characters"],
                },
            )

        except AsyncFileError as e:
            # Convert async file errors to tool execution errors
            raise ToolExecutionError(str(e)) from e


class DeleteFileTool(BaseTool):
    """Tool for deleting files."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="delete_file",
            description="Permanently delete a file from the filesystem. Use with caution as this action cannot be undone. Useful for cleaning up temporary files, removing outdated files, or maintaining file system hygiene. Always verify the file path before deletion.",
            brief_description="Permanently delete a file from the filesystem",
            detailed_description="Permanently delete a file from the filesystem. Takes 'path' (required) as the file location to delete, and 'force' (boolean, default False) to override read-only permissions. Use with caution as this action cannot be undone. Useful for cleaning up temporary files, removing outdated files, or maintaining file system hygiene. Always verify the file path before deletion.",
            category="filesystem",
            tags=["file", "delete", "remove", "cleanup", "permanent"],
            dangerous=True,  # File deletion is dangerous
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.PATH,
                    description="Path to the file to delete",
                    required=True,
                ),
                ToolParameter(
                    name="force",
                    type=ParameterType.BOOLEAN,
                    description="Force deletion even if file is read-only",
                    default=False,
                ),
            ],
        )

    @handle_tool_error
    @validate_parameters(DeleteFileParams)
    async def execute(
        self, params: DeleteFileParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file delete operation."""
        file_path = Path(params.path)
        force = params.force

        try:
            # Check if file exists
            if not file_path.exists():
                raise ToolExecutionError(f"File does not exist: {file_path}")

            # Check if it's a file (not directory)
            if not file_path.is_file():
                raise ToolExecutionError(f"Path is not a file: {file_path}")

            # Get file info before deletion
            file_size = file_path.stat().st_size

            # Handle read-only files
            if force and not os.access(file_path, os.W_OK):
                file_path.chmod(0o666)  # Make writable

            # Delete the file
            file_path.unlink()

            return Result[Any].success_result(
                data={
                    "path": str(file_path),
                    "size": file_size,
                    "forced": force,
                },
            )

        except PermissionError:
            raise ToolExecutionError(f"Permission denied deleting file: {file_path}")
        except OSError as e:
            raise ToolExecutionError(f"OS error deleting file: {e}")


class CreateFileTool(BaseTool):
    """Tool for creating empty files."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_file",
            description="Create a new empty file at the specified path. Similar to 'touch' command - useful for creating placeholder files, initializing new files before writing content, or creating files that will be populated later. Creates parent directories if they don't exist.",
            brief_description="Create a new empty file at the specified path",
            detailed_description="Create a new empty file at the specified path. Takes 'path' (required) for the file location, 'create_dirs' (boolean, default False) to create parent directories if needed, and 'overwrite' (boolean, default False) to replace existing files. Similar to 'touch' command - useful for creating placeholder files, initializing new files before writing content, or creating files that will be populated later.",
            category="filesystem",
            tags=[
                "file",
                "create",
                "touch",
                "empty",
                "initialize",
                "placeholder",
            ],
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.PATH,
                    description="Path where the new empty file will be created",
                    required=True,
                ),
                ToolParameter(
                    name="create_dirs",
                    type=ParameterType.BOOLEAN,
                    description="Create parent directories if they don't exist",
                    default=False,
                ),
                ToolParameter(
                    name="overwrite",
                    type=ParameterType.BOOLEAN,
                    description="Overwrite file if it exists",
                    default=False,
                ),
            ],
        )

    @handle_tool_error
    @validate_parameters(CreateFileParams)
    async def execute(
        self, params: CreateFileParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file creation operation."""
        file_path = Path(params.path)
        create_dirs = params.create_dirs
        overwrite = params.overwrite
        content = params.content or ""

        try:
            # Check if file exists and overwrite flag
            if file_path.exists() and not overwrite:
                raise ToolExecutionError(
                    f"File already exists and overwrite=False: {file_path}"
                )

            # Create parent directories if needed
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            elif not file_path.parent.exists():
                raise ToolExecutionError(
                    f"Parent directory does not exist: {file_path.parent}"
                )

            # Create file with content
            if content:
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.touch()

            return Result[Any].success_result(
                data={"path": str(file_path), "created_dirs": create_dirs}
            )

        except PermissionError:
            raise ToolExecutionError(f"Permission denied creating file: {file_path}")
        except OSError as e:
            raise ToolExecutionError(f"OS error creating file: {e}")
