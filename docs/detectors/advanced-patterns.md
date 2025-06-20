# Advanced Patterns Detector

The Advanced Patterns Detector finds similar algorithmic patterns and identifies opportunities for design pattern implementation, helping improve code architecture and maintainability.

## What it Detects

- Similar algorithmic structures across functions
- Opportunities for design pattern implementation
- Repeated conditional logic patterns
- Similar iteration and recursion patterns
- Template method opportunities
- Strategy pattern candidates
- Observer pattern implementations
- Factory pattern opportunities

## When to Use

- **Architecture improvement**: Identify design pattern opportunities
- **Code standardization**: Establish consistent algorithmic approaches
- **Refactoring planning**: Find structural improvements
- **Design review**: Evaluate architectural patterns
- **Pattern migration**: Modernize code with established patterns

## Configuration Options

```yaml
detectors:
  advanced_patterns:
    # Pattern similarity threshold
    pattern_similarity: 0.75
    
    # Minimum pattern complexity
    min_pattern_complexity: 5
    
    # Detect specific pattern types
    detect_strategy_pattern: true
    detect_template_method: true
    detect_factory_pattern: true
    detect_observer_pattern: true
    detect_decorator_pattern: true
    
    # Cross-module pattern analysis
    cross_module_analysis: true
    
    # Include inheritance hierarchies
    analyze_inheritance: true
    
    # Pattern suggestion confidence
    suggestion_confidence: 0.8
```

## Example Output

```
[ERROR] Advanced Patterns: Strategy pattern opportunity detected
  Location: src/processors/
  Pattern: Multiple classes with similar process() methods
  Suggestion: Implement Strategy pattern for pluggable algorithms
  Confidence: 92%
  
[WARN] Advanced Patterns: Template method pattern candidate
  Functions: data_validator.py:validate_user(), validate_product(), validate_order()
  Pattern: Similar validation structure with varying steps
  Suggestion: Extract template method with hook methods
  Confidence: 85%
  
[INFO] Advanced Patterns: Factory pattern opportunity
  Location: src/models/
  Pattern: Multiple object creation methods with similar logic
  Suggestion: Implement Factory pattern for object creation
  Confidence: 78%
```

## Common Pattern Opportunities

### Strategy Pattern
```python
# Before: Conditional logic for different algorithms
class DataProcessor:
    def process_data(self, data, algorithm_type):
        if algorithm_type == "fast":
            # Fast algorithm implementation
            result = []
            for item in data:
                result.append(item * 2)
            return result
        
        elif algorithm_type == "accurate":
            # Accurate algorithm implementation
            result = []
            for item in data:
                # More complex processing
                processed = item * 2.5 + 0.1
                result.append(round(processed, 2))
            return result
        
        elif algorithm_type == "memory_efficient":
            # Memory efficient implementation
            for item in data:
                yield item * 2.2
        
        else:
            raise ValueError("Unknown algorithm type")

# After: Strategy pattern implementation
from abc import ABC, abstractmethod

class ProcessingStrategy(ABC):
    @abstractmethod
    def process(self, data):
        pass

class FastStrategy(ProcessingStrategy):
    def process(self, data):
        return [item * 2 for item in data]

class AccurateStrategy(ProcessingStrategy):
    def process(self, data):
        result = []
        for item in data:
            processed = item * 2.5 + 0.1
            result.append(round(processed, 2))
        return result

class MemoryEfficientStrategy(ProcessingStrategy):
    def process(self, data):
        for item in data:
            yield item * 2.2

class DataProcessor:
    def __init__(self, strategy: ProcessingStrategy):
        self.strategy = strategy
    
    def set_strategy(self, strategy: ProcessingStrategy):
        self.strategy = strategy
    
    def process_data(self, data):
        return self.strategy.process(data)

# Usage
processor = DataProcessor(FastStrategy())
result = processor.process_data(data)

# Switch strategies at runtime
processor.set_strategy(AccurateStrategy())
accurate_result = processor.process_data(data)
```

### Template Method Pattern
```python
# Before: Similar structure with duplicated code
class UserValidator:
    def validate_user(self, user_data):
        # Common setup
        if not user_data:
            raise ValueError("User data required")
        
        # User-specific validation
        if 'email' not in user_data:
            raise ValueError("Email required")
        if '@' not in user_data['email']:
            raise ValueError("Invalid email")
        
        # Common cleanup
        return {"status": "valid", "type": "user"}

class ProductValidator:
    def validate_product(self, product_data):
        # Common setup (duplicated)
        if not product_data:
            raise ValueError("Product data required")
        
        # Product-specific validation
        if 'name' not in product_data:
            raise ValueError("Product name required")
        if 'price' not in product_data:
            raise ValueError("Price required")
        
        # Common cleanup (duplicated)
        return {"status": "valid", "type": "product"}

# After: Template method pattern
class BaseValidator(ABC):
    def validate(self, data):
        """Template method defining validation algorithm."""
        self._check_data_exists(data)
        self._validate_specific_fields(data)
        return self._create_result()
    
    def _check_data_exists(self, data):
        """Common validation step."""
        if not data:
            raise ValueError(f"{self._get_data_type()} data required")
    
    @abstractmethod
    def _validate_specific_fields(self, data):
        """Hook method for specific validation logic."""
        pass
    
    @abstractmethod
    def _get_data_type(self):
        """Hook method for data type name."""
        pass
    
    def _create_result(self):
        """Common result creation."""
        return {"status": "valid", "type": self._get_data_type()}

class UserValidator(BaseValidator):
    def _validate_specific_fields(self, data):
        if 'email' not in data:
            raise ValueError("Email required")
        if '@' not in data['email']:
            raise ValueError("Invalid email")
    
    def _get_data_type(self):
        return "user"

class ProductValidator(BaseValidator):
    def _validate_specific_fields(self, data):
        if 'name' not in data:
            raise ValueError("Product name required")
        if 'price' not in data:
            raise ValueError("Price required")
    
    def _get_data_type(self):
        return "product"
```

### Factory Pattern
```python
# Before: Scattered object creation logic
def create_user_from_data(data):
    if data.get('type') == 'admin':
        user = AdminUser()
        user.permissions = ['read', 'write', 'delete']
    elif data.get('type') == 'regular':
        user = RegularUser()
        user.permissions = ['read']
    else:
        user = GuestUser()
        user.permissions = []
    
    user.name = data.get('name', '')
    user.email = data.get('email', '')
    return user

def create_admin_user(name, email):
    user = AdminUser()
    user.name = name
    user.email = email
    user.permissions = ['read', 'write', 'delete']
    return user

def create_regular_user(name, email):
    user = RegularUser()
    user.name = name
    user.email = email
    user.permissions = ['read']
    return user

# After: Factory pattern
from abc import ABC, abstractmethod
from enum import Enum

class UserType(Enum):
    ADMIN = "admin"
    REGULAR = "regular"
    GUEST = "guest"

class User(ABC):
    def __init__(self, name="", email=""):
        self.name = name
        self.email = email
        self.permissions = []

class AdminUser(User):
    def __init__(self, name="", email=""):
        super().__init__(name, email)
        self.permissions = ['read', 'write', 'delete']

class RegularUser(User):
    def __init__(self, name="", email=""):
        super().__init__(name, email)
        self.permissions = ['read']

class GuestUser(User):
    def __init__(self, name="", email=""):
        super().__init__(name, email)
        self.permissions = []

class UserFactory:
    """Factory for creating different types of users."""
    
    _user_classes = {
        UserType.ADMIN: AdminUser,
        UserType.REGULAR: RegularUser,
        UserType.GUEST: GuestUser
    }
    
    @classmethod
    def create_user(cls, user_type: UserType, name: str = "", email: str = "") -> User:
        """Create user of specified type."""
        user_class = cls._user_classes.get(user_type)
        if not user_class:
            raise ValueError(f"Unknown user type: {user_type}")
        
        return user_class(name, email)
    
    @classmethod
    def create_user_from_data(cls, data: dict) -> User:
        """Create user from data dictionary."""
        user_type_str = data.get('type', 'guest')
        try:
            user_type = UserType(user_type_str)
        except ValueError:
            user_type = UserType.GUEST
        
        return cls.create_user(
            user_type,
            data.get('name', ''),
            data.get('email', '')
        )

# Usage
admin = UserFactory.create_user(UserType.ADMIN, "Alice", "alice@example.com")
user_from_data = UserFactory.create_user_from_data({
    'type': 'regular',
    'name': 'Bob',
    'email': 'bob@example.com'
})
```

### Observer Pattern
```python
# Before: Tight coupling with manual notifications
class OrderProcessor:
    def __init__(self):
        self.email_service = EmailService()
        self.inventory_service = InventoryService()
        self.analytics_service = AnalyticsService()
    
    def process_order(self, order):
        # Process order
        order.status = "processed"
        
        # Manual notifications (tightly coupled)
        self.email_service.send_confirmation(order)
        self.inventory_service.update_stock(order)
        self.analytics_service.track_order(order)

# After: Observer pattern
from abc import ABC, abstractmethod
from typing import List

class OrderObserver(ABC):
    @abstractmethod
    def on_order_processed(self, order):
        pass

class EmailNotificationObserver(OrderObserver):
    def on_order_processed(self, order):
        # Send email confirmation
        print(f"Sending confirmation email for order {order.id}")

class InventoryObserver(OrderObserver):
    def on_order_processed(self, order):
        # Update inventory
        print(f"Updating inventory for order {order.id}")

class AnalyticsObserver(OrderObserver):
    def on_order_processed(self, order):
        # Track analytics
        print(f"Recording analytics for order {order.id}")

class OrderSubject:
    def __init__(self):
        self._observers: List[OrderObserver] = []
    
    def attach(self, observer: OrderObserver):
        self._observers.append(observer)
    
    def detach(self, observer: OrderObserver):
        self._observers.remove(observer)
    
    def notify(self, order):
        for observer in self._observers:
            observer.on_order_processed(order)

class OrderProcessor(OrderSubject):
    def process_order(self, order):
        # Process order
        order.status = "processed"
        
        # Notify all observers
        self.notify(order)

# Usage
processor = OrderProcessor()
processor.attach(EmailNotificationObserver())
processor.attach(InventoryObserver())
processor.attach(AnalyticsObserver())

processor.process_order(order)  # All observers notified automatically
```

### Decorator Pattern
```python
# Before: Monolithic function with mixed concerns
def process_request(request):
    # Logging
    print(f"Processing request: {request.id}")
    start_time = time.time()
    
    # Authentication
    if not request.user or not request.user.is_authenticated:
        raise AuthenticationError("User not authenticated")
    
    # Authorization
    if not request.user.has_permission('process_requests'):
        raise AuthorizationError("User not authorized")
    
    # Rate limiting
    if request.user.request_count > 100:
        raise RateLimitError("Rate limit exceeded")
    
    # Actual processing
    result = handle_business_logic(request)
    
    # More logging
    end_time = time.time()
    print(f"Request processed in {end_time - start_time:.2f} seconds")
    
    return result

# After: Decorator pattern
from functools import wraps
import time

def log_requests(func):
    @wraps(func)
    def wrapper(request):
        print(f"Processing request: {request.id}")
        start_time = time.time()
        
        result = func(request)
        
        end_time = time.time()
        print(f"Request processed in {end_time - start_time:.2f} seconds")
        return result
    return wrapper

def authenticate(func):
    @wraps(func)
    def wrapper(request):
        if not request.user or not request.user.is_authenticated:
            raise AuthenticationError("User not authenticated")
        return func(request)
    return wrapper

def authorize(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(request):
            if not request.user.has_permission(permission):
                raise AuthorizationError("User not authorized")
            return func(request)
        return wrapper
    return decorator

def rate_limit(max_requests=100):
    def decorator(func):
        @wraps(func)
        def wrapper(request):
            if request.user.request_count > max_requests:
                raise RateLimitError("Rate limit exceeded")
            return func(request)
        return wrapper
    return decorator

# Clean, composable implementation
@log_requests
@authenticate
@authorize('process_requests')
@rate_limit(100)
def process_request(request):
    return handle_business_logic(request)
```

## Pattern Detection Strategies

### Structural Analysis
```python
import ast
from typing import Dict, List, Set

class PatternDetector:
    def __init__(self):
        self.patterns = {
            'strategy': self._detect_strategy_pattern,
            'template_method': self._detect_template_method,
            'factory': self._detect_factory_pattern,
            'observer': self._detect_observer_pattern
        }
    
    def analyze_codebase(self, file_paths: List[str]) -> Dict[str, List[dict]]:
        """Analyze codebase for design pattern opportunities."""
        results = {}
        
        for pattern_name, detector in self.patterns.items():
            results[pattern_name] = detector(file_paths)
        
        return results
    
    def _detect_strategy_pattern(self, file_paths: List[str]) -> List[dict]:
        """Detect strategy pattern opportunities."""
        opportunities = []
        
        # Look for classes with similar method signatures
        # and conditional logic that could be extracted
        for file_path in file_paths:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                    
                    # Look for methods with conditional logic
                    for method in methods:
                        if self._has_strategy_pattern_indicators(method):
                            opportunities.append({
                                'file': file_path,
                                'class': node.name,
                                'method': method.name,
                                'confidence': self._calculate_strategy_confidence(method)
                            })
        
        return opportunities
    
    def _has_strategy_pattern_indicators(self, method_node: ast.FunctionDef) -> bool:
        """Check if method has indicators for strategy pattern."""
        # Look for multiple if/elif chains that could be strategies
        if_count = 0
        for node in ast.walk(method_node):
            if isinstance(node, ast.If):
                if_count += 1
        
        return if_count >= 3  # Arbitrary threshold
    
    def _detect_template_method(self, file_paths: List[str]) -> List[dict]:
        """Detect template method opportunities."""
        opportunities = []
        
        # Look for classes with similar method structures
        class_methods = {}
        
        for file_path in file_paths:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                    method_structures = []
                    
                    for method in methods:
                        structure = self._extract_method_structure(method)
                        method_structures.append(structure)
                    
                    class_methods[f"{file_path}:{node.name}"] = method_structures
        
        # Compare structures to find similar patterns
        similar_structures = self._find_similar_structures(class_methods)
        
        for structure_group in similar_structures:
            if len(structure_group) >= 2:
                opportunities.append({
                    'classes': structure_group,
                    'pattern': 'template_method',
                    'confidence': 0.8
                })
        
        return opportunities
    
    def _extract_method_structure(self, method_node: ast.FunctionDef) -> List[str]:
        """Extract structural elements of a method."""
        structure = []
        
        for node in method_node.body:
            if isinstance(node, ast.If):
                structure.append('conditional')
            elif isinstance(node, ast.For):
                structure.append('loop')
            elif isinstance(node, ast.While):
                structure.append('while_loop')
            elif isinstance(node, ast.Try):
                structure.append('exception_handling')
            elif isinstance(node, ast.Return):
                structure.append('return')
            else:
                structure.append('statement')
        
        return structure
```

### Pattern Confidence Scoring
```python
class PatternConfidenceCalculator:
    def __init__(self):
        self.weights = {
            'structural_similarity': 0.4,
            'naming_conventions': 0.2,
            'complexity_reduction': 0.25,
            'maintainability_gain': 0.15
        }
    
    def calculate_pattern_confidence(self, pattern_type: str, evidence: dict) -> float:
        """Calculate confidence score for pattern recommendation."""
        
        if pattern_type == 'strategy':
            return self._calculate_strategy_confidence(evidence)
        elif pattern_type == 'template_method':
            return self._calculate_template_confidence(evidence)
        elif pattern_type == 'factory':
            return self._calculate_factory_confidence(evidence)
        
        return 0.0
    
    def _calculate_strategy_confidence(self, evidence: dict) -> float:
        """Calculate confidence for strategy pattern recommendation."""
        score = 0.0
        
        # Structural similarity
        conditional_complexity = evidence.get('conditional_complexity', 0)
        if conditional_complexity > 5:
            score += self.weights['structural_similarity']
        
        # Naming conventions
        similar_method_names = evidence.get('similar_method_names', False)
        if similar_method_names:
            score += self.weights['naming_conventions']
        
        # Complexity reduction potential
        code_duplication = evidence.get('code_duplication', 0)
        if code_duplication > 0.3:
            score += self.weights['complexity_reduction']
        
        # Maintainability gain
        method_length = evidence.get('method_length', 0)
        if method_length > 50:
            score += self.weights['maintainability_gain']
        
        return min(score, 1.0)
```

## Best Practices

1. **Start with high-confidence patterns**: Implement patterns with clear benefits first
2. **Consider context**: Not every similar structure needs a design pattern
3. **Measure impact**: Ensure pattern implementation improves maintainability
4. **Gradual adoption**: Introduce patterns incrementally
5. **Team training**: Ensure team understands the patterns being introduced

## Integration Examples

### Command Line
```bash
# Detect advanced patterns
pythonium crawl --detectors advanced_patterns src/

# Focus on specific patterns
pythonium crawl --detectors advanced_patterns --config advanced_patterns.detect_strategy_pattern=true src/

# High confidence suggestions only
pythonium crawl --detectors advanced_patterns --config advanced_patterns.suggestion_confidence=0.9 src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["advanced_patterns"],
    config={
        "advanced_patterns": {
            "pattern_similarity": 0.8,
            "detect_strategy_pattern": True,
            "detect_template_method": True,
            "suggestion_confidence": 0.8
        }
    }
)

# Categorize patterns by type
patterns_by_type = {}
for issue in results.get_issues("advanced_patterns"):
    pattern_type = issue.metadata.get("pattern_type", "unknown")
    if pattern_type not in patterns_by_type:
        patterns_by_type[pattern_type] = []
    patterns_by_type[pattern_type].append(issue)

# Report pattern opportunities
for pattern_type, patterns in patterns_by_type.items():
    print(f"\n{pattern_type.title()} Pattern Opportunities: {len(patterns)}")
    for pattern in patterns:
        confidence = pattern.metadata.get("confidence", 0)
        print(f"  - Confidence: {confidence:.1%} - {pattern.description}")
```

### Pattern Implementation Priority
```python
def prioritize_pattern_implementations(results):
    """Prioritize pattern implementations by impact and effort."""
    
    implementations = []
    
    for issue in results.get_issues("advanced_patterns"):
        pattern_type = issue.metadata.get("pattern_type", "unknown")
        confidence = issue.metadata.get("confidence", 0)
        complexity_reduction = issue.metadata.get("complexity_reduction", 0)
        
        # Calculate priority score
        impact_score = confidence * complexity_reduction
        effort_estimate = {
            'strategy': 3,      # Medium effort
            'template_method': 2,  # Low-medium effort
            'factory': 2,       # Low-medium effort
            'observer': 4,      # Higher effort
            'decorator': 2      # Low-medium effort
        }.get(pattern_type, 3)
        
        priority_score = impact_score / effort_estimate
        
        implementations.append({
            'issue': issue,
            'pattern_type': pattern_type,
            'priority_score': priority_score,
            'confidence': confidence,
            'effort_estimate': effort_estimate
        })
    
    return sorted(implementations, key=lambda x: x['priority_score'], reverse=True)

# Usage
prioritized = prioritize_pattern_implementations(results)
print("Top 5 pattern implementation priorities:")
for i, impl in enumerate(prioritized[:5], 1):
    print(f"{i}. {impl['pattern_type'].title()} Pattern")
    print(f"   Priority Score: {impl['priority_score']:.2f}")
    print(f"   Confidence: {impl['confidence']:.1%}")
    print(f"   Effort: {impl['effort_estimate']}/5")
    print(f"   Location: {impl['issue'].description}")
```

## Related Detectors

- **Clone**: Duplicated patterns indicate design pattern opportunities
- **Complexity Hotspot**: Complex code often benefits from pattern application
- **Alternative Implementation**: Multiple implementations suggest strategy pattern

## Troubleshooting

**Too many false positives?**
- Increase `suggestion_confidence` threshold
- Increase `min_pattern_complexity`
- Focus on specific pattern types

**Missing obvious pattern opportunities?**
- Lower `pattern_similarity` threshold
- Enable `cross_module_analysis`
- Check specific pattern detection settings

**Performance issues with large codebases?**
- Disable less important pattern types
- Analyze modules separately
- Increase minimum complexity thresholds
