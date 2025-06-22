"""
Response formatter for Pythonium MCP tools.

This module provides structured, actionable response formatting to guide agents
through effective issue resolution workflows.

BACKWARD COMPATIBILITY MODULE:
This module now imports from the modular formatters package to maintain 
backward compatibility while providing a cleaner internal structure.
"""

# Import everything from the new modular structure
from .formatters import (
    ResponseFormatter,
    ResponseType,
    WorkflowStage,
    ActionSuggestion,
    WorkflowContext,
    ResponseData,
)

# Maintain backward compatibility by re-exporting everything
__all__ = [
    'ResponseFormatter',
    'ResponseType',
    'WorkflowStage',
    'ActionSuggestion', 
    'WorkflowContext',
    'ResponseData',
]

# The old monolithic ResponseFormatter class has been replaced by imports
# from the modular structure. All existing code should continue to work.