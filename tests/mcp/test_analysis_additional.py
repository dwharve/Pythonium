import builtins
import importlib
import sys
import types
import pytest

from pythonium.models import Issue, Location
from pythonium.mcp.tools import analysis

class DummyHandlers:
    def __init__(self, results):
        self._analysis_results = results

class DummyServer:
    def __init__(self, detector_info, results=None):
        self._detector_info = detector_info
        self.handlers = DummyHandlers(results or {})
    @property
    def available_detectors(self):
        return list(self._detector_info.keys())

@pytest.mark.asyncio
async def test_analyze_issues_no_previous_results(tmp_path):
    path = tmp_path / "missing.py"
    server = DummyServer({"d": {"description": "desc"}}, {})
    result = await analysis.analyze_issues(server, {"path": str(path)})
    text = result[0].text
    assert "No paths have been analyzed yet" in text

@pytest.mark.asyncio
async def test_analyze_issues_no_issues_after_filter(tmp_path):
    path = tmp_path / "code.py"
    path.write_text("print('hi')")
    issues = [Issue(id="i", severity="info", message="m", location=Location(file=path, line=1), detector_id="d")]
    server = DummyServer({"d": {"description": "d"}}, {str(path): issues})
    result = await analysis.analyze_issues(server, {"path": str(path), "severity_filter": "error"})
    text = result[0].text
    assert "No issues found" in text
    assert "Total issues in analysis: 1" in text

@pytest.mark.asyncio
async def test_analyze_issues_match_by_filename(tmp_path):
    analyzed_path = tmp_path / "existing.py"
    analyzed_path.write_text("print('hi')")
    issues = [Issue(id="i", severity="warn", message="m", location=Location(file=analyzed_path, line=1), detector_id="circular" )]
    server = DummyServer({"circular": {"description": "circular check"}}, {str(analyzed_path): issues})
    query_path = tmp_path / "subdir" / "existing.py"
    result = await analysis.analyze_issues(server, {"path": str(query_path)})
    text = result[0].text
    assert "Pythonium Analysis Summary" in text
    assert "circular" in text


def test_get_tool_definitions_missing_mcp(monkeypatch):
    import pythonium.mcp.tools.definitions as definitions
    original_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == "mcp.types":
            raise ImportError
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    importlib.reload(definitions)
    try:
        assert definitions.MCP_AVAILABLE is False
        assert definitions.get_tool_definitions() == []
    finally:
        monkeypatch.setattr(builtins, "__import__", original_import)
        importlib.reload(definitions)
