# Block Clone Detector

The Block Clone Detector finds duplicate code blocks within and across functions at the statement level, providing fine-grained detection of code duplication for targeted refactoring.

## What it Detects

- Duplicate statement sequences within functions
- Similar code blocks across different methods
- Copy-paste code at the statement level
- Repeated code patterns within loops and conditionals
- Cross-function statement-level duplicates
- Similar error handling blocks

## When to Use

- **Fine-grained refactoring**: Extract common statement sequences
- **Method-level optimization**: Find internal duplication within functions
- **Code review preparation**: Identify copy-paste patterns
- **Extract method opportunities**: Find candidates for helper methods
- **Statement-level analysis**: When function-level clone detection is too coarse

## Configuration Options

```yaml
detectors:
  block_clone:
    # Minimum number of statements to consider as a block
    min_block_size: 3
    
    # Maximum number of statements in a block
    max_block_size: 20
    
    # Similarity threshold for block comparison
    similarity_threshold: 0.85
    
    # Allow gaps between similar statements
    allow_gaps: true
    
    # Maximum gap size when allow_gaps is true
    max_gap_size: 2
    
    # Include blocks across different functions
    cross_function: true
    
    # Ignore variable name differences
    ignore_variable_names: true
    
    # Ignore literal value differences
    ignore_literals: false
```

## Example Output

```
[ERROR] Block Clone: Duplicate statement block detected
  Locations: src/processor.py:45-48, src/handler.py:67-70
  Block size: 4 statements
  Similarity: 92%
  Consider extracting to helper method
  
[WARN] Block Clone: Similar error handling pattern
  Locations: src/auth.py:23-26, src/auth.py:89-92
  Block size: 4 statements
  Pattern: try-except with logging
  Consider extracting error handling method
  
[INFO] Block Clone: Repeated validation sequence
  Locations: src/models/user.py:34-36, src/models/product.py:78-80
  Block size: 3 statements
  Pattern: Input validation and sanitization
  Consider creating validation utility
```

## Common Block Clone Patterns

### Duplicate Statement Sequences
```python
# Function 1: User validation
def validate_user_data(data):
    # Block clone starts here
    if not data:
        logger.error("Data is empty")
        raise ValueError("Data cannot be empty")
    
    if not isinstance(data, dict):
        logger.error("Data is not a dictionary") 
        raise ValueError("Data must be a dictionary")
    # Block clone ends here
    
    # User-specific validation
    if 'email' not in data:
        raise ValueError("Email is required")

# Function 2: Product validation - contains duplicate block
def validate_product_data(data):
    # Block clone starts here (same as above)
    if not data:
        logger.error("Data is empty")
        raise ValueError("Data cannot be empty")
    
    if not isinstance(data, dict):
        logger.error("Data is not a dictionary")
        raise ValueError("Data must be a dictionary") 
    # Block clone ends here
    
    # Product-specific validation
    if 'name' not in data:
        raise ValueError("Product name is required")
```

**Refactored with extracted method:**
```python
def validate_base_data(data, data_type="data"):
    """Common validation for all data inputs."""
    if not data:
        logger.error(f"{data_type} is empty")
        raise ValueError(f"{data_type} cannot be empty")
    
    if not isinstance(data, dict):
        logger.error(f"{data_type} is not a dictionary")
        raise ValueError(f"{data_type} must be a dictionary")

def validate_user_data(data):
    validate_base_data(data, "User data")
    
    if 'email' not in data:
        raise ValueError("Email is required")

def validate_product_data(data):
    validate_base_data(data, "Product data")
    
    if 'name' not in data:
        raise ValueError("Product name is required")
```

### Repeated Error Handling Blocks
```python
# Multiple functions with similar error handling
def process_user_request(request):
    try:
        result = handle_user_logic(request)
        return {"success": True, "data": result}
    except ValidationError as e:
        logger.error(f"Validation error in user processing: {e}")
        return {"success": False, "error": str(e), "code": 400}
    except DatabaseError as e:
        logger.error(f"Database error in user processing: {e}")
        return {"success": False, "error": "Database unavailable", "code": 500}
    except Exception as e:
        logger.error(f"Unexpected error in user processing: {e}")
        return {"success": False, "error": "Internal error", "code": 500}

def process_product_request(request):
    try:
        result = handle_product_logic(request)
        return {"success": True, "data": result}
    except ValidationError as e:
        logger.error(f"Validation error in product processing: {e}")
        return {"success": False, "error": str(e), "code": 400}
    except DatabaseError as e:
        logger.error(f"Database error in product processing: {e}")
        return {"success": False, "error": "Database unavailable", "code": 500}
    except Exception as e:
        logger.error(f"Unexpected error in product processing: {e}")
        return {"success": False, "error": "Internal error", "code": 500}
```

**Refactored with decorator:**
```python
from functools import wraps

def handle_api_errors(operation_name):
    """Decorator to handle common API errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(request):
            try:
                result = func(request)
                return {"success": True, "data": result}
            except ValidationError as e:
                logger.error(f"Validation error in {operation_name}: {e}")
                return {"success": False, "error": str(e), "code": 400}
            except DatabaseError as e:
                logger.error(f"Database error in {operation_name}: {e}")
                return {"success": False, "error": "Database unavailable", "code": 500}
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                return {"success": False, "error": "Internal error", "code": 500}
        return wrapper
    return decorator

@handle_api_errors("user processing")
def process_user_request(request):
    return handle_user_logic(request)

@handle_api_errors("product processing")
def process_product_request(request):
    return handle_product_logic(request)
```

### Database Operation Patterns
```python
# Repeated database connection and transaction patterns
def save_user(user_data):
    connection = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        
        query = "INSERT INTO users (name, email) VALUES (?, ?)"
        cursor.execute(query, (user_data['name'], user_data['email']))
        
        connection.commit()
        return cursor.lastrowid
        
    except Exception as e:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

def save_product(product_data):
    connection = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        
        query = "INSERT INTO products (name, price) VALUES (?, ?)"
        cursor.execute(query, (product_data['name'], product_data['price']))
        
        connection.commit()
        return cursor.lastrowid
        
    except Exception as e:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()
```

**Refactored with context manager:**
```python
from contextlib import contextmanager

@contextmanager
def database_transaction():
    """Context manager for database transactions."""
    connection = None
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        yield cursor
        connection.commit()
    except Exception as e:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

def save_user(user_data):
    with database_transaction() as cursor:
        query = "INSERT INTO users (name, email) VALUES (?, ?)"
        cursor.execute(query, (user_data['name'], user_data['email']))
        return cursor.lastrowid

def save_product(product_data):
    with database_transaction() as cursor:
        query = "INSERT INTO products (name, price) VALUES (?, ?)"
        cursor.execute(query, (product_data['name'], product_data['price']))
        return cursor.lastrowid
```

### File Processing Patterns
```python
# Repeated file handling patterns
def process_csv_file(filename):
    file_handle = None
    try:
        file_handle = open(filename, 'r')
        reader = csv.reader(file_handle)
        headers = next(reader)
        
        data = []
        for row in reader:
            record = dict(zip(headers, row))
            data.append(record)
            
        return data
        
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        raise
    except PermissionError:
        logger.error(f"Permission denied: {filename}")
        raise
    finally:
        if file_handle:
            file_handle.close()

def process_json_file(filename):
    file_handle = None
    try:
        file_handle = open(filename, 'r')
        data = json.load(file_handle)
        return data
        
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        raise
    except PermissionError:
        logger.error(f"Permission denied: {filename}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {filename}")
        raise
    finally:
        if file_handle:
            file_handle.close()
```

**Refactored with template method:**
```python
from abc import ABC, abstractmethod

class FileProcessor(ABC):
    """Template for file processing with common error handling."""
    
    def process_file(self, filename):
        """Template method with common file handling."""
        file_handle = None
        try:
            file_handle = self._open_file(filename)
            data = self._parse_file(file_handle)
            return self._process_data(data)
            
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            raise
        except PermissionError:
            logger.error(f"Permission denied: {filename}")
            raise
        finally:
            if file_handle:
                file_handle.close()
    
    def _open_file(self, filename):
        return open(filename, 'r')
    
    @abstractmethod
    def _parse_file(self, file_handle):
        pass
    
    def _process_data(self, data):
        return data

class CsvProcessor(FileProcessor):
    def _parse_file(self, file_handle):
        reader = csv.reader(file_handle)
        headers = next(reader)
        
        data = []
        for row in reader:
            record = dict(zip(headers, row))
            data.append(record)
        return data

class JsonProcessor(FileProcessor):
    def _parse_file(self, file_handle):
        try:
            return json.load(file_handle)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            raise

# Usage
csv_processor = CsvProcessor()
json_processor = JsonProcessor()

csv_data = csv_processor.process_file("data.csv")
json_data = json_processor.process_file("config.json")
```

## Refactoring Strategies

### Extract Method
```python
# Before: Repeated blocks within the same class
class DataProcessor:
    def process_user_data(self, data):
        # Validation block (repeated)
        if not data:
            raise ValueError("Data cannot be empty")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        # User processing logic
        return self._handle_user(data)
    
    def process_product_data(self, data):
        # Validation block (repeated)
        if not data:
            raise ValueError("Data cannot be empty")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        # Product processing logic
        return self._handle_product(data)

# After: Extracted validation method
class DataProcessor:
    def _validate_input_data(self, data):
        """Common validation for all input data."""
        if not data:
            raise ValueError("Data cannot be empty")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
    
    def process_user_data(self, data):
        self._validate_input_data(data)
        return self._handle_user(data)
    
    def process_product_data(self, data):
        self._validate_input_data(data)
        return self._handle_product(data)
```

### Create Utility Functions
```python
# Extract repeated blocks to utility module
# File: utils/common_operations.py

def safe_divide(numerator, denominator, default=0):
    """Safe division with error handling."""
    if denominator == 0:
        logger.warning("Division by zero attempted")
        return default
    return numerator / denominator

def validate_and_convert_id(id_value):
    """Common ID validation and conversion."""
    if id_value is None:
        raise ValueError("ID cannot be None")
    
    try:
        return int(id_value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid ID format: {id_value}")

def log_operation_time(operation_name, start_time):
    """Common operation timing logging."""
    duration = time.time() - start_time
    logger.info(f"{operation_name} completed in {duration:.2f} seconds")

# File: services/user_service.py
from utils.common_operations import validate_and_convert_id, log_operation_time

class UserService:
    def get_user(self, user_id):
        start_time = time.time()
        
        user_id = validate_and_convert_id(user_id)  # Using utility
        user = self.repository.find_by_id(user_id)
        
        log_operation_time("get_user", start_time)  # Using utility
        return user
```

### Use Design Patterns
```python
# Template Method Pattern for repeated algorithmic structures
class DataAnalyzer(ABC):
    def analyze(self, data):
        """Template method defining analysis steps."""
        self._validate_data(data)
        processed_data = self._preprocess_data(data)
        results = self._perform_analysis(processed_data)
        return self._format_results(results)
    
    def _validate_data(self, data):
        """Common validation (was repeated block)."""
        if not data:
            raise ValueError("Data cannot be empty")
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
    
    @abstractmethod
    def _preprocess_data(self, data):
        pass
    
    @abstractmethod
    def _perform_analysis(self, data):
        pass
    
    def _format_results(self, results):
        """Common result formatting (was repeated block)."""
        return {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "status": "completed"
        }

class StatisticalAnalyzer(DataAnalyzer):
    def _preprocess_data(self, data):
        return [float(x) for x in data if x is not None]
    
    def _perform_analysis(self, data):
        return {
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "std_dev": statistics.stdev(data)
        }
```

## Best Practices

1. **Start with largest blocks**: Extract bigger duplicates first for maximum impact
2. **Consider context**: Ensure extracted code makes logical sense together
3. **Preserve behavior**: Test thoroughly after extracting blocks
4. **Choose good names**: Extracted methods should have clear, descriptive names
5. **Balance granularity**: Don't extract trivially small blocks

## Integration Examples

### Command Line
```bash
# Analyze block-level clones
pythonium crawl --detectors block_clone src/

# Focus on larger blocks
pythonium crawl --detectors block_clone --config block_clone.min_block_size=5 src/

# Allow gaps in blocks
pythonium crawl --detectors block_clone --config block_clone.allow_gaps=true src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["block_clone"],
    config={
        "block_clone": {
            "min_block_size": 4,
            "similarity_threshold": 0.9,
            "cross_function": True,
            "ignore_variable_names": True
        }
    }
)

# Analyze block clone patterns
patterns = {}
for issue in results.get_issues("block_clone"):
    block_type = issue.metadata.get("block_type", "unknown")
    if block_type not in patterns:
        patterns[block_type] = []
    patterns[block_type].append(issue)

# Report by pattern type
for pattern_type, blocks in patterns.items():
    print(f"\n{pattern_type.title()} block clones: {len(blocks)}")
    for block in blocks:
        print(f"  Size: {block.metadata.get('block_size', 'N/A')} statements")
        print(f"  Locations: {block.description}")
```

### Refactoring Candidate Ranking
```python
def rank_extraction_candidates(results):
    """Rank block clones by extraction potential."""
    
    candidates = []
    
    for issue in results.get_issues("block_clone"):
        block_size = issue.metadata.get("block_size", 0)
        similarity = issue.metadata.get("similarity", 0)
        occurrences = issue.metadata.get("occurrence_count", 0)
        
        # Calculate extraction score
        # Larger, more similar, more frequent blocks score higher
        extraction_score = (block_size * 2) + (similarity * 10) + (occurrences * 5)
        
        candidates.append({
            "issue": issue,
            "extraction_score": extraction_score,
            "block_size": block_size,
            "similarity": similarity,
            "occurrences": occurrences
        })
    
    # Sort by extraction score (highest first)
    return sorted(candidates, key=lambda x: x["extraction_score"], reverse=True)

# Usage
ranked_candidates = rank_extraction_candidates(results)
print("Top 5 block extraction candidates:")
for i, candidate in enumerate(ranked_candidates[:5], 1):
    print(f"{i}. Score: {candidate['extraction_score']}")
    print(f"   Size: {candidate['block_size']} statements")
    print(f"   Similarity: {candidate['similarity']:.1%}")
    print(f"   Occurrences: {candidate['occurrences']}")
    print(f"   Description: {candidate['issue'].description}")
    print()
```

## Related Detectors

- **Clone**: Function-level clone detection complements block-level analysis
- **Complexity Hotspot**: Complex functions often contain extractable blocks
- **Alternative Implementation**: Different implementations may share common blocks

## Troubleshooting

**Too many small, trivial blocks?**
- Increase `min_block_size`
- Raise `similarity_threshold`
- Enable `ignore_literals` for minor variations

**Missing obvious block duplicates?**
- Lower `similarity_threshold`
- Enable `allow_gaps` for non-contiguous blocks
- Check `ignore_variable_names` setting

**Performance issues with large functions?**
- Set reasonable `max_block_size`
- Disable `cross_function` for faster analysis
- Focus on specific file patterns
