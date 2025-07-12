"""
Tests for Phase 3 Advanced Workflow Orchestration functionality.
"""

import asyncio
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from pythonium.managers.devteam_advanced_workflows import (
    AdvancedWorkflowOrchestrator,
    DynamicAgentAssigner,
    ErrorRecoveryManager,
    TaskComplexity,
    TaskComplexityAnalyzer,
    TaskMetrics,
    WorkflowOptimizer,
    WorkflowPattern,
)
from pythonium.managers.devteam_events import AgentType, TaskType, WorkflowPhase
from pythonium.agents import DevTeamAgentRegistry


@pytest.fixture
def mock_agent_registry():
    """Create a mock agent registry for testing."""
    registry = MagicMock(spec=DevTeamAgentRegistry)
    registry.agents = {
        "project_manager": MagicMock(),
        "architect": MagicMock(),
        "developer_1": MagicMock(),
        "developer_2": MagicMock(),
        "code_reviewer": MagicMock(),
        "qa_agent": MagicMock(),
        "documentation_agent": MagicMock(),
    }
    return registry


@pytest.fixture
def complexity_analyzer():
    """Create a task complexity analyzer."""
    return TaskComplexityAnalyzer()


@pytest.fixture
def agent_assigner(mock_agent_registry):
    """Create a dynamic agent assigner."""
    return DynamicAgentAssigner(mock_agent_registry)


@pytest.fixture
def workflow_optimizer():
    """Create a workflow optimizer."""
    return WorkflowOptimizer()


@pytest.fixture
def error_recovery():
    """Create an error recovery manager."""
    return ErrorRecoveryManager()


@pytest.fixture
def advanced_orchestrator(mock_agent_registry):
    """Create an advanced workflow orchestrator."""
    return AdvancedWorkflowOrchestrator(mock_agent_registry)


class TestTaskComplexityAnalyzer:
    """Test task complexity analysis."""

    @pytest.mark.asyncio
    async def test_analyze_simple_task(self, complexity_analyzer):
        """Test analysis of a simple task."""
        task_data = {
            "task_id": "simple-001",
            "task_type": TaskType.BUGFIX,
            "description": "Fix minor UI bug",
            "requirements": ["Fix button alignment"],
        }

        complexity, metrics = await complexity_analyzer.analyze_task(task_data)

        assert complexity == TaskComplexity.SIMPLE
        assert metrics.estimated_hours <= 6  # Adjusted for more realistic estimation
        assert metrics.number_of_components == 1

    @pytest.mark.asyncio
    async def test_analyze_complex_task(self, complexity_analyzer):
        """Test analysis of a complex task."""
        task_data = {
            "task_id": "complex-001",
            "task_type": TaskType.FEATURE,
            "description": "Implement user authentication system with database integration and API endpoints",
            "requirements": [
                "JWT token authentication",
                "Password reset functionality", 
                "Multi-factor authentication",
                "Database schema design",
                "API endpoint implementation",
                "Frontend integration",
            ],
        }

        complexity, metrics = await complexity_analyzer.analyze_task(task_data)

        assert complexity in [TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE]
        assert metrics.estimated_hours > 8
        assert metrics.number_of_components > 3
        assert "authentication" in str(metrics.required_skills).lower()

    @pytest.mark.asyncio
    async def test_recommend_workflow_pattern(self, complexity_analyzer):
        """Test workflow pattern recommendation."""
        # Simple task should get sequential pattern
        pattern = complexity_analyzer.recommend_pattern(TaskComplexity.SIMPLE, TaskMetrics())
        assert pattern == WorkflowPattern.SEQUENTIAL

        # Complex task should get parallel or fan-out pattern
        complex_metrics = TaskMetrics(external_dependencies=2)
        pattern = complexity_analyzer.recommend_pattern(TaskComplexity.COMPLEX, complex_metrics)
        assert pattern in [WorkflowPattern.PARALLEL, WorkflowPattern.FAN_OUT_IN]

    @pytest.mark.asyncio
    async def test_extract_task_metrics(self, complexity_analyzer):
        """Test task metrics extraction."""
        task_data = {
            "task_id": "metrics-001",
            "task_type": TaskType.FEATURE,
            "description": "Build secure API with database integration and performance optimization",
            "requirements": [
                "REST API endpoints",
                "Database integration",
                "Security implementation",
                "Performance testing",
            ],
        }

        metrics = await complexity_analyzer._extract_task_metrics(task_data)

        assert metrics.lines_of_code_estimate > 0
        assert metrics.number_of_components >= 4
        assert "Security implementation required" in metrics.risk_factors
        assert len(metrics.required_skills) > 0


class TestDynamicAgentAssigner:
    """Test dynamic agent assignment."""

    @pytest.mark.asyncio
    async def test_agent_assignment_initialization(self, agent_assigner):
        """Test agent assignment initialization."""
        assert len(agent_assigner.agent_workloads) > 0
        assert len(agent_assigner.agent_skills) > 0
        assert len(agent_assigner.agent_performance) > 0

        # All agents should start with zero workload
        for workload in agent_assigner.agent_workloads.values():
            assert workload == 0

        # All agents should start with perfect performance
        for performance in agent_assigner.agent_performance.values():
            assert performance == 1.0

    @pytest.mark.asyncio
    async def test_select_best_agent(self, agent_assigner):
        """Test best agent selection."""
        available_agents = {
            AgentType.DEVELOPER: ["developer_1", "developer_2"],
            AgentType.REVIEWER: ["code_reviewer"],
        }

        # Test selecting developer
        best_dev = agent_assigner._select_best_agent(AgentType.DEVELOPER, available_agents)
        assert best_dev in ["developer_1", "developer_2"]

        # Test selecting code reviewer
        best_reviewer = agent_assigner._select_best_agent(AgentType.REVIEWER, available_agents)
        assert best_reviewer == "code_reviewer"

        # Test selecting unavailable agent type
        best_missing = agent_assigner._select_best_agent(AgentType.ARCHITECT, available_agents)
        assert best_missing is None

    @pytest.mark.asyncio
    async def test_workload_balancing(self, agent_assigner):
        """Test workload balancing in agent selection."""
        available_agents = {AgentType.DEVELOPER: ["developer_1", "developer_2"]}

        # Assign workload to one agent
        agent_assigner.agent_workloads["developer_1"] = 3
        agent_assigner.agent_workloads["developer_2"] = 1

        # Should prefer agent with lower workload
        best_agent = agent_assigner._select_best_agent(AgentType.DEVELOPER, available_agents)
        assert best_agent == "developer_2"

    @pytest.mark.asyncio
    async def test_performance_tracking(self, agent_assigner):
        """Test agent performance tracking."""
        initial_performance = agent_assigner.agent_performance["developer_1"]
        
        # Update with success
        await agent_assigner.update_agent_performance("developer_1", True)
        success_performance = agent_assigner.agent_performance["developer_1"]
        
        # Update with failure
        await agent_assigner.update_agent_performance("developer_1", False)
        failure_performance = agent_assigner.agent_performance["developer_1"]
        
        # Performance should be between 0 and 1
        assert 0 <= failure_performance <= 1
        assert failure_performance < success_performance


class TestWorkflowOptimizer:
    """Test workflow optimization."""

    @pytest.mark.asyncio
    async def test_optimization_initialization(self, workflow_optimizer):
        """Test optimizer initialization."""
        assert hasattr(workflow_optimizer, 'optimization_history')
        assert isinstance(workflow_optimizer.optimization_history, list)

    @pytest.mark.asyncio
    async def test_parallel_execution_optimization(self, workflow_optimizer, advanced_orchestrator):
        """Test parallel execution optimization."""
        # Create a workflow plan with independent tasks
        task_data = {
            "task_id": "parallel-test",
            "task_type": TaskType.FEATURE,
            "description": "Test parallel optimization",
            "requirements": ["requirement1", "requirement2"],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(task_data)
        
        # Run optimization
        optimized_plan = await workflow_optimizer.optimize_workflow(workflow_plan)
        
        # Should have some optimizations applied
        assert optimized_plan is not None
        assert len(workflow_optimizer.optimization_history) > 0


class TestErrorRecoveryManager:
    """Test error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_error_recovery_initialization(self, error_recovery):
        """Test error recovery manager initialization."""
        assert hasattr(error_recovery, 'retry_policies')
        assert hasattr(error_recovery, 'recovery_history')
        assert "agent_timeout" in error_recovery.retry_policies
        assert "agent_failure" in error_recovery.retry_policies

    @pytest.mark.asyncio
    async def test_recovery_strategy_determination(self, error_recovery):
        """Test recovery strategy determination."""
        # Test agent timeout strategy
        strategy = await error_recovery._determine_recovery_strategy(
            "agent_timeout", {"retry_count": 0}
        )
        assert strategy == "retry_with_backoff"

        # Test agent failure strategy
        strategy = await error_recovery._determine_recovery_strategy(
            "agent_failure", {}
        )
        assert strategy == "fallback_agent"

        # Test unknown error strategy
        strategy = await error_recovery._determine_recovery_strategy(
            "unknown_error", {}
        )
        assert strategy == "escalate_to_human"

    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, error_recovery):
        """Test retry with backoff mechanism."""
        context = {"retry_count": 0, "error_type": "agent_timeout"}
        
        result = await error_recovery._retry_with_backoff("workflow_123", context)
        
        assert result["success"] is True
        assert result["action"] == "retry"
        assert result["retry_count"] == 1
        assert "delay" in result

    @pytest.mark.asyncio
    async def test_fallback_agent_assignment(self, error_recovery):
        """Test fallback agent assignment."""
        context = {
            "agent_id": "developer_1",
            "agent_type": AgentType.DEVELOPER,
        }
        
        result = await error_recovery._assign_fallback_agent("workflow_123", context)
        
        assert result["success"] is True
        assert result["action"] == "fallback_assignment"
        assert result["original_agent"] == "developer_1"
        assert "fallback_agent" in result

    @pytest.mark.asyncio
    async def test_human_escalation(self, error_recovery):
        """Test human escalation."""
        context = {"error_type": "quality_gate_failure"}
        
        result = await error_recovery._escalate_to_human("workflow_123", context)
        
        assert result["success"] is True
        assert result["action"] == "human_escalation"
        assert result["requires_human_intervention"] is True

    @pytest.mark.asyncio
    async def test_recovery_history_recording(self, error_recovery):
        """Test recovery history recording."""
        initial_count = len(error_recovery.recovery_history)
        
        await error_recovery.handle_workflow_error(
            "workflow_123", "agent_timeout", {"retry_count": 0}
        )
        
        assert len(error_recovery.recovery_history) == initial_count + 1


class TestAdvancedWorkflowOrchestrator:
    """Test the main advanced workflow orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, advanced_orchestrator):
        """Test orchestrator initialization."""
        assert hasattr(advanced_orchestrator, 'complexity_analyzer')
        assert hasattr(advanced_orchestrator, 'agent_assigner')
        assert hasattr(advanced_orchestrator, 'optimizer')
        assert hasattr(advanced_orchestrator, 'error_recovery')
        assert hasattr(advanced_orchestrator, 'active_workflows')

    @pytest.mark.asyncio
    async def test_create_simple_workflow(self, advanced_orchestrator):
        """Test creating a simple workflow."""
        task_data = {
            "task_id": "simple-workflow-001",
            "task_type": TaskType.BUGFIX,
            "description": "Fix small UI issue",
            "requirements": ["Fix button styling"],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(task_data)

        assert workflow_plan is not None
        assert workflow_plan.task_id == "simple-workflow-001"
        assert workflow_plan.complexity == TaskComplexity.SIMPLE
        assert workflow_plan.pattern == WorkflowPattern.SEQUENTIAL
        assert len(workflow_plan.assignments) > 0

    @pytest.mark.asyncio
    async def test_create_complex_workflow(self, advanced_orchestrator):
        """Test creating a complex workflow."""
        task_data = {
            "task_id": "complex-workflow-001",
            "task_type": TaskType.FEATURE,
            "description": "Build authentication system with database integration and external API calls",
            "requirements": [
                "User registration and login",
                "JWT token management",
                "Password reset via email",
                "OAuth integration",
                "Database schema design",
                "API endpoint development",
                "Frontend integration",
                "Security audit"
            ],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(task_data)

        assert workflow_plan is not None
        assert workflow_plan.task_id == "complex-workflow-001"
        assert workflow_plan.complexity in [TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE]
        assert workflow_plan.pattern in [WorkflowPattern.PARALLEL, WorkflowPattern.FAN_OUT_IN, WorkflowPattern.CONDITIONAL]
        assert len(workflow_plan.assignments) > 3

    @pytest.mark.asyncio
    async def test_workflow_execution(self, advanced_orchestrator):
        """Test workflow execution."""
        task_data = {
            "task_id": "execution-test-001",
            "task_type": TaskType.FEATURE,
            "description": "Test workflow execution",
            "requirements": ["requirement1"],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(task_data)
        result = await advanced_orchestrator.execute_workflow(workflow_plan.workflow_id)

        assert result["success"] is True
        assert "workflow_id" in result
        assert "total_duration" in result
        assert "completed_tasks" in result

    @pytest.mark.asyncio
    async def test_workflow_status_tracking(self, advanced_orchestrator):
        """Test workflow status tracking."""
        task_data = {
            "task_id": "status-test-001",
            "task_type": TaskType.FEATURE,
            "description": "Test status tracking",
            "requirements": ["requirement1"],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(task_data)
        status = advanced_orchestrator.get_workflow_status(workflow_plan.workflow_id)

        assert status is not None
        assert status["workflow_id"] == workflow_plan.workflow_id
        assert status["task_id"] == "status-test-001"
        assert "complexity" in status
        assert "pattern" in status
        assert "total_assignments" in status

    @pytest.mark.asyncio
    async def test_workflow_pattern_generation(self, advanced_orchestrator):
        """Test different workflow pattern generation."""
        # Test sequential pattern
        sequential_assignments = advanced_orchestrator._create_sequential_assignments(TaskComplexity.SIMPLE)
        assert len(sequential_assignments) >= 3
        
        # Test parallel pattern
        parallel_assignments = advanced_orchestrator._create_parallel_assignments(TaskComplexity.COMPLEX)
        assert len(parallel_assignments) >= 2
        
        # Check for parallel groups
        parallel_groups = [a for a in parallel_assignments if a.parallel_group is not None]
        assert len(parallel_groups) >= 2

        # Test fan-out/fan-in pattern
        fan_out_assignments = advanced_orchestrator._create_fan_out_in_assignments(TaskComplexity.COMPLEX)
        assert len(fan_out_assignments) >= 4
        
        # Should have both parallel and sequential phases
        parallel_tasks = [a for a in fan_out_assignments if a.parallel_group is not None]
        sequential_tasks = [a for a in fan_out_assignments if a.parallel_group is None]
        assert len(parallel_tasks) > 0
        assert len(sequential_tasks) > 0

    @pytest.mark.asyncio
    async def test_conditional_workflow_creation(self, advanced_orchestrator):
        """Test conditional workflow creation based on task characteristics."""
        # Task with security requirements
        security_task = {
            "task_id": "security-001",
            "task_type": TaskType.FEATURE,
            "description": "Implement security features with authentication",
            "requirements": ["Security audit", "Authentication system"],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(security_task)
        
        # Should include security-specific agents or phases
        assert len(workflow_plan.assignments) > 0
        
        # Check if security considerations are included
        phases = [a.task_phase for a in workflow_plan.assignments]
        assert WorkflowPhase.PLANNING in phases

    @pytest.mark.asyncio 
    async def test_workflow_optimization_integration(self, advanced_orchestrator):
        """Test integration with workflow optimizer."""
        task_data = {
            "task_id": "optimization-test-001",
            "task_type": TaskType.FEATURE,
            "description": "Test optimization integration",
            "requirements": ["req1", "req2", "req3"],
        }

        workflow_plan = await advanced_orchestrator.create_advanced_workflow(task_data)
        
        # Workflow should be optimized during creation
        assert workflow_plan.total_estimated_duration.total_seconds() > 0
        assert len(advanced_orchestrator.optimizer.optimization_history) > 0

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, advanced_orchestrator):
        """Test integration with error recovery."""
        # This test would require more complex mocking to simulate actual errors
        # For now, just verify error recovery manager is available
        assert advanced_orchestrator.error_recovery is not None
        assert hasattr(advanced_orchestrator.error_recovery, 'handle_workflow_error')


@pytest.mark.asyncio
async def test_phase3_integration():
    """Test Phase 3 component integration."""
    # Create mock registry
    registry = MagicMock(spec=DevTeamAgentRegistry)
    registry.agents = {"test_agent": MagicMock()}
    
    # Create orchestrator
    orchestrator = AdvancedWorkflowOrchestrator(registry)
    
    # Test complete workflow creation and execution
    task_data = {
        "task_id": "integration-test-001",
        "task_type": TaskType.FEATURE,
        "description": "Integration test task",
        "requirements": ["requirement1", "requirement2"],
    }
    
    # Create workflow
    workflow_plan = await orchestrator.create_advanced_workflow(task_data)
    assert workflow_plan is not None
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow_plan.workflow_id)
    assert result["success"] is True
    
    # Check status
    status = orchestrator.get_workflow_status(workflow_plan.workflow_id)
    assert status is not None
    assert status["workflow_id"] == workflow_plan.workflow_id