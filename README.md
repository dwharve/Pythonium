# Pythonium

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive static analysis tool for identifying and reporting code health issues in Python projects. Designed for developers who want to maintain high-quality, maintainable codebases.

## 🚀 Features

### Core Detectors
- **Dead Code Detection**: Identify unused functions, classes, and modules
- **Code Clone Detection**: Find exact and near-duplicate code blocks
- **Alternative Implementation Detection**: Spot competing patterns and duplicate effort
- **Circular Dependency Detection**: Identify import cycles and dependency tangles
- **Complexity Hotspots**: Flag functions with high cyclomatic complexity
- **Security Smell Detection**: Find potential security vulnerabilities
- **API Consistency Checks**: Enforce consistent coding patterns
- **Deprecated API Detection**: Find usage of deprecated functions and patterns
- **Block-Level Clone Detection**: Find duplicate code blocks within and across functions
- **Semantic Equivalence Detection**: Identify functionally equivalent code implemented differently
- **Advanced Pattern Recognition**: Detect algorithmic patterns and design pattern opportunities

### Capabilities  
- **🤖 MCP Integration**: Model Context Protocol support for LLM agents
- **📊 Multiple Output Formats**: Text, JSON, SARIF, HTML reports
- **⚙️ Configurable Rules**: Customize thresholds and detector behavior
- **🔌 Extensible Architecture**: Plugin system for custom detectors
- **🏃‍♂️ Fast Analysis**: Efficient parsing and analysis engine
- **💾 Persistent Caching**: SQLite cache in project root for fast incremental analysis

## 📦 Installation

```bash
# Basic installation
pip install pythonium

# With MCP support for LLM agents
pip install pythonium[mcp]

# Development installation
pip install pythonium[dev]
```

## 🏁 Quick Start

### Command Line Usage

```bash
# Analyze your Python project
pythonium crawl /path/to/your/project

# Generate HTML dashboard
pythonium crawl myproject/ --format html --output report.html

# Focus on specific issues
pythonium crawl myproject/ --fail-on error

# Run specific detectors only
pythonium crawl myproject/ --detectors dead_code,security_smell

# List available detectors
pythonium list-detectors

# Use JSON output for CI/CD integration
pythonium crawl myproject/ --format json --output issues.json

# Create default configuration file
pythonium init-config
```

### MCP Server for LLM Agents

```bash
# Start MCP server with stdio transport
pythonium mcp-server --transport stdio

# Start MCP server with SSE transport (HTTP)
pythonium mcp-server --transport sse --host localhost --port 8000
```

### Python API

```python
from pythonium import Analyzer
from pathlib import Path

# Initialize analyzer
analyzer = Analyzer(root_path=Path("myproject/"))

# Run analysis
issues = analyzer.analyze()

# Process results
for issue in issues:
    print(f"{issue.severity}: {issue.message}")
    if issue.location:
        print(f"  Location: {issue.location}")
```

## Configuration

Create a `.pythonium.yml` file in your project root:

```yaml
# Enable/disable specific detectors with configuration
detectors:
  dead_code:
    enabled: true
    entry_points:
      - "main"
      - "app:main"
  clone:
    enabled: true
    similarity_threshold: 0.9  # 1.0 for exact clones, <1.0 for near clones
    min_lines: 5
  block_clone:
    enabled: true
    min_statements: 3
    similarity_threshold: 0.9
  semantic_equivalence:
    enabled: true
    detect_builtin_equivalents: true
    min_confidence: 0.7
  advanced_patterns:
    enabled: true
    detect_design_patterns: true
    detect_algorithmic_patterns: true
    similarity_threshold: 0.8
  security_smell:
    enabled: true
    check_hardcoded_secrets: true
    check_sql_injection: true
  complexity_hotspot:
    enabled: true
    max_complexity: 10
  inconsistent_api:
    enabled: false

# Set severity levels
severity:
  dead_code: "warn"
  clone: "error"
  block_clone: "warn"
  semantic_equivalence: "info"
  advanced_patterns: "info"
  security_smell: "error"
  complexity_hotspot: "warn"
```

## 📚 Documentation

For comprehensive documentation, see the [`docs/`](docs/) directory:

- **[Creating Custom Detectors](docs/creating-detectors.md)** - Complete guide to writing custom detectors
- **[Documentation Index](docs/README.md)** - Full documentation structure and links

## Development

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest
   ```

## License

MIT - See [LICENSE](LICENSE) for details.
