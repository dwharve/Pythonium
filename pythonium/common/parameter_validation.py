"""
Parameter validation framework for Pythonium tools.

This module provides decorators and utilities to standardize parameter
validation across all tools, reducing boilerplate code and improving
consistency.
"""

import functools
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from pythonium.common.base import Result
from pythonium.common.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ParameterModel(BaseModel):
    """Base class for tool parameter models with common functionality."""

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown parameters
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_unset=True)

    @classmethod
    def get_parameter_names(cls) -> List[str]:
        """Get list of parameter names."""
        return list(cls.model_fields.keys())


def validate_parameters(parameter_model: Type[ParameterModel]):
    """
    Decorator to validate tool parameters using a Pydantic model.

    Args:
        parameter_model: Pydantic model class defining parameter schema

    Example:
        @validate_parameters(HttpRequestParams)
        async def execute(self, params: HttpRequestParams, context: ToolContext):
            url = params.url
            method = params.method
            # ... rest of implementation
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, parameters: Dict[str, Any], context, *args, **kwargs):
            try:
                # Validate parameters using the model
                validated_params = parameter_model(**parameters)

                # Call the original function with validated parameters
                return await func(self, validated_params, context, *args, **kwargs)

            except ValidationError as e:
                error_msg = f"Parameter validation failed: {e}"
                logger.warning(f"Tool {self.__class__.__name__}: {error_msg}")
                return Result.error_result(error=error_msg)
            except Exception as e:
                error_msg = f"Unexpected validation error: {e}"
                logger.error(f"Tool {self.__class__.__name__}: {error_msg}")
                return Result.error_result(error=error_msg)

        return wrapper

    return decorator


class HttpRequestParams(ParameterModel):
    """Parameter model for HTTP request tools."""

    url: str = Field(..., description="URL to request")
    method: str = Field(..., description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")
    data: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Request body data"
    )
    params: Optional[Dict[str, str]] = Field(None, description="URL query parameters")
    timeout: int = Field(30, description="Request timeout in seconds")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    follow_redirects: bool = Field(True, description="Follow HTTP redirects")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if v.upper() not in allowed_methods:
            raise ValueError(f"Invalid HTTP method. Allowed: {allowed_methods}")
        return v.upper()


class ProcessManagerParams(ParameterModel):
    """Parameter model for ProcessManagerTool."""

    operation: str = Field(..., description="Operation to perform")
    pid: Optional[int] = Field(None, description="Process ID")
    process_name: Optional[str] = Field(None, description="Process name")
    signal_type: str = Field("TERM", description="Signal type to send")
    include_children: bool = Field(False, description="Include child processes")

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate operation type."""
        valid_operations = [
            "kill",
            "terminate",
            "suspend",
            "resume",
            "send_signal",
            "list",
        ]
        if v.lower() not in valid_operations:
            raise ValueError(f"Invalid operation. Valid operations: {valid_operations}")
        return v.lower()


class SystemInfoToolParams(ParameterModel):
    """Parameter model for SystemInfoTool."""

    include_hardware: bool = Field(True, description="Include hardware information")
    include_network: bool = Field(True, description="Include network information")
    include_python: bool = Field(True, description="Include Python information")


class DiskUsageParams(ParameterModel):
    """Parameter model for DiskUsageTool."""

    paths: List[str] = Field(["."], description="Paths to analyze")
    human_readable: bool = Field(True, description="Use human-readable formats")


class NetworkInfoParams(ParameterModel):
    """Parameter model for NetworkInfoTool."""

    test_connectivity: bool = Field(True, description="Test network connectivity")
    test_hosts: List[str] = Field(
        ["8.8.8.8", "1.1.1.1"], description="Hosts to test connectivity"
    )
    timeout: int = Field(5, description="Connection timeout in seconds")


class ServiceStatusParams(ParameterModel):
    """Parameter model for ServiceStatusTool."""

    services: List[str] = Field(..., description="List of service names to check")
    platform: str = Field(
        "auto", description="Target platform (auto, windows, linux, darwin)"
    )


class PortMonitorParams(ParameterModel):
    """Parameter model for PortMonitorTool."""

    ports: List[int] = Field(..., description="List of ports to monitor")
    host: str = Field("localhost", description="Host to check ports on")
    timeout: int = Field(5, description="Connection timeout in seconds")
    protocol: str = Field("tcp", description="Protocol to use (tcp/udp)")


class SystemLoadParams(ParameterModel):
    """Parameter model for SystemLoadTool."""

    include_processes: bool = Field(
        True, description="Include top processes information"
    )
    process_limit: int = Field(10, description="Maximum number of processes to include")
    sort_by: str = Field("cpu", description="Sort processes by (cpu, memory, name)")


class ExecuteCommandParams(ParameterModel):
    """Parameter model for ExecuteCommandTool."""

    command: str = Field(..., description="Command to execute")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    working_directory: Optional[str] = Field(
        None, description="Working directory for execution"
    )
    timeout: int = Field(30, description="Execution timeout in seconds")
    capture_output: bool = Field(True, description="Capture command output")
    shell: bool = Field(False, description="Execute command in shell")
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    stdin: Optional[str] = Field(None, description="Input to send to command's stdin")


class WebScrapingParams(ParameterModel):
    """Parameter model for WebScrapingTool."""

    url: str = Field(..., description="URL to scrape")
    selectors: Dict[str, str] = Field(..., description="CSS selectors to extract data")
    user_agent: Optional[str] = Field(
        None, description="User agent string for the request"
    )
    follow_links: bool = Field(
        False, description="Follow links and scrape multiple pages"
    )
    max_pages: int = Field(5, description="Maximum number of pages to scrape")
    wait_time: int = Field(1, description="Wait time between requests in seconds")


class HtmlParsingParams(ParameterModel):
    """Parameter model for HtmlParsingTool."""

    html_content: str = Field(..., description="HTML content to parse")
    selector: str = Field(..., description="CSS selector to extract elements")
    extract_attributes: Optional[List[str]] = Field(
        None, description="Attributes to extract from elements"
    )
    extract_text: bool = Field(True, description="Extract text content from elements")


# API Tools Parameters
class RestApiParams(ParameterModel):
    """Parameter model for RestApiTool."""

    base_url: str = Field(..., description="Base URL of the API")
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field("GET", description="HTTP method")
    auth_type: str = Field("none", description="Authentication type")
    auth_token: Optional[str] = Field(None, description="Authentication token")
    data: Optional[Dict[str, Any]] = Field(None, description="Request data")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    custom_headers: Optional[Dict[str, str]] = Field(
        None, description="Additional custom headers"
    )


class GraphQLParams(ParameterModel):
    """Parameter model for GraphQLTool."""

    endpoint: str = Field(..., description="GraphQL endpoint URL")
    query: str = Field(..., description="GraphQL query or mutation")
    variables: Optional[Dict[str, Any]] = Field(None, description="Query variables")
    operation_name: Optional[str] = Field(None, description="Operation name")
    auth_token: Optional[str] = Field(None, description="Authentication token")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")


# Filesystem operation parameter models
class FileOperationParams(ParameterModel):
    """Parameters for file operations."""

    path: Union[str, Path] = Field(..., description="File path")
    encoding: str = Field("utf-8", description="File encoding")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Union[str, Path]) -> str:
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


class ReadFileParams(FileOperationParams):
    """Parameters for reading files."""

    max_size: int = Field(
        10485760, description="Maximum file size in bytes", ge=1
    )  # 10MB default


class WriteFileParams(FileOperationParams):
    """Parameters for writing files."""

    content: str = Field(..., description="Content to write")
    append: bool = Field(False, description="Append to file instead of overwriting")
    overwrite: bool = Field(True, description="Overwrite existing file")
    create_dirs: bool = Field(
        True, description="Create parent directories if they don't exist"
    )


class CreateFileParams(ParameterModel):
    """Parameter model for CreateFileTool."""

    path: Union[str, Path] = Field(..., description="Path for the file to create")
    content: Optional[str] = Field("", description="Content to write to the file")
    create_dirs: bool = Field(
        True, description="Create parent directories if they don't exist"
    )
    overwrite: bool = Field(False, description="Overwrite file if it exists")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """Validate file path."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


class DeleteFileParams(ParameterModel):
    """Parameter model for DeleteFileTool."""

    path: Union[str, Path] = Field(..., description="Path of the file to delete")
    force: bool = Field(False, description="Force deletion of read-only files")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """Validate file path."""
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
    def validate_path(cls, v):
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v):
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
    exclude_files: Optional[str] = Field(
        None, description="Glob pattern to exclude files from search"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        """Validate path format."""
        if not v:
            raise ValueError("Path cannot be empty")
        return str(v)  # Convert Path to string


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
