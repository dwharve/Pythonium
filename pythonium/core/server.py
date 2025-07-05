"""
MCP server implementation using the official MCP SDK.
"""

import asyncio
import logging
import signal
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from pythonium.common.config import TransportType
from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger
from pythonium.core.config import ConfigurationManager
from pythonium.core.tools import ToolDiscoveryManager
from pythonium.tools.base import BaseTool, ToolContext

logger = get_logger(__name__)


class ServerError(PythoniumError):
    """MCP SDK server error."""

    pass


class PythoniumMCPServer:
    """
    MCP server implementation using the official MCP SDK.

    This server provides the same functionality as the custom implementation
    but uses the official MCP SDK's FastMCP class for protocol handling.
    """

    def __init__(
        self,
        config_file: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ):
        # Configuration
        self.config_manager = ConfigurationManager(config_file, config_overrides)
        self.config = self.config_manager.get_settings()

        # Create FastMCP server
        self.mcp_server = FastMCP(
            name=self.config.server.name,
            description=self.config.server.description,
        )

        # Tool management
        self.tool_discovery = ToolDiscoveryManager()

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._registered_tools: Dict[str, BaseTool] = {}

        # Setup logging
        self._setup_logging()

        logger.info(
            f"Pythonium MCP Server initialized with transport: {self.config.server.transport}"
        )

    async def start(self) -> None:
        """Start the MCP server."""
        if self._running:
            logger.warning("Server is already running")
            return

        try:
            logger.info("Starting Pythonium MCP server...")

            # Validate configuration
            config_issues = self.config_manager.validate_config()
            if config_issues:
                raise ServerError(f"Configuration validation failed: {config_issues}")

            # Discover and register tools
            await self._discover_and_register_tools()

            # Setup signal handlers
            self._setup_signal_handlers()

            self._running = True
            logger.info("Pythonium MCP server started successfully")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self._cleanup()
            raise ServerError(f"Server startup failed: {e}")

    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._running:
            return

        logger.info("Stopping Pythonium MCP server...")
        self._running = False

        await self._cleanup()

        # Signal shutdown complete
        self._shutdown_event.set()

        logger.info("Pythonium MCP server stopped")

    async def run(self) -> None:
        """
        Run the server until shutdown.

        This method determines the transport type and runs the server accordingly.
        """
        await self.start()

        try:
            # Determine transport type and run accordingly
            transport_type = self.config.server.transport.value.lower()

            def run_mcp_server(transport_type):
                """Run MCP server with specified transport."""
                if transport_type == "stdio":
                    # For stdio, we use the FastMCP's built-in run method
                    self.mcp_server.run(transport="stdio")
                elif transport_type == "http":
                    # For HTTP, we use streamable-http transport
                    self.mcp_server.run(transport="streamable-http")
                elif transport_type == "websocket":
                    # WebSocket transport (using SSE for now)
                    self.mcp_server.run(transport="sse")
                else:
                    raise ServerError(f"Unsupported transport type: {transport_type}")

            # Run the MCP server in the current event loop's thread pool
            await asyncio.get_event_loop().run_in_executor(
                None, run_mcp_server, transport_type
            )

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()

    async def run_forever(self) -> None:
        """Run the server forever (until interrupted)."""
        await self.run()

    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool with the server.

        Args:
            tool: Tool instance to register
        """
        tool_name = tool.metadata.name

        # Store the tool instance
        self._registered_tools[tool_name] = tool

        # Create the tool function for FastMCP with proper signature
        tool_func = self._create_dynamic_tool_function(tool)

        # Register the tool with FastMCP
        self.mcp_server.tool()(tool_func)

        logger.debug(f"Registered tool: {tool_name}")

    def _create_dynamic_tool_function(self, tool_instance: BaseTool):
        """Create a dynamic tool function with proper parameter signature."""
        import inspect

        # Build parameter signature dynamically
        parameters = []
        annotations = {}

        for param in tool_instance.metadata.parameters:
            # Map our parameter types to Python types
            python_type = self._map_parameter_type(param.type)
            annotations[param.name] = python_type

            # Create parameter with default value if not required
            if param.required:
                parameters.append(
                    inspect.Parameter(
                        param.name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=python_type,
                    )
                )
            else:
                default_value = param.default if param.default is not None else None
                parameters.append(
                    inspect.Parameter(
                        param.name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=default_value,
                        annotation=python_type,
                    )
                )

        # Create the function signature
        sig = inspect.Signature(parameters)

        # Create the actual function
        async def tool_function(*args, **kwargs):
            """Dynamically created tool function."""
            try:
                # Create tool context with proper dataclass fields
                context = ToolContext(
                    user_id=None,
                    session_id=None,
                    workspace_path=None,
                    environment={},
                    permissions={},
                    logger=logging.getLogger(
                        f"pythonium.tools.{tool_instance.metadata.name}"
                    ),
                    progress_callback=None,
                )

                # Bind arguments to parameters using the signature
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                parameters = dict(bound_args.arguments)

                # Execute the tool with parameters and context
                result = await tool_instance.execute(parameters, context)

                # Return the result data
                return result.data if result else None

            except Exception as e:
                logger.error(f"Error executing tool {tool_instance.metadata.name}: {e}")
                raise

        # Set function attributes
        tool_function.__name__ = tool_instance.metadata.name
        tool_function.__doc__ = tool_instance.metadata.description
        tool_function.__signature__ = sig  # type: ignore
        tool_function.__annotations__ = annotations

        return tool_function

    def register_tools(self, tools: List[BaseTool]) -> None:
        """
        Register multiple tools with the server.

        Args:
            tools: List of tool instances to register
        """
        for tool in tools:
            self.register_tool(tool)

        logger.info(f"Registered {len(tools)} tools")

    def _map_parameter_type(self, param_type) -> type:
        """Map tool parameter types to Python types."""
        from pythonium.tools.base import ParameterType

        type_mapping = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.NUMBER: float,
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: list,
            ParameterType.OBJECT: dict,
            ParameterType.PATH: str,
            ParameterType.URL: str,
            ParameterType.EMAIL: str,
        }

        return type_mapping.get(param_type, str)

    async def _discover_and_register_tools(self) -> None:
        """Discover and register available tools."""
        try:
            # Discover tools from the tools package
            discovered_tools_dict = self.tool_discovery.discover_tools()

            # Register discovered tools
            for tool_name, discovered_tool in discovered_tools_dict.items():
                try:
                    tool_instance = discovered_tool.tool_class()
                    self.register_tool(tool_instance)
                except Exception as e:
                    logger.warning(
                        f"Failed to register tool {discovered_tool.tool_class.__name__}: {e}"
                    )

            logger.info(f"Discovered and registered {len(discovered_tools_dict)} tools")

        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")

    async def _cleanup(self) -> None:
        """Clean up server resources."""
        try:
            # Clear registered tools
            self._registered_tools.clear()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Configure standard Python logging for FastMCP framework
        import logging

        # Get the log level from config
        log_level = self.config.logging.level.upper()

        # Map string levels to logging constants
        level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        python_log_level = level_mapping.get(log_level, logging.INFO)

        # Set the log level for all relevant loggers
        loggers_to_configure = [
            "mcp.server.fastmcp",
            "mcp.server",
            "mcp",
            "",  # root logger
        ]

        for logger_name in loggers_to_configure:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.setLevel(python_log_level)

        # Also configure the handler level if needed
        root_logger = logging.getLogger()
        if root_logger.handlers:
            for handler in root_logger.handlers:
                handler.setLevel(python_log_level)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, _frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")

        # Create a task to stop the server
        asyncio.create_task(self.stop())

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "name": self.config.server.name,
            "version": self.config.server.version,
            "description": self.config.server.description,
            "transport": self.config.server.transport.value,
            "running": self._running,
            "debug_mode": self.config.debug_mode,
            "sdk_type": "official_mcp_sdk",
        }

    def get_registered_tools(self) -> Dict[str, BaseTool]:
        """Get currently registered tools."""
        return self._registered_tools.copy()


# Factory functions for different server configurations


def create_stdio_server(
    config_overrides: Optional[Dict[str, Any]] = None,
) -> PythoniumMCPServer:
    """
    Create an MCP server configured for STDIO transport.

    Args:
        config_overrides: Configuration overrides

    Returns:
        Configured MCP server
    """
    overrides = config_overrides or {}
    overrides.setdefault("server", {})["transport"] = TransportType.STDIO.value

    return PythoniumMCPServer(config_overrides=overrides)


def create_http_server(
    host: str = "localhost",
    port: int = 8080,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> PythoniumMCPServer:
    """
    Create an MCP server configured for HTTP transport.

    Args:
        host: Server host
        port: Server port
        config_overrides: Configuration overrides

    Returns:
        Configured MCP server
    """
    overrides = config_overrides or {}
    server_config = {
        "transport": TransportType.HTTP.value,
        "host": host,
        "port": port,
    }
    overrides["server"] = server_config

    return PythoniumMCPServer(config_overrides=overrides)


def create_websocket_server(
    host: str = "localhost",
    port: int = 8080,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> PythoniumMCPServer:
    """
    Create an MCP server configured for WebSocket transport.

    Args:
        host: Server host
        port: Server port
        config_overrides: Configuration overrides

    Returns:
        Configured MCP server
    """
    overrides = config_overrides or {}
    server_config = {
        "transport": TransportType.WEBSOCKET.value,
        "host": host,
        "port": port,
    }
    overrides["server"] = server_config

    return PythoniumMCPServer(config_overrides=overrides)
