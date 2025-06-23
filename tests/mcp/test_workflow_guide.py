from pythonium.mcp.utils.workflow import WorkflowGuide
from pythonium.mcp.formatters.data_models import WorkflowStage


def test_assess_issue_complexity():
    guide = WorkflowGuide()
    issue = {
        "detector_id": "security-smell",
        "file_path": "src/auth/login.py",
        "message": "possible security vulnerability"
    }
    assert guide.assess_issue_complexity(issue) == guide.detector_complexity_map["security-smell"]
    simple_issue = {"detector_id": "dead-code", "file_path": "simple.py", "message": "unused"}
    assert guide.assess_issue_complexity(simple_issue) == guide.detector_complexity_map["dead-code"]
    project_context = {"total_issues": 150}
    assert guide.assess_issue_complexity(simple_issue, project_context) != guide.detector_complexity_map["dead-code"]


def test_create_workflow_plan():
    guide = WorkflowGuide()
    issues = [
        {"detector_id": "dead-code", "classification": "unclassified", "status": "pending"},
        {"detector_id": "circular-deps", "classification": "true_positive", "status": "pending"},
    ]
    plan = guide.create_workflow_plan(issues, WorkflowStage.DISCOVERY)
    assert plan.complexity.value in {c.value for c in guide.detector_complexity_map.values()}
    assert WorkflowStage.INVESTIGATION in plan.stages


def test_suggest_and_estimate_and_blockers():
    guide = WorkflowGuide()
    issues = [
        {
            "detector_id": "security-smell",
            "classification": "unclassified",
            "status": "pending",
            "file_path": "auth/app.py"
        },
        {
            "detector_id": "dead-code",
            "classification": "true_positive",
            "status": "pending",
            "file_path": "src/foo.py"
        }
    ]
    suggestions = guide.suggest_next_actions(WorkflowStage.INVESTIGATION, issues)
    assert any(s.action == "classify_investigated" for s in suggestions)
    total, stages = guide.estimate_completion_time(issues, WorkflowStage.RESOLUTION)
    assert "Resolution" in stages
    blockers = guide.identify_blockers(issues)
    assert any("security" in b.lower() for b in blockers)
