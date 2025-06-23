"""
Issue tracking and management formatters.

This module handles formatting of issue-related operations including marking,
tracking, detailed info, and suppression.
"""

from typing import Dict, List, Any

from .data_models import (
    ResponseData, ResponseType, WorkflowStage, WorkflowContext, ActionSuggestion
)
from .base_formatter import BaseResponseFormatter


class IssueFormatter(BaseResponseFormatter):
    """Formatter for issue tracking and management operations."""
    
    def format_issue_marked(
        self,
        issue_hash: str,
        classification: str,
        status: str,
        notes: str = None
    ) -> ResponseData:
        """Format issue marking results with workflow guidance."""
        
        stage = WorkflowStage.CLASSIFICATION
        next_stage = None
        suggestions = []
        
        if classification == "true_positive":
            if status == "pending":
                next_stage = WorkflowStage.RESOLUTION
                suggestions.extend([
                    ActionSuggestion(
                        action="start_resolution",
                        description="Begin working on this issue",
                        tool_call="update_issue",
                        parameters={"issue_hash": issue_hash, "status": "work_in_progress"},
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="investigate_further",
                        description="Gather more context about this issue",
                        tool_call="get_next_issue",
                        parameters={"issue_hash": issue_hash},
                        priority="medium"
                    )
                ])
            elif status == "work_in_progress":
                stage = WorkflowStage.RESOLUTION
                next_stage = WorkflowStage.VERIFICATION
                suggestions.append(ActionSuggestion(
                    action="add_progress_notes",
                    description="Document progress and findings",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="medium"
                ))
            elif status == "completed":
                stage = WorkflowStage.COMPLETION
                suggestions.append(ActionSuggestion(
                    action="verify_fix",
                    description="Re-analyze code to confirm the issue is resolved",
                    tool_call="analyze_code",
                    priority="high"
                ))
        
        elif classification == "false_positive":
            suggestions.append(ActionSuggestion(
                action="update_issue",
                description="Suppress this false positive to clean up future analyses",
                tool_call="update_issue",
                parameters={"issue_hash": issue_hash, "suppress": True},
                priority="medium"
            ))
        
        # Add general suggestions
        suggestions.extend([
            ActionSuggestion(
                action="view_all_issues",
                description="See all tracked issues for this project",
                tool_call="list_issues",
                priority="low"
            ),
            ActionSuggestion(
                action="get_issue_details",
                description="View detailed information about this issue",
                tool_call="get_issue",
                parameters={"issue_hash": issue_hash},
                priority="low"
            )
        ])
        
        message = f"Issue {issue_hash} marked as {classification}"
        if status:
            message += f" with status: {status}"
        if notes:
            message += f"\nNotes: {notes}"
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            data={
                "issue_hash": issue_hash,
                "classification": classification,
                "status": status,
                "notes": notes
            },
            workflow_context=WorkflowContext(
                current_stage=stage,
                next_stage=next_stage,
                progress_percentage=60 if stage == WorkflowStage.CLASSIFICATION else 80
            ),
            suggestions=suggestions,
            metadata={
                "issue_hash": issue_hash,
                "action": "marked"
            }
        )
    
    def format_tracked_issues(
        self,
        issues: List[Dict[str, Any]],
        filters: Dict[str, Any] = None
    ) -> ResponseData:
        """Format tracked issues list with workflow guidance."""
        
        if not issues:
            return ResponseData(
                type=ResponseType.INFO,
                message="No tracked issues found",
                data=[],
                workflow_context=WorkflowContext(
                    current_stage=WorkflowStage.COMPLETION,
                    progress_percentage=100
                ),
                suggestions=[
                    ActionSuggestion(
                        action="analyze_code",
                        description="Run code analysis to discover issues",
                        tool_call="analyze_code",
                        priority="medium"
                    )
                ],
                metadata={"total_issues": 0}
            )
        
        # Analyze issue distribution
        by_status = {}
        by_classification = {}
        
        for issue in issues:
            status = issue.get("status", "pending")
            classification = issue.get("classification", "unclassified")
            
            by_status[status] = by_status.get(status, 0) + 1
            by_classification[classification] = by_classification.get(classification, 0) + 1
        
        # Generate workflow suggestions
        suggestions = []
        
        if by_classification.get("unclassified", 0) > 0:
            suggestions.append(ActionSuggestion(
                action="classify_unclassified",
                description=f"Classify {by_classification['unclassified']} unclassified issues",
                tool_call="update_issue",
                priority="high"
            ))
        
        if by_status.get("pending", 0) > 0:
            suggestions.append(ActionSuggestion(
                action="start_pending_work",
                description=f"Begin work on {by_status['pending']} pending issues",
                tool_call="update_issue",
                priority="medium"
            ))
        
        if by_status.get("work_in_progress", 0) > 0:
            suggestions.append(ActionSuggestion(
                action="continue_in_progress",
                description=f"Continue work on {by_status['work_in_progress']} issues in progress",
                tool_call="update_issue",
                priority="high"
            ))
        
        # General suggestions
        suggestions.extend([
            ActionSuggestion(
                action="get_statistics",
                description="View detailed project statistics",
                tool_call="list_issues",
                priority="low"
            ),
            ActionSuggestion(
                action="investigate_specific",
                description="Investigate a specific issue for more context",
                tool_call="get_next_issue",
                priority="medium"
            )
        ])
        
        # Determine current stage
        stage = WorkflowStage.CLASSIFICATION
        if by_classification.get("unclassified", 0) == 0:
            if by_status.get("completed", 0) == len(issues):
                stage = WorkflowStage.COMPLETION
            elif by_status.get("work_in_progress", 0) > 0:
                stage = WorkflowStage.RESOLUTION
        
        message_parts = [f"Found {len(issues)} tracked issues"]
        
        if filters:
            filter_desc = []
            if filters.get("classification"):
                filter_desc.append(f"classification: {filters['classification']}")
            if filters.get("status"):
                filter_desc.append(f"status: {filters['status']}")
            if filter_desc:
                message_parts.append(f"Filtered by {', '.join(filter_desc)}")
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message="\n".join(message_parts),
            data=issues,
            workflow_context=WorkflowContext(
                current_stage=stage,
                progress_percentage=min(90, 20 + (by_status.get("completed", 0) / len(issues)) * 70)
            ),
            suggestions=suggestions,
            metadata={
                "total_issues": len(issues),
                "by_status": by_status,
                "by_classification": by_classification,
                "filters_applied": filters or {}
            }
        )
    
    def format_issue_info(
        self,
        tracked_issue: Dict[str, Any],
        issue_hash: str
    ) -> ResponseData:
        """Format detailed issue information with workflow guidance."""
        
        original = tracked_issue.get("original_issue")
        classification = tracked_issue.get("classification", "unclassified")
        status = tracked_issue.get("status", "pending")
        
        # Generate workflow suggestions based on current state
        suggestions = []
        
        if classification == "unclassified":
            suggestions.extend([
                ActionSuggestion(
                    action="classify_true_positive",
                    description="Mark as true positive if this is a real issue",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash, "classification": "true_positive"},
                    priority="high"
                ),
                ActionSuggestion(
                    action="classify_false_positive", 
                    description="Mark as false positive if this is not a real issue",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash, "classification": "false_positive"},
                    priority="high"
                ),
                ActionSuggestion(
                    action="investigate_more",
                    description="Investigate further to understand the issue context",
                    tool_call="get_next_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="medium"
                )
            ])
        elif classification == "true_positive" and status == "pending":
            suggestions.extend([
                ActionSuggestion(
                    action="start_work",
                    description="Begin working on this issue",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash, "status": "work_in_progress"},
                    priority="high"
                ),
                ActionSuggestion(
                    action="assign_issue",
                    description="Assign this issue to someone",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="medium"
                )
            ])
        elif status == "work_in_progress":
            suggestions.extend([
                ActionSuggestion(
                    action="add_progress_note",
                    description="Add a note about current progress",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash, "agent_action": "investigated"},
                    priority="medium"
                ),
                ActionSuggestion(
                    action="mark_completed",
                    description="Mark as completed if work is done",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash, "status": "completed"},
                    priority="high"
                )
            ])
        
        # Add general suggestions
        suggestions.extend([
            ActionSuggestion(
                action="update_issue",
                description="Suppress this issue if it shouldn't appear in future analyses",
                tool_call="update_issue",
                parameters={"issue_hash": issue_hash},
                priority="low"
            ),
            ActionSuggestion(
                action="view_agent_history",
                description="View history of agent actions on this issue",
                tool_call="list_issues",
                parameters={"issue_hash": issue_hash},
                priority="low"
            )
        ])
        
        # Determine current stage
        stage_map = {
            ("unclassified", "pending"): WorkflowStage.CLASSIFICATION,
            ("true_positive", "pending"): WorkflowStage.RESOLUTION,
            ("true_positive", "work_in_progress"): WorkflowStage.RESOLUTION,
            ("true_positive", "completed"): WorkflowStage.COMPLETION,
            ("false_positive", "pending"): WorkflowStage.COMPLETION
        }
        
        stage = stage_map.get((classification, status), WorkflowStage.INVESTIGATION)
        
        detector_id = original.get("detector_id", "unknown") if original else "unknown"
        message = f"Issue Details: {issue_hash} ({detector_id})"
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            data=tracked_issue,
            workflow_context=WorkflowContext(
                current_stage=stage,
                progress_percentage=50 if classification == "unclassified" else 80 if status != "completed" else 100
            ),
            suggestions=suggestions,
            metadata={
                "issue_hash": issue_hash,
                "classification": classification,
                "status": status,
                "detector": detector_id
            }
        )
    
    def format_issue_suppressed(
        self,
        issue_hash: str,
        suppressed: bool
    ) -> ResponseData:
        """Format issue suppression response with workflow guidance."""
        
        action = "suppressed" if suppressed else "unsuppressed"
        message = f"🔇 Issue {issue_hash} {action}"
        
        suggestions = []
        
        if suppressed:
            suggestions.extend([
                ActionSuggestion(
                    action="verify_suppression",
                    description="Run analysis to verify issue no longer appears",
                    tool_call="analyze_code",
                    priority="medium"
                ),
                ActionSuggestion(
                    action="document_reason",
                    description="Add a note explaining why this issue was suppressed",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash, "agent_action": "suppressed"},
                    priority="low"
                )
            ])
        else:
            suggestions.extend([
                ActionSuggestion(
                    action="reclassify_issue",
                    description="Reclassify this issue now that it's active again",
                    tool_call="update_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="high"
                ),
                ActionSuggestion(
                    action="investigate_again",
                    description="Investigate why this issue needs to be unsuppressed",
                    tool_call="get_next_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="medium"
                )
            ])
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            workflow_context=WorkflowContext(
                current_stage=WorkflowStage.CLASSIFICATION if not suppressed else WorkflowStage.COMPLETION,
                progress_percentage=100 if suppressed else 30
            ),
            suggestions=suggestions,
            metadata={
                "issue_hash": issue_hash,
                "action": action,
                "suppressed": suppressed
            }
        )
