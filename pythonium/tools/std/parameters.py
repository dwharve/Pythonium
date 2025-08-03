"""
Parameter models for standard tools.

This module provides clean, modern parameter validation models.
"""

from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import Field, field_validator

from pythonium.common.parameters import ParameterModel


class DescribeToolParams(ParameterModel):
    """Parameter model for DescribeToolTool."""

    tool_name: str = Field(..., description="Name of the tool to describe")
    include_examples: bool = Field(
        True, description="Include usage examples in the description"
    )
    include_schema: bool = Field(True, description="Include parameter schema details")
    include_metadata: bool = Field(
        False, description="Include detailed metadata information"
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()


class ExecuteCommandParams(ParameterModel):
    """Parameter model for ExecuteCommandTool."""

    command: str = Field(..., description="Command to execute")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    working_directory: Optional[str] = Field(
        None, description="Working directory for execution"
    )
    timeout: int = Field(30, description="Execution timeout in seconds", ge=1, le=300)
    capture_output: bool = Field(True, description="Capture command output")
    shell: bool = Field(False, description="Execute command in shell")
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    stdin: Optional[str] = Field(None, description="Input to send to command's stdin")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate command is not empty."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()

    @field_validator("args")
    @classmethod
    def validate_args(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate command arguments."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("args must be a list of strings")
            for arg in v:
                if not isinstance(arg, str):
                    raise ValueError("All arguments must be strings")
        return v

    @field_validator("working_directory")
    @classmethod
    def validate_working_directory(cls, v: Optional[str]) -> Optional[str]:
        """Validate working directory path."""
        if v is not None:
            if not v.strip():
                raise ValueError("Working directory cannot be empty string")
            return v.strip()
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Validate environment variables."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("environment must be a dictionary")
            for key, value in v.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError(
                        "Environment variables must be string key-value pairs"
                    )
        return v


class ExecutePythonParams(ParameterModel):
    """Parameter model for ExecutePythonTool."""

    code: str = Field(..., description="Python code to execute")
    working_directory: Optional[str] = Field(None, description="Working directory")
    timeout: int = Field(30, description="Execution timeout", ge=1, le=300)
    capture_output: bool = Field(True, description="Capture output")
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )


class SearchToolsParams(ParameterModel):
    """Parameter model for SearchToolsTool."""

    query: str = Field(..., description="Search query for finding tools")
    category: Optional[str] = Field(None, description="Filter by tool category")
    tags: Optional[List[str]] = Field(None, description="Filter by tool tags")
    include_description: bool = Field(
        True, description="Include tool descriptions in results"
    )
    include_parameters: bool = Field(
        False, description="Include parameter information in results"
    )
    limit: Optional[int] = Field(
        None, description="Maximum number of results to return"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: Optional[int]) -> Optional[int]:
        """Validate search limit."""
        if v is not None and v <= 0:
            raise ValueError("Limit must be positive")
        return v


# File Operation Parameter Models


class ReadFileParams(ParameterModel):
    """Parameter model for ReadFileTool with flexible line selection."""

    path: str = Field(..., description="Path to the file to read")
    encoding: str = Field("utf-8", description="Text encoding")
    max_size: int = Field(10485760, description="Maximum file size in bytes", ge=1)

    # Line selection (mutually exclusive)
    start_line: Optional[int] = Field(None, description="Start line (1-indexed)", ge=1)
    end_line: Optional[int] = Field(None, description="End line (1-indexed)", ge=1)
    line_numbers: Optional[List[int]] = Field(None, description="Specific line numbers")
    line_pattern: Optional[str] = Field(
        None, description="Regex pattern to match lines"
    )
    head_lines: Optional[int] = Field(None, description="First N lines", ge=1)
    tail_lines: Optional[int] = Field(None, description="Last N lines", ge=1)

    # Output options
    include_line_numbers: bool = Field(False, description="Include line numbers")
    strip_whitespace: bool = Field(False, description="Strip line whitespace")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path is not empty."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()

    def model_post_init(self, __context: Any) -> None:
        """Ensure only one line selection method is used."""
        selections = [
            self.start_line is not None or self.end_line is not None,
            self.line_numbers is not None,
            self.line_pattern is not None,
            self.head_lines is not None,
            self.tail_lines is not None,
        ]

        if sum(selections) > 1:
            raise ValueError("Use only one line selection method at a time")


class WriteFileParams(ParameterModel):
    """Parameter model for WriteFileTool with multiple write modes."""

    path: str = Field(..., description="Path to write file")
    content: str = Field("", description="Content to write")
    encoding: str = Field("utf-8", description="File encoding")
    mode: str = Field(
        "write", description="Write mode: write, append, prepend, insert, replace"
    )

    # Mode-specific options
    insert_at_line: Optional[int] = Field(
        None, description="Line number for insert mode", ge=1
    )
    replace_pattern: Optional[str] = Field(
        None, description="Regex pattern for replace mode"
    )
    replace_all: bool = Field(False, description="Replace all occurrences")

    # File options
    create_dirs: bool = Field(True, description="Create parent directories")
    backup: bool = Field(False, description="Create backup before modification")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path is not empty."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate write mode."""
        valid_modes = ["write", "append", "prepend", "insert", "replace"]
        if v not in valid_modes:
            raise ValueError(f"Invalid mode: {v}. Use: {', '.join(valid_modes)}")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate mode requirements."""
        if self.mode == "insert" and self.insert_at_line is None:
            raise ValueError("insert_at_line required for insert mode")
        if self.mode == "replace" and self.replace_pattern is None:
            raise ValueError("replace_pattern required for replace mode")


class DeleteFileParams(ParameterModel):
    """Parameter model for DeleteFileTool."""

    path: str = Field(..., description="Path to the file to delete")
    force: bool = Field(False, description="Force deletion even if file is read-only")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()


class FindFilesParams(ParameterModel):
    """Parameter model for FindFilesTool."""

    path: str = Field(..., description="Root directory path to start searching from")
    name_pattern: Optional[str] = Field(
        None, description="Glob pattern to match filenames (e.g., '*.py', 'test_*')"
    )
    regex_pattern: Optional[str] = Field(
        None, description="Regular expression pattern to match file/directory names"
    )
    file_type: str = Field(
        "both", description="Filter by item type: 'file', 'directory', or 'both'"
    )
    min_size: Optional[int] = Field(
        None, description="Minimum file size in bytes", ge=0
    )
    max_size: Optional[int] = Field(
        None, description="Maximum file size in bytes", ge=0
    )
    max_depth: int = Field(10, description="Maximum search depth", ge=1)
    include_hidden: bool = Field(
        False, description="Include hidden files and directories"
    )
    case_sensitive: bool = Field(True, description="Case sensitive pattern matching")
    limit: int = Field(1000, description="Maximum number of results to return", ge=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """Validate file type filter."""
        if v not in ["file", "directory", "both"]:
            raise ValueError("file_type must be 'file', 'directory', or 'both'")
        return v


class SearchTextParams(ParameterModel):
    """Parameter model for SearchFilesTool."""

    path: str = Field(..., description="Root directory path to search within")
    pattern: str = Field(..., description="Text pattern or code snippet to search for")
    regex: bool = Field(False, description="Treat pattern as a regular expression")
    case_sensitive: bool = Field(True, description="Case sensitive search")
    file_pattern: str = Field("*", description="Glob pattern to filter files to search")
    max_file_size: int = Field(
        10485760, description="Maximum file size to search in bytes", ge=1
    )  # 10MB
    max_depth: int = Field(10, description="Maximum search depth", ge=1)
    include_line_numbers: bool = Field(
        True, description="Include line numbers in results"
    )
    context_lines: int = Field(
        0, description="Number of context lines to include around matches", ge=0, le=10
    )
    limit: int = Field(100, description="Maximum number of matches to return", ge=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


# Web Operation Parameter Models


class WebSearchParams(ParameterModel):
    """Parameter model for WebSearchTool."""

    query: str = Field(..., description="Search query string")
    engine: str = Field(
        "duckduckgo", description="Search engine to use (only 'duckduckgo' supported)"
    )
    max_results: int = Field(
        10, description="Maximum number of search results to return", ge=1, le=50
    )
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=120)
    language: Optional[str] = Field(
        None, description="Search language (e.g., 'en', 'es', 'fr')"
    )
    region: Optional[str] = Field(
        None, description="Search region (e.g., 'us', 'uk', 'de')"
    )
    include_snippets: bool = Field(
        True, description="Include content snippets in results"
    )
    use_fallback: bool = Field(
        True, description="Enable fallback search strategies (HTML/lite) if API fails"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        """Validate search engine."""
        supported_engines = ["duckduckgo"]
        if v.lower() not in supported_engines:
            raise ValueError(
                f"Unsupported engine. Supported engines: {', '.join(supported_engines)}"
            )
        return v.lower()

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code."""
        if v is not None:
            v = v.strip().lower()
            if len(v) != 2:
                raise ValueError(
                    "Language code must be 2 characters (e.g., 'en', 'es')"
                )
            return v
        return None

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: Optional[str]) -> Optional[str]:
        """Validate region code."""
        if v is not None:
            v = v.strip().lower()
            if len(v) != 2:
                raise ValueError("Region code must be 2 characters (e.g., 'us', 'uk')")
            return v
        return None


class HttpRequestParams(ParameterModel):
    """Parameter model for HTTP request tools."""

    url: str = Field(..., description="URL to request")
    method: str = Field(..., description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    data: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Request body data"
    )
    params: Optional[Dict[str, str]] = Field(None, description="URL query parameters")
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=300)
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    follow_redirects: bool = Field(True, description="Follow HTTP redirects")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")

        v = v.strip()
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                "Invalid URL format - must include scheme (http/https) and domain"
            )

        if parsed.scheme not in ["http", "https"]:
            raise ValueError("URL scheme must be http or https")

        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        if not v or not v.strip():
            raise ValueError("HTTP method cannot be empty")

        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        method_upper = v.strip().upper()

        if method_upper not in allowed_methods:
            raise ValueError(
                f"Invalid HTTP method '{v}'. Allowed methods: {', '.join(allowed_methods)}"
            )

        return method_upper

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Validate HTTP headers."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("Headers must be a dictionary")

            # Validate header names and values
            for name, value in v.items():
                if not isinstance(name, str) or not isinstance(value, str):
                    raise ValueError("Header names and values must be strings")
                if not name.strip():
                    raise ValueError("Header names cannot be empty")

        return v

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Validate URL query parameters."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("Query parameters must be a dictionary")

            # Validate parameter names and values
            for name, value in v.items():
                if not isinstance(name, str) or not isinstance(value, str):
                    raise ValueError("Parameter names and values must be strings")

        return v


class FetchWebpageParams(ParameterModel):
    """Parameter model for fetching and converting webpages to LLM-friendly markup."""

    url: str = Field(..., description="URL of the webpage to fetch")
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=300)
    max_content_length: int = Field(
        50000, description="Maximum content length to process", ge=1000, le=500000
    )
    include_links: bool = Field(
        True, description="Include extracted links in the output"
    )
    include_images: bool = Field(
        True, description="Include image descriptions and alt text"
    )
    include_metadata: bool = Field(
        True, description="Include page metadata (title, description, etc.)"
    )
    user_agent: Optional[str] = Field(
        None, description="Custom User-Agent header for the request"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")

        v = v.strip()
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                "Invalid URL format - must include scheme (http/https) and domain"
            )

        if parsed.scheme not in ["http", "https"]:
            raise ValueError("URL scheme must be http or https")

        return v
