"""
Text content conversion utilities.

This module provides utilities for converting structured ResponseData
to formatted text content for display.
"""

import json
import mcp.types as types

from .data_models import ResponseData


class TextConverter:
    """Converts ResponseData to formatted text content."""
    
    @staticmethod
    def to_text_content(response_data: ResponseData) -> types.TextContent:
        """Convert ResponseData to formatted text content.
        
        Returns a proper TextContent object ready for use in handler responses.
        """
        
        lines = [response_data.message]
        
        # Add workflow context
        if response_data.workflow_context:
            wc = response_data.workflow_context
            lines.append("")
            lines.append("**Workflow Status:**")
            lines.append(f"   Current Stage: {wc.current_stage.value}")
            
            if wc.next_stage:
                lines.append(f"   Next Stage: {wc.next_stage.value}")
            
            if wc.progress_percentage is not None:
                lines.append(f"   Progress: {wc.progress_percentage}%")
            
            if wc.blockers:
                lines.append(f"   Blockers: {', '.join(wc.blockers)}")
        
        # Add suggestions
        if response_data.suggestions:
            lines.append("")
            lines.append("**Suggested Actions:**")
            
            # Group by priority
            by_priority = {"critical": [], "high": [], "medium": [], "low": []}
            for suggestion in response_data.suggestions:
                by_priority[suggestion.priority].append(suggestion)
            
            for priority in ["critical", "high", "medium", "low"]:
                if by_priority[priority]:
                    priority_icon = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}[priority]
                    lines.append(f"   {priority_icon} **{priority.title()} Priority:**")
                    
                    for suggestion in by_priority[priority]:
                        line = f"      • {suggestion.description}"
                        if suggestion.tool_call:
                            line += f" (use `{suggestion.tool_call}`)"
                        lines.append(line)
        
        # Add metadata summary
        if response_data.metadata:
            lines.append("")
            lines.append("**Summary:**")
            for key, value in response_data.metadata.items():
                if isinstance(value, dict):
                    lines.append(f"   {key}: {json.dumps(value, indent=2)}")
                else:
                    lines.append(f"   {key}: {value}")
        
        # Create and return a proper TextContent object
        return types.TextContent(
            type="text", 
            text="\n".join(lines)
        )
