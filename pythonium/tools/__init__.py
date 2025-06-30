"""
Pythonium Tools Package

This package provides a comprehensive set of tools for various operations
including file system manipulation, data processing, network operations,
and system interactions.

The tools package is built on a common framework that provides:
- Parameter validation and type checking
- Execution context management
- Standardized result formatting
- Comprehensive error handling
- Tool metadata and discovery
"""

# Import tool management
from pythonium.managers.tools.registry import ToolRegistry

# Import tool base classes
from .base import (
    BaseTool,
    ParameterType,
    ToolContext,
    ToolError,
    ToolExecutionError,
    ToolMetadata,
    ToolParameter,
    ToolValidationError,
)

# Import filesystem tools
from .filesystem import (
    CreateFileTool,
    DeleteFileTool,
    FindFilesTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)

# Import network tools
from .network import (
    GraphQLTool,
    HtmlParserTool,
    HttpClientTool,
    RestApiTool,
    WebCrawlerTool,
    WebScrapingTool,
    WebSearchTool,
)

# Import system tools
from .system import (
    CommandHistoryTool,
    DiskUsageTool,
    ExecuteCommandTool,
    NetworkInfoTool,
    PortMonitorTool,
    ProcessManagerTool,
    ServiceStatusTool,
    ShellEnvironmentTool,
    SystemInfoTool,
    SystemLoadTool,
    WhichCommandTool,
)

__version__ = "0.1.0"

__all__ = [
    # Base classes
    "BaseTool",
    "ToolMetadata",
    "ToolParameter",
    "ParameterType",
    "ToolContext",
    # Exceptions
    "ToolError",
    "ToolValidationError",
    "ToolExecutionError",
    # Filesystem tools
    "ReadFileTool",
    "WriteFileTool",
    "DeleteFileTool",
    "CreateFileTool",
    "SearchFilesTool",
    "FindFilesTool",
    # Network tools
    "HttpClientTool",
    "RestApiTool",
    "GraphQLTool",
    "WebScrapingTool",
    "HtmlParserTool",
    "WebCrawlerTool",
    "WebSearchTool",
    # System tools
    "ProcessManagerTool",
    "SystemInfoTool",
    "DiskUsageTool",
    "NetworkInfoTool",
    "ExecuteCommandTool",
    "WhichCommandTool",
    "CommandHistoryTool",
    "ShellEnvironmentTool",
    "ServiceStatusTool",
    "PortMonitorTool",
    "SystemLoadTool",
    # Tool registry
    "ToolRegistry",
]
