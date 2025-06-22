"""
Statistics and agent interaction MCP tool handlers for Pythonium.
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..debug import profiler, profile_operation
from ..response_formatter import ActionSuggestion
from .base import BaseHandler


class StatisticsAndAgentHandlers(BaseHandler):
    """Handlers for statistics and agent interaction operations."""
    
    @profile_operation("get_tracking_statistics")
    async def get_tracking_statistics(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get statistics about issue tracking across all projects."""
        project_path = arguments.get("project_path")
        
        if project_path:
            # Get stats for specific project
            project_root = Path(project_path).resolve()
            if str(project_root) not in self._issue_trackers:
                response_data = self.response_formatter.format_error(
                    error_message=f"No issue tracking found for project: {project_root}",
                    error_type="no_tracking",
                    recovery_suggestions=[
                        ActionSuggestion(
                            action="analyze_project",
                            description="Run code analysis on this project to start tracking",
                            tool_call="analyze_code",
                            parameters={"path": str(project_root)},
                            priority="high"
                        ),
                        ActionSuggestion(
                            action="check_path",
                            description="Verify the project path is correct",
                            priority="medium"
                        )
                    ]
                )
                return [self.response_formatter.to_text_content(response_data)]

            tracker = self._issue_trackers[str(project_root)]
            stats = tracker.get_statistics()

            response_data = self.response_formatter.format_tracking_statistics(
                stats=stats,
                project_path=str(project_root)
            )
        else:
            # Get stats across all projects
            all_stats = {}
            
            for project_root, tracker in self._issue_trackers.items():
                stats = tracker.get_statistics()
                all_stats[project_root] = stats

            if not all_stats:
                response_data = self.response_formatter.format_error(
                    error_message="No tracked projects found",
                    error_type="no_projects",
                    recovery_suggestions=[
                        ActionSuggestion(
                            action="analyze_code",
                            description="Run code analysis on projects to start tracking issues",
                            tool_call="analyze_code",
                            priority="high"
                        ),
                        ActionSuggestion(
                            action="check_workspace",
                            description="Verify you're working in a directory with Python projects",
                            priority="medium"
                        )
                    ]
                )
                return [self.response_formatter.to_text_content(response_data)]

            # Aggregate stats
            total_tracked = sum(s['total_tracked'] for s in all_stats.values())
            total_active = sum(s['active'] for s in all_stats.values())
            total_suppressed = sum(s['suppressed'] for s in all_stats.values())

            # Create aggregated stats dictionary
            aggregated_stats = {
                'total_tracked': total_tracked,
                'active': total_active,
                'suppressed': total_suppressed,
                'by_classification': {},
                'by_status': {},
                'projects': all_stats
            }

            # Aggregate classification and status counts
            for stats in all_stats.values():
                for classification, count in stats.get('by_classification', {}).items():
                    aggregated_stats['by_classification'][classification] = (
                        aggregated_stats['by_classification'].get(classification, 0) + count
                    )
                for status, count in stats.get('by_status', {}).items():
                    aggregated_stats['by_status'][status] = (
                        aggregated_stats['by_status'].get(status, 0) + count
                    )

            response_data = self.response_formatter.format_tracking_statistics(
                stats=aggregated_stats,
                project_path=None
            )

        # Format the basic response
        formatted_response = self.response_formatter.to_text_content(response_data)
        
        # Create response with additional details
        response_parts = [formatted_response.text]
        
        if not project_path and 'all_stats' in locals():
            project_breakdown = ["", "📁 **Per Project Breakdown:**"]
            for project_root, stats in all_stats.items():
                project_name = Path(project_root).name
                project_breakdown.append(f"   **{project_name}:**")
                project_breakdown.append(f"      Total: {stats['total_tracked']}, Active: {stats['active']}, Suppressed: {stats['suppressed']}")
            
            response_parts.append("\n".join(project_breakdown))

        return [types.TextContent(
            type="text",
            text="\n".join(response_parts)
        )]
    
    @profile_operation("add_agent_note")
    async def add_agent_note(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Add an agent-generated note to an issue for tracking agent work."""
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        agent_action = arguments.get("agent_action", "investigated")
        investigation_details = arguments.get("investigation_details", "")
        resolution_details = arguments.get("resolution_details", "")
        
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

        # Add the agent note
        success = found_tracker.add_agent_note(issue_hash, agent_action, investigation_details, resolution_details)

        if success:
            response_data = self.response_formatter.format_agent_note_added(
                issue_hash=issue_hash,
                agent_action=agent_action,
                investigation_details=investigation_details,
                resolution_details=resolution_details
            )
            return [self.response_formatter.to_text_content(response_data)]
        else:
            response_data = self.response_formatter.format_error(
                error_message=f"Failed to add agent note to issue {issue_hash}",
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
                        description="Try adding the agent note again",
                        tool_call="add_agent_note",
                        parameters={
                            "issue_hash": issue_hash, 
                            "agent_action": agent_action,
                            "investigation_details": investigation_details,
                            "resolution_details": resolution_details
                        },
                        priority="medium"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
    
    @profile_operation("get_agent_actions")
    async def get_agent_actions(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get the history of agent actions on a specific issue."""
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
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

        # Get agent actions
        actions = found_tracker.get_agent_actions(issue_hash)

        response_data = self.response_formatter.format_agent_actions(
            actions=actions,
            issue_hash=issue_hash
        )

        # Format the basic response
        formatted_response = self.response_formatter.to_text_content(response_data)
        
        # Create response with additional details
        response_parts = [formatted_response.text]
        
        if actions:
            action_details = ["\\n📋 **Action History Details:**"]
            for i, action in enumerate(actions, 1):
                action_details.append(f"   **{i}. {action['timestamp']}**")
                action_details.append(f"      Action: {action['action']}")
                
                if action['investigation']:
                    action_details.append(f"      Investigation: {action['investigation']}")
                
                if action['resolution']:
                    action_details.append(f"      Resolution: {action['resolution']}")
            
            response_parts.append("\n".join(action_details))

        return [types.TextContent(
            type="text",
            text="\n".join(response_parts)
        )]
    
    @profile_operation("investigate_issue")
    async def investigate_issue(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """
        Investigate an issue and automatically add agent notes about findings.
        This is a helper function that can be used by agents to record their investigation process.
        """
        issue_hash = arguments.get("issue_hash")
        if not issue_hash:
            raise ValueError("issue_hash is required")
        
        # Find the issue tracker and get issue details
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

        original = tracked_issue.original_issue
        if not original:
            response_data = self.response_formatter.format_error(
                error_message=f"No original issue data found for {issue_hash}",
                error_type="missing_data",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="get_issue_info",
                        description="View available issue information",
                        tool_call="get_issue_info",
                        parameters={"issue_hash": issue_hash},
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="add_manual_note",
                        description="Manually add investigation notes",
                        tool_call="add_agent_note",
                        parameters={"issue_hash": issue_hash},
                        priority="medium"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
        
        # Generate investigation details based on the issue
        investigation_parts = []
        
        # Analyze the issue type and location
        investigation_parts.append(f"Issue Type: {original.detector_id} - {original.severity.upper()}")
        investigation_parts.append(f"Message: {original.message}")
        
        if original.location:
            investigation_parts.append(f"Location: {original.location.file}:{original.location.line}")
            
            # Try to read the code around the issue location
            try:
                with open(original.location.file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # Get context around the issue (5 lines before and after)
                start_line = max(0, original.location.line - 6)  # -6 because lines are 1-indexed
                end_line = min(len(lines), original.location.line + 4)
                
                if start_line < len(lines):
                    context_lines = []
                    for i in range(start_line, end_line):
                        line_num = i + 1
                        prefix = ">>> " if line_num == original.location.line else "    "
                        context_lines.append(f"{prefix}{line_num:4d}: {lines[i].rstrip()}")
                    
                    investigation_parts.append(f"Code Context:\\n" + "\n".join(context_lines))
            except Exception as e:
                investigation_parts.append(f"Could not read file context: {str(e)}")
        
        # Add metadata analysis
        if original.metadata:
            investigation_parts.append(f"Metadata: {original.metadata}")
        
        # Generate findings based on detector type
        findings = []
        detector_id = original.detector_id or ""
        
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
        
        if tracked_issue.classification != tracked_issue.classification.UNCLASSIFIED:
            findings.append(f"Previously classified as: {tracked_issue.classification.value}")
        
        investigation_details = "\n".join(investigation_parts)
        findings_text = "; ".join(findings)
        
        # Automatically add the investigation note
        success = found_tracker.add_agent_note(
            issue_hash, 
            "investigated", 
            investigation_details, 
            f"Findings: {findings_text}"
        )
        
        if success:
            response_data = self.response_formatter.format_investigation_complete(
                issue_hash=issue_hash,
                investigation_details=investigation_details,
                findings=findings_text
            )
            
            # Format the basic response
            formatted_response = self.response_formatter.to_text_content(response_data)
            
            # Create response with additional details
            response_parts = [formatted_response.text]
            
            # Add detailed investigation information
            response_parts.append(f"\\n🔍 **Investigation Details:**\\n{investigation_details}")
            response_parts.append(f"\\n📋 **Findings:**\\n{findings_text}")
            
            return [types.TextContent(
                type="text",
                text="\n".join(response_parts)
            )]
        else:
            response_data = self.response_formatter.format_error(
                error_message=f"Investigation completed but failed to save agent note for issue {issue_hash}",
                error_type="save_failed",
                recovery_suggestions=[
                    ActionSuggestion(
                        action="manual_note",
                        description="Manually save the investigation results",
                        tool_call="add_agent_note",
                        parameters={
                            "issue_hash": issue_hash,
                            "agent_action": "investigated",
                            "investigation_details": investigation_details,
                            "resolution_details": f"Findings: {findings_text}"
                        },
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="classify_issue",
                        description="Proceed to classify the issue based on findings",
                        tool_call="mark_issue",
                        parameters={"issue_hash": issue_hash},
                        priority="medium"
                    )
                ]
            )
            return [self.response_formatter.to_text_content(response_data)]
