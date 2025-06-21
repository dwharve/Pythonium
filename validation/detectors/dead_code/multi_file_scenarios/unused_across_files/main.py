"""
Main module that uses some utilities but leaves others unused.
This should help test multi-file dead code detection.
"""

from .unused_utilities import (
    used_function,
    UsedClass,
    USED_CONSTANT
)

# Note: unused_function, UnusedClass, UNUSED_CONSTANT are not imported
# They should be detected as dead code by the detector


def main_function():
    """Main function that uses some imported utilities"""
    print(f"Using constant: {USED_CONSTANT}")
    
    result = used_function("test data")
    print(f"Function result: {result}")
    
    instance = UsedClass()
    instance.process()
    
    return "Main completed"


class MainProcessor:
    """Main processor that uses some utilities"""
    
    def __init__(self):
        self.processor = UsedClass()
        self.config = USED_CONSTANT
    
    def run(self):
        """Run the main processing"""
        data = used_function("processing data")
        return self.processor.transform(data)


# This function is defined but never called - should be detected as dead
def unused_main_function():
    """This function is never called"""
    return "This should be detected as dead code"


# This class is defined but never instantiated - should be detected as dead
class UnusedMainClass:
    """This class is never used"""
    
    def method(self):
        return "unused method"


# This constant is defined but never used - should be detected as dead
UNUSED_MAIN_CONSTANT = "This constant is never used"


if __name__ == "__main__":
    main_function()
    processor = MainProcessor()
    processor.run()
