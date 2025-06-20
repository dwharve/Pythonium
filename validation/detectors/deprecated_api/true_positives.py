"""
True positive cases for deprecated API detector.
These contain usage of deprecated APIs that should be detected.
"""

import warnings

# Case 1: Functions with deprecation warnings
def old_function(x, y):
    """Deprecated function with warning"""
    warnings.warn("old_function is deprecated, use new_function instead", 
                  DeprecationWarning, stacklevel=2)
    return x + y

def legacy_calculation(data):
    """Another deprecated function"""
    warnings.warn("legacy_calculation will be removed in version 2.0", 
                  FutureWarning, stacklevel=2)
    return sum(data) / len(data)

@warnings.deprecated  # If this decorator exists
def outdated_method(value):
    """Method marked with deprecation decorator"""
    return value * 2

# Case 2: Classes with deprecated methods
class LegacyClass:
    """Class with deprecated methods"""
    
    def __init__(self):
        self.data = []
    
    def add_item(self, item):
        """Deprecated method"""
        warnings.warn("add_item is deprecated, use append instead", 
                      DeprecationWarning, stacklevel=2)
        self.data.append(item)
    
    def get_size(self):
        """Deprecated getter"""
        warnings.warn("get_size is deprecated, use len(obj) instead", 
                      DeprecationWarning, stacklevel=2)
        return len(self.data)

# Case 3: Deprecated API usage patterns
def uses_deprecated_apis():
    """Function that uses deprecated APIs"""
    # Using deprecated function
    result1 = old_function(5, 3)
    
    # Using deprecated class method
    legacy = LegacyClass()
    legacy.add_item("test")
    size = legacy.get_size()
    
    # Using deprecated calculation
    data = [1, 2, 3, 4, 5]
    avg = legacy_calculation(data)
    
    return result1, size, avg

# Case 4: Deprecated imports and modules
try:
    import imp  # Deprecated module
    has_imp = True
except ImportError:
    has_imp = False

try:
    from distutils import sysconfig  # Deprecated module
    has_distutils = True
except ImportError:
    has_distutils = False

# Case 5: Deprecated standard library usage
import platform

def deprecated_platform_usage():
    """Using deprecated platform methods"""
    # platform.dist() is deprecated
    try:
        dist_info = platform.dist()  # Deprecated
    except AttributeError:
        dist_info = None
    
    # platform.linux_distribution() is deprecated
    try:
        linux_info = platform.linux_distribution()  # Deprecated
    except AttributeError:
        linux_info = None
    
    return dist_info, linux_info

# Case 6: Deprecated string methods
def deprecated_string_methods():
    """Using deprecated string methods"""
    text = "Hello World"
    
    # String formatting with % (considered deprecated)
    formatted1 = "Hello %s" % "World"  # Old style formatting
    
    # Using deprecated string methods if any exist
    # Most string methods are stable, but some patterns are discouraged
    return formatted1

# Case 7: Deprecated file operations
def deprecated_file_operations():
    """Using deprecated file operation patterns"""
    import os
    
    # os.path.walk is deprecated (use os.walk instead)
    # This is just an example - os.path.walk doesn't exist in Python 3
    
    # Using deprecated file modes or operations
    try:
        # Example of potentially deprecated file operation pattern
        with open("test.txt", "U") as f:  # Universal newlines mode deprecated
            content = f.read()
    except ValueError:
        content = None
    
    return content

# Case 8: Deprecated exception handling patterns
def deprecated_exception_patterns():
    """Using deprecated exception handling"""
    try:
        # Old-style exception handling (Python 2 style)
        # raise "String exception"  # This would be deprecated/invalid
        
        # Using deprecated exception types
        result = 1 / 0
    except ZeroDivisionError as e:
        # Standard exception handling - this is fine
        # But accessing deprecated attributes might not be
        error_msg = str(e)
    
    return error_msg

# Case 9: Deprecated configuration patterns
class DeprecatedConfig:
    """Configuration class using deprecated patterns"""
    
    def __init__(self):
        # Using deprecated configuration loading
        self.load_config_old_way()
    
    def load_config_old_way(self):
        """Deprecated configuration loading"""
        warnings.warn("load_config_old_way is deprecated, use load_config instead", 
                      DeprecationWarning, stacklevel=2)
        self.settings = {"debug": True, "port": 8080}
    
    def get_setting(self, key):
        """Deprecated getter pattern"""
        warnings.warn("get_setting is deprecated, access settings directly", 
                      DeprecationWarning, stacklevel=2)
        return self.settings.get(key)

# Case 10: Deprecated utility functions
def deprecated_utilities():
    """Collection of deprecated utility functions"""
    
    def old_string_join(items, separator):
        """Deprecated string joining method"""
        warnings.warn("old_string_join is deprecated, use str.join instead", 
                      DeprecationWarning, stacklevel=2)
        result = ""
        for i, item in enumerate(items):
            if i > 0:
                result += separator
            result += str(item)
        return result
    
    def old_list_filter(items, condition):
        """Deprecated filtering method"""
        warnings.warn("old_list_filter is deprecated, use list comprehension instead", 
                      DeprecationWarning, stacklevel=2)
        result = []
        for item in items:
            if condition(item):
                result.append(item)
        return result
    
    # Usage of deprecated utilities
    items = ["a", "b", "c"]
    joined = old_string_join(items, ",")
    
    numbers = [1, 2, 3, 4, 5]
    filtered = old_list_filter(numbers, lambda x: x > 3)
    
    return joined, filtered

# Case 11: Deprecated database patterns
class DeprecatedDatabase:
    """Database class with deprecated methods"""
    
    def __init__(self):
        self.connection = None
    
    def execute_sql(self, sql, params=None):
        """Deprecated SQL execution method"""
        warnings.warn("execute_sql is deprecated, use execute_query instead", 
                      DeprecationWarning, stacklevel=2)
        # Simulate SQL execution
        return f"Executed: {sql} with {params}"
    
    def fetch_all(self, sql):
        """Deprecated fetch method"""
        warnings.warn("fetch_all is deprecated, use query_all instead", 
                      DeprecationWarning, stacklevel=2)
        return [{"id": 1, "name": "test"}]

# Case 12: Deprecated async patterns
import asyncio

async def deprecated_async_function():
    """Function using deprecated async patterns"""
    
    # Using deprecated asyncio functions
    try:
        # asyncio.coroutine decorator is deprecated
        @asyncio.coroutine
        def old_coroutine():
            yield from asyncio.sleep(1)
            return "done"
        
        result = await old_coroutine()
    except AttributeError:
        # Handle case where decorator doesn't exist
        result = "deprecated pattern not available"
    
    return result

# Case 13: Deprecated testing patterns
class DeprecatedTestUtils:
    """Testing utilities with deprecated methods"""
    
    def assert_equal_old(self, a, b):
        """Deprecated assertion method"""
        warnings.warn("assert_equal_old is deprecated, use assertEqual instead", 
                      DeprecationWarning, stacklevel=2)
        if a != b:
            raise AssertionError(f"{a} != {b}")
    
    def setup_test_old(self):
        """Deprecated test setup"""
        warnings.warn("setup_test_old is deprecated, use setUp instead", 
                      DeprecationWarning, stacklevel=2)
        # Setup test environment
        pass
