"""
Analysis-related MCP tool handlers for Pythonium.
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from pythonium.analyzer import Analyzer
from pythonium.cli import find_project_root, get_or_create_config
from pythonium.database_paths import DatabasePathResolver
from ..debug import profiler, profile_operation, log_file_discovery, log_analyzer_creation, log_analysis_start, info_log, warning_log, error_log
from ..config_utilities import get_default_config_dict, merge_configs, configure_detectors
from .base import BaseHandler


class AnalysisHandlers(BaseHandler):
    """Handlers for code analysis operations."""
    
    @profile_operation("analyze_code")
    async def analyze_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze code for health issues."""
        path_str = arguments.get("path")
        if not path_str:
            raise ValueError("Path is required")
        
        path = Path(path_str).resolve()
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        profiler.checkpoint("path_validation", path=str(path), is_dir=path.is_dir())
        
        # Initialize analyzer with merged default and user configuration
        user_config = arguments.get("config", {})
        detector_ids = arguments.get("detectors")
        
        # Get default configuration and merge with user config
        default_config = get_default_config_dict(self.server.available_detectors)
        config = merge_configs(default_config, user_config)
        
        profiler.checkpoint("config_setup", 
                          detectors=detector_ids, 
                          has_user_config=bool(user_config))
        
        # Handle special MCP legacy parameters if provided (for backward compatibility)
        if arguments.get("clear_cache", False):
            self.clear_analysis_results()
            profiler.checkpoint("cache_cleared")
        
        # Override cache settings if disable_cache is provided
        if arguments.get("disable_cache", False):
            if "performance" not in config:
                config["performance"] = {}
            config["performance"]["cache_enabled"] = False
        
        # Override parallel settings if disable_parallel is provided  
        if arguments.get("disable_parallel", False):
            if "performance" not in config:
                config["performance"] = {}
            config["performance"]["parallel"] = False
        
        # Find the actual project root directory
        project_root = find_project_root(path)
        profiler.checkpoint("project_root_found", project_root=str(project_root))
        
        # Get or create config from the project root
        project_config = get_or_create_config(project_root, auto_create=False)
        profiler.checkpoint("project_config_loaded", 
                          has_config=project_config is not None)
        
        # Merge provided config with project config (provided config takes precedence)
        if project_config:
            merged_config = project_config.copy()
            merged_config.update(config)
            config = merged_config
        
        # Configure detectors using the same approach as CLI
        config = configure_detectors(config, detector_ids, self.server.available_detectors)
        profiler.checkpoint("detectors_configured")
        
        # Extract performance settings from config
        performance_config = config.get("performance", {})
        use_cache = performance_config.get("cache_enabled", True)
        use_parallel = performance_config.get("parallel", True)
        
        # Log analyzer creation details
        log_analyzer_creation(config, use_cache, use_parallel)
        
        # Create analyzer with settings from config
        analyzer = Analyzer(root_path=project_root, config=config, 
                          use_cache=use_cache, use_parallel=use_parallel)
        
        profiler.checkpoint("analyzer_created")
        
        # Discover files before analysis and check limits
        if path.is_dir():
            # Use analyzer's file discovery logic which respects ignore patterns
            python_files = analyzer.loader._discover_python_files(path)
            
            # Apply ignore patterns to get the actual files that would be analyzed
            filtered_files = [f for f in python_files if not analyzer.settings.is_path_ignored(f)]
            files_to_analyze = filtered_files
            
            log_file_discovery(path, filtered_files)
            profiler.checkpoint("file_discovery", file_count=len(filtered_files))
            
            # Check max files limit from MCP config
            mcp_config = config.get("mcp", {})
            max_files = mcp_config.get("max_files_to_analyze", 1000)
            
            if len(filtered_files) > max_files:
                # Show both filtered and total counts for better context
                total_files = len(python_files)
                ignored_count = total_files - len(filtered_files)
                
                error_msg = (
                    f"Directory contains {len(filtered_files)} Python files "
                    f"(after filtering {ignored_count} ignored files from {total_files} total), "
                    f"which exceeds the maximum limit of {max_files} files for analysis.\\n\\n"
                    f"RECOMMENDED SOLUTIONS:\\n"
                    f"1. Add more ignore patterns to exclude additional directories:\\n"
                    f"   config: {{\\n"
                    f"     \"ignore\": [\\n"
                    f"       \"**/venv/**\", \"**/env/**\", \"**/.venv/**\",\\n"
                    f"       \"**/node_modules/**\", \"**/build/**\", \"**/dist/**\",\\n"
                    f"       \"**/tests/**\", \"**/__pycache__/**\"\\n"
                    f"     ]\\n"
                    f"   }}\\n\\n"
                    f"2. Temporarily override the limit in this request:\\n"
                    f"   config: {{\"mcp\": {{\"max_files_to_analyze\": {len(filtered_files)}}}}}\\n\\n"
                    f"TIP: The current ignore patterns filtered out {ignored_count} files. "
                    f"You may need additional patterns for your specific project structure."
                )
                warning_log(error_msg)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {error_msg}"
                )]
            
            # Add safety check for large repositories
            if len(filtered_files) > 100:
                warning_log(f"Large repository detected: {len(filtered_files)} files. Analysis may take longer.")
                profiler.checkpoint("large_repo_warning", file_count=len(filtered_files))
        else:
            files_to_analyze = [path]
            log_file_discovery(path, [path])
            profiler.checkpoint("file_discovery", file_count=1)
        
        # Purge cache of excluded paths at the beginning of analysis
        if use_cache and analyzer.cache:
            ignored_paths = config.get("ignore", [])
            if ignored_paths:
                info_log("Purging cache for excluded paths...")
                analyzer.cache.purge_excluded_paths(ignored_paths)
                profiler.checkpoint("cache_purged", excluded_patterns=len(ignored_paths))
        
        # Start analysis
        log_analysis_start(files_to_analyze)
        profiler.checkpoint("analysis_start")
        
        try:
            # Run analysis with timeout protection (5 minutes max)
            info_log(f"Starting analysis of {path} with timeout protection...")
            
            # Wrap the blocking analysis call in an executor to make it async-friendly
            def run_analysis():
                profiler.checkpoint("analysis_execution_start")
                # Use the filtered file list instead of the directory path
                if path.is_file():
                    issues = analyzer.analyze([path])
                else:
                    # For directories, use the pre-filtered file list
                    issues = analyzer.analyze(files_to_analyze)
                profiler.checkpoint("analysis_execution_complete", issue_count=len(issues))
                return issues
            
            # Run with timeout
            loop = asyncio.get_event_loop()
            issues = await asyncio.wait_for(
                loop.run_in_executor(None, run_analysis),
                timeout=300.0  # 5 minutes
            )
            
            profiler.checkpoint("analysis_completed", issue_count=len(issues))
            info_log(f"Analysis completed successfully. Found {len(issues)} issues.")
            
        except asyncio.TimeoutError:
            error_msg = f"Analysis timed out after 5 minutes. Try analyzing smaller directories or specific files."
            error_log(error_msg)
            profiler.checkpoint("analysis_timeout")
            return [types.TextContent(
                type="text",
                text=f"Error: {error_msg}\\n\\nFor large codebases, consider:\\n• Analyzing specific subdirectories\\n• Using specific detectors with the 'detectors' parameter\\n• Running analysis on individual files"
            )]
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            error_log(error_msg)
            profiler.checkpoint("analysis_error", error=str(e))
            return [types.TextContent(
                type="text",
                text=f"Error: {error_msg}"
            )]
        
        # Apply issue tracking to filter and track issues
        issue_tracker = self._get_issue_tracker(project_root)
        tracked_issues = issue_tracker.process_new_issues(issues)
        
        # Store original and filtered results for later use by analyze_issues
        self._analysis_results[str(path)] = issues  # Store original for analyze_issues
        profiler.checkpoint("results_stored", 
                          original_count=len(issues), 
                          filtered_count=len(tracked_issues))
        
        # Calculate tracking statistics
        new_count = sum(1 for issue in tracked_issues if issue_tracker._generate_issue_hash(issue) not in issue_tracker.tracked_issues)
        suppressed_count = len(issues) - len(tracked_issues)
        tracked_count = len(tracked_issues) - new_count
        
        # Use new response formatter
        response_data = self.response_formatter.format_analysis_results(
            issues=tracked_issues,
            project_path=str(path),
            tracked_count=tracked_count,
            suppressed_count=suppressed_count,
            new_count=new_count
        )
        
        # Convert to text content
        response_text = self.response_formatter.to_text_content(response_data)
        
        profiler.checkpoint("output_formatted")
        
        return [response_text]
    
    @profile_operation("analyze_inline_code")
    async def analyze_inline_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze inline Python code for health issues."""
        code = arguments.get("code")
        if not code:
            raise ValueError("Code is required")
        
        filename = arguments.get("filename", "temp_code.py")
        if not filename.endswith('.py'):
            filename += '.py'
        
        profiler.checkpoint("temp_file_setup", filename=filename)
        
        # Create temporary file with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, 
                                       prefix='pythonium_', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_path = Path(temp_file.name)
        
        try:
            # Use the workspace project root instead of temporary directory
            # This ensures inline code analysis is tracked with the main project
            workspace_root = DatabasePathResolver.resolve_project_root()
            root_path = workspace_root
            
            # Initialize analyzer with merged default and user configuration
            user_config = arguments.get("config", {})
            detector_ids = arguments.get("detectors")
            
            # Get default configuration and merge with user config
            default_config = get_default_config_dict(self.server.available_detectors)
            config = merge_configs(default_config, user_config)
            
            profiler.checkpoint("inline_config_setup", 
                              detectors=detector_ids,
                              has_user_config=bool(user_config))
            
            # Handle special MCP legacy parameters if provided (for backward compatibility)
            if arguments.get("disable_cache", False):
                if "performance" not in config:
                    config["performance"] = {}
                config["performance"]["cache_enabled"] = False
            
            # Configure detectors using the same approach as CLI
            config = configure_detectors(config, detector_ids, self.server.available_detectors)
            
            # Extract performance settings from config
            performance_config = config.get("performance", {})
            use_cache = performance_config.get("cache_enabled", True)
            use_parallel = performance_config.get("parallel", True)
            
            # Create analyzer with settings from config
            analyzer = Analyzer(root_path=root_path, config=config, 
                              use_cache=use_cache, use_parallel=use_parallel)
            
            profiler.checkpoint("inline_analyzer_created")
            
            # Run analysis on the temporary file
            issues = analyzer.analyze([temp_path])
            
            profiler.checkpoint("inline_analysis_completed", issue_count=len(issues))
            
            # Apply issue tracking for inline code (use temp root path for tracking)
            issue_tracker = self._get_issue_tracker(root_path)
            tracked_issues = issue_tracker.process_new_issues(issues)
            
            # Store original results for later use by analyze_issues (using original filename)
            self._analysis_results[filename] = issues
            
            profiler.checkpoint("inline_results_stored", 
                              original_count=len(issues), 
                              filtered_count=len(tracked_issues))
            
            # Calculate tracking statistics
            new_count = sum(1 for issue in tracked_issues if issue_tracker._generate_issue_hash(issue) not in issue_tracker.tracked_issues)
            suppressed_count = len(issues) - len(tracked_issues)
            tracked_count = len(tracked_issues) - new_count
            
            # Use new response formatter for inline code
            response_data = self.response_formatter.format_analysis_results(
                issues=tracked_issues,
                project_path=filename,
                tracked_count=tracked_count,
                suppressed_count=suppressed_count,
                new_count=new_count
            )
            
            # Convert to text content
            response_text = self.response_formatter.to_text_content(response_data)
            
            return [response_text]
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
                profiler.checkpoint("temp_file_cleanup")
            except OSError:
                pass  # Ignore cleanup errors
