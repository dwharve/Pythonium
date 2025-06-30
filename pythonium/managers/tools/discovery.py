"""
Tool discovery manager for the Pythonium framework.

Provides automatic discovery and registration of tools from various sources
including Python modules, plugins, and external packages.
"""

import importlib
import inspect
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from pythonium.common.logging import get_logger
from pythonium.tools.base import BaseTool

logger = get_logger(__name__)


@dataclass
class DiscoveredTool:
    """Represents a discovered tool."""

    tool_class: Type[BaseTool]
    module_name: str
    source_path: str
    discovery_method: str
    metadata: Dict[str, Any]
    discovered_at: datetime


class ToolDiscoveryManager:
    """Manages automatic discovery of tools from various sources."""

    def __init__(self):
        self.discovered_tools: Dict[str, DiscoveredTool] = {}
        self.search_paths: List[Path] = []
        self.excluded_modules: Set[str] = set()
        self.tool_filters: List[Callable] = []

        # Add default search paths
        self._add_default_search_paths()

    def _add_default_search_paths(self):
        """Add default tool search paths."""
        # Add built-in tools path
        # This file is in managers/tools/discovery.py, so go up to pythonium/ then into tools/
        tools_path = Path(__file__).parent.parent.parent / "tools"
        self.search_paths.append(tools_path)

        # Add current working directory tools if exists
        cwd_tools = Path.cwd() / "pythonium_tools"
        if cwd_tools.exists():
            self.search_paths.append(cwd_tools)

    def add_search_path(self, path: Union[str, Path]):
        """Add a path to search for tools."""
        path = Path(path)
        if path.exists() and path not in self.search_paths:
            self.search_paths.append(path)
            logger.info(f"Added tool search path: {path}")

    def exclude_module(self, module_name: str):
        """Exclude a module from tool discovery."""
        self.excluded_modules.add(module_name)
        logger.info(f"Excluded module from discovery: {module_name}")

    def add_tool_filter(self, filter_func: Callable):
        """Add a filter function for discovered tools."""
        self.tool_filters.append(filter_func)

    def discover_tools(
        self,
        scan_packages: bool = True,
        scan_modules: bool = True,
        scan_plugins: bool = True,
    ) -> Dict[str, DiscoveredTool]:
        """Discover tools from all configured sources."""
        logger.info("Starting tool discovery...")

        discovered_count = 0

        if scan_packages:
            discovered_count += self._discover_from_packages()

        if scan_modules:
            discovered_count += self._discover_from_modules()

        if scan_plugins:
            discovered_count += self._discover_from_plugins()

        logger.info(f"Tool discovery completed. Found {discovered_count} new tools.")
        return self.discovered_tools

    def _discover_from_packages(self) -> int:
        """Discover tools from Python packages."""
        discovered = 0

        for search_path in self.search_paths:
            try:
                # Walk through all Python packages in the search path
                for root, dirs, files in os.walk(search_path):
                    # Skip __pycache__ and .pyc files
                    dirs[:] = [d for d in dirs if not d.startswith("__pycache__")]

                    if "__init__.py" in files:
                        # This is a Python package
                        package_path = Path(root)
                        relative_path = package_path.relative_to(search_path)

                        # Convert path to module name
                        module_parts = list(relative_path.parts)
                        if module_parts and package_path != search_path:
                            module_name = ".".join(module_parts)

                            # Skip excluded modules
                            if any(
                                excluded in module_name
                                for excluded in self.excluded_modules
                            ):
                                continue

                            try:
                                # Add the search path to sys.path temporarily
                                if str(search_path) not in sys.path:
                                    sys.path.insert(0, str(search_path))

                                # Import the module
                                module = importlib.import_module(module_name)
                                discovered += self._scan_module_for_tools(
                                    module,
                                    module_name,
                                    str(package_path),
                                    "package_scan",
                                )

                            except ImportError as e:
                                logger.debug(
                                    f"Could not import module {module_name}: {e}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Error scanning module {module_name}: {e}"
                                )
                            finally:
                                # Remove from sys.path if we added it
                                if str(search_path) in sys.path:
                                    sys.path.remove(str(search_path))

            except Exception as e:
                logger.error(f"Error discovering tools from path {search_path}: {e}")

        return discovered

    def _discover_from_modules(self) -> int:
        """Discover tools from individual Python modules."""
        discovered = 0

        for search_path in self.search_paths:
            try:
                # Look for individual .py files
                for py_file in search_path.glob("**/*.py"):
                    if py_file.name.startswith("__"):
                        continue

                    # Convert file path to module name
                    relative_path = py_file.relative_to(search_path)
                    module_parts = list(relative_path.with_suffix("").parts)
                    module_name = ".".join(module_parts)

                    # Skip excluded modules
                    if any(
                        excluded in module_name for excluded in self.excluded_modules
                    ):
                        continue

                    try:
                        # Add the search path to sys.path temporarily
                        if str(search_path) not in sys.path:
                            sys.path.insert(0, str(search_path))

                        # Import the module
                        module = importlib.import_module(module_name)
                        discovered += self._scan_module_for_tools(
                            module, module_name, str(py_file), "module_scan"
                        )

                    except ImportError as e:
                        logger.debug(f"Could not import module {module_name}: {e}")
                    except Exception as e:
                        logger.warning(f"Error scanning module {module_name}: {e}")
                    finally:
                        # Remove from sys.path if we added it
                        if str(search_path) in sys.path:
                            sys.path.remove(str(search_path))

            except Exception as e:
                logger.error(f"Error discovering modules from path {search_path}: {e}")

        return discovered

    def _discover_from_plugins(self) -> int:
        """Discover tools from installed plugins."""
        discovered = 0

        try:
            # Look for entry points (setuptools plugins)
            try:
                import pkg_resources

                for entry_point in pkg_resources.iter_entry_points("pythonium.tools"):
                    try:
                        tool_class = entry_point.load()

                        if self._is_valid_tool_class(tool_class):
                            tool_name = getattr(tool_class, "name", entry_point.name)

                            if tool_name not in self.discovered_tools:
                                discovered_tool = DiscoveredTool(
                                    tool_class=tool_class,
                                    module_name=tool_class.__module__,
                                    source_path=entry_point.dist.location,
                                    discovery_method="entry_point",
                                    metadata={
                                        "entry_point_name": entry_point.name,
                                        "distribution": entry_point.dist.project_name,
                                        "version": entry_point.dist.version,
                                    },
                                    discovered_at=datetime.now(),
                                )

                                self.discovered_tools[tool_name] = discovered_tool
                                discovered += 1
                                logger.info(
                                    f"Discovered tool via entry point: {tool_name}"
                                )

                    except Exception as e:
                        logger.warning(
                            f"Error loading entry point {entry_point.name}: {e}"
                        )

            except ImportError:
                logger.debug("pkg_resources not available for plugin discovery")

        except Exception as e:
            logger.error(f"Error discovering tools from plugins: {e}")

        return discovered

    def _scan_module_for_tools(
        self, module, module_name: str, source_path: str, discovery_method: str
    ) -> int:
        """Scan a module for tool classes."""
        discovered = 0

        try:
            for name, obj in inspect.getmembers(module):
                if self._is_valid_tool_class(obj):
                    tool_name = getattr(obj, "name", name)

                    # Apply filters
                    if not self._passes_filters(obj):
                        continue

                    if tool_name not in self.discovered_tools:
                        discovered_tool = DiscoveredTool(
                            tool_class=obj,
                            module_name=module_name,
                            source_path=source_path,
                            discovery_method=discovery_method,
                            metadata={
                                "class_name": name,
                                "module_file": getattr(module, "__file__", None),
                            },
                            discovered_at=datetime.now(),
                        )

                        self.discovered_tools[tool_name] = discovered_tool
                        discovered += 1
                        logger.debug(f"Discovered tool: {tool_name} from {module_name}")

        except Exception as e:
            logger.warning(f"Error scanning module {module_name} for tools: {e}")

        return discovered

    def _is_valid_tool_class(self, obj) -> bool:
        """Check if an object is a valid tool class."""
        try:
            return (
                inspect.isclass(obj)
                and issubclass(obj, BaseTool)
                and obj != BaseTool
                and not inspect.isabstract(obj)
            )
        except Exception:
            return False

    def _passes_filters(self, tool_class: Type[BaseTool]) -> bool:
        """Check if a tool class passes all configured filters."""
        for filter_func in self.tool_filters:
            try:
                if not filter_func(tool_class):
                    return False
            except Exception as e:
                logger.warning(f"Tool filter error: {e}")
                return False
        return True

    def get_discovered_tool(self, tool_name: str) -> Optional[DiscoveredTool]:
        """Get a discovered tool by name."""
        return self.discovered_tools.get(tool_name)

    def get_tools_by_category(self, category: str) -> List[DiscoveredTool]:
        """Get discovered tools by category."""
        tools = []
        for tool in self.discovered_tools.values():
            try:
                tool_instance = tool.tool_class()
                if (
                    hasattr(tool_instance, "metadata")
                    and tool_instance.metadata.category == category
                ):
                    tools.append(tool)
            except Exception as e:
                logger.debug(f"Error checking tool category: {e}")
        return tools

    def get_tools_by_source(self, source_path: str) -> List[DiscoveredTool]:
        """Get discovered tools by source path."""
        return [
            tool
            for tool in self.discovered_tools.values()
            if tool.source_path == source_path
        ]

    def refresh_discovery(self):
        """Refresh tool discovery by clearing cache and re-scanning."""
        logger.info("Refreshing tool discovery...")
        old_count = len(self.discovered_tools)
        self.discovered_tools.clear()

        new_tools = self.discover_tools()
        new_count = len(new_tools)

        logger.info(f"Discovery refresh complete: {old_count} -> {new_count} tools")
        return new_tools

    def export_discovery_report(self) -> Dict[str, Any]:
        """Export a comprehensive discovery report."""
        report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "total_tools": len(self.discovered_tools),
            "search_paths": [str(p) for p in self.search_paths],
            "excluded_modules": list(self.excluded_modules),
            "tools": {},
        }

        for tool_name, tool in self.discovered_tools.items():
            report["tools"][tool_name] = {
                "class_name": tool.tool_class.__name__,
                "module_name": tool.module_name,
                "source_path": tool.source_path,
                "discovery_method": tool.discovery_method,
                "discovered_at": tool.discovered_at.isoformat(),
                "metadata": tool.metadata,
            }

        # Group by discovery method
        report["by_discovery_method"] = {}
        for tool in self.discovered_tools.values():
            method = tool.discovery_method
            if method not in report["by_discovery_method"]:
                report["by_discovery_method"][method] = 0
            report["by_discovery_method"][method] += 1

        return report
