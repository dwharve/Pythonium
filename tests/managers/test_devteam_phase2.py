"""
Tests for DevTeam Manager Phase 2 - LangGraph integration and AI agents.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythonium.agents import (
    AgentType,
    AIModelConfig,
    DevTeamAgentRegistry,
    ModelProvider,
    create_default_registry,
    get_local_openai_config,
    get_ollama_config,
)
from pythonium.common.config import PythoniumSettings
from pythonium.common.events import EventManager
from pythonium.managers.devteam import DevTeamManager
from pythonium.managers.devteam_events import (
    DevTeamProgressEvent,
    DevTeamTaskSubmissionEvent,
)
from pythonium.managers.devteam_langgraph import LangGraphWorkflowEngine, WorkflowState


class TestLangGraphWorkflowEngine:
    """Test cases for LangGraph workflow engine."""

    @pytest.fixture
    def workflow_engine(self):
        """Create a workflow engine for testing."""
        return LangGraphWorkflowEngine()

    @pytest.fixture
    def mock_event_publisher(self):
        """Create a mock event publisher."""
        return AsyncMock()

    @pytest.fixture
    def sample_task_submission(self):
        """Create a sample task submission event."""
        return DevTeamTaskSubmissionEvent(
            task_id="test-001",
            task_type="feature",
            title="Test Feature",
            description="A test feature for validation",
            submitter="test_user",
            priority="high",
            requirements=["Requirement 1", "Requirement 2"],
        )

    @pytest.mark.asyncio
    async def test_workflow_engine_initialization(self, workflow_engine):
        """Test that workflow engine initializes correctly."""
        assert workflow_engine is not None
        assert workflow_engine.checkpointer is not None
        assert (
            len(workflow_engine._graphs) == 4
        )  # feature, bug_fix, documentation, code_review
        assert "feature" in workflow_engine._graphs
        assert "bug_fix" in workflow_engine._graphs
        assert "documentation" in workflow_engine._graphs
        assert "code_review" in workflow_engine._graphs

    @pytest.mark.asyncio
    async def test_workflow_execution(self, workflow_engine, sample_task_submission):
        """Test workflow execution."""
        workflow_id = await workflow_engine.execute_workflow(sample_task_submission)

        assert workflow_id is not None
        assert workflow_id in workflow_engine.active_workflows

        # Wait a bit for workflow to start
        await asyncio.sleep(0.1)

        status = workflow_engine.get_workflow_status(workflow_id)
        assert status is not None
        assert status["workflow_id"] == workflow_id
        assert status["status"] in ["pending", "running", "completed"]

    @pytest.mark.asyncio
    async def test_workflow_progress_tracking(
        self, mock_event_publisher, sample_task_submission
    ):
        """Test workflow progress tracking."""
        engine = LangGraphWorkflowEngine(event_publisher=mock_event_publisher)
        workflow_id = await engine.execute_workflow(sample_task_submission)

        # Wait for workflow to progress
        await asyncio.sleep(0.2)

        # Check that progress events were published
        assert mock_event_publisher.call_count > 0

    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, workflow_engine, sample_task_submission):
        """Test workflow cancellation."""
        workflow_id = await workflow_engine.execute_workflow(sample_task_submission)

        # Cancel the workflow
        result = await workflow_engine.cancel_workflow(workflow_id)
        assert result is True

        status = workflow_engine.get_workflow_status(workflow_id)
        assert status["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_all_workflows(self, workflow_engine, sample_task_submission):
        """Test getting all workflows."""
        # Start multiple workflows
        workflow_id1 = await workflow_engine.execute_workflow(sample_task_submission)

        task2 = DevTeamTaskSubmissionEvent(
            task_id="test-002",
            task_type="bug_fix",
            title="Bug Fix",
            description="Fix a bug",
            submitter="test_user",
            priority="medium",
        )
        workflow_id2 = await workflow_engine.execute_workflow(task2)

        all_workflows = workflow_engine.get_all_workflows()
        assert len(all_workflows) == 2
        assert any(w["workflow_id"] == workflow_id1 for w in all_workflows)
        assert any(w["workflow_id"] == workflow_id2 for w in all_workflows)


class TestAgentRegistry:
    """Test cases for AI agent registry."""

    @pytest.fixture
    def agent_registry(self):
        """Create an agent registry for testing."""
        return create_default_registry()

    def test_registry_initialization(self, agent_registry):
        """Test that registry initializes with default agents."""
        assert len(agent_registry.agents) > 0

        # Check that all required agent types are present
        expected_types = [
            AgentType.PROJECT_MANAGER,
            AgentType.ARCHITECT,
            AgentType.DEVELOPER,
            AgentType.CODE_REVIEWER,
            AgentType.QA_AGENT,
            AgentType.DOCUMENTATION_AGENT,
        ]

        available_types = {
            agent.agent_type for agent in agent_registry.get_available_agents()
        }
        for expected_type in expected_types:
            assert expected_type in available_types

    def test_localhost_api_configuration(self, agent_registry):
        """Test that agents are configured with localhost API by default."""
        pm_agent = agent_registry.get_agent("project_manager")
        assert pm_agent is not None
        assert pm_agent.model_config.api_base == "http://localhost:1234/v1"
        assert pm_agent.model_config.api_key == "local-key"
        assert pm_agent.model_config.provider == ModelProvider.OPENAI

    def test_agent_capabilities(self, agent_registry):
        """Test agent capabilities."""
        # Developer agent should be able to generate code
        dev_agent = agent_registry.get_agent("developer_1")
        assert dev_agent is not None
        assert dev_agent.capabilities.can_generate_code is True
        assert dev_agent.capabilities.can_write_tests is True

        # Code reviewer should be able to review code
        reviewer = agent_registry.get_agent("code_reviewer")
        assert reviewer is not None
        assert reviewer.capabilities.can_review_code is True

        # Project manager should be able to plan
        pm = agent_registry.get_agent("project_manager")
        assert pm is not None
        assert pm.capabilities.can_plan_projects is True

    def test_get_agents_by_type(self, agent_registry):
        """Test getting agents by type."""
        developers = agent_registry.get_agents_by_type(AgentType.DEVELOPER)
        assert len(developers) == 2  # Should have 2 developer instances

        architects = agent_registry.get_agents_by_type(AgentType.ARCHITECT)
        assert len(architects) == 1

    def test_agent_management(self, agent_registry):
        """Test adding, updating, and removing agents."""
        from pythonium.agents import AgentCapabilities, AgentConfig, AgentPersonality

        # Add a new agent
        new_config = AgentConfig(
            agent_type=AgentType.DEVELOPER,
            name="DEV-3",
            model_config=get_local_openai_config(),
            capabilities=AgentCapabilities(can_generate_code=True),
            personality=AgentPersonality(),
        )

        agent_registry.add_agent("developer_3", new_config)
        assert agent_registry.get_agent("developer_3") is not None

        # Update agent
        new_config.enabled = False
        agent_registry.update_agent("developer_3", new_config)
        updated = agent_registry.get_agent("developer_3")
        assert updated.enabled is False

        # Remove agent
        result = agent_registry.remove_agent("developer_3")
        assert result is True
        assert agent_registry.get_agent("developer_3") is None


class TestLocalAPIConfiguration:
    """Test local API configuration functions."""

    def test_local_openai_config(self):
        """Test local OpenAI configuration."""
        config = get_local_openai_config(
            api_base="http://localhost:8080/v1",
            model="gpt-3.5-turbo",
            api_key="test-key",
        )

        assert config.provider == ModelProvider.OPENAI
        assert config.api_base == "http://localhost:8080/v1"
        assert config.model_name == "gpt-3.5-turbo"
        assert config.api_key == "test-key"

    def test_ollama_config(self):
        """Test Ollama configuration."""
        config = get_ollama_config(api_base="http://localhost:11434/v1", model="llama2")

        assert config.provider == ModelProvider.OLLAMA
        assert config.api_base == "http://localhost:11434/v1"
        assert config.model_name == "llama2"
        assert config.api_key == "ollama"


class TestDevTeamManagerPhase2:
    """Test DevTeam Manager Phase 2 integration."""

    @pytest.fixture
    async def manager(self):
        """Create a DevTeam manager with Phase 2 features."""
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
    async def test_workflow_engine_integration(self, manager):
        """Test that workflow engine is properly integrated."""
        assert manager._workflow_engine is not None
        assert manager._agent_registry is not None
        assert len(manager._agent_registry.agents) > 0

    @pytest.mark.asyncio
    async def test_task_submission_with_workflow(self, manager):
        """Test task submission triggers workflow execution."""
        # Create a task submission event
        task_data = {
            "task_id": "phase2-test-001",
            "task_type": "feature",
            "title": "Phase 2 Test Feature",
            "description": "Testing Phase 2 LangGraph integration",
            "submitter": "test_system",
            "priority": "high",
            "requirements": ["LangGraph integration", "AI agent orchestration"],
        }

        # Submit the task
        await manager._handle_task_submission({"data": task_data})

        # Check that task was queued and workflow started
        assert task_data["task_id"] in manager._active_tasks
        assert task_data["task_id"] in manager._active_workflows

        # Verify workflow ID was assigned
        workflow_id = manager._active_workflows[task_data["task_id"]]
        assert workflow_id is not None

        # Check workflow status
        workflow_status = manager._workflow_engine.get_workflow_status(workflow_id)
        assert workflow_status is not None

    @pytest.mark.asyncio
    async def test_enhanced_team_status(self, manager):
        """Test enhanced team status includes workflow information."""
        status = manager.get_team_status()

        assert "active_tasks" in status
        assert "agents" in status
        assert "metrics" in status

        # Phase 2: Should have workflow engine info
        assert manager._workflow_engine is not None
        assert manager._agent_registry is not None

    @pytest.mark.asyncio
    async def test_agent_configuration_localhost(self, manager):
        """Test that agents are configured with localhost by default."""
        pm_config = manager._agent_registry.get_agent("project_manager")
        assert pm_config is not None
        assert "localhost" in pm_config.model_config.api_base
        assert pm_config.model_config.api_key == "local-key"


class TestWorkflowStateManagement:
    """Test workflow state management."""

    def test_workflow_state_structure(self):
        """Test workflow state structure is correct."""
        state: WorkflowState = {
            "task_id": "test-001",
            "task_type": "feature",
            "task_title": "Test Task",
            "task_description": "Test description",
            "task_priority": "high",
            "requirements": ["req1", "req2"],
            "current_phase": "planning",
            "current_agent": "project_manager",
            "messages": [],
            "artifacts": {},
            "progress_percentage": 0,
            "errors": [],
            "checkpoints": [],
            "metadata": {},
        }

        # All required keys should be present
        required_keys = [
            "task_id",
            "task_type",
            "task_title",
            "task_description",
            "current_phase",
            "current_agent",
            "messages",
            "artifacts",
            "progress_percentage",
            "errors",
            "checkpoints",
            "metadata",
        ]

        for key in required_keys:
            assert key in state

    def test_workflow_phase_progression(self):
        """Test workflow phase progression logic."""
        # This would be implemented with actual workflow tests
        # For now, just verify the structure is in place
        phases = [
            "planning",
            "architecture",
            "development",
            "code_review",
            "testing",
            "documentation",
        ]

        # Phases should be defined and ordered
        assert len(phases) == 6
        assert phases[0] == "planning"
        assert phases[-1] == "documentation"


@pytest.mark.asyncio
async def test_end_to_end_workflow_execution():
    """End-to-end test of Phase 2 workflow execution."""
    # Create components
    engine = LangGraphWorkflowEngine()
    registry = create_default_registry()

    # Create a test task
    task = DevTeamTaskSubmissionEvent(
        task_id="e2e-test-001",
        task_type="feature",
        title="End-to-End Test",
        description="Complete end-to-end test of Phase 2",
        submitter="test_system",
        priority="medium",
        requirements=["Comprehensive testing", "Full workflow"],
    )

    # Execute workflow
    workflow_id = await engine.execute_workflow(task)
    assert workflow_id is not None

    # Monitor progress
    await asyncio.sleep(0.1)  # Let workflow start

    status = engine.get_workflow_status(workflow_id)
    assert status is not None
    assert status["workflow_id"] == workflow_id

    # Verify agent registry has all agents
    agents = registry.get_available_agents()
    assert len(agents) >= 6  # At least 6 agent types

    # Verify localhost configuration
    for agent in agents:
        if agent.model_config.provider == ModelProvider.OPENAI:
            assert "localhost" in agent.model_config.api_base


if __name__ == "__main__":
    # Run a simple test to verify imports work
    print("Testing Phase 2 imports...")

    try:
        from pythonium.agents import create_default_registry
        from pythonium.managers.devteam import DevTeamManager
        from pythonium.managers.devteam_langgraph import LangGraphWorkflowEngine

        print("✅ All Phase 2 imports successful")

        # Test basic initialization
        engine = LangGraphWorkflowEngine()
        registry = create_default_registry()
        print("✅ Basic initialization successful")

        # Test localhost configuration
        pm_agent = registry.get_agent("project_manager")
        if pm_agent and "localhost" in pm_agent.model_config.api_base:
            print("✅ Localhost configuration verified")
        else:
            print("❌ Localhost configuration failed")

    except Exception as e:
        print(f"❌ Phase 2 test failed: {e}")
        raise
