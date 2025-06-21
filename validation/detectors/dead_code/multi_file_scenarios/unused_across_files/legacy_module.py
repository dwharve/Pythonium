"""
Legacy module with completely unused code.
Nothing from this module is imported or used anywhere.
All code here should be detected as dead code.
"""


class LegacyProcessor:
    """Legacy processor that's no longer used"""
    
    def __init__(self, config):
        self.config = config
        self.processed_items = []
    
    def process_item(self, item):
        """Process an item the old way"""
        processed = {
            'original': item,
            'processed_at': 'legacy_time',
            'method': 'legacy'
        }
        self.processed_items.append(processed)
        return processed
    
    def get_results(self):
        """Get processing results"""
        return self.processed_items
    
    def clear(self):
        """Clear processed items"""
        self.processed_items = []


class LegacyValidator:
    """Legacy validator that's no longer used"""
    
    @staticmethod
    def validate_input(data):
        """Validate input using legacy rules"""
        if not data:
            return False
        if not isinstance(data, dict):
            return False
        required_fields = ['id', 'name', 'type']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_output(result):
        """Validate output using legacy rules"""
        return isinstance(result, dict) and 'processed' in result


def legacy_helper_function(data):
    """Legacy helper function"""
    return f"Legacy processing: {data}"


def another_legacy_function():
    """Another legacy function"""
    return "legacy result"


def legacy_calculation(x, y, z):
    """Legacy calculation function"""
    return (x * y) + z - (x / 2)


# Legacy constants
LEGACY_CONFIG = {
    'version': '1.0',
    'mode': 'legacy',
    'settings': {
        'timeout': 30,
        'retries': 3
    }
}

LEGACY_PATTERNS = [
    r'^legacy_\w+',
    r'old_\d+',
    r'deprecated_.*'
]

LEGACY_MULTIPLIER = 2.5


# Legacy exception classes
class LegacyError(Exception):
    """Legacy error class"""
    pass


class LegacyValidationError(LegacyError):
    """Legacy validation error"""
    pass


class LegacyProcessingError(LegacyError):
    """Legacy processing error"""
    pass


# Legacy decorator
def legacy_decorator(func):
    """Legacy decorator for functions"""
    def wrapper(*args, **kwargs):
        print(f"Legacy call to {func.__name__}")
        try:
            result = func(*args, **kwargs)
            print(f"Legacy success: {func.__name__}")
            return result
        except Exception as e:
            print(f"Legacy error in {func.__name__}: {e}")
            raise LegacyError(f"Legacy processing failed: {e}")
    return wrapper


@legacy_decorator
def decorated_legacy_function(data):
    """Function decorated with legacy decorator"""
    return legacy_helper_function(data)


# Legacy utility functions
def legacy_format_output(data):
    """Format output in legacy format"""
    return f"LEGACY[{data}]"


def legacy_parse_input(input_str):
    """Parse input using legacy parser"""
    parts = input_str.split('|')
    return {
        'id': parts[0] if len(parts) > 0 else None,
        'name': parts[1] if len(parts) > 1 else None,
        'value': parts[2] if len(parts) > 2 else None
    }


# Legacy global variable
legacy_cache = {}
legacy_counter = 0
