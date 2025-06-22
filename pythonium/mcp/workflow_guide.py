"""
Workflow guidance for Pythonium agent interactions.

This module provides intelligent workflow guidance to help agents
navigate through effective issue resolution patterns.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .response_formatter import WorkflowStage, ActionSuggestion, ResponseType


class IssueComplexity(Enum):
    """Complexity levels for issues."""
    TRIVIAL = "trivial"
    SIMPLE = "simple" 
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


@dataclass
class WorkflowPlan:
    """A suggested workflow plan for issue resolution."""
    stages: List[WorkflowStage]
    estimated_effort: str  # "5 minutes", "1 hour", "half day", etc.
    complexity: IssueComplexity
    prerequisites: List[str]
    success_criteria: List[str]
    risk_factors: List[str]


class WorkflowGuide:
    """Provides intelligent workflow guidance for agents."""
    
    def __init__(self):
        self.stage_transitions = {
            WorkflowStage.DISCOVERY: [WorkflowStage.INVESTIGATION],
            WorkflowStage.INVESTIGATION: [WorkflowStage.CLASSIFICATION, WorkflowStage.DISCOVERY],
            WorkflowStage.CLASSIFICATION: [WorkflowStage.RESOLUTION, WorkflowStage.COMPLETION],
            WorkflowStage.RESOLUTION: [WorkflowStage.VERIFICATION, WorkflowStage.INVESTIGATION],
            WorkflowStage.VERIFICATION: [WorkflowStage.COMPLETION, WorkflowStage.RESOLUTION],
            WorkflowStage.COMPLETION: [WorkflowStage.DISCOVERY]
        }
        
        self.complexity_indicators = {
            # File patterns that indicate complexity
            "architecture_files": ["__init__.py", "setup.py", "config", "settings"],
            "critical_modules": ["auth", "security", "crypto", "payment"],
            "integration_points": ["api", "client", "server", "protocol"],
            "performance_critical": ["performance", "cache", "optimization"],
        }
        
        self.detector_complexity_map = {
            # Map detector types to complexity levels
            "dead-code": IssueComplexity.SIMPLE,
            "stub-implementation": IssueComplexity.MODERATE,
            "circular-deps": IssueComplexity.COMPLEX,
            "security-smell": IssueComplexity.CRITICAL,
            "complexity-hotspot": IssueComplexity.MODERATE,
            "deprecated-api": IssueComplexity.SIMPLE,
            "inconsistent-api": IssueComplexity.MODERATE,
            "clone": IssueComplexity.SIMPLE,
            "block-clone": IssueComplexity.MODERATE,
            "semantic-equivalence": IssueComplexity.COMPLEX,
            "alt-implementation": IssueComplexity.MODERATE,
            "advanced-patterns": IssueComplexity.COMPLEX,
        }
    
    def assess_issue_complexity(
        self,
        issue: Dict,
        project_context: Dict = None
    ) -> IssueComplexity:
        """Assess the complexity level of an issue."""
        
        # Start with detector-based complexity
        detector_id = issue.get("detector_id", "")
        base_complexity = self.detector_complexity_map.get(
            detector_id, IssueComplexity.MODERATE
        )
        
        # Adjust based on file context
        file_path = issue.get("file_path", "")
        
        # Critical files increase complexity
        for pattern_type, patterns in self.complexity_indicators.items():
            if any(pattern in file_path.lower() for pattern in patterns):
                if pattern_type == "critical_modules":
                    return IssueComplexity.CRITICAL
                elif pattern_type == "architecture_files":
                    # Increase complexity by one level
                    complexity_order = [
                        IssueComplexity.TRIVIAL,
                        IssueComplexity.SIMPLE,
                        IssueComplexity.MODERATE,
                        IssueComplexity.COMPLEX,
                        IssueComplexity.CRITICAL
                    ]
                    current_idx = complexity_order.index(base_complexity)
                    return complexity_order[min(current_idx + 1, len(complexity_order) - 1)]
        
        # Consider issue message for additional indicators
        message = issue.get("message", "").lower()
        
        if any(keyword in message for keyword in ["security", "vulnerability", "exploit"]):
            return IssueComplexity.CRITICAL
        
        if any(keyword in message for keyword in ["performance", "memory", "leak"]):
            return IssueComplexity.COMPLEX
        
        # Consider project context
        if project_context:
            total_issues = project_context.get("total_issues", 0)
            if total_issues > 100:  # Large codebase
                complexity_order = [
                    IssueComplexity.TRIVIAL,
                    IssueComplexity.SIMPLE,
                    IssueComplexity.MODERATE,
                    IssueComplexity.COMPLEX,
                    IssueComplexity.CRITICAL
                ]
                current_idx = complexity_order.index(base_complexity)
                return complexity_order[min(current_idx + 1, len(complexity_order) - 1)]
        
        return base_complexity
    
    def create_workflow_plan(
        self,
        issues: List[Dict],
        current_stage: WorkflowStage,
        project_context: Dict = None
    ) -> WorkflowPlan:
        """Create a workflow plan for resolving issues."""
        
        if not issues:
            return WorkflowPlan(
                stages=[WorkflowStage.COMPLETION],
                estimated_effort="Complete",
                complexity=IssueComplexity.TRIVIAL,
                prerequisites=[],
                success_criteria=["No issues remaining"],
                risk_factors=[]
            )
        
        # Assess overall complexity
        complexities = [self.assess_issue_complexity(issue, project_context) for issue in issues]
        max_complexity = max(complexities, key=lambda x: list(IssueComplexity).index(x))
        
        # Count issues by classification/status
        unclassified = sum(1 for issue in issues if issue.get("classification") == "unclassified")
        pending = sum(1 for issue in issues if issue.get("status") == "pending")
        in_progress = sum(1 for issue in issues if issue.get("status") == "work_in_progress")
        
        # Determine workflow stages needed
        stages = []
        effort_estimates = []
        prerequisites = []
        success_criteria = []
        risk_factors = []
        
        if current_stage == WorkflowStage.DISCOVERY:
            stages.append(WorkflowStage.INVESTIGATION)
            effort_estimates.append("investigation: 10-30 min")
            prerequisites.append("Issues have been discovered through analysis")
            success_criteria.append("All issues have been investigated for context")
        
        if unclassified > 0 or current_stage in [WorkflowStage.INVESTIGATION, WorkflowStage.DISCOVERY]:
            stages.append(WorkflowStage.CLASSIFICATION)
            effort_estimates.append(f"classification: {unclassified * 2}-{unclassified * 5} min")
            prerequisites.append("Issues have been investigated")
            success_criteria.append("All issues classified as true/false positives")
        
        # Only include resolution stages for true positives
        true_positives = [issue for issue in issues if issue.get("classification") == "true_positive"]
        
        if true_positives:
            if pending > 0 or in_progress > 0:
                stages.append(WorkflowStage.RESOLUTION)
                
                # Estimate effort based on complexity
                complexity_time_map = {
                    IssueComplexity.TRIVIAL: "5-15 min per issue",
                    IssueComplexity.SIMPLE: "15-45 min per issue", 
                    IssueComplexity.MODERATE: "1-3 hours per issue",
                    IssueComplexity.COMPLEX: "half day per issue",
                    IssueComplexity.CRITICAL: "1-3 days per issue"
                }
                effort_estimates.append(f"resolution: {complexity_time_map[max_complexity]}")
                
                prerequisites.append("Issues classified as true positives")
                success_criteria.append("All code changes implemented")
                
                # Add risk factors based on complexity
                if max_complexity in [IssueComplexity.COMPLEX, IssueComplexity.CRITICAL]:
                    risk_factors.extend([
                        "Changes may affect system architecture",
                        "Extensive testing required",
                        "May require team coordination"
                    ])
                    
                if any("security" in str(issue).lower() for issue in issues):
                    risk_factors.append("Security implications require careful review")
            
            stages.append(WorkflowStage.VERIFICATION)
            effort_estimates.append("verification: 5-15 min")
            prerequisites.append("Code changes have been implemented")
            success_criteria.append("Re-analysis shows issues are resolved")
        
        stages.append(WorkflowStage.COMPLETION)
        success_criteria.append("All workflow stages completed successfully")
        
        # Calculate total effort estimate
        if len(effort_estimates) <= 1:
            total_effort = effort_estimates[0] if effort_estimates else "Minimal"
        elif max_complexity == IssueComplexity.CRITICAL:
            total_effort = "Multiple days"
        elif max_complexity == IssueComplexity.COMPLEX:
            total_effort = "1-2 days"
        elif len(issues) > 10:
            total_effort = "Half day to full day"
        else:
            total_effort = "1-4 hours"
        
        return WorkflowPlan(
            stages=stages,
            estimated_effort=total_effort,
            complexity=max_complexity,
            prerequisites=prerequisites,
            success_criteria=success_criteria,
            risk_factors=risk_factors
        )
    
    def suggest_next_actions(
        self,
        current_stage: WorkflowStage,
        issues: List[Dict],
        project_context: Dict = None
    ) -> List[ActionSuggestion]:
        """Suggest next actions based on current workflow stage and context."""
        
        suggestions = []
        
        if current_stage == WorkflowStage.DISCOVERY:
            suggestions.extend([
                ActionSuggestion(
                    action="investigate_all",
                    description="Investigate all discovered issues to understand their impact",
                    tool_call="investigate_issue",
                    priority="high"
                ),
                ActionSuggestion(
                    action="quick_triage",
                    description="Quickly classify obvious false positives",
                    tool_call="mark_issue",
                    priority="medium"
                )
            ])
        
        elif current_stage == WorkflowStage.INVESTIGATION:
            unclassified = [issue for issue in issues if issue.get("classification") == "unclassified"]
            
            if unclassified:
                suggestions.append(ActionSuggestion(
                    action="classify_investigated",
                    description=f"Classify {len(unclassified)} investigated issues",
                    tool_call="mark_issue",
                    priority="high"
                ))
            
            # Suggest prioritization for complex issues
            complex_issues = [
                issue for issue in issues 
                if self.assess_issue_complexity(issue, project_context) in [IssueComplexity.COMPLEX, IssueComplexity.CRITICAL]
            ]
            
            if complex_issues:
                suggestions.append(ActionSuggestion(
                    action="prioritize_complex",
                    description=f"Prioritize {len(complex_issues)} complex/critical issues",
                    priority="high"
                ))
        
        elif current_stage == WorkflowStage.CLASSIFICATION:
            true_positives = [issue for issue in issues if issue.get("classification") == "true_positive"]
            false_positives = [issue for issue in issues if issue.get("classification") == "false_positive"]
            
            if true_positives:
                pending_tp = [issue for issue in true_positives if issue.get("status") == "pending"]
                
                if pending_tp:
                    suggestions.append(ActionSuggestion(
                        action="start_resolution",
                        description=f"Begin resolving {len(pending_tp)} true positive issues",
                        tool_call="mark_issue",
                        priority="high"
                    ))
                
                # Suggest starting with simpler issues
                simple_issues = [
                    issue for issue in true_positives
                    if self.assess_issue_complexity(issue, project_context) in [IssueComplexity.TRIVIAL, IssueComplexity.SIMPLE]
                ]
                
                if simple_issues:
                    suggestions.append(ActionSuggestion(
                        action="start_with_simple",
                        description=f"Start with {len(simple_issues)} simple issues for quick wins",
                        priority="medium"
                    ))
            
            if false_positives:
                suggestions.append(ActionSuggestion(
                    action="suppress_false_positives",
                    description=f"Suppress {len(false_positives)} false positives",
                    tool_call="suppress_issue",
                    priority="medium"
                ))
        
        elif current_stage == WorkflowStage.RESOLUTION:
            in_progress = [issue for issue in issues if issue.get("status") == "work_in_progress"]
            
            if in_progress:
                suggestions.extend([
                    ActionSuggestion(
                        action="document_progress",
                        description="Document progress on issues being worked",
                        tool_call="add_agent_note",
                        priority="high"
                    ),
                    ActionSuggestion(
                        action="verify_partial_fixes",
                        description="Test partial fixes to ensure they work",
                        tool_call="analyze_code",
                        priority="medium"
                    )
                ])
        
        elif current_stage == WorkflowStage.VERIFICATION:
            suggestions.extend([
                ActionSuggestion(
                    action="comprehensive_reanalysis",
                    description="Run comprehensive analysis to verify all fixes",
                    tool_call="analyze_code",
                    priority="high"
                ),
                ActionSuggestion(
                    action="mark_completed",
                    description="Mark successfully resolved issues as completed",
                    tool_call="mark_issue",
                    priority="medium"
                )
            ])
        
        elif current_stage == WorkflowStage.COMPLETION:
            suggestions.extend([
                ActionSuggestion(
                    action="final_statistics",
                    description="Review final project statistics",
                    tool_call="get_tracking_statistics",
                    priority="low"
                ),
                ActionSuggestion(
                    action="document_learnings",
                    description="Document lessons learned for future reference",
                    tool_call="add_agent_note",
                    priority="low"
                )
            ])
        
        return suggestions
    
    def estimate_completion_time(
        self,
        issues: List[Dict],
        current_stage: WorkflowStage,
        agent_velocity: Dict = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Estimate time to completion based on issues and current progress.
        
        Returns:
            Tuple of (total_estimate, stage_breakdown)
        """
        
        if not issues:
            return "Complete", {}
        
        # Default agent velocity (issues per hour by complexity)
        if agent_velocity is None:
            agent_velocity = {
                IssueComplexity.TRIVIAL: 12,      # 5 min each
                IssueComplexity.SIMPLE: 4,       # 15 min each
                IssueComplexity.MODERATE: 1,     # 1 hour each
                IssueComplexity.COMPLEX: 0.25,   # 4 hours each
                IssueComplexity.CRITICAL: 0.125  # 8 hours each
            }
        
        stage_estimates = {}
        
        # Categorize issues by what work they need
        unclassified = [issue for issue in issues if issue.get("classification") == "unclassified"]
        true_positives = [issue for issue in issues if issue.get("classification") == "true_positive"]
        pending_tp = [issue for issue in true_positives if issue.get("status") == "pending"]
        in_progress_tp = [issue for issue in true_positives if issue.get("status") == "work_in_progress"]
        
        # Investigation/Classification time (5 min per issue)
        if unclassified:
            investigation_hours = len(unclassified) * 0.083  # 5 minutes
            stage_estimates["Investigation & Classification"] = f"{investigation_hours:.1f} hours"
        
        # Resolution time based on complexity
        resolution_issues = pending_tp + in_progress_tp
        if resolution_issues:
            resolution_hours = 0
            for issue in resolution_issues:
                complexity = self.assess_issue_complexity(issue)
                resolution_hours += 1 / agent_velocity[complexity]
            
            stage_estimates["Resolution"] = f"{resolution_hours:.1f} hours"
        
        # Verification time (fixed 15 min)
        if true_positives:
            stage_estimates["Verification"] = "0.25 hours"
        
        # Calculate total
        total_hours = sum(
            float(estimate.split()[0]) 
            for estimate in stage_estimates.values()
        )
        
        if total_hours < 1:
            total_estimate = f"{int(total_hours * 60)} minutes"
        elif total_hours < 8:
            total_estimate = f"{total_hours:.1f} hours"
        elif total_hours < 24:
            total_estimate = f"{total_hours/8:.1f} days"
        else:
            total_estimate = f"{total_hours/40:.1f} weeks"
        
        return total_estimate, stage_estimates
    
    def identify_blockers(
        self,
        issues: List[Dict],
        project_context: Dict = None
    ) -> List[str]:
        """Identify potential blockers in the workflow."""
        
        blockers = []
        
        # Complexity-based blockers
        critical_issues = [
            issue for issue in issues
            if self.assess_issue_complexity(issue, project_context) == IssueComplexity.CRITICAL
        ]
        
        if critical_issues:
            blockers.append(f"{len(critical_issues)} critical issues require careful planning")
        
        # Security-related blockers
        security_issues = [
            issue for issue in issues
            if "security" in str(issue).lower() or issue.get("detector_id") == "security-smell"
        ]
        
        if security_issues:
            blockers.append(f"{len(security_issues)} security issues need expert review")
        
        # Architecture-related blockers
        architecture_issues = [
            issue for issue in issues
            if any(keyword in issue.get("file_path", "").lower() 
                  for keyword in ["__init__", "setup", "config", "settings"])
        ]
        
        if architecture_issues:
            blockers.append(f"{len(architecture_issues)} architecture files affected")
        
        # Circular dependency blockers
        circular_deps = [
            issue for issue in issues
            if issue.get("detector_id") == "circular-deps"
        ]
        
        if circular_deps:
            blockers.append("Circular dependencies require systematic refactoring")
        
        # Large volume blockers
        if len(issues) > 50:
            blockers.append("Large number of issues requires systematic approach")
        
        return blockers
