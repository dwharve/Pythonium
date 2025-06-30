"""
Main MCP server implementation.

This module provides the core MCP server class that orchestrates
all components including configuration, session management, transport,
and message handling.
"""

import asyncio
import logging
import signal
from typing import Any, Dict, List, Optional

from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger
from pythonium.managers.plugin_manager import PluginManager
from pythonium.managers.security_manager import SecurityManager
from pythonium.managers.tools import ToolDiscoveryManager
from pythonium.tools.base import BaseTool

from .config import MCPConfigManager, TransportType
from .handlers import MCPMessageHandler
from .protocol import MCPMessage, MCPNotification, MCPRequest
from .session import SessionManager
from .transport import Transport, create_transport

logger = get_logger(__name__)


class MCPServerError(PythoniumError):
    """MCP server error."""

    pass


class MCPServer:
    """
    Main MCP (Model Context Protocol) server.

    Provides a complete MCP server implementation that can handle
    multiple transport types and manages client sessions, tools,
    resources, and prompts according to the MCP specification.
    """

    def __init__(
        self,
        config_file: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ):
        # Configuration
        self.config_manager = MCPConfigManager()
        self.config = self.config_manager.load_config(config_file, config_overrides)

        # Core components
        self.session_manager = SessionManager(
            session_timeout_minutes=self.config.performance.request_timeout_seconds
            // 60,
            max_sessions=self.config.performance.max_concurrent_requests,
        )

        # Security manager (optional)
        self.security_manager = None
        if self.config.security.authentication_method.value != "none":
            self.security_manager = SecurityManager()

        # Message handler
        self.message_handler = MCPMessageHandler(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            security_manager=self.security_manager,
        )

        # Transport
        self.transport: Optional[Transport] = None

        # Tool management
        self.tool_discovery = ToolDiscoveryManager()
        self.plugin_manager: Optional[PluginManager] = None

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Setup logging
        self._setup_logging()

        logger.info(
            f"MCP Server initialized with transport: {self.config.transport.type}"
        )

    async def start(self) -> None:
        """
        Start the MCP server.

        Raises:
            MCPServerError: If server fails to start
        """
        if self._running:
            logger.warning("Server is already running")
            return

        try:
            logger.info("Starting MCP server...")

            # Validate configuration
            config_issues = self.config_manager.validate_config()
            if config_issues:
                raise MCPServerError(
                    f"Configuration validation failed: {config_issues}"
                )

            # Start session manager
            await self.session_manager.start()

            # Start message handler
            await self.message_handler.start()

            # Discover and register tools
            await self._discover_and_register_tools()

            # Initialize plugin system if enabled
            if self.config.enable_experimental_features:
                await self._initialize_plugins()

            # Create and start transport
            self.transport = create_transport(
                config=self.config.transport,
                session_manager=self.session_manager,
                message_handler=self._handle_transport_message,
            )
            await self.transport.start()

            # Setup signal handlers
            self._setup_signal_handlers()

            self._running = True
            logger.info(
                f"MCP server started successfully on {self.config.transport.type}"
            )

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self._cleanup()
            raise MCPServerError(f"Server startup failed: {e}")

    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._running:
            return

        logger.info("Stopping MCP server...")
        self._running = False

        await self._cleanup()

        # Signal shutdown complete
        self._shutdown_event.set()

        logger.info("MCP server stopped")

    async def run(self) -> None:
        """
        Run the server until shutdown.

        This method will block until the server is stopped.
        """
        await self.start()

        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
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
        self.message_handler.register_tool(tool)
        logger.debug(f"Registered tool: {tool.metadata.name}")

    def register_tools(self, tools: List[BaseTool]) -> None:
        """
        Register multiple tools with the server.

        Args:
            tools: List of tool instances to register
        """
        for tool in tools:
            self.register_tool(tool)

        logger.info(f"Registered {len(tools)} tools")

    def register_resource_handler(self, uri: str, handler) -> None:
        """
        Register a resource handler.

        Args:
            uri: Resource URI pattern
            handler: Handler function
        """
        self.message_handler.register_resource_handler(uri, handler)
        logger.debug(f"Registered resource handler for: {uri}")

    def register_prompt_handler(self, name: str, handler) -> None:
        """
        Register a prompt handler.

        Args:
            name: Prompt name
            handler: Handler function
        """
        self.message_handler.register_prompt_handler(name, handler)
        logger.debug(f"Registered prompt handler: {name}")

    async def send_notification(
        self,
        session_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Send a notification to a client.

        Args:
            session_id: Target session ID
            method: Notification method
            params: Notification parameters
        """
        if self.transport:
            notification = self.message_handler.protocol.create_notification(
                method, params
            )
            await self.transport.send_message(session_id, notification)

    async def broadcast_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Broadcast a notification to all active sessions.

        Args:
            method: Notification method
            params: Notification parameters
        """
        active_sessions = await self.session_manager.get_active_sessions()
        for session in active_sessions:
            await self.send_notification(session.session_id, method, params)

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "description": self.config.description,
            "transport": self.config.transport.type.value,
            "running": self._running,
            "debug_mode": self.config.debug_mode,
        }

    async def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        session_summary = await self.session_manager.get_session_summary()

        stats = {
            "server_info": self.get_server_info(),
            "sessions": session_summary,
            "uptime_seconds": 0,  # Would track actual uptime
            "tools": {
                "total_registered": len(
                    self.message_handler.tool_registry.list_tools()
                ),
                "categories": {},  # Would categorize tools
            },
        }

        # Add performance metrics if monitoring is enabled
        if hasattr(self.message_handler, "performance_monitor"):
            stats["performance"] = (
                self.message_handler.performance_monitor.get_all_tools_summary()
            )

        return stats

    async def _handle_transport_message(
        self, session_id: str, message: MCPMessage
    ) -> Optional[MCPMessage]:
        """
        Handle a message from the transport layer.

        Args:
            session_id: Session ID
            message: Received message

        Returns:
            Response message (if any)
        """
        try:
            # Handle the message through the message handler
            if isinstance(message, (MCPRequest, MCPNotification)):
                response = await self.message_handler.handle_message(
                    session_id, message
                )

                # Send response through transport if it's a request
                if response and self.transport:
                    await self.transport.send_message(session_id, response)

                return response
            else:
                logger.warning(f"Received unexpected message type: {type(message)}")
                return None

        except Exception as e:
            logger.error(f"Error handling transport message: {e}")

            # Send error response if it was a request
            if (
                isinstance(message, MCPRequest)
                and self.transport
                and message.id is not None
            ):
                error_response = self.message_handler.protocol.create_error_response(
                    message.id,
                    {"code": -32603, "message": f"Internal error: {e}"},
                )
                await self.transport.send_message(session_id, error_response)

            return None

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

    async def _initialize_plugins(self) -> None:
        """Initialize the plugin system."""
        try:
            self.plugin_manager = PluginManager()
            await self.plugin_manager.initialize()

            # Load plugins would go here
            # await self.plugin_manager.load_plugins_from_directory("plugins")

            logger.info("Plugin system initialized")

        except Exception as e:
            logger.error(f"Plugin system initialization failed: {e}")

    async def _cleanup(self) -> None:
        """Clean up server resources."""
        try:
            # Stop transport
            if self.transport:
                await self.transport.stop()
                self.transport = None

            # Stop message handler
            await self.message_handler.stop()

            # Stop session manager
            await self.session_manager.stop()

            # Stop plugin manager
            if self.plugin_manager:
                await self.plugin_manager.shutdown()
                self.plugin_manager = None

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        logging_config = self.config.logging

        # Set log level
        log_level = getattr(logging, logging_config.level.upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)

        # Configure file logging if specified
        if logging_config.log_file:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                logging_config.log_file,
                maxBytes=logging_config.max_log_file_size_mb * 1024 * 1024,
                backupCount=logging_config.log_file_backup_count,
            )
            file_handler.setFormatter(logging.Formatter(logging_config.log_format))
            logging.getLogger().addHandler(file_handler)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")

        # Schedule shutdown
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(self.stop())
        else:
            asyncio.run(self.stop())


# Factory functions for different server configurations


def create_stdio_server(
    config_overrides: Optional[Dict[str, Any]] = None,
) -> MCPServer:
    """
    Create an MCP server configured for STDIO transport.

    Args:
        config_overrides: Configuration overrides

    Returns:
        Configured MCP server
    """
    overrides = config_overrides or {}
    overrides.setdefault("transport", {})["type"] = TransportType.STDIO.value

    return MCPServer(config_overrides=overrides)


def create_http_server(
    host: str = "localhost",
    port: int = 8080,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> MCPServer:
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
    transport_config = {
        "type": TransportType.HTTP.value,
        "host": host,
        "port": port,
    }
    overrides["transport"] = transport_config

    return MCPServer(config_overrides=overrides)


def create_websocket_server(
    host: str = "localhost",
    port: int = 8080,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> MCPServer:
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
    transport_config = {
        "type": TransportType.WEBSOCKET.value,
        "host": host,
        "port": port,
    }
    overrides["transport"] = transport_config

    return MCPServer(config_overrides=overrides)
