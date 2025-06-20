# Inconsistent API Detector

The Inconsistent API Detector identifies functions and methods with inconsistent signatures, parameter patterns, and naming conventions, helping standardize APIs and improve developer experience.

## What it Detects

- Inconsistent parameter ordering across similar functions
- Mixed naming conventions (camelCase vs snake_case)
- Inconsistent return type patterns
- Similar functions with different parameter types
- Inconsistent error handling patterns
- Missing or inconsistent documentation patterns

## When to Use

- **API design reviews**: Ensure consistent interfaces
- **Library development**: Maintain coherent public APIs
- **Team onboarding**: Standardize coding patterns
- **Documentation generation**: Consistent APIs are easier to document
- **Refactoring preparation**: Identify inconsistencies before major changes

## Configuration Options

```yaml
detectors:
  inconsistent_api:
    # Minimum similarity threshold for function comparison
    similarity_threshold: 0.7
    
    # Check parameter naming consistency
    check_parameter_names: true
    
    # Check return type consistency
    check_return_types: true
    
    # Check error handling patterns
    check_error_handling: true
    
    # Enforce naming conventions
    enforce_snake_case: true
    
    # Include private methods in analysis
    include_private_methods: false
    
    # Patterns for similar function groups
    function_groups:
      - ["create_*", "update_*", "delete_*"]  # CRUD operations
      - ["get_*", "find_*", "fetch_*"]        # Retrieval operations
      - ["validate_*", "check_*"]             # Validation operations
```

## Example Output

```
[ERROR] Inconsistent API: Parameter order inconsistency
  Functions: create_user(name, email, age) vs create_product(email, name, price)
  Issue: Similar functions have different parameter ordering
  Suggestion: Standardize parameter order across CRUD operations
  
[WARN] Inconsistent API: Mixed naming conventions
  Function: getUserProfile() in user_service.py:45
  Context: Other functions use snake_case (get_user_data, get_user_preferences)
  Suggestion: Use snake_case consistently
  
[INFO] Inconsistent API: Inconsistent return patterns
  Functions: find_user() returns User object, find_product() returns dict
  Issue: Similar retrieval functions have different return types
  Suggestion: Standardize return types for similar operations
```

## Common Inconsistency Patterns

### Parameter Order Inconsistency
```python
# Inconsistent parameter ordering
def create_user(name, email, age, department):
    pass

def create_product(email, name, price, category):  # Different order
    pass

def create_order(user_id, product_id, quantity, email):  # Another order
    pass

# Consistent approach
def create_user(name, email, age=None, department=None):
    pass

def create_product(name, category, price=None, description=None):
    pass

def create_order(user_id, product_id, quantity=1, notes=None):
    pass
```

### Mixed Naming Conventions
```python
# Mixed conventions (detected)
class UserService:
    def getUserData(self, user_id):      # camelCase
        pass
    
    def get_user_profile(self, user_id): # snake_case
        pass
    
    def GetUserPreferences(self, user_id): # PascalCase
        pass

# Consistent convention
class UserService:
    def get_user_data(self, user_id):
        pass
    
    def get_user_profile(self, user_id):
        pass
    
    def get_user_preferences(self, user_id):
        pass
```

### Inconsistent Return Types
```python
# Inconsistent return patterns
def find_user(user_id):
    user = database.get_user(user_id)
    return user  # Returns User object or None

def find_product(product_id):
    product = database.get_product(product_id)
    if product:
        return {"id": product.id, "name": product.name}  # Returns dict
    return {}  # Returns empty dict instead of None

def find_order(order_id):
    order = database.get_order(order_id)
    if not order:
        raise OrderNotFound()  # Raises exception
    return order

# Consistent return patterns
def find_user(user_id):
    return database.get_user(user_id)  # Returns User or None

def find_product(product_id):
    return database.get_product(product_id)  # Returns Product or None

def find_order(order_id):
    return database.get_order(order_id)  # Returns Order or None

# Alternative: Consistent exception handling
def find_user(user_id):
    user = database.get_user(user_id)
    if not user:
        raise UserNotFound(f"User {user_id} not found")
    return user

def find_product(product_id):
    product = database.get_product(product_id)
    if not product:
        raise ProductNotFound(f"Product {product_id} not found")
    return product
```

### Inconsistent Error Handling
```python
# Inconsistent error handling patterns
def process_payment(amount, card_info):
    if amount <= 0:
        return False  # Returns boolean
    # Process payment
    return True

def process_refund(amount, transaction_id):
    if amount <= 0:
        raise ValueError("Amount must be positive")  # Raises exception
    # Process refund
    return refund_id

def process_transfer(amount, from_account, to_account):
    if amount <= 0:
        return {"success": False, "error": "Invalid amount"}  # Returns dict
    # Process transfer
    return {"success": True, "transaction_id": "12345"}

# Consistent error handling
class PaymentError(Exception):
    pass

def process_payment(amount, card_info):
    if amount <= 0:
        raise PaymentError("Amount must be positive")
    # Process payment
    return payment_id

def process_refund(amount, transaction_id):
    if amount <= 0:
        raise PaymentError("Amount must be positive")
    # Process refund
    return refund_id

def process_transfer(amount, from_account, to_account):
    if amount <= 0:
        raise PaymentError("Amount must be positive")
    # Process transfer
    return transaction_id
```

### Inconsistent Parameter Types
```python
# Inconsistent parameter types
def get_user_by_id(user_id: int):
    return database.get_user(user_id)

def get_user_by_email(email: str):
    return database.get_user_by_email(email)

def get_user_by_username(username):  # No type hint
    return database.get_user_by_username(username)

def getUsersByDepartment(dept_id: str):  # ID as string, different naming
    return database.get_users_by_department(int(dept_id))

# Consistent approach
def get_user_by_id(user_id: int) -> Optional[User]:
    return database.get_user(user_id)

def get_user_by_email(email: str) -> Optional[User]:
    return database.get_user_by_email(email)

def get_user_by_username(username: str) -> Optional[User]:
    return database.get_user_by_username(username)

def get_users_by_department(department_id: int) -> List[User]:
    return database.get_users_by_department(department_id)
```

## API Standardization Strategies

### Define API Patterns
```python
# Standard CRUD pattern
class BaseService:
    def create(self, data: dict) -> ModelType:
        """Create a new entity."""
        pass
    
    def get_by_id(self, entity_id: int) -> Optional[ModelType]:
        """Retrieve entity by ID."""
        pass
    
    def update(self, entity_id: int, data: dict) -> ModelType:
        """Update existing entity."""
        pass
    
    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID."""
        pass
    
    def list_all(self, filters: Optional[dict] = None) -> List[ModelType]:
        """List entities with optional filtering."""
        pass

# Implement consistent services
class UserService(BaseService[User]):
    def create(self, data: dict) -> User:
        return User.objects.create(**data)
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return User.objects.filter(id=user_id).first()

class ProductService(BaseService[Product]):
    def create(self, data: dict) -> Product:
        return Product.objects.create(**data)
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        return Product.objects.filter(id=product_id).first()
```

### Consistent Error Handling
```python
# Define standard exceptions
class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

class NotFoundError(Exception):
    def __init__(self, entity_type: str, entity_id: Any):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id {entity_id} not found")

# Use consistently across services
def get_user(user_id: int) -> User:
    user = database.get_user(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    return user

def get_product(product_id: int) -> Product:
    product = database.get_product(product_id)
    if not product:
        raise NotFoundError("Product", product_id)
    return product
```

### Parameter Validation Patterns
```python
# Consistent validation approach
from typing import TypeVar, Generic
from dataclasses import dataclass

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: Optional[int] = None
    department: Optional[str] = None

@dataclass
class CreateProductRequest:
    name: str
    category: str
    price: Optional[float] = None
    description: Optional[str] = None

# Consistent service methods
def create_user(request: CreateUserRequest) -> User:
    # Validation is handled by dataclass
    return User.objects.create(
        name=request.name,
        email=request.email,
        age=request.age,
        department=request.department
    )

def create_product(request: CreateProductRequest) -> Product:
    return Product.objects.create(
        name=request.name,
        category=request.category,
        price=request.price,
        description=request.description
    )
```

## Best Practices for API Consistency

### 1. Establish Conventions
```python
# Document and enforce naming conventions
"""
API Naming Conventions:
- Functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Private methods: _underscore_prefix

Parameter Ordering:
1. Required parameters (alphabetical)
2. Optional parameters (alphabetical)
3. **kwargs if needed

Return Types:
- Single entity: Return object or None
- Multiple entities: Return List[Object]
- Success/failure: Raise exception or return object
"""
```

### 2. Use Type Hints Consistently
```python
from typing import Optional, List, Dict, Any

def process_data(
    data: Dict[str, Any], 
    validation_rules: Optional[List[str]] = None
) -> Dict[str, Any]:
    pass
```

### 3. Standardize Response Formats
```python
# For APIs that return structured data
@dataclass
class ApiResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

def api_get_user(user_id: int) -> ApiResponse:
    try:
        user = get_user(user_id)
        return ApiResponse(success=True, data=user.to_dict())
    except NotFoundError as e:
        return ApiResponse(success=False, error=str(e))
```

## Integration Examples

### Command Line
```bash
# Check API consistency
pythonium crawl --detectors inconsistent_api src/

# Strict consistency checking
pythonium crawl --detectors inconsistent_api --config inconsistent_api.similarity_threshold=0.9 src/

# Focus on public APIs only
pythonium crawl --detectors inconsistent_api --config inconsistent_api.include_private_methods=false src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["inconsistent_api"],
    config={
        "inconsistent_api": {
            "similarity_threshold": 0.8,
            "check_parameter_names": True,
            "check_return_types": True,
            "enforce_snake_case": True
        }
    }
)

# Categorize inconsistencies by type
inconsistency_types = {
    "naming": [],
    "parameters": [],
    "return_types": [],
    "error_handling": []
}

for issue in results.get_issues("inconsistent_api"):
    if "naming" in issue.description.lower():
        inconsistency_types["naming"].append(issue)
    elif "parameter" in issue.description.lower():
        inconsistency_types["parameters"].append(issue)
    elif "return" in issue.description.lower():
        inconsistency_types["return_types"].append(issue)
    elif "error" in issue.description.lower():
        inconsistency_types["error_handling"].append(issue)

for category, issues in inconsistency_types.items():
    print(f"{category.title()} inconsistencies: {len(issues)}")
```

### Generate API Standards Document
```python
def generate_api_standards_report(results):
    """Generate a report of API inconsistencies to help create standards."""
    
    naming_patterns = set()
    parameter_patterns = set()
    return_patterns = set()
    
    for issue in results.get_issues("inconsistent_api"):
        # Extract patterns from inconsistency reports
        if hasattr(issue, 'patterns'):
            naming_patterns.update(issue.patterns.get('naming', []))
            parameter_patterns.update(issue.patterns.get('parameters', []))
            return_patterns.update(issue.patterns.get('returns', []))
    
    report = f"""
# API Consistency Report

## Found Naming Patterns
{chr(10).join(f"- {pattern}" for pattern in sorted(naming_patterns))}

## Parameter Patterns
{chr(10).join(f"- {pattern}" for pattern in sorted(parameter_patterns))}

## Return Type Patterns  
{chr(10).join(f"- {pattern}" for pattern in sorted(return_patterns))}

## Recommendations
1. Choose one naming convention and apply consistently
2. Standardize parameter ordering for similar operations
3. Use consistent return types for similar functions
4. Implement uniform error handling patterns
"""
    
    return report
```

## Related Detectors

- **Clone**: Inconsistent APIs often result in duplicated logic
- **Alternative Implementation**: Multiple implementations may have different interfaces
- **Dead Code**: Inconsistent APIs may lead to some versions becoming unused

## Troubleshooting

**Too many false positives?**
- Increase `similarity_threshold`
- Add exclude patterns for different API layers
- Separate analysis for public vs internal APIs

**Missing obvious inconsistencies?**
- Lower `similarity_threshold`
- Enable all consistency checks
- Review function grouping patterns

**Performance issues with large codebases?**
- Disable `include_private_methods`
- Analyze modules separately
- Focus on specific function groups
