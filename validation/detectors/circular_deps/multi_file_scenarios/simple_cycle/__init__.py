"""
Init file for simple cycle scenario.
This makes it a proper Python package.
"""

# Export main classes to make the circular dependency more obvious
from .module_a import ModuleA
from .module_b import ModuleB

__all__ = ['ModuleA', 'ModuleB']
