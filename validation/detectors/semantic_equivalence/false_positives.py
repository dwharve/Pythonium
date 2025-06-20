"""
False positive cases for semantic equivalence detector.
These should NOT be flagged as semantically equivalent.
"""

# Case 1: Similar structure but different behavior
def calculate_area(width, height):
    """Calculate rectangle area"""
    return width * height

def calculate_perimeter(width, height):
    """Calculate rectangle perimeter - different formula"""
    return 2 * (width + height)

def calculate_diagonal(width, height):
    """Calculate rectangle diagonal - different formula"""
    return (width ** 2 + height ** 2) ** 0.5

# Case 2: Different mathematical operations
def compound_interest(principal, rate, time):
    """Calculate compound interest"""
    return principal * (1 + rate) ** time

def simple_interest(principal, rate, time):
    """Calculate simple interest - different formula"""
    return principal * rate * time

def depreciation(initial_value, rate, time):
    """Calculate depreciation - different behavior"""
    return initial_value * (1 - rate) ** time

# Case 3: Different filtering criteria
def filter_adults(people):
    """Filter people 18 and older"""
    return [person for person in people if person['age'] >= 18]

def filter_seniors(people):
    """Filter people 65 and older - different age threshold"""
    return [person for person in people if person['age'] >= 65]

def filter_minors(people):
    """Filter people under 18 - opposite logic"""
    return [person for person in people if person['age'] < 18]

# Case 4: Different validation rules
def validate_password_basic(password):
    """Basic password validation"""
    return len(password) >= 8

def validate_password_strong(password):
    """Strong password validation - different requirements"""
    if len(password) < 12:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

def validate_password_medium(password):
    """Medium password validation - different requirements"""
    return (len(password) >= 8 and 
            any(c.isdigit() for c in password) and
            any(c.isalpha() for c in password))

# Case 5: Different error handling strategies
def safe_divide_return_none(a, b):
    """Return None on division by zero"""
    try:
        return a / b
    except ZeroDivisionError:
        return None

def safe_divide_return_zero(a, b):
    """Return 0 on division by zero - different default"""
    try:
        return a / b
    except ZeroDivisionError:
        return 0

def safe_divide_raise_custom(a, b):
    """Raise custom exception - different error handling"""
    try:
        return a / b
    except ZeroDivisionError:
        raise ValueError("Cannot divide by zero")

# Case 6: Different data transformations
def normalize_to_uppercase(text):
    """Convert text to uppercase"""
    return text.strip().upper()

def normalize_to_lowercase(text):
    """Convert text to lowercase - different transformation"""
    return text.strip().lower()

def normalize_to_title(text):
    """Convert text to title case - different transformation"""
    return text.strip().title()

# Case 7: Different sorting criteria
def sort_by_age(people):
    """Sort people by age"""
    return sorted(people, key=lambda p: p['age'])

def sort_by_name(people):
    """Sort people by name - different sort key"""
    return sorted(people, key=lambda p: p['name'])

def sort_by_age_desc(people):
    """Sort people by age descending - different order"""
    return sorted(people, key=lambda p: p['age'], reverse=True)

# Case 8: Different aggregation methods
def calculate_sum(numbers):
    """Calculate sum of numbers"""
    total = 0
    for num in numbers:
        total += num
    return total

def calculate_average(numbers):
    """Calculate average - different aggregation"""
    if not numbers:
        return 0
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def calculate_product(numbers):
    """Calculate product - different operation"""
    result = 1
    for num in numbers:
        result *= num
    return result

# Case 9: Different search strategies
def linear_search(items, target):
    """Linear search algorithm"""
    for i, item in enumerate(items):
        if item == target:
            return i
    return -1

def binary_search(items, target):
    """Binary search algorithm - different approach"""
    left, right = 0, len(items) - 1
    while left <= right:
        mid = (left + right) // 2
        if items[mid] == target:
            return mid
        elif items[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

def find_all_occurrences(items, target):
    """Find all occurrences - different goal"""
    indices = []
    for i, item in enumerate(items):
        if item == target:
            indices.append(i)
    return indices

# Case 10: Different data structures
def store_in_list(items):
    """Store items in a list"""
    result = []
    for item in items:
        result.append(item)
    return result

def store_in_set(items):
    """Store items in a set - different data structure"""
    result = set()
    for item in items:
        result.add(item)
    return result

def store_in_dict(items):
    """Store items in a dictionary - different structure"""
    result = {}
    for i, item in enumerate(items):
        result[i] = item
    return result

# Case 11: Different business logic
def calculate_tax_standard(amount):
    """Calculate standard tax rate"""
    return amount * 0.1

def calculate_tax_premium(amount):
    """Calculate premium tax rate - different rate"""
    return amount * 0.15

def calculate_discount(amount):
    """Calculate discount - opposite of tax"""
    return amount * 0.1

# Case 12: Different state modifications
def increment_counter(counter):
    """Increment counter by 1"""
    counter['value'] += 1
    return counter

def decrement_counter(counter):
    """Decrement counter by 1 - opposite operation"""
    counter['value'] -= 1
    return counter

def reset_counter(counter):
    """Reset counter to 0 - different operation"""
    counter['value'] = 0
    return counter

# Case 13: Different file operations
def read_entire_file(filename):
    """Read entire file content"""
    with open(filename, 'r') as f:
        return f.read()

def read_first_line(filename):
    """Read only first line - different scope"""
    with open(filename, 'r') as f:
        return f.readline().strip()

def count_lines(filename):
    """Count lines in file - different operation"""
    with open(filename, 'r') as f:
        return len(f.readlines())

# Case 14: Different string operations
def extract_domain(email):
    """Extract domain from email"""
    return email.split('@')[1] if '@' in email else None

def extract_username(email):
    """Extract username from email - different part"""
    return email.split('@')[0] if '@' in email else None

def validate_email_format(email):
    """Validate email format - different purpose"""
    return '@' in email and '.' in email.split('@')[1]

# Case 15: Different algorithmic approaches
def fibonacci_recursive(n):
    """Fibonacci using recursion"""
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

def fibonacci_iterative(n):
    """Fibonacci using iteration - different algorithm"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def factorial(n):
    """Factorial calculation - different mathematical function"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Case 16: Different caching strategies
def memoized_function(cache, key, compute_func):
    """Memoization with explicit cache"""
    if key not in cache:
        cache[key] = compute_func(key)
    return cache[key]

def cached_function_lru(key, compute_func):
    """LRU caching - different caching strategy"""
    # Simulated LRU cache behavior
    # In real implementation, would use functools.lru_cache
    return compute_func(key)

def no_cache_function(key, compute_func):
    """No caching - always compute"""
    return compute_func(key)

# Case 17: Different concurrency patterns
def sequential_processing(items, process_func):
    """Process items sequentially"""
    results = []
    for item in items:
        result = process_func(item)
        results.append(result)
    return results

def parallel_processing_simulation(items, process_func):
    """Simulate parallel processing - different execution model"""
    # In real implementation would use threading/multiprocessing
    results = []
    for item in items:
        # Simulated parallel execution
        result = process_func(item)
        results.append(result)
    return results

def batch_processing(items, process_func, batch_size=10):
    """Process items in batches - different processing strategy"""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for item in batch:
            result = process_func(item)
            results.append(result)
    return results
