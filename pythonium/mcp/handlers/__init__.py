"""
MCP tool handlers module for Pythonium.

This module provides organized, modular handlers for different categories
of MCP tool operations:

- Analysis: Code analysis operations (analyze_code, analyze_inline_code)
- Execution: Code execution and repair (execute_code, repair_python_syntax)  
- Issue Tracking: Issue management (mark_issue, list_tracked_issues, etc.)
- Statistics and Agents: Stats and agent interactions (get_tracking_statistics, investigate_issue, etc.)

The composite.ToolHandlers class provides a unified interface that maintains
compatibility with the original handlers.py.
"""

from .composite import ToolHandlers

__all__ = ['ToolHandlers']
