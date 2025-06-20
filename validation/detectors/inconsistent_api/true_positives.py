"""
True positive cases for inconsistent API detector.
These contain inconsistent API patterns that should be detected.
"""

# Case 1: Inconsistent method naming conventions
class DataManager:
    """Class with inconsistent method naming"""
    
    def get_user(self, user_id):
        """Get user by ID - using get_ prefix"""
        return f"User {user_id}"
    
    def fetch_product(self, product_id):
        """Fetch product by ID - using fetch_ prefix (inconsistent)"""
        return f"Product {product_id}"
    
    def retrieve_order(self, order_id):
        """Retrieve order by ID - using retrieve_ prefix (inconsistent)"""
        return f"Order {order_id}"
    
    def getUserProfile(self, user_id):
        """Get user profile - using camelCase (inconsistent)"""
        return f"Profile for {user_id}"

# Case 2: Inconsistent parameter patterns
class ApiClient:
    """API client with inconsistent parameter patterns"""
    
    def create_user(self, name, email, age):
        """Create user with individual parameters"""
        return f"Created user: {name}, {email}, {age}"
    
    def create_product(self, product_data):
        """Create product with dictionary parameter (inconsistent)"""
        return f"Created product: {product_data}"
    
    def update_user(self, user_id, **kwargs):
        """Update user with keyword arguments (inconsistent)"""
        return f"Updated user {user_id}: {kwargs}"
    
    def update_product(self, product_id, data_dict):
        """Update product with dictionary (different pattern)"""
        return f"Updated product {product_id}: {data_dict}"

# Case 3: Inconsistent return types
class ServiceLayer:
    """Service with inconsistent return types"""
    
    def get_user_by_id(self, user_id):
        """Returns user object directly"""
        return {"id": user_id, "name": f"User {user_id}"}
    
    def get_user_by_email(self, email):
        """Returns tuple (found, user) - inconsistent"""
        user = {"email": email, "name": "User"}
        return True, user
    
    def get_user_by_name(self, name):
        """Returns None if not found - inconsistent"""
        if name == "unknown":
            return None
        return {"name": name, "id": 123}
    
    def get_user_profile(self, user_id):
        """Returns list with one item - inconsistent"""
        profile = {"user_id": user_id, "bio": "User bio"}
        return [profile]

# Case 4: Inconsistent error handling
class DatabaseService:
    """Database service with inconsistent error handling"""
    
    def save_user(self, user):
        """Raises exception on error"""
        if not user.get('name'):
            raise ValueError("Name is required")
        return f"Saved user: {user['name']}"
    
    def save_product(self, product):
        """Returns None on error - inconsistent"""
        if not product.get('name'):
            return None
        return f"Saved product: {product['name']}"
    
    def save_order(self, order):
        """Returns boolean success flag - inconsistent"""
        if not order.get('items'):
            return False
        return True
    
    def save_category(self, category):
        """Returns error message string - inconsistent"""
        if not category.get('name'):
            return "Error: Category name is required"
        return f"Saved category: {category['name']}"

# Case 5: Inconsistent property access patterns
class Configuration:
    """Configuration class with inconsistent property access"""
    
    def __init__(self):
        self._database_url = "postgresql://localhost/db"
        self._api_key = "secret_key"
        self._debug_mode = True
        self._cache_timeout = 300
    
    @property
    def database_url(self):
        """Property accessor"""
        return self._database_url
    
    def get_api_key(self):
        """Getter method - inconsistent"""
        return self._api_key
    
    def debug_mode(self):
        """Plain method - inconsistent"""
        return self._debug_mode
    
    # Direct attribute access for cache_timeout - inconsistent
    def set_cache_timeout(self, timeout):
        """Setter method"""
        self.cache_timeout = timeout

# Case 6: Inconsistent initialization patterns
class ConnectionManager:
    """Connection manager with inconsistent initialization"""
    pass

def create_http_connection(host, port):
    """Factory function for HTTP connections"""
    conn = ConnectionManager()
    conn.host = host
    conn.port = port
    conn.type = "HTTP"
    return conn

def create_database_connection(connection_string):
    """Factory function with different parameter pattern"""
    conn = ConnectionManager()
    conn.connection_string = connection_string
    conn.type = "DATABASE"
    return conn

class FtpConnection(ConnectionManager):
    """Class-based approach for FTP - inconsistent pattern"""
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.type = "FTP"

# Case 7: Inconsistent validation patterns
class Validator:
    """Validator with inconsistent validation approaches"""
    
    def validate_email(self, email):
        """Returns boolean"""
        return "@" in email and "." in email
    
    def validate_phone(self, phone):
        """Returns error message or None - inconsistent"""
        if len(phone) < 10:
            return "Phone number too short"
        if not phone.isdigit():
            return "Phone number must contain only digits"
        return None
    
    def validate_age(self, age):
        """Raises exception - inconsistent"""
        if not isinstance(age, int):
            raise TypeError("Age must be an integer")
        if age < 0 or age > 150:
            raise ValueError("Age must be between 0 and 150")
        return True
    
    def validate_password(self, password):
        """Returns tuple (is_valid, errors) - inconsistent"""
        errors = []
        if len(password) < 8:
            errors.append("Password too short")
        if not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letter")
        return len(errors) == 0, errors

# Case 8: Inconsistent callback patterns
class EventSystem:
    """Event system with inconsistent callback patterns"""
    
    def __init__(self):
        self.user_created_callbacks = []
        self.user_updated_handlers = []  # Different naming
        self.on_user_deleted = []        # Different naming
        self.product_listeners = []      # Different naming
    
    def add_user_created_callback(self, callback):
        """Add callback for user creation"""
        self.user_created_callbacks.append(callback)
    
    def register_user_update_handler(self, handler):
        """Register handler - different verb"""
        self.user_updated_handlers.append(handler)
    
    def on_user_delete(self, listener):
        """Different naming pattern"""
        self.on_user_deleted.append(listener)
    
    def subscribe_to_product_events(self, listener):
        """Different API pattern"""
        self.product_listeners.append(listener)

# Case 9: Inconsistent data transformation
class DataTransformer:
    """Data transformer with inconsistent transformation patterns"""
    
    def transform_user_data(self, data):
        """Returns transformed data"""
        return {
            'full_name': f"{data['first_name']} {data['last_name']}",
            'email': data['email'].lower()
        }
    
    def transform_product_data(self, data):
        """Modifies data in place - inconsistent"""
        data['name'] = data['name'].strip().title()
        data['price'] = float(data['price'])
        # Returns None implicitly
    
    def process_order_data(self, data):
        """Different method name pattern and returns tuple"""
        processed_data = {
            'order_id': data['id'],
            'total': sum(item['price'] for item in data['items'])
        }
        metadata = {'processed_at': 'now', 'version': '1.0'}
        return processed_data, metadata

# Case 10: Inconsistent state management
class StateMachine:
    """State machine with inconsistent state management"""
    
    def __init__(self):
        self.current_state = "initial"
        self._previous_state = None
        self.state_history = []
    
    def change_state(self, new_state):
        """Changes state and returns boolean success"""
        if self._is_valid_transition(new_state):
            self._previous_state = self.current_state
            self.current_state = new_state
            return True
        return False
    
    def transition_to(self, new_state):
        """Different method name, raises exception on failure"""
        if not self._is_valid_transition(new_state):
            raise ValueError(f"Invalid transition to {new_state}")
        self.state_history.append(self.current_state)
        self.current_state = new_state
    
    def set_state(self, new_state):
        """Third approach - always succeeds, different tracking"""
        self.current_state = new_state
        # No validation, no history tracking
    
    def _is_valid_transition(self, new_state):
        """Helper method for validation"""
        # Simplified validation
        return new_state != self.current_state
