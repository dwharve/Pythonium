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
                
                response_data = self.response_formatter.format_issue_marked(
                    issue_hash=issue_hash,
                    classification=classification or updated_issue.classification,
                    status=status or updated_issue.status,
                    notes=note or "No note added"
                )
                return [self.response_formatter._text_converter.to_text_content(response_data)]
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
                return [self.response_formatter._text_converter.to_text_content(response_data)]
                
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
            return [self.response_formatter._text_converter.to_text_content(response_data)]
    
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
                response_data = self.response_formatter.format_tracked_issues(
                    issues=[],
                    filters={
                        "classification": classification, 
                        "status": status, 
                        "project": str(project_path) if project_path else "all"
                    }
                )
                return [self.response_formatter._text_converter.to_text_content(response_data)]
            
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
            
            response_data = self.response_formatter.format_tracked_issues(
                issues=[{
                    "hash": issue_data["hash"],
                    "severity": issue_data["severity"],
                    "message": issue_data["message"],
                    "classification": issue_data["classification"],
                    "status": issue_data["status"],
                    "location": issue_data["location"],
                    "notes_count": issue_data["notes_count"],
                    "detector": issue_data["detector"]
                } for issue_data in issues_data],
                filters={
                    "classification": classification,
                    "status": status,
                    "project": str(project_path) if project_path else "all"
                }
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error listing issues: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
    
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
                return [self.response_formatter._text_converter.to_text_content(response_data)]
            
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
                "last_seen": issue.last_seen.isoformat() if issue.last_seen else None            }
            
            response_data = self.response_formatter.format_issue_info(
                tracked_issue=issue_data,
                issue_hash=issue_hash
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error retrieving issue: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
    
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
                    response_data = self.response_formatter.format_error(
                        error_message="No issues requiring immediate attention",
                        error_type="no_data",
                        recovery_suggestions=[
                            ActionSuggestion(
                                action="analyze_code",
                                description="Run code analysis to find new issues",
                                tool_call="analyze_code",
                                priority="medium"
                            )
                        ]
                    )
                    return [self.response_formatter._text_converter.to_text_content(response_data)]
            
            # Format the next issue
            location_str = ""
            if next_issue.location:
                file_name = Path(next_issue.location.file).name
                location_str = f"{file_name}:{next_issue.location.line}"
            
            response_data = self.response_formatter.format_issue_info(
                tracked_issue={
                    "id": next_issue.id,
                    "severity": next_issue.severity,
                    "message": next_issue.message,
                    "classification": next_issue.classification,
                    "status": next_issue.status,
                    "location": location_str,
                    "priority": priority,
                    "reason": reason,
                    "suggested_action": "update_issue"
                },
                issue_hash=next_issue.issue_hash
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
            
        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error finding next issue: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
    
    @profile_operation("investigate_issue")
    async def investigate_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """
        Investigate an issue and automatically add notes about findings.
        This is a helper function that can be used by agents to record their investigation process.
        """
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        try:
            # Get the issue details
            issue = await self.services.issues.get_issue(issue_hash)
            
            if not issue:
                response_data = self.response_formatter.format_error(
                    error_message=f"Issue with hash '{issue_hash}' not found",
                    error_type="issue_not_found",
                    recovery_suggestions=[
                        ActionSuggestion(
                            action="list_issues",
                            description="View all available issues to find the correct hash",
                            tool_call="list_issues",
                            priority="high"
                        ),
                        ActionSuggestion(
                            action="analyze_code",
                            description="Re-analyze code to ensure issues are tracked",
                            tool_call="analyze_code",
                            priority="medium"
                        )
                    ]
                )
                return [self.response_formatter._text_converter.to_text_content(response_data)]

            # Generate investigation details based on the issue
            investigation_parts = []
            
            # Analyze the issue type and location
            investigation_parts.append(f"Issue Type: {issue.detector_id} - {issue.severity.upper()}")
            investigation_parts.append(f"Message: {issue.message}")
            
            if issue.location:
                investigation_parts.append(f"Location: {issue.location.file}:{issue.location.line}")

                # Try to read the code around the issue location
                try:
                    with open(issue.location.file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    # Get context around the issue (5 lines before and after)
                    start_line = max(0, issue.location.line - 6)  # -6 because lines are 1-indexed
                    end_line = min(len(lines), issue.location.line + 4)

                    if start_line < len(lines):
                        context_lines = []
                        for i in range(start_line, end_line):
                            line_num = i + 1
                            prefix = ">>> " if line_num == issue.location.line else "    "
                            context_lines.append(f"{prefix}{line_num:4d}: {lines[i].rstrip()}")

                        investigation_parts.append(f"Code Context:\n" + "\n".join(context_lines))
                except Exception as e:
                    investigation_parts.append(f"Could not read file context: {str(e)}")
            
            # Add metadata analysis
            if issue.metadata:
                investigation_parts.append(f"Metadata: {issue.metadata}")
            
            # Generate findings based on detector type
            findings = []
            detector_id = issue.detector_id or ""
            
            if "dead_code" in detector_id:
                findings.append("Analyzed for unused code patterns, imports, or unreachable statements")
            elif "security" in detector_id:
                findings.append("Reviewed for security vulnerabilities and unsafe patterns")
            elif "complexity" in detector_id:
                findings.append("Evaluated code complexity metrics and refactoring opportunities")
            elif "clone" in detector_id:
                findings.append("Identified code duplication that could be refactored")
            elif "circular" in detector_id:
                findings.append("Found circular dependency that may cause import issues")
            else:
                findings.append(f"Analyzed issue reported by {detector_id} detector")
            
            if issue.classification != "unclassified":
                findings.append(f"Previously classified as: {issue.classification}")
            
            investigation_details = "\n".join(investigation_parts)
            findings_text = "; ".join(findings)
            
            # Add the investigation note to the issue
            investigation_note = f"Investigation: {investigation_details}\nFindings: {findings_text}"
            success = await self.services.issues.update_issue(
                issue_hash=issue_hash,
                note=investigation_note
            )
            
            if success:
                response_data = self.response_formatter.format_investigation_complete(
                    issue_hash=issue_hash,
                    investigation_details=investigation_details,
                    findings=findings_text
                )

                # Format the basic response
                formatted_response = self.response_formatter._text_converter.to_text_content(response_data)

                # Create response with additional details
                response_parts = [formatted_response.text]

                # Add detailed investigation information
                response_parts.append(f"\n**Investigation Details:**\n{investigation_details}")
                response_parts.append(f"\n**Findings:**\n{findings_text}")

                return [types.TextContent(
                    type="text",
                    text="\n".join(response_parts)
                )]
            else:
                response_data = self.response_formatter.format_error(
                    error_message=f"Investigation completed but failed to save notes for issue {issue_hash}",
                    error_type="save_failed",
                    recovery_suggestions=[
                        ActionSuggestion(
                            action="manual_note",
                            description="Manually save the investigation results",
                            tool_call="update_issue",
                            parameters={
                                "issue_hash": issue_hash,
                                "note": investigation_note
                            },
                            priority="high"
                        ),
                        ActionSuggestion(
                            action="classify_issue",
                            description="Proceed to classify the issue based on findings",
                            tool_call="update_issue",
                            parameters={"issue_hash": issue_hash, "classification": "true_positive"},
                            priority="medium"
                        )
                    ]
                )
                return [self.response_formatter._text_converter.to_text_content(response_data)]

        except Exception as e:
            response_data = self.response_formatter.format_error(
                error_message=f"Error investigating issue: {str(e)}",
                error_type="operation_failed"
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
