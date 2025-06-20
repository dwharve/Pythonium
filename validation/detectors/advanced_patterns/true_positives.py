"""
True positive cases for advanced patterns detector.
These contain advanced code patterns that should be detected.
"""

# Case 1: Complex nested loops with multiple conditions
def complex_data_processing(data_matrix, filters, transformations):
    """Complex nested processing with multiple conditions"""
    results = []
    
    for row_idx, row in enumerate(data_matrix):
        for col_idx, cell in enumerate(row):
            for filter_name, filter_func in filters.items():
                if filter_func(cell, row_idx, col_idx):
                    for transform_name, transform_func in transformations.items():
                        if transform_name.startswith(filter_name):
                            for multiplier in [1, 2, 4]:
                                if cell * multiplier > 100:
                                    transformed = transform_func(cell * multiplier)
                                    if transformed not in results:
                                        results.append(transformed)
    
    return results

# Case 2: Deep recursion with multiple recursive calls
def complex_tree_traversal(node, depth=0, visited=None, callback=None):
    """Complex recursive tree traversal with multiple patterns"""
    if visited is None:
        visited = set()
    
    if node is None or node.id in visited:
        return []
    
    visited.add(node.id)
    results = []
    
    # Process current node
    if callback:
        result = callback(node, depth)
        if result:
            results.append(result)
    
    # Recursive calls for children
    if hasattr(node, 'children'):
        for child in node.children:
            child_results = complex_tree_traversal(child, depth + 1, visited, callback)
            results.extend(child_results)
    
    # Recursive calls for siblings
    if hasattr(node, 'siblings'):
        for sibling in node.siblings:
            if sibling.id not in visited:
                sibling_results = complex_tree_traversal(sibling, depth, visited, callback)
                results.extend(sibling_results)
    
    # Recursive calls for parents (if depth allows)
    if hasattr(node, 'parent') and depth < 5:
        parent_results = complex_tree_traversal(node.parent, depth + 1, visited, callback)
        results.extend(parent_results)
    
    return results

# Case 3: Multiple inheritance with method resolution complexity
class DatabaseMixin:
    """Database operations mixin"""
    def save(self):
        return f"{self.__class__.__name__} saved to database"
    
    def delete(self):
        return f"{self.__class__.__name__} deleted from database"

class CacheMixin:
    """Cache operations mixin"""
    def cache_key(self):
        return f"{self.__class__.__name__}_{getattr(self, 'id', 'unknown')}"
    
    def save(self):
        result = super().save()
        self.cache_set(self.cache_key(), self)
        return result
    
    def cache_set(self, key, value):
        return f"Cached {key}: {value}"

class ValidationMixin:
    """Validation mixin"""
    def validate(self):
        for field in self.required_fields:
            if not hasattr(self, field):
                raise ValueError(f"Missing required field: {field}")
        return True
    
    def save(self):
        self.validate()
        return super().save()

class ComplexModel(DatabaseMixin, CacheMixin, ValidationMixin):
    """Complex model with multiple inheritance"""
    required_fields = ['name', 'email']
    
    def __init__(self, name, email, id=None):
        self.name = name
        self.email = email
        self.id = id

# Case 4: Dynamic method generation and metaclass usage
class DynamicMethodMeta(type):
    """Metaclass that dynamically creates methods"""
    def __new__(cls, name, bases, attrs):
        # Generate getter/setter methods for all fields
        if 'fields' in attrs:
            for field in attrs['fields']:
                # Create getter
                def make_getter(field_name):
                    def getter(self):
                        return getattr(self, f'_{field_name}', None)
                    return getter
                
                # Create setter
                def make_setter(field_name):
                    def setter(self, value):
                        setattr(self, f'_{field_name}', value)
                        self._notify_change(field_name, value)
                    return setter
                
                attrs[f'get_{field}'] = make_getter(field)
                attrs[f'set_{field}'] = make_setter(field)
        
        return super().__new__(cls, name, bases, attrs)

class DynamicModel(metaclass=DynamicMethodMeta):
    """Model with dynamically generated methods"""
    fields = ['name', 'email', 'age', 'address']
    
    def __init__(self):
        self._observers = []
    
    def _notify_change(self, field, value):
        for observer in self._observers:
            observer.on_field_change(self, field, value)

# Case 5: Complex decorator patterns with state
class StatefulDecorator:
    """Decorator that maintains state across calls"""
    def __init__(self, max_calls=None, track_args=False):
        self.max_calls = max_calls
        self.track_args = track_args
        self.call_count = {}
        self.call_history = {}
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            
            # Initialize tracking
            if func_name not in self.call_count:
                self.call_count[func_name] = 0
                self.call_history[func_name] = []
            
            # Check call limit
            if self.max_calls and self.call_count[func_name] >= self.max_calls:
                raise Exception(f"Function {func_name} exceeded max calls ({self.max_calls})")
            
            # Track call
            self.call_count[func_name] += 1
            if self.track_args:
                self.call_history[func_name].append((args, kwargs))
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Rollback count on error
                self.call_count[func_name] -= 1
                raise e
        
        return wrapper

# Case 6: Complex context manager with nested resource management
class ComplexResourceManager:
    """Complex context manager handling multiple resources"""
    def __init__(self, resources, cleanup_order=None):
        self.resources = resources
        self.cleanup_order = cleanup_order or list(reversed(resources.keys()))
        self.active_resources = {}
        self.errors = []
    
    def __enter__(self):
        for name, resource_config in self.resources.items():
            try:
                if isinstance(resource_config, dict):
                    resource_type = resource_config['type']
                    resource_args = resource_config.get('args', [])
                    resource_kwargs = resource_config.get('kwargs', {})
                    
                    if resource_type == 'file':
                        resource = open(*resource_args, **resource_kwargs)
                    elif resource_type == 'connection':
                        resource = self._create_connection(*resource_args, **resource_kwargs)
                    else:
                        resource = resource_type(*resource_args, **resource_kwargs)
                    
                    self.active_resources[name] = resource
                else:
                    self.active_resources[name] = resource_config
            
            except Exception as e:
                self.errors.append(f"Failed to initialize {name}: {e}")
                # Cleanup already initialized resources
                self.__exit__(type(e), e, None)
                raise e
        
        return self.active_resources
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for name in self.cleanup_order:
            if name in self.active_resources:
                try:
                    resource = self.active_resources[name]
                    if hasattr(resource, 'close'):
                        resource.close()
                    elif hasattr(resource, '__exit__'):
                        resource.__exit__(exc_type, exc_val, exc_tb)
                except Exception as e:
                    self.errors.append(f"Error closing {name}: {e}")
                finally:
                    del self.active_resources[name]
    
    def _create_connection(self, host, port, **kwargs):
        """Simulate connection creation"""
        return f"Connection to {host}:{port}"

# Case 7: Complex generator with multiple yield points and state
def complex_data_generator(data_sources, filters=None, batch_size=100):
    """Complex generator with multiple yield points and state management"""
    state = {
        'processed_count': 0,
        'error_count': 0,
        'current_source': None,
        'batch_buffer': []
    }
    
    for source_name, source in data_sources.items():
        state['current_source'] = source_name
        
        try:
            for item in source:
                # Apply filters
                if filters:
                    skip_item = False
                    for filter_name, filter_func in filters.items():
                        try:
                            if not filter_func(item):
                                skip_item = True
                                break
                        except Exception as e:
                            state['error_count'] += 1
                            yield {'error': f"Filter {filter_name} failed: {e}", 'item': item}
                            skip_item = True
                            break
                    
                    if skip_item:
                        continue
                
                # Add to batch
                state['batch_buffer'].append(item)
                state['processed_count'] += 1
                
                # Yield batch when full
                if len(state['batch_buffer']) >= batch_size:
                    yield {
                        'batch': state['batch_buffer'].copy(),
                        'source': source_name,
                        'batch_number': state['processed_count'] // batch_size,
                        'state': state.copy()
                    }
                    state['batch_buffer'].clear()
                
                # Yield progress updates
                if state['processed_count'] % 1000 == 0:
                    yield {
                        'progress': {
                            'processed': state['processed_count'],
                            'errors': state['error_count'],
                            'current_source': source_name
                        }
                    }
        
        except Exception as e:
            state['error_count'] += 1
            yield {'source_error': f"Source {source_name} failed: {e}"}
    
    # Yield remaining items
    if state['batch_buffer']:
        yield {
            'final_batch': state['batch_buffer'],
            'final_state': state
        }

# Case 8: Complex function composition and higher-order functions
def create_complex_pipeline(*operations):
    """Create a complex data processing pipeline"""
    def pipeline(data):
        result = data
        operation_results = []
        
        for i, operation in enumerate(operations):
            try:
                if callable(operation):
                    # Simple function
                    result = operation(result)
                elif isinstance(operation, dict):
                    # Operation with configuration
                    func = operation['func']
                    args = operation.get('args', [])
                    kwargs = operation.get('kwargs', {})
                    
                    if operation.get('partial'):
                        # Create partial application
                        from functools import partial
                        func = partial(func, *args, **kwargs)
                        result = func(result)
                    else:
                        result = func(result, *args, **kwargs)
                elif isinstance(operation, tuple):
                    # Multiple operations in parallel
                    parallel_results = []
                    for sub_op in operation:
                        parallel_results.append(sub_op(result))
                    
                    # Combine parallel results
                    if len(parallel_results) == 1:
                        result = parallel_results[0]
                    else:
                        result = parallel_results
                
                operation_results.append({
                    'step': i,
                    'operation': str(operation),
                    'result_type': type(result).__name__,
                    'result_size': len(result) if hasattr(result, '__len__') else 'unknown'
                })
            
            except Exception as e:
                operation_results.append({
                    'step': i,
                    'operation': str(operation),
                    'error': str(e)
                })
                raise e
        
        return {
            'result': result,
            'pipeline_info': operation_results
        }
    
    return pipeline

# Case 9: Complex async patterns with multiple awaits
async def complex_async_orchestrator(tasks, concurrency_limit=5, timeout=30):
    """Complex async orchestrator with multiple patterns"""
    import asyncio
    from collections import defaultdict
    
    results = defaultdict(list)
    errors = []
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async def execute_task(task_id, task_func, *args, **kwargs):
        async with semaphore:
            try:
                if asyncio.iscoroutinefunction(task_func):
                    result = await asyncio.wait_for(task_func(*args, **kwargs), timeout=timeout)
                else:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, task_func, *args, **kwargs)
                
                results['completed'].append({
                    'task_id': task_id,
                    'result': result,
                    'timestamp': asyncio.get_event_loop().time()
                })
                
            except asyncio.TimeoutError:
                errors.append(f"Task {task_id} timed out")
                results['timeout'].append(task_id)
            except Exception as e:
                errors.append(f"Task {task_id} failed: {e}")
                results['failed'].append(task_id)
    
    # Create coroutines for all tasks
    coroutines = []
    for task_id, task_config in tasks.items():
        if isinstance(task_config, dict):
            func = task_config['func']
            args = task_config.get('args', [])
            kwargs = task_config.get('kwargs', {})
        else:
            func = task_config
            args = []
            kwargs = {}
        
        coroutines.append(execute_task(task_id, func, *args, **kwargs))
    
    # Execute all tasks
    await asyncio.gather(*coroutines, return_exceptions=True)
    
    return {
        'results': dict(results),
        'errors': errors,
        'summary': {
            'total': len(tasks),
            'completed': len(results['completed']),
            'failed': len(results['failed']),
            'timeout': len(results['timeout'])
        }
    }

# Case 10: Complex algorithm with multiple optimization strategies
def complex_optimization_algorithm(problem_space, strategies, max_iterations=1000):
    """Complex optimization algorithm using multiple strategies"""
    best_solution = None
    best_score = float('-inf')
    iteration_history = []
    strategy_performance = {}
    
    # Initialize strategies
    for strategy_name, strategy_config in strategies.items():
        strategy_performance[strategy_name] = {
            'attempts': 0,
            'improvements': 0,
            'best_score': float('-inf')
        }
    
    for iteration in range(max_iterations):
        iteration_info = {
            'iteration': iteration,
            'strategy_results': {}
        }
        
        # Try each strategy
        for strategy_name, strategy_config in strategies.items():
            strategy_func = strategy_config['func']
            strategy_params = strategy_config.get('params', {})
            
            # Apply strategy
            try:
                candidate_solution = strategy_func(
                    problem_space, 
                    current_best=best_solution,
                    iteration=iteration,
                    **strategy_params
                )
                
                # Evaluate solution
                score = problem_space.evaluate(candidate_solution)
                strategy_performance[strategy_name]['attempts'] += 1
                
                # Track improvements
                if score > strategy_performance[strategy_name]['best_score']:
                    strategy_performance[strategy_name]['best_score'] = score
                    strategy_performance[strategy_name]['improvements'] += 1
                
                # Update global best
                if score > best_score:
                    best_solution = candidate_solution
                    best_score = score
                
                iteration_info['strategy_results'][strategy_name] = {
                    'score': score,
                    'improved': score > best_score
                }
                
            except Exception as e:
                iteration_info['strategy_results'][strategy_name] = {
                    'error': str(e)
                }
        
        iteration_history.append(iteration_info)
        
        # Early termination conditions
        if best_score >= problem_space.target_score:
            break
        
        # Adaptive strategy selection based on performance
        if iteration % 100 == 0 and iteration > 0:
            strategies = _adapt_strategies(strategies, strategy_performance)
    
    return {
        'best_solution': best_solution,
        'best_score': best_score,
        'iterations': len(iteration_history),
        'strategy_performance': strategy_performance,
        'history': iteration_history
    }

def _adapt_strategies(strategies, performance):
    """Adapt strategy parameters based on performance"""
    adapted_strategies = {}
    
    for name, config in strategies.items():
        perf = performance[name]
        improvement_rate = perf['improvements'] / max(perf['attempts'], 1)
        
        # Adapt parameters based on performance
        new_config = config.copy()
        if improvement_rate > 0.1:
            # Strategy is performing well, keep it
            adapted_strategies[name] = new_config
        elif improvement_rate > 0.05:
            # Strategy is okay, adjust parameters
            params = new_config.get('params', {})
            # Example adaptations
            if 'temperature' in params:
                params['temperature'] *= 0.9  # Cool down
            if 'mutation_rate' in params:
                params['mutation_rate'] *= 1.1  # Increase mutation
            adapted_strategies[name] = new_config
        # Strategies with poor performance are dropped
    
    return adapted_strategies
