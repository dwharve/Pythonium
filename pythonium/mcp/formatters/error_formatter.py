"""
Error handling and recovery formatters.

This module handles formatting of error responses with recovery guidance.
"""

from typing import List

from .data_models import (
    ResponseData, ResponseType, WorkflowStage, WorkflowContext, ActionSuggestion
)
from .base_formatter import BaseResponseFormatter


class ErrorFormatter(BaseResponseFormatter):
    """Formatter for error responses and recovery guidance."""
    
    def format_error_response(
        self,
        error_message: str,
        error_type: str = "general",
        recovery_suggestions: List[ActionSuggestion] = None
    ) -> ResponseData:
        """Alias for format_error to ensure backward compatibility."""
        return self.format_error(
            error_message=error_message,
            error_type=error_type,
            recovery_suggestions=recovery_suggestions
        )
        
    def format_error(
        self,
        error_message: str,
        error_type: str = "general",
        recovery_suggestions: List[ActionSuggestion] = None
    ) -> ResponseData:
        """Format error responses with recovery guidance."""
        
        if recovery_suggestions is None:
            recovery_suggestions = []
        
        # Add general recovery suggestions based on error type
        if error_type == "file_not_found":
            recovery_suggestions.extend([
                ActionSuggestion(
                    action="check_path",
                    description="Verify the file path exists and is accessible",
                    priority="high"
                ),
                ActionSuggestion(
                    action="search_files",
                    description="Search for files with similar names",
                    priority="medium"
                )
            ])
        elif error_type == "syntax_error":
            recovery_suggestions.extend([
                ActionSuggestion(
                    action="repair_syntax",
                    description="Use syntax repair tool to fix syntax errors",
                    tool_call="repair_python_syntax",
                    priority="high"
                ),
                ActionSuggestion(
                    action="manual_review",
                    description="Manually review and fix syntax issues",
                    priority="medium"
                )
            ])
        
        return ResponseData(
            type=ResponseType.ERROR,
            message=f"❌ Error: {error_message}",
            workflow_context=WorkflowContext(
                current_stage=WorkflowStage.DISCOVERY,  # Restart workflow
                blockers=[error_message]
            ),
            suggestions=recovery_suggestions,
            metadata={
                "error_type": error_type,
                "has_recovery": len(recovery_suggestions) > 0
            }
        )
