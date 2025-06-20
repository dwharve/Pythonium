"""
Complexity Hotspot Detector Validation - High Complexity Cases

This module contains functions with genuinely high complexity that should
be detected by the complexity hotspot detector.
"""

# =============================================================================
# HIGH CYCLOMATIC COMPLEXITY - Many decision points
# =============================================================================

def complex_data_processor(data, options=None):
    """
    Complex data processing function with high cyclomatic complexity.
    This should be detected as a complexity hotspot.
    """
    if not data:
        return None
    
    if not isinstance(data, (list, dict)):
        return None
    
    options = options or {}
    result = {}
    
    # Multiple nested conditions and loops
    if isinstance(data, dict):
        for key, value in data.items():
            if key.startswith('_'):
                continue
            
            if isinstance(value, str):
                if options.get('uppercase'):
                    if options.get('trim'):
                        value = value.strip().upper()
                    else:
                        value = value.upper()
                elif options.get('lowercase'):
                    if options.get('trim'):
                        value = value.strip().lower()
                    else:
                        value = value.lower()
                elif options.get('title'):
                    if options.get('trim'):
                        value = value.strip().title()
                    else:
                        value = value.title()
                
                if options.get('remove_special'):
                    import re
                    value = re.sub(r'[^a-zA-Z0-9\s]', '', value)
                
                if options.get('max_length'):
                    if len(value) > options['max_length']:
                        value = value[:options['max_length']]
                
            elif isinstance(value, (int, float)):
                if options.get('round'):
                    if isinstance(value, float):
                        value = round(value, options.get('decimals', 2))
                
                if options.get('abs'):
                    value = abs(value)
                
                if options.get('min_value'):
                    if value < options['min_value']:
                        value = options['min_value']
                
                if options.get('max_value'):
                    if value > options['max_value']:
                        value = options['max_value']
                
                if options.get('multiply'):
                    value = value * options['multiply']
                
            elif isinstance(value, list):
                if options.get('sort'):
                    if options.get('reverse'):
                        value = sorted(value, reverse=True)
                    else:
                        value = sorted(value)
                
                if options.get('unique'):
                    value = list(set(value))
                
                if options.get('filter_none'):
                    value = [v for v in value if v is not None]
                
                if options.get('filter_empty'):
                    value = [v for v in value if v]
                
                if options.get('max_items'):
                    if len(value) > options['max_items']:
                        value = value[:options['max_items']]
            
            result[key] = value
    
    elif isinstance(data, list):
        processed_items = []
        
        for item in data:
            if isinstance(item, dict):
                processed_item = {}
                
                for k, v in item.items():
                    if k.startswith('_'):
                        continue
                    
                    if isinstance(v, str):
                        if options.get('normalize_strings'):
                            v = v.strip().lower()
                        
                        if options.get('remove_html'):
                            import re
                            v = re.sub(r'<[^>]+>', '', v)
                        
                        if options.get('validate_email'):
                            if '@' not in v:
                                continue
                    
                    elif isinstance(v, (int, float)):
                        if options.get('validate_positive'):
                            if v <= 0:
                                continue
                        
                        if options.get('validate_range'):
                            min_val = options.get('min_range', 0)
                            max_val = options.get('max_range', 100)
                            if not (min_val <= v <= max_val):
                                continue
                    
                    processed_item[k] = v
                
                if processed_item:
                    processed_items.append(processed_item)
            
            elif isinstance(item, str):
                if options.get('filter_short'):
                    if len(item) < options.get('min_length', 3):
                        continue
                
                if options.get('filter_pattern'):
                    import re
                    pattern = options['filter_pattern']
                    if not re.match(pattern, item):
                        continue
                
                processed_items.append(item)
            
            elif isinstance(item, (int, float)):
                if options.get('filter_outliers'):
                    # Complex outlier detection
                    if isinstance(data, list) and len(data) > 1:
                        numbers = [x for x in data if isinstance(x, (int, float))]
                        if numbers:
                            mean = sum(numbers) / len(numbers)
                            variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
                            std_dev = variance ** 0.5
                            
                            if abs(item - mean) > 2 * std_dev:
                                continue
                
                processed_items.append(item)
        
        result = processed_items
    
    # Final validation and cleanup
    if options.get('validate_result'):
        if isinstance(result, dict):
            if not result:
                return None
            
            if options.get('required_fields'):
                for field in options['required_fields']:
                    if field not in result:
                        return None
        
        elif isinstance(result, list):
            if not result:
                return None
            
            if options.get('min_items'):
                if len(result) < options['min_items']:
                    return None
    
    return result

# =============================================================================
# DEEPLY NESTED FUNCTION - High nesting complexity
# =============================================================================

def deeply_nested_processor(config):
    """
    Function with deep nesting levels that should be detected.
    """
    if config:
        if 'processing' in config:
            if config['processing'].get('enabled'):
                if 'rules' in config['processing']:
                    for rule in config['processing']['rules']:
                        if rule.get('active'):
                            if 'conditions' in rule:
                                for condition in rule['conditions']:
                                    if condition.get('type') == 'filter':
                                        if 'parameters' in condition:
                                            for param_name, param_value in condition['parameters'].items():
                                                if param_name == 'threshold':
                                                    if isinstance(param_value, (int, float)):
                                                        if param_value > 0:
                                                            if param_value < 100:
                                                                # Apply threshold filter
                                                                if 'data' in config:
                                                                    filtered_data = []
                                                                    for item in config['data']:
                                                                        if isinstance(item, dict):
                                                                            if 'score' in item:
                                                                                if item['score'] >= param_value:
                                                                                    filtered_data.append(item)
                                                                    config['data'] = filtered_data
                                    elif condition.get('type') == 'transform':
                                        if 'operations' in condition:
                                            for operation in condition['operations']:
                                                if operation.get('name') == 'normalize':
                                                    if 'data' in config:
                                                        for item in config['data']:
                                                            if isinstance(item, dict):
                                                                for key, value in item.items():
                                                                    if isinstance(value, str):
                                                                        item[key] = value.strip().lower()
    
    return config

# =============================================================================
# MANY PARAMETERS FUNCTION - High parameter complexity
# =============================================================================

def function_with_many_parameters(
    param1, param2, param3, param4, param5, param6, param7, param8, param9, param10,
    param11=None, param12=None, param13=None, param14=None, param15=None,
    option_a=False, option_b=False, option_c=False, option_d=False, option_e=False,
    config_x=None, config_y=None, config_z=None,
    flag_alpha=True, flag_beta=True, flag_gamma=True,
    threshold_1=10, threshold_2=20, threshold_3=30,
    multiplier_a=1.0, multiplier_b=2.0, multiplier_c=3.0,
    **kwargs
):
    """
    Function with many parameters that increases complexity.
    """
    # Complex parameter validation and processing
    params = [param1, param2, param3, param4, param5, param6, param7, param8, param9, param10]
    optional_params = [param11, param12, param13, param14, param15]
    options = [option_a, option_b, option_c, option_d, option_e]
    configs = [config_x, config_y, config_z]
    flags = [flag_alpha, flag_beta, flag_gamma]
    thresholds = [threshold_1, threshold_2, threshold_3]
    multipliers = [multiplier_a, multiplier_b, multiplier_c]
    
    result = {}
    
    # Complex processing logic based on parameters
    for i, param in enumerate(params):
        if param is not None:
            if options[i % len(options)]:
                if flags[i % len(flags)]:
                    processed_value = param * multipliers[i % len(multipliers)]
                    if processed_value > thresholds[i % len(thresholds)]:
                        result[f'param_{i+1}'] = processed_value
    
    for i, opt_param in enumerate(optional_params):
        if opt_param is not None:
            if configs[i % len(configs)] is not None:
                result[f'optional_{i+1}'] = opt_param
    
    # Process kwargs
    for key, value in kwargs.items():
        if key.startswith('special_'):
            result[key] = value
    
    return result

# =============================================================================
# COMPLEX STATE MACHINE - High logical complexity
# =============================================================================

def complex_state_machine(events, initial_state='start'):
    """
    Complex state machine with many transitions and conditions.
    """
    state = initial_state
    results = []
    context = {}
    
    for event in events:
        event_type = event.get('type')
        event_data = event.get('data', {})
        
        if state == 'start':
            if event_type == 'initialize':
                if event_data.get('valid'):
                    state = 'initialized'
                    context['initialized_at'] = event_data.get('timestamp')
                else:
                    state = 'error'
                    context['error'] = 'Invalid initialization'
            elif event_type == 'reset':
                state = 'start'
                context.clear()
            else:
                state = 'error'
                context['error'] = f'Invalid event {event_type} in state {state}'
        
        elif state == 'initialized':
            if event_type == 'configure':
                if event_data.get('config'):
                    config = event_data['config']
                    if config.get('mode') == 'normal':
                        state = 'configured'
                        context['config'] = config
                    elif config.get('mode') == 'debug':
                        state = 'debug_configured'
                        context['config'] = config
                        context['debug'] = True
                    elif config.get('mode') == 'test':
                        state = 'test_configured'
                        context['config'] = config
                        context['test_mode'] = True
                    else:
                        state = 'error'
                        context['error'] = f'Invalid mode {config.get("mode")}'
                else:
                    state = 'error'
                    context['error'] = 'Missing configuration'
            elif event_type == 'reset':
                state = 'start'
                context.clear()
            else:
                state = 'error'
                context['error'] = f'Invalid event {event_type} in state {state}'
        
        elif state == 'configured':
            if event_type == 'start_processing':
                if event_data.get('data'):
                    state = 'processing'
                    context['processing_data'] = event_data['data']
                else:
                    state = 'error'
                    context['error'] = 'No data to process'
            elif event_type == 'reconfigure':
                state = 'initialized'
            elif event_type == 'reset':
                state = 'start'
                context.clear()
            else:
                state = 'error'
                context['error'] = f'Invalid event {event_type} in state {state}'
        
        elif state == 'debug_configured':
            if event_type == 'start_debug':
                if event_data.get('debug_level'):
                    level = event_data['debug_level']
                    if level in ['low', 'medium', 'high']:
                        state = 'debugging'
                        context['debug_level'] = level
                    else:
                        state = 'error'
                        context['error'] = f'Invalid debug level {level}'
                else:
                    state = 'error'
                    context['error'] = 'Missing debug level'
            elif event_type == 'exit_debug':
                state = 'configured'
                context.pop('debug', None)
            elif event_type == 'reset':
                state = 'start'
                context.clear()
            else:
                state = 'error'
                context['error'] = f'Invalid event {event_type} in state {state}'
        
        elif state == 'test_configured':
            if event_type == 'run_test':
                if event_data.get('test_suite'):
                    suite = event_data['test_suite']
                    if suite in ['unit', 'integration', 'e2e']:
                        state = 'testing'
                        context['test_suite'] = suite
                    else:
                        state = 'error'
                        context['error'] = f'Invalid test suite {suite}'
                else:
                    state = 'error'
                    context['error'] = 'Missing test suite'
            elif event_type == 'exit_test':
                state = 'configured'
                context.pop('test_mode', None)
            elif event_type == 'reset':
                state = 'start'
                context.clear()
            else:
                state = 'error'
                context['error'] = f'Invalid event {event_type} in state {state}'
        
        elif state == 'processing':
            if event_type == 'process_item':
                if event_data.get('item'):
                    # Complex item processing
                    item = event_data['item']
                    processed = process_complex_item(item, context)
                    results.append(processed)
                else:
                    state = 'error'
                    context['error'] = 'Missing item to process'
            elif event_type == 'finish_processing':
                state = 'completed'
                context['completed_at'] = event_data.get('timestamp')
            elif event_type == 'pause_processing':
                state = 'paused'
                context['paused_at'] = event_data.get('timestamp')
            elif event_type == 'error_processing':
                state = 'processing_error'
                context['processing_error'] = event_data.get('error')
            elif event_type == 'reset':
                state = 'start'
                context.clear()
                results.clear()
            else:
                state = 'error'
                context['error'] = f'Invalid event {event_type} in state {state}'
        
        # Add more states...
        
        # Record state transition
        results.append({
            'event': event,
            'state': state,
            'context': context.copy()
        })
    
    return {
        'final_state': state,
        'context': context,
        'results': results
    }

def process_complex_item(item, context):
    """Helper function for complex item processing."""
    if not item:
        return None
    
    config = context.get('config', {})
    
    # Complex processing logic
    if config.get('transform'):
        if isinstance(item, str):
            if config.get('uppercase'):
                item = item.upper()
            elif config.get('lowercase'):
                item = item.lower()
        elif isinstance(item, (int, float)):
            if config.get('multiply'):
                item = item * config['multiply']
    
    if config.get('validate'):
        # Complex validation
        if isinstance(item, str):
            if len(item) < config.get('min_length', 1):
                return None
        elif isinstance(item, (int, float)):
            if item < config.get('min_value', 0):
                return None
    
    return item

# =============================================================================
# LONG FUNCTION - High length complexity
# =============================================================================

def very_long_function_with_many_operations():
    """
    A very long function that should be detected for length complexity.
    This function has many lines and operations.
    """
    # Initialize variables
    result = {}
    data = []
    config = {}
    state = 'start'
    counter = 0
    
    # First phase: Setup
    print("Starting setup phase")
    config['phase'] = 'setup'
    config['start_time'] = 'now'
    
    # Data initialization
    for i in range(100):
        data.append({
            'id': i,
            'value': i * 2,
            'category': 'A' if i % 2 == 0 else 'B',
            'active': True
        })
    
    # Second phase: Validation
    print("Starting validation phase")
    config['phase'] = 'validation'
    valid_data = []
    
    for item in data:
        if item['value'] > 0:
            if item['category'] == 'A':
                if item['active']:
                    valid_data.append(item)
                    counter += 1
            elif item['category'] == 'B':
                if item['value'] % 4 == 0:
                    valid_data.append(item)
                    counter += 1
    
    # Third phase: Processing
    print("Starting processing phase")
    config['phase'] = 'processing'
    processed_data = []
    
    for item in valid_data:
        processed_item = {}
        processed_item['original_id'] = item['id']
        processed_item['processed_value'] = item['value'] * 1.5
        processed_item['category_upper'] = item['category'].upper()
        processed_item['processing_timestamp'] = 'now'
        
        # Additional processing based on category
        if item['category'] == 'A':
            processed_item['special_flag'] = True
            processed_item['bonus'] = item['value'] * 0.1
        else:
            processed_item['special_flag'] = False
            processed_item['penalty'] = item['value'] * 0.05
        
        processed_data.append(processed_item)
    
    # Fourth phase: Aggregation
    print("Starting aggregation phase")
    config['phase'] = 'aggregation'
    
    total_a = sum(item['processed_value'] for item in processed_data if item['category_upper'] == 'A')
    total_b = sum(item['processed_value'] for item in processed_data if item['category_upper'] == 'B')
    
    avg_a = total_a / len([item for item in processed_data if item['category_upper'] == 'A']) if total_a > 0 else 0
    avg_b = total_b / len([item for item in processed_data if item['category_upper'] == 'B']) if total_b > 0 else 0
    
    # Fifth phase: Reporting
    print("Starting reporting phase")
    config['phase'] = 'reporting'
    
    result['summary'] = {
        'total_items_processed': len(processed_data),
        'category_a_total': total_a,
        'category_b_total': total_b,
        'category_a_average': avg_a,
        'category_b_average': avg_b,
        'processing_counter': counter
    }
    
    result['details'] = processed_data
    result['config'] = config
    result['metadata'] = {
        'version': '1.0',
        'processing_date': 'today',
        'total_phases': 5
    }
    
    # Sixth phase: Cleanup
    print("Starting cleanup phase")
    config['phase'] = 'cleanup'
    
    # Clean up temporary data
    temp_data = []
    for item in processed_data:
        clean_item = {
            'id': item['original_id'],
            'value': item['processed_value'],
            'category': item['category_upper']
        }
        temp_data.append(clean_item)
    
    result['cleaned_data'] = temp_data
    
    # Final phase: Finalization
    print("Starting finalization phase")
    config['phase'] = 'finalization'
    config['end_time'] = 'now'
    config['status'] = 'completed'
    
    # Add final metadata
    result['final_metadata'] = {
        'success': True,
        'error_count': 0,
        'warning_count': 0,
        'total_processing_time': 'calculated',
        'memory_usage': 'calculated'
    }
    
    return result
