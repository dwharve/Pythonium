# Circular Dependency Detector

The Circular Dependency Detector identifies import cycles and dependency tangles in Python codebases, helping maintain clean architecture and prevent import-related issues.

## What it Detects

- Direct circular imports (A imports B, B imports A)
- Indirect circular dependencies (A → B → C → A)
- Complex dependency cycles involving multiple modules
- Self-referential imports
- Cross-package dependency cycles
- Transitive dependency loops

## When to Use

- **Architecture reviews**: Ensure clean module separation
- **Large codebase maintenance**: Prevent dependency tangles
- **Refactoring preparation**: Identify coupling issues before changes
- **Package design**: Maintain clear boundaries between components
- **Import error debugging**: Resolve mysterious import failures

## Configuration Options

```yaml
detectors:
  circular_deps:
    # Maximum dependency chain length to analyze
    max_chain_length: 10
    
    # Include indirect dependencies in analysis
    include_indirect: true
    
    # Minimum cycle length to report
    min_cycle_length: 2
    
    # Exclude test files from analysis
    exclude_tests: false
    
    # Include standard library imports
    include_stdlib: false
    
    # Package-level analysis (group modules by package)
    package_level_analysis: true
    
    # Visualization output format
    output_format: "text"  # Options: text, dot, json
```

## Example Output

```
[ERROR] Circular Dependency: Direct import cycle detected
  Cycle: src/models/user.py → src/services/auth.py → src/models/user.py
  Length: 2 modules
  Impact: High - Direct circular import will cause import errors
  
[WARN] Circular Dependency: Indirect dependency cycle
  Cycle: src/api/handlers.py → src/business/logic.py → src/data/repository.py → src/api/handlers.py
  Length: 3 modules
  Impact: Medium - Complex dependency chain, consider architectural refactoring
  
[INFO] Circular Dependency: Package-level cycle
  Cycle: package.auth → package.models → package.auth
  Length: 2 packages
  Impact: Low - Consider moving shared components to common package
```

## Common Circular Dependency Patterns

### Direct Circular Import
```python
# File: models/user.py
from services.auth import AuthService  # Imports auth service

class User:
    def authenticate(self, password):
        return AuthService.verify_password(self, password)

# File: services/auth.py
from models.user import User  # Circular import!

class AuthService:
    @staticmethod
    def verify_password(user: User, password):
        return user.check_password(password)
```

**Resolution:**
```python
# File: models/user.py - Remove direct import
class User:
    def authenticate(self, password):
        # Use late import or dependency injection
        from services.auth import AuthService
        return AuthService.verify_password(self, password)

# File: services/auth.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User  # Only for type hints

class AuthService:
    @staticmethod
    def verify_password(user: "User", password):
        return user.check_password(password)
```

### Three-Way Circular Dependency
```python
# File: handlers/api.py
from business.user_logic import UserLogic

class UserHandler:
    def get_user(self, user_id):
        return UserLogic.get_user_data(user_id)

# File: business/user_logic.py
from data.user_repository import UserRepository

class UserLogic:
    @staticmethod
    def get_user_data(user_id):
        return UserRepository.find_by_id(user_id)

# File: data/user_repository.py
from handlers.api import UserHandler  # Creates cycle!

class UserRepository:
    @staticmethod
    def log_access(user_id):
        # This creates a circular dependency
        UserHandler.log_user_access(user_id)
```

**Resolution with Dependency Injection:**
```python
# File: handlers/api.py
from business.user_logic import UserLogic

class UserHandler:
    def __init__(self, user_logic: UserLogic):
        self.user_logic = user_logic
    
    def get_user(self, user_id):
        return self.user_logic.get_user_data(user_id)
    
    def log_user_access(self, user_id):
        # Implementation here
        pass

# File: business/user_logic.py
from data.user_repository import UserRepository

class UserLogic:
    def __init__(self, user_repository: UserRepository, access_logger=None):
        self.user_repository = user_repository
        self.access_logger = access_logger
    
    def get_user_data(self, user_id):
        user = self.user_repository.find_by_id(user_id)
        if self.access_logger:
            self.access_logger.log_user_access(user_id)
        return user

# File: data/user_repository.py - No more circular import
class UserRepository:
    def find_by_id(self, user_id):
        # Implementation without circular dependency
        pass

# File: main.py - Wire dependencies
def create_app():
    user_repository = UserRepository()
    user_handler = UserHandler(None)  # Will be set later
    user_logic = UserLogic(user_repository, user_handler)
    user_handler.user_logic = user_logic
    return user_handler
```

### Package-Level Circular Dependencies
```python
# Package structure with circular dependencies:
# package_a/
#   __init__.py
#   module1.py  (imports package_b.module2)
# package_b/
#   __init__.py  
#   module2.py  (imports package_a.module1)

# File: package_a/module1.py
from package_b.module2 import SomeClass

# File: package_b/module2.py  
from package_a.module1 import AnotherClass  # Circular!
```

**Resolution with Shared Package:**
```python
# Refactored structure:
# shared/
#   __init__.py
#   interfaces.py  (common interfaces/base classes)
# package_a/
#   __init__.py
#   module1.py  (imports shared.interfaces)
# package_b/
#   __init__.py
#   module2.py  (imports shared.interfaces)

# File: shared/interfaces.py
from abc import ABC, abstractmethod

class ProcessorInterface(ABC):
    @abstractmethod
    def process(self, data):
        pass

# File: package_a/module1.py
from shared.interfaces import ProcessorInterface

class ProcessorA(ProcessorInterface):
    def process(self, data):
        # Implementation
        pass

# File: package_b/module2.py
from shared.interfaces import ProcessorInterface

class ProcessorB(ProcessorInterface):
    def process(self, data):
        # Implementation
        pass
```

## Breaking Circular Dependencies

### Strategy 1: Extract Common Interface
```python
# Before: Circular dependency between User and Order
# File: models/user.py
from models.order import Order

class User:
    def get_orders(self):
        return Order.find_by_user(self.id)

# File: models/order.py
from models.user import User

class Order:
    def get_user(self):
        return User.find_by_id(self.user_id)

# After: Extract common interface
# File: interfaces/models.py
from abc import ABC, abstractmethod

class UserInterface(ABC):
    @abstractmethod
    def get_id(self):
        pass

class OrderInterface(ABC):
    @abstractmethod
    def get_user_id(self):
        pass

# File: models/user.py
from interfaces.models import UserInterface
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.order import Order

class User(UserInterface):
    def get_id(self):
        return self.id
    
    def get_orders(self):
        from models.order import Order  # Late import
        return Order.find_by_user(self.id)

# File: models/order.py
from interfaces.models import OrderInterface, UserInterface
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User

class Order(OrderInterface):
    def get_user_id(self):
        return self.user_id
    
    def get_user(self):
        from models.user import User  # Late import
        return User.find_by_id(self.user_id)
```

### Strategy 2: Dependency Injection
```python
# Use dependency injection to break cycles
class UserService:
    def __init__(self, order_service=None):
        self._order_service = order_service
    
    def set_order_service(self, order_service):
        self._order_service = order_service
    
    def get_user_orders(self, user_id):
        if self._order_service:
            return self._order_service.get_orders_by_user(user_id)
        return []

class OrderService:
    def __init__(self, user_service=None):
        self._user_service = user_service
    
    def set_user_service(self, user_service):
        self._user_service = user_service
    
    def get_order_user(self, order_id):
        order = self.get_order(order_id)
        if self._user_service and order:
            return self._user_service.get_user(order.user_id)
        return None

# Wire dependencies without circular imports
def setup_services():
    user_service = UserService()
    order_service = OrderService()
    
    user_service.set_order_service(order_service)
    order_service.set_user_service(user_service)
    
    return user_service, order_service
```

### Strategy 3: Event-Driven Architecture
```python
# Replace direct calls with events
from typing import Dict, List, Callable

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def publish(self, event_type: str, data):
        for handler in self._subscribers.get(event_type, []):
            handler(data)

# File: models/user.py - No direct import of Order
class User:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    def save(self):
        # Save user logic
        self.event_bus.publish('user_saved', {'user_id': self.id})

# File: models/order.py - No direct import of User
class Order:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        event_bus.subscribe('user_saved', self.handle_user_saved)
    
    def handle_user_saved(self, data):
        # Update orders when user is saved
        pass
```

## Visualization and Analysis

### Generate Dependency Graph
```python
import networkx as nx
import matplotlib.pyplot as plt

def visualize_dependencies(analysis_results):
    """Create a visual dependency graph."""
    G = nx.DiGraph()
    
    # Add nodes and edges from analysis results
    for issue in analysis_results.get_issues("circular_deps"):
        if hasattr(issue, 'cycle_path'):
            cycle = issue.cycle_path
            for i in range(len(cycle)):
                current = cycle[i]
                next_node = cycle[(i + 1) % len(cycle)]
                G.add_edge(current, next_node)
    
    # Create layout
    pos = nx.spring_layout(G)
    
    # Draw the graph
    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=3000, font_size=8, arrows=True)
    
    # Highlight cycles in red
    cycle_edges = [(u, v) for u, v in G.edges() if nx.has_path(G, v, u)]
    nx.draw_networkx_edges(G, pos, edgelist=cycle_edges, edge_color='red', width=2)
    
    plt.title("Module Dependency Graph (Red edges indicate cycles)")
    plt.savefig("dependency_graph.png", dpi=300, bbox_inches='tight')
    plt.show()
```

### Dependency Matrix Analysis
```python
def create_dependency_matrix(modules, dependencies):
    """Create a dependency matrix to visualize relationships."""
    import pandas as pd
    import seaborn as sns
    
    # Create matrix
    matrix = pd.DataFrame(0, index=modules, columns=modules)
    
    for source, target in dependencies:
        if source in modules and target in modules:
            matrix.loc[source, target] = 1
    
    # Visualize
    plt.figure(figsize=(10, 10))
    sns.heatmap(matrix, annot=True, cmap='Reds', square=True)
    plt.title("Module Dependency Matrix")
    plt.xlabel("Depends On")
    plt.ylabel("Module")
    plt.show()
    
    return matrix
```

## Best Practices

1. **Design with layers**: Higher layers can depend on lower layers, but not vice versa
2. **Use interfaces**: Define contracts to break direct dependencies
3. **Apply dependency injection**: Make dependencies explicit and configurable
4. **Late imports**: Use imports inside functions when necessary
5. **Event-driven patterns**: Replace direct calls with event publishing/subscribing

## Integration Examples

### Command Line
```bash
# Analyze circular dependencies
pythonium crawl --detectors circular_deps src/

# Include indirect dependencies
pythonium crawl --detectors circular_deps --config circular_deps.include_indirect=true src/

# Package-level analysis
pythonium crawl --detectors circular_deps --config circular_deps.package_level_analysis=true src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["circular_deps"],
    config={
        "circular_deps": {
            "max_chain_length": 15,
            "include_indirect": True,
            "min_cycle_length": 2
        }
    }
)

# Analyze cycle complexity
cycles_by_length = {}
for issue in results.get_issues("circular_deps"):
    length = issue.metadata.get("cycle_length", 0)
    if length not in cycles_by_length:
        cycles_by_length[length] = []
    cycles_by_length[length].append(issue)

# Report by complexity
for length in sorted(cycles_by_length.keys()):
    cycles = cycles_by_length[length]
    print(f"Cycles of length {length}: {len(cycles)}")
    for cycle in cycles:
        print(f"  - {cycle.description}")
```

### Refactoring Priority Script
```python
def prioritize_circular_dependencies(results):
    """Prioritize circular dependencies by impact and complexity."""
    
    priority_scores = []
    
    for issue in results.get_issues("circular_deps"):
        cycle_length = issue.metadata.get("cycle_length", 0)
        modules_involved = issue.metadata.get("modules_involved", [])
        
        # Calculate priority score
        # Shorter cycles are higher priority (harder to break)
        # More modules involved = higher impact
        length_score = max(0, 10 - cycle_length)  # Shorter = higher score
        impact_score = len(modules_involved)
        
        priority_score = length_score + impact_score
        
        priority_scores.append({
            "issue": issue,
            "priority_score": priority_score,
            "cycle_length": cycle_length,
            "modules_involved": len(modules_involved)
        })
    
    # Sort by priority (highest first)
    return sorted(priority_scores, key=lambda x: x["priority_score"], reverse=True)

# Usage
prioritized = prioritize_circular_dependencies(results)
print("Top 5 circular dependencies to fix:")
for i, item in enumerate(prioritized[:5], 1):
    print(f"{i}. {item['issue'].description}")
    print(f"   Priority: {item['priority_score']}, Length: {item['cycle_length']}")
```

## Related Detectors

- **Dead Code**: Circular dependencies may keep unused code alive
- **Alternative Implementation**: Multiple implementations might create unnecessary cycles
- **Complexity Hotspot**: Complex modules often have more dependencies

## Troubleshooting

**Missing obvious cycles?**
- Increase `max_chain_length`
- Enable `include_indirect` analysis
- Check if modules are in analysis scope

**Too many false positives?**
- Increase `min_cycle_length`
- Enable `exclude_tests` if test files cause noise
- Use package-level analysis for high-level view

**Performance issues?**
- Reduce `max_chain_length`
- Disable `include_indirect` for large codebases
- Analyze packages separately
