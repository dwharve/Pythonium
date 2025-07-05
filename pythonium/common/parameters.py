"""
Parameter validation framework for Pythonium tools.

This module provides decorators and utilities to standardize parameter
validation across all tools, reducing boilerplate code and improving
consistency.
"""

import functools
from typing import Any, Callable, Dict, List, Type, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from pythonium.common.base import Result
from pythonium.common.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ParameterModel(BaseModel):
    """Base class for tool parameter models with common functionality."""

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown parameters
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_unset=True)

    @classmethod
    def get_parameter_names(cls) -> List[str]:
        """Get list of parameter names."""
        return list(cls.model_fields.keys())


def validate_parameters(parameter_model: Type[ParameterModel]):
    """
    Decorator to validate tool parameters using a Pydantic model.

    Args:
        parameter_model: Pydantic model class defining parameter schema

    Example:
        @validate_parameters(HttpRequestParams)
        async def execute(self, params: HttpRequestParams, context: ToolContext):
            url = params.url
            method = params.method
            # ... rest of implementation
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, parameters: Dict[str, Any], context, *args, **kwargs):
            try:
                # Validate parameters using the model
                validated_params = parameter_model(**parameters)

                # Call the original function with validated parameters
                return await func(self, validated_params, context, *args, **kwargs)

            except ValidationError as e:
                error_msg = f"Parameter validation failed: {e}"
                logger.warning(f"Tool {self.__class__.__name__}: {error_msg}")
                return Result.error_result(error=error_msg)
            except Exception as e:
                error_msg = f"Unexpected validation error: {e}"
                logger.error(f"Tool {self.__class__.__name__}: {error_msg}")
                return Result.error_result(error=error_msg)

        return wrapper

    return decorator
