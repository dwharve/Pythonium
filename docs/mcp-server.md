# MCP Server Setup

Model Context Protocol (MCP) server integration allows AI agents and coding assistants to use Pythonium for sophisticated code analysis. This guide covers setup, configuration, and usage of the Pythonium MCP server.

## Overview

The Pythonium MCP server provides AI agents with tools to:
- Analyze Python codebases for quality issues
- Get detailed information about specific detectors
- Analyze code snippets and inline code
- Generate analysis summaries and recommendations

## Installation

Install Pythonium with MCP dependencies:

```bash
# Basic installation
pip install pythonium

# With MCP support
pip install pythonium[mcp]

# Verify MCP availability
python -c "from pythonium.mcp_server import PythoniumMCPServer; print('MCP available')"
```

## Quick Start

### Start the MCP Server

```bash
# Start stdio server (most common for local AI agents)
pythonium mcp-server

# Start with specific transport
pythonium mcp-server --transport stdio

# Start SSE server (for web-based agents)
pythonium mcp-server --transport sse --host localhost --port 8000
```

### Basic Usage with an AI Agent

Once the server is running, AI agents can use these tools:

1. **analyze_code** - Analyze files or directories
2. **analyze_inline_code** - Analyze code snippets
3. **list_detectors** - Get available detectors
4. **get_detector_info** - Get detailed detector information
5. **analyze_issues** - Generate analysis summaries

## Server Configuration

### Command Line Options

```bash
pythonium mcp-server [OPTIONS]
```

**Options:**
- `--transport TYPE` - Transport type: `stdio` or `sse` (default: stdio)
- `--host HOST` - Host for SSE transport (default: localhost)
- `--port PORT` - Port for SSE transport (default: 8000)

### Transport Types

#### STDIO Transport

Standard input/output transport for local AI agents:

```bash
pythonium mcp-server --transport stdio
```

**Use Cases:**
- Local AI coding assistants
- Desktop applications
- Command-line tools
- Development environments

#### SSE Transport

Server-Sent Events transport for web-based integration:

```bash
pythonium mcp-server --transport sse --host 0.0.0.0 --port 8080
```

**Use Cases:**
- Web applications
- Remote AI agents
- Cloud-based coding assistants
- Browser extensions

## Available Tools

### 1. analyze_code

Analyze Python files or directories for code health issues.

**Parameters:**
- `path` (required) - File or directory path to analyze
- `detectors` (optional) - Comma-separated list of detector IDs
- `config` (optional) - Configuration overrides as JSON object

**Example Usage:**
```json
{
  "name": "analyze_code",
  "arguments": {
    "path": "/path/to/project",
    "detectors": "security_smell,dead_code",
    "config": {
      "detectors": {
        "security_smell": {"check_hardcoded_secrets": true}
      }
    }
  }
}
```

**Response:**
Returns detailed analysis results with:
- Issues found with severity levels
- File locations and line numbers
- Detector-specific metadata
- Recommendations for fixes

### 2. analyze_inline_code

Analyze code snippets provided as strings.

**Parameters:**
- `code` (required) - Python code to analyze
- `detectors` (optional) - Specific detectors to run
- `filename` (optional) - Virtual filename for context

**Example Usage:**
```json
{
  "name": "analyze_inline_code", 
  "arguments": {
    "code": "def unused_function():\n    password = 'secret123'\n    return password",
    "detectors": "dead_code,security_smell",
    "filename": "example.py"
  }
}
```

### 3. list_detectors

Get information about all available detectors.

**Parameters:** None

**Response:** List of detectors with:
- Detector ID and name
- Description and category
- Usage tips and related detectors
- Typical severity level

### 4. get_detector_info

Get detailed information about a specific detector.

**Parameters:**
- `detector_id` (required) - ID of the detector

**Example Usage:**
```json
{
  "name": "get_detector_info",
  "arguments": {
    "detector_id": "security_smell"
  }
}
```

**Response:** Comprehensive detector information including:
- Purpose and what it detects
- Configuration options
- Example usage
- Related detectors

### 5. analyze_issues

Generate summaries and recommendations from analysis results.

**Parameters:**
- `path` (required) - Path that was previously analyzed
- `severity_filter` (optional) - Minimum severity to include

**Example Usage:**
```json
{
  "name": "analyze_issues",
  "arguments": {
    "path": "/path/to/project",
    "severity_filter": "warn"
  }
}
```

**Response:** Analysis summary with:
- Issue statistics by detector and severity
- Prioritized recommendations
- Action items for improvement

## Integration Examples

### Claude Desktop Integration

Configure Claude Desktop to use Pythonium MCP server:

```json
{
  "mcpServers": {
    "pythonium": {
      "command": "pythonium",
      "args": ["mcp-server", "--transport", "stdio"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

### VS Code Extension Integration

Create a VS Code extension that uses the MCP server:

```typescript
import { ChildProcess, spawn } from 'child_process';

class PythoniumMCPClient {
    private server: ChildProcess;

    async start() {
        this.server = spawn('pythonium', ['mcp-server', '--transport', 'stdio']);
        
        // Handle server communication
        this.server.stdout?.on('data', this.handleResponse.bind(this));
    }

    async analyzeCode(path: string, detectors?: string[]) {
        const request = {
            method: 'tools/call',
            params: {
                name: 'analyze_code',
                arguments: {
                    path,
                    detectors: detectors?.join(',')
                }
            }
        };
        
        this.server.stdin?.write(JSON.stringify(request) + '\n');
    }
}
```

### GitHub Actions Integration

Use Pythonium MCP server in GitHub Actions:

```yaml
name: Code Analysis with MCP

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Pythonium
      run: pip install pythonium[mcp]
    
    - name: Start MCP Server and Analyze
      run: |
        # Start server in background
        pythonium mcp-server --transport stdio &
        SERVER_PID=$!
        
        # Give server time to start
        sleep 2
        
        # Use MCP client to analyze code
        python scripts/mcp_analyze.py
        
        # Clean up
        kill $SERVER_PID
```

### Custom AI Agent Integration

Build a custom AI agent that uses Pythonium MCP:

```python
import asyncio
import json
import subprocess
from typing import Dict, Any

class PythoniumAgent:
    def __init__(self):
        self.server = None
    
    async def start_server(self):
        """Start the Pythonium MCP server."""
        self.server = await asyncio.create_subprocess_exec(
            'pythonium', 'mcp-server', '--transport', 'stdio',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Call a Pythonium MCP tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Send request
        request_json = json.dumps(request) + '\n'
        self.server.stdin.write(request_json.encode())
        await self.server.stdin.drain()
        
        # Read response
        response_line = await self.server.stdout.readline()
        response = json.loads(response_line.decode())
        
        return response
    
    async def analyze_project(self, project_path: str):
        """Analyze a project and provide recommendations."""
        # Get available detectors
        detectors_response = await self.call_tool("list_detectors", {})
        detectors = detectors_response["result"]["content"][0]["text"]
        
        # Run comprehensive analysis
        analysis_response = await self.call_tool("analyze_code", {
            "path": project_path
        })
        
        # Get analysis summary
        summary_response = await self.call_tool("analyze_issues", {
            "path": project_path,
            "severity_filter": "warn"
        })
        
        return {
            "detectors": detectors,
            "analysis": analysis_response,
            "summary": summary_response
        }

# Usage
async def main():
    agent = PythoniumAgent()
    await agent.start_server()
    
    results = await agent.analyze_project("./my_project")
    print(json.dumps(results, indent=2))

asyncio.run(main())
```

## Configuration

### Server Configuration

Configure the MCP server through environment variables or configuration files:

```bash
# Environment variables
export PYTHONIUM_MCP_HOST=localhost
export PYTHONIUM_MCP_PORT=8000
export PYTHONIUM_MCP_TIMEOUT=30

# Or use configuration file
```

```yaml
# .pythonium.yml
mcp:
  server:
    host: "localhost"
    port: 8000
    timeout: 30
    max_requests_per_minute: 100
  
  tools:
    analyze_code:
      max_file_size: 1048576  # 1MB
      timeout: 60
    
    analyze_inline_code:
      max_code_length: 10000
      timeout: 10
```

### Security Configuration

Configure security settings for production use:

```yaml
mcp:
  security:
    # Allowed paths for analysis
    allowed_paths:
      - "/home/user/projects"
      - "/opt/code"
    
    # Denied paths
    denied_paths:
      - "/etc"
      - "/usr/bin"
    
    # Maximum analysis time
    max_analysis_time: 300  # 5 minutes
    
    # Rate limiting
    rate_limit:
      requests_per_minute: 60
      burst_size: 10
```

## Troubleshooting

### Common Issues

#### 1. MCP Dependencies Not Available

```bash
# Error: ImportError: No module named 'mcp'
pip install pythonium[mcp]

# Or install MCP directly
pip install mcp
```

#### 2. Server Won't Start

```bash
# Check if port is available (for SSE transport)
netstat -an | grep 8000

# Try different port
pythonium mcp-server --transport sse --port 8001

# Check permissions
ls -la ~/.pythonium/
```

#### 3. Communication Issues

```bash
# Test server manually
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | pythonium mcp-server

# Enable debug logging
export PYTHONIUM_LOG_LEVEL=DEBUG
pythonium mcp-server --transport stdio
```

#### 4. Analysis Timeouts

```yaml
# Increase timeouts in configuration
mcp:
  tools:
    analyze_code:
      timeout: 120  # 2 minutes
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Debug mode
export PYTHONIUM_LOG_LEVEL=DEBUG
export PYTHONIUM_MCP_DEBUG=true

# Start server with debug info
pythonium mcp-server --transport stdio
```

### Performance Optimization

#### For Large Codebases

```yaml
# Optimize for large projects
analysis:
  max_file_size: 2097152  # 2MB
  max_files: 5000
  
performance:
  parallel: true
  workers: 4
  cache_enabled: true

mcp:
  tools:
    analyze_code:
      timeout: 300  # 5 minutes
      chunk_size: 100  # Process in chunks
```

#### For High-Frequency Usage

```yaml
# Optimize for frequent requests
performance:
  cache_enabled: true
  cache_ttl: 3600  # 1 hour

mcp:
  server:
    keep_alive: true
    connection_pool_size: 10
  
  tools:
    # Cache analysis results
    cache_results: true
    cache_duration: 1800  # 30 minutes
```

## Advanced Usage

### Custom Tool Development

Extend the MCP server with custom tools:

```python
from pythonium.mcp_server import PythoniumMCPServer

class CustomMCPServer(PythoniumMCPServer):
    async def handle_custom_tool(self, arguments: dict):
        """Custom tool implementation."""
        # Your custom logic here
        return {"result": "custom analysis"}

# Register custom tools
server = CustomMCPServer()
server.register_tool("custom_analysis", server.handle_custom_tool)
```

### Batch Analysis

Process multiple projects efficiently:

```python
import asyncio
from pythonium.mcp_server import PythoniumMCPServer

async def batch_analyze(projects: list):
    """Analyze multiple projects in batch."""
    server = PythoniumMCPServer()
    
    results = []
    for project_path in projects:
        result = await server.analyze_code({"path": project_path})
        results.append({
            "project": project_path,
            "analysis": result
        })
    
    return results
```

### Integration Testing

Test MCP server integration:

```python
import unittest
import asyncio
from pythonium.mcp_server import PythoniumMCPServer

class TestMCPIntegration(unittest.TestCase):
    def setUp(self):
        self.server = PythoniumMCPServer()
    
    async def test_analyze_code_tool(self):
        """Test analyze_code tool."""
        result = await self.server.analyze_code({
            "path": "test_project/",
            "detectors": "dead_code"
        })
        
        self.assertIn("content", result)
        self.assertGreater(len(result["content"]), 0)
    
    def test_server_startup(self):
        """Test server can start successfully."""
        # Test server initialization
        self.assertIsNotNone(self.server.name)
        self.assertIsNotNone(self.server.version)
```

The Pythonium MCP server provides a powerful interface for AI agents to perform sophisticated code analysis, enabling better code quality insights and automated code improvement suggestions.
