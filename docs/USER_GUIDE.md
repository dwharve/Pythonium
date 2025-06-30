# Pythonium User Guide

**Version**: 0.1.1  
**Last Updated**: June 30, 2025

##  **Quick Start**

Pythonium is a modular MCP (Model Context Protocol) server that provides AI agents with powerful capabilities through a plugin-based architecture.

### Installation

```bash
# Install from PyPI (when available)
pip install pythonium

# Or install from source
git clone https://github.com/dwharve/pythonium.git
cd pythonium
pip install -e .
```

### Basic Usage

```bash
# Start the MCP server with default configuration
python -m pythonium serve

# Or use the installed script
pythonium serve

# Start with custom configuration
pythonium serve --config config.yaml

# Start with specific transport
pythonium serve --transport stdio
pythonium serve --transport http --port 8080
```

### Your First Tool Execution

```python
# Example: Using the file reader tool
import asyncio
from pythonium.client import MCPClient

async def main():
    client = MCPClient("stdio")
    await client.connect()
    
    # Execute a file reading tool
    result = await client.execute_tool(
        "file_reader",
        {"path": "/path/to/your/file.txt"}
    )
    
    print(f"File content: {result.data['content']}")
    await client.disconnect()

asyncio.run(main())
```

---

##  **Installation Guide**

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, Linux
- **Memory**: Minimum 512MB RAM
- **Disk Space**: 100MB for installation

### Dependencies

Core dependencies are automatically installed:

```txt
pydantic>=2.0.0
asyncio
aiofiles
pyyaml
toml
psutil
structlog
```

### Installation Methods

#### 1. Using pip (Recommended)

```bash
# Latest stable release
pip install pythonium

# Specific version
pip install pythonium==1.0.0

# With optional dependencies
pip install pythonium[dev,test,docs]
```

#### 2. From Source

```bash
# Clone repository
git clone https://github.com/dwharve/pythonium.git
cd pythonium

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e .[dev,test]
```

#### 3. Using Docker

```bash
# Pull the official image
docker pull pythonium/pythonium:latest

# Run with stdio transport
docker run -it pythonium/pythonium:latest

# Run with HTTP transport
docker run -p 8080:8080 pythonium/pythonium:latest --transport http --port 8080
```

### Verification

```bash
# Check installation
python -c "import pythonium; print(pythonium.__version__)"

# Run built-in tests
python -m pythonium.test

# Start server to test
pythonium --help
```

---

##  **Configuration Reference**

### Configuration File Formats

Pythonium supports multiple configuration formats:

#### YAML Configuration (config.yaml)

```yaml
# Server configuration
server:
  name: "My Pythonium Server"
  version: "1.0.0"
  description: "Custom MCP server"

# Transport settings
transport:
  type: "stdio"  # stdio, http, websocket
  host: "localhost"
  port: 8080
  ssl_enabled: false

# Security settings
security:
  authentication_method: "none"  # none, api_key, oauth2
  api_keys:
    - "your-api-key-here"
  require_tls: false
  cors_enabled: true

# Performance settings
performance:
  max_concurrent_requests: 100
  request_timeout_seconds: 30
  compression_enabled: true
  compression_threshold_bytes: 1024

# Logging configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: "logs/pythonium.log"
  max_log_file_size_mb: 10
  backup_count: 5

# Resource management
resources:
  cache_ttl_seconds: 300
  max_cache_size_mb: 100
  allowed_resource_schemes:
    - "file"
    - "http"
    - "https"
  resource_timeout_seconds: 30

# Tool configuration
tools:
  enable_tool_execution: true
  tool_timeout_seconds: 300
  max_tool_output_size_bytes: 10485760  # 10MB
  allowed_tool_categories:
    - "filesystem"
    - "data_processing"
    - "network"
    - "system"

# Plugin settings
plugins:
  discovery_paths:
    - "plugins/"
    - "~/.pythonium/plugins/"
  auto_load: true
  sandbox_enabled: true
```

#### JSON Configuration (config.json)

```json
{
  "server": {
    "name": "My Pythonium Server",
    "version": "1.0.0",
    "description": "Custom MCP server"
  },
  "transport": {
    "type": "http",
    "host": "0.0.0.0",
    "port": 8080,
    "ssl_enabled": false
  },
  "security": {
    "authentication_method": "api_key",
    "api_keys": ["your-api-key-here"],
    "require_tls": false,
    "cors_enabled": true
  },
  "logging": {
    "level": "INFO",
    "file_path": "logs/pythonium.log"
  }
}
```

#### TOML Configuration (config.toml)

```toml
[server]
name = "My Pythonium Server"
version = "1.0.0"
description = "Custom MCP server"

[transport]
type = "stdio"
host = "localhost"
port = 8080
ssl_enabled = false

[security]
authentication_method = "none"
api_keys = ["your-api-key-here"]
require_tls = false
cors_enabled = true

[logging]
level = "INFO"
file_path = "logs/pythonium.log"
max_log_file_size_mb = 10
```

### Environment Variables

Override configuration using environment variables:

```bash
# Server settings
export PYTHONIUM_SERVER_NAME="Production Server"
export PYTHONIUM_SERVER_DEBUG=false

# Transport settings
export PYTHONIUM_TRANSPORT_TYPE=http
export PYTHONIUM_TRANSPORT_PORT=8080

# Security settings
export PYTHONIUM_API_KEY="your-secure-api-key"
export PYTHONIUM_REQUIRE_TLS=true

# Logging
export PYTHONIUM_LOG_LEVEL=DEBUG
export PYTHONIUM_LOG_FILE="logs/debug.log"
```

---

##  **Available Tools**

### File System Tools

#### file_reader
Read content from files with encoding detection.

```python
await client.execute_tool("file_reader", {
    "path": "/path/to/file.txt",
    "encoding": "utf-8",  # Optional, auto-detected if not specified
    "max_size_mb": 10     # Optional, default 10MB limit
})
```

#### file_writer
Write content to files with backup options.

```python
await client.execute_tool("file_writer", {
    "path": "/path/to/output.txt",
    "content": "Hello, World!",
    "encoding": "utf-8",     # Optional
    "create_backup": true,   # Optional
    "create_dirs": true      # Optional, create parent directories
})
```

#### directory_scanner
List directory contents with filtering options.

```python
await client.execute_tool("directory_scanner", {
    "path": "/path/to/directory",
    "recursive": true,           # Optional
    "include_hidden": false,     # Optional
    "file_pattern": "*.txt",     # Optional glob pattern
    "max_depth": 3               # Optional recursion limit
})
```

#### file_search
Search for files by name or content.

```python
await client.execute_tool("file_search", {
    "root_path": "/search/root",
    "search_term": "configuration",
    "search_in_content": true,    # Optional, search file contents
    "case_sensitive": false,      # Optional
    "file_extensions": [".txt", ".py"],  # Optional filter
    "max_results": 100            # Optional limit
})
```

### Data Processing Tools

#### text_processor
Process text with various operations.

```python
await client.execute_tool("text_processor", {
    "text": "Hello World",
    "operations": [
        {"type": "uppercase"},
        {"type": "replace", "find": "WORLD", "replace": "PYTHON"}
    ]
})
```

#### json_processor
Parse, validate, and manipulate JSON data.

```python
await client.execute_tool("json_processor", {
    "data": '{"name": "test", "value": 123}',
    "operation": "parse",         # parse, validate, minify, prettify
    "schema": {...},              # Optional JSON schema for validation
    "query": "$.name"             # Optional JSONPath query
})
```

#### csv_processor
Read, write, and manipulate CSV data.

```python
await client.execute_tool("csv_processor", {
    "file_path": "/data/sample.csv",
    "operation": "read",          # read, write, filter, transform
    "delimiter": ",",             # Optional
    "has_header": true,           # Optional
    "filters": [                  # Optional for filter operation
        {"column": "age", "operator": ">", "value": 18}
    ]
})
```

### Network Tools

#### http_client
Make HTTP requests with full feature support.

```python
await client.execute_tool("http_client", {
    "url": "https://api.example.com/data",
    "method": "POST",             # GET, POST, PUT, DELETE, etc.
    "headers": {                  # Optional
        "Content-Type": "application/json",
        "Authorization": "Bearer token"
    },
    "body": {"key": "value"},     # Optional request body
    "timeout": 30,                # Optional timeout in seconds
    "follow_redirects": true      # Optional
})
```

#### web_scraper
Extract data from web pages.

```python
await client.execute_tool("web_scraper", {
    "url": "https://example.com",
    "selectors": {                # CSS selectors
        "title": "h1",
        "content": ".content p",
        "links": "a[href]"
    },
    "wait_for": "h1",             # Optional, wait for element
    "timeout": 30                 # Optional page load timeout
})
```

### System Tools

#### command_executor
Execute system commands safely.

```python
await client.execute_tool("command_executor", {
    "command": ["ls", "-la", "/tmp"],
    "timeout": 30,                # Optional
    "working_directory": "/tmp",  # Optional
    "capture_output": true,       # Optional
    "environment": {              # Optional env vars
        "PATH": "/usr/bin:/bin"
    }
})
```

#### system_info
Get system information and metrics.

```python
await client.execute_tool("system_info", {
    "categories": [               # Optional filter
        "cpu", "memory", "disk", "network", "processes"
    ],
    "include_processes": false,   # Optional, can be expensive
    "format": "detailed"          # Optional: summary, detailed
})
```

---

##  **Advanced Usage**

### Custom Tool Development

Create your own tools by extending the BaseTool class:

```python
from pythonium.tools.base import BaseTool, ToolMetadata, ToolResult
from typing import Dict, Any

class CustomTool(BaseTool):
    def __init__(self):
        super().__init__(name="custom_tool")
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="custom_tool",
            description="A custom tool example",
            version="1.0.0",
            category="custom",
            author="Your Name",
            parameters=[
                {
                    "name": "input_text",
                    "type": "string",
                    "description": "Text to process",
                    "required": True
                }
            ],
            requirements=[],
            outputs=[
                {
                    "name": "processed_text",
                    "type": "string",
                    "description": "Processed output"
                }
            ]
        )
    
    async def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        input_text = parameters["input_text"]
        processed = input_text.upper()  # Simple processing
        
        return ToolResult(
            success=True,
            data={"processed_text": processed},
            metadata={"processing_time": 0.001}
        )
```

### Plugin Development

Create plugins to extend Pythonium functionality:

```python
from pythonium.common.plugins import BasePlugin

class CustomPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="custom_plugin",
            version="1.0.0",
            description="A custom plugin example"
        )
    
    async def initialize(self):
        """Called when plugin is loaded."""
        self.logger.info("Custom plugin initializing")
        # Initialize plugin resources
    
    async def configure(self, config: Dict[str, Any]):
        """Called when plugin configuration is updated."""
        self.config = config
    
    async def shutdown(self):
        """Called when plugin is unloaded."""
        self.logger.info("Custom plugin shutting down")
        # Clean up resources
```

### Configuration Management

Access and modify configuration at runtime:

```python
from pythonium.managers.config_manager import ConfigManager

async def update_config():
    config_manager = ConfigManager()
    await config_manager.initialize()
    
    # Get current configuration
    current_config = await config_manager.get_config()
    
    # Update configuration
    await config_manager.update_config({
        "logging.level": "DEBUG",
        "performance.max_concurrent_requests": 200
    })
    
    # Reload from file
    await config_manager.reload_config()
```

### Security Configuration

Set up authentication and authorization:

```python
# API Key Authentication
security:
  authentication_method: "api_key"
  api_keys:
    - "sk-1234567890abcdef"
    - "sk-fedcba0987654321"
  require_tls: true

# OAuth2 Authentication (when supported)
security:
  authentication_method: "oauth2"
  oauth2:
    provider: "custom"
    client_id: "your-client-id"
    client_secret: "your-client-secret"
    token_url: "https://auth.example.com/token"
```

---

##  **Troubleshooting**

### Common Issues

#### 1. Server Won't Start

**Problem**: Server fails to start with configuration errors.

**Solution**:
```bash
# Validate configuration
pythonium --validate-config

# Check configuration syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Start with minimal configuration
pythonium serve --transport stdio --log-level DEBUG
```

#### 2. Tool Execution Fails

**Problem**: Tools fail with permission or timeout errors.

**Solution**:
```yaml
# Increase timeouts
tools:
  tool_timeout_seconds: 600
  max_tool_output_size_bytes: 52428800  # 50MB

# Check tool permissions
security:
  allowed_tool_categories:
    - "filesystem"
    - "network"
```

#### 3. High Memory Usage

**Problem**: Server consumes too much memory.

**Solution**:
```yaml
# Adjust resource limits
resources:
  max_cache_size_mb: 50
  cache_ttl_seconds: 60

performance:
  max_concurrent_requests: 10
```

#### 4. Connection Issues

**Problem**: Client can't connect to server.

**Solution**:
```bash
# Check if server is running
netstat -tulpn | grep 8080

# Test connection
curl http://localhost:8080/health

# Check firewall settings
sudo ufw status
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Command line
pythonium serve --log-level DEBUG

# Configuration file
logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
```

### Log Analysis

Common log patterns to watch for:

```bash
# Filter for errors
grep "ERROR" logs/pythonium.log

# Tool execution issues
grep "tool_execution" logs/pythonium.log

# Performance issues
grep "timeout\|slow" logs/pythonium.log

# Security issues
grep "authentication\|authorization" logs/pythonium.log
```

---

##  **Performance Tuning**

### Server Optimization

```yaml
# High-performance configuration
performance:
  max_concurrent_requests: 1000
  request_timeout_seconds: 60
  compression_enabled: true
  compression_threshold_bytes: 512

resources:
  cache_ttl_seconds: 3600
  max_cache_size_mb: 500

transport:
  type: "http"
  host: "0.0.0.0"
  port: 8080
  ssl_enabled: true
```

### Memory Management

```yaml
# Memory-optimized configuration
resources:
  cache_ttl_seconds: 300
  max_cache_size_mb: 100

tools:
  max_tool_output_size_bytes: 10485760  # 10MB

logging:
  max_log_file_size_mb: 10
  backup_count: 3
```

### Monitoring

Set up monitoring and metrics:

```python
from pythonium.common.metrics import MetricsCollector

# Custom metrics
metrics = MetricsCollector()
metrics.increment("custom_event_count")
metrics.gauge("memory_usage", psutil.virtual_memory().percent)
```

---

##  **Integration Examples**

### Claude Desktop Integration

```json
{
  "mcpServers": {
    "pythonium": {
      "command": "pythonium",
      "args": ["serve"],
      "env": {
        "PYTHONIUM_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Custom Client Integration

```python
import asyncio
from pythonium.client import MCPClient

class CustomAIAgent:
    def __init__(self):
        self.mcp_client = MCPClient("stdio")
    
    async def start(self):
        await self.mcp_client.connect()
    
    async def process_file(self, file_path: str) -> str:
        """Process a file and return summary."""
        # Read file content
        content_result = await self.mcp_client.execute_tool(
            "file_reader",
            {"path": file_path}
        )
        
        # Process with text tool
        summary_result = await self.mcp_client.execute_tool(
            "text_processor",
            {
                "text": content_result.data["content"],
                "operations": [{"type": "summarize", "max_length": 100}]
            }
        )
        
        return summary_result.data["processed_text"]
    
    async def stop(self):
        await self.mcp_client.disconnect()
```

---

## 🆘 **Support**

### Getting Help

- **Documentation**: [https://pythonium.readthedocs.io](https://pythonium.readthedocs.io)
- **Issues**: [https://github.com/dwharve/pythonium/issues](https://github.com/dwharve/pythonium/issues)
- **Discussions**: [https://github.com/dwharve/pythonium/discussions](https://github.com/dwharve/pythonium/discussions)
- **Discord**: [https://discord.gg/pythonium](https://discord.gg/pythonium)

### Reporting Bugs

When reporting bugs, please include:

1. Pythonium version (`python -c "import pythonium; print(pythonium.__version__)"`)
2. Python version (`python --version`)
3. Operating system and version
4. Configuration file (remove sensitive information)
5. Error logs with debug level enabled
6. Steps to reproduce the issue

### Feature Requests

Feature requests are welcome! Please:

1. Check existing issues first
2. Describe the use case clearly
3. Provide examples of how it would be used
4. Consider contributing the implementation

---

**Need more help?** Check out our [Developer Guide](DEVELOPER_GUIDE.md) for advanced topics and [API Reference](API_REFERENCE.md) for detailed API documentation.
