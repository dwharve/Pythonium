"""
Parameter models for standard tools.

This module provides parameter validation models for tools in the std module.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import Field, field_validator

from pythonium.common.parameter_validation import ParameterModel


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
    """Parameter model for ReadFileTool."""

    path: Union[str, Path] = Field(..., description="Path to the file to read")
    encoding: str = Field("utf-8", description="Text encoding of the file")
    max_size: int = Field(
        10485760, description="Maximum file size to read in bytes", ge=1
    )  # 10MB default

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Union[str, Path]) -> str:
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


class WriteFileParams(ParameterModel):
    """Parameter model for WriteFileTool (unified create/write functionality)."""

    path: Union[str, Path] = Field(
        ..., description="Path where the file will be written"
    )
    content: str = Field(
        "", description="Content to write to the file (empty for empty file)"
    )
    encoding: str = Field("utf-8", description="File encoding")
    append: bool = Field(False, description="Append to file instead of overwriting")
    overwrite: bool = Field(True, description="Overwrite file if it exists")
    create_dirs: bool = Field(
        True, description="Create parent directories if they don't exist"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Union[str, Path]) -> str:
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


class DeleteFileParams(ParameterModel):
    """Parameter model for DeleteFileTool."""

    path: Union[str, Path] = Field(..., description="Path to the file to delete")
    force: bool = Field(False, description="Force deletion even if file is read-only")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Union[str, Path]) -> str:
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


class FindFilesParams(ParameterModel):
    """Parameter model for FindFilesTool."""

    path: Union[str, Path] = Field(
        ..., description="Root directory path to start searching from"
    )
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
    def validate_path(cls, v: Union[str, Path]) -> str:
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

    path: Union[str, Path] = Field(
        ..., description="Root directory path to search within"
    )
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
    def validate_path(cls, v: Union[str, Path]) -> str:
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
