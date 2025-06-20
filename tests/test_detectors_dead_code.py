"""
Tests for the Dead Code Detector

This module contains comprehensive test cases for the DeadCodeDetector class,
ensuring it correctly identifies unused functions, classes, and other symbols
while respecting entry points and ignore patterns.

Test coverage includes:
- Detection of unused functions and classes
- Handling of entry points
- Ignore patterns for test files
- Symbol reference tracking
- Edge cases and error conditions
"""

import ast
import os
import sys
from pathlib import Path
from unittest import TestCase, mock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pythonium.detectors.dead_code import DeadCodeDetector
from pythonium.models import CodeGraph, Symbol, Location


class TestDeadCodeDetector(TestCase):
    """
    Test cases for the DeadCodeDetector class.
    
    This test suite verifies that the dead code detector correctly identifies
    unused code while handling various edge cases and configuration options.
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.detector = DeadCodeDetector()
        self.graph = CodeGraph()
    
    def _create_mock_symbol(self, name, references=None, file_path="test.py", line=1):
        """
        Helper method to create a mock symbol for testing.
        
        Args:
            name: Fully qualified symbol name
            references: Set of symbols this symbol references
            file_path: Source file path for the symbol
            line: Line number where symbol is defined
            
        Returns:
            Symbol instance for testing
        """
        if references is None:
            references = set()
            
        location = Location(
            file=Path(file_path),
            line=line,
            column=0,
            end_line=line + 1,
            end_column=10
        )
        
        # Create a minimal AST node
        node = ast.FunctionDef(
            name=name.split('.')[-1],  # Use just the last part of the name
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            ),
            body=[],
            decorator_list=[],
            lineno=line,
            col_offset=0,
            end_lineno=line + 1,
            end_col_offset=10
        )
        
        symbol = Symbol(
            fqname=name,
            ast_node=node,
            location=location,
        )
        
        # Add references
        for ref in references:
            symbol.references.add(ref)
        
        return symbol
    
    def test_no_dead_code(self):
        """Test that no issues are found when all code is used."""
        # Create a used function
        used_func = self._create_mock_symbol("module.used_function")
        
        # Create a main function that uses it
        main_func = self._create_mock_symbol("module.main", {"module.used_function"})
        
        # Add to graph
        self.graph.add_symbol(used_func)
        self.graph.add_symbol(main_func)
        
        # Set up detector with module.main as an entry point
        self.detector = DeadCodeDetector(entry_points=["module.main"])
        
        # Debug: Print graph state before analysis
        print("\nGraph symbols before analysis:")
        for sym_name, symbol in self.graph.symbols.items():
            print(f"- {sym_name} (references: {symbol.references})")
        
        # Analyze
        issues = self.detector._analyze(self.graph)
        
        # Debug: Print analysis results
        print("\nFound issues:")
        for issue in issues:
            print(f"- {issue.message}")
        
        # Debug: Print referenced symbols
        print("\nReferenced symbols:")
        referenced = set()
        for symbol in self.graph.symbols.values():
            referenced.update(symbol.references)
        print(f"- {referenced}")
        
        # Should be no dead code
        self.assertEqual(len(issues), 0, f"Expected no issues, but got: {[i.message for i in issues]}")
    
    def test_dead_function(self):
        """Test that an unused function is detected."""
        # Create an unused function
        unused_func = self._create_mock_symbol("module.unused_function")
        
        # Add to graph
        self.graph.add_symbol(unused_func)
        
        # Analyze
        issues = self.detector._analyze(self.graph)
        
        # Should find one issue
        self.assertEqual(len(issues), 1)
        self.assertIn("unused", issues[0].message.lower())
    
    def test_entry_points(self):
        """Test that entry points are not marked as dead code."""
        # Create a detector with custom entry points
        detector = DeadCodeDetector(entry_points=["module.main"])
        
        # Create a main function that would be dead without being an entry point
        main_func = self._create_mock_symbol("module.main")
        
        # Add to graph
        self.graph.add_symbol(main_func)
        
        # Analyze
        issues = detector._analyze(self.graph)
        
        # Should be no dead code (main is an entry point)
        self.assertEqual(len(issues), 0)
    
    def test_ignored_paths(self):
        """Test that ignored paths are not reported as dead code."""
        # Create a detector that ignores test files
        detector = DeadCodeDetector(ignore=["**/test_*.py"])
        
        # Create a test function in a test file
        test_func = self._create_mock_symbol("test_module.test_function", file_path="tests/test_module.py")
        
        # Add to graph
        self.graph.add_symbol(test_func)
        
        # Analyze
        issues = detector._analyze(self.graph)
        
        # Should be no dead code (test files are ignored)
        self.assertEqual(len(issues), 0)
