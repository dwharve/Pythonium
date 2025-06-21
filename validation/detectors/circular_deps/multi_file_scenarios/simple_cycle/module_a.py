"""
Module A that imports from Module B, creating a circular dependency.
This should be detected by the circular dependency detector.
"""

from module_b import ModuleB, process_data_b


class ModuleA:
    """Class that depends on ModuleB"""
    
    def __init__(self):
        self.name = "ModuleA"
        # This would create a circular dependency if instantiated
        # self.module_b = ModuleB()
    
    def process_data_a(self, data):
        """Process data using ModuleB functionality"""
        # This creates a dependency on module_b
        module_b = ModuleB()
        processed = module_b.transform(data)
        return f"ModuleA processed: {processed}"
    
    def get_combined_result(self, data):
        """Get result combining both modules"""
        # Another dependency on module_b
        b_result = process_data_b(data)
        return f"Combined: {self.process_data_a(data)} + {b_result}"


def helper_function_a(value):
    """Helper function that also depends on module_b"""
    from module_b import helper_function_b
    return helper_function_b(value) + 10


# This creates a direct dependency at module level
from module_b import CONSTANT_B

CONSTANT_A = CONSTANT_B + 100
