"""
Analysis and reporting tools for the Pythonium MCP server.
Contains methods for analyzing issues, detector info, and reporting.
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .debug import info_log


async def list_detectors(server, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """List all available detectors."""
    # Implementation similar to original but simplified
    output_lines = [
        "Available Pythonium Code Health Detectors",
        f"Total detectors: {len(server._detector_info)}",
        ""
    ]
    
    for detector_id, info in server._detector_info.items():
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


async def get_detector_info(server, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get information about a specific detector."""
    detector_id = arguments.get("detector_id")
    if not detector_id or detector_id not in server._detector_info:
        return [types.TextContent(
            type="text",
            text=f"Detector '{detector_id}' not found. Available: {', '.join(server.available_detectors)}"
        )]
    
    info = server._detector_info[detector_id]
    return [types.TextContent(
        type="text",
        text=f"Detector: {info['name']}\nDescription: {info['description']}"
    )]


async def analyze_issues(server, arguments: Dict[str, Any]) -> List[types.TextContent]:
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
    if path_key in server.handlers._analysis_results:
        issues = server.handlers._analysis_results[path_key]
    # If not found, try the original path string (fallback for inline code)
    elif path_str in server.handlers._analysis_results:
        issues = server.handlers._analysis_results[path_str]
        path_key = path_str
    # If still not found, try to match by filename for inline code
    else:
        filename = Path(path_str).name
        matching_keys = [key for key in server.handlers._analysis_results.keys() if Path(key).name == filename]
        if matching_keys:
            path_key = matching_keys[0]
            issues = server.handlers._analysis_results[path_key]
        else:
            return [types.TextContent(
                type="text",
                text=f"No previous analysis results found for path: {path}\n\n"
                     "Please run 'analyze_code' on this path first to generate analysis results.\n\n"
                     "Available analyzed paths:\n" + 
                     "\n".join([f"  • {p}" for p in server.handlers._analysis_results.keys()]) if server.handlers._analysis_results else
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
        detector_info = server._detector_info.get(detector_id, {})
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
    if top_detector and top_detector in server._detector_info:
        detector_info = server._detector_info[top_detector]
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


async def debug_profile(server, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Return profiling information for debugging."""
    from .debug import profiler
    
    reset = arguments.get("reset", False)
    
    report = profiler.get_report()
    
    if reset:
        profiler.operations.clear()
        report += "\n\nProfiling data has been reset."
    
    return [types.TextContent(
        type="text",
        text=report
    )]
