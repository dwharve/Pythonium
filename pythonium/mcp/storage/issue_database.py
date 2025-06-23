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
                    id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    detector_id TEXT,
                    metadata BLOB,
                    file_path TEXT,
                    line_number INTEGER,
                    column_number INTEGER,
                    end_line INTEGER,
                    end_column INTEGER,
                    classification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
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
    
    def upsert_tracked_issue(self, issue: Issue) -> None:
        """
        Insert or update a tracked issue.
        
        Args:
            issue: The Issue object to store
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Convert notes list to JSON string for storage
                notes_json = json.dumps(issue.notes) if issue.notes else "[]"
                
                # Prepare location data
                file_path = str(issue.location.file) if issue.location else None
                line_number = issue.location.line if issue.location else None
                column_number = issue.location.column if issue.location else None
                end_line = issue.location.end_line if issue.location else None
                end_column = issue.location.end_column if issue.location else None
                
                # Insert/update tracked issue
                conn.execute("""
                    INSERT OR REPLACE INTO tracked_issues
                    (issue_hash, id, severity, message, detector_id, metadata, 
                     file_path, line_number, column_number, end_line, end_column,
                     classification, status, notes, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue.issue_hash,
                    issue.id,
                    issue.severity,
                    issue.message,
                    issue.detector_id,
                    pickle.dumps(issue.metadata) if issue.metadata else None,
                    file_path,
                    line_number,
                    column_number,
                    end_line,
                    end_column,
                    issue.classification,
                    issue.status,
                    notes_json,
                    issue.first_seen.isoformat() if issue.first_seen else None,
                    issue.last_seen.isoformat() if issue.last_seen else None
                ))
                
                # Handle related files
                if issue.related_files:
                    # First delete existing related files
                    conn.execute("DELETE FROM related_files WHERE issue_hash = ?", (issue.issue_hash,))
                    
                    # Insert new related files
                    for file_path in issue.related_files:
                        conn.execute("""
                            INSERT INTO related_files (issue_hash, file_path)
                            VALUES (?, ?)
                        """, (issue.issue_hash, str(file_path)))
                
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
                cursor = conn.execute("""
                    SELECT 
                        issue_hash, id, severity, message, detector_id, metadata,
                        file_path, line_number, column_number, end_line, end_column,
                        classification, status, notes, first_seen, last_seen
                    FROM 
                        tracked_issues
                    WHERE 
                        issue_hash = ?
                """, (issue_hash,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                # Build issue dict
                issue = {
                    "issue_hash": row[0],
                    "id": row[1],
                    "severity": row[2],
                    "message": row[3],
                    "detector_id": row[4],
                    "metadata": pickle.loads(row[5]) if row[5] else {},
                    "file_path": row[6],
                    "line_number": row[7],
                    "column_number": row[8],
                    "end_line": row[9],
                    "end_column": row[10],
                    "classification": row[11],
                    "status": row[12],
                    "notes": json.loads(row[13]) if row[13] else [],
                    "first_seen": row[14],
                    "last_seen": row[15],
                }
                
                # Get related files
                cursor = conn.execute("""
                    SELECT file_path FROM related_files
                    WHERE issue_hash = ?
                """, (issue_hash,))
                
                issue["related_files"] = [row[0] for row in cursor.fetchall()]
                
                return issue
                
        except Exception as e:
            logger.error(f"Error getting tracked issue: {e}")
            return None
    
    def update_issue(self, issue_hash: str, classification: Optional[str] = None, 
                    status: Optional[str] = None, severity: Optional[str] = None,
                    message: Optional[str] = None, notes: Optional[List[str]] = None) -> bool:
        """
        Update issue classification, status, severity, message, or notes.
        
        Args:
            issue_hash: Hash of the issue to update
            classification: New classification (or None to leave unchanged)
            status: New status (or None to leave unchanged)
            severity: New severity (or None to leave unchanged)
            message: New message (or None to leave unchanged)
            notes: New notes list (or None to leave unchanged)
            
        Returns:
            True if issue was found and updated, False otherwise
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Check if issue exists and get current values
                cursor = conn.execute(
                    "SELECT classification, status, severity, message, notes FROM tracked_issues WHERE issue_hash = ?", 
                    (issue_hash,)
                )
                row = cursor.fetchone()
                if not row:
                    return False
                
                # Use existing values for fields not being updated
                current_classification, current_status, current_severity, current_message, current_notes = row
                
                update_classification = classification if classification is not None else current_classification
                update_status = status if status is not None else current_status
                update_severity = severity if severity is not None else current_severity
                update_message = message if message is not None else current_message
                update_notes = json.dumps(notes) if notes is not None else current_notes
                
                # Update the record
                conn.execute("""
                    UPDATE tracked_issues
                    SET classification = ?, status = ?, severity = ?, message = ?, notes = ?
                    WHERE issue_hash = ?
                """, (
                    update_classification, 
                    update_status, 
                    update_severity,
                    update_message,
                    update_notes,
                    issue_hash
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating issue: {e}")
            return False
    
    def list_issues(self, classification: Optional[str] = None,
                   status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List tracked issues with optional filtering.
        
        Args:
            classification: Filter by classification
            status: Filter by status
            
        Returns:
            List of matching tracked issues
        """
        issues = []
        
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Build query with filters
                query = """
                    SELECT issue_hash, id, severity, message, detector_id, metadata,
                           file_path, line_number, column_number, end_line, end_column,
                           classification, status, notes, first_seen, last_seen
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
                
                # Execute query
                cursor = conn.execute(query, params)
                
                # Convert to list of dictionaries
                for row in cursor.fetchall():
                    issue = {
                        "issue_hash": row[0],
                        "id": row[1],
                        "severity": row[2],
                        "message": row[3],
                        "detector_id": row[4],
                        "metadata": pickle.loads(row[5]) if row[5] else {},
                        "file_path": row[6],
                        "line_number": row[7],
                        "column_number": row[8],
                        "end_line": row[9],
                        "end_column": row[10],
                        "classification": row[11],
                        "status": row[12],
                        "notes": json.loads(row[13]) if row[13] else [],
                        "first_seen": row[14],
                        "last_seen": row[15],
                    }
                    
                    # Get related files
                    cursor2 = conn.execute("""
                        SELECT file_path FROM related_files
                        WHERE issue_hash = ?
                    """, (row[0],))
                    issue["related_files"] = [r[0] for r in cursor2.fetchall()]
                    
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
            "by_severity": {}
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
                
                # Count by severity
                cursor = conn.execute(
                    "SELECT severity, COUNT(*) FROM tracked_issues GROUP BY severity"
                )
                for row in cursor.fetchall():
                    stats["by_severity"][row[0]] = row[1]
                
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
                # Search in tracked issues
                cursor = conn.execute("""
                    SELECT issue_hash FROM tracked_issues
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
                        SELECT line_number FROM tracked_issues
                        WHERE issue_hash = ?
                    """, (issue_hash,))
                    line_row = cursor2.fetchone()
                    if line_row and line_row[0] == line:
                        return issue_hash
                
        except Exception as e:
            logger.error(f"Error finding issue by location: {e}")
        
        return None
    
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
