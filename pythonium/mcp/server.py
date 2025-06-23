"""
Modern MCP server implementation for Pythonium.

This implementation uses the new service layer, tool registry,
and middleware for maintainability and testability.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import mcp.server.stdio
import mcp.server.sse
import mcp.types as types
from mcp.server import Server
from mcp.types import ServerCapabilities, ToolsCapability

from pythonium.analyzer import Analyzer
from pythonium.cli import find_project_root, get_or_create_config

from .utils.debug import setup_debug_logging, setup_minimal_logging, profiler, profile_operation, logger, info_log, warning_log, error_log
from .services import ServiceRegistry
from .core import ToolRegistry, Middleware, MiddlewareChain
from .core.middleware import LoggingMiddleware, ValidationMiddleware, ErrorHandlingMiddleware, PerformanceMiddleware
from .handlers import ToolHandlers
from .tools.definitions import get_tool_definitions
from .tools.analysis import list_detectors, get_detector_info, analyze_issues, debug_profile
from .tools.configuration import get_configuration_schema, configure_analyzer_logging


class PythoniumMCPServer:
    """
    MCP server for Pythonium code health analysis.
    
    This server implementation provides:
    - Service layer with dependency injection
    - Tool registry for dynamic tool management
    - Middleware chain for cross-cutting concerns
    - Robust error handling and logging
    """
    
    def __init__(self, name: str = "pythonium", version: str = "0.1.0", debug: bool = False):
        """Initialize the MCP server."""
        
        # Setup logging
        if debug:
            setup_debug_logging()
            info_log(f"Initializing Pythonium MCP Server v{version}")
        else:
            setup_minimal_logging()
            warning_log(f"Initializing Pythonium MCP Server v{version}")
        
        # Configure analyzer logging
        configure_analyzer_logging(debug)
        
        # Initialize core components
        self.server = Server(name, version)
        self.name = name
        self.version = version
        self.debug = debug
        
        # Initialize service registry
        self.services = ServiceRegistry()
        
        # Initialize tool registry and middleware
        self.tool_registry = ToolRegistry()
        self.middleware_chain = MiddlewareChain()
        
        # Setup middleware
        self._setup_middleware()
        
        # Initialize handlers with service registry
        self.handlers = ToolHandlers(self.services)
        
        # Dynamically discover available detectors
        self._detector_info = self._discover_detectors()
        
        # Register tools
        self._register_tools()
        
        # Setup MCP handlers
        self._setup_handlers()
        
        if debug:
            info_log(f"MCP Server initialized with {len(self.available_detectors)} detectors")
            info_log(f"Tool registry: {self.tool_registry.get_registry_info()}")
        else:
            warning_log(f"MCP Server initialized with {len(self.available_detectors)} detectors")
    
    def _setup_middleware(self) -> None:
        """Setup the middleware chain."""
        # Add middleware in execution order
        self.middleware_chain.add(LoggingMiddleware())
        self.middleware_chain.add(ValidationMiddleware())
        self.middleware_chain.add(ErrorHandlingMiddleware())
        self.middleware_chain.add(PerformanceMiddleware())
        
        info_log(f"Middleware chain setup with {len(self.middleware_chain._middleware)} components")
    
    @profile_operation("discover_detectors")
    def _discover_detectors(self) -> Dict[str, Dict[str, Any]]:
        """Dynamically discover available detectors."""
        try:
            project_root = find_project_root(Path.cwd())
            config = get_or_create_config(project_root, auto_create=False)
            analyzer = Analyzer(root_path=project_root, config=config)
            
            detector_info = {}
            for detector_id, detector in analyzer.detectors.items():
                info = {
                    "id": detector.id,
                    "name": detector.name,
                    "description": detector.description,
                    "type": "core",
                    "category": getattr(detector, 'category', 'Code Analysis'),
                    "usage_tips": getattr(detector, 'usage_tips', f"Use for focused analysis of {detector.description.lower()}"),
                    "related_detectors": getattr(detector, 'related_detectors', []),
                    "typical_severity": getattr(detector, 'typical_severity', 'info'),
                    "detailed_description": getattr(detector, 'detailed_description', detector.description)
                }
                detector_info[detector_id] = info
            
            info_log(f"Discovered {len(detector_info)} detectors")
            
            return detector_info
            
        except Exception as e:
            error_log("Failed to discover detectors: %s", str(e))
            raise RuntimeError(f"Could not discover available detectors: {str(e)}")
    
    @property
    def available_detectors(self) -> List[str]:
        """Get list of available detector IDs."""
        return list(self._detector_info.keys())
    
    def _register_tools(self) -> None:
        """Register all tools with the tool registry."""
        tools = get_tool_definitions()
        
        for tool in tools:
            self.tool_registry.register(
                name=tool.name,
                handler=self._get_tool_handler(tool.name),
                schema=tool,
                category=self._get_tool_category(tool.name),
                description=tool.description
            )
        
        info_log(f"Registered {len(tools)} tools with registry")
    
    def _get_tool_category(self, tool_name: str) -> str:
        """Get category for a tool."""
        category_map = {
            'analyze_code': 'Code Analysis',
            'analyze_inline_code': 'Code Analysis', 
            'execute_code': 'Code Execution',
            'list_detectors': 'Configuration',
            'get_detector_info': 'Configuration',
            'analyze_issues': 'Issue Management',
            'get_configuration_schema': 'Configuration',
            'debug_profile': 'Debugging',
            'update_issue': 'Issue Tracking',
            'list_issues': 'Issue Tracking',
            'get_issue': 'Issue Tracking',
            'get_next_issue': 'Issue Tracking',
            'investigate_issue': 'Issue Tracking',
            'repair_python_syntax': 'Code Repair'
        }
        return category_map.get(tool_name, 'General')
    
    def _get_tool_handler(self, tool_name: str) -> Callable:
        """Get handler for a tool."""
        handler_map = {
            'analyze_code': self.handlers.analyze_code,
            'analyze_inline_code': self.handlers.analyze_inline_code,
            'execute_code': self.handlers.execute_code,
            'list_detectors': lambda args: list_detectors(self, args),
            'get_detector_info': lambda args: get_detector_info(self, args),
            'analyze_issues': lambda args: analyze_issues(self, args),
            'get_configuration_schema': lambda args: get_configuration_schema(self, args),
            'debug_profile': lambda args: debug_profile(self, args),
            'update_issue': self.handlers.update_issue,
            'list_issues': self.handlers.list_issues,
            'get_issue': self.handlers.get_issue,
            'get_next_issue': self.handlers.get_next_issue,
            'investigate_issue': self.handlers.investigate_issue,
            'repair_python_syntax': self.handlers.repair_python_syntax
        }
        return handler_map.get(tool_name, lambda args: [types.TextContent(type="text", text=f"Unknown tool: {tool_name}")])
    
    def _setup_handlers(self) -> None:
        """Set up MCP message handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools():
            """Return list of available tools."""
            info_log("list_tools handler called")
            tools = get_tool_definitions()
            info_log(f"Returning {len(tools)} tools")
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments):
            """Handle tool calls through middleware chain."""
            info_log(f"call_tool handler called - tool: {name}, args: {arguments}")
            if arguments is None:
                arguments = {}
            
            profiler.start_operation(f"tool_call_{name}", tool=name, args_keys=list(arguments.keys()))
            
            try:
                # Execute through middleware chain if available
                if self.tool_registry.is_registered(name):
                    tool_info = self.tool_registry.get_tool_info(name)
                    if tool_info and self.middleware_chain:
                        # Wrapper to match middleware signature
                        async def tool_wrapper(tool_name: str, args: Dict[str, Any]) -> List[types.Content]:
                            return await tool_info.handler(args)
                        return await self.middleware_chain.process(name, arguments, tool_wrapper)
                    elif tool_info:
                        return await tool_info.handler(arguments)
                
                # Direct execution if no middleware
                return await self._execute_tool_direct(name, arguments)
                
            except Exception as e:
                error_log("Error handling tool call: %s", str(e))
                profiler.end_operation(success=False, error=str(e))
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
            finally:
                if profiler.current_operation and profiler.current_operation.get("status") == "running":
                    profiler.end_operation(success=True)
    
    async def _execute_tool_direct(self, name: str, arguments: Dict[str, Any]) -> List[types.Content]:
        """Direct tool execution fallback."""
        if name == "analyze_code":
            return await self.handlers.analyze_code(arguments)
        elif name == "analyze_inline_code":
            return await self.handlers.analyze_inline_code(arguments)
        elif name == "execute_code":
            return await self.handlers.execute_code(arguments)
        elif name == "list_detectors":
            return await list_detectors(self, arguments)
        elif name == "get_detector_info":
            return await get_detector_info(self, arguments)
        elif name == "analyze_issues":
            return await analyze_issues(self, arguments)
        elif name == "get_configuration_schema":
            return await get_configuration_schema(self, arguments)
        elif name == "debug_profile":
            return await debug_profile(self, arguments)
        elif name == "update_issue":
            return await self.handlers.update_issue(arguments)
        elif name == "list_issues":
            return await self.handlers.list_issues(arguments)
        elif name == "get_issue":
            return await self.handlers.get_issue(arguments)
        elif name == "get_next_issue":
            return await self.handlers.get_next_issue(arguments)
        elif name == "investigate_issue":
            return await self.handlers.investigate_issue(arguments)
        elif name == "repair_python_syntax":
            return await self.handlers.repair_python_syntax(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get comprehensive server information."""
        return {
            "name": self.name,
            "version": self.version,
            "debug": self.debug,
            "detectors": {
                "count": len(self.available_detectors),
                "list": self.available_detectors
            },
            "services": {
                name: type(service).__name__ 
                for name, service in self.services._services.items()
            },
            "tool_registry": self.tool_registry.get_registry_info(),
            "middleware": self.middleware_chain.get_middleware_info()
        }
    
    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        import mcp.server.stdio
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream,
                self.server.create_initialization_options()
            )
