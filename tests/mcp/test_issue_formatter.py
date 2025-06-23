from pythonium.mcp.formatters.issue_formatter import IssueFormatter


def test_issue_formatter_mark_and_list():
    fmt = IssueFormatter()
    res = fmt.format_issue_marked('h', 'true_positive', 'pending', 'note')
    assert 'Issue h marked' in res.message
    res_list = fmt.format_tracked_issues([
        {'classification': 'unclassified', 'status': 'pending'},
        {'classification': 'true_positive', 'status': 'work_in_progress'},
    ])
    assert 'Found 2 tracked issues' in res_list.message
    res_info = fmt.format_issue_info(
        {
            'classification': 'true_positive',
            'status': 'pending',
            'original_issue': {'id': 'x'}
        },
        'h'
    )
    assert res_info.metadata['issue_hash'] == 'h'
