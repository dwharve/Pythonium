# Configuration Guide

This guide covers how to configure Pythonium for your specific project needs through configuration files, environment variables, and command-line options.

## Configuration File

Pythonium uses YAML configuration files for project-specific settings. The default configuration file is `.pythonium.yml` in your project root.

### Creating a Configuration File

Generate a default configuration file:

```bash
pythonium init-config
```

This creates a `.pythonium.yml` file with all available options and their defaults.

### Basic Configuration Structure

```yaml
# Enable/disable specific detectors with their configuration
detectors:
  dead_code:
    enabled: true
    entry_points:
      - "main"
      - "app:main"
      - "__main__"
  
  clone:
    enabled: true
    similarity_threshold: 0.7
    min_lines: 5
    ignore_imports: true
    ignore_docstrings: true
    ignore_comments: true
    ignore_whitespace: true
  
  security_smell:
    enabled: true
    check_hardcoded_secrets: true
    check_dangerous_functions: true
    check_weak_crypto: true

# Set severity levels (overrides detector defaults)
severity:
  dead_code: "warn"
  clone: "error"           # High similarity clones are serious
  security_smell: "error"  # Potential vulnerabilities
  deprecated_api: "warn"

# Global ignore patterns (applied to all detectors)
ignore:
  - "**/tests/**"          # Test directories
  - "**/test_*.py"         # Test files
  - "**/*_test.py"         # Test files
  - "**/migrations/**"     # Database migrations
  - "**/venv/**"           # Virtual environments
  - "**/__pycache__/**"    # Python cache
```
  
  # Sort issues by severity
  sort_by_severity: true

# Performance settings
performance:
  # Enable parallel analysis
  parallel: true
  
  # Number of worker processes (0 = auto-detect)
  workers: 0
  
  # Enable caching
  cache_enabled: true
  
  # Cache location (relative to project root)
  cache_path: ".pythonium/cache.db"

# Integration settings
integration:
  # Git integration
  git:
    # Enable incremental analysis based on git changes
    incremental: true
    
    # Base branch for comparison
    base_branch: "main"
  
  # CI/CD settings
  ci:
    # Fail on specific severity levels
    fail_on: "error"  # never, error, warn, info
    
    # Generate reports for CI
    generate_reports: true
```

## Detector-Specific Configuration

### Dead Code Detector

```yaml
detectors:
  dead_code:
    enabled: true
    entry_points:
      - "main"
      - "app:main"
      - "__main__"
```

### Clone Detector

```yaml
detectors:
  clone:
    enabled: true
    similarity_threshold: 0.7
    min_lines: 5
    ignore_imports: true
    ignore_docstrings: true
    ignore_comments: true
    ignore_whitespace: true
```

### Security Smell Detector

```yaml
detectors:
  security_smell:
    enabled: true
    
    # Built-in checks
    check_hardcoded_secrets: true
    check_sql_injection: true
    check_weak_crypto: true
    check_unsafe_eval: true
    check_path_traversal: true
    
    # Custom security patterns
    custom_patterns:
      - pattern: "password\\s*=\\s*['\"]\\w+['\"]"
        message: "Hardcoded password detected"
        severity: "error"
      
      - pattern: "api_key\\s*=\\s*['\"][^'\"]+['\"]"
        message: "Hardcoded API key detected"
        severity: "error"
    
    # Exclude patterns
    exclude_patterns:
      - "**/test_*.py"
      - "**/example_*.py"
```

### Complexity Detector

```yaml
detectors:
  complexity_hotspot:
    enabled: true
    
    # Cyclomatic complexity threshold
    max_complexity: 10
    
    # Lines of code threshold
    max_lines: 50
    
    # Cognitive complexity threshold
    max_cognitive_complexity: 15
    
    # Nesting depth threshold
    max_nesting_depth: 4
    
    # Parameter count threshold
    max_parameters: 6
```

### Block Clone Detector

```yaml
detectors:
  block_clone:
    enabled: true
    
    # Minimum statements in a block
    min_statements: 3
    
    # Maximum statements to consider
    max_statements: 20
    
    # Similarity threshold
    similarity_threshold: 0.9
    
    # Detect clones within same function
    intra_function: true
    
    # Detect clones across functions
    inter_function: true
```

## Environment Variables

Override configuration using environment variables:

```bash
# Enable/disable specific detectors
export PYTHONIUM_DETECTOR_DEAD_CODE=true
export PYTHONIUM_DETECTOR_CLONE=false

# Set output format
export PYTHONIUM_OUTPUT_FORMAT=json

# Set cache location
export PYTHONIUM_CACHE_PATH=/path/to/project/.pythonium/cache.db

# Set log level
export PYTHONIUM_LOG_LEVEL=DEBUG

# Disable parallel processing
export PYTHONIUM_PARALLEL=false
```

## Command-Line Overrides

Command-line options override both configuration files and environment variables:

```bash
# Run specific detectors only
pythonium crawl --detectors dead_code,security_smell

# Override output format
pythonium crawl --format json --output results.json

# Override fail-on setting
pythonium crawl --fail-on warn

# Silent mode (minimal output)
pythonium crawl --silent

# Verbose output
pythonium crawl --verbose
```

## Configuration Precedence

Configuration is applied in this order (later overrides earlier):

1. **Built-in defaults**
2. **Configuration file** (`.pythonium.yml`)
3. **Environment variables**
4. **Command-line options**

## Advanced Configuration

### Custom Detector Settings

```yaml
detectors:
  # Configure any detector by its ID
  my_custom_detector:
    enabled: true
    custom_option: "value"
    threshold: 0.8
```

### Path Configuration

```yaml
analysis:
  # Use glob patterns for include/exclude
  include:
    - "src/**/*.py"
    - "lib/**/*.py"
  
  exclude:
    - "**/__pycache__/**"
    - "**/test_*.py"
    - "build/**"
    - "dist/**"
  
  # Follow symbolic links
  follow_symlinks: false
  
  # Include hidden files
  include_hidden: false
```

### Output Customization

```yaml
output:
  # Custom output template for text format
  text_template: "{file}:{line}: {severity}: {message}"
  
  # Include metadata in JSON output
  include_metadata: true
  
  # Pretty-print JSON output
  pretty_json: true
  
  # HTML report customization
  html:
    title: "Code Analysis Report"
    include_source: true
    theme: "dark"  # light, dark
```

### Performance Tuning

```yaml
performance:
  # Memory limits
  max_memory_mb: 1024
  
  # Processing limits
  max_files: 10000
  max_file_size: 1048576  # 1MB
  
  # Cache settings
  cache_ttl: 86400  # 24 hours in seconds
  cache_cleanup_interval: 3600  # 1 hour
```

## Validation

Validate your configuration file:

```bash
# Check configuration syntax
pythonium init-config --validate

# Show effective configuration
pythonium crawl --show-config
```

## Examples

### Minimal Configuration

```yaml
detectors:
  dead_code:
    enabled: true
  security_smell:
    enabled: true

severity:
  dead_code: "warn"
  security_smell: "error"
```

### Enterprise Configuration

```yaml
project:
  name: "Enterprise Application"
  version: "2.1.0"

analysis:
  include:
    - "src/"
    - "api/"
  exclude:
    - "tests/"
    - "migrations/"
    - "static/"

detectors:
  dead_code:
    enabled: true
    entry_points:
      - "main"
      - "wsgi:application"
      - "celery:app"
  
  clone:
    enabled: true
    similarity_threshold: 0.85
    min_lines: 8
  
  security_smell:
    enabled: true
    check_all: true
    custom_patterns:
      - pattern: "SECRET_KEY\\s*=\\s*['\"][^'\"]+['\"]"
        message: "Hardcoded secret key"
        severity: "error"
  
  complexity_hotspot:
    enabled: true
    max_complexity: 8
    max_lines: 40

severity:
  dead_code: "warn"
  clone: "error"
  security_smell: "error"
  complexity_hotspot: "warn"

output:
  format: "json"
  include_source: true
  max_issues: 500

performance:
  parallel: true
  workers: 4
  cache_enabled: true

integration:
  ci:
    fail_on: "error"
    generate_reports: true
```

## Troubleshooting

### Common Issues

1. **Configuration not loading**
   - Check file location (should be in project root)
   - Verify YAML syntax
   - Check file permissions

2. **Detectors not working as expected**
   - Verify detector IDs in configuration
   - Check if detectors are enabled
   - Review threshold settings

3. **Performance issues**
   - Reduce number of workers
   - Increase file size limits
   - Enable caching
   - Use more specific include/exclude patterns

### Debug Configuration

```bash
# Show effective configuration
pythonium crawl --verbose --show-config

# Validate configuration file
pythonium init-config --validate .pythonium.yml

# Test with minimal configuration
pythonium crawl --detectors dead_code --format text
```
