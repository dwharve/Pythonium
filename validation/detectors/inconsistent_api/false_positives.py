"""
False positive cases for inconsistent API detector.
These contain intentionally different APIs that should NOT be flagged.
"""

# Case 1: Different domains requiring different patterns
class FileProcessor:
    """File processor with domain-appropriate methods"""
    
    def read_text_file(self, filename):
        """Read text file - returns string"""
        with open(filename, 'r') as f:
            return f.read()
    
    def read_binary_file(self, filename):
        """Read binary file - returns bytes (different type appropriate)"""
        with open(filename, 'rb') as f:
            return f.read()
    
    def read_csv_file(self, filename):
        """Read CSV file - returns list of dictionaries (appropriate structure)"""
        import csv
        with open(filename, 'r') as f:
            return list(csv.DictReader(f))
    
    def read_json_file(self, filename):
        """Read JSON file - returns parsed object (appropriate structure)"""
        import json
        with open(filename, 'r') as f:
            return json.load(f)

# Case 2: Different abstraction levels
class DatabaseConnection:
    """Database connection with different abstraction levels"""
    
    def execute_query(self, sql, params=None):
        """Low-level SQL execution - returns raw results"""
        # Simulate database execution
        return [{"id": 1, "name": "test"}]
    
    def get_user(self, user_id):
        """High-level user retrieval - returns domain object"""
        result = self.execute_query("SELECT * FROM users WHERE id = ?", [user_id])
        return User(result[0]) if result else None
    
    def get_users_batch(self, user_ids):
        """Batch operation - returns list (appropriate for batch)"""
        placeholders = ",".join(["?"] * len(user_ids))
        results = self.execute_query(f"SELECT * FROM users WHERE id IN ({placeholders})", user_ids)
        return [User(row) for row in results]

class User:
    """Simple user domain object"""
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']

# Case 3: Protocol/interface implementation differences
class HttpClient:
    """HTTP client"""
    
    def get(self, url, headers=None):
        """HTTP GET - returns response object"""
        return {"status": 200, "body": "response data", "headers": {}}
    
    def post(self, url, data, headers=None):
        """HTTP POST - accepts data parameter"""
        return {"status": 201, "body": "created", "headers": {}}

class WebSocketClient:
    """WebSocket client - different protocol needs different API"""
    
    def connect(self, url):
        """Connect to WebSocket - returns connection status"""
        return True
    
    def send_message(self, message):
        """Send message - no return value (fire and forget)"""
        pass
    
    def receive_message(self, timeout=None):
        """Receive message - blocking operation with timeout"""
        return "received message"
    
    def close(self):
        """Close connection - no return value"""
        pass

# Case 4: Builder pattern with fluent interface
class QueryBuilder:
    """SQL query builder with fluent interface"""
    
    def __init__(self):
        self._select = []
        self._from = None
        self._where = []
    
    def select(self, *columns):
        """Select columns - returns self for chaining"""
        self._select.extend(columns)
        return self
    
    def from_table(self, table):
        """From clause - returns self for chaining"""
        self._from = table
        return self
    
    def where(self, condition):
        """Where clause - returns self for chaining"""
        self._where.append(condition)
        return self
    
    def build(self):
        """Build final query - returns string (terminal operation)"""
        query_parts = [f"SELECT {', '.join(self._select)}"]
        if self._from:
            query_parts.append(f"FROM {self._from}")
        if self._where:
            query_parts.append(f"WHERE {' AND '.join(self._where)}")
        return " ".join(query_parts)

# Case 5: Factory pattern with different creation methods
class ShapeFactory:
    """Shape factory with different creation patterns"""
    
    @staticmethod
    def create_circle(radius):
        """Create circle - single parameter"""
        return Circle(radius)
    
    @staticmethod
    def create_rectangle(width, height):
        """Create rectangle - two parameters"""
        return Rectangle(width, height)
    
    @staticmethod
    def create_polygon(points):
        """Create polygon - list of points"""
        return Polygon(points)
    
    @classmethod
    def from_config(cls, config):
        """Create from configuration - different pattern for complex cases"""
        shape_type = config['type']
        if shape_type == 'circle':
            return cls.create_circle(config['radius'])
        elif shape_type == 'rectangle':
            return cls.create_rectangle(config['width'], config['height'])
        elif shape_type == 'polygon':
            return cls.create_polygon(config['points'])

class Circle:
    def __init__(self, radius):
        self.radius = radius

class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

class Polygon:
    def __init__(self, points):
        self.points = points

# Case 6: Adapter pattern with different interfaces
class LegacyPrinter:
    """Legacy printer with old interface"""
    
    def print_document(self, content, copies=1):
        """Legacy print method"""
        return f"Printed {copies} copies of: {content[:50]}..."

class ModernPrinter:
    """Modern printer with new interface"""
    
    def print(self, document):
        """Modern print method - accepts document object"""
        return f"Printed document: {document.title}"
    
    def print_with_options(self, document, options):
        """Advanced printing with options"""
        return f"Printed {document.title} with options: {options}"

class Document:
    """Document object for modern printer"""
    def __init__(self, title, content):
        self.title = title
        self.content = content

# Case 7: Strategy pattern with different strategies
class SortingContext:
    """Sorting context that uses different sorting strategies"""
    
    def __init__(self, strategy):
        self.strategy = strategy
    
    def sort(self, data):
        """Sort using current strategy"""
        return self.strategy.sort(data)

class QuickSortStrategy:
    """Quick sort strategy"""
    
    def sort(self, data):
        """Sort using quicksort - in-place modification"""
        # Simulate quicksort
        sorted_data = sorted(data)
        data.clear()
        data.extend(sorted_data)
        return data

class MergeSortStrategy:
    """Merge sort strategy"""
    
    def sort(self, data):
        """Sort using mergesort - returns new list"""
        # Simulate mergesort (returns new list)
        return sorted(data)

class HeapSortStrategy:
    """Heap sort strategy"""
    
    def sort(self, data):
        """Sort using heapsort - returns iterator"""
        # Simulate heapsort (returns iterator for memory efficiency)
        return iter(sorted(data))

# Case 8: Command pattern with different command types
class Command:
    """Base command interface"""
    
    def execute(self):
        """Execute command"""
        raise NotImplementedError()

class SimpleCommand(Command):
    """Simple command with no parameters"""
    
    def __init__(self, action):
        self.action = action
    
    def execute(self):
        """Execute simple action - returns result"""
        return self.action()

class ParameterizedCommand(Command):
    """Command with parameters"""
    
    def __init__(self, action, *args, **kwargs):
        self.action = action
        self.args = args
        self.kwargs = kwargs
    
    def execute(self):
        """Execute with parameters - returns result"""
        return self.action(*self.args, **self.kwargs)

class AsyncCommand(Command):
    """Asynchronous command"""
    
    def __init__(self, async_action, callback=None):
        self.async_action = async_action
        self.callback = callback
    
    def execute(self):
        """Execute asynchronously - returns future/task object"""
        # Simulate async execution
        result = self.async_action()
        if self.callback:
            self.callback(result)
        return result

# Case 9: Template method pattern with different implementations
class DataProcessor:
    """Template method pattern base class"""
    
    def process(self, data):
        """Template method"""
        validated = self.validate(data)
        cleaned = self.clean(validated)
        return self.transform(cleaned)
    
    def validate(self, data):
        """Base validation"""
        return data is not None
    
    def clean(self, data):
        """Must be implemented by subclasses"""
        raise NotImplementedError()
    
    def transform(self, data):
        """Must be implemented by subclasses"""
        raise NotImplementedError()

class NumberProcessor(DataProcessor):
    """Process numeric data"""
    
    def clean(self, data):
        """Remove non-numeric values"""
        return [x for x in data if isinstance(x, (int, float))]
    
    def transform(self, data):
        """Apply mathematical transformation"""
        return [x * 2 for x in data]

class TextProcessor(DataProcessor):
    """Process text data"""
    
    def clean(self, data):
        """Clean text data"""
        return [str(x).strip().lower() for x in data if x]
    
    def transform(self, data):
        """Apply text transformation"""
        return [f"processed_{text}" for text in data]

# Case 10: State pattern with different state behaviors
class State:
    """Base state interface"""
    
    def handle(self, context, request):
        """Handle request in this state"""
        raise NotImplementedError()

class IdleState(State):
    """Idle state - can accept new requests"""
    
    def handle(self, context, request):
        """Handle request from idle state"""
        if request == "start":
            context.set_state(ProcessingState())
            return "Started processing"
        return "Invalid request in idle state"

class ProcessingState(State):
    """Processing state - limited operations"""
    
    def handle(self, context, request):
        """Handle request from processing state"""
        if request == "stop":
            context.set_state(IdleState())
            return "Stopped processing"
        elif request == "pause":
            context.set_state(PausedState())
            return "Paused processing"
        return "Cannot handle request while processing"

class PausedState(State):
    """Paused state - can resume or stop"""
    
    def handle(self, context, request):
        """Handle request from paused state"""
        if request == "resume":
            context.set_state(ProcessingState())
            return "Resumed processing"
        elif request == "stop":
            context.set_state(IdleState())
            return "Stopped from pause"
        return "Invalid request in paused state"

class StateContext:
    """Context that manages state"""
    
    def __init__(self):
        self._state = IdleState()
    
    def set_state(self, state):
        """Set current state"""
        self._state = state
    
    def request(self, request):
        """Handle request using current state"""
        return self._state.handle(self, request)
