"""
File A with utilities that are duplicated in other files.
This should be detected by the clone detector.
"""


def validate_email(email):
    """Validate email address - duplicated in file_b.py"""
    if not email or '@' not in email:
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


def process_user_data(user_data):
    """Process user data - similar logic in file_b.py"""
    if not user_data:
        raise ValueError("User data cannot be empty")
    
    required_fields = ['name', 'email', 'age']
    for field in required_fields:
        if field not in user_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Validation logic
    if not user_data['name'].strip():
        raise ValueError("Name cannot be empty")
    
    if not validate_email(user_data['email']):
        raise ValueError("Invalid email format")
    
    if user_data['age'] < 0 or user_data['age'] > 150:
        raise ValueError("Invalid age")
    
    return {
        'name': user_data['name'].strip().title(),
        'email': user_data['email'].lower(),
        'age': int(user_data['age'])
    }


def calculate_statistics(numbers):
    """Calculate basic statistics - duplicated in file_c.py"""
    if not numbers:
        return {
            'count': 0,
            'sum': 0,
            'average': 0,
            'min': 0,
            'max': 0
        }
    
    total = sum(numbers)
    count = len(numbers)
    
    return {
        'count': count,
        'sum': total,
        'average': total / count,
        'min': min(numbers),
        'max': max(numbers)
    }


class DataProcessor:
    """Data processor class - similar in file_b.py"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    def process_item(self, item):
        """Process a single item"""
        try:
            if not item:
                raise ValueError("Item cannot be empty")
            
            # Basic processing logic
            result = {
                'original': item,
                'processed': str(item).upper(),
                'length': len(str(item)),
                'timestamp': 'now'
            }
            
            self.processed_count += 1
            return result
        
        except Exception as e:
            self.error_count += 1
            return {'error': str(e)}
    
    def get_stats(self):
        """Get processing statistics"""
        total = self.processed_count + self.error_count
        success_rate = (self.processed_count / total * 100) if total > 0 else 0
        
        return {
            'processed': self.processed_count,
            'errors': self.error_count,
            'total': total,
            'success_rate': success_rate
        }
