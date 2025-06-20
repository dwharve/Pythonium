"""
Dead Code Detector Validation - Performance Stress Test

This module tests the detector's performance with various scales of dead code
to identify performance bottlenecks and scaling issues.
"""

# =============================================================================
# LARGE SCALE DEAD CODE PATTERNS
# =============================================================================

# Generate many unused functions to test performance
def generate_unused_functions():
    """Test performance with many unused functions."""
    pass

# Programmatically generate unused functions
for i in range(100):
    exec(f"""
def unused_function_{i}():
    '''Unused function number {i}'''
    return {i}
""")

# =============================================================================
# DEEP INHERITANCE HIERARCHIES
# =============================================================================

class Level0:
    def method_level0(self): return 0

class Level1(Level0):
    def method_level1(self): return 1

class Level2(Level1):
    def method_level2(self): return 2

class Level3(Level2):
    def method_level3(self): return 3

class Level4(Level3):
    def method_level4(self): return 4

class Level5(Level4):
    def method_level5(self): return 5

# Only use the deepest level - test if it properly tracks inheritance
deep_instance = Level5()
result = deep_instance.method_level3()  # Uses level 3 method

# =============================================================================
# COMPLEX REFERENCE CHAINS
# =============================================================================

def function_a():
    """Function A calls B."""
    return function_b()

def function_b():
    """Function B calls C."""
    return function_c()

def function_c():
    """Function C calls D."""
    return function_d()

def function_d():
    """Function D is the end of chain."""
    return "end"

def function_e():
    """Function E is unused and breaks the chain."""
    return function_f()

def function_f():
    """Function F is also unused."""
    return "unused chain"

# Only call the first function - test chain tracking
chain_result = function_a()

# =============================================================================
# CIRCULAR REFERENCES
# =============================================================================

def circular_a():
    """Function A in circular reference."""
    return circular_b()

def circular_b():
    """Function B in circular reference."""
    return circular_a()

# Circular functions that are never actually called
# Should be detected as dead code

# =============================================================================
# NESTED FUNCTION DEFINITIONS
# =============================================================================

def outer_function():
    """Outer function with nested definitions."""
    
    def nested_used():
        """Nested function that is used."""
        return "nested used"
    
    def nested_unused():
        """Nested function that is unused."""
        return "nested unused"
    
    # Only use one nested function
    return nested_used()

# Call outer function
nested_result = outer_function()

# =============================================================================
# LAMBDA AND FUNCTIONAL PATTERNS
# =============================================================================

# Used lambda
used_lambda = lambda x: x * 2
lambda_result = used_lambda(5)

# Unused lambda
unused_lambda = lambda x: x * 3  # Should be detected as unused

# Complex functional patterns
def functional_processor():
    """Function using functional patterns."""
    
    def mapper(x):
        return x * 2
    
    def filter_func(x):
        return x > 5
    
    def unused_reducer(acc, x):
        """Unused reducer function."""
        return acc + x
    
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    mapped = list(map(mapper, data))
    filtered = list(filter(filter_func, mapped))
    
    return filtered

functional_result = functional_processor()

# =============================================================================
# CLASS METHOD AND STATIC METHOD PATTERNS
# =============================================================================

class MethodTestClass:
    """Class testing different method types."""
    
    class_var = "shared"
    
    def instance_method_used(self):
        """Used instance method."""
        return "instance used"
    
    def instance_method_unused(self):
        """Unused instance method."""
        return "instance unused"
    
    @classmethod
    def class_method_used(cls):
        """Used class method."""
        return cls.class_var
    
    @classmethod
    def class_method_unused(cls):
        """Unused class method."""
        return "class unused"
    
    @staticmethod
    def static_method_used():
        """Used static method."""
        return "static used"
    
    @staticmethod
    def static_method_unused():
        """Unused static method."""
        return "static unused"

# Use only some methods
method_instance = MethodTestClass()
instance_result = method_instance.instance_method_used()
class_result = MethodTestClass.class_method_used()
static_result = MethodTestClass.static_method_used()

# =============================================================================
# PROPERTY PATTERNS
# =============================================================================

class PropertyTestClass:
    """Class testing property patterns."""
    
    def __init__(self):
        self._used_value = "used"
        self._unused_value = "unused"
    
    @property
    def used_property(self):
        """Property that is accessed."""
        return self._used_value
    
    @used_property.setter
    def used_property(self, value):
        """Setter that is used."""
        self._used_value = value
    
    @property
    def unused_property(self):
        """Property that is never accessed."""
        return self._unused_value
    
    @unused_property.setter
    def unused_property(self, value):
        """Setter that is never used."""
        self._unused_value = value

# Use only some properties
prop_instance = PropertyTestClass()
prop_value = prop_instance.used_property
prop_instance.used_property = "new value"

# =============================================================================
# EXCEPTION HANDLING PATTERNS
# =============================================================================

def function_in_try():
    """Function called in try block."""
    return "try result"

def function_in_except():
    """Function called in except block."""
    return "except result"

def function_in_finally():
    """Function called in finally block."""
    return "finally result"

def unused_exception_function():
    """Function in exception context that's never reached."""
    return "never reached"

# Exception handling usage
try:
    result = function_in_try()
except Exception:
    result = function_in_except()
finally:
    function_in_finally()

# =============================================================================
# GENERATOR AND ITERATOR PATTERNS
# =============================================================================

def used_generator():
    """Generator that is used."""
    for i in range(5):
        yield i

def unused_generator():
    """Generator that is never used."""
    for i in range(5):
        yield i * 2

# Use only one generator
gen_result = list(used_generator())

# =============================================================================
# CONTEXT MANAGER PATTERNS
# =============================================================================

class UsedContextManager:
    """Context manager that is used."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class UnusedContextManager:
    """Context manager that is never used."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Use only one context manager
with UsedContextManager() as cm:
    pass
