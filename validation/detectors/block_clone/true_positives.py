"""
True positive cases for block clone detector.
These contain duplicated code blocks that should be detected.
"""

# Case 1: Duplicated validation logic
def validate_user_data(data):
    """First instance of validation logic"""
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if 'name' not in data:
        raise ValueError("Name is required")
    if 'email' not in data:
        raise ValueError("Email is required")
    if not isinstance(data['name'], str) or len(data['name']) < 2:
        raise ValueError("Name must be a string with at least 2 characters")
    if '@' not in data['email']:
        raise ValueError("Email must contain @ symbol")
    return True

def validate_admin_data(data):
    """Duplicate validation logic with slight variation"""
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if 'name' not in data:
        raise ValueError("Name is required")
    if 'email' not in data:
        raise ValueError("Email is required")
    if not isinstance(data['name'], str) or len(data['name']) < 2:
        raise ValueError("Name must be a string with at least 2 characters")
    if '@' not in data['email']:
        raise ValueError("Email must contain @ symbol")
    # Only difference: additional admin check
    if 'admin_level' not in data:
        raise ValueError("Admin level is required")
    return True

# Case 2: Duplicated file processing logic
def process_csv_file(filename):
    """First instance of CSV processing"""
    results = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if i == 0:  # Skip header
                    continue
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    record = {
                        'id': parts[0].strip(),
                        'name': parts[1].strip(),
                        'value': parts[2].strip()
                    }
                    results.append(record)
    except FileNotFoundError:
        print(f"File {filename} not found")
    except Exception as e:
        print(f"Error processing file: {e}")
    return results

def process_log_file(filename):
    """Nearly identical file processing logic"""
    results = []
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if i == 0:  # Skip header
                    continue
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    record = {
                        'timestamp': parts[0].strip(),
                        'level': parts[1].strip(),
                        'message': parts[2].strip()
                    }
                    results.append(record)
    except FileNotFoundError:
        print(f"File {filename} not found")
    except Exception as e:
        print(f"Error processing file: {e}")
    return results

# Case 3: Duplicated calculation blocks
def calculate_statistics_v1(numbers):
    """First version of statistics calculation"""
    if not numbers:
        return None
    
    # Duplicated calculation block
    total = sum(numbers)
    count = len(numbers)
    mean = total / count
    
    squared_diffs = []
    for num in numbers:
        diff = num - mean
        squared_diffs.append(diff * diff)
    
    variance = sum(squared_diffs) / count
    std_dev = variance ** 0.5
    
    return {
        'mean': mean,
        'variance': variance,
        'std_dev': std_dev,
        'count': count
    }

def calculate_statistics_v2(data_points):
    """Second version with same calculation logic"""
    if not data_points:
        return {'error': 'No data'}
    
    # Same duplicated calculation block
    total = sum(data_points)
    count = len(data_points)
    mean = total / count
    
    squared_diffs = []
    for num in data_points:
        diff = num - mean
        squared_diffs.append(diff * diff)
    
    variance = sum(squared_diffs) / count
    std_dev = variance ** 0.5
    
    return {
        'average': mean,  # Different key name
        'var': variance,  # Different key name
        'standard_deviation': std_dev,
        'size': count
    }

# Case 4: Duplicated error handling pattern
def fetch_user_by_id(user_id):
    """First instance of error handling pattern"""
    try:
        # Simulate database operation
        if not isinstance(user_id, int):
            raise TypeError("User ID must be an integer")
        if user_id <= 0:
            raise ValueError("User ID must be positive")
        
        # Simulate fetching user
        user_data = {'id': user_id, 'name': f'User {user_id}'}
        return {'success': True, 'data': user_data}
        
    except TypeError as e:
        return {'success': False, 'error': str(e), 'error_type': 'TYPE_ERROR'}
    except ValueError as e:
        return {'success': False, 'error': str(e), 'error_type': 'VALUE_ERROR'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'error_type': 'UNKNOWN_ERROR'}

def fetch_product_by_id(product_id):
    """Duplicate error handling pattern"""
    try:
        # Simulate database operation
        if not isinstance(product_id, int):
            raise TypeError("Product ID must be an integer")
        if product_id <= 0:
            raise ValueError("Product ID must be positive")
        
        # Simulate fetching product
        product_data = {'id': product_id, 'name': f'Product {product_id}'}
        return {'success': True, 'data': product_data}
        
    except TypeError as e:
        return {'success': False, 'error': str(e), 'error_type': 'TYPE_ERROR'}
    except ValueError as e:
        return {'success': False, 'error': str(e), 'error_type': 'VALUE_ERROR'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'error_type': 'UNKNOWN_ERROR'}

# Case 5: Duplicated setup/teardown logic
class DatabaseConnection:
    """First instance of connection management"""
    def __init__(self, host, port, database):
        self.host = host
        self.port = port
        self.database = database
        self.connection = None
    
    def connect(self):
        """Duplicated connection logic"""
        try:
            # Simulate connection setup
            self.connection = f"connection://{self.host}:{self.port}/{self.database}"
            print(f"Connected to {self.connection}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """Duplicated disconnection logic"""
        try:
            if self.connection:
                print(f"Disconnecting from {self.connection}")
                self.connection = None
                print("Disconnected successfully")
                return True
        except Exception as e:
            print(f"Disconnection failed: {e}")
            return False

class CacheConnection:
    """Duplicate connection management logic"""
    def __init__(self, host, port, namespace):
        self.host = host
        self.port = port
        self.namespace = namespace
        self.connection = None
    
    def connect(self):
        """Same duplicated connection logic"""
        try:
            # Simulate connection setup
            self.connection = f"connection://{self.host}:{self.port}/{self.namespace}"
            print(f"Connected to {self.connection}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """Same duplicated disconnection logic"""
        try:
            if self.connection:
                print(f"Disconnecting from {self.connection}")
                self.connection = None
                print("Disconnected successfully")
                return True
        except Exception as e:
            print(f"Disconnection failed: {e}")
            return False
