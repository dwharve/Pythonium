"""
Base handler class with shared functionality for MCP tool handlers.
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..debug import profiler, profile_operation, logger, info_log, warning_log, error_log
from ..issue_tracking import IssueTracker
from ..response_formatter import ResponseFormatter, ActionSuggestion
from ..workflow_guide import WorkflowGuide
from pythonium.database_paths import DatabasePathResolver


class BaseHandler:
    """Base class for MCP tool handlers with shared functionality."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self._analysis_results: Dict[str, List] = {}
        self._issue_trackers: Dict[str, IssueTracker] = {}  # Project root -> IssueTracker
        self.response_formatter = ResponseFormatter()
        self.workflow_guide = WorkflowGuide()
        
        # Initialize any existing issue trackers
        self._initialize_existing_trackers()
    
    def _initialize_existing_trackers(self) -> None:
        """Initialize issue trackers using consistent path resolution."""
        
        # Use centralized path resolver to determine the workspace project root
        workspace_root = DatabasePathResolver.resolve_project_root()
        
        info_log(f"Initializing issue tracker for workspace: {workspace_root}")
        
        # Only initialize tracker for the workspace project
        issues_db_path = DatabasePathResolver.get_issues_db_path(workspace_root)
        if issues_db_path.exists():
            info_log(f"Found existing issues database at {issues_db_path}")
            tracker = self._get_issue_tracker(workspace_root)
            info_log(f"Loaded tracker for {workspace_root} with {len(tracker.tracked_issues)} issues")
        else:
            info_log(f"No existing issues database found, will create on first analysis")
        
        info_log(f"Initialization complete. Using single project root: {workspace_root}")
    
    def _get_issue_tracker(self, project_root: Path) -> IssueTracker:
        """
        Get or create an issue tracker for the given project root.
        
        Args:
            project_root: Root directory of the project
            
        Returns:
            IssueTracker instance for the project
        """
        root_str = str(project_root)
        if root_str not in self._issue_trackers:
            self._issue_trackers[root_str] = IssueTracker(project_root)
        return self._issue_trackers[root_str]
    
    def clear_analysis_results(self, path: str = None) -> None:
        """Clear stored analysis results."""
        if path:
            self._analysis_results.pop(path, None)
        else:
            self._analysis_results.clear()
    
    def _find_issue_tracker_for_hash(self, issue_hash: str):
        """Find the issue tracker that contains the given issue hash."""
        for tracker in self._issue_trackers.values():
            if issue_hash in tracker.tracked_issues:
                return tracker
        return None
