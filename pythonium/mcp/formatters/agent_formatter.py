"""
Agent actions and investigation formatters.

This module handles formatting of agent-related operations including note addition,
action history, and investigation completion.
"""

from typing import Dict, List, Any

from .data_models import (
    ResponseData, ResponseType, WorkflowStage, WorkflowContext, ActionSuggestion
)
from .base_formatter import BaseResponseFormatter


class AgentFormatter(BaseResponseFormatter):
    """Formatter for agent actions and investigations."""
    
    def format_agent_note_added(
        self,
        issue_hash: str,
        agent_action: str,
        investigation_details: str = None,
        resolution_details: str = None
    ) -> ResponseData:
        """Format agent note addition with workflow guidance."""
        
        stage_map = {
            "investigated": WorkflowStage.INVESTIGATION,
            "classified": WorkflowStage.CLASSIFICATION,
            "fixed": WorkflowStage.RESOLUTION,
            "verified": WorkflowStage.VERIFICATION,
            "completed": WorkflowStage.COMPLETION
        }
        
        stage = stage_map.get(agent_action, WorkflowStage.INVESTIGATION)
        
        suggestions = []
        
        if agent_action == "investigated":
            suggestions.extend([
                ActionSuggestion(
                    action="classify_issue",
                    description="Classify this issue based on investigation findings",
                    tool_call="mark_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="high"
                ),
                ActionSuggestion(
                    action="investigate_further",
                    description="Continue investigation if more context is needed",
                    tool_call="investigate_issue",
                    parameters={"issue_hash": issue_hash},
                    priority="medium"
                )
            ])
        elif agent_action == "fixed":
            suggestions.extend([
                ActionSuggestion(
                    action="verify_fix",
                    description="Run analysis to verify the fix resolved the issue",
                    tool_call="analyze_code",
                    priority="high"
                ),
                ActionSuggestion(
                    action="mark_completed",
                    description="Mark issue as completed if fix is verified",
                    tool_call="mark_issue",
                    parameters={"issue_hash": issue_hash, "status": "completed"},
                    priority="medium"
                )
            ])
        
        message = f"📝 Added agent note to issue {issue_hash}: {agent_action}"
        if investigation_details:
            message += f"\n🔍 Investigation: {investigation_details[:100]}..."
        if resolution_details:
            message += f"\n🔧 Resolution: {resolution_details[:100]}..."
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            data={
                "issue_hash": issue_hash,
                "agent_action": agent_action,
                "investigation_details": investigation_details,
                "resolution_details": resolution_details
            },
            workflow_context=WorkflowContext(
                current_stage=stage,
                progress_percentage=min(90, 30 + (list(stage_map.values()).index(stage) * 15))
            ),
            suggestions=suggestions,
            metadata={
                "issue_hash": issue_hash,
                "action": "note_added"
            }
        )
    
    def format_agent_actions(
        self,
        actions: List[Dict[str, Any]],
        issue_hash: str
    ) -> ResponseData:
        """Format agent action history with workflow guidance."""
        
        if not actions:
            return ResponseData(
                type=ResponseType.INFO,
                message=f"📝 No agent actions recorded for issue {issue_hash}",
                data=[],
                workflow_context=WorkflowContext(
                    current_stage=WorkflowStage.INVESTIGATION
                ),
                suggestions=[
                    ActionSuggestion(
                        action="start_investigation",
                        description="Begin investigating this issue",
                        tool_call="investigate_issue",
                        parameters={"issue_hash": issue_hash},
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="add_manual_note",
                        description="Manually add a note about this issue",
                        tool_call="add_agent_note",
                        parameters={"issue_hash": issue_hash},
                        priority="medium"
                    )
                ],
                metadata={"issue_hash": issue_hash, "action_count": 0}
            )
        
        # Analyze action history to determine current state
        latest_action = actions[-1] if actions else {}
        action_types = [a.get("action", "") for a in actions]
        
        suggestions = []
        
        # Generate suggestions based on action history
        if "investigated" in action_types and "classified" not in action_types:
            suggestions.append(ActionSuggestion(
                action="classify_issue",
                description="Classify this issue based on investigation findings",
                tool_call="mark_issue",
                parameters={"issue_hash": issue_hash},
                priority="high"
            ))
        
        if "fixed" in action_types and "verified" not in action_types:
            suggestions.append(ActionSuggestion(
                action="verify_fix",
                description="Verify that the fix resolved the issue",
                tool_call="analyze_code",
                priority="high"
            ))
        
        suggestions.extend([
            ActionSuggestion(
                action="continue_work",
                description="Add another note to continue documenting work",
                tool_call="add_agent_note",
                parameters={"issue_hash": issue_hash},
                priority="medium"
            ),
            ActionSuggestion(
                action="investigate_further", 
                description="Run automatic investigation for more context",
                tool_call="investigate_issue",
                parameters={"issue_hash": issue_hash},
                priority="low"
            )
        ])
        
        # Determine stage from latest action
        stage_map = {
            "investigated": WorkflowStage.INVESTIGATION,
            "classified": WorkflowStage.CLASSIFICATION, 
            "fixed": WorkflowStage.VERIFICATION,
            "verified": WorkflowStage.COMPLETION,
            "completed": WorkflowStage.COMPLETION
        }
        
        latest_action_type = latest_action.get("action", "")
        stage = stage_map.get(latest_action_type, WorkflowStage.INVESTIGATION)
        
        message = f"📋 Agent action history for {issue_hash}: {len(actions)} actions recorded"
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            data=actions,
            workflow_context=WorkflowContext(
                current_stage=stage,
                progress_percentage=min(90, 20 + len(actions) * 15)
            ),
            suggestions=suggestions,
            metadata={
                "issue_hash": issue_hash,
                "action_count": len(actions),
                "latest_action": latest_action_type
            }
        )
    
    def format_investigation_complete(
        self,
        issue_hash: str,
        investigation_details: str,
        findings: str
    ) -> ResponseData:
        """Format investigation completion with workflow guidance."""
        
        suggestions = [
            ActionSuggestion(
                action="classify_based_on_findings",
                description="Classify this issue based on investigation findings",
                tool_call="mark_issue",
                parameters={"issue_hash": issue_hash},
                priority="high"
            ),
            ActionSuggestion(
                action="start_resolution",
                description="Begin working on resolving this issue",
                tool_call="mark_issue",
                parameters={"issue_hash": issue_hash, "status": "work_in_progress"},
                priority="medium"
            ),
            ActionSuggestion(
                action="get_full_details",
                description="View complete issue details with investigation notes",
                tool_call="get_issue_info",
                parameters={"issue_hash": issue_hash},
                priority="low"
            )
        ]
        
        message = f"🔍 Investigation completed for issue {issue_hash}"
        
        return ResponseData(
            type=ResponseType.SUCCESS,
            message=message,
            data={
                "issue_hash": issue_hash,
                "investigation_details": investigation_details,
                "findings": findings
            },
            workflow_context=WorkflowContext(
                current_stage=WorkflowStage.CLASSIFICATION,
                next_stage=WorkflowStage.RESOLUTION,
                progress_percentage=60
            ),
            suggestions=suggestions,
            metadata={
                "issue_hash": issue_hash,
                "action": "investigation_completed"
            }
        )
