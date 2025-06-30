"""
Tool execution pipeline system.

This module provides functionality to orchestrate tool execution with proper
dependency handling, error management, and result processing.
"""

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, cast

from pythonium.common.exceptions import PythoniumError

from .dependency import DependencyManager

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of tool execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """Execution mode for the pipeline."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"  # Parallel where possible, sequential for dependencies


@dataclass
class ExecutionResult:
    """Result of tool execution."""

    tool_id: str
    status: ExecutionStatus
    result: Any = None
    error: Optional[Exception] = None
    error_traceback: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def failed(self) -> bool:
        """Check if execution failed."""
        return self.status == ExecutionStatus.FAILED


@dataclass
class ExecutionContext:
    """Context for tool execution."""

    tool_id: str
    args: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 0


class ExecutionError(PythoniumError):
    """Raised when execution operations fail."""

    pass


class PipelineError(ExecutionError):
    """Raised when pipeline operations fail."""

    pass


class ExecutionPipeline:
    """
    Orchestrates tool execution with dependency management.

    This pipeline provides:
    - Dependency-aware execution ordering
    - Parallel execution where possible
    - Error handling and recovery
    - Result aggregation and reporting
    - Timeout and cancellation support
    """

    def __init__(
        self,
        dependency_manager: Optional[DependencyManager] = None,
        default_timeout: Optional[float] = None,
        max_concurrent: int = 10,
    ):
        self.dependency_manager = dependency_manager or DependencyManager()
        self.default_timeout = default_timeout
        self.max_concurrent = max_concurrent
        self._tool_registry: Dict[str, Callable] = {}
        self._execution_hooks: Dict[str, List[Callable]] = {
            "before_execution": [],
            "after_execution": [],
            "on_error": [],
            "on_success": [],
        }
        self._active_executions: Dict[str, asyncio.Task] = {}

    def register_tool(self, tool_id: str, tool_func: Callable) -> None:
        """
        Register a tool function for execution.

        Args:
            tool_id: Unique identifier for the tool
            tool_func: Function to execute (can be sync or async)
        """
        self._tool_registry[tool_id] = tool_func
        logger.debug(f"Registered tool: {tool_id}")

    def unregister_tool(self, tool_id: str) -> bool:
        """
        Unregister a tool.

        Args:
            tool_id: Tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_id in self._tool_registry:
            del self._tool_registry[tool_id]
            logger.debug(f"Unregistered tool: {tool_id}")
            return True
        return False

    def add_hook(self, event: str, callback: Callable) -> None:
        """
        Add an execution hook.

        Args:
            event: Event to hook ('before_execution', 'after_execution', 'on_error', 'on_success')
            callback: Callback function
        """
        if event in self._execution_hooks:
            self._execution_hooks[event].append(callback)
            logger.debug(f"Added {event} hook")
        else:
            raise ValueError(f"Invalid hook event: {event}")

    def remove_hook(self, event: str, callback: Callable) -> bool:
        """
        Remove an execution hook.

        Args:
            event: Event to unhook
            callback: Callback function to remove

        Returns:
            True if hook was removed, False if not found
        """
        if event in self._execution_hooks and callback in self._execution_hooks[event]:
            self._execution_hooks[event].remove(callback)
            logger.debug(f"Removed {event} hook")
            return True
        return False

    async def execute_single(
        self,
        tool_id: str,
        args: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a single tool.

        Args:
            tool_id: Tool to execute
            args: Arguments to pass to the tool
            timeout: Execution timeout
            max_retries: Maximum retry attempts
            metadata: Additional metadata

        Returns:
            ExecutionResult containing the result or error
        """
        if tool_id not in self._tool_registry:
            return ExecutionResult(
                tool_id=tool_id,
                status=ExecutionStatus.FAILED,
                error=ExecutionError(f"Tool {tool_id} not registered"),
            )

        context = ExecutionContext(
            tool_id=tool_id,
            args=args or {},
            timeout=timeout or self.default_timeout,
            max_retries=max_retries,
            metadata=metadata or {},
        )

        return await self._execute_tool(context)

    async def _execute_sequential(
        self,
        ordered_tools: List[str],
        context_map: Dict[str, ExecutionContext],
        fail_fast: bool,
    ) -> Dict[str, ExecutionResult]:
        """Execute tools sequentially."""
        results = {}

        for tool_id in ordered_tools:
            if tool_id in context_map:
                result = await self._execute_tool(context_map[tool_id])
                results[tool_id] = result

                if fail_fast and result.failed:
                    # Mark remaining tools as skipped
                    for remaining_id in ordered_tools[
                        ordered_tools.index(tool_id) + 1 :
                    ]:
                        if remaining_id in context_map:
                            results[remaining_id] = ExecutionResult(
                                tool_id=remaining_id,
                                status=ExecutionStatus.SKIPPED,
                                error=PipelineError("Skipped due to earlier failure"),
                            )
                    break

        return results

    async def _execute_parallel(
        self, contexts: List[ExecutionContext], available_tools: set
    ) -> Dict[str, ExecutionResult]:
        """Execute all tools in parallel (ignoring dependencies)."""
        results = {}
        tasks = {}

        for ctx in contexts:
            if ctx.tool_id in available_tools:
                task = asyncio.create_task(self._execute_tool(ctx))
                tasks[ctx.tool_id] = task

        # Wait for all tasks
        if tasks:
            completed_results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            for tool_id, result in zip(tasks.keys(), completed_results):
                if isinstance(result, Exception):
                    results[tool_id] = ExecutionResult(
                        tool_id=tool_id,
                        status=ExecutionStatus.FAILED,
                        error=result,
                    )
                else:
                    results[tool_id] = cast(ExecutionResult, result)

        return results

    async def _execute_mixed(
        self,
        ordered_tools: List[str],
        context_map: Dict[str, ExecutionContext],
    ) -> Dict[str, ExecutionResult]:
        """Execute in dependency order with parallelization where possible."""
        results: Dict[str, ExecutionResult] = {}
        executed = set()
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def execute_when_ready(tool_id: str) -> ExecutionResult:
            # Wait for dependencies
            deps = self.dependency_manager.get_dependencies(tool_id)
            for dep in deps:
                if dep.tool_id in context_map:
                    # Wait for dependency to complete
                    while dep.tool_id not in executed:
                        await asyncio.sleep(0.01)

                    # Check if dependency failed and this is required
                    dep_result = results.get(dep.tool_id)
                    if dep_result and dep_result.failed:
                        return ExecutionResult(
                            tool_id=tool_id,
                            status=ExecutionStatus.FAILED,
                            error=PipelineError(
                                f"Required dependency {dep.tool_id} failed"
                            ),
                        )

            # Execute with concurrency control
            async with semaphore:
                result = await self._execute_tool(context_map[tool_id])
                executed.add(tool_id)
                return result

        # Start all tasks
        tasks = {}
        for tool_id in ordered_tools:
            if tool_id in context_map:
                task = asyncio.create_task(execute_when_ready(tool_id))
                tasks[tool_id] = task

        # Wait for completion
        if tasks:
            completed_results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            for tool_id, result in zip(tasks.keys(), completed_results):
                if isinstance(result, Exception):
                    results[tool_id] = ExecutionResult(
                        tool_id=tool_id,
                        status=ExecutionStatus.FAILED,
                        error=result,
                    )
                else:
                    results[tool_id] = cast(ExecutionResult, result)

        return results

    def _resolve_execution_order(
        self, tool_ids: List[str], available_tools: set, mode: ExecutionMode
    ) -> List[str]:
        """Resolve the execution order based on mode."""
        if mode == ExecutionMode.SEQUENTIAL:
            return tool_ids
        else:
            return self.dependency_manager.resolve_dependencies(
                tool_ids, available_tools, include_optional=True
            )

    def _create_failed_results(
        self, contexts: List[ExecutionContext], error_message: str
    ) -> List[ExecutionResult]:
        """Create failed results for all contexts."""
        return [
            ExecutionResult(
                tool_id=ctx.tool_id,
                status=ExecutionStatus.FAILED,
                error=PipelineError(error_message),
            )
            for ctx in contexts
        ]

    async def execute_batch(
        self,
        contexts: List[ExecutionContext],
        mode: ExecutionMode = ExecutionMode.MIXED,
        fail_fast: bool = False,
    ) -> List[ExecutionResult]:
        """
        Execute multiple tools with dependency management.

        Args:
            contexts: List of execution contexts
            mode: Execution mode
            fail_fast: Stop execution on first failure

        Returns:
            List of execution results
        """
        if not contexts:
            return []

        # Extract tool IDs and resolve dependencies
        tool_ids = [ctx.tool_id for ctx in contexts]
        available_tools = set(self._tool_registry.keys())

        try:
            # Resolve execution order
            ordered_tools = self._resolve_execution_order(
                tool_ids, available_tools, mode
            )
        except Exception as e:
            # Return failed results for all tools
            return self._create_failed_results(
                contexts, f"Dependency resolution failed: {e}"
            )

        # Create context mapping
        context_map = {ctx.tool_id: ctx for ctx in contexts}

        # Execute based on mode
        if mode == ExecutionMode.SEQUENTIAL:
            results = await self._execute_sequential(
                ordered_tools, context_map, fail_fast
            )
        elif mode == ExecutionMode.PARALLEL:
            results = await self._execute_parallel(contexts, available_tools)
        else:  # MIXED mode
            results = await self._execute_mixed(ordered_tools, context_map)

        # Return results in original order
        return [
            results.get(
                ctx.tool_id,
                ExecutionResult(
                    tool_id=ctx.tool_id,
                    status=ExecutionStatus.FAILED,
                    error=ExecutionError("Tool not executed"),
                ),
            )
            for ctx in contexts
        ]

    async def _execute_tool(self, context: ExecutionContext) -> ExecutionResult:
        """Execute a single tool with retry logic."""
        tool_func = self._tool_registry[context.tool_id]

        for attempt in range(context.max_retries + 1):
            result = ExecutionResult(
                tool_id=context.tool_id,
                status=ExecutionStatus.PENDING,
                start_time=datetime.now(),
            )

            try:
                # Run before_execution hooks
                await self._run_hooks("before_execution", context, result)

                result.status = ExecutionStatus.RUNNING

                # Execute the tool
                if asyncio.iscoroutinefunction(tool_func):
                    if context.timeout:
                        task_result = await asyncio.wait_for(
                            tool_func(**context.args), timeout=context.timeout
                        )
                    else:
                        task_result = await tool_func(**context.args)
                else:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    if context.timeout:
                        task_result = await asyncio.wait_for(
                            loop.run_in_executor(
                                None, lambda: tool_func(**context.args)
                            ),
                            timeout=context.timeout,
                        )
                    else:
                        task_result = await loop.run_in_executor(
                            None, lambda: tool_func(**context.args)
                        )

                # Success
                result.status = ExecutionStatus.COMPLETED
                result.result = task_result
                result.end_time = datetime.now()
                if result.start_time is not None:
                    result.duration_ms = (
                        result.end_time - result.start_time
                    ).total_seconds() * 1000

                # Run success hooks
                await self._run_hooks("on_success", context, result)

                logger.debug(
                    f"Tool {context.tool_id} executed successfully in {result.duration_ms:.2f}ms"
                )
                return result

            except asyncio.TimeoutError as e:
                result.status = ExecutionStatus.FAILED
                result.error = e
                result.error_traceback = traceback.format_exc()
                logger.warning(
                    f"Tool {context.tool_id} timed out on attempt {attempt + 1}"
                )

            except Exception as e:
                result.status = ExecutionStatus.FAILED
                result.error = e
                result.error_traceback = traceback.format_exc()
                logger.warning(
                    f"Tool {context.tool_id} failed on attempt {attempt + 1}: {e}"
                )

            finally:
                if result.end_time is None:
                    result.end_time = datetime.now()
                    if result.start_time is not None:
                        result.duration_ms = (
                            result.end_time - result.start_time
                        ).total_seconds() * 1000

                # Run after_execution hooks
                await self._run_hooks("after_execution", context, result)

                if result.failed:
                    # Run error hooks
                    await self._run_hooks("on_error", context, result)

            # Check if we should retry
            if attempt < context.max_retries and result.failed:
                retry_delay = min(2**attempt, 10)  # Exponential backoff, max 10s
                logger.debug(
                    f"Retrying {context.tool_id} in {retry_delay}s (attempt {attempt + 2})"
                )
                await asyncio.sleep(retry_delay)
                continue

            return result

        return result

    async def _run_hooks(
        self, event: str, context: ExecutionContext, result: ExecutionResult
    ) -> None:
        """Run execution hooks."""
        hooks = self._execution_hooks.get(event, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context, result)
                else:
                    hook(context, result)
            except Exception as e:
                logger.error(f"Hook {event} failed: {e}")

    def cancel_execution(self, tool_id: str) -> bool:
        """
        Cancel an active execution.

        Args:
            tool_id: Tool execution to cancel

        Returns:
            True if execution was cancelled, False if not found
        """
        if tool_id in self._active_executions:
            task = self._active_executions[tool_id]
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled execution of {tool_id}")
                return True
        return False

    def get_active_executions(self) -> List[str]:
        """Get list of currently executing tools."""
        active = []
        for tool_id, task in self._active_executions.items():
            if not task.done():
                active.append(tool_id)
        return active

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tools."""
        return list(self._tool_registry.keys())

    async def shutdown(self) -> None:
        """Shutdown the pipeline and cancel all active executions."""
        logger.info("Shutting down execution pipeline")

        # Cancel all active tasks
        for tool_id, task in self._active_executions.items():
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled {tool_id} during shutdown")

        # Wait for tasks to complete cancellation
        if self._active_executions:
            await asyncio.gather(
                *self._active_executions.values(), return_exceptions=True
            )

        self._active_executions.clear()
        logger.info("Pipeline shutdown complete")
