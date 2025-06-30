"""
MCP server message handlers.

This module provides message handlers for different MCP protocol
messages including initialization, tool calls, resource access, etc.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from pythonium.managers.security_manager import SecurityManager
from pythonium.managers.tools import (
    DependencyManager,
    ExecutionPipeline,
    PerformanceMonitor,
    ResultCache,
    ToolRegistry,
)
from pythonium.tools.base import BaseTool

from .config import MCPConfigManager
from .protocol import (
    InitializeResult,
    InternalError,
    InvalidParams,
    InvalidRequest,
    LogLevel,
    MCPError,
    MCPNotification,
    MCPProtocol,
    MCPRequest,
    MCPResponse,
    MessageType,
    MethodNotFound,
    Prompt,
    ServerCapabilities,
)
from .session import SessionManager

logger = logging.getLogger(__name__)


class MCPMessageHandler:
    """
    Handles MCP protocol messages.

    Processes incoming requests and generates appropriate responses
    according to the MCP specification.
    """

    def __init__(
        self,
        config_manager: MCPConfigManager,
        session_manager: SessionManager,
        tool_registry: Optional[ToolRegistry] = None,
        security_manager: Optional[SecurityManager] = None,
    ):
        self.config_manager = config_manager
        self.session_manager = session_manager
        self.protocol = MCPProtocol()

        # Tool management
        self.tool_registry = tool_registry or ToolRegistry()
        self.dependency_manager = DependencyManager()
        self.execution_pipeline = ExecutionPipeline(self.dependency_manager)
        self.result_cache = ResultCache()
        self.performance_monitor = PerformanceMonitor()

        # Security
        self.security_manager = security_manager

        # Server info
        config = self.config_manager.get_config()
        self.server_info = {
            "name": config.name,
            "version": config.version,
            "description": config.description,
        }

        # Capabilities
        self.server_capabilities = ServerCapabilities(
            tools=(
                {"listChanged": True} if config.tools.enable_tool_execution else None
            ),
            resources=(
                {"subscribe": True, "listChanged": True} if config.resources else None
            ),
            prompts=({"listChanged": True} if config.prompts.enable_prompts else None),
            logging={"level": config.logging.level},
        )

        # Message handlers mapping
        self._handlers: Dict[str, Callable] = {
            MessageType.INITIALIZE.value: self._handle_initialize,
            MessageType.PING.value: self._handle_ping,
            MessageType.LIST_TOOLS.value: self._handle_list_tools,
            MessageType.CALL_TOOL.value: self._handle_call_tool,
            MessageType.LIST_RESOURCES.value: self._handle_list_resources,
            MessageType.READ_RESOURCE.value: self._handle_read_resource,
            MessageType.LIST_PROMPTS.value: self._handle_list_prompts,
            MessageType.GET_PROMPT.value: self._handle_get_prompt,
            MessageType.COMPLETE.value: self._handle_completion,
            "tools/describe": self._handle_describe_tool,  # Custom handler for detailed tool info
        }

        # Resource handlers
        self._resource_handlers: Dict[str, Callable] = {}

        # Prompt handlers
        self._prompt_handlers: Dict[str, Callable] = {}

        # Background tasks
        self._notification_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the message handler."""
        if self._running:
            return

        self._running = True

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        # Start notification task
        self._notification_task = asyncio.create_task(self._notification_loop())

        logger.info("MCP message handler started")

    async def stop(self) -> None:
        """Stop the message handler."""
        if not self._running:
            return

        self._running = False

        # Stop performance monitoring
        self.performance_monitor.stop_monitoring()

        # Stop notification task
        if self._notification_task:
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass

        # Shutdown execution pipeline
        await self.execution_pipeline.shutdown()

        logger.info("MCP message handler stopped")

    async def handle_message(
        self, session_id: str, message: MCPRequest | MCPNotification
    ) -> Optional[MCPResponse]:
        """
        Handle an incoming MCP message.

        Args:
            session_id: Session ID
            message: MCP message to handle

        Returns:
            Response message (None for notifications)
        """
        start_time = datetime.now()

        try:
            # Update session activity
            await self.session_manager.update_session_activity(session_id)

            # Handle notification (no response)
            if isinstance(message, MCPNotification):
                await self._handle_notification(session_id, message)
                return None

            # Handle request
            if not isinstance(message, MCPRequest):
                raise InvalidRequest("Expected request or notification")

            # Check if handler exists
            handler = self._handlers.get(message.method)
            if not handler:
                raise MethodNotFound(f"Unknown method: {message.method}")

            # Authenticate request if security is enabled
            if self.security_manager:
                await self._authenticate_request(session_id, message)

            # Execute handler
            result = await handler(session_id, message)

            # Create response
            if message.id is None:
                logger.error("Received message with no ID, cannot create response")
                return None
            response = self.protocol.create_response(message.id, result)

            # Record metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.session_manager.record_response(
                session_id, response, response_time
            )

            # Record performance metrics
            self.performance_monitor.record_execution_time(
                f"mcp.{message.method}", response_time, success=True
            )

            return response

        except MCPError as e:
            # Create error response
            message_id = getattr(message, "id", None)
            if message_id is None:
                logger.error(
                    f"Cannot create error response for message with no ID: {e}"
                )
                return None
            response = self.protocol.create_error_response(message_id, e)

            # Record metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.session_manager.record_response(
                session_id, response, response_time
            )

            # Record performance metrics
            self.performance_monitor.record_execution_time(
                f"mcp.{getattr(message, 'method', 'unknown')}",
                response_time,
                success=False,
            )

            logger.warning(
                f"MCP error handling {getattr(message, 'method', 'unknown')}: {e}"
            )
            return response

        except Exception as e:
            # Unexpected error
            error = InternalError(f"Internal server error: {e}")
            message_id = getattr(message, "id", None)
            if message_id is None:
                logger.error(
                    f"Cannot create error response for message with no ID: {e}"
                )
                return None
            response = self.protocol.create_error_response(message_id, error)

            # Record metrics
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.session_manager.record_response(
                session_id, response, response_time
            )

            logger.error(
                f"Unexpected error handling {getattr(message, 'method', 'unknown')}: {e}"
            )
            return response

    async def _handle_initialize(
        self, session_id: str, request: MCPRequest
    ) -> InitializeResult:
        """Handle initialize request."""
        if not request.params:
            raise InvalidParams("Initialize params required")

        try:
            params = self.protocol.validate_initialize_params(request.params)
        except Exception as e:
            raise InvalidParams(f"Invalid initialize params: {e}")

        # Initialize session
        await self.session_manager.initialize_session(session_id, params)

        # Create response
        result = self.protocol.create_initialize_result(
            self.server_capabilities, self.server_info
        )

        logger.info(
            f"Session {session_id} initialized with client: {params.clientInfo}"
        )
        return result

    async def _handle_ping(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle ping request."""
        return {}

    async def _handle_list_tools(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle list tools request."""
        config = self.config_manager.get_config()
        if not config.tools.enable_tool_execution:
            return {"tools": []}

        brief = self._get_brief_flag(request)
        tools = self._build_tools_list(brief)
        return {"tools": tools}

    def _get_brief_flag(self, request: MCPRequest) -> bool:
        """Extract brief flag from request parameters."""
        if request.params and isinstance(request.params, dict):
            return bool(request.params.get("brief", False))
        return False

    def _build_tools_list(self, brief: bool) -> List[Dict[str, Any]]:
        """Build list of available tools with their schemas."""
        tools = []
        try:
            tool_registrations = self.tool_registry.list_tools()
            for tool_registration in tool_registrations:
                tool_schema = self._create_tool_schema(tool_registration, brief)
                tools.append(tool_schema)
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e
        return tools

    def _create_tool_schema(self, tool_registration, brief: bool) -> Dict[str, Any]:
        """Create JSON schema for a tool."""
        properties, required = self._build_parameter_schema(
            tool_registration.metadata.parameters
        )

        return {
            "name": tool_registration.tool_id,
            "description": tool_registration.metadata.get_description(brief=brief),
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def _build_parameter_schema(self, parameters) -> Tuple[Dict[str, Any], List[str]]:
        """Build parameter schema from tool parameters."""
        properties = {}
        required = []

        for param in parameters:
            param_type = self._convert_parameter_type(param.type)
            param_schema = {
                "type": param_type,
                "description": param.description,
            }

            # Add constraints if present
            self._add_parameter_constraints(param_schema, param)
            properties[param.name] = param_schema

            if param.required:
                required.append(param.name)

        return properties, required

    def _add_parameter_constraints(self, param_schema: Dict[str, Any], param):
        """Add constraints to parameter schema."""
        if param.min_value is not None:
            param_schema["minimum"] = param.min_value
        if param.max_value is not None:
            param_schema["maximum"] = param.max_value
        if param.min_length is not None:
            param_schema["minLength"] = param.min_length
        if param.max_length is not None:
            param_schema["maxLength"] = param.max_length
        if param.allowed_values is not None:
            param_schema["enum"] = param.allowed_values
        if param.default is not None:
            param_schema["default"] = param.default

    async def _handle_describe_tool(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle describe tool request for detailed tool information."""
        config = self.config_manager.get_config()
        if not config.tools.enable_tool_execution:
            raise InvalidRequest("Tool execution is disabled")

        tool_name = self._validate_tool_name(request)
        tool_registration = self._find_tool_registration(tool_name)
        return self._build_detailed_tool_response(tool_registration)

    def _validate_tool_name(self, request: MCPRequest) -> str:
        """Validate and extract tool name from request."""
        if not request.params or not request.params.get("name"):
            raise InvalidParams("Tool name required")
        return str(request.params["name"])

    def _find_tool_registration(self, tool_name: str):
        """Find tool registration by name."""
        try:
            tool_registrations = self.tool_registry.list_tools()
            for reg in tool_registrations:
                if reg.tool_id == tool_name:
                    return reg
            raise InvalidParams(f"Tool '{tool_name}' not found")
        except Exception as e:
            logger.exception(f"Error describing tool {tool_name}")
            raise InternalError(f"Failed to describe tool: {e}")

    def _build_detailed_tool_response(self, tool_registration) -> Dict[str, Any]:
        """Build detailed tool response with full descriptions."""
        properties, required = self._build_parameter_schema(
            tool_registration.metadata.parameters
        )

        return {
            "tool": {
                "name": tool_registration.tool_id,
                "description": tool_registration.metadata.get_detailed_description(),
                "brief_description": tool_registration.metadata.get_brief_description(),
                "category": tool_registration.metadata.category,
                "tags": tool_registration.metadata.tags,
                "version": tool_registration.metadata.version,
                "author": tool_registration.metadata.author,
                "dangerous": tool_registration.metadata.dangerous,
                "requires_auth": tool_registration.metadata.requires_auth,
                "max_execution_time": tool_registration.metadata.max_execution_time,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        }

    def _convert_parameter_type(self, param_type) -> str:
        """Convert ParameterType to JSON schema type."""
        from pythonium.tools.base import ParameterType

        type_mapping = {
            ParameterType.STRING: "string",
            ParameterType.INTEGER: "integer",
            ParameterType.FLOAT: "number",
            ParameterType.BOOLEAN: "boolean",
            ParameterType.ARRAY: "array",
            ParameterType.OBJECT: "object",
            ParameterType.PATH: "string",
            ParameterType.URL: "string",
            ParameterType.EMAIL: "string",
        }

        return type_mapping.get(param_type, "string")

    async def _handle_call_tool(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle call tool request."""
        config = self.config_manager.get_config()
        if not config.tools.enable_tool_execution:
            raise InvalidRequest("Tool execution is disabled")

        if not request.params:
            raise InvalidParams("Tool call params required")

        try:
            params = self.protocol.validate_tool_call_params(request.params)
        except Exception as e:
            raise InvalidParams(f"Invalid tool call params: {e}")

        # Check if tool exists
        if not self.tool_registry.has_tool(params.name):
            raise InvalidParams(f"Tool '{params.name}' not found")

        try:
            # Execute tool through pipeline
            result = await self.execution_pipeline.execute_single(
                tool_id=params.name,
                args=params.arguments or {},
                timeout=config.tools.tool_timeout_seconds,
                metadata={"session_id": session_id},
            )

            # Convert result to MCP format
            if result.success:
                # Extract content from ToolResult properly
                tool_result_obj = result.result

                if hasattr(tool_result_obj, "data") and tool_result_obj.data:
                    # For command execution, extract stdout from data
                    if (
                        isinstance(tool_result_obj.data, dict)
                        and "stdout" in tool_result_obj.data
                    ):
                        content_text = tool_result_obj.data["stdout"]
                    else:
                        content_text = str(tool_result_obj.data)
                elif hasattr(tool_result_obj, "success") and tool_result_obj.success:
                    # Fallback: try to get meaningful content
                    content_text = "Tool executed successfully"
                else:
                    content_text = str(tool_result_obj)

                content = [{"type": "text", "text": content_text}]
                tool_result = self.protocol.create_tool_result(content, is_error=False)
            else:
                error_content = [
                    {
                        "type": "text",
                        "text": f"Tool execution failed: {result.error}",
                    }
                ]
                tool_result = self.protocol.create_tool_result(
                    error_content, is_error=True
                )

            return tool_result.model_dump()

        except Exception as e:
            error_content = [{"type": "text", "text": f"Tool execution error: {e}"}]
            tool_result = self.protocol.create_tool_result(error_content, is_error=True)
            return tool_result.model_dump()

    async def _handle_list_resources(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle list resources request."""
        # For now, return empty list - this would be extended to support actual resources
        return {"resources": []}

    async def _handle_read_resource(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle read resource request."""
        if not request.params or "uri" not in request.params:
            raise InvalidParams("Resource URI required")

        uri = request.params["uri"]

        # Check if we have a handler for this resource
        handler = self._resource_handlers.get(uri)
        if not handler:
            raise InvalidParams(f"Resource '{uri}' not found")

        try:
            contents = await handler(session_id, uri)
            return {"contents": [contents]}
        except Exception as e:
            raise InternalError(f"Failed to read resource: {e}")

    async def _handle_list_prompts(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle list prompts request."""
        config = self.config_manager.get_config()
        if not config.prompts.enable_prompts:
            return {"prompts": []}

        # Get available prompts
        prompts = []
        for prompt_name, handler in self._prompt_handlers.items():
            # Get prompt metadata
            prompt_info = await self._get_prompt_info(prompt_name)
            if prompt_info:
                prompts.append(prompt_info.model_dump())

        return {"prompts": prompts}

    async def _handle_get_prompt(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle get prompt request."""
        config = self.config_manager.get_config()
        if not config.prompts.enable_prompts:
            raise InvalidRequest("Prompts are disabled")

        if not request.params or "name" not in request.params:
            raise InvalidParams("Prompt name required")

        prompt_name = request.params["name"]
        arguments = request.params.get("arguments", {})

        # Check if prompt exists
        handler = self._prompt_handlers.get(prompt_name)
        if not handler:
            raise InvalidParams(f"Prompt '{prompt_name}' not found")

        try:
            # Execute prompt handler
            result = await handler(session_id, arguments)
            return dict(result.model_dump())
        except Exception as e:
            raise InternalError(f"Failed to get prompt: {e}")

    async def _handle_completion(
        self, session_id: str, request: MCPRequest
    ) -> Dict[str, Any]:
        """Handle completion request."""
        # Completion is typically handled by AI models
        # For now, return empty completion
        return {"completion": {"values": []}}

    async def _handle_notification(
        self, session_id: str, notification: MCPNotification
    ) -> None:
        """Handle notification message."""
        # Process notifications (e.g., cancelled requests)
        if notification.method == MessageType.CANCEL_REQUEST.value:
            # Handle request cancellation
            if notification.params and "id" in notification.params:
                request_id = notification.params["id"]
                logger.info(f"Request {request_id} cancelled by client")

    async def _authenticate_request(self, session_id: str, request: MCPRequest) -> None:
        """Authenticate a request using security manager."""
        # This would integrate with the security manager for authentication
        pass

    def _convert_tool_schema(self, parameters: List[Any]) -> Dict[str, Any]:
        """Convert tool parameters to JSON schema."""
        schema: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

        for param in parameters:
            param_schema = {
                "type": "string",  # Default type
                "description": getattr(param, "description", ""),
            }

            # Map parameter types
            if hasattr(param, "parameter_type"):
                type_mapping = {
                    "string": "string",
                    "integer": "integer",
                    "number": "number",
                    "boolean": "boolean",
                    "array": "array",
                    "object": "object",
                }
                param_schema["type"] = type_mapping.get(
                    str(param.parameter_type), "string"
                )

            schema["properties"][param.name] = param_schema

            if getattr(param, "required", False):
                schema["required"].append(param.name)

        return schema

    async def _get_prompt_info(self, prompt_name: str) -> Optional[Prompt]:
        """Get prompt information."""
        # This would be implemented to return actual prompt metadata
        return None

    async def _notification_loop(self) -> None:
        """Background loop for sending notifications."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Send periodic notifications

                # Send tool list changed notification if tools were updated
                # This would be triggered by actual tool changes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")

    def register_resource_handler(self, uri: str, handler: Callable) -> None:
        """Register a resource handler."""
        self._resource_handlers[uri] = handler
        logger.debug(f"Registered resource handler for: {uri}")

    def register_prompt_handler(self, name: str, handler: Callable) -> None:
        """Register a prompt handler."""
        self._prompt_handlers[name] = handler
        logger.debug(f"Registered prompt handler: {name}")

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the handler."""
        # First register with the tool registry, which returns the tool_id
        tool_id = self.tool_registry.register_tool(tool.__class__)

        # Create a wrapper function that uses the tool's run method (includes validation)
        async def tool_wrapper(**kwargs):
            from pythonium.tools.base import ToolContext

            context = ToolContext()
            result = await tool.run(kwargs, context)
            return result  # Return the full ToolResult object

        # Register with execution pipeline using the same tool_id
        self.execution_pipeline.register_tool(tool_id, tool_wrapper)
        logger.debug(f"Registered tool: {tool_id}")

    async def send_notification(
        self,
        session_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a notification to a client."""
        # This would be handled by the transport layer
        logger.debug(f"Sending notification {method} to session {session_id}")

    async def send_log_message(
        self,
        session_id: str,
        level: LogLevel,
        message: str,
        logger_name: Optional[str] = None,
    ) -> None:
        """Send a log message to the client."""
        await self.send_notification(
            session_id,
            MessageType.LOG_MESSAGE.value,
            {"level": level.value, "data": message, "logger": logger_name},
        )
