# Detector Documentation

This directory contains comprehensive documentation for all Pythonium detectors, their capabilities, configuration options, and usage examples.

## Overview

Pythonium includes 12 core detectors that analyze different aspects of Python code quality:

| Detector | Category | Purpose | Typical Severity |
|----------|----------|---------|------------------|
| [Dead Code](dead-code.md) | Code Quality | Find unused code | warn |
| [Clone Detector](clone.md) | Duplication | Find duplicate code | warn |
| [Security Smell](security-smell.md) | Security | Find vulnerabilities | error |
| [Complexity Hotspot](complexity-hotspot.md) | Code Quality | Find complex code | warn |
| [Circular Dependencies](circular-deps.md) | Architecture | Find import cycles | error |
| [Inconsistent API](inconsistent-api.md) | Architecture | Find API inconsistencies | warn |
| [Alternative Implementation](alt-implementation.md) | Architecture | Find competing implementations | warn |
| [Deprecated API](deprecated-api.md) | Maintenance | Find deprecated usage | warn |
| [Block Clone](block-clone.md) | Duplication | Find duplicate blocks | warn |
| [Semantic Equivalence](semantic-equivalence.md) | Code Quality | Find equivalent implementations | info |
| [Advanced Patterns](advanced-patterns.md) | Architecture | Find design patterns | info |
| [Stub Implementation](stub-implementation.md) | Code Quality | Find placeholder code | info |

## Quick Reference

### By Use Case

**Security Review:**
- [Security Smell Detector](security-smell.md) - Find hardcoded secrets, SQL injection risks
- [Deprecated API Detector](deprecated-api.md) - Find usage of deprecated functions

**Code Quality:**
- [Dead Code Detector](dead-code.md) - Remove unused functions and variables
- [Complexity Hotspot Detector](complexity-hotspot.md) - Identify overly complex functions
- [Semantic Equivalence Detector](semantic-equivalence.md) - Find better implementations
- [Stub Implementation Detector](stub-implementation.md) - Find placeholder code

**Refactoring:**
- [Clone Detector](clone.md) - Identify duplicate code for extraction
- [Block Clone Detector](block-clone.md) - Find smaller duplicate blocks
- [Alternative Implementation Detector](alt-implementation.md) - Spot competing solutions

**Architecture:**
- [Circular Dependencies Detector](circular-deps.md) - Fix import cycles
- [Inconsistent API Detector](inconsistent-api.md) - Standardize interfaces
- [Advanced Patterns Detector](advanced-patterns.md) - Improve design patterns

### By Severity

**Error Level (Fix Immediately):**
- Security vulnerabilities
- Circular dependencies

**Warning Level (Fix Soon):**
- Dead code
- High complexity
- API inconsistencies
- Deprecated API usage
- Code clones
- Alternative implementations

**Info Level (Consider Improving):**
- Design pattern opportunities
- Semantic equivalence suggestions
- Stub implementations

## Configuration Examples

### Comprehensive Setup

```yaml
# .pythonium.yml
detectors:
  # Security (highest priority)
  security_smell:
    enabled: true
    check_hardcoded_secrets: true
    check_sql_injection: true
    check_weak_crypto: true
  
  deprecated_api:
    enabled: true
    check_version_compatibility: true
  
  # Code quality
  dead_code:
    enabled: true
    entry_points:
      - "main"
      - "app:create_app"
    ignore_patterns:
      - "**/test_*.py"
  
  complexity_hotspot:
    enabled: true
    max_complexity: 10
    max_lines: 50
  
  # Duplication
  clone:
    enabled: true
    similarity_threshold: 0.9
    min_lines: 5
  
  block_clone:
    enabled: true
    min_statements: 3
    similarity_threshold: 0.85
  
  # Architecture
  circular_deps:
    enabled: true
    max_cycle_length: 5
  
  inconsistent_api:
    enabled: true
    check_parameter_order: true
    check_naming_conventions: true

# Severity overrides
severity:
  security_smell: "error"
  deprecated_api: "error"
  dead_code: "warn"
  clone: "error"
  circular_deps: "error"
  complexity_hotspot: "warn"
  inconsistent_api: "warn"
  block_clone: "warn"
  semantic_equivalence: "info"
  alt_implementation: "info"
  advanced_patterns: "info"
```

### Project-Specific Configurations

#### Web Application

```yaml
# Focus on security and API consistency
detectors:
  security_smell:
    enabled: true
    check_all: true
  
  deprecated_api:
    enabled: true
    
  inconsistent_api:
    enabled: true
    enforce_rest_conventions: true
  
  dead_code:
    enabled: true
    entry_points:
      - "app:create_app"
      - "wsgi:application"
```

#### Data Science Project

```yaml
# Focus on code quality and performance
detectors:
  complexity_hotspot:
    enabled: true
    max_complexity: 8  # Stricter for data processing
  
  semantic_equivalence:
    enabled: true
    detect_builtin_equivalents: true
  
  clone:
    enabled: true
    min_lines: 3  # Shorter clones acceptable in notebooks
  
  dead_code:
    enabled: true
    ignore_patterns:
      - "**/*.ipynb"  # Skip notebooks
```

#### Library/Package

```yaml
# Focus on API design and maintainability
detectors:
  inconsistent_api:
    enabled: true
    strict_mode: true
  
  deprecated_api:
    enabled: true
    check_docstring_warnings: true
  
  advanced_patterns:
    enabled: true
    detect_design_patterns: true
  
  alt_implementation:
    enabled: true
    similarity_threshold: 0.8
```

## Integration Workflows

### Development Workflow

1. **Local Development**: Use dead code and complexity detectors
2. **Pre-commit**: Run security and deprecated API checks
3. **Code Review**: Full analysis with all detectors
4. **Release**: Final security and quality verification

### CI/CD Integration

```bash
# Security gate (fast)
pythonium crawl --detectors security_smell,deprecated_api --fail-on error

# Quality gate (comprehensive)
pythonium crawl --fail-on warn --format sarif --output results.sarif

# Documentation
pythonium crawl --format html --output reports/quality-report.html
```

## Detector Performance

### Execution Time (relative)

| Detector | Speed | Memory | Notes |
|----------|-------|--------|-------|
| Dead Code | Fast | Low | Quick symbol analysis |
| Security Smell | Fast | Low | Pattern matching |
| Complexity | Fast | Low | AST traversal only |
| Clone | Medium | Medium | Text comparison algorithms |
| Block Clone | Medium | Medium | Detailed AST analysis |
| Circular Deps | Medium | Low | Graph algorithms |
| Semantic Equivalence | Slow | Medium | Complex pattern matching |
| Advanced Patterns | Slow | High | Comprehensive analysis |
| Alternative Implementation | Slow | High | Cross-function comparison |
| Inconsistent API | Fast | Low | Signature analysis |
| Deprecated API | Fast | Low | Pattern matching |

### Optimization Tips

**For Large Codebases:**
- Start with fast detectors (security, dead code, complexity)
- Use specific detector selection: `--detectors security_smell,dead_code`
- Enable caching for repeated analysis
- Use parallel processing: `--workers 4`

**For CI/CD:**
- Split into fast security check and comprehensive quality check
- Use incremental analysis for changed files only
- Cache results between builds

## Common Issues and Solutions

### False Positives

**Dead Code:**
- Configure entry points properly
- Use ignore patterns for test files
- Check for dynamic imports

**Security Smell:**
- Exclude test files and examples
- Use custom patterns for domain-specific issues
- Configure severity levels appropriately

**Clone Detection:**
- Adjust similarity thresholds
- Consider minimum line requirements
- Exclude generated code

### Performance Issues

**Slow Analysis:**
- Reduce detector scope
- Use file size limits
- Enable parallel processing
- Check for large files or complex ASTs

**Memory Usage:**
- Process files in batches
- Use streaming for large projects
- Clear caches between runs

## Contributing

### Adding Detector Documentation

When adding a new detector, create documentation following this template:

```markdown
# Detector Name

Brief description of what the detector finds.

## Purpose

Detailed explanation of the detector's purpose and benefits.

## Configuration

Available configuration options with examples.

## Examples

Code examples showing what the detector finds.

## Integration

How to use this detector effectively.

## Related Detectors

Links to complementary detectors.
```

### Testing Detector Documentation

Ensure all examples in documentation work:

```bash
# Test configuration examples
pythonium init-config --validate examples/detector-config.yml

# Test command examples
pythonium crawl examples/ --detectors your_detector
```

## See Also

- [Creating Custom Detectors](../creating-detectors.md) - Guide for building new detectors
- [Configuration Guide](../configuration.md) - Complete configuration reference
- [CLI Reference](../cli-reference.md) - Command-line usage
- [API Reference](../api-reference.md) - Programmatic usage
