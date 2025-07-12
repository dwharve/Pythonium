"""
Tests for the DevTeam Manager.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from pythonium.managers.devteam import DevTeamManager
from pythonium.managers.devteam_events import (
    TaskType, TaskPriority, TaskStatus, WorkflowPhase,
    create_task_submission_event
)
from pythonium.common.events import EventManager
from pythonium.common.config import PythoniumSettings


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
        assert "project_manager" in [agent['type'] for agent in manager._agents.values()]

    @pytest.mark.asyncio
    async def test_task_submission_validation(self, manager):
        """Test task submission data validation."""
        # Valid task data
        valid_data = {
            'task_id': 'test-001',
            'task_type': 'feature',
            'title': 'Test Feature',
            'description': 'A test feature implementation',
            'submitter': 'test_tool'
        }
        
        task_event = manager._validate_task_submission(valid_data)
        assert task_event.task_id == 'test-001'
        assert task_event.task_type == TaskType.FEATURE
        assert task_event.title == 'Test Feature'
        assert task_event.submitter == 'test_tool'

    @pytest.mark.asyncio
    async def test_task_submission_missing_fields(self, manager):
        """Test task submission with missing required fields."""
        # Missing required field
        invalid_data = {
            'task_id': 'test-002',
            'title': 'Test Feature',
            'description': 'A test feature implementation',
            'submitter': 'test_tool'
            # Missing 'task_type'
        }
        
        with pytest.raises(ValueError, match="Missing required field: task_type"):
            manager._validate_task_submission(invalid_data)

    @pytest.mark.asyncio
    async def test_task_queuing(self, manager):
        """Test that tasks are queued correctly."""
        task_event = create_task_submission_event(
            task_id='test-003',
            task_type=TaskType.BUGFIX,
            title='Test Bug Fix',
            description='Fix a test bug',
            submitter='test_tool'
        )
        
        await manager._queue_task(task_event)
        
        # Check that task was stored
        assert 'test-003' in manager._active_tasks
        assert manager._task_status['test-003'] in [TaskStatus.QUEUED, TaskStatus.PLANNING]
        assert 'test-003' in manager._task_progress

    @pytest.mark.asyncio
    async def test_agent_initialization(self, manager):
        """Test that agents are initialized correctly."""
        # Check that default agents are created
        agent_types = [agent['type'] for agent in manager._agents.values()]
        expected_types = ['project_manager', 'architect', 'developer', 'reviewer', 'qa', 'documentation']
        
        for expected_type in expected_types:
            assert expected_type in agent_types

    @pytest.mark.asyncio
    async def test_task_status_retrieval(self, manager):
        """Test getting task status."""
        # Add a test task
        task_event = create_task_submission_event(
            task_id='test-004',
            task_type=TaskType.FEATURE,
            title='Test Status',
            description='Test status retrieval',
            submitter='test_tool'
        )
        
        await manager._queue_task(task_event)
        
        # Get task status
        status = manager.get_task_status('test-004')
        assert status is not None
        assert status['task_id'] == 'test-004'
        assert status['title'] == 'Test Status'
        assert 'status' in status
        assert 'progress' in status

    @pytest.mark.asyncio
    async def test_team_status(self, manager):
        """Test getting team status."""
        status = manager.get_team_status()
        
        assert 'active_tasks' in status
        assert 'queued_tasks' in status
        assert 'total_tasks' in status
        assert 'agents' in status
        assert 'metrics' in status
        
        # Check agents info
        assert len(status['agents']) > 0
        for agent_info in status['agents'].values():
            assert 'type' in agent_info
            assert 'status' in agent_info
            assert 'current_tasks' in agent_info
            assert 'max_tasks' in agent_info

    @pytest.mark.asyncio
    async def test_health_checks(self, manager):
        """Test manager health checks."""
        # Run health checks
        health_results = await manager.run_health_checks()
        
        # Should have registered health checks
        assert 'state_check' in health_results
        assert 'agents_responsive' in health_results
        assert 'queue_size' in health_results
        
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
            task_id='test-cancel',
            task_type=TaskType.FEATURE,
            title='Test Cancellation',
            description='Test task cancellation',
            submitter='test_tool'
        )
        
        await manager._queue_task(task_event)
        
        # Verify task is active
        assert 'test-cancel' in manager._active_tasks
        
        # Create cancellation event
        cancel_event = MagicMock()
        cancel_event.data = {'task_id': 'test-cancel'}
        
        # Handle cancellation
        await manager._handle_task_cancellation(cancel_event)
        
        # Verify task was cancelled
        assert manager._task_status['test-cancel'] == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_workflow_execution(self, manager):
        """Test basic workflow execution."""
        # This is a simplified test of the workflow
        # In a full implementation, this would test LangGraph integration
        
        # Start workflow execution
        task_id = 'test-workflow'
        task_event = create_task_submission_event(
            task_id=task_id,
            task_type=TaskType.FEATURE,
            title='Test Workflow',
            description='Test workflow execution',
            submitter='test_tool'
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
        task_id = 'test-progress'
        
        # Update progress
        await manager._update_task_progress(
            task_id,
            TaskStatus.IN_PROGRESS,
            WorkflowPhase.IMPLEMENTATION,
            50.0,
            recent_accomplishments=["Completed design"],
            next_steps=["Start implementation"]
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
        max_concurrent = manager._config['max_concurrent_tasks']
        
        # Add more tasks than the limit
        for i in range(max_concurrent + 2):
            task_event = create_task_submission_event(
                task_id=f'test-concurrent-{i}',
                task_type=TaskType.FEATURE,
                title=f'Test Concurrent {i}',
                description=f'Test concurrent task {i}',
                submitter='test_tool'
            )
            await manager._queue_task(task_event)
        
        # Check that excess tasks are queued
        planning_or_in_progress = sum(
            1 for status in manager._task_status.values() 
            if status in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]
        )
        
        assert planning_or_in_progress <= max_concurrent
        assert len(manager._task_queue) >= 2