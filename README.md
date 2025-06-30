# Pythonium

A modular Model Context Protocol (MCP) server designed to enable advanced capabilities for AI agents through a comprehensive plugin-based architecture.

## Overview

Pythonium provides a robust, extensible foundation for building sophisticated AI agent tools and capabilities. Built around the Model Context Protocol specification, it offers a clean separation of concerns through its modular package structure.

## Architecture

### Core Packages

- **`pythonium.common`** - Shared utilities, base classes, and plugin framework foundation
- **`pythonium.managers`** - Object-oriented management systems for configuration, plugins, resources, and security
- **`pythonium.tools`** - Comprehensive tool management system with plugin framework
- **`pythonium.mcp`** - Full-featured MCP server implementation with configuration management

## Features

### Plugin Framework
- Dynamic plugin discovery and loading
- Dependency resolution and lifecycle management
- Plugin isolation and sandboxing
- Extensible tool and manager registration

### Tool Categories
- **File System**: File operations, directory management, content analysis (`pythonium.tools.filesystem`)
- **Network**: HTTP operations, API interactions, web scraping (`pythonium.tools.network`)
- **System**: Process management, environment access, monitoring (`pythonium.tools.system`)

### Management Systems
- **Configuration**: Multi-format config loading with hot-reload
- **Plugin**: Dynamic plugin lifecycle and dependency management
- **Resource**: Memory, connection pooling, and resource monitoring
- **Security**: Authentication, authorization, rate limiting, audit logging

### MCP Server
- Full Model Context Protocol compliance
- Multiple transport options (stdio, HTTP, WebSocket)
- Tool registration and capability negotiation
- Resource management and streaming
- Prompt template system

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/dwharve/pythonium.git
cd pythonium

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Basic Usage

```bash
# Run the MCP server
python -m pythonium --help

# Start with default configuration
python -m pythonium serve

# Start with custom configuration
python -m pythonium serve --config config/server.yaml

# List available tools
python -m pythonium tools list

# Show server status
python -m pythonium status

# Alternative: Use installed script
pythonium --help
pythonium serve
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run tests with coverage
pytest --cov=pythonium --cov-report=html

# Format code
black pythonium tests
isort pythonium tests

# Type checking
mypy pythonium
```

### Project Structure

```
pythonium/
├── pythonium/           # Main package
│   ├── common/         # Shared utilities and plugin framework
│   ├── managers/       # Management systems
│   ├── tools/          # Tool implementations
│   ├── mcp/           # MCP server implementation
│   └── __main__.py    # Module entry point
├── tests/              # Test suite
├── docs/               # Documentation
├── config/             # Configuration files
└── requirements.txt    # Dependencies
```

### Testing

The project uses pytest for testing with comprehensive coverage:

- **Unit Tests**: Individual component testing (78 total tests)
- **Integration Tests**: Package interaction testing  
- **End-to-End Tests**: Full MCP server functionality
- **Performance Tests**: Load and performance testing

**Current Status**: 77 tests passing, 1 test failing (dependency injection issue in manager integration)

```bash
# Run all tests
pytest

# Run specific test category
pytest -m unit
pytest -m integration

# Run with coverage
pytest --cov=pythonium --cov-report=term-missing

# Quick test run
pytest -q
```

## Configuration

Pythonium supports multiple configuration formats (YAML, JSON, TOML) with environment variable integration:

```yaml
# config/server.yaml
server:
  host: "localhost"
  port: 8080
  transport: "stdio"  # stdio, http, websocket

plugins:
  auto_discover: true
  plugin_dirs:
    - "plugins"
    - "~/.pythonium/plugins"

tools:
  categories:
    - filesystem
    - network
    - system

logging:
  level: "INFO"
  format: "structured"
```

## Plugin Development

### Creating a Tool Plugin

```python
from pythonium.tools.base import BaseTool
from pythonium.common.types import ToolResult

class MyCustomTool(BaseTool):
    name = "my_custom_tool"
    description = "A custom tool example"
    
    async def execute(self, **kwargs) -> ToolResult:
        # Implementation here
        return ToolResult(
            success=True,
            data={"result": "Hello from custom tool!"}
        )
```

### Creating a Manager Plugin

```python
from pythonium.managers.base import BaseManager

class MyCustomManager(BaseManager):
    name = "custom_manager"
    
    async def initialize(self):
        # Initialize manager
        pass
    
    async def shutdown(self):
        # Cleanup manager
        pass
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

For a detailed history of changes, see [CHANGELOG.md](CHANGELOG.md).

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints throughout
- Maintain test coverage above 90%
- Document all public APIs
- Use conventional commit messages

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://pythonium.readthedocs.io/](https://pythonium.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/dwharve/pythonium/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dwharve/pythonium/discussions)

## Acknowledgments

- Model Context Protocol specification
- The open-source Python community
- Contributors and maintainers

---

**Status**: Beta - Core functionality implemented, under active development with known issues being addressed

**Current Version**: 0.1.1  
**Last Updated**: June 30, 2025  
**Maintainer**: David Harvey
