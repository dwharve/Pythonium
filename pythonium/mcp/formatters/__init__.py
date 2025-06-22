"""
Response formatting for Pythonium MCP tools.

This module provides structured, actionable response formatting to guide agents
through effective issue resolution workflows.

This is a modular implementation that maintains backward compatibility with the
original ResponseFormatter interface.
"""

from typing import Any, Dict, List, Optional, Union
import mcp.types as types

from pythonium.models import Issue

# Import all data models and components
from .data_models import (
    ResponseType, WorkflowStage, ActionSuggestion, WorkflowContext, ResponseData
)
from .base_formatter import BaseResponseFormatter
from .analysis_formatter import AnalysisFormatter
from .issue_formatter import IssueFormatter
from .agent_formatter import AgentFormatter
from .statistics_formatter import StatisticsFormatter
from .error_formatter import ErrorFormatter
from .text_converter import TextConverter


class ResponseFormatter(BaseResponseFormatter):
    """Main response formatter that combines all specialized formatters.
    
    This class maintains backward compatibility with the original ResponseFormatter
    while providing a modular internal structure.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize specialized formatters
        self._analysis_formatter = AnalysisFormatter()
        self._issue_formatter = IssueFormatter()
        self._agent_formatter = AgentFormatter()
        self._statistics_formatter = StatisticsFormatter()
        self._error_formatter = ErrorFormatter()
        self._text_converter = TextConverter()
    
    # Analysis methods
    def format_analysis_results(
        self,
        issues: List[Issue],
        project_path: str,
        tracked_count: int = 0,
        suppressed_count: int = 0,
        new_count: int = 0
    ) -> ResponseData:
        """Format code analysis results with workflow guidance."""
        return self._analysis_formatter.format_analysis_results(
            issues, project_path, tracked_count, suppressed_count, new_count
        )
    
    # Issue management methods
    def format_issue_marked(
        self,
        issue_hash: str,
        classification: str,
        status: str,
        notes: str = None
    ) -> ResponseData:
        """Format issue marking results with workflow guidance."""
        return self._issue_formatter.format_issue_marked(
            issue_hash, classification, status, notes
        )
    
    def format_tracked_issues(
        self,
        issues: List[Dict[str, Any]],
        filters: Dict[str, Any] = None
    ) -> ResponseData:
        """Format tracked issues list with workflow guidance."""
        return self._issue_formatter.format_tracked_issues(issues, filters)
    
    def format_issue_info(
        self,
        tracked_issue: Dict[str, Any],
        issue_hash: str
    ) -> ResponseData:
        """Format detailed issue information with workflow guidance."""
        return self._issue_formatter.format_issue_info(tracked_issue, issue_hash)
    
    def format_issue_suppressed(
        self,
        issue_hash: str,
        suppressed: bool
    ) -> ResponseData:
        """Format issue suppression response with workflow guidance."""
        return self._issue_formatter.format_issue_suppressed(issue_hash, suppressed)
    
    # Agent action methods
    def format_agent_note_added(
        self,
        issue_hash: str,
        agent_action: str,
        investigation_details: str = None,
        resolution_details: str = None
    ) -> ResponseData:
        """Format agent note addition with workflow guidance."""
        return self._agent_formatter.format_agent_note_added(
            issue_hash, agent_action, investigation_details, resolution_details
        )
    
    def format_agent_actions(
        self,
        actions: List[Dict[str, Any]],
        issue_hash: str
    ) -> ResponseData:
        """Format agent action history with workflow guidance."""
        return self._agent_formatter.format_agent_actions(actions, issue_hash)
    
    def format_investigation_complete(
        self,
        issue_hash: str,
        investigation_details: str,
        findings: str
    ) -> ResponseData:
        """Format investigation completion with workflow guidance."""
        return self._agent_formatter.format_investigation_complete(
            issue_hash, investigation_details, findings
        )
    
    # Statistics methods
    def format_tracking_statistics(
        self,
        stats: Dict[str, Any],
        project_path: str = None
    ) -> ResponseData:
        """Format tracking statistics with workflow guidance."""
        return self._statistics_formatter.format_tracking_statistics(stats, project_path)
    
    # Error handling methods
    def format_error_response(
        self,
        error_message: str,
        error_type: str = "general",
        recovery_suggestions: List[ActionSuggestion] = None
    ) -> ResponseData:
        """Alias for format_error to ensure backward compatibility."""
        return self._error_formatter.format_error_response(
            error_message, error_type, recovery_suggestions
        )
        
    def format_error(
        self,
        error_message: str,
        error_type: str = "general",
        recovery_suggestions: List[ActionSuggestion] = None
    ) -> ResponseData:
        """Format error responses with recovery guidance."""
        return self._error_formatter.format_error(
            error_message, error_type, recovery_suggestions
        )
    
    # Text conversion method
    def to_text_content(self, response_data: ResponseData) -> types.TextContent:
        """Convert ResponseData to formatted text content.
        
        Returns a proper TextContent object ready for use in handler responses.
        """
        return self._text_converter.to_text_content(response_data)


# Export all public classes and types for backward compatibility
__all__ = [
    'ResponseFormatter',
    'ResponseType',
    'WorkflowStage', 
    'ActionSuggestion',
    'WorkflowContext',
    'ResponseData',
]
