"""
Module B that imports from Module A, completing the circular dependency.
This should be detected by the circular dependency detector.
"""

from module_a import ModuleA, helper_function_a


class ModuleB:
    """Class that depends on ModuleA"""
    
    def __init__(self):
        self.name = "ModuleB"
        # Avoid actual circular instantiation but keep the import dependency
        # self.module_a = ModuleA()
    
    def transform(self, data):
        """Transform data using ModuleA functionality"""
        # Dependency on module_a
        module_a = ModuleA()
        a_result = module_a.process_data_a(data)
        return f"ModuleB transformed: {a_result}"
    
    def process_with_helper(self, value):
        """Process using helper from module_a"""
        # Another dependency on module_a
        return helper_function_a(value) * 2


def process_data_b(data):
    """Function that creates dependency on ModuleA"""
    from module_a import ModuleA
    processor = ModuleA()
    return processor.process_data_a(data)


def helper_function_b(value):
    """Helper function that depends on module_a"""
    from module_a import CONSTANT_A
    return value + CONSTANT_A


# Module level dependency
from module_a import CONSTANT_A

CONSTANT_B = CONSTANT_A - 50
