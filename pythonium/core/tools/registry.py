"""
Tool registry for the Pythonium framework.

Provides centralized registration and management of tools with
versioning, metadata, and lifecycle support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type

from pythonium.common.exceptions import ToolError
from pythonium.common.logging import get_logger
from pythonium.tools.base import BaseTool, ToolMetadata

logger = get_logger(__name__)


class ToolStatus(Enum):
    """Tool registration status."""

    REGISTERED = "registered"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ToolRegistration:
    """Represents a tool registration."""

    tool_id: str
    tool_class: Type[BaseTool]
    name: str
    version: str
    status: ToolStatus
    metadata: ToolMetadata
    registered_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0
    tags: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure tags are in set format - this is already guaranteed by type annotation
        pass


class ToolRegistry:
    """Central registry for tool management."""

    def __init__(self):
        self.tools: Dict[str, ToolRegistration] = {}
        self.tools_by_name: Dict[str, List[str]] = {}  # name -> [tool_ids]
        self.tools_by_category: Dict[str, List[str]] = {}  # category -> [tool_ids]
        self.tools_by_tags: Dict[str, List[str]] = {}  # tag -> [tool_ids]
        self.aliases: Dict[str, str] = {}  # alias -> tool_id

        self._event_handlers: Dict[str, List[Callable]] = {
            "tool_registered": [],
            "tool_unregistered": [],
            "tool_status_changed": [],
            "tool_used": [],
        }

    def register_tool(
        self,
        tool_class: Type[BaseTool],
        name: Optional[str] = None,
        version: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None,
    ) -> str:
        """Register a tool in the registry."""

        # Create tool instance to get metadata
        try:
            tool_instance = tool_class()
            metadata = tool_instance.metadata
        except Exception as e:
            raise ToolError(f"Failed to instantiate tool {tool_class.__name__}: {e}")

        # Use provided name or default to tool's name
        tool_name = name or metadata.name
        tool_version = version or metadata.version or "1.0.0"

        # Check for existing tool with same name and version
        existing_tool_id = self._find_tool_by_name_version(tool_name, tool_version)
        if existing_tool_id:
            raise ToolError(f"Tool {tool_name} v{tool_version} is already registered")

        # Generate stable tool ID (deterministic based on name only, no version)
        tool_id = tool_name

        # Create registration
        registration = ToolRegistration(
            tool_id=tool_id,
            tool_class=tool_class,
            name=tool_name,
            version=tool_version,
            status=ToolStatus.REGISTERED,
            metadata=metadata,
            registered_at=datetime.now(),
            tags=set(tags or []),
            dependencies=dependencies or [],
            config=config or {},
        )

        # Store in registry
        self.tools[tool_id] = registration

        # Update indexes
        self._update_name_index(tool_name, tool_id)
        self._update_category_index(metadata.category or "uncategorized", tool_id)

        for tag in registration.tags:
            self._update_tag_index(tag, tool_id)

        # Register aliases
        if aliases:
            for alias in aliases:
                self.add_alias(alias, tool_id)

        # Emit event
        self._emit_event(
            "tool_registered",
            {
                "tool_id": tool_id,
                "name": tool_name,
                "version": tool_version,
                "registration": registration,
            },
        )

        logger.info(f"Registered tool: {tool_name} v{tool_version} (ID: {tool_id})")
        return tool_id

    def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool from the registry."""
        if tool_id not in self.tools:
            return False

        registration = self.tools[tool_id]

        # Remove from indexes
        self._remove_from_name_index(registration.name, tool_id)
        self._remove_from_category_index(
            registration.metadata.category or "uncategorized", tool_id
        )

        for tag in registration.tags:
            self._remove_from_tag_index(tag, tool_id)

        # Remove aliases
        aliases_to_remove = [
            alias for alias, tid in self.aliases.items() if tid == tool_id
        ]
        for alias in aliases_to_remove:
            del self.aliases[alias]

        # Remove from registry
        del self.tools[tool_id]

        # Emit event
        self._emit_event(
            "tool_unregistered",
            {
                "tool_id": tool_id,
                "name": registration.name,
                "version": registration.version,
            },
        )

        logger.info(
            f"Unregistered tool: {registration.name} v{registration.version} (ID: {tool_id})"
        )
        return True

    def get_tool(self, identifier: str) -> Optional[ToolRegistration]:
        """Get a tool by ID, name, or alias."""
        # Try direct ID lookup
        if identifier in self.tools:
            return self.tools[identifier]

        # Try alias lookup
        if identifier in self.aliases:
            tool_id = self.aliases[identifier]
            return self.tools.get(tool_id)

        # Try name lookup (return latest version)
        if identifier in self.tools_by_name:
            tool_ids = self.tools_by_name[identifier]
            if tool_ids:
                # Return the most recently registered tool with this name
                latest_registration = None
                for tool_id in tool_ids:
                    registration = self.tools[tool_id]
                    if (
                        latest_registration is None
                        or registration.registered_at
                        > latest_registration.registered_at
                    ):
                        latest_registration = registration
                return latest_registration

        return None

    def get_tool_by_name_version(
        self, name: str, version: str
    ) -> Optional[ToolRegistration]:
        """Get a specific tool by name and version."""
        tool_id = self._find_tool_by_name_version(name, version)
        return self.tools.get(tool_id) if tool_id else None

    def list_tools(
        self,
        status: Optional[ToolStatus] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        name_pattern: Optional[str] = None,
    ) -> List[ToolRegistration]:
        """List tools with optional filtering."""
        tools = list(self.tools.values())

        # Filter by status
        if status:
            tools = [t for t in tools if t.status == status]

        # Filter by category
        if category:
            tools = [t for t in tools if t.metadata.category == category]

        # Filter by tags (tool must have all specified tags)
        if tags:
            tag_set = set(tags)
            tools = [t for t in tools if tag_set.issubset(t.tags)]

        # Filter by name pattern
        if name_pattern:
            import fnmatch

            tools = [t for t in tools if fnmatch.fnmatch(t.name, name_pattern)]

        return sorted(tools, key=lambda t: (t.name, t.version))

    def get_tools_by_category(self, category: str) -> List[ToolRegistration]:
        """Get all tools in a specific category."""
        tool_ids = self.tools_by_category.get(category, [])
        return [self.tools[tool_id] for tool_id in tool_ids if tool_id in self.tools]

    def get_tools_by_tag(self, tag: str) -> List[ToolRegistration]:
        """Get all tools with a specific tag."""
        tool_ids = self.tools_by_tags.get(tag, [])
        return [self.tools[tool_id] for tool_id in tool_ids if tool_id in self.tools]

    def update_tool_status(self, tool_id: str, status: ToolStatus) -> bool:
        """Update a tool's status."""
        if tool_id not in self.tools:
            return False

        old_status = self.tools[tool_id].status
        self.tools[tool_id].status = status

        # Emit event
        self._emit_event(
            "tool_status_changed",
            {
                "tool_id": tool_id,
                "old_status": old_status,
                "new_status": status,
                "registration": self.tools[tool_id],
            },
        )

        logger.info(f"Tool {tool_id} status changed: {old_status} -> {status}")
        return True

    def record_tool_usage(self, tool_id: str):
        """Record that a tool was used."""
        if tool_id in self.tools:
            registration = self.tools[tool_id]
            registration.last_used = datetime.now()
            registration.usage_count += 1

            # Emit event
            self._emit_event(
                "tool_used",
                {
                    "tool_id": tool_id,
                    "usage_count": registration.usage_count,
                    "registration": registration,
                },
            )

    def add_alias(self, alias: str, tool_id: str) -> bool:
        """Add an alias for a tool."""
        if alias in self.aliases:
            logger.warning(
                f"Alias {alias} already exists for tool {self.aliases[alias]}"
            )
            return False

        if tool_id not in self.tools:
            logger.error(f"Cannot create alias {alias}: tool {tool_id} not found")
            return False

        self.aliases[alias] = tool_id
        logger.info(f"Added alias {alias} for tool {tool_id}")
        return True

    def remove_alias(self, alias: str) -> bool:
        """Remove an alias."""
        if alias in self.aliases:
            tool_id = self.aliases[alias]
            del self.aliases[alias]
            logger.info(f"Removed alias {alias} for tool {tool_id}")
            return True
        return False

    def add_tool_tag(self, tool_id: str, tag: str) -> bool:
        """Add a tag to a tool."""
        if tool_id not in self.tools:
            return False

        registration = self.tools[tool_id]
        if tag not in registration.tags:
            registration.tags.add(tag)
            self._update_tag_index(tag, tool_id)
            logger.debug(f"Added tag {tag} to tool {tool_id}")

        return True

    def remove_tool_tag(self, tool_id: str, tag: str) -> bool:
        """Remove a tag from a tool."""
        if tool_id not in self.tools:
            return False

        registration = self.tools[tool_id]
        if tag in registration.tags:
            registration.tags.remove(tag)
            self._remove_from_tag_index(tag, tool_id)
            logger.debug(f"Removed tag {tag} from tool {tool_id}")

        return True

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        stats: Dict[str, Any] = {
            "total_tools": len(self.tools),
            "by_status": {},
            "by_category": {},
            "total_aliases": len(self.aliases),
            "total_tags": len(self.tools_by_tags),
            "most_used": [],
            "recently_registered": [],
        }

        # Count by status
        for registration in self.tools.values():
            status = registration.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # Count by category
        for category, tool_ids in self.tools_by_category.items():
            stats["by_category"][category] = len(tool_ids)

        # Most used tools (top 10)
        most_used = sorted(
            self.tools.values(), key=lambda t: t.usage_count, reverse=True
        )[:10]
        stats["most_used"] = [
            {
                "name": t.name,
                "version": t.version,
                "usage_count": t.usage_count,
            }
            for t in most_used
        ]

        # Recently registered tools (top 10)
        recently_registered = sorted(
            self.tools.values(), key=lambda t: t.registered_at, reverse=True
        )[:10]
        stats["recently_registered"] = [
            {
                "name": t.name,
                "version": t.version,
                "registered_at": t.registered_at.isoformat(),
            }
            for t in recently_registered
        ]

        return stats

    def clear_registry(self):
        """Clear all tools from the registry."""
        logger.warning("Clearing entire tool registry")
        self.tools.clear()
        self.tools_by_name.clear()
        self.tools_by_category.clear()
        self.tools_by_tags.clear()
        self.aliases.clear()

    def add_event_handler(self, event_type: str, handler: Callable):
        """Add an event handler."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove an event handler."""
        if (
            event_type in self._event_handlers
            and handler in self._event_handlers[event_type]
        ):
            self._event_handlers[event_type].remove(handler)

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    def _find_tool_by_name_version(self, name: str, version: str) -> Optional[str]:
        """Find a tool ID by name and version."""
        tool_ids = self.tools_by_name.get(name, [])
        for tool_id in tool_ids:
            if self.tools[tool_id].version == version:
                return tool_id
        return None

    def _update_name_index(self, name: str, tool_id: str):
        """Update the name index."""
        if name not in self.tools_by_name:
            self.tools_by_name[name] = []
        if tool_id not in self.tools_by_name[name]:
            self.tools_by_name[name].append(tool_id)

    def _remove_from_name_index(self, name: str, tool_id: str):
        """Remove from name index."""
        if name in self.tools_by_name and tool_id in self.tools_by_name[name]:
            self.tools_by_name[name].remove(tool_id)
            if not self.tools_by_name[name]:
                del self.tools_by_name[name]

    def _update_category_index(self, category: str, tool_id: str):
        """Update the category index."""
        if category not in self.tools_by_category:
            self.tools_by_category[category] = []
        if tool_id not in self.tools_by_category[category]:
            self.tools_by_category[category].append(tool_id)

    def _remove_from_category_index(self, category: str, tool_id: str):
        """Remove from category index."""
        if (
            category in self.tools_by_category
            and tool_id in self.tools_by_category[category]
        ):
            self.tools_by_category[category].remove(tool_id)
            if not self.tools_by_category[category]:
                del self.tools_by_category[category]

    def _update_tag_index(self, tag: str, tool_id: str):
        """Update the tag index."""
        if tag not in self.tools_by_tags:
            self.tools_by_tags[tag] = []
        if tool_id not in self.tools_by_tags[tag]:
            self.tools_by_tags[tag].append(tool_id)

    def _remove_from_tag_index(self, tag: str, tool_id: str):
        """Remove from tag index."""
        if tag in self.tools_by_tags and tool_id in self.tools_by_tags[tag]:
            self.tools_by_tags[tag].remove(tool_id)
            if not self.tools_by_tags[tag]:
                del self.tools_by_tags[tag]

    def has_tool(self, identifier: str) -> bool:
        """Check if a tool exists by ID, name, or alias.

        Args:
            identifier: Tool ID, name, or alias

        Returns:
            True if tool exists, False otherwise
        """
        return self.get_tool(identifier) is not None
