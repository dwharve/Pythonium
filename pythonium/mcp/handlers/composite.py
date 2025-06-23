"""
Composite MCP tool handler that combines all handler modules.
"""

from typing import Any, Dict, List, TYPE_CHECKING

import mcp.types as types

from .analysis import AnalysisHandlers
from .execution import ExecutionHandlers
from .issue_tracking import IssueTrackingHandlers

if TYPE_CHECKING:
    from ..services import ServiceRegistry


class ToolHandlers(
    AnalysisHandlers,
    ExecutionHandlers, 
    IssueTrackingHandlers
):
    """
    Composite MCP tool handler that provides all functionality.
    
    This class inherits from all specialized handler classes to provide
    a unified interface for MCP tool calls. It maintains compatibility
    with the original handlers.py interface while using the new service layer.
    """
    
    def __init__(self, service_registry: 'ServiceRegistry'):
        """
        Initialize the composite handler with the service registry.
        
        Args:
            service_registry: Registry providing access to all services
        """
        # Only call one parent __init__ since they all use the same BaseHandler
        super().__init__(service_registry)
