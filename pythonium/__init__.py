"""
Pythonium - A comprehensive static analysis tool for Python code quality and health.

This package provides comprehensive static analysis capabilities to identify
code health issues, including dead code, duplicates, complexity hotspots,
security smells, and more.

Key Components:
    - Analyzer: Core analysis engine
    - Detectors: Pluggable issue detection modules
    - CLI: Command-line interface
    - MCP Server: Model Context Protocol integration for LLM agents
"""

from .version import __version__, __version_info__
from .analyzer import Analyzer
from .models import CodeGraph, Issue, Symbol, Location

__all__ = [
    "__version__",
    "__version_info__", 
    "Analyzer",
    "CodeGraph",
    "Issue", 
    "Symbol",
    "Location",
]
