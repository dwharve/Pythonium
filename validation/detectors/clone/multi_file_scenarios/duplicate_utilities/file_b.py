"""
File B with utilities that duplicate logic from file_a.py.
This should be detected by the clone detector.
"""


def email_validator(email_address):
    """Validate email - almost identical to validate_email in file_a.py"""
    if not email_address or '@' not in email_address:
        return False
    
    email_parts = email_address.split('@')
    if len(email_parts) != 2:
        return False
    
    user_part, domain_part = email_parts
    if not user_part or not domain_part:
        return False
    
    if '.' not in domain_part:
        return False
    
    return True


def validate_user_info(user_info):
    """Validate user info - very similar to process_user_data in file_a.py"""
    if not user_info:
        raise ValueError("User info cannot be empty")
    
    mandatory_fields = ['name', 'email', 'age']
    for field in mandatory_fields:
        if field not in user_info:
            raise ValueError(f"Missing required field: {field}")
    
    # Almost identical validation logic
    if not user_info['name'].strip():
        raise ValueError("Name cannot be empty")
    
    if not email_validator(user_info['email']):
        raise ValueError("Invalid email format")
    
    if user_info['age'] < 0 or user_info['age'] > 150:
        raise ValueError("Invalid age")
    
    return {
        'name': user_info['name'].strip().title(),
        'email': user_info['email'].lower(),
        'age': int(user_info['age'])
    }


class ItemProcessor:
    """Item processor - very similar to DataProcessor in file_a.py"""
    
    def __init__(self):
        self.items_processed = 0
        self.processing_errors = 0
    
    def handle_item(self, item):
        """Handle a single item - similar to process_item"""
        try:
            if not item:
                raise ValueError("Item cannot be empty")
            
            # Almost identical processing logic
            result = {
                'original': item,
                'processed': str(item).upper(),
                'length': len(str(item)),
                'timestamp': 'now'
            }
            
            self.items_processed += 1
            return result
        
        except Exception as e:
            self.processing_errors += 1
            return {'error': str(e)}
    
    def get_processing_stats(self):
        """Get stats - similar to get_stats in file_a.py"""
        total_items = self.items_processed + self.processing_errors
        success_percentage = (self.items_processed / total_items * 100) if total_items > 0 else 0
        
        return {
            'processed': self.items_processed,
            'errors': self.processing_errors,
            'total': total_items,
            'success_rate': success_percentage
        }


def format_phone_number(phone):
    """Format phone number - unique to file_b"""
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone  # Return original if can't format
