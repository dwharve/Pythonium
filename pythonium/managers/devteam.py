"""
DevTeam Manager for the Pythonium MCP server.

This manager utilizes LangGraph to orchestrate a series of AI agents
working together as a complete software development team.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import asdict

from pythonium.common.logging import get_logger
from pythonium.common.events import EventManager
from pythonium.common.exceptions import ManagerError
from pythonium.managers.base import BaseManager, ManagerPriority
from pythonium.managers.devteam_events import (
    TaskSubmissionEvent,
    TaskProgressEvent,
    TaskCompletionEvent,
    AgentEvent,
    CollaborationEvent,
    DevTeamStatusEvent,
    DevTeamEvents,
    TaskType,
    TaskStatus,
    TaskPriority,
    AgentType,
    WorkflowPhase,
    create_task_submission_event,
    create_progress_event,
    create_completion_event,
)

logger = get_logger(__name__)


class DevTeamManager(BaseManager):
    """
    Manager that orchestrates AI agents to function as a software development team.
    
    This manager provides:
    - Task submission and management
    - Agent orchestration and coordination
    - Progress tracking and reporting
    - Event-driven communication with tools
    - Workflow management and quality gates
    """

    def __init__(self):
        super().__init__(
            name="devteam",
            version="1.0.0",
            description="AI-powered software development team manager"
        )
        
        # Set manager priority to normal
        self._info.priority = ManagerPriority.NORMAL
        
        # Task management
        self._active_tasks: Dict[str, TaskSubmissionEvent] = {}
        self._task_queue: List[str] = []
        self._task_status: Dict[str, TaskStatus] = {}
        self._task_progress: Dict[str, TaskProgressEvent] = {}
        
        # Agent management
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._agent_queues: Dict[str, List[str]] = {}
        self._agent_capacity: Dict[str, float] = {}
        
        # Configuration
        self._config = {
            'max_concurrent_tasks': 5,
            'default_timeout_hours': 24,
            'agent_timeout_minutes': 30,
            'agents': {
                'project_manager': {'enabled': True, 'max_tasks': 10},
                'architect': {'enabled': True, 'max_tasks': 3},
                'developer': {'enabled': True, 'instances': 2, 'max_tasks': 5},
                'reviewer': {'enabled': True, 'max_tasks': 8},
                'qa': {'enabled': True, 'max_tasks': 5},
                'documentation': {'enabled': True, 'max_tasks': 3},
            },
            'workflow': {
                'require_architecture_review': True,
                'require_code_review': True,
                'require_testing': True,
                'require_documentation': True,
                'parallel_development': True,
            },
            'quality_gates': {
                'code_coverage_threshold': 80,
                'complexity_threshold': 10,
                'security_scan_required': True,
                'performance_test_required': False,
            }
        }
        
        # Performance tracking (custom metrics go in _custom_metrics)
        self._custom_metrics = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_completion_time': 0.0,
            'agent_utilization': {},
        }
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

    async def _initialize(self) -> None:
        """Initialize the DevTeam manager."""
        logger.info("Initializing DevTeam manager")
        
        # Initialize agents
        await self._initialize_agents()
        
        # Set up event handlers
        await self._setup_event_handlers()
        
        # Register health checks
        await self._register_health_checks()
        
        logger.info("DevTeam manager initialized successfully")

    async def _start(self) -> None:
        """Start the DevTeam manager."""
        logger.info("Starting DevTeam manager")
        
        # Start background tasks
        await self._start_background_tasks()
        
        # Emit startup event
        await self._emit_status_event()
        
        logger.info("DevTeam manager started successfully")

    async def _stop(self) -> None:
        """Stop the DevTeam manager."""
        logger.info("Stopping DevTeam manager")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete with timeout
        if self._background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some background tasks did not shut down gracefully")
        
        self._background_tasks.clear()
        
        logger.info("DevTeam manager stopped successfully")

    async def _cleanup(self) -> None:
        """Clean up DevTeam manager resources."""
        logger.info("Cleaning up DevTeam manager")
        
        # Clear all data structures
        self._active_tasks.clear()
        self._task_queue.clear()
        self._task_status.clear()
        self._task_progress.clear()
        self._agents.clear()
        self._agent_queues.clear()
        self._agent_capacity.clear()
        self._custom_metrics.clear()
        
        logger.info("DevTeam manager cleanup completed")

    async def _initialize_agents(self) -> None:
        """Initialize all configured agents."""
        logger.info("Initializing agents")
        
        for agent_type, config in self._config['agents'].items():
            if not config.get('enabled', False):
                continue
                
            instances = config.get('instances', 1)
            max_tasks = config.get('max_tasks', 5)
            
            for i in range(instances):
                agent_id = f"{agent_type}_{i}" if instances > 1 else agent_type
                
                self._agents[agent_id] = {
                    'type': agent_type,
                    'max_tasks': max_tasks,
                    'current_tasks': 0,
                    'status': 'idle',
                    'created_at': datetime.utcnow(),
                }
                
                self._agent_queues[agent_id] = []
                self._agent_capacity[agent_id] = 1.0
                
                logger.debug(f"Initialized agent: {agent_id}")
        
        logger.info(f"Initialized {len(self._agents)} agents")

    async def _setup_event_handlers(self) -> None:
        """Set up event handlers for task submission."""
        if not self._event_manager:
            return
            
        # Subscribe to task submission events
        self._event_manager.subscribe(
            "devteam.task.submit",
            self._handle_task_submission
        )
        
        # Subscribe to task cancellation events
        self._event_manager.subscribe(
            "devteam.task.cancel",
            self._handle_task_cancellation
        )
        
        logger.info("Event handlers set up successfully")

    async def _register_health_checks(self) -> None:
        """Register custom health checks."""
        from pythonium.managers.base import HealthCheck
        
        # Check if agents are responsive
        def agents_health_check():
            if not self._agents:
                return False
            return all(
                agent['status'] != 'error' 
                for agent in self._agents.values()
            )
        
        self.add_health_check(
            HealthCheck(
                name="agents_responsive",
                check_func=agents_health_check,
                critical=True
            )
        )
        
        # Check task queue size
        def queue_health_check():
            return len(self._task_queue) < self._config['max_concurrent_tasks'] * 2
        
        self.add_health_check(
            HealthCheck(
                name="queue_size",
                check_func=queue_health_check,
                critical=False
            )
        )

    async def _start_background_tasks(self) -> None:
        """Start background processing tasks."""
        # Task processor
        task_processor = asyncio.create_task(self._process_task_queue())
        self._background_tasks.add(task_processor)
        
        # Status reporter
        status_reporter = asyncio.create_task(self._periodic_status_reporting())
        self._background_tasks.add(status_reporter)
        
        # Cleanup completed tasks
        task_cleaner = asyncio.create_task(self._cleanup_completed_tasks())
        self._background_tasks.add(task_cleaner)

    async def _handle_task_submission(self, event) -> None:
        """Handle task submission events."""
        try:
            data = event.data
            logger.info(f"Received task submission: {data.get('task_id', 'unknown')}")
            
            # Validate the submission data
            task_event = self._validate_task_submission(data)
            
            # Queue the task
            await self._queue_task(task_event)
            
            # Acknowledge submission
            await self._emit_task_event(
                DevTeamEvents.TASK_SUBMITTED,
                task_event.task_id,
                {"status": "submitted", "queued_at": datetime.utcnow().isoformat()}
            )
            
        except Exception as e:
            logger.error(f"Failed to handle task submission: {e}")
            if 'task_id' in data:
                await self._emit_task_event(
                    DevTeamEvents.TASK_FAILED,
                    data['task_id'],
                    {"error": str(e), "phase": "submission"}
                )

    async def _handle_task_cancellation(self, event) -> None:
        """Handle task cancellation events."""
        try:
            data = event.data
            task_id = data.get('task_id')
            
            if not task_id:
                logger.error("Task cancellation event missing task_id")
                return
            
            if task_id in self._active_tasks:
                # Cancel the task
                self._task_status[task_id] = TaskStatus.CANCELLED
                
                # Remove from queue if not started
                if task_id in self._task_queue:
                    self._task_queue.remove(task_id)
                
                # Emit cancellation event
                await self._emit_task_event(
                    DevTeamEvents.TASK_CANCELLED,
                    task_id,
                    {"cancelled_at": datetime.utcnow().isoformat()}
                )
                
                logger.info(f"Task {task_id} cancelled successfully")
            else:
                logger.warning(f"Attempted to cancel unknown task: {task_id}")
                
        except Exception as e:
            logger.error(f"Failed to handle task cancellation: {e}")

    def _validate_task_submission(self, data: Dict[str, Any]) -> TaskSubmissionEvent:
        """Validate and convert task submission data."""
        # Required fields
        required_fields = ['task_id', 'task_type', 'title', 'description', 'submitter']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Convert to proper types
        task_type = TaskType(data['task_type']) if isinstance(data['task_type'], str) else data['task_type']
        
        # Handle priority conversion
        priority_value = data.get('priority', 'medium')
        if isinstance(priority_value, str):
            priority_mapping = {
                'low': TaskPriority.LOW,
                'medium': TaskPriority.MEDIUM,
                'high': TaskPriority.HIGH, 
                'urgent': TaskPriority.URGENT,
                'critical': TaskPriority.CRITICAL
            }
            priority = priority_mapping.get(priority_value.lower(), TaskPriority.MEDIUM)
        else:
            priority = priority_value if isinstance(priority_value, TaskPriority) else TaskPriority.MEDIUM
        
        # Create event
        excluded_fields = required_fields + ['priority']  # Exclude priority from kwargs since we handle it explicitly
        return create_task_submission_event(
            task_id=data['task_id'],
            task_type=task_type,
            title=data['title'],
            description=data['description'],
            submitter=data['submitter'],
            priority=priority,
            **{k: v for k, v in data.items() if k not in excluded_fields}
        )

    async def _queue_task(self, task: TaskSubmissionEvent) -> None:
        """Queue a task for processing."""
        # Check if we're at capacity
        if len(self._active_tasks) >= self._config['max_concurrent_tasks']:
            # Queue for later processing
            self._task_queue.append(task.task_id)
            self._task_status[task.task_id] = TaskStatus.QUEUED
        else:
            # Start processing immediately
            self._task_status[task.task_id] = TaskStatus.PLANNING
            
        # Store the task
        self._active_tasks[task.task_id] = task
        self._custom_metrics['tasks_submitted'] += 1
        
        # Create initial progress event
        progress_event = create_progress_event(
            task_id=task.task_id,
            status=self._task_status[task.task_id],
            phase=WorkflowPhase.PLANNING,
            percentage_complete=0.0,
            recent_accomplishments=["Task submitted and validated"],
            next_steps=["Task analysis and planning"]
        )
        
        self._task_progress[task.task_id] = progress_event
        
        logger.info(f"Task {task.task_id} queued for processing")

    async def _process_task_queue(self) -> None:
        """Background task to process the task queue."""
        while not self._shutdown_event.is_set():
            try:
                # Check if we have queued tasks and capacity
                if (self._task_queue and 
                    len([t for t in self._task_status.values() 
                         if t in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]]) < 
                    self._config['max_concurrent_tasks']):
                    
                    # Get next task from queue
                    task_id = self._task_queue.pop(0)
                    
                    # Start processing the task
                    await self._start_task_processing(task_id)
                
                # Wait before checking again
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in task queue processor: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error

    async def _start_task_processing(self, task_id: str) -> None:
        """Start processing a specific task."""
        try:
            task = self._active_tasks[task_id]
            logger.info(f"Starting processing for task {task_id}")
            
            # Update status
            self._task_status[task_id] = TaskStatus.PLANNING
            
            # Emit start event
            await self._emit_task_event(
                DevTeamEvents.TASK_STARTED,
                task_id,
                {"started_at": datetime.utcnow().isoformat()}
            )
            
            # Start the workflow (placeholder for now)
            await self._execute_development_workflow(task_id)
            
        except Exception as e:
            logger.error(f"Failed to start task processing for {task_id}: {e}")
            self._task_status[task_id] = TaskStatus.FAILED
            await self._emit_task_event(
                DevTeamEvents.TASK_FAILED,
                task_id,
                {"error": str(e), "failed_at": datetime.utcnow().isoformat()}
            )

    async def _execute_development_workflow(self, task_id: str) -> None:
        """Execute the development workflow for a task (placeholder implementation)."""
        task = self._active_tasks[task_id]
        
        # This is a simplified workflow - in the full implementation,
        # this would use LangGraph to orchestrate the actual agents
        
        phases = [
            (WorkflowPhase.PLANNING, "Planning and analysis"),
            (WorkflowPhase.ARCHITECTURE, "Architecture design"),
            (WorkflowPhase.IMPLEMENTATION, "Code implementation"),
            (WorkflowPhase.REVIEW, "Code review"),
            (WorkflowPhase.TESTING, "Quality assurance"),
            (WorkflowPhase.DOCUMENTATION, "Documentation"),
            (WorkflowPhase.DELIVERY, "Final delivery")
        ]
        
        for i, (phase, description) in enumerate(phases):
            try:
                logger.info(f"Task {task_id}: Starting {description}")
                
                # Update progress
                progress = ((i + 1) / len(phases)) * 100
                await self._update_task_progress(
                    task_id, 
                    TaskStatus.IN_PROGRESS, 
                    phase, 
                    progress,
                    recent_accomplishments=[f"Completed {description}"],
                    next_steps=[phases[i + 1][1]] if i + 1 < len(phases) else ["Task completion"]
                )
                
                # Simulate work (replace with actual agent work)
                await asyncio.sleep(2.0)
                
            except Exception as e:
                logger.error(f"Error in phase {phase} for task {task_id}: {e}")
                raise
        
        # Mark task as completed
        await self._complete_task(task_id, TaskStatus.COMPLETED)

    async def _update_task_progress(
        self, 
        task_id: str, 
        status: TaskStatus, 
        phase: WorkflowPhase, 
        percentage: float,
        **kwargs
    ) -> None:
        """Update task progress and emit progress event."""
        progress_event = create_progress_event(
            task_id=task_id,
            status=status,
            phase=phase,
            percentage_complete=percentage,
            **kwargs
        )
        
        self._task_progress[task_id] = progress_event
        self._task_status[task_id] = status
        
        # Emit progress event
        await self._emit_event(DevTeamEvents.TASK_PROGRESS, asdict(progress_event))

    async def _complete_task(self, task_id: str, final_status: TaskStatus) -> None:
        """Mark a task as completed and emit completion event."""
        try:
            task = self._active_tasks[task_id]
            
            # Update task status
            self._task_status[task_id] = final_status
            
            # Create completion event
            completion_event = create_completion_event(
                task_id=task_id,
                status=final_status,
                summary=f"Task {task_id} completed successfully",
                deliverables=[
                    {"type": "implementation", "description": "Feature implementation"},
                    {"type": "tests", "description": "Comprehensive test suite"},
                    {"type": "documentation", "description": "Technical documentation"}
                ],
                total_time_hours=2.0,  # Placeholder
            )
            
            # Update metrics
            if final_status == TaskStatus.COMPLETED:
                self._custom_metrics['tasks_completed'] += 1
            else:
                self._custom_metrics['tasks_failed'] += 1
            
            # Emit completion event
            await self._emit_event(DevTeamEvents.TASK_COMPLETED, asdict(completion_event))
            
            logger.info(f"Task {task_id} completed with status {final_status.value}")
            
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")

    async def _periodic_status_reporting(self) -> None:
        """Periodically emit status updates."""
        while not self._shutdown_event.is_set():
            try:
                await self._emit_status_event()
                await asyncio.sleep(30.0)  # Report every 30 seconds
            except Exception as e:
                logger.error(f"Error in status reporting: {e}")
                await asyncio.sleep(60.0)

    async def _cleanup_completed_tasks(self) -> None:
        """Periodically clean up old completed tasks."""
        while not self._shutdown_event.is_set():
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                tasks_to_remove = []
                
                for task_id, task in self._active_tasks.items():
                    if (self._task_status[task_id] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                        task.submitted_at < cutoff_time):
                        tasks_to_remove.append(task_id)
                
                for task_id in tasks_to_remove:
                    self._active_tasks.pop(task_id, None)
                    self._task_status.pop(task_id, None)
                    self._task_progress.pop(task_id, None)
                
                if tasks_to_remove:
                    logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
                
                await asyncio.sleep(3600.0)  # Clean up every hour
                
            except Exception as e:
                logger.error(f"Error in task cleanup: {e}")
                await asyncio.sleep(3600.0)

    async def _emit_status_event(self) -> None:
        """Emit current DevTeam status."""
        status_event = DevTeamStatusEvent(
            active_tasks=len([s for s in self._task_status.values() 
                             if s in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]]),
            queued_tasks=len(self._task_queue),
            completed_tasks_today=self._custom_metrics['tasks_completed'],
            failed_tasks_today=self._custom_metrics['tasks_failed'],
            active_agents={agent_type: 1 for agent_type in self._config['agents'].keys()},
            system_load=len(self._active_tasks) / max(self._config['max_concurrent_tasks'], 1),
        )
        
        await self._emit_event(DevTeamEvents.STATUS_UPDATE, asdict(status_event))

    async def _emit_task_event(self, event_name: str, task_id: str, data: Dict[str, Any]) -> None:
        """Emit a task-related event."""
        event_data = {"task_id": task_id, **data}
        await self._emit_event(event_name, event_data)

    async def _emit_event(self, event_name: str, data: Any) -> None:
        """Emit an event via the event manager."""
        if self._event_manager:
            await self._event_manager.publish(event_name, data, source="devteam_manager")

    # Public interface methods
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task."""
        if task_id not in self._active_tasks:
            return None
            
        task = self._active_tasks[task_id]
        progress = self._task_progress.get(task_id)
        
        return {
            "task_id": task_id,
            "title": task.title,
            "status": self._task_status[task_id].value,
            "progress": progress.percentage_complete if progress else 0.0,
            "phase": progress.phase.value if progress else "unknown",
            "submitted_at": task.submitted_at.isoformat(),
            "submitter": task.submitter
        }

    def get_team_status(self) -> Dict[str, Any]:
        """Get the current status of the entire team."""
        return {
            "active_tasks": len([s for s in self._task_status.values() 
                               if s in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]]),
            "queued_tasks": len(self._task_queue),
            "total_tasks": len(self._active_tasks),
            "agents": {
                agent_id: {
                    "type": agent["type"],
                    "status": agent["status"],
                    "current_tasks": agent["current_tasks"],
                    "max_tasks": agent["max_tasks"]
                }
                for agent_id, agent in self._agents.items()
            },
            "metrics": self._custom_metrics.copy()
        }

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """List all currently active tasks."""
        return [
            self.get_task_status(task_id) 
            for task_id in self._active_tasks.keys()
            if self._task_status[task_id] not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]