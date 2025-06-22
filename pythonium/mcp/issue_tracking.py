"""
Issue tracking system for Pythonium MCP server.

This module provides persistent issue tracking functionality that allows marking
issues as true/false positives, tracking their status, and maintaining state
across analyze_code runs. Storage is handled via SQLite database for reliability
and improved performance.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

from pythonium.models import Issue, Location
from .issue_db import IssueDatabase


class IssueStatus(Enum):
    """Status of an issue in the tracking system."""
    PENDING = "pending"
    WORK_IN_PROGRESS = "work_in_progress"
    COMPLETED = "completed"


class IssueClassification(Enum):
    """Classification of an issue."""
    UNCLASSIFIED = "unclassified"
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"


@dataclass
class TrackedIssue:
    """
    A tracked issue with additional metadata for issue tracking.
    
    Attributes:
        issue_hash: Unique hash identifying this issue
        classification: Whether this is a true/false positive
        status: Current status of the issue
        first_seen: When this issue was first detected
        last_seen: When this issue was last detected
        notes: User notes about this issue
        assigned_to: Person assigned to work on this issue
        original_issue: The original Issue object
        suppressed: Whether this issue should be suppressed from output
    """
    issue_hash: str
    classification: IssueClassification
    status: IssueStatus
    first_seen: datetime
    last_seen: datetime
    notes: str = ""
    assigned_to: str = ""
    original_issue: Optional[Issue] = None
    suppressed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "issue_hash": self.issue_hash,
            "classification": self.classification.value,
            "status": self.status.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "notes": self.notes,
            "assigned_to": self.assigned_to,
            "suppressed": self.suppressed
        }
        
        # Store original issue data (without circular references)
        if self.original_issue:
            result["original_issue"] = {
                "id": self.original_issue.id,
                "severity": self.original_issue.severity,
                "message": self.original_issue.message,
                "detector_id": self.original_issue.detector_id,
                "metadata": self.original_issue.metadata,
                "location": {
                    "file": str(self.original_issue.location.file) if self.original_issue.location else None,
                    "line": self.original_issue.location.line if self.original_issue.location else None,
                    "column": self.original_issue.location.column if self.original_issue.location else None,
                    "end_line": self.original_issue.location.end_line if self.original_issue.location else None,
                    "end_column": self.original_issue.location.end_column if self.original_issue.location else None,
                } if self.original_issue.location else None,
                "related_files": [str(f) for f in self.original_issue.related_files]
            }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackedIssue":
        """Create TrackedIssue from dictionary."""
        # Parse dates
        first_seen = datetime.fromisoformat(data["first_seen"])
        last_seen = datetime.fromisoformat(data["last_seen"])
        
        # Reconstruct original issue
        original_issue = None
        if "original_issue" in data and data["original_issue"]:
            issue_data = data["original_issue"]
            location = None
            if issue_data.get("location"):
                loc_data = issue_data["location"]
                location = Location(
                    file=Path(loc_data["file"]) if loc_data["file"] else Path("unknown"),
                    line=loc_data.get("line", 1),
                    column=loc_data.get("column", 0),
                    end_line=loc_data.get("end_line"),
                    end_column=loc_data.get("end_column")
                )
            
            original_issue = Issue(
                id=issue_data["id"],
                severity=issue_data["severity"],
                message=issue_data["message"],
                detector_id=issue_data.get("detector_id"),
                metadata=issue_data.get("metadata", {}),
                location=location,
                related_files=[Path(f) for f in issue_data.get("related_files", [])]
            )
        
        return cls(
            issue_hash=data["issue_hash"],
            classification=IssueClassification(data["classification"]),
            status=IssueStatus(data["status"]),
            first_seen=first_seen,
            last_seen=last_seen,
            notes=data.get("notes", ""),
            assigned_to=data.get("assigned_to", ""),
            original_issue=original_issue,
            suppressed=data.get("suppressed", False)
        )


class IssueTracker:
    """
    Persistent issue tracking system for Pythonium analysis.
    
    This class manages the lifecycle of issues, tracks their status,
    and provides functionality to mark issues as true/false positives.
    Storage is backed by a SQLite database for durability and performance.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize the issue tracker.
        
        Args:
            project_root: Root directory of the project being analyzed
        """
        self.project_root = project_root
        # Keep reference to legacy file path for backward compatibility
        self.tracking_file = project_root / ".pythonium" / "issue_tracking.json"
        
        # In-memory cache of tracked issues
        self.tracked_issues: Dict[str, TrackedIssue] = {}
        
        # Initialize database
        self.db = IssueDatabase(project_root)
        
        # Load issues from database into memory
        self._load_issues_from_db()
    
    def _load_issues_from_db(self) -> None:
        """Load all tracked issues from the database into memory."""
        self.tracked_issues.clear()
        
        try:
            # Get all raw issue data from database without any filters
            import sqlite3
            with sqlite3.connect(self.db.db_file) as conn:
                cursor = conn.cursor()
                
                # Get basic tracked issue data
                cursor.execute("""
                    SELECT issue_hash, classification, status, 
                           first_seen, last_seen, notes, assigned_to, suppressed
                    FROM tracked_issues
                """)
                
                tracked_rows = cursor.fetchall()
                
                for row in tracked_rows:
                    issue_hash, classification, status, first_seen, last_seen, notes, assigned_to, suppressed = row
                    
                    # Get original issue data
                    cursor.execute("""
                        SELECT id, severity, message, detector_id, metadata, 
                               file_path, line_number, column_number, end_line, end_column
                        FROM original_issues 
                        WHERE issue_hash = ?
                    """, (issue_hash,))
                    
                    original_row = cursor.fetchone()
                    original_issue = None
                    
                    if original_row:
                        (orig_id, severity, message, detector_id, metadata_blob, 
                         file_path, line_number, column_number, end_line, end_column) = original_row
                        
                        # Deserialize metadata
                        metadata = {}
                        if metadata_blob:
                            import pickle
                            try:
                                metadata = pickle.loads(metadata_blob)
                            except:
                                metadata = {}
                        
                        # Create location if file_path exists
                        location = None
                        if file_path:
                            from pathlib import Path
                            location = Location(
                                file=Path(file_path),
                                line=line_number or 1,
                                column=column_number or 0,
                                end_line=end_line,
                                end_column=end_column
                            )
                        
                        # Create original issue
                        from pythonium.models import Issue
                        original_issue = Issue(
                            id=orig_id,
                            severity=severity,
                            message=message,
                            detector_id=detector_id,
                            metadata=metadata,
                            location=location,
                            related_files=[]  # TODO: load related files if needed
                        )
                    
                    # Create TrackedIssue
                    from datetime import datetime
                    tracked_issue = TrackedIssue(
                        issue_hash=issue_hash,
                        classification=IssueClassification(classification),
                        status=IssueStatus(status),
                        first_seen=datetime.fromisoformat(first_seen),
                        last_seen=datetime.fromisoformat(last_seen),
                        notes=notes or "",
                        assigned_to=assigned_to or "",
                        original_issue=original_issue,
                        suppressed=bool(suppressed)
                    )
                    
                    self.tracked_issues[issue_hash] = tracked_issue
                    
        except Exception as e:
            # Import debug here to avoid circular imports
            try:
                from .debug import error_log
                error_log(f"Error loading issues from database: {str(e)}")
            except:
                # Fallback if debug import fails
                print(f"Error loading issues from database: {str(e)}")
            # Continue with empty tracked_issues if loading fails
    
    def _ensure_tracking_dir(self) -> None:
        """Ensure the tracking directory exists."""
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _generate_issue_hash(self, issue: Issue) -> str:
        """
        Generate a unique hash for an issue based on its identifying characteristics.
        
        This hash should be stable across runs for the same logical issue,
        even if some metadata changes.
        
        Args:
            issue: The issue to generate a hash for
            
        Returns:
            A unique hash string for the issue
        """
        # Use characteristics that identify the logical issue
        hash_components = [
            issue.detector_id or "unknown",
            issue.id,
            str(issue.location.file) if issue.location else "no-file",
            str(issue.location.line) if issue.location else "no-line",
            # Include message as it often contains the specific symbol/construct
            issue.message[:200],  # Truncate to avoid huge hashes
        ]
        
        # Add key metadata that affects issue identity
        if issue.metadata:
            # Sort keys for consistent hashing
            for key in sorted(issue.metadata.keys()):
                if key in ["symbol_name", "function_name", "class_name", "variable_name"]:
                    hash_components.append(f"{key}:{issue.metadata[key]}")
        
        # Create hash
        hash_string = "|".join(str(c) for c in hash_components)
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
    
    def _load_issues_from_db(self) -> None:
        """Load issues from the database into the in-memory cache."""
        # Clear current cache
        self.tracked_issues.clear()
        
        # Get all issues from database
        issues = self.db.list_issues(include_suppressed=True)
        
        for issue_data in issues:
            issue_hash = issue_data["issue_hash"]
            
            # Get full issue data including original issue
            full_data = self.db.get_tracked_issue(issue_hash)
            if not full_data:
                continue
            
            # Reconstruct original issue if available
            original_issue = None
            if "original_issue" in full_data and full_data["original_issue"]:
                issue_data = full_data["original_issue"]
                location = None
                
                if "location" in issue_data and issue_data["location"]:
                    loc_data = issue_data["location"]
                    location = Location(
                        file=Path(loc_data["file"]) if loc_data["file"] else Path("unknown"),
                        line=loc_data.get("line", 1),
                        column=loc_data.get("column", 0),
                        end_line=loc_data.get("end_line"),
                        end_column=loc_data.get("end_column")
                    )
                
                original_issue = Issue(
                    id=issue_data["id"],
                    severity=issue_data["severity"],
                    message=issue_data["message"],
                    detector_id=issue_data.get("detector_id"),
                    metadata=issue_data.get("metadata", {}),
                    location=location,
                    related_files=[Path(f) for f in issue_data.get("related_files", [])]
                )
            
            # Create TrackedIssue object
            tracked = TrackedIssue(
                issue_hash=issue_hash,
                classification=IssueClassification(full_data["classification"]),
                status=IssueStatus(full_data["status"]),
                first_seen=full_data["first_seen"],
                last_seen=full_data["last_seen"],
                notes=full_data.get("notes", ""),
                assigned_to=full_data.get("assigned_to", ""),
                original_issue=original_issue,
                suppressed=full_data["suppressed"]
            )
            
            self.tracked_issues[issue_hash] = tracked
    
    def process_new_issues(self, issues: List[Issue]) -> List[Issue]:
        """
        Process a list of new issues from an analysis run.
        
        This method:
        1. Updates existing tracked issues' last_seen timestamp
        2. Creates new tracked issues for previously unseen issues
        3. Filters out suppressed issues from the returned list
        
        Args:
            issues: List of issues from current analysis
            
        Returns:
            List of issues that should be reported (excluding suppressed ones)
        """
        now = datetime.now(timezone.utc)
        current_hashes = set()
        filtered_issues = []
        
        for issue in issues:
            issue_hash = self._generate_issue_hash(issue)
            current_hashes.add(issue_hash)
            
            if issue_hash in self.tracked_issues:
                # Update existing tracked issue
                tracked = self.tracked_issues[issue_hash]
                tracked.last_seen = now
                tracked.original_issue = issue  # Update with latest data
                
                # Update in database
                self.db.upsert_tracked_issue(
                    issue_hash=issue_hash,
                    classification=tracked.classification.value,
                    status=tracked.status.value,
                    first_seen=tracked.first_seen,
                    last_seen=tracked.last_seen,
                    notes=tracked.notes,
                    assigned_to=tracked.assigned_to,
                    suppressed=tracked.suppressed,
                    original_issue=issue
                )
                
                # Only include in output if not suppressed
                if not tracked.suppressed:
                    filtered_issues.append(issue)
            else:
                # Create new tracked issue
                tracked = TrackedIssue(
                    issue_hash=issue_hash,
                    classification=IssueClassification.UNCLASSIFIED,
                    status=IssueStatus.PENDING,
                    first_seen=now,
                    last_seen=now,
                    original_issue=issue
                )
                self.tracked_issues[issue_hash] = tracked
                
                # Save to database
                self.db.upsert_tracked_issue(
                    issue_hash=issue_hash,
                    classification=tracked.classification.value,
                    status=tracked.status.value,
                    first_seen=tracked.first_seen,
                    last_seen=tracked.last_seen,
                    notes=tracked.notes,
                    assigned_to=tracked.assigned_to,
                    suppressed=tracked.suppressed,
                    original_issue=issue
                )
                
                # Include in output (new issues are not suppressed by default)
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
        stale_hashes = set(self.tracked_issues.keys()) - current_hashes
        for hash_to_remove in stale_hashes:
            del self.tracked_issues[hash_to_remove]
        
        # Clean up database
        self.db.cleanup_stale_issues(current_hashes)
    
    def mark_issue(self, issue_hash: str, classification: IssueClassification, 
                  status: Optional[IssueStatus] = None, notes: str = "", 
                  assigned_to: str = "") -> bool:
        """
        Mark an issue with classification and status.
        
        Args:
            issue_hash: Hash of the issue to mark
            classification: True positive, false positive, etc.
            status: Optional status update
            notes: Optional notes about the issue
            assigned_to: Optional person assigned to the issue
            
        Returns:
            True if the issue was found and updated, False otherwise
        """
        if issue_hash not in self.tracked_issues:
            return False
        
        tracked = self.tracked_issues[issue_hash]
        tracked.classification = classification
        
        if status is not None:
            tracked.status = status
        
        if notes:
            tracked.notes = notes
        
        if assigned_to:
            tracked.assigned_to = assigned_to
        
        # Auto-suppress false positives
        if classification == IssueClassification.FALSE_POSITIVE:
            tracked.suppressed = True
        
        # Update in database
        updated = self.db.mark_issue(
            issue_hash=issue_hash,
            classification=tracked.classification.value,
            status=tracked.status.value if status else None,
            notes=notes if notes else None,
            assigned_to=assigned_to if assigned_to else None
        )
        
        # If false positive, update suppression status
        if classification == IssueClassification.FALSE_POSITIVE:
            self.db.suppress_issue(issue_hash, True)
        
        return updated
    
    def suppress_issue(self, issue_hash: str, suppress: bool = True) -> bool:
        """
        Suppress or unsuppress an issue.
        
        Args:
            issue_hash: Hash of the issue
            suppress: Whether to suppress (True) or unsuppress (False)
            
        Returns:
            True if the issue was found and updated, False otherwise
        """
        if issue_hash not in self.tracked_issues:
            return False
        
        # Update in-memory cache
        self.tracked_issues[issue_hash].suppressed = suppress
        
        # Update in database
        return self.db.suppress_issue(issue_hash, suppress)
    
    def get_issue_info(self, issue_hash: str) -> Optional[TrackedIssue]:
        """
        Get tracking information for an issue.
        
        Args:
            issue_hash: Hash of the issue
            
        Returns:
            TrackedIssue object or None if not found
        """
        # Use in-memory cache for better performance
        if issue_hash in self.tracked_issues:
            return self.tracked_issues.get(issue_hash)
        
        # If not in cache, try from database (this will update cache)
        issue_data = self.db.get_tracked_issue(issue_hash)
        if issue_data:
            # Parse from database and add to cache
            self._load_issues_from_db()
            return self.tracked_issues.get(issue_hash)
        
        return None
    
    def list_issues(self, classification: Optional[IssueClassification] = None,
                   status: Optional[IssueStatus] = None,
                   include_suppressed: bool = False) -> List[TrackedIssue]:
        """
        List tracked issues with optional filtering.
        
        Args:
            classification: Filter by classification
            status: Filter by status
            include_suppressed: Whether to include suppressed issues
            
        Returns:
            List of matching tracked issues
        """
        # First ensure our cache is up to date with the database
        self._load_issues_from_db()
        
        issues = list(self.tracked_issues.values())
        
        if classification is not None:
            issues = [i for i in issues if i.classification == classification]
        
        if status is not None:
            issues = [i for i in issues if i.status == status]
        
        if not include_suppressed:
            issues = [i for i in issues if not i.suppressed]
        
        return issues
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked issues.
        
        Returns:
            Dictionary with various statistics
        """
        # Use database statistics for better performance and accuracy
        return self.db.get_statistics()
    
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
    
    def add_agent_note(self, issue_hash: str, agent_action: str, investigation_details: str = "", resolution_details: str = "") -> bool:
        """
        Add an agent-generated note to an issue for tracking agent work.
        
        Args:
            issue_hash: Hash of the issue
            agent_action: Type of action taken (e.g., "investigated", "fixed", "classified")
            investigation_details: What the agent found when investigating
            resolution_details: What the agent did to address the issue
            
        Returns:
            True if the note was added successfully, False if issue not found
        """
        if issue_hash not in self.tracked_issues:
            return False
        
        tracked = self.tracked_issues[issue_hash]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Create formatted agent note for backward compatibility in notes field
        agent_note_parts = [f"[AGENT ACTION - {timestamp}]"]
        agent_note_parts.append(f"Action: {agent_action}")
        
        if investigation_details:
            agent_note_parts.append(f"Investigation: {investigation_details}")
        
        if resolution_details:
            agent_note_parts.append(f"Resolution: {resolution_details}")
        
        new_note = "\n".join(agent_note_parts)
        
        # Append to existing notes in memory
        if tracked.notes:
            tracked.notes = f"{tracked.notes}\n\n{new_note}"
        else:
            tracked.notes = new_note
        
        # Add to database - first update the notes field for compatibility
        self.db.mark_issue(issue_hash, notes=tracked.notes)
        
        # Then add the structured agent action
        result = self.db.add_agent_action(
            issue_hash=issue_hash,
            action_type=agent_action,
            investigation=investigation_details,
            resolution=resolution_details,
            timestamp=timestamp
        )
        
        return result
    
    def get_agent_actions(self, issue_hash: str) -> List[Dict[str, str]]:
        """
        Get agent actions for an issue.
        
        Args:
            issue_hash: Hash of the issue
            
        Returns:
            List of agent action dictionaries with timestamps
        """
        # Use database for better performance and structured data
        return self.db.get_agent_actions(issue_hash)
