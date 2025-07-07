# Pythonium

A modular Model Context Protocol (MCP) server designed to enable advanced capabilities for AI agents through a robust, extensible architecture built on the official MCP SDK.

## Overview

Pythonium provides a comprehensive, production-ready foundation for building sophisticated AI agent tools and capabilities. Built around the Model Context Protocol specification and leveraging the official MCP SDK (FastMCP), it offers a clean separation of concerns through its modular package structure and streamlined configuration management.

## Architecture

### Core Packages

- **`pythonium.common`** - Shared utilities, configuration management, and base components
- **`pythonium.core`** - Central server implementation, configuration, and tool management
- **`pythonium.tools`** - Comprehensive standard tool library with extensible framework
- **`pythonium.managers`** - Lightweight management systems for specialized functionality

## Features

### MCP SDK Integration
- Built on the official MCP SDK's FastMCP framework
- Full Model Context Protocol compliance
- Multiple transport support (stdio, HTTP, WebSocket)
- Native tool registration and capability negotiation

### Comprehensive Tool Library
- **System Operations**: Command execution, environment access, system monitoring (`pythonium.tools.std.execution`)
- **File Operations**: Advanced file and directory management (`pythonium.tools.std.file_ops`)
- **Web Operations**: HTTP client, web search with multiple engines (`pythonium.tools.std.web`)
- **Tool Management**: Meta-tools for tool discovery and introspection (`pythonium.tools.std.tool_ops`)

### Advanced Configuration
- Pydantic-based configuration with validation
- Environment variable integration
- Multiple format support (YAML, JSON, TOML)
- Hot-reload capability and override support

### Production Features
- Structured logging with multiple output formats
- Comprehensive error handling and recovery
- Resource management and connection pooling
- Security considerations and rate limiting
- Performance optimizations with async architecture

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

# Start with default configuration (stdio transport)
python -m pythonium serve

# Start with HTTP transport
python -m pythonium serve --transport http --host localhost --port 8080

# Start with WebSocket transport
python -m pythonium serve --transport websocket --host localhost --port 8080

# Start with custom configuration file
python -m pythonium serve --config config/server.yaml

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
│   ├── common/         # Shared utilities and base components
│   │   ├── config.py   # Pydantic configuration management
│   │   ├── base.py     # Base classes and result types
│   │   ├── logging.py  # Structured logging system
│   │   └── ...         # HTTP client, error handling, etc.
│   ├── core/           # Core server and management
│   │   ├── server.py   # Main MCP server implementation
│   │   ├── config.py   # Configuration manager
│   │   └── tools/      # Tool registry and discovery
│   ├── tools/          # Tool implementations
│   │   ├── base.py     # Base tool framework
│   │   └── std/        # Standard tool library
│   ├── managers/       # Specialized managers
│   ├── main.py         # CLI entry point
│   └── __main__.py     # Module entry point
├── tests/              # Comprehensive test suite (238 tests)
├── docs/               # Documentation
├── config/             # Configuration examples
└── requirements.txt    # Dependencies
```

### Testing

The project uses pytest for testing with comprehensive coverage across all components:

- **Unit Tests**: Individual component testing 
- **Integration Tests**: Cross-component interaction testing  
- **Core Tests**: Configuration, server, and tool management
- **End-to-End Tests**: Full MCP server functionality
- **Performance Tests**: Load testing and benchmarks

**Current Status**: 238 tests with robust coverage across all modules

```bash
# Run all tests
pytest

# Run with coverage reporting
pytest --cov=pythonium --cov-report=html

# Run specific test categories
pytest tests/core/         # Core functionality tests
pytest tests/tools/        # Tool implementation tests
pytest tests/common/       # Common utilities tests

# Quick test run
pytest -q

# Verbose test output
pytest -v
```

## Configuration

Pythonium uses Pydantic-based configuration with support for multiple formats (YAML, JSON, TOML) and environment variable integration:

```yaml
# config/server.yaml
server:
  name: "Pythonium MCP Server"
  description: "A modular MCP server for AI agents"
  host: "localhost"
  port: 8080
  transport: "stdio"  # stdio, http, websocket

tools:
  # Tool discovery and loading configuration
  auto_discover: true
  categories:
    - "system"
    - "web"
    - "file_operations"

logging:
  level: "INFO"           # DEBUG, INFO, WARNING, ERROR
  format: "structured"    # structured, plain
  output: "console"       # console, file

security:
  authentication: "none"  # none, api_key
  rate_limit:
    enabled: false
    requests_per_minute: 60
```

## Tool Development

### Creating a Custom Tool

```python
from pythonium.tools.base import BaseTool, ToolMetadata, ToolParameter, ParameterType
from pythonium.common.base import Result
from pythonium.common.parameters import validate_parameters

class MyCustomTool(BaseTool):
    """A custom tool example with proper parameter validation."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_custom_tool",
            description="A custom tool example that demonstrates the framework",
            brief_description="Custom tool example",
            category="custom",
            tags=["example", "custom"],
            parameters=[
                ToolParameter(
                    name="message",
                    type=ParameterType.STRING,
                    description="Message to process",
                    required=True,
                    min_length=1,
                    max_length=1000
                )
            ]
        )
    
    @validate_parameters  # Automatic parameter validation
    async def execute(self, message: str, context: ToolContext) -> Result:
        """Execute the tool with validated parameters."""
        try:
            result = f"Processed: {message}"
            return Result.success_result(
                data={"result": result, "original": message},
                metadata={"tool": "my_custom_tool"}
            )
        except Exception as e:
            return Result.error_result(f"Tool execution failed: {e}")
```

### Tool Registration

Tools are automatically discovered and registered when placed in the appropriate package structure. The tool discovery system handles:

- Automatic tool detection and registration
- Parameter validation and schema generation
- Error handling and logging
- Integration with the MCP protocol

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
- Use type hints throughout the codebase
- Maintain comprehensive test coverage
- Document all public APIs with detailed docstrings
- Use conventional commit messages
- Leverage Pydantic for data validation and configuration
- Implement proper async/await patterns for I/O operations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: Available in the `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/dwharve/pythonium/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dwharve/pythonium/discussions)

## Acknowledgments

- Official Model Context Protocol SDK and specification
- The open-source Python community
- Pydantic and FastAPI ecosystems for configuration and validation patterns
- Contributors and maintainers

---

**Status**: Production-ready Beta - Core functionality stable, comprehensive test coverage, active development

**Current Version**: 0.1.4  
**Last Updated**: July 6, 2025  
**Maintainer**: David Harvey
