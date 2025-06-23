import asyncio
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
async def test_list_and_get_detectors():
    info = {
        "a": {"name": "A", "description": "desc a"},
        "b": {"name": "B", "description": "desc b"},
    }
    server = DummyServer(info, {})
    result = await analysis.list_detectors(server, {})
    text = result[0].text
    assert "Total detectors: 2" in text
    assert "a" in text and "b" in text

    result = await analysis.get_detector_info(server, {"detector_id": "a"})
    assert "Detector: A" in result[0].text

    result = await analysis.get_detector_info(server, {"detector_id": "missing"})
    assert "not found" in result[0].text

@pytest.mark.asyncio
async def test_analyze_issues_filters_and_summary(tmp_path):
    path = tmp_path / "code.py"
    path.write_text("print('hi')")

    issues = [
        Issue(id="i1", severity="info", message="m1", location=Location(file=path, line=1), detector_id="det1"),
        Issue(id="i2", severity="warn", message="m2", location=Location(file=path, line=2), detector_id="det2"),
        Issue(id="i3", severity="error", message="m3", location=Location(file=path, line=3), detector_id="det2"),
    ]
    server = DummyServer({"det1": {"description": "d1"}, "det2": {"description": "d2"}}, {str(path): issues})

    result = await analysis.analyze_issues(server, {"path": str(path), "severity_filter": "warn"})
    text = result[0].text
    assert "Pythonium Analysis Summary" in text
    assert "Issues found" in text
    assert "det2" in text  # detector breakdown present

@pytest.mark.asyncio
async def test_debug_profile_resets():
    server = DummyServer({})
    from pythonium.mcp.utils import debug

    debug.profiler.start_operation("op1")
    debug.profiler.checkpoint("c1")
    debug.profiler.end_operation()

    result = await analysis.debug_profile(server, {"reset": True})
    text = result[0].text
    assert "Profiling" in text and "op1" in text
    assert "reset" in text.lower()
    assert debug.profiler.operations == []
