"""
Model Context Protocol (MCP) server implementation for Pythonium code health analysis.

This module provides a comprehensive MCP server that allows AI agents to perform
sophisticated Python code analysis using Pythonium's suite of detectors. The server
offers tools for analyzing files, directories, and inline        result_lines = [
            f"Pythonium Analysis Results",
            f"Path: {path}",
            f"Total issues found: {len(issues)}",
            f"Detectors used: {', '.join(detector_ids) if detector_ids else 'all available'}",
            "",
            "ISSUE BREAKDOWN BY SEVERITY:"
        ]ippets to identify
code health issues including security vulnerabilities, code duplication, dead code,
and complexity problems.

Key Features:
- Multi-detector code analysis (security, complexity, duplication, etc.)
- Support for both file/directory and inline code analysis
- Detailed issue reporting with severity levels (ERROR/WARN/INFO)
- Comprehensive detector information and usage guidance
- Analysis summaries with actionable recommendations

Available Tools:
- analyze_code: Main analysis tool for files and directories
- analyze_inline_code: Analyze code snippets provided as strings
- list_detectors: Get information about all available detectors
- get_detector_info: Detailed information about specific detectors
- analyze_issues: Generate summaries and recommendations from analysis results
- get_configuration_schema: Comprehensive configuration documentation and examples

Best Practices for Agents:
1. Start with 'list_detectors' to understand available analysis capabilities
2. Use 'get_configuration_schema' to understand configuration options and structure
3. Use 'analyze_code' for comprehensive codebase analysis
4. Use specific detectors (e.g., 'security_smell') for focused reviews
5. Follow up with 'analyze_issues' for actionable recommendations
6. Use 'get_detector_info' to understand specific findings in detail
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from collections import defaultdict

try:
    import mcp.server.stdio
    import mcp.server.sse
    import mcp.types as types
    from mcp.server import Server, InitializationOptions
    from mcp.types import ServerCapabilities, ToolsCapability
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .analyzer import Analyzer
from .models import Issue
from .cli import get_or_create_config, find_project_root

logger = logging.getLogger(__name__)


class PythoniumMCPServer:
    """MCP server for Pythonium."""
    
    def __init__(self, name: str = "pythonium", version: str = "0.1.0"):
        """Initialize the MCP server.
        
        Args:
            name: Server name
            version: Server version
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP dependencies not available. Install with: "
                "pip install mcp"
            )
        
        self.server = Server(name, version)
        self.name = name
        self.version = version
        
        # Dynamically discover available detectors
        self._detector_info = self._discover_detectors()
        
        # Configure logging to be silent (avoid interference with MCP)
        self._setup_silent_logging()
        self._setup_handlers()
    
    def _discover_detectors(self) -> Dict[str, Dict[str, Any]]:
        """Dynamically discover available detectors and their information.
        
        Returns:
            Dictionary mapping detector ID to their information including:
            - id: Detector identifier
            - name: Human-readable name
            - description: What the detector checks for
            - type: Detector type
            - category: Detector category
            - usage_tips: How to best use this detector
            - related_detectors: List of related detector IDs
            - typical_severity: Typical severity level
            - detailed_description: Extended description
        """
        try:
            # Create a temporary analyzer to discover detectors
            project_root = find_project_root(Path.cwd())
            config = get_or_create_config(project_root)
            analyzer = Analyzer(root_path=project_root, config=config)
            
            detector_info = {}
            for detector_id, detector in analyzer.detectors.items():
                # Get all metadata from the detector itself
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
            
            return detector_info
            
        except Exception as e:
            logger.error("Failed to discover detectors: %s", str(e))
            # If discovery fails completely, we can't provide meaningful service
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
            tools = [
                types.Tool(
                    name="analyze_code",
                    description="Analyze Python code files or directories for code health issues using Pythonium detectors. This is the primary analysis tool - use it to scan codebases for problems like dead code, security vulnerabilities, code duplication, and complexity issues. Returns detailed findings with severity levels (ERROR/WARN/INFO) and specific locations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute or relative path to a Python file (.py) or directory to analyze. For directories, all Python files will be recursively analyzed. Examples: '/path/to/file.py', './src/', '/project/mymodule.py'"
                            },
                            "detectors": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": self.available_detectors
                                },
                                "description": f"Optional list of specific detectors to run. If not provided, all detectors will be used. Available detectors: {', '.join(self.available_detectors)}. Use 'list_detectors' tool to see detailed descriptions and usage guidance for each detector."
                            },
                            "config": {
                                "type": "object",
                                "description": "Optional configuration overrides for analysis behavior. Advanced users can customize detector sensitivity, thresholds, and output formatting."
                            }
                        },
                        "required": ["path"]
                    }
                ),
                types.Tool(
                    name="list_detectors",
                    description="Get a comprehensive list of all available Pythonium code health detectors with their descriptions and purposes. Use this to understand what types of issues each detector can find before running analysis. Essential for choosing the right detectors for your specific code review needs.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="get_detector_info",
                    description="Get detailed information about a specific detector including its purpose, what it detects, and configuration options. Use this when you need to understand exactly what a detector does or how to configure it for your analysis needs.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "detector_id": {
                                "type": "string",
                                "description": f"ID of the detector to get detailed information for. Must be one of: {', '.join(self.available_detectors)}. Use 'list_detectors' to see all available options."
                            }
                        },
                        "required": ["detector_id"]
                    }
                ),
                types.Tool(
                    name="analyze_inline_code",
                    description="Analyze Python code provided as a string rather than from a file. Perfect for analyzing code snippets, generated code, or code from external sources. The code will be temporarily saved and analyzed, then cleaned up automatically.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python source code to analyze as a string. Should be valid Python syntax. Can be a single function, class, module, or complete script."
                            },
                            "filename": {
                                "type": "string",
                                "description": "Optional filename to use in error reports (default: 'temp_code.py'). Helps with identifying the source in analysis results. Should end with .py extension."
                            },
                            "detectors": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": self.available_detectors
                                },
                                "description": f"Optional list of specific detectors to run on the code. If not provided, all detectors will be used. Available: {', '.join(self.available_detectors)}. Use 'list_detectors' tool for detailed information."
                            },
                            "config": {
                                "type": "object",
                                "description": "Optional configuration overrides for analysis behavior."
                            }
                        },
                        "required": ["code"]
                    }
                ),
                types.Tool(
                    name="analyze_issues",
                    description="Generate a summary report and actionable recommendations for code health issues found in previous analysis. Provides statistics, prioritization guidance, and strategic recommendations for addressing problems. Use this after analyze_code to get high-level insights and action plans.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path that was previously analyzed with analyze_code. Must match the exact path used in the original analysis."
                            },
                            "severity_filter": {
                                "type": "string",
                                "enum": ["info", "warn", "error"],
                                "description": "Minimum severity level to include in the summary. 'error' shows only critical issues, 'warn' includes warnings and errors, 'info' shows all findings. Default is 'info'."
                            }
                        },
                        "required": ["path"]
                    }
                ),
                types.Tool(
                    name="get_configuration_schema",
                    description="Get comprehensive documentation of Pythonium's configuration system including file structure, global options, detector-specific settings, and usage examples. Essential for understanding how to configure analysis behavior through .pythonium.yml files or runtime config overrides.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "enum": ["overview", "detectors", "global", "examples", "precedence", "validation"],
                                "description": "Specific configuration section to focus on. 'overview' for complete schema, 'detectors' for detector-specific options, 'global' for project-level settings, 'examples' for configuration samples, 'precedence' for configuration hierarchy, 'validation' for syntax and validation rules."
                            }
                        }
                    }
                )
            ]
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments):
            """Handle tool calls."""
            if arguments is None:
                arguments = {}
            
            try:
                if name == "analyze_code":
                    return await self._analyze_code(arguments)
                elif name == "analyze_inline_code":
                    return await self._analyze_inline_code(arguments)
                elif name == "list_detectors":
                    return await self._list_detectors(arguments)
                elif name == "get_detector_info":
                    return await self._get_detector_info(arguments)
                elif name == "analyze_issues":
                    return await self._analyze_issues(arguments)
                elif name == "get_configuration_schema":
                    return await self._get_configuration_schema(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.exception("Error handling tool call: %s", str(e))
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def _analyze_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze code for health issues."""
        path_str = arguments.get("path")
        if not path_str:
            raise ValueError("Path is required")
        
        path = Path(path_str).resolve()
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        # Initialize analyzer with detector filtering
        config = arguments.get("config", {})
        detector_ids = arguments.get("detectors")
        
        # Find the actual project root directory
        project_root = find_project_root(path)
        
        # Get or create config from the project root
        project_config = get_or_create_config(project_root)
        
        # Merge provided config with project config (provided config takes precedence)
        if project_config:
            merged_config = project_config.copy()
            merged_config.update(config)
            config = merged_config
        
        # Configure detectors using the same approach as CLI
        config = self._configure_detectors(config, detector_ids)
        
        analyzer = Analyzer(root_path=project_root, config=config)
        
        # Run analysis - always pass the path for specific analysis
        issues = analyzer.analyze([path])
        
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
        
        # Format output with better structure and guidance
        output_lines = [
            f"Pythonium Analysis Results",
            f"Path: {path}",
            f"Total issues found: {len(issues)}",
            f"Detectors used: {', '.join(detector_ids) if detector_ids else 'all available'}",
            "",
            "ISSUE BREAKDOWN BY SEVERITY:"
        ]
        
        for severity in ["error", "warn", "info"]:
            severity_issues = issues_by_severity[severity]
            if severity_issues:
                severity_icon = {"error": "ERROR", "warn": "WARN", "info": "INFO"}[severity]
                output_lines.append(f"\n{severity_icon} {severity.upper()} ({len(severity_issues)} issues):")
                for issue in severity_issues[:10]:  # Limit to first 10 per severity
                    location = ""
                    if issue.location:
                        location = f" at {issue.location.file}:{issue.location.line}"
                    output_lines.append(f"  • {issue.message}{location}")
                
                if len(severity_issues) > 10:
                    output_lines.append(f"  ... and {len(severity_issues) - 10} more {severity} issues")
          # Add guidance for next steps
        output_lines.extend([
            "",
            "NEXT STEPS:",
            "• Use 'analyze_issues' tool for detailed summary and recommendations",
            "• Focus on ERROR issues first (security, blocking problems)",
            "• Use 'get_detector_info' to understand specific detector findings",
            "• Use 'get_configuration_schema' to understand configuration options",
            f"• Re-run analysis with specific detectors for focused analysis"
        ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _list_detectors(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """List all available detectors with their comprehensive information."""
        # Use the detector information we already discovered
        detectors_info = self._detector_info
        
        if not detectors_info:
            return [types.TextContent(
                type="text",
                text="No detectors available. This indicates a system configuration issue."
            )]
        
        output_lines = [
            "Available Pythonium Code Health Detectors",
            f"Total detectors: {len(detectors_info)}",
            "",
            "Each detector specializes in finding specific types of code quality issues:",
            ""
        ]
        
        # Sort detectors by category for better organization
        categorized_detectors = self._categorize_detectors(detectors_info)
        
        for category, detectors in categorized_detectors.items():
            if detectors:
                output_lines.append(f"{category.upper()} ANALYSIS:")
                output_lines.append("")
                
                for detector_id in detectors:
                    if detector_id in detectors_info:
                        detector = detectors_info[detector_id]
                        # Use usage tips directly from detector metadata
                        usage_tip = detector.get("usage_tips", "")                        
                        output_lines.extend([
                            f"{detector_id}",
                            f"   {detector['name']}",
                            f"   {detector['description']}",
                            f"   {usage_tip}",
                            ""
                        ])
        
        output_lines.extend([
            "USAGE GUIDANCE:",
            "• Use 'get_detector_info <detector_id>' for detailed configuration options",
            "• Use 'get_configuration_schema' for complete configuration documentation",
            "• Run 'analyze_code' with specific detectors for focused analysis",
            "• Combine multiple detectors for comprehensive code review",
            "• Start with security and error-prone detectors for critical issues",
            "",
            "RECOMMENDED WORKFLOWS:",
            "• Security review: Use detectors containing 'security' or 'deprecated'",
            "• Code cleanup: Focus on 'dead_code', 'clone', and complexity detectors",
            "• Refactoring prep: Apply 'clone', 'semantic', and 'pattern' detectors",
            "• Architecture review: Use 'circular', 'inconsistent', and pattern detectors"
        ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    def _categorize_detectors(self, detectors_info: Dict[str, Any]) -> Dict[str, List[str]]:
        """Categorize detectors by their primary focus area using detector-provided categories."""
        categories = defaultdict(list)
        
        for detector_id, info in detectors_info.items():
            # Use the category provided by the detector itself, preserve original case
            category = info.get('category', 'Code Analysis')
            categories[category].append(detector_id)
        
        return dict(categories)
    
    async def _get_detector_info(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Get comprehensive information about a specific detector."""
        detector_id = arguments.get("detector_id")
        if not detector_id:
            raise ValueError("detector_id is required")
        
        # Get fresh analyzer instance with current detectors
        project_root = find_project_root(Path.cwd())
        config = get_or_create_config(project_root)
        analyzer = Analyzer(root_path=project_root, config=config)
        
        # Get actual available detectors
        available_detectors = list(analyzer.detectors.keys())
        
        # Validate detector ID
        if detector_id not in available_detectors:
            return [types.TextContent(
                type="text",
                text=f"Detector '{detector_id}' not found.\n\n"
                     f"Available detectors ({len(available_detectors)}):\n" + 
                     "\n".join([f"  • {d}" for d in sorted(available_detectors)]) +
                     "\n\nUse 'list_detectors' to see detailed descriptions for all detectors."
            )]
        
        # Get detector instance and detailed information
        detector = analyzer.get_detector(detector_id)
        if not detector:
            return [types.TextContent(
                type="text",
                text=f"Detector '{detector_id}' exists but could not be loaded.\n\n"
                     "This indicates a configuration or dependency issue."
            )]
        
        # Gather comprehensive detector information
        detector_info = self._get_comprehensive_detector_info(detector_id, detector)
        
        output_lines = [
            f"Detector Analysis: {detector_id}",
            f"Name: {detector.name}",
            f"Purpose: {detector.description}",
            f"Type: Core detector",
            ""
        ]
        
        # Add enhanced description and usage guidance
        if detector_info['category']:
            output_lines.extend([
                f"Category: {detector_info['category']}",
                ""
            ])
        
        output_lines.extend([
            "What it detects:",
            f"   {detector_info['detailed_description']}",
            ""
        ])
        
        # Add configuration information if available
        if detector_info['config_options']:
            output_lines.extend([
                "Configuration Options:",
                *[f"   • {opt}: {desc}" for opt, desc in detector_info['config_options'].items()],
                ""
            ])
        
        # Add usage recommendations
        output_lines.extend([
            "Best Use Cases:",
            f"   {detector_info['usage_tips']}",
            "",
            "Usage Examples:",
            f"   analyze_code --detectors {detector_id} <path>",
            f"   analyze_code --detectors {detector_id},security_smell <path>  # Combined analysis",
            ""
        ])
        
        # Add severity and impact information
        if detector_info['typical_severity']:
            output_lines.extend([
                "Typical Issue Severity:",
                f"   {detector_info['typical_severity']}",
                ""
            ])
        
        # Add related detectors
        if detector_info['related_detectors']:
            output_lines.extend([
                "Related Detectors:",
                *[f"   • {rel_id}: {rel_desc}" for rel_id, rel_desc in detector_info['related_detectors'].items()],
                ""
            ])
        
        output_lines.extend([
            "Integration Tips:",
            "• Run this detector as part of your regular code review process",
            "• Combine with related detectors for comprehensive analysis",
            "• Use specific configuration options to fine-tune sensitivity",
            "• Review findings in context of your project's coding standards"
        ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    def _get_comprehensive_detector_info(self, detector_id: str, detector) -> Dict[str, Any]:
        """Get comprehensive information about a detector using detector-provided metadata."""
        # Get the metadata directly from the detector instance
        category = getattr(detector, 'category', 'Code Analysis')
        detailed_description = getattr(detector, 'detailed_description', detector.description)
        usage_tips = getattr(detector, 'usage_tips', f"Use for analysis of {detector.description.lower()}")
        typical_severity = getattr(detector, 'typical_severity', 'info')
        related_detector_ids = getattr(detector, 'related_detectors', [])
        
        # Get configuration options
        config_options = self._extract_config_options(detector)
        
        # Build related detectors dict with descriptions
        related_detectors = {}
        for rel_id in related_detector_ids:
            if rel_id in self._detector_info:
                rel_info = self._detector_info[rel_id]
                related_detectors[rel_id] = rel_info.get('description', 'Related detector')
        
        # Format typical severity for display
        severity_display = {
            'error': "ERROR - Critical issues requiring immediate attention",
            'warn': "WARN - Important quality issues that should be addressed", 
            'info': "INFO - Suggestions for code improvement and optimization"
        }.get(typical_severity.lower(), f"{typical_severity.upper()} - Analysis findings")
        
        return {
            'category': category,
            'detailed_description': detailed_description,
            'config_options': config_options,
            'usage_tips': usage_tips,
            'typical_severity': severity_display,
            'related_detectors': related_detectors
        }
    
    def _extract_config_options(self, detector) -> Dict[str, str]:
        """Extract configuration options from a detector."""
        config_options = {}
        
        # Try to get configuration from detector constructor
        if hasattr(detector, '__init__'):
            import inspect
            try:
                sig = inspect.signature(detector.__init__)
                for param_name, param in sig.parameters.items():
                    if param_name not in ['self', 'settings', 'options']:
                        default_val = param.default if param.default != inspect.Parameter.empty else "No default"
                        config_options[param_name] = f"Default: {default_val}"
            except Exception:
                pass
        
        # Add common configuration hints
        if not config_options:
            config_options = {"enabled": "Whether this detector is active (true/false)"}
        
        return config_options
    
    async def _analyze_issues(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Provide analysis summary and recommendations."""
        path_str = arguments.get("path")
        if not path_str:
            raise ValueError("Path is required")
        
        path = Path(path_str).resolve()
        severity_filter = arguments.get("severity_filter", "info")
        
        # Find the actual project root directory
        project_root = find_project_root(path)
        
        # Get or create config for the project root
        project_config = get_or_create_config(project_root)
        
        # Run analysis
        analyzer = Analyzer(root_path=project_root, config=project_config)
        issues = analyzer.analyze([path] if path.is_file() else None)
        
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
                text=f"No issues found with severity '{severity_filter}' or higher.\n\nPath analyzed: {path}\nThis indicates good code health at the selected severity level.\n\nTip: Try lowering the severity filter to 'info' to see all findings."
            )]
        
        # Generate analysis summary
        issue_counts = {}
        detector_counts = {}
        
        for issue in filtered_issues:
            severity = issue.severity.lower()
            issue_counts[severity] = issue_counts.get(severity, 0) + 1
            
            detector_id = issue.detector_id or "unknown"
            detector_counts[detector_id] = detector_counts.get(detector_id, 0) + 1
        
        output_lines = [
            f"Pythonium Analysis Summary",
            f"Path: {path}",
            f"Issues found (severity >= {severity_filter}): {len(filtered_issues)}",
            f"Filter applied: {severity_filter.upper()} level and above",
            ""
        ]
        
        # Issue breakdown by severity with enhanced formatting
        output_lines.append("ISSUES BY SEVERITY:")
        severity_icons = {"error": "ERROR", "warn": "WARN", "info": "INFO"}
        for severity in ["error", "warn", "info"]:
            count = issue_counts.get(severity, 0)
            if count > 0:
                icon = severity_icons.get(severity, "•")
                output_lines.append(f"  {icon} {severity.upper()}: {count}")
        output_lines.append("")
        
        # Issues by detector with descriptions
        output_lines.append("ISSUES BY DETECTOR:")
        for detector_id, count in sorted(detector_counts.items(), key=lambda x: x[1], reverse=True):
            detector_info = self._detector_info.get(detector_id, {})
            short_desc = detector_info.get('description', detector_id.replace("_", " "))
            if short_desc and '.' in short_desc:
                short_desc = short_desc.split(".")[0]
            output_lines.append(f"  • {detector_id}: {count} ({short_desc})")
        output_lines.append("")
        
        # Enhanced recommendations with priorities
        output_lines.append("PRIORITIZED RECOMMENDATIONS:")
        priority_order = []
        
        if issue_counts.get("error", 0) > 0:
            priority_order.append("CRITICAL: Fix ERROR-level issues immediately (security, blocking problems)")
        if issue_counts.get("warn", 0) > 0:
            priority_order.append("HIGH: Address WARN-level issues for better code quality")
        if issue_counts.get("info", 0) > 0:
            priority_order.append("MEDIUM: Consider INFO-level suggestions for code improvements")
        
        # Add detector-specific recommendations based on actual detector info
        top_detector = max(detector_counts.items(), key=lambda x: x[1])[0] if detector_counts else None
        if top_detector and top_detector in self._detector_info:
            usage_tip = self._detector_info[top_detector].get('usage_tips', '')
            if usage_tip:
                priority_order.append(f"FOCUS: {usage_tip} (most common: {top_detector})")
        
        for i, recommendation in enumerate(priority_order, 1):
            output_lines.append(f"{i}. {recommendation}")
        
        output_lines.extend([
            "",
            "NEXT ACTIONS:",
            "• Use 'analyze_code' with specific detectors for focused analysis",
            "• Use 'get_detector_info' to understand detector findings in detail",
            "• Re-run analysis after fixes to track improvement",
            f"• Consider running with severity filter 'error' to focus on critical issues first"
        ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _analyze_inline_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze inline Python code for health issues."""
        import tempfile
        import os
        
        code = arguments.get("code")
        if not code:
            raise ValueError("Code is required")
        
        filename = arguments.get("filename", "temp_code.py")
        if not filename.endswith('.py'):
            filename += '.py'
        
        # Create temporary file with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, 
                                       prefix='pythonium_', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_path = Path(temp_file.name)
        
        try:
            # Get the directory containing the temp file as root path
            root_path = temp_path.parent
            
            # Initialize analyzer with detector filtering
            config = arguments.get("config", {})
            detector_ids = arguments.get("detectors")
            
            # Configure detectors using the same approach as CLI
            config = self._configure_detectors(config, detector_ids)
            
            analyzer = Analyzer(root_path=root_path, config=config)
            
            # Run analysis on the temporary file
            issues = analyzer.analyze([temp_path])
            
            # Format results with enhanced output for inline code
            if not issues:
                return [types.TextContent(
                    type="text",
                    text=f"No issues found in the analyzed code snippet.\n\nFile: {filename}\nDetectors used: {', '.join(detector_ids) if detector_ids else 'all available detectors'}\n\nThe code appears to be healthy according to the selected analysis criteria."
                )]
            
            # Group issues by severity and update file references
            issues_by_severity = {"error": [], "warn": [], "info": []}
            for issue in issues:
                # Create new issue with updated file reference
                if issue.location and issue.location.file:
                    from .models import Location, Issue
                    new_location = Location(
                        file=Path(filename),
                        line=issue.location.line,
                        column=issue.location.column,
                        end_line=issue.location.end_line,
                        end_column=issue.location.end_column
                    )
                    issue = Issue(
                        id=issue.id,
                        detector_id=issue.detector_id,
                        message=issue.message,
                        location=new_location,
                        severity=issue.severity,
                        symbol=issue.symbol,
                        metadata=issue.metadata
                    )
                
                severity = issue.severity.lower()
                if severity in issues_by_severity:
                    issues_by_severity[severity].append(issue)
            
            # Format output with enhanced structure
            output_lines = [
                f"Pythonium Analysis Results (Inline Code)",
                f"File: {filename}",
                f"Total issues found: {len(issues)}",
                f"Detectors used: {', '.join(detector_ids) if detector_ids else 'all available'}",
                "",
                "ISSUE BREAKDOWN BY SEVERITY:"
            ]
            
            for severity in ["error", "warn", "info"]:
                severity_issues = issues_by_severity[severity]
                if severity_issues:
                    severity_icon = {"error": "ERROR", "warn": "WARN", "info": "INFO"}[severity]
                    output_lines.append(f"\n{severity_icon} {severity.upper()} ({len(severity_issues)} issues):")
                    for issue in severity_issues[:10]:  # Limit to first 10 per severity
                        location = ""
                        if issue.location:
                            location = f" at line {issue.location.line}"
                        output_lines.append(f"  • {issue.message}{location}")
                    
                    if len(severity_issues) > 10:
                        output_lines.append(f"  ... and {len(severity_issues) - 10} more {severity} issues")
            
            # Add guidance for next steps
            output_lines.extend([
                "",
                "NEXT STEPS:",
                "• Fix ERROR issues first (security, blocking problems)",
                "• Use 'get_detector_info' to understand specific findings",
                "• Consider refactoring based on WARN and INFO suggestions",
                "• Re-analyze after making changes to verify improvements"
            ])
            
            return [types.TextContent(
                type="text",
                text="\n".join(output_lines)
            )]
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # Ignore cleanup errors
    
    def _setup_silent_logging(self) -> None:
        """Configure logging to be silent to avoid interference with MCP communication."""
        # Set logging level to WARNING to suppress INFO messages
        logging.getLogger().setLevel(logging.WARNING)
        # Also disable logging for the analyzer and related modules
        logging.getLogger("pythonium").setLevel(logging.WARNING)
    
    def _validate_detectors(self, detector_ids: List[str]) -> List[str]:
        """Validate detector IDs against currently available detectors.
        
        Args:
            detector_ids: List of detector IDs to validate
            
        Returns:
            List of valid detector IDs
        """
        if not detector_ids:
            return []
        
        # Get current available detectors
        available = self.available_detectors
        
        valid_detectors = []
        for detector_id in detector_ids:
            if detector_id in available:
                valid_detectors.append(detector_id)
            else:
                logger.warning("Unknown detector: %s. Available detectors: %s", 
                              detector_id, ", ".join(available))
        
        if not valid_detectors:
            logger.warning("No valid detectors provided from: %s. Available detectors: %s", 
                          detector_ids, ", ".join(available))
            return []
        
        return valid_detectors
    
    def _configure_detectors(self, config: Dict[str, Any], detector_ids: Optional[List[str]]) -> Dict[str, Any]:
        """Configure detectors in config based on detector IDs (matches CLI approach).
        
        Args:
            config: Configuration dictionary
            detector_ids: List of detector IDs to enable, or None for all
            
        Returns:
            Updated configuration dictionary
        """
        if not detector_ids:
            return config
        
        # Validate detector IDs
        valid_detector_ids = self._validate_detectors(detector_ids)
        if not valid_detector_ids:
            return config
        
        # Configure only specified detectors in config (matches CLI approach)
        if "detectors" not in config:
            config["detectors"] = {}
        
        # Get current available detectors
        available_detectors = self.available_detectors
        
        # Disable all detectors first, then enable only specified ones
        for detector_id in available_detectors:
            config["detectors"][detector_id] = {"enabled": False}
        
        # Enable specified detectors
        for detector_id in valid_detector_ids:
            config["detectors"][detector_id] = {"enabled": True}
        
        return config
    
    def _extract_config_options(self, detector) -> Dict[str, str]:
        """Extract configuration options from a detector."""
        config_options = {}
        
        # Try to get configuration from detector constructor
        if hasattr(detector, '__init__'):
            import inspect
            try:
                sig = inspect.signature(detector.__init__)
                for param_name, param in sig.parameters.items():
                    if param_name not in ['self', 'settings', 'options']:
                        default_val = param.default if param.default != inspect.Parameter.empty else "No default"
                        config_options[param_name] = f"Default: {default_val}"
            except Exception:
                pass
        
        # Add common configuration hints
        if not config_options:
            config_options = {"enabled": "Whether this detector is active (true/false)"}
        
        return config_options
    
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
        output_lines = [
            "Pythonium Configuration Schema",
            "=" * 35,
            "",
            "Pythonium uses YAML configuration files (.pythonium.yml) to customize analysis behavior.",
            "Configuration supports detector-specific settings, global options, and runtime overrides.",
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
            "3. RUNTIME OPTIONS - Environment and execution settings",
            "   • python_version: Target Python version compatibility",
            "   • parallel: Enable/disable parallel processing",
            "   • cache: Caching configuration",
            "",
            "CONFIGURATION STRUCTURE:",
            "",
            "```yaml",
            "# Basic structure of .pythonium.yml",
            "detectors:",
            "  detector_name:",
            "    enabled: true|false",
            "    option_name: value",
            "    severity: error|warn|info",
            "",
            "severity:",
            "  detector_name: error|warn|info",
            "",
            "ignore:",
            "  - \"**/pattern/**\"",
            "",
            "thresholds:",
            "  threshold_name: value",
            "",
            "suppression:",
            "  patterns:",
            "    category: [\"pattern1\", \"pattern2\"]",
            "",
            "output:",
            "  max_issues_per_detector: 50",
            "  enable_deduplication: true",
            "```",
            "",
            "QUICK START:",
            "• Use 'get_configuration_schema examples' for sample configurations",
            "• Use 'get_configuration_schema detectors' for detector-specific options", 
            "• Use 'get_configuration_schema global' for project-level settings",
            "• Use 'get_configuration_schema precedence' for configuration hierarchy",
            "",
            "CONFIGURATION SOURCES:",
            "1. Built-in defaults (lowest priority)",
            "2. .pythonium.yml configuration file",
            "3. Environment variables (PYTHONIUM_*)",
            "4. Runtime config overrides (highest priority)",
            "",
            f"AVAILABLE DETECTORS: {len(self.available_detectors)}",
            f"Detector IDs: {', '.join(sorted(self.available_detectors))}"
        ]
        
        return [types.TextContent(
            type="text",
            text="\n".join(output_lines)
        )]
    
    async def _get_detector_configurations(self) -> List[types.TextContent]:
        """Get detailed detector configuration options - placeholder method."""
        return [types.TextContent(
            type="text",
            text="Detector configuration documentation (placeholder - method not fully implemented yet)"
        )]
    
    async def _get_global_configurations(self) -> List[types.TextContent]:
        """Get global configuration options documentation - placeholder method."""
        return [types.TextContent(
            type="text",
            text="Global configuration documentation (placeholder - method not fully implemented yet)"
        )]
    
    async def _get_configuration_examples(self) -> List[types.TextContent]:
        """Get practical configuration examples - placeholder method."""
        return [types.TextContent(
            type="text",
            text="Configuration examples (placeholder - method not fully implemented yet)"
        )]
    
    async def _get_configuration_precedence(self) -> List[types.TextContent]:
        """Get configuration precedence documentation - placeholder method."""
        return [types.TextContent(
            type="text",
            text="Configuration precedence documentation (placeholder - method not fully implemented yet)"
        )]
    
    async def _get_configuration_validation(self) -> List[types.TextContent]:
        """Get configuration validation documentation - placeholder method."""
        return [types.TextContent(
            type="text",
            text="Configuration validation documentation (placeholder - method not fully implemented yet)"
        )]
    
    async def run_stdio(self):
        """Run the server using stdio transport."""
        try:
            async with mcp.server.stdio.stdio_server() as streams:
                read_stream, write_stream = streams
                init_options = InitializationOptions(
                    server_name=self.name,
                    server_version=self.version,
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability()
                    )
                )
                await self.server.run(
                    read_stream, 
                    write_stream, 
                    init_options
                )
        except Exception as e:
            logger.error("Error in run_stdio: %s", str(e))
            raise
    
    async def run_sse(self, host: str = "localhost", port: int = 8000):
        """Run the server using SSE transport."""
        # SSE transport is not yet fully implemented in current MCP version
        raise NotImplementedError("SSE transport is not yet available in this MCP version")


async def main_stdio():
    """Main entry point for stdio MCP server."""
    if not MCP_AVAILABLE:
        print("MCP dependencies not available. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)
    
    server = PythoniumMCPServer()
    await server.run_stdio()


async def main_sse(host: str = "localhost", port: int = 8000):
    """Main entry point for SSE MCP server."""
    if not MCP_AVAILABLE:
        print("MCP dependencies not available. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)
    
    server = PythoniumMCPServer()
    await server.run_sse(host, port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pythonium Crawler MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for SSE transport (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE transport (default: 8000)"
    )
    
    args = parser.parse_args()
    
    if args.transport == "stdio":
        asyncio.run(main_stdio())
    else:
        asyncio.run(main_sse(args.host, args.port))
