from pythonium.mcp.formatters.statistics_formatter import StatisticsFormatter


def test_statistics_formatter_basic():
    stats = {
        'total_tracked': 2,
        'active': 1,
        'suppressed': 0,
        'by_classification': {'unclassified': 1},
        'by_status': {'pending': 2}
    }
    fmt = StatisticsFormatter()
    res = fmt.format_tracking_statistics(stats, project_path='p')
    assert 'Issue tracking statistics' in res.message
    assert res.workflow_context.current_stage == res.workflow_context.current_stage.__class__.CLASSIFICATION
