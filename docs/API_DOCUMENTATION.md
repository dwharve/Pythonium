# Pythonium API Documentation

**Version**: 0.1.1  
**Updated**: June 30, 2025

## Overview

This document provides comprehensive API documentation for the Pythonium MCP Server, including all packages, classes, and methods available for developers.

---

##  **Package Structure**

```
pythonium/
├── common/          # Common utilities and base classes
├── managers/        # Core system managers
├── tools/          # Tool implementations and management
└── mcp/            # MCP protocol implementation
```

---

##  **Common Package API**

### Base Classes

#### `BasePlugin`
Abstract base class for all plugins in the Pythonium system.

```python
from pythonium.common.base import BasePlugin

class MyPlugin(BasePlugin):
    def get_name(self) -> str:
        return "my-plugin"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    async def initialize(self) -> None:
        # Plugin initialization logic
        pass
    
    async def cleanup(self) -> None:
        # Plugin cleanup logic
        pass
```

**Methods:**
- `get_name() -> str`: Returns the plugin name
- `get_version() -> str`: Returns the plugin version
- `get_description() -> str`: Returns the plugin description
- `get_dependencies() -> List[str]`: Returns list of dependency names
- `async initialize() -> None`: Initialize the plugin
- `async cleanup() -> None`: Clean up plugin resources
- `is_initialized() -> bool`: Check if plugin is initialized

#### `BaseManager`
Abstract base class for system managers.

```python
from pythonium.managers.base import BaseManager

class MyManager(BaseManager):
    async def start(self) -> None:
        # Manager startup logic
        pass
    
    async def stop(self) -> None:
        # Manager shutdown logic
        pass
    
    async def get_health_status(self) -> Dict[str, Any]:
        return {"status": "healthy"}
```

**Methods:**
- `async start() -> None`: Start the manager
- `async stop() -> None`: Stop the manager
- `async restart() -> None`: Restart the manager
- `async get_health_status() -> Dict[str, Any]`: Get health information
- `get_metrics() -> Dict[str, Any]`: Get performance metrics
- `is_running() -> bool`: Check if manager is running

### Event System

#### `EventBus`
Central event bus for inter-component communication.

```python
from pythonium.common.events import EventBus, Event

# Create event bus
bus = EventBus()

# Subscribe to events
async def handle_event(event: Event):
    print(f"Received: {event.type}")

bus.subscribe("user.login", handle_event)

# Publish events
await bus.publish(Event("user.login", {"user_id": "123"}))
```

**Methods:**
- `subscribe(event_type: str, handler: Callable) -> str`: Subscribe to events
- `unsubscribe(subscription_id: str) -> None`: Remove subscription
- `async publish(event: Event) -> None`: Publish an event
- `get_subscribers(event_type: str) -> List[str]`: Get event subscribers

### Caching

#### `CacheManager`
Multi-level caching system with TTL support.

```python
from pythonium.common.cache import CacheManager

cache = CacheManager()

# Store and retrieve data
await cache.set("key", "value", ttl=300)
value = await cache.get("key")

# Batch operations
await cache.set_many({"key1": "value1", "key2": "value2"})
values = await cache.get_many(["key1", "key2"])
```

**Methods:**
- `async get(key: str) -> Any`: Get cached value
- `async set(key: str, value: Any, ttl: int = None) -> None`: Set cached value
- `async delete(key: str) -> None`: Delete cached value
- `async clear() -> None`: Clear all cache entries
- `async get_many(keys: List[str]) -> Dict[str, Any]`: Get multiple values
- `async set_many(mapping: Dict[str, Any], ttl: int = None) -> None`: Set multiple values

---

##  **Managers Package API**

### Configuration Manager

#### `ConfigurationManager`
Manages configuration loading, validation, and hot-reload.

```python
from pythonium.managers.config_manager import ConfigurationManager

config_manager = ConfigurationManager()

# Load configuration
config = await config_manager.load_config("config.yaml")

# Get configuration values
db_host = config_manager.get("database.host", "localhost")
debug = config_manager.get_bool("debug", False)

# Watch for changes
config_manager.watch_file("config.yaml")
```

**Methods:**
- `async load_config(file_path: str) -> Dict[str, Any]`: Load configuration file
- `get(key: str, default: Any = None) -> Any`: Get configuration value
- `get_bool(key: str, default: bool = False) -> bool`: Get boolean value
- `get_int(key: str, default: int = 0) -> int`: Get integer value
- `set(key: str, value: Any) -> None`: Set configuration value
- `validate_config() -> List[str]`: Validate configuration
- `watch_file(file_path: str) -> None`: Watch for file changes
- `reload() -> None`: Reload configuration

### Plugin Manager

#### `PluginManager`
Handles plugin discovery, loading, and lifecycle management.

```python
from pythonium.managers.plugin_manager import PluginManager

plugin_manager = PluginManager()

# Discover and load plugins
await plugin_manager.discover_plugins("./plugins")
await plugin_manager.load_plugin("my-plugin")

# Get plugin information
plugin = plugin_manager.get_plugin("my-plugin")
plugins = plugin_manager.list_plugins()
```

**Methods:**
- `async discover_plugins(directory: str) -> List[str]`: Discover available plugins
- `async load_plugin(name: str) -> BasePlugin`: Load a specific plugin
- `async unload_plugin(name: str) -> None`: Unload a plugin
- `get_plugin(name: str) -> BasePlugin`: Get loaded plugin instance
- `list_plugins() -> List[str]`: List all loaded plugins
- `is_plugin_loaded(name: str) -> bool`: Check if plugin is loaded

### Resource Manager

#### `ResourceManager`
Manages system resources, connection pools, and memory usage.

```python
from pythonium.managers.resource_manager import ResourceManager

resource_manager = ResourceManager()

# Get connection pool
pool = await resource_manager.get_connection_pool("database")

# Monitor memory usage
memory_stats = resource_manager.get_memory_stats()
```

**Methods:**
- `async get_connection_pool(name: str) -> ConnectionPool`: Get connection pool
- `async create_pool(name: str, config: Dict[str, Any]) -> ConnectionPool`: Create new pool
- `get_memory_stats() -> Dict[str, int]`: Get memory usage statistics
- `set_memory_limit(limit_bytes: int) -> None`: Set memory limit
- `cleanup_resources() -> None`: Clean up unused resources

### Security Manager

#### `SecurityManager`
Handles authentication, authorization, and security policies.

```python
from pythonium.managers.security_manager import SecurityManager

security_manager = SecurityManager()

# Authentication
token = await security_manager.authenticate(username, password)
user = await security_manager.validate_token(token)

# Authorization
allowed = await security_manager.check_permission(user, "tool.execute")
```

**Methods:**
- `async authenticate(username: str, password: str) -> str`: Authenticate user
- `async validate_token(token: str) -> Dict[str, Any]`: Validate authentication token
- `async check_permission(user: Dict, permission: str) -> bool`: Check user permissions
- `async create_api_key(user_id: str) -> str`: Create API key
- `async revoke_api_key(api_key: str) -> None`: Revoke API key
- `get_rate_limit(user_id: str) -> int`: Get rate limit for user

---

##  **Tools Package API**

### Base Tool

#### `BaseTool`
Abstract base class for all tools.

```python
from pythonium.tools.base import BaseTool, ToolResult

class MyTool(BaseTool):
    def get_name(self) -> str:
        return "my-tool"
    
    def get_description(self) -> str:
        return "My custom tool"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "input": {"type": "string", "description": "Input text"}
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        input_text = kwargs.get("input", "")
        result = f"Processed: {input_text}"
        return ToolResult(success=True, data=result)
```

**Methods:**
- `get_name() -> str`: Get tool name
- `get_description() -> str`: Get tool description
- `get_parameters() -> Dict[str, Any]`: Get parameter schema
- `async execute(**kwargs) -> ToolResult`: Execute the tool
- `validate_parameters(params: Dict[str, Any]) -> bool`: Validate parameters

### File System Tools

#### `FileOperations`
File system operations tool.

```python
from pythonium.tools.filesystem.file_ops import FileOperations

file_tool = FileOperations()

# Read file
result = await file_tool.execute(action="read", path="/path/to/file.txt")

# Write file
result = await file_tool.execute(
    action="write", 
    path="/path/to/output.txt", 
    content="Hello, World!"
)

# List directory
result = await file_tool.execute(action="list", path="/path/to/directory")
```

### Data Processing Tools

#### `JSONProcessor`
JSON data processing tool.

```python
from pythonium.tools.data_processing.json_xml_tools import JSONProcessor

json_tool = JSONProcessor()

# Parse JSON
result = await json_tool.execute(
    action="parse", 
    data='{"name": "John", "age": 30}'
)

# Query JSON
result = await json_tool.execute(
    action="query", 
    data=json_data, 
    query="$.name"
)
```

### Network Tools

#### `HTTPClient`
HTTP client operations tool.

```python
from pythonium.tools.network.http_client import HTTPClient

http_tool = HTTPClient()

# GET request
result = await http_tool.execute(
    method="GET", 
    url="https://api.example.com/data"
)

# POST request
result = await http_tool.execute(
    method="POST", 
    url="https://api.example.com/data", 
    data={"key": "value"}
)
```

---

##  **MCP Package API**

### MCP Server

#### `MCPServer`
Main MCP server implementation.

```python
from pythonium.mcp.server import MCPServer
from pythonium.mcp.config import ServerConfig, TransportConfig

# Create configuration
transport_config = TransportConfig(type="stdio")
config = ServerConfig(transport=transport_config)

# Create and start server
server = MCPServer(config)
await server.start()

# Register tools
server.register_tool(my_tool)

# Stop server
await server.stop()
```

**Methods:**
- `async start() -> None`: Start the MCP server
- `async stop() -> None`: Stop the MCP server
- `register_tool(tool: BaseTool) -> None`: Register a tool
- `unregister_tool(tool_name: str) -> None`: Unregister a tool
- `list_tools() -> List[str]`: List registered tools
- `get_server_info() -> Dict[str, Any]`: Get server information

### Configuration

#### `ServerConfig`
Complete MCP server configuration.

```python
from pythonium.mcp.config import (
    ServerConfig, TransportConfig, SecurityConfig, 
    PerformanceConfig, LoggingConfig
)

# Create configuration
config = ServerConfig(
    name="My MCP Server",
    transport=TransportConfig(type="http", host="localhost", port=8080),
    security=SecurityConfig(authentication_method="api_key"),
    performance=PerformanceConfig(max_concurrent_requests=50),
    logging=LoggingConfig(level="info", log_file="server.log")
)
```

### Session Management

#### `SessionManager`
Manages client sessions and state.

```python
from pythonium.mcp.session import SessionManager

session_manager = SessionManager()

# Create session
session_id = session_manager.create_session()

# Get session
session = session_manager.get_session(session_id)

# Update session state
session_manager.update_session(session_id, {"user_id": "123"})

# Clean up session
session_manager.cleanup_session(session_id)
```

---

##  **Error Handling**

### Common Exceptions

```python
from pythonium.common.exceptions import (
    PythoniumError,
    ConfigurationError,
    PluginError,
    ToolError,
    SecurityError
)

try:
    # Some operation
    pass
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except ToolError as e:
    print(f"Tool execution error: {e}")
except PythoniumError as e:
    print(f"General error: {e}")
```

### Error Codes

| Code | Exception | Description |
|------|-----------|-------------|
| 1000 | `ConfigurationError` | Configuration validation failed |
| 2000 | `PluginError` | Plugin loading or execution error |
| 3000 | `ToolError` | Tool execution error |
| 4000 | `SecurityError` | Authentication or authorization error |
| 5000 | `NetworkError` | Network operation error |

---

##  **Performance and Monitoring**

### Metrics Collection

```python
from pythonium.common.base import MetricsCollector

metrics = MetricsCollector()

# Record metrics
metrics.increment("requests.count")
metrics.gauge("memory.usage", memory_bytes)
metrics.timer("operation.duration", duration_ms)

# Get metrics
stats = metrics.get_all_metrics()
```

### Health Checks

```python
# Check system health
health_status = await manager_registry.get_health_status()

# Example response
{
    "status": "healthy",
    "components": {
        "config_manager": {"status": "healthy", "uptime": 3600},
        "plugin_manager": {"status": "healthy", "plugins_loaded": 5},
        "resource_manager": {"status": "warning", "memory_usage": 0.85}
    }
}
```

---

##  **Integration Examples**

### Basic MCP Server Setup

```python
import asyncio
from pythonium.mcp.server import MCPServer
from pythonium.mcp.config import ServerConfig, TransportConfig
from pythonium.tools.filesystem.file_ops import FileOperations

async def main():
    # Create configuration
    config = ServerConfig(
        name="File Operations Server",
        transport=TransportConfig(type="stdio")
    )
    
    # Create server
    server = MCPServer(config)
    
    # Register tools
    server.register_tool(FileOperations())
    
    # Start server
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Tool Development

```python
from pythonium.tools.base import BaseTool, ToolResult
from typing import Dict, Any

class WeatherTool(BaseTool):
    def get_name(self) -> str:
        return "weather"
    
    def get_description(self) -> str:
        return "Get weather information for a location"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "location": {
                "type": "string",
                "description": "City name or coordinates",
                "required": True
            },
            "units": {
                "type": "string",
                "description": "Temperature units (celsius/fahrenheit)",
                "default": "celsius"
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        location = kwargs.get("location")
        units = kwargs.get("units", "celsius")
        
        # Weather API call logic here
        weather_data = await self._fetch_weather(location, units)
        
        return ToolResult(
            success=True,
            data=weather_data,
            metadata={"location": location, "units": units}
        )
    
    async def _fetch_weather(self, location: str, units: str) -> Dict[str, Any]:
        # Implementation details
        return {"temperature": 20, "condition": "sunny"}
```

---

##  **Configuration Reference**

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONIUM_CONFIG_FILE` | Path to configuration file | `config.yaml` |
| `PYTHONIUM_LOG_LEVEL` | Logging level | `INFO` |
| `PYTHONIUM_DEBUG` | Enable debug mode | `False` |
| `PYTHONIUM_PLUGINS_DIR` | Plugin directory | `./plugins` |

### Configuration File Format

```yaml
# config.yaml
name: "Pythonium MCP Server"
version: "0.1.1"

transport:
  type: "stdio"
  # For HTTP/WebSocket
  # host: "localhost"
  # port: 8080

security:
  authentication_method: "none"
  # api_keys: ["key1", "key2"]
  # rate_limit_enabled: true

performance:
  max_concurrent_requests: 100
  request_timeout_seconds: 300

logging:
  level: "info"
  log_file: "pythonium.log"
  enable_request_logging: true

tools:
  enable_tool_execution: true
  tool_timeout_seconds: 300
  dangerous_tools_enabled: false
```

---

For more detailed examples and advanced usage patterns, see the [Developer Guide](DEVELOPER_GUIDE.md) and [User Guide](USER_GUIDE.md).
