"""
MCP server transport layer implementations.

This module provides transport layer implementations for different
connection types including STDIO, HTTP, WebSocket, and TCP.
"""

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from aiohttp import WSMsgType, web
from aiohttp.web_request import Request
from aiohttp.web_ws import WebSocketResponse

from pythonium.common.exceptions import PythoniumError

from .config import TransportConfig
from .protocol import (
    MCPMessage,
    MCPNotification,
    MCPProtocol,
    MCPRequest,
    MCPResponse,
)
from .session import ConnectionType, SessionManager

logger = logging.getLogger(__name__)


class TransportError(PythoniumError):
    """Transport layer error."""

    pass


class Transport(ABC):
    """Abstract base class for transport implementations."""

    def __init__(
        self,
        config: TransportConfig,
        session_manager: SessionManager,
        message_handler: Callable[[str, MCPMessage], Any],
    ):
        self.config = config
        self.session_manager = session_manager
        self.message_handler = message_handler
        self.protocol = MCPProtocol()
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start the transport."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport."""
        pass

    @abstractmethod
    async def send_message(self, session_id: str, message: MCPMessage) -> None:
        """Send a message to a client."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if transport is running."""
        return self._running


class StdioTransport(Transport):
    """
    STDIO transport implementation.

    Handles communication over standard input/output streams.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_id: Optional[str] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._stdin_reader: Optional[asyncio.StreamReader] = None
        self._stdout_writer: Optional[asyncio.StreamWriter] = None

    async def start(self) -> None:
        """Start STDIO transport."""
        if self._running:
            return

        try:
            # Set up stdin/stdout streams
            loop = asyncio.get_event_loop()
            self._stdin_reader = asyncio.StreamReader()
            stdin_protocol = asyncio.StreamReaderProtocol(self._stdin_reader)
            # Use buffer property for binary access
            stdin_buffer = sys.stdin.buffer if hasattr(sys.stdin, "buffer") else sys.stdin.detach()  # type: ignore
            await loop.connect_read_pipe(lambda: stdin_protocol, stdin_buffer)

            # Set up stdout writer
            stdout_transport, stdout_protocol = await loop.connect_write_pipe(
                lambda: asyncio.StreamReaderProtocol(asyncio.StreamReader()),
                sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout.detach(),  # type: ignore
            )
            self._stdout_writer = asyncio.StreamWriter(
                transport=stdout_transport,
                protocol=stdout_protocol,
                reader=None,
                loop=loop,
            )

            # Create session
            self._session_id = await self.session_manager.create_session(
                connection_type=ConnectionType.STDIO,
                metadata={"transport": "stdio"},
            )

            # Start reading messages
            self._reader_task = asyncio.create_task(self._read_messages())
            self._running = True

            logger.info("STDIO transport started")

        except Exception as e:
            logger.error(f"Failed to start STDIO transport: {e}")
            raise TransportError(f"Failed to start STDIO transport: {e}")

    async def stop(self) -> None:
        """Stop STDIO transport."""
        if not self._running:
            return

        self._running = False

        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Close session
        if self._session_id:
            await self.session_manager.close_session(
                self._session_id, "Transport shutdown"
            )

        logger.info("STDIO transport stopped")

    async def send_message(self, session_id: str, message: MCPMessage) -> None:
        """Send message via STDOUT."""
        if not self._running or session_id != self._session_id:
            return

        try:
            message_json = self.protocol.serialize_message(message)
            sys.stdout.write(message_json + "\n")
            sys.stdout.flush()

            # Record metrics
            if isinstance(message, MCPResponse):
                await self.session_manager.record_response(session_id, message, 0.0)
            elif isinstance(message, MCPNotification):
                await self.session_manager.record_notification(session_id, message)

        except Exception as e:
            logger.error(f"Failed to send message via STDIO: {e}")

    async def _process_message_line(self, line: str) -> None:
        """Process a single message line from STDIN."""
        try:
            # Parse message
            message = self.protocol.parse_message(line)

            # Update session activity
            if self._session_id:
                await self.session_manager.update_session_activity(self._session_id)

                # Record request metrics
                if isinstance(message, MCPRequest):
                    await self.session_manager.record_request(self._session_id, message)

            # Handle message
            if self._session_id:
                await self.message_handler(self._session_id, message)

        except Exception as e:
            logger.error(f"Failed to process STDIO message: {e}")
            # Send error response if it was a request
            if self._session_id and hasattr(message, "id") and message.id:
                error_response = self.protocol.create_error_response(
                    message.id, {"code": -32603, "message": str(e)}
                )
                await self.send_message(self._session_id, error_response)

    async def _read_stdin_lines(self) -> None:
        """Read and process lines from STDIN."""
        if not self._stdin_reader:
            return

        while self._running:
            line_bytes = await self._stdin_reader.readline()
            if not line_bytes:
                break

            line = line_bytes.decode().strip()
            if not line:
                continue

            await self._process_message_line(line)

    async def _read_messages(self) -> None:
        """Read messages from STDIN."""
        if not self._stdin_reader:
            logger.error("STDIN reader not initialized")
            return

        try:
            await self._read_stdin_lines()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in STDIO message reader: {e}")


class HttpTransport(Transport):
    """
    HTTP transport implementation.

    Handles communication over HTTP requests/responses.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def start(self) -> None:
        """Start HTTP transport."""
        if self._running:
            return

        try:
            # Create web application
            self._app = web.Application()
            self._app.router.add_post("/", self._handle_http_request)
            self._app.router.add_options("/", self._handle_options)

            # Add CORS middleware if enabled
            if hasattr(self.config, "cors_enabled") and self.config.cors_enabled:
                self._app.middlewares.append(self._cors_middleware)

            # Start server
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            self._site = web.TCPSite(
                self._runner,
                self.config.host or "localhost",
                self.config.port or 8080,
            )
            await self._site.start()

            self._running = True
            logger.info(
                f"HTTP transport started on {self.config.host}:{self.config.port}"
            )

        except Exception as e:
            logger.error(f"Failed to start HTTP transport: {e}")
            raise TransportError(f"Failed to start HTTP transport: {e}")

    async def stop(self) -> None:
        """Stop HTTP transport."""
        if not self._running:
            return

        self._running = False

        # Stop server
        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        logger.info("HTTP transport stopped")

    async def send_message(self, session_id: str, message: MCPMessage) -> None:
        """Send message via HTTP response (handled in request handler)."""
        # HTTP responses are handled directly in the request handler
        pass

    async def _handle_http_request(self, request: Request) -> web.Response:
        """Handle HTTP request."""
        try:
            # Create session for this request
            session_id = await self.session_manager.create_session(
                connection_type=ConnectionType.HTTP,
                remote_address=request.remote,
                metadata={
                    "transport": "http",
                    "user_agent": request.headers.get("User-Agent"),
                    "path": request.path,
                },
            )

            # Read request body
            body = await request.text()

            # Parse MCP message
            message = self.protocol.parse_message(body)

            # Update session activity and metrics
            await self.session_manager.update_session_activity(session_id)
            if isinstance(message, MCPRequest):
                await self.session_manager.record_request(session_id, message)

            # Handle message and get response
            response_message = await self.message_handler(session_id, message)

            # Close session after handling
            await self.session_manager.close_session(
                session_id, "HTTP request completed"
            )

            # Return HTTP response
            if response_message:
                response_json = self.protocol.serialize_message(response_message)
                return web.Response(
                    text=response_json,
                    content_type="application/json",
                    headers=self._get_cors_headers(),
                )
            else:
                return web.Response(status=204, headers=self._get_cors_headers())

        except Exception as e:
            logger.error(f"Error handling HTTP request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": (getattr(message, "id", None) if "message" in locals() else None),
            }
            return web.Response(
                text=json.dumps(error_response),
                status=500,
                content_type="application/json",
                headers=self._get_cors_headers(),
            )

    async def _handle_options(self, request: Request) -> web.Response:
        """Handle CORS preflight request."""
        return web.Response(headers=self._get_cors_headers())

    def _get_cors_headers(self) -> Dict[str, str]:
        """Get CORS headers."""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
        }

    @web.middleware
    async def _cors_middleware(self, request: Request, handler):
        """CORS middleware."""
        response = await handler(request)
        response.headers.update(self._get_cors_headers())
        return response


class WebSocketTransport(Transport):
    """
    WebSocket transport implementation.

    Handles communication over WebSocket connections.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._websockets: Dict[str, WebSocketResponse] = {}

    async def start(self) -> None:
        """Start WebSocket transport."""
        if self._running:
            return

        try:
            # Create web application
            self._app = web.Application()
            self._app.router.add_get("/", self._handle_websocket)

            # Start server
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            self._site = web.TCPSite(
                self._runner,
                self.config.host or "localhost",
                self.config.port or 8080,
            )
            await self._site.start()

            self._running = True
            logger.info(
                f"WebSocket transport started on {self.config.host}:{self.config.port}"
            )

        except Exception as e:
            logger.error(f"Failed to start WebSocket transport: {e}")
            raise TransportError(f"Failed to start WebSocket transport: {e}")

    async def stop(self) -> None:
        """Stop WebSocket transport."""
        if not self._running:
            return

        self._running = False

        # Close all websockets
        for ws in self._websockets.values():
            await ws.close()
        self._websockets.clear()

        # Stop server
        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        logger.info("WebSocket transport stopped")

    async def send_message(self, session_id: str, message: MCPMessage) -> None:
        """Send message via WebSocket."""
        if session_id in self._websockets:
            ws = self._websockets[session_id]
            try:
                message_json = self.protocol.serialize_message(message)
                await ws.send_str(message_json)

                # Record metrics
                if isinstance(message, MCPResponse):
                    await self.session_manager.record_response(session_id, message, 0.0)
                elif isinstance(message, MCPNotification):
                    await self.session_manager.record_notification(session_id, message)

            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                # Remove closed websocket
                self._websockets.pop(session_id, None)

    async def _handle_websocket(self, request: Request) -> WebSocketResponse:
        """Handle WebSocket connection."""
        ws = WebSocketResponse()
        await ws.prepare(request)

        # Create session
        session_id = await self.session_manager.create_session(
            connection_type=ConnectionType.WEBSOCKET,
            remote_address=request.remote,
            metadata={
                "transport": "websocket",
                "user_agent": request.headers.get("User-Agent"),
            },
        )

        # Store websocket
        self._websockets[session_id] = ws

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        # Parse message
                        message = self.protocol.parse_message(msg.data)

                        # Update session activity and metrics
                        await self.session_manager.update_session_activity(session_id)
                        if isinstance(message, MCPRequest):
                            await self.session_manager.record_request(
                                session_id, message
                            )

                        # Handle message
                        await self.message_handler(session_id, message)

                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
                        # Send error response
                        if hasattr(message, "id") and message.id:
                            error_response = self.protocol.create_error_response(
                                message.id,
                                {"code": -32603, "message": str(e)},
                            )
                            await self.send_message(session_id, error_response)

                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break

                elif msg.type == WSMsgType.CLOSE:
                    break

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")

        finally:
            # Clean up
            self._websockets.pop(session_id, None)
            await self.session_manager.close_session(
                session_id, "WebSocket connection closed"
            )

        return ws


def create_transport(
    config: TransportConfig,
    session_manager: SessionManager,
    message_handler: Callable[[str, MCPMessage], Any],
) -> Transport:
    """
    Create a transport instance based on configuration.

    Args:
        config: Transport configuration
        session_manager: Session manager instance
        message_handler: Message handler function

    Returns:
        Transport instance

    Raises:
        TransportError: If transport type is not supported
    """
    transport_map = {
        "stdio": StdioTransport,
        "http": HttpTransport,
        "websocket": WebSocketTransport,
    }

    transport_class = transport_map.get(config.type.lower())
    if not transport_class:
        raise TransportError(f"Unsupported transport type: {config.type}")

    return transport_class(config, session_manager, message_handler)  # type: ignore
