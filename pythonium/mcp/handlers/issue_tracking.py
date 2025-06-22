"""
Issue tracking MCP tool handlers for Pythonium.
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..debug import profiler, profile_operation, info_log
from ..response_formatter import ActionSuggestion
from .base import BaseHandler


class IssueTrackingHandlers(BaseHandler):
    """Handlers for issue tracking operations."""
    
    @profile_operation("mark_issue")
    async def mark_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Mark an issue as true/false positive and set its status."""
        from ..issue_tracking import IssueStatus, IssueClassification
        
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        classification_str = arguments.get("classification", "unclassified")
        try:
            classification = IssueClassification(classification_str)
        except ValueError:
            valid_values = [e.value for e in IssueClassification]
            raise ValueError(f"Invalid classification '{classification_str}'. Valid values: {valid_values}")
        
        status_str = arguments.get("status")
        status = None
        if status_str:
            try:
                status = IssueStatus(status_str)
            except ValueError:
                valid_values = [e.value for e in IssueStatus]
                raise ValueError(f"Invalid status '{status_str}'. Valid values: {valid_values}")
        
        notes = arguments.get("notes", "")
        assigned_to = arguments.get("assigned_to", "")
        
        # Find the issue tracker that contains this issue
        found_tracker = self._find_issue_tracker_for_hash(issue_hash)
        
        if not found_tracker:
            # Try to initialize trackers in case some were missed
            info_log("mark_issue: Attempting to initialize additional trackers...")
            self._initialize_existing_trackers()
            found_tracker = self._find_issue_tracker_for_hash(issue_hash)
        
        if not found_tracker:
            response_data = self.response_formatter.format_error(
                error_message=f"Issue with hash '{issue_hash}' not found in any tracked projects.",
                error_type="issue_not_found",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="list_tracked_issues",
                        description="View all available issues to find the correct hash",
                        tool_call="list_tracked_issues",
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
            return [self.response_formatter.to_text_content(response_data)]
        
        # Mark the issue
        success = found_tracker.mark_issue(issue_hash, classification, status, notes, assigned_to)
        
        if success:
            # Automatically add agent note about the marking action
            action_parts = []
            if classification_str != "unclassified":
                action_parts.append(f"classified as {classification_str}")
            if status_str:
                action_parts.append(f"status set to {status_str}")
            if assigned_to:
                action_parts.append(f"assigned to {assigned_to}")
            
            action_description = "marked issue - " + ", ".join(action_parts) if action_parts else "marked issue"
            
            # Generate investigation details based on the classification
            investigation_details = ""
            if classification == IssueClassification.TRUE_POSITIVE:
                investigation_details = "Confirmed as a legitimate issue that should be addressed"
            elif classification == IssueClassification.FALSE_POSITIVE:
                investigation_details = "Determined to be a false positive - not a real issue"
            
            if notes:
                resolution_details = f"User notes: {notes}"
            else:
                resolution_details = "Issue classification updated"
            
            # Add the agent note
            found_tracker.add_agent_note(
                issue_hash, 
                action_description, 
                investigation_details, 
                resolution_details
            )
            
            tracked_issue = found_tracker.get_issue_info(issue_hash)
            
            response_data = self.response_formatter.format_issue_marked(
                issue_hash=issue_hash,
                classification=tracked_issue.classification.value,
                status=tracked_issue.status.value,
                notes=tracked_issue.notes
            )
            return [self.response_formatter.to_text_content(response_data)]
        else:
            response_data = self.response_formatter.format_error(
                error_message=f"Failed to update issue {issue_hash}",
                error_type="operation_failed",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="get_issue_info",
                        description="Check if the issue still exists and get current details",
                        tool_call="get_issue_info",
                        parameters={"issue_hash": issue_hash},
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="list_tracked_issues",
                        description="Verify the issue hash is correct",
                        tool_call="list_tracked_issues",
                        priority="medium"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("list_tracked_issues")
    async def list_tracked_issues(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """List tracked issues with optional filtering."""
        from ..issue_tracking import IssueStatus, IssueClassification
        
        project_path = arguments.get("project_path")
        classification_str = arguments.get("classification")
        status_str = arguments.get("status")
        include_suppressed = arguments.get("include_suppressed", False)
        
        # Parse filters
        classification = None
        if classification_str:
            try:
                classification = IssueClassification(classification_str)
            except ValueError:
                valid_values = [e.value for e in IssueClassification]
                raise ValueError(f"Invalid classification '{classification_str}'. Valid values: {valid_values}")
        
        status = None
        if status_str:
            try:
                status = IssueStatus(status_str)
            except ValueError:
                valid_values = [e.value for e in IssueStatus]
                raise ValueError(f"Invalid status '{status_str}'. Valid values: {valid_values}")
        
        # Get trackers to query
        trackers_to_query = []
        if project_path:
            # Query specific project
            project_root = Path(project_path).resolve()
            tracker = self._get_issue_tracker(project_root)
            trackers_to_query = [tracker]
        else:
            # Query all tracked projects
            trackers_to_query = list(self._issue_trackers.values())
        
        if not trackers_to_query:
            response_data = self.response_formatter.format_error(
                error_message="No tracked projects found",
                error_type="no_projects",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="analyze_code",
                        description="Run code analysis on a project to start tracking issues",
                        tool_call="analyze_code",
                        priority="high"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]

        # Collect all matching issues
        all_issues = []
        for tracker in trackers_to_query:
            issues = tracker.list_issues(classification, status, include_suppressed)
            for issue in issues:
                # Convert original issue to dictionary format for the formatter
                original_issue_dict = None
                if issue.original_issue:
                    original = issue.original_issue
                    original_issue_dict = {
                        "id": original.id,
                        "severity": original.severity,
                        "message": original.message,
                        "symbol": original.symbol,
                        "detector_id": original.detector_id,
                        "metadata": original.metadata,
                        "location": {
                            "file": str(original.location.file) if original.location else None,
                            "line": original.location.line if original.location else None,
                            "column": original.location.column if original.location else None,
                            "end_line": original.location.end_line if original.location else None,
                            "end_column": original.location.end_column if original.location else None,
                        } if original.location else None,
                        "related_files": [str(f) for f in original.related_files] if original.related_files else []
                    }
                
                # Convert tracked issue to dictionary format for the formatter
                issue_dict = {
                    "issue_hash": issue.issue_hash,
                    "classification": issue.classification.value,
                    "status": issue.status.value,
                    "suppressed": issue.suppressed,
                    "notes": issue.notes,
                    "assigned_to": issue.assigned_to,
                    "first_seen": issue.first_seen,
                    "last_seen": issue.last_seen,
                    "project_root": tracker.project_root,
                    "original_issue": original_issue_dict
                }
                all_issues.append(issue_dict)

        # Prepare filters for the formatter
        filters = {}
        if classification:
            filters["classification"] = classification.value
        if status:
            filters["status"] = status.value
        if include_suppressed:
            filters["include_suppressed"] = True

        # Use new response formatter
        response_data = self.response_formatter.format_tracked_issues(
            issues=all_issues,
            filters=filters
        )

        # Add detailed issue listing to the response data
        if all_issues:
            # Group by project for detailed display
            by_project = {}
            for issue_dict in all_issues:
                project_root = issue_dict["project_root"]
                if project_root not in by_project:
                    by_project[project_root] = []
                by_project[project_root].append(issue_dict)
            
            detailed_lines = []
            for project_root, issues in by_project.items():
                detailed_lines.extend([
                    f"\\n📁 **Project: {Path(project_root).name}** ({len(issues)} issues)",
                    ""
                ])
                
                for issue in issues[:20]:  # Limit per project
                    original = issue["original_issue"]
                    location_str = ""
                    if original and original.get("location"):
                        location = original["location"]
                        if location:
                            file_name = Path(location["file"]).name if location["file"] else "unknown"
                            line_num = location["line"] if location["line"] else "?"
                            location_str = f" @ {file_name}:{line_num}"
                    
                    status_indicator = {
                        "pending": "⏳",
                        "work_in_progress": "🔄", 
                        "completed": "✅"
                    }.get(issue["status"], "❓")
                    
                    classification_indicator = {
                        "true_positive": "🔴",
                        "false_positive": "🟢",
                        "unclassified": "⚪"
                    }.get(issue["classification"], "❓")
                    
                    suppressed_indicator = " [SUPPRESSED]" if issue["suppressed"] else ""
                    
                    detailed_lines.append(
                        f"   {classification_indicator} {status_indicator} `{issue['issue_hash']}`: "
                        f"{original.get('message', 'No message')[:80] if original else 'No message'}...{location_str}{suppressed_indicator}"
                    )
                    
                    if issue["notes"]:
                        detailed_lines.append(f"      💭 Notes: {issue['notes']}")
                    if issue["assigned_to"]:
                        detailed_lines.append(f"      👤 Assigned: {issue['assigned_to']}")
                
                if len(issues) > 20:
                    detailed_lines.append(f"   ... and {len(issues) - 20} more issues")

            # Format the basic response - now returns a TextContent
            formatted_response = self.response_formatter.to_text_content(response_data)
            
            # Extract the text from the TextContent to combine with other parts
            response_parts = [formatted_response.text]
            response_parts.append("\n".join(detailed_lines))
            response_parts.append("\\n🔍 **Legend:** 🔴 True Positive  🟢 False Positive  ⚪ Unclassified\\n⏳ Pending  🔄 Work in Progress  ✅ Completed")
            
            # Create final text content
            response_text = types.TextContent(
                type="text",
                text="\n".join(response_parts)
            )
        else:
            # Already a TextContent object
            response_text = self.response_formatter.to_text_content(response_data)

        return [response_text]
    
    @profile_operation("get_issue_info")
    async def get_issue_info(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get detailed information about a specific tracked issue."""
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        # Find the issue tracker that contains this issue
        found_tracker = None
        tracked_issue = None
        for tracker in self._issue_trackers.values():
            tracked_issue = tracker.get_issue_info(issue_hash)
            if tracked_issue:
                found_tracker = tracker
                break
        
        if not tracked_issue:
            response_data = self.response_formatter.format_error(
                error_message=f"Issue with hash '{issue_hash}' not found",
                error_type="issue_not_found",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="list_tracked_issues",
                        description="View all available issues to find the correct hash",
                        tool_call="list_tracked_issues",
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
            return [self.response_formatter.to_text_content(response_data)]

        # Convert tracked issue to dictionary format for the formatter
        original_issue_dict = None
        if tracked_issue.original_issue:
            original = tracked_issue.original_issue
            original_issue_dict = {
                "id": original.id,
                "severity": original.severity,
                "message": original.message,
                "symbol": original.symbol,
                "detector_id": original.detector_id,
                "metadata": original.metadata,
                "location": {
                    "file": str(original.location.file) if original.location else None,
                    "line": original.location.line if original.location else None,
                    "column": original.location.column if original.location else None,
                    "end_line": original.location.end_line if original.location else None,
                    "end_column": original.location.end_column if original.location else None,
                } if original.location else None,
                "related_files": [str(f) for f in original.related_files] if original.related_files else []
            }
        
        tracked_issue_dict = {
            "issue_hash": tracked_issue.issue_hash,
            "classification": tracked_issue.classification.value,
            "status": tracked_issue.status.value,
            "suppressed": tracked_issue.suppressed,
            "notes": tracked_issue.notes,
            "assigned_to": tracked_issue.assigned_to,
            "first_seen": tracked_issue.first_seen,
            "last_seen": tracked_issue.last_seen,
            "original_issue": original_issue_dict
        }

        # Use new response formatter
        response_data = self.response_formatter.format_issue_info(
            tracked_issue=tracked_issue_dict,
            issue_hash=issue_hash
        )

        # Format the basic response
        formatted_response = self.response_formatter.to_text_content(response_data)
        
        # Create response with additional details
        response_parts = [formatted_response.text]
        
        # Add detailed original issue information
        original = tracked_issue.original_issue
        if original:
            detail_lines = [
                "",
                "🔍 **Original Issue Details:**",
                f"   **ID:** {original.id}",
                f"   **Detector:** {original.detector_id}",
                f"   **Severity:** {original.severity}",
                f"   **Message:** {original.message}",
            ]
            
            if original.location:
                detail_lines.extend([
                    f"   **File:** {original.location.file}",
                    f"   **Line:** {original.location.line}",
                    f"   **Column:** {original.location.column}",
                ])
            
            if original.metadata:
                detail_lines.append("   **Metadata:**")
                for k, v in original.metadata.items():
                    detail_lines.append(f"      {k}: {v}")
            
            response_parts.append("\n".join(detail_lines))

        # Add tracking information
        tracking_info = [
            f"\\n\\n📊 **Tracking Info:**",
            f"   First seen: {tracked_issue.first_seen.strftime('%Y-%m-%d %H:%M:%S')}",
            f"   Last seen: {tracked_issue.last_seen.strftime('%Y-%m-%d %H:%M:%S')}",
            f"   Suppressed: {'Yes' if tracked_issue.suppressed else 'No'}"
        ]
        response_parts.append("\n".join(tracking_info))

        # Return as a single text content
        return [types.TextContent(
            type="text",
            text="\n".join(response_parts)
        )]
    
    @profile_operation("suppress_issue")
    async def suppress_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Suppress or unsuppress an issue."""
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        suppress = arguments.get("suppress", True)
        
        # Find the issue tracker that contains this issue
        found_tracker = self._find_issue_tracker_for_hash(issue_hash)
        
        if not found_tracker:
            response_data = self.response_formatter.format_error(
                error_message=f"Issue with hash '{issue_hash}' not found",
                error_type="issue_not_found",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="list_tracked_issues",
                        description="View all available issues to find the correct hash",
                        tool_call="list_tracked_issues",
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
            return [self.response_formatter.to_text_content(response_data)]

        success = found_tracker.suppress_issue(issue_hash, suppress)

        if success:
            response_data = self.response_formatter.format_issue_suppressed(
                issue_hash=issue_hash,
                suppressed=suppress
            )
            return [self.response_formatter.to_text_content(response_data)]
        else:
            response_data = self.response_formatter.format_error(
                error_message=f"Failed to update suppression status for issue {issue_hash}",
                error_type="operation_failed",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="check_issue_status",
                        description="Check if the issue still exists and is accessible",
                        tool_call="get_issue_info",
                        parameters={"issue_hash": issue_hash},
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="retry_operation",
                        description="Try the suppress operation again",
                        tool_call="suppress_issue",
                        parameters={"issue_hash": issue_hash, "suppress": suppress},
                        priority="medium"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("get_next_issue_to_work")
    async def get_next_issue_to_work(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get details of the next issue that needs to be worked on."""
        from ..issue_tracking import IssueStatus, IssueClassification
        
        project_path = arguments.get("project_path")
        priority_order = arguments.get("priority_order", ["unclassified", "pending", "work_in_progress"])
        include_suppressed = arguments.get("include_suppressed", False)
        
        # Parse priority order
        parsed_priority = []
        for status_str in priority_order:
            if status_str == "unclassified":
                parsed_priority.append(IssueClassification.UNCLASSIFIED)
            elif status_str in ["pending", "work_in_progress"]:
                try:
                    parsed_priority.append(IssueStatus(status_str))
                except ValueError:
                    continue
        
        # Get trackers to query
        trackers_to_query = []
        if project_path:
            # Query specific project
            project_root = Path(project_path).resolve()
            tracker = self._get_issue_tracker(project_root)
            trackers_to_query = [tracker]
        else:
            # Query all tracked projects
            trackers_to_query = list(self._issue_trackers.values())
        
        if not trackers_to_query:
            response_data = self.response_formatter.format_error(
                error_message="No tracked projects found",
                error_type="no_projects",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="analyze_code",
                        description="Run code analysis on a project to start tracking issues",
                        tool_call="analyze_code",
                        priority="high"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]

        # Collect all issues and find the next one to work on
        next_issue = None
        
        for priority_item in parsed_priority:
            for tracker in trackers_to_query:
                try:
                    if isinstance(priority_item, IssueClassification):
                        # Look for issues with this classification
                        issues = tracker.list_issues(
                            classification=priority_item,
                            include_suppressed=include_suppressed
                        )
                    elif isinstance(priority_item, IssueStatus):
                        # Look for issues with this status
                        issues = tracker.list_issues(
                            status=priority_item,
                            include_suppressed=include_suppressed
                        )
                    else:
                        continue
                    
                    if issues:
                        # Return the first issue found in priority order
                        next_issue = issues[0]
                        break
                        
                except Exception as e:
                    # Skip this tracker and continue
                    continue
            
            if next_issue:
                break
        
        if not next_issue:
            response_data = self.response_formatter.format_error(
                error_message="No actionable issues found",
                error_type="no_actionable_issues",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="analyze_code",
                        description="Run code analysis to find new issues",
                        tool_call="analyze_code",
                        priority="medium"
                    ),
                    ActionSuggestion(
                        action="list_tracked_issues", 
                        description="List all tracked issues to see what's available",
                        tool_call="list_tracked_issues",
                        priority="low"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
        
        # Format the next issue details
        original = next_issue.original_issue
        issue_data = {
            "issue_hash": next_issue.issue_hash,
            "classification": next_issue.classification.value,
            "status": next_issue.status.value,
            "notes": next_issue.notes,
            "assigned_to": next_issue.assigned_to,
            "first_seen": next_issue.first_seen.isoformat(),
            "last_seen": next_issue.last_seen.isoformat(),
            "suppressed": next_issue.suppressed
        }
        
        # Add original issue details if available
        if original:
            issue_data.update({
                "message": original.message,
                "detector_id": original.detector_id,
                "severity": original.severity,
                "symbol": original.symbol,
                "file_path": str(original.location.file) if original.location else None,
                "line_number": original.location.line if original.location else None,
                "column": original.location.column if original.location else None,
                "metadata": original.metadata or {}
            })
        
        # Create a manual response
        response_text = f"**Next Issue to Work On**\n\n"
        response_text += f"Issue Hash: `{next_issue.issue_hash}`\n"
        if original:
            response_text += f"Message: {original.message}\n"
            response_text += f"Detector: {original.detector_id}\n"
            response_text += f"Severity: {original.severity}\n"
            if original.location:
                response_text += f"File: {original.location.file}\n"
                response_text += f"Line: {original.location.line}\n"
        
        response_text += f"Classification: {next_issue.classification.value}\n"
        response_text += f"Status: {next_issue.status.value}\n"
        
        if next_issue.notes:
            response_text += f"Notes: {next_issue.notes}\n"
        if next_issue.assigned_to:
            response_text += f"Assigned To: {next_issue.assigned_to}\n"
            
        response_text += f"\nSuggested Actions:\n"
        response_text += f"   • Use `investigate_issue` with hash `{next_issue.issue_hash}` to analyze this issue\n"
        response_text += f"   • Use `mark_issue` to classify or update status\n"
        response_text += f"   • Use `get_issue_info` for detailed information\n"
        
        return [types.TextContent(type="text", text=response_text)]
