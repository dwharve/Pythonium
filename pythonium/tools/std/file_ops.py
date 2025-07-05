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
from pythonium.common.parameter_validation import validate_parameters
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
    """Tool for reading file contents."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read and return the complete contents of a text file. Handles various file encodings and supports reading code files (Python, JavaScript, etc.), configuration files, documentation, logs, and other text-based files. Includes safety limits to prevent reading extremely large files.",
            brief_description="Read the contents of a text file",
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


class WriteFileTool(BaseTool):
    """Tool for writing content to files and creating new files.

    This tool combines file creation and writing functionality. It can create new files
    with content or update existing files, with options for appending and directory creation.
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write text content to a file, creating it if it doesn't exist or updating existing content. Supports creating new files, saving generated code, writing configuration files, creating documentation, or updating existing files. Creates parent directories if they don't exist. Can append to existing files or overwrite them.",
            brief_description="Write text content to a file or create new files",
            category="filesystem",
            tags=["file", "write", "create", "save", "generate", "update", "append"],
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
                    description="Text content to write to the file (use empty string to create empty file)",
                    default="",
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
                    default=True,
                ),
                ToolParameter(
                    name="overwrite",
                    type=ParameterType.BOOLEAN,
                    description="Overwrite file if it exists",
                    default=True,
                ),
                ToolParameter(
                    name="append",
                    type=ParameterType.BOOLEAN,
                    description="Append to existing file instead of overwriting",
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
