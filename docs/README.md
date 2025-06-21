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
- [Detector Overview](detectors/README.md) - Complete detector reference and documentation
- [Advanced Patterns](detectors/advanced-patterns.md) - Pattern detection capabilities
- [Alternative Implementation](detectors/alt-implementation.md) - Finding competing implementations
- [Block Clone Detection](detectors/block-clone.md) - Block-level code duplication
- [Circular Dependencies](detectors/circular-deps.md) - Import cycle detection
- [Code Clone Detection](detectors/clone.md) - Code duplication analysis
- [Complexity Hotspots](detectors/complexity-hotspot.md) - Complexity analysis
- [Dead Code Detection](detectors/dead-code.md) - Unused code identification
- [Deprecated API Detection](detectors/deprecated-api.md) - Finding deprecated usage
- [Inconsistent API](detectors/inconsistent-api.md) - API consistency checking
- [Security Smell Detection](detectors/security-smell.md) - Security vulnerability detection
- [Semantic Equivalence](detectors/semantic-equivalence.md) - Functionally equivalent code
- [Stub Implementation](detectors/stub-implementation.md) - Placeholder code detection

## Documentation Structure

```
docs/
├── README.md                    # This file
├── api-reference.md             # Python API documentation
├── architecture.md              # Internal architecture overview
├── cli-reference.md             # CLI documentation
├── configuration.md             # Configuration reference
├── creating-detectors.md        # Guide for creating custom detectors
├── llm-integration.md           # LLM agent integration guide
├── mcp-server.md               # MCP server documentation
├── output-formats.md           # Output format specifications
└── detectors/                  # Detector-specific documentation
    ├── README.md               # Detector overview
    ├── advanced-patterns.md    # Pattern detection
    ├── alt-implementation.md   # Alternative implementations
    ├── block-clone.md          # Block-level clones
    ├── circular-deps.md        # Circular dependencies
    ├── clone.md                # Code clones
    ├── complexity-hotspot.md   # Complexity analysis
    ├── dead-code.md            # Dead code detection
    ├── deprecated-api.md       # Deprecated API usage
    ├── inconsistent-api.md     # API consistency
    ├── security-smell.md       # Security issues
    ├── semantic-equivalence.md # Semantic equivalence
    └── stub-implementation.md  # Placeholder code detection
```
