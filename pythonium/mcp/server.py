"""
Main MCP server implementation for Pythonium.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import mcp.server.stdio
    import mcp.server.sse
    import mcp.types as types
    from mcp.server import Server
    from mcp.types import ServerCapabilities, ToolsCapability
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from pythonium.analyzer import Analyzer
from pythonium.cli import find_project_root, get_or_create_config
from .debug import setup_debug_logging, setup_minimal_logging, profiler, profile_operation, logger, info_log, warning_log, error_log
from .handlers import ToolHandlers
from .tool_definitions import get_tool_definitions
from .analysis_tools import list_detectors, get_detector_info, analyze_issues, debug_profile
from .configuration_tools import get_configuration_schema
from .config_utilities import configure_analyzer_logging

class PythoniumMCPServer:
    """MCP server for Pythonium code health analysis."""
    
    def __init__(self, name: str = "pythonium", version: str = "0.1.0", debug: bool = False):
        """Initialize the MCP server."""
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP dependencies not available. Install with: "
                "pip install mcp"
            )
        
        # Setup debug logging only if requested
        if debug:
            setup_debug_logging()
            info_log(f"Initializing Pythonium MCP Server v{version}")
        else:
            # Setup minimal logging - only warnings and errors to console
            setup_minimal_logging()
            warning_log(f"Initializing Pythonium MCP Server v{version}")
        
        # Configure analyzer logging to respect debug mode
        configure_analyzer_logging(debug)
        
        self.server = Server(name, version)
        self.name = name
        self.version = version
        self.debug = debug
        
        # Initialize tool handlers
        self.handlers = ToolHandlers(self)
        
        # Dynamically discover available detectors
        self._detector_info = self._discover_detectors()
        
        # Setup MCP handlers
        self._setup_handlers()
        
        if debug:
            info_log(f"MCP Server initialized with {len(self.available_detectors)} detectors")
        else:
            # Log at WARNING level so it shows in minimal logging mode
            warning_log(f"MCP Server initialized with {len(self.available_detectors)} detectors")
    
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
            """Handle tool calls with profiling."""
            info_log(f"call_tool handler called - tool: {name}, args: {arguments}")
            if arguments is None:
                arguments = {}
            
            profiler.start_operation(f"tool_call_{name}", tool=name, args_keys=list(arguments.keys()))
            
            try:
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
                elif name == "mark_issue":
                    return await self.handlers.mark_issue(arguments)
                elif name == "list_tracked_issues":
                    return await self.handlers.list_tracked_issues(arguments)
                elif name == "get_issue_info":
                    return await self.handlers.get_issue_info(arguments)
                elif name == "suppress_issue":
                    return await self.handlers.suppress_issue(arguments)
                elif name == "get_tracking_statistics":
                    return await self.handlers.get_tracking_statistics(arguments)
                elif name == "add_agent_note":
                    return await self.handlers.add_agent_note(arguments)
                elif name == "get_agent_actions":
                    return await self.handlers.get_agent_actions(arguments)
                elif name == "investigate_issue":
                    return await self.handlers.investigate_issue(arguments)
                elif name == "repair_python_syntax":
                    return await self.handlers.repair_python_syntax(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
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

    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        import mcp.server.stdio
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream,
                self.server.create_initialization_options()
            )
