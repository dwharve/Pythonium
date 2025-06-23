from datetime import datetime, timezone
from pythonium.models import Issue, Location
from pythonium.mcp.storage.issue_database import IssueDatabase


def make_issue(tmp_path, hash_id='h1'):
    return Issue(
        id='test.id',
        severity='info',
        message='msg',
        location=Location(file=tmp_path / 'f.py', line=1),
        detector_id='det',
        issue_hash=hash_id,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
    )


def test_issue_database_crud(tmp_path):
    db = IssueDatabase(tmp_path)
    issue = make_issue(tmp_path)
    db.upsert_tracked_issue(issue)
    assert db.has_issue('h1')
    data = db.get_tracked_issue('h1')
    assert data['id'] == 'test.id'

    db.update_issue('h1', classification='false_positive', status='completed', notes=['n'])
    updated = db.get_tracked_issue('h1')
    assert updated['classification'] == 'false_positive'
    assert updated['status'] == 'completed'

    issues = db.list_issues()
    assert len(issues) == 1
    stats = db.get_statistics()
    assert stats['total_tracked'] == 1

    found = db.find_issue_by_location(tmp_path / 'f.py', 1)
    assert found == 'h1'

    db.update_issue_timestamp('h1')
    assert db.get_tracked_issue('h1')['last_seen'] is not None

    db.cleanup_stale_issues({'h1'})
    assert db.has_issue('h1')
