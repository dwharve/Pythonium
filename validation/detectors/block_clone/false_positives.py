"""
False positive cases for block clone detector.
These contain similar-looking code that should NOT be flagged as clones.
"""

# Case 1: Similar structure but different semantics
def calculate_area_rectangle(width, height):
    """Rectangle area calculation"""
    if width <= 0 or height <= 0:
        raise ValueError("Dimensions must be positive")
    
    result = width * height
    return result

def calculate_area_triangle(base, height):
    """Triangle area calculation - different formula"""
    if base <= 0 or height <= 0:
        raise ValueError("Dimensions must be positive")
    
    result = (base * height) / 2  # Different calculation
    return result

# Case 2: Similar control flow but different operations
def process_integers(numbers):
    """Integer processing logic"""
    results = []
    for num in numbers:
        if isinstance(num, int):
            if num > 0:
                processed = num ** 2  # Square positive integers
                results.append(processed)
    return results

def process_strings(texts):
    """String processing logic - different operations"""
    results = []
    for text in texts:
        if isinstance(text, str):
            if len(text) > 0:
                processed = text.upper()  # Uppercase non-empty strings
                results.append(processed)
    return results

# Case 3: Template method pattern (intentionally similar structure)
class DataProcessor:
    """Base processor with template method"""
    def process(self, data):
        """Template method with common structure"""
        if not self.validate(data):
            return None
        
        preprocessed = self.preprocess(data)
        result = self.transform(preprocessed)
        postprocessed = self.postprocess(result)
        
        return postprocessed
    
    def validate(self, data):
        """Default validation"""
        return data is not None
    
    def preprocess(self, data):
        """Default preprocessing"""
        return data
    
    def transform(self, data):
        """Must be implemented by subclasses"""
        raise NotImplementedError()
    
    def postprocess(self, data):
        """Default postprocessing"""
        return data

class NumberProcessor(DataProcessor):
    """Number-specific processor"""
    def validate(self, data):
        """Number-specific validation"""
        return isinstance(data, (int, float))
    
    def preprocess(self, data):
        """Convert to float"""
        return float(data)
    
    def transform(self, data):
        """Square the number"""
        return data ** 2
    
    def postprocess(self, data):
        """Round to 2 decimal places"""
        return round(data, 2)

class StringProcessor(DataProcessor):
    """String-specific processor"""
    def validate(self, data):
        """String-specific validation"""
        return isinstance(data, str) and len(data) > 0
    
    def preprocess(self, data):
        """Strip whitespace"""
        return data.strip()
    
    def transform(self, data):
        """Convert to uppercase"""
        return data.upper()
    
    def postprocess(self, data):
        """Add prefix"""
        return f"PROCESSED: {data}"

# Case 4: Builder pattern (similar structure, different purpose)
class SqlQueryBuilder:
    """SQL query builder"""
    def __init__(self):
        self._select = []
        self._from = None
        self._where = []
        self._order = []
    
    def select(self, *columns):
        """Add SELECT clause"""
        self._select.extend(columns)
        return self
    
    def from_table(self, table):
        """Add FROM clause"""
        self._from = table
        return self
    
    def where(self, condition):
        """Add WHERE clause"""
        self._where.append(condition)
        return self
    
    def order_by(self, column):
        """Add ORDER BY clause"""
        self._order.append(column)
        return self
    
    def build(self):
        """Build the final query"""
        query_parts = []
        
        if self._select:
            query_parts.append(f"SELECT {', '.join(self._select)}")
        
        if self._from:
            query_parts.append(f"FROM {self._from}")
        
        if self._where:
            query_parts.append(f"WHERE {' AND '.join(self._where)}")
        
        if self._order:
            query_parts.append(f"ORDER BY {', '.join(self._order)}")
        
        return ' '.join(query_parts)

class HttpRequestBuilder:
    """HTTP request builder - similar pattern, different domain"""
    def __init__(self):
        self._method = 'GET'
        self._url = None
        self._headers = {}
        self._params = {}
    
    def method(self, http_method):
        """Set HTTP method"""
        self._method = http_method
        return self
    
    def url(self, request_url):
        """Set request URL"""
        self._url = request_url
        return self
    
    def header(self, key, value):
        """Add header"""
        self._headers[key] = value
        return self
    
    def param(self, key, value):
        """Add query parameter"""
        self._params[key] = value
        return self
    
    def build(self):
        """Build the final request"""
        request_info = {
            'method': self._method,
            'url': self._url,
            'headers': self._headers,
            'params': self._params
        }
        return request_info

# Case 5: Common algorithms with different data types
def binary_search_integers(arr, target):
    """Binary search for integers"""
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

def binary_search_strings(arr, target):
    """Binary search for strings - same algorithm, different comparison"""
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:  # String comparison
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# Case 6: State machine implementations
class OrderStateMachine:
    """Order state machine"""
    def __init__(self):
        self.state = 'pending'
        self.transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['shipped', 'cancelled'],
            'shipped': ['delivered'],
            'delivered': [],
            'cancelled': []
        }
    
    def transition_to(self, new_state):
        """Transition to new state"""
        if new_state not in self.transitions[self.state]:
            raise ValueError(f"Invalid transition from {self.state} to {new_state}")
        
        old_state = self.state
        self.state = new_state
        self._on_state_change(old_state, new_state)
    
    def _on_state_change(self, old_state, new_state):
        """Handle state change for orders"""
        print(f"Order state changed: {old_state} -> {new_state}")

class PaymentStateMachine:
    """Payment state machine - similar structure, different domain"""
    def __init__(self):
        self.state = 'initialized'
        self.transitions = {
            'initialized': ['processing', 'failed'],
            'processing': ['completed', 'failed'],
            'completed': ['refunded'],
            'failed': ['retry'],
            'retry': ['processing', 'failed'],
            'refunded': []
        }
    
    def transition_to(self, new_state):
        """Transition to new state"""
        if new_state not in self.transitions[self.state]:
            raise ValueError(f"Invalid transition from {self.state} to {new_state}")
        
        old_state = self.state
        self.state = new_state
        self._on_state_change(old_state, new_state)
    
    def _on_state_change(self, old_state, new_state):
        """Handle state change for payments"""
        print(f"Payment state changed: {old_state} -> {new_state}")
        # Different logic than order state machine
        if new_state == 'failed':
            self._log_failure()
    
    def _log_failure(self):
        """Log payment failure"""
        print("Payment failure logged")
