"""
Service monitoring tools for the Pythonium framework.

Provides tools for monitoring system services, processes, and
application health with cross-platform support.
"""

import os
import socket
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

from pythonium.common.base import Result
from pythonium.common.parameter_validation import (
    PortMonitorParams,
    ServiceStatusParams,
    SystemLoadParams,
    validate_parameters,
)
from pythonium.tools.base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolMetadata,
    ToolParameter,
)


class ServiceStatusTool(BaseTool):
    """Tool for checking service status on different platforms."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="service_status",
            description="Check the status of system services across different platforms with comprehensive service information.",
            brief_description="Check the status of system services",
            detailed_description="Check the status of system services across different platforms. Takes 'services' (required array) for list of service names to check, and optional 'platform' (string, default 'auto') to specify target platform (auto, windows, linux, darwin). Returns detailed service information including status, running state, enabled state, and resource usage when available. Essential for system monitoring, service health checks, and infrastructure management.",
            category="system",
            tags=["service", "status", "monitoring", "system", "health"],
            parameters=[
                ToolParameter(
                    name="services",
                    type=ParameterType.ARRAY,
                    required=True,
                    description="List of service names to check",
                ),
                ToolParameter(
                    name="platform",
                    type=ParameterType.STRING,
                    required=False,
                    description="Target platform (auto, windows, linux, darwin) (default: auto)",
                ),
            ],
        )

    def _detect_platform(self, platform: str) -> str:
        """Auto-detect platform if needed."""
        if platform != "auto":
            return platform

        if os.name == "nt":
            return "windows"
        elif sys.platform == "darwin":
            return "darwin"
        else:
            return "linux"

    def _check_windows_service(self, service: str) -> Dict[str, Any]:
        """Check Windows service using sc command."""
        import subprocess

        service_info = {
            "service_name": service,
            "platform": "windows",
            "status": "unknown",
            "running": False,
            "enabled": None,
            "pid": None,
            "memory_usage": None,
            "cpu_usage": None,
        }

        try:
            result = subprocess.run(
                ["sc", "query", service],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout
                if "RUNNING" in output:
                    service_info["status"] = "running"
                    service_info["running"] = True
                elif "STOPPED" in output:
                    service_info["status"] = "stopped"
                elif "PAUSED" in output:
                    service_info["status"] = "paused"

                # Get service configuration
                self._get_windows_service_config(service, service_info)
            else:
                service_info["status"] = "not_found"
                service_info["error"] = result.stderr.strip()

        except subprocess.TimeoutExpired:
            service_info["status"] = "timeout"
            service_info["error"] = "Command timed out"
        except Exception as e:
            service_info["status"] = "error"
            service_info["error"] = str(e)

        return service_info

    def _get_windows_service_config(
        self, service: str, service_info: Dict[str, Any]
    ) -> None:
        """Get Windows service configuration details."""
        import subprocess

        try:
            config_result = subprocess.run(
                ["sc", "qc", service],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if config_result.returncode == 0:
                config_output = config_result.stdout
                if "AUTO_START" in config_output:
                    service_info["enabled"] = True
                elif "DISABLED" in config_output:
                    service_info["enabled"] = False
        except subprocess.TimeoutExpired:
            pass

    def _check_linux_service(self, service: str) -> Dict[str, Any]:
        """Check Linux service using systemctl or service command."""
        import subprocess

        service_info = {
            "service_name": service,
            "platform": "linux",
            "status": "unknown",
            "running": False,
            "enabled": None,
            "pid": None,
            "memory_usage": None,
            "cpu_usage": None,
        }

        try:
            # Try systemctl first
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=10,
            )

            status = result.stdout.strip()
            service_info["running"] = status == "active"
            service_info["status"] = status

            # Check if enabled
            enabled_result = subprocess.run(
                ["systemctl", "is-enabled", service],
                capture_output=True,
                text=True,
                timeout=10,
            )
            enabled_status = enabled_result.stdout.strip()
            service_info["enabled"] = enabled_status == "enabled"

        except FileNotFoundError:
            # Fallback to service command
            self._check_linux_service_fallback(service, service_info)
        except subprocess.TimeoutExpired:
            service_info["status"] = "timeout"
            service_info["error"] = "Command timed out"
        except Exception as e:
            service_info["status"] = "error"
            service_info["error"] = str(e)

        return service_info

    def _check_linux_service_fallback(
        self, service: str, service_info: Dict[str, Any]
    ) -> None:
        """Fallback Linux service check using service command."""
        import subprocess

        try:
            result = subprocess.run(
                ["service", service, "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout.lower()
                if "running" in output or "active" in output:
                    service_info["status"] = "running"
                    service_info["running"] = True
                else:
                    service_info["status"] = "stopped"
            else:
                service_info["status"] = "unknown"
                service_info["error"] = result.stderr.strip()
        except FileNotFoundError:
            service_info["status"] = "command_not_found"
            service_info["error"] = "Neither systemctl nor service command available"

    def _check_darwin_service(self, service: str) -> Dict[str, Any]:
        """Check macOS service using launchctl."""
        import subprocess

        service_info = {
            "service_name": service,
            "platform": "darwin",
            "status": "unknown",
            "running": False,
            "enabled": None,
            "pid": None,
            "memory_usage": None,
            "cpu_usage": None,
        }

        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self._parse_launchctl_output(result.stdout, service, service_info)
            else:
                service_info["status"] = "error"
                service_info["error"] = result.stderr.strip()

        except FileNotFoundError:
            service_info["status"] = "command_not_found"
            service_info["error"] = "launchctl command not available"
        except subprocess.TimeoutExpired:
            service_info["status"] = "timeout"
            service_info["error"] = "Command timed out"
        except Exception as e:
            service_info["status"] = "error"
            service_info["error"] = str(e)

        return service_info

    def _parse_launchctl_output(
        self, output: str, service: str, service_info: Dict[str, Any]
    ) -> None:
        """Parse launchctl list output for service information."""
        lines = output.split("\n")
        service_found = False

        for line in lines:
            if service in line:
                parts = line.split()
                if len(parts) >= 3:
                    pid = parts[0]
                    service_info["running"] = pid != "-"
                    service_info["status"] = "running" if pid != "-" else "stopped"
                    if pid != "-":
                        try:
                            service_info["pid"] = int(pid)
                        except ValueError:
                            pass
                    service_found = True
                    break

        if not service_found:
            service_info["status"] = "not_found"

        # Function modifies service_info in place, no return needed

    def _enhance_service_info_with_process_data(
        self, service_info: Dict[str, Any]
    ) -> None:
        """Add process information if service is running."""
        if not service_info["running"] or not service_info["pid"]:
            return

        try:
            import psutil

            process = psutil.Process(service_info["pid"])
            service_info["memory_usage"] = process.memory_info().rss
            service_info["cpu_usage"] = process.cpu_percent()
        except (ImportError, psutil.NoSuchProcess):
            pass

    def _check_single_service(self, service: str, platform: str) -> Dict[str, Any]:
        """Check a single service based on platform."""
        try:
            if platform == "windows":
                service_info = self._check_windows_service(service)
            elif platform == "linux":
                service_info = self._check_linux_service(service)
            elif platform == "darwin":
                service_info = self._check_darwin_service(service)
            else:
                return {
                    "service_name": service,
                    "status": "unsupported_platform",
                    "error": f"Platform {platform} not supported",
                    "running": False,
                }

            # Enhance with process information
            self._enhance_service_info_with_process_data(service_info)
            return service_info

        except Exception as e:
            return {
                "service_name": service,
                "status": "error",
                "error": str(e),
                "running": False,
            }

    @validate_parameters(ServiceStatusParams)
    async def execute(
        self, parameters: ServiceStatusParams, context: ToolContext
    ) -> Result:
        """Execute the service status check operation."""
        try:
            services = parameters.services
            platform = self._detect_platform(parameters.platform)

            results = []
            for service in services:
                service_info = self._check_single_service(service, platform)
                results.append(service_info)

            return Result[Any].success_result(
                data={
                    "services": results,
                    "platform": platform,
                    "checked_count": len(results),
                    "running_count": sum(1 for s in results if s.get("running", False)),
                }
            )

        except Exception as e:
            return Result[Any].error_result(f"Failed to check service status: {str(e)}")


class PortMonitorTool(BaseTool):
    """Tool for monitoring network ports and services."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="port_monitor",
            description="Monitor network ports and check if services are listening with configurable protocols and timeout settings.",
            brief_description="Monitor network ports and check if services are listening",
            detailed_description="Monitor network ports and check if services are listening with configurable options. Takes 'ports' (required array) for list of ports to check in format 'port' or 'host:port', optional 'timeout' (integer, default 5) for connection timeout in seconds, and 'protocol' (string, default 'tcp') for protocol to use (tcp, udp). Essential for network monitoring, service discovery, and connectivity testing.",
            category="system",
            tags=["port", "monitor", "network", "services", "connectivity"],
            parameters=[
                ToolParameter(
                    name="ports",
                    type=ParameterType.ARRAY,
                    required=True,
                    description="List of ports to check (format: port or host:port)",
                ),
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    required=False,
                    description="Connection timeout in seconds (default: 5)",
                ),
                ToolParameter(
                    name="protocol",
                    type=ParameterType.STRING,
                    required=False,
                    description="Protocol to use for checking (tcp, udp) (default: tcp)",
                ),
            ],
        )

    @validate_parameters(PortMonitorParams)
    async def execute(
        self, parameters: PortMonitorParams, context: ToolContext
    ) -> Result:
        """Execute the port monitoring operation."""
        try:
            ports = parameters.ports
            timeout = parameters.timeout
            protocol = parameters.protocol
            host = parameters.host

            results = []

            for port in ports:
                port_info = self._check_single_port(f"{host}:{port}", timeout, protocol)
                results.append(port_info)

            return Result[Any].success_result(
                data={
                    "ports": results,
                    "protocol": protocol,
                    "timeout": timeout,
                    "host": host,
                    "total_checked": len(results),
                    "open_ports": sum(1 for p in results if p.get("open", False)),
                }
            )

        except Exception as e:
            return Result[Any].error_result(f"Failed to monitor ports: {str(e)}")

    def _check_single_port(
        self, port_spec: str, timeout: int, protocol: str
    ) -> Dict[str, Any]:
        """Check a single port specification."""
        try:
            # Parse port specification
            host, port = self._parse_port_spec(port_spec)

            port_info = {
                "host": host,
                "port": port,
                "protocol": protocol,
                "open": False,
                "response_time": None,
                "service_name": None,
                "error": None,
            }

            # Check if port is open and measure response time
            start_time = time.time()
            port_info["open"] = self._check_port_connectivity(
                host, port, timeout, protocol, port_info
            )
            end_time = time.time()

            port_info["response_time"] = round((end_time - start_time) * 1000, 2)  # ms

            # Try to identify service if port is open
            if port_info["open"]:
                port_info["service_name"] = self._identify_service(port, protocol)

            return port_info

        except ValueError:
            return {
                "port_spec": port_spec,
                "error": "Invalid port specification",
                "open": False,
            }
        except Exception as e:
            return {"port_spec": port_spec, "error": str(e), "open": False}

    def _parse_port_spec(self, port_spec: str) -> tuple:
        """Parse port specification into host and port."""
        if ":" in port_spec:
            host, port_str = port_spec.rsplit(":", 1)
            port = int(port_str)
        else:
            host = "localhost"
            port = int(port_spec)
        return host, port

    def _check_port_connectivity(
        self,
        host: str,
        port: int,
        timeout: int,
        protocol: str,
        port_info: Dict,
    ) -> bool:
        """Check if the port is open using the specified protocol."""
        if protocol == "tcp":
            return self._check_tcp_port(host, port, timeout, port_info)
        elif protocol == "udp":
            return self._check_udp_port(host, port, timeout, port_info)
        return False

    def _check_tcp_port(
        self, host: str, port: int, timeout: int, port_info: Dict
    ) -> bool:
        """Check TCP port connectivity."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except socket.gaierror as e:
            port_info["error"] = f"Name resolution failed: {str(e)}"
            return False
        except Exception as e:
            port_info["error"] = str(e)
            return False

    def _check_udp_port(
        self, host: str, port: int, timeout: int, port_info: Dict
    ) -> bool:
        """Check UDP port connectivity."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                sock.sendto(b"test", (host, port))
                try:
                    sock.recvfrom(1024)
                    return True
                except socket.timeout:
                    # For UDP, timeout might mean the port is open but not responding
                    port_info["note"] = (
                        "UDP port may be open (no response to test packet)"
                    )
                    return True
        except Exception as e:
            port_info["error"] = str(e)
            return False

    def _identify_service(self, port: int, protocol: str) -> str:
        """Identify the service running on the port."""
        try:
            return socket.getservbyport(port, protocol)
        except OSError:
            # Common port mappings
            common_ports = {
                21: "ftp",
                22: "ssh",
                23: "telnet",
                25: "smtp",
                53: "dns",
                80: "http",
                110: "pop3",
                143: "imap",
                443: "https",
                993: "imaps",
                995: "pop3s",
                3306: "mysql",
                5432: "postgresql",
                6379: "redis",
                27017: "mongodb",
            }
            return common_ports.get(port, "unknown")


class SystemLoadTool(BaseTool):
    """Tool for monitoring system load and performance metrics."""

    async def initialize(self) -> None:
        """Initialize the tool."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="system_load",
            description="Monitor comprehensive system load and performance metrics including CPU, memory, disk usage, and top processes.",
            brief_description="Monitor system load and performance metrics",
            detailed_description="Monitor comprehensive system load and performance metrics with configurable process reporting. Takes optional 'include_processes' (boolean, default true) to include top processes information, 'process_limit' (integer, default 10) for number of top processes to include, and 'sort_by' (string, default 'cpu') for process sorting metric (cpu, memory, pid, name). Provides detailed system information including uptime, load average, CPU usage, memory consumption, and disk utilization. Essential for performance monitoring, system analysis, and resource optimization.",
            category="system",
            tags=["system", "load", "performance", "monitoring", "metrics"],
            parameters=[
                ToolParameter(
                    name="include_processes",
                    type=ParameterType.BOOLEAN,
                    required=False,
                    description="Include top processes information (default: true)",
                ),
                ToolParameter(
                    name="process_limit",
                    type=ParameterType.INTEGER,
                    required=False,
                    description="Number of top processes to include (default: 10)",
                ),
                ToolParameter(
                    name="sort_by",
                    type=ParameterType.STRING,
                    required=False,
                    description="Sort processes by metric (cpu, memory, pid, name) (default: cpu)",
                ),
            ],
        )

    @validate_parameters(SystemLoadParams)
    def _initialize_load_info(self) -> Dict[str, Any]:
        """Initialize the load info structure."""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "uptime": None,
                "load_average": None,
                "cpu": {"percent": None, "count": None},
                "memory": {
                    "total": None,
                    "available": None,
                    "used": None,
                    "percent": None,
                },
                "disk": {
                    "total": None,
                    "used": None,
                    "free": None,
                    "percent": None,
                },
            },
        }

    def _collect_cpu_info(self, psutil, load_info: Dict[str, Any]) -> None:
        """Collect CPU information."""
        load_info["system"]["cpu"]["percent"] = psutil.cpu_percent(interval=1)
        load_info["system"]["cpu"]["count"] = psutil.cpu_count()

    def _collect_memory_info(self, psutil, load_info: Dict[str, Any]) -> None:
        """Collect memory information."""
        memory = psutil.virtual_memory()
        load_info["system"]["memory"] = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
        }

    def _collect_disk_info(self, psutil, load_info: Dict[str, Any]) -> None:
        """Collect disk information."""
        disk = psutil.disk_usage("/")
        load_info["system"]["disk"] = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": round((disk.used / disk.total) * 100, 2),
        }

    def _collect_uptime_info(self, psutil, load_info: Dict[str, Any]) -> None:
        """Collect system uptime information."""
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        load_info["system"]["uptime"] = {
            "seconds": int(uptime_seconds),
            "formatted": str(timedelta(seconds=int(uptime_seconds))),
        }

    def _collect_load_average(self, load_info: Dict[str, Any]) -> None:
        """Collect load average information."""
        if hasattr(os, "getloadavg"):
            load_avg = os.getloadavg()
            load_info["system"]["load_average"] = {
                "1min": load_avg[0],
                "5min": load_avg[1],
                "15min": load_avg[2],
            }

    def _collect_processes_info(
        self, psutil, sort_by: str, process_limit: int
    ) -> List[Dict[str, Any]]:
        """Collect and sort process information."""
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                proc_info = proc.info
                proc_info["cpu_percent"] = proc.cpu_percent()
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort processes
        if sort_by == "cpu":
            processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
        elif sort_by == "pid":
            processes.sort(key=lambda x: x.get("pid", 0))
        elif sort_by == "name":
            processes.sort(key=lambda x: x.get("name", ""))

        return processes

    async def execute(self, parameters: Dict[str, Any], context: ToolContext) -> Result:
        """Execute the system load monitoring operation."""
        try:
            include_processes = parameters.get("include_processes", False)
            process_limit = parameters.get("process_limit", 10)
            sort_by = parameters.get("sort_by", "cpu")

            load_info = self._initialize_load_info()

            try:
                import psutil

                self._collect_cpu_info(psutil, load_info)
                self._collect_memory_info(psutil, load_info)
                self._collect_disk_info(psutil, load_info)
                self._collect_uptime_info(psutil, load_info)
                self._collect_load_average(load_info)

                # Process information
                if include_processes:
                    processes = self._collect_processes_info(
                        psutil, sort_by, process_limit
                    )
                    load_info["processes"] = {
                        "top_processes": processes[:process_limit],
                        "total_count": len(processes),
                        "sort_by": sort_by,
                    }

            except ImportError:
                load_info["error"] = (
                    "psutil not available for detailed system monitoring"
                )

                # Fallback to basic system information
                self._collect_load_average(load_info)

            return Result[Any].success_result(data=load_info)

        except Exception as e:
            return Result[Any].error_result(
                f"Failed to get system load information: {str(e)}"
            )
