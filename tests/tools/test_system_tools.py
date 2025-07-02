"""
Tests for system tools.
"""

import asyncio
import platform
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythonium.tools.base import ToolContext
from pythonium.tools.std.execution import ExecuteCommandTool
from pythonium.tools.system.command_execution import (
    CommandHistoryTool,
    ShellEnvironmentTool,
    WhichCommandTool,
)
from pythonium.tools.system.service_monitoring import (
    PortMonitorTool,
    ServiceStatusTool,
    SystemLoadTool,
)
from pythonium.tools.system.system_info import SystemInfoTool


class TestExecuteCommandTool:
    """Test command execution tool functionality."""

    @pytest.mark.asyncio
    async def test_command_execution_initialization(self):
        """Test command execution tool initialization."""
        tool = ExecuteCommandTool()
        assert tool.metadata.name == "execute_command"
        await tool.initialize()
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_simple_command_execution(self):
        """Test executing a simple command."""
        tool = ExecuteCommandTool()
        context = ToolContext()

        await tool.initialize()
        try:
            # Use a cross-platform command
            command = "echo hello" if platform.system() != "Windows" else "echo hello"

            with patch("asyncio.create_subprocess_shell") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"hello\n", b"")
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {"command": command, "timeout": 10}, context
                )

                assert result.success is True
                assert "hello" in str(result.data)
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_command_with_working_directory(self):
        """Test command execution with working directory."""
        tool = ExecuteCommandTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("asyncio.create_subprocess_shell") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"/tmp\n", b"")
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {"command": "pwd", "working_directory": "/tmp", "timeout": 10},
                    context,
                )

                assert result.success is True
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_command_timeout(self):
        """Test command timeout handling."""
        tool = ExecuteCommandTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("asyncio.create_subprocess_shell") as mock_subprocess:
                mock_subprocess.side_effect = asyncio.TimeoutError()

                result = await tool.execute(
                    {"command": "sleep 100", "timeout": 1}, context
                )

                assert result.success is False
                assert "timed out" in str(result.error).lower()
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_command_error_handling(self):
        """Test command error handling."""
        tool = ExecuteCommandTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("asyncio.create_subprocess_shell") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 1
                mock_process.communicate.return_value = (b"", b"Command not found\n")
                mock_subprocess.return_value = mock_process

                result = await tool.execute(
                    {"command": "nonexistent_command", "timeout": 10}, context
                )

                assert result.success is False
        finally:
            await tool.shutdown()


class TestServiceStatusTool:
    """Test service status tool functionality."""

    @pytest.mark.asyncio
    async def test_service_status_initialization(self):
        """Test service status tool initialization."""
        tool = ServiceStatusTool()
        assert tool.metadata.name == "service_status"
        await tool.initialize()
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_linux_service_check(self):
        """Test checking Linux service status."""
        tool = ServiceStatusTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("subprocess.run") as mock_subprocess:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "SERVICE_NAME: ssh\nSTATUS: active (running)"
                mock_subprocess.return_value = mock_result

                result = await tool.execute(
                    {"services": ["ssh"], "platform": "linux"}, context
                )

                assert result.success is True
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_service_not_found(self):
        """Test handling of non-existent service."""
        tool = ServiceStatusTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("subprocess.run") as mock_subprocess:
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stdout = "Service not found"
                mock_subprocess.return_value = mock_result

                result = await tool.execute(
                    {"services": ["nonexistent_service"], "platform": "linux"}, context
                )

                # Should still succeed but report service as not found
                assert result.success is True
        finally:
            await tool.shutdown()


class TestPortMonitorTool:
    """Test port monitoring tool functionality."""

    @pytest.mark.asyncio
    async def test_port_monitor_initialization(self):
        """Test port monitor tool initialization."""
        tool = PortMonitorTool()
        assert tool.metadata.name == "port_monitor"
        await tool.initialize()
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_port_check(self):
        """Test checking port availability."""
        tool = PortMonitorTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 0  # Port is open
                mock_socket.return_value.__enter__.return_value = mock_sock

                result = await tool.execute(
                    {"host": "localhost", "ports": [80, 443], "timeout": 5}, context
                )

                assert result.success is True
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_port_closed(self):
        """Test checking closed port."""
        tool = PortMonitorTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 1  # Port is closed
                mock_socket.return_value.__enter__.return_value = mock_sock

                result = await tool.execute(
                    {"host": "localhost", "ports": [9999], "timeout": 5}, context
                )

                assert result.success is True
        finally:
            await tool.shutdown()


class TestSystemLoadTool:
    """Test system load monitoring tool functionality."""

    @pytest.mark.asyncio
    async def test_system_load_initialization(self):
        """Test system load tool initialization."""
        tool = SystemLoadTool()
        assert tool.metadata.name == "system_load"
        await tool.initialize()
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_system_load_check(self):
        """Test checking system load."""
        tool = SystemLoadTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("psutil.cpu_percent") as mock_cpu, patch(
                "psutil.virtual_memory"
            ) as mock_memory, patch("psutil.disk_usage") as mock_disk:

                mock_cpu.return_value = 25.5
                mock_memory.return_value = MagicMock(percent=60.0)
                mock_disk.return_value = MagicMock(percent=45.0)

                result = await tool.execute(
                    {"interval": 1, "include_processes": False}, context
                )

                assert result.success is True
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_system_load_with_processes(self):
        """Test system load check including processes."""
        tool = SystemLoadTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("psutil.cpu_percent") as mock_cpu, patch(
                "psutil.virtual_memory"
            ) as mock_memory, patch("psutil.disk_usage") as mock_disk, patch(
                "psutil.process_iter"
            ) as mock_processes:

                mock_cpu.return_value = 25.5
                mock_memory.return_value = MagicMock(percent=60.0)
                mock_disk.return_value = MagicMock(percent=45.0)

                mock_process = MagicMock()
                mock_process.info = {
                    "name": "python",
                    "cpu_percent": 10.0,
                    "memory_percent": 5.0,
                }
                mock_processes.return_value = [mock_process]

                result = await tool.execute(
                    {"interval": 1, "include_processes": True}, context
                )

                assert result.success is True
        finally:
            await tool.shutdown()


class TestSystemInfoTool:
    """Test system info tool functionality."""

    @pytest.mark.asyncio
    async def test_system_info_initialization(self):
        """Test system info tool initialization."""
        tool = SystemInfoTool()
        assert tool.metadata.name == "system_info"
        await tool.initialize()
        await tool.shutdown()

    @pytest.mark.asyncio
    async def test_basic_system_info(self):
        """Test getting basic system information."""
        tool = SystemInfoTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("platform.system") as mock_system, patch(
                "platform.release"
            ) as mock_release, patch("platform.machine") as mock_machine:

                mock_system.return_value = "Linux"
                mock_release.return_value = "5.4.0"
                mock_machine.return_value = "x86_64"

                result = await tool.execute(
                    {"include_hardware": False, "include_network": False}, context
                )

                assert result.success is True
                assert "Linux" in str(result.data)
        finally:
            await tool.shutdown()

    @pytest.mark.asyncio
    async def test_system_info_with_hardware(self):
        """Test getting system info including hardware details."""
        tool = SystemInfoTool()
        context = ToolContext()

        await tool.initialize()
        try:
            with patch("platform.system") as mock_system, patch(
                "psutil.cpu_count"
            ) as mock_cpu_count, patch("psutil.virtual_memory") as mock_memory:

                mock_system.return_value = "Linux"
                mock_cpu_count.return_value = 4
                mock_memory.return_value = MagicMock(
                    total=8 * 1024 * 1024 * 1024
                )  # 8GB

                result = await tool.execute(
                    {"include_hardware": True, "include_network": False}, context
                )

                assert result.success is True
        finally:
            await tool.shutdown()


class TestSystemToolsIntegration:
    """Test system tools integration scenarios."""

    @pytest.mark.asyncio
    async def test_monitoring_workflow(self):
        """Test a complete monitoring workflow."""
        service_tool = ServiceStatusTool()
        port_tool = PortMonitorTool()
        load_tool = SystemLoadTool()

        await service_tool.initialize()
        await port_tool.initialize()
        await load_tool.initialize()

        try:
            context = ToolContext()

            # Mock all the tools
            with patch("subprocess.run") as mock_subprocess, patch(
                "socket.socket"
            ) as mock_socket, patch("psutil.cpu_percent") as mock_cpu:

                # Service check
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "SERVICE_NAME: nginx\nSTATUS: active"
                mock_subprocess.return_value = mock_result

                # Port check
                mock_sock = MagicMock()
                mock_sock.connect_ex.return_value = 0
                mock_socket.return_value.__enter__.return_value = mock_sock

                # Load check
                mock_cpu.return_value = 15.0

                # Execute monitoring workflow
                service_result = await service_tool.execute(
                    {"services": ["nginx"], "platform": "linux"}, context
                )

                port_result = await port_tool.execute(
                    {"host": "localhost", "ports": [80], "timeout": 5}, context
                )

                load_result = await load_tool.execute(
                    {"interval": 1, "include_processes": False}, context
                )

                # All checks should succeed
                assert service_result.success is True
                assert port_result.success is True
                assert load_result.success is True

        finally:
            await service_tool.shutdown()
            await port_tool.shutdown()
            await load_tool.shutdown()

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery in system tools."""
        tools = [ServiceStatusTool(), PortMonitorTool(), SystemLoadTool()]

        for tool in tools:
            await tool.initialize()

        try:
            context = ToolContext()

            # All tools should handle errors gracefully
            for tool in tools:
                result = await tool.execute(
                    {
                        "services": ["test"],
                        "host": "localhost",
                        "ports": [80],
                        "interval": 1,
                    },
                    context,
                )

                # Should not crash, even with invalid parameters
                assert isinstance(result.success, bool)

        finally:
            for tool in tools:
                await tool.shutdown()
