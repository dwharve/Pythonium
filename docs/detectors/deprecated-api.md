# Deprecated API Detector

The Deprecated API Detector identifies usage of deprecated APIs, functions, and libraries, helping plan migrations and modernization efforts.

## What it Detects

- Usage of deprecated Python built-in functions
- Deprecated third-party library APIs
- Functions marked with deprecation decorators
- Import statements for deprecated modules
- Usage of deprecated language features
- Custom deprecation patterns specific to your codebase

## When to Use

- **Migration planning**: Assess scope of required updates
- **Dependency updates**: Before upgrading major library versions
- **Security audits**: Deprecated APIs may have known vulnerabilities
- **Modernization projects**: Systematically update legacy code
- **Compliance requirements**: Some standards prohibit deprecated APIs

## Configuration Options

```yaml
detectors:
  deprecated_api:
    # Built-in Python deprecation patterns
    check_python_builtins: true
    
    # Third-party library deprecations
    check_third_party: true
    
    # Custom deprecation patterns
    custom_patterns:
      - "old_function_name"
      - "legacy_.*"  # Regex patterns supported
    
    # Deprecation decorator patterns
    deprecation_decorators:
      - "@deprecated"
      - "@deprecation.deprecated"
      - "@warnings.deprecated"
    
    # Minimum Python version to check against
    target_python_version: "3.9"
    
    # Include severity levels
    include_severity: true
    
    # Exclude test files from warnings
    exclude_test_files: false
```

## Example Output

```
[ERROR] Deprecated API: Usage of deprecated function
  File: src/utils.py:23
  Function: imp.load_source() (deprecated since Python 3.4)
  Replacement: Use importlib.util.spec_from_file_location() instead
  
[WARN] Deprecated API: Deprecated library import
  File: src/authentication.py:5
  Import: from cgi import escape (deprecated since Python 3.8)
  Replacement: Use html.escape() instead
  
[INFO] Deprecated API: Custom deprecated function
  File: src/legacy.py:45
  Function: calculate_old_way() marked with @deprecated
  Replacement: Use calculate_new_way() instead
```

## Common Deprecated Patterns

### Python Built-in Deprecations
```python
# Deprecated Python built-ins
import imp  # Deprecated in Python 3.4
imp.load_source('module', 'path.py')

# Modern replacement
import importlib.util
spec = importlib.util.spec_from_file_location("module", "path.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Deprecated CGI escape
from cgi import escape  # Deprecated in Python 3.8
escaped = escape(user_input)

# Modern replacement
import html
escaped = html.escape(user_input)

# Deprecated distutils
from distutils.version import LooseVersion  # Deprecated in Python 3.10

# Modern replacement
from packaging import version
ver = version.parse("1.2.3")
```

### Third-party Library Deprecations
```python
# Deprecated pandas methods
import pandas as pd
df = pd.DataFrame(data)
result = df.append(other_df)  # Deprecated in pandas 1.4.0

# Modern replacement
result = pd.concat([df, other_df], ignore_index=True)

# Deprecated sklearn API
from sklearn.cross_validation import train_test_split  # Deprecated

# Modern replacement
from sklearn.model_selection import train_test_split

# Deprecated requests functionality
import requests
response = requests.get(url, verify=False)  # Deprecated security practice

# Modern approach
response = requests.get(url, verify=True)  # Or configure proper certificates
```

### Custom Deprecation Markers
```python
import warnings
from functools import wraps

def deprecated(reason="This function is deprecated"):
    """Decorator to mark functions as deprecated."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {reason}",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage of deprecated function
@deprecated("Use calculate_new_way() instead")
def calculate_old_way(data):
    # Legacy implementation
    return sum(data) / len(data)

def calculate_new_way(data):
    # Modern implementation with better error handling
    if not data:
        raise ValueError("Data cannot be empty")
    return statistics.mean(data)

# Deprecated function call (detected)
result = calculate_old_way([1, 2, 3, 4, 5])
```

### Language Feature Deprecations
```python
# Deprecated string formatting
name = "Alice"
age = 30
message = "Hello, %s! You are %d years old." % (name, age)  # Old style

# Modern replacement with f-strings (Python 3.6+)
message = f"Hello, {name}! You are {age} years old."

# Deprecated exception syntax (Python 2 style)
try:
    risky_operation()
except ValueError, e:  # Old syntax
    handle_error(e)

# Modern exception handling
try:
    risky_operation()
except ValueError as e:
    handle_error(e)
```

## Migration Strategies

### Gradual Migration Plan
```python
# Phase 1: Add new implementations alongside old ones
def calculate_stats_old(data):
    """Deprecated: Use calculate_stats() instead."""
    warnings.warn("calculate_stats_old is deprecated", DeprecationWarning)
    return calculate_stats(data)

def calculate_stats(data):
    """Modern implementation with better error handling."""
    if not data:
        raise ValueError("Data cannot be empty")
    
    import statistics
    return {
        'mean': statistics.mean(data),
        'median': statistics.median(data),
        'stdev': statistics.stdev(data) if len(data) > 1 else 0
    }

# Phase 2: Update all callers
# Phase 3: Remove deprecated function
```

### Wrapper for Compatibility
```python
# Create compatibility layer for major API changes
class ModernAPIWrapper:
    """Wrapper providing backward compatibility for deprecated API."""
    
    def __init__(self):
        self._modern_impl = ModernImplementation()
    
    def old_method(self, *args, **kwargs):
        """Deprecated method with compatibility wrapper."""
        warnings.warn(
            "old_method is deprecated, use new_method instead",
            DeprecationWarning,
            stacklevel=2
        )
        # Transform old API calls to new API
        transformed_args = self._transform_args(args, kwargs)
        return self._modern_impl.new_method(**transformed_args)
    
    def _transform_args(self, args, kwargs):
        """Transform deprecated arguments to modern format."""
        # Implementation specific to your API changes
        pass
```

### Automated Migration Scripts
```python
import ast
import re
from pathlib import Path

class DeprecationFixer(ast.NodeTransformer):
    """AST transformer to automatically fix some deprecations."""
    
    def visit_ImportFrom(self, node):
        # Fix deprecated imports
        if node.module == 'cgi' and any(alias.name == 'escape' for alias in node.names):
            # Replace with html.escape import
            return ast.ImportFrom(
                module='html',
                names=[ast.alias(name='escape', asname=None)],
                level=0
            )
        return node
    
    def visit_Call(self, node):
        # Fix deprecated function calls
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'df' and 
                node.func.attr == 'append'):
                # Transform df.append() to pd.concat()
                return self._transform_to_concat(node)
        return node
    
    def _transform_to_concat(self, node):
        # Implementation to transform append() to concat()
        pass

def fix_deprecated_code(file_path):
    """Automatically fix some deprecated patterns in a file."""
    with open(file_path, 'r') as f:
        source = f.read()
    
    tree = ast.parse(source)
    fixer = DeprecationFixer()
    new_tree = fixer.visit(tree)
    
    # Convert back to source code
    import astor
    new_source = astor.to_source(new_tree)
    
    with open(file_path, 'w') as f:
        f.write(new_source)
```

## Deprecation Timeline Management

### Version-based Deprecation
```python
import sys
from packaging import version

def check_python_version_deprecation():
    """Check for Python version-specific deprecations."""
    current_version = version.parse(f"{sys.version_info.major}.{sys.version_info.minor}")
    
    deprecation_schedule = {
        version.parse("3.8"): ["cgi.escape", "imp module"],
        version.parse("3.9"): ["distutils.version.LooseVersion"],
        version.parse("3.10"): ["distutils package"],
        version.parse("3.11"): ["asyncio.coroutine decorator"],
    }
    
    active_deprecations = []
    for deprecated_version, items in deprecation_schedule.items():
        if current_version >= deprecated_version:
            active_deprecations.extend(items)
    
    return active_deprecations
```

### Library Version Tracking
```python
import pkg_resources

def check_library_deprecations():
    """Check for library-specific deprecations based on installed versions."""
    
    deprecation_map = {
        'pandas': {
            '1.4.0': ['DataFrame.append', 'Series.append'],
            '1.5.0': ['DataFrame.groupby.apply with axis'],
        },
        'sklearn': {
            '0.24.0': ['sklearn.cross_validation'],
            '1.0.0': ['sklearn.utils.testing'],
        }
    }
    
    active_deprecations = []
    
    for package_name, version_map in deprecation_map.items():
        try:
            installed_version = pkg_resources.get_distribution(package_name).version
            installed_ver = version.parse(installed_version)
            
            for deprecated_version, deprecated_items in version_map.items():
                if installed_ver >= version.parse(deprecated_version):
                    active_deprecations.extend([
                        f"{package_name}: {item}" for item in deprecated_items
                    ])
        except pkg_resources.DistributionNotFound:
            continue
    
    return active_deprecations
```

## Best Practices

1. **Prioritize by impact**: Fix security-related deprecations first
2. **Plan migration phases**: Don't try to fix everything at once
3. **Test thoroughly**: Ensure replacements maintain the same behavior
4. **Document changes**: Keep track of what was changed and why
5. **Use deprecation warnings**: Add warnings before removing old APIs

## Integration Examples

### Command Line
```bash
# Check for deprecated APIs
pythonium crawl --detectors deprecated_api src/

# Target specific Python version
pythonium crawl --detectors deprecated_api --config deprecated_api.target_python_version="3.10" src/

# Focus on third-party deprecations
pythonium crawl --detectors deprecated_api --config deprecated_api.check_python_builtins=false src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["deprecated_api"],
    config={
        "deprecated_api": {
            "target_python_version": "3.9",
            "check_third_party": True,
            "include_severity": True
        }
    }
)

# Categorize by severity and plan migration
critical_deps = []
warning_deps = []
info_deps = []

for issue in results.get_issues("deprecated_api"):
    severity = issue.severity.upper() if hasattr(issue, 'severity') else 'UNKNOWN'
    
    if severity == 'ERROR':
        critical_deps.append(issue)
    elif severity == 'WARN':
        warning_deps.append(issue)
    else:
        info_deps.append(issue)

print(f"Critical deprecations (fix immediately): {len(critical_deps)}")
print(f"Warning deprecations (fix soon): {len(warning_deps)}")
print(f"Info deprecations (fix when convenient): {len(info_deps)}")

# Generate migration plan
migration_plan = {
    "phase_1_critical": [issue.description for issue in critical_deps],
    "phase_2_warnings": [issue.description for issue in warning_deps],
    "phase_3_info": [issue.description for issue in info_deps]
}
```

### CI/CD Integration
```yaml
# .github/workflows/deprecation-check.yml
name: Deprecation Analysis
on: [push, pull_request]

jobs:
  check_deprecations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install Pythonium
        run: pip install pythonium
      - name: Check for Critical Deprecations
        run: |
          pythonium crawl --detectors deprecated_api --output json --file deprecations.json src/
          # Fail if critical deprecations found
          if grep -q '"severity": "ERROR"' deprecations.json; then
            echo "Critical deprecations found - failing build"
            exit 1
          fi
      - name: Upload Deprecation Report
        uses: actions/upload-artifact@v2
        with:
          name: deprecation-report
          path: deprecations.json
```

## Related Detectors

- **Security Smell**: Deprecated APIs may have security vulnerabilities
- **Dead Code**: Some deprecated code may also be unused
- **Alternative Implementation**: Deprecated and new implementations may coexist

## Troubleshooting

**False positives on custom functions?**
- Adjust `custom_patterns` to be more specific
- Use exclude patterns for internal APIs
- Check deprecation decorator configuration

**Missing known deprecations?**
- Update `target_python_version` to latest
- Enable third-party library checking
- Add custom patterns for project-specific deprecations

**Performance issues with large codebases?**
- Disable less critical checks temporarily
- Focus on specific file patterns
- Run analysis on changed files only in CI/CD
