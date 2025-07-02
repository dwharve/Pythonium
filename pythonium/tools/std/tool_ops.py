"""
Tool operations and meta-tools for the Pythonium framework.

Provides tools for describing other tools, searching tools, and other
tool-related operations.
"""

from typing import Any, Dict, List, Optional, cast

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.exceptions import ToolExecutionError
from pythonium.common.parameter_validation import validate_parameters
from pythonium.managers.tools.registry import ToolRegistry
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)

from .parameters import DescribeToolParams, SearchToolsParams


class DescribeToolTool(BaseTool):
    """Tool for describing other tools in the system."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="describe_tool",
            description="Get detailed information about any tool in the system to understand its purpose, parameters, usage patterns, and examples. Essential for discovering tool capabilities, understanding parameter requirements, and getting help on how to use specific tools effectively.",
            brief_description="Get detailed information about any tool in the system",
            detailed_description="Get comprehensive information about any tool including its description, parameters with types and constraints, usage examples, and metadata. Takes 'tool_name' (required) to specify which tool to describe, 'include_examples' (boolean) to include usage examples, 'include_schema' (boolean) to include detailed parameter schema, and 'include_metadata' (boolean) for comprehensive metadata. Essential for tool discovery, understanding capabilities, and learning proper usage patterns.",
            category="tools",
            tags=[
                "describe",
                "help",
                "documentation",
                "introspection",
                "discovery",
                "metadata",
                "parameters",
                "schema",
            ],
            parameters=[
                ToolParameter(
                    name="tool_name",
                    type=ParameterType.STRING,
                    description="Name of the tool to describe",
                    required=True,
                ),
                ToolParameter(
                    name="include_examples",
                    type=ParameterType.BOOLEAN,
                    description="Include usage examples in the description",
                    default=True,
                ),
                ToolParameter(
                    name="include_schema",
                    type=ParameterType.BOOLEAN,
                    description="Include detailed parameter schema",
                    default=True,
                ),
                ToolParameter(
                    name="include_metadata",
                    type=ParameterType.BOOLEAN,
                    description="Include comprehensive metadata information",
                    default=False,
                ),
            ],
        )

    def _get_tool_registry(
        self, context: Optional[ToolContext] = None
    ) -> Optional[ToolRegistry]:
        """Get the tool registry instance from the context or system."""
        try:
            # Try to get registry from context if available
            if context and hasattr(context, "registry"):
                return cast(ToolRegistry, context.registry)

            # Try to import and get a registry instance
            from pythonium.managers.tools.registry import ToolRegistry

            # Create a new registry instance as fallback
            # In a real application, this should be injected or managed globally
            return ToolRegistry()
        except Exception:
            return None

    def _generate_parameter_schema(
        self, parameters: List[ToolParameter]
    ) -> Dict[str, Any]:
        """Generate a detailed parameter schema."""
        schema = {}
        for param in parameters:
            param_info: Dict[str, Any] = {
                "type": param.type.value,
                "description": param.description,
                "required": param.required,
            }

            if param.default is not None:
                param_info["default"] = param.default

            if param.min_value is not None:
                param_info["min_value"] = param.min_value

            if param.max_value is not None:
                param_info["max_value"] = param.max_value

            if param.min_length is not None:
                param_info["min_length"] = param.min_length

            if param.max_length is not None:
                param_info["max_length"] = param.max_length

            if param.pattern is not None:
                param_info["pattern"] = param.pattern

            if param.allowed_values is not None:
                param_info["allowed_values"] = param.allowed_values

            schema[param.name] = param_info

        return schema

    def _get_example_value_for_type(self, param: ToolParameter) -> Any:
        """Get example value for a parameter based on its type."""
        if param.type == ParameterType.STRING:
            return f"example_{param.name}"
        elif param.type == ParameterType.INTEGER:
            return 1
        elif param.type == ParameterType.BOOLEAN:
            return True
        elif param.type == ParameterType.PATH:
            return "/path/to/example"
        elif param.type == ParameterType.ARRAY:
            return ["example1", "example2"]
        elif param.type == ParameterType.OBJECT:
            return {"key": "value"}
        else:
            return "example_value"

    def _create_basic_example(
        self, tool_name: str, parameters: List[ToolParameter]
    ) -> Dict[str, Any]:
        """Create basic usage example with required parameters only."""
        basic_params = {}
        for param in parameters:
            if param.required:
                basic_params[param.name] = self._get_example_value_for_type(param)

        return {
            "title": "Basic Usage",
            "description": f"Basic usage of {tool_name} with required parameters",
            "parameters": basic_params,
        }

    def _create_advanced_example(
        self,
        tool_name: str,
        parameters: List[ToolParameter],
        basic_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create advanced usage example with optional parameters."""
        advanced_params = basic_params.copy()
        for param in parameters:
            if not param.required and param.default is not None:
                advanced_params[param.name] = param.default

        return {
            "title": "Advanced Usage",
            "description": f"Advanced usage of {tool_name} with optional parameters",
            "parameters": advanced_params,
        }

    def _generate_usage_examples(
        self, tool_name: str, parameters: List[ToolParameter]
    ) -> List[Dict[str, Any]]:
        """Generate usage examples for a tool."""
        examples = []

        # Basic example with required parameters only
        basic_example = self._create_basic_example(tool_name, parameters)
        if basic_example["parameters"]:
            examples.append(basic_example)

        # Advanced example with optional parameters
        if any(not param.required for param in parameters):
            advanced_example = self._create_advanced_example(
                tool_name, parameters, basic_example["parameters"]
            )
            examples.append(advanced_example)

        return examples

    @validate_parameters(DescribeToolParams)
    @handle_tool_error
    async def execute(
        self, params: DescribeToolParams, context: ToolContext
    ) -> Result[Any]:
        """Execute tool description operation."""
        tool_name = params.tool_name
        include_examples = params.include_examples
        include_schema = params.include_schema
        include_metadata = params.include_metadata

        try:
            # Try to get tool from registry
            registry = self._get_tool_registry(context)
            tool_info = None

            if registry:
                # Get actual tool registration from registry
                tool_registrations = registry.list_tools()
                for registration in tool_registrations:
                    if registration.tool_id == tool_name:
                        tool_info = {
                            "description": registration.metadata.description,
                            "brief_description": registration.metadata.brief_description,
                            "detailed_description": registration.metadata.detailed_description,
                            "category": registration.metadata.category,
                            "tags": registration.metadata.tags,
                            "version": registration.metadata.version,
                            "dangerous": registration.metadata.dangerous,
                            "parameters": registration.metadata.parameters,
                        }
                        break

            if not tool_info:
                raise ToolExecutionError(f"Tool '{tool_name}' not found")

            result_data: Dict[str, Any] = {
                "tool_name": tool_name,
                "description": tool_info.get("description", "No description available"),
                "brief_description": tool_info.get("brief_description", ""),
                "category": tool_info.get("category", "unknown"),
                "tags": tool_info.get("tags", []),
            }

            # Add parameter schema if requested
            if include_schema:
                parameters = tool_info.get("parameters", [])
                if isinstance(parameters, list) and all(
                    hasattr(p, "type") for p in parameters
                ):
                    typed_parameters = cast(List[ToolParameter], parameters)
                    result_data["parameter_schema"] = self._generate_parameter_schema(
                        typed_parameters
                    )

            # Add usage examples if requested
            if include_examples:
                parameters = tool_info.get("parameters", [])
                if isinstance(parameters, list) and all(
                    hasattr(p, "type") for p in parameters
                ):
                    typed_parameters = cast(List[ToolParameter], parameters)
                    result_data["usage_examples"] = self._generate_usage_examples(
                        tool_name, typed_parameters
                    )

            # Add metadata if requested
            if include_metadata:
                metadata_info = {
                    "version": tool_info.get("version", "unknown"),
                    "dangerous": tool_info.get("dangerous", False),
                    "full_description": tool_info.get("detailed_description", ""),
                }
                result_data["metadata"] = metadata_info

            return Result[Any].success_result(
                data=result_data,
                metadata={
                    "tool_name": tool_name,
                    "include_examples": include_examples,
                    "include_schema": include_schema,
                    "include_metadata": include_metadata,
                },
            )

        except Exception as e:
            raise ToolExecutionError(f"Error describing tool '{tool_name}': {e}")


class SearchToolsTool(BaseTool):
    """Tool for searching and discovering tools in the system."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_tools",
            description="Search and discover tools in the system based on keywords, categories, tags, or functionality. Perfect for finding the right tool for a task, exploring available capabilities, or discovering new tools that might be useful for specific problems.",
            brief_description="Search and discover tools in the system",
            detailed_description="Search and discover tools in the system based on keywords, categories, tags, or functionality. Takes 'query' (required) for keyword search, 'category' (optional) to filter by tool category, 'tags' (optional array) to filter by specific tags, 'include_description' (boolean) to include tool descriptions, 'include_parameters' (boolean) to include parameter information, and 'limit' (optional) to restrict number of results. Perfect for tool discovery and finding the right tool for specific tasks.",
            category="tools",
            tags=[
                "search",
                "discover",
                "find",
                "tools",
                "help",
                "exploration",
                "capabilities",
            ],
            parameters=[
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="Search query for finding tools by name, description, or functionality",
                    required=True,
                ),
                ToolParameter(
                    name="category",
                    type=ParameterType.STRING,
                    description="Filter results by tool category (e.g., 'filesystem', 'network', 'system')",
                    required=False,
                ),
                ToolParameter(
                    name="tags",
                    type=ParameterType.ARRAY,
                    description="Filter results by tool tags",
                    required=False,
                ),
                ToolParameter(
                    name="include_description",
                    type=ParameterType.BOOLEAN,
                    description="Include tool descriptions in results",
                    default=True,
                ),
                ToolParameter(
                    name="include_parameters",
                    type=ParameterType.BOOLEAN,
                    description="Include parameter information in results",
                    default=False,
                ),
                ToolParameter(
                    name="limit",
                    type=ParameterType.INTEGER,
                    description="Maximum number of results to return",
                    default=20,
                    min_value=1,
                    max_value=100,
                ),
            ],
        )

    def _get_tool_registry(
        self, context: Optional[ToolContext] = None
    ) -> Optional[ToolRegistry]:
        """Get the tool registry instance from the context or system."""
        print(f"DEBUG _get_tool_registry: context={context}")
        print(f"DEBUG: context type: {type(context)}")

        try:
            # Import first to ensure it's available
            from pythonium.managers.tools.registry import ToolRegistry

            # Try to get registry from context if available
            if (
                context
                and hasattr(context, "registry")
                and context.registry is not None
            ):
                print(f"DEBUG: Found context.registry: {context.registry}")
                print(f"DEBUG: context.registry type: {type(context.registry)}")
                # For testing, the registry might be a mock, so return it directly
                return context.registry  # type: ignore

            print("DEBUG: Context or registry not available, creating new ToolRegistry")
            # Create a new registry instance as fallback
            # In a real application, this should be injected or managed globally
            return ToolRegistry()
        except Exception as e:
            print(f"DEBUG: Exception in _get_tool_registry: {e}")
            return None

    def _matches_query(self, tool: Dict[str, Any], query: str) -> bool:
        """Check if tool matches the search query."""
        query_lower = query.lower()

        print(
            f"DEBUG _matches_query: Checking tool '{tool['name']}' against query '{query}'"
        )
        print(f"DEBUG: Tool data: {tool}")

        # Check name
        if query_lower in tool["name"].lower():
            print("DEBUG: Matched on name")
            return True

        # Check description
        if query_lower in tool.get("description", "").lower():
            print("DEBUG: Matched on description")
            return True

        # Check brief description
        if query_lower in tool.get("brief_description", "").lower():
            print("DEBUG: Matched on brief_description")
            return True

        # Check tags
        for tag in tool.get("tags", []):
            if query_lower in tag.lower():
                print(f"DEBUG: Matched on tag '{tag}'")
                return True

        print("DEBUG: No match found")
        return False

    def _matches_category(self, tool: Dict[str, Any], category: str) -> bool:
        """Check if tool matches the category filter."""
        tool_category = tool.get("category", "")
        return str(tool_category).lower() == category.lower()

    def _matches_tags(self, tool: Dict[str, Any], tags: List[str]) -> bool:
        """Check if tool matches any of the tag filters."""
        tool_tags = [tag.lower() for tag in tool.get("tags", [])]
        filter_tags = [tag.lower() for tag in tags]

        # Tool must have at least one of the filter tags
        return any(tag in tool_tags for tag in filter_tags)

    def _get_tools_from_registry(self, registry) -> List[Dict[str, Any]]:
        """Get tools from registry and convert to search format."""
        print(f"DEBUG _get_tools_from_registry: registry={registry}")
        print(f"DEBUG: registry type: {type(registry)}")

        if not registry:
            print("DEBUG: Registry is None or falsy")
            return []

        tool_registrations = registry.list_tools()
        print(f"DEBUG: tool_registrations={tool_registrations}")
        print(f"DEBUG: tool_registrations type: {type(tool_registrations)}")
        print(
            f"DEBUG: Number of registrations: {len(tool_registrations) if tool_registrations else 'None'}"
        )

        all_tools = []
        for registration in tool_registrations:
            all_tools.append(
                {
                    "name": registration.tool_id,
                    "description": registration.metadata.description,
                    "brief_description": registration.metadata.brief_description,
                    "category": registration.metadata.category,
                    "tags": registration.metadata.tags,
                    "version": registration.metadata.version,
                    "dangerous": registration.metadata.dangerous,
                    "parameters": registration.metadata.parameters,
                }
            )
        print(f"DEBUG: Converted {len(all_tools)} tools")
        return all_tools

    def _filter_tools(
        self,
        all_tools: List[Dict[str, Any]],
        query: str,
        category: Optional[str],
        tags: List[str],
    ) -> List[Dict[str, Any]]:
        """Filter tools based on search criteria."""
        matching_tools = []

        for tool in all_tools:
            # Apply query filter
            if not self._matches_query(tool, query):
                continue

            # Apply category filter
            if category and not self._matches_category(tool, category):
                continue

            # Apply tags filter
            if tags and not self._matches_tags(tool, tags):
                continue

            matching_tools.append(tool)

        return matching_tools

    def _build_result_tools(
        self,
        matching_tools: List[Dict[str, Any]],
        include_description: bool,
        include_parameters: bool,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Build result tool objects with requested information."""
        result_tools = []

        for tool in matching_tools:
            # Build result item
            result_tool = {
                "name": tool["name"],
                "brief_description": tool.get("brief_description", ""),
                "category": tool.get("category", "unknown"),
                "tags": tool.get("tags", []),
                "dangerous": tool.get("dangerous", False),
            }

            if include_description:
                result_tool["description"] = tool.get("description", "")

            if include_parameters:
                result_tool["parameters"] = tool.get("parameters", [])

            result_tools.append(result_tool)

            # Apply limit
            if len(result_tools) >= limit:
                break

        return result_tools

    def _sort_tools_by_relevance(
        self, tools: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Sort tools by relevance (name matches first, then description matches)."""

        def sort_key(tool):
            name_match = query.lower() in tool["name"].lower()
            return (not name_match, tool["name"])

        return sorted(tools, key=sort_key)

    @validate_parameters(SearchToolsParams)
    @handle_tool_error
    async def execute(
        self, params: SearchToolsParams, context: ToolContext
    ) -> Result[Any]:
        """Execute tool search operation."""
        query = params.query
        category = params.category
        tags = params.tags or []
        include_description = params.include_description
        include_parameters = params.include_parameters
        limit = params.limit or 20

        try:
            # Get tools from registry
            registry = self._get_tool_registry(context)
            all_tools = self._get_tools_from_registry(registry)

            # Debug output
            print(f"DEBUG SearchToolsTool: Found {len(all_tools)} tools from registry")
            for tool in all_tools:
                print(f"DEBUG: Tool {tool['name']}: {tool}")

            # Filter tools based on search criteria
            matching_tools = self._filter_tools(all_tools, query, category, tags)

            print(
                f"DEBUG SearchToolsTool: After filtering, {len(matching_tools)} tools match"
            )

            # Build result tools with requested information
            result_tools = self._build_result_tools(
                matching_tools, include_description, include_parameters, limit
            )

            # Sort by relevance
            result_tools = self._sort_tools_by_relevance(result_tools, query)

            return Result[Any].success_result(
                data={
                    "query": query,
                    "filters": {
                        "category": category,
                        "tags": tags,
                    },
                    "tools": result_tools,
                    "total_found": len(result_tools),
                    "truncated": len(result_tools) >= limit,
                },
                metadata={
                    "search_query": query,
                    "category_filter": category,
                    "tags_filter": tags,
                    "include_description": include_description,
                    "include_parameters": include_parameters,
                    "limit": limit,
                },
            )

        except Exception as e:
            raise ToolExecutionError(f"Error searching tools: {e}")
