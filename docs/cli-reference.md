# CLI Reference

Complete command-line interface reference for Pythonium.

## Synopsis

```bash
pythonium [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

## Global Options

- `--version` - Show version and exit
- `--verbose, -v` - Enable verbose output
- `--config PATH` - Path to configuration file
- `--help` - Show help message

## Commands

### `crawl` - Analyze Code

Analyze Python source files for code health issues.

```bash
pythonium crawl [OPTIONS] [PATHS...]
```

#### Arguments

- `PATHS` - Paths to analyze (files or directories). If not specified, analyzes current directory.

#### Options

**Output Options:**
- `--format FORMAT` - Output format: `text`, `json`, `sarif`, `html` (default: `text`)
- `--output PATH, -o PATH` - Output file. If not specified, writes to stdout
- `--silent, -s` - Silent mode - only output issues, no progress messages

**Analysis Options:**
- `--detectors LIST, -d LIST` - Comma-separated list of detector IDs to run
- `--fail-on LEVEL` - Exit with non-zero status if issues of this severity or higher are found: `never`, `error`, `warn` (default: `error`)

**Available Detectors:**
- `dead_code` - Find unused code
- `clone` - Find duplicate code
- `security_smell` - Find security vulnerabilities
- `complexity_hotspot` - Find complex functions
- `alt_implementation` - Find alternative implementations
- `circular_deps` - Find circular dependencies
- `inconsistent_api` - Find API inconsistencies
- `deprecated_api` - Find deprecated API usage
- `block_clone` - Find duplicate code blocks
- `semantic_equivalence` - Find functionally equivalent code
- `advanced_patterns` - Find design patterns and opportunities

#### Examples

```bash
# Analyze current directory
pythonium crawl

# Analyze specific paths
pythonium crawl src/ lib/utils.py

# Use specific detectors only
pythonium crawl --detectors dead_code,security_smell

# Generate HTML report
pythonium crawl --format html --output report.html

# JSON output for CI/CD
pythonium crawl --format json --output results.json

# Silent mode (no progress messages)
pythonium crawl --silent

# Fail on warnings
pythonium crawl --fail-on warn

# Analyze with verbose output
pythonium crawl --verbose src/
```

### `list-detectors` - List Available Detectors

List all available detectors with descriptions.

```bash
pythonium list-detectors
```

#### Output Format

```
Available detectors:

  detector_id          [type]   Display Name
    Description line 1
    Description line 2

  dead_code            [core]   Dead Code Detector
    Finds code that is defined but never used

  clone                [core]   Clone Detector
    Finds duplicate and similar code blocks with configurable
    similarity threshold
```

#### Example

```bash
# List all detectors
pythonium list-detectors

# List detectors with configuration loaded
pythonium --config .pythonium.yml list-detectors
```

### `init-config` - Initialize Configuration

Create a default configuration file.

```bash
pythonium init-config [OPTIONS]
```

#### Options

- `--force, -f` - Overwrite existing configuration file if it exists
- `--output PATH, -o PATH` - Output path for config file (default: `.pythonium.yml` in current directory)

#### Examples

```bash
# Create default config
pythonium init-config

# Create config in specific location
pythonium init-config --output config/pythonium.yml

# Overwrite existing config
pythonium init-config --force

# Create config with specific output path and force overwrite
pythonium init-config --output .pythonium.yml --force
```

### `mcp-server` - Start MCP Server

Start Model Context Protocol server for AI agent integration.

```bash
pythonium mcp-server [OPTIONS]
```

#### Options

- `--transport TYPE` - Transport type: `stdio`, `sse` (default: `stdio`)
- `--host HOST` - Host for SSE transport (default: `localhost`)
- `--port PORT` - Port for SSE transport (default: `8000`)

#### Examples

```bash
# Start stdio server (for local AI agents)
pythonium mcp-server

# Start SSE server (for web-based agents)
pythonium mcp-server --transport sse --host 0.0.0.0 --port 8080
```

**Note:** Requires `mcp` optional dependency: `pip install pythonium[mcp]`

### `version` - Show Version

Show Pythonium version information.

```bash
pythonium version
```

## Exit Codes

- `0` - Success, no issues found (or issues below fail-on threshold)
- `1` - Issues found at or above fail-on threshold
- `2` - Error in analysis (file not found, permission denied, etc.)

## Configuration Loading

Pythonium loads configuration in this order:

1. Built-in defaults
2. Configuration file (`.pythonium.yml` in current directory)
3. Configuration file specified with `--config`
4. Environment variables
5. Command-line options

## Output Formats

### Text Format

Human-readable output showing issues with file location and description.

```
src/main.py:15:5: ERROR: Hardcoded password detected (security_smell)
src/utils.py:42: WARN: Function 'unused_helper' is defined but never used (dead_code)
```

### JSON Format

Machine-readable JSON output suitable for integration with other tools.

```json
[
  {
    "id": "security_smell.hardcoded_password",
    "severity": "error",
    "message": "Hardcoded password detected",
    "location": {
      "file": "src/main.py",
      "line": 15,
      "column": 5
    },
    "symbol": "main.authenticate",
    "metadata": {
      "detector_name": "Security Smell Detector",
      "pattern": "password\\s*=\\s*['\"]\\w+['\"]"
    }
  }
]
```

### SARIF Format

Static Analysis Results Interchange Format for integration with IDEs and security tools.

```json
{
  "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "Pythonium",
          "version": "0.1.0"
        }
      },
      "results": [...]
    }
  ]
}
```

### HTML Format

Interactive HTML dashboard with charts, filtering, and source code navigation.

```bash
pythonium crawl --format html --output report.html
```

Opens in browser showing:
- Issue summary and statistics
- Issues grouped by detector and severity
- Source code viewer with highlighted issues
- Filtering and search capabilities

## Environment Variables

Override configuration and behavior:

- `PYTHONIUM_CONFIG` - Path to configuration file
- `PYTHONIUM_LOG_LEVEL` - Log level: `DEBUG`, `INFO`, `WARN`, `ERROR`
- `PYTHONIUM_PARALLEL` - Enable/disable parallel processing: `true`, `false`
- `PYTHONIUM_CACHE_PATH` - Cache database path
- `PYTHONIUM_OUTPUT_FORMAT` - Default output format
- `PYTHONIUM_DETECTOR_*` - Enable/disable specific detectors

### Examples

```bash
# Use specific config file
export PYTHONIUM_CONFIG=/path/to/config.yml
pythonium crawl

# Enable debug logging
export PYTHONIUM_LOG_LEVEL=DEBUG
pythonium crawl --verbose

# Disable specific detector
export PYTHONIUM_DETECTOR_CLONE=false
pythonium crawl

# Use JSON output by default
export PYTHONIUM_OUTPUT_FORMAT=json
pythonium crawl
```

## Integration Examples

### CI/CD Pipeline

```bash
#!/bin/bash
# Run Pythonium in CI/CD pipeline

# Install Pythonium
pip install pythonium

# Run analysis
pythonium crawl \
    --format json \
    --output pythonium-results.json \
    --fail-on error \
    --silent \
    src/

# Exit code will be non-zero if errors found
echo "Analysis completed with exit code: $?"
```

### GitHub Actions

```yaml
name: Code Quality Check

on: [push, pull_request]

jobs:
  pythonium:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Pythonium
      run: pip install pythonium
    
    - name: Run Code Analysis
      run: |
        pythonium crawl \
          --format sarif \
          --output pythonium.sarif \
          --fail-on error
    
    - name: Upload SARIF
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: pythonium.sarif
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pythonium
        name: Pythonium Code Analysis
        entry: pythonium
        args: [crawl, --fail-on, error, --silent]
        language: system
        types: [python]
```

### Make Integration

```makefile
# Makefile
.PHONY: lint
lint:
	pythonium crawl --fail-on warn

.PHONY: security
security:
	pythonium crawl --detectors security_smell --fail-on error

.PHONY: report
report:
	pythonium crawl --format html --output report.html
	@echo "Report generated: report.html"
```

## Advanced Usage

### Custom Detector Selection

```bash
# Security-focused analysis
pythonium crawl --detectors security_smell,deprecated_api

# Code quality analysis
pythonium crawl --detectors dead_code,clone,complexity_hotspot

# Refactoring analysis
pythonium crawl --detectors clone,semantic_equivalence,advanced_patterns
```

### Incremental Analysis

```bash
# Analyze only changed files (requires git)
pythonium crawl --incremental

# Analyze changes since specific commit
pythonium crawl --since-commit abc123

# Analyze changes in current branch vs main
pythonium crawl --since-branch main
```

### Performance Optimization

```bash
# Use specific number of workers
pythonium crawl --workers 4

# Disable caching
pythonium crawl --no-cache

# Analyze only specific file patterns
pythonium crawl --include "*.py" --exclude "**/test_*.py"
```

## Troubleshooting

### Common Issues

1. **No issues found when expected**
   ```bash
   # Check if detectors are enabled
   pythonium list-detectors
   
   # Run with verbose output
   pythonium crawl --verbose
   
   # Check configuration
   pythonium crawl --show-config
   ```

2. **Permission errors**
   ```bash
   # Check file permissions
   ls -la .pythonium.yml
   
   # Use different cache location
   pythonium crawl --cache-path /path/to/project/.pythonium/cache.db
   ```

3. **Performance issues**
   ```bash
   # Reduce parallelism
   pythonium crawl --workers 1
   
   # Disable caching
   pythonium crawl --no-cache
   
   # Use more specific paths
   pythonium crawl src/ --exclude "tests/"
   ```

4. **Configuration problems**
   ```bash
   # Validate configuration
   pythonium init-config --validate
   
   # Use minimal config
   pythonium init-config --minimal
   
   # Show effective configuration
   pythonium crawl --show-config --verbose
   ```

### Debug Mode

```bash
# Enable debug logging
export PYTHONIUM_LOG_LEVEL=DEBUG
pythonium crawl --verbose

# Show detailed timing information
pythonium crawl --profile

# Show memory usage
pythonium crawl --memory-profile
```

### Getting Help

```bash
# Show general help
pythonium --help

# Show command-specific help
pythonium crawl --help
pythonium list-detectors --help
pythonium init-config --help

# Show version information
pythonium version
```
