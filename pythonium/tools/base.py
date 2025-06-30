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
from typing import Any, Dict, List, Optional, Union

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
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    PATH = "path"
    URL = "url"
    EMAIL = "email"


class ToolParameter(BaseModel):
    """Defines a tool parameter with validation rules."""

    name: str = Field(description="Parameter name")
    type: ParameterType = Field(description="Parameter type")
    description: str = Field(description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value")

    # Validation constraints
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

    def validate_value(self, value: Any) -> Any:
        """Validate a parameter value against this parameter definition."""
        if value is None:
            if self.required:
                raise ToolValidationError(
                    f"Required parameter '{self.name}' is missing"
                )
            return self.default

        # Type validation
        try:
            validated_value = self._validate_type(value)
        except (ValueError, TypeError) as e:
            raise ToolValidationError(f"Invalid type for parameter '{self.name}': {e}")

        # Constraint validation
        self._validate_constraints(validated_value)

        return validated_value

    def _validate_type(self, value: Any) -> Any:
        """Validate value type."""
        type_validators = {
            ParameterType.STRING: self._validate_string,
            ParameterType.INTEGER: self._validate_integer,
            ParameterType.FLOAT: self._validate_float,
            ParameterType.BOOLEAN: self._validate_boolean,
            ParameterType.ARRAY: self._validate_array,
            ParameterType.OBJECT: self._validate_object,
            ParameterType.PATH: self._validate_path,
            ParameterType.URL: self._validate_url,
            ParameterType.EMAIL: self._validate_email,
        }

        validator = type_validators.get(self.type)
        if validator:
            return validator(value)
        return value

    def _validate_string(self, value: Any) -> str:
        """Validate string type."""
        return str(value)

    def _validate_integer(self, value: Any) -> int:
        """Validate integer type."""
        return int(value)

    def _validate_float(self, value: Any) -> float:
        """Validate float type."""
        return float(value)

    def _validate_boolean(self, value: Any) -> bool:
        """Validate boolean type."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def _validate_array(self, value: Any) -> list:
        """Validate array type."""
        if not isinstance(value, list):
            raise ValueError("Expected list/array")
        return value

    def _validate_object(self, value: Any) -> dict:
        """Validate object type."""
        if not isinstance(value, dict):
            raise ValueError("Expected object/dict")
        return value

    def _validate_path(self, value: Any) -> Path:
        """Validate path type."""
        return Path(str(value))

    def _validate_url(self, value: Any) -> str:
        """Validate URL type."""
        url_str = str(value)
        if not url_str.startswith(("http://", "https://", "ftp://", "file://")):
            raise ValueError("Invalid URL format")
        return url_str

    def _validate_email(self, value: Any) -> str:
        """Validate email type."""
        email_str = str(value)
        if "@" not in email_str or "." not in email_str.split("@")[-1]:
            raise ValueError("Invalid email format")
        return email_str

    def _validate_constraints(self, value: Any) -> None:
        """Validate value constraints."""
        # Number constraints
        if self.type in (ParameterType.INTEGER, ParameterType.FLOAT):
            if self.min_value is not None and value < self.min_value:
                raise ToolValidationError(
                    f"Value {value} below minimum {self.min_value}"
                )
            if self.max_value is not None and value > self.max_value:
                raise ToolValidationError(
                    f"Value {value} above maximum {self.max_value}"
                )

        # Length constraints
        if self.type in (ParameterType.STRING, ParameterType.ARRAY):
            length = len(value)
            if self.min_length is not None and length < self.min_length:
                raise ToolValidationError(
                    f"Length {length} below minimum {self.min_length}"
                )
            if self.max_length is not None and length > self.max_length:
                raise ToolValidationError(
                    f"Length {length} above maximum {self.max_length}"
                )

        # Pattern constraint (for strings)
        if self.type == ParameterType.STRING and self.pattern is not None:
            import re

            if not re.match(self.pattern, value):
                raise ToolValidationError(
                    f"Value does not match pattern: {self.pattern}"
                )

        # Allowed values constraint
        if self.allowed_values is not None and value not in self.allowed_values:
            raise ToolValidationError(f"Value must be one of: {self.allowed_values}")


class ToolMetadata(BaseModel):
    """Metadata for a tool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    brief_description: Optional[str] = Field(
        default=None, description="Brief description for LLM prompts"
    )
    detailed_description: Optional[str] = Field(
        default=None, description="Detailed description for on-demand help"
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

    def get_detailed_description(self) -> str:
        """Get detailed description for on-demand help."""
        return self.detailed_description or self.description

    def get_description(self, brief: bool = False) -> str:
        """Get description based on preference for brief or detailed."""
        if brief:
            return self.get_brief_description()
        return self.get_detailed_description()


@dataclass
class ToolContext:
    """Execution context for tools."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    workspace_path: Optional[Path] = None
    environment: Dict[str, str] = field(default_factory=dict)
    permissions: Dict[str, bool] = field(default_factory=dict)
    logger: Optional[logging.Logger] = None

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

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize tool parameters."""
        validated = {}

        # Check for unknown parameters
        param_names = {p.name for p in self.metadata.parameters}
        unknown = set(parameters.keys()) - param_names
        if unknown:
            raise ToolValidationError(f"Unknown parameters: {unknown}")

        # Validate each parameter
        for param_def in self.metadata.parameters:
            value = parameters.get(param_def.name)
            validated[param_def.name] = param_def.validate_value(value)

        return validated

    async def run(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Run the tool with parameter validation and error handling."""
        start_time = datetime.now()

        try:
            # Check if execute method has @validate_parameters decorator
            has_new_validation = hasattr(self.execute, "__wrapped__")

            if has_new_validation:
                # New validation system - call execute directly
                validated_params = parameters
            else:
                # Old validation system - validate parameters
                validated_params = self.validate_parameters(parameters)

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

    def get_schema(self, brief: bool = False) -> Dict[str, Any]:
        """Get JSON schema for the tool."""
        return {
            "name": self.metadata.name,
            "description": self.metadata.get_description(brief=brief),
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type.value,
                        "description": param.description,
                        **(
                            {"default": param.default}
                            if param.default is not None
                            else {}
                        ),
                    }
                    for param in self.metadata.parameters
                },
                "required": [p.name for p in self.metadata.parameters if p.required],
            },
        }
