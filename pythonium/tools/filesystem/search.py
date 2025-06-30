"""
File search and filtering tools.
"""

import fnmatch
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.parameter_validation import (
    FindFilesParams,
    SearchTextParams,
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


class FindFilesTool(BaseTool):
    """Tool for finding files based on various criteria."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="find_files",
            description="Search for files and directories using flexible criteria including name patterns, file types, size filters, and modification dates. Perfect for locating specific files, counting files by type (e.g., 'how many Python files'), finding large files, or discovering recently modified content. Supports glob patterns (*.py, test_*) and regex matching.",
            brief_description="Search for files and directories using flexible criteria",
            detailed_description="Search for files and directories using flexible criteria including name patterns, file types, size filters, and modification dates. Takes 'path' (required) as the root directory, 'name_pattern' (glob like '*.py'), 'regex_pattern' for complex matching, 'file_type' (file/directory/both), size filters ('min_size', 'max_size' in bytes), 'max_depth' for recursion control, 'include_hidden' (boolean), 'case_sensitive' (boolean), and 'limit' for result count. Perfect for locating specific files, counting files by type, finding large files, or discovering recently modified content.",
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
        else:  # "all"
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

        if current_depth > max_depth or (limit is not None and len(results) >= limit):
            return

        try:
            for item in path.iterdir():
                if self._process_search_item(
                    item, search_params, results, current_depth
                ):
                    return  # Hit limit, stop searching
        except PermissionError:
            # Skip directories we can't access
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

        try:
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
            }

            results: List[Dict[str, Any]] = []
            self._search_directory(root_path, search_params, results)

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

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_files",
            description="Search for text patterns or code snippets within file contents across multiple files. Like 'grep' but more powerful - find function definitions, variable usage, import statements, configuration values, or any text content. Supports both literal text search and regular expressions. Essential for code analysis, debugging, and understanding large codebases.",
            brief_description="Search for text patterns within file contents",
            detailed_description="Search for text patterns or code snippets within file contents across multiple files. Takes 'path' (required directory), 'pattern' (required text to find), 'regex' (boolean for regex mode), 'case_sensitive' (boolean), 'file_pattern' (glob to filter files like '*.py'), 'max_file_size' (bytes limit), 'max_depth' (recursion limit), 'include_line_numbers' (boolean), 'context_lines' (number of surrounding lines), and 'limit' (max results). Like 'grep' but more powerful - find function definitions, variable usage, import statements, or any text content.",
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

        if current_depth > max_depth or (limit is not None and len(results) >= limit):
            return

        try:
            for item in dir_path.iterdir():
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

        except PermissionError:
            # Skip directories we can't access
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

        try:
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
