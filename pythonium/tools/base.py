"""
Base tool framework for Pythonium MCP server.

This module provides the abstract base classes and common interfaces
for all tools in the Pythonium system.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from pythonium.common.base import BaseComponent, Result
from pythonium.common.exceptions import PythoniumError


class ToolError(PythoniumError):
    """Base exception for tool-related errors."""

    pass


class ToolValidationError(ToolError):
    """Raised when tool parameter validation fails."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    pass


class ParameterType(Enum):
    """Tool parameter types."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    PATH = "string"
    URL = "string"
    EMAIL = "string"


class ToolParameter(BaseModel):
    """Defines a tool parameter for schema generation."""

    name: str = Field(description="Parameter name")
    type: ParameterType = Field(description="Parameter type")
    description: str = Field(description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value")

    # Schema constraints for JSON Schema generation
    min_value: Optional[Union[int, float]] = Field(
        default=None, description="Minimum value for numbers"
    )
    max_value: Optional[Union[int, float]] = Field(
        default=None, description="Maximum value for numbers"
    )
    min_length: Optional[int] = Field(
        default=None, description="Minimum length for strings/arrays"
    )
    max_length: Optional[int] = Field(
        default=None, description="Maximum length for strings/arrays"
    )
    pattern: Optional[str] = Field(
        default=None, description="Regex pattern for string validation"
    )
    allowed_values: Optional[List[Any]] = Field(
        default=None, description="List of allowed values"
    )


class ToolMetadata(BaseModel):
    """Metadata for a tool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    brief_description: Optional[str] = Field(
        default=None, description="Brief description for LLM prompts"
    )
    version: str = Field(default="1.0.0", description="Tool version")
    author: Optional[str] = Field(default=None, description="Tool author")
    category: str = Field(description="Tool category")
    tags: List[str] = Field(default_factory=list, description="Tool tags")
    parameters: List[ToolParameter] = Field(
        default_factory=list, description="Tool parameters"
    )

    # Execution constraints
    max_execution_time: Optional[float] = Field(
        default=None, description="Max execution time in seconds"
    )
    requires_auth: bool = Field(
        default=False, description="Whether tool requires authentication"
    )
    dangerous: bool = Field(
        default=False, description="Whether tool performs dangerous operations"
    )

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v):
        """Validate parameter names are unique."""
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("Parameter names must be unique")
        return v

    def get_brief_description(self) -> str:
        """Get brief description for LLM prompts."""
        return self.brief_description or self.description

    def get_description(self, brief: bool = False) -> str:
        """Get description based on preference for brief or detailed."""
        if brief:
            return self.get_brief_description()
        return self.get_description()


@dataclass
class ToolContext:
    """Execution context for tools."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    workspace_path: Optional[Path] = None
    environment: Dict[str, str] = field(default_factory=dict)
    permissions: Dict[str, bool] = field(default_factory=dict)
    logger: Optional[logging.Logger] = None
    progress_callback: Optional[Callable[[str], None]] = None
    registry: Optional[Any] = None

    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission."""
        return self.permissions.get(permission, False)

    def get_logger(self) -> logging.Logger:
        """Get context logger or create default."""
        if self.logger is None:
            self.logger = logging.getLogger(f"pythonium.tools.context.{id(self)}")
        return self.logger


class BaseTool(BaseComponent, ABC):
    """Abstract base class for all tools."""

    def __init__(self, name: Optional[str] = None):
        """Initialize tool."""
        super().__init__(name or self.__class__.__name__)
        self._metadata = None
        self._logger = logging.getLogger(f"pythonium.tools.{self.name}")

    async def initialize(self) -> None:
        """Initialize the tool (default implementation does nothing)."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool (default implementation does nothing)."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        pass

    @abstractmethod
    async def execute(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute the tool with given parameters and context."""
        pass

    async def run(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Run the tool with parameter validation and error handling."""
        start_time = datetime.now()

        try:
            validated_params = parameters

            # Check permissions if required
            if self.metadata.requires_auth and not context.has_permission(
                "tool_execution"
            ):
                raise ToolExecutionError(
                    "Tool requires authentication but context lacks permission"
                )

            # Execute tool
            result = await self.execute(validated_params, context)

            # Set execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            if result:
                result.execution_time = execution_time

            return result

        except ToolValidationError as e:
            return Result.error_result(
                error=f"Parameter validation failed: {e}",
                execution_time=(datetime.now() - start_time).total_seconds(),
            )
        except ToolExecutionError as e:
            return Result.error_result(
                error=f"Execution failed: {e}",
                execution_time=(datetime.now() - start_time).total_seconds(),
            )
        except Exception as e:
            self._logger.exception(f"Unexpected error in tool {self.name}")
            return Result.error_result(
                error=f"Unexpected error: {e}",
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

    def _add_numeric_constraints(
        self, prop: Dict[str, Any], param: ToolParameter
    ) -> None:
        """Add numeric constraints to schema property."""
        if param.min_value is not None:
            prop["minimum"] = param.min_value
        if param.max_value is not None:
            prop["maximum"] = param.max_value

    def _add_string_constraints(
        self, prop: Dict[str, Any], param: ToolParameter
    ) -> None:
        """Add string constraints to schema property."""
        if param.min_length is not None:
            prop["minLength"] = param.min_length
        if param.max_length is not None:
            prop["maxLength"] = param.max_length
        if param.pattern is not None:
            prop["pattern"] = param.pattern

        # Add format hints for special string types
        if param.type == ParameterType.URL:
            prop["format"] = "uri"
        elif param.type == ParameterType.EMAIL:
            prop["format"] = "email"
        elif param.type == ParameterType.PATH:
            prop["format"] = "path"

    def _add_array_constraints(
        self, prop: Dict[str, Any], param: ToolParameter
    ) -> None:
        """Add array constraints to schema property."""
        if param.min_length is not None:
            prop["minItems"] = param.min_length
        if param.max_length is not None:
            prop["maxItems"] = param.max_length

    def _build_parameter_property(self, param: ToolParameter) -> Dict[str, Any]:
        """Build JSON schema property for a single parameter."""
        prop: Dict[str, Any] = {
            "type": param.type.value,
            "description": param.description,
        }

        # Add default value if present
        if param.default is not None:
            prop["default"] = param.default

        # Add validation constraints based on parameter type
        if param.type in (ParameterType.INTEGER, ParameterType.NUMBER):
            self._add_numeric_constraints(prop, param)
        elif param.type in (
            ParameterType.STRING,
            ParameterType.PATH,
            ParameterType.URL,
            ParameterType.EMAIL,
        ):
            self._add_string_constraints(prop, param)
        elif param.type == ParameterType.ARRAY:
            self._add_array_constraints(prop, param)

        # Add enum constraint for allowed values
        if param.allowed_values is not None:
            prop["enum"] = param.allowed_values

        return prop

    def get_schema(self, brief: bool = False) -> Dict[str, Any]:
        """Get JSON schema for the tool."""
        properties: Dict[str, Dict[str, Any]] = {}

        for param in self.metadata.parameters:
            properties[param.name] = self._build_parameter_property(param)

        return {
            "name": self.metadata.name,
            "description": self.metadata.get_description(brief=brief),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [p.name for p in self.metadata.parameters if p.required],
            },
        }
