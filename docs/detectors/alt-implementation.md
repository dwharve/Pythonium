# Alternative Implementation Detector

The Alternative Implementation Detector finds semantically similar utilities and functions that compete for the same purpose, helping consolidate redundant code and improve maintainability.

## What it Detects

- Multiple functions that solve the same problem differently
- Competing utility implementations across modules
- Similar functionality with different interfaces
- Redundant helper functions
- Alternative approaches to the same algorithm
- Overlapping business logic implementations

## When to Use

- **Code consolidation**: Identify redundant implementations for merging
- **API standardization**: Find competing interfaces for the same functionality
- **Refactoring planning**: Discover consolidation opportunities
- **Architecture review**: Identify unnecessary duplication of logic
- **Library design**: Ensure single responsibility for each function

## Configuration Options

```yaml
detectors:
  alt_implementation:
    # Similarity threshold for semantic comparison
    similarity_threshold: 0.75
    
    # Minimum function complexity to analyze
    min_complexity: 3
    
    # Include functions with different signatures
    different_signatures: true
    
    # Cross-module analysis
    cross_module: true
    
    # Algorithm similarity detection
    algorithm_similarity: true
    
    # Ignore trivial differences (whitespace, variable names)
    ignore_trivial: true
    
    # Functional equivalence testing
    test_equivalence: false
```

## Example Output

```
[ERROR] Alternative Implementation: Competing utility functions detected
  Functions: utils/formatting.py:format_date() vs helpers/dates.py:date_formatter()
  Similarity: 89%
  Both functions format dates but with different interfaces
  Suggestion: Consolidate into single implementation
  
[WARN] Alternative Implementation: Similar validation logic
  Functions: models/user.py:validate_email() vs validators/email.py:check_email_format()
  Similarity: 76%
  Different approaches to email validation
  Suggestion: Use consistent validation approach
  
[INFO] Alternative Implementation: Algorithm variations detected
  Functions: processors/data.py:sort_items() vs utils/sorting.py:item_sorter()
  Similarity: 82%
  Different sorting algorithms for same data type
  Suggestion: Benchmark and choose optimal implementation
```

## Common Alternative Implementation Patterns

### Competing Utility Functions
```python
# File: utils/string_helpers.py
def format_phone_number(phone):
    """Format phone number with dashes."""
    clean = ''.join(filter(str.isdigit, phone))
    if len(clean) == 10:
        return f"{clean[:3]}-{clean[3:6]}-{clean[6:]}"
    return phone

# File: formatters/phone.py - Alternative implementation
def phone_formatter(number):
    """Format phone number with parentheses."""
    digits = re.sub(r'\D', '', number)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return number

# File: models/contact.py - Yet another approach
class Contact:
    def format_phone(self):
        """Format phone as international number."""
        clean = re.sub(r'[^\d]', '', self.phone)
        if len(clean) == 10:
            return f"+1-{clean[:3]}-{clean[3:6]}-{clean[6:]}"
        return self.phone
```

**Consolidated approach:**
```python
# File: utils/phone_formatter.py
from enum import Enum

class PhoneFormat(Enum):
    DASHES = "dashes"           # 555-123-4567
    PARENTHESES = "parentheses" # (555) 123-4567
    INTERNATIONAL = "international" # +1-555-123-4567

def format_phone_number(phone: str, format_type: PhoneFormat = PhoneFormat.DASHES) -> str:
    """Unified phone formatting function."""
    clean_digits = re.sub(r'\D', '', phone)
    
    if len(clean_digits) != 10:
        return phone  # Return original if not valid US number
    
    area, exchange, number = clean_digits[:3], clean_digits[3:6], clean_digits[6:]
    
    if format_type == PhoneFormat.DASHES:
        return f"{area}-{exchange}-{number}"
    elif format_type == PhoneFormat.PARENTHESES:
        return f"({area}) {exchange}-{number}"
    elif format_type == PhoneFormat.INTERNATIONAL:
        return f"+1-{area}-{exchange}-{number}"
    else:
        return phone
```

### Multiple Validation Approaches
```python
# File: validators/email_basic.py
def validate_email(email):
    """Basic email validation."""
    return '@' in email and '.' in email.split('@')[1]

# File: validators/email_regex.py
import re

def is_valid_email(email):
    """Regex-based email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# File: validators/email_advanced.py
import dns.resolver
from email_validator import validate_email as external_validate

def check_email_validity(email):
    """Advanced email validation with DNS checking."""
    try:
        validation = external_validate(email)
        return True
    except:
        return False
```

**Unified validation approach:**
```python
# File: validators/email.py
import re
from typing import Union, Tuple
from enum import Enum

class EmailValidationLevel(Enum):
    BASIC = "basic"
    REGEX = "regex" 
    FULL = "full"

class EmailValidationResult:
    def __init__(self, is_valid: bool, message: str = ""):
        self.is_valid = is_valid
        self.message = message

def validate_email(email: str, level: EmailValidationLevel = EmailValidationLevel.REGEX) -> EmailValidationResult:
    """Unified email validation with configurable strictness."""
    
    if not email or not isinstance(email, str):
        return EmailValidationResult(False, "Email must be a non-empty string")
    
    if level == EmailValidationLevel.BASIC:
        is_valid = '@' in email and '.' in email.split('@')[1]
        return EmailValidationResult(is_valid, "Basic format check")
    
    elif level == EmailValidationLevel.REGEX:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = re.match(pattern, email) is not None
        return EmailValidationResult(is_valid, "Regex pattern validation")
    
    elif level == EmailValidationLevel.FULL:
        try:
            from email_validator import validate_email as external_validate
            validation = external_validate(email)
            return EmailValidationResult(True, "Full validation passed")
        except Exception as e:
            return EmailValidationResult(False, f"Validation failed: {str(e)}")
```

### Algorithm Alternatives
```python
# File: sorting/bubble_sort.py
def sort_items(items):
    """Sort using bubble sort algorithm."""
    arr = items.copy()
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

# File: sorting/quick_sort.py
def sort_data(data):
    """Sort using quicksort algorithm."""
    if len(data) <= 1:
        return data
    
    pivot = data[len(data) // 2]
    left = [x for x in data if x < pivot]
    middle = [x for x in data if x == pivot]
    right = [x for x in data if x > pivot]
    
    return sort_data(left) + middle + sort_data(right)

# File: sorting/merge_sort.py  
def merge_sort_items(items):
    """Sort using merge sort algorithm."""
    if len(items) <= 1:
        return items
    
    mid = len(items) // 2
    left = merge_sort_items(items[:mid])
    right = merge_sort_items(items[mid:])
    
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    result.extend(left[i:])
    result.extend(right[j:])
    return result
```

**Unified sorting with strategy pattern:**
```python
# File: sorting/unified_sort.py
from abc import ABC, abstractmethod
from typing import List, Any, Callable
from enum import Enum

class SortAlgorithm(Enum):
    PYTHON_BUILTIN = "builtin"
    QUICKSORT = "quicksort"
    MERGESORT = "mergesort"
    HEAPSORT = "heapsort"

class SortStrategy(ABC):
    @abstractmethod
    def sort(self, items: List[Any], key: Callable = None, reverse: bool = False) -> List[Any]:
        pass

class BuiltinSort(SortStrategy):
    def sort(self, items: List[Any], key: Callable = None, reverse: bool = False) -> List[Any]:
        return sorted(items, key=key, reverse=reverse)

class QuickSort(SortStrategy):
    def sort(self, items: List[Any], key: Callable = None, reverse: bool = False) -> List[Any]:
        # Implementation of quicksort with key and reverse support
        pass

class MergeSort(SortStrategy):
    def sort(self, items: List[Any], key: Callable = None, reverse: bool = False) -> List[Any]:
        # Implementation of mergesort with key and reverse support
        pass

def sort_items(items: List[Any], algorithm: SortAlgorithm = SortAlgorithm.PYTHON_BUILTIN, 
               key: Callable = None, reverse: bool = False) -> List[Any]:
    """Unified sorting function with pluggable algorithms."""
    
    strategies = {
        SortAlgorithm.PYTHON_BUILTIN: BuiltinSort(),
        SortAlgorithm.QUICKSORT: QuickSort(),
        SortAlgorithm.MERGESORT: MergeSort(),
    }
    
    strategy = strategies.get(algorithm, BuiltinSort())
    return strategy.sort(items, key, reverse)
```

### Competing Data Processing Approaches
```python
# File: processors/csv_handler.py
def process_csv_file(filename):
    """Process CSV using csv module."""
    import csv
    results = []
    with open(filename, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            results.append(row)
    return results

# File: processors/pandas_handler.py
def load_csv_data(filepath):
    """Process CSV using pandas."""
    import pandas as pd
    df = pd.read_csv(filepath)
    return df.to_dict('records')

# File: processors/manual_parser.py
def parse_csv_manually(file_path):
    """Manual CSV parsing without libraries."""
    results = []
    with open(file_path, 'r') as file:
        lines = file.readlines()
        headers = lines[0].strip().split(',')
        
        for line in lines[1:]:
            values = line.strip().split(',')
            row = dict(zip(headers, values))
            results.append(row)
    
    return results
```

**Unified CSV processing with adapter pattern:**
```python
# File: processors/csv_processor.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum

class CsvBackend(Enum):
    STANDARD_LIB = "csv"
    PANDAS = "pandas"
    MANUAL = "manual"

class CsvAdapter(ABC):
    @abstractmethod
    def read_csv(self, filepath: str) -> List[Dict[str, Any]]:
        pass

class StandardLibCsvAdapter(CsvAdapter):
    def read_csv(self, filepath: str) -> List[Dict[str, Any]]:
        import csv
        results = []
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            results = list(reader)
        return results

class PandasCsvAdapter(CsvAdapter):
    def read_csv(self, filepath: str) -> List[Dict[str, Any]]:
        import pandas as pd
        df = pd.read_csv(filepath)
        return df.to_dict('records')

class ManualCsvAdapter(CsvAdapter):
    def read_csv(self, filepath: str) -> List[Dict[str, Any]]:
        results = []
        with open(filepath, 'r') as file:
            lines = file.readlines()
            if not lines:
                return results
            
            headers = [h.strip() for h in lines[0].strip().split(',')]
            
            for line in lines[1:]:
                values = [v.strip() for v in line.strip().split(',')]
                row = dict(zip(headers, values))
                results.append(row)
        
        return results

def process_csv(filepath: str, backend: CsvBackend = CsvBackend.STANDARD_LIB) -> List[Dict[str, Any]]:
    """Unified CSV processing with selectable backend."""
    
    adapters = {
        CsvBackend.STANDARD_LIB: StandardLibCsvAdapter(),
        CsvBackend.PANDAS: PandasCsvAdapter(),
        CsvBackend.MANUAL: ManualCsvAdapter(),
    }
    
    adapter = adapters.get(backend, StandardLibCsvAdapter())
    return adapter.read_csv(filepath)
```

## Consolidation Strategies

### 1. Extract Common Interface
```python
# Define common interface for alternative implementations
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    @abstractmethod
    def process(self, data: Any) -> Any:
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        pass

# Implement alternatives as strategies
class FastProcessor(DataProcessor):
    def process(self, data):
        # Fast but less accurate implementation
        pass
    
    def get_algorithm_name(self):
        return "fast"

class AccurateProcessor(DataProcessor):
    def process(self, data):
        # Slower but more accurate implementation
        pass
    
    def get_algorithm_name(self):
        return "accurate"
```

### 2. Configuration-Driven Selection
```python
from typing import Dict, Any
import json

class ConfigurableProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.algorithm = config.get('algorithm', 'default')
    
    def process(self, data):
        if self.algorithm == 'fast':
            return self._fast_process(data)
        elif self.algorithm == 'accurate':
            return self._accurate_process(data)
        else:
            return self._default_process(data)
    
    def _fast_process(self, data):
        # Fast implementation
        pass
    
    def _accurate_process(self, data):
        # Accurate implementation  
        pass
    
    def _default_process(self, data):
        # Default implementation
        pass

# Usage
config = json.load(open('config.json'))
processor = ConfigurableProcessor(config)
result = processor.process(data)
```

### 3. Benchmarking and Selection
```python
import time
from typing import Callable, List, Any, Tuple

class BenchmarkedProcessor:
    def __init__(self):
        self.algorithms = {
            'algorithm_a': self._algorithm_a,
            'algorithm_b': self._algorithm_b,
            'algorithm_c': self._algorithm_c,
        }
        self.performance_cache = {}
    
    def benchmark_algorithms(self, test_data: List[Any]) -> Dict[str, float]:
        """Benchmark all algorithms and return performance metrics."""
        results = {}
        
        for name, algorithm in self.algorithms.items():
            start_time = time.time()
            
            for data in test_data:
                algorithm(data)
            
            execution_time = time.time() - start_time
            results[name] = execution_time
        
        return results
    
    def get_best_algorithm(self, test_data: List[Any]) -> str:
        """Return the name of the fastest algorithm for given data."""
        if not self.performance_cache:
            self.performance_cache = self.benchmark_algorithms(test_data)
        
        return min(self.performance_cache, key=self.performance_cache.get)
    
    def process_with_best_algorithm(self, data: Any, test_data: List[Any] = None) -> Any:
        """Process data using the best performing algorithm."""
        if test_data:
            best_algorithm_name = self.get_best_algorithm(test_data)
        else:
            best_algorithm_name = 'algorithm_a'  # Default
        
        algorithm = self.algorithms[best_algorithm_name]
        return algorithm(data)
```

## Best Practices

1. **Analyze before consolidating**: Understand why alternatives exist
2. **Preserve functionality**: Ensure consolidated version supports all use cases
3. **Benchmark performance**: Choose the best performing approach
4. **Gradual migration**: Replace alternatives incrementally
5. **Document decisions**: Record why certain approaches were chosen

## Integration Examples

### Command Line
```bash
# Find alternative implementations
pythonium crawl --detectors alt_implementation src/

# High similarity threshold for exact alternatives
pythonium crawl --detectors alt_implementation --config alt_implementation.similarity_threshold=0.9 src/

# Cross-module analysis
pythonium crawl --detectors alt_implementation --config alt_implementation.cross_module=true src/
```

### Python API
```python
from pythonium import analyze_code

results = analyze_code(
    path="src/",
    detectors=["alt_implementation"],
    config={
        "alt_implementation": {
            "similarity_threshold": 0.8,
            "different_signatures": True,
            "cross_module": True
        }
    }
)

# Group alternatives by functionality
alternatives_by_function = {}
for issue in results.get_issues("alt_implementation"):
    function_type = issue.metadata.get("function_category", "unknown")
    if function_type not in alternatives_by_function:
        alternatives_by_function[function_type] = []
    alternatives_by_function[function_type].append(issue)

# Report consolidation opportunities
for function_type, alternatives in alternatives_by_function.items():
    print(f"\n{function_type.title()} alternatives found: {len(alternatives)}")
    for alt in alternatives:
        print(f"  - {alt.description}")
```

### Consolidation Planning Script
```python
def create_consolidation_plan(results):
    """Create a plan for consolidating alternative implementations."""
    
    consolidation_groups = []
    processed_functions = set()
    
    for issue in results.get_issues("alt_implementation"):
        if issue.function_name in processed_functions:
            continue
        
        # Find all related alternatives
        related_functions = [issue.function_name]
        for other_issue in results.get_issues("alt_implementation"):
            if (other_issue.function_name != issue.function_name and
                other_issue.metadata.get("similar_to") == issue.function_name):
                related_functions.append(other_issue.function_name)
        
        if len(related_functions) > 1:
            consolidation_groups.append({
                "functions": related_functions,
                "primary_function": issue.function_name,
                "consolidation_priority": calculate_priority(related_functions),
                "estimated_effort": estimate_consolidation_effort(related_functions)
            })
            
            processed_functions.update(related_functions)
    
    return sorted(consolidation_groups, key=lambda x: x["consolidation_priority"], reverse=True)

def calculate_priority(functions):
    """Calculate consolidation priority based on usage and complexity."""
    # Implementation would analyze function usage and complexity
    return len(functions) * 10  # Simple heuristic

def estimate_consolidation_effort(functions):
    """Estimate effort required for consolidation."""
    # Implementation would analyze function complexity and dependencies
    if len(functions) <= 2:
        return "Low"
    elif len(functions) <= 4:
        return "Medium"
    else:
        return "High"
```

## Related Detectors

- **Clone**: Alternative implementations often contain duplicate code
- **Semantic Equivalence**: Finds functionally equivalent code with different implementations
- **Inconsistent API**: Alternative implementations may have inconsistent interfaces

## Troubleshooting

**Too many false positives?**
- Increase `similarity_threshold`
- Disable `different_signatures` if needed
- Add function complexity minimum

**Missing obvious alternatives?**
- Lower `similarity_threshold`
- Enable `cross_module` analysis
- Check `algorithm_similarity` setting

**Performance issues?**
- Increase `min_complexity` to focus on substantial functions
- Disable `test_equivalence` for faster analysis
- Analyze modules separately for large codebases
