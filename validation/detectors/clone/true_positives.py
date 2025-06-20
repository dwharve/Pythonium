"""
Clone Detector Validation - True Positives

This module contains code patterns that should be detected as clones
to validate the clone detector's ability to find duplicate code.
"""

# =============================================================================
# EXACT CLONES - Identical code blocks
# =============================================================================

def process_user_data_v1(user_data):
    """Process user data - version 1."""
    if not user_data:
        return None
    
    result = {}
    result['name'] = user_data.get('name', '').strip().title()
    result['email'] = user_data.get('email', '').strip().lower()
    result['age'] = int(user_data.get('age', 0))
    
    if result['age'] < 0:
        result['age'] = 0
    
    return result

def process_customer_data_v1(customer_data):
    """Process customer data - version 1 (EXACT CLONE)."""
    if not customer_data:
        return None
    
    result = {}
    result['name'] = customer_data.get('name', '').strip().title()
    result['email'] = customer_data.get('email', '').strip().lower()
    result['age'] = int(customer_data.get('age', 0))
    
    if result['age'] < 0:
        result['age'] = 0
    
    return result

# =============================================================================
# NEAR CLONES - Very similar code with minor differences
# =============================================================================

def validate_email_format(email):
    """Validate email format - version A."""
    if not email:
        return False
    
    if '@' not in email:
        return False
    
    parts = email.split('@')
    if len(parts) != 2:
        return False
    
    local, domain = parts
    if not local or not domain:
        return False
    
    return True

def validate_email_address(email_addr):
    """Validate email address - version B (NEAR CLONE)."""
    if not email_addr:
        return False
    
    if '@' not in email_addr:
        return False
    
    parts = email_addr.split('@')
    if len(parts) != 2:
        return False
    
    username, domain = parts  # Different variable names
    if not username or not domain:
        return False
    
    return True

# =============================================================================
# ALGORITHM CLONES - Same algorithm, different variable names
# =============================================================================

def calculate_fibonacci_iterative(n):
    """Calculate fibonacci number iteratively."""
    if n <= 1:
        return n
    
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    
    return b

def compute_fib_sequence(num):
    """Compute fibonacci sequence value (ALGORITHM CLONE)."""
    if num <= 1:
        return num
    
    prev, curr = 0, 1
    for j in range(2, num + 1):
        prev, curr = curr, prev + curr
    
    return curr

# =============================================================================
# STRUCTURAL CLONES - Same structure, different operations
# =============================================================================

def process_numbers_sum(numbers):
    """Process numbers by summing them."""
    if not numbers:
        return 0
    
    total = 0
    for num in numbers:
        if isinstance(num, (int, float)):
            total += num
    
    return total

def process_numbers_product(numbers):
    """Process numbers by multiplying them (STRUCTURAL CLONE)."""
    if not numbers:
        return 1  # Different default value
    
    total = 1  # Different initial value
    for num in numbers:
        if isinstance(num, (int, float)):
            total *= num  # Different operation
    
    return total

# =============================================================================
# CLASS METHOD CLONES
# =============================================================================

class UserManager:
    """User management class."""
    
    def create_user(self, name, email, age):
        """Create a new user."""
        if not name or not email:
            raise ValueError("Name and email are required")
        
        user_data = {
            'name': name.strip().title(),
            'email': email.strip().lower(),
            'age': int(age) if age else 0,
            'created_at': 'now',
            'active': True
        }
        
        return user_data
    
    def update_user(self, name, email, age):
        """Update existing user (METHOD CLONE)."""
        if not name or not email:
            raise ValueError("Name and email are required")
        
        user_data = {
            'name': name.strip().title(),
            'email': email.strip().lower(),
            'age': int(age) if age else 0,
            'updated_at': 'now',  # Slight difference
            'active': True
        }
        
        return user_data

class CustomerManager:
    """Customer management class."""
    
    def create_customer(self, name, email, age):
        """Create a new customer (CLASS CLONE)."""
        if not name or not email:
            raise ValueError("Name and email are required")
        
        customer_data = {  # Different variable name
            'name': name.strip().title(),
            'email': email.strip().lower(),
            'age': int(age) if age else 0,
            'created_at': 'now',
            'active': True
        }
        
        return customer_data

# =============================================================================
# LOOP PATTERN CLONES
# =============================================================================

def find_max_in_list(items):
    """Find maximum value in list."""
    if not items:
        return None
    
    max_val = items[0]
    for item in items[1:]:
        if item > max_val:
            max_val = item
    
    return max_val

def find_min_in_list(items):
    """Find minimum value in list (LOOP CLONE)."""
    if not items:
        return None
    
    min_val = items[0]
    for item in items[1:]:
        if item < min_val:  # Different comparison
            min_val = item
    
    return min_val

# =============================================================================
# ERROR HANDLING CLONES
# =============================================================================

def safe_file_read(filename):
    """Safely read file content."""
    try:
        with open(filename, 'r') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    except PermissionError:
        print(f"Permission denied for {filename}")
        return None
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None

def safe_file_write(filename, content):
    """Safely write file content (ERROR HANDLING CLONE)."""
    try:
        with open(filename, 'w') as f:
            f.write(content)
        return True
    except FileNotFoundError:
        print(f"File {filename} not found")
        return False
    except PermissionError:
        print(f"Permission denied for {filename}")
        return False
    except Exception as e:
        print(f"Error writing {filename}: {e}")
        return False

# =============================================================================
# VALIDATION CLONES
# =============================================================================

def validate_user_input(data):
    """Validate user input data."""
    errors = []
    
    if not data.get('name'):
        errors.append("Name is required")
    elif len(data['name']) < 2:
        errors.append("Name must be at least 2 characters")
    
    if not data.get('email'):
        errors.append("Email is required")
    elif '@' not in data['email']:
        errors.append("Invalid email format")
    
    if data.get('age') and data['age'] < 0:
        errors.append("Age cannot be negative")
    
    return errors

def validate_customer_input(data):
    """Validate customer input data (VALIDATION CLONE)."""
    errors = []
    
    if not data.get('name'):
        errors.append("Name is required")
    elif len(data['name']) < 2:
        errors.append("Name must be at least 2 characters")
    
    if not data.get('email'):
        errors.append("Email is required")
    elif '@' not in data['email']:
        errors.append("Invalid email format")
    
    if data.get('age') and data['age'] < 0:
        errors.append("Age cannot be negative")
    
    return errors

# =============================================================================
# CONFIGURATION CLONES
# =============================================================================

def setup_database_connection():
    """Setup database connection."""
    import os
    
    config = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 5432)),
        'username': os.environ.get('DB_USER', 'admin'),
        'password': os.environ.get('DB_PASS', 'secret'),
        'database': os.environ.get('DB_NAME', 'myapp'),
        'timeout': 30,
        'retry_count': 3
    }
    
    return config

def setup_cache_connection():
    """Setup cache connection (CONFIG CLONE)."""
    import os
    
    config = {
        'host': os.environ.get('CACHE_HOST', 'localhost'),
        'port': int(os.environ.get('CACHE_PORT', 6379)),
        'username': os.environ.get('CACHE_USER', 'admin'),
        'password': os.environ.get('CACHE_PASS', 'secret'),
        'database': os.environ.get('CACHE_DB', '0'),  # Slight difference
        'timeout': 30,
        'retry_count': 3
    }
    
    return config

# =============================================================================
# SORTING ALGORITHM CLONES
# =============================================================================

def bubble_sort_ascending(arr):
    """Bubble sort in ascending order."""
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

def bubble_sort_descending(arr):
    """Bubble sort in descending order (SORT CLONE)."""
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] < arr[j + 1]:  # Different comparison
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

# =============================================================================
# DATA TRANSFORMATION CLONES
# =============================================================================

def transform_user_data(raw_data):
    """Transform raw user data."""
    transformed = {}
    
    for key, value in raw_data.items():
        if key == 'name':
            transformed[key] = value.strip().title()
        elif key == 'email':
            transformed[key] = value.strip().lower()
        elif key == 'phone':
            transformed[key] = ''.join(filter(str.isdigit, value))
        else:
            transformed[key] = value
    
    return transformed

def transform_customer_data(raw_data):
    """Transform raw customer data (TRANSFORM CLONE)."""
    transformed = {}
    
    for key, value in raw_data.items():
        if key == 'name':
            transformed[key] = value.strip().title()
        elif key == 'email':
            transformed[key] = value.strip().lower()
        elif key == 'phone':
            transformed[key] = ''.join(filter(str.isdigit, value))
        else:
            transformed[key] = value
    
    return transformed

# =============================================================================
# UTILITY FUNCTION CLONES
# =============================================================================

def format_currency_usd(amount):
    """Format amount as USD currency."""
    if amount is None:
        return "$0.00"
    
    try:
        amount = float(amount)
        return f"${amount:.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def format_currency_eur(amount):
    """Format amount as EUR currency (UTILITY CLONE)."""
    if amount is None:
        return "€0.00"
    
    try:
        amount = float(amount)
        return f"€{amount:.2f}"  # Different currency symbol
    except (ValueError, TypeError):
        return "€0.00"
