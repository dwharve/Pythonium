"""
Advanced Workflow Orchestration for DevTeam Manager.

This module implements Phase 3 features including:
- Complex decision trees and dynamic routing
- Parallel and sequential workflow patterns  
- Dynamic agent assignment and optimization
- Error recovery mechanisms
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .devteam_events import TaskType, TaskPriority, WorkflowPhase, AgentType
from pythonium.common.logging import get_logger

logger = get_logger(__name__)


class TaskComplexity(str, Enum):
    """Task complexity levels for routing decisions."""
    
    SIMPLE = "simple"      # Single agent, single phase
    MODERATE = "moderate"  # Multiple phases, single track
    COMPLEX = "complex"    # Multiple agents, parallel work
    ENTERPRISE = "enterprise"  # Full team, complex dependencies


class WorkflowPattern(str, Enum):
    """Available workflow execution patterns."""
    
    SEQUENTIAL = "sequential"     # One agent at a time
    PARALLEL = "parallel"        # Multiple agents simultaneously
    FAN_OUT_IN = "fan_out_in"    # Split work, then merge
    PIPELINE = "pipeline"        # Continuous flow through stages
    CONDITIONAL = "conditional"   # Decision-based routing


class ResourceConstraint(str, Enum):
    """Resource constraint types."""
    
    AGENT_CAPACITY = "agent_capacity"
    TIME_LIMIT = "time_limit"
    QUALITY_GATE = "quality_gate"
    DEPENDENCY = "dependency"


@dataclass
class TaskMetrics:
    """Metrics for task complexity assessment."""
    
    lines_of_code_estimate: int = 0
    number_of_components: int = 1
    external_dependencies: int = 0
    risk_factors: List[str] = field(default_factory=list)
    estimated_hours: float = 1.0
    required_skills: Set[str] = field(default_factory=set)
    quality_requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAssignment:
    """Assignment of an agent to a workflow task."""
    
    agent_id: str
    agent_type: AgentType
    task_phase: WorkflowPhase
    estimated_duration: timedelta
    dependencies: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None
    priority: int = 1  # 1 is highest priority


@dataclass
class WorkflowPlan:
    """Complete execution plan for a workflow."""
    
    workflow_id: str
    task_id: str
    complexity: TaskComplexity
    pattern: WorkflowPattern
    total_estimated_duration: timedelta
    assignments: List[AgentAssignment]
    critical_path: List[str]
    parallel_groups: Dict[str, List[str]] = field(default_factory=dict)
    quality_gates: List[str] = field(default_factory=list)
    risk_mitigation: List[str] = field(default_factory=list)


class TaskComplexityAnalyzer:
    """Analyzes task complexity and recommends workflow patterns."""
    
    def __init__(self):
        self.complexity_thresholds = {
            TaskComplexity.SIMPLE: {"max_hours": 6, "max_components": 1, "max_skills": 2},
            TaskComplexity.MODERATE: {"max_hours": 20, "max_components": 3, "max_skills": 4},
            TaskComplexity.COMPLEX: {"max_hours": 50, "max_components": 8, "max_skills": 6},
            TaskComplexity.ENTERPRISE: {"max_hours": float("inf"), "max_components": float("inf"), "max_skills": float("inf")},
        }
    
    async def analyze_task(self, task_data: Dict[str, Any]) -> Tuple[TaskComplexity, TaskMetrics]:
        """Analyze a task and determine its complexity level."""
        metrics = await self._extract_task_metrics(task_data)
        complexity = self._determine_complexity(metrics)
        
        logger.info(f"Task {task_data.get('task_id')} analyzed as {complexity.value}")
        return complexity, metrics
    
    async def _extract_task_metrics(self, task_data: Dict[str, Any]) -> TaskMetrics:
        """Extract quantifiable metrics from task description."""
        description = task_data.get("description", "")
        requirements = task_data.get("requirements", [])
        task_type = task_data.get("task_type", TaskType.FEATURE)
        
        # Estimate based on keywords and task type
        metrics = TaskMetrics()
        
        # Estimate lines of code
        if "authentication" in description.lower() or "auth" in description.lower():
            metrics.lines_of_code_estimate += 500
        if "database" in description.lower() or "db" in description.lower():
            metrics.lines_of_code_estimate += 300
        if "api" in description.lower():
            metrics.lines_of_code_estimate += 200
        if "ui" in description.lower() or "interface" in description.lower():
            metrics.lines_of_code_estimate += 400
            
        # Component count estimation
        metrics.number_of_components = max(1, len(requirements))
        
        # External dependencies
        dep_keywords = ["integration", "external", "third-party", "api", "service"]
        metrics.external_dependencies = sum(1 for req in requirements 
                                          for keyword in dep_keywords 
                                          if keyword in req.lower())
        
        # Risk factors
        risk_keywords = {
            "security": "Security implementation required",
            "performance": "Performance optimization needed", 
            "scalability": "Scalability considerations",
            "legacy": "Legacy system integration",
            "data migration": "Data migration required"
        }
        
        # Check both description and requirements for risk factors
        full_text = description.lower() + " " + " ".join(requirements).lower()
        for keyword, risk in risk_keywords.items():
            if keyword in full_text:
                metrics.risk_factors.append(risk)
        
        # Time estimation based on task type
        base_hours = {
            TaskType.FEATURE: 8,
            TaskType.BUGFIX: 4,
            TaskType.DOCUMENTATION: 2,
            "code_review": 1,
            TaskType.REFACTOR: 6,
        }
        
        metrics.estimated_hours = base_hours.get(task_type, 4)
        complexity_multiplier = 1 + (metrics.lines_of_code_estimate / 5000) + (metrics.external_dependencies * 0.2)
        metrics.estimated_hours *= complexity_multiplier
        
        # Required skills
        skill_keywords = {
            "frontend": {"javascript", "css", "html", "react", "vue"},
            "backend": {"python", "java", "node", "api", "database"},
            "devops": {"docker", "kubernetes", "deployment", "ci/cd"},
            "security": {"authentication", "encryption", "security"},
            "testing": {"test", "qa", "validation", "quality"},
        }
        
        full_text = description.lower() + " " + " ".join(requirements).lower()
        for category, skills in skill_keywords.items():
            if any(skill in full_text for skill in skills):
                # Only add 1-2 skills per category to avoid over-skilling
                matching_skills = [skill for skill in skills if skill in full_text]
                metrics.required_skills.update(matching_skills[:2])
        
        return metrics
    
    def _determine_complexity(self, metrics: TaskMetrics) -> TaskComplexity:
        """Determine task complexity based on metrics."""
        # Check against thresholds in order
        for complexity, thresholds in self.complexity_thresholds.items():
            if (metrics.estimated_hours <= thresholds["max_hours"] and
                metrics.number_of_components <= thresholds["max_components"] and
                len(metrics.required_skills) <= thresholds["max_skills"]):
                return complexity
        
        return TaskComplexity.ENTERPRISE
    
    def recommend_pattern(self, complexity: TaskComplexity, metrics: TaskMetrics) -> WorkflowPattern:
        """Recommend workflow pattern based on complexity and metrics."""
        if complexity == TaskComplexity.SIMPLE:
            return WorkflowPattern.SEQUENTIAL
        elif complexity == TaskComplexity.MODERATE:
            if metrics.number_of_components > 1:
                return WorkflowPattern.PIPELINE
            return WorkflowPattern.SEQUENTIAL
        elif complexity == TaskComplexity.COMPLEX:
            if metrics.external_dependencies > 0:
                return WorkflowPattern.FAN_OUT_IN
            return WorkflowPattern.PARALLEL
        else:  # ENTERPRISE
            return WorkflowPattern.CONDITIONAL


class DynamicAgentAssigner:
    """Handles dynamic assignment of agents to workflow tasks."""
    
    def __init__(self, agent_registry):
        self.agent_registry = agent_registry
        self.agent_workloads: Dict[str, int] = {}
        self.agent_skills: Dict[str, Set[str]] = {}
        self.agent_performance: Dict[str, float] = {}  # Success rate 0-1
        self._initialize_agent_data()
    
    def _initialize_agent_data(self):
        """Initialize agent workload and skill tracking."""
        for agent_id, config in self.agent_registry.agents.items():
            self.agent_workloads[agent_id] = 0
            self.agent_skills[agent_id] = set(config.capabilities.specializations)
            self.agent_performance[agent_id] = 1.0  # Start with perfect score
    
    async def assign_agents(
        self, 
        workflow_plan: WorkflowPlan, 
        available_agents: Dict[AgentType, List[str]]
    ) -> List[AgentAssignment]:
        """Dynamically assign agents to workflow tasks."""
        assignments = []
        
        # Group assignments by parallel groups and dependencies
        dependency_graph = self._build_dependency_graph(workflow_plan)
        execution_phases = self._topological_sort(dependency_graph)
        
        for phase in execution_phases:
            phase_assignments = await self._assign_phase_agents(phase, available_agents)
            assignments.extend(phase_assignments)
        
        # Update workload tracking
        self._update_workloads(assignments)
        
        return assignments
    
    def _build_dependency_graph(self, workflow_plan: WorkflowPlan) -> Dict[str, List[str]]:
        """Build dependency graph for workflow tasks."""
        graph = {}
        for assignment in workflow_plan.assignments:
            task_key = f"{assignment.agent_type}_{assignment.task_phase}"
            graph[task_key] = assignment.dependencies
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Sort tasks into execution phases based on dependencies."""
        # Simplified topological sort - in practice would be more sophisticated
        phases = []
        remaining = set(graph.keys())
        
        while remaining:
            # Find tasks with no unresolved dependencies
            phase = []
            for task in list(remaining):
                deps = graph[task]
                if not any(dep in remaining for dep in deps):
                    phase.append(task)
                    remaining.remove(task)
            
            if not phase and remaining:
                # Circular dependency - break it
                phase.append(remaining.pop())
            
            if phase:
                phases.append(phase)
        
        return phases
    
    async def _assign_phase_agents(
        self, 
        phase_tasks: List[str], 
        available_agents: Dict[AgentType, List[str]]
    ) -> List[AgentAssignment]:
        """Assign agents for a single execution phase."""
        assignments = []
        
        for task in phase_tasks:
            # Parse task to get agent type and phase
            parts = task.split("_", 1)
            if len(parts) != 2:
                continue
                
            agent_type_str, phase_str = parts
            try:
                agent_type = AgentType(agent_type_str)
                phase = WorkflowPhase(phase_str)
            except ValueError:
                logger.warning(f"Invalid task format: {task}")
                continue
            
            # Find best available agent
            best_agent = self._select_best_agent(agent_type, available_agents)
            if best_agent:
                assignment = AgentAssignment(
                    agent_id=best_agent,
                    agent_type=agent_type,
                    task_phase=phase,
                    estimated_duration=timedelta(hours=2),  # Default estimate
                )
                assignments.append(assignment)
        
        return assignments
    
    def _select_best_agent(self, agent_type: AgentType, available_agents: Dict[AgentType, List[str]]) -> Optional[str]:
        """Select the best available agent of the specified type."""
        candidates = available_agents.get(agent_type, [])
        if not candidates:
            return None
        
        # Score agents based on workload and performance
        best_agent = None
        best_score = float('-inf')
        
        for agent_id in candidates:
            workload_score = 1.0 / (1 + self.agent_workloads.get(agent_id, 0))
            performance_score = self.agent_performance.get(agent_id, 1.0)
            total_score = workload_score * performance_score
            
            if total_score > best_score:
                best_score = total_score
                best_agent = agent_id
        
        return best_agent
    
    def _update_workloads(self, assignments: List[AgentAssignment]):
        """Update agent workload tracking."""
        for assignment in assignments:
            current_load = self.agent_workloads.get(assignment.agent_id, 0)
            self.agent_workloads[assignment.agent_id] = current_load + 1
    
    async def update_agent_performance(self, agent_id: str, success: bool):
        """Update agent performance metrics."""
        current_performance = self.agent_performance.get(agent_id, 1.0)
        # Simple moving average with decay
        alpha = 0.1  # Learning rate
        new_score = 1.0 if success else 0.0
        self.agent_performance[agent_id] = (1 - alpha) * current_performance + alpha * new_score


class WorkflowOptimizer:
    """Optimizes workflow execution for efficiency and quality."""
    
    def __init__(self):
        self.optimization_history: List[Dict[str, Any]] = []
    
    async def optimize_workflow(self, workflow_plan: WorkflowPlan) -> WorkflowPlan:
        """Optimize a workflow plan for better performance."""
        optimized_plan = workflow_plan
        
        # Apply optimization strategies
        optimized_plan = await self._optimize_parallel_execution(optimized_plan)
        optimized_plan = await self._optimize_critical_path(optimized_plan)
        optimized_plan = await self._optimize_resource_allocation(optimized_plan)
        
        # Record optimization results
        self._record_optimization(workflow_plan, optimized_plan)
        
        return optimized_plan
    
    async def _optimize_parallel_execution(self, plan: WorkflowPlan) -> WorkflowPlan:
        """Identify opportunities for parallel execution."""
        # Identify independent tasks that can run in parallel
        independent_tasks = []
        for assignment in plan.assignments:
            if not assignment.dependencies:
                independent_tasks.append(assignment)
        
        # Group independent tasks into parallel groups
        if len(independent_tasks) > 1:
            parallel_group_id = f"parallel_{uuid.uuid4().hex[:8]}"
            for task in independent_tasks:
                task.parallel_group = parallel_group_id
            
            plan.parallel_groups[parallel_group_id] = [task.agent_id for task in independent_tasks]
        
        return plan
    
    async def _optimize_critical_path(self, plan: WorkflowPlan) -> WorkflowPlan:
        """Identify and optimize the critical path."""
        # Build dependency graph and find longest path
        task_durations = {f"{a.agent_type}_{a.task_phase}": a.estimated_duration.total_seconds() 
                         for a in plan.assignments}
        
        # Simple critical path calculation - in practice would use more sophisticated algorithms
        critical_tasks = []
        total_duration = 0
        
        for assignment in plan.assignments:
            if not assignment.dependencies:  # Start with root tasks
                task_key = f"{assignment.agent_type}_{assignment.task_phase}"
                critical_tasks.append(task_key)
                total_duration += assignment.estimated_duration.total_seconds()
        
        plan.critical_path = critical_tasks
        plan.total_estimated_duration = timedelta(seconds=total_duration)
        
        return plan
    
    async def _optimize_resource_allocation(self, plan: WorkflowPlan) -> WorkflowPlan:
        """Optimize resource allocation across tasks."""
        # Sort assignments by priority and estimated duration
        plan.assignments.sort(key=lambda x: (x.priority, x.estimated_duration.total_seconds()))
        
        # Balance workload across agents
        agent_loads = {}
        for assignment in plan.assignments:
            if assignment.agent_id not in agent_loads:
                agent_loads[assignment.agent_id] = timedelta()
            agent_loads[assignment.agent_id] += assignment.estimated_duration
        
        # Identify overloaded agents and rebalance if possible
        avg_load = sum(load.total_seconds() for load in agent_loads.values()) / len(agent_loads)
        
        for agent_id, load in agent_loads.items():
            if load.total_seconds() > avg_load * 1.5:  # 50% above average
                logger.info(f"Agent {agent_id} is overloaded, considering rebalancing")
                # In practice, would implement sophisticated rebalancing logic
        
        return plan
    
    def _record_optimization(self, original: WorkflowPlan, optimized: WorkflowPlan):
        """Record optimization results for learning."""
        optimization_record = {
            "timestamp": datetime.now().isoformat(),
            "workflow_id": original.workflow_id,
            "original_duration": original.total_estimated_duration.total_seconds(),
            "optimized_duration": optimized.total_estimated_duration.total_seconds(),
            "improvement": (original.total_estimated_duration.total_seconds() - 
                          optimized.total_estimated_duration.total_seconds()),
            "parallel_groups_added": len(optimized.parallel_groups) - len(original.parallel_groups),
        }
        
        self.optimization_history.append(optimization_record)
        logger.info(f"Workflow {original.workflow_id} optimized with {optimization_record['improvement']}s improvement")


class ErrorRecoveryManager:
    """Handles error recovery and workflow resilience."""
    
    def __init__(self):
        self.retry_policies = {
            "agent_timeout": {"max_retries": 3, "backoff_factor": 2.0},
            "agent_failure": {"max_retries": 2, "backoff_factor": 1.5},
            "resource_unavailable": {"max_retries": 5, "backoff_factor": 1.2},
            "quality_gate_failure": {"max_retries": 1, "backoff_factor": 1.0},
        }
        self.recovery_history: List[Dict[str, Any]] = []
    
    async def handle_workflow_error(
        self, 
        workflow_id: str, 
        error_type: str, 
        error_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle workflow errors with appropriate recovery strategy."""
        recovery_strategy = await self._determine_recovery_strategy(error_type, error_context)
        recovery_result = await self._execute_recovery(workflow_id, recovery_strategy, error_context)
        
        # Record recovery attempt
        self._record_recovery_attempt(workflow_id, error_type, recovery_strategy, recovery_result)
        
        return recovery_result
    
    async def _determine_recovery_strategy(self, error_type: str, context: Dict[str, Any]) -> str:
        """Determine the best recovery strategy for an error."""
        if error_type == "agent_timeout":
            if context.get("retry_count", 0) < self.retry_policies[error_type]["max_retries"]:
                return "retry_with_backoff"
            else:
                return "fallback_agent"
        
        elif error_type == "agent_failure":
            return "fallback_agent"
        
        elif error_type == "resource_unavailable":
            return "wait_and_retry"
        
        elif error_type == "quality_gate_failure":
            return "escalate_to_human"
        
        else:
            return "escalate_to_human"
    
    async def _execute_recovery(
        self, 
        workflow_id: str, 
        strategy: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the chosen recovery strategy."""
        if strategy == "retry_with_backoff":
            return await self._retry_with_backoff(workflow_id, context)
        
        elif strategy == "fallback_agent":
            return await self._assign_fallback_agent(workflow_id, context)
        
        elif strategy == "wait_and_retry":
            return await self._wait_and_retry(workflow_id, context)
        
        elif strategy == "escalate_to_human":
            return await self._escalate_to_human(workflow_id, context)
        
        else:
            return {"success": False, "message": f"Unknown recovery strategy: {strategy}"}
    
    async def _retry_with_backoff(self, workflow_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retry the failed operation with exponential backoff."""
        retry_count = context.get("retry_count", 0)
        error_type = context.get("error_type", "unknown")
        
        policy = self.retry_policies.get(error_type, {"max_retries": 1, "backoff_factor": 1.0})
        
        if retry_count >= policy["max_retries"]:
            return {"success": False, "message": "Max retries exceeded"}
        
        # Calculate backoff delay
        delay = policy["backoff_factor"] ** retry_count
        await asyncio.sleep(delay)
        
        # Mark for retry
        return {
            "success": True, 
            "action": "retry",
            "delay": delay,
            "retry_count": retry_count + 1
        }
    
    async def _assign_fallback_agent(self, workflow_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a fallback agent to continue the workflow."""
        failed_agent = context.get("agent_id")
        agent_type = context.get("agent_type")
        
        # In practice, would integrate with agent registry to find alternatives
        fallback_agent = f"fallback_{agent_type}_{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "action": "fallback_assignment",
            "original_agent": failed_agent,
            "fallback_agent": fallback_agent
        }
    
    async def _wait_and_retry(self, workflow_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for resources to become available and retry."""
        wait_time = context.get("wait_time", 30)  # Default 30 seconds
        await asyncio.sleep(wait_time)
        
        return {
            "success": True,
            "action": "wait_and_retry",
            "wait_time": wait_time
        }
    
    async def _escalate_to_human(self, workflow_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate the issue to human intervention."""
        return {
            "success": True,
            "action": "human_escalation",
            "escalation_reason": context.get("error_type", "unknown"),
            "workflow_id": workflow_id,
            "requires_human_intervention": True
        }
    
    def _record_recovery_attempt(
        self, 
        workflow_id: str, 
        error_type: str, 
        strategy: str, 
        result: Dict[str, Any]
    ):
        """Record recovery attempt for analysis."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "workflow_id": workflow_id,
            "error_type": error_type,
            "recovery_strategy": strategy,
            "success": result.get("success", False),
            "action_taken": result.get("action", "unknown")
        }
        
        self.recovery_history.append(record)
        logger.info(f"Recovery attempt recorded for workflow {workflow_id}: {strategy} -> {result.get('action', 'unknown')}")


class AdvancedWorkflowOrchestrator:
    """Main orchestrator for advanced workflow patterns."""
    
    def __init__(self, agent_registry):
        self.complexity_analyzer = TaskComplexityAnalyzer()
        self.agent_assigner = DynamicAgentAssigner(agent_registry)
        self.optimizer = WorkflowOptimizer()
        self.error_recovery = ErrorRecoveryManager()
        self.active_workflows: Dict[str, WorkflowPlan] = {}
    
    async def create_advanced_workflow(self, task_data: Dict[str, Any]) -> WorkflowPlan:
        """Create an advanced workflow plan for a task."""
        # Analyze task complexity
        complexity, metrics = await self.complexity_analyzer.analyze_task(task_data)
        
        # Recommend workflow pattern
        pattern = self.complexity_analyzer.recommend_pattern(complexity, metrics)
        
        # Create initial workflow plan
        workflow_plan = WorkflowPlan(
            workflow_id=f"workflow_{uuid.uuid4().hex[:8]}",
            task_id=task_data.get("task_id", "unknown"),
            complexity=complexity,
            pattern=pattern,
            total_estimated_duration=timedelta(hours=metrics.estimated_hours),
            assignments=[],
            critical_path=[],
        )
        
        # Generate agent assignments based on pattern
        workflow_plan.assignments = await self._generate_assignments(pattern, complexity, metrics)
        
        # Optimize the workflow
        workflow_plan = await self.optimizer.optimize_workflow(workflow_plan)
        
        # Store active workflow
        self.active_workflows[workflow_plan.workflow_id] = workflow_plan
        
        logger.info(f"Created advanced workflow {workflow_plan.workflow_id} with pattern {pattern.value}")
        return workflow_plan
    
    async def _generate_assignments(
        self, 
        pattern: WorkflowPattern, 
        complexity: TaskComplexity, 
        metrics: TaskMetrics
    ) -> List[AgentAssignment]:
        """Generate agent assignments based on workflow pattern."""
        assignments = []
        
        if pattern == WorkflowPattern.SEQUENTIAL:
            assignments = self._create_sequential_assignments(complexity)
        elif pattern == WorkflowPattern.PARALLEL:
            assignments = self._create_parallel_assignments(complexity)
        elif pattern == WorkflowPattern.FAN_OUT_IN:
            assignments = self._create_fan_out_in_assignments(complexity)
        elif pattern == WorkflowPattern.PIPELINE:
            assignments = self._create_pipeline_assignments(complexity)
        elif pattern == WorkflowPattern.CONDITIONAL:
            assignments = self._create_conditional_assignments(complexity, metrics)
        
        return assignments
    
    def _create_sequential_assignments(self, complexity: TaskComplexity) -> List[AgentAssignment]:
        """Create sequential workflow assignments."""
        assignments = [
            AgentAssignment(
                agent_id="project_manager",
                agent_type=AgentType.PROJECT_MANAGER,
                task_phase=WorkflowPhase.PLANNING,
                estimated_duration=timedelta(hours=1),
                dependencies=[],
                priority=1
            ),
            AgentAssignment(
                agent_id="developer_1",
                agent_type=AgentType.DEVELOPER,
                task_phase=WorkflowPhase.IMPLEMENTATION,
                estimated_duration=timedelta(hours=4),
                dependencies=["planning"],
                priority=2
            ),
            AgentAssignment(
                agent_id="code_reviewer",
                agent_type=AgentType.REVIEWER,
                task_phase=WorkflowPhase.REVIEW,
                estimated_duration=timedelta(hours=1),
                dependencies=["development"],
                priority=3
            ),
        ]
        
        if complexity in [TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE]:
            assignments.append(
                AgentAssignment(
                    agent_id="qa_agent",
                    agent_type=AgentType.QA,
                    task_phase=WorkflowPhase.TESTING,
                    estimated_duration=timedelta(hours=2),
                    dependencies=["code_review"],
                    priority=4
                )
            )
        
        return assignments
    
    def _create_parallel_assignments(self, complexity: TaskComplexity) -> List[AgentAssignment]:
        """Create parallel workflow assignments."""
        parallel_group = f"parallel_{uuid.uuid4().hex[:8]}"
        
        assignments = [
            AgentAssignment(
                agent_id="project_manager",
                agent_type=AgentType.PROJECT_MANAGER,
                task_phase=WorkflowPhase.PLANNING,
                estimated_duration=timedelta(hours=1),
                dependencies=[],
                priority=1
            ),
            AgentAssignment(
                agent_id="developer_1",
                agent_type=AgentType.DEVELOPER,
                task_phase=WorkflowPhase.IMPLEMENTATION,
                estimated_duration=timedelta(hours=3),
                dependencies=["planning"],
                parallel_group=parallel_group,
                priority=2
            ),
            AgentAssignment(
                agent_id="developer_2",
                agent_type=AgentType.DEVELOPER,
                task_phase=WorkflowPhase.IMPLEMENTATION,
                estimated_duration=timedelta(hours=3),
                dependencies=["planning"],
                parallel_group=parallel_group,
                priority=2
            ),
        ]
        
        return assignments
    
    def _create_fan_out_in_assignments(self, complexity: TaskComplexity) -> List[AgentAssignment]:
        """Create fan-out/fan-in workflow assignments."""
        parallel_group = f"parallel_{uuid.uuid4().hex[:8]}"
        
        assignments = [
            # Fan out phase
            AgentAssignment(
                agent_id="project_manager",
                agent_type=AgentType.PROJECT_MANAGER,
                task_phase=WorkflowPhase.PLANNING,
                estimated_duration=timedelta(hours=1),
                dependencies=[],
                priority=1
            ),
            AgentAssignment(
                agent_id="architect",
                agent_type=AgentType.ARCHITECT,
                task_phase=WorkflowPhase.ARCHITECTURE,
                estimated_duration=timedelta(hours=2),
                dependencies=["planning"],
                parallel_group=parallel_group,
                priority=2
            ),
            AgentAssignment(
                agent_id="developer_1",
                agent_type=AgentType.DEVELOPER,
                task_phase=WorkflowPhase.IMPLEMENTATION,
                estimated_duration=timedelta(hours=4),
                dependencies=["planning"],
                parallel_group=parallel_group,
                priority=2
            ),
            AgentAssignment(
                agent_id="qa_agent",
                agent_type=AgentType.QA,
                task_phase=WorkflowPhase.TESTING,
                estimated_duration=timedelta(hours=2),
                dependencies=["planning"],
                parallel_group=parallel_group,
                priority=2
            ),
            # Fan in phase
            AgentAssignment(
                agent_id="code_reviewer",
                agent_type=AgentType.REVIEWER,
                task_phase=WorkflowPhase.REVIEW,
                estimated_duration=timedelta(hours=1),
                dependencies=["architecture", "development", "testing"],
                priority=3
            ),
        ]
        
        return assignments
    
    def _create_pipeline_assignments(self, complexity: TaskComplexity) -> List[AgentAssignment]:
        """Create pipeline workflow assignments."""
        return [
            AgentAssignment(
                agent_id="project_manager",
                agent_type=AgentType.PROJECT_MANAGER,
                task_phase=WorkflowPhase.PLANNING,
                estimated_duration=timedelta(hours=1),
                dependencies=[],
                priority=1
            ),
            AgentAssignment(
                agent_id="architect",
                agent_type=AgentType.ARCHITECT,
                task_phase=WorkflowPhase.ARCHITECTURE,
                estimated_duration=timedelta(hours=2),
                dependencies=["planning"],
                priority=2
            ),
            AgentAssignment(
                agent_id="developer_1",
                agent_type=AgentType.DEVELOPER,
                task_phase=WorkflowPhase.IMPLEMENTATION,
                estimated_duration=timedelta(hours=4),
                dependencies=["architecture"],
                priority=3
            ),
            AgentAssignment(
                agent_id="code_reviewer",
                agent_type=AgentType.REVIEWER,
                task_phase=WorkflowPhase.REVIEW,
                estimated_duration=timedelta(hours=1),
                dependencies=["development"],
                priority=4
            ),
            AgentAssignment(
                agent_id="qa_agent",
                agent_type=AgentType.QA,
                task_phase=WorkflowPhase.TESTING,
                estimated_duration=timedelta(hours=2),
                dependencies=["code_review"],
                priority=5
            ),
        ]
    
    def _create_conditional_assignments(
        self, 
        complexity: TaskComplexity, 
        metrics: TaskMetrics
    ) -> List[AgentAssignment]:
        """Create conditional workflow assignments based on task characteristics."""
        assignments = []
        
        # Always start with planning
        assignments.append(
            AgentAssignment(
                agent_id="project_manager",
                agent_type=AgentType.PROJECT_MANAGER,
                task_phase=WorkflowPhase.PLANNING,
                estimated_duration=timedelta(hours=1),
                dependencies=[],
                priority=1
            )
        )
        
        # Add architecture phase for complex tasks
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE]:
            assignments.append(
                AgentAssignment(
                    agent_id="architect",
                    agent_type=AgentType.ARCHITECT,
                    task_phase=WorkflowPhase.ARCHITECTURE,
                    estimated_duration=timedelta(hours=2),
                    dependencies=["planning"],
                    priority=2
                )
            )
        
        # Development phase
        dev_deps = ["architecture"] if complexity in [TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE] else ["planning"]
        assignments.append(
            AgentAssignment(
                agent_id="developer_1",
                agent_type=AgentType.DEVELOPER,
                task_phase=WorkflowPhase.IMPLEMENTATION,
                estimated_duration=timedelta(hours=metrics.estimated_hours * 0.7),
                dependencies=dev_deps,
                priority=3
            )
        )
        
        # Add security review for security-related tasks
        if "security" in metrics.risk_factors:
            assignments.append(
                AgentAssignment(
                    agent_id="security_reviewer",
                    agent_type=AgentType.REVIEWER,
                    task_phase=WorkflowPhase.REVIEW,
                    estimated_duration=timedelta(hours=2),
                    dependencies=["development"],
                    priority=4
                )
            )
        
        return assignments
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute an advanced workflow with error handling."""
        if workflow_id not in self.active_workflows:
            return {"success": False, "message": "Workflow not found"}
        
        workflow_plan = self.active_workflows[workflow_id]
        
        try:
            # Execute workflow with monitoring
            result = await self._execute_with_monitoring(workflow_plan)
            return result
        
        except Exception as e:
            # Handle workflow errors
            error_context = {
                "workflow_id": workflow_id,
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            recovery_result = await self.error_recovery.handle_workflow_error(
                workflow_id, error_context["error_type"], error_context
            )
            
            return {"success": False, "error": str(e), "recovery": recovery_result}
    
    async def _execute_with_monitoring(self, workflow_plan: WorkflowPlan) -> Dict[str, Any]:
        """Execute workflow with real-time monitoring."""
        start_time = datetime.now()
        completed_tasks = []
        
        # Execute assignments in dependency order
        for assignment in workflow_plan.assignments:
            task_start = datetime.now()
            
            # Simulate task execution (in practice would call actual agents)
            await asyncio.sleep(0.1)  # Simulate work
            
            task_end = datetime.now()
            completed_tasks.append({
                "agent_id": assignment.agent_id,
                "task_phase": assignment.task_phase,
                "duration": (task_end - task_start).total_seconds(),
                "completed_at": task_end.isoformat()
            })
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        return {
            "success": True,
            "workflow_id": workflow_plan.workflow_id,
            "total_duration": total_duration,
            "completed_tasks": completed_tasks,
            "optimization_applied": True
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow."""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow_plan = self.active_workflows[workflow_id]
        
        return {
            "workflow_id": workflow_id,
            "task_id": workflow_plan.task_id,
            "complexity": workflow_plan.complexity,
            "pattern": workflow_plan.pattern,
            "total_assignments": len(workflow_plan.assignments),
            "parallel_groups": len(workflow_plan.parallel_groups),
            "estimated_duration": workflow_plan.total_estimated_duration.total_seconds(),
            "critical_path": workflow_plan.critical_path,
        }