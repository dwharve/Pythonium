"""
False positive cases for alternative implementation detector.
These should NOT be flagged as having better alternatives.
"""

# Case 1: Complex logic that can't be simplified to comprehension
def complex_processing(items):
    """Complex processing logic that needs explicit loops"""
    result = []
    state = {'counter': 0, 'last_value': None}
    
    for item in items:
        if state['last_value'] is not None:
            if item > state['last_value'] * 2:
                state['counter'] += 1
                result.append((item, state['counter']))
            else:
                state['counter'] = 0
        state['last_value'] = item
    
    return result

# Case 2: Early termination logic
def find_first_match(items, condition_func):
    """Early termination can't be replaced with comprehension"""
    for i, item in enumerate(items):
        if condition_func(item):
            # Additional processing after finding match
            processed = item.upper() if isinstance(item, str) else str(item)
            return i, processed
    return None, None

# Case 3: Side effects in loop
def log_and_process(items, logger):
    """Loop with side effects (logging)"""
    results = []
    for i, item in enumerate(items):
        logger.info(f"Processing item {i}: {item}")
        if item is not None:
            results.append(item * 2)
            logger.debug(f"Processed result: {item * 2}")
    return results

# Case 4: Exception handling in loop
def safe_convert_numbers(strings):
    """Exception handling makes simple comprehension inappropriate"""
    results = []
    errors = []
    
    for i, s in enumerate(strings):
        try:
            num = float(s)
            results.append(num)
        except ValueError as e:
            errors.append((i, s, str(e)))
    
    return results, errors

# Case 5: Multiple collections being built
def partition_data(items):
    """Building multiple collections simultaneously"""
    positive = []
    negative = []
    zero = []
    
    for item in items:
        if item > 0:
            positive.append(item)
        elif item < 0:
            negative.append(item)
        else:
            zero.append(item)
    
    return positive, negative, zero

# Case 6: Stateful iteration
def running_average(numbers):
    """Stateful computation requiring explicit loop"""
    averages = []
    total = 0
    
    for i, num in enumerate(numbers):
        total += num
        avg = total / (i + 1)
        averages.append(avg)
    
    return averages

# Case 7: Complex nested conditions
def validate_and_transform(data):
    """Complex validation logic"""
    results = []
    
    for item in data:
        if isinstance(item, dict):
            if 'value' in item and 'type' in item:
                if item['type'] == 'numeric' and isinstance(item['value'], (int, float)):
                    if item['value'] >= 0:
                        results.append({'transformed': item['value'] ** 0.5})
                elif item['type'] == 'string' and isinstance(item['value'], str):
                    if len(item['value']) > 3:
                        results.append({'transformed': item['value'].upper()})
    
    return results

# Case 8: Resource management in loop
def process_files(filenames):
    """Resource management requires explicit control"""
    results = []
    
    for filename in filenames:
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if len(content) > 0:
                    results.append({
                        'filename': filename,
                        'size': len(content),
                        'first_line': content.split('\n')[0] if content else ''
                    })
        except IOError:
            # Log error but continue processing
            results.append({
                'filename': filename,
                'error': 'Could not read file'
            })
    
    return results

# Case 9: Performance-critical custom implementation
def optimized_search(sorted_list, target):
    """Custom binary search implementation for performance"""
    left, right = 0, len(sorted_list) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if sorted_list[mid] == target:
            return mid
        elif sorted_list[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# Case 10: Generator-like behavior with memory constraints
def chunked_processing(large_data, chunk_size):
    """Memory-efficient processing of large data"""
    results = []
    current_chunk = []
    
    for item in large_data:
        current_chunk.append(item)
        if len(current_chunk) >= chunk_size:
            # Process chunk
            processed = sum(current_chunk) / len(current_chunk)
            results.append(processed)
            current_chunk = []
    
    # Process remaining items
    if current_chunk:
        processed = sum(current_chunk) / len(current_chunk)
        results.append(processed)
    
    return results
