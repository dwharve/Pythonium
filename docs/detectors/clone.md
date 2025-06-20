# Clone Detector

The Clone Detector identifies duplicate and similar code blocks, helping reduce technical debt and improve maintainability through code consolidation.

## What it Detects

- Exact code duplicates across files
- Similar code blocks with minor variations
- Copy-paste code with slight modifications
- Repeated logic patterns
- Function-level and block-level clones

## When to Use

- **Refactoring planning**: Identify consolidation opportunities
- **Code reviews**: Prevent introduction of duplicates
- **Technical debt reduction**: Systematically eliminate duplication
- **Maintenance optimization**: Reduce effort needed for bug fixes and updates

## Configuration Options

```yaml
detectors:
  clone:
    # Similarity threshold (0.0-1.0, higher = more similar required)
    similarity_threshold: 0.8
    
    # Minimum lines to consider for cloning
    min_lines: 5
    
    # Maximum distance between similar blocks
    max_distance: 100
    
    # Whether to include cross-file clones
    cross_file: true
    
    # Ignore whitespace and comments in comparison
    ignore_formatting: true
```

## Example Output

```
[ERROR] Clone: Duplicate code block detected
  Files: src/auth.py:45-52, src/utils.py:123-130
  Similarity: 95%
  8 lines of nearly identical code
  
[WARN] Clone: Similar code pattern found
  Files: src/processor.py:67-74, src/handler.py:34-41
  Similarity: 82%
  Consider extracting common functionality
  
[INFO] Clone: Repeated validation pattern
  Files: src/models/user.py:12-18, src/models/product.py:89-95
  Similarity: 78%
  Similar validation logic detected
```

## Common Patterns Detected

### Exact Duplicates
```python
# File 1: auth.py
def validate_user_input(data):
    if not data:
        raise ValueError("Data cannot be empty")
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    return True

# File 2: utils.py - Exact duplicate
def validate_user_input(data):  # Clone detected
    if not data:
        raise ValueError("Data cannot be empty")
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    return True
```

### Similar Code with Variations
```python
# File 1: user_service.py
def create_user(name, email):
    if not name or not email:
        raise ValueError("Missing required fields")
    user = User(name=name, email=email)
    user.save()
    return user

# File 2: product_service.py - Similar pattern
def create_product(title, price):  # Clone detected (similar structure)
    if not title or not price:
        raise ValueError("Missing required fields")
    product = Product(title=title, price=price)
    product.save()
    return product
```

### Copy-Paste with Modifications
```python
# Original implementation
def process_json_data(data):
    try:
        parsed = json.loads(data)
        validated = validate_schema(parsed)
        return transform_data(validated)
    except Exception as e:
        logger.error(f"JSON processing failed: {e}")
        raise

# Copy-paste with slight changes - detected as clone
def process_xml_data(data):
    try:
        parsed = xml_parser.parse(data)  # Only this line differs
        validated = validate_schema(parsed)
        return transform_data(validated)
    except Exception as e:
        logger.error(f"XML processing failed: {e}")  # And this message
        raise
```

## Refactoring Strategies

### Extract Common Function
```python
# Before: Duplicated code
def validate_user_data(data):
    if not data:
        raise ValueError("Data cannot be empty")
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    return True

def validate_product_data(data):
    if not data:
        raise ValueError("Data cannot be empty") 
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    return True

# After: Extracted common function
def validate_input_data(data, data_type="data"):
    if not data:
        raise ValueError(f"{data_type} cannot be empty")
    if not isinstance(data, dict):
        raise ValueError(f"{data_type} must be a dictionary")
    return True

def validate_user_data(data):
    return validate_input_data(data, "User data")

def validate_product_data(data):
    return validate_input_data(data, "Product data")
```

### Use Template Pattern
```python
# Before: Similar processing logic
def process_user_request(request):
    # Authentication logic (duplicated)
    if not authenticate(request):
        return error_response("Authentication failed")
    
    # User-specific processing
    user = get_user(request.user_id)
    return success_response(user)

def process_product_request(request):
    # Authentication logic (duplicated)
    if not authenticate(request):
        return error_response("Authentication failed")
    
    # Product-specific processing
    product = get_product(request.product_id)
    return success_response(product)

# After: Template pattern
class RequestProcessor:
    def process_request(self, request):
        if not self.authenticate(request):
            return error_response("Authentication failed")
        
        result = self.handle_specific_logic(request)
        return success_response(result)
    
    def authenticate(self, request):
        return authenticate(request)
    
    def handle_specific_logic(self, request):
        raise NotImplementedError

class UserRequestProcessor(RequestProcessor):
    def handle_specific_logic(self, request):
        return get_user(request.user_id)

class ProductRequestProcessor(RequestProcessor):
    def handle_specific_logic(self, request):
        return get_product(request.product_id)
```

## Best Practices

1. **Start with high similarity**: Focus on exact or near-exact duplicates first
2. **Consider context**: Not all similar code should be consolidated
3. **Extract incrementally**: Small, focused refactoring is safer
4. **Maintain tests**: Ensure behavior doesn't change during consolidation
5. **Document decisions**: Record why certain "clones" should remain separate

## Integration Examples

### Command Line
```bash
# Analyze for code clones only
pythonium crawl --detectors clone src/

# Adjust similarity threshold
pythonium crawl --detectors clone --config clone.similarity_threshold=0.9 src/

# Focus on larger clones
pythonium crawl --detectors clone --config clone.min_lines=10 src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["clone"],
    config={
        "clone": {
            "similarity_threshold": 0.85,
            "min_lines": 6,
            "cross_file": True
        }
    }
)

# Group clones by similarity for prioritization
clones_by_similarity = {}
for issue in results.get_issues("clone"):
    similarity = issue.metadata.get("similarity", 0)
    if similarity not in clones_by_similarity:
        clones_by_similarity[similarity] = []
    clones_by_similarity[similarity].append(issue)

# Process highest similarity clones first
for similarity in sorted(clones_by_similarity.keys(), reverse=True):
    print(f"Clones with {similarity}% similarity:")
    for clone in clones_by_similarity[similarity]:
        print(f"  {clone.description}")
```

## Related Detectors

- **Block Clone**: Detects smaller-scale duplicates within functions
- **Semantic Equivalence**: Finds functionally equivalent code with different implementations
- **Alternative Implementation**: Identifies competing implementations of similar functionality

## Troubleshooting

**Too many false positives?**
- Increase `similarity_threshold`
- Raise `min_lines` to focus on larger clones
- Add exclude patterns for generated code

**Missing obvious clones?**
- Lower `similarity_threshold`
- Enable `ignore_formatting` for minor style differences
- Check `cross_file` setting for inter-file clones

**Performance issues with large codebases?**
- Increase `min_lines` to reduce analysis scope
- Use `max_distance` to limit comparison range
- Consider analyzing subdirectories separately
