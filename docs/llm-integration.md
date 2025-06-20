# LLM Agent Integration

This guide covers integrating Pythonium with Large Language Model (LLM) agents and AI coding assistants for automated code analysis and improvement suggestions.

## Overview

Pythonium provides several integration points for LLM agents:

1. **MCP Server** - Model Context Protocol server for real-time analysis
2. **JSON API** - Structured output for agent processing
3. **SARIF Format** - Industry-standard results format
4. **Command-line Interface** - Direct CLI integration

## MCP Integration (Recommended)

The Model Context Protocol provides the most sophisticated integration with AI agents.

### Quick Setup

```bash
# Install with MCP support
pip install pythonium[mcp]

# Start MCP server
pythonium mcp-server --transport stdio
```

### Agent Configuration

#### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "pythonium": {
      "command": "pythonium",
      "args": ["mcp-server", "--transport", "stdio"],
      "cwd": "/path/to/your/workspace"
    }
  }
}
```

#### Custom Agent

```python
import asyncio
import json
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class AnalysisResult:
    issues: List[Dict]
    summary: Dict
    recommendations: List[str]

class PythoniumAgent:
    """AI agent with Pythonium integration."""
    
    def __init__(self):
        self.mcp_server = None
    
    async def analyze_codebase(self, path: str, focus_areas: List[str] = None) -> AnalysisResult:
        """Analyze codebase with AI-guided focus."""
        
        # Step 1: Get available detectors
        detectors_info = await self.call_tool("list_detectors", {})
        
        # Step 2: Select relevant detectors based on focus areas
        selected_detectors = self._select_detectors(detectors_info, focus_areas)
        
        # Step 3: Run targeted analysis
        analysis = await self.call_tool("analyze_code", {
            "path": path,
            "detectors": ",".join(selected_detectors)
        })
        
        # Step 4: Get analysis summary
        summary = await self.call_tool("analyze_issues", {
            "path": path,
            "severity_filter": "warn"
        })
        
        # Step 5: Generate AI recommendations
        recommendations = await self._generate_recommendations(analysis, summary)
        
        return AnalysisResult(
            issues=analysis["issues"],
            summary=summary,
            recommendations=recommendations
        )
    
    def _select_detectors(self, detectors_info: Dict, focus_areas: List[str]) -> List[str]:
        """AI-guided detector selection based on focus areas."""
        detector_mapping = {
            "security": ["security_smell", "deprecated_api"],
            "performance": ["complexity_hotspot", "semantic_equivalence"],
            "maintainability": ["dead_code", "clone", "inconsistent_api"],
            "architecture": ["circular_deps", "alt_implementation"],
            "code_quality": ["advanced_patterns", "block_clone"]
        }
        
        if not focus_areas:
            return list(detectors_info.keys())
        
        selected = []
        for area in focus_areas:
            selected.extend(detector_mapping.get(area, []))
        
        return list(set(selected))
    
    async def _generate_recommendations(self, analysis: Dict, summary: Dict) -> List[str]:
        """Generate AI-powered recommendations."""
        recommendations = []
        
        # Analyze issue patterns
        issue_counts = {}
        for issue in analysis["issues"]:
            detector = issue["metadata"]["detector_name"]
            issue_counts[detector] = issue_counts.get(detector, 0) + 1
        
        # Generate recommendations based on patterns
        if issue_counts.get("Security Smell Detector", 0) > 0:
            recommendations.append(
                "🔒 Security Review: Found potential security vulnerabilities. "
                "Prioritize fixing hardcoded credentials and unsafe operations."
            )
        
        if issue_counts.get("Dead Code Detector", 0) > 5:
            recommendations.append(
                "🧹 Code Cleanup: Significant amount of unused code detected. "
                "Consider removing dead code to improve maintainability."
            )
        
        if issue_counts.get("Clone Detector", 0) > 3:
            recommendations.append(
                "♻️ Refactoring: Multiple code duplications found. "
                "Extract common functionality into reusable functions or classes."
            )
        
        return recommendations
```

### Advanced Agent Patterns

#### Progressive Analysis

```python
class ProgressiveAnalysisAgent:
    """Agent that performs analysis in stages."""
    
    async def staged_analysis(self, path: str) -> Dict:
        """Perform analysis in progressive stages."""
        
        # Stage 1: Quick security scan
        security_issues = await self.call_tool("analyze_code", {
            "path": path,
            "detectors": "security_smell,deprecated_api"
        })
        
        # If critical security issues found, stop here
        critical_security = [
            i for i in security_issues["issues"] 
            if i["severity"] == "error"
        ]
        
        if critical_security:
            return {
                "stage": "security",
                "critical_issues": critical_security,
                "recommendation": "Fix critical security issues before proceeding"
            }
        
        # Stage 2: Code quality analysis
        quality_issues = await self.call_tool("analyze_code", {
            "path": path,
            "detectors": "dead_code,clone,complexity_hotspot"
        })
        
        # Stage 3: Architecture analysis
        arch_issues = await self.call_tool("analyze_code", {
            "path": path,
            "detectors": "circular_deps,inconsistent_api,alt_implementation"
        })
        
        # Combine and prioritize
        return self._prioritize_issues(security_issues, quality_issues, arch_issues)
```

#### Interactive Code Review

```python
class CodeReviewAgent:
    """Agent for interactive code review sessions."""
    
    async def review_pull_request(self, changed_files: List[str]) -> Dict:
        """Review changed files in a pull request."""
        
        review_results = []
        
        for file_path in changed_files:
            # Analyze individual file
            file_analysis = await self.call_tool("analyze_code", {
                "path": file_path
            })
            
            # Generate file-specific review comments
            comments = self._generate_review_comments(file_analysis)
            
            review_results.append({
                "file": file_path,
                "issues": file_analysis["issues"],
                "comments": comments,
                "approval_status": self._determine_approval(file_analysis)
            })
        
        return {
            "overall_status": self._overall_review_status(review_results),
            "file_reviews": review_results,
            "summary": self._generate_review_summary(review_results)
        }
    
    def _generate_review_comments(self, analysis: Dict) -> List[Dict]:
        """Generate human-friendly review comments."""
        comments = []
        
        for issue in analysis["issues"]:
            if issue["severity"] == "error":
                comment_type = "change_requested"
                prefix = "🚨 Critical:"
            elif issue["severity"] == "warn":
                comment_type = "suggestion"
                prefix = "⚠️ Warning:"
            else:
                comment_type = "comment"
                prefix = "💡 Suggestion:"
            
            comments.append({
                "type": comment_type,
                "line": issue["location"]["line"],
                "message": f"{prefix} {issue['message']}",
                "suggestion": self._generate_fix_suggestion(issue)
            })
        
        return comments
```

## JSON API Integration

For agents that prefer structured data over MCP:

### Basic Integration

```python
import subprocess
import json
from typing import List, Dict

class JSONAPIAgent:
    """Agent using Pythonium JSON output."""
    
    def analyze_code(self, path: str, detectors: List[str] = None) -> Dict:
        """Run analysis and get JSON results."""
        
        cmd = ["pythonium", "crawl", path, "--format", "json", "--silent"]
        
        if detectors:
            cmd.extend(["--detectors", ",".join(detectors)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Analysis failed: {result.stderr}")
        
        return json.loads(result.stdout)
    
    def process_issues(self, issues: List[Dict]) -> Dict:
        """Process and categorize issues."""
        
        categorized = {
            "security": [],
            "maintainability": [],
            "performance": [],
            "style": []
        }
        
        category_mapping = {
            "security_smell": "security",
            "deprecated_api": "security",
            "dead_code": "maintainability",
            "clone": "maintainability",
            "complexity_hotspot": "performance",
            "semantic_equivalence": "performance",
            "inconsistent_api": "style",
            "advanced_patterns": "style"
        }
        
        for issue in issues:
            detector_id = issue["id"].split(".")[0]
            category = category_mapping.get(detector_id, "other")
            categorized.setdefault(category, []).append(issue)
        
        return categorized
    
    def generate_report(self, path: str) -> str:
        """Generate AI-powered analysis report."""
        
        issues = self.analyze_code(path)
        categorized = self.process_issues(issues)
        
        report = f"# Code Analysis Report for {path}\n\n"
        
        # Executive summary
        total_issues = len(issues)
        report += f"**Total Issues Found:** {total_issues}\n\n"
        
        # Category breakdown
        for category, category_issues in categorized.items():
            if category_issues:
                report += f"## {category.title()} Issues ({len(category_issues)})\n\n"
                
                for issue in category_issues[:5]:  # Show top 5 per category
                    report += f"- **{issue['location']['file']}:{issue['location']['line']}** "
                    report += f"- {issue['message']}\n"
                
                if len(category_issues) > 5:
                    report += f"- ... and {len(category_issues) - 5} more\n"
                
                report += "\n"
        
        # Recommendations
        report += "## Recommendations\n\n"
        report += self._generate_recommendations(categorized)
        
        return report
```

### Batch Processing

```python
class BatchAnalysisAgent:
    """Agent for processing multiple projects."""
    
    def analyze_multiple_projects(self, projects: List[str]) -> Dict:
        """Analyze multiple projects and compare results."""
        
        results = {}
        
        for project in projects:
            try:
                issues = self.analyze_code(project)
                results[project] = {
                    "status": "success",
                    "issues": issues,
                    "metrics": self._calculate_metrics(issues)
                }
            except Exception as e:
                results[project] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "projects": results,
            "comparison": self._compare_projects(results)
        }
    
    def _calculate_metrics(self, issues: List[Dict]) -> Dict:
        """Calculate code quality metrics."""
        
        severity_counts = {"error": 0, "warn": 0, "info": 0}
        detector_counts = {}
        
        for issue in issues:
            severity_counts[issue["severity"]] += 1
            
            detector = issue["id"].split(".")[0]
            detector_counts[detector] = detector_counts.get(detector, 0) + 1
        
        return {
            "total_issues": len(issues),
            "by_severity": severity_counts,
            "by_detector": detector_counts,
            "quality_score": self._calculate_quality_score(severity_counts)
        }
    
    def _calculate_quality_score(self, severity_counts: Dict) -> float:
        """Calculate overall quality score (0-100)."""
        
        total = sum(severity_counts.values())
        if total == 0:
            return 100.0
        
        # Weight errors more heavily
        weighted_score = (
            severity_counts["error"] * 3 +
            severity_counts["warn"] * 1 +
            severity_counts["info"] * 0.1
        )
        
        # Normalize to 0-100 scale (assuming max 1 issue per 10 lines)
        normalized = max(0, 100 - (weighted_score / total * 100))
        
        return round(normalized, 1)
```

## CI/CD Integration

### GitHub Actions with AI Analysis

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0  # Full history for better analysis
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Pythonium
      run: pip install pythonium[mcp]
    
    - name: Run AI-Powered Analysis
      run: |
        python scripts/ai_review.py \
          --base-branch ${{ github.event.pull_request.base.ref }} \
          --head-branch ${{ github.event.pull_request.head.ref }} \
          --output review_comments.json
    
    - name: Post Review Comments
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const comments = JSON.parse(fs.readFileSync('review_comments.json'));
          
          for (const comment of comments) {
            await github.rest.pulls.createReviewComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number,
              body: comment.message,
              path: comment.path,
              line: comment.line
            });
          }
```

### AI Review Script

```python
#!/usr/bin/env python3
"""AI-powered code review script for CI/CD."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

class AICodeReviewer:
    def __init__(self):
        self.pythonium_available = self._check_pythonium()
    
    def _check_pythonium(self) -> bool:
        """Check if Pythonium is available."""
        try:
            subprocess.run(["pythonium", "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_changed_files(self, base_branch: str, head_branch: str) -> List[str]:
        """Get list of Python files changed in PR."""
        
        cmd = [
            "git", "diff", "--name-only", 
            f"origin/{base_branch}...origin/{head_branch}",
            "*.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return [
            line.strip() for line in result.stdout.split('\n')
            if line.strip() and line.endswith('.py')
        ]
    
    def analyze_changed_files(self, files: List[str]) -> Dict:
        """Analyze changed files for issues."""
        
        if not files:
            return {"issues": [], "summary": "No Python files changed"}
        
        # Analyze all changed files
        cmd = [
            "pythonium", "crawl", 
            "--format", "json",
            "--silent",
            "--detectors", "security_smell,dead_code,clone,complexity_hotspot"
        ] + files
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"error": f"Analysis failed: {result.stderr}"}
        
        return json.loads(result.stdout)
    
    def generate_review_comments(self, analysis: Dict, 
                               changed_files: List[str]) -> List[Dict]:
        """Generate review comments from analysis."""
        
        comments = []
        
        for issue in analysis.get("issues", []):
            location = issue.get("location", {})
            file_path = location.get("file")
            
            # Only comment on changed files
            if file_path not in changed_files:
                continue
            
            # Generate appropriate comment based on severity
            if issue["severity"] == "error":
                emoji = "🚨"
                priority = "Critical"
            elif issue["severity"] == "warn":
                emoji = "⚠️"
                priority = "Warning"
            else:
                emoji = "💡"
                priority = "Suggestion"
            
            comment = {
                "path": file_path,
                "line": location.get("line", 1),
                "message": f"{emoji} **{priority}**: {issue['message']}\n\n"
                          f"*Detected by {issue['metadata']['detector_name']}*"
            }
            
            # Add fix suggestion if available
            fix_suggestion = self._generate_fix_suggestion(issue)
            if fix_suggestion:
                comment["message"] += f"\n\n**Suggested fix:**\n{fix_suggestion}"
            
            comments.append(comment)
        
        return comments
    
    def _generate_fix_suggestion(self, issue: Dict) -> str:
        """Generate fix suggestions based on issue type."""
        
        detector_id = issue["id"].split(".")[0]
        
        suggestions = {
            "security_smell": "Consider using environment variables or a secrets management system.",
            "dead_code": "Remove this unused code to improve maintainability.",
            "clone": "Extract common functionality into a reusable function or class.",
            "complexity_hotspot": "Consider breaking this function into smaller, more focused functions."
        }
        
        return suggestions.get(detector_id, "")

def main():
    parser = argparse.ArgumentParser(description="AI-powered code review")
    parser.add_argument("--base-branch", required=True, help="Base branch name")
    parser.add_argument("--head-branch", required=True, help="Head branch name")
    parser.add_argument("--output", required=True, help="Output file for comments")
    
    args = parser.parse_args()
    
    reviewer = AICodeReviewer()
    
    if not reviewer.pythonium_available:
        print("Pythonium not available, skipping AI review")
        sys.exit(0)
    
    # Get changed files
    changed_files = reviewer.get_changed_files(args.base_branch, args.head_branch)
    
    if not changed_files:
        print("No Python files changed")
        with open(args.output, 'w') as f:
            json.dump([], f)
        sys.exit(0)
    
    # Analyze changed files
    analysis = reviewer.analyze_changed_files(changed_files)
    
    if "error" in analysis:
        print(f"Analysis error: {analysis['error']}")
        sys.exit(1)
    
    # Generate review comments
    comments = reviewer.generate_review_comments(analysis, changed_files)
    
    # Save comments
    with open(args.output, 'w') as f:
        json.dump(comments, f, indent=2)
    
    print(f"Generated {len(comments)} review comments")

if __name__ == "__main__":
    main()
```

## Best Practices for LLM Integration

### 1. Progressive Analysis

Start with high-priority detectors and progressively add more based on results:

```python
analysis_stages = [
    ["security_smell", "deprecated_api"],  # Security first
    ["dead_code", "complexity_hotspot"],   # Quality issues
    ["clone", "inconsistent_api"],         # Maintainability
    ["advanced_patterns", "semantic_equivalence"]  # Optimization
]
```

### 2. Context-Aware Detection

Adapt analysis based on project context:

```python
def select_detectors_by_context(project_path: str) -> List[str]:
    """Select detectors based on project characteristics."""
    
    detectors = ["dead_code", "security_smell"]  # Always include these
    
    # Check for web frameworks
    if has_flask_or_django(project_path):
        detectors.extend(["deprecated_api", "inconsistent_api"])
    
    # Check for data science libraries
    if has_data_science_libs(project_path):
        detectors.extend(["complexity_hotspot", "semantic_equivalence"])
    
    # Check project size
    if get_project_size(project_path) > 10000:  # Large project
        detectors.extend(["clone", "circular_deps"])
    
    return detectors
```

### 3. Intelligent Prioritization

Prioritize issues based on impact and effort:

```python
def prioritize_issues(issues: List[Dict]) -> List[Dict]:
    """Prioritize issues by impact and effort."""
    
    priority_scores = []
    
    for issue in issues:
        impact = get_impact_score(issue)
        effort = get_effort_score(issue)
        priority = impact / effort  # High impact, low effort = high priority
        
        priority_scores.append((priority, issue))
    
    # Sort by priority (highest first)
    priority_scores.sort(key=lambda x: x[0], reverse=True)
    
    return [issue for priority, issue in priority_scores]
```

### 4. Learning and Adaptation

Implement feedback loops to improve analysis:

```python
class AdaptiveLLMAgent:
    def __init__(self):
        self.feedback_history = []
        self.detector_effectiveness = {}
    
    def record_feedback(self, issue_id: str, was_helpful: bool):
        """Record whether an issue was helpful."""
        self.feedback_history.append({
            "issue_id": issue_id,
            "helpful": was_helpful,
            "timestamp": datetime.now()
        })
        
        # Update detector effectiveness
        detector = issue_id.split(".")[0]
        if detector not in self.detector_effectiveness:
            self.detector_effectiveness[detector] = {"helpful": 0, "total": 0}
        
        self.detector_effectiveness[detector]["total"] += 1
        if was_helpful:
            self.detector_effectiveness[detector]["helpful"] += 1
    
    def get_recommended_detectors(self) -> List[str]:
        """Get detectors based on historical effectiveness."""
        effective_detectors = []
        
        for detector, stats in self.detector_effectiveness.items():
            if stats["total"] >= 5:  # Minimum sample size
                effectiveness = stats["helpful"] / stats["total"]
                if effectiveness >= 0.7:  # 70% helpful threshold
                    effective_detectors.append(detector)
        
        return effective_detectors or ["security_smell", "dead_code"]  # Fallback
```

This comprehensive integration guide enables LLM agents to leverage Pythonium's powerful analysis capabilities for intelligent, context-aware code review and improvement suggestions.
