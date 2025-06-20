# Dead Code Detector

The Dead Code Detector identifies code that is defined but never used, helping to clean up codebases and reduce maintenance overhead.

## What it Detects

- Unused functions, classes, and methods
- Unreferenced variables and constants
- Imports that are never used
- Dead code blocks after early returns
- Unused parameters in function definitions

## When to Use

- **Code cleanup phases**: Remove unused code before releases
- **Refactoring projects**: Identify safe-to-remove code
- **Code reviews**: Ensure new code doesn't introduce unused elements
- **Legacy code maintenance**: Find and remove obsolete functionality

## Configuration Options

```yaml
detectors:
  dead_code:
    # Minimum confidence threshold (0.0-1.0)
    confidence_threshold: 0.8
    
    # Whether to include unused imports
    include_imports: true
    
    # Whether to include unused parameters
    include_parameters: false
    
    # Patterns to exclude from analysis
    exclude_patterns:
      - "test_*"
      - "__*__"
```

## Example Output

```
[ERROR] Dead Code: Unused function 'calculate_legacy_tax'
  File: src/calculations.py:45
  Function defined but never called
  
[WARN] Dead Code: Unused import 'datetime'
  File: src/utils.py:3
  Import never referenced in module
  
[INFO] Dead Code: Unused variable 'temp_result'
  File: src/processor.py:23
  Variable assigned but never used
```

## Common Patterns Detected

### Unused Functions
```python
def legacy_function():  # Detected as dead code
    return "old implementation"

def current_function():
    return "new implementation"

# Only current_function() is called
result = current_function()
```

### Unused Imports
```python
import os  # Used
import sys  # Dead code - never referenced
from typing import List  # Dead code - never used

def get_files():
    return os.listdir('.')
```

### Unreachable Code
```python
def process_data(data):
    if not data:
        return None
    
    # This code is reachable
    result = transform(data)
    return result
    
    # This code is dead - unreachable
    print("This will never execute")
```

## Best Practices

1. **Run regularly**: Include dead code detection in CI/CD pipelines
2. **Review carefully**: Some "unused" code might be API endpoints or callbacks
3. **Consider test coverage**: Dead code detection complements test coverage analysis
4. **Handle false positives**: Use exclude patterns for intentionally unused code

## Integration Examples

### Command Line
```bash
# Analyze only for dead code
pythonium crawl --detectors dead_code src/

# Focus on unused imports
pythonium crawl --detectors dead_code --config dead_code.confidence_threshold=0.9 src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["dead_code"],
    config={
        "dead_code": {
            "confidence_threshold": 0.8,
            "include_imports": True
        }
    }
)

for issue in results.get_issues("dead_code"):
    print(f"Dead code found: {issue.description}")
```

## Related Detectors

- **Complexity Hotspot**: Complex unused code is especially wasteful
- **Clone**: Duplicated dead code compounds the problem
- **Deprecated API**: Dead code using deprecated APIs should be prioritized for removal

## Troubleshooting

**High false positive rate?**
- Increase `confidence_threshold`
- Add exclude patterns for dynamic imports
- Consider framework-specific conventions

**Missing obvious dead code?**
- Lower `confidence_threshold` 
- Check if code is referenced through dynamic calls
- Verify analysis includes all relevant files
