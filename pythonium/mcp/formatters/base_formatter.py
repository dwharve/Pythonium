"""
Base formatter with common functionality.

This module provides the base ResponseFormatter class with shared utilities
and workflow stage descriptions.
"""

from .data_models import WorkflowStage


class BaseResponseFormatter:
    """Base class for response formatting with shared functionality."""
    
    def __init__(self):
        self.workflow_stage_descriptions = {
            WorkflowStage.DISCOVERY: "Finding and analyzing code health issues",
            WorkflowStage.INVESTIGATION: "Understanding issue context and impact",
            WorkflowStage.CLASSIFICATION: "Determining if issues are true/false positives",
            WorkflowStage.RESOLUTION: "Implementing fixes and improvements",
            WorkflowStage.VERIFICATION: "Validating that fixes work correctly",
            WorkflowStage.COMPLETION: "Finalizing and documenting the resolution"
        }
    
    def get_stage_description(self, stage: WorkflowStage) -> str:
        """Get description for a workflow stage."""
        return self.workflow_stage_descriptions.get(stage, stage.value)
