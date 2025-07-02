"""
MCP (Model Context Protocol) core protocol implementation.

This module implements the core MCP protocol specification including
message types, request/response handling, and protocol utilities.
"""

import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel


# Base types and utilities
class Role(str, Enum):
    """The sender or recipient of messages and data in a conversation."""

    ASSISTANT = "assistant"
    USER = "user"


class BaseMetadata(BaseModel):
    """Base interface for metadata with name (identifier) and title (display name) properties."""

    name: str
    title: Optional[str] = None


class RequestId(BaseModel):
    """Request identifier type."""

    id: Union[str, int]


class ProgressToken(BaseModel):
    """Progress token for tracking progress of operations."""

    token: Union[str, int]


class Cursor(BaseModel):
    """Cursor for pagination."""

    cursor: str


class EmptyResult(BaseModel):
    """Empty result for operations that don't return data."""

    pass


# Content Block Types (Union type for all content)
# Will be defined later after the content classes are defined
ContentBlock = None


# JSON-RPC base types
class JSONRPCMessage(BaseModel):
    """Base JSON-RPC message."""

    jsonrpc: Literal["2.0"] = "2.0"


class JSONRPCRequest(JSONRPCMessage):
    """JSON-RPC request message."""

    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(JSONRPCMessage):
    """JSON-RPC response message."""

    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional["JSONRPCError"] = None


class JSONRPCError(BaseModel):
    """JSON-RPC error object."""

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCNotification(JSONRPCMessage):
    """JSON-RPC notification message."""

    method: str
    params: Optional[Dict[str, Any]] = None


# Notification types
class Notification(BaseModel):
    """Base notification type."""

    method: str
    params: Optional[Dict[str, Any]] = None


class CancelledNotification(Notification):
    """Notification sent when a request is cancelled."""

    method: Literal["notifications/cancelled"] = "notifications/cancelled"
    params: Dict[str, Union[str, int]]  # requestId


class InitializedNotification(Notification):
    """Notification sent when initialization is complete."""

    method: Literal["notifications/initialized"] = "notifications/initialized"


class ProgressNotification(Notification):
    """Notification for progress updates."""

    method: Literal["notifications/progress"] = "notifications/progress"
    params: Optional[Dict[str, Any]] = None  # Will contain ProgressParams


class LoggingMessageNotification(Notification):
    """Notification for logging messages."""

    method: Literal["notifications/message"] = "notifications/message"
    params: Optional[Dict[str, Any]] = None  # Will contain LoggingParams


class ResourceListChangedNotification(Notification):
    """Notification when resource list changes."""

    method: Literal["notifications/resources/list_changed"] = (
        "notifications/resources/list_changed"
    )


class ResourceUpdatedNotification(Notification):
    """Notification when a resource is updated."""

    method: Literal["notifications/resources/updated"] = (
        "notifications/resources/updated"
    )
    params: Dict[str, str]  # uri


class PromptListChangedNotification(Notification):
    """Notification when prompt list changes."""

    method: Literal["notifications/prompts/list_changed"] = (
        "notifications/prompts/list_changed"
    )


class ToolListChangedNotification(Notification):
    """Notification when tool list changes."""

    method: Literal["notifications/tools/list_changed"] = (
        "notifications/tools/list_changed"
    )


class RootsListChangedNotification(Notification):
    """Notification when roots list changes."""

    method: Literal["notifications/roots/list_changed"] = (
        "notifications/roots/list_changed"
    )


# Request/Response types
class Request(BaseModel):
    """Base request type."""

    method: str
    params: Optional[Dict[str, Any]] = None


class Result(BaseModel):
    """Base result type."""

    pass


class ClientRequest(Request):
    """Base type for client-initiated requests."""

    pass


class ServerRequest(Request):
    """Base type for server-initiated requests."""

    pass


class ClientResult(Result):
    """Base type for results from client requests."""

    pass


class ServerResult(Result):
    """Base type for results from server requests."""

    pass


class ClientNotification(Notification):
    """Base type for client notifications."""

    pass


class ServerNotification(Notification):
    """Base type for server notifications."""

    pass


# Schema definition types
class PrimitiveSchemaDefinition(BaseModel):
    """Base class for primitive schema definitions."""

    type: str
    description: Optional[str] = None


class StringSchema(PrimitiveSchemaDefinition):
    """String schema definition."""

    type: Literal["string"] = "string"
    enum: Optional[List[str]] = None
    const: Optional[str] = None


class NumberSchema(PrimitiveSchemaDefinition):
    """Number schema definition."""

    type: Literal["number"] = "number"
    minimum: Optional[float] = None
    maximum: Optional[float] = None


class BooleanSchema(PrimitiveSchemaDefinition):
    """Boolean schema definition."""

    type: Literal["boolean"] = "boolean"


class EnumSchema(BaseModel):
    """Enum schema definition."""

    enum: List[Union[str, int, float]]
    description: Optional[str] = None


# Additional missing types
class Implementation(BaseModel):
    """Implementation details."""

    name: str
    version: str


class LoggingLevel(str, Enum):
    """Logging levels."""

    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class ModelHint(BaseModel):
    """Hint about which model to use."""

    name: Optional[str] = None


class ModelPreferences(BaseModel):
    """Model preferences for sampling."""

    hints: Optional[List[ModelHint]] = None
    costPriority: Optional[float] = None
    speedPriority: Optional[float] = None
    intelligencePriority: Optional[float] = None


class SamplingMessage(BaseModel):
    """Message for sampling operations."""

    role: Role
    content: Any  # ContentBlock (defined later)


class Root(BaseModel):
    """Represents a root directory or file that the server can operate on."""

    uri: str
    name: Optional[str] = None


class ResourceTemplate(BaseModel):
    """Template for creating resources."""

    uriTemplate: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ResourceTemplateReference(BaseModel):
    """Reference to a resource template."""

    type: Literal["ref/template"] = "ref/template"
    uriTemplate: str


class PromptReference(BaseModel):
    """Reference to a prompt."""

    type: Literal["ref/prompt"] = "ref/prompt"
    name: str


class ToolAnnotations(BaseModel):
    """Annotations specific to tools."""

    title: Optional[str] = None


# Pagination types
class PaginatedRequest(BaseModel):
    """Base for paginated requests."""

    cursor: Optional[str] = None


class PaginatedResult(BaseModel):
    """Base for paginated results."""

    nextCursor: Optional[str] = None


# Specific request types
class CreateMessageRequest(ServerRequest):
    """Request to create a message via LLM sampling."""

    method: Literal["sampling/createMessage"] = "sampling/createMessage"
    params: Dict[str, Any]  # Contains messages, modelPreferences, etc.


class CreateMessageResult(ServerResult):
    """Result from message creation."""

    content: Any  # ContentBlock (defined later)
    model: str
    stopReason: Optional[str] = None


class ElicitRequest(ServerRequest):
    """Request to elicit information from the user."""

    method: Literal["elicitation/create"] = "elicitation/create"
    params: Dict[str, Any]


class ElicitResult(ServerResult):
    """Result from elicitation."""

    content: Any  # ContentBlock (defined later)


class ListRootsRequest(ServerRequest):
    """Request to list available roots."""

    method: Literal["roots/list"] = "roots/list"


class ListRootsResult(ServerResult):
    """Result from listing roots."""

    roots: List[Root]


class ListResourceTemplatesResult(ClientResult):
    """Result from listing resource templates."""

    resourceTemplates: List[ResourceTemplate]


class ListPromptsResult(ClientResult):
    """Result from listing prompts."""

    prompts: List["Prompt"]


class ListResourcesResult(ClientResult):
    """Result from listing resources."""

    resources: List["Resource"]


class ListToolsResult(ClientResult):
    """Result from listing tools."""

    tools: List["Tool"]


class ReadResourceResult(ClientResult):
    """Result from reading a resource."""

    contents: List["ResourceContents"]


class CallToolResult(ClientResult):
    """Result from calling a tool."""

    content: List[Any]  # List[ContentBlock] (defined later)
    isError: Optional[bool] = None


class CompleteResult(ClientResult):
    """Result from completion."""

    completion: Dict[str, Any]


class MCPVersion(str, Enum):
    """Supported MCP protocol versions."""

    V2024_11_05 = "2024-11-05"


class MessageType(str, Enum):
    """MCP message types."""

    # Client to server
    INITIALIZE = "initialize"
    PING = "ping"
    LIST_RESOURCES = "resources/list"
    LIST_RESOURCE_TEMPLATES = "resources/templates/list"
    READ_RESOURCE = "resources/read"
    SUBSCRIBE = "resources/subscribe"
    UNSUBSCRIBE = "resources/unsubscribe"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    COMPLETE = "completion/complete"
    SET_LOGGING_LEVEL = "logging/setLevel"

    # Server to client requests
    CREATE_MESSAGE = "sampling/createMessage"
    LIST_ROOTS = "roots/list"
    ELICIT = "elicitation/create"

    # Server to client notifications
    INITIALIZED = "notifications/initialized"
    PROGRESS = "notifications/progress"
    RESOURCE_UPDATED = "notifications/resources/updated"
    RESOURCE_LIST_CHANGED = "notifications/resources/list_changed"
    PROMPT_LIST_CHANGED = "notifications/prompts/list_changed"
    TOOL_LIST_CHANGED = "notifications/tools/list_changed"
    LOG_MESSAGE = "notifications/message"
    ROOTS_LIST_CHANGED = "notifications/roots/list_changed"

    # Bidirectional
    CANCEL_REQUEST = "notifications/cancelled"


class LogLevel(str, Enum):
    """Log levels for MCP messages."""

    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class ResourceType(str, Enum):
    """Resource types."""

    TEXT = "text"
    BLOB = "blob"


class PromptArgumentType(str, Enum):
    """Prompt argument types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


# Base message classes
class MCPMessage(BaseModel):
    """Base MCP message."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None


class MCPRequest(MCPMessage):
    """MCP request message."""

    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(MCPMessage):
    """MCP response message."""

    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPNotification(MCPMessage):
    """MCP notification message."""

    method: str
    params: Optional[Dict[str, Any]] = None


# Content types for MCP protocol
class Annotations(BaseModel):
    """Optional annotations for the client."""

    audience: Optional[List[str]] = None
    lastModified: Optional[str] = None
    priority: Optional[float] = None


class TextContent(BaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str
    annotations: Optional[Annotations] = None


class ImageContent(BaseModel):
    """Image content block."""

    type: Literal["image"] = "image"
    data: str  # base64-encoded image data
    mimeType: str
    annotations: Optional[Annotations] = None


class AudioContent(BaseModel):
    """Audio content block."""

    type: Literal["audio"] = "audio"
    data: str  # base64-encoded audio data
    mimeType: str
    annotations: Optional[Annotations] = None


class ResourceLink(BaseModel):
    """Resource link content block."""

    type: Literal["resource"] = "resource"
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    size: Optional[int] = None
    title: Optional[str] = None
    annotations: Optional[Annotations] = None


class EmbeddedResource(BaseModel):
    """Embedded resource content block."""

    type: Literal["resource"] = "resource"
    resource: Union["TextResourceContents", "BlobResourceContents"]
    annotations: Optional[Annotations] = None


class TextResourceContents(BaseModel):
    """Text resource contents."""

    uri: str
    text: str
    mimeType: Optional[str] = None


class BlobResourceContents(BaseModel):
    """Binary resource contents."""

    uri: str
    blob: str  # base64-encoded binary data
    mimeType: Optional[str] = None


# Union type for all content blocks (defined once at module level)
ContentBlock = Union[
    TextContent, ImageContent, AudioContent, ResourceLink, EmbeddedResource
]


# Specific message types
class ClientCapabilities(BaseModel):
    """Client capabilities."""

    experimental: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class ServerCapabilities(BaseModel):
    """Server capabilities."""

    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None


class InitializeParams(BaseModel):
    """Initialize request parameters."""

    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Dict[str, Any]


class InitializeResult(BaseModel):
    """Initialize response result."""

    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Dict[str, Any]


class ResourceReference(BaseModel):
    """Resource reference."""

    uri: str
    type: Optional[ResourceType] = None


class Resource(BaseModel):
    """MCP resource."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ResourceContents(BaseModel):
    """Resource contents."""

    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None  # Base64 encoded


class PromptArgument(BaseModel):
    """Prompt argument definition."""

    name: str
    description: Optional[str] = None
    required: Optional[bool] = None


class Prompt(BaseModel):
    """MCP prompt."""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None


class PromptMessage(BaseModel):
    """Prompt message."""

    role: Literal["user", "assistant"]
    content: Union[str, Dict[str, Any]]


class GetPromptResult(BaseModel):
    """Get prompt result."""

    description: Optional[str] = None
    messages: List[PromptMessage]


class Tool(BaseModel):
    """MCP tool definition."""

    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any]


class CallToolParams(BaseModel):
    """Call tool parameters."""

    name: str
    arguments: Optional[Dict[str, Any]] = None


class ToolResult(BaseModel):
    """Tool execution result."""

    content: List[Dict[str, Any]]
    isError: Optional[bool] = None


class ProgressParams(BaseModel):
    """Progress notification parameters."""

    progressToken: Union[str, int]
    progress: int
    total: Optional[int] = None


class LoggingParams(BaseModel):
    """Logging notification parameters."""

    level: LogLevel
    data: Any
    logger: Optional[str] = None


class MCPError(Exception):
    """Base MCP error."""

    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON-RPC error response."""
        error_dict = {"code": self.code, "message": self.message}
        if self.data is not None:
            error_dict["data"] = self.data
        return error_dict


class ParseError(MCPError):
    """Parse error (-32700)."""

    def __init__(self, message: str = "Parse error", data: Optional[Any] = None):
        super().__init__(-32700, message, data)


class InvalidRequest(MCPError):
    """Invalid request (-32600)."""

    def __init__(self, message: str = "Invalid Request", data: Optional[Any] = None):
        super().__init__(-32600, message, data)


class MethodNotFound(MCPError):
    """Method not found (-32601)."""

    def __init__(self, message: str = "Method not found", data: Optional[Any] = None):
        super().__init__(-32601, message, data)


class InvalidParams(MCPError):
    """Invalid parameters (-32602)."""

    def __init__(self, message: str = "Invalid params", data: Optional[Any] = None):
        super().__init__(-32602, message, data)


class InternalError(MCPError):
    """Internal error (-32603)."""

    def __init__(self, message: str = "Internal error", data: Optional[Any] = None):
        super().__init__(-32603, message, data)


class RequestCancelled(MCPError):
    """Request cancelled (-32800)."""

    def __init__(self, message: str = "Request cancelled", data: Optional[Any] = None):
        super().__init__(-32800, message, data)


class MCPProtocol:
    """
    MCP protocol implementation.

    Handles message parsing, validation, and serialization according to
    the MCP specification.
    """

    def __init__(self, version: MCPVersion = MCPVersion.V2024_11_05):
        self.version = version
        self._request_id_counter = 0

    def create_request_id(self) -> str:
        """Create a unique request ID."""
        self._request_id_counter += 1
        return f"req_{self._request_id_counter}_{uuid.uuid4().hex[:8]}"

    def parse_message(
        self, data: str
    ) -> Union[MCPRequest, MCPResponse, MCPNotification]:
        """
        Parse a JSON-RPC message from string.

        Args:
            data: JSON string to parse

        Returns:
            Parsed MCP message

        Raises:
            ParseError: If JSON parsing fails
            InvalidRequest: If message structure is invalid
        """
        raw_message = self._parse_json(data)
        self._validate_json_rpc(raw_message)
        return self._create_message_object(raw_message)

    def _parse_json(self, data: str) -> dict:
        """Parse JSON data and validate basic structure."""
        try:
            raw_message = json.loads(data)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}")

        if not isinstance(raw_message, dict):
            raise InvalidRequest("Message must be a JSON object")

        return raw_message

    def _validate_json_rpc(self, raw_message: dict):
        """Validate JSON-RPC version."""
        if raw_message.get("jsonrpc") != "2.0":
            raise InvalidRequest("Invalid JSON-RPC version")

    def _create_message_object(
        self, raw_message: dict
    ) -> Union[MCPRequest, MCPResponse, MCPNotification]:
        """Create appropriate message object based on message type."""
        if "method" in raw_message:
            return self._create_method_message(raw_message)
        elif "id" in raw_message:
            return self._create_response_message(raw_message)
        else:
            raise InvalidRequest("Message must have 'method' or 'id' field")

    def _create_method_message(
        self, raw_message: dict
    ) -> Union[MCPRequest, MCPNotification]:
        """Create request or notification based on presence of id."""
        if "id" in raw_message:
            try:
                return MCPRequest(**raw_message)
            except Exception as e:
                raise InvalidRequest(f"Invalid request format: {e}")
        else:
            try:
                return MCPNotification(**raw_message)
            except Exception as e:
                raise InvalidRequest(f"Invalid notification format: {e}")

    def _create_response_message(self, raw_message: dict) -> MCPResponse:
        """Create response message."""
        try:
            return MCPResponse(**raw_message)
        except Exception as e:
            raise InvalidRequest(f"Invalid response format: {e}")

    def serialize_message(self, message: MCPMessage) -> str:
        """
        Serialize an MCP message to JSON string.

        Args:
            message: MCP message to serialize

        Returns:
            JSON string representation
        """
        return message.model_dump_json(exclude_none=True)

    def create_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> MCPRequest:
        """Create an MCP request."""
        return MCPRequest(id=self.create_request_id(), method=method, params=params)

    def create_response(
        self, request_id: Union[str, int], result: Any = None
    ) -> MCPResponse:
        """Create an MCP response."""
        return MCPResponse(id=request_id, result=result)

    def create_error_response(
        self,
        request_id: Union[str, int],
        error: Union[MCPError, Dict[str, Any]],
    ) -> MCPResponse:
        """Create an MCP error response."""
        if isinstance(error, MCPError):
            error_dict = error.to_dict()
        else:
            error_dict = error

        return MCPResponse(id=request_id, error=error_dict)

    def create_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> MCPNotification:
        """Create an MCP notification."""
        return MCPNotification(method=method, params=params)

    def validate_initialize_params(self, params: Dict[str, Any]) -> InitializeParams:
        """Validate initialize request parameters."""
        try:
            return InitializeParams(**params)
        except Exception as e:
            raise InvalidParams(f"Invalid initialize parameters: {e}")

    def create_initialize_result(
        self, capabilities: ServerCapabilities, server_info: Dict[str, Any]
    ) -> InitializeResult:
        """Create initialize response result."""
        return InitializeResult(
            protocolVersion=self.version.value,
            capabilities=capabilities,
            serverInfo=server_info,
        )

    def validate_tool_call_params(self, params: Dict[str, Any]) -> CallToolParams:
        """Validate tool call parameters."""
        try:
            return CallToolParams(**params)
        except Exception as e:
            raise InvalidParams(f"Invalid tool call parameters: {e}")

    def create_tool_result(
        self, content: List[Dict[str, Any]], is_error: bool = False
    ) -> ToolResult:
        """Create tool result."""
        return ToolResult(content=content, isError=is_error)

    def create_progress_notification(
        self,
        progress_token: Union[str, int],
        progress: int,
        total: Optional[int] = None,
    ) -> MCPNotification:
        """Create progress notification."""
        params = ProgressParams(
            progressToken=progress_token, progress=progress, total=total
        )
        return self.create_notification(MessageType.PROGRESS.value, params.model_dump())

    def create_log_notification(
        self, level: LogLevel, data: Any, logger: Optional[str] = None
    ) -> MCPNotification:
        """Create log notification."""
        params = LoggingParams(level=level, data=data, logger=logger)
        return self.create_notification(
            MessageType.LOG_MESSAGE.value, params.model_dump()
        )
