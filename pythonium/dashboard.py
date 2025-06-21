"""HTML dashboard generator for pythonium reports."""

import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from string import Template

from .models import Issue

logger = logging.getLogger(__name__)

# Path to the template directory
TEMPLATE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "templates"
# Log the absolute path of the template directory for debugging
logger.info("Template directory path: %s", os.path.abspath(TEMPLATE_DIR))
# Make sure the template directory exists
if not TEMPLATE_DIR.exists():
    logger.info("Creating template directory")
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def generate_html_report(issues: List[Issue], output_path: Path, root_path: Path) -> None:
    """Generate an HTML dashboard showing code health metrics."""
    logger.info("Generating HTML report to %s", output_path)
    
    # Prepare data for the dashboard
    dashboard_data = _prepare_dashboard_data(issues, root_path)
    
    # Generate HTML content
    html_content = _generate_html_content(dashboard_data)
    
    # Write to file
    output_path.write_text(html_content, encoding='utf-8')
    logger.info("HTML report generated successfully")


def _prepare_dashboard_data(issues: List[Issue], root_path: Path) -> Dict[str, Any]:
    """Prepare data for the HTML dashboard."""
    # Convert root_path to absolute for consistent comparison
    root_path_abs = root_path.absolute()
    
    # Group issues by various dimensions
    issues_by_severity = defaultdict(list)
    issues_by_detector = defaultdict(list)
    issues_by_file = defaultdict(list)
    
    for issue in issues:
        issues_by_severity[issue.severity].append(issue)
        issues_by_detector[issue.detector_id or "unknown"].append(issue)
        
        if issue.location:
            try:
                rel_path = str(issue.location.file.relative_to(root_path_abs))
                issues_by_file[rel_path].append(issue)
            except ValueError:
                # Fallback to just the filename if relative_to fails
                issues_by_file[issue.location.file.name].append(issue)    # Calculate summary statistics
    total_issues = len(issues)
    multi_file_issues = [issue for issue in issues if issue.is_multi_file]
    severity_counts = {severity: len(issues_list) for severity, issues_list in issues_by_severity.items()}
    detector_counts = {detector: len(issues_list) for detector, issues_list in issues_by_detector.items()}    # Prepare file data for treemap
    file_data = []
    for file_path, file_issues in issues_by_file.items():
        file_multi_file_issues = [issue for issue in file_issues if issue.is_multi_file]
        file_data.append({
            'name': file_path,
            'size': len(file_issues),
            'multi_file_issues': len(file_multi_file_issues),
            'issues': [_issue_to_dict(issue, root_path_abs) for issue in file_issues]
        })
    
    # Sort files by issue count
    file_data.sort(key=lambda x: x['size'], reverse=True)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'root_path': str(root_path),        'summary': {
            'total_issues': total_issues,
            'multi_file_issues': len(multi_file_issues),
            'severity_counts': severity_counts,
            'detector_counts': detector_counts,
            'files_affected': len(issues_by_file)
        },
        'files': file_data,
        'issues_by_detector': {
            detector: [_issue_to_dict(issue, root_path_abs) for issue in issues_list]
            for detector, issues_list in issues_by_detector.items()
        }
    }


def _issue_to_dict(issue: Issue, root_path: Path) -> Dict[str, Any]:
    """Convert an Issue to a dictionary for JSON serialization."""
    issue_dict = {
        'id': issue.id,
        'severity': issue.severity,
        'message': issue.message,
        'detector_id': issue.detector_id,
        'metadata': issue.metadata or {},
        'is_multi_file': issue.is_multi_file,
        'related_files': [str(f) for f in issue.related_files] if issue.related_files else []
    }
    
    if issue.location:
        try:
            # root_path should already be absolute when passed to this function
            rel_path = str(issue.location.file.relative_to(root_path))
        except ValueError:
            # Fallback to just the filename if relative_to fails
            rel_path = issue.location.file.name
        
        issue_dict['location'] = {
            'file': rel_path,
            'line': issue.location.line,
            'column': issue.location.column or 0,
            'end_line': issue.location.end_line,
            'end_column': issue.location.end_column
        }
    if issue.symbol:
        if issue.symbol.module_name and issue.symbol.name:
            issue_dict['symbol'] = f"{issue.symbol.module_name}.{issue.symbol.name}"
        else:
            issue_dict['symbol'] = issue.symbol.name
    
    return issue_dict


def _generate_html_content(data: Dict[str, Any]) -> str:
    """Generate the HTML content for the dashboard."""
    # Load the template from file
    template_path = TEMPLATE_DIR / "dashboard.html"
    logger.info("Looking for template at %s", template_path)
    
    if not template_path.exists():
        logger.error("Dashboard template not found at %s", template_path)
        raise FileNotFoundError(f"Dashboard template not found at {template_path}")
    
    logger.info("Template found, reading content")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    if not template_content.strip():
        logger.error("Template file is empty")
        raise ValueError("Dashboard template file is empty")
        
    logger.info("Template content loaded successfully, length: %d", len(template_content))
    
    # Use string.Template for safer substitution
    template = Template(template_content)      # Generate file list HTML
    file_list_html = ""
    for file_data in data['files'][:20]:  # Show top 20 files
        severity_counts = defaultdict(int)
        multi_file_count = 0
        for issue in file_data['issues']:
            severity_counts[issue['severity']] += 1
            if issue.get('is_multi_file', False):
                multi_file_count += 1
        
        # Create metric badges
        badges_html = ""
        if severity_counts.get('error', 0) > 0:
            badges_html += f'<span class="metric-badge error">{severity_counts["error"]} errors</span>'
        if severity_counts.get('warn', 0) > 0 or severity_counts.get('warning', 0) > 0:
            warn_count = severity_counts.get('warn', 0) + severity_counts.get('warning', 0)
            badges_html += f'<span class="metric-badge warn">{warn_count} warnings</span>'
        if severity_counts.get('info', 0) > 0:
            badges_html += f'<span class="metric-badge info">{severity_counts["info"]} info</span>'
        if multi_file_count > 0:
            badges_html += f'<span class="metric-badge multi-file">{multi_file_count} multi-file</span>'          # Create issues detail HTML
        issues_html = ""
        for issue in file_data['issues'][:10]:  # Show top 10 issues per file
            # Get location info safely
            location_info = issue.get('location', {})
            line_number = location_info.get('line', '?') if location_info else '?'
            
            # Add multi-file indicator
            multi_file_indicator = ""
            if issue.get('is_multi_file', False):
                multi_file_indicator = ' <span class="metric-badge multi-file">multi-file</span>'
            
            issues_html += f"""
            <div class="issue-item {issue['severity']}">
                <div class="issue-header">
                    <span class="issue-severity {issue['severity']}">{issue['severity'].upper()}</span>
                    <span class="issue-location">Line {line_number}{multi_file_indicator}</span>
                </div>
                <div class="issue-message">{issue['message']}</div>
                <div class="issue-detector">{issue.get('detector_id', 'unknown').replace('_', ' ').title()}</div>
            </div>
            """
        
        file_list_html += f"""
        <div class="file-item">
            <div class="file-header">
                <div class="file-name" title="{file_data['name']}">{file_data['name']}</div>
                <div class="file-metrics">{badges_html}</div>
            </div>
            <div class="file-issues">{issues_html}</div>
        </div>
        """      # Substitute values in the template
    try:
        return template.safe_substitute(
            timestamp=data['timestamp'],
            total_issues=data['summary']['total_issues'],
            files_affected=data['summary']['files_affected'],
            multi_file_issues=data['summary']['multi_file_issues'],
            error_count=data['summary']['severity_counts'].get('error', 0),
            warn_count=data['summary']['severity_counts'].get('warn', 0) + data['summary']['severity_counts'].get('warning', 0),
            info_count=data['summary']['severity_counts'].get('info', 0),
            detector_count=len(data['summary']['detector_counts']),
            file_list_html=file_list_html,
            data_json=json.dumps(data)
        )
    except Exception as e:
        logger.error("Template substitution failed: %s", e)
        raise
