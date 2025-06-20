# Complexity Hotspot Detector

The Complexity Hotspot Detector identifies functions and classes with excessive cyclomatic complexity, helping prioritize refactoring efforts and improve code maintainability.

## What it Detects

- Functions with high cyclomatic complexity
- Long functions exceeding line limits
- Deeply nested code structures
- Functions with too many parameters
- Classes with excessive method counts
- Complex conditional logic

## When to Use

- **Refactoring planning**: Identify the most complex code first
- **Code review focus**: Concentrate review effort on complex areas
- **Maintenance prediction**: Complex code is harder to maintain
- **Performance optimization**: Complex code often has performance issues

## Configuration Options

```yaml
detectors:
  complexity_hotspot:
    # Maximum cyclomatic complexity before flagging
    max_complexity: 10
    
    # Maximum function length in lines
    max_function_lines: 50
    
    # Maximum number of parameters
    max_parameters: 5
    
    # Maximum nesting depth
    max_nesting_depth: 4
    
    # Maximum methods per class
    max_methods_per_class: 20
    
    # Include complexity score in output
    include_metrics: true
```

## Example Output

```
[ERROR] Complexity Hotspot: Function has excessive cyclomatic complexity
  File: src/processor.py:45
  Function: process_complex_data
  Complexity: 15 (threshold: 10)
  Consider breaking into smaller functions
  
[WARN] Complexity Hotspot: Function is too long
  File: src/handlers.py:123
  Function: handle_request
  Lines: 67 (threshold: 50)
  Consider extracting helper methods
  
[INFO] Complexity Hotspot: Deep nesting detected
  File: src/validator.py:34
  Function: validate_nested_data
  Nesting depth: 6 (threshold: 4)
  Consider using early returns or helper functions
```

## Complexity Metrics Explained

### Cyclomatic Complexity
Measures the number of independent paths through code:
- Simple function: 1
- Each if/while/for: +1
- Each except/elif: +1
- Each logical operator (and/or): +1

### Function Length
Lines of code excluding:
- Comments
- Blank lines
- Simple declarations

### Nesting Depth
Maximum level of nested control structures:
```python
def example():          # Depth 0
    if condition1:      # Depth 1
        for item in items:  # Depth 2
            if condition2:  # Depth 3
                while True: # Depth 4 - getting deep!
                    pass
```

## Common Anti-Patterns

### High Cyclomatic Complexity
```python
# Complex function (complexity ~12)
def process_order(order):
    if order.type == "premium":
        if order.amount > 1000:
            if order.customer.is_vip:
                discount = 0.2
            elif order.customer.years > 5:
                discount = 0.15
            else:
                discount = 0.1
        elif order.amount > 500:
            discount = 0.05
        else:
            discount = 0.0
    elif order.type == "standard":
        if order.amount > 100:
            discount = 0.02
        else:
            discount = 0.0
    else:
        discount = 0.0
    
    return order.amount * (1 - discount)

# Refactored version (complexity ~3 per function)
def calculate_discount(order):
    if order.type == "premium":
        return calculate_premium_discount(order)
    elif order.type == "standard":
        return calculate_standard_discount(order)
    return 0.0

def calculate_premium_discount(order):
    if order.amount > 1000:
        return get_vip_discount(order.customer)
    elif order.amount > 500:
        return 0.05
    return 0.0

def calculate_standard_discount(order):
    return 0.02 if order.amount > 100 else 0.0

def get_vip_discount(customer):
    if customer.is_vip:
        return 0.2
    elif customer.years > 5:
        return 0.15
    return 0.1

def process_order(order):
    discount = calculate_discount(order)
    return order.amount * (1 - discount)
```

### Long Function
```python
# Long function that does too much
def generate_report(data, format_type, include_charts, send_email):
    # 100+ lines of mixed responsibilities
    # Data processing
    # Formatting 
    # Chart generation
    # Email sending
    # Error handling
    pass

# Refactored into focused functions
def generate_report(data, options):
    processed_data = process_report_data(data)
    formatted_report = format_report(processed_data, options.format_type)
    
    if options.include_charts:
        charts = generate_charts(processed_data)
        formatted_report = add_charts_to_report(formatted_report, charts)
    
    if options.send_email:
        send_report_email(formatted_report, options.recipients)
    
    return formatted_report
```

### Deep Nesting
```python
# Deeply nested validation
def validate_user_data(data):
    if data:
        if 'user' in data:
            if 'profile' in data['user']:
                if 'email' in data['user']['profile']:
                    if '@' in data['user']['profile']['email']:
                        return True
                    else:
                        raise ValueError("Invalid email format")
                else:
                    raise ValueError("Email required")
            else:
                raise ValueError("Profile required")
        else:
            raise ValueError("User data required")
    else:
        raise ValueError("Data cannot be empty")

# Flattened with early returns
def validate_user_data(data):
    if not data:
        raise ValueError("Data cannot be empty")
    
    if 'user' not in data:
        raise ValueError("User data required")
    
    user = data['user']
    if 'profile' not in user:
        raise ValueError("Profile required")
    
    profile = user['profile']
    if 'email' not in profile:
        raise ValueError("Email required")
    
    email = profile['email']
    if '@' not in email:
        raise ValueError("Invalid email format")
    
    return True
```

### Too Many Parameters
```python
# Function with too many parameters
def create_user(name, email, age, address, phone, company, 
                department, role, salary, start_date, manager_id):
    # Implementation
    pass

# Refactored with data classes or dictionaries
from dataclasses import dataclass

@dataclass
class PersonalInfo:
    name: str
    email: str
    age: int
    address: str
    phone: str

@dataclass
class EmploymentInfo:
    company: str
    department: str
    role: str
    salary: float
    start_date: str
    manager_id: int

def create_user(personal_info: PersonalInfo, employment_info: EmploymentInfo):
    # Implementation with structured data
    pass
```

## Refactoring Strategies

### Extract Method
Break large functions into smaller, focused ones:
```python
# Before: One large function
def process_order(order_data):
    # Validation logic (20 lines)
    # Calculation logic (30 lines)  
    # Database operations (25 lines)
    # Email notifications (15 lines)
    pass

# After: Multiple focused functions
def process_order(order_data):
    validate_order(order_data)
    calculations = calculate_order_totals(order_data)
    save_order_to_database(order_data, calculations)
    send_order_confirmation(order_data)
```

### Replace Conditional with Polymorphism
```python
# Before: Complex conditional logic
def calculate_shipping(order):
    if order.shipping_type == "standard":
        return order.weight * 0.5
    elif order.shipping_type == "express":
        return order.weight * 1.0 + 10
    elif order.shipping_type == "overnight":
        return order.weight * 2.0 + 25
    else:
        raise ValueError("Unknown shipping type")

# After: Polymorphic approach
class ShippingCalculator:
    def calculate(self, order):
        raise NotImplementedError

class StandardShipping(ShippingCalculator):
    def calculate(self, order):
        return order.weight * 0.5

class ExpressShipping(ShippingCalculator):
    def calculate(self, order):
        return order.weight * 1.0 + 10

class OvernightShipping(ShippingCalculator):
    def calculate(self, order):
        return order.weight * 2.0 + 25

SHIPPING_CALCULATORS = {
    "standard": StandardShipping(),
    "express": ExpressShipping(),
    "overnight": OvernightShipping(),
}

def calculate_shipping(order):
    calculator = SHIPPING_CALCULATORS.get(order.shipping_type)
    if not calculator:
        raise ValueError("Unknown shipping type")
    return calculator.calculate(order)
```

### Use Strategy Pattern
```python
# Complex processing with multiple algorithms
class DataProcessor:
    def __init__(self, strategy):
        self.strategy = strategy
    
    def process(self, data):
        return self.strategy.process(data)

class FastProcessingStrategy:
    def process(self, data):
        # Simple, fast algorithm
        pass

class AccurateProcessingStrategy:
    def process(self, data):
        # Complex, accurate algorithm
        pass

# Usage
processor = DataProcessor(FastProcessingStrategy())
result = processor.process(data)
```

## Best Practices

1. **Set appropriate thresholds**: Start with industry standards, adjust for your context
2. **Prioritize by impact**: Focus on complex code that changes frequently
3. **Refactor incrementally**: Small, safe changes are better than big rewrites
4. **Measure before and after**: Verify that refactoring actually reduces complexity
5. **Consider context**: Some complexity is necessary for performance or clarity

## Integration Examples

### Command Line
```bash
# Analyze complexity hotspots
pythonium crawl --detectors complexity_hotspot src/

# Strict complexity limits
pythonium crawl --detectors complexity_hotspot --config complexity_hotspot.max_complexity=8 src/

# Focus on function length
pythonium crawl --detectors complexity_hotspot --config complexity_hotspot.max_function_lines=30 src/
```

### Python API
```python
from pythonium import analyze_code

# Configuration for different complexity thresholds
strict_config = {
    "complexity_hotspot": {
        "max_complexity": 6,
        "max_function_lines": 25,
        "max_parameters": 4,
        "include_metrics": True
    }
}

results = analyze_code(
    path="src/",
    detectors=["complexity_hotspot"],
    config=strict_config
)

# Analyze complexity distribution
complexity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

for issue in results.get_issues("complexity_hotspot"):
    complexity = issue.metadata.get("complexity_score", 0)
    if complexity <= 5:
        complexity_counts["low"] += 1
    elif complexity <= 10:
        complexity_counts["medium"] += 1
    elif complexity <= 15:
        complexity_counts["high"] += 1
    else:
        complexity_counts["critical"] += 1

print("Complexity Distribution:")
for level, count in complexity_counts.items():
    print(f"  {level.capitalize()}: {count}")
```

### Prioritization Script
```python
# Prioritize complex functions by change frequency
import git
from collections import defaultdict

def get_change_frequency(repo_path, file_path):
    repo = git.Repo(repo_path)
    commits = list(repo.iter_commits(paths=file_path, max_count=100))
    return len(commits)

def prioritize_complexity_issues(results, repo_path):
    issues_with_priority = []
    
    for issue in results.get_issues("complexity_hotspot"):
        file_path = issue.location.file_path
        complexity = issue.metadata.get("complexity_score", 0)
        change_freq = get_change_frequency(repo_path, file_path)
        
        # Priority = complexity * change frequency
        priority = complexity * change_freq
        
        issues_with_priority.append({
            "issue": issue,
            "priority": priority,
            "complexity": complexity,
            "change_frequency": change_freq
        })
    
    # Sort by priority (highest first)
    return sorted(issues_with_priority, key=lambda x: x["priority"], reverse=True)

# Usage
priority_issues = prioritize_complexity_issues(results, ".")
print("Top 5 priority complexity issues:")
for i, item in enumerate(priority_issues[:5], 1):
    print(f"{i}. {item['issue'].description}")
    print(f"   Complexity: {item['complexity']}, Changes: {item['change_frequency']}")
```

## Related Detectors

- **Dead Code**: Complex unused code should be removed first
- **Clone**: Duplicated complex code multiplies the maintenance burden
- **Alternative Implementation**: Multiple complex implementations of the same logic

## Troubleshooting

**Thresholds too strict?**
- Increase `max_complexity` and other limits
- Consider your team's experience level
- Look at industry benchmarks for your domain

**Missing obvious complexity?**
- Lower thresholds temporarily to see what's detected
- Check if the detector supports the complexity pattern
- Verify file is included in analysis scope

**False positives on generated code?**
- Add exclude patterns for generated files
- Use different thresholds for different file types
- Consider separate analysis for generated vs. hand-written code
