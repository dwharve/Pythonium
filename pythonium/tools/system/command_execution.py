"""
Command execution tools for the Pythonium framework.

Provides tools for executing system commands with proper security
considerations, output capture, and error handling.
"""

import os
import shlex
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Union

from pythonium.common.base import Result
from pythonium.common.error_handling import handle_tool_error
from pythonium.common.parameter_validation import (
    ExecuteCommandParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


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
            command = parameters.command
            args = parameters.args or []
            working_directory = parameters.working_directory
            timeout = parameters.timeout
            capture_output = parameters.capture_output
            use_shell = parameters.shell
            environment = parameters.environment or {}
            stdin_input = parameters.stdin

            # Prepare command
            cmd: Union[str, List[str]]
            if args:
                # Use command and args separately
                cmd = [command] + args
            elif use_shell:
                # Use shell command as string
                cmd = command
            else:
                # Split command string into components
                cmd = shlex.split(command)

            # Prepare environment
            env = os.environ.copy()
            env.update(environment)

            # Prepare working directory
            cwd = working_directory if working_directory else None

            # Execute command
            start_time = datetime.now()

            if capture_output:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    env=env,
                    shell=use_shell,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    input=stdin_input,
                )

                output_data = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "execution_time": (datetime.now() - start_time).total_seconds(),
                }
            else:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    env=env,
                    shell=use_shell,
                    timeout=timeout,
                    input=stdin_input,
                    text=True if stdin_input else False,
                )

                output_data = {
                    "returncode": result.returncode,
                    "execution_time": (datetime.now() - start_time).total_seconds(),
                }

            # Check if command was successful
            if result.returncode != 0:
                error_msg = f"Command failed with return code {result.returncode}"
                if capture_output and result.stderr:
                    error_msg += f": {result.stderr}"

                return Result.error_result(error_msg)

            return Result.success_result(output_data)

        except subprocess.TimeoutExpired:
            return Result.error_result(f"Command timed out after {timeout} seconds")
        except FileNotFoundError:
            return Result.error_result(f"Command not found: {command}")
        except PermissionError as e:
            return Result.error_result(f"Permission denied: {e}")
        except Exception as e:
            return Result.error_result(f"Command execution failed: {e}")


class WhichCommandTool(BaseTool):
    """Tool for finding the location of executable commands."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="which_command",
            description="Find the location of executable commands in the system PATH. Useful for locating binaries and checking if commands are available.",
            brief_description="Find the location of executable commands",
            detailed_description="Find the location of executable commands in the system PATH. Takes 'commands' (required array) as the list of commands to locate, and 'all_paths' (optional boolean, default False) to find all occurrences in PATH rather than just the first. Returns the full paths to executables, helping verify command availability and locate specific binaries.",
            category="system",
            tags=[
                "which",
                "command",
                "executable",
                "path",
                "locate",
                "binary",
            ],
            parameters=[
                ToolParameter(
                    name="commands",
                    type=ParameterType.ARRAY,
                    description="List of commands to locate",
                    required=True,
                ),
                ToolParameter(
                    name="all_paths",
                    type=ParameterType.BOOLEAN,
                    description="Find all occurrences in PATH",
                    default=False,
                ),
            ],
        )

    def _find_all_command_paths(self, command: str) -> List[str]:
        """Find all paths where a command exists."""
        paths = []
        path_env = os.environ.get("PATH", "")

        for directory in path_env.split(os.pathsep):
            if directory:
                potential_path = os.path.join(directory, command)
                if os.name == "nt":
                    paths.extend(self._check_windows_executable(potential_path))
                else:
                    paths.extend(self._check_unix_executable(potential_path))

        return paths

    def _check_windows_executable(self, potential_path: str) -> List[str]:
        """Check if a path is executable on Windows."""
        paths = []
        # Windows: try with common executable extensions
        for ext in [".exe", ".bat", ".cmd", ".com"]:
            full_path = potential_path + ext
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                paths.append(full_path)
        # Also try without extension
        if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
            paths.append(potential_path)
        return paths

    def _check_unix_executable(self, potential_path: str) -> List[str]:
        """Check if a path is executable on Unix-like systems."""
        if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
            return [potential_path]
        return []

    @handle_tool_error
    async def execute(self, parameters: Dict[str, Any], context: ToolContext) -> Result:
        """Execute the which command operation."""
        try:
            import shutil

            commands = parameters["commands"]
            all_paths = parameters.get("all_paths", False)

            results = []

            for command in commands:
                try:
                    if all_paths:
                        paths = self._find_all_command_paths(command)
                        results.append(
                            {
                                "command": command,
                                "found": len(paths) > 0,
                                "paths": paths,
                                "primary_path": paths[0] if paths else None,
                            }
                        )
                    else:
                        # Find first occurrence
                        path = shutil.which(command)
                        results.append(
                            {
                                "command": command,
                                "found": path is not None,
                                "path": path,
                            }
                        )

                except Exception as e:
                    results.append(
                        {"command": command, "found": False, "error": str(e)}
                    )

            return Result.success_result({"results": results, "all_paths": all_paths})

        except Exception as e:
            return Result.error_result(f"Failed to locate commands: {str(e)}")


class CommandHistoryTool(BaseTool):
    """Tool for managing command execution history."""

    def __init__(self):
        super().__init__()
        # Simple in-memory history storage
        # In a production system, this might be persistent
        self._history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="command_history",
            description="View and manage command execution history. Tracks commands run through the system for analysis and reference.",
            brief_description="View and manage command execution history",
            detailed_description="View and manage command execution history. Takes 'action' (required string) which can be 'list', 'clear', or 'search'. Optional parameters include 'limit' (integer, default 50) for maximum entries to return, and 'search_term' (string) for filtering history when using search action. Maintains a record of executed commands with timestamps and execution details.",
            category="system",
            tags=["history", "command", "tracking", "log", "management"],
            parameters=[
                ToolParameter(
                    name="action",
                    type=ParameterType.STRING,
                    description="Action to perform (list, clear, search)",
                    required=True,
                ),
                ToolParameter(
                    name="limit",
                    type=ParameterType.INTEGER,
                    description="Maximum number of entries to return",
                    default=50,
                ),
                ToolParameter(
                    name="search_term",
                    type=ParameterType.STRING,
                    description="Search term for filtering history",
                ),
            ],
        )

    def add_to_history(self, command: str, result: Dict[str, Any]):
        """Add a command execution to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "success": result.get("success", False),
            "return_code": result.get("return_code"),
            "execution_time": result.get("execution_time"),
            "working_directory": result.get("working_directory"),
        }
        self._history.append(entry)

        # Keep only last 1000 entries
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    @handle_tool_error
    async def execute(self, parameters: Dict[str, Any], context: ToolContext) -> Result:
        """Execute the command history operation."""
        try:
            action = parameters["action"]
            limit = parameters.get("limit", 50)
            search_term = parameters.get("search_term")

            if action == "list":
                # List command history
                history = self._history[-limit:] if limit else self._history

                return Result.success_result(
                    {
                        "history": history,
                        "total_entries": len(self._history),
                        "returned_entries": len(history),
                    }
                )

            elif action == "clear":
                # Clear command history
                cleared_count = len(self._history)
                self._history.clear()

                return Result.success_result(
                    {
                        "cleared_entries": cleared_count,
                        "message": "Command history cleared",
                    }
                )

            elif action == "search":
                # Search command history
                if not search_term:
                    return Result.error_result(
                        "Search term is required for search action"
                    )

                matching_entries = []
                for entry in self._history:
                    if search_term.lower() in entry["command"].lower():
                        matching_entries.append(entry)

                # Apply limit
                if limit:
                    matching_entries = matching_entries[-limit:]

                return Result.success_result(
                    {
                        "search_term": search_term,
                        "matching_entries": matching_entries,
                        "total_matches": len(matching_entries),
                    }
                )

            else:
                return Result.error_result(f"Unknown action: {action}")

        except Exception as e:
            return Result.error_result(f"Failed to manage command history: {str(e)}")


class ShellEnvironmentTool(BaseTool):
    """Tool for getting shell environment information."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="shell_environment",
            description="Get comprehensive information about the shell environment including variables, PATH, aliases, and platform details.",
            brief_description="Get information about the shell environment",
            detailed_description="Get comprehensive information about the shell environment. Takes 'include_aliases' (optional boolean, default True) to include shell aliases if available, and 'include_functions' (optional boolean, default False) to include shell functions. Returns detailed environment information including shell type, PATH, home directory, current user, platform details, and optionally aliases and functions.",
            category="system",
            tags=[
                "environment",
                "shell",
                "variables",
                "path",
                "aliases",
                "platform",
            ],
            parameters=[
                ToolParameter(
                    name="include_aliases",
                    type=ParameterType.BOOLEAN,
                    description="Include shell aliases (if available)",
                    default=True,
                ),
                ToolParameter(
                    name="include_functions",
                    type=ParameterType.BOOLEAN,
                    description="Include shell functions (if available)",
                    default=False,
                ),
            ],
        )

    @handle_tool_error
    async def execute(self, parameters: Dict[str, Any], context: ToolContext) -> Result:
        """Execute the shell environment operation."""
        try:
            include_aliases = parameters.get("include_aliases", True)
            include_functions = parameters.get("include_functions", False)

            # Get basic shell information
            info = self._get_basic_shell_info()

            # Add platform-specific information
            self._add_platform_specific_info(info, include_aliases, include_functions)

            # Get available commands information
            self._add_available_commands_info(info)

            return Result.success_result(info)

        except Exception as e:
            return Result.error_result(f"Failed to get shell environment: {str(e)}")

    def _get_basic_shell_info(self) -> Dict[str, Any]:
        """Get basic shell environment information."""
        return {
            "shell": os.environ.get("SHELL", "Unknown"),
            "term": os.environ.get("TERM", "Unknown"),
            "path": os.environ.get("PATH", "").split(os.pathsep),
            "home": os.environ.get("HOME") or os.environ.get("USERPROFILE", "Unknown"),
            "user": os.environ.get("USER") or os.environ.get("USERNAME", "Unknown"),
            "pwd": os.getcwd(),
        }

    def _add_platform_specific_info(
        self,
        info: Dict[str, Any],
        include_aliases: bool,
        include_functions: bool,
    ) -> None:
        """Add platform-specific information to the shell info."""
        if os.name == "nt":  # Windows
            info["platform"] = "Windows"
            info["comspec"] = os.environ.get("COMSPEC", "Unknown")
            info["pathext"] = os.environ.get("PATHEXT", "").split(os.pathsep)
        else:  # Unix-like
            info["platform"] = "Unix-like"
            self._add_unix_shell_info(info, include_aliases, include_functions)

    def _add_unix_shell_info(
        self,
        info: Dict[str, Any],
        include_aliases: bool,
        include_functions: bool,
    ) -> None:
        """Add Unix-specific shell information."""
        # Try to get shell-specific information
        try:
            # Get shell type
            result = subprocess.run(
                ["ps", "-p", str(os.getppid()), "-o", "comm="],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                info["parent_process"] = result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Get shell aliases if requested
        if include_aliases:
            self._add_shell_aliases(info)

        # Get shell functions if requested
        if include_functions:
            self._add_shell_functions(info)

    def _add_shell_aliases(self, info: Dict[str, Any]) -> None:
        """Add shell aliases to the info."""
        try:
            result = subprocess.run(
                ["alias"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                aliases = {}
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line and "=" in line:
                        name, value = line.split("=", 1)
                        name = name.replace("alias ", "").strip()
                        value = value.strip("'\"")
                        aliases[name] = value
                info["aliases"] = aliases
        except (subprocess.SubprocessError, FileNotFoundError):
            info["aliases"] = {"error": "Could not retrieve aliases"}

    def _add_shell_functions(self, info: Dict[str, Any]) -> None:
        """Add shell functions to the info."""
        try:
            result = subprocess.run(
                ["declare", "-F"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                functions = []
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line.startswith("declare -f "):
                        function_name = line.replace("declare -f ", "").strip()
                        functions.append(function_name)
                info["functions"] = functions
        except (subprocess.SubprocessError, FileNotFoundError):
            info["functions"] = {"error": "Could not retrieve functions"}

    def _add_available_commands_info(self, info: Dict[str, Any]) -> None:
        """Add information about available commands in PATH."""
        try:
            available_commands = set()
            for directory in info["path"]:
                if directory and os.path.isdir(directory):
                    try:
                        for item in os.listdir(directory):
                            item_path = os.path.join(directory, item)
                            if os.path.isfile(item_path) and os.access(
                                item_path, os.X_OK
                            ):
                                available_commands.add(item)
                    except (PermissionError, OSError):
                        continue

            info["available_commands_count"] = len(available_commands)
            # Include sample of common commands
            common_commands = [
                "ls",
                "cat",
                "grep",
                "find",
                "cp",
                "mv",
                "rm",
                "mkdir",
                "pwd",
                "cd",
            ]
            found_common = [cmd for cmd in common_commands if cmd in available_commands]
            info["common_commands_available"] = found_common

        except Exception as e:
            info["available_commands_error"] = str(e)
