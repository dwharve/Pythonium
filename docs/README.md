# Pythonium Documentation

Welcome to the Pythonium documentation! This directory contains comprehensive guides and references for using and extending Pythonium.

## Table of Contents

### User Guides
- [Installation & Quick Start](../README.md#installation) - Getting started with Pythonium
- [Configuration Guide](configuration.md) - Configuring Pythonium for your project
- [CLI Reference](cli-reference.md) - Complete command-line interface documentation
- [Output Formats](output-formats.md) - Understanding different output formats

### Developer Guides
- [Creating Custom Detectors](creating-detectors.md) - Complete guide to writing custom detectors
- [API Reference](api-reference.md) - Python API documentation
- [Architecture Overview](architecture.md) - How Pythonium works internally

### MCP Integration
- [MCP Server Setup](mcp-server.md) - Setting up the Model Context Protocol server
- [LLM Agent Integration](llm-integration.md) - Using Pythonium with AI coding assistants

### Detector Documentation
- [Dead Code Detector](detectors/dead-code.md) - Finding unused code
- [Clone Detector](detectors/clone.md) - Identifying code duplication
- [Security Detector](detectors/security-smell.md) - Finding security vulnerabilities
- [Complexity Detector](detectors/complexity-hotspot.md) - Identifying complex code
- [All Detectors](detectors/README.md) - Complete detector reference

## Documentation Structure

```
docs/
├── README.md                    # This file
├── creating-detectors.md        # Guide for creating custom detectors
├── configuration.md             # Configuration reference
├── cli-reference.md             # CLI documentation
├── api-reference.md             # Python API docs
├── architecture.md              # Internal architecture
├── mcp-server.md               # MCP server documentation
├── output-formats.md           # Output format specifications
├── detectors/                  # Detector-specific documentation
│   ├── README.md
│   ├── dead-code.md
│   ├── clone.md
│   └── ...
```
