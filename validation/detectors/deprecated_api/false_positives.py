"""
False positive cases for deprecated API detector.
These should NOT be flagged as using deprecated APIs.
"""

import warnings

# Case 1: Modern API usage
def modern_function(x, y):
    """Modern function without deprecation warnings"""
    return x + y

def current_calculation(data):
    """Current, non-deprecated calculation method"""
    if not data:
        return 0
    return sum(data) / len(data)

def up_to_date_method(value):
    """Current method without deprecation"""
    return value * 2

# Case 2: Current class with modern methods
class ModernClass:
    """Class with current, non-deprecated methods"""
    
    def __init__(self):
        self.items = []
    
    def append(self, item):
        """Modern method for adding items"""
        self.items.append(item)
    
    def __len__(self):
        """Modern way to get size using len()"""
        return len(self.items)
    
    @property
    def size(self):
        """Modern property for size"""
        return len(self.items)

# Case 3: Using current APIs
def uses_current_apis():
    """Function that uses current, non-deprecated APIs"""
    # Using modern function
    result1 = modern_function(5, 3)
    
    # Using modern class
    modern = ModernClass()
    modern.append("test")
    size = len(modern)  # Modern way
    
    # Using modern calculation
    data = [1, 2, 3, 4, 5]
    avg = current_calculation(data)
    
    return result1, size, avg

# Case 4: Current imports and modules
import json  # Current, stable module
import pathlib  # Modern path handling
from collections import defaultdict  # Current collections

def modern_imports_usage():
    """Using current, non-deprecated imports"""
    # JSON handling - current
    data = {"key": "value"}
    json_str = json.dumps(data)
    parsed = json.loads(json_str)
    
    # Modern path handling
    path = pathlib.Path("example.txt")
    exists = path.exists()
    
    # Current collections usage
    dd = defaultdict(list)
    dd["key"].append("value")
    
    return parsed, exists, dict(dd)

# Case 5: Current standard library usage
import platform
import sys

def current_platform_usage():
    """Using current platform methods"""
    # Current platform methods
    system = platform.system()  # Current
    architecture = platform.architecture()  # Current
    python_version = platform.python_version()  # Current
    
    # Current sys usage
    version_info = sys.version_info  # Current
    path = sys.path  # Current
    
    return system, architecture, python_version, version_info

# Case 6: Modern string methods
def modern_string_methods():
    """Using modern string methods and formatting"""
    text = "Hello World"
    
    # Modern string formatting
    formatted1 = "Hello {}".format("World")  # Modern .format()
    formatted2 = f"Hello {'World'}"  # Modern f-strings
    
    # Current string methods
    upper_text = text.upper()  # Current
    split_text = text.split()  # Current
    joined_text = " ".join(["Hello", "World"])  # Current
    
    return formatted1, formatted2, upper_text, split_text, joined_text

# Case 7: Modern file operations
def modern_file_operations():
    """Using modern file operation patterns"""
    import os
    from pathlib import Path
    
    # Modern path operations
    path = Path("test.txt")
    exists = path.exists()
    
    # Modern file operations
    try:
        with open("test.txt", "r", encoding="utf-8") as f:  # Modern with encoding
            content = f.read()
    except FileNotFoundError:
        content = None
    
    # Modern directory operations
    current_dir = Path.cwd()  # Modern way
    
    return content, exists, str(current_dir)

# Case 8: Modern exception handling patterns
def modern_exception_patterns():
    """Using modern exception handling"""
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        # Modern exception handling
        error_msg = str(e)
        error_type = type(e).__name__
    except Exception as e:
        # Generic exception handling - modern pattern
        error_msg = f"Unexpected error: {e}"
        error_type = type(e).__name__
    else:
        error_msg = None
        error_type = None
    finally:
        # Cleanup - modern pattern
        pass
    
    return error_msg, error_type

# Case 9: Modern configuration patterns
class ModernConfig:
    """Configuration class using modern patterns"""
    
    def __init__(self, config_file=None):
        self.settings = {}
        if config_file:
            self.load_config(config_file)
    
    def load_config(self, config_file):
        """Modern configuration loading"""
        try:
            with open(config_file, 'r') as f:
                import json
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = self.get_default_settings()
    
    def get_default_settings(self):
        """Get default configuration"""
        return {"debug": False, "port": 8000}
    
    def get(self, key, default=None):
        """Modern getter with default"""
        return self.settings.get(key, default)
    
    def __getitem__(self, key):
        """Modern dictionary-like access"""
        return self.settings[key]

# Case 10: Modern utility functions
def modern_utilities():
    """Collection of modern utility functions"""
    
    def join_strings(items, separator=","):
        """Modern string joining"""
        return separator.join(str(item) for item in items)
    
    def filter_items(items, condition):
        """Modern filtering using list comprehension"""
        return [item for item in items if condition(item)]
    
    def map_items(items, transform):
        """Modern mapping using list comprehension"""
        return [transform(item) for item in items]
    
    # Usage of modern utilities
    items = ["a", "b", "c"]
    joined = join_strings(items, ",")
    
    numbers = [1, 2, 3, 4, 5]
    filtered = filter_items(numbers, lambda x: x > 3)
    mapped = map_items(numbers, lambda x: x * 2)
    
    return joined, filtered, mapped

# Case 11: Modern database patterns
class ModernDatabase:
    """Database class with modern methods"""
    
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.connection = None
    
    def execute_query(self, query, params=None):
        """Modern query execution method"""
        # Modern parameter binding and execution
        return f"Executed: {query} with {params}"
    
    def query_one(self, query, params=None):
        """Modern single row query"""
        result = self.execute_query(query, params)
        return {"id": 1, "name": "test"}
    
    def query_all(self, query, params=None):
        """Modern multiple row query"""
        result = self.execute_query(query, params)
        return [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
    
    def __enter__(self):
        """Modern context manager support"""
        # Setup connection
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Modern context manager cleanup"""
        # Cleanup connection
        pass

# Case 12: Modern async patterns
import asyncio

async def modern_async_function():
    """Function using modern async patterns"""
    
    # Modern async/await syntax
    await asyncio.sleep(0.1)
    
    # Modern async context manager
    async with async_context_manager():
        result = "async result"
    
    # Modern async comprehension
    async_results = [x async for x in async_generator()]
    
    return result, async_results

async def async_context_manager():
    """Modern async context manager"""
    class AsyncContextManager:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return AsyncContextManager()

async def async_generator():
    """Modern async generator"""
    for i in range(3):
        await asyncio.sleep(0.01)
        yield i

# Case 13: Modern testing patterns
class ModernTestUtils:
    """Testing utilities with modern methods"""
    
    def assert_equal(self, a, b, msg=None):
        """Modern assertion method"""
        if a != b:
            error_msg = msg or f"{a} != {b}"
            raise AssertionError(error_msg)
    
    def assert_raises(self, exception_class, callable_obj, *args, **kwargs):
        """Modern exception assertion"""
        try:
            callable_obj(*args, **kwargs)
        except exception_class:
            return  # Expected exception
        except Exception as e:
            raise AssertionError(f"Expected {exception_class}, got {type(e)}")
        else:
            raise AssertionError(f"Expected {exception_class}, but no exception was raised")
    
    def setUp(self):
        """Modern test setup method"""
        # Modern setup pattern
        pass
    
    def tearDown(self):
        """Modern test teardown method"""
        # Modern teardown pattern
        pass

# Case 14: Modern decorators and context managers
from contextlib import contextmanager
from functools import wraps

def modern_decorator(func):
    """Modern decorator pattern"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Modern decorator implementation
        result = func(*args, **kwargs)
        return result
    return wrapper

@contextmanager
def modern_context_manager():
    """Modern context manager using contextlib"""
    try:
        yield "resource"
    finally:
        # Cleanup
        pass

@modern_decorator
def decorated_function():
    """Function using modern decorator"""
    return "decorated result"

def use_modern_context():
    """Using modern context manager"""
    with modern_context_manager() as resource:
        return f"Used {resource}"

# Case 15: Modern data structures and algorithms
from collections import namedtuple, Counter
from dataclasses import dataclass
from typing import List, Dict, Optional

# Modern named tuple
Point = namedtuple('Point', ['x', 'y'])

# Modern dataclass
@dataclass
class ModernDataClass:
    name: str
    value: int
    tags: List[str] = None
    metadata: Optional[Dict[str, str]] = None

def modern_data_processing():
    """Modern data processing with current structures"""
    # Modern collections usage
    counter = Counter(['a', 'b', 'a', 'c', 'b', 'a'])
    most_common = counter.most_common(2)
    
    # Modern namedtuple usage
    point = Point(10, 20)
    
    # Modern dataclass usage
    data_obj = ModernDataClass(
        name="example",
        value=42,
        tags=["tag1", "tag2"]
    )
    
    return most_common, point, data_obj
