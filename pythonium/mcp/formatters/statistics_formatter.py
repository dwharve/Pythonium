"""
Statistics and tracking formatters.

This module handles formatting of tracking statistics and project-wide metrics.
"""

from typing import Dict, Any

from .data_models import (
    ResponseData, ResponseType, WorkflowStage, WorkflowContext, ActionSuggestion
)
from .base_formatter import BaseResponseFormatter


class StatisticsFormatter(BaseResponseFormatter):
    """Formatter for tracking statistics and metrics."""
    
    def format_tracking_statistics(
        self,
        stats: Dict[str, Any],
        project_path: str = None
    ) -> ResponseData:
        """Format tracking statistics with workflow guidance."""
        
        total_tracked = stats.get("total_tracked", 0)
        active = stats.get("active", 0) 
        suppressed = stats.get("suppressed", 0)
        by_classification = stats.get("by_classification", {})
        by_status = stats.get("by_status", {})
        
        suggestions = []
        
        # Generate suggestions based on statistics
        unclassified = by_classification.get("unclassified", 0)
        if unclassified > 0:
            suggestions.append(ActionSuggestion(
                action="classify_unclassified",
                description=f"Classify {unclassified} unclassified issues",
                tool_call="list_tracked_issues",
                parameters={"classification": "unclassified"},
                priority="high"
            ))
        
        pending = by_status.get("pending", 0)
        if pending > 0:
            suggestions.append(ActionSuggestion(
                action="start_pending_work",
                description=f"Begin work on {pending} pending issues",
                tool_call="list_tracked_issues",
                parameters={"status": "pending"},
                priority="medium"
            ))
        
        in_progress = by_status.get("work_in_progress", 0)
        if in_progress > 0:
            suggestions.append(ActionSuggestion(
                action="continue_in_progress",
                description=f"Continue {in_progress} issues in progress",
                tool_call="list_tracked_issues", 
                parameters={"status": "work_in_progress"},
                priority="high"
            ))
        
        if total_tracked == 0:
            suggestions.append(ActionSuggestion(
                action="run_analysis",
                description="Run code analysis to discover issues",
                tool_call="analyze_code",
                priority="medium"
            ))
        
        # General suggestions
        suggestions.extend([
            ActionSuggestion(
                action="view_all_issues",
                description="View all tracked issues",
                tool_call="list_tracked_issues",
                priority="low"
            ),
            ActionSuggestion(
                action="analyze_project",
                description="Run fresh analysis to update statistics",
                tool_call="analyze_code",
                priority="low"
            )
        ])
        
        # Determine current stage based on statistics
        if total_tracked == 0:
            stage = WorkflowStage.DISCOVERY
            progress = 0
        elif unclassified > 0:
            stage = WorkflowStage.CLASSIFICATION
            progress = 20
        elif pending > 0 or in_progress > 0:
            stage = WorkflowStage.RESOLUTION
            progress = 50 + (by_status.get("completed", 0) / max(total_tracked, 1)) * 40
        else:
            stage = WorkflowStage.COMPLETION
            progress = 100
        
        scope = f"for {project_path}" if project_path else "across all projects"
        message = f"Issue tracking statistics {scope}: {total_tracked} total, {active} active"
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            data=stats,
            workflow_context=WorkflowContext(
                current_stage=stage,
                progress_percentage=int(progress)
            ),
            suggestions=suggestions,
            metadata={
                "scope": scope,
                "total_tracked": total_tracked,
                "active": active,
                "suppressed": suppressed
            }
        )
