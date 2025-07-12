"""
Example tool that demonstrates how to use the DevTeam Manager.

This tool shows how external tools can submit development tasks
to the DevTeam Manager and receive progress updates.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from pythonium.tools.base import BaseTool, ToolMetadata, ToolParameter, ParameterType
from pythonium.common.base import Result
from pythonium.common.parameters import validate_parameters
from pythonium.common.events import get_event_manager
from pythonium.managers.devteam_events import (
    TaskType, TaskPriority, DevTeamEvents,
    create_task_submission_event
)


class DevTeamTaskSubmissionTool(BaseTool):
    """Tool for submitting development tasks to the DevTeam Manager."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="devteam_submit_task",
            description="Submit a development task to the DevTeam Manager for processing by AI agents",
            brief_description="Submit development task to AI team",
            category="development",
            tags=["devteam", "development", "ai-agents", "task-management"],
            parameters=[
                ToolParameter(
                    name="title",
                    type=ParameterType.STRING,
                    description="Brief title for the development task",
                    required=True,
                    min_length=5,
                    max_length=100
                ),
                ToolParameter(
                    name="description",
                    type=ParameterType.STRING,
                    description="Detailed description of what needs to be developed",
                    required=True,
                    min_length=10,
                    max_length=2000
                ),
                ToolParameter(
                    name="task_type",
                    type=ParameterType.STRING,
                    description="Type of development task",
                    required=True,
                    enum_values=["feature", "bugfix", "refactor", "analysis", "documentation", "testing", "security", "performance"]
                ),
                ToolParameter(
                    name="priority",
                    type=ParameterType.STRING,
                    description="Priority level for the task",
                    required=False,
                    default_value="medium",
                    enum_values=["low", "medium", "high", "urgent", "critical"]
                ),
                ToolParameter(
                    name="requirements",
                    type=ParameterType.ARRAY,
                    description="List of specific requirements for the task",
                    required=False,
                    default_value=[]
                ),
                ToolParameter(
                    name="tags",
                    type=ParameterType.ARRAY,
                    description="Tags to help categorize the task",
                    required=False,
                    default_value=[]
                )
            ]
        )
    
    @validate_parameters
    async def execute(
        self,
        title: str,
        description: str,
        task_type: str,
        priority: str = "medium",
        requirements: List[str] = None,
        tags: List[str] = None,
        context=None
    ) -> Result:
        """Submit a development task to the DevTeam Manager."""
        try:
            # Generate unique task ID
            task_id = f"task-{uuid.uuid4().hex[:8]}"
            
            # Convert string values to enums
            task_type_enum = TaskType(task_type.upper())
            priority_enum = TaskPriority(priority.upper())
            
            # Get event manager
            event_manager = get_event_manager()
            
            # Create task submission event
            task_data = {
                "task_id": task_id,
                "task_type": task_type,
                "title": title,
                "description": description,
                "priority": priority,
                "submitter": "devteam_tool",
                "submitter_type": "tool",
                "requirements": [{"description": req} for req in (requirements or [])],
                "tags": tags or [],
                "context": {
                    "tool_name": self.metadata.name,
                    "submitted_via": "mcp_tool"
                }
            }
            
            # Submit the task
            await event_manager.publish(
                DevTeamEvents.TASK_SUBMITTED.replace("submitted", "submit"),  # Use "submit" for submission
                task_data,
                source="devteam_tool"
            )
            
            return Result.success_result(
                data={
                    "task_id": task_id,
                    "status": "submitted",
                    "message": f"Development task '{title}' has been submitted to the DevTeam",
                    "task_type": task_type,
                    "priority": priority,
                    "expected_events": [
                        "devteam.task.submitted",
                        "devteam.task.started", 
                        "devteam.task.progress",
                        "devteam.task.completed"
                    ]
                },
                metadata={
                    "tool": "devteam_submit_task",
                    "task_id": task_id
                }
            )
            
        except Exception as e:
            return Result.error_result(f"Failed to submit development task: {e}")


class DevTeamStatusTool(BaseTool):
    """Tool for checking the status of the DevTeam Manager."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="devteam_status",
            description="Get the current status of the DevTeam Manager including active tasks and agent information",
            brief_description="Check DevTeam status",
            category="development",
            tags=["devteam", "status", "monitoring"],
            parameters=[
                ToolParameter(
                    name="include_tasks",
                    type=ParameterType.BOOLEAN,
                    description="Whether to include detailed task information",
                    required=False,
                    default_value=True
                ),
                ToolParameter(
                    name="include_agents",
                    type=ParameterType.BOOLEAN,
                    description="Whether to include agent status information",
                    required=False,
                    default_value=True
                )
            ]
        )
    
    @validate_parameters
    async def execute(
        self,
        include_tasks: bool = True,
        include_agents: bool = True,
        context=None
    ) -> Result:
        """Get the current status of the DevTeam Manager."""
        try:
            # For this example, we'll simulate getting status
            # In a real implementation, this would query the DevTeam Manager
            
            from pythonium.core.managers import get_manager_registry
            
            # Try to get the DevTeam manager
            registry = get_manager_registry()
            devteam_manager = await registry.get_manager("devteam")
            
            if not devteam_manager:
                return Result.error_result("DevTeam Manager is not available")
            
            # Get team status
            team_status = devteam_manager.get_team_status()
            
            result_data = {
                "manager_status": "running" if devteam_manager.is_running else "not_running",
                "active_tasks": team_status.get("active_tasks", 0),
                "queued_tasks": team_status.get("queued_tasks", 0),
                "total_tasks": team_status.get("total_tasks", 0),
            }
            
            if include_tasks:
                # Get active task details
                active_tasks = devteam_manager.list_active_tasks()
                result_data["tasks"] = active_tasks
            
            if include_agents:
                # Get agent information
                result_data["agents"] = team_status.get("agents", {})
            
            # Add metrics
            result_data["metrics"] = team_status.get("metrics", {})
            
            return Result.success_result(
                data=result_data,
                metadata={
                    "tool": "devteam_status",
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
            
        except Exception as e:
            return Result.error_result(f"Failed to get DevTeam status: {e}")


class DevTeamTaskStatusTool(BaseTool):
    """Tool for checking the status of a specific task."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="devteam_task_status",
            description="Get the current status and progress of a specific development task",
            brief_description="Check task status",
            category="development",
            tags=["devteam", "task", "status", "progress"],
            parameters=[
                ToolParameter(
                    name="task_id",
                    type=ParameterType.STRING,
                    description="ID of the task to check status for",
                    required=True,
                    min_length=8,
                    max_length=50
                )
            ]
        )
    
    @validate_parameters
    async def execute(self, task_id: str, context=None) -> Result:
        """Get the status of a specific task."""
        try:
            from pythonium.core.managers import get_manager_registry
            
            # Get the DevTeam manager
            registry = get_manager_registry()
            devteam_manager = await registry.get_manager("devteam")
            
            if not devteam_manager:
                return Result.error_result("DevTeam Manager is not available")
            
            # Get task status
            task_status = devteam_manager.get_task_status(task_id)
            
            if not task_status:
                return Result.error_result(f"Task {task_id} not found")
            
            return Result.success_result(
                data=task_status,
                metadata={
                    "tool": "devteam_task_status",
                    "task_id": task_id
                }
            )
            
        except Exception as e:
            return Result.error_result(f"Failed to get task status: {e}")


# Example usage documentation
USAGE_EXAMPLES = """
## DevTeam Manager Tool Usage Examples

### 1. Submit a Feature Development Task

```python
# Submit a new feature for development
result = await devteam_submit_task(
    title="User Authentication System",
    description="Implement a comprehensive user authentication system with JWT tokens, password reset, and multi-factor authentication support",
    task_type="feature",
    priority="high",
    requirements=[
        "JWT token-based authentication",
        "Password reset functionality", 
        "Multi-factor authentication support",
        "User session management",
        "Security audit logging"
    ],
    tags=["authentication", "security", "user-management"]
)

print(f"Task submitted: {result.data['task_id']}")
```

### 2. Submit a Bug Fix Task

```python
# Submit a bug fix
result = await devteam_submit_task(
    title="Fix Memory Leak in User Session Handler",
    description="Memory leak detected in the user session handler causing server instability after extended use",
    task_type="bugfix",
    priority="urgent",
    requirements=[
        "Identify source of memory leak",
        "Fix memory management issues",
        "Add memory usage monitoring",
        "Ensure no regression in functionality"
    ],
    tags=["bug", "memory", "performance", "stability"]
)
```

### 3. Check DevTeam Status

```python
# Get overall team status
status_result = await devteam_status(
    include_tasks=True,
    include_agents=True
)

print(f"Active tasks: {status_result.data['active_tasks']}")
print(f"Agents: {len(status_result.data['agents'])}")
```

### 4. Check Specific Task Status

```python
# Check task progress
task_result = await devteam_task_status(task_id="task-abc12345")

print(f"Task: {task_result.data['title']}")
print(f"Status: {task_result.data['status']}")
print(f"Progress: {task_result.data['progress']}%")
```

### 5. Event Subscription for Progress Updates

To receive real-time updates on task progress, tools can subscribe to DevTeam events:

```python
from pythonium.common.events import get_event_manager

event_manager = get_event_manager()

# Subscribe to task progress updates
def handle_task_progress(event):
    data = event.data
    print(f"Task {data['task_id']}: {data['percentage_complete']}% complete")
    print(f"Current phase: {data['phase']}")
    print(f"Current agent: {data['current_agent']}")

event_manager.subscribe("devteam.task.progress", handle_task_progress)

# Subscribe to task completion
def handle_task_completion(event):
    data = event.data
    print(f"Task {data['task_id']} completed!")
    print(f"Status: {data['status']}")
    print(f"Deliverables: {data['deliverables']}")

event_manager.subscribe("devteam.task.completed", handle_task_completion)
```

## Integration with Manager Registry

The DevTeam Manager can be registered and managed through the Pythonium manager registry:

```python
from pythonium.core.managers import get_manager_registry
from pythonium.managers import DevTeamManager

# Register the DevTeam manager
registry = get_manager_registry()
registry.register_manager("devteam", DevTeamManager, auto_start=True)

# Start all managers
await registry.start_all_managers()
```
"""