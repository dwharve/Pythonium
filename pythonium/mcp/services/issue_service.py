"""
Issue tracking service for Pythonium MCP server.

Provides centralized issue management functionality including tracking,
classification, and agent interactions with issues.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

from pythonium.database_paths import DatabasePathResolver
from pythonium.models import Issue
from ..utils.debug import info_log, warning_log, error_log
from .issue_tracking import IssueTracker

if TYPE_CHECKING:
    from .service_registry import ServiceRegistry


class IssueService:
    """
    Service for managing issue tracking operations.
    
    This service encapsulates all issue tracking functionality:
    - Managing issue trackers for different projects
    - Providing unified interface for issue operations
    - Handling agent interactions and notes
    """
    
    def __init__(self, registry: 'ServiceRegistry'):
        """Initialize the issue service."""
        self.registry = registry
        self._issue_trackers: Dict[str, IssueTracker] = {}
        self._initialize_existing_trackers()
    
    def _initialize_existing_trackers(self) -> None:
        """Initialize issue trackers for existing databases."""
        # Don't initialize any trackers at startup - they will be created on demand
        # This avoids the issue where the working directory determines the project root
        info_log("Issue service initialized - trackers will be created on demand")
    
    def get_tracker(self, project_root: Path) -> IssueTracker:
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
            info_log(f"Created issue tracker for project: {project_root}")
        return self._issue_trackers[root_str]
    
    def find_tracker_for_issue(self, issue_hash: str) -> Optional[IssueTracker]:
        """
        Find the issue tracker that contains the given issue hash.
        
        Args:
            issue_hash: Hash of the issue to find
            
        Returns:
            IssueTracker containing the issue, or None if not found
        """
        for tracker in self._issue_trackers.values():
            if issue_hash in tracker.issues:
                return tracker
        return None
    
    async def track_issues(
        self,
        issues: List[Issue],
        project_root: Path,
        analysis_path: Path
    ) -> Dict[str, Any]:
        """
        Track a list of issues in the appropriate tracker.
        
        Args:
            issues: List of issues to track
            project_root: Project root directory
            analysis_path: Path that was analyzed
            
        Returns:
            Dictionary with tracking statistics
        """
        tracker = self.get_tracker(project_root)
        
        new_issues = 0
        updated_issues = 0
        
        # Process all issues at once
        processed_issues = tracker.process_new_issues(issues)
        new_issues = len([i for i in processed_issues if i.first_seen and i.first_seen.date() == datetime.now().date()])
        updated_issues = len(processed_issues) - new_issues
        
        info_log(f"Tracked {new_issues} new issues, updated {updated_issues} existing issues")
        
        return {
            'new_issues': new_issues,
            'updated_issues': updated_issues,
            'total_tracked': len(tracker.issues)
        }
    
    async def update_issue(
        self,
        issue_hash: str,
        severity: Optional[str] = None,
        message: Optional[str] = None,
        classification: Optional[str] = None,
        status: Optional[str] = None,
        note: Optional[str] = None
    ) -> bool:
        """
        Update an issue with new information.
        
        Args:
            issue_hash: Hash of the issue to update
            severity: Optional new severity
            message: Optional new message
            classification: Optional new classification
            status: Optional new status
            note: Optional new note to add
            
        Returns:
            True if the issue was successfully updated
        """
        tracker = self.find_tracker_for_issue(issue_hash)
        if not tracker:
            raise ValueError(f"Issue not found: {issue_hash}")
        
        return tracker.update_issue(
            issue_hash=issue_hash,
            severity=severity,
            message=message,
            classification=classification,
            status=status,
            note=note
        )
    
    async def get_issue(self, issue_hash: str) -> Optional[Issue]:
        """
        Get detailed information about an issue.
        
        Args:
            issue_hash: Hash of the issue
            
        Returns:
            Issue object, or None if not found
        """
        tracker = self.find_tracker_for_issue(issue_hash)
        if not tracker:
            return None
        
        return tracker.get_issue(issue_hash)
    
    async def list_issues(
        self,
        project_path: Optional[Path] = None,
        classification: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Issue]:
        """
        List issues with optional filtering.
        
        Args:
            project_path: Specific project to list issues for
            classification: Filter by classification
            status: Filter by status  
            
        Returns:
            List of Issue objects
        """
        issues = []
        
        if project_path:
            # List issues for specific project
            tracker = self.get_tracker(project_path)
            issues.extend(tracker.list_issues(
                classification=classification,
                status=status
            ))
        else:
            # If no project path specified, check all available trackers
            # If no trackers exist yet, try to find a project based on analysis context
            if not self._issue_trackers:
                # Try to find the most likely project root
                # Look for common Python project indicators in nearby directories
                potential_roots = []
                
                # Check if we can find a project root from the current context
                try:
                    current_root = DatabasePathResolver.resolve_project_root()
                    potential_roots.append(current_root)
                except:
                    pass
                
                # Check common project locations relative to this code
                code_location = Path(__file__).parents[3]  # Pythonium project root
                if code_location.exists():
                    potential_roots.append(code_location)
                
                # Use the first viable project root we find
                for root in potential_roots:
                    if root.exists():
                        tracker = self.get_tracker(root)
                        issues.extend(tracker.list_issues(
                            classification=classification,
                            status=status
                        ))
                        break
            else:
                # List issues from all existing trackers
                for tracker in self._issue_trackers.values():
                    issues.extend(tracker.list_issues(
                        classification=classification,
                        status=status
                    ))
        
        return issues
    
    async def get_statistics(self, project_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get statistics for a project or all projects.
        
        Args:
            project_path: Specific project to get statistics for
            
        Returns:
            Dictionary with statistics
        """
        if project_path:
            tracker = self.get_tracker(project_path)
            return tracker.db.get_statistics()
        else:
            # Aggregate statistics from all trackers
            total_stats = {
                'total_tracked': 0,
                'by_classification': {},
                'by_status': {},
                'by_severity': {}
            }
            
            for tracker in self._issue_trackers.values():
                stats = tracker.db.get_statistics()
                total_stats['total_tracked'] += stats.get('total_tracked', 0)
                
                # Merge classification counts
                for classification, count in stats.get('by_classification', {}).items():
                    total_stats['by_classification'][classification] = \
                        total_stats['by_classification'].get(classification, 0) + count
                
                # Merge status counts
                for status, count in stats.get('by_status', {}).items():
                    total_stats['by_status'][status] = \
                        total_stats['by_status'].get(status, 0) + count
                
                # Merge severity counts
                for severity, count in stats.get('by_severity', {}).items():
                    total_stats['by_severity'][severity] = \
                        total_stats['by_severity'].get(severity, 0) + count
            
            return total_stats
        
    async def get_next_issue(
        self,
        project_path: Optional[Path] = None,
        priority_order: Optional[List[str]] = None
    ) -> Optional[Issue]:
        """
        Get the next issue that needs attention.
        
        Args:
            project_path: Specific project to get next issue for
            priority_order: Priority order for issue selection
            
        Returns:
            Next issue to work on, or None if no issues need attention
        """
        if priority_order is None:
            priority_order = ["unclassified", "pending", "work_in_progress"]
        
        # Get all issues using the same logic as list_issues
        all_issues = await self.list_issues(project_path=project_path)
        
        # Find issues by priority order
        for priority in priority_order:
            if priority == "unclassified":
                candidates = [i for i in all_issues if i.classification == "unclassified"]
            elif priority in ["pending", "work_in_progress", "completed"]:
                candidates = [i for i in all_issues if i.status == priority]
            else:
                continue
                
            if candidates:
                # Return the first candidate (could be enhanced with more sophisticated ordering)
                return candidates[0]
        
        return None
