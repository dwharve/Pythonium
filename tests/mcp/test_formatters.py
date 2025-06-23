import asyncio
from pythonium.models import Issue, Location
from pythonium.mcp.formatters.analysis_formatter import AnalysisFormatter
from pythonium.mcp.formatters.agent_formatter import AgentFormatter
from pythonium.mcp.formatters.text_converter import TextConverter
from pythonium.mcp.formatters.data_models import ResponseData, ResponseType, WorkflowStage, WorkflowContext, ActionSuggestion


def test_analysis_formatter_and_text_converter(tmp_path):
    formatter = AnalysisFormatter()
    issue = Issue(
        id="i1",
        severity="warn",
        message="problem",
        location=Location(file=tmp_path / "f.py", line=1),
        detector_id="det1",
    )
    result = formatter.format_analysis_results([issue], str(tmp_path), tracked_count=1)
    assert result.type == ResponseType.SUCCESS
    assert "Found 1 code health issues" in result.message
    text = TextConverter.to_text_content(result)
    assert "Workflow Status" in text.text
    assert "Mark issues" in text.text


async def _async_agent_calls(issue_hash):
    formatter = AgentFormatter()
    note = formatter.format_agent_note_added(issue_hash, "investigated", "details", "res")
    actions = formatter.format_agent_actions([{"action": "investigated"}], issue_hash)
    complete = formatter.format_investigation_complete(issue_hash, "det", "finding")
    return note, actions, complete


def test_agent_formatter_async():
    note, actions, complete = asyncio.run(_async_agent_calls("h"))
    assert note.workflow_context.current_stage == WorkflowStage.INVESTIGATION
    assert actions.metadata["action_count"] == 1
    assert "investigation completed".split()[0] in TextConverter.to_text_content(complete).text.lower()
