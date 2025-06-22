"""
Test module for SQLite-backed issue tracking system.

This module provides end-to-end testing for the database-backed
issue tracking functionality.
"""

import os
import shutil
import tempfile
from pathlib import Path

from pythonium.models import Issue, Location
from pythonium.mcp.issue_tracking import IssueTracker, IssueClassification, IssueStatus
from pythonium.mcp.issue_db import IssueDatabase


def test_issue_tracking():
    """Test the database-backed issue tracking system."""
    # Create a temporary directory for testing
    test_dir = Path(tempfile.mkdtemp())
    try:
        # Create a test issue tracker
        tracker = IssueTracker(test_dir)
        
        # Create test issues
        test_issues = [
            Issue(
                id="test.unused_import",
                severity="warn",
                message="Unused import 'os'",
                location=Location(
                    file=Path("test.py"),
                    line=10,
                    column=1
                ),
                detector_id="dead_code"
            ),
            Issue(
                id="test.complex_function",
                severity="error",
                message="Function is too complex",
                location=Location(
                    file=Path("test.py"),
                    line=20,
                    column=1
                ),
                detector_id="complexity"
            )
        ]
        
        # Process issues
        processed_issues = tracker.process_new_issues(test_issues)
        assert len(processed_issues) == 2, "Expected 2 processed issues"
        
        # List issues
        tracked_issues = tracker.list_issues()
        assert len(tracked_issues) == 2, "Expected 2 tracked issues"
        
        # Get issue hashes
        issue_hashes = [i.issue_hash for i in tracked_issues]
        
        # Test marking an issue
        tracker.mark_issue(
            issue_hash=issue_hashes[0],
            classification=IssueClassification.FALSE_POSITIVE,
            status=IssueStatus.COMPLETED,
            notes="This is a test note",
            assigned_to="test_user"
        )
        
        # Verify marking worked
        info = tracker.get_issue_info(issue_hashes[0])
        assert info is not None, "Expected issue info to be found"
        assert info.classification == IssueClassification.FALSE_POSITIVE, "Expected FALSE_POSITIVE classification"
        assert info.status == IssueStatus.COMPLETED, "Expected COMPLETED status"
        assert info.notes == "This is a test note", "Expected note to be set"
        assert info.assigned_to == "test_user", "Expected assigned_to to be set"
        assert info.suppressed, "Expected suppressed to be True for FALSE_POSITIVE"
        
        # Test adding agent note
        tracker.add_agent_note(
            issue_hash=issue_hashes[1],
            agent_action="investigated",
            investigation_details="Found the issue in the code",
            resolution_details="Fixed by simplifying the function"
        )
        
        # Verify agent notes were added
        actions = tracker.get_agent_actions(issue_hashes[1])
        assert len(actions) == 1, "Expected 1 agent action"
        assert actions[0]['action'] == "investigated", "Expected 'investigated' action"
        
        # Test statistics
        stats = tracker.get_statistics()
        assert stats["total_tracked"] == 2, "Expected 2 total tracked issues"
        assert stats["by_classification"].get("false_positive") == 1, "Expected 1 false positive"
        assert stats["by_classification"].get("unclassified") == 1, "Expected 1 unclassified"
        assert stats["suppressed"] == 1, "Expected 1 suppressed issue"
        
        # Test suppressing an issue
        tracker.suppress_issue(issue_hashes[1], True)
        
        # Verify suppression worked
        info = tracker.get_issue_info(issue_hashes[1])
        assert info.suppressed, "Expected issue to be suppressed"
        
        # Test unsuppressing an issue
        tracker.suppress_issue(issue_hashes[1], False)
        
        # Verify unsuppression worked
        info = tracker.get_issue_info(issue_hashes[1])
        assert not info.suppressed, "Expected issue to be unsuppressed"
        
        # Test finding issue by location
        found_hash = tracker.find_issue_by_location(Path("test.py"), 20)
        assert found_hash == issue_hashes[1], "Expected to find issue by location"
        
        # Test reloading from database (creating a new tracker)
        tracker2 = IssueTracker(test_dir)
        tracked_issues2 = tracker2.list_issues()
        assert len(tracked_issues2) == 1, "Expected 1 tracked issue (1 suppressed)"
        
        # Include suppressed issues
        tracked_issues2 = tracker2.list_issues(include_suppressed=True)
        assert len(tracked_issues2) == 2, "Expected 2 tracked issues when including suppressed"
        
        print("All issue tracking tests passed!")
        return True
        
    finally:
        # Clean up test directory
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_issue_tracking()
