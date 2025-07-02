"""
Test the SearchToolsTool functionality.
"""

from unittest.mock import Mock

import pytest

from pythonium.tools.base import ToolContext
from pythonium.tools.std.parameters import SearchToolsParams
from pythonium.tools.std.tool_ops import SearchToolsTool


class TestSearchToolsTool:
    """Test the SearchToolsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create a SearchToolsTool instance for testing."""
        return SearchToolsTool()

    @pytest.fixture
    def context(self):
        """Create a ToolContext instance for testing."""
        from datetime import datetime

        from pythonium.managers.tools.registry import ToolRegistration, ToolStatus
        from pythonium.tools.base import ToolMetadata

        # Create mock registry with some tools
        mock_registry = Mock()

        # Create sample tool registrations
        sample_tools = [
            ToolRegistration(
                tool_id="search_test_tool",
                tool_class=Mock,
                name="search_test_tool",
                version="1.0.0",
                status=ToolStatus.ACTIVE,
                metadata=ToolMetadata(
                    name="search_test_tool",
                    description="A test tool for searching functionality",
                    brief_description="Search test tool",
                    category="test",
                    tags=["search", "test"],
                ),
                registered_at=datetime.now(),
            ),
            ToolRegistration(
                tool_id="another_search_tool",
                tool_class=Mock,
                name="another_search_tool",
                version="1.0.0",
                status=ToolStatus.ACTIVE,
                metadata=ToolMetadata(
                    name="another_search_tool",
                    description="Another tool with search capabilities",
                    brief_description="Another search tool",
                    category="tools",
                    tags=["search", "utility"],
                ),
                registered_at=datetime.now(),
            ),
        ]

        mock_registry.list_tools.return_value = sample_tools

        context = ToolContext()
        context.registry = mock_registry
        return context

    @pytest.mark.asyncio
    async def test_tool_initialization(self, tool):
        """Test that the tool can be initialized and shut down."""
        await tool.initialize()
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_metadata_properties(self, tool):
        """Test that the tool has proper metadata."""
        metadata = tool.metadata

        assert metadata.name == "search_tools"
        assert "search" in metadata.description.lower()
        assert metadata.category == "tools"
        assert "search" in metadata.tags

    @pytest.mark.asyncio
    async def test_basic_search(self, tool, context):
        """Test basic tool search functionality."""
        await tool.initialize()

        params = {
            "query": "search",
            "include_description": True,
            "include_parameters": False,
            "limit": 10,
        }

        result = await tool.execute(params, context)

        # Debug output
        print(f"DEBUG: Result success: {result.success}")
        print(f"DEBUG: Result data: {result.data}")
        if hasattr(context, "registry") and context.registry:
            print(f"DEBUG: Registry list_tools result: {context.registry.list_tools()}")

        assert result.success
        assert "tools" in result.data
        assert "total_found" in result.data
        assert result.data["query"] == "search"

        # Should find some tools containing "search"
        assert result.data["total_found"] > 0

        for tool_info in result.data["tools"]:
            assert "name" in tool_info
            assert "brief_description" in tool_info
            assert "category" in tool_info
            assert "tags" in tool_info

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, tool, context):
        """Test searching with category filter."""
        await tool.initialize()

        params = {
            "query": "files",
            "category": "filesystem",
            "include_description": True,
            "limit": 10,
        }

        result = await tool.execute(params, context)

        assert result.success
        assert result.data["filters"]["category"] == "filesystem"

        # All returned tools should be in filesystem category
        for tool_info in result.data["tools"]:
            assert tool_info["category"] == "filesystem"

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_search_with_tags_filter(self, tool, context):
        """Test searching with tags filter."""
        await tool.initialize()

        params = {
            "query": "search",
            "tags": ["find", "search"],
            "include_description": True,
            "limit": 10,
        }

        result = await tool.execute(params, context)

        assert result.success
        assert result.data["filters"]["tags"] == ["find", "search"]

        # All returned tools should have at least one of the specified tags
        for tool_info in result.data["tools"]:
            tool_tags = [tag.lower() for tag in tool_info["tags"]]
            assert any(tag in tool_tags for tag in ["find", "search"])

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_search_with_limit(self, tool, context):
        """Test searching with result limit."""
        await tool.initialize()

        params = {
            "query": "tool",
            "limit": 2,
        }

        result = await tool.execute(params, context)

        assert result.success
        assert len(result.data["tools"]) <= 2

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_search_with_parameters_included(self, tool, context):
        """Test searching with parameter information included."""
        await tool.initialize()

        params = {
            "query": "search",
            "include_parameters": True,
            "limit": 1,
        }

        result = await tool.execute(params, context)

        assert result.success
        if result.data["tools"]:
            # Check that parameters are included when requested
            first_tool = result.data["tools"][0]
            assert "parameters" in first_tool

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_empty_query_validation(self, tool, context):
        """Test that empty query is properly validated."""
        await tool.initialize()

        params = {
            "query": "",  # Empty query should fail validation
            "limit": 10,
        }

        result = await tool.execute(params, context)

        # Should fail due to validation error
        assert not result.success
        assert "validation" in result.error.lower() or "empty" in result.error.lower()

        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_parameter_validation(self, tool):
        """Test parameter validation with SearchToolsParams."""
        # Test valid parameters
        valid_params = SearchToolsParams(
            query="test",
            category="filesystem",
            tags=["search", "find"],
            include_description=True,
            limit=5,
        )

        assert valid_params.query == "test"
        assert valid_params.category == "filesystem"
        assert valid_params.tags == ["search", "find"]
        assert valid_params.limit == 5

        # Test invalid parameters (empty query)
        with pytest.raises(ValueError):
            SearchToolsParams(query="")

        # Test invalid limit
        with pytest.raises(ValueError):
            SearchToolsParams(query="test", limit=0)
