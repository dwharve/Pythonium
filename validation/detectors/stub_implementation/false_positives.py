"""
Stub Implementation Detector Validation - False Positive Scenarios

This module contains patterns that might trigger false positives in the
stub implementation detector. These should help tune the algorithm to
be more precise.
"""

# =============================================================================
# LEGITIMATE MINIMAL IMPLEMENTATIONS
# =============================================================================

def is_enabled():
    """Feature flag check - legitimately minimal."""
    import os
    return os.environ.get('FEATURE_ENABLED', 'false').lower() == 'true'

def get_current_timestamp():
    """Simple timestamp function."""
    import time
    return int(time.time())

def generate_uuid():
    """UUID generator - minimal but complete."""
    import uuid
    return str(uuid.uuid4())

def get_random_number():
    """Random number generator."""
    import random
    return random.randint(1, 100)

def is_debug_mode():
    """Debug mode check."""
    import sys
    return hasattr(sys, '_getframe')

# =============================================================================
# LEGITIMATE PASS IMPLEMENTATIONS
# =============================================================================

def abstract_method(self):
    """Abstract method that should be overridden."""
    pass  # Intentionally empty - not a stub

class AbstractBase:
    """Abstract base class."""
    
    def concrete_method(self):
        """Concrete implementation."""
        return "concrete"
    
    def abstract_method(self):
        """Abstract method to be overridden."""
        pass  # Legitimate abstract method

class ConcreteImplementation(AbstractBase):
    """Concrete implementation of abstract class."""
    
    def abstract_method(self):
        """Concrete implementation of abstract method."""
        return "implemented"

# =============================================================================
# LEGITIMATE NONE RETURNS
# =============================================================================

def find_item(items, predicate):
    """Find first item matching predicate."""
    for item in items:
        if predicate(item):
            return item
    return None  # Legitimate None return when not found

def get_optional_config(key):
    """Get optional configuration value."""
    import os
    return os.environ.get(key)  # May legitimately return None

def parse_optional_int(value):
    """Parse integer with None fallback."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None  # Legitimate None return for invalid input

def safe_divide(a, b):
    """Safe division that returns None for division by zero."""
    if b == 0:
        return None  # Legitimate None return
    return a / b

# =============================================================================
# LEGITIMATE HARDCODED RETURNS
# =============================================================================

def get_api_version():
    """API version - legitimately hardcoded."""
    return "2.1.0"

def get_max_file_size():
    """Maximum file size constant."""
    return 10 * 1024 * 1024  # 10MB

def get_default_timeout():
    """Default timeout value."""
    return 30  # 30 seconds

def is_production():
    """Production environment check."""
    import os
    return os.environ.get('ENV') == 'production'

def get_supported_formats():
    """Supported file formats."""
    return ['json', 'xml', 'csv']  # Legitimate hardcoded list

def get_default_headers():
    """Default HTTP headers."""
    return {  # Legitimate hardcoded dict
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

# =============================================================================
# LEGITIMATE EMPTY CONTAINERS
# =============================================================================

def get_empty_list():
    """Function that legitimately returns empty list."""
    return []  # Valid for initializing collections

def get_empty_dict():
    """Function that legitimately returns empty dict."""
    return {}  # Valid for initializing mappings

def get_empty_set():
    """Function that legitimately returns empty set."""
    return set()  # Valid for initializing sets

def create_empty_config():
    """Create empty configuration object."""
    return {}  # Legitimate empty config

# =============================================================================
# LEGITIMATE BOOLEAN RETURNS
# =============================================================================

def always_true():
    """Function that legitimately always returns True."""
    return True  # E.g., for feature that's always enabled

def always_false():
    """Function that legitimately always returns False."""
    return False  # E.g., for deprecated feature

def is_supported():
    """Check if feature is supported."""
    return True  # Current platform always supports this

def is_legacy():
    """Check if running in legacy mode."""
    return False  # No longer support legacy mode

# =============================================================================
# LEGITIMATE SIMPLE IMPLEMENTATIONS
# =============================================================================

def negate(value):
    """Negate a boolean value."""
    return not value

def double(value):
    """Double a numeric value."""
    return value * 2

def to_string(value):
    """Convert value to string."""
    return str(value)

def get_length(collection):
    """Get length of collection."""
    return len(collection)

def is_empty(collection):
    """Check if collection is empty."""
    return len(collection) == 0

# =============================================================================
# LEGITIMATE TODO/COMMENT PATTERNS
# =============================================================================

def optimized_algorithm():
    """Function with optimization notes."""
    # TODO: Optimize this algorithm in future version
    # Current implementation is correct but could be faster
    data = list(range(1000))
    result = []
    for item in data:
        if item % 2 == 0:
            result.append(item * 2)
    return result

def documented_limitation():
    """Function with documented limitations."""
    # FIXME: This doesn't handle edge case X, but it's not needed for v1.0
    # Will be addressed in future version
    def process_data(data):
        if not data:
            return []
        return [item.upper() for item in data if isinstance(item, str)]
    
    return process_data

def future_enhancement():
    """Function with future enhancement notes."""
    # TODO: Add caching in v2.0
    # Current implementation is sufficient for current requirements
    import hashlib
    
    def compute_hash(data):
        return hashlib.md5(str(data).encode()).hexdigest()
    
    return compute_hash

# =============================================================================
# LEGITIMATE DECORATOR USAGE
# =============================================================================

def timing_decorator(func):
    """Real timing decorator."""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    
    return wrapper

@timing_decorator
def heavy_computation():
    """Function with legitimate decorator."""
    import time
    time.sleep(0.01)  # Simulate work
    return sum(range(1000))

# =============================================================================
# LEGITIMATE FACTORY PATTERNS
# =============================================================================

def create_logger(name="default"):
    """Logger factory."""
    import logging
    return logging.getLogger(name)

def create_connection(host="localhost", port=5432):
    """Connection factory."""
    return f"connection://{host}:{port}"

def create_parser():
    """Parser factory."""
    import argparse
    return argparse.ArgumentParser()

# =============================================================================
# LEGITIMATE NAMING PATTERNS THAT LOOK LIKE STUBS
# =============================================================================

def test_connection():
    """Real connection testing function."""
    import socket
    try:
        socket.create_connection(('8.8.8.8', 53), timeout=3)
        return True
    except OSError:
        return False

def mock_request(url, method='GET'):
    """Real HTTP request mocker for testing framework."""
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url)
    return {
        'url': url,
        'method': method,
        'host': parsed.netloc,
        'path': parsed.path,
        'timestamp': 'mocked'
    }

def dummy_data_cleanup():
    """Real cleanup function for test data."""
    import tempfile
    import os
    import shutil
    
    temp_dir = tempfile.gettempdir()
    for item in os.listdir(temp_dir):
        if item.startswith('test_') and item.endswith('.tmp'):
            item_path = os.path.join(temp_dir, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

def simulate_load():
    """Real load simulation for performance testing."""
    import concurrent.futures
    import time
    
    def worker_task(task_id):
        time.sleep(0.01)  # Simulate work
        return f"Task {task_id} completed"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_task, i) for i in range(100)]
        results = [future.result() for future in futures]
    
    return len(results)

def fake_server_start():
    """Real test server starter."""
    import http.server
    import socketserver
    import threading
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Test server response')
    
    server = socketserver.TCPServer(('localhost', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    return server

# =============================================================================
# USAGE OF ALL FUNCTIONS TO DEMONSTRATE THEY'RE REAL
# =============================================================================

# Use all the functions to show they're legitimate
enabled = is_enabled()
timestamp = get_current_timestamp()
uuid_val = generate_uuid()
random_num = get_random_number()
debug = is_debug_mode()

# Abstract class usage
concrete = ConcreteImplementation()
result = concrete.abstract_method()

# Search functions
items = [1, 2, 3, 4, 5]
found = find_item(items, lambda x: x > 3)
config_val = get_optional_config('NON_EXISTENT')
parsed = parse_optional_int("not a number")
division = safe_divide(10, 0)

# Constants
version = get_api_version()
max_size = get_max_file_size()
timeout = get_default_timeout()
prod = is_production()
formats = get_supported_formats()
headers = get_default_headers()

# Empty containers
empty_list = get_empty_list()
empty_dict = get_empty_dict()
empty_set = get_empty_set()
empty_config = create_empty_config()

# Boolean functions
true_val = always_true()
false_val = always_false()
supported = is_supported()
legacy = is_legacy()

# Simple operations
negated = negate(True)
doubled = double(5)
stringified = to_string(42)
length = get_length([1, 2, 3])
is_empty_result = is_empty([])

# Complex functions with comments
optimized = optimized_algorithm()
documented = documented_limitation()
enhanced = future_enhancement()

# Decorator usage
computation_result = heavy_computation()

# Factories
logger = create_logger("test")
connection = create_connection()
parser = create_parser()

# "Fake" named functions that are real
conn_test = test_connection()
mock_resp = mock_request("http://example.com")
dummy_data_cleanup()
load_result = simulate_load()
server = fake_server_start()
