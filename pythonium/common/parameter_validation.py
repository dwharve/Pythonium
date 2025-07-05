"""
Parameter validation framework for Pythonium tools.

This module provides decorators and utilities to standardize parameter
validation across all tools, reducing boilerplate code and improving
consistency.
"""

import functools
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
