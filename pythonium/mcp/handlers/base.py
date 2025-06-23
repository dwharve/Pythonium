"""
Base handler class with shared functionality for MCP tool handlers.
"""

from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..utils.debug import profiler, profile_operation, logger, info_log, warning_log, error_log
from ..formatters import ResponseFormatter, ActionSuggestion
from ..utils.workflow import WorkflowGuide

if TYPE_CHECKING:
    from ..services import ServiceRegistry


class BaseHandler:
    """Base class for MCP tool handlers with shared functionality."""
    
    def __init__(self, service_registry: 'ServiceRegistry'):
        """
        Initialize the base handler with service registry.
        
        Args:
            service_registry: Registry providing access to all services
        """
        self.services = service_registry
        self.response_formatter = ResponseFormatter()
        self.workflow_guide = WorkflowGuide()
    
    def clear_analysis_results(self, path: str = None) -> None:
        """Clear stored analysis results via the analysis service."""
        if path:
            # Clear specific analyzer cache
            project_root = Path(path).resolve()
            self.services.analysis.clear_analyzer_cache(project_root)
        else:
            # Clear all analyzer caches
            self.services.analysis.clear_analyzer_cache()
