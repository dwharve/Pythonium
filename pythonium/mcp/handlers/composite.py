"""
Composite MCP tool handler that combines all handler modules.
"""

from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .analysis import AnalysisHandlers
from .execution import ExecutionHandlers
from .issue_tracking import IssueTrackingHandlers
from .statistics_and_agents import StatisticsAndAgentHandlers


class ToolHandlers(
    AnalysisHandlers,
    ExecutionHandlers, 
    IssueTrackingHandlers,
    StatisticsAndAgentHandlers
):
    """
    Composite MCP tool handler that provides all functionality.
    
    This class inherits from all specialized handler classes to provide
    a unified interface for MCP tool calls. It maintains compatibility
    with the original handlers.py interface.
    """
    
    def __init__(self, server_instance):
        """Initialize the composite handler with the server instance."""
        # Only call one parent __init__ since they all use the same BaseHandler
        super().__init__(server_instance)
