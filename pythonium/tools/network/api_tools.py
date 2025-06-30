"""API interaction tools for REST, GraphQL, and webhook operations."""

from typing import Any, Dict
from urllib.parse import urljoin

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.parameter_validation import (
    GraphQLParams,
    RestApiParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)

from .http_client import HttpClientTool


class RestApiTool(BaseTool):
    """Tool for interacting with REST APIs."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="rest_api",
            description="Execute REST API requests with authentication",
            brief_description="Execute REST API requests with authentication",
            detailed_description="Interact with REST APIs using various HTTP methods (GET, POST, PUT, DELETE, PATCH) with automatic authentication support including Bearer tokens, API keys, and Basic auth. Handles response parsing and provides comprehensive API interaction capabilities.",
            category="network",
            parameters=[
                ToolParameter(
                    name="base_url",
                    type=ParameterType.STRING,
                    description="Base URL of the API",
                    required=True,
                ),
                ToolParameter(
                    name="endpoint",
                    type=ParameterType.STRING,
                    description="API endpoint path",
                    required=True,
                ),
                ToolParameter(
                    name="method",
                    type=ParameterType.STRING,
                    description="HTTP method",
                    required=False,
                    allowed_values=["GET", "POST", "PUT", "DELETE", "PATCH"],
                ),
                ToolParameter(
                    name="auth_type",
                    type=ParameterType.STRING,
                    description="Authentication type",
                    required=False,
                    allowed_values=["bearer", "api_key", "basic", "none"],
                ),
                ToolParameter(
                    name="auth_token",
                    type=ParameterType.STRING,
                    description="Authentication token or API key",
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
                    description="Query parameters",
                    required=False,
                ),
                ToolParameter(
                    name="custom_headers",
                    type=ParameterType.OBJECT,
                    description="Additional custom headers",
                    required=False,
                ),
            ],
        )

    async def initialize(self) -> None:
        """Initialize the REST API tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the REST API tool."""
        pass

    @validate_parameters(RestApiParams)
    @handle_tool_error
    async def execute(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute REST API request."""
        try:
            # Extract parameters
            base_url = parameters["base_url"]
            endpoint = parameters["endpoint"]
            method = parameters.get("method", "GET")
            auth_type = parameters.get("auth_type", "none")
            auth_token = parameters.get("auth_token")
            data = parameters.get("data")
            params = parameters.get("params")
            custom_headers = parameters.get("custom_headers")

            # Build full URL
            full_url = urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Add authentication
            if auth_type == "bearer" and auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            elif auth_type == "api_key" and auth_token:
                headers["X-API-Key"] = auth_token
            elif auth_type == "basic" and auth_token:
                headers["Authorization"] = f"Basic {auth_token}"

            # Add custom headers
            if custom_headers:
                headers.update(custom_headers)

            # Execute request
            http_client = HttpClientTool()
            await http_client.initialize()
            try:
                result: Result[Any] = await http_client.execute(
                    {
                        "url": full_url,
                        "method": method,
                        "headers": headers,
                        "data": data,
                        "params": params,
                    },
                    context,
                )
            finally:
                await http_client.shutdown()

            # Enhance result with API-specific information
            if result.success and result.data:
                result.data["api_info"] = {
                    "base_url": base_url,
                    "endpoint": endpoint,
                    "auth_type": auth_type,
                    "full_url": full_url,
                }

            return result

        except Exception as e:
            return Result[Any].error_result(error=f"REST API request failed: {str(e)}")


class GraphQLTool(BaseTool):
    """Tool for executing GraphQL queries and mutations."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="graphql",
            description="Execute GraphQL queries and mutations",
            brief_description="Execute GraphQL queries and mutations",
            detailed_description="Execute GraphQL queries and mutations with support for variables, operation names, and authentication. Provides comprehensive GraphQL support including error handling and response parsing.",
            category="network",
            parameters=[
                ToolParameter(
                    name="endpoint",
                    type=ParameterType.STRING,
                    description="GraphQL endpoint URL",
                    required=True,
                ),
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="GraphQL query or mutation",
                    required=True,
                ),
                ToolParameter(
                    name="variables",
                    type=ParameterType.OBJECT,
                    description="GraphQL variables",
                    required=False,
                ),
                ToolParameter(
                    name="operation_name",
                    type=ParameterType.STRING,
                    description="Operation name for named queries",
                    required=False,
                ),
                ToolParameter(
                    name="auth_token",
                    type=ParameterType.STRING,
                    description="Authentication token",
                    required=False,
                ),
                ToolParameter(
                    name="custom_headers",
                    type=ParameterType.OBJECT,
                    description="Additional custom headers",
                    required=False,
                ),
            ],
        )

    async def initialize(self) -> None:
        """Initialize the GraphQL tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the GraphQL tool."""
        pass

    @validate_parameters(GraphQLParams)
    @handle_tool_error
    async def execute(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute GraphQL request."""
        try:
            # Extract parameters
            endpoint = parameters["endpoint"]
            query = parameters["query"]
            variables = parameters.get("variables")
            operation_name = parameters.get("operation_name")
            auth_token = parameters.get("auth_token")
            custom_headers = parameters.get("custom_headers")

            # Prepare GraphQL payload
            payload: Dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables
            if operation_name:
                payload["operationName"] = operation_name

            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            if custom_headers:
                headers.update(custom_headers)

            # Execute request
            http_client = HttpClientTool()
            await http_client.initialize()
            try:
                result: Result[Any] = await http_client.execute(
                    {
                        "url": endpoint,
                        "method": "POST",
                        "headers": headers,
                        "data": payload,
                    },
                    context,
                )
            finally:
                await http_client.shutdown()

            # Parse GraphQL response
            if result.success and result.data:
                response_data = result.data.get("data")
                if isinstance(response_data, dict):
                    graphql_data = response_data.get("data")
                    graphql_errors = response_data.get("errors")

                    result.data = {
                        "data": graphql_data,
                        "errors": graphql_errors,
                        "status": result.data.get("status"),
                        "query": query,
                        "variables": variables,
                        "operation_name": operation_name,
                    }

                    # If there are GraphQL errors, mark as unsuccessful
                    if graphql_errors:
                        result.success = False
                        result.error = f"GraphQL errors: {graphql_errors}"

            return result

        except Exception as e:
            return Result[Any].error_result(error=f"GraphQL request failed: {str(e)}")
