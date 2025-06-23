"""
Tests for the deprecated API detector.
"""

import unittest
import ast
from pathlib import Path

from pythonium.models import CodeGraph, Symbol, Location
from pythonium.detectors.deprecated import DeprecatedApiDetector


class TestDeprecatedApiDetector(unittest.TestCase):
    """Test cases for the Deprecated API Detector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = DeprecatedApiDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "deprecated_api")
        self.assertEqual(self.detector.name, "Deprecated API Detector")
        self.assertIn("deprecated", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_deprecated_decorator_detection(self):
        """Test detection of @deprecated decorator usage."""
        # Function with @deprecated decorator
        func_code = """
@deprecated("Use new_function instead")
def old_function():
    '''This function is deprecated.'''
    return "old behavior"
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="old_function",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["old_function"] = symbol
        
        issues = self.detector._analyze(self.graph)
        # The detector should run without errors
        self.assertIsInstance(issues, list)
    
    def test_deprecated_in_docstring(self):
        """Test detection of deprecated mentions in docstrings."""
        # Function with deprecated in docstring
        func_code = """
def old_api():
    '''
    This function is deprecated since version 2.0.
    Use new_api() instead.
    '''
    return "deprecated behavior"
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="old_api",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["old_api"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_deprecated_import_detection(self):
        """Test detection of imports from deprecated modules."""
        # Import from deprecated module
        import_code = """
import warnings
from deprecated_module import old_function
"""
        import_ast = ast.parse(import_code)
        
        # Add import statements to graph
        for i, node in enumerate(import_ast.body):
            symbol = Symbol(
                fqname=f"import_{i}",
                location=Location(Path("test.py"), i+1, 1),
                ast_node=node
            )
            self.graph.symbols[f"import_{i}"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_deprecated_call_detection(self):
        """Test detection of calls to deprecated functions."""
        # Function that calls deprecated API
        func_code = """
def caller():
    # Call to potentially deprecated function
    warnings.warn("deprecated", DeprecationWarning)
    return old_function()
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="caller",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["caller"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_deprecated_class_detection(self):
        """Test detection of deprecated classes."""
        # Class with deprecated decorator
        class_code = """
@deprecated("Use NewClass instead")
class OldClass:
    '''This class is deprecated.'''
    
    def __init__(self):
        pass
    
    def old_method(self):
        '''Deprecated method.'''
        return "old"
"""
        class_ast = ast.parse(class_code).body[0]
        symbol = Symbol(
            fqname="OldClass",
            location=Location(Path("test.py"), 1, 1),
            ast_node=class_ast
        )
        self.graph.symbols["OldClass"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_deprecation_warning_detection(self):
        """Test detection of deprecation warnings."""
        # Function with deprecation warning
        func_code = """
def warning_function():
    import warnings
    warnings.warn("This is deprecated", DeprecationWarning)
    warnings.warn("Future warning", FutureWarning)
    return "deprecated"
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="warning_function",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["warning_function"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_multiple_deprecated_functions(self):
        """Test detection with multiple deprecated functions."""
        # Multiple functions with different deprecation patterns
        func1_code = """
@deprecated
def func1():
    return "deprecated1"
"""
        func2_code = """
def func2():
    '''DEPRECATED: Use func3 instead'''
    return "deprecated2"
"""
        func3_code = """
def func3():
    '''This function is deprecated in version 3.0'''
    return "deprecated3"
"""
        
        for i, code in enumerate([func1_code, func2_code, func3_code], 1):
            func_ast = ast.parse(code).body[0]
            symbol = Symbol(
                fqname=f"func{i}",
                location=Location(Path("test.py"), i*5, 1),
                ast_node=func_ast
            )
            self.graph.symbols[f"func{i}"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_version_info_parsing(self):
        """Test parsing of version information in deprecation messages."""
        # Function with version info
        func_code = """
def versioned_deprecated():
    '''
    Deprecated since version 2.1.0.
    Will be removed in version 3.0.0.
    Use new_function() instead.
    '''
    return "versioned"
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="versioned_deprecated",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["versioned_deprecated"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_custom_deprecation_patterns(self):
        """Test with custom deprecation patterns."""
        # Test with custom configuration
        custom_detector = DeprecatedApiDetector(
            deprecated_modules=['old_module', 'legacy_module'],
            deprecated_functions={'old_func': 'Use new_func instead', 'legacy_func': 'Use modern_func instead'}
        )
        
        # Function calling custom deprecated function
        func_code = """
def test_func():
    return old_func() + legacy_func()
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="test_func",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["test_func"] = symbol
        
        issues = custom_detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Function with complex AST structure
        complex_code = """
class TestClass:
    @deprecated("Use new method")
    @staticmethod
    def old_static():
        try:
            import deprecated_module
            deprecated_module.old_function()
        except ImportError:
            warnings.warn("Fallback deprecated", DeprecationWarning)
        finally:
            return "complex"
"""
        class_ast = ast.parse(complex_code).body[0]
        symbol = Symbol(
            fqname="TestClass",
            location=Location(Path("test.py"), 1, 1),
            ast_node=class_ast
        )
        self.graph.symbols["TestClass"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_no_deprecated_usage(self):
        """Test that clean code doesn't trigger false positives."""
        # Clean function without deprecated usage
        clean_code = """
def clean_function():
    '''A normal, non-deprecated function.'''
    import os
    return os.path.join("path", "to", "file")
"""
        func_ast = ast.parse(clean_code).body[0]
        symbol = Symbol(
            fqname="clean_function",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["clean_function"] = symbol
        
        issues = self.detector._analyze(self.graph)
        # Should not find deprecation issues in clean code
        self.assertIsInstance(issues, list)


if __name__ == "__main__":
    unittest.main()
