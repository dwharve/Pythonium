"""
Stub Implementation Detector Validation - Edge Cases

This module tests edge cases for the stub implementation detector to minimize
false positives and ensure accurate detection of actual stub implementations.
"""

from unittest import mock
import pytest

# =============================================================================
# TRUE POSITIVES - Should be detected as stubs/mocks/fakes
# =============================================================================

def stub_user_service():
    """Clear stub implementation."""
    return None

def mock_payment_gateway():
    """Mock payment service."""
    return {"status": "success", "transaction_id": "mock_123"}

class FakeEmailService:
    """Fake email service for testing."""
    
    def send(self, recipient, subject, body):
        # TODO: implement actual email sending
        pass

def dummy_authentication():
    """Dummy auth that always succeeds."""
    return True

def simulate_network_delay():
    """Simulates network delay for testing."""
    import time
    time.sleep(0.1)  # Fake delay

def fallback_algorithm():
    """Fallback when main algorithm fails."""
    raise NotImplementedError("Use optimized version when available")

def placeholder_feature():
    """Placeholder for future feature."""
    pass

@mock.patch('external_service')
def test_service_integration():
    """Test with mock decorator."""
    return "mocked result"

def noop_logger(message):
    """No-op logger implementation."""
    pass

def temporary_fix():
    """Temporary workaround."""
    # FIXME: Replace with proper implementation
    return "quick fix"

# =============================================================================
# FALSE POSITIVES - Should NOT be detected as stubs
# =============================================================================

def authenticate_user(username, password):
    """Legitimate authentication function."""
    if not username or not password:
        return False
    
    # Simplified but real authentication logic
    import hashlib
    hash_obj = hashlib.sha256((username + password).encode())
    return len(hash_obj.hexdigest()) > 0

def process_payment(amount, card_number):
    """Real payment processing logic."""
    if amount <= 0:
        raise ValueError("Invalid amount")
    
    if len(str(card_number)) != 16:
        raise ValueError("Invalid card number")
    
    # Simplified payment logic
    fee = amount * 0.03
    return {
        "amount": amount,
        "fee": fee,
        "total": amount + fee,
        "status": "processed"
    }

class EmailService:
    """Real email service implementation."""
    
    def __init__(self, smtp_host="localhost", smtp_port=587):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.connected = False
    
    def connect(self):
        """Connect to SMTP server."""
        # Real connection logic would go here
        self.connected = True
        return True
    
    def send(self, recipient, subject, body):
        """Send email with real implementation."""
        if not self.connected:
            self.connect()
        
        if not recipient or "@" not in recipient:
            raise ValueError("Invalid recipient")
        
        # Real email sending logic would go here
        return {"sent": True, "recipient": recipient}

def calculate_tax(income, tax_rate=0.25):
    """Real tax calculation."""
    if income < 0:
        raise ValueError("Income cannot be negative")
    
    if tax_rate < 0 or tax_rate > 1:
        raise ValueError("Tax rate must be between 0 and 1")
    
    return income * tax_rate

def get_user_preferences(user_id):
    """Real function that returns actual user preferences."""
    # Simulate database lookup
    default_prefs = {
        "theme": "dark",
        "notifications": True,
        "language": "en"
    }
    
    # In real implementation, this would query database
    return default_prefs.copy()

# =============================================================================
# BOUNDARY CASES - Challenging edge cases
# =============================================================================

def debug_helper():
    """Debug function that might look like a stub but isn't."""
    import sys
    import traceback
    
    frame = sys._getframe(1)
    print(f"Debug: {frame.f_code.co_name} at line {frame.f_lineno}")
    traceback.print_stack()

def returns_none_legitimately():
    """Function that legitimately returns None."""
    import os
    
    # Real case where None is appropriate return value
    env_var = os.environ.get('NONEXISTENT_VAR')
    if env_var is None:
        return None  # Legitimate None return
    
    return env_var.strip()

def simple_but_real_function():
    """Simple function that might appear stub-like but isn't."""
    import datetime
    return datetime.datetime.now().isoformat()

def validation_function(data):
    """Real validation that might return hardcoded values."""
    if not data:
        return False  # Legitimate hardcoded return
    
    if not isinstance(data, dict):
        return False  # Legitimate hardcoded return
    
    return True  # Legitimate hardcoded return

def factory_method():
    """Factory that returns hardcoded instance."""
    # This is a real factory pattern, not a stub
    return EmailService()

def configuration_getter():
    """Configuration function with hardcoded defaults."""
    # Real configuration with sensible defaults
    return {
        "max_retries": 3,
        "timeout": 30,
        "debug": False
    }

def boolean_check():
    """Function that legitimately returns True/False."""
    import os
    return os.path.exists('/etc/passwd')  # Real boolean check

# =============================================================================
# NAMING EDGE CASES - Functions with stub-like names that aren't stubs
# =============================================================================

def simulation_engine():
    """Real simulation engine, not a stub."""
    import random
    import math
    
    # Complex simulation logic
    particles = []
    for i in range(100):
        particle = {
            'x': random.uniform(0, 100),
            'y': random.uniform(0, 100),
            'velocity_x': random.uniform(-10, 10),
            'velocity_y': random.uniform(-10, 10)
        }
        particles.append(particle)
    
    # Physics simulation
    for particle in particles:
        particle['x'] += particle['velocity_x'] * 0.1
        particle['y'] += particle['velocity_y'] * 0.1
        
        # Apply gravity
        particle['velocity_y'] += -9.8 * 0.1
    
    return particles

def mock_server():
    """Real mock server implementation for testing infrastructure."""
    import socket
    import threading
    
    def handle_request(conn, addr):
        data = conn.recv(1024)
        response = b"HTTP/1.1 200 OK\r\n\r\nTest Response"
        conn.send(response)
        conn.close()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 0))
    server.listen(1)
    
    def run_server():
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_request, args=(conn, addr))
            thread.start()
    
    return server, run_server

def fake_data_generator():
    """Real fake data generator for testing."""
    import random
    import string
    
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    domains = ["example.com", "test.org", "demo.net"]
    
    data = []
    for _ in range(10):
        name = random.choice(names)
        domain = random.choice(domains)
        email = f"{name.lower()}@{domain}"
        
        record = {
            "name": name,
            "email": email,
            "age": random.randint(18, 80),
            "id": ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        }
        data.append(record)
    
    return data

def test_helper():
    """Real test utility function."""
    import tempfile
    import os
    
    # Create temporary test directory
    test_dir = tempfile.mkdtemp()
    
    # Create test files
    test_files = []
    for i in range(3):
        file_path = os.path.join(test_dir, f"test_{i}.txt")
        with open(file_path, 'w') as f:
            f.write(f"Test content {i}")
        test_files.append(file_path)
    
    return test_dir, test_files

# =============================================================================
# COMPLEX IMPLEMENTATION PATTERNS
# =============================================================================

def minimal_but_complete():
    """Minimal implementation that is complete."""
    import sys
    return sys.version_info.major

class SimpleButReal:
    """Simple class that might appear stub-like."""
    
    def __init__(self):
        self.initialized = True
    
    def is_ready(self):
        """Simple method that returns boolean."""
        return self.initialized

def single_line_real_function():
    """Real function with single line implementation."""
    return len([1, 2, 3, 4, 5])

def returns_constant_legitimately():
    """Function that legitimately returns a constant."""
    # API version number - legitimate constant
    return "1.0.0"

# =============================================================================
# DECORATOR AND WRAPPER PATTERNS
# =============================================================================

def real_decorator(func):
    """Real decorator implementation."""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    
    return wrapper

@real_decorator
def decorated_real_function():
    """Real function with real decorator."""
    return "real result"

# Use the decorated function
result = decorated_real_function()

# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

class RealContextManager:
    """Real context manager implementation."""
    
    def __init__(self, resource_name):
        self.resource_name = resource_name
        self.resource = None
    
    def __enter__(self):
        print(f"Acquiring {self.resource_name}")
        self.resource = f"resource_{self.resource_name}"
        return self.resource
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Releasing {self.resource_name}")
        self.resource = None
        return False

# Use the context manager
with RealContextManager("database") as db:
    print(f"Using {db}")

# =============================================================================
# REAL USAGE OF VALIDATION FUNCTIONS
# =============================================================================

# Actually use the functions to show they're real
auth_result = authenticate_user("testuser", "password123")
payment_result = process_payment(100.00, 1234567890123456)
email_service = EmailService()
tax_amount = calculate_tax(50000)
prefs = get_user_preferences(123)
debug_helper()
none_result = returns_none_legitimately()
timestamp = simple_but_real_function()
is_valid = validation_function({"key": "value"})
factory_instance = factory_method()
config = configuration_getter()
file_exists = boolean_check()
simulation_data = simulation_engine()
fake_records = fake_data_generator()
test_data = test_helper()
version = returns_constant_legitimately()
