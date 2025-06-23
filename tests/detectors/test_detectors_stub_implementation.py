"""
Tests for the Stub Implementation Detector

This module contains comprehensive test cases for the StubImplementationDetector class,
ensuring it correctly identifies stub, mock, fake, simulated, and fallback implementations
in Python code.

Test coverage includes:
- Detection of naming patterns (stub, mock, fake, etc.)
- Minimal implementations (pass, return None)
- NotImplementedError raises
- TODO/FIXME comments
- Hardcoded return values
- Testing decorators
- Class naming patterns
- Edge cases and configuration options
"""

import ast
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, mock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pythonium.detectors.stub_implementation import StubImplementationDetector
from pythonium.models import CodeGraph, Symbol, Location


class TestStubImplementationDetector(TestCase):
    """
    Test cases for the StubImplementationDetector class.
    
    This test suite verifies that the stub implementation detector correctly identifies
    various types of stub, mock, fake, and placeholder implementations.
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.detector = StubImplementationDetector()
        self.graph = CodeGraph()
    
    def _create_mock_symbol(self, name, ast_node, file_path="test.py", line=1, end_line=None):
        """
        Helper method to create a mock symbol for testing.
        
        Args:
            name: Fully qualified symbol name
            ast_node: Associated AST node
            file_path: Source file path for the symbol
            line: Line number where symbol is defined
            end_line: End line number for the symbol
            
        Returns:
            Symbol instance for testing
        """
        location = Location(
            file=Path(file_path),
            line=line,
            end_line=end_line or line
        )
        return Symbol(fqname=name, ast_node=ast_node, location=location)
    
    def test_stub_naming_patterns(self):
        """Test detection of stub-like naming patterns."""
        # Create function with stub name
        code = "def stub_user_service(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.stub_user_service", func_node)
        
        self.graph.symbols = {"test.stub_user_service": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect stub naming pattern
        naming_issues = [i for i in issues if i.id == "stub_implementation.stub_naming"]
        self.assertEqual(len(naming_issues), 1)
        self.assertIn("stub", naming_issues[0].message.lower())
    
    def test_mock_naming_patterns(self):
        """Test detection of mock-like naming patterns."""
        # Create function with mock name
        code = "def mock_payment_processor(): return {'status': 'success'}"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.mock_payment_processor", func_node)
        
        self.graph.symbols = {"test.mock_payment_processor": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect mock naming pattern
        naming_issues = [i for i in issues if i.id == "stub_implementation.stub_naming"]
        self.assertEqual(len(naming_issues), 1)
        self.assertIn("mock", naming_issues[0].message.lower())
    
    def test_fake_naming_patterns(self):
        """Test detection of fake-like naming patterns."""
        # Create function with fake name
        code = "def get_data_fake(): return []"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.get_data_fake", func_node)
        
        self.graph.symbols = {"test.get_data_fake": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect fake naming pattern
        naming_issues = [i for i in issues if i.id == "stub_implementation.stub_naming"]
        self.assertEqual(len(naming_issues), 1)
        self.assertIn("fake", naming_issues[0].message.lower())
    
    def test_class_stub_naming_patterns(self):
        """Test detection of stub-like class naming patterns."""
        # Create class with dummy name
        code = "class DummyEmailService: pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        symbol = self._create_mock_symbol("test.DummyEmailService", class_node)
        
        self.graph.symbols = {"test.DummyEmailService": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect class stub naming pattern
        naming_issues = [i for i in issues if i.id == "stub_implementation.stub_class_naming"]
        self.assertEqual(len(naming_issues), 1)
        self.assertIn("dummy", naming_issues[0].message.lower())
    
    def test_minimal_pass_implementation(self):
        """Test detection of minimal pass implementations."""
        # Create function with only pass
        code = "def empty_function(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.empty_function", func_node)
        
        self.graph.symbols = {"test.empty_function": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect minimal pass implementation
        pass_issues = [i for i in issues if i.id == "stub_implementation.minimal_pass_implementation"]
        self.assertEqual(len(pass_issues), 1)
        self.assertIn("pass", pass_issues[0].message.lower())
    
    def test_minimal_return_none_implementation(self):
        """Test detection of minimal return None implementations."""
        # Create function that only returns None
        code = "def empty_function(): return None"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.empty_function", func_node)
        
        self.graph.symbols = {"test.empty_function": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect minimal return None implementation
        return_issues = [i for i in issues if i.id == "stub_implementation.minimal_return_none"]
        self.assertEqual(len(return_issues), 1)
        self.assertIn("returns none", return_issues[0].message.lower())
    
    def test_not_implemented_error(self):
        """Test detection of NotImplementedError raises."""
        # Create function that raises NotImplementedError
        code = "def incomplete_function(): raise NotImplementedError('TODO: implement this')"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.incomplete_function", func_node)
        
        self.graph.symbols = {"test.incomplete_function": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect NotImplementedError
        not_impl_issues = [i for i in issues if i.id == "stub_implementation.not_implemented_error"]
        self.assertEqual(len(not_impl_issues), 1)
        self.assertIn("notimplementederror", not_impl_issues[0].message.lower())
    
    def test_hardcoded_return_values(self):
        """Test detection of hardcoded return values."""
        # Create function with hardcoded return
        code = "def get_status(): return 'success'"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.get_status", func_node)
        
        self.graph.symbols = {"test.get_status": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect hardcoded return
        hardcoded_issues = [i for i in issues if i.id == "stub_implementation.hardcoded_return"]
        self.assertEqual(len(hardcoded_issues), 1)
        self.assertIn("hardcoded", hardcoded_issues[0].message.lower())
    
    def test_empty_list_return(self):
        """Test detection of empty list returns."""
        # Create function that returns empty list
        code = "def get_items(): return []"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.get_items", func_node)
        
        self.graph.symbols = {"test.get_items": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect hardcoded empty list return
        hardcoded_issues = [i for i in issues if i.id == "stub_implementation.hardcoded_return"]
        self.assertEqual(len(hardcoded_issues), 1)
        self.assertIn("[]", hardcoded_issues[0].message)
    
    def test_empty_dict_return(self):
        """Test detection of empty dict returns."""
        # Create function that returns empty dict
        code = "def get_config(): return {}"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.get_config", func_node)
        
        self.graph.symbols = {"test.get_config": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect hardcoded empty dict return
        hardcoded_issues = [i for i in issues if i.id == "stub_implementation.hardcoded_return"]
        self.assertEqual(len(hardcoded_issues), 1)
        self.assertIn("{}", hardcoded_issues[0].message)
    
    def test_testing_decorators(self):
        """Test detection of testing-related decorators."""
        # Create function with mock decorator
        code = "@mock.patch('module')\ndef test_function(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.test_function", func_node)
        
        self.graph.symbols = {"test.test_function": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect testing decorator
        decorator_issues = [i for i in issues if i.id == "stub_implementation.testing_decorator"]
        self.assertEqual(len(decorator_issues), 1)
        self.assertIn("decorator", decorator_issues[0].message.lower())
    
    def test_todo_comments_detection(self):
        """Test detection of TODO comments in function source."""
        # Create a temporary file with function and TODO comment
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def incomplete_function():\n")
            f.write("    # TODO: implement actual logic\n")
            f.write("    pass\n")
            temp_file = Path(f.name)
        
        try:
            # Create function AST
            code = "def incomplete_function(): pass"
            tree = ast.parse(code)
            func_node = tree.body[0]
            symbol = self._create_mock_symbol("test.incomplete_function", func_node, 
                                            file_path=str(temp_file), line=1, end_line=3)
            
            self.graph.symbols = {"test.incomplete_function": symbol}
            issues = self.detector._analyze(self.graph)
            
            # Should detect TODO comment
            todo_issues = [i for i in issues if i.id == "stub_implementation.todo_comment"]
            self.assertEqual(len(todo_issues), 1)
            self.assertIn("todo", todo_issues[0].message.lower())
        
        finally:
            # Clean up temporary file
            temp_file.unlink()
    
    def test_custom_stub_keywords(self):
        """Test detector with custom stub keywords."""
        # Create detector with custom keywords
        detector = StubImplementationDetector(stub_keywords=['placeholder', 'temporary'])
        
        # Create function with custom keyword
        code = "def placeholder_function(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.placeholder_function", func_node)
        
        self.graph.symbols = {"test.placeholder_function": symbol}
        issues = detector._analyze(self.graph)
        
        # Should detect custom keyword
        naming_issues = [i for i in issues if i.id == "stub_implementation.stub_naming"]
        self.assertEqual(len(naming_issues), 1)
        self.assertIn("placeholder", naming_issues[0].message.lower())
    
    def test_disabled_checks(self):
        """Test detector with disabled checks."""
        # Create detector with minimal checks disabled
        detector = StubImplementationDetector(
            check_naming_patterns=False,
            check_minimal_implementations=False
        )
        
        # Create function with stub name and minimal implementation
        code = "def stub_function(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.stub_function", func_node)
        
        self.graph.symbols = {"test.stub_function": symbol}
        issues = detector._analyze(self.graph)
        
        # Should not detect naming or minimal implementation issues
        naming_issues = [i for i in issues if i.id == "stub_implementation.stub_naming"]
        minimal_issues = [i for i in issues if i.id == "stub_implementation.minimal_pass_implementation"]
        
        self.assertEqual(len(naming_issues), 0)
        self.assertEqual(len(minimal_issues), 0)
    
    def test_complex_function_not_flagged(self):
        """Test that complex functions are not flagged for hardcoded returns."""
        # Create function with multiple statements
        code = """
def complex_function():
    x = calculate_something()
    y = process_data(x)
    return y
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.complex_function", func_node)
        
        self.graph.symbols = {"test.complex_function": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should not detect hardcoded return for complex function
        hardcoded_issues = [i for i in issues if i.id == "stub_implementation.hardcoded_return"]
        self.assertEqual(len(hardcoded_issues), 0)
    
    def test_multiple_issues_same_function(self):
        """Test detection of multiple issues in the same function."""
        # Create function with multiple stub indicators
        code = "def stub_function(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.stub_function", func_node)
        
        self.graph.symbols = {"test.stub_function": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should detect both naming and minimal implementation issues
        self.assertGreaterEqual(len(issues), 2)
        
        issue_types = {issue.id.split('.')[-1] for issue in issues}
        self.assertIn("stub_naming", issue_types)
        self.assertIn("minimal_pass_implementation", issue_types)
    
    def test_regular_function_not_flagged(self):
        """Test that regular functions are not flagged."""
        # Create normal function
        code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = self._create_mock_symbol("test.calculate_total", func_node)
        
        self.graph.symbols = {"test.calculate_total": symbol}
        issues = self.detector._analyze(self.graph)
        
        # Should not detect any stub-related issues
        self.assertEqual(len(issues), 0)
    
    def test_detector_metadata(self):
        """Test detector metadata is properly set."""
        self.assertEqual(self.detector.id, "stub_implementation")
        self.assertEqual(self.detector.name, "Stub Implementation Detector")
        self.assertIn("stub", self.detector.description.lower())
        self.assertEqual(self.detector.category, "Code Quality & Maintainability")
        self.assertEqual(self.detector.typical_severity, "warn")
        self.assertIsInstance(self.detector.stub_keywords, list)
        self.assertIn("stub", self.detector.stub_keywords)
        self.assertIn("mock", self.detector.stub_keywords)


if __name__ == '__main__':
    import unittest
    unittest.main()
