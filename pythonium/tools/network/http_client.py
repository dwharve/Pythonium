"""HTTP client tools for making web requests."""

from typing import Any

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.http import HttpService
from pythonium.common.parameter_validation import HttpRequestParams, validate_parameters
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


class HttpClientTool(BaseTool):
    """Generic HTTP client tool for making requests."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="http_client",
            description="Make HTTP requests with custom methods, headers, and data. Supports all standard HTTP methods with flexible parameter handling.",
            brief_description="Make HTTP requests with custom methods",
            detailed_description="Make HTTP requests with custom methods, headers, and data. Takes 'url' (required string), 'method' (required string: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS), optional 'headers' (object), 'data' (object for request body), 'params' (object for query parameters), 'timeout' (integer, default 30), and 'verify_ssl' (boolean, default True). Supports comprehensive HTTP client functionality.",
            category="network",
            tags=["http", "client", "web", "api", "request"],
            parameters=[
                ToolParameter(
                    name="url",
                    type=ParameterType.STRING,
                    description="URL to send the request to",
                    required=True,
                ),
                ToolParameter(
                    name="method",
                    type=ParameterType.STRING,
                    description="HTTP method (GET, POST, PUT, DELETE, etc.)",
                    required=True,
                ),
                ToolParameter(
                    name="headers",
                    type=ParameterType.OBJECT,
                    description="HTTP headers as key-value pairs",
                    required=False,
                ),
                ToolParameter(
                    name="data",
                    type=ParameterType.OBJECT,
                    description="Request body data",
                    required=False,
                ),
                ToolParameter(
                    name="params",
                    type=ParameterType.OBJECT,
                    description="URL query parameters",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Request timeout in seconds",
                    required=False,
                ),
                ToolParameter(
                    name="follow_redirects",
                    type=ParameterType.BOOLEAN,
                    description="Whether to follow redirects",
                    required=False,
                ),
            ],
        )

    @handle_tool_error
    @validate_parameters(HttpRequestParams)
    async def execute(
        self, params: HttpRequestParams, context: ToolContext
    ) -> Result[Any]:
        """Execute HTTP request."""
        try:
            # Create HTTP service with specified configuration
            async with HttpService(
                timeout=params.timeout,
                verify_ssl=params.verify_ssl,
                follow_redirects=params.follow_redirects,
            ) as http_service:

                # Prepare request kwargs
                request_kwargs = {}
                if params.headers:
                    request_kwargs["headers"] = params.headers
                if params.params:
                    request_kwargs["params"] = params.params

                # Handle request body
                json_data = None
                data = None
                if params.data:
                    if isinstance(params.data, dict):
                        json_data = params.data
                    else:
                        data = params.data

                # Make the request
                result = await http_service.request(
                    params.method,
                    params.url,
                    data=data,
                    json_data=json_data,
                    **request_kwargs,
                )

                if result.success:
                    return Result[Any].success_result(
                        data=result.data, metadata=result.metadata
                    )
                else:
                    return Result[Any].error_result(
                        error=result.error, metadata=result.metadata
                    )

        except Exception as e:
            return Result[Any].error_result(error=f"Unexpected error: {str(e)}")
