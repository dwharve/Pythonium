"""
Database backend for issue tracking in Pythonium MCP server.

This module provides a SQLite-based issue tracking database that replaces
the previous JSON file-based storage system. It handles storage, retrieval,
and querying of tracked issues and agent actions.
"""

import json
import pickle
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pythonium.models import Issue, Location
from pythonium.database_paths import DatabasePathResolver


logger = logging.getLogger(__name__)


class IssueDatabase:
    """
    SQLite database for persistent issue tracking.
    
    This class manages the database operations for the issue tracking system,
    including table creation, migrations, and CRUD operations for issues
    and agent actions.
    """
    
    DB_VERSION = 1
    
    def __init__(self, project_root: Path):
        """
        Initialize the database.
        
        Args:
            project_root: Root directory of the project being analyzed
        """
        self.project_root = project_root
        # Use centralized path resolver for consistent database location
        self.db_file = DatabasePathResolver.get_issues_db_path(project_root)
        self._init_db()
        
        # Path to legacy JSON file for migration
        self.legacy_file = project_root / ".pythonium" / "issue_tracking.json"
        self._migrate_from_json_if_needed()
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_file) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Version tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS db_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Main issue tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_issues (
                    issue_hash TEXT PRIMARY KEY,
                    classification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    notes TEXT,
                    assigned_to TEXT,
                    suppressed INTEGER NOT NULL DEFAULT 0
                )
            """)
            
            # Original issue data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS original_issues (
                    issue_hash TEXT PRIMARY KEY,
                    id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    detector_id TEXT,
                    metadata BLOB,  -- Pickled metadata
                    file_path TEXT,  -- Path to main file
                    line_number INTEGER,
                    column_number INTEGER,
                    end_line INTEGER,
                    end_column INTEGER,
                    FOREIGN KEY (issue_hash) REFERENCES tracked_issues (issue_hash) ON DELETE CASCADE
                )
            """)
            
            # Related files for multi-file issues
            conn.execute("""
                CREATE TABLE IF NOT EXISTS related_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY (issue_hash) REFERENCES tracked_issues (issue_hash) ON DELETE CASCADE
                )
            """)
            
            # Agent actions history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_hash TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    investigation TEXT,
                    resolution TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (issue_hash) REFERENCES tracked_issues (issue_hash) ON DELETE CASCADE
                )
            """)
            
            # Set version if not exists
            cursor = conn.execute("SELECT value FROM db_info WHERE key = ?", ("version",))
            if not cursor.fetchone():
                conn.execute("INSERT INTO db_info (key, value) VALUES (?, ?)", 
                          ("version", str(self.DB_VERSION)))
            
            conn.commit()
    
    def _migrate_from_json_if_needed(self) -> None:
        """Check for and migrate data from legacy JSON file if needed."""
        if not self.legacy_file.exists():
            return
            
        # Check if we already have data in the DB
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM tracked_issues")
            if cursor.fetchone()[0] > 0:
                # We already have data, skip migration
                return
        
        # Attempt to load and migrate data
        try:
            logger.info("Migrating issue tracking data from JSON to SQLite DB")
            from .issue_tracking import IssueTracker, TrackedIssue
            
            # Create a temporary tracker to load the JSON data
            temp_tracker = IssueTracker(self.project_root)
            
            # Migrate each issue to the database
            for issue_hash, tracked in temp_tracker.tracked_issues.items():
                # Insert main issue data
                self.upsert_tracked_issue(
                    issue_hash=issue_hash,
                    classification=tracked.classification.value,
                    status=tracked.status.value,
                    first_seen=tracked.first_seen,
                    last_seen=tracked.last_seen,
                    notes=tracked.notes,
                    assigned_to=tracked.assigned_to,
                    suppressed=tracked.suppressed,
                    original_issue=tracked.original_issue
                )
                
                # Migrate agent actions
                agent_actions = temp_tracker.get_agent_actions(issue_hash)
                for action in agent_actions:
                    self.add_agent_action(
                        issue_hash=issue_hash,
                        action_type=action.get('action', ''),
                        investigation=action.get('investigation', ''),
                        resolution=action.get('resolution', ''),
                        timestamp=action.get('timestamp', '')
                    )
            
            logger.info(f"Migration complete. Imported {len(temp_tracker.tracked_issues)} issues")
            
        except Exception as e:
            logger.error(f"Error migrating from JSON: {e}")
    
    def upsert_tracked_issue(self, issue_hash: str, classification: str, status: str,
                             first_seen: datetime, last_seen: datetime, notes: str = "",
                             assigned_to: str = "", suppressed: bool = False,
                             original_issue: Optional[Issue] = None) -> None:
        """
        Insert or update a tracked issue.
        
        Args:
            issue_hash: Unique identifier for the issue
            classification: Classification string (e.g., "true_positive")
            status: Status string (e.g., "pending")
            first_seen: When issue was first detected
            last_seen: When issue was last detected
            notes: Additional notes
            assigned_to: Person assigned to the issue
            suppressed: Whether issue is suppressed
            original_issue: Original Issue object
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Insert/update tracked issue
                conn.execute("""
                    INSERT OR REPLACE INTO tracked_issues
                    (issue_hash, classification, status, first_seen, last_seen, notes, assigned_to, suppressed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue_hash,
                    classification,
                    status,
                    first_seen.isoformat(),
                    last_seen.isoformat(),
                    notes,
                    assigned_to,
                    1 if suppressed else 0
                ))
                
                # Handle original issue data if present
                if original_issue:
                    # First delete existing original issue data
                    conn.execute("DELETE FROM original_issues WHERE issue_hash = ?", (issue_hash,))
                    conn.execute("DELETE FROM related_files WHERE issue_hash = ?", (issue_hash,))
                    
                    # Insert new original issue data
                    file_path = None
                    line_number = None
                    column_number = None
                    end_line = None
                    end_column = None
                    
                    if original_issue.location:
                        file_path = str(original_issue.location.file)
                        line_number = original_issue.location.line
                        column_number = original_issue.location.column
                        end_line = original_issue.location.end_line
                        end_column = original_issue.location.end_column
                    
                    conn.execute("""
                        INSERT INTO original_issues
                        (issue_hash, id, severity, message, detector_id, metadata,
                        file_path, line_number, column_number, end_line, end_column)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        issue_hash,
                        original_issue.id,
                        original_issue.severity,
                        original_issue.message,
                        original_issue.detector_id,
                        pickle.dumps(original_issue.metadata) if original_issue.metadata else None,
                        file_path,
                        line_number,
                        column_number,
                        end_line,
                        end_column
                    ))
                    
                    # Insert related files
                    if original_issue.related_files:
                        for file_path in original_issue.related_files:
                            conn.execute("""
                                INSERT INTO related_files (issue_hash, file_path)
                                VALUES (?, ?)
                            """, (issue_hash, str(file_path)))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error upserting tracked issue: {e}")
            raise
    
    def get_tracked_issue(self, issue_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get a tracked issue by hash.
        
        Args:
            issue_hash: Hash of the issue to retrieve
            
        Returns:
            Dictionary with issue data or None if not found
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Query joined data for the issue
                cursor = conn.execute("""
                    SELECT 
                        t.issue_hash, t.classification, t.status, 
                        t.first_seen, t.last_seen, t.notes, t.assigned_to, t.suppressed,
                        o.id, o.severity, o.message, o.detector_id, o.metadata,
                        o.file_path, o.line_number, o.column_number, o.end_line, o.end_column
                    FROM 
                        tracked_issues t
                    LEFT JOIN 
                        original_issues o ON t.issue_hash = o.issue_hash
                    WHERE 
                        t.issue_hash = ?
                """, (issue_hash,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                # Build issue dict
                issue = {
                    "issue_hash": row[0],
                    "classification": row[1],
                    "status": row[2],
                    "first_seen": datetime.fromisoformat(row[3]),
                    "last_seen": datetime.fromisoformat(row[4]),
                    "notes": row[5],
                    "assigned_to": row[6],
                    "suppressed": bool(row[7]),
                }
                
                # Add original issue data if available
                if row[8]:  # If we have an issue ID
                    original_issue = {
                        "id": row[8],
                        "severity": row[9],
                        "message": row[10],
                        "detector_id": row[11],
                        "metadata": pickle.loads(row[12]) if row[12] else {},
                        "location": None,
                        "related_files": []
                    }
                    
                    # Build location
                    if row[13]:  # file_path
                        original_issue["location"] = {
                            "file": row[13],
                            "line": row[14],
                            "column": row[15],
                            "end_line": row[16],
                            "end_column": row[17]
                        }
                    
                    # Get related files
                    cursor = conn.execute("""
                        SELECT file_path FROM related_files
                        WHERE issue_hash = ?
                    """, (issue_hash,))
                    
                    original_issue["related_files"] = [row[0] for row in cursor.fetchall()]
                    issue["original_issue"] = original_issue
                
                return issue
                
        except Exception as e:
            logger.error(f"Error getting tracked issue: {e}")
            return None
    
    def mark_issue(self, issue_hash: str, classification: Optional[str] = None, 
                  status: Optional[str] = None, notes: Optional[str] = None, 
                  assigned_to: Optional[str] = None) -> bool:
        """
        Update issue classification, status, notes, or assignment.
        
        Args:
            issue_hash: Hash of the issue to update
            classification: New classification (or None to leave unchanged)
            status: New status (or None to leave unchanged)
            notes: New notes (or None to leave unchanged)
            assigned_to: New assignment (or None to leave unchanged)
            
        Returns:
            True if issue was found and updated, False otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Check if issue exists
                cursor = conn.execute(
                    "SELECT classification, status, notes, assigned_to, suppressed FROM tracked_issues WHERE issue_hash = ?", 
                    (issue_hash,)
                )
                row = cursor.fetchone()
                if not row:
                    return False
                
                # Use existing values for fields not being updated
                current_classification, current_status, current_notes, current_assigned_to, current_suppressed = row
                
                update_classification = classification if classification is not None else current_classification
                update_status = status if status is not None else current_status
                update_notes = notes if notes is not None else current_notes
                update_assigned_to = assigned_to if assigned_to is not None else current_assigned_to
                
                # Auto-suppress false positives
                update_suppressed = 1 if classification == "false_positive" else current_suppressed
                
                # Update the record
                conn.execute("""
                    UPDATE tracked_issues
                    SET classification = ?, status = ?, notes = ?, assigned_to = ?, suppressed = ?
                    WHERE issue_hash = ?
                """, (
                    update_classification, 
                    update_status, 
                    update_notes, 
                    update_assigned_to,
                    update_suppressed,
                    issue_hash
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error marking issue: {e}")
            return False
    
    def suppress_issue(self, issue_hash: str, suppress: bool = True) -> bool:
        """
        Suppress or unsuppress an issue.
        
        Args:
            issue_hash: Hash of the issue
            suppress: Whether to suppress (True) or unsuppress (False)
            
        Returns:
            True if issue was found and updated, False otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Check if issue exists
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tracked_issues WHERE issue_hash = ?", 
                    (issue_hash,)
                )
                if cursor.fetchone()[0] == 0:
                    return False
                
                # Update suppression status
                conn.execute("""
                    UPDATE tracked_issues
                    SET suppressed = ?
                    WHERE issue_hash = ?
                """, (1 if suppress else 0, issue_hash))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error suppressing issue: {e}")
            return False
    
    def list_issues(self, classification: Optional[str] = None,
                   status: Optional[str] = None,
                   include_suppressed: bool = False) -> List[Dict[str, Any]]:
        """
        List tracked issues with optional filtering.
        
        Args:
            classification: Filter by classification
            status: Filter by status
            include_suppressed: Whether to include suppressed issues
            
        Returns:
            List of matching tracked issues
        """
        issues = []
        
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Build query with filters
                query = """
                    SELECT issue_hash, classification, status, 
                           first_seen, last_seen, notes, assigned_to, suppressed
                    FROM tracked_issues
                    WHERE 1=1
                """
                params = []
                
                if classification:
                    query += " AND classification = ?"
                    params.append(classification)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                if not include_suppressed:
                    query += " AND suppressed = 0"
                
                # Execute query
                cursor = conn.execute(query, params)
                
                # Convert to list of dictionaries
                for row in cursor.fetchall():
                    issue = {
                        "issue_hash": row[0],
                        "classification": row[1],
                        "status": row[2],
                        "first_seen": datetime.fromisoformat(row[3]),
                        "last_seen": datetime.fromisoformat(row[4]),
                        "notes": row[5],
                        "assigned_to": row[6],
                        "suppressed": bool(row[7]),
                    }
                    issues.append(issue)
                
        except Exception as e:
            logger.error(f"Error listing issues: {e}")
        
        return issues
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tracked issues.
        
        Returns:
            Dictionary with various statistics
        """
        stats = {
            "total_tracked": 0,
            "by_classification": {},
            "by_status": {},
            "suppressed": 0,
            "active": 0
        }
        
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Total count
                cursor = conn.execute("SELECT COUNT(*) FROM tracked_issues")
                stats["total_tracked"] = cursor.fetchone()[0]
                
                # Count by classification
                cursor = conn.execute(
                    "SELECT classification, COUNT(*) FROM tracked_issues GROUP BY classification"
                )
                for row in cursor.fetchall():
                    stats["by_classification"][row[0]] = row[1]
                
                # Count by status
                cursor = conn.execute(
                    "SELECT status, COUNT(*) FROM tracked_issues GROUP BY status"
                )
                for row in cursor.fetchall():
                    stats["by_status"][row[0]] = row[1]
                
                # Count suppressed
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tracked_issues WHERE suppressed = 1"
                )
                stats["suppressed"] = cursor.fetchone()[0]
                
                # Active (not suppressed)
                stats["active"] = stats["total_tracked"] - stats["suppressed"]
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
        
        return stats
    
    def find_issue_by_location(self, file_path: Path, line: int) -> Optional[str]:
        """
        Find an issue hash by file location.
        
        Args:
            file_path: Path to the file
            line: Line number
            
        Returns:
            Issue hash if found, None otherwise
        """
        try:
            file_path_str = str(file_path)
            with sqlite3.connect(self.db_file) as conn:
                # Search in original issues first
                cursor = conn.execute("""
                    SELECT issue_hash FROM original_issues
                    WHERE file_path = ? AND line_number = ?
                """, (file_path_str, line))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # Also search in related files
                cursor = conn.execute("""
                    SELECT issue_hash FROM related_files
                    WHERE file_path = ?
                """, (file_path_str,))
                
                # For related files, we'll need to verify the line number
                for row in cursor.fetchall():
                    issue_hash = row[0]
                    cursor2 = conn.execute("""
                        SELECT line_number FROM original_issues
                        WHERE issue_hash = ?
                    """, (issue_hash,))
                    line_row = cursor2.fetchone()
                    if line_row and line_row[0] == line:
                        return issue_hash
                
        except Exception as e:
            logger.error(f"Error finding issue by location: {e}")
        
        return None
    
    def add_agent_action(self, issue_hash: str, action_type: str,
                        investigation: str = "", resolution: str = "",
                        timestamp: Optional[str] = None) -> bool:
        """
        Add an agent action for an issue.
        
        Args:
            issue_hash: Hash of the issue
            action_type: Type of action taken (e.g., "investigated")
            investigation: What the agent found
            resolution: How the agent resolved the issue
            timestamp: Timestamp as string (if None, uses current time)
            
        Returns:
            True if action was added, False otherwise
        """
        try:
            # Check if issue exists
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tracked_issues WHERE issue_hash = ?", 
                    (issue_hash,)
                )
                if cursor.fetchone()[0] == 0:
                    return False
                
                # Use current time if timestamp not provided
                if timestamp is None:
                    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                
                # Insert action
                conn.execute("""
                    INSERT INTO agent_actions
                    (issue_hash, action_type, investigation, resolution, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (issue_hash, action_type, investigation, resolution, timestamp))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding agent action: {e}")
            return False
    
    def get_agent_actions(self, issue_hash: str) -> List[Dict[str, str]]:
        """
        Get agent actions for an issue.
        
        Args:
            issue_hash: Hash of the issue
            
        Returns:
            List of agent action dictionaries
        """
        actions = []
        
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute("""
                    SELECT action_type, investigation, resolution, timestamp
                    FROM agent_actions
                    WHERE issue_hash = ?
                    ORDER BY id ASC  -- Preserve insertion order
                """, (issue_hash,))
                
                for row in cursor.fetchall():
                    action = {
                        'action': row[0],
                        'investigation': row[1] or '',
                        'resolution': row[2] or '',
                        'timestamp': row[3]
                    }
                    actions.append(action)
                
        except Exception as e:
            logger.error(f"Error getting agent actions: {e}")
        
        return actions
    
    def has_issue(self, issue_hash: str) -> bool:
        """
        Check if an issue exists.
        
        Args:
            issue_hash: Hash of the issue
            
        Returns:
            True if issue exists, False otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tracked_issues WHERE issue_hash = ?", 
                    (issue_hash,)
                )
                return cursor.fetchone()[0] > 0
                
        except Exception as e:
            logger.error(f"Error checking if issue exists: {e}")
            return False
    
    def update_issue_timestamp(self, issue_hash: str) -> None:
        """
        Update the last_seen timestamp for an issue.
        
        Args:
            issue_hash: Hash of the issue to update
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    UPDATE tracked_issues
                    SET last_seen = ?
                    WHERE issue_hash = ?
                """, (now, issue_hash))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating issue timestamp: {e}")
    
    def cleanup_stale_issues(self, current_hashes: Set[str]) -> None:
        """
        Remove tracked issues that are no longer detected.
        
        Args:
            current_hashes: Set of issue hashes from current analysis
        """
        if not current_hashes:
            return
            
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Find issues not in current_hashes
                placeholders = ','.join(['?' for _ in current_hashes])
                query = f"""
                    DELETE FROM tracked_issues
                    WHERE issue_hash NOT IN ({placeholders})
                """
                conn.execute(query, list(current_hashes))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error cleaning up stale issues: {e}")
