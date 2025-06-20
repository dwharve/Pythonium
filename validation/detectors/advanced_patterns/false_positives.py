"""
False positive cases for advanced patterns detector.
These should NOT be flagged as overly complex advanced patterns.
"""

# Case 1: Simple, clear algorithms
def binary_search(arr, target):
    """Simple binary search - clear and efficient"""
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

def quicksort(arr):
    """Simple quicksort implementation"""
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quicksort(left) + middle + quicksort(right)

# Case 2: Standard design patterns (not overly complex)
class Observer:
    """Simple observer pattern"""
    def update(self, subject):
        raise NotImplementedError()

class Subject:
    """Simple subject in observer pattern"""
    def __init__(self):
        self._observers = []
    
    def attach(self, observer):
        self._observers.append(observer)
    
    def detach(self, observer):
        self._observers.remove(observer)
    
    def notify(self):
        for observer in self._observers:
            observer.update(self)

class ConcreteObserver(Observer):
    """Concrete observer implementation"""
    def __init__(self, name):
        self.name = name
    
    def update(self, subject):
        print(f"Observer {self.name} notified")

# Case 3: Simple inheritance hierarchy
class Animal:
    """Base animal class"""
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        raise NotImplementedError()

class Dog(Animal):
    """Dog implementation"""
    def speak(self):
        return f"{self.name} says Woof!"

class Cat(Animal):
    """Cat implementation"""
    def speak(self):
        return f"{self.name} says Meow!"

# Case 4: Basic context manager
class FileManager:
    """Simple file context manager"""
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.file = None
    
    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

# Case 5: Simple decorator
def timer_decorator(func):
    """Simple timing decorator"""
    import time
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    
    return wrapper

@timer_decorator
def example_function():
    """Example function with decorator"""
    import time
    time.sleep(0.1)
    return "Done"

# Case 6: Basic generator
def fibonacci_generator(n):
    """Simple fibonacci generator"""
    a, b = 0, 1
    count = 0
    
    while count < n:
        yield a
        a, b = b, a + b
        count += 1

def range_with_step(start, end, step):
    """Simple range generator with step"""
    current = start
    while current < end:
        yield current
        current += step

# Case 7: Simple factory pattern
class ShapeFactory:
    """Simple shape factory"""
    
    @staticmethod
    def create_shape(shape_type, *args):
        if shape_type == "circle":
            return Circle(*args)
        elif shape_type == "square":
            return Square(*args)
        elif shape_type == "rectangle":
            return Rectangle(*args)
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")

class Circle:
    def __init__(self, radius):
        self.radius = radius
    
    def area(self):
        return 3.14159 * self.radius ** 2

class Square:
    def __init__(self, side):
        self.side = side
    
    def area(self):
        return self.side ** 2

class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def area(self):
        return self.width * self.height

# Case 8: Basic async function
import asyncio

async def simple_async_function():
    """Simple async function"""
    await asyncio.sleep(0.1)
    return "Async result"

async def fetch_data(url):
    """Simple async data fetching simulation"""
    await asyncio.sleep(0.5)  # Simulate network delay
    return f"Data from {url}"

async def process_urls(urls):
    """Simple async processing of multiple URLs"""
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

# Case 9: Simple data processing
def process_csv_data(csv_content):
    """Simple CSV data processing"""
    lines = csv_content.strip().split('\n')
    headers = lines[0].split(',')
    
    data = []
    for line in lines[1:]:
        values = line.split(',')
        row = dict(zip(headers, values))
        data.append(row)
    
    return data

def filter_and_sort(data, filter_func, sort_key):
    """Simple filter and sort operation"""
    filtered = [item for item in data if filter_func(item)]
    sorted_data = sorted(filtered, key=sort_key)
    return sorted_data

# Case 10: Basic validation
def validate_email(email):
    """Simple email validation"""
    if not email or not isinstance(email, str):
        return False
    
    if '@' not in email:
        return False
    
    parts = email.split('@')
    if len(parts) != 2:
        return False
    
    username, domain = parts
    if not username or not domain:
        return False
    
    if '.' not in domain:
        return False
    
    return True

def validate_password(password):
    """Simple password validation"""
    if not password or len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit

# Case 11: Simple caching
class SimpleCache:
    """Simple in-memory cache"""
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size:
            # Remove oldest item (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = value
    
    def clear(self):
        self.cache.clear()

# Case 12: Simple state machine
class LightSwitch:
    """Simple state machine for a light switch"""
    def __init__(self):
        self.state = "off"
    
    def toggle(self):
        if self.state == "off":
            self.state = "on"
        else:
            self.state = "off"
    
    def is_on(self):
        return self.state == "on"

class TrafficLight:
    """Simple traffic light state machine"""
    def __init__(self):
        self.state = "red"
        self.transitions = {
            "red": "green",
            "green": "yellow", 
            "yellow": "red"
        }
    
    def next_state(self):
        self.state = self.transitions[self.state]
        return self.state

# Case 13: Simple builder pattern
class QueryBuilder:
    """Simple SQL query builder"""
    def __init__(self):
        self.query_parts = {
            'select': [],
            'from': None,
            'where': [],
            'order_by': []
        }
    
    def select(self, *columns):
        self.query_parts['select'].extend(columns)
        return self
    
    def from_table(self, table):
        self.query_parts['from'] = table
        return self
    
    def where(self, condition):
        self.query_parts['where'].append(condition)
        return self
    
    def order_by(self, column):
        self.query_parts['order_by'].append(column)
        return self
    
    def build(self):
        query = f"SELECT {', '.join(self.query_parts['select'])}"
        
        if self.query_parts['from']:
            query += f" FROM {self.query_parts['from']}"
        
        if self.query_parts['where']:
            query += f" WHERE {' AND '.join(self.query_parts['where'])}"
        
        if self.query_parts['order_by']:
            query += f" ORDER BY {', '.join(self.query_parts['order_by'])}"
        
        return query

# Case 14: Simple error handling
def safe_divide(a, b):
    """Simple division with error handling"""
    try:
        return a / b
    except ZeroDivisionError:
        return None
    except TypeError:
        return None

def safe_file_read(filename):
    """Simple file reading with error handling"""
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except PermissionError:
        return None

# Case 15: Simple utility functions
def chunk_list(lst, chunk_size):
    """Simple list chunking"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def flatten_list(nested_list):
    """Simple list flattening"""
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result

def count_words(text):
    """Simple word counting"""
    words = text.lower().split()
    word_count = {}
    
    for word in words:
        # Remove basic punctuation
        word = word.strip('.,!?;:"')
        if word:
            word_count[word] = word_count.get(word, 0) + 1
    
    return word_count

# Case 16: Simple configuration management
class Config:
    """Simple configuration class"""
    def __init__(self, config_dict=None):
        self.config = config_dict or {}
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
    
    def load_from_file(self, filename):
        try:
            import json
            with open(filename, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = {}
    
    def save_to_file(self, filename):
        import json
        with open(filename, 'w') as f:
            json.dump(self.config, f, indent=2)

# Case 17: Simple logging
class SimpleLogger:
    """Simple logging class"""
    def __init__(self, name, level="INFO"):
        self.name = name
        self.level = level
        self.levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
    
    def _should_log(self, level):
        return self.levels.get(level, 1) >= self.levels.get(self.level, 1)
    
    def debug(self, message):
        if self._should_log("DEBUG"):
            print(f"[DEBUG] {self.name}: {message}")
    
    def info(self, message):
        if self._should_log("INFO"):
            print(f"[INFO] {self.name}: {message}")
    
    def warning(self, message):
        if self._should_log("WARNING"):
            print(f"[WARNING] {self.name}: {message}")
    
    def error(self, message):
        if self._should_log("ERROR"):
            print(f"[ERROR] {self.name}: {message}")
