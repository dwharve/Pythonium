"""
Tool dependency management system.

This module provides functionality to manage dependencies between tools,
including dependency resolution, validation, and ordering.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pythonium.common.exceptions import PythoniumError

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies between tools."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    SOFT = "soft"


@dataclass
class Dependency:
    """Represents a tool dependency."""

    tool_id: str
    dependency_type: DependencyType
    version_requirement: Optional[str] = None
    description: Optional[str] = None


class DependencyError(PythoniumError):
    """Raised when dependency operations fail."""

    pass


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected."""

    pass


class MissingDependencyError(DependencyError):
    """Raised when required dependencies are missing."""

    pass


class DependencyManager:
    """
    Manages tool dependencies and provides resolution capabilities.

    This manager handles:
    - Dependency registration and validation
    - Circular dependency detection
    - Dependency resolution and ordering
    - Dependency graph analysis
    """

    def __init__(self):
        self._dependencies: Dict[str, List[Dependency]] = {}
        self._reverse_dependencies: Dict[str, Set[str]] = {}
        self._resolution_cache: Dict[str, List[str]] = {}

    def register_dependency(
        self,
        tool_id: str,
        dependency_id: str,
        dependency_type: DependencyType = DependencyType.REQUIRED,
        version_requirement: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Register a dependency for a tool.

        Args:
            tool_id: ID of the tool that has the dependency
            dependency_id: ID of the tool that is depended upon
            dependency_type: Type of dependency
            version_requirement: Version requirement string
            description: Human-readable description

        Raises:
            CircularDependencyError: If this would create a circular dependency
        """
        dependency = Dependency(
            tool_id=dependency_id,
            dependency_type=dependency_type,
            version_requirement=version_requirement,
            description=description,
        )

        # Check for circular dependencies before adding
        if self._would_create_cycle(tool_id, dependency_id):
            raise CircularDependencyError(
                f"Adding dependency {dependency_id} to {tool_id} would create a circular dependency"
            )

        # Add to dependencies
        if tool_id not in self._dependencies:
            self._dependencies[tool_id] = []
        self._dependencies[tool_id].append(dependency)

        # Update reverse dependencies
        if dependency_id not in self._reverse_dependencies:
            self._reverse_dependencies[dependency_id] = set()
        self._reverse_dependencies[dependency_id].add(tool_id)

        # Clear resolution cache
        self._resolution_cache.clear()

        logger.debug(
            f"Registered {dependency_type.value} dependency: {tool_id} -> {dependency_id}"
        )

    def get_dependencies(self, tool_id: str) -> List[Dependency]:
        """Get all dependencies for a tool."""
        return self._dependencies.get(tool_id, []).copy()

    def get_dependents(self, tool_id: str) -> Set[str]:
        """Get all tools that depend on the given tool."""
        return self._reverse_dependencies.get(tool_id, set()).copy()

    def has_dependency(self, tool_id: str, dependency_id: str) -> bool:
        """Check if a tool has a specific dependency."""
        dependencies = self._dependencies.get(tool_id, [])
        return any(dep.tool_id == dependency_id for dep in dependencies)

    def remove_dependency(self, tool_id: str, dependency_id: str) -> bool:
        """
        Remove a dependency.

        Args:
            tool_id: Tool with the dependency
            dependency_id: Dependency to remove

        Returns:
            True if dependency was removed, False if not found
        """
        if tool_id not in self._dependencies:
            return False

        dependencies = self._dependencies[tool_id]
        original_count = len(dependencies)

        # Remove the dependency
        dependencies[:] = [dep for dep in dependencies if dep.tool_id != dependency_id]

        if len(dependencies) < original_count:
            # Update reverse dependencies
            if dependency_id in self._reverse_dependencies:
                self._reverse_dependencies[dependency_id].discard(tool_id)
                if not self._reverse_dependencies[dependency_id]:
                    del self._reverse_dependencies[dependency_id]

            # Clear resolution cache
            self._resolution_cache.clear()

            logger.debug(f"Removed dependency: {tool_id} -> {dependency_id}")
            return True

        return False

    def resolve_dependencies(
        self,
        tool_ids: List[str],
        available_tools: Set[str],
        include_optional: bool = False,
    ) -> List[str]:
        """
        Resolve dependencies and return tools in execution order.

        Args:
            tool_ids: List of tools to resolve dependencies for
            available_tools: Set of available tool IDs
            include_optional: Whether to include optional dependencies

        Returns:
            List of tool IDs in dependency order

        Raises:
            MissingDependencyError: If required dependencies are missing
            CircularDependencyError: If circular dependencies exist
        """
        # Check cache first
        cache_key = f"{sorted(tool_ids)}:{sorted(available_tools)}:{include_optional}"
        if cache_key in self._resolution_cache:
            return self._resolution_cache[cache_key].copy()

        resolved = []
        visited = set()
        visiting = set()

        def visit(tool_id: str) -> None:
            if tool_id in visiting:
                raise CircularDependencyError(
                    f"Circular dependency detected involving {tool_id}"
                )
            if tool_id in visited:
                return

            visiting.add(tool_id)

            # Process dependencies
            dependencies = self._dependencies.get(tool_id, [])
            for dep in dependencies:
                # Skip optional dependencies if not requested
                if (
                    not include_optional
                    and dep.dependency_type == DependencyType.OPTIONAL
                ):
                    continue

                # Check if dependency is available
                if dep.tool_id not in available_tools:
                    if dep.dependency_type == DependencyType.REQUIRED:
                        raise MissingDependencyError(
                            f"Required dependency {dep.tool_id} for {tool_id} is not available"
                        )
                    else:
                        logger.warning(
                            f"Optional dependency {dep.tool_id} for {tool_id} is not available"
                        )
                        continue

                # Recursively visit dependency
                visit(dep.tool_id)

            visiting.remove(tool_id)
            visited.add(tool_id)

            if tool_id not in resolved:
                resolved.append(tool_id)

        # Visit all requested tools
        for tool_id in tool_ids:
            if tool_id in available_tools:
                visit(tool_id)
            else:
                raise MissingDependencyError(f"Tool {tool_id} is not available")

        # Cache result
        self._resolution_cache[cache_key] = resolved.copy()

        logger.debug(f"Resolved dependencies for {tool_ids}: {resolved}")
        return resolved

    def validate_dependencies(self, available_tools: Set[str]) -> Dict[str, List[str]]:
        """
        Validate all registered dependencies against available tools.

        Args:
            available_tools: Set of available tool IDs

        Returns:
            Dictionary mapping tool IDs to lists of missing required dependencies
        """
        missing_deps = {}

        for tool_id, dependencies in self._dependencies.items():
            missing = []
            for dep in dependencies:
                if (
                    dep.dependency_type == DependencyType.REQUIRED
                    and dep.tool_id not in available_tools
                ):
                    missing.append(dep.tool_id)

            if missing:
                missing_deps[tool_id] = missing

        return missing_deps

    def get_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the complete dependency graph.

        Returns:
            Dictionary representation of the dependency graph
        """
        graph = {}

        for tool_id, dependencies in self._dependencies.items():
            graph[tool_id] = {
                "dependencies": [
                    {
                        "tool_id": dep.tool_id,
                        "type": dep.dependency_type.value,
                        "version_requirement": dep.version_requirement,
                        "description": dep.description,
                    }
                    for dep in dependencies
                ],
                "dependents": list(self._reverse_dependencies.get(tool_id, set())),
            }

        return graph

    def clear_dependencies(self, tool_id: Optional[str] = None) -> None:
        """
        Clear dependencies for a specific tool or all tools.

        Args:
            tool_id: Tool to clear dependencies for, or None for all tools
        """
        if tool_id is None:
            self._dependencies.clear()
            self._reverse_dependencies.clear()
            logger.debug("Cleared all dependencies")
        else:
            # Clear dependencies for specific tool
            if tool_id in self._dependencies:
                deps = self._dependencies[tool_id]
                for dep in deps:
                    if dep.tool_id in self._reverse_dependencies:
                        self._reverse_dependencies[dep.tool_id].discard(tool_id)
                        if not self._reverse_dependencies[dep.tool_id]:
                            del self._reverse_dependencies[dep.tool_id]
                del self._dependencies[tool_id]

            # Clear reverse dependencies
            if tool_id in self._reverse_dependencies:
                for dependent in self._reverse_dependencies[tool_id]:
                    if dependent in self._dependencies:
                        self._dependencies[dependent] = [
                            dep
                            for dep in self._dependencies[dependent]
                            if dep.tool_id != tool_id
                        ]
                del self._reverse_dependencies[tool_id]

            logger.debug(f"Cleared dependencies for {tool_id}")

        # Clear resolution cache
        self._resolution_cache.clear()

    def _would_create_cycle(self, tool_id: str, dependency_id: str) -> bool:
        """Check if adding a dependency would create a circular dependency."""
        if tool_id == dependency_id:
            return True

        # Check if dependency_id already depends on tool_id (directly or indirectly)
        visited = set()

        def has_path_to(current: str, target: str) -> bool:
            if current == target:
                return True
            if current in visited:
                return False

            visited.add(current)
            dependencies = self._dependencies.get(current, [])

            for dep in dependencies:
                if has_path_to(dep.tool_id, target):
                    return True

            return False

        return has_path_to(dependency_id, tool_id)
