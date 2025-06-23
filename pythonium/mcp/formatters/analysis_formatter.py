"""
Analysis results formatter.

This module handles formatting of code ana            ActionSuggestion(
                action="classify_issues",
                description="Mark issues as true/false positives for better tracking",
                tool_call="update_issue",
                priority="high"
            ),
            ActionSuggestion(
                action="review_statistics",
                description="View project-wide issue statistics and trends",
                tool_call="list_issues",
                priority="low"
            )s with workflow guidance.
"""

from typing import List
from dataclasses import asdict

from pythonium.models import Issue
from .data_models import (
    ResponseData, ResponseType, WorkflowStage, WorkflowContext, ActionSuggestion
)
from .base_formatter import BaseResponseFormatter


class AnalysisFormatter(BaseResponseFormatter):
    """Formatter for code analysis results."""
    
    def format_analysis_results(
        self,
        issues: List[Issue],
        project_path: str,
        tracked_count: int = 0,
        suppressed_count: int = 0,
        new_count: int = 0
    ) -> ResponseData:
        """Format code analysis results with workflow guidance."""
        
        if not issues:
            return ResponseData(
                type=ResponseType.SUCCESS,
                message=f"No code health issues found in {project_path}",
                data=[],
                workflow_context=WorkflowContext(
                    current_stage=WorkflowStage.COMPLETION,
                    progress_percentage=100
                ),
                suggestions=[
                    ActionSuggestion(
                        action="maintain_quality",
                        description="Continue regular code analysis to maintain quality",
                        priority="low"
                    )
                ],
                metadata={
                    "project_path": project_path,
                    "total_issues": 0,
                    "analysis_clean": True
                }
            )
        
        # Determine workflow stage based on issue state
        stage = WorkflowStage.DISCOVERY
        suggestions = []
        
        if new_count > 0:
            stage = WorkflowStage.INVESTIGATION
            suggestions.append(ActionSuggestion(
                action="investigate_new_issues",
                description=f"Investigate {new_count} newly discovered issues",
                tool_call="get_next_issue",
                priority="high"
            ))
        
        if tracked_count > 0:
            suggestions.append(ActionSuggestion(
                action="review_tracked_issues",
                description=f"Review {tracked_count} issues already being tracked",
                tool_call="list_issues",
                priority="medium"
            ))
        
        # Add general suggestions
        suggestions.extend([
            ActionSuggestion(
                action="classify_issues",
                description="Mark issues as true/false positives for better tracking",
                tool_call="update_issue",
                priority="high"
            ),
            ActionSuggestion(
                action="get_statistics",
                description="View project-wide issue statistics and trends",
                tool_call="list_issues",
                priority="low"
            )
        ])
        
        message_parts = [
            f"Found {len(issues)} code health issues in {project_path}"
        ]
        
        if new_count > 0:
            message_parts.append(f"• {new_count} new issues discovered")
        if tracked_count > 0:
            message_parts.append(f"• {tracked_count} issues already tracked")
        if suppressed_count > 0:
            message_parts.append(f"• {suppressed_count} issues suppressed")
        
        return ResponseData(
            type=ResponseType.SUCCESS if len(issues) < 10 else ResponseType.WARNING,
            message="\n".join(message_parts),
            data=[asdict(issue) for issue in issues],
            workflow_context=WorkflowContext(
                current_stage=stage,
                next_stage=WorkflowStage.CLASSIFICATION if stage == WorkflowStage.INVESTIGATION else None,
                progress_percentage=20 if stage == WorkflowStage.DISCOVERY else 40
            ),
            suggestions=suggestions,
            metadata={
                "project_path": project_path,
                "total_issues": len(issues),
                "new_issues": new_count,
                "tracked_issues": tracked_count,
                "suppressed_issues": suppressed_count
            }
        )
