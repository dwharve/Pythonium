"""
Issue tracking system for Pythonium MCP server.

This module provides persistent issue tracking functionality that allows updating
issues with classification, status changes, and note tracking. Storage is handled 
via SQLite database for reliability and optimized performance.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pythonium.models import Issue, Location
from ..storage.issue_database import IssueDatabase


class IssueTracker:
    """
    Persistent issue tracking system for Pythonium analysis using unified Issue model.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize the issue tracker.
        
        Args:
            project_root: Root directory of the project being analyzed
        """
        self.project_root = project_root
        
        # In-memory cache of tracked issues
        self.issues: Dict[str, Issue] = {}
        
        # Initialize database
        self.db = IssueDatabase(project_root)
        
        # Load issues from database into memory
        self._load_issues_from_db()
    
    def _load_issues_from_db(self) -> None:
        """Load all tracked issues from the database into memory."""
        self.issues.clear()
        
        try:
            db_issues = self.db.list_issues()
            for issue_data in db_issues:
                # Convert notes from string to list if needed
                notes = issue_data.get("notes", [])
                if isinstance(notes, str):
                    notes = [notes] if notes else []
                
                issue = Issue(
                    id=issue_data["id"],
                    severity=issue_data["severity"],
                    message=issue_data["message"],
                    symbol=None,  # Not persisted
                    location=self._create_location_from_data(issue_data),
                    detector_id=issue_data.get("detector_id"),
                    metadata=issue_data.get("metadata", {}),
                    related_files=[Path(f) for f in issue_data.get("related_files", [])],
                    issue_hash=issue_data["issue_hash"],
                    classification=issue_data["classification"],
                    status=issue_data["status"],
                    notes=notes,
                    first_seen=datetime.fromisoformat(issue_data["first_seen"]) if issue_data.get("first_seen") else None,
                    last_seen=datetime.fromisoformat(issue_data["last_seen"]) if issue_data.get("last_seen") else None,
                )
                self.issues[issue.issue_hash] = issue
                
        except Exception as e:
            # Import debug here to avoid circular imports
            try:
                from ..utils.debug import error_log
                error_log(f"Error loading issues from database: {str(e)}")
            except:
                # Fallback if debug import fails
                print(f"Error loading issues from database: {str(e)}")
            # Continue with empty issues if loading fails
    
    def _create_location_from_data(self, issue_data: Dict[str, Any]) -> Optional[Location]:
        """Create Location object from database data."""
        file_path = issue_data.get("file_path")
        if file_path:
            return Location(
                file=Path(file_path),
                line=issue_data.get("line_number", 1),
                column=issue_data.get("column_number", 0),
                end_line=issue_data.get("end_line"),
                end_column=issue_data.get("end_column")
            )
        return None
    
    def _ensure_tracking_dir(self) -> None:
        """Ensure the tracking directory exists."""
        pass  # No longer needed with database storage
    
    def _generate_issue_hash(self, issue: Issue) -> str:
        """
        Generate a unique hash for an issue based on its identifying characteristics.
        
        This method is deprecated - use issue.generate_hash() instead.
        """
        return issue.generate_hash()
    
    def _load_issues_from_db(self) -> None:
        """Load issues from the database into the in-memory cache."""
        # Clear current cache
        self.issues.clear()
        
        # Get all issues from database
        db_issues = self.db.list_issues()
        
        for issue_data in db_issues:
            # Convert notes from string to list if needed
            notes = issue_data.get("notes", [])
            if isinstance(notes, str):
                notes = [notes] if notes else []
            
            issue = Issue(
                id=issue_data["id"],
                severity=issue_data["severity"],
                message=issue_data["message"],
                symbol=None,  # Not persisted
                location=self._create_location_from_data(issue_data),
                detector_id=issue_data.get("detector_id"),
                metadata=issue_data.get("metadata", {}),
                related_files=[Path(f) for f in issue_data.get("related_files", [])],
                issue_hash=issue_data["issue_hash"],
                classification=issue_data["classification"],
                status=issue_data["status"],
                notes=notes,
                first_seen=datetime.fromisoformat(issue_data["first_seen"]) if issue_data.get("first_seen") else None,
                last_seen=datetime.fromisoformat(issue_data["last_seen"]) if issue_data.get("last_seen") else None,
            )
            self.issues[issue.issue_hash] = issue
    
    def process_new_issues(self, issues: List[Issue]) -> List[Issue]:
        """
        Process a list of new issues from an analysis run.
        
        This method:
        1. Updates existing tracked issues' last_seen timestamp
        2. Creates new tracked issues for previously unseen issues
        
        Args:
            issues: List of issues from current analysis
            
        Returns:
            List of issues that should be reported
        """
        now = datetime.now(timezone.utc)
        current_hashes = set()
        filtered_issues = []
        
        for issue in issues:
            issue_hash = issue.generate_hash()
            current_hashes.add(issue_hash)
            
            if issue_hash in self.issues:
                # Update existing tracked issue
                tracked = self.issues[issue_hash]
                tracked.last_seen = now
                tracked.severity = issue.severity
                tracked.message = issue.message
                tracked.metadata = issue.metadata
                tracked.related_files = issue.related_files
                
                # Update in database
                self.db.upsert_tracked_issue(tracked)
                filtered_issues.append(tracked)
            else:
                # Create new tracked issue
                issue.issue_hash = issue_hash
                issue.first_seen = now
                issue.last_seen = now
                self.issues[issue_hash] = issue
                
                # Save to database
                self.db.upsert_tracked_issue(issue)
                filtered_issues.append(issue)
        
        # Remove issues that are no longer detected
        self._cleanup_stale_issues(current_hashes)
        
        return filtered_issues
    
    def _cleanup_stale_issues(self, current_hashes: Set[str]) -> None:
        """
        Remove tracked issues that are no longer detected.
        
        Args:
            current_hashes: Set of issue hashes from current analysis
        """
        # Clean up in-memory cache
        stale_hashes = set(self.issues.keys()) - current_hashes
        for hash_to_remove in stale_hashes:
            del self.issues[hash_to_remove]
        
        # Clean up database
        self.db.cleanup_stale_issues(current_hashes)
    
    def update_issue(self, issue_hash: str, severity: Optional[str] = None, message: Optional[str] = None,
                     classification: Optional[str] = None, status: Optional[str] = None, note: Optional[str] = None) -> bool:
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
            True if the issue was found and updated, False otherwise
        """
        if issue_hash not in self.issues:
            return False
        
        issue = self.issues[issue_hash]
        
        if severity:
            issue.severity = severity
        
        if message:
            issue.message = message
        
        if classification:
            issue.classification = classification
        
        if status:
            issue.status = status
        
        if note:
            issue.add_note(note)
        
        # Update in database
        self.db.upsert_tracked_issue(issue)
        return True
    
    def get_issue(self, issue_hash: str) -> Optional[Issue]:
        """
        Get tracking information for an issue.
        
        Args:
            issue_hash: Hash of the issue
            
        Returns:
            Issue object or None if not found
        """
        return self.issues.get(issue_hash)
    
    def list_issues(self, classification: Optional[str] = None, status: Optional[str] = None) -> List[Issue]:
        """
        List tracked issues with optional filtering.
        
        Args:
            classification: Filter by classification
            status: Filter by status
            
        Returns:
            List of matching tracked issues
        """
        # First ensure our cache is up to date with the database
        self._load_issues_from_db()
        
        issues = list(self.issues.values())
        
        if classification:
            issues = [i for i in issues if i.classification == classification]
        
        if status:
            issues = [i for i in issues if i.status == status]
        
        return issues
    
    def find_issue_by_location(self, file_path: Path, line: int) -> Optional[str]:
        """
        Find an issue hash by file location.
        
        Args:
            file_path: Path to the file
            line: Line number
            
        Returns:
            Issue hash if found, None otherwise
        """
        # Use database query for better performance
        return self.db.find_issue_by_location(file_path, line)
