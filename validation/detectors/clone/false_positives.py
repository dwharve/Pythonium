"""
Clone Detector Validation - False Positives

This module contains code patterns that might appear similar but should NOT
be detected as clones. These help tune the detector to avoid false positives.
"""

# =============================================================================
# SIMILAR STRUCTURE BUT DIFFERENT SEMANTICS
# =============================================================================

def encrypt_password(password):
    """Encrypt a password using secure hashing."""
    import hashlib
    import secrets
    
    # Generate a random salt
    salt = secrets.token_hex(16)
    
    # Hash the password with salt
    pwd_hash = hashlib.pbkdf2_hmac('sha256', 
                                   password.encode('utf-8'), 
                                   salt.encode('utf-8'), 
                                   100000)
    
    return salt + pwd_hash.hex()

def verify_password(password, stored_hash):
    """Verify a password against stored hash."""
    import hashlib
    
    # Extract salt from stored hash
    salt = stored_hash[:32]
    stored_password_hash = stored_hash[32:]
    
    # Hash the provided password with the same salt
    pwd_hash = hashlib.pbkdf2_hmac('sha256',
                                   password.encode('utf-8'),
                                   salt.encode('utf-8'),
                                   100000)
    
    return pwd_hash.hex() == stored_password_hash

# =============================================================================
# SIMILAR PATTERNS BUT DIFFERENT DOMAINS
# =============================================================================

def calculate_tax(income, tax_rate):
    """Calculate income tax."""
    if income <= 0:
        return 0
    
    if tax_rate < 0 or tax_rate > 1:
        raise ValueError("Tax rate must be between 0 and 1")
    
    # Progressive tax calculation
    brackets = [
        (10000, 0.10),
        (40000, 0.20),
        (80000, 0.30),
        (float('inf'), 0.40)
    ]
    
    total_tax = 0
    remaining_income = income
    
    for bracket_limit, rate in brackets:
        if remaining_income <= 0:
            break
        
        taxable_amount = min(remaining_income, bracket_limit)
        total_tax += taxable_amount * rate
        remaining_income -= taxable_amount
    
    return total_tax

def calculate_shipping(weight, distance):
    """Calculate shipping cost."""
    if weight <= 0 or distance <= 0:
        return 0
    
    if weight > 50:  # Max weight limit
        raise ValueError("Weight exceeds maximum limit")
    
    # Shipping cost calculation
    weight_brackets = [
        (1, 5.00),
        (5, 3.00),
        (10, 2.00),
        (float('inf'), 1.50)
    ]
    
    base_cost = 0
    remaining_weight = weight
    
    for weight_limit, cost_per_unit in weight_brackets:
        if remaining_weight <= 0:
            break
        
        applicable_weight = min(remaining_weight, weight_limit)
        base_cost += applicable_weight * cost_per_unit
        remaining_weight -= applicable_weight
    
    # Distance multiplier
    distance_multiplier = 1 + (distance / 1000) * 0.1
    
    return base_cost * distance_multiplier

# =============================================================================
# TEMPLATE PATTERNS WITH DIFFERENT IMPLEMENTATIONS
# =============================================================================

def process_json_data(data):
    """Process JSON data with specific validation."""
    import json
    
    try:
        parsed = json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON data")
    
    if not isinstance(parsed, dict):
        raise ValueError("JSON must be an object")
    
    # JSON-specific validation
    required_fields = ['id', 'type', 'timestamp']
    for field in required_fields:
        if field not in parsed:
            raise ValueError(f"Missing required field: {field}")
    
    # JSON-specific transformations
    if 'timestamp' in parsed:
        import datetime
        try:
            datetime.datetime.fromisoformat(parsed['timestamp'])
        except ValueError:
            raise ValueError("Invalid timestamp format")
    
    return parsed

def process_xml_data(data):
    """Process XML data with specific validation."""
    import xml.etree.ElementTree as ET
    
    try:
        root = ET.fromstring(data) if isinstance(data, str) else data
    except ET.ParseError:
        raise ValueError("Invalid XML data")
    
    if root.tag != 'record':
        raise ValueError("XML root must be 'record'")
    
    # XML-specific validation
    required_attrs = ['id', 'type', 'timestamp']
    for attr in required_attrs:
        if attr not in root.attrib:
            raise ValueError(f"Missing required attribute: {attr}")
    
    # XML-specific transformations
    timestamp = root.attrib.get('timestamp')
    if timestamp:
        import datetime
        try:
            datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ValueError("Invalid timestamp format")
    
    return root

# =============================================================================
# ALGORITHMS WITH DIFFERENT COMPLEXITIES
# =============================================================================

def linear_search(arr, target):
    """Linear search algorithm."""
    for i, item in enumerate(arr):
        if item == target:
            return i
    return -1

def binary_search(arr, target):
    """Binary search algorithm (different approach)."""
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

# =============================================================================
# DIFFERENT DATA STRUCTURES FOR SAME PURPOSE
# =============================================================================

def implement_stack_with_list():
    """Stack implementation using list."""
    class ListStack:
        def __init__(self):
            self._items = []
        
        def push(self, item):
            self._items.append(item)
        
        def pop(self):
            if not self._items:
                raise IndexError("Stack is empty")
            return self._items.pop()
        
        def peek(self):
            if not self._items:
                raise IndexError("Stack is empty")
            return self._items[-1]
        
        def is_empty(self):
            return len(self._items) == 0
        
        def size(self):
            return len(self._items)
    
    return ListStack()

def implement_stack_with_linked_list():
    """Stack implementation using linked list."""
    class Node:
        def __init__(self, data):
            self.data = data
            self.next = None
    
    class LinkedStack:
        def __init__(self):
            self._top = None
            self._size = 0
        
        def push(self, item):
            new_node = Node(item)
            new_node.next = self._top
            self._top = new_node
            self._size += 1
        
        def pop(self):
            if self._top is None:
                raise IndexError("Stack is empty")
            data = self._top.data
            self._top = self._top.next
            self._size -= 1
            return data
        
        def peek(self):
            if self._top is None:
                raise IndexError("Stack is empty")
            return self._top.data
        
        def is_empty(self):
            return self._top is None
        
        def size(self):
            return self._size
    
    return LinkedStack()

# =============================================================================
# DIFFERENT APPROACHES TO SAME PROBLEM
# =============================================================================

def fibonacci_recursive(n):
    """Fibonacci using recursion."""
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

def fibonacci_memoized(n, memo={}):
    """Fibonacci using memoization."""
    if n in memo:
        return memo[n]
    
    if n <= 1:
        result = n
    else:
        result = fibonacci_memoized(n - 1, memo) + fibonacci_memoized(n - 2, memo)
    
    memo[n] = result
    return result

def fibonacci_iterative(n):
    """Fibonacci using iteration."""
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b

# =============================================================================
# DOMAIN-SPECIFIC IMPLEMENTATIONS
# =============================================================================

def validate_email(email):
    """Email validation with email-specific rules."""
    import re
    
    if not email or not isinstance(email, str):
        return False
    
    # Email-specific validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False
    
    # Check for common email providers
    valid_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    domain = email.split('@')[1].lower()
    
    # Email-specific length checks
    local_part, domain_part = email.split('@')
    if len(local_part) > 64 or len(domain_part) > 253:
        return False
    
    return True

def validate_phone(phone):
    """Phone validation with phone-specific rules."""
    import re
    
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Phone-specific validation
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False
    
    # Check for valid country codes
    valid_country_codes = ['1', '44', '49', '33', '39', '34', '81', '86']
    
    # US phone number validation
    if len(digits_only) == 10:
        return digits_only[0] != '0' and digits_only[0] != '1'
    
    # International phone validation
    elif len(digits_only) > 10:
        for code in valid_country_codes:
            if digits_only.startswith(code):
                return True
    
    return False

# =============================================================================
# CONFIGURATION WITH DIFFERENT PURPOSES
# =============================================================================

def setup_development_environment():
    """Development environment configuration."""
    import os
    
    config = {
        'debug': True,
        'testing': True,
        'log_level': 'DEBUG',
        'database_url': 'sqlite:///dev.db',
        'cache_backend': 'dummy',
        'secret_key': 'dev-secret-key',
        'allowed_hosts': ['localhost', '127.0.0.1'],
        'cors_enabled': True,
        'csrf_protection': False,
        'session_timeout': 3600,
        'max_upload_size': 10 * 1024 * 1024  # 10MB
    }
    
    # Development-specific settings
    config['hot_reload'] = True
    config['profiling'] = True
    config['mock_external_apis'] = True
    
    return config

def setup_production_environment():
    """Production environment configuration."""
    import os
    
    config = {
        'debug': False,
        'testing': False,
        'log_level': 'WARNING',
        'database_url': os.environ.get('DATABASE_URL'),
        'cache_backend': 'redis',
        'secret_key': os.environ.get('SECRET_KEY'),
        'allowed_hosts': os.environ.get('ALLOWED_HOSTS', '').split(','),
        'cors_enabled': False,
        'csrf_protection': True,
        'session_timeout': 1800,
        'max_upload_size': 5 * 1024 * 1024  # 5MB
    }
    
    # Production-specific settings
    config['ssl_required'] = True
    config['rate_limiting'] = True
    config['monitoring_enabled'] = True
    
    return config

# =============================================================================
# PROTOCOLS WITH DIFFERENT IMPLEMENTATIONS
# =============================================================================

def http_client_get(url, headers=None):
    """HTTP GET client implementation."""
    import urllib.request
    import urllib.error
    
    try:
        request = urllib.request.Request(url)
        
        if headers:
            for key, value in headers.items():
                request.add_header(key, value)
        
        with urllib.request.urlopen(request, timeout=30) as response:
            return {
                'status_code': response.getcode(),
                'headers': dict(response.headers),
                'body': response.read().decode('utf-8')
            }
    
    except urllib.error.HTTPError as e:
        return {
            'status_code': e.code,
            'headers': {},
            'body': None,
            'error': str(e)
        }

def websocket_client_connect(url, protocols=None):
    """WebSocket client implementation."""
    import socket
    import base64
    import hashlib
    
    # WebSocket handshake
    key = base64.b64encode(b'random-key-16-bytes').decode()
    
    handshake = f"""GET {url} HTTP/1.1\r
Host: localhost\r
Upgrade: websocket\r
Connection: Upgrade\r
Sec-WebSocket-Key: {key}\r
Sec-WebSocket-Version: 13\r
\r
"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sock.connect(('localhost', 8080))
        sock.send(handshake.encode())
        
        response = sock.recv(1024).decode()
        
        if '101 Switching Protocols' in response:
            return {
                'connected': True,
                'socket': sock,
                'protocols': protocols or []
            }
        else:
            return {
                'connected': False,
                'socket': None,
                'error': 'Handshake failed'
            }
    
    except Exception as e:
        return {
            'connected': False,
            'socket': None,
            'error': str(e)
        }
