"""
File C with utilities that also contain duplicated logic.
This should be detected by the clone detector.
"""


def compute_stats(number_list):
    """Compute statistics - identical to calculate_statistics in file_a.py"""
    if not number_list:
        return {
            'count': 0,
            'sum': 0,
            'average': 0,
            'min': 0,
            'max': 0
        }
    
    total_sum = sum(number_list)
    list_count = len(number_list)
    
    return {
        'count': list_count,
        'sum': total_sum,
        'average': total_sum / list_count,
        'min': min(number_list),
        'max': max(number_list)
    }


def analyze_numbers(numbers):
    """Analyze numbers - different name but very similar logic"""
    if not numbers:
        return {
            'total_count': 0,
            'total_sum': 0,
            'mean': 0,
            'minimum': 0,
            'maximum': 0
        }
    
    sum_total = sum(numbers)
    count_total = len(numbers)
    
    return {
        'total_count': count_total,
        'total_sum': sum_total,
        'mean': sum_total / count_total,
        'minimum': min(numbers),
        'maximum': max(numbers)
    }


def check_email_format(email_str):
    """Check email format - another duplicate of email validation"""
    if not email_str or '@' not in email_str:
        return False
    
    components = email_str.split('@')
    if len(components) != 2:
        return False
    
    local, domain = components
    if not local or not domain:
        return False
    
    if '.' not in domain:
        return False
    
    return True


class NumberProcessor:
    """Process numbers with similar error tracking"""
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.results = []
    
    def process_number(self, number):
        """Process a number with error handling"""
        try:
            if number is None:
                raise ValueError("Number cannot be None")
            
            # Processing logic
            result = {
                'input': number,
                'squared': number ** 2,
                'doubled': number * 2,
                'is_positive': number > 0
            }
            
            self.success_count += 1
            self.results.append(result)
            return result
        
        except Exception as e:
            self.failure_count += 1
            error_result = {'error': str(e), 'input': number}
            self.results.append(error_result)
            return error_result
    
    def get_summary(self):
        """Get processing summary"""
        total = self.success_count + self.failure_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0
        
        return {
            'successful': self.success_count,
            'failed': self.failure_count,
            'total_processed': total,
            'success_percentage': success_rate,
            'all_results': self.results
        }


def duplicate_file_processing_logic():
    """This function contains logic very similar to file_a and file_b"""
    items_to_process = ['item1', 'item2', 'item3']
    results = []
    
    for item in items_to_process:
        try:
            if not item:
                raise ValueError("Item cannot be empty")
            
            # Similar processing pattern
            processed = {
                'original': item,
                'processed': str(item).upper(),
                'length': len(str(item)),
                'timestamp': 'processed'
            }
            
            results.append(processed)
        
        except Exception as e:
            results.append({'error': str(e)})
    
    return results
