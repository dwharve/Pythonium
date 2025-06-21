"""
Main MCP server implementation for Pythonium.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict

try:
    import mcp.server.stdio
    import mcp.server.sse
    import mcp.types as types
    from mcp.server import Server
    from mcp.types import ServerCapabilities, ToolsCapability
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from pythonium.analyzer import Analyzer
from pythonium.cli import find_project_root, get_or_create_config
from .debug import setup_debug_logging, profiler, profile_operation, logger
from .handlers import ToolHandlers

class PythoniumMCPServer:
    """MCP server for Pythonium code health analysis."""
    
    def __init__(self, name: str = "pythonium", version: str = "0.1.0", debug: bool = False):
        """Initialize the MCP server."""
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP dependencies not available. Install with: "
                "pip install mcp"
            )
        
        # Setup debug logging only if requested
        if debug:
            setup_debug_logging()
            logger.info(f"Initializing Pythonium MCP Server v{version}")
        else:
            # Setup minimal logging - only errors to console
            logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
            # Use logger for initialization message but at WARNING level so it shows
            logging.getLogger("pythonium.mcp").warning(f"Initializing Pythonium MCP Server v{version}")
        
        self.server = Server(name, version)
        self.name = name
        self.version = version
        self.debug = debug
        
        # Initialize tool handlers
        self.handlers = ToolHandlers(self)
        
        # Dynamically discover available detectors
        self._detector_info = self._discover_detectors()
        
        # Setup MCP handlers
        self._setup_handlers()
        
        if debug:
            logger.info(f"MCP Server initialized with {len(self.available_detectors)} detectors")
        else:
            # Log at WARNING level so it shows in minimal logging mode
            logging.getLogger("pythonium.mcp").warning(f"MCP Server initialized with {len(self.available_detectors)} detectors")
    
    @profile_operation("discover_detectors")
    def _discover_detectors(self) -> Dict[str, Dict[str, Any]]:
        """Dynamically discover available detectors."""
        try:
            project_root = find_project_root(Path.cwd())
            config = get_or_create_config(project_root, auto_create=False)
            analyzer = Analyzer(root_path=project_root, config=config)
            
            detector_info = {}
            for detector_id, detector in analyzer.detectors.items():
                info = {
                    "id": detector.id,
                    "name": detector.name,
                    "description": detector.description,
                    "type": "core",
                    "category": getattr(detector, 'category', 'Code Analysis'),
                    "usage_tips": getattr(detector, 'usage_tips', f"Use for focused analysis of {detector.description.lower()}"),
                    "related_detectors": getattr(detector, 'related_detectors', []),
                    "typical_severity": getattr(detector, 'typical_severity', 'info'),
                    "detailed_description": getattr(detector, 'detailed_description', detector.description)
                }
                detector_info[detector_id] = info
            
            if logger.handlers:  # Only log if debug logging is enabled
                logger.info(f"Discovered {len(detector_info)} detectors")
            else:
                # Log at INFO level - won't show in minimal mode but available if needed
                logging.getLogger("pythonium.mcp").info(f"Discovered {len(detector_info)} detector classes")
                logging.getLogger("pythonium.mcp").info(f"Loaded {len(detector_info)} detectors")
            
            return detector_info
            
        except Exception as e:
            logger.error("Failed to discover detectors: %s", str(e))
            raise RuntimeError(f"Could not discover available detectors: {str(e)}")
    
    @property
    def available_detectors(self) -> List[str]:
        """Get list of available detector IDs."""
        return list(self._detector_info.keys())
    
    def _setup_handlers(self) -> None:
        """Set up MCP message handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools():
            """Return list of available tools."""
            if logger.handlers:
                logger.info("list_tools handler called")
            else:
                # Log request processing at DEBUG level - won't show in minimal mode
                logging.getLogger("pythonium.mcp").debug("Processing request of type ListToolsRequest")
            tools = self._get_tool_definitions()
            if logger.handlers:
                logger.info(f"Returning {len(tools)} tools")
            else:
                logging.getLogger("pythonium.mcp").debug("list_tools handler called")
                logging.getLogger("pythonium.mcp").debug(f"Returning {len(tools)} tools")
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments):
            """Handle tool calls with profiling."""
            if logger.handlers:
                logger.info(f"call_tool handler called - tool: {name}, args: {arguments}")
            if arguments is None:
                arguments = {}
            
            profiler.start_operation(f"tool_call_{name}", tool=name, args_keys=list(arguments.keys()))
            
            try:
                if name == "analyze_code":
                    return await self.handlers.analyze_code(arguments)
                elif name == "analyze_inline_code":
                    return await self.handlers.analyze_inline_code(arguments)
                elif name == "execute_code":
                    return await self.handlers.execute_code(arguments)
                elif name == "list_detectors":
                    return await self._list_detectors(arguments)
                elif name == "get_detector_info":
                    return await self._get_detector_info(arguments)
                elif name == "analyze_issues":
                    return await self._analyze_issues(arguments)
                elif name == "get_configuration_schema":
                    return await self._get_configuration_schema(arguments)
                elif name == "debug_profile":
                    return await self._debug_profile(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.exception("Error handling tool call: %s", str(e))
                profiler.end_operation(success=False, error=str(e))
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
            finally:
                if profiler.current_operation and profiler.current_operation.get("status") == "running":
                    profiler.end_operation(success=True)
    
    def _get_tool_definitions(self) -> List[types.Tool]:
        """Get MCP tool definitions."""
        return [
            types.Tool(
                name="analyze_code",
                description="Analyze Python code files or directories for code health issues using Pythonium detectors. Returns detailed findings with severity levels and locations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute or relative path to a Python file (.py) or directory to analyze."
                        },
                        "detectors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific detectors to run. Use list_detectors tool to see available options."
                        },
                        "config": {
                            "type": "object",
                            "description": "Optional configuration overrides for analysis behavior. This merges with sensible defaults that include path filtering for virtual environments, cache directories, etc."
                        }
                    },
                    "required": ["path"]
                }
            ),
            types.Tool(
                name="analyze_inline_code",
                description="Analyze Python code provided as a string rather than from a file. Perfect for analyzing code snippets, generated code, or code from external sources.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python source code to analyze as a string."
                        },
                        "detectors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific detectors to run. Use list_detectors tool to see available options."
                        },
                        "filename": {
                            "type": "string",
                            "description": "Optional filename to use in error reports (default: 'temp_code.py')."
                        },
                        "config": {
                            "type": "object",
                            "description": "Optional configuration overrides for analysis behavior. This merges with sensible defaults."
                        }
                    },
                    "required": ["code"]
                }
            ),
            types.Tool(
                name="execute_code",
                description="Execute Python code provided as a string and return the output. Perfect for running code snippets, testing small functions, or demonstrating code examples.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python source code to execute as a string."
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Maximum execution time in seconds (default: 30)."
                        },
                        "capture_output": {
                            "type": "boolean",
                            "description": "Whether to capture stdout/stderr output (default: true)."
                        }
                    },
                    "required": ["code"]
                }
            ),
            types.Tool(
                name="list_detectors",
                description="Get a comprehensive list of all available Pythonium code health detectors with their descriptions and purposes.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            types.Tool(
                name="get_detector_info",
                description="Get detailed information about a specific detector including its purpose, what it detects, and configuration options.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "detector_id": {
                            "type": "string",
                            "description": "ID of the detector to get detailed information for. Available detectors will be shown in list_detectors output."
                        }
                    },
                    "required": ["detector_id"]
                }
            ),
            types.Tool(
                name="analyze_issues",
                description="Generate a summary report and actionable recommendations for code health issues found in previous analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path that was previously analyzed with analyze_code."
                        },
                        "severity_filter": {
                            "type": "string",
                            "enum": ["info", "warn", "error"],
                            "description": "Minimum severity level to include in the summary."
                        }
                    },
                    "required": ["path"]
                }
            ),
            types.Tool(
                name="get_configuration_schema",
                description="Get comprehensive documentation of Pythonium's configuration system including file structure, global options, detector-specific settings, and usage examples.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "section": {
                            "type": "string",
                            "enum": ["overview", "detectors", "global", "examples", "precedence", "validation"],
                            "description": "Specific configuration section to focus on."
                        }
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="debug_profile",
                description="Get profiling information about MCP server operations to help debug performance issues.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reset": {
                            "type": "boolean",
                            "description": "Whether to reset the profiling data after returning the report."
                        }
                    },
                    "required": []
                }
            )
        ]
    
    async def _debug_profile(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Return profiling information for debugging."""
        reset = arguments.get("reset", False)
        
        report = profiler.get_report()
        
        if reset:
            profiler.operations.clear()
            report += "\n\nProfiling data has been reset."
        
        return [types.TextContent(
            type="text",
            text=report
        )]
    
    async def _list_detectors(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """List all available detectors."""
        # Implementation similar to original but simplified
        output_lines = [
            "Available Pythonium Code Health Detectors",
            f"Total detectors: {len(self._detector_info)}",
            ""
        ]
        
        for detector_id, info in self._detector_info.items():
            output_lines.extend([
                f"{detector_id}",
                f"   {info['name']}",
                f"   {info['description']}",
                ""
            ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_detector_info(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get information about a specific detector."""
        detector_id = arguments.get("detector_id")
        if not detector_id or detector_id not in self._detector_info:
            return [types.TextContent(
                type="text",
                text=f"Detector '{detector_id}' not found. Available: {', '.join(self.available_detectors)}"
            )]
        
        info = self._detector_info[detector_id]
        return [types.TextContent(
            type="text",
            text=f"Detector: {info['name']}\nDescription: {info['description']}"
        )]
    
    async def _analyze_issues(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Provide analysis summary and recommendations from previously stored results."""
        path_str = arguments.get("path")
        if not path_str:
            raise ValueError("Path is required")
          # Handle path resolution for both real files and inline code analysis
        if Path(path_str).exists():
            # For real files, use the resolved absolute path
            path = Path(path_str).resolve()
            path_key = str(path)
        else:
            # For inline code or non-existent files, use the original path string
            path = Path(path_str)
            path_key = path_str
        
        severity_filter = arguments.get("severity_filter", "info")
        
        # Check if we have stored results for this path
        # First try the resolved path key
        if path_key in self.handlers._analysis_results:
            issues = self.handlers._analysis_results[path_key]
        # If not found, try the original path string (fallback for inline code)
        elif path_str in self.handlers._analysis_results:
            issues = self.handlers._analysis_results[path_str]
            path_key = path_str
        # If still not found, try to match by filename for inline code
        else:
            filename = Path(path_str).name
            matching_keys = [key for key in self.handlers._analysis_results.keys() if Path(key).name == filename]
            if matching_keys:
                path_key = matching_keys[0]
                issues = self.handlers._analysis_results[path_key]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"No previous analysis results found for path: {path}\n\n"
                         "Please run 'analyze_code' on this path first to generate analysis results.\n\n"
                         "Available analyzed paths:\n" + 
                         "\n".join([f"  • {p}" for p in self.handlers._analysis_results.keys()]) if self.handlers._analysis_results else
                         "No paths have been analyzed yet."
                )]
        
        # Filter by severity
        severity_levels = {"info": 0, "warn": 1, "error": 2}
        min_level = severity_levels.get(severity_filter, 0)
        filtered_issues = [
            issue for issue in issues
            if severity_levels.get(issue.severity.lower(), 0) >= min_level
        ]
        
        if not filtered_issues:
            return [types.TextContent(
                type="text",
                text=f"No issues found with severity '{severity_filter}' or higher.\n\n"
                     f"Path analyzed: {path}\n"
                     f"Total issues in analysis: {len(issues)}\n"
                     "This indicates good code health at the selected severity level.\n\n"
                     "Tip: Try lowering the severity filter to 'info' to see all findings."
            )]
        
        # Generate comprehensive analysis summary with actionable insights
        issue_counts = {}
        detector_counts = {}
        file_counts = {}
        
        for issue in filtered_issues:
            severity = issue.severity.lower()
            issue_counts[severity] = issue_counts.get(severity, 0) + 1
            
            detector_id = issue.detector_id or "unknown"
            detector_counts[detector_id] = detector_counts.get(detector_id, 0) + 1
            
            if issue.location and issue.location.file:
                file_path = str(issue.location.file)
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
        
        output_lines = [
            f"Pythonium Analysis Summary & Recommendations",
            f"=" * 50,
            f"Path: {path}",
            f"Analysis Date: Previous analysis results",
            f"Issues found (severity >= {severity_filter}): {len(filtered_issues)}",
            f"Total issues in full analysis: {len(issues)}",
            f"Filter applied: {severity_filter.upper()} level and above",
            ""
        ]
        
        # Executive Summary
        output_lines.extend([
            "EXECUTIVE SUMMARY:",
            f"• {len(filtered_issues)} issues require attention at {severity_filter}+ severity",
            f"• {len(detector_counts)} different detectors found issues",
            f"• {len(file_counts)} files contain issues" if file_counts else "• Issues span multiple areas of the codebase",
            ""
        ])
        
        # Issue breakdown by severity with risk assessment
        output_lines.append("RISK ASSESSMENT BY SEVERITY:")
        severity_descriptions = {
            "error": "CRITICAL - Security vulnerabilities, blocking bugs, broken functionality",
            "warn": "HIGH RISK - Quality issues, potential bugs, maintainability problems", 
            "info": "MODERATE - Optimization opportunities, style improvements"
        }
        
        for severity in ["error", "warn", "info"]:
            count = issue_counts.get(severity, 0)
            if count > 0:
                desc = severity_descriptions.get(severity, "")
                output_lines.append(f"  {severity.upper()}: {count} issues - {desc}")
        output_lines.append("")
        
        # Top problematic detectors with actionable insights
        output_lines.append("ISSUE HOTSPOTS BY DETECTOR:")
        sorted_detectors = sorted(detector_counts.items(), key=lambda x: x[1], reverse=True)
        for detector_id, count in sorted_detectors[:5]:  # Top 5 detectors
            detector_info = self._detector_info.get(detector_id, {})
            short_desc = detector_info.get('description', detector_id.replace("_", " "))
            if short_desc and '.' in short_desc:
                short_desc = short_desc.split(".")[0]
            output_lines.append(f"  • {detector_id}: {count} issues - {short_desc}")
        
        if len(sorted_detectors) > 5:
            output_lines.append(f"  ... and {len(sorted_detectors) - 5} other detectors")
        output_lines.append("")
        
        # Most problematic files (if we have location info)
        if file_counts:
            output_lines.append("FILES NEEDING ATTENTION:")
            sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
            for file_path, count in sorted_files[:5]:  # Top 5 files
                rel_path = Path(file_path).name  # Just filename for brevity
                output_lines.append(f"  • {rel_path}: {count} issues")
            
            if len(sorted_files) > 5:
                output_lines.append(f"  ... and {len(sorted_files) - 5} other files")
            output_lines.append("")
        
        # Strategic recommendations with priorities
        output_lines.append("STRATEGIC RECOMMENDATIONS:")
        recommendations = []
        
        if issue_counts.get("error", 0) > 0:
            recommendations.append("IMMEDIATE: Fix all ERROR-level issues (security risks, blocking bugs)")
        if issue_counts.get("warn", 0) > 0:
            recommendations.append("HIGH PRIORITY: Address WARN-level issues for code quality")
        if issue_counts.get("info", 0) > 0:
            recommendations.append("OPTIMIZE: Review INFO-level suggestions for improvements")
        
        # Add detector-specific strategic advice
        top_detector = sorted_detectors[0][0] if sorted_detectors else None
        if top_detector and top_detector in self._detector_info:
            detector_info = self._detector_info[top_detector]
            category = detector_info.get('category', 'Code Quality')
            recommendations.append(f"FOCUS AREA: {category} issues are most prevalent ({top_detector})")
        
        # Add architectural recommendations based on detector patterns
        if any('circular' in d for d, _ in sorted_detectors):
            recommendations.append("ARCHITECTURE: Review module dependencies and circular imports")
        if any('security' in d for d, _ in sorted_detectors):
            recommendations.append("SECURITY: Conduct security review and update vulnerable patterns")
        if any('duplicate' in d or 'clone' in d for d, _ in sorted_detectors):
            recommendations.append("REFACTOR: Eliminate code duplication through refactoring")
        
        for i, rec in enumerate(recommendations, 1):
            output_lines.append(f"{i}. {rec}")
        
        output_lines.extend([
            "",
            "IMPLEMENTATION ROADMAP:",
            "Phase 1: Address ERROR issues (critical path)",
            "Phase 2: Fix WARN issues in high-traffic files",
            "Phase 3: Implement INFO suggestions during maintenance cycles",
            "Phase 4: Establish automated checks to prevent regression",
            "",
            "NEXT ACTIONS:",
            "• Use 'get_detector_info' for specific remediation guidance",
            "• Re-run 'analyze_code' after fixes to measure improvement",
            "• Focus on files with highest issue counts first",
            "• Consider setting up pre-commit hooks with Pythonium",
            f"• Use severity filter 'error' to prioritize critical issues"
        ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_configuration_schema(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get comprehensive configuration schema documentation."""
        section = arguments.get("section", "overview")
        
        if section == "overview":
            return await self._get_schema_overview()
        elif section == "detectors":
            return await self._get_detector_configurations()
        elif section == "global":
            return await self._get_global_configurations()
        elif section == "examples":
            return await self._get_configuration_examples()
        elif section == "precedence":
            return await self._get_configuration_precedence()
        elif section == "validation":
            return await self._get_configuration_validation()
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown configuration section: {section}. Available sections: overview, detectors, global, examples, precedence, validation"
            )]
    
    async def _get_schema_overview(self) -> List[types.TextContent]:
        """Get complete configuration schema overview."""
        from pythonium.settings import Settings
        
        # Get actual defaults from Settings
        default_settings = Settings()
        sample_thresholds = {k: v for k, v in list(default_settings.thresholds.items())[:3]}
        sample_patterns = default_settings.ignored_paths[:3]
        
        output_lines = [
            "Pythonium Configuration Schema",
            "=" * 35,
            "",
            "Pythonium uses intelligent configuration loading with this hierarchy:",
            "1. Hardcoded defaults → 2. .gitignore patterns → 3. .pythonium.yml overrides",
            "",
            "MAIN CONFIGURATION SECTIONS:",
            "",
            "1. DETECTORS - Per-detector configuration and options",
            "   • Enable/disable specific detectors",
            "   • Configure detector-specific thresholds and behavior",
            "   • Set detector-specific severity overrides",
            "",
            "2. GLOBAL SETTINGS - Project-wide configuration",
            "   • severity: Override default severity levels",
            "   • ignore: Global ignore patterns for files/directories",
            "   • thresholds: Common threshold values",
            "   • suppression: Pattern-based issue suppression",
            "   • output: Output formatting and limits",
            "",
            "CURRENT DEFAULTS (from Settings class):",
            f"• Default ignore patterns: {len(default_settings.ignored_paths)} patterns",
            f"  Examples: {sample_patterns}",
            f"• Default thresholds: {len(default_settings.thresholds)} thresholds",
            f"  Examples: {sample_thresholds}",
            f"• Output limits: max_issues_per_detector={default_settings.output_limits.get('max_issues_per_detector', 50)}",
            "",
            "CONFIGURATION STRUCTURE:",
            "",
            "```yaml",
            "# Basic structure of .pythonium.yml",
            "detectors:",
            "  detector_name:",
            "    enabled: true|false",
            "    options: detector_specific_values",
            "",
            "ignore:  # Replaces all default patterns",
            "  - \"**/custom/**\"",
            "",
            "thresholds:  # Merges with defaults",
            "  complexity_cyclomatic: 8",
            "",
            "severity:  # Global overrides",
            "  detector_name: error|warn|info",
            "```",
            "",
            "INTELLIGENT CONFIGURATION LOADING:",
            "• If .gitignore exists: ignore patterns replaced with gitignore",
            "• If .pythonium.yml exists: configuration merged (replaces, not extends)",
            "• Values always replace previous settings, ensuring predictable behavior",
            "",
            f"AVAILABLE DETECTORS: {len(self.available_detectors)}",
            f"Detector IDs: {', '.join(sorted(self.available_detectors))}"
        ]
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_detector_configurations(self) -> List[types.TextContent]:
        """Get detailed detector configuration options."""
        output_lines = [
            "Detector Configuration Options",
            "=" * 30,
            "",
            "Each detector can be configured with specific options in the .pythonium.yml file.",
            "All detector settings use replacement semantics (values replace, don't extend).",
            "",
            "COMMON DETECTOR CONFIGURATION:",
            "```yaml",
            "detectors:",
            "  detector_name:",
            "    enabled: true                 # Enable/disable this detector",
            "    options:                      # Detector-specific options",
            "      threshold_name: value",
            "```",
            "",
            "AVAILABLE DETECTORS WITH ACTUAL INFO:",
            ""
        ]
        
        # Add documentation for each actual detector
        for detector_id in sorted(self.available_detectors[:5]):  # Show first 5 to avoid too much output
            detector_info = self._detector_info.get(detector_id, {})
            output_lines.extend([
                f"{detector_id.upper()}:",
                f"  Description: {detector_info.get('description', 'No description available')}",
                f"  Category: {detector_info.get('category', 'Code Analysis')}",
                f"  Typical severity: {detector_info.get('typical_severity', 'warn')}",
                "  Configuration:",
                "  ```yaml",
                "  detectors:",
                f"    {detector_id}:",
                "      enabled: true",
            ])
            
            # Add detector-specific realistic options
            if "complexity" in detector_id:
                from pythonium.settings import Settings
                default_settings = Settings()
                complexity_threshold = default_settings.thresholds.get('complexity_cyclomatic', 8)
                output_lines.extend([
                    "      options:",
                    f"        max_complexity: {complexity_threshold}",
                ])
            elif "clone" in detector_id:
                from pythonium.settings import Settings
                default_settings = Settings()
                similarity = default_settings.thresholds.get('clone_similarity', 0.85)
                min_lines = default_settings.thresholds.get('clone_min_lines', 4)
                output_lines.extend([
                    "      options:",
                    f"        similarity_threshold: {similarity}",
                    f"        min_lines: {min_lines}",
                ])
            elif "dead_code" in detector_id:
                output_lines.extend([
                    "      options:",
                    "        ignore_private: false",
                    "        ignore_test_files: true",
                ])
            
            output_lines.extend(["  ```", ""])
        
        if len(self.available_detectors) > 5:
            output_lines.extend([
                f"... and {len(self.available_detectors) - 5} more detectors.",
                "Use 'get_detector_info <detector_id>' for specific detector details.",
                ""
            ])
        
        output_lines.extend([
            "CENTRALIZED CONFIGURATION:",
            "• All default values come from the Settings class",
            "• Settings.create_with_intelligent_defaults() loads configuration",
            "• Use 'list_detectors' to see all available detectors",
            "• Use 'get_detector_info' for detailed detector information"
        ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_global_configurations(self) -> List[types.TextContent]:
        """Get global configuration options documentation."""
        from pythonium.settings import Settings
        
        # Get actual defaults from Settings
        default_settings = Settings()
        
        output_lines = [
            "Global Configuration Options",
            "=" * 30,
            "",
            "Global settings apply across all detectors and analysis runs.",
            "These settings use intelligent configuration loading with replacement semantics.",
            "",
            "CURRENT DEFAULTS (from centralized Settings):",
            f"• Ignore patterns: {len(default_settings.ignored_paths)} patterns",
            f"• Thresholds: {len(default_settings.thresholds)} configured",
            f"• Output limits: {default_settings.output_limits}",
            "",
            "```yaml",
            "# Example .pythonium.yml configuration",
            "# Note: ignore patterns REPLACE defaults completely",
            "ignore:",
            f"  - \"{default_settings.ignored_paths[0]}\"  # Example from defaults",
            f"  - \"{default_settings.ignored_paths[1]}\"  # Example from defaults", 
            "  - \"**/custom/**\"                    # Your custom patterns",
            "",
            "# Threshold values MERGE with defaults",
            "thresholds:",
            f"  complexity_cyclomatic: {default_settings.thresholds.get('complexity_cyclomatic', 8)}",
            f"  clone_similarity: {default_settings.thresholds.get('clone_similarity', 0.85)}",
            f"  high_fanin: {default_settings.thresholds.get('high_fanin', 15)}",
            "",
            "# Detector severity overrides",
            "severity:",
            "  dead_code: error",
            "  security_smell: error",
            "  complexity_hotspot: warn",
            "",
            "# Output configuration",
            "output:",
            f"  max_issues_per_detector: {default_settings.output_limits.get('max_issues_per_detector', 50)}",
            f"  enable_deduplication: {default_settings.output_limits.get('enable_deduplication', True)}",
            f"  min_confidence: {default_settings.output_limits.get('min_confidence', 0.2)}",
            "```",
            "",
            "INTELLIGENT CONFIGURATION HIERARCHY:",
            "1. Settings class provides hardcoded defaults",
            "2. .gitignore replaces ignore patterns (if exists)",
            "3. .pythonium.yml merges configuration (replaces specific values)",
            "",
            "KEY FEATURES:",
            "• Ignore patterns: Complete replacement at each level",
            "• Thresholds: Individual value replacement",
            "• Detector settings: Complete replacement per detector",
            "• Suppression patterns: Complete replacement",
            ""
        ]
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_configuration_examples(self) -> List[types.TextContent]:
        """Get practical configuration examples using actual Settings defaults."""
        from pythonium.settings import Settings
        
        # Get actual defaults to show realistic examples
        default_settings = Settings()
        
        output_lines = [
            "Configuration Examples",
            "=" * 20,
            "",
            "All examples use the intelligent configuration system with replacement semantics.",
            "",
            "BASIC CONFIGURATION (.pythonium.yml):",
            "```yaml",
            "# Enable only specific detectors",
            "detectors:",
            "  dead_code:",
            "    enabled: true",
            "  security_smell:",
            "    enabled: true",
            "  complexity_hotspot:",
            "    enabled: false",
            "",
            "# Override just a few ignore patterns (replaces all defaults)",
            "ignore:",
            "  - \"**/tests/**\"",
            "  - \"**/__pycache__/**\"",
            "  - \"**/node_modules/**\"",
            "```",
            "",
            "USING GITIGNORE + OVERRIDES:",
            "```yaml",
            "# Let .gitignore handle most ignore patterns",
            "# Only override specific settings",
            "detectors:",
            "  security_smell:",
            "    enabled: true",
            "",
            "thresholds:",
            f"  complexity_cyclomatic: {default_settings.thresholds.get('complexity_cyclomatic', 8)}",
            f"  clone_similarity: {default_settings.thresholds.get('clone_similarity', 0.85)}",
            "",
            "severity:",
            "  dead_code: error",
            "```",
            "",
            "LIBRARY/PACKAGE CONFIGURATION:",
            "```yaml",
            "# Strict quality standards",
            "detectors:",
            "  dead_code:",
            "    enabled: true",
            "  clone:",
            "    enabled: true",
            "  security_smell:",
            "    enabled: true",
            "",
            "# Custom ignore patterns for library",
            "ignore:",
            f"  - \"{default_settings.ignored_paths[0]}\"  # Keep some defaults",
            f"  - \"{default_settings.ignored_paths[1]}\"",
            "  - \"**/examples/**\"          # Library-specific",
            "  - \"**/docs/**\"",
            "",
            "# Stricter thresholds",
            "thresholds:",
            "  complexity_cyclomatic: 6     # Stricter than default",
            f"  clone_similarity: {min(0.95, default_settings.thresholds.get('clone_similarity', 0.85) + 0.1)}",
            "",
            "output:",
            "  max_issues_per_detector: 100",
            "  enable_deduplication: true",
            "```",
            "",
            "LEGACY CODEBASE (GRADUAL IMPROVEMENT):",
            "```yaml",
            "# More lenient settings for legacy code",
            "detectors:",
            "  security_smell:",
            "    enabled: true    # Security is always important",
            "  dead_code:",
            "    enabled: true",
            "  complexity_hotspot:",
            "    enabled: true",
            "",
            "# More permissive thresholds",
            "thresholds:",
            "  complexity_cyclomatic: 15   # More lenient",
            f"  high_fanin: {default_settings.thresholds.get('high_fanin', 15) + 5}",
            "",
            "# Manageable output",
            "output:",
            "  max_issues_per_detector: 20",
            "```",
            "",
            "NOTES:",
            f"• Default settings provide {len(default_settings.ignored_paths)} ignore patterns",
            f"• Default thresholds: {len(default_settings.thresholds)} preconfigured values",
            "• Use Settings.create_with_intelligent_defaults() in code",
            "• Ignore patterns always replace completely (no merging)"
        ]
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_configuration_precedence(self) -> List[types.TextContent]:
        """Get configuration precedence documentation."""
        output_lines = [
            "Configuration Precedence & Hierarchy",
            "=" * 35,
            "",
            "Pythonium uses intelligent configuration loading with REPLACEMENT semantics:",
            "",
            "1. HARDCODED DEFAULTS (Settings class)",
            "   • Built into the Settings class",
            "   • 24 default ignore patterns (venv, __pycache__, tests, etc.)",
            "   • Optimized thresholds for common use cases",
            "   • Standard suppression patterns",
            "",
            "2. GITIGNORE REPLACEMENT (if .gitignore exists)",
            "   • REPLACES all default ignore patterns",
            "   • Converts gitignore syntax to glob patterns",
            "   • Maintains project-specific ignore logic",
            "",
            "3. PYTHONIUM.YML OVERRIDE (if .pythonium.yml exists)",
            "   • REPLACES values from previous steps",
            "   • Individual settings replace completely (no merging)",
            "   • Ignore patterns: complete replacement",
            "   • Thresholds: individual value replacement",
            "",
            "4. MCP TOOL PARAMETERS (highest priority)",
            "   • Runtime configuration overrides",
            "   • Tool-specific detector selection",
            "   • Temporary analysis configuration",
            "",
            "REPLACEMENT BEHAVIOR EXAMPLES:",
            "",
            "Default: 24 ignore patterns from Settings",
            "↓",
            "With .gitignore: Replaced with gitignore patterns (e.g., 112 patterns)",
            "↓",
            "With .pythonium.yml ignore section: Replaced with yml patterns (e.g., 12 patterns)",
            "",
            "IMPLEMENTATION:",
            "```python",
            "# This is how the system works internally:",
            "settings = Settings()  # Hardcoded defaults",
            "if gitignore_exists:",
            "    settings.ignored_paths = load_gitignore_patterns()",
            "if pythonium_yml_exists:",
            "    settings = merge_settings(settings, yml_config)  # Replacement",
            "```",
            "",
            "BEST PRACTICES:",
            "• Use .gitignore for file ignore patterns when possible",
            "• Use .pythonium.yml only for detector-specific overrides",
            "• Remember: ignore patterns are replaced, not merged",
            "• Test configuration with list_detectors and debug tools"
        ]
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_configuration_validation(self) -> List[types.TextContent]:
        """Get configuration validation documentation."""
        output_lines = [
            "Configuration Validation",
            "=" * 25,
            "",
            "Pythonium validates configuration files to prevent common errors and misconfigurations.",
            "",
            "VALIDATION RULES:",
            "",
            "1. SCHEMA VALIDATION",
            "   • All configuration keys must be recognized",
            "   • Values must match expected types",
            "   • Required fields must be present",
            "",
            "2. DETECTOR VALIDATION",
            "   • Detector names must exist in available detectors",
            "   • Detector-specific options must be valid",
            "   • Severity levels must be: error, warn, or info",
            "",
            "3. PATH VALIDATION",
            "   • Ignore patterns must use valid glob syntax",
            "   • File paths must be relative to project root",
            "   • Circular dependencies in configuration not allowed",
            "",
            "4. VALUE RANGE VALIDATION",
            "   • Thresholds must be within valid ranges",
            "   • Similarity values must be between 0.0 and 1.0",
            "   • Complexity limits must be positive integers",
            "",
            "COMMON VALIDATION ERRORS:",
            "",
            "Invalid detector name:",
            "```yaml",
            "detectors:",
            "  invalid_detector:  # ERROR: Unknown detector",
            "    enabled: true",
            "```",
            "",
            "Invalid severity level:",
            "```yaml",
            "severity:",
            "  dead_code: critical  # ERROR: Must be error|warn|info",
            "```",
            "",
            "Invalid threshold:",
            "```yaml",
            "thresholds:",
            "  similarity_threshold: 1.5  # ERROR: Must be 0.0-1.0",
            "```",
            "",
            "Invalid ignore pattern:",
            "```yaml",
            "ignore:",
            "  - \"[invalid\"  # ERROR: Invalid glob pattern",
            "```",
            "",
            "VALID CONFIGURATION:",
            "```yaml",
            "detectors:",
            "  dead_code:",
            "    enabled: true",
            "    severity: error",
            "    ignore_private: false",
            "",
            "severity:",
            "  complexity_hotspot: warn",
            "",
            "thresholds:",
            "  similarity_threshold: 0.8",
            "  complexity_threshold: 10",
            "",
            "ignore:",
            "  - \"**/test/**\"",
            "  - \"build/**\"",
            "```",
            "",
            "VALIDATION PROCESS:",
            "1. Parse YAML syntax",
            "2. Validate against schema",
            "3. Check detector existence",
            "4. Validate value ranges",
            "5. Test ignore patterns",
            "6. Report all errors with suggestions",
            "",
            "GETTING HELP:",
            "• Use 'analyze_code' with invalid config to see validation errors",
            "• Check the debug log for detailed validation messages",
            "• Use 'get_configuration_schema examples' for working examples"
        ]
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    def _validate_detectors(self, detector_ids: List[str]) -> List[str]:
        """Validate detector IDs against available detectors."""
        if not detector_ids:
            return []
        
        available = self.available_detectors
        valid_detectors = [d for d in detector_ids if d in available]
        
        if not valid_detectors:
            logger.warning("No valid detectors from: %s. Available: %s", 
                          detector_ids, ", ".join(available))
        
        return valid_detectors
    
    def _get_default_config_dict(self) -> Dict[str, Any]:
        """Get default configuration as a dictionary using Settings class with intelligent defaults."""
        from pythonium.settings import Settings
        from pythonium.cli import find_project_root
        
        # Find project root for intelligent configuration loading
        project_root = find_project_root(Path.cwd())
        
        # Create settings with intelligent defaults (hardcoded -> gitignore -> .pythonium.yml)
        settings = Settings.create_with_intelligent_defaults(project_root)
        
        # Convert to MCP config format
        return settings.to_mcp_config_dict(
            enable_all_detectors=True, 
            available_detectors=self.available_detectors
        )

    def _merge_configs(self, default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with default configuration, with user config taking precedence."""
        import copy
        
        # Deep copy the default config to avoid modifying the original
        merged = copy.deepcopy(default_config)
        
        def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
            """Recursively merge source into target."""
            for key, value in source.items():
                if key == "ignore" and isinstance(value, list):
                    # Special handling for ignore patterns - replace instead of merge
                    # This allows users to completely override default ignore patterns
                    target[key] = list(value)
                elif key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        deep_merge(merged, user_config)
        return merged

    def _configure_detectors(self, config: Dict[str, Any], detector_ids: Optional[List[str]]) -> Dict[str, Any]:
        """Configure detectors in config based on detector IDs."""
        if not detector_ids:
            return config
        
        valid_detector_ids = self._validate_detectors(detector_ids)
        if not valid_detector_ids:
            return config
        
        if "detectors" not in config:
            config["detectors"] = {}
        
        # Disable all detectors first, then enable specified ones
        for detector_id in self.available_detectors:
            config["detectors"][detector_id] = {"enabled": False}
        
        for detector_id in valid_detector_ids:
            config["detectors"][detector_id] = {"enabled": True}
        
        return config
    
    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        import mcp.server.stdio
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream,
                self.server.create_initialization_options()
            )
