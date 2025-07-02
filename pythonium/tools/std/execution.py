"""
Command execution tools for the Pythonium framework.

Provides tools for executing system commands with proper security
considerations, output capture, and error handling.
"""

import os
import shlex
import subprocess
from datetime import datetime
from typing import Callable, Dict, List, Optional, Union

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.parameter_validation import validate_parameters
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)

from .parameters import ExecuteCommandParams


class ExecuteCommandTool(BaseTool):
    """Tool for executing system commands."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="execute_command",
            description="Execute a system command and return output with security considerations and error handling. Supports command arguments, working directory, timeout, shell execution, and environment variables.",
            brief_description="Execute a system command and return output",
            detailed_description="Execute a system command and return output with security considerations and error handling. Takes 'command' (required) as the command to run, 'args' (optional array) for command arguments, 'working_directory' for execution context, 'timeout' (default 30 seconds), 'capture_output' (boolean, default True), 'shell' (boolean for shell execution), 'environment' (object for env vars), and 'stdin' (optional string) for input to send to command's stdin. Powerful but dangerous - use with caution as it can execute any system command.",
            category="system",
            tags=[
                "command",
                "execute",
                "system",
                "shell",
                "process",
                "dangerous",
            ],
            dangerous=True,  # Command execution is dangerous
            parameters=[
                ToolParameter(
                    name="command",
                    type=ParameterType.STRING,
                    description="Command to execute",
                    required=True,
                ),
                ToolParameter(
                    name="args",
                    type=ParameterType.ARRAY,
                    description="Command arguments (alternative to including in command string)",
                    default=[],
                ),
                ToolParameter(
                    name="working_directory",
                    type=ParameterType.STRING,
                    description="Working directory for command execution",
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Timeout in seconds",
                    default=30,
                ),
                ToolParameter(
                    name="capture_output",
                    type=ParameterType.BOOLEAN,
                    description="Capture stdout and stderr",
                    default=True,
                ),
                ToolParameter(
                    name="shell",
                    type=ParameterType.BOOLEAN,
                    description="Execute command through shell",
                    default=False,
                ),
                ToolParameter(
                    name="environment",
                    type=ParameterType.OBJECT,
                    description="Environment variables to set",
                    default={},
                ),
                ToolParameter(
                    name="stdin",
                    type=ParameterType.STRING,
                    description="Input to send to command's stdin",
                ),
            ],
        )

    @validate_parameters(ExecuteCommandParams)
    @handle_tool_error
    async def execute(
        self, parameters: ExecuteCommandParams, context: ToolContext
    ) -> Result:
        """Execute the command execution operation."""
        try:
            progress_callback = getattr(context, "progress_callback", None)

            if progress_callback:
                progress_callback(f"Starting command execution: {parameters.command}")

            # Prepare command and environment
            cmd = self._prepare_command(parameters)
            env = self._prepare_environment(parameters.environment)

            # Execute command and get result
            start_time = datetime.now()
            result = self._execute_subprocess(cmd, parameters, env, progress_callback)

            # Process result
            return self._process_result(
                result, parameters, progress_callback, start_time
            )

        except subprocess.TimeoutExpired:
            if progress_callback:
                progress_callback(
                    f"Command timed out after {parameters.timeout} seconds"
                )
            return Result.error_result(
                f"Command timed out after {parameters.timeout} seconds"
            )
        except FileNotFoundError:
            return Result.error_result(f"Command not found: {parameters.command}")
        except PermissionError as e:
            return Result.error_result(f"Permission denied: {e}")
        except Exception as e:
            return Result.error_result(f"Command execution failed: {e}")

    def _prepare_command(
        self, parameters: ExecuteCommandParams
    ) -> Union[str, List[str]]:
        """Prepare command for execution."""
        command = parameters.command
        args = parameters.args or []

        if args:
            # Use command and args separately
            return [command] + args
        elif parameters.shell:
            # Use shell command as string
            return command
        else:
            # Split command string into components
            return shlex.split(command)

    def _prepare_environment(
        self, environment: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """Prepare environment variables."""
        env = os.environ.copy()
        if environment:
            env.update(environment)
        return env

    def _execute_subprocess(
        self,
        cmd: Union[str, List[str]],
        parameters: ExecuteCommandParams,
        env: Dict[str, str],
        progress_callback: Optional[Callable[[str], None]],
    ) -> subprocess.CompletedProcess:
        """Execute the subprocess with appropriate settings."""
        cwd = parameters.working_directory if parameters.working_directory else None

        if parameters.capture_output:
            if progress_callback:
                progress_callback("Executing command with output capture...")

            return subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                shell=parameters.shell,
                capture_output=True,
                text=True,
                timeout=parameters.timeout,
                input=parameters.stdin,
            )
        else:
            if progress_callback:
                progress_callback("Executing command without output capture...")

            return subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                shell=parameters.shell,
                timeout=parameters.timeout,
                input=parameters.stdin,
                text=True if parameters.stdin else False,
            )

    def _process_result(
        self,
        result: subprocess.CompletedProcess,
        parameters: ExecuteCommandParams,
        progress_callback: Optional[Callable[[str], None]],
        start_time: datetime,
    ) -> Result:
        """Process subprocess result and return appropriate Result."""
        execution_time = (datetime.now() - start_time).total_seconds()

        if parameters.capture_output:
            output_data = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "execution_time": execution_time,
            }
        else:
            output_data = {
                "returncode": result.returncode,
                "execution_time": execution_time,
            }

        if progress_callback:
            progress_callback(
                f"Command completed in {execution_time:.2f} seconds with return code {result.returncode}"
            )

        # Check if command was successful
        if result.returncode != 0:
            error_msg = f"Command failed with return code {result.returncode}"
            if parameters.capture_output and result.stderr:
                error_msg += f": {result.stderr}"
            return Result.error_result(error_msg)

        return Result.success_result(output_data)
