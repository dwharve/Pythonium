"""
Issue tracking MCP tool handlers for Pythonium.
"""

from pathlib import Path
from typing import Any, Dict, List

import mcp.types as types

from ..utils.debug import profiler, profile_operation, info_log
from ..formatters import ActionSuggestion
from .base import BaseHandler


class IssueTrackingHandlers(BaseHandler):
    """Handlers for issue tracking operations."""
    
    @profile_operation("update_issue")
    async def update_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Update an issue with new information."""
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        severity = arguments.get("severity")
        message = arguments.get("message")
        classification = arguments.get("classification")
        status = arguments.get("status")
        note = arguments.get("note")
        
        # Validate classification if provided
        if classification and classification not in ["unclassified", "true_positive", "false_positive"]:
            raise ValueError(f"Invalid classification '{classification}'. Valid values: unclassified, true_positive, false_positive")
        
        # Validate status if provided
        if status and status not in ["pending", "work_in_progress", "completed"]:
            raise ValueError(f"Invalid status '{status}'. Valid values: pending, work_in_progress, completed")
        
        # Validate severity if provided
        if severity and severity not in ["info", "warn", "error"]:
            raise ValueError(f"Invalid severity '{severity}'. Valid values: info, warn, error")
        
        try:
            # Update the issue
            success = await self.services.issues.update_issue(
                issue_hash=issue_hash,
                severity=severity,
                message=message,
                classification=classification,
                status=status,
                note=note
            )
            
            if success:
                # Get updated issue for response
                updated_issue = await self.services.issues.get_issue(issue_hash)
                
                response_data = self.response_formatter.format_success(
                    message=f"Issue {issue_hash} updated successfully",
                    data={
                        "issue_hash": issue_hash,
                        "updated_fields": {
                            k: v for k, v in {
                                "severity": severity,
                                "message": message,
                                "classification": classification,
                                "status": status,
                                "note_added": note is not None
                            }.items() if v is not None
                        },
                        "current_state": {
                            "severity": updated_issue.severity,
                            "classification": updated_issue.classification,
                            "status": updated_issue.status,
                            "notes_count": len(updated_issue.notes)
                        }
                    }
                )
                return [self.response_formatter.to_text_content(response_data)]
            else:
                response_data = self.response_formatter.format_error(
                    error_message=f"Failed to update issue {issue_hash}",
                    error_type="operation_failed",
                    recovery_suggestions=[
                        ActionSuggestion(
                            action="get_issue",
                            description="Check if the issue still exists and get current details",
                            tool_call="get_issue",
                            parameters={"issue_hash": issue_hash},
                            priority="high"
                        ),
                        ActionSuggestion(
                            action="list_issues",
                            description="Verify the issue hash is correct",
                            tool_call="list_issues",
                            priority="medium"
                        )
                    ]
                )
                return [self.response_formatter.to_text_content(response_data)]
                
        except ValueError as e:
            response_data = self.response_formatter.format_error(
                error_message=str(e),
                error_type="issue_not_found",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="list_issues",
                        description="View all available issues to find the correct hash",
                        tool_call="list_issues",
                        priority="high"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("list_issues")
    async def list_issues(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """List issues with optional filtering."""
        project_path_str = arguments.get("project_path")
        classification = arguments.get("classification")
        status = arguments.get("status")
        
        # Validate classification if provided
        if classification and classification not in ["unclassified", "true_positive", "false_positive"]:
            raise ValueError(f"Invalid classification '{classification}'. Valid values: unclassified, true_positive, false_positive")
        
        # Validate status if provided
        if status and status not in ["pending", "work_in_progress", "completed"]:
            raise ValueError(f"Invalid status '{status}'. Valid values: pending, work_in_progress, completed")
        
        project_path = Path(project_path_str).resolve() if project_path_str else None
        
        try:
            # Get issues from service
            issues = await self.services.issues.list_issues(
                project_path=project_path,
                classification=classification,
                status=status
            )
            
            if not issues:
                response_data = self.response_formatter.format_info(
                    message="No issues found matching the specified criteria",
                    data={
                        "filters": {
                            "classification": classification, 
                            "status": status, 
                            "project": str(project_path) if project_path else "all"
                        }
                    },
                    suggestions=[
                        ActionSuggestion(
                            action="analyze_code",
                            description="Run code analysis to find issues",
                            tool_call="analyze_code",
                            priority="high"
                        )
                    ]
                )
                return [self.response_formatter.to_text_content(response_data)]
            
            # Format issues for display
            issues_data = []
            for issue in issues:
                location_str = ""
                if issue.location:
                    file_name = Path(issue.location.file).name
                    location_str = f"{file_name}:{issue.location.line}"
                
                issues_data.append({
                    "hash": issue.issue_hash,
                    "id": issue.id,
                    "severity": issue.severity,
                    "message": issue.message[:100] + "..." if len(issue.message) > 100 else issue.message,
                    "classification": issue.classification,
                    "status": issue.status,
                    "location": location_str,
                    "notes_count": len(issue.notes),
                    "detector": issue.detector_id
                })
            
            response_data = self.response_formatter.format_success(
                message=f"Found {len(issues)} issues",
                data={
                    "count": len(issues),
                    "filters": {
                        "classification": classification,
                        "status": status,
                        "project": str(project_path) if project_path else "all"
                    },
                    "issues": issues_data
                }
            )
            return [self.response_formatter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error listing issues: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("get_issue")
    async def get_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get detailed information about a specific issue."""
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        try:
            issue = await self.services.issues.get_issue(issue_hash)
            
            if not issue:
                response_data = self.response_formatter.format_error(
                    error_message=f"Issue with hash '{issue_hash}' not found",
                    error_type="issue_not_found",
                    recovery_suggestions=[
                        ActionSuggestion(
                            action="list_issues",
                            description="View all available issues",
                            tool_call="list_issues",
                            priority="high"
                        )
                    ]
                )
                return [self.response_formatter.to_text_content(response_data)]
            
            # Format issue details
            location_info = None
            if issue.location:
                location_info = {
                    "file": str(issue.location.file),
                    "line": issue.location.line,
                    "column": issue.location.column,
                    "end_line": issue.location.end_line,
                    "end_column": issue.location.end_column
                }
            
            issue_data = {
                "hash": issue.issue_hash,
                "id": issue.id,
                "severity": issue.severity,
                "message": issue.message,
                "classification": issue.classification,
                "status": issue.status,
                "detector_id": issue.detector_id,
                "location": location_info,
                "related_files": [str(f) for f in issue.related_files],
                "metadata": issue.metadata,
                "notes": issue.notes,
                "first_seen": issue.first_seen.isoformat() if issue.first_seen else None,
                "last_seen": issue.last_seen.isoformat() if issue.last_seen else None
            }
            
            response_data = self.response_formatter.format_success(
                message=f"Issue details for {issue_hash}",
                data=issue_data
            )
            return [self.response_formatter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error retrieving issue: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("get_next_issue")
    async def get_next_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get the next issue that needs attention."""
        project_path_str = arguments.get("project_path")
        project_path = Path(project_path_str).resolve() if project_path_str else None
        
        try:
            # Get unclassified issues first, then pending issues
            unclassified_issues = await self.services.issues.list_issues(
                project_path=project_path,
                classification="unclassified"
            )
            
            if unclassified_issues:
                next_issue = unclassified_issues[0]
                priority = "classification"
                reason = "This issue needs to be classified as true_positive or false_positive"
            else:
                # Look for pending issues
                pending_issues = await self.services.issues.list_issues(
                    project_path=project_path,
                    status="pending"
                )
                
                if pending_issues:
                    next_issue = pending_issues[0]
                    priority = "work"
                    reason = "This issue is ready to be worked on"
                else:
                    # No issues need immediate attention
                    response_data = self.response_formatter.format_info(
                        message="No issues requiring immediate attention",
                        data={"message": "All issues are either classified as false positives or are in progress/completed"}
                    )
                    return [self.response_formatter.to_text_content(response_data)]
            
            # Format the next issue
            location_str = ""
            if next_issue.location:
                file_name = Path(next_issue.location.file).name
                location_str = f"{file_name}:{next_issue.location.line}"
            
            response_data = self.response_formatter.format_success(
                message=f"Next issue to work on ({priority} needed)",
                data={
                    "hash": next_issue.issue_hash,
                    "id": next_issue.id,
                    "severity": next_issue.severity,
                    "message": next_issue.message,
                    "classification": next_issue.classification,
                    "status": next_issue.status,
                    "location": location_str,
                    "priority": priority,
                    "reason": reason,
                    "suggested_action": "update_issue" if priority == "classification" else "update_issue"
                },
                suggestions=[
                    ActionSuggestion(
                        action="update_issue",
                        description=f"Update this issue - {reason}",
                        tool_call="update_issue",
                        parameters={"issue_hash": next_issue.issue_hash},
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="get_issue",
                        description="Get full details about this issue",
                        tool_call="get_issue",
                        parameters={"issue_hash": next_issue.issue_hash},
                        priority="medium"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error finding next issue: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("get_statistics")
    async def get_statistics(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get statistics about tracked issues."""
        project_path_str = arguments.get("project_path")
        project_path = Path(project_path_str).resolve() if project_path_str else None
        
        try:
            stats = await self.services.issues.get_statistics(project_path=project_path)
            
            response_data = self.response_formatter.format_success(
                message=f"Issue tracking statistics",
                data={
                    "total_tracked": stats.get("total_tracked", 0),
                    "by_classification": stats.get("by_classification", {}),
                    "by_status": stats.get("by_status", {}),
                    "by_severity": stats.get("by_severity", {}),
                    "project": str(project_path) if project_path else "all projects"
                }
            )
            return [self.response_formatter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error getting statistics: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter.to_text_content(response_data)]
