"""
Analysis-related MCP tool handlers for Pythonium.
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import Any, Dict, List

import mcp.types as types

from pythonium.analyzer import Analyzer
from pythonium.cli import find_project_root, get_or_create_config
from pythonium.database_paths import DatabasePathResolver
from ..utils.debug import profiler, profile_operation, log_file_discovery, log_analyzer_creation, log_analysis_start, info_log, warning_log, error_log
from ..tools.configuration import get_default_config_dict, merge_configs, configure_detectors
from .base import BaseHandler


class AnalysisHandlers(BaseHandler):
    """Handlers for code analysis operations."""
    
    @profile_operation("analyze_code")
    async def analyze_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze code for health issues using the analysis service."""
        path_str = arguments.get("path")
        if not path_str:
            raise ValueError("Path is required")
        
        path = Path(path_str).resolve()
        detector_ids = arguments.get("detectors")
        user_config = arguments.get("config", {})
        
        profiler.checkpoint("analysis_handler_start", path=str(path))
        
        # Use the analysis service for the actual analysis
        try:
            issues = await self.services.analysis.analyze_code_file(
                path=path,
                detector_ids=detector_ids,
                user_config=user_config
            )
            
            profiler.checkpoint("analysis_completed", issue_count=len(issues))
            
            # Track issues if enabled
            project_root = find_project_root(path)
            tracking_stats = {'new_issues': 0, 'updated_issues': 0, 'total_tracked': 0}
            if user_config.get("analysis", {}).get("track_issues", True):
                tracking_stats = await self.services.issues.track_issues(
                    issues=issues,
                    project_root=project_root,
                    analysis_path=path
                )
                profiler.checkpoint("issues_tracked", **tracking_stats)
            
            # Format and return response
            response_data = self.response_formatter.format_analysis_results(
                issues=issues,
                project_path=str(path),
                tracked_count=tracking_stats.get('total_tracked', 0),
                new_count=tracking_stats.get('new_issues', 0)
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
            
        except Exception as e:
            error_log(f"Analysis failed: {str(e)}")
            raise
    
    @profile_operation("analyze_inline_code")
    async def analyze_inline_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze inline Python code for health issues using the analysis service."""
        code = arguments.get("code")
        if not code:
            raise ValueError("Code is required")
        
        filename = arguments.get("filename", "temp_code.py")
        detector_ids = arguments.get("detectors")
        user_config = arguments.get("config", {})
        
        profiler.checkpoint("inline_analysis_start", filename=filename)
        
        try:
            # Use the analysis service for inline code analysis
            issues = await self.services.analysis.analyze_inline_code(
                code=code,
                filename=filename,
                detector_ids=detector_ids,
                user_config=user_config
            )
            
            profiler.checkpoint("inline_analysis_completed", issue_count=len(issues))
            
            # Format and return response
            response_data = self.response_formatter.format_analysis_results(
                issues=issues,
                project_path=filename
            )
            return [self.response_formatter._text_converter.to_text_content(response_data)]
            
        except Exception as e:
            error_log(f"Inline analysis failed: {str(e)}")
            raise

