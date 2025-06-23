"""
Storage layer for Pythonium MCP server.

This module provides database and persistence functionality including:
- Issue database management
- Tracking data storage
- Agent action history
"""

from .issue_database import IssueDatabase

__all__ = [
    'IssueDatabase',
]
