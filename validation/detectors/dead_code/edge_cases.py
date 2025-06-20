"""
Dead Code Detector Validation

This module contains edge cases and boundary conditions for testing the dead code detector.
Focus areas:
- True positives: Code that is genuinely unused
- False positives: Code that appears unused but is actually used
- Boundary cases: Dynamic imports, reflection, entry points
"""

# =============================================================================
# TRUE POSITIVES - Should be detected as dead code
# =============================================================================

def unused_function():
    """This function is never called and should be detected as dead code."""
    return "unused"

class UnusedClass:
    """This class is never instantiated and should be detected as dead code."""
    
    def method_in_unused_class(self):
        return "also unused"

# Unused variable
UNUSED_CONSTANT = "this constant is never referenced"

def function_with_unused_locals():
    """Function with unused local variables."""
    used_var = "this is used"
    unused_var = "this is not used"  # Should be detected
    another_unused = 42  # Should be detected
    return used_var

# Unused import (if not used elsewhere)
import json  # May be unused if not referenced

def function_returning_unused_value():
    """Function that returns something but return value is never used."""
    return "unused return value"

# Call the function but don't use return value
function_returning_unused_value()

# =============================================================================
# FALSE POSITIVES - Should NOT be detected as dead code
# =============================================================================

def used_function():
    """This function is used and should not be detected as dead code."""
    return "used"

# This function is used
result = used_function()

class UsedClass:
    """This class is used and should not be detected."""
    
    def __init__(self):
        self.value = "initialized"
    
    def used_method(self):
        return self.value

# This class is instantiated
instance = UsedClass()
method_result = instance.used_method()

# Used constant
USED_CONSTANT = "this constant is referenced"
constant_reference = USED_CONSTANT

# =============================================================================
# BOUNDARY CASES - Edge cases that might confuse the detector
# =============================================================================

def conditionally_used_function():
    """Function used in conditional code - should not be detected as dead."""
    return "conditionally used"

# Conditional usage
import random
if random.random() > 0.5:
    conditionally_used_function()

def function_used_in_lambda():
    """Function used in lambda - should not be detected as dead."""
    return "lambda usage"

# Usage in lambda
lambda_func = lambda: function_used_in_lambda()

def function_used_in_comprehension():
    """Function used in list comprehension - should not be detected as dead."""
    return "comprehension usage"

# Usage in comprehension
comprehension_result = [function_used_in_comprehension() for _ in range(1)]

def function_used_as_argument():
    """Function passed as argument - should not be detected as dead."""
    return "argument usage"

def higher_order_function(func):
    """Function that takes another function as argument."""
    return func()

# Usage as argument
higher_order_result = higher_order_function(function_used_as_argument)

# =============================================================================
# DYNAMIC USAGE PATTERNS - Challenging cases for static analysis
# =============================================================================

def dynamically_called_function():
    """Function called via getattr - static analysis might miss this."""
    return "dynamic call"

# Dynamic call via getattr
import sys
current_module = sys.modules[__name__]
if hasattr(current_module, 'dynamically_called_function'):
    getattr(current_module, 'dynamically_called_function')()

def function_called_via_string():
    """Function called using string name - very hard to detect statically."""
    return "string call"

# Call via string evaluation
function_name = "function_called_via_string"
if function_name in globals():
    globals()[function_name]()

class DynamicallyUsedClass:
    """Class instantiated dynamically."""
    
    def dynamic_method(self):
        return "dynamic"

# Dynamic instantiation
class_name = "DynamicallyUsedClass"
if class_name in globals():
    dynamic_instance = globals()[class_name]()

# =============================================================================
# INHERITANCE AND POLYMORPHISM
# =============================================================================

class BaseClass:
    """Base class that might appear unused if only subclasses are used."""
    
    def base_method(self):
        return "base"

class DerivedClass(BaseClass):
    """Derived class that uses base class."""
    
    def derived_method(self):
        return "derived"

# Only derived class is directly instantiated
derived = DerivedClass()
base_result = derived.base_method()  # Uses base class method

# =============================================================================
# DECORATOR PATTERNS
# =============================================================================

def decorator_function(func):
    """Decorator that might appear unused if only used as @decorator."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@decorator_function
def decorated_function():
    """Function using the decorator."""
    return "decorated"

# Use the decorated function
decorated_result = decorated_function()

# =============================================================================
# MODULE-LEVEL EXECUTION
# =============================================================================

def main():
    """Main function that serves as entry point."""
    print("Main function executed")
    return 0

# Entry point usage
if __name__ == "__main__":
    main()

# =============================================================================
# PROPERTY AND DESCRIPTOR USAGE
# =============================================================================

class PropertyUser:
    """Class using properties that might confuse dead code detection."""
    
    def __init__(self):
        self._value = "initial"
    
    @property
    def value(self):
        """Property getter that might appear unused."""
        return self._value
    
    @value.setter
    def value(self, new_value):
        """Property setter that might appear unused."""
        self._value = new_value

# Property usage
prop_instance = PropertyUser()
prop_value = prop_instance.value  # Uses getter
prop_instance.value = "new"       # Uses setter

# =============================================================================
# METACLASS AND ADVANCED PATTERNS
# =============================================================================

class MetaClass(type):
    """Metaclass that might appear unused."""
    
    def __new__(cls, name, bases, attrs):
        return super().__new__(cls, name, bases, attrs)

class ClassWithMeta(metaclass=MetaClass):
    """Class using metaclass."""
    pass

# Metaclass is used through the class definition
meta_instance = ClassWithMeta()

# =============================================================================
# CALLBACK AND EVENT PATTERNS
# =============================================================================

# Callback registry
callbacks = []

def register_callback(func):
    """Register a callback function."""
    callbacks.append(func)
    return func

@register_callback
def callback_function():
    """Callback that's registered but might appear unused."""
    return "callback"

def trigger_callbacks():
    """Trigger all registered callbacks."""
    return [cb() for cb in callbacks]

# Trigger callbacks (uses callback_function indirectly)
callback_results = trigger_callbacks()
