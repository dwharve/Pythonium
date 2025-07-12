"""
Tests for the DevTeam Manager.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pythonium.common.config import PythoniumSettings
from pythonium.common.events import EventManager
from pythonium.managers.devteam import DevTeamManager
from pythonium.managers.devteam_events import (
    TaskPriority,
    TaskStatus,
    TaskType,
    WorkflowPhase,
    create_task_submission_event,
)


class TestDevTeamManager:
    """Test cases for DevTeam Manager."""

    @pytest.fixture
    async def manager(self):
        """Create a DevTeam manager instance for testing."""
        manager = DevTeamManager()

        # Mock event manager
        event_manager = MagicMock(spec=EventManager)
        event_manager.publish = AsyncMock()
        event_manager.subscribe = MagicMock()

        # Mock settings
        settings = MagicMock(spec=PythoniumSettings)

        # Initialize the manager
        await manager.initialize(settings=settings, event_manager=event_manager)
        await manager.start()

        yield manager

        # Cleanup
        await manager.stop()
        await manager.dispose()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test that the manager initializes correctly."""
        assert manager.is_running
        assert manager.state.value == "running"
        assert len(manager._agents) > 0
        assert "project_manager" in [
            agent["type"] for agent in manager._agents.values()
        ]

    @pytest.mark.asyncio
    async def test_task_submission_validation(self, manager):
        """Test task submission data validation."""
        # Valid task data
        valid_data = {
            "task_id": "test-001",
            "task_type": "feature",
            "title": "Test Feature",
            "description": "A test feature implementation",
            "submitter": "test_tool",
        }

        task_event = manager._validate_task_submission(valid_data)
        assert task_event.task_id == "test-001"
        assert task_event.task_type == TaskType.FEATURE
        assert task_event.title == "Test Feature"
        assert task_event.submitter == "test_tool"

    @pytest.mark.asyncio
    async def test_task_submission_missing_fields(self, manager):
        """Test task submission with missing required fields."""
        # Missing required field
        invalid_data = {
            "task_id": "test-002",
            "title": "Test Feature",
            "description": "A test feature implementation",
            "submitter": "test_tool",
            # Missing 'task_type'
        }

        with pytest.raises(ValueError, match="Missing required field: task_type"):
            manager._validate_task_submission(invalid_data)

    @pytest.mark.asyncio
    async def test_task_queuing(self, manager):
        """Test that tasks are queued correctly."""
        task_event = create_task_submission_event(
            task_id="test-003",
            task_type=TaskType.BUGFIX,
            title="Test Bug Fix",
            description="Fix a test bug",
            submitter="test_tool",
        )

        await manager._queue_task(task_event)

        # Check that task was stored
        assert "test-003" in manager._active_tasks
        assert manager._task_status["test-003"] in [
            TaskStatus.QUEUED,
            TaskStatus.PLANNING,
        ]
        assert "test-003" in manager._task_progress

    @pytest.mark.asyncio
    async def test_agent_initialization(self, manager):
        """Test that agents are initialized correctly."""
        # Check that default agents are created
        agent_types = [agent["type"] for agent in manager._agents.values()]
        expected_types = [
            "project_manager",
            "architect",
            "developer",
            "reviewer",
            "qa",
            "documentation",
        ]

        for expected_type in expected_types:
            assert expected_type in agent_types

    @pytest.mark.asyncio
    async def test_task_status_retrieval(self, manager):
        """Test getting task status."""
        # Add a test task
        task_event = create_task_submission_event(
            task_id="test-004",
            task_type=TaskType.FEATURE,
            title="Test Status",
            description="Test status retrieval",
            submitter="test_tool",
        )

        await manager._queue_task(task_event)

        # Get task status
        status = manager.get_task_status("test-004")
        assert status is not None
        assert status["task_id"] == "test-004"
        assert status["title"] == "Test Status"
        assert "status" in status
        assert "progress" in status

    @pytest.mark.asyncio
    async def test_team_status(self, manager):
        """Test getting team status."""
        status = manager.get_team_status()

        assert "active_tasks" in status
        assert "queued_tasks" in status
        assert "total_tasks" in status
        assert "agents" in status
        assert "metrics" in status

        # Check agents info
        assert len(status["agents"]) > 0
        for agent_info in status["agents"].values():
            assert "type" in agent_info
            assert "status" in agent_info
            assert "current_tasks" in agent_info
            assert "max_tasks" in agent_info

    @pytest.mark.asyncio
    async def test_health_checks(self, manager):
        """Test manager health checks."""
        # Run health checks
        health_results = await manager.run_health_checks()

        # Should have registered health checks
        assert "state_check" in health_results
        assert "agents_responsive" in health_results
        assert "queue_size" in health_results

        # All should pass initially
        assert all(health_results.values())

    @pytest.mark.asyncio
    async def test_event_handling_setup(self, manager):
        """Test that event handlers are set up correctly."""
        # Event manager should have been called to subscribe
        manager._event_manager.subscribe.assert_called()

        # Check that the right events were subscribed to
        calls = manager._event_manager.subscribe.call_args_list
        subscribed_events = [call[0][0] for call in calls]

        assert "devteam.task.submit" in subscribed_events
        assert "devteam.task.cancel" in subscribed_events

    @pytest.mark.asyncio
    async def test_task_cancellation(self, manager):
        """Test task cancellation functionality."""
        # Add a test task
        task_event = create_task_submission_event(
            task_id="test-cancel",
            task_type=TaskType.FEATURE,
            title="Test Cancellation",
            description="Test task cancellation",
            submitter="test_tool",
        )

        await manager._queue_task(task_event)

        # Verify task is active
        assert "test-cancel" in manager._active_tasks

        # Create cancellation event
        cancel_event = MagicMock()
        cancel_event.data = {"task_id": "test-cancel"}

        # Handle cancellation
        await manager._handle_task_cancellation(cancel_event)

        # Verify task was cancelled
        assert manager._task_status["test-cancel"] == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_workflow_execution(self, manager):
        """Test basic workflow execution."""
        # This is a simplified test of the workflow
        # In a full implementation, this would test LangGraph integration

        # Start workflow execution
        task_id = "test-workflow"
        task_event = create_task_submission_event(
            task_id=task_id,
            task_type=TaskType.FEATURE,
            title="Test Workflow",
            description="Test workflow execution",
            submitter="test_tool",
        )

        manager._active_tasks[task_id] = task_event
        manager._task_status[task_id] = TaskStatus.PLANNING

        # Execute workflow (this will complete quickly in test mode)
        await manager._execute_development_workflow(task_id)

        # Check that task completed - allow a brief moment for async completion
        await asyncio.sleep(0.1)
        assert manager._task_status[task_id] == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_progress_updates(self, manager):
        """Test task progress updates."""
        task_id = "test-progress"

        # Update progress
        await manager._update_task_progress(
            task_id,
            TaskStatus.IN_PROGRESS,
            WorkflowPhase.IMPLEMENTATION,
            50.0,
            recent_accomplishments=["Completed design"],
            next_steps=["Start implementation"],
        )

        # Check progress was stored
        assert task_id in manager._task_progress
        progress = manager._task_progress[task_id]
        assert progress.percentage_complete == 50.0
        assert progress.phase == WorkflowPhase.IMPLEMENTATION
        assert progress.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_concurrent_task_limit(self, manager):
        """Test that concurrent task limit is respected."""
        max_concurrent = manager._config["max_concurrent_tasks"]

        # Add more tasks than the limit
        for i in range(max_concurrent + 2):
            task_event = create_task_submission_event(
                task_id=f"test-concurrent-{i}",
                task_type=TaskType.FEATURE,
                title=f"Test Concurrent {i}",
                description=f"Test concurrent task {i}",
                submitter="test_tool",
            )
            await manager._queue_task(task_event)

        # Check that excess tasks are queued
        planning_or_in_progress = sum(
            1
            for status in manager._task_status.values()
            if status in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]
        )

        assert planning_or_in_progress <= max_concurrent
        assert len(manager._task_queue) >= 2

    @pytest.mark.asyncio
    async def test_task_submission_error_handling(self, manager):
        """Test error handling during task submission."""
        # Create invalid event with missing data
        invalid_event = MagicMock()
        invalid_event.data = {"task_id": "invalid-task"}  # Missing required fields

        # Handle the invalid submission
        await manager._handle_task_submission(invalid_event)

        # Check that error event was published
        manager._event_manager.publish.assert_called()

        # Check for task failed event
        call_args = manager._event_manager.publish.call_args_list
        failed_calls = [
            call for call in call_args if call[0][0] == "devteam.task.failed"
        ]
        assert len(failed_calls) > 0

    @pytest.mark.asyncio
    async def test_background_task_timeout_handling(self, manager):
        """Test timeout handling during shutdown."""

        # Create a long-running background task
        async def long_running_task():
            await asyncio.sleep(15)  # Longer than shutdown timeout (10s)

        # Add to background tasks
        task = asyncio.create_task(long_running_task())
        manager._background_tasks.add(task)

        # Stop manager (should handle timeout gracefully)
        await manager.stop()

        # Task should be cancelled due to timeout
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_list_active_tasks(self, manager):
        """Test listing active tasks functionality."""
        # Add some tasks in different states
        task1 = create_task_submission_event(
            task_id="active-1",
            task_type=TaskType.FEATURE,
            title="Active Task 1",
            description="First active task",
            submitter="test_tool",
        )

        task2 = create_task_submission_event(
            task_id="completed-2",
            task_type=TaskType.BUGFIX,
            title="Completed Task 2",
            description="Second completed task",
            submitter="test_tool",
        )

        await manager._queue_task(task1)
        await manager._queue_task(task2)

        # Mark one as completed
        manager._task_status["completed-2"] = TaskStatus.COMPLETED

        # Get active tasks
        active_tasks = manager.list_active_tasks()

        # Should only have the active task
        assert len(active_tasks) == 1
        assert active_tasks[0]["task_id"] == "active-1"

    @pytest.mark.asyncio
    async def test_missing_task_status_handling(self, manager):
        """Test handling of missing task status."""
        # Try to get status for non-existent task
        status = manager.get_task_status("non-existent-task")
        assert status is None

    @pytest.mark.asyncio
    async def test_invalid_task_type_validation(self, manager):
        """Test validation with invalid task type."""
        invalid_data = {
            "task_id": "test-invalid-type",
            "task_type": "invalid_type",  # Not a valid TaskType
            "title": "Test Invalid Type",
            "description": "Test invalid task type",
            "submitter": "test_tool",
        }

        with pytest.raises(ValueError):
            manager._validate_task_submission(invalid_data)

    @pytest.mark.asyncio
    async def test_task_priority_handling(self, manager):
        """Test task priority validation and handling."""
        # Test with invalid priority (should default to MEDIUM)
        invalid_data = {
            "task_id": "test-priority",
            "task_type": "feature",
            "title": "Test Priority",
            "description": "Test priority handling",
            "submitter": "test_tool",
            "priority": "invalid_priority",
        }

        task_event = manager._validate_task_submission(invalid_data)
        assert task_event.priority == TaskPriority.MEDIUM  # Should default to medium

        # Test with valid priority
        valid_data = {
            "task_id": "test-priority-valid",
            "task_type": "feature",
            "title": "Test Priority Valid",
            "description": "Test valid priority handling",
            "submitter": "test_tool",
            "priority": "high",
        }

        task_event = manager._validate_task_submission(valid_data)
        assert task_event.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_configuration_loading(self, manager):
        """Test configuration loading and validation."""
        # Test that configuration is loaded properly
        assert "max_concurrent_tasks" in manager._config
        assert "agents" in manager._config
        assert "workflow" in manager._config
        assert "quality_gates" in manager._config

        # Test agent configuration
        agents_config = manager._config["agents"]
        assert "project_manager" in agents_config
        assert "developer" in agents_config
        assert agents_config["developer"]["instances"] == 2

    @pytest.mark.asyncio
    async def test_metrics_collection(self, manager):
        """Test custom metrics collection."""
        # Submit a task to generate metrics
        task_event = create_task_submission_event(
            task_id="metrics-test",
            task_type=TaskType.FEATURE,
            title="Metrics Test",
            description="Test metrics collection",
            submitter="test_tool",
        )

        await manager._queue_task(task_event)

        # Check that metrics are collected
        status = manager.get_team_status()
        assert "metrics" in status
        metrics = status["metrics"]

        # Should have some basic metrics
        assert "tasks_submitted" in metrics
        assert metrics["tasks_submitted"] >= 1

    @pytest.mark.asyncio
    async def test_agent_capacity_management(self, manager):
        """Test agent capacity and load balancing."""
        # Check initial agent capacity
        for agent_id, agent in manager._agents.items():
            assert agent["current_tasks"] == 0
            assert agent["max_tasks"] > 0
            assert agent["status"] == "idle"

        # Test capacity calculations
        pm_agent = next(
            agent
            for agent in manager._agents.values()
            if agent["type"] == "project_manager"
        )
        assert pm_agent["max_tasks"] == 10  # From config

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks(self, manager):
        """Test cleanup of completed tasks."""
        # Add an old completed task
        task_event = create_task_submission_event(
            task_id="old-completed",
            task_type=TaskType.FEATURE,
            title="Old Completed Task",
            description="Old task for cleanup",
            submitter="test_tool",
        )

        await manager._queue_task(task_event)
        manager._task_status["old-completed"] = TaskStatus.COMPLETED

        # Manually trigger cleanup (normally runs in background)
        await manager._cleanup_completed_tasks()

        # Task should still exist (cleanup only after 24 hours)
        assert "old-completed" in manager._active_tasks
