# Tool Development Guide

**Version**: 0.1.1  
**Updated**: June 30, 2025

## Overview

This guide provides step-by-step instructions for creating, testing, and deploying custom tools for the Pythonium MCP Server. Whether you're extending functionality or creating domain-specific tools, this guide will help you build robust, efficient tools.

---

## 🎯 **Quick Start**

### 1. Basic Tool Creation

Create a simple text processing tool:

```python
# my_text_tool.py
from pythonium.tools.base import BaseTool, ToolResult
from typing import Dict, Any

class TextProcessorTool(BaseTool):
    def get_name(self) -> str:
        return "text-processor"
    
    def get_description(self) -> str:
        return "Processes text with various operations"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "text": {
                "type": "string",
                "description": "Text to process",
                "required": True
            },
            "operation": {
                "type": "string",
                "description": "Operation to perform",
                "enum": ["uppercase", "lowercase", "reverse", "count_words"],
                "default": "uppercase"
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        text = kwargs.get("text")
        operation = kwargs.get("operation", "uppercase")
        
        if operation == "uppercase":
            result = text.upper()
        elif operation == "lowercase":
            result = text.lower()
        elif operation == "reverse":
            result = text[::-1]
        elif operation == "count_words":
            result = {"word_count": len(text.split())}
        else:
            return ToolResult(success=False, error=f"Unknown operation: {operation}")
        
        return ToolResult(success=True, data=result)
```

### 2. Register and Test

```python
# test_tool.py
import asyncio
from my_text_tool import TextProcessorTool

async def test_tool():
    tool = TextProcessorTool()
    
    # Test basic operation
    result = await tool.execute(text="hello world", operation="uppercase")
    print(f"Result: {result.data}")  # Output: HELLO WORLD
    
    # Test word count
    result = await tool.execute(text="hello world", operation="count_words")
    print(f"Word count: {result.data}")  # Output: {'word_count': 2}

if __name__ == "__main__":
    asyncio.run(test_tool())
```

### 3. Add to MCP Server

```python
# server_setup.py
from pythonium.mcp.server import MCPServer
from pythonium.mcp.config import ServerConfig, TransportConfig
from my_text_tool import TextProcessorTool

async def main():
    # Create server configuration
    config = ServerConfig(
        transport=TransportConfig(type="stdio")
    )
    
    # Create and start server
    server = MCPServer(config)
    
    # Register custom tool
    server.register_tool(TextProcessorTool())
    
    # Start server
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

---

##  **Tool Architecture**

### Tool Lifecycle

```
1. Tool Registration
   ↓
2. Parameter Validation
   ↓
3. Execution Request
   ↓
4. Context Setup
   ↓
5. Tool Execution
   ↓
6. Result Processing
   ↓
7. Response Return
```

### Base Tool Interface

All tools must inherit from `BaseTool` and implement these methods:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Return unique tool name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return tool description."""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return JSON schema for parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    # Optional methods to override
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_category(self) -> str:
        return "general"
    
    def get_tags(self) -> List[str]:
        return []
    
    async def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Custom parameter validation."""
        return True
    
    async def before_execute(self, **kwargs) -> None:
        """Called before execution."""
        pass
    
    async def after_execute(self, result: ToolResult, **kwargs) -> None:
        """Called after execution."""
        pass
```

---

##  **Parameter Schema Design**

### JSON Schema Format

Use JSON Schema to define tool parameters:

```python
def get_parameters(self) -> Dict[str, Any]:
    return {
        "input_file": {
            "type": "string",
            "description": "Path to input file",
            "required": True,
            "format": "file-path"  # Custom format hint
        },
        "encoding": {
            "type": "string",
            "description": "File encoding",
            "enum": ["utf-8", "ascii", "latin-1"],
            "default": "utf-8"
        },
        "max_size": {
            "type": "integer",
            "description": "Maximum file size in bytes",
            "minimum": 1,
            "maximum": 10485760,  # 10MB
            "default": 1048576    # 1MB
        },
        "options": {
            "type": "object",
            "description": "Additional options",
            "properties": {
                "ignore_errors": {"type": "boolean", "default": False},
                "chunk_size": {"type": "integer", "minimum": 1024}
            },
            "additionalProperties": False
        },
        "filters": {
            "type": "array",
            "description": "Filter patterns",
            "items": {"type": "string"},
            "minItems": 0,
            "maxItems": 10
        }
    }
```

### Parameter Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | `"hello"` |
| `integer` | Whole number | `42` |
| `number` | Decimal number | `3.14` |
| `boolean` | True/false | `true` |
| `array` | List of values | `["a", "b", "c"]` |
| `object` | Key-value mapping | `{"key": "value"}` |

### Advanced Schema Features

```python
{
    "file_path": {
        "type": "string",
        "pattern": r"^[a-zA-Z0-9./\-_]+$",  # Regex validation
        "minLength": 1,
        "maxLength": 255
    },
    "choice": {
        "type": "string",
        "enum": ["option1", "option2", "option3"]
    },
    "conditional": {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"}
        ]
    },
    "complex_object": {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "integer"}
        },
        "required": ["required_field"],
        "additionalProperties": False
    }
}
```

---

##  **Implementation Patterns**

### 1. File Processing Tool

```python
import asyncio
import aiofiles
from pathlib import Path

class FileProcessorTool(BaseTool):
    def get_name(self) -> str:
        return "file-processor"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {"type": "string", "required": True},
            "operation": {
                "type": "string",
                "enum": ["read", "size", "hash", "metadata"],
                "required": True
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        file_path = Path(kwargs["file_path"])
        operation = kwargs["operation"]
        
        # Validate file exists and is accessible
        if not await self._validate_file(file_path):
            return ToolResult(
                success=False,
                error=f"File not accessible: {file_path}"
            )
        
        try:
            if operation == "read":
                content = await self._read_file(file_path)
                return ToolResult(success=True, data=content)
            
            elif operation == "size":
                size = file_path.stat().st_size
                return ToolResult(success=True, data={"size_bytes": size})
            
            elif operation == "hash":
                file_hash = await self._calculate_hash(file_path)
                return ToolResult(success=True, data={"sha256": file_hash})
            
            elif operation == "metadata":
                metadata = await self._get_metadata(file_path)
                return ToolResult(success=True, data=metadata)
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Operation failed: {str(e)}"
            )
    
    async def _validate_file(self, file_path: Path) -> bool:
        """Validate file access."""
        return file_path.exists() and file_path.is_file()
    
    async def _read_file(self, file_path: Path) -> str:
        """Read file content asynchronously."""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash."""
        import hashlib
        
        hash_obj = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    async def _get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get file metadata."""
        stat = file_path.stat()
        return {
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "permissions": oct(stat.st_mode)[-3:]
        }
```

### 2. API Integration Tool

```python
import aiohttp
import asyncio
from typing import Optional

class APIClientTool(BaseTool):
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
    
    def get_name(self) -> str:
        return "api-client"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "endpoint": {"type": "string", "required": True},
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE"],
                "default": "GET"
            },
            "headers": {"type": "object", "default": {}},
            "params": {"type": "object", "default": {}},
            "data": {"type": "object", "default": {}}
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        endpoint = kwargs["endpoint"]
        method = kwargs.get("method", "GET")
        headers = kwargs.get("headers", {})
        params = kwargs.get("params", {})
        data = kwargs.get("data", {})
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            session = await self._get_session()
            
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data if data else None,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                
                response_data = {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }
                
                # Try to parse JSON, fall back to text
                try:
                    response_data["data"] = await response.json()
                except:
                    response_data["data"] = await response.text()
                
                return ToolResult(
                    success=response.status < 400,
                    data=response_data,
                    metadata={"method": method, "endpoint": endpoint}
                )
                
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Request timeout after {self.timeout}s"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Request failed: {str(e)}"
            )
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def cleanup(self) -> None:
        """Clean up HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
```

### 3. Database Tool

```python
import asyncpg
from typing import List, Dict

class DatabaseTool(BaseTool):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._pool = None
    
    def get_name(self) -> str:
        return "database-query"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "query": {"type": "string", "required": True},
            "parameters": {"type": "array", "default": []},
            "operation": {
                "type": "string",
                "enum": ["select", "insert", "update", "delete"],
                "default": "select"
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 1000}
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs["query"]
        parameters = kwargs.get("parameters", [])
        operation = kwargs.get("operation", "select")
        limit = kwargs.get("limit")
        
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as connection:
                if operation == "select":
                    # Add LIMIT clause if specified
                    if limit and "LIMIT" not in query.upper():
                        query += f" LIMIT {limit}"
                    
                    rows = await connection.fetch(query, *parameters)
                    result = [dict(row) for row in rows]
                    
                    return ToolResult(
                        success=True,
                        data=result,
                        metadata={
                            "row_count": len(result),
                            "operation": operation
                        }
                    )
                
                else:  # insert, update, delete
                    result = await connection.execute(query, *parameters)
                    
                    # Parse affected rows from result
                    affected_rows = int(result.split()[-1]) if result else 0
                    
                    return ToolResult(
                        success=True,
                        data={"affected_rows": affected_rows},
                        metadata={"operation": operation}
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Database operation failed: {str(e)}"
            )
    
    async def _get_pool(self):
        """Get or create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.connection_string)
        return self._pool
    
    async def cleanup(self) -> None:
        """Clean up database connections."""
        if self._pool:
            await self._pool.close()
```

---

## ⚡ **Advanced Features**

### 1. Streaming Results

For tools that process large datasets or long-running operations:

```python
from typing import AsyncGenerator

class StreamingTool(BaseTool):
    def get_name(self) -> str:
        return "streaming-processor"
    
    async def execute_streaming(self, **kwargs) -> AsyncGenerator[ToolResult, None]:
        """Execute tool with streaming results."""
        data_source = kwargs.get("data_source")
        
        async for chunk in self._process_data_stream(data_source):
            yield ToolResult(
                success=True,
                data=chunk,
                metadata={"streaming": True, "chunk_id": chunk.id}
            )
    
    async def _process_data_stream(self, source):
        """Process data in chunks."""
        # Implementation for streaming data processing
        for i in range(10):
            await asyncio.sleep(0.1)  # Simulate processing
            yield {"id": i, "data": f"chunk_{i}"}
```

### 2. Resource Management

```python
from contextlib import asynccontextmanager

class ResourceManagedTool(BaseTool):
    def __init__(self):
        super().__init__()
        self._resources = {}
    
    @asynccontextmanager
    async def _resource_context(self, resource_type: str):
        """Context manager for resource allocation."""
        resource = await self._allocate_resource(resource_type)
        try:
            yield resource
        finally:
            await self._release_resource(resource)
    
    async def execute(self, **kwargs) -> ToolResult:
        async with self._resource_context("database") as db:
            async with self._resource_context("cache") as cache:
                # Use allocated resources
                result = await self._process_with_resources(db, cache, kwargs)
                return ToolResult(success=True, data=result)
    
    async def _allocate_resource(self, resource_type: str):
        """Allocate a specific resource."""
        # Resource allocation logic
        pass
    
    async def _release_resource(self, resource):
        """Release allocated resource."""
        # Resource cleanup logic
        pass
```

### 3. Error Recovery

```python
import asyncio
from functools import wraps

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for automatic retry on failure."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
            return None
        return wrapper
    return decorator

class ResilientTool(BaseTool):
    @retry_on_failure(max_retries=3, delay=0.5)
    async def _robust_operation(self, data):
        """Operation with automatic retry."""
        # Implementation that might fail
        pass
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            result = await self._robust_operation(kwargs)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Operation failed after retries: {str(e)}"
            )
```

---

## 🧪 **Testing Tools**

### Unit Testing Framework

```python
import pytest
from unittest.mock import AsyncMock, Mock, patch
from my_tool import MyCustomTool

class TestMyCustomTool:
    @pytest.fixture
    def tool(self):
        return MyCustomTool()
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, tool):
        """Test successful tool execution."""
        result = await tool.execute(
            required_param="test_value",
            optional_param="optional"
        )
        
        assert result.success is True
        assert result.data is not None
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_missing_required_parameter(self, tool):
        """Test handling of missing required parameters."""
        result = await tool.execute(optional_param="optional")
        
        assert result.success is False
        assert "required_param" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_parameter_type(self, tool):
        """Test handling of invalid parameter types."""
        result = await tool.execute(
            required_param=123,  # Should be string
            optional_param="optional"
        )
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_with_mocked_dependency(self, tool):
        """Test tool with mocked external dependencies."""
        with patch.object(tool, '_external_service_call') as mock_call:
            mock_call.return_value = {"status": "success"}
            
            result = await tool.execute(required_param="test")
            
            assert result.success is True
            mock_call.assert_called_once()
```

### Integration Testing

```python
import pytest
from pythonium.mcp.server import MCPServer
from pythonium.mcp.config import ServerConfig, TransportConfig

class TestToolIntegration:
    @pytest.fixture
    async def server_with_tool(self):
        """Create test server with tool registered."""
        config = ServerConfig(
            transport=TransportConfig(type="stdio")
        )
        server = MCPServer(config)
        server.register_tool(MyCustomTool())
        
        await server.start()
        yield server
        await server.stop()
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, server_with_tool):
        """Test tool is properly registered."""
        tools = server_with_tool.list_tools()
        assert "my-custom-tool" in tools
    
    @pytest.mark.asyncio
    async def test_tool_execution_through_server(self, server_with_tool):
        """Test tool execution through MCP server."""
        result = await server_with_tool.execute_tool(
            "my-custom-tool",
            {"required_param": "test_value"}
        )
        
        assert result.success is True
```

### Performance Testing

```python
import time
import asyncio
import pytest

class TestToolPerformance:
    @pytest.mark.asyncio
    async def test_execution_time(self):
        """Test tool execution time."""
        tool = MyCustomTool()
        
        start_time = time.time()
        result = await tool.execute(required_param="test")
        execution_time = time.time() - start_time
        
        assert execution_time < 1.0  # Should complete in under 1 second
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent tool execution."""
        tool = MyCustomTool()
        
        # Execute tool concurrently
        tasks = [
            tool.execute(required_param=f"test_{i}")
            for i in range(10)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time
        
        # All executions should succeed
        assert all(result.success for result in results)
        
        # Concurrent execution should be faster than sequential
        assert execution_time < 5.0  # Reasonable time for 10 concurrent executions
```

---

##  **Packaging and Distribution**

### Tool as Plugin

Create a distributable plugin containing your tool:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="pythonium-my-tools",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pythonium>=0.1.0",
        # Add your tool's dependencies
    ],
    entry_points={
        "pythonium.tools": [
            "my-custom-tool = my_tools:MyCustomTool",
            "another-tool = my_tools:AnotherTool"
        ]
    }
)
```

### Tool Configuration

```python
# tool_config.py
from pythonium.common.config import BaseConfig

class MyToolConfig(BaseConfig):
    """Configuration for custom tool."""
    
    def __init__(self):
        super().__init__()
        self.api_key = self.get("api_key", required=True)
        self.timeout = self.get("timeout", default=30)
        self.max_retries = self.get("max_retries", default=3)

# In your tool
class ConfigurableTool(BaseTool):
    def __init__(self, config: MyToolConfig):
        super().__init__()
        self.config = config
```

### Documentation Template

```python
"""
My Custom Tool

Description:
    Detailed description of what the tool does and its use cases.

Parameters:
    required_param (str): Description of the required parameter
    optional_param (str, optional): Description of optional parameter
    
Returns:
    ToolResult: Contains the processed data or error information
    
Examples:
    Basic usage:
        result = await tool.execute(required_param="value")
    
    With options:
        result = await tool.execute(
            required_param="value",
            optional_param="option"
        )

Notes:
    - Performance considerations
    - Known limitations
    - Security considerations
"""
```

---

## 🔐 **Security Best Practices**

### Input Validation

```python
import re
from pathlib import Path

class SecureTool(BaseTool):
    def _validate_file_path(self, path: str) -> bool:
        """Validate file path for security."""
        # Check for path traversal attacks
        if '..' in path or path.startswith('/'):
            return False
        
        # Validate allowed characters
        if not re.match(r'^[a-zA-Z0-9._/-]+$', path):
            return False
        
        return True
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string input."""
        # Remove dangerous characters
        return re.sub(r'[<>"\']', '', text)
    
    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        
        if not self._validate_file_path(file_path):
            return ToolResult(
                success=False,
                error="Invalid file path"
            )
        
        # Continue with safe execution
        pass
```

### Permission Checking

```python
from pythonium.managers.security_manager import SecurityManager

class PermissionAwareTool(BaseTool):
    def __init__(self, security_manager: SecurityManager):
        super().__init__()
        self.security_manager = security_manager
    
    async def execute(self, **kwargs) -> ToolResult:
        # Get user context from kwargs
        user_context = kwargs.get("_user_context")
        
        # Check permissions
        if not await self.security_manager.check_permission(
            user_context, 
            f"tool.{self.get_name()}.execute"
        ):
            return ToolResult(
                success=False,
                error="Insufficient permissions"
            )
        
        # Continue with authorized execution
        pass
```

---

##  **Monitoring and Metrics**

### Performance Tracking

```python
import time
from pythonium.common.metrics import MetricsCollector

class MonitoredTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.metrics = MetricsCollector()
    
    async def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        try:
            # Execute tool logic
            result = await self._perform_operation(kwargs)
            
            # Record success metrics
            self.metrics.increment(f"tool.{self.get_name()}.success")
            
            return result
            
        except Exception as e:
            # Record error metrics
            self.metrics.increment(f"tool.{self.get_name()}.error")
            
            return ToolResult(success=False, error=str(e))
            
        finally:
            # Record execution time
            execution_time = time.time() - start_time
            self.metrics.timer(f"tool.{self.get_name()}.duration", execution_time)
```

---

##  **Deployment**

### Production Considerations

1. **Resource Limits**: Set appropriate timeouts and memory limits
2. **Error Handling**: Comprehensive error handling and logging
3. **Monitoring**: Add metrics and health checks
4. **Security**: Validate all inputs and check permissions
5. **Performance**: Optimize for production workloads

### Example Production Tool

```python
import asyncio
import logging
from typing import Dict, Any, Optional
from pythonium.tools.base import BaseTool, ToolResult
from pythonium.common.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class ProductionTool(BaseTool):
    """Production-ready tool template."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self.metrics = MetricsCollector()
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
    
    def get_name(self) -> str:
        return "production-tool"
    
    def get_description(self) -> str:
        return "Production-ready tool with monitoring and error handling"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "data": {"type": "string", "required": True},
            "options": {"type": "object", "default": {}}
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool with comprehensive error handling."""
        operation_id = self._generate_operation_id()
        
        logger.info(f"Starting operation {operation_id}")
        
        try:
            # Validate inputs
            if not await self._validate_inputs(kwargs):
                return self._error_result("Invalid inputs", operation_id)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_operation(kwargs),
                timeout=self.timeout
            )
            
            logger.info(f"Operation {operation_id} completed successfully")
            self.metrics.increment(f"{self.get_name()}.success")
            
            return ToolResult(
                success=True,
                data=result,
                metadata={"operation_id": operation_id}
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Operation {operation_id} timed out")
            self.metrics.increment(f"{self.get_name()}.timeout")
            return self._error_result("Operation timeout", operation_id)
            
        except Exception as e:
            logger.error(f"Operation {operation_id} failed: {str(e)}")
            self.metrics.increment(f"{self.get_name()}.error")
            return self._error_result(str(e), operation_id)
    
    async def _validate_inputs(self, kwargs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        # Add your validation logic
        return True
    
    async def _execute_operation(self, kwargs: Dict[str, Any]) -> Any:
        """Execute the main operation."""
        # Add your operation logic
        await asyncio.sleep(0.1)  # Simulate work
        return {"result": "success"}
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _error_result(self, error: str, operation_id: str) -> ToolResult:
        """Create standardized error result."""
        return ToolResult(
            success=False,
            error=error,
            metadata={"operation_id": operation_id}
        )
```

---

For more information, see:
- [API Documentation](API_DOCUMENTATION.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [User Guide](USER_GUIDE.md)
