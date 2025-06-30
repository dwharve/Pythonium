"""Process management tools for system operations."""

import asyncio
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import psutil

from pythonium.common.base import Result
from pythonium.common.parameter_validation import (
    ProcessManagerParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


class ProcessManagerTool(BaseTool):
    """Tool for managing system processes."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="process_manager",
            description="Comprehensive process management tool for system operations including listing, monitoring, and controlling processes.",
            brief_description="Manage system processes - start, stop, and monitor",
            detailed_description="Comprehensive process management tool for system operations. Takes 'operation' (required string) specifying the action to perform (list, info, kill, suspend, resume, children), optional 'pid' (integer) for process ID operations, 'process_name' (string) for name-based operations, 'signal_type' (string) for kill signals (TERM, KILL, INT, QUIT), and 'include_children' (boolean) for child process handling. Essential for system administration, process monitoring, and application lifecycle management.",
            category="system",
            tags=["process", "management", "system", "monitoring", "control"],
            parameters=[
                ToolParameter(
                    name="operation",
                    type=ParameterType.STRING,
                    required=True,
                    description="Operation to perform (list, info, kill, suspend, resume, children)",
                ),
                ToolParameter(
                    name="pid",
                    type=ParameterType.INTEGER,
                    required=False,
                    description="Process ID for operations",
                ),
                ToolParameter(
                    name="process_name",
                    type=ParameterType.STRING,
                    required=False,
                    description="Process name for operations",
                ),
                ToolParameter(
                    name="signal_type",
                    type=ParameterType.STRING,
                    required=False,
                    description="Signal type for kill operation (TERM, KILL, INT, QUIT)",
                ),
                ToolParameter(
                    name="include_children",
                    type=ParameterType.BOOLEAN,
                    required=False,
                    description="Include child processes",
                ),
            ],
        )

    @validate_parameters(ProcessManagerParams)
    async def execute(
        self, params: ProcessManagerParams, context: ToolContext
    ) -> Result[Any]:
        """Execute process management operation."""
        try:
            # Run process operations in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    self._execute_process_operation,
                    params.operation,
                    params.pid,
                    params.process_name,
                    params.signal_type,
                    params.include_children,
                )

            return result

        except Exception as e:
            return Result[Any].error_result(
                error=f"Process management failed: {str(e)}"
            )

    def _execute_process_operation(
        self,
        operation: str,
        pid: Optional[int],
        process_name: Optional[str],
        signal_type: str,
        include_children: bool,
    ) -> Result[Any]:
        """Execute process operation synchronously."""
        try:
            if operation == "list":
                return self._list_processes(process_name)
            elif operation == "info":
                return self._get_process_info(pid, process_name)
            elif operation == "kill":
                return self._kill_process(
                    pid, process_name, signal_type, include_children
                )
            elif operation == "suspend":
                return self._suspend_process(pid, process_name)
            elif operation == "resume":
                return self._resume_process(pid, process_name)
            elif operation == "children":
                return self._get_process_children(pid, process_name)
            else:
                return Result[Any].error_result(
                    error=f"Unsupported operation: {operation}"
                )

        except Exception as e:
            return Result[Any].error_result(error=f"Process operation failed: {str(e)}")

    def _list_processes(self, process_name: Optional[str]) -> Result[Any]:
        """List system processes."""
        try:
            processes = []

            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "status"]
            ):
                try:
                    proc_info = proc.info
                    if (
                        process_name
                        and process_name.lower() not in proc_info["name"].lower()
                    ):
                        continue

                    processes.append(
                        {
                            "pid": proc_info["pid"],
                            "name": proc_info["name"],
                            "cpu_percent": proc_info["cpu_percent"],
                            "memory_percent": proc_info["memory_percent"],
                            "status": proc_info["status"],
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return Result[Any].success_result(
                data={
                    "processes": processes,
                    "count": len(processes),
                    "filter": process_name,
                },
            )

        except Exception as e:
            return Result[Any].error_result(error=f"Failed to list processes: {str(e)}")

    def _get_process_info(
        self, pid: Optional[int], process_name: Optional[str]
    ) -> Result[Any]:
        """Get detailed information about a process."""
        try:
            proc = self._find_process(pid, process_name)
            if not proc:
                return Result[Any].error_result(error="Process not found")

            with proc.oneshot():
                info = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "exe": proc.exe() if proc.exe() else None,
                    "cmdline": proc.cmdline(),
                    "status": proc.status(),
                    "create_time": proc.create_time(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "memory_info": proc.memory_info()._asdict(),
                    "num_threads": proc.num_threads(),
                    "username": (
                        proc.username() if hasattr(proc, "username") else None
                    ),
                    "cwd": proc.cwd() if proc.cwd() else None,
                    "nice": proc.nice() if hasattr(proc, "nice") else None,
                }

            return Result[Any].success_result(data={"process_info": info})

        except Exception as e:
            return Result[Any].error_result(
                error=f"Failed to get process info: {str(e)}"
            )

    def _kill_process(
        self,
        pid: Optional[int],
        process_name: Optional[str],
        signal_type: str,
        include_children: bool,
    ) -> Result[Any]:
        """Kill a process."""
        try:
            proc = self._find_process(pid, process_name)
            if not proc:
                return Result[Any].error_result(error="Process not found")

            killed_pids = []

            # Kill children first if requested
            if include_children:
                try:
                    children = proc.children(recursive=True)
                    for child in children:
                        try:
                            self._send_signal(child, signal_type)
                            killed_pids.append(child.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Kill the main process
            self._send_signal(proc, signal_type)
            killed_pids.append(proc.pid)

            return Result[Any].success_result(
                data={
                    "message": f"Process killed with signal {signal_type}",
                    "killed_pids": killed_pids,
                    "signal": signal_type,
                },
            )

        except Exception as e:
            return Result[Any].error_result(error=f"Failed to kill process: {str(e)}")

    def _suspend_process(
        self, pid: Optional[int], process_name: Optional[str]
    ) -> Result[Any]:
        """Suspend a process."""
        try:
            proc = self._find_process(pid, process_name)
            if not proc:
                return Result[Any].error_result(error="Process not found")

            proc.suspend()

            return Result[Any].success_result(
                data={
                    "message": "Process suspended successfully",
                    "pid": proc.pid,
                    "name": proc.name(),
                },
            )

        except Exception as e:
            return Result[Any].error_result(
                error=f"Failed to suspend process: {str(e)}"
            )

    def _resume_process(
        self, pid: Optional[int], process_name: Optional[str]
    ) -> Result[Any]:
        """Resume a suspended process."""
        try:
            proc = self._find_process(pid, process_name)
            if not proc:
                return Result[Any].error_result(error="Process not found")

            proc.resume()

            return Result[Any].success_result(
                data={
                    "message": "Process resumed successfully",
                    "pid": proc.pid,
                    "name": proc.name(),
                },
            )

        except Exception as e:
            return Result[Any].error_result(error=f"Failed to resume process: {str(e)}")

    def _get_process_children(
        self, pid: Optional[int], process_name: Optional[str]
    ) -> Result[Any]:
        """Get child processes."""
        try:
            proc = self._find_process(pid, process_name)
            if not proc:
                return Result[Any].error_result(error="Process not found")

            children = []
            for child in proc.children(recursive=True):
                try:
                    children.append(
                        {
                            "pid": child.pid,
                            "name": child.name(),
                            "status": child.status(),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return Result[Any].success_result(
                data={
                    "parent_pid": proc.pid,
                    "parent_name": proc.name(),
                    "children": children,
                    "count": len(children),
                },
            )

        except Exception as e:
            return Result[Any].error_result(
                error=f"Failed to get process children: {str(e)}",
            )

    def _find_process(
        self, pid: Optional[int], process_name: Optional[str]
    ) -> Optional[psutil.Process]:
        """Find a process by PID or name."""
        if pid:
            try:
                return psutil.Process(pid)
            except psutil.NoSuchProcess:
                return None
        elif process_name:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if process_name.lower() in proc.info["name"].lower():
                        return psutil.Process(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None

    def _send_signal(self, proc: psutil.Process, signal_type: str):
        """Send signal to process."""
        if os.name == "nt":  # Windows
            if signal_type in ["TERM", "KILL"]:
                proc.terminate()
            elif signal_type == "KILL":
                proc.kill()
        else:  # Unix-like
            signal_map = {
                "TERM": signal.SIGTERM,
                "KILL": signal.SIGKILL,
                "INT": signal.SIGINT,
                "QUIT": signal.SIGQUIT,
            }
            proc.send_signal(signal_map.get(signal_type, signal.SIGTERM))
