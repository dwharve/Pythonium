# Pythonium Developer Guide

**Version**: 0.1.1  
**Updated**: June 30, 2025

## Overview

This guide provides comprehensive information for developers who want to extend, customize, or contribute to the Pythonium MCP Server project.

---

##  **Architecture Overview**

### System Design

Pythonium follows a modular, plugin-based architecture designed for extensibility and maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client                               │
└─────────────────┬───────────────────────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────────────────────┐
│                 MCP Server                                  │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │   Session   │  Transport  │  Handlers   │  Protocol   │  │
│  │ Management  │    Layer    │             │   Layer     │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │ Internal API
┌─────────────────▼───────────────────────────────────────────┐
│                Manager Layer                                │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │    Config   │   Plugin    │  Resource   │  Security   │  │
│  │   Manager   │   Manager   │   Manager   │   Manager   │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │ Manager API
┌─────────────────▼───────────────────────────────────────────┐
│                  Tools Layer                                │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │ File System │    Data     │   Network   │   System    │  │
│  │    Tools    │ Processing  │    Tools    │    Tools    │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │ Common API
┌─────────────────▼───────────────────────────────────────────┐
│                Common Layer                                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │ Base Classes│   Events    │   Cache     │ Utilities   │  │
│  │  & Plugins  │   System    │   System    │             │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Modularity**: Each component is independently testable and replaceable
2. **Plugin Architecture**: Easy extension through plugins and tools
3. **Dependency Injection**: Loose coupling between components
4. **Event-Driven**: Asynchronous communication between components
5. **Configuration-Driven**: Behavior controlled through configuration
6. **Security-First**: Built-in authentication and authorization

---

##  **Development Environment Setup**

### Prerequisites

- Python 3.11+
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

1. **Clone the Repository**
```bash
git clone https://github.com/dwharve/pythonium.git
cd pythonium
```

2. **Create Virtual Environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix/macOS
source venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Install in Development Mode**
```bash
pip install -e .
```

5. **Run Tests**
```bash
pytest tests/ -v
```

### Development Tools

- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Linting**: flake8, black, isort
- **Type Checking**: mypy
- **Documentation**: sphinx (planned)

---

##  **Creating Custom Tools**

### Tool Development Workflow

1. Define tool requirements and interface
2. Create tool class extending `BaseTool`
3. Implement required methods
4. Add parameter validation
5. Write comprehensive tests
6. Register tool with the system

### Basic Tool Template

```python
from typing import Dict, Any, Optional
from pythonium.tools.base import BaseTool, ToolResult, ToolError

class MyCustomTool(BaseTool):
    """
    Custom tool for [describe functionality].
    """
    
    def get_name(self) -> str:
        """Return the tool name."""
        return "my-custom-tool"
    
    def get_description(self) -> str:
        """Return the tool description."""
        return "Performs custom operations on data"
    
    def get_parameters(self) -> Dict[str, Any]:
        """Return the parameter schema."""
        return {
            "input_data": {
                "type": "string",
                "description": "Input data to process",
                "required": True
            },
            "operation": {
                "type": "string",
                "description": "Operation to perform",
                "enum": ["transform", "validate", "analyze"],
                "default": "transform"
            },
            "options": {
                "type": "object",
                "description": "Additional options",
                "properties": {
                    "case_sensitive": {"type": "boolean", "default": False},
                    "max_length": {"type": "integer", "minimum": 1}
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        try:
            # Extract and validate parameters
            input_data = kwargs.get("input_data")
            operation = kwargs.get("operation", "transform")
            options = kwargs.get("options", {})
            
            # Validate required parameters
            if not input_data:
                raise ToolError("input_data is required")
            
            # Perform the operation
            result = await self._perform_operation(input_data, operation, options)
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": operation,
                    "input_length": len(input_data),
                    "options": options
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )
    
    async def _perform_operation(
        self, 
        input_data: str, 
        operation: str, 
        options: Dict[str, Any]
    ) -> Any:
        """Internal method to perform the actual operation."""
        if operation == "transform":
            return await self._transform_data(input_data, options)
        elif operation == "validate":
            return await self._validate_data(input_data, options)
        elif operation == "analyze":
            return await self._analyze_data(input_data, options)
        else:
            raise ToolError(f"Unknown operation: {operation}")
    
    async def _transform_data(self, data: str, options: Dict[str, Any]) -> str:
        """Transform the input data."""
        # Implementation details
        case_sensitive = options.get("case_sensitive", False)
        if not case_sensitive:
            data = data.lower()
        return f"transformed: {data}"
    
    async def _validate_data(self, data: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the input data."""
        max_length = options.get("max_length")
        is_valid = True
        errors = []
        
        if max_length and len(data) > max_length:
            is_valid = False
            errors.append(f"Data exceeds maximum length of {max_length}")
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "length": len(data)
        }
    
    async def _analyze_data(self, data: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the input data."""
        return {
            "length": len(data),
            "word_count": len(data.split()),
            "character_frequency": {char: data.count(char) for char in set(data)}
        }
```

### Advanced Tool Features

#### Async Operations
```python
import asyncio
import aiohttp

class AsyncHTTPTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.text()
                return ToolResult(success=True, data=data)
```

#### Streaming Results
```python
from typing import AsyncGenerator

class StreamingTool(BaseTool):
    async def execute_streaming(self, **kwargs) -> AsyncGenerator[ToolResult, None]:
        data_source = kwargs.get("data_source")
        
        async for chunk in self._process_data_stream(data_source):
            yield ToolResult(
                success=True,
                data=chunk,
                metadata={"chunk_index": chunk.index}
            )
```

#### Resource Management
```python
class ResourceAwareTool(BaseTool):
    def __init__(self, resource_manager):
        super().__init__()
        self.resource_manager = resource_manager
    
    async def execute(self, **kwargs) -> ToolResult:
        # Check resource availability
        if not await self.resource_manager.check_memory_availability(1024 * 1024):
            raise ToolError("Insufficient memory")
        
        # Perform operation with resource tracking
        with self.resource_manager.track_memory():
            result = await self._memory_intensive_operation(kwargs)
            return ToolResult(success=True, data=result)
```

---

## 🔌 **Plugin Development**

### Plugin Architecture

Plugins in Pythonium extend the core functionality by:
- Adding new tools
- Providing custom managers
- Extending the event system
- Adding new transport protocols

### Basic Plugin Structure

```python
from pythonium.common.base import BasePlugin
from pythonium.tools.base import BaseTool
from typing import List, Dict, Any

class MyPlugin(BasePlugin):
    """
    Example plugin that adds custom functionality.
    """
    
    def get_name(self) -> str:
        return "my-plugin"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Adds custom tools and functionality"
    
    def get_dependencies(self) -> List[str]:
        return ["core-plugin"]  # Optional dependencies
    
    async def initialize(self) -> None:
        """Initialize the plugin."""
        # Register tools
        await self._register_tools()
        
        # Subscribe to events
        await self._setup_event_handlers()
        
        # Initialize resources
        await self._initialize_resources()
    
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        await self._cleanup_resources()
    
    def get_tools(self) -> List[BaseTool]:
        """Return tools provided by this plugin."""
        return [
            MyCustomTool(),
            AnotherCustomTool()
        ]
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Return configuration schema for this plugin."""
        return {
            "api_key": {"type": "string", "required": True},
            "timeout": {"type": "integer", "default": 30},
            "enabled_features": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["feature1", "feature2"]
            }
        }
    
    async def _register_tools(self) -> None:
        """Register plugin tools with the system."""
        from pythonium.managers.registry import get_manager_registry
        
        registry = get_manager_registry()
        tool_manager = registry.get_manager("tool_manager")
        
        for tool in self.get_tools():
            await tool_manager.register_tool(tool)
    
    async def _setup_event_handlers(self) -> None:
        """Set up event handlers."""
        from pythonium.common.events import get_event_bus
        
        event_bus = get_event_bus()
        event_bus.subscribe("tool.executed", self._handle_tool_executed)
        event_bus.subscribe("system.shutdown", self._handle_system_shutdown)
    
    async def _handle_tool_executed(self, event) -> None:
        """Handle tool execution events."""
        tool_name = event.data.get("tool_name")
        if tool_name in [tool.get_name() for tool in self.get_tools()]:
            # Log or process tool execution
            pass
    
    async def _handle_system_shutdown(self, event) -> None:
        """Handle system shutdown events."""
        await self.cleanup()
```

### Plugin Discovery

Plugins are discovered through:

1. **Directory Scanning**: Plugins in `plugins/` directory
2. **Entry Points**: Using setuptools entry points
3. **Configuration**: Explicit plugin lists in configuration

#### Entry Points Setup

```python
# setup.py
setup(
    name="my-pythonium-plugin",
    entry_points={
        "pythonium.plugins": [
            "my_plugin = my_plugin:MyPlugin"
        ]
    }
)
```

### Plugin Configuration

```yaml
# config.yaml
plugins:
  enabled:
    - my-plugin
    - another-plugin
  
  my-plugin:
    api_key: "your-api-key"
    timeout: 60
    enabled_features: ["feature1", "feature3"]
```

---

##  **Manager Development**

### Creating Custom Managers

Managers handle system-level concerns like configuration, resources, and security.

```python
from pythonium.managers.base import BaseManager
from typing import Dict, Any, Optional

class CustomManager(BaseManager):
    """
    Custom manager for handling specific system concerns.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self._resources = {}
    
    async def start(self) -> None:
        """Start the manager."""
        await super().start()
        
        # Initialize manager-specific resources
        await self._initialize_resources()
        
        # Start background tasks
        await self._start_background_tasks()
    
    async def stop(self) -> None:
        """Stop the manager."""
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Clean up resources
        await self._cleanup_resources()
        
        await super().stop()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get manager health status."""
        base_status = await super().get_health_status()
        
        custom_status = {
            "resource_count": len(self._resources),
            "background_tasks_running": self._are_background_tasks_running(),
            "custom_metric": await self._get_custom_metric()
        }
        
        return {**base_status, **custom_status}
    
    # Custom manager methods
    async def custom_operation(self, param: str) -> Any:
        """Perform custom manager operation."""
        if not self.is_running():
            raise RuntimeError("Manager is not running")
        
        # Implementation
        return f"Processed: {param}"
    
    async def _initialize_resources(self) -> None:
        """Initialize manager resources."""
        # Resource initialization logic
        pass
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks."""
        # Background task startup logic
        pass
    
    async def _stop_background_tasks(self) -> None:
        """Stop background tasks."""
        # Background task cleanup logic
        pass
    
    async def _cleanup_resources(self) -> None:
        """Clean up manager resources."""
        self._resources.clear()
    
    def _are_background_tasks_running(self) -> bool:
        """Check if background tasks are running."""
        # Implementation
        return True
    
    async def _get_custom_metric(self) -> float:
        """Get custom metric value."""
        # Implementation
        return 0.95
```

### Manager Registration

```python
# Register custom manager
from pythonium.managers.registry import get_manager_registry

registry = get_manager_registry()
registry.register_manager("custom_manager", CustomManager)
```

---

##  **Testing Guidelines**

### Test Structure

Follow the existing test structure:

```
tests/
├── common/          # Common package tests
├── managers/        # Manager tests
├── tools/          # Tool tests
├── mcp/            # MCP package tests
├── integration/    # Integration tests
├── e2e/            # End-to-end tests
└── performance/    # Performance tests
```

### Unit Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock
from pythonium.tools.my_tool import MyCustomTool

class TestMyCustomTool:
    """Test suite for MyCustomTool."""
    
    @pytest.fixture
    def tool(self):
        """Create tool instance for testing."""
        return MyCustomTool()
    
    def test_get_name(self, tool):
        """Test tool name."""
        assert tool.get_name() == "my-custom-tool"
    
    def test_get_parameters(self, tool):
        """Test parameter schema."""
        params = tool.get_parameters()
        assert "input_data" in params
        assert params["input_data"]["required"] is True
    
    @pytest.mark.asyncio
    async def test_execute_success(self, tool):
        """Test successful tool execution."""
        result = await tool.execute(
            input_data="test data",
            operation="transform"
        )
        
        assert result.success is True
        assert "transformed: test data" in result.data
    
    @pytest.mark.asyncio
    async def test_execute_missing_parameter(self, tool):
        """Test execution with missing parameter."""
        result = await tool.execute(operation="transform")
        
        assert result.success is False
        assert "input_data is required" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_with_options(self, tool):
        """Test execution with options."""
        result = await tool.execute(
            input_data="TEST DATA",
            operation="transform",
            options={"case_sensitive": True}
        )
        
        assert result.success is True
        assert "transformed: TEST DATA" in result.data
```

### Integration Testing

```python
import pytest
from pythonium.mcp.server import MCPServer
from pythonium.mcp.config import ServerConfig, TransportConfig

class TestMCPIntegration:
    """Integration tests for MCP server."""
    
    @pytest.fixture
    async def server(self):
        """Create test server."""
        config = ServerConfig(
            transport=TransportConfig(type="stdio")
        )
        server = MCPServer(config)
        await server.start()
        yield server
        await server.stop()
    
    @pytest.mark.asyncio
    async def test_tool_registration_and_execution(self, server):
        """Test tool registration and execution."""
        from pythonium.tools.my_tool import MyCustomTool
        
        tool = MyCustomTool()
        server.register_tool(tool)
        
        # Test tool is registered
        tools = server.list_tools()
        assert "my-custom-tool" in tools
        
        # Test tool execution through server
        result = await server.execute_tool(
            "my-custom-tool",
            {"input_data": "test"}
        )
        assert result.success is True
```

### Mock Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pythonium.managers.custom_manager import CustomManager

class TestCustomManager:
    """Test suite for CustomManager."""
    
    @pytest.fixture
    def manager(self):
        """Create manager instance."""
        return CustomManager({"setting": "value"})
    
    @pytest.mark.asyncio
    async def test_start_initializes_resources(self, manager):
        """Test manager start initializes resources."""
        with patch.object(manager, '_initialize_resources') as mock_init:
            await manager.start()
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_custom_operation_requires_running_manager(self, manager):
        """Test custom operation requires running manager."""
        with pytest.raises(RuntimeError, match="Manager is not running"):
            await manager.custom_operation("test")
```

### Performance Testing

```python
import pytest
import time
import asyncio
from pythonium.tools.performance_tool import PerformanceTool

class TestPerformance:
    """Performance tests."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_performance(self):
        """Test tool execution performance."""
        tool = PerformanceTool()
        
        # Measure execution time
        start_time = time.time()
        
        tasks = [
            tool.execute(data=f"test_{i}")
            for i in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert performance requirements
        assert execution_time < 5.0  # Should complete in under 5 seconds
        assert all(result.success for result in results)
```

---

## 🔐 **Security Considerations**

### Input Validation

Always validate and sanitize inputs:

```python
from pythonium.common.validation import validate_input, sanitize_string

class SecureTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        # Validate input parameters
        file_path = kwargs.get("file_path")
        if not validate_input(file_path, "file_path"):
            raise ToolError("Invalid file path")
        
        # Sanitize strings
        user_input = sanitize_string(kwargs.get("user_input", ""))
        
        # Continue with secure execution
        pass
```

### Permission Checking

```python
class RestrictedTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        # Check user permissions
        user_context = kwargs.get("_user_context")
        if not await self._check_permission(user_context, "tool.execute"):
            raise SecurityError("Insufficient permissions")
        
        # Continue with execution
        pass
    
    async def _check_permission(self, user_context, permission) -> bool:
        from pythonium.managers.registry import get_manager_registry
        
        registry = get_manager_registry()
        security_manager = registry.get_manager("security_manager")
        
        return await security_manager.check_permission(user_context, permission)
```

### Resource Limits

```python
class ResourceLimitedTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        # Check resource limits
        resource_manager = await self._get_resource_manager()
        
        if not await resource_manager.check_memory_limit():
            raise ToolError("Memory limit exceeded")
        
        if not await resource_manager.check_rate_limit(kwargs.get("_user_id")):
            raise ToolError("Rate limit exceeded")
        
        # Continue with execution
        pass
```

---

## 📈 **Performance Optimization**

### Async Best Practices

```python
import asyncio
from typing import List

class OptimizedTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        # Use asyncio.gather for concurrent operations
        tasks = [
            self._process_item(item)
            for item in kwargs.get("items", [])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        successful_results = [
            result for result in results
            if not isinstance(result, Exception)
        ]
        
        return ToolResult(success=True, data=successful_results)
    
    async def _process_item(self, item):
        """Process individual item asynchronously."""
        # Async processing logic
        await asyncio.sleep(0.1)  # Simulate work
        return f"processed: {item}"
```

### Caching Strategies

```python
from pythonium.common.cache import CacheManager

class CachedTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.cache = CacheManager()
    
    async def execute(self, **kwargs) -> ToolResult:
        # Create cache key
        cache_key = self._create_cache_key(kwargs)
        
        # Try to get from cache
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return ToolResult(
                success=True,
                data=cached_result,
                metadata={"from_cache": True}
            )
        
        # Compute result
        result = await self._compute_result(kwargs)
        
        # Cache result
        await self.cache.set(cache_key, result, ttl=300)
        
        return ToolResult(
            success=True,
            data=result,
            metadata={"from_cache": False}
        )
```

### Memory Management

```python
import gc
from contextlib import asynccontextmanager

class MemoryEfficientTool(BaseTool):
    @asynccontextmanager
    async def _memory_context(self):
        """Context manager for memory-intensive operations."""
        try:
            # Pre-operation cleanup
            gc.collect()
            yield
        finally:
            # Post-operation cleanup
            gc.collect()
    
    async def execute(self, **kwargs) -> ToolResult:
        async with self._memory_context():
            # Memory-intensive operation
            large_data = await self._process_large_dataset(kwargs)
            result = self._extract_summary(large_data)
            
            # Clear large data before returning
            del large_data
            
            return ToolResult(success=True, data=result)
```

---

##  **Deployment Guidelines**

### Production Configuration

```yaml
# production.yaml
name: "Pythonium Production Server"

transport:
  type: "http"
  host: "0.0.0.0"
  port: 8080
  ssl_enabled: true
  ssl_cert_file: "/etc/ssl/certs/pythonium.crt"
  ssl_key_file: "/etc/ssl/private/pythonium.key"

security:
  authentication_method: "api_key"
  api_keys:
    - "${API_KEY_1}"
    - "${API_KEY_2}"
  rate_limit_enabled: true
  rate_limit_requests_per_minute: 1000

performance:
  max_concurrent_requests: 500
  request_timeout_seconds: 120

logging:
  level: "warning"
  log_file: "/var/log/pythonium/server.log"
  enable_request_logging: false

tools:
  dangerous_tools_enabled: false
  tool_timeout_seconds: 60
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY pythonium/ ./pythonium/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 pythonium
USER pythonium

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start server
CMD ["python", "-m", "pythonium", "--config", "config/production.yaml"]
```

### Monitoring Setup

```python
# monitoring.py
import time
import psutil
from pythonium.common.events import get_event_bus

class PerformanceMonitor:
    def __init__(self):
        self.event_bus = get_event_bus()
        self.metrics = {}
    
    async def start_monitoring(self):
        """Start performance monitoring."""
        self.event_bus.subscribe("tool.executed", self._track_tool_performance)
        self.event_bus.subscribe("manager.health", self._track_manager_health)
        
        # Start metric collection loop
        asyncio.create_task(self._collect_system_metrics())
    
    async def _track_tool_performance(self, event):
        """Track tool execution performance."""
        tool_name = event.data.get("tool_name")
        execution_time = event.data.get("execution_time")
        
        if tool_name not in self.metrics:
            self.metrics[tool_name] = []
        
        self.metrics[tool_name].append(execution_time)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics."""
        while True:
            # Collect CPU and memory usage
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            # Publish metrics
            await self.event_bus.publish(Event(
                "system.metrics",
                {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "timestamp": time.time()
                }
            ))
            
            await asyncio.sleep(30)  # Collect every 30 seconds
```

---

## 🤝 **Contributing**

### Development Workflow

1. **Fork the Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Make Changes**
   - Follow coding standards
   - Add comprehensive tests
   - Update documentation
4. **Run Tests**
   ```bash
   pytest tests/ -v
   flake8 pythonium/
   mypy pythonium/
   ```
5. **Submit Pull Request**

### Code Standards

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations for all public APIs
- **Docstrings**: Document all classes and methods
- **Error Handling**: Comprehensive error handling and logging
- **Testing**: Achieve >90% test coverage

### Pull Request Guidelines

- Clear, descriptive title
- Detailed description of changes
- Link to related issues
- Include tests for new functionality
- Update documentation as needed

---

For additional support and advanced topics, see:
- [API Documentation](API_DOCUMENTATION.md)
- [User Guide](USER_GUIDE.md)
- [AI Agent Rules](AI_AGENT_RULES.md)
