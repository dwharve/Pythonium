"""
Tests for the DevTeam Manager Prompt Optimization System.

This module contains comprehensive tests for the prompt optimization functionality,
including performance analysis, A/B testing, and adaptive learning capabilities.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from pythonium.agents import AgentType, AgentConfig, DevTeamAgentRegistry, create_default_registry
from pythonium.managers.devteam_prompt_optimization import (
    AgentPerformanceAnalyzer,
    PerformanceMetrics,
    PromptABTestingFramework,
    PromptOptimizationAgent,
    PromptOptimizationResult,
    PromptTestStatus,
    PromptVariation,
    PromptVariationGenerator,
    PromptVariationType,
)


class TestAgentPerformanceAnalyzer:
    """Test the AgentPerformanceAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a performance analyzer instance."""
        return AgentPerformanceAnalyzer()

    @pytest.mark.asyncio
    async def test_record_task_performance(self, analyzer):
        """Test recording task performance metrics."""
        agent_id = "test_agent"
        task_id = "task_001"
        
        await analyzer.record_task_performance(
            agent_id=agent_id,
            task_id=task_id,
            success=True,
            response_time=1.5,
            quality_score=85.0,
            user_satisfaction=90.0
        )
        
        assert agent_id in analyzer.task_logs
        assert len(analyzer.task_logs[agent_id]) == 1
        
        log = analyzer.task_logs[agent_id][0]
        assert log["task_id"] == task_id
        assert log["success"] is True
        assert log["response_time"] == 1.5
        assert log["quality_score"] == 85.0
        assert log["user_satisfaction"] == 90.0

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, analyzer):
        """Test calculating performance metrics from task logs."""
        agent_id = "test_agent"
        
        # Record multiple tasks
        tasks = [
            {"success": True, "response_time": 1.0, "quality_score": 90.0, "satisfaction": 95.0},
            {"success": True, "response_time": 1.5, "quality_score": 85.0, "satisfaction": 90.0},
            {"success": False, "response_time": 3.0, "quality_score": 40.0, "satisfaction": 30.0},
            {"success": True, "response_time": 1.2, "quality_score": 88.0, "satisfaction": 92.0},
        ]
        
        for i, task in enumerate(tasks):
            await analyzer.record_task_performance(
                agent_id=agent_id,
                task_id=f"task_{i:03d}",
                success=task["success"],
                response_time=task["response_time"],
                quality_score=task["quality_score"],
                user_satisfaction=task["satisfaction"]
            )
        
        metrics = await analyzer.calculate_performance_metrics(agent_id)
        
        assert metrics.total_tasks == 4
        assert metrics.successful_tasks == 3
        assert metrics.failed_tasks == 1
        assert metrics.success_rate == 75.0
        assert metrics.error_rate == 25.0
        assert abs(metrics.average_response_time - 1.675) < 0.001
        assert abs(metrics.quality_score - 75.75) < 0.001
        assert abs(metrics.user_satisfaction - 76.75) < 0.001

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics_with_time_window(self, analyzer):
        """Test calculating metrics with time window filtering."""
        agent_id = "test_agent"
        
        # Mock datetime to control timestamps
        old_time = datetime.now() - timedelta(days=2)
        recent_time = datetime.now()
        
        # Add old task
        analyzer.task_logs[agent_id] = [{
            "task_id": "old_task",
            "timestamp": old_time,
            "success": False,
            "response_time": 5.0,
            "quality_score": 20.0,
            "user_satisfaction": 10.0
        }]
        
        # Add recent task
        await analyzer.record_task_performance(
            agent_id, "recent_task", True, 1.0, 90.0, 95.0
        )
        
        # Get metrics for last day only
        metrics = await analyzer.calculate_performance_metrics(
            agent_id, time_window=timedelta(days=1)
        )
        
        assert metrics.total_tasks == 1
        assert metrics.success_rate == 100.0
        assert metrics.quality_score == 90.0

    @pytest.mark.asyncio
    async def test_compare_performance(self, analyzer):
        """Test performance comparison between baseline and variation."""
        baseline = PerformanceMetrics(
            success_rate=70.0,
            average_response_time=2.0,
            quality_score=75.0,
            user_satisfaction=80.0
        )
        
        variation = PerformanceMetrics(
            success_rate=85.0,
            average_response_time=1.5,
            quality_score=90.0,
            user_satisfaction=92.0
        )
        
        comparison = await analyzer.compare_performance(baseline, variation)
        
        assert abs(comparison["success_rate_improvement"] - 21.43) < 0.1
        assert abs(comparison["response_time_improvement"] - 25.0) < 0.1
        assert abs(comparison["quality_improvement"] - 20.0) < 0.1
        assert abs(comparison["satisfaction_improvement"] - 15.0) < 0.1


class TestPromptVariationGenerator:
    """Test the PromptVariationGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a prompt variation generator instance."""
        return PromptVariationGenerator()

    @pytest.mark.asyncio
    async def test_generate_variations(self, generator):
        """Test generating prompt variations."""
        original_prompt = "You are a helpful AI assistant that writes code."
        agent_type = AgentType.DEVELOPER
        
        variations = await generator.generate_variations(
            original_prompt, agent_type, variation_count=3
        )
        
        assert len(variations) == 3
        
        for variation in variations:
            assert variation.original_prompt == original_prompt
            assert variation.modified_prompt != original_prompt
            assert isinstance(variation.variation_type, PromptVariationType)
            assert variation.variation_id
            assert variation.description
            assert isinstance(variation.created_at, datetime)

    @pytest.mark.asyncio
    async def test_tone_adjustment_variation(self, generator):
        """Test tone adjustment variation."""
        original_prompt = "You are a friendly AI assistant."
        
        result = await generator._adjust_tone(
            original_prompt, 
            "Make the tone more professional and formal",
            AgentType.DEVELOPER
        )
        
        assert "professional" in result or "formal" in result

    @pytest.mark.asyncio
    async def test_structure_modification_variation(self, generator):
        """Test structure modification variation."""
        original_prompt = "Do task A. Then do task B. Finally do task C."
        
        result = await generator._modify_structure(
            original_prompt,
            "Add numbered steps for clarity",
            AgentType.DEVELOPER
        )
        
        assert "1." in result or "2." in result


class TestPromptABTestingFramework:
    """Test the PromptABTestingFramework class."""

    @pytest.fixture
    def analyzer(self):
        """Create a performance analyzer instance."""
        return AgentPerformanceAnalyzer()

    @pytest.fixture
    def framework(self, analyzer):
        """Create an A/B testing framework instance."""
        return PromptABTestingFramework(analyzer)

    @pytest.fixture
    def sample_variations(self):
        """Create sample prompt variations."""
        variations = []
        for i in range(3):
            variation = PromptVariation(
                variation_id=str(uuid.uuid4()),
                original_prompt="Original prompt",
                modified_prompt=f"Modified prompt {i}",
                variation_type=PromptVariationType.TONE_ADJUSTMENT,
                description=f"Variation {i}",
                created_at=datetime.now()
            )
            variations.append(variation)
        return variations

    @pytest.mark.asyncio
    async def test_start_ab_test(self, framework, sample_variations):
        """Test starting an A/B test."""
        agent_id = "test_agent"
        
        test_id = await framework.start_ab_test(
            agent_id, sample_variations, test_duration=timedelta(seconds=1)
        )
        
        assert test_id in framework.active_tests
        assert len(framework.active_tests[test_id]) == 3
        
        for variation in framework.active_tests[test_id]:
            assert variation.test_status == PromptTestStatus.RUNNING

    @pytest.mark.asyncio
    async def test_assign_variation_for_task(self, framework, sample_variations):
        """Test assigning variations for tasks."""
        agent_id = "test_agent"
        
        test_id = await framework.start_ab_test(agent_id, sample_variations)
        
        # Assign variations for multiple tasks
        assignments = []
        for i in range(6):  # More tasks than variations to test round-robin
            task_id = f"task_{i:03d}"
            variation = await framework.assign_variation_for_task(test_id, task_id)
            assignments.append(variation.variation_id)
        
        # Should have used all variations
        unique_assignments = set(assignments)
        assert len(unique_assignments) == 3

    @pytest.mark.asyncio
    async def test_record_test_result(self, framework, sample_variations):
        """Test recording test results."""
        agent_id = "test_agent"
        
        test_id = await framework.start_ab_test(agent_id, sample_variations)
        task_id = "test_task"
        
        # Assign variation and record result
        variation = await framework.assign_variation_for_task(test_id, task_id)
        await framework.record_test_result(
            task_id, success=True, response_time=1.5, quality_score=85.0, user_satisfaction=90.0
        )
        
        # Check that metrics were updated
        assert variation.performance_metrics.total_tasks == 1
        assert variation.performance_metrics.successful_tasks == 1
        assert variation.performance_metrics.success_rate == 100.0
        assert variation.performance_metrics.quality_score == 85.0

    @pytest.mark.asyncio
    async def test_analyze_test_results_insufficient_data(self, framework, sample_variations):
        """Test analyzing results with insufficient data."""
        agent_id = "test_agent"
        
        test_id = await framework.start_ab_test(agent_id, sample_variations)
        
        # Try to analyze with no data
        result = await framework.analyze_test_results(test_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_test_results_with_data(self, framework, sample_variations):
        """Test analyzing results with sufficient data."""
        agent_id = "test_agent"
        
        test_id = await framework.start_ab_test(agent_id, sample_variations)
        
        # Add sufficient data to one variation
        best_variation = sample_variations[1]
        for i in range(35):  # More than minimum required
            best_variation.performance_metrics.total_tasks += 1
            best_variation.performance_metrics.successful_tasks += 1
            best_variation.performance_metrics.response_times.append(1.0)
            best_variation.performance_metrics.quality_scores.append(90.0)
            best_variation.performance_metrics.satisfaction_scores.append(95.0)
        
        # Recalculate derived metrics
        metrics = best_variation.performance_metrics
        metrics.success_rate = 100.0
        metrics.average_response_time = 1.0
        metrics.quality_score = 90.0
        metrics.user_satisfaction = 95.0
        
        # Add some data to baseline
        baseline_variation = sample_variations[0]
        for i in range(30):
            baseline_variation.performance_metrics.total_tasks += 1
            baseline_variation.performance_metrics.successful_tasks += 25  # Lower success rate
            baseline_variation.performance_metrics.response_times.append(2.0)
            baseline_variation.performance_metrics.quality_scores.append(75.0)
            baseline_variation.performance_metrics.satisfaction_scores.append(80.0)
        
        baseline_metrics = baseline_variation.performance_metrics
        baseline_metrics.success_rate = 83.33
        baseline_metrics.average_response_time = 2.0
        baseline_metrics.quality_score = 75.0
        baseline_metrics.user_satisfaction = 80.0
        
        result = await framework.analyze_test_results(test_id)
        
        assert result is not None
        assert result.best_variation == best_variation
        assert result.improvement_percentage > 0


class TestPromptOptimizationAgent:
    """Test the PromptOptimizationAgent class."""

    @pytest.fixture
    def registry(self):
        """Create an agent registry instance."""
        return create_default_registry()

    @pytest.fixture
    def optimizer(self, registry):
        """Create a prompt optimization agent instance."""
        return PromptOptimizationAgent(registry)

    @pytest.mark.asyncio
    async def test_start_optimization_cycle(self, optimizer):
        """Test starting an optimization cycle."""
        agent_id = "developer_1"
        
        test_id = await optimizer.start_optimization_cycle(agent_id)
        
        assert test_id
        assert agent_id in optimizer.active_optimizations
        assert optimizer.active_optimizations[agent_id] == test_id

    @pytest.mark.asyncio
    async def test_get_optimized_prompt_for_task(self, optimizer):
        """Test getting optimized prompt for a task."""
        agent_id = "developer_1"
        task_id = "test_task"
        
        # Start optimization
        test_id = await optimizer.start_optimization_cycle(agent_id)
        
        # Get optimized prompt
        optimized_prompt = await optimizer.get_optimized_prompt_for_task(agent_id, task_id)
        
        # Should return a prompt since optimization is active
        assert optimized_prompt is not None
        assert isinstance(optimized_prompt, str)

    @pytest.mark.asyncio
    async def test_record_task_performance(self, optimizer):
        """Test recording task performance."""
        agent_id = "developer_1"
        task_id = "test_task"
        
        await optimizer.record_task_performance(
            agent_id, task_id, True, 1.5, 85.0, 90.0
        )
        
        # Check that performance was recorded
        assert agent_id in optimizer.performance_analyzer.task_logs
        assert len(optimizer.performance_analyzer.task_logs[agent_id]) == 1

    @pytest.mark.asyncio
    async def test_apply_optimized_prompt(self, optimizer):
        """Test applying an optimized prompt."""
        agent_id = "developer_1"
        new_prompt = "Optimized prompt for better performance"
        
        # Get original prompt
        original_config = optimizer.agent_registry.get_agent(agent_id)
        original_prompt = original_config.system_prompt
        
        # Apply optimized prompt
        success = await optimizer.apply_optimized_prompt(agent_id, new_prompt)
        
        assert success
        
        # Check that prompt was updated
        updated_config = optimizer.agent_registry.get_agent(agent_id)
        assert updated_config.system_prompt == new_prompt
        assert updated_config.system_prompt != original_prompt

    @pytest.mark.asyncio
    async def test_get_optimization_status(self, optimizer):
        """Test getting optimization status."""
        status = await optimizer.get_optimization_status()
        
        assert isinstance(status, dict)
        assert "active_optimizations" in status
        assert "optimization_history" in status
        assert "agents_under_optimization" in status
        assert "recent_improvements" in status


class TestIntegrationPromptOptimization:
    """Integration tests for the complete prompt optimization system."""

    @pytest.fixture
    def registry(self):
        """Create an agent registry instance."""
        return create_default_registry()

    @pytest.fixture
    def optimizer(self, registry):
        """Create a prompt optimization agent instance."""
        return PromptOptimizationAgent(registry)

    @pytest.mark.asyncio
    async def test_full_optimization_cycle(self, optimizer):
        """Test a complete optimization cycle."""
        agent_id = "developer_1"
        
        # Start optimization
        test_id = await optimizer.start_optimization_cycle(agent_id)
        assert test_id
        
        # Simulate task performance over time
        for i in range(40):  # Generate sufficient data
            task_id = f"task_{i:03d}"
            
            # Get optimized prompt (simulates task assignment)
            optimized_prompt = await optimizer.get_optimized_prompt_for_task(agent_id, task_id)
            
            # Simulate task performance (better for some variations)
            success = i % 4 != 0  # 75% success rate
            response_time = 1.0 + (i % 3) * 0.5  # Variable response time
            quality_score = 80.0 + (i % 20)  # Variable quality
            satisfaction = quality_score * 0.9
            
            # Record performance
            await optimizer.record_task_performance(
                agent_id, task_id, success, response_time, quality_score, satisfaction
            )
        
        # Check if optimization is complete
        result = await optimizer.check_optimization_results(agent_id)
        
        # May or may not be complete depending on variation performance
        # This tests the framework works end-to-end
        status = await optimizer.get_optimization_status()
        assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_multiple_agent_optimization(self, optimizer):
        """Test optimizing multiple agents simultaneously."""
        agent_ids = ["developer_1", "code_reviewer", "project_manager"]
        
        # Start optimization for multiple agents
        test_ids = []
        for agent_id in agent_ids:
            test_id = await optimizer.start_optimization_cycle(agent_id)
            test_ids.append(test_id)
        
        # Verify all optimizations are active
        status = await optimizer.get_optimization_status()
        assert status["active_optimizations"] == 3
        assert len(status["agents_under_optimization"]) == 3
        
        # Simulate some task performance
        for agent_id in agent_ids:
            for i in range(10):
                task_id = f"{agent_id}_task_{i:03d}"
                await optimizer.record_task_performance(
                    agent_id, task_id, True, 1.5, 85.0, 90.0
                )
        
        # Check individual results
        for agent_id in agent_ids:
            result = await optimizer.check_optimization_results(agent_id)
            # Results may vary, but framework should handle multiple agents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])