"""
System information gathering tools for the Pythonium framework.

Provides tools for collecting system information including hardware,
operating system, and runtime environment details.
"""

import getpass
import os
import platform
import socket
import sys
from datetime import datetime
from typing import Any, Dict, List

from pythonium.common.base import Result
from pythonium.common.parameter_validation import (
    SystemInfoToolParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


class SystemInfoTool(BaseTool):
    """Tool for getting comprehensive system information."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="system_info",
            description="Get comprehensive system information including hardware, operating system, network, and Python runtime details. Essential for troubleshooting, environment setup, and system diagnostics.",
            brief_description="Get comprehensive system information",
            detailed_description="Get comprehensive system information including hardware, operating system, network, and Python runtime details. Takes 'include_hardware' (boolean, default True) to include CPU and memory info, 'include_network' (boolean, default True) for network and hostname details, and 'include_python' (boolean, default True) for Python runtime information. Essential for troubleshooting, environment setup, and system diagnostics.",
            category="system",
            tags=[
                "system",
                "info",
                "hardware",
                "os",
                "network",
                "python",
                "diagnostics",
            ],
            parameters=[
                ToolParameter(
                    name="include_hardware",
                    type=ParameterType.BOOLEAN,
                    description="Include hardware information (CPU, memory, etc.)",
                    default=True,
                ),
                ToolParameter(
                    name="include_network",
                    type=ParameterType.BOOLEAN,
                    description="Include network information (hostname, IP, etc.)",
                    default=True,
                ),
                ToolParameter(
                    name="include_python",
                    type=ParameterType.BOOLEAN,
                    description="Include Python runtime information",
                    default=True,
                ),
            ],
        )

    @validate_parameters(SystemInfoToolParams)
    def _get_basic_info(self) -> Dict[str, Any]:
        """Get basic system and user information."""
        return {
            "timestamp": datetime.now().isoformat(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
            },
            "user": {
                "username": getpass.getuser(),
                "home_directory": os.path.expanduser("~"),
                "current_directory": os.getcwd(),
            },
        }

    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information using psutil."""
        try:
            import psutil

            # CPU information
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_freq": (
                    psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                ),
            }

            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
            }

            # Disk information
            disk = psutil.disk_usage("/")
            disk_info = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            }

            return {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
            }

        except ImportError:
            return {"error": "psutil not available for detailed hardware info"}

    def _get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            network_info: Dict[str, Any] = {
                "hostname": hostname,
                "local_ip": local_ip,
                "fqdn": socket.getfqdn(),
            }

            # Try to get additional network interfaces
            try:
                import psutil

                interfaces = {}
                for interface, addrs in psutil.net_if_addrs().items():
                    interface_info = []
                    for addr in addrs:
                        interface_info.append(
                            {
                                "family": str(addr.family),
                                "address": addr.address,
                                "netmask": addr.netmask,
                                "broadcast": addr.broadcast,
                            }
                        )
                    interfaces[interface] = interface_info
                network_info["interfaces"] = interfaces
            except ImportError:
                pass

            return network_info

        except Exception as e:
            return {"error": f"Failed to get network info: {str(e)}"}

    def _get_python_info(self) -> Dict[str, Any]:
        """Get Python runtime information."""
        return {
            "version": sys.version,
            "version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
                "releaselevel": sys.version_info.releaselevel,
                "serial": sys.version_info.serial,
            },
            "executable": sys.executable,
            "path": sys.path[:5],  # First 5 entries
            "platform": sys.platform,
            "prefix": sys.prefix,
            "exec_prefix": sys.exec_prefix,
        }

    async def execute(
        self, params: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute the system info operation."""
        try:
            info = self._get_basic_info()

            # Add hardware information
            if params.get("include_hardware", False):
                info["hardware"] = self._get_hardware_info()

            # Add network information
            if params.get("include_network", False):
                info["network"] = self._get_network_info()

            # Add Python runtime information
            if params.get("include_python", False):
                info["python"] = self._get_python_info()

            return Result[Any].success_result(data=info)

        except Exception as e:
            return Result[Any].error_result(
                error=f"Failed to get system info: {str(e)}"
            )


class DiskUsageTool(BaseTool):
    """Tool for getting disk usage information."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="disk_usage",
            description="Get disk usage information for specified paths with human-readable formatting and detailed statistics for system monitoring and diagnostics.",
            brief_description="Get disk usage information for specified paths",
            detailed_description="Get disk usage information for specified paths. Takes optional 'paths' (array, default ['.']) for list of paths to check, and 'human_readable' (boolean, default true) to format sizes in human readable format. Returns total, used, free space, and percentage usage for each path. Essential for disk space monitoring and system diagnostics.",
            category="system",
            tags=[
                "disk",
                "usage",
                "storage",
                "monitoring",
                "system",
                "diagnostics",
            ],
            parameters=[
                ToolParameter(
                    name="paths",
                    type=ParameterType.ARRAY,
                    required=False,
                    description="List of paths to check (default: current directory)",
                ),
                ToolParameter(
                    name="human_readable",
                    type=ParameterType.BOOLEAN,
                    required=False,
                    description="Format sizes in human readable format (default: true)",
                ),
            ],
        )

    def _format_bytes(self, bytes_val: int, human_readable: bool):
        """Format bytes value."""
        if not human_readable:
            return bytes_val

        bytes_value = float(bytes_val)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

    def _get_disk_usage_psutil(self, path: str, human_readable: bool) -> Dict[str, Any]:
        """Get disk usage using psutil."""
        import psutil

        usage = psutil.disk_usage(path)

        return {
            "path": os.path.abspath(path),
            "total": self._format_bytes(usage.total, human_readable),
            "used": self._format_bytes(usage.used, human_readable),
            "free": self._format_bytes(usage.free, human_readable),
            "percent": round((usage.used / usage.total) * 100, 2),
            "raw_bytes": (
                {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                }
                if not human_readable
                else None
            ),
        }

    def _get_disk_usage_statvfs(
        self, path: str, human_readable: bool
    ) -> Dict[str, Any]:
        """Get disk usage using os.statvfs (Unix fallback)."""
        statvfs = os.statvfs(path)
        total = statvfs.f_frsize * statvfs.f_blocks
        # Use f_bavail if f_available is not available
        available_blocks = getattr(statvfs, "f_available", statvfs.f_bavail)
        free = statvfs.f_frsize * available_blocks
        used = total - free

        return {
            "path": os.path.abspath(path),
            "total": self._format_bytes(total, human_readable),
            "used": self._format_bytes(used, human_readable),
            "free": self._format_bytes(free, human_readable),
            "percent": (round((used / total) * 100, 2) if total > 0 else 0),
            "raw_bytes": (
                {
                    "total": total,
                    "used": used,
                    "free": free,
                }
                if not human_readable
                else None
            ),
        }

    def _get_path_disk_usage(self, path: str, human_readable: bool) -> Dict[str, Any]:
        """Get disk usage for a single path."""
        if not os.path.exists(path):
            return {"path": path, "error": "Path does not exist"}

        try:
            return self._get_disk_usage_psutil(path, human_readable)
        except ImportError:
            # Fallback to os.statvfs on Unix systems
            if hasattr(os, "statvfs"):
                return self._get_disk_usage_statvfs(path, human_readable)
            else:
                return {
                    "path": os.path.abspath(path),
                    "error": "Disk usage information not available on this platform",
                }

    async def execute(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute the disk usage operation."""
        try:
            paths = parameters.get("paths", ["."])
            human_readable = parameters.get("human_readable", True)

            results = []

            for path in paths:
                try:
                    result = self._get_path_disk_usage(path, human_readable)
                    results.append(result)
                except Exception as e:
                    results.append(
                        {
                            "path": path,
                            "error": f"Failed to get disk usage: {str(e)}",
                        }
                    )

            return Result[Any].success_result(
                data={"results": results, "human_readable": human_readable}
            )

        except Exception as e:
            return Result[Any].error_result(error=f"Failed to get disk usage: {str(e)}")


class NetworkInfoTool(BaseTool):
    """Tool for getting network connectivity information."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="network_info",
            description="Get comprehensive network connectivity and interface information including DNS resolution, connection tests, interface details, and I/O statistics for network diagnostics.",
            brief_description="Get network connectivity and interface information",
            detailed_description="Get comprehensive network connectivity and interface information. Takes optional 'test_connectivity' (boolean, default true) to test internet connectivity, 'test_hosts' (array, default ['8.8.8.8', 'google.com']) for list of hosts to test connectivity to, and 'timeout' (integer, default 5) for timeout in seconds for connectivity tests. Returns hostname, local IP, connectivity test results, network interfaces, and I/O statistics.",
            category="system",
            tags=[
                "network",
                "connectivity",
                "interfaces",
                "dns",
                "diagnostics",
                "monitoring",
            ],
            parameters=[
                ToolParameter(
                    name="test_connectivity",
                    type=ParameterType.BOOLEAN,
                    required=False,
                    description="Test internet connectivity (default: true)",
                ),
                ToolParameter(
                    name="test_hosts",
                    type=ParameterType.ARRAY,
                    required=False,
                    description="List of hosts to test connectivity to (default: ['8.8.8.8', 'google.com'])",
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    required=False,
                    description="Timeout in seconds for connectivity tests (default: 5)",
                ),
            ],
        )

    def _get_basic_network_info(self) -> Dict[str, Any]:
        """Get basic network information."""
        info = {"hostname": socket.gethostname(), "fqdn": socket.getfqdn()}

        # Get local IP address
        try:
            # Connect to a remote address to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                info["local_ip"] = s.getsockname()[0]
        except Exception:
            info["local_ip"] = "127.0.0.1"

        return info

    def _test_host_connectivity(self, host: str, timeout: int) -> Dict[str, Any]:
        """Test connectivity to a single host."""
        try:
            start_time = datetime.now()

            # DNS resolution
            try:
                resolved_ip = socket.gethostbyname(host)
                dns_success = True
            except socket.gaierror:
                resolved_ip = None
                dns_success = False

            # Connection test
            connection_success = False
            if resolved_ip:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(timeout)
                        result = s.connect_ex((resolved_ip, 80))
                        connection_success = result == 0
                except Exception:
                    connection_success = False

            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            return {
                "host": host,
                "resolved_ip": resolved_ip,
                "dns_success": dns_success,
                "connection_success": connection_success,
                "response_time": response_time,
            }

        except Exception as e:
            return {"host": host, "error": str(e)}

    def _get_connectivity_tests(
        self, test_hosts: list, timeout: int
    ) -> List[Dict[str, Any]]:
        """Test connectivity to multiple hosts."""
        connectivity_results = []
        for host in test_hosts:
            result = self._test_host_connectivity(host, timeout)
            connectivity_results.append(result)
        return connectivity_results

    def _get_detailed_network_info(self) -> Dict[str, Any]:
        """Get detailed network information using psutil."""
        try:
            import psutil

            network_info = {}

            # Network interfaces
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info: Dict[str, Any] = {
                    "addresses": [],
                    "is_up": interface in psutil.net_if_stats()
                    and psutil.net_if_stats()[interface].isup,
                }

                for addr in addrs:
                    interface_info["addresses"].append(
                        {
                            "family": str(addr.family),
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast,
                        }
                    )

                interfaces[interface] = interface_info

            network_info["interfaces"] = interfaces

            # Network I/O statistics
            net_io = psutil.net_io_counters()
            network_info["io_stats"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
            }

            return network_info

        except ImportError:
            return {"interfaces": {"note": "Detailed interface info requires psutil"}}

    async def execute(
        self, parameters: Dict[str, Any], context: ToolContext
    ) -> Result[Any]:
        """Execute the network info operation."""
        try:
            test_connectivity = parameters.get("test_connectivity", True)
            test_hosts = parameters.get("test_hosts", ["8.8.8.8", "google.com"])
            timeout = parameters.get("timeout", 5)

            info = self._get_basic_network_info()

            # Test connectivity
            if test_connectivity:
                info["connectivity_tests"] = self._get_connectivity_tests(
                    test_hosts, timeout
                )

            # Get detailed network information
            detailed_info = self._get_detailed_network_info()
            info.update(detailed_info)

            return Result[Any].success_result(data=info)

        except Exception as e:
            return Result[Any].error_result(
                error=f"Failed to get network info: {str(e)}"
            )
