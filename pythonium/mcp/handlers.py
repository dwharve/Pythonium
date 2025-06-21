"""
MCP tool handlers for Pythonium analysis operations.
"""

import os
import sys
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
from .debug import profiler, profile_operation, logger, log_file_discovery, log_analyzer_creation, log_analysis_start


class ToolHandlers:
    """Handles MCP tool call implementations."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self._analysis_results: Dict[str, List] = {}
    
    @profile_operation("analyze_code")
    async def analyze_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze code for health issues."""
        import asyncio
        
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
        default_config = self.server._get_default_config_dict()
        config = self.server._merge_configs(default_config, user_config)
        
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
        config = self.server._configure_detectors(config, detector_ids)
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
            # Get list of files that will be analyzed
            python_files = list(path.rglob("*.py"))
            log_file_discovery(path, python_files)
            profiler.checkpoint("file_discovery", file_count=len(python_files))
            
            # Check max files limit from MCP config
            mcp_config = config.get("mcp", {})
            max_files = mcp_config.get("max_files_to_analyze", 1000)
            
            if len(python_files) > max_files:
                error_msg = (
                    f"Directory contains {len(python_files)} Python files, which exceeds the "
                    f"maximum limit of {max_files} files for analysis.\n\n"
                    f"RECOMMENDED SOLUTIONS:\n"
                    f"1. Exclude common directories by adding ignore patterns:\n"
                    f"   config: {{\n"
                    f"     \"ignore\": [\n"
                    f"       \"**/venv/**\", \"**/env/**\", \"**/.venv/**\",\n"
                    f"       \"**/node_modules/**\", \"**/build/**\", \"**/dist/**\",\n"
                    f"       \"**/tests/**\", \"**/__pycache__/**\"\n"
                    f"     ]\n"
                    f"   }}\n\n"
                    f"2. Temporarily override the limit in this request:\n"
                    f"   config: {{\"mcp\": {{\"max_files_to_analyze\": {len(python_files)}}}}}\n\n"
                    f"TIP: Virtual environments, build artifacts, and test directories often contain "
                    f"many files that don't need analysis."
                )
                logger.warning(error_msg)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {error_msg}"
                )]
            
            # Add safety check for large repositories
            if len(python_files) > 100:
                logger.warning(f"Large repository detected: {len(python_files)} files. Analysis may take longer.")
                profiler.checkpoint("large_repo_warning", file_count=len(python_files))
        else:
            log_file_discovery(path, [path])
            profiler.checkpoint("file_discovery", file_count=1)
        
        # Purge cache of excluded paths at the beginning of analysis
        if use_cache and analyzer.cache:
            ignored_paths = config.get("ignore", [])
            if ignored_paths:
                logger.info("Purging cache for excluded paths...")
                analyzer.cache.purge_excluded_paths(ignored_paths)
                profiler.checkpoint("cache_purged", excluded_patterns=len(ignored_paths))
        
        # Start analysis
        log_analysis_start([path] if path.is_file() else python_files)
        profiler.checkpoint("analysis_start")
        
        try:
            # Run analysis with timeout protection (5 minutes max)
            logger.info(f"Starting analysis of {path} with timeout protection...")
            
            # Wrap the blocking analysis call in an executor to make it async-friendly
            def run_analysis():
                profiler.checkpoint("analysis_execution_start")
                issues = analyzer.analyze([path])
                profiler.checkpoint("analysis_execution_complete", issue_count=len(issues))
                return issues
            
            # Run with timeout
            loop = asyncio.get_event_loop()
            issues = await asyncio.wait_for(
                loop.run_in_executor(None, run_analysis),
                timeout=300.0  # 5 minutes
            )
            
            profiler.checkpoint("analysis_completed", issue_count=len(issues))
            logger.info(f"Analysis completed successfully. Found {len(issues)} issues.")
            
        except asyncio.TimeoutError:
            error_msg = f"Analysis timed out after 5 minutes. Try analyzing smaller directories or specific files."
            logger.error(error_msg)
            profiler.checkpoint("analysis_timeout")
            return [types.TextContent(
                type="text",
                text=f"Error: {error_msg}\n\nFor large codebases, consider:\n• Analyzing specific subdirectories\n• Using specific detectors with the 'detectors' parameter\n• Running analysis on individual files"
            )]
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg)
            profiler.checkpoint("analysis_error", error=str(e))
            return [types.TextContent(
                type="text",
                text=f"Error: {error_msg}"
            )]
        
        # Store results for later use by analyze_issues
        self._analysis_results[str(path)] = issues
        profiler.checkpoint("results_stored")
        
        # Format results with enhanced output
        if not issues:
            return [types.TextContent(
                type="text",
                text=f"No issues found in the analyzed code.\n\nPath analyzed: {path}\nDetectors used: {', '.join(detector_ids) if detector_ids else 'all available detectors'}\n\nThe code appears to be healthy according to the selected analysis criteria."
            )]
        
        # Group issues by severity
        issues_by_severity = {"error": [], "warn": [], "info": []}
        for issue in issues:
            severity = issue.severity.lower()
            if severity in issues_by_severity:
                issues_by_severity[severity].append(issue)
        
        profiler.checkpoint("results_grouped")
        
        # Format output with better structure and guidance
        output_lines = [
            f"Pythonium Analysis Results",
            f"Path: {path}",
            f"Total issues found: {len(issues)}",
            f"Detectors used: {', '.join(detector_ids) if detector_ids else 'all available'}",
            "",
            "ISSUE BREAKDOWN BY SEVERITY:"
        ]
        
        # Limit output size for very large result sets
        max_issues_per_severity = 20
        truncated = False
        
        for severity in ["error", "warn", "info"]:
            severity_issues = issues_by_severity[severity]
            if severity_issues:
                severity_icon = {"error": "ERROR", "warn": "WARN", "info": "INFO"}[severity]
                output_lines.append(f"\n{severity_icon} {severity.upper()} ({len(severity_issues)} issues):")
                
                # Show limited number of issues
                shown_issues = severity_issues[:max_issues_per_severity]
                for issue in shown_issues:
                    location = ""
                    if issue.location:
                        location = f" at {issue.location.file}:{issue.location.line}"
                    output_lines.append(f"  • {issue.message}{location}")
                
                # Add truncation notice if needed
                if len(severity_issues) > max_issues_per_severity:
                    remaining = len(severity_issues) - max_issues_per_severity
                    output_lines.append(f"  ... and {remaining} more {severity} issues")
                    truncated = True
        
        # Add guidance for next steps
        output_lines.extend([
            "",
            "NEXT STEPS:",
            "• Use 'analyze_issues' tool for detailed summary and recommendations",
            "• Focus on ERROR issues first (security, blocking problems)",
            "• Use 'get_detector_info' to understand specific detector findings",
            "• Use 'get_configuration_schema' to understand configuration options",
            "• Re-run analysis with specific detectors for focused analysis"
        ])
        
        if truncated:
            output_lines.append("• Output was truncated due to large number of issues - use 'analyze_issues' for full details")
        
        profiler.checkpoint("output_formatted")
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
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
            # Get the directory containing the temp file as root path
            root_path = temp_path.parent
            
            # Initialize analyzer with merged default and user configuration
            user_config = arguments.get("config", {})
            detector_ids = arguments.get("detectors")
            
            # Get default configuration and merge with user config
            default_config = self.server._get_default_config_dict()
            config = self.server._merge_configs(default_config, user_config)
            
            profiler.checkpoint("inline_config_setup", 
                              detectors=detector_ids,
                              has_user_config=bool(user_config))
            
            # Handle special MCP legacy parameters if provided (for backward compatibility)
            if arguments.get("disable_cache", False):
                if "performance" not in config:
                    config["performance"] = {}
                config["performance"]["cache_enabled"] = False
            
            # Configure detectors using the same approach as CLI
            config = self.server._configure_detectors(config, detector_ids)
            
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
            
            # Store results for later use by analyze_issues (using original filename)
            self._analysis_results[filename] = issues
            
            # Format results (similar to analyze_code but adapted for inline)
            # ... (rest of the formatting logic)
            
            return [types.TextContent(
                type="text",
                text=f"Inline code analysis completed. Found {len(issues)} issues."
            )]
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
                profiler.checkpoint("temp_file_cleanup")
            except OSError:
                pass  # Ignore cleanup errors
    
    @profile_operation("execute_code")
    async def execute_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute Python code and return the output."""
        code = arguments.get("code")
        if not code:
            raise ValueError("Code is required")
        
        # Get timeout with validation and max limit (5 minutes)
        requested_timeout = arguments.get("timeout", 30)
        max_timeout = 300  # 5 minutes maximum
        timeout = min(requested_timeout, max_timeout)
        
        profiler.checkpoint("code_execution_setup", timeout=timeout)
        
        if requested_timeout > max_timeout:
            timeout_warning = f"Requested timeout ({requested_timeout}s) exceeds maximum allowed ({max_timeout}s). Using {max_timeout}s.\\n\\n"
        else:
            timeout_warning = ""
        
        try:
            # Create subprocess that reads from stdin
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            profiler.checkpoint("subprocess_created")
            
            # Send code to stdin and wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=code.encode('utf-8')), 
                timeout=timeout
            )
            
            profiler.checkpoint("code_execution_completed", exit_code=process.returncode)
            
            # Decode output
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            output_lines = [
                f"{timeout_warning}Python Code Execution Results",
                "=" * 35,
                f"Exit Code: {process.returncode}",
                f"Execution Time: ≤ {timeout}s",
                ""
            ]
            
            if stdout_text:
                output_lines.extend([
                    "STDOUT:",
                    stdout_text.rstrip(),
                    ""
                ])
            
            if stderr_text:
                output_lines.extend([
                    "STDERR:",
                    stderr_text.rstrip(),
                    ""
                ])
            
            if not stdout_text and not stderr_text:
                output_lines.append("No output produced.")
            
            return [types.TextContent(
                type="text",
                text="\\n".join(output_lines)
            )]
            
        except asyncio.TimeoutError:
            profiler.checkpoint("code_execution_timeout")
            return [types.TextContent(
                type="text",
                text=f"{timeout_warning}Code execution timed out after {timeout} seconds."
            )]
        except Exception as e:
            profiler.checkpoint("code_execution_error", error=str(e))
            return [types.TextContent(
                type="text",
                text=f"{timeout_warning}Error executing code: {str(e)}"
            )]
    
    def clear_analysis_results(self, path: str = None) -> None:
        """Clear stored analysis results."""
        if path:
            self._analysis_results.pop(path, None)
        else:
            self._analysis_results.clear()
