from datetime import datetime
from unittest.mock import Mock

import pytest

from pythonium.core.tools.registry import ToolRegistry, ToolStatus
from pythonium.tools.base import BaseTool, ToolMetadata


class SimpleTool(BaseTool):
    @property
    def metadata(self):
        return ToolMetadata(
            name="simple",
            description="Simple tool",
            category="test",
        )

    async def execute(self, params, context):
        return {}


class AnotherTool(SimpleTool):
    @property
    def metadata(self):
        return ToolMetadata(
            name="another",
            description="Another tool",
            category="test",
            version="2.0.0",
        )


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool_id = registry.register_tool(SimpleTool)
        assert registry.has_tool(tool_id)
        reg = registry.get_tool(tool_id)
        assert reg.name == "simple"
        assert reg.version == "1.0.0"

    def test_duplicate_registration_version(self):
        registry = ToolRegistry()
        registry.register_tool(SimpleTool)
        with pytest.raises(Exception):
            registry.register_tool(SimpleTool)

    def test_alias_and_status_and_usage(self):
        registry = ToolRegistry()
        tool_id = registry.register_tool(SimpleTool)
        assert registry.add_alias("alias", tool_id)
        assert registry.get_tool("alias").tool_id == tool_id
        assert registry.update_tool_status(tool_id, ToolStatus.ACTIVE)
        registry.record_tool_usage(tool_id)
        assert registry.get_tool(tool_id).usage_count == 1
        assert registry.remove_alias("alias")
        assert not registry.remove_alias("missing")

    def test_list_and_tags_and_category(self):
        registry = ToolRegistry()
        id1 = registry.register_tool(SimpleTool, tags=["a"], dependencies=["x"])
        id2 = registry.register_tool(AnotherTool, tags=["b"], dependencies=["x"], aliases=["two"])
        assert registry.has_tool("two")
        registry.add_tool_tag(id1, "b")
        registry.remove_tool_tag(id1, "a")

        tools = registry.list_tools(status=ToolStatus.REGISTERED, category="test")
        names = [t.name for t in tools]
        assert "simple" in names

        stats = registry.get_registry_stats()
        assert stats["total_tools"] == 2
        assert stats["by_category"]["test"] == 2

        assert registry.unregister_tool(id1)
        assert registry.unregister_tool(id2)
        assert registry.clear_registry() is None

    def test_event_handlers_and_has_tool(self):
        registry = ToolRegistry()
        events = []
        def on_register(data):
            events.append(data["tool_id"])
        registry.add_event_handler("tool_registered", on_register)
        tid = registry.register_tool(SimpleTool)
        assert events == [tid]
        registry.remove_event_handler("tool_registered", on_register)
        registry.register_tool(AnotherTool, name="another2")
        assert len(events) == 1
        assert registry.has_tool(tid)
