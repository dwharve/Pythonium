from pythonium.mcp.tools import definitions


def test_get_tool_definitions_contains_expected():
    tools = definitions.get_tool_definitions()
    assert any(t.name == "analyze_code" for t in tools)
    assert any(t.name == "debug_profile" for t in tools)
