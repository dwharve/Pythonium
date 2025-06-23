"""
Tool registry for dynamic tool management in Pythonium MCP server.

Provides a clean registry pattern for managing MCP tools, eliminating
the need for large if/elif chains and enabling dynamic tool discovery.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

import mcp.types as types

from ..utils.debug import info_log, warning_log, error_log, profiler


@dataclass
class ToolDefinition:
    """
    Definition of an MCP tool including its handler and metadata.
    """
    name: str
    handler: Callable[[Dict[str, Any]], Awaitable[List[types.TextContent]]]
    schema: types.Tool
    category: str = "general"
    description: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = self.schema.description


class ToolRegistry:
    """
    Registry for managing MCP tools with dynamic discovery and execution.
    
    This registry provides:
    - Dynamic tool registration and discovery
    - Clean separation between tool definitions and handlers
    - Consistent error handling and profiling
    - Category-based tool organization
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Awaitable[List[types.TextContent]]],
        schema: types.Tool,
        category: str = "general",
        description: str = ""
    ) -> None:
        """
        Register a tool with the registry.
        
        Args:
            name: Unique name for the tool
            handler: Async function to handle tool calls
            schema: MCP tool schema definition
            category: Category for organization (analysis, execution, etc.)
            description: Optional description override
        """
        if name in self._tools:
            warning_log(f"Tool '{name}' is already registered, replacing existing registration")
        
        tool_def = ToolDefinition(
            name=name,
            handler=handler,
            schema=schema,
            category=category,
            description=description
        )
        
        self._tools[name] = tool_def
        
        # Update category index
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
        
        info_log(f"Registered tool '{name}' in category '{category}'")
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool from the registry.
        
        Args:
            name: Name of the tool to unregister
            
        Returns:
            True if the tool was unregistered, False if it wasn't found
        """
        if name not in self._tools:
            return False
        
        tool_def = self._tools.pop(name)
        
        # Remove from category index
        if tool_def.category in self._categories:
            try:
                self._categories[tool_def.category].remove(name)
                if not self._categories[tool_def.category]:
                    del self._categories[tool_def.category]
            except ValueError:
                pass  # Tool wasn't in category list
        
        info_log(f"Unregistered tool '{name}'")
        return True
    
    def get_tool_definitions(self) -> List[types.Tool]:
        """
        Get all registered tool schemas for MCP list_tools response.
        
        Returns:
            List of MCP tool schemas
        """
        return [tool_def.schema for tool_def in self._tools.values()]
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """
        Get tool names by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of tool names in the category
        """
        return self._categories.get(category, [])
    
    def get_categories(self) -> List[str]:
        """
        Get all registered categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def is_registered(self, name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            name: Tool name to check
            
        Returns:
            True if the tool is registered
        """
        return name in self._tools
    
    def get_tool_info(self, name: str) -> Optional[ToolDefinition]:
        """
        Get information about a registered tool.
        
        Args:
            name: Tool name
            
        Returns:
            ToolDefinition if found, None otherwise
        """
        return self._tools.get(name)
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """
        Execute a tool by name with the given arguments.
        
        Args:
            name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution results
            
        Raises:
            ValueError: If the tool is not registered
            Exception: If the tool execution fails
        """
        if name not in self._tools:
            available_tools = ", ".join(self._tools.keys())
            raise ValueError(f"Unknown tool: {name}. Available tools: {available_tools}")
        
        tool_def = self._tools[name]
        
        # Start profiling
        profiler.start_operation(
            f"tool_call_{name}",
            tool=name,
            category=tool_def.category,
            args_keys=list(arguments.keys()) if arguments else []
        )
        
        try:
            info_log(f"Executing tool '{name}' with arguments: {list(arguments.keys()) if arguments else []}")
            
            # Execute the tool handler
            result = await tool_def.handler(arguments or {})
            
            profiler.end_operation(success=True)
            info_log(f"Tool '{name}' executed successfully")
            
            return result
            
        except Exception as e:
            error_log(f"Tool '{name}' execution failed: {str(e)}")
            profiler.end_operation(success=False, error=str(e))
            
            # Return error as text content
            return [types.TextContent(
                type="text",
                text=f"Error executing tool '{name}': {str(e)}"
            )]
    
    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the registry state.
        
        Returns:
            Dictionary with registry information
        """
        return {
            "total_tools": len(self._tools),
            "categories": {
                category: len(tools) 
                for category, tools in self._categories.items()
            },
            "tools": {
                name: {
                    "category": tool_def.category,
                    "description": tool_def.description
                }
                for name, tool_def in self._tools.items()
            }
        }
    
    def clear(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self._tools.clear()
        self._categories.clear()
        info_log("Tool registry cleared")
