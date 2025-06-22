"""
Data models for response formatting.

This module contains all enums and dataclasses used for structured responses.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    """Types of tool responses."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    WORKFLOW_GUIDANCE = "workflow_guidance"


class WorkflowStage(Enum):
    """Stages in the issue resolution workflow."""
    DISCOVERY = "discovery"
    INVESTIGATION = "investigation"
    CLASSIFICATION = "classification"
    RESOLUTION = "resolution"
    VERIFICATION = "verification"
    COMPLETION = "completion"


@dataclass
class ActionSuggestion:
    """Suggested action for the agent."""
    action: str
    description: str
    tool_call: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    priority: str = "medium"  # low, medium, high, critical


@dataclass
class WorkflowContext:
    """Context for workflow guidance."""
    current_stage: WorkflowStage
    next_stage: Optional[WorkflowStage] = None
    progress_percentage: Optional[int] = None
    blockers: List[str] = None
    
    def __post_init__(self):
        if self.blockers is None:
            self.blockers = []


@dataclass
class ResponseData:
    """Structured response data."""
    type: ResponseType
    message: str
    data: Any = None
    workflow_context: Optional[WorkflowContext] = None
    suggestions: List[ActionSuggestion] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.metadata is None:
            self.metadata = {}
