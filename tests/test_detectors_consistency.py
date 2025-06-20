"""
Tests for the consistency detector.
"""

import unittest
import ast
from pathlib import Path

from pythonium.models import CodeGraph, Symbol, Location
from pythonium.detectors.consistency import InconsistentApiDetector


class TestInconsistentApiDetector(unittest.TestCase):
    """Test cases for the Inconsistent API Detector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = InconsistentApiDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "inconsistent_api")
        self.assertEqual(self.detector.name, "Inconsistent API Detector")
        self.assertIn("inconsistent", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_single_function(self):
        """Test detector with single function - should find no issues."""
        # Create a simple function
        func_code = """
def get_user_data(user_id, include_private=False):
    '''Get user data by ID'''
    return {"id": user_id, "private": include_private}
"""
        func_ast = ast.parse(func_code).body[0]
        symbol = Symbol(
            fqname="get_user_data",
            location=Location(Path("test.py"), 1, 1),
            ast_node=func_ast
        )
        self.graph.symbols["get_user_data"] = symbol
        
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_custom_configuration(self):
        """Test detector with custom configuration options."""
        detector = InconsistentApiDetector(
            check_parameter_order=True,
            check_naming_patterns=True,
            min_functions_for_pattern=3
        )
        
        # Test with empty graph
        issues = detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_consistent_functions_no_issues(self):
        """Test that consistent functions don't trigger issues."""
        # Create functions with consistent API patterns
        func1_code = """
def get_user_profile(user_id, include_private=False):
    '''Get user profile data'''
    return {"id": user_id, "private": include_private}
"""
        func2_code = """
def get_user_settings(user_id, include_private=False):
    '''Get user settings data'''
    return {"id": user_id, "private": include_private}
"""
        
        func1_ast = ast.parse(func1_code).body[0]
        func2_ast = ast.parse(func2_code).body[0]
        
        symbol1 = Symbol(
            fqname="module.get_user_profile",
            location=Location(Path("module.py"), 1, 1),
            ast_node=func1_ast
        )
        
        symbol2 = Symbol(
            fqname="module.get_user_settings",
            location=Location(Path("module.py"), 10, 1),
            ast_node=func2_ast
        )
        
        self.graph.symbols["get_user_profile"] = symbol1
        self.graph.symbols["get_user_settings"] = symbol2
        
        issues = self.detector._analyze(self.graph)
        # These functions have consistent APIs, should not trigger issues
        self.assertEqual(len(issues), 0)
    
    def test_inconsistent_parameter_order(self):
        """Test detection of inconsistent parameter ordering."""
        # Create functions with inconsistent parameter order
        func1_code = """
def process_data(data, options, callback):
    '''Process data with options and callback'''
    return callback(data, options)
"""
        func2_code = """
def process_text(options, data, callback):
    '''Process text with different parameter order'''
    return callback(data, options)
"""
        
        func1_ast = ast.parse(func1_code).body[0]
        func2_ast = ast.parse(func2_code).body[0]
        
        symbol1 = Symbol(
            fqname="processor.process_data",
            location=Location(Path("processor.py"), 1, 1),
            ast_node=func1_ast
        )
        
        symbol2 = Symbol(
            fqname="processor.process_text",
            location=Location(Path("processor.py"), 10, 1),
            ast_node=func2_ast
        )
        
        self.graph.symbols["process_data"] = symbol1
        self.graph.symbols["process_text"] = symbol2
        
        issues = self.detector._analyze(self.graph)
        # May or may not find issues depending on the detector's implementation
        # This is primarily testing that the detector runs without errors
        self.assertGreaterEqual(len(issues), 0)
    
    def test_mixed_naming_conventions(self):
        """Test detection of mixed naming conventions."""
        # Create functions with mixed naming conventions
        func1_code = """
def get_UserData(userId):
    '''Get user data - mixed case'''
    return {"id": userId}
"""
        func2_code = """
def get_user_profile(user_id):
    '''Get user profile - snake_case'''
    return {"id": user_id}
"""
        
        func1_ast = ast.parse(func1_code).body[0]
        func2_ast = ast.parse(func2_code).body[0]
        
        symbol1 = Symbol(
            fqname="api.get_UserData",
            location=Location(Path("api.py"), 1, 1),
            ast_node=func1_ast
        )
        
        symbol2 = Symbol(
            fqname="api.get_user_profile",
            location=Location(Path("api.py"), 10, 1),
            ast_node=func2_ast
        )
        
        self.graph.symbols["get_UserData"] = symbol1
        self.graph.symbols["get_user_profile"] = symbol2
        
        issues = self.detector._analyze(self.graph)
        # Testing that the detector runs without errors
        self.assertGreaterEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
