"""
Event schemas for the DevTeam Manager.

This module defines the event data structures used for communication
between tools and the DevTeam Manager.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pythonium.common.types import MetadataDict


class TaskType(Enum):
    """Types of development tasks."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class TaskStatus(Enum):
    """Task execution status."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(Enum):
    """Types of development agents."""

    PROJECT_MANAGER = "project_manager"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    QA = "qa"
    DOCUMENTATION = "documentation"


class WorkflowPhase(Enum):
    """Development workflow phases."""

    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DELIVERY = "delivery"


@dataclass
class TaskRequirement:
    """Represents a task requirement."""

    description: str
    type: str = "functional"  # functional, non-functional, technical
    priority: TaskPriority = TaskPriority.MEDIUM
    acceptance_criteria: List[str] = field(default_factory=list)
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class TaskConstraint:
    """Represents a task constraint."""

    type: str  # time, resource, technology, compliance
    description: str
    value: Any
    mandatory: bool = True
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class TaskSubmissionEvent:
    """Event data for task submission."""

    task_id: str
    task_type: TaskType
    title: str
    description: str
    requirements: List[TaskRequirement] = field(default_factory=list)
    constraints: List[TaskConstraint] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    submitter: str = ""
    submitter_type: str = "tool"  # tool, user, system
    context: MetadataDict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    related_task_ids: List[str] = field(default_factory=list)
    estimated_effort_hours: Optional[float] = None

    # Workflow preferences
    skip_architecture: bool = False
    skip_review: bool = False
    skip_testing: bool = False
    skip_documentation: bool = False

    submitted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DevTeamTaskSubmissionEvent:
    """Enhanced task submission event for LangGraph workflow orchestration."""

    task_id: str
    task_type: str  # String for LangGraph compatibility
    title: str
    description: str
    submitter: str
    priority: str  # String for LangGraph compatibility
    requirements: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DevTeamProgressEvent:
    """Progress event for LangGraph workflow tracking."""

    task_id: str
    phase: str
    current_agent: str
    percentage_complete: int
    status: TaskStatus
    timestamp: datetime
    message: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgressEvent:
    """Event data for task progress updates."""

    task_id: str
    status: TaskStatus
    phase: WorkflowPhase
    percentage_complete: float  # 0.0 to 100.0
    current_agent: Optional[AgentType] = None
    current_agent_id: Optional[str] = None

    # Time estimates
    estimated_completion: Optional[datetime] = None
    time_spent_hours: float = 0.0
    time_remaining_hours: Optional[float] = None

    # Progress details
    recent_accomplishments: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

    # Quality metrics
    tests_passing: Optional[int] = None
    tests_failing: Optional[int] = None
    code_coverage: Optional[float] = None
    review_issues: Optional[int] = None

    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class TaskCompletionEvent:
    """Event data for task completion."""

    task_id: str
    status: TaskStatus  # COMPLETED or FAILED

    # Results
    deliverables: List[Dict[str, Any]] = field(default_factory=list)
    documentation_urls: List[str] = field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

    # Summary
    summary: str = ""
    lessons_learned: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Quality metrics
    final_test_coverage: Optional[float] = None
    review_score: Optional[float] = None
    complexity_score: Optional[float] = None

    # Time tracking
    total_time_hours: float = 0.0
    time_per_phase: Dict[str, float] = field(default_factory=dict)

    # Error information (if failed)
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    recovery_suggestions: List[str] = field(default_factory=list)

    completed_at: datetime = field(default_factory=datetime.utcnow)
    completed_by: Optional[str] = None
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class AgentEvent:
    """Event data for agent activities."""

    task_id: str
    agent_type: AgentType
    agent_id: str
    action: str  # assigned, started, completed, error, paused, resumed

    # Work details
    work_description: str = ""
    work_output: Optional[Dict[str, Any]] = None
    time_spent_minutes: float = 0.0

    # Agent state
    current_capacity: float = 1.0  # 0.0 to 1.0
    queue_length: int = 0

    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class CollaborationEvent:
    """Event data for agent collaboration activities."""

    task_id: str
    event_type: str  # handoff, review_request, feedback, dependency, blocking

    # Participants
    from_agent_type: AgentType
    from_agent_id: str
    to_agent_type: Optional[AgentType] = None
    to_agent_id: Optional[str] = None

    # Collaboration details
    message: str = ""
    work_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    review_feedback: Optional[Dict[str, Any]] = None
    dependency_description: Optional[str] = None
    blocking_reason: Optional[str] = None

    # Resolution
    resolution_required: bool = False
    resolution_deadline: Optional[datetime] = None

    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class DevTeamStatusEvent:
    """Event data for overall DevTeam status."""

    # Team status
    active_tasks: int = 0
    queued_tasks: int = 0
    completed_tasks_today: int = 0
    failed_tasks_today: int = 0

    # Agent status
    active_agents: Dict[str, int] = field(default_factory=dict)  # agent_type -> count
    idle_agents: Dict[str, int] = field(default_factory=dict)
    overloaded_agents: Dict[str, int] = field(default_factory=dict)

    # Performance metrics
    average_task_completion_hours: Optional[float] = None
    task_success_rate: Optional[float] = None
    agent_utilization: Dict[str, float] = field(default_factory=dict)

    # System health
    system_load: float = 0.0  # 0.0 to 1.0
    error_rate: float = 0.0
    last_error: Optional[str] = None

    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: MetadataDict = field(default_factory=dict)


# Event name constants
class DevTeamEvents:
    """Constants for DevTeam event names."""

    # Task events
    TASK_SUBMITTED = "devteam.task.submitted"
    TASK_STARTED = "devteam.task.started"
    TASK_PROGRESS = "devteam.task.progress"
    TASK_COMPLETED = "devteam.task.completed"
    TASK_FAILED = "devteam.task.failed"
    TASK_CANCELLED = "devteam.task.cancelled"

    # Agent events
    AGENT_ASSIGNED = "devteam.agent.assigned"
    AGENT_STARTED = "devteam.agent.started"
    AGENT_COMPLETED = "devteam.agent.completed"
    AGENT_ERROR = "devteam.agent.error"
    AGENT_PAUSED = "devteam.agent.paused"
    AGENT_RESUMED = "devteam.agent.resumed"

    # Collaboration events
    COLLABORATION_HANDOFF = "devteam.collaboration.handoff"
    COLLABORATION_REVIEW_REQUEST = "devteam.collaboration.review_request"
    COLLABORATION_FEEDBACK = "devteam.collaboration.feedback"
    COLLABORATION_DEPENDENCY = "devteam.collaboration.dependency"
    COLLABORATION_BLOCKING = "devteam.collaboration.blocking"

    # Status events
    STATUS_UPDATE = "devteam.status.update"
    SYSTEM_HEALTH = "devteam.system.health"

    # Milestone events
    MILESTONE_REACHED = "devteam.milestone.reached"
    PHASE_TRANSITION = "devteam.phase.transition"
    QUALITY_GATE_PASSED = "devteam.quality_gate.passed"
    QUALITY_GATE_FAILED = "devteam.quality_gate.failed"


# Helper functions for event creation
def create_task_submission_event(
    task_id: str,
    task_type: TaskType,
    title: str,
    description: str,
    submitter: str,
    **kwargs,
) -> TaskSubmissionEvent:
    """Create a task submission event with sensible defaults."""
    return TaskSubmissionEvent(
        task_id=task_id,
        task_type=task_type,
        title=title,
        description=description,
        submitter=submitter,
        **kwargs,
    )


def create_progress_event(
    task_id: str,
    status: TaskStatus,
    phase: WorkflowPhase,
    percentage_complete: float,
    **kwargs,
) -> TaskProgressEvent:
    """Create a task progress event with sensible defaults."""
    return TaskProgressEvent(
        task_id=task_id,
        status=status,
        phase=phase,
        percentage_complete=percentage_complete,
        **kwargs,
    )


def create_completion_event(
    task_id: str, status: TaskStatus, **kwargs
) -> TaskCompletionEvent:
    """Create a task completion event with sensible defaults."""
    return TaskCompletionEvent(task_id=task_id, status=status, **kwargs)
