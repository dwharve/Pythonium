"""
LangGraph integration module for DevTeam Manager.

This module provides LangGraph-based workflow orchestration for AI agents,
enabling sophisticated multi-agent coordination and workflow execution.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypedDict, Union

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from .devteam_events import (
    DevTeamProgressEvent,
    DevTeamTaskSubmissionEvent,
    TaskPriority,
    TaskStatus,
    TaskType,
    WorkflowPhase,
)


class GraphExecutionStatus(str, Enum):
    """Status of graph execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowState(TypedDict):
    """State for DevTeam workflow graphs."""

    task_id: str
    task_type: str
    task_title: str
    task_description: str
    task_priority: str
    requirements: List[str]
    current_phase: str
    current_agent: str
    messages: List[Dict[str, Any]]
    artifacts: Dict[str, Any]
    progress_percentage: int
    errors: List[str]
    checkpoints: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class AgentResponse(BaseModel):
    """Response from an AI agent."""

    agent_type: str
    success: bool
    message: str
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    next_phase: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LangGraphWorkflowEngine:
    """LangGraph-based workflow execution engine."""

    def __init__(self, event_publisher: Optional[Callable] = None):
        """Initialize the workflow engine."""
        self.event_publisher = event_publisher
        self.checkpointer = MemorySaver()
        self.active_workflows: Dict[str, Any] = {}
        self._graphs: Dict[str, StateGraph] = {}
        self._initialize_graphs()

    def _initialize_graphs(self) -> None:
        """Initialize all workflow graphs."""
        self._graphs["feature"] = self._create_feature_workflow()
        self._graphs["bug_fix"] = self._create_bug_fix_workflow()
        self._graphs["documentation"] = self._create_documentation_workflow()
        self._graphs["code_review"] = self._create_code_review_workflow()

    def _create_feature_workflow(self) -> StateGraph:
        """Create feature development workflow graph."""
        graph = StateGraph(WorkflowState)

        # Add nodes for each phase
        graph.add_node("planning", self._planning_node)
        graph.add_node("architecture", self._architecture_node)
        graph.add_node("development", self._development_node)
        graph.add_node("code_review", self._code_review_node)
        graph.add_node("testing", self._testing_node)
        graph.add_node("documentation", self._documentation_node)

        # Define workflow edges
        graph.set_entry_point("planning")
        graph.add_edge("planning", "architecture")
        graph.add_edge("architecture", "development")
        graph.add_edge("development", "code_review")
        graph.add_edge("code_review", "testing")
        graph.add_edge("testing", "documentation")
        graph.add_edge("documentation", END)

        return graph.compile(checkpointer=self.checkpointer)

    def _create_bug_fix_workflow(self) -> StateGraph:
        """Create bug fix workflow graph."""
        graph = StateGraph(WorkflowState)

        # Add nodes
        graph.add_node("analysis", self._bug_analysis_node)
        graph.add_node("reproduction", self._bug_reproduction_node)
        graph.add_node("fix_development", self._development_node)
        graph.add_node("testing", self._testing_node)
        graph.add_node("code_review", self._code_review_node)

        # Define edges
        graph.set_entry_point("analysis")
        graph.add_edge("analysis", "reproduction")
        graph.add_edge("reproduction", "fix_development")
        graph.add_edge("fix_development", "testing")
        graph.add_edge("testing", "code_review")
        graph.add_edge("code_review", END)

        return graph.compile(checkpointer=self.checkpointer)

    def _create_documentation_workflow(self) -> StateGraph:
        """Create documentation workflow graph."""
        graph = StateGraph(WorkflowState)

        # Add nodes
        graph.add_node("analysis", self._doc_analysis_node)
        graph.add_node("writing", self._documentation_node)
        graph.add_node("review", self._doc_review_node)

        # Define edges
        graph.set_entry_point("analysis")
        graph.add_edge("analysis", "writing")
        graph.add_edge("writing", "review")
        graph.add_edge("review", END)

        return graph.compile(checkpointer=self.checkpointer)

    def _create_code_review_workflow(self) -> StateGraph:
        """Create code review workflow graph."""
        graph = StateGraph(WorkflowState)

        # Add nodes
        graph.add_node("review", self._code_review_node)
        graph.add_node("feedback", self._review_feedback_node)

        # Define edges
        graph.set_entry_point("review")
        graph.add_edge("review", "feedback")
        graph.add_edge("feedback", END)

        return graph.compile(checkpointer=self.checkpointer)

    async def _planning_node(self, state: WorkflowState) -> WorkflowState:
        """Project Manager planning phase."""
        await self._publish_progress(state, "planning", "project_manager", 10)

        # Simulate project manager planning
        state["current_phase"] = "planning"
        state["current_agent"] = "project_manager"
        state["progress_percentage"] = 10

        # Add planning artifacts
        state["artifacts"]["project_plan"] = {
            "tasks": [
                "analyze_requirements",
                "design_architecture",
                "implement_feature",
            ],
            "timeline": "5 days",
            "resources": ["1 architect", "2 developers", "1 qa"],
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "project_manager",
                "message": f"Project plan created for: {state['task_title']}",
            }
        )

        return state

    async def _architecture_node(self, state: WorkflowState) -> WorkflowState:
        """System Architect design phase."""
        await self._publish_progress(state, "architecture", "architect", 25)

        state["current_phase"] = "architecture"
        state["current_agent"] = "architect"
        state["progress_percentage"] = 25

        # Add architecture artifacts
        state["artifacts"]["architecture"] = {
            "components": ["api", "database", "frontend"],
            "technologies": ["python", "postgresql", "react"],
            "patterns": ["mvc", "repository", "observer"],
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "architect",
                "message": f"Architecture design completed for: {state['task_title']}",
            }
        )

        return state

    async def _development_node(self, state: WorkflowState) -> WorkflowState:
        """Developer implementation phase."""
        await self._publish_progress(state, "development", "developer", 60)

        state["current_phase"] = "development"
        state["current_agent"] = "developer"
        state["progress_percentage"] = 60

        # Add development artifacts
        state["artifacts"]["code"] = {
            "files_created": [
                "api/endpoints.py",
                "models/user.py",
                "tests/test_user.py",
            ],
            "lines_of_code": 250,
            "test_coverage": 85,
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "developer",
                "message": f"Implementation completed for: {state['task_title']}",
            }
        )

        return state

    async def _code_review_node(self, state: WorkflowState) -> WorkflowState:
        """Code Reviewer phase."""
        await self._publish_progress(state, "code_review", "code_reviewer", 75)

        state["current_phase"] = "code_review"
        state["current_agent"] = "code_reviewer"
        state["progress_percentage"] = 75

        # Add review artifacts
        state["artifacts"]["code_review"] = {
            "issues_found": 2,
            "suggestions": ["Add input validation", "Improve error handling"],
            "approval_status": "approved_with_comments",
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "code_reviewer",
                "message": f"Code review completed for: {state['task_title']}",
            }
        )

        return state

    async def _testing_node(self, state: WorkflowState) -> WorkflowState:
        """QA testing phase."""
        await self._publish_progress(state, "testing", "qa_agent", 90)

        state["current_phase"] = "testing"
        state["current_agent"] = "qa_agent"
        state["progress_percentage"] = 90

        # Add testing artifacts
        state["artifacts"]["testing"] = {
            "test_cases_run": 45,
            "test_cases_passed": 43,
            "coverage_percentage": 88,
            "bugs_found": 2,
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "qa_agent",
                "message": f"Testing completed for: {state['task_title']}",
            }
        )

        return state

    async def _documentation_node(self, state: WorkflowState) -> WorkflowState:
        """Documentation phase."""
        await self._publish_progress(state, "documentation", "documentation_agent", 100)

        state["current_phase"] = "documentation"
        state["current_agent"] = "documentation_agent"
        state["progress_percentage"] = 100

        # Add documentation artifacts
        state["artifacts"]["documentation"] = {
            "api_docs": "Generated OpenAPI specification",
            "user_guide": "User guide updated with new feature",
            "developer_docs": "Code documentation updated",
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "documentation_agent",
                "message": f"Documentation completed for: {state['task_title']}",
            }
        )

        return state

    async def _bug_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """Bug analysis phase."""
        await self._publish_progress(state, "analysis", "developer", 20)

        state["current_phase"] = "analysis"
        state["current_agent"] = "developer"
        state["progress_percentage"] = 20

        state["artifacts"]["bug_analysis"] = {
            "root_cause": "Null pointer exception in user validation",
            "affected_components": ["user_service", "validation_module"],
            "severity": "medium",
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "developer",
                "message": f"Bug analysis completed for: {state['task_title']}",
            }
        )

        return state

    async def _bug_reproduction_node(self, state: WorkflowState) -> WorkflowState:
        """Bug reproduction phase."""
        await self._publish_progress(state, "reproduction", "qa_agent", 40)

        state["current_phase"] = "reproduction"
        state["current_agent"] = "qa_agent"
        state["progress_percentage"] = 40

        state["artifacts"]["reproduction"] = {
            "steps_to_reproduce": [
                "1. Create user with empty email",
                "2. Attempt to validate user",
                "3. Exception occurs",
            ],
            "test_case": "test_user_validation_empty_email.py",
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "qa_agent",
                "message": f"Bug reproduction completed for: {state['task_title']}",
            }
        )

        return state

    async def _doc_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """Documentation analysis phase."""
        await self._publish_progress(state, "analysis", "documentation_agent", 30)

        state["current_phase"] = "analysis"
        state["current_agent"] = "documentation_agent"
        state["progress_percentage"] = 30

        state["artifacts"]["doc_analysis"] = {
            "missing_docs": ["API endpoint /users/create", "Configuration options"],
            "outdated_docs": ["Installation guide", "Migration instructions"],
            "priority": "high",
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "documentation_agent",
                "message": f"Documentation analysis completed for: {state['task_title']}",
            }
        )

        return state

    async def _doc_review_node(self, state: WorkflowState) -> WorkflowState:
        """Documentation review phase."""
        await self._publish_progress(state, "review", "project_manager", 100)

        state["current_phase"] = "review"
        state["current_agent"] = "project_manager"
        state["progress_percentage"] = 100

        state["artifacts"]["doc_review"] = {
            "review_status": "approved",
            "feedback": "Documentation is comprehensive and well-structured",
            "quality_score": 9.2,
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "project_manager",
                "message": f"Documentation review completed for: {state['task_title']}",
            }
        )

        return state

    async def _review_feedback_node(self, state: WorkflowState) -> WorkflowState:
        """Review feedback phase."""
        await self._publish_progress(state, "feedback", "project_manager", 100)

        state["current_phase"] = "feedback"
        state["current_agent"] = "project_manager"
        state["progress_percentage"] = 100

        state["artifacts"]["review_feedback"] = {
            "feedback_provided": True,
            "recommendations": ["Fix security issues", "Improve test coverage"],
            "next_steps": "Address feedback and resubmit",
        }

        state["messages"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "project_manager",
                "message": f"Review feedback provided for: {state['task_title']}",
            }
        )

        return state

    async def _publish_progress(
        self, state: WorkflowState, phase: str, agent: str, percentage: int
    ) -> None:
        """Publish progress update event."""
        if self.event_publisher:
            progress_event = DevTeamProgressEvent(
                task_id=state["task_id"],
                phase=phase,
                current_agent=agent,
                percentage_complete=percentage,
                status=TaskStatus.IN_PROGRESS,
                timestamp=datetime.now(),
                message=f"Workflow in {phase} phase",
                artifacts=state.get("artifacts", {}),
                metadata={"workflow_state": "active"},
            )
            # Use asdict for dataclass serialization
            from dataclasses import asdict

            await self.event_publisher(
                "devteam.progress.update", asdict(progress_event)
            )

    async def execute_workflow(
        self, task_submission: DevTeamTaskSubmissionEvent
    ) -> str:
        """Execute a workflow for the given task."""
        workflow_id = str(uuid.uuid4())

        # Determine workflow type
        task_type = task_submission.task_type.lower()
        if task_type not in self._graphs:
            task_type = "feature"  # Default to feature workflow

        # Initialize workflow state
        initial_state: WorkflowState = {
            "task_id": task_submission.task_id,
            "task_type": task_submission.task_type,
            "task_title": task_submission.title,
            "task_description": task_submission.description,
            "task_priority": task_submission.priority,
            "requirements": task_submission.requirements or [],
            "current_phase": "initialization",
            "current_agent": "system",
            "messages": [],
            "artifacts": {},
            "progress_percentage": 0,
            "errors": [],
            "checkpoints": [],
            "metadata": {
                "workflow_id": workflow_id,
                "created_at": datetime.now().isoformat(),
                "submitter": task_submission.submitter,
            },
        }

        # Store workflow
        self.active_workflows[workflow_id] = {
            "graph": self._graphs[task_type],
            "state": initial_state,
            "status": GraphExecutionStatus.PENDING,
        }

        # Start workflow execution
        asyncio.create_task(self._execute_workflow_async(workflow_id))

        return workflow_id

    async def _execute_workflow_async(self, workflow_id: str) -> None:
        """Execute workflow asynchronously."""
        try:
            workflow = self.active_workflows[workflow_id]
            workflow["status"] = GraphExecutionStatus.RUNNING

            graph = workflow["graph"]
            state = workflow["state"]

            # Create config with thread ID for checkpointing
            config = RunnableConfig(configurable={"thread_id": workflow_id})

            # Execute the graph
            async for chunk in graph.astream(state, config=config):
                # Update workflow state
                workflow["state"].update(chunk)

                # Publish intermediate progress if needed
                if self.event_publisher:
                    current_state = workflow["state"]
                    if (
                        current_state.get("current_phase")
                        and current_state.get("progress_percentage", 0) > 0
                    ):
                        progress_event = DevTeamProgressEvent(
                            task_id=current_state["task_id"],
                            phase=current_state["current_phase"],
                            current_agent=current_state["current_agent"],
                            percentage_complete=current_state["progress_percentage"],
                            status=TaskStatus.IN_PROGRESS,
                            timestamp=datetime.now(),
                            message=f"Workflow progress: {current_state['progress_percentage']}%",
                            artifacts=current_state.get("artifacts", {}),
                            metadata={"workflow_id": workflow_id},
                        )
                        await self.event_publisher(
                            "devteam.progress.update", progress_event.model_dump()
                        )

            # Mark as completed
            workflow["status"] = GraphExecutionStatus.COMPLETED

            # Publish completion event
            if self.event_publisher:
                final_state = workflow["state"]
                completion_event = DevTeamProgressEvent(
                    task_id=final_state["task_id"],
                    phase="completed",
                    current_agent="system",
                    percentage_complete=100,
                    status=TaskStatus.COMPLETED,
                    timestamp=datetime.now(),
                    message="Workflow completed successfully",
                    artifacts=final_state.get("artifacts", {}),
                    metadata={"workflow_id": workflow_id},
                )
                from dataclasses import asdict

                await self.event_publisher(
                    "devteam.task.completed", asdict(completion_event)
                )

        except Exception as e:
            # Handle workflow failure
            workflow = self.active_workflows.get(workflow_id)
            if workflow:
                workflow["status"] = GraphExecutionStatus.FAILED
                workflow["state"]["errors"].append(str(e))

                # Publish failure event
                if self.event_publisher:
                    failure_event = DevTeamProgressEvent(
                        task_id=workflow["state"]["task_id"],
                        phase="failed",
                        current_agent="system",
                        percentage_complete=0,
                        status=TaskStatus.FAILED,
                        timestamp=datetime.now(),
                        message=f"Workflow failed: {str(e)}",
                        artifacts={},
                        metadata={"workflow_id": workflow_id, "error": str(e)},
                    )
                    from dataclasses import asdict

                    await self.event_publisher(
                        "devteam.task.failed", asdict(failure_event)
                    )

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None

        return {
            "workflow_id": workflow_id,
            "status": workflow["status"],
            "current_phase": workflow["state"].get("current_phase"),
            "current_agent": workflow["state"].get("current_agent"),
            "progress_percentage": workflow["state"].get("progress_percentage", 0),
            "messages": workflow["state"].get("messages", []),
            "artifacts": workflow["state"].get("artifacts", {}),
            "errors": workflow["state"].get("errors", []),
        }

    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """Get status of all workflows."""
        return [
            self.get_workflow_status(workflow_id)
            for workflow_id in self.active_workflows.keys()
        ]

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        workflow["status"] = GraphExecutionStatus.CANCELLED

        # Publish cancellation event
        if self.event_publisher:
            cancellation_event = DevTeamProgressEvent(
                task_id=workflow["state"]["task_id"],
                phase="cancelled",
                current_agent="system",
                percentage_complete=workflow["state"].get("progress_percentage", 0),
                status=TaskStatus.CANCELLED,
                timestamp=datetime.now(),
                message="Workflow cancelled by user",
                artifacts=workflow["state"].get("artifacts", {}),
                metadata={"workflow_id": workflow_id},
            )
            from dataclasses import asdict

            await self.event_publisher(
                "devteam.task.cancelled", asdict(cancellation_event)
            )

        return True
