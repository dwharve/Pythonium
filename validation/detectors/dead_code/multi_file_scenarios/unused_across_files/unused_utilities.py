"""
Utilities module with both used and unused code.
Some functions/classes are imported by main.py, others are not.
"""


def used_function(data):
    """This function is imported and used by main.py"""
    return f"Processed: {data}"


def unused_function(data):
    """This function is never imported or used - should be detected as dead code"""
    return f"Unused processing: {data}"


def another_unused_function():
    """Another unused function - should be detected as dead code"""
    return "This is never called"


class UsedClass:
    """This class is imported and used by main.py"""
    
    def __init__(self):
        self.data = "used data"
    
    def process(self):
        """This method is called"""
        return f"Processing: {self.data}"
    
    def transform(self, data):
        """This method is also called"""
        return f"Transformed: {data}"
    
    def unused_method(self):
        """This method is never called - should be detected as dead code"""
        return "This method is unused"


class UnusedClass:
    """This class is never imported or used - should be detected as dead code"""
    
    def __init__(self):
        self.value = "unused"
    
    def method_one(self):
        """Unused method in unused class"""
        return "unused method one"
    
    def method_two(self):
        """Another unused method in unused class"""
        return "unused method two"


class PartiallyUsedClass:
    """This class is never imported but has some internal usage"""
    
    def __init__(self):
        self.helper = UnusedHelper()
    
    def public_method(self):
        """Public method that's never called externally"""
        return self.helper.help()
    
    def another_public_method(self):
        """Another public method that's never called"""
        return "not used"


class UnusedHelper:
    """Helper class used only by PartiallyUsedClass"""
    
    def help(self):
        return "helping"


# Constants
USED_CONSTANT = "This constant is imported and used"
UNUSED_CONSTANT = "This constant is never imported or used"
INTERNAL_CONSTANT = "This constant is only used within this file"


# Functions that use internal constants
def internal_function():
    """Function that uses internal constant but is never called externally"""
    return f"Internal: {INTERNAL_CONSTANT}"


def completely_isolated_function():
    """Function that has no external usage and no internal usage"""
    return "completely isolated"


# Variable that's never used
unused_variable = "This variable is never referenced"


# Complex unused code
def complex_unused_function(param1, param2, *args, **kwargs):
    """Complex function signature that's never used"""
    result = []
    for arg in args:
        if isinstance(arg, str):
            result.append(arg.upper())
        else:
            result.append(str(arg))
    
    for key, value in kwargs.items():
        result.append(f"{key}={value}")
    
    return param1 + param2 + " ".join(result)


# Decorator that's never used
def unused_decorator(func):
    """Decorator that's never applied to any function"""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
