"""
Unit tests for MCP protocol implementation.

Tests protocol message types, serialization, validation,
and compliance with the MCP specification.
"""

import json
from typing import Any, Dict

import pytest

from pythonium.mcp_legacy.protocol import (  # Core protocol types; Result types; Content types; Error types; Other types
    Annotations,
    AudioContent,
    ClientCapabilities,
    ContentBlock,
    EmbeddedResource,
    ImageContent,
    InitializeResult,
    InternalError,
    InvalidParams,
    InvalidRequest,
    LogLevel,
    MCPError,
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    MCPVersion,
    MessageType,
    MethodNotFound,
    ParseError,
    ProgressParams,
    Prompt,
    PromptArgument,
    RequestCancelled,
    Resource,
    ResourceLink,
    Role,
    ServerCapabilities,
    TextContent,
    Tool,
)


class TestMCPProtocolTypes:
    """Test MCP protocol type definitions."""

    def test_mcp_message_creation(self):
        """Test basic MCPMessage creation."""
        msg = MCPMessage(jsonrpc="2.0", id="test-123")

        assert msg.jsonrpc == "2.0"
        assert msg.id == "test-123"

    def test_mcp_request_creation(self):
        """Test MCPRequest creation."""
        request = MCPRequest(id="req-1", method="test/method", params={"key": "value"})

        assert request.id == "req-1"
        assert request.method == "test/method"
        assert request.params == {"key": "value"}
        assert request.jsonrpc == "2.0"

    def test_mcp_response_creation(self):
        """Test MCPResponse creation."""
        response = MCPResponse(id="resp-1", result={"status": "success"})

        assert response.id == "resp-1"
        assert response.result == {"status": "success"}
        assert response.error is None
        assert response.jsonrpc == "2.0"

    def test_mcp_response_with_error(self):
        """Test MCPResponse creation with error."""
        error = MCPError(code=-32601, message="Method not found")

        response = MCPResponse(id="error-resp-1", error=error.to_dict())

        assert response.id == "error-resp-1"
        assert response.result is None
        assert response.error["code"] == -32601
        assert response.error["message"] == "Method not found"

    def test_mcp_notification_creation(self):
        """Test MCPNotification creation."""
        notification = MCPNotification(method="notifications/initialized", params={})

        assert notification.method == "notifications/initialized"
        assert notification.params == {}
        assert notification.jsonrpc == "2.0"
        assert not notification.id  # Should be None for notifications

    def test_message_type_enum(self):
        """Test MessageType enum values."""
        assert MessageType.INITIALIZE == "initialize"
        assert MessageType.PING == "ping"
        assert MessageType.LIST_TOOLS == "tools/list"
        assert MessageType.CALL_TOOL == "tools/call"
        assert MessageType.LIST_RESOURCES == "resources/list"

    def test_mcp_version_enum(self):
        """Test MCPVersion enum."""
        assert MCPVersion.V2024_11_05 == "2024-11-05"

    def test_role_enum(self):
        """Test Role enum."""
        assert Role.USER == "user"
        assert Role.ASSISTANT == "assistant"


class TestMCPContentTypes:
    """Test MCP content type definitions."""

    def test_text_content_creation(self):
        """Test TextContent creation."""
        content = TextContent(type="text", text="Hello, world!")

        assert content.type == "text"
        assert content.text == "Hello, world!"
        assert content.annotations is None

    def test_text_content_with_annotations(self):
        """Test TextContent with annotations."""
        annotations = Annotations(audience=[Role.USER], priority=0.8)

        content = TextContent(
            type="text", text="Important message", annotations=annotations
        )

        assert content.annotations.priority == 0.8
        assert content.annotations.audience == [Role.USER]

    def test_image_content_creation(self):
        """Test ImageContent creation."""
        content = ImageContent(
            type="image", data="base64encodeddata", mimeType="image/png"
        )

        assert content.type == "image"
        assert content.data == "base64encodeddata"
        assert content.mimeType == "image/png"

    def test_audio_content_creation(self):
        """Test AudioContent creation."""
        content = AudioContent(
            type="audio", data="base64encodedaudio", mimeType="audio/wav"
        )

        assert content.type == "audio"
        assert content.data == "base64encodedaudio"
        assert content.mimeType == "audio/wav"

    def test_resource_link_creation(self):
        """Test ResourceLink creation."""
        link = ResourceLink(
            type="resource",
            uri="file:///path/to/file.txt",
            name="test_file",
            description="A test file",
        )

        assert link.type == "resource"
        assert link.uri == "file:///path/to/file.txt"
        assert link.name == "test_file"
        assert link.description == "A test file"

    def test_embedded_resource_creation(self):
        """Test EmbeddedResource creation."""
        from pythonium.mcp_legacy.protocol import TextResourceContents

        resource_contents = TextResourceContents(
            uri="file:///test.txt", text="File contents", mimeType="text/plain"
        )

        embedded = EmbeddedResource(type="resource", resource=resource_contents)

        assert embedded.type == "resource"
        assert embedded.resource.text == "File contents"


class TestMCPErrorTypes:
    """Test MCP error type definitions."""

    def test_invalid_params_error(self):
        """Test InvalidParams error."""
        error = InvalidParams(message="Invalid parameters provided")

        assert error.code == -32602
        assert error.message == "Invalid parameters provided"

    def test_method_not_found_error(self):
        """Test MethodNotFound error."""
        error = MethodNotFound(message="Method not found")

        assert error.code == -32601
        assert error.message == "Method not found"

    def test_internal_error(self):
        """Test InternalError."""
        error = InternalError(message="Internal server error")

        assert error.code == -32603
        assert error.message == "Internal server error"

    def test_parse_error(self):
        """Test ParseError."""
        error = ParseError(message="Parse error")

        assert error.code == -32700
        assert error.message == "Parse error"

    def test_invalid_request_error(self):
        """Test InvalidRequest error."""
        error = InvalidRequest(message="Invalid request")

        assert error.code == -32600
        assert error.message == "Invalid request"

    def test_request_cancelled_error(self):
        """Test RequestCancelled error."""
        error = RequestCancelled(message="Request cancelled")

        assert error.code == -32800
        assert error.message == "Request cancelled"


class TestMCPResourceTypes:
    """Test MCP resource type definitions."""

    def test_resource_creation(self):
        """Test Resource creation."""
        resource = Resource(
            uri="file:///test/resource.txt",
            name="test_resource",
            description="A test resource",
            mimeType="text/plain",
        )

        assert resource.uri == "file:///test/resource.txt"
        assert resource.name == "test_resource"
        assert resource.description == "A test resource"
        assert resource.mimeType == "text/plain"

    def test_resource_minimal(self):
        """Test Resource with minimal fields."""
        resource = Resource(uri="file:///minimal.txt", name="minimal_resource")

        assert resource.uri == "file:///minimal.txt"
        assert resource.name == "minimal_resource"
        assert resource.description is None
        assert resource.mimeType is None


class TestMCPToolTypes:
    """Test MCP tool type definitions."""

    def test_tool_creation(self):
        """Test Tool creation."""
        schema = {"type": "object", "properties": {"message": {"type": "string"}}}

        tool = Tool(
            name="echo_tool", description="Echoes input back", inputSchema=schema
        )

        assert tool.name == "echo_tool"
        assert tool.description == "Echoes input back"
        assert tool.inputSchema == schema

    def test_tool_with_schema(self):
        """Test Tool with input schema."""
        schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to echo"}
            },
            "required": ["message"],
        }

        tool = Tool(
            name="echo_tool", description="Echoes input back", inputSchema=schema
        )

        assert tool.inputSchema == schema
        assert tool.inputSchema["properties"]["message"]["type"] == "string"


class TestMCPPromptTypes:
    """Test MCP prompt type definitions."""

    def test_prompt_creation(self):
        """Test Prompt creation."""
        prompt = Prompt(name="greeting_prompt", description="A greeting prompt")

        assert prompt.name == "greeting_prompt"
        assert prompt.description == "A greeting prompt"
        assert prompt.arguments is None

    def test_prompt_with_arguments(self):
        """Test Prompt with arguments."""
        arg = PromptArgument(name="name", description="Name to greet", required=True)

        prompt = Prompt(
            name="greeting_prompt", description="A greeting prompt", arguments=[arg]
        )

        assert len(prompt.arguments) == 1
        assert prompt.arguments[0].name == "name"
        assert prompt.arguments[0].required is True


class TestMCPCapabilities:
    """Test MCP capability definitions."""

    def test_server_capabilities_creation(self):
        """Test ServerCapabilities creation."""
        capabilities = ServerCapabilities(
            tools={"listChanged": True},
            resources={"subscribe": True, "listChanged": True},
            prompts={"listChanged": True},
        )

        assert capabilities.tools["listChanged"] is True
        assert capabilities.resources["subscribe"] is True
        assert capabilities.prompts["listChanged"] is True

    def test_client_capabilities_creation(self):
        """Test ClientCapabilities creation."""
        capabilities = ClientCapabilities(
            experimental={"feature1": True}, sampling={"enabled": True}
        )

        assert capabilities.experimental["feature1"] is True
        assert capabilities.sampling["enabled"] is True


class TestMCPSerialization:
    """Test MCP message serialization and deserialization."""

    def test_request_serialization(self):
        """Test MCPRequest serialization."""
        request = MCPRequest(id="test-1", method="ping", params={})

        data = request.model_dump()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert data["method"] == "ping"
        assert data["params"] == {}

    def test_response_serialization(self):
        """Test MCPResponse serialization."""
        response = MCPResponse(id="test-1", result={"status": "ok"})

        data = response.model_dump()

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert data["result"] == {"status": "ok"}
        assert "error" not in data or data["error"] is None

    def test_notification_serialization(self):
        """Test MCPNotification serialization."""
        notification = MCPNotification(method="notifications/initialized", params={})

        data = notification.model_dump()

        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "notifications/initialized"
        assert data["params"] == {}
        assert data["id"] is None  # notifications have id=None

    def test_error_response_serialization(self):
        """Test error response serialization."""
        error = MCPError(
            code=-32601, message="Method not found", data={"method": "unknown/method"}
        )

        response = MCPResponse(id="error-1", error=error.to_dict())

        data = response.model_dump()

        assert data["error"]["code"] == -32601
        assert data["error"]["message"] == "Method not found"
        assert data["error"]["data"]["method"] == "unknown/method"

    def test_json_serialization(self):
        """Test JSON serialization of MCP messages."""
        request = MCPRequest(
            id="json-test", method="test/method", params={"key": "value"}
        )

        json_str = request.model_dump_json()
        data = json.loads(json_str)

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "json-test"
        assert data["method"] == "test/method"
        assert data["params"]["key"] == "value"

    def test_deserialization_from_dict(self):
        """Test creating MCP objects from dictionaries."""
        data = {"jsonrpc": "2.0", "id": "deser-test", "method": "ping", "params": {}}

        request = MCPRequest(**data)

        assert request.id == "deser-test"
        assert request.method == "ping"
        assert request.params == {}


class TestMCPValidation:
    """Test MCP message validation."""

    def test_invalid_jsonrpc_version(self):
        """Test validation with invalid JSON-RPC version."""
        with pytest.raises(ValueError):
            MCPMessage(jsonrpc="1.0", id="test")

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        with pytest.raises(ValueError):
            MCPRequest(id="test")  # Missing method

    def test_content_type_validation(self):
        """Test content type validation."""
        # Valid text content
        content = TextContent(type="text", text="Hello")
        assert content.type == "text"

        # Invalid type should raise validation error
        with pytest.raises(ValueError):
            TextContent(type="invalid", text="Hello")

    def test_message_type_validation(self):
        """Test message type validation."""
        # Valid message types
        assert MessageType.INITIALIZE == "initialize"
        assert MessageType.PING == "ping"

        # Check all defined message types are valid
        all_types = list(MessageType)
        assert len(all_types) > 0

        for msg_type in all_types:
            assert isinstance(msg_type.value, str)
            assert len(msg_type.value) > 0
