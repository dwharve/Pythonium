"""
Parameter models for standard tools.

This module provides parameter validation models for tools in the std module.
"""

from typing import Dict, List, Optional

from pydantic import Field, field_validator

from pythonium.common.parameter_validation import ParameterModel


class DescribeToolParams(ParameterModel):
    """Parameter model for DescribeToolTool."""

    tool_name: str = Field(..., description="Name of the tool to describe")
    include_examples: bool = Field(
        True, description="Include usage examples in the description"
    )
    include_schema: bool = Field(True, description="Include parameter schema details")
    include_metadata: bool = Field(
        False, description="Include detailed metadata information"
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()


class ExecuteCommandParams(ParameterModel):
    """Parameter model for ExecuteCommandTool."""

    command: str = Field(..., description="Command to execute")
    args: Optional[List[str]] = Field(None, description="Command arguments")
    working_directory: Optional[str] = Field(
        None, description="Working directory for execution"
    )
    timeout: int = Field(30, description="Execution timeout in seconds")
    capture_output: bool = Field(True, description="Capture command output")
    shell: bool = Field(False, description="Execute command in shell")
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    stdin: Optional[str] = Field(None, description="Input to send to command's stdin")


class SearchToolsParams(ParameterModel):
    """Parameter model for SearchToolsTool."""

    query: str = Field(..., description="Search query for finding tools")
    category: Optional[str] = Field(None, description="Filter by tool category")
    tags: Optional[List[str]] = Field(None, description="Filter by tool tags")
    include_description: bool = Field(
        True, description="Include tool descriptions in results"
    )
    include_parameters: bool = Field(
        False, description="Include parameter information in results"
    )
    limit: Optional[int] = Field(
        None, description="Maximum number of results to return"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: Optional[int]) -> Optional[int]:
        """Validate search limit."""
        if v is not None and v <= 0:
            raise ValueError("Limit must be positive")
        return v
