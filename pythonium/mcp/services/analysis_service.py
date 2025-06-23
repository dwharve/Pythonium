"""
Analysis service for Pythonium MCP server.

Encapsulates all code analysis operations and provides a clean interface
for handlers to perform analysis without directly managing analyzer instances.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pythonium.analyzer import Analyzer
from pythonium.cli import find_project_root, get_or_create_config
from pythonium.models import Issue
from ..utils.debug import profiler, profile_operation, info_log, warning_log, error_log
from ..tools.configuration import get_default_config_dict, merge_configs, configure_detectors

if TYPE_CHECKING:
    from .service_registry import ServiceRegistry


class AnalysisService:
    """
    Service for handling code analysis operations.
    
    This service encapsulates all analysis-related functionality:
    - Managing analyzer instances and configuration
    - Handling both file-based and inline code analysis
    - Providing consistent analysis results
    """
    
    def __init__(self, registry: 'ServiceRegistry'):
        """Initialize the analysis service."""
        self.registry = registry
        self._analyzers: Dict[str, Analyzer] = {}  # project_root -> analyzer
        self._available_detectors: Optional[List[str]] = None
    
    def _get_available_detectors(self) -> List[str]:
        """Get list of available detector IDs."""
        if self._available_detectors is None:
            try:
                # Discover detectors by creating a temporary analyzer
                project_root = find_project_root(Path.cwd())
                config = get_or_create_config(project_root, auto_create=False)
                temp_analyzer = Analyzer(root_path=project_root, config=config)
                self._available_detectors = list(temp_analyzer.detectors.keys())
            except Exception as e:
                warning_log(f"Failed to discover detectors: {e}")
                self._available_detectors = []
        return self._available_detectors
    
    @profile_operation("analyze_code_file")
    async def analyze_code_file(
        self,
        path: Path,
        detector_ids: Optional[List[str]] = None,
        user_config: Optional[Dict[str, Any]] = None
    ) -> List[Issue]:
        """
        Analyze a code file or directory.
        
        Args:
            path: Path to analyze
            detector_ids: Specific detectors to run
            user_config: User configuration overrides
            
        Returns:
            List of issues found
        """
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        profiler.checkpoint("path_validation", path=str(path), is_dir=path.is_dir())
        
        # Get project configuration
        project_root = find_project_root(path)
        config = await self._get_merged_config(project_root, detector_ids, user_config)
        
        profiler.checkpoint("config_setup", project_root=str(project_root))
        
        # Get or create analyzer for this project
        analyzer = self._get_analyzer(project_root, config)
        
        # Perform analysis
        if path.is_file():
            files_to_analyze = [path]
        else:
            # For directories, find all Python files in that directory
            files_to_analyze = list(path.glob("**/*.py"))
            if not files_to_analyze:
                warning_log(f"No Python files found in directory: {path}")
                return []
        
        results = analyzer.analyze(files_to_analyze)
        
        profiler.checkpoint("analysis_completed", issue_count=len(results))
        return results
    
    @profile_operation("analyze_inline_code")
    async def analyze_inline_code(
        self,
        code: str,
        filename: str = "temp_code.py",
        detector_ids: Optional[List[str]] = None,
        user_config: Optional[Dict[str, Any]] = None
    ) -> List[Issue]:
        """
        Analyze code provided as a string.
        
        Args:
            code: Python source code to analyze
            filename: Filename to use in reports
            detector_ids: Specific detectors to run
            user_config: User configuration overrides
            
        Returns:
            List of issues found
        """
        profiler.checkpoint("inline_analysis_start", filename=filename)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            # Use current working directory as project root for inline analysis
            project_root = Path.cwd()
            config = await self._get_merged_config(project_root, detector_ids, user_config)
            
            # Create analyzer for inline analysis
            analyzer = Analyzer(root_path=project_root, config=config)
            
            # Analyze the temporary file
            results = analyzer.analyze([temp_path])
            
            # Update file paths in results to use the provided filename
            for issue in results:
                if issue.location and str(issue.location.file) == str(temp_path):
                    # Create a new location with the correct filename
                    from pythonium.models import Location
                    issue.location = Location(
                        file=Path(filename),
                        line=issue.location.line,
                        column=issue.location.column,
                        end_line=issue.location.end_line,
                        end_column=issue.location.end_column
                    )
            
            profiler.checkpoint("inline_analysis_completed", issue_count=len(results))
            return results
            
        finally:
            # Clean up temporary file
            try:
                temp_path.unlink()
            except Exception as e:
                warning_log(f"Failed to clean up temporary file {temp_path}: {e}")
    
    def _get_analyzer(self, project_root: Path, config: Dict[str, Any]) -> Analyzer:
        """Get or create an analyzer for the given project root."""
        root_str = str(project_root)
        
        if root_str not in self._analyzers:
            self._analyzers[root_str] = Analyzer(root_path=project_root, config=config)
            info_log(f"Created new analyzer for project: {project_root}")
        
        return self._analyzers[root_str]
    
    async def _get_merged_config(
        self,
        project_root: Path,
        detector_ids: Optional[List[str]] = None,
        user_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get merged configuration from defaults, project config, and user overrides."""
        # Get available detectors from registry
        available_detectors = self._get_available_detectors()
        
        # Get default configuration
        default_config = get_default_config_dict(available_detectors)
        
        # Get project configuration
        project_config = get_or_create_config(project_root, auto_create=False) or {}
        
        # Merge configurations: defaults < project < user
        config = merge_configs(default_config, project_config)
        if user_config:
            config = merge_configs(config, user_config)
        
        # Configure specific detectors if requested
        if detector_ids:
            config = configure_detectors(config, detector_ids, available_detectors)
        
        return config
    
    def clear_analyzer_cache(self, project_root: Optional[Path] = None) -> None:
        """Clear analyzer cache for a project or all projects."""
        if project_root:
            self._analyzers.pop(str(project_root), None)
            info_log(f"Cleared analyzer cache for project: {project_root}")
        else:
            self._analyzers.clear()
            info_log("Cleared all analyzer caches")
