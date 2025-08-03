"""
File operation tools for basic file manipulation with async support.

This module provides essential file operations including reading, writing, deleting files,
finding files based on criteria, and searching file contents.
"""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pythonium.common.async_file_ops import AsyncFileError, async_file_service
from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.parameters import validate_parameters
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
)

from .parameters import (
    DeleteFileParams,
    FindFilesParams,
    ReadFileParams,
    SearchTextParams,
    WriteFileParams,
)


class ReadFileTool(BaseTool):
    """Tool for reading file contents with advanced line selection capabilities."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read file contents with line selection: ranges, specific lines, patterns, head/tail operations",
            brief_description="Read file contents with line selection",
            category="filesystem",
            tags=["file", "read", "lines", "text"],
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
                ToolParameter(
                    name="start_line",
                    type=ParameterType.INTEGER,
                    description="Starting line number for range reading (1-indexed)",
                    min_value=1,
                ),
                ToolParameter(
                    name="end_line",
                    type=ParameterType.INTEGER,
                    description="Ending line number for range reading (1-indexed)",
                    min_value=1,
                ),
                ToolParameter(
                    name="line_numbers",
                    type=ParameterType.ARRAY,
                    description="Specific line numbers to read (1-indexed)",
                ),
                ToolParameter(
                    name="line_pattern",
                    type=ParameterType.STRING,
                    description="Regex pattern to match lines (only matching lines returned)",
                ),
                ToolParameter(
                    name="head_lines",
                    type=ParameterType.INTEGER,
                    description="Read only the first N lines of the file",
                    min_value=1,
                ),
                ToolParameter(
                    name="tail_lines",
                    type=ParameterType.INTEGER,
                    description="Read only the last N lines of the file",
                    min_value=1,
                ),
                ToolParameter(
                    name="include_line_numbers",
                    type=ParameterType.BOOLEAN,
                    description="Include line numbers in the output",
                    default=False,
                ),
                ToolParameter(
                    name="strip_whitespace",
                    type=ParameterType.BOOLEAN,
                    description="Strip leading/trailing whitespace from each line",
                    default=False,
                ),
            ],
        )

    @validate_parameters(ReadFileParams)
    @handle_tool_error
    async def execute(
        self, params: ReadFileParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file read operation with advanced line selection."""
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

            # Read the entire file first
            content = await async_file_service.read_text(
                file_path, encoding=encoding, max_size=max_size
            )

            # Split into lines for processing
            all_lines = content.splitlines()
            total_lines = len(all_lines)

            # Apply line selection based on parameters
            selected_lines = self._select_lines(params, all_lines)

            # Process lines (add line numbers, strip whitespace)
            processed_lines = self._process_lines(params, selected_lines, all_lines)

            # Reconstruct content
            final_content = "\n".join(processed_lines) if processed_lines else ""

            # Get file info
            file_info = await async_file_service.get_file_info(file_path)

            return Result[Any].success_result(
                data={
                    "content": final_content,
                    "path": str(file_path),
                    "size": file_info["size"],
                    "encoding": encoding,
                    "lines_returned": len(processed_lines),
                    "total_lines": total_lines,
                },
                metadata={
                    "selection_type": self._get_selection_type(params),
                    "lines_selected": len(selected_lines),
                    "characters": len(final_content),
                    "modified": file_info["modified"],
                },
            )

        except AsyncFileError as e:
            # Convert async file errors to tool execution errors
            raise ToolExecutionError(str(e)) from e

    def _select_lines(
        self, params: ReadFileParams, all_lines: List[str]
    ) -> List[tuple]:
        """Select lines based on parameters. Returns list of (line_number, content) tuples."""
        if params.start_line is not None or params.end_line is not None:
            return self._select_line_range(params, all_lines)
        elif params.line_numbers is not None:
            return self._select_specific_lines(params, all_lines)
        elif params.line_pattern is not None:
            return self._select_pattern_lines(params, all_lines)
        elif params.head_lines is not None:
            return self._select_head_lines(params, all_lines)
        elif params.tail_lines is not None:
            return self._select_tail_lines(params, all_lines)
        else:
            # Return all lines
            return [(i + 1, line) for i, line in enumerate(all_lines)]

    def _select_line_range(
        self, params: ReadFileParams, all_lines: List[str]
    ) -> List[tuple]:
        """Select lines within a range."""
        start = (params.start_line or 1) - 1  # Convert to 0-indexed
        end = (params.end_line or len(all_lines)) - 1  # Convert to 0-indexed

        start = max(0, start)
        end = min(len(all_lines) - 1, end)

        return [(i + 1, all_lines[i]) for i in range(start, end + 1)]

    def _select_specific_lines(
        self, params: ReadFileParams, all_lines: List[str]
    ) -> List[tuple]:
        """Select specific line numbers."""
        if params.line_numbers is None:
            return []

        selected = []
        for line_num in params.line_numbers:
            if 1 <= line_num <= len(all_lines):
                selected.append((line_num, all_lines[line_num - 1]))
        return selected

    def _select_pattern_lines(
        self, params: ReadFileParams, all_lines: List[str]
    ) -> List[tuple]:
        """Select lines matching a regex pattern."""
        if params.line_pattern is None:
            return []

        import re

        flags = 0
        # Default to case-insensitive matching
        flags |= re.IGNORECASE

        pattern = re.compile(params.line_pattern, flags)
        selected = []

        for i, line in enumerate(all_lines):
            if pattern.search(line):
                selected.append((i + 1, line))

        return selected

    def _select_head_lines(
        self, params: ReadFileParams, all_lines: List[str]
    ) -> List[tuple]:
        """Select first N lines."""
        if params.head_lines is None:
            return []
        n = min(params.head_lines, len(all_lines))
        return [(i + 1, all_lines[i]) for i in range(n)]

    def _select_tail_lines(
        self, params: ReadFileParams, all_lines: List[str]
    ) -> List[tuple]:
        """Select last N lines."""
        if params.tail_lines is None:
            return []
        n = min(params.tail_lines, len(all_lines))
        start_idx = max(0, len(all_lines) - n)
        return [(i + 1, all_lines[i]) for i in range(start_idx, len(all_lines))]

    def _process_lines(
        self, params: ReadFileParams, selected_lines: List[tuple], all_lines: List[str]
    ) -> List[str]:
        """Process selected lines (add line numbers, strip whitespace)."""
        processed = []

        for line_num, line_content in selected_lines:
            if params.strip_whitespace:
                line_content = line_content.strip()

            if params.include_line_numbers:
                processed.append(f"{line_num:4d}: {line_content}")
            else:
                processed.append(line_content)

        return processed

    def _get_selection_type(self, params: ReadFileParams) -> str:
        """Get a string describing the selection type used."""
        if params.start_line is not None or params.end_line is not None:
            return "line_range"
        elif params.line_numbers is not None:
            return "specific_lines"
        elif params.line_pattern is not None:
            return "pattern_match"
        elif params.head_lines is not None:
            return "head"
        elif params.tail_lines is not None:
            return "tail"
        else:
            return "full_file"


class WriteFileTool(BaseTool):
    """Tool for writing and editing files with multiple write modes."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write/edit files with modes: write, append, prepend, insert, replace",
            brief_description="Write and edit file contents",
            category="filesystem",
            tags=["file", "write", "edit", "modify"],
            dangerous=True,
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
                    description="Text content to write/add to the file",
                    default="",
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="File encoding (utf-8, ascii, latin-1, etc.)",
                    default="utf-8",
                ),
                ToolParameter(
                    name="mode",
                    type=ParameterType.STRING,
                    description="Write mode: 'write' (overwrite), 'append', 'prepend', 'insert', 'replace'",
                    default="write",
                    allowed_values=["write", "append", "prepend", "insert", "replace"],
                ),
                ToolParameter(
                    name="insert_at_line",
                    type=ParameterType.INTEGER,
                    description="Line number to insert content at (1-indexed, required for 'insert' mode)",
                    min_value=1,
                ),
                ToolParameter(
                    name="replace_pattern",
                    type=ParameterType.STRING,
                    description="Regex pattern to find and replace (required for 'replace' mode)",
                ),
                ToolParameter(
                    name="replace_all",
                    type=ParameterType.BOOLEAN,
                    description="Replace all occurrences of pattern (default: first only)",
                    default=False,
                ),
                ToolParameter(
                    name="create_dirs",
                    type=ParameterType.BOOLEAN,
                    description="Create parent directories if they don't exist",
                    default=True,
                ),
                ToolParameter(
                    name="backup",
                    type=ParameterType.BOOLEAN,
                    description="Create backup of existing file before modification",
                    default=False,
                ),
            ],
        )

    @validate_parameters(WriteFileParams)
    @handle_tool_error
    async def execute(
        self, params: WriteFileParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file write operation with advanced editing capabilities."""
        file_path = Path(params.path)

        try:
            # Create backup if requested and file exists
            backup_path = None
            if params.backup and file_path.exists():
                backup_path = await self._create_backup(file_path, ".bak")

            # Process content based on mode
            if params.mode == "write":
                result = await self._write_content(file_path, params)
            elif params.mode == "append":
                result = await self._append_content(file_path, params)
            elif params.mode == "prepend":
                result = await self._prepend_content(file_path, params)
            elif params.mode == "insert":
                result = await self._insert_content(file_path, params)
            elif params.mode == "replace":
                result = await self._replace_content(file_path, params)
            else:
                raise ToolExecutionError(f"Unsupported write mode: {params.mode}")

            # Add backup information to result
            if backup_path:
                result["backup_created"] = str(backup_path)

            return Result[Any].success_result(
                data=result,
                metadata={
                    "mode": params.mode,
                    "backup_created": backup_path is not None,
                    "operation_type": "file_write",
                },
            )

        except AsyncFileError as e:
            # Convert async file errors to tool execution errors
            raise ToolExecutionError(str(e)) from e

    async def _create_backup(self, file_path: Path, backup_extension: str) -> Path:
        """Create a backup of the existing file."""
        backup_path = file_path.with_suffix(file_path.suffix + backup_extension)

        # Handle cases where backup already exists
        counter = 1
        while backup_path.exists():
            backup_path = file_path.with_suffix(
                f"{file_path.suffix}{backup_extension}.{counter}"
            )
            counter += 1

        # Copy the file
        content = await async_file_service.read_text(file_path)
        await async_file_service.write_text(backup_path, content, create_dirs=False)
        return backup_path

    async def _write_content(
        self, file_path: Path, params: WriteFileParams
    ) -> Dict[str, Any]:
        """Write content to file (overwrite mode)."""
        content = self._process_content(params.content, params)

        result = await async_file_service.write_text(
            file_path,
            content,
            encoding=params.encoding,
            append=False,
            create_dirs=params.create_dirs,
        )

        return {
            "path": result["path"],
            "size": result["size"],
            "encoding": result["encoding"],
            "lines": result["lines"],
            "characters": result["characters"],
            "mode": "write",
        }

    async def _append_content(
        self, file_path: Path, params: WriteFileParams
    ) -> Dict[str, Any]:
        """Append content to file."""
        content = self._process_content(params.content, params)

        result = await async_file_service.write_text(
            file_path,
            content,
            encoding=params.encoding,
            append=True,
            create_dirs=params.create_dirs,
        )

        return {
            "path": result["path"],
            "size": result["size"],
            "encoding": result["encoding"],
            "lines_added": result["lines"],
            "characters_added": result["characters"],
            "mode": "append",
        }

    async def _prepend_content(
        self, file_path: Path, params: WriteFileParams
    ) -> Dict[str, Any]:
        """Prepend content to beginning of file."""
        # Read existing content if file exists
        existing_content = ""
        if file_path.exists():
            existing_content = await async_file_service.read_text(
                file_path, encoding=params.encoding
            )

        # Combine new content with existing content
        new_content = self._process_content(params.content, params)
        combined_content = new_content + existing_content

        result = await async_file_service.write_text(
            file_path,
            combined_content,
            encoding=params.encoding,
            append=False,
            create_dirs=params.create_dirs,
        )

        return {
            "path": result["path"],
            "size": result["size"],
            "encoding": result["encoding"],
            "total_lines": result["lines"],
            "lines_prepended": len(new_content.splitlines()),
            "mode": "prepend",
        }

    async def _insert_content(
        self, file_path: Path, params: WriteFileParams
    ) -> Dict[str, Any]:
        """Insert content at specific line number."""
        # Read existing content
        if not file_path.exists():
            raise ToolExecutionError(
                f"Cannot insert into non-existent file: {file_path}"
            )

        existing_content = await async_file_service.read_text(
            file_path, encoding=params.encoding
        )
        lines = existing_content.splitlines()

        # Insert content at specified line
        if params.insert_at_line is None:
            raise ToolExecutionError("insert_at_line is required for insert mode")
        insert_line = params.insert_at_line - 1  # Convert to 0-indexed
        new_content_lines = self._process_content(params.content, params).splitlines()

        # Insert the new lines
        lines[insert_line:insert_line] = new_content_lines

        # Reconstruct content
        combined_content = "\n".join(lines)
        combined_content += "\n"

        result = await async_file_service.write_text(
            file_path,
            combined_content,
            encoding=params.encoding,
            append=False,
            create_dirs=params.create_dirs,
        )

        return {
            "path": result["path"],
            "size": result["size"],
            "encoding": result["encoding"],
            "total_lines": result["lines"],
            "lines_inserted": len(new_content_lines),
            "inserted_at_line": params.insert_at_line,
            "mode": "insert",
        }

    async def _replace_content(
        self, file_path: Path, params: WriteFileParams
    ) -> Dict[str, Any]:
        """Replace content using regex pattern."""
        import re

        # Read existing content
        if not file_path.exists():
            raise ToolExecutionError(
                f"Cannot replace in non-existent file: {file_path}"
            )

        existing_content = await async_file_service.read_text(
            file_path, encoding=params.encoding
        )

        # Prepare regex flags (default behavior)
        flags = 0

        # Compile pattern
        if params.replace_pattern is None:
            raise ToolExecutionError("replace_pattern is required for replace mode")
        pattern = re.compile(params.replace_pattern, flags)

        # Perform replacement
        replacement_content = self._process_content(params.content, params)

        if params.replace_all:
            new_content, count = pattern.subn(replacement_content, existing_content)
        else:
            new_content, count = pattern.subn(
                replacement_content, existing_content, count=1
            )

        if count == 0:
            raise ToolExecutionError(f"Pattern not found: {params.replace_pattern}")

        result = await async_file_service.write_text(
            file_path,
            new_content,
            encoding=params.encoding,
            append=False,
            create_dirs=params.create_dirs,
        )

        return {
            "path": result["path"],
            "size": result["size"],
            "encoding": result["encoding"],
            "total_lines": result["lines"],
            "replacements_made": count,
            "pattern": params.replace_pattern,
            "mode": "replace",
        }

    def _process_content(self, content: str, params: WriteFileParams) -> str:
        """Process content (minimal processing for simplicity)."""
        return content


class DeleteFileTool(BaseTool):
    """Tool for deleting files."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="delete_file",
            description="Permanently delete a file from the filesystem. Use with caution as this action cannot be undone. Useful for cleaning up temporary files, removing outdated files, or maintaining file system hygiene. Always verify the file path before deletion.",
            brief_description="Permanently delete a file from the filesystem",
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


class FindFilesTool(BaseTool):
    """Tool for finding files based on various criteria."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="find_files",
            description="Search for files and directories using flexible criteria including name patterns, file types, size filters, and modification dates. Perfect for locating specific files, counting files by type (e.g., 'how many Python files'), finding large files, or discovering recently modified content. Supports glob patterns (*.py, test_*) and regex matching.",
            brief_description="Search for files and directories using flexible criteria",
            category="filesystem",
            tags=[
                "find",
                "search",
                "filter",
                "locate",
                "count",
                "pattern",
                "type",
            ],
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.PATH,
                    description="Root directory path to start searching from",
                    required=True,
                ),
                ToolParameter(
                    name="name_pattern",
                    type=ParameterType.STRING,
                    description="Glob pattern to match filenames (e.g., '*.py', 'test_*', '*.json')",
                    required=False,
                ),
                ToolParameter(
                    name="regex_pattern",
                    type=ParameterType.STRING,
                    description="Regular expression pattern to match file/directory names",
                    required=False,
                ),
                ToolParameter(
                    name="file_type",
                    type=ParameterType.STRING,
                    description="Filter by item type: 'file', 'directory', or 'both'",
                    default="both",
                    allowed_values=["file", "directory", "both"],
                ),
                ToolParameter(
                    name="min_size",
                    type=ParameterType.INTEGER,
                    description="Minimum file size in bytes",
                    required=False,
                    min_value=0,
                ),
                ToolParameter(
                    name="max_size",
                    type=ParameterType.INTEGER,
                    description="Maximum file size in bytes",
                    required=False,
                    min_value=0,
                ),
                ToolParameter(
                    name="max_depth",
                    type=ParameterType.INTEGER,
                    description="Maximum search depth",
                    default=10,
                    min_value=1,
                ),
                ToolParameter(
                    name="include_hidden",
                    type=ParameterType.BOOLEAN,
                    description="Include hidden files and directories",
                    default=False,
                ),
                ToolParameter(
                    name="case_sensitive",
                    type=ParameterType.BOOLEAN,
                    description="Case sensitive pattern matching",
                    default=True,
                ),
                ToolParameter(
                    name="limit",
                    type=ParameterType.INTEGER,
                    description="Maximum number of results to return",
                    default=1000,
                    min_value=1,
                ),
            ],
        )

    def _should_include_item(self, item: Path, include_hidden: bool) -> bool:
        """Check if item should be included based on hidden file settings."""
        return include_hidden or not item.name.startswith(".")

    def _matches_file_type_filter(self, item: Path, file_type: str) -> bool:
        """Check if item matches the file type filter."""
        is_file = item.is_file()
        is_dir = item.is_dir()

        if file_type == "file":
            return is_file
        elif file_type == "directory":
            return is_dir
        else:  # "both"
            return True

    def _matches_name_patterns(
        self,
        item: Path,
        name_pattern: str,
        regex_compiled,
        case_sensitive: bool,
    ) -> bool:
        """Check if item name matches the specified patterns."""
        name_matches = True

        if name_pattern:
            if case_sensitive:
                name_matches = fnmatch.fnmatch(item.name, name_pattern)
            else:
                name_matches = fnmatch.fnmatch(item.name.lower(), name_pattern.lower())

        if regex_compiled and name_matches:
            name_matches = bool(regex_compiled.search(item.name))

        return name_matches

    def _matches_size_constraints(
        self, item: Path, min_size: Optional[int], max_size: Optional[int]
    ) -> bool:
        """Check if file matches size constraints (only applies to files)."""
        if not item.is_file():
            return True

        try:
            file_size = item.stat().st_size
            if min_size is not None and file_size < min_size:
                return False
            if max_size is not None and file_size > max_size:
                return False
            return True
        except OSError:
            # Skip files we can't stat
            return False

    def _create_result_item(
        self, item: Path, current_depth: int
    ) -> Optional[Dict[str, Any]]:
        """Create a result item from a file/directory."""
        try:
            stat = item.stat()
            is_file = item.is_file()
            return {
                "path": str(item),
                "name": item.name,
                "type": "file" if is_file else "directory",
                "size": stat.st_size if is_file else None,
                "modified": stat.st_mtime,
                "depth": current_depth,
            }
        except OSError:
            # Skip items we can't access
            return None

    def _search_directory(
        self,
        path: Path,
        search_params: Dict[str, Any],
        results: List[Dict[str, Any]],
        current_depth: int = 0,
    ) -> None:
        """Recursively search a directory for matching files."""
        max_depth = search_params["max_depth"]
        limit = search_params["limit"]
        progress_callback = search_params.get("progress_callback")

        if current_depth > max_depth or (limit is not None and len(results) >= limit):
            return

        try:
            items = list(path.iterdir())
            total_items = len(items)

            # Report progress for directories being processed
            if (
                progress_callback and current_depth <= 2
            ):  # Only report for shallow depths to avoid spam
                progress_callback(f"Searching directory: {path} ({total_items} items)")

            for i, item in enumerate(items):
                if self._process_search_item(
                    item, search_params, results, current_depth
                ):
                    return  # Hit limit, stop searching

                # Report progress periodically for large directories
                if progress_callback and total_items > 100 and i % 50 == 0:
                    progress_callback(
                        f"Processed {i}/{total_items} items in {path}, found {len(results)} matches"
                    )

        except PermissionError:
            # Skip directories we can't access
            if progress_callback:
                progress_callback(f"Skipping directory (permission denied): {path}")
            pass

    def _process_search_item(self, item, search_params, results, current_depth):
        """Process a single item during directory search. Returns True if limit hit."""
        # Extract search parameters
        include_hidden = search_params["include_hidden"]
        file_type = search_params["file_type"]
        name_pattern = search_params["name_pattern"]
        regex_compiled = search_params["regex_compiled"]
        case_sensitive = search_params["case_sensitive"]
        min_size = search_params["min_size"]
        max_size = search_params["max_size"]
        limit = search_params["limit"]

        # Apply filters
        if not self._should_include_item(item, include_hidden):
            return False

        if not self._matches_file_type_filter(item, file_type):
            return False

        name_matches = self._matches_name_patterns(
            item, name_pattern, regex_compiled, case_sensitive
        )

        if not name_matches:
            # Still recurse into directories even if they don't match
            if item.is_dir():
                self._search_directory(item, search_params, results, current_depth + 1)
            return False

        # Check size constraints (only for files)
        if not self._matches_size_constraints(item, min_size, max_size):
            return False

        # Add to results
        result_item = self._create_result_item(item, current_depth)
        if result_item:
            results.append(result_item)
            if limit is not None and len(results) >= limit:
                return True

        # Recurse into directories
        if item.is_dir():
            self._search_directory(item, search_params, results, current_depth + 1)

        return False

    @validate_parameters(FindFilesParams)
    @handle_tool_error
    async def execute(
        self, params: FindFilesParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file finding operation."""
        root_path = Path(params.path)
        name_pattern = params.name_pattern
        regex_pattern = params.regex_pattern
        file_type = params.file_type
        min_size = params.min_size
        max_size = params.max_size
        max_depth = params.max_depth
        include_hidden = params.include_hidden
        case_sensitive = params.case_sensitive
        limit = params.limit

        # Get progress callback from context
        progress_callback = getattr(context, "progress_callback", None)

        try:
            if progress_callback:
                progress_callback(f"Starting file search in: {root_path}")

            # Check if root path exists
            if not root_path.exists():
                raise ToolExecutionError(f"Root path does not exist: {root_path}")

            if not root_path.is_dir():
                raise ToolExecutionError(f"Root path is not a directory: {root_path}")

            # Compile regex pattern if provided
            regex_compiled = None
            if regex_pattern:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex_compiled = re.compile(regex_pattern, flags)

            # Prepare search parameters
            search_params = {
                "max_depth": max_depth,
                "limit": limit,
                "include_hidden": include_hidden,
                "file_type": file_type,
                "name_pattern": name_pattern,
                "regex_compiled": regex_compiled,
                "case_sensitive": case_sensitive,
                "min_size": min_size,
                "max_size": max_size,
                "progress_callback": progress_callback,
            }

            results: List[Dict[str, Any]] = []
            self._search_directory(root_path, search_params, results)

            if progress_callback:
                progress_callback(f"Search completed. Found {len(results)} matches.")

            # Sort results by path
            results.sort(key=lambda x: x["path"])

            return Result[Any].success_result(
                data={
                    "root_path": str(root_path),
                    "results": results,
                    "total_found": len(results),
                    "truncated": limit is not None and len(results) >= limit,
                },
                metadata={
                    "name_pattern": name_pattern,
                    "regex_pattern": regex_pattern,
                    "file_type": file_type,
                    "size_constraints": {
                        "min_size": min_size,
                        "max_size": max_size,
                    },
                    "search_params": {
                        "max_depth": max_depth,
                        "include_hidden": include_hidden,
                        "case_sensitive": case_sensitive,
                        "limit": limit,
                    },
                },
            )

        except re.error as e:
            raise ToolExecutionError(f"Invalid regex pattern: {e}")
        except OSError as e:
            raise ToolExecutionError(f"OS error during search: {e}")


class SearchFilesTool(BaseTool):
    """Tool for searching file contents using text patterns."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_files",
            description="Search for text patterns or code snippets within file contents across multiple files. Like 'grep' but more powerful - find function definitions, variable usage, import statements, configuration values, or any text content. Supports both literal text search and regular expressions. Essential for code analysis, debugging, and understanding large codebases.",
            brief_description="Search for text patterns within file contents",
            category="filesystem",
            tags=[
                "search",
                "grep",
                "text",
                "content",
                "code",
                "find",
                "pattern",
                "analysis",
            ],
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.PATH,
                    description="Root directory path to search within",
                    required=True,
                ),
                ToolParameter(
                    name="pattern",
                    type=ParameterType.STRING,
                    description="Text pattern or code snippet to search for",
                    required=True,
                ),
                ToolParameter(
                    name="regex",
                    type=ParameterType.BOOLEAN,
                    description="Treat pattern as a regular expression for advanced matching",
                    default=False,
                ),
                ToolParameter(
                    name="case_sensitive",
                    type=ParameterType.BOOLEAN,
                    description="Case sensitive search",
                    default=True,
                ),
                ToolParameter(
                    name="file_pattern",
                    type=ParameterType.STRING,
                    description="Glob pattern to filter files to search",
                    default="*",
                ),
                ToolParameter(
                    name="max_file_size",
                    type=ParameterType.INTEGER,
                    description="Maximum file size to search in bytes",
                    default=10 * 1024 * 1024,  # 10MB
                    min_value=1,
                ),
                ToolParameter(
                    name="max_depth",
                    type=ParameterType.INTEGER,
                    description="Maximum search depth",
                    default=10,
                    min_value=1,
                ),
                ToolParameter(
                    name="include_line_numbers",
                    type=ParameterType.BOOLEAN,
                    description="Include line numbers in results",
                    default=True,
                ),
                ToolParameter(
                    name="context_lines",
                    type=ParameterType.INTEGER,
                    description="Number of context lines to include around matches",
                    default=0,
                    min_value=0,
                    max_value=10,
                ),
                ToolParameter(
                    name="limit",
                    type=ParameterType.INTEGER,
                    description="Maximum number of matches to return",
                    default=100,
                    min_value=1,
                ),
            ],
        )

    def _should_search_file(
        self, file_path: Path, file_pattern: str, max_file_size: int
    ) -> bool:
        """Check if file should be searched."""
        try:
            # Check file pattern (skip if no pattern specified)
            if file_pattern and not fnmatch.fnmatch(file_path.name, file_pattern):
                return False

            # Check file size
            if file_path.stat().st_size > max_file_size:
                return False

            return True
        except OSError:
            return False

    def _find_pattern_in_line(
        self,
        line: str,
        pattern: str,
        search_pattern,
        use_regex: bool,
        case_sensitive: bool,
    ) -> bool:
        """Check if pattern matches in a line."""
        if use_regex and search_pattern:
            return bool(search_pattern.search(line))
        else:
            search_text = line if case_sensitive else line.lower()
            search_for = pattern if case_sensitive else pattern.lower()
            return search_for in search_text

    def _create_match_data(
        self,
        file_path: Path,
        line: str,
        line_num: int,
        pattern: str,
        lines: List[str],
        include_line_numbers: bool,
        context_lines: int,
    ) -> Dict[str, Any]:
        """Create match data structure."""
        match_data: Dict[str, Any] = {
            "file": str(file_path),
            "line": line.strip(),
            "match": pattern,
        }

        if include_line_numbers:
            match_data["line_number"] = line_num

        # Add context lines if requested
        if context_lines > 0:
            start_line = max(0, line_num - 1 - context_lines)
            end_line = min(len(lines), line_num + context_lines)
            context = []

            for i in range(start_line, end_line):
                context_line = {
                    "line_number": i + 1,
                    "content": lines[i].strip(),
                    "is_match": i == line_num - 1,
                }
                context.append(context_line)

            match_data["context"] = context

        return match_data

    def _search_single_file(
        self,
        file_path: Path,
        search_params: Dict[str, Any],
        results: List[Dict[str, Any]],
        counters: Dict[str, int],
    ) -> None:
        """Search for pattern in a single file."""
        pattern = search_params["pattern"]
        search_pattern = search_params["search_pattern"]
        use_regex = search_params["use_regex"]
        case_sensitive = search_params["case_sensitive"]
        include_line_numbers = search_params["include_line_numbers"]
        context_lines = search_params["context_lines"]
        limit = search_params["limit"]

        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()

            counters["files_searched"] += 1
            file_matches = []

            for line_num, line in enumerate(lines, 1):
                if limit is not None and len(results) >= limit:
                    break

                # Search for pattern
                if self._find_pattern_in_line(
                    line, pattern, search_pattern, use_regex, case_sensitive
                ):
                    match_data = self._create_match_data(
                        file_path,
                        line,
                        line_num,
                        pattern,
                        lines,
                        include_line_numbers,
                        context_lines,
                    )
                    file_matches.append(match_data)
                    results.append(match_data)

            if file_matches:
                counters["files_with_matches"] += 1

        except (UnicodeDecodeError, PermissionError, OSError):
            # Skip files we can't read
            pass

    def _search_directory_for_content(
        self,
        dir_path: Path,
        search_params: Dict[str, Any],
        results: List[Dict[str, Any]],
        counters: Dict[str, int],
        current_depth: int = 0,
    ) -> None:
        """Recursively search directory for content."""
        max_depth = search_params["max_depth"]
        limit = search_params["limit"]
        file_pattern = search_params["file_pattern"]
        max_file_size = search_params["max_file_size"]
        progress_callback = search_params.get("progress_callback")

        if current_depth > max_depth or (limit is not None and len(results) >= limit):
            return

        try:
            items = list(dir_path.iterdir())
            total_items = len(items)

            # Report progress for directories being processed
            if (
                progress_callback and current_depth <= 2
            ):  # Only report for shallow depths
                progress_callback(
                    f"Searching content in directory: {dir_path} ({total_items} items)"
                )

            for i, item in enumerate(items):
                if limit is not None and len(results) >= limit:
                    break

                if item.is_file():
                    # Check if file should be searched
                    if self._should_search_file(item, file_pattern, max_file_size):
                        self._search_single_file(item, search_params, results, counters)
                elif item.is_dir() and not item.name.startswith("."):
                    self._search_directory_for_content(
                        item,
                        search_params,
                        results,
                        counters,
                        current_depth + 1,
                    )

                # Report progress periodically for large directories
                if progress_callback and total_items > 50 and i % 25 == 0:
                    progress_callback(
                        f"Processed {i}/{total_items} items, searched {counters['files_searched']} files, found {len(results)} matches"
                    )

        except PermissionError:
            # Skip directories we can't access
            if progress_callback:
                progress_callback(f"Skipping directory (permission denied): {dir_path}")
            pass

    @validate_parameters(SearchTextParams)
    @handle_tool_error
    async def execute(
        self, params: SearchTextParams, context: ToolContext
    ) -> Result[Any]:
        """Execute file content search operation."""
        root_path = Path(params.path)
        pattern = params.pattern
        use_regex = params.regex
        case_sensitive = params.case_sensitive
        file_pattern = params.file_pattern
        max_file_size = params.max_file_size
        max_depth = params.max_depth
        include_line_numbers = params.include_line_numbers
        context_lines = params.context_lines
        limit = params.limit

        # Get progress callback from context
        progress_callback = getattr(context, "progress_callback", None)

        try:
            if progress_callback:
                progress_callback(
                    f"Starting content search for pattern '{pattern}' in: {root_path}"
                )

            # Check if root path exists
            if not root_path.exists():
                raise ToolExecutionError(f"Root path does not exist: {root_path}")

            if not root_path.is_dir():
                raise ToolExecutionError(f"Root path is not a directory: {root_path}")

            # Compile search pattern
            search_pattern = None
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                search_pattern = re.compile(pattern, flags)

            # Prepare search parameters
            search_params = {
                "pattern": pattern,
                "search_pattern": search_pattern,
                "use_regex": use_regex,
                "case_sensitive": case_sensitive,
                "file_pattern": file_pattern,
                "max_file_size": max_file_size,
                "max_depth": max_depth,
                "include_line_numbers": include_line_numbers,
                "context_lines": context_lines,
                "limit": limit,
                "progress_callback": progress_callback,
            }

            results: List[Dict[str, Any]] = []
            counters = {"files_searched": 0, "files_with_matches": 0}

            # Start search
            if root_path.is_file():
                if self._should_search_file(root_path, file_pattern, max_file_size):
                    self._search_single_file(
                        root_path, search_params, results, counters
                    )
            else:
                self._search_directory_for_content(
                    root_path, search_params, results, counters
                )

            if progress_callback:
                progress_callback(
                    f"Content search completed. Searched {counters['files_searched']} files, found {len(results)} matches."
                )

            return Result[Any].success_result(
                data={
                    "root_path": str(root_path),
                    "pattern": pattern,
                    "matches": results,
                    "total_matches": len(results),
                    "truncated": limit is not None and len(results) >= limit,
                },
                metadata={
                    "files_searched": counters["files_searched"],
                    "files_with_matches": counters["files_with_matches"],
                    "search_params": {
                        "regex": use_regex,
                        "case_sensitive": case_sensitive,
                        "file_pattern": file_pattern,
                        "max_file_size": max_file_size,
                        "context_lines": context_lines,
                    },
                },
            )

        except re.error as e:
            raise ToolExecutionError(f"Invalid regex pattern: {e}")
        except OSError as e:
            raise ToolExecutionError(f"OS error during search: {e}")
