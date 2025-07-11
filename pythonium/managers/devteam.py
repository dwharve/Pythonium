"""
DevTeam Manager for the Pythonium MCP server.

This manager utilizes LangGraph to orchestrate a series of AI agents
working together as a complete software development team.
"""

import asyncio
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from pythonium.agents import DevTeamAgentRegistry, create_default_registry
from pythonium.common.events import EventManager
from pythonium.common.exceptions import ManagerError
from pythonium.common.logging import get_logger
from pythonium.managers.base import BaseManager, ManagerPriority
from pythonium.managers.devteam_events import (
    AgentEvent,
    AgentType,
    CollaborationEvent,
    DevTeamEvents,
    DevTeamStatusEvent,
    DevTeamTaskSubmissionEvent,
    TaskCompletionEvent,
    TaskPriority,
    TaskProgressEvent,
    TaskStatus,
    TaskSubmissionEvent,
    TaskType,
    WorkflowPhase,
    create_completion_event,
    create_progress_event,
    create_task_submission_event,
)
from pythonium.managers.devteam_langgraph import LangGraphWorkflowEngine
from pythonium.managers.devteam_advanced_workflows import AdvancedWorkflowOrchestrator
from pythonium.managers.devteam_prompt_optimization import PromptOptimizationAgent

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
            version="4.0.0",  # Updated version for Phase 4
            description="AI-powered software development team manager with prompt optimization and adaptive learning",
        )

        # Set manager priority to normal
        self._info.priority = ManagerPriority.NORMAL

        # Task management
        self._active_tasks: Dict[str, TaskSubmissionEvent] = {}
        self._task_queue: List[str] = []
        self._task_status: Dict[str, TaskStatus] = {}
        self._task_progress: Dict[str, TaskProgressEvent] = {}

        # Agent management (Phase 2: Enhanced with AI agent registry)
        self._agent_registry: DevTeamAgentRegistry = create_default_registry()
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._agent_queues: Dict[str, List[str]] = {}
        self._agent_capacity: Dict[str, float] = {}

        # LangGraph workflow engine (Phase 2: New)
        self._workflow_engine: Optional[LangGraphWorkflowEngine] = None
        self._active_workflows: Dict[str, str] = {}  # task_id -> workflow_id
        
        # Advanced workflow orchestration (Phase 3: New)
        self._advanced_orchestrator: Optional[AdvancedWorkflowOrchestrator] = None

        # Prompt optimization system (Phase 4: New)
        self._prompt_optimizer: Optional[PromptOptimizationAgent] = None

        # Configuration
        self._config = {
            "max_concurrent_tasks": 5,
            "default_timeout_hours": 24,
            "agent_timeout_minutes": 30,
            "agents": {
                "project_manager": {"enabled": True, "max_tasks": 10},
                "architect": {"enabled": True, "max_tasks": 3},
                "developer": {"enabled": True, "instances": 2, "max_tasks": 5},
                "reviewer": {"enabled": True, "max_tasks": 8},
                "qa": {"enabled": True, "max_tasks": 5},
                "documentation": {"enabled": True, "max_tasks": 3},
            },
            "workflow": {
                "require_architecture_review": True,
                "require_code_review": True,
                "require_testing": True,
                "require_documentation": True,
                "parallel_development": True,
            },
            "quality_gates": {
                "code_coverage_threshold": 80,
                "complexity_threshold": 10,
                "security_scan_required": True,
                "performance_test_required": False,
            },
        }

        # Performance tracking (custom metrics go in _custom_metrics)
        self._custom_metrics = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_completion_time": 0.0,
            "agent_utilization": {},
        }

        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

    async def _initialize(self) -> None:
        """Initialize the DevTeam manager."""
        logger.info("Initializing DevTeam manager with LangGraph workflow engine")

        # Initialize LangGraph workflow engine (Phase 2: New)
        await self._initialize_workflow_engine()

        # Initialize agents
        await self._initialize_agents()

        # Initialize prompt optimization system (Phase 4: New)
        await self._initialize_prompt_optimizer()

        # Set up event handlers
        await self._setup_event_handlers()

        # Register health checks
        await self._register_health_checks()

        logger.info(
            "DevTeam manager initialized successfully with AI workflow orchestration"
        )

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
                    timeout=10.0,
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

        for agent_type, config in self._config["agents"].items():
            if not config.get("enabled", False):
                continue

            instances = config.get("instances", 1)
            max_tasks = config.get("max_tasks", 5)

            for i in range(instances):
                agent_id = f"{agent_type}_{i}" if instances > 1 else agent_type

                self._agents[agent_id] = {
                    "type": agent_type,
                    "max_tasks": max_tasks,
                    "current_tasks": 0,
                    "status": "idle",
                    "created_at": datetime.utcnow(),
                }

                self._agent_queues[agent_id] = []
                self._agent_capacity[agent_id] = 1.0

                logger.debug(f"Initialized agent: {agent_id}")

        logger.info(f"Initialized {len(self._agents)} agents")

    async def _initialize_workflow_engine(self) -> None:
        """Initialize the LangGraph workflow engine (Phase 2)."""
        logger.info("Initializing LangGraph workflow engine")

        # Create workflow engine with event publisher
        self._workflow_engine = LangGraphWorkflowEngine(
            event_publisher=self._publish_workflow_event
        )

        # Initialize advanced workflow orchestrator (Phase 3)
        logger.info("Initializing advanced workflow orchestrator")
        self._advanced_orchestrator = AdvancedWorkflowOrchestrator(self._agent_registry)

        logger.info("LangGraph workflow engine and advanced orchestrator initialized successfully")

    async def _initialize_prompt_optimizer(self) -> None:
        """Initialize the prompt optimization system (Phase 4)."""
        logger.info("Initializing prompt optimization system")

        # Create prompt optimization agent
        self._prompt_optimizer = PromptOptimizationAgent(self._agent_registry)

        logger.info("Prompt optimization system initialized successfully")

    async def _publish_workflow_event(
        self, event_name: str, data: Dict[str, Any]
    ) -> None:
        """Publish workflow events to the event bus."""
        if self._event_manager:
            await self._event_manager.publish(
                event_name, data, source="devteam_langgraph"
            )

    async def _setup_event_handlers(self) -> None:
        """Set up event handlers for task submission."""
        if not self._event_manager:
            return

        # Subscribe to task submission events
        self._event_manager.subscribe(
            "devteam.task.submit", self._handle_task_submission
        )

        # Subscribe to task cancellation events
        self._event_manager.subscribe(
            "devteam.task.cancel", self._handle_task_cancellation
        )

        logger.info("Event handlers set up successfully")

    async def _register_health_checks(self) -> None:
        """Register custom health checks."""
        from pythonium.managers.base import HealthCheck

        # Check if agents are responsive
        def agents_health_check():
            if not self._agents:
                return False
            return all(agent["status"] != "error" for agent in self._agents.values())

        self.add_health_check(
            HealthCheck(
                name="agents_responsive", check_func=agents_health_check, critical=True
            )
        )

        # Check task queue size
        def queue_health_check():
            return len(self._task_queue) < self._config["max_concurrent_tasks"] * 2

        self.add_health_check(
            HealthCheck(
                name="queue_size", check_func=queue_health_check, critical=False
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
            # Handle both event objects and direct dict data
            if hasattr(event, "data"):
                data = event.data
            elif isinstance(event, dict) and "data" in event:
                data = event["data"]
            else:
                data = event

            logger.info(f"Received task submission: {data.get('task_id', 'unknown')}")

            # Validate the submission data
            task_event = self._validate_task_submission(data)

            # Queue the task
            await self._queue_task(task_event)

            # Acknowledge submission
            await self._emit_task_event(
                DevTeamEvents.TASK_SUBMITTED,
                task_event.task_id,
                {"status": "submitted", "queued_at": datetime.utcnow().isoformat()},
            )

        except Exception as e:
            logger.error(f"Failed to handle task submission: {e}")
            # Try to get task_id from various sources
            task_id = None
            try:
                if hasattr(event, "data"):
                    task_id = event.data.get("task_id")
                elif isinstance(event, dict) and "data" in event:
                    task_id = event["data"].get("task_id")
                elif isinstance(event, dict):
                    task_id = event.get("task_id")
            except Exception:
                pass

            if task_id:
                await self._emit_task_event(
                    DevTeamEvents.TASK_FAILED,
                    task_id,
                    {"error": str(e), "phase": "submission"},
                )

    async def _handle_task_cancellation(self, event) -> None:
        """Handle task cancellation events."""
        try:
            data = event.data
            task_id = data.get("task_id")

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
                    {"cancelled_at": datetime.utcnow().isoformat()},
                )

                logger.info(f"Task {task_id} cancelled successfully")
            else:
                logger.warning(f"Attempted to cancel unknown task: {task_id}")

        except Exception as e:
            logger.error(f"Failed to handle task cancellation: {e}")

    def _validate_task_submission(self, data: Dict[str, Any]) -> TaskSubmissionEvent:
        """Validate and convert task submission data."""
        # Required fields
        required_fields = ["task_id", "task_type", "title", "description", "submitter"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Convert to proper types
        task_type = (
            TaskType(data["task_type"])
            if isinstance(data["task_type"], str)
            else data["task_type"]
        )

        # Handle priority conversion
        priority_value = data.get("priority", "medium")
        if isinstance(priority_value, str):
            priority_mapping = {
                "low": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM,
                "high": TaskPriority.HIGH,
                "urgent": TaskPriority.URGENT,
                "critical": TaskPriority.CRITICAL,
            }
            priority = priority_mapping.get(priority_value.lower(), TaskPriority.MEDIUM)
        else:
            priority = (
                priority_value
                if isinstance(priority_value, TaskPriority)
                else TaskPriority.MEDIUM
            )

        # Create event
        excluded_fields = required_fields + [
            "priority"
        ]  # Exclude priority from kwargs since we handle it explicitly
        return create_task_submission_event(
            task_id=data["task_id"],
            task_type=task_type,
            title=data["title"],
            description=data["description"],
            submitter=data["submitter"],
            priority=priority,
            **{k: v for k, v in data.items() if k not in excluded_fields},
        )

    async def _queue_task(self, task: TaskSubmissionEvent) -> None:
        """Queue a task for processing with LangGraph workflow (Phase 2)."""
        # Check if we're at capacity
        if len(self._active_tasks) >= self._config["max_concurrent_tasks"]:
            # Queue for later processing
            self._task_queue.append(task.task_id)
            self._task_status[task.task_id] = TaskStatus.QUEUED
        else:
            # Start processing immediately
            self._task_status[task.task_id] = TaskStatus.PLANNING

            # Phase 2: Start LangGraph workflow execution
            if self._workflow_engine:
                try:
                    # Convert to DevTeamTaskSubmissionEvent for workflow engine
                    workflow_task = DevTeamTaskSubmissionEvent(
                        task_id=task.task_id,
                        task_type=task.task_type.value,
                        title=task.title,
                        description=task.description,
                        submitter=task.submitter,
                        priority=task.priority.value,
                        requirements=getattr(task, "requirements", []),
                        submitted_at=task.submitted_at,
                        metadata=getattr(task, "metadata", {}),
                    )

                    # Execute workflow
                    workflow_id = await self._workflow_engine.execute_workflow(
                        workflow_task
                    )
                    self._active_workflows[task.task_id] = workflow_id

                    logger.info(
                        f"Task {task.task_id} started with workflow {workflow_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to start workflow for task {task.task_id}: {e}"
                    )
                    # Fallback to traditional processing
                    self._task_status[task.task_id] = TaskStatus.FAILED

        # Store the task
        self._active_tasks[task.task_id] = task
        self._custom_metrics["tasks_submitted"] += 1

        # Create initial progress event
        progress_event = create_progress_event(
            task_id=task.task_id,
            status=self._task_status[task.task_id],
            phase=WorkflowPhase.PLANNING,
            percentage_complete=0.0,
            recent_accomplishments=["Task submitted and validated"],
            next_steps=[
                (
                    "LangGraph workflow orchestration initiated"
                    if self._workflow_engine
                    else "Task analysis and planning"
                )
            ],
        )

        self._task_progress[task.task_id] = progress_event

        logger.info(f"Task {task.task_id} queued for processing")

    async def _process_task_queue(self) -> None:
        """Background task to process the task queue."""
        while not self._shutdown_event.is_set():
            try:
                # Check if we have queued tasks and capacity
                if (
                    self._task_queue
                    and len(
                        [
                            t
                            for t in self._task_status.values()
                            if t in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]
                        ]
                    )
                    < self._config["max_concurrent_tasks"]
                ):

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
                {"started_at": datetime.utcnow().isoformat()},
            )

            # Start the workflow (placeholder for now)
            await self._execute_development_workflow(task_id)

        except Exception as e:
            logger.error(f"Failed to start task processing for {task_id}: {e}")
            self._task_status[task_id] = TaskStatus.FAILED
            await self._emit_task_event(
                DevTeamEvents.TASK_FAILED,
                task_id,
                {"error": str(e), "failed_at": datetime.utcnow().isoformat()},
            )

    async def _execute_development_workflow(self, task_id: str) -> None:
        """Execute the development workflow for a task using advanced orchestration."""
        task = self._active_tasks[task_id]
        
        try:
            logger.info(f"Task {task_id}: Creating advanced workflow")
            
            # Convert task to format needed by advanced orchestrator
            task_data = {
                "task_id": task_id,
                "task_type": task.task_type,
                "title": task.title,
                "description": task.description,
                "requirements": task.requirements,
                "priority": task.priority,
            }
            
            # Check for prompt optimization (Phase 4: New)
            start_time = datetime.utcnow()
            
            # Create advanced workflow plan
            if self._advanced_orchestrator:
                workflow_plan = await self._advanced_orchestrator.create_advanced_workflow(task_data)
                self._active_workflows[task_id] = workflow_plan.workflow_id
                
                logger.info(f"Task {task_id}: Created {workflow_plan.pattern.value} workflow with {workflow_plan.complexity.value} complexity")
                
                # Execute the advanced workflow
                result = await self._advanced_orchestrator.execute_workflow(workflow_plan.workflow_id)
                
                # Record performance metrics for prompt optimization (Phase 4: New)
                await self._record_workflow_performance(task_id, result, start_time)
                
                if result["success"]:
                    logger.info(f"Task {task_id}: Advanced workflow completed successfully")
                    await self._complete_task(task_id, TaskStatus.COMPLETED)
                else:
                    logger.error(f"Task {task_id}: Advanced workflow failed: {result.get('error', 'Unknown error')}")
                    await self._complete_task(task_id, TaskStatus.FAILED)
            else:
                # Fallback to legacy workflow if advanced orchestrator not available
                logger.warning(f"Task {task_id}: Advanced orchestrator not available, using legacy workflow")
                await self._execute_legacy_workflow(task_id)
                
        except Exception as e:
            logger.error(f"Error executing workflow for task {task_id}: {e}")
            await self._complete_task(task_id, TaskStatus.FAILED)

    async def _execute_legacy_workflow(self, task_id: str) -> None:
        """Execute the legacy simple workflow (fallback implementation)."""
        task = self._active_tasks[task_id]

        phases = [
            (WorkflowPhase.PLANNING, "Planning and analysis"),
            (WorkflowPhase.ARCHITECTURE, "Architecture design"),
            (WorkflowPhase.IMPLEMENTATION, "Code implementation"),
            (WorkflowPhase.REVIEW, "Code review"),
            (WorkflowPhase.TESTING, "Quality assurance"),
            (WorkflowPhase.DOCUMENTATION, "Documentation"),
            (WorkflowPhase.DELIVERY, "Final delivery"),
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
                    next_steps=(
                        [phases[i + 1][1]]
                        if i + 1 < len(phases)
                        else ["Task completion"]
                    ),
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
        **kwargs,
    ) -> None:
        """Update task progress and emit progress event."""
        progress_event = create_progress_event(
            task_id=task_id,
            status=status,
            phase=phase,
            percentage_complete=percentage,
            **kwargs,
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
                    {"type": "documentation", "description": "Technical documentation"},
                ],
                total_time_hours=2.0,  # Placeholder
            )

            # Update metrics
            if final_status == TaskStatus.COMPLETED:
                self._custom_metrics["tasks_completed"] += 1
            else:
                self._custom_metrics["tasks_failed"] += 1

            # Emit completion event
            await self._emit_event(
                DevTeamEvents.TASK_COMPLETED, asdict(completion_event)
            )

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
                    if (
                        self._task_status[task_id]
                        in [
                            TaskStatus.COMPLETED,
                            TaskStatus.FAILED,
                            TaskStatus.CANCELLED,
                        ]
                        and task.submitted_at < cutoff_time
                    ):
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
            active_tasks=len(
                [
                    s
                    for s in self._task_status.values()
                    if s in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]
                ]
            ),
            queued_tasks=len(self._task_queue),
            completed_tasks_today=self._custom_metrics["tasks_completed"],
            failed_tasks_today=self._custom_metrics["tasks_failed"],
            active_agents={
                agent_type: 1 for agent_type in self._config["agents"].keys()
            },
            system_load=len(self._active_tasks)
            / max(self._config["max_concurrent_tasks"], 1),
        )

        await self._emit_event(DevTeamEvents.STATUS_UPDATE, asdict(status_event))

    async def _emit_task_event(
        self, event_name: str, task_id: str, data: Dict[str, Any]
    ) -> None:
        """Emit a task-related event."""
        event_data = {"task_id": task_id, **data}
        await self._emit_event(event_name, event_data)

    async def _emit_event(self, event_name: str, data: Any) -> None:
        """Emit an event via the event manager."""
        if self._event_manager:
            await self._event_manager.publish(
                event_name, data, source="devteam_manager"
            )

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
            "submitter": task.submitter,
        }

    def get_team_status(self) -> Dict[str, Any]:
        """Get the current status of the entire team."""
        return {
            "active_tasks": len(
                [
                    s
                    for s in self._task_status.values()
                    if s in [TaskStatus.PLANNING, TaskStatus.IN_PROGRESS]
                ]
            ),
            "queued_tasks": len(self._task_queue),
            "total_tasks": len(self._active_tasks),
            "agents": {
                agent_id: {
                    "type": agent["type"],
                    "status": agent["status"],
                    "current_tasks": agent["current_tasks"],
                    "max_tasks": agent["max_tasks"],
                }
                for agent_id, agent in self._agents.items()
            },
            "advanced_workflows": len(self._active_workflows),
            "metrics": self._custom_metrics.copy(),
        }

    def get_advanced_workflow_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get advanced workflow status for a task."""
        if task_id not in self._active_workflows:
            return None
        
        workflow_id = self._active_workflows[task_id]
        if self._advanced_orchestrator:
            return self._advanced_orchestrator.get_workflow_status(workflow_id)
        
        return None

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """List all currently active tasks."""
        return [
            self.get_task_status(task_id)
            for task_id in self._active_tasks.keys()
            if self._task_status[task_id]
            not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]

    # Phase 4: Prompt Optimization Methods

    async def _record_workflow_performance(
        self, task_id: str, workflow_result: Dict[str, Any], start_time: datetime
    ) -> None:
        """Record workflow performance metrics for prompt optimization."""
        if not self._prompt_optimizer:
            return

        try:
            # Calculate metrics
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            success = workflow_result.get("success", False)
            
            # Simple quality scoring based on workflow result
            quality_score = 85.0 if success else 30.0
            if "deliverables" in workflow_result:
                quality_score += len(workflow_result["deliverables"]) * 5.0
            quality_score = min(100.0, quality_score)

            # Assume user satisfaction correlates with success and quality
            user_satisfaction = quality_score * 0.9 if success else quality_score * 0.6

            # Record performance for each agent involved (simplified - record for primary agent)
            primary_agent_id = self._get_primary_agent_for_task(task_id)
            if primary_agent_id:
                await self._prompt_optimizer.record_task_performance(
                    primary_agent_id,
                    task_id,
                    success,
                    response_time,
                    quality_score,
                    user_satisfaction
                )

        except Exception as e:
            logger.error(f"Error recording workflow performance for task {task_id}: {e}")

    def _get_primary_agent_for_task(self, task_id: str) -> Optional[str]:
        """Get the primary agent responsible for a task."""
        # Simplified implementation - in practice this would track actual agent assignments
        task = self._active_tasks.get(task_id)
        if not task:
            return None

        # Default to developer for most tasks
        if task.task_type in ["feature", "bugfix"]:
            return "developer_1"
        elif task.task_type == "documentation":
            return "documentation_agent"
        elif task.task_type == "code_review":
            return "code_reviewer"
        else:
            return "project_manager"

    async def start_prompt_optimization(self, agent_id: str) -> str:
        """Start prompt optimization for a specific agent."""
        if not self._prompt_optimizer:
            raise ManagerError("Prompt optimization system not initialized")

        test_id = await self._prompt_optimizer.start_optimization_cycle(agent_id)
        
        logger.info(f"Started prompt optimization for agent {agent_id} with test ID {test_id}")
        return test_id

    async def get_prompt_optimization_status(self) -> Dict[str, Any]:
        """Get current prompt optimization status."""
        if not self._prompt_optimizer:
            return {"error": "Prompt optimization system not initialized"}

        return await self._prompt_optimizer.get_optimization_status()

    async def check_optimization_results(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Check optimization results for an agent."""
        if not self._prompt_optimizer:
            return None

        result = await self._prompt_optimizer.check_optimization_results(agent_id)
        if result:
            return {
                "agent_type": result.agent_type,
                "improvement_percentage": result.improvement_percentage,
                "confidence_level": result.confidence_level,
                "recommendation": result.recommendation,
                "analysis_summary": result.analysis_summary
            }
        
        return None

    async def apply_prompt_optimization(self, agent_id: str, optimized_prompt: str) -> bool:
        """Apply an optimized prompt to an agent."""
        if not self._prompt_optimizer:
            return False

        success = await self._prompt_optimizer.apply_optimized_prompt(agent_id, optimized_prompt)
        
        if success:
            logger.info(f"Applied optimized prompt to agent {agent_id}")
        else:
            logger.error(f"Failed to apply optimized prompt to agent {agent_id}")
        
        return success
