# Stub Implementation Detector

The Stub Implementation Detector identifies placeholder, mock, fake, simulated, and fallback implementations in your Python codebase.

## Purpose

This detector helps maintain code quality by identifying temporary or placeholder implementations that may need to be completed before production deployment. It's particularly useful for:

- Finding TODO implementations that raise `NotImplementedError`
- Identifying mock/fake implementations used for testing
- Locating fallback implementations that might indicate incomplete features
- Discovering stub methods with placeholder return values

## What It Detects

### Stub Patterns
- Functions that only raise `NotImplementedError`
- Methods with names containing "stub", "mock", "fake", "simulate"
- Functions that return hardcoded placeholder values
- Methods with minimal placeholder implementations

### Code Examples

**Will be detected:**
```python
def process_payment(amount):
    """TODO: Implement payment processing"""
    raise NotImplementedError("Payment processing not implemented")

def mock_api_call(data):
    """Mock implementation for testing"""
    return {"status": "success", "mock": True}

def fallback_calculation(values):
    """Fallback when main algorithm fails"""
    return 0  # Placeholder return

class StubDatabaseManager:
    def save(self, data):
        pass  # Stub implementation
```

**Will NOT be detected:**
```python
def abstract_method(self):
    """Legitimate abstract method"""
    raise NotImplementedError("Subclasses must implement")

def validate_input(data):
    """Complete implementation"""
    if not data:
        raise ValueError("Data cannot be empty")
    return True
```

## Configuration

### Basic Configuration
```yaml
detectors:
  stub_implementation:
    enabled: true
```

### Advanced Configuration
```yaml
detectors:
  stub_implementation:
    enabled: true
    options:
      # Patterns to identify stub methods
      stub_keywords:
        - "stub"
        - "mock" 
        - "fake"
        - "simulate"
        - "placeholder"
      
      # Whether to check for NotImplementedError patterns
      check_not_implemented: true
      
      # Whether to flag functions with minimal implementations
      check_minimal_implementations: true
      
      # Minimum lines for a function to not be considered minimal
      min_implementation_lines: 2
```

## Severity

**Default:** `info`

This detector typically reports issues at the `info` level since stub implementations are often intentional during development phases.

## Integration Tips

### Development Workflow
- Use this detector before merging to production branches
- Include stub detection in code review processes
- Set up CI warnings for stub implementations in production code

### Filtering False Positives
- Use ignore patterns for legitimate test mocks
- Exclude testing directories if needed
- Configure custom patterns for your team's conventions

## Related Detectors

- **[Dead Code Detector](dead-code.md)** - May overlap with unused stub implementations
- **[Deprecated API Detector](deprecated-api.md)** - Can identify deprecated stub patterns

## Example Output

```
INFO: Function 'mock_user_auth' appears to be a stub implementation (contains 'mock') at line 45
INFO: Function 'process_payment' raises NotImplementedError at line 78  
INFO: Method 'fallback_method' returns hardcoded value: 0 at line 123
```

## Best Practices

1. **Use clear naming** for intentional stubs and mocks
2. **Add TODO comments** to stub implementations that need completion
3. **Exclude test directories** if they contain legitimate mocks
4. **Review regularly** to ensure stubs don't make it to production
5. **Document** the purpose of intentional stub implementations
