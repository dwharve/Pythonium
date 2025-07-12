"""
DevTeam Manager Prompt Optimization Module.

This module provides intelligent prompt optimization capabilities for AI agents,
including performance analysis, A/B testing, and adaptive learning systems.
"""

import asyncio
import json
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pythonium.common.logging import get_logger
from pythonium.agents import AgentConfig, AgentType

logger = get_logger(__name__)


class PromptTestStatus(str, Enum):
    """Status of prompt testing."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptVariationType(str, Enum):
    """Types of prompt variations."""
    
    TONE_ADJUSTMENT = "tone_adjustment"
    STRUCTURE_MODIFICATION = "structure_modification"
    DETAIL_LEVEL_CHANGE = "detail_level_change"
    INSTRUCTION_CLARITY = "instruction_clarity"
    CONTEXT_ENHANCEMENT = "context_enhancement"
    SPECIALIZATION_FOCUS = "specialization_focus"


@dataclass
class PerformanceMetrics:
    """Performance metrics for agent interactions."""
    
    success_rate: float = 0.0
    average_response_time: float = 0.0
    quality_score: float = 0.0  # 0-100 scale
    user_satisfaction: float = 0.0  # 0-100 scale
    task_completion_rate: float = 0.0
    error_rate: float = 0.0
    retry_rate: float = 0.0
    
    # Detailed metrics
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    response_times: List[float] = field(default_factory=list)
    quality_scores: List[float] = field(default_factory=list)
    satisfaction_scores: List[float] = field(default_factory=list)


@dataclass
class PromptVariation:
    """A variation of an agent prompt for testing."""
    
    variation_id: str
    original_prompt: str
    modified_prompt: str
    variation_type: PromptVariationType
    description: str
    created_at: datetime
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    test_status: PromptTestStatus = PromptTestStatus.PENDING
    test_task_count: int = 0
    target_test_count: int = 50  # Minimum tasks for statistical significance


@dataclass
class PromptOptimizationResult:
    """Result of prompt optimization analysis."""
    
    agent_type: AgentType
    original_performance: PerformanceMetrics
    best_variation: Optional[PromptVariation]
    improvement_percentage: float
    confidence_level: float
    recommendation: str
    analysis_summary: str


class AgentPerformanceAnalyzer:
    """Analyzes agent performance metrics for prompt optimization."""
    
    def __init__(self):
        """Initialize the performance analyzer."""
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.task_logs: Dict[str, List[Dict[str, Any]]] = {}
    
    async def record_task_performance(
        self,
        agent_id: str,
        task_id: str,
        success: bool,
        response_time: float,
        quality_score: float,
        user_satisfaction: Optional[float] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record performance metrics for a task."""
        if agent_id not in self.task_logs:
            self.task_logs[agent_id] = []
        
        task_log = {
            "task_id": task_id,
            "timestamp": datetime.now(),
            "success": success,
            "response_time": response_time,
            "quality_score": quality_score,
            "user_satisfaction": user_satisfaction,
            "additional_metrics": additional_metrics or {}
        }
        
        self.task_logs[agent_id].append(task_log)
        logger.debug(f"Recorded task performance for agent {agent_id}: {task_log}")
    
    async def calculate_performance_metrics(
        self,
        agent_id: str,
        time_window: Optional[timedelta] = None
    ) -> PerformanceMetrics:
        """Calculate performance metrics for an agent."""
        if agent_id not in self.task_logs:
            return PerformanceMetrics()
        
        logs = self.task_logs[agent_id]
        
        # Filter by time window if specified
        if time_window:
            cutoff_time = datetime.now() - time_window
            logs = [log for log in logs if log["timestamp"] >= cutoff_time]
        
        if not logs:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        
        # Basic counts
        metrics.total_tasks = len(logs)
        metrics.successful_tasks = sum(1 for log in logs if log["success"])
        metrics.failed_tasks = metrics.total_tasks - metrics.successful_tasks
        
        # Calculate rates
        metrics.success_rate = metrics.successful_tasks / metrics.total_tasks * 100
        metrics.task_completion_rate = metrics.success_rate  # Same for now
        metrics.error_rate = metrics.failed_tasks / metrics.total_tasks * 100
        
        # Response times
        response_times = [log["response_time"] for log in logs]
        metrics.response_times = response_times
        metrics.average_response_time = statistics.mean(response_times)
        
        # Quality scores
        quality_scores = [log["quality_score"] for log in logs if log["quality_score"] is not None]
        if quality_scores:
            metrics.quality_scores = quality_scores
            metrics.quality_score = statistics.mean(quality_scores)
        
        # User satisfaction
        satisfaction_scores = [
            log["user_satisfaction"] for log in logs 
            if log["user_satisfaction"] is not None
        ]
        if satisfaction_scores:
            metrics.satisfaction_scores = satisfaction_scores
            metrics.user_satisfaction = statistics.mean(satisfaction_scores)
        
        return metrics
    
    async def compare_performance(
        self,
        baseline_metrics: PerformanceMetrics,
        variation_metrics: PerformanceMetrics
    ) -> Dict[str, float]:
        """Compare performance between baseline and variation."""
        comparison = {}
        
        if baseline_metrics.success_rate > 0:
            comparison["success_rate_improvement"] = (
                (variation_metrics.success_rate - baseline_metrics.success_rate) 
                / baseline_metrics.success_rate * 100
            )
        
        if baseline_metrics.average_response_time > 0:
            comparison["response_time_improvement"] = (
                (baseline_metrics.average_response_time - variation_metrics.average_response_time)
                / baseline_metrics.average_response_time * 100
            )
        
        if baseline_metrics.quality_score > 0:
            comparison["quality_improvement"] = (
                (variation_metrics.quality_score - baseline_metrics.quality_score)
                / baseline_metrics.quality_score * 100
            )
        
        if baseline_metrics.user_satisfaction > 0:
            comparison["satisfaction_improvement"] = (
                (variation_metrics.user_satisfaction - baseline_metrics.user_satisfaction)
                / baseline_metrics.user_satisfaction * 100
            )
        
        return comparison


class PromptVariationGenerator:
    """Generates variations of prompts for A/B testing."""
    
    def __init__(self):
        """Initialize the prompt variation generator."""
        self.variation_templates = self._load_variation_templates()
    
    def _load_variation_templates(self) -> Dict[PromptVariationType, List[str]]:
        """Load templates for different types of prompt variations."""
        return {
            PromptVariationType.TONE_ADJUSTMENT: [
                "Make the tone more professional and formal",
                "Make the tone more friendly and approachable", 
                "Make the tone more direct and concise",
                "Make the tone more encouraging and supportive"
            ],
            PromptVariationType.STRUCTURE_MODIFICATION: [
                "Add numbered steps for clarity",
                "Use bullet points for better organization",
                "Restructure with clear sections and headers",
                "Add examples and use cases"
            ],
            PromptVariationType.DETAIL_LEVEL_CHANGE: [
                "Provide more detailed explanations and context",
                "Be more concise and focus on key points",
                "Add specific technical requirements",
                "Include edge cases and error handling"
            ],
            PromptVariationType.INSTRUCTION_CLARITY: [
                "Make instructions more explicit and specific",
                "Add clarification on expected outputs",
                "Include validation criteria and success metrics",
                "Specify format and structure requirements"
            ],
            PromptVariationType.CONTEXT_ENHANCEMENT: [
                "Add more context about the project and goals",
                "Include information about team dynamics",
                "Provide background on technology stack",
                "Add context about user requirements"
            ],
            PromptVariationType.SPECIALIZATION_FOCUS: [
                "Emphasize specific technical expertise areas",
                "Focus on domain-specific best practices",
                "Highlight relevant industry standards",
                "Emphasize specialized tools and techniques"
            ]
        }
    
    async def generate_variations(
        self,
        original_prompt: str,
        agent_type: AgentType,
        variation_count: int = 3
    ) -> List[PromptVariation]:
        """Generate variations of a prompt for testing."""
        variations = []
        
        for variation_type in PromptVariationType:
            for i in range(min(variation_count, len(self.variation_templates[variation_type]))):
                template = self.variation_templates[variation_type][i]
                modified_prompt = await self._apply_variation(
                    original_prompt, variation_type, template, agent_type
                )
                
                variation = PromptVariation(
                    variation_id=str(uuid.uuid4()),
                    original_prompt=original_prompt,
                    modified_prompt=modified_prompt,
                    variation_type=variation_type,
                    description=f"{variation_type.value}: {template}",
                    created_at=datetime.now()
                )
                
                variations.append(variation)
        
        return variations[:variation_count]  # Limit to requested count
    
    async def _apply_variation(
        self,
        original_prompt: str,
        variation_type: PromptVariationType,
        template: str,
        agent_type: AgentType
    ) -> str:
        """Apply a specific variation to the original prompt."""
        # This is a simplified implementation
        # In a real system, this would use an LLM to intelligently modify the prompt
        
        variation_instructions = {
            PromptVariationType.TONE_ADJUSTMENT: self._adjust_tone,
            PromptVariationType.STRUCTURE_MODIFICATION: self._modify_structure,
            PromptVariationType.DETAIL_LEVEL_CHANGE: self._change_detail_level,
            PromptVariationType.INSTRUCTION_CLARITY: self._clarify_instructions,
            PromptVariationType.CONTEXT_ENHANCEMENT: self._enhance_context,
            PromptVariationType.SPECIALIZATION_FOCUS: self._focus_specialization
        }
        
        modifier = variation_instructions.get(variation_type)
        if modifier:
            return await modifier(original_prompt, template, agent_type)
        
        return original_prompt
    
    async def _adjust_tone(self, prompt: str, template: str, agent_type: AgentType) -> str:
        """Adjust the tone of the prompt."""
        if "professional and formal" in template:
            return prompt.replace("friendly", "professional").replace("casual", "formal")
        elif "friendly and approachable" in template:
            return f"{prompt}\n\nAlways maintain a friendly and approachable tone in your interactions."
        elif "direct and concise" in template:
            return f"Be direct and concise in all responses.\n\n{prompt}"
        elif "encouraging and supportive" in template:
            return f"{prompt}\n\nProvide encouraging feedback and support to team members."
        return prompt
    
    async def _modify_structure(self, prompt: str, template: str, agent_type: AgentType) -> str:
        """Modify the structure of the prompt."""
        if "numbered steps" in template:
            return f"Follow these numbered steps:\n1. {prompt.replace('. ', '.\n2. ')}"
        elif "bullet points" in template:
            return f"Key responsibilities:\n• {prompt.replace('. ', '.\n• ')}"
        return prompt
    
    async def _change_detail_level(self, prompt: str, template: str, agent_type: AgentType) -> str:
        """Change the detail level of the prompt."""
        if "more detailed" in template:
            return f"{prompt}\n\nProvide detailed explanations and comprehensive analysis in all responses."
        elif "more concise" in template:
            return f"Be concise and focus on key points.\n\n{prompt}"
        return prompt
    
    async def _clarify_instructions(self, prompt: str, template: str, agent_type: AgentType) -> str:
        """Clarify instructions in the prompt."""
        if "more explicit" in template:
            return f"{prompt}\n\nBe explicit about requirements and provide specific, actionable guidance."
        return prompt
    
    async def _enhance_context(self, prompt: str, template: str, agent_type: AgentType) -> str:
        """Enhance context in the prompt."""
        if "project and goals" in template:
            return f"Consider the overall project context and goals when completing tasks.\n\n{prompt}"
        return prompt
    
    async def _focus_specialization(self, prompt: str, template: str, agent_type: AgentType) -> str:
        """Focus on specialization in the prompt."""
        specializations = {
            AgentType.DEVELOPER: "coding best practices and software engineering",
            AgentType.CODE_REVIEWER: "code quality and security standards",
            AgentType.ARCHITECT: "system design and architectural patterns",
            AgentType.PROJECT_MANAGER: "project management and team coordination",
            AgentType.QA_AGENT: "testing methodologies and quality assurance",
            AgentType.DOCUMENTATION_AGENT: "technical writing and documentation standards"
        }
        
        focus_area = specializations.get(agent_type, "general expertise")
        return f"Focus on {focus_area} in your responses.\n\n{prompt}"


class PromptABTestingFramework:
    """Framework for A/B testing prompt variations."""
    
    def __init__(self, performance_analyzer: AgentPerformanceAnalyzer):
        """Initialize the A/B testing framework."""
        self.performance_analyzer = performance_analyzer
        self.active_tests: Dict[str, List[PromptVariation]] = {}
        self.test_assignments: Dict[str, str] = {}  # task_id -> variation_id
    
    async def start_ab_test(
        self,
        agent_id: str,
        variations: List[PromptVariation],
        test_duration: timedelta = timedelta(days=7)
    ) -> str:
        """Start an A/B test for prompt variations."""
        test_id = str(uuid.uuid4())
        
        for variation in variations:
            variation.test_status = PromptTestStatus.RUNNING
        
        self.active_tests[test_id] = variations
        
        logger.info(f"Started A/B test {test_id} for agent {agent_id} with {len(variations)} variations")
        
        # Schedule test completion
        asyncio.create_task(self._complete_test_after_duration(test_id, test_duration))
        
        return test_id
    
    async def assign_variation_for_task(self, test_id: str, task_id: str) -> Optional[PromptVariation]:
        """Assign a variation for a specific task."""
        if test_id not in self.active_tests:
            return None
        
        variations = self.active_tests[test_id]
        active_variations = [v for v in variations if v.test_status == PromptTestStatus.RUNNING]
        
        if not active_variations:
            return None
        
        # Simple round-robin assignment
        # In a real system, this would be more sophisticated (e.g., random with equal distribution)
        variation_index = len(self.test_assignments) % len(active_variations)
        selected_variation = active_variations[variation_index]
        
        self.test_assignments[task_id] = selected_variation.variation_id
        selected_variation.test_task_count += 1
        
        return selected_variation
    
    async def record_test_result(
        self,
        task_id: str,
        success: bool,
        response_time: float,
        quality_score: float,
        user_satisfaction: Optional[float] = None
    ) -> None:
        """Record test result for a task."""
        variation_id = self.test_assignments.get(task_id)
        if not variation_id:
            return
        
        # Find the variation and update metrics
        for test_variations in self.active_tests.values():
            for variation in test_variations:
                if variation.variation_id == variation_id:
                    metrics = variation.performance_metrics
                    metrics.total_tasks += 1
                    
                    if success:
                        metrics.successful_tasks += 1
                    else:
                        metrics.failed_tasks += 1
                    
                    metrics.response_times.append(response_time)
                    metrics.quality_scores.append(quality_score)
                    
                    if user_satisfaction is not None:
                        metrics.satisfaction_scores.append(user_satisfaction)
                    
                    # Recalculate derived metrics
                    metrics.success_rate = metrics.successful_tasks / metrics.total_tasks * 100
                    metrics.error_rate = metrics.failed_tasks / metrics.total_tasks * 100
                    metrics.average_response_time = statistics.mean(metrics.response_times)
                    metrics.quality_score = statistics.mean(metrics.quality_scores)
                    
                    if metrics.satisfaction_scores:
                        metrics.user_satisfaction = statistics.mean(metrics.satisfaction_scores)
                    
                    break
    
    async def analyze_test_results(self, test_id: str) -> Optional[PromptOptimizationResult]:
        """Analyze A/B test results and determine the best variation."""
        if test_id not in self.active_tests:
            return None
        
        variations = self.active_tests[test_id]
        
        # Check if we have enough data for statistical significance
        min_samples = 30  # Minimum for basic statistical significance
        valid_variations = [v for v in variations if v.performance_metrics.total_tasks >= min_samples]
        
        if not valid_variations:
            return None
        
        # Find the best performing variation
        best_variation = max(
            valid_variations,
            key=lambda v: (
                v.performance_metrics.success_rate * 0.4 +
                v.performance_metrics.quality_score * 0.3 +
                v.performance_metrics.user_satisfaction * 0.2 +
                (100 - v.performance_metrics.error_rate) * 0.1
            )
        )
        
        # Calculate improvement over original (assuming first variation is baseline)
        baseline = variations[0]
        improvement = 0.0
        
        if baseline.performance_metrics.total_tasks >= min_samples:
            baseline_score = (
                baseline.performance_metrics.success_rate * 0.4 +
                baseline.performance_metrics.quality_score * 0.3 +
                baseline.performance_metrics.user_satisfaction * 0.2 +
                (100 - baseline.performance_metrics.error_rate) * 0.1
            )
            
            best_score = (
                best_variation.performance_metrics.success_rate * 0.4 +
                best_variation.performance_metrics.quality_score * 0.3 +
                best_variation.performance_metrics.user_satisfaction * 0.2 +
                (100 - best_variation.performance_metrics.error_rate) * 0.1
            )
            
            improvement = ((best_score - baseline_score) / baseline_score) * 100
        
        # Calculate confidence level (simplified)
        confidence = min(95.0, (best_variation.performance_metrics.total_tasks / 100) * 95)
        
        return PromptOptimizationResult(
            agent_type=AgentType.DEVELOPER,  # This should be passed as parameter
            original_performance=baseline.performance_metrics,
            best_variation=best_variation,
            improvement_percentage=improvement,
            confidence_level=confidence,
            recommendation=f"Implement {best_variation.variation_type.value} variation",
            analysis_summary=f"Best variation shows {improvement:.1f}% improvement with {confidence:.1f}% confidence"
        )
    
    async def _complete_test_after_duration(self, test_id: str, duration: timedelta) -> None:
        """Complete test after specified duration."""
        await asyncio.sleep(duration.total_seconds())
        
        if test_id in self.active_tests:
            for variation in self.active_tests[test_id]:
                if variation.test_status == PromptTestStatus.RUNNING:
                    variation.test_status = PromptTestStatus.COMPLETED
            
            logger.info(f"A/B test {test_id} completed after {duration}")


class PromptOptimizationAgent:
    """Main agent responsible for prompt optimization orchestration."""
    
    def __init__(self, agent_registry=None):
        """Initialize the prompt optimization agent."""
        self.agent_registry = agent_registry
        self.performance_analyzer = AgentPerformanceAnalyzer()
        self.variation_generator = PromptVariationGenerator()
        self.ab_testing_framework = PromptABTestingFramework(self.performance_analyzer)
        
        self.optimization_history: List[PromptOptimizationResult] = []
        self.active_optimizations: Dict[str, str] = {}  # agent_id -> test_id
    
    async def start_optimization_cycle(self, agent_id: str) -> str:
        """Start an optimization cycle for an agent."""
        if agent_id in self.active_optimizations:
            logger.warning(f"Optimization already running for agent {agent_id}")
            return self.active_optimizations[agent_id]
        
        # Get current agent configuration
        if not self.agent_registry:
            logger.error("Agent registry not available")
            return ""
        
        agent_config = self.agent_registry.get_agent(agent_id)
        if not agent_config:
            logger.error(f"Agent {agent_id} not found in registry")
            return ""
        
        # Generate prompt variations
        variations = await self.variation_generator.generate_variations(
            agent_config.system_prompt,
            agent_config.agent_type,
            variation_count=5
        )
        
        # Start A/B test
        test_id = await self.ab_testing_framework.start_ab_test(
            agent_id,
            variations,
            test_duration=timedelta(days=3)  # Shorter for testing
        )
        
        self.active_optimizations[agent_id] = test_id
        
        logger.info(f"Started optimization cycle for agent {agent_id} with test {test_id}")
        return test_id
    
    async def get_optimized_prompt_for_task(self, agent_id: str, task_id: str) -> Optional[str]:
        """Get optimized prompt for a specific task if optimization is running."""
        test_id = self.active_optimizations.get(agent_id)
        if not test_id:
            return None
        
        variation = await self.ab_testing_framework.assign_variation_for_task(test_id, task_id)
        if variation:
            return variation.modified_prompt
        
        return None
    
    async def record_task_performance(
        self,
        agent_id: str,
        task_id: str,
        success: bool,
        response_time: float,
        quality_score: float,
        user_satisfaction: Optional[float] = None
    ) -> None:
        """Record task performance for optimization analysis."""
        # Record for general performance tracking
        await self.performance_analyzer.record_task_performance(
            agent_id, task_id, success, response_time, quality_score, user_satisfaction
        )
        
        # Record for active A/B tests
        test_id = self.active_optimizations.get(agent_id)
        if test_id:
            await self.ab_testing_framework.record_test_result(
                task_id, success, response_time, quality_score, user_satisfaction
            )
    
    async def check_optimization_results(self, agent_id: str) -> Optional[PromptOptimizationResult]:
        """Check if optimization is complete and get results."""
        test_id = self.active_optimizations.get(agent_id)
        if not test_id:
            return None
        
        result = await self.ab_testing_framework.analyze_test_results(test_id)
        if result and result.best_variation:
            # Check if we have enough confidence to make a recommendation
            if (result.confidence_level >= 80.0 and 
                result.improvement_percentage > 5.0):
                
                self.optimization_history.append(result)
                del self.active_optimizations[agent_id]
                
                logger.info(f"Optimization complete for agent {agent_id}: {result.improvement_percentage:.1f}% improvement")
                return result
        
        return None
    
    async def apply_optimized_prompt(self, agent_id: str, optimized_prompt: str) -> bool:
        """Apply an optimized prompt to an agent."""
        if not self.agent_registry:
            return False
        
        agent_config = self.agent_registry.get_agent(agent_id)
        if not agent_config:
            return False
        
        # Update the agent's system prompt
        agent_config.system_prompt = optimized_prompt
        self.agent_registry.update_agent(agent_id, agent_config)
        
        logger.info(f"Applied optimized prompt to agent {agent_id}")
        return True
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            "active_optimizations": len(self.active_optimizations),
            "optimization_history": len(self.optimization_history),
            "agents_under_optimization": list(self.active_optimizations.keys()),
            "recent_improvements": [
                {
                    "agent_type": result.agent_type,
                    "improvement": result.improvement_percentage,
                    "confidence": result.confidence_level
                }
                for result in self.optimization_history[-5:]  # Last 5 results
            ]
        }