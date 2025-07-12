"""
AI Agent Configuration for DevTeam Manager.

This module provides configuration and base classes for AI agents,
including default settings for local OpenAI-compatible API endpoints.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of AI agents in the development team."""

    PROJECT_MANAGER = "project_manager"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    CODE_REVIEWER = "code_reviewer"
    QA_AGENT = "qa_agent"
    DOCUMENTATION_AGENT = "documentation_agent"


class ModelProvider(str, Enum):
    """AI model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OLLAMA = "ollama"


@dataclass
class AIModelConfig:
    """Configuration for AI models."""

    provider: ModelProvider = ModelProvider.OPENAI
    model_name: str = "gpt-4"
    api_base: str = "http://localhost:1234/v1"  # Default to localhost
    api_key: str = "local-key"  # Default local key
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    max_retries: int = 3

    def __post_init__(self):
        """Set environment-based defaults."""
        # Use environment variables if available
        if self.provider == ModelProvider.OPENAI:
            self.api_base = os.getenv("OPENAI_API_BASE", self.api_base)
            self.api_key = os.getenv("OPENAI_API_KEY", self.api_key)
            self.model_name = os.getenv("OPENAI_MODEL", self.model_name)
        elif self.provider == ModelProvider.ANTHROPIC:
            self.api_key = os.getenv("ANTHROPIC_API_KEY", self.api_key)
            self.model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        elif self.provider == ModelProvider.OLLAMA:
            self.api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
            self.api_key = "ollama"  # Ollama doesn't require API key
            self.model_name = os.getenv("OLLAMA_MODEL", "llama2")


@dataclass
class AgentCapabilities:
    """Capabilities and constraints for an AI agent."""

    can_generate_code: bool = False
    can_review_code: bool = False
    can_write_tests: bool = False
    can_write_docs: bool = False
    can_plan_projects: bool = False
    can_design_architecture: bool = False
    max_concurrent_tasks: int = 3
    supported_languages: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)


@dataclass
class AgentPersonality:
    """Personality traits for an AI agent."""

    communication_style: str = "professional"  # professional, friendly, formal, casual
    detail_level: str = "balanced"  # high, balanced, low
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    creativity_level: str = "balanced"  # low, balanced, high
    collaboration_preference: str = "cooperative"  # independent, cooperative, lead


@dataclass
class AgentConfig:
    """Complete configuration for an AI agent."""

    agent_type: AgentType
    name: str
    model_config: AIModelConfig
    capabilities: AgentCapabilities
    personality: AgentPersonality
    system_prompt: str = ""
    enabled: bool = True

    def __post_init__(self):
        """Set default system prompt if not provided."""
        if not self.system_prompt:
            self.system_prompt = self._get_default_system_prompt()

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt based on agent type."""
        prompts = {
            AgentType.PROJECT_MANAGER: """You are an AI Project Manager for a software development team. Your responsibilities include:
- Breaking down complex tasks into manageable subtasks
- Estimating effort and timelines
- Identifying risks and dependencies
- Coordinating team activities
- Tracking progress and updating stakeholders

Always be clear, organized, and focus on practical solutions. Communicate in a professional but approachable manner.""",
            AgentType.ARCHITECT: """You are an AI System Architect for software projects. Your responsibilities include:
- Designing system architecture and component relationships
- Selecting appropriate technologies and patterns
- Ensuring scalability, performance, and maintainability
- Creating technical specifications and diagrams
- Reviewing architectural decisions for alignment with requirements

Focus on creating robust, scalable designs that follow best practices and industry standards.""",
            AgentType.DEVELOPER: """You are an AI Software Developer. Your responsibilities include:
- Writing clean, efficient, and well-documented code
- Implementing features according to specifications
- Following coding standards and best practices
- Writing unit tests for your code
- Debugging and fixing issues

Always prioritize code quality, readability, and maintainability. Include appropriate comments and documentation.""",
            AgentType.CODE_REVIEWER: """You are an AI Code Reviewer. Your responsibilities include:
- Reviewing code for quality, style, and best practices
- Identifying potential bugs, security issues, and performance problems
- Ensuring code follows team standards and conventions
- Providing constructive feedback and suggestions
- Verifying test coverage and documentation

Be thorough but constructive in your reviews. Focus on helping improve code quality while being respectful.""",
            AgentType.QA_AGENT: """You are an AI Quality Assurance Agent. Your responsibilities include:
- Creating comprehensive test plans and test cases
- Executing tests and reporting bugs
- Verifying bug fixes and conducting regression testing
- Ensuring software meets quality standards
- Automating testing processes where possible

Focus on finding issues early and ensuring high-quality software delivery.""",
            AgentType.DOCUMENTATION_AGENT: """You are an AI Documentation Specialist. Your responsibilities include:
- Writing clear, comprehensive documentation
- Creating API documentation and user guides
- Maintaining up-to-date technical documentation
- Ensuring documentation is accessible and well-organized
- Generating code comments and inline documentation

Focus on clarity, completeness, and usability of all documentation.""",
        }

        return prompts.get(
            self.agent_type,
            "You are an AI assistant helping with software development.",
        )


class DevTeamAgentRegistry:
    """Registry for managing AI agent configurations."""

    def __init__(self):
        """Initialize the agent registry."""
        self.agents: Dict[str, AgentConfig] = {}
        self._setup_default_agents()

    def _setup_default_agents(self) -> None:
        """Set up default agent configurations."""
        # Default model config (localhost OpenAI-compatible)
        default_model = AIModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            api_base="http://localhost:1234/v1",
            api_key="local-key",
            temperature=0.7,
            max_tokens=2000,
        )

        # Project Manager
        self.agents["project_manager"] = AgentConfig(
            agent_type=AgentType.PROJECT_MANAGER,
            name="PM-1",
            model_config=default_model,
            capabilities=AgentCapabilities(
                can_plan_projects=True,
                max_concurrent_tasks=5,
                specializations=["project_planning", "risk_management", "coordination"],
            ),
            personality=AgentPersonality(
                communication_style="professional",
                detail_level="balanced",
                collaboration_preference="lead",
            ),
        )

        # System Architect
        self.agents["architect"] = AgentConfig(
            agent_type=AgentType.ARCHITECT,
            name="ARCH-1",
            model_config=default_model,
            capabilities=AgentCapabilities(
                can_design_architecture=True,
                can_review_code=True,
                max_concurrent_tasks=3,
                supported_languages=["python", "javascript", "java", "go", "rust"],
                specializations=["system_design", "scalability", "performance"],
            ),
            personality=AgentPersonality(
                communication_style="formal",
                detail_level="high",
                risk_tolerance="conservative",
            ),
        )

        # Developers (multiple instances)
        for i in range(2):
            dev_model = AIModelConfig(**default_model.__dict__)
            dev_model.temperature = 0.5  # Lower temperature for more deterministic code

            self.agents[f"developer_{i+1}"] = AgentConfig(
                agent_type=AgentType.DEVELOPER,
                name=f"DEV-{i+1}",
                model_config=dev_model,
                capabilities=AgentCapabilities(
                    can_generate_code=True,
                    can_write_tests=True,
                    can_write_docs=True,
                    max_concurrent_tasks=2,
                    supported_languages=[
                        "python",
                        "javascript",
                        "typescript",
                        "html",
                        "css",
                    ],
                    specializations=["web_development", "api_development", "testing"],
                ),
                personality=AgentPersonality(
                    communication_style="friendly",
                    detail_level="high",
                    creativity_level="balanced",
                ),
            )

        # Code Reviewer
        review_model = AIModelConfig(**default_model.__dict__)
        review_model.temperature = 0.3  # Very low temperature for consistent reviews

        self.agents["code_reviewer"] = AgentConfig(
            agent_type=AgentType.CODE_REVIEWER,
            name="REV-1",
            model_config=review_model,
            capabilities=AgentCapabilities(
                can_review_code=True,
                max_concurrent_tasks=4,
                supported_languages=[
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "go",
                ],
                specializations=[
                    "security_review",
                    "performance_analysis",
                    "best_practices",
                ],
            ),
            personality=AgentPersonality(
                communication_style="professional",
                detail_level="high",
                risk_tolerance="conservative",
            ),
        )

        # QA Agent
        self.agents["qa_agent"] = AgentConfig(
            agent_type=AgentType.QA_AGENT,
            name="QA-1",
            model_config=default_model,
            capabilities=AgentCapabilities(
                can_write_tests=True,
                can_review_code=True,
                max_concurrent_tasks=3,
                supported_languages=["python", "javascript", "typescript"],
                specializations=[
                    "test_automation",
                    "bug_detection",
                    "quality_assurance",
                ],
            ),
            personality=AgentPersonality(
                communication_style="professional",
                detail_level="high",
                risk_tolerance="conservative",
            ),
        )

        # Documentation Agent
        self.agents["documentation_agent"] = AgentConfig(
            agent_type=AgentType.DOCUMENTATION_AGENT,
            name="DOC-1",
            model_config=default_model,
            capabilities=AgentCapabilities(
                can_write_docs=True,
                can_review_code=True,
                max_concurrent_tasks=3,
                supported_languages=["markdown", "rst", "html"],
                specializations=[
                    "api_documentation",
                    "user_guides",
                    "technical_writing",
                ],
            ),
            personality=AgentPersonality(
                communication_style="friendly",
                detail_level="balanced",
                creativity_level="balanced",
            ),
        )

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID."""
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: AgentType) -> List[AgentConfig]:
        """Get all agents of a specific type."""
        return [
            agent for agent in self.agents.values() if agent.agent_type == agent_type
        ]

    def get_available_agents(self) -> List[AgentConfig]:
        """Get all enabled agents."""
        return [agent for agent in self.agents.values() if agent.enabled]

    def add_agent(self, agent_id: str, config: AgentConfig) -> None:
        """Add a new agent configuration."""
        self.agents[agent_id] = config

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent configuration."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def update_agent(self, agent_id: str, config: AgentConfig) -> bool:
        """Update an existing agent configuration."""
        if agent_id in self.agents:
            self.agents[agent_id] = config
            return True
        return False

    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent."""
        if agent_id in self.agents:
            self.agents[agent_id].enabled = True
            return True
        return False

    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent."""
        if agent_id in self.agents:
            self.agents[agent_id].enabled = False
            return True
        return False


class AIAgentProtocol(Protocol):
    """Protocol for AI agents."""

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return results."""
        ...

    async def collaborate(
        self, other_agent: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collaborate with another agent."""
        ...

    def get_capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        ...


class BaseAIAgent(ABC):
    """Base class for AI agents."""

    def __init__(self, config: AgentConfig):
        """Initialize the agent."""
        self.config = config
        self.is_busy = False
        self.current_tasks: List[str] = []
        self.task_history: List[Dict[str, Any]] = []

    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return results."""
        pass

    @abstractmethod
    async def collaborate(
        self, other_agent: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collaborate with another agent."""
        pass

    def get_capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        return self.config.capabilities

    def can_accept_task(self) -> bool:
        """Check if agent can accept a new task."""
        return (
            self.config.enabled
            and len(self.current_tasks) < self.config.capabilities.max_concurrent_tasks
        )

    async def start_task(self, task_id: str) -> None:
        """Start working on a task."""
        if self.can_accept_task():
            self.current_tasks.append(task_id)
            if len(self.current_tasks) >= self.config.capabilities.max_concurrent_tasks:
                self.is_busy = True

    async def complete_task(self, task_id: str, result: Dict[str, Any]) -> None:
        """Complete a task."""
        if task_id in self.current_tasks:
            self.current_tasks.remove(task_id)
            self.task_history.append(
                {
                    "task_id": task_id,
                    "completed_at": result.get("completed_at"),
                    "result": result,
                }
            )

            if len(self.current_tasks) < self.config.capabilities.max_concurrent_tasks:
                self.is_busy = False

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.config.name,
            "agent_type": self.config.agent_type,
            "enabled": self.config.enabled,
            "is_busy": self.is_busy,
            "current_tasks": len(self.current_tasks),
            "max_tasks": self.config.capabilities.max_concurrent_tasks,
            "tasks_completed": len(self.task_history),
        }


def create_default_registry() -> DevTeamAgentRegistry:
    """Create a default agent registry with localhost configuration."""
    return DevTeamAgentRegistry()


def get_local_openai_config(
    api_base: str = "http://localhost:1234/v1",
    model: str = "gpt-4",
    api_key: str = "local-key",
) -> AIModelConfig:
    """Get configuration for local OpenAI-compatible API."""
    return AIModelConfig(
        provider=ModelProvider.OPENAI,
        model_name=model,
        api_base=api_base,
        api_key=api_key,
        temperature=0.7,
        max_tokens=2000,
    )


def get_ollama_config(
    api_base: str = "http://localhost:11434/v1", model: str = "llama2"
) -> AIModelConfig:
    """Get configuration for Ollama local API."""
    return AIModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name=model,
        api_base=api_base,
        api_key="ollama",
        temperature=0.7,
        max_tokens=2000,
    )
