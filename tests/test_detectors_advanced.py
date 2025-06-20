"""
Comprehensive tests for advanced detectors.
Combines tests for blocks, semantic, and patterns detectors for better organization.
"""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock

from pythonium.models import Symbol, Location, CodeGraph
from pythonium.detectors.blocks import BlockCloneDetector
from pythonium.detectors.semantic import SemanticDetector
from pythonium.detectors.patterns import PatternDetector


class TestBlockCloneDetector(unittest.TestCase):
    """Test cases for the BlockCloneDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = BlockCloneDetector(min_statements=3)
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "block_clone")
        self.assertEqual(self.detector.name, "Block Clone Detector")
        self.assertIn("block", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_block_clone_detection(self):
        """Test detection of duplicate code blocks."""
        code = '''
def validate_user(user_data):
    if not user_data:
        raise ValueError("User data cannot be empty")
    if not isinstance(user_data, dict):
        raise TypeError("User data must be a dictionary")
    if 'email' not in user_data:
        raise KeyError("Email is required")
    return True

def validate_product(product_data):
    if not product_data:
        raise ValueError("Product data cannot be empty")
    if not isinstance(product_data, dict):
        raise TypeError("Product data must be a dictionary")
    if 'name' not in product_data:
        raise KeyError("Name is required")
    return True
'''
        # Parse the code and create symbols
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbol = Symbol(
                    fqname=f"test.{node.name}",
                    ast_node=node,
                    location=Location(file=Path("test.py"), line=node.lineno, column=node.col_offset)
                )
                self.graph.add_symbol(symbol)
        
        # Run detector
        issues = self.detector._analyze(self.graph)
        
        # Should detect block-level clones in validation patterns
        self.assertGreater(len(issues), 0)
        clone_issue = issues[0]
        self.assertIn("duplicate", clone_issue.message.lower())
    
    def test_configuration_options(self):
        """Test various configuration options."""
        # Test with different minimum statement thresholds
        detector_strict = BlockCloneDetector(min_statements=5)
        detector_lenient = BlockCloneDetector(min_statements=2)
        
        self.assertEqual(detector_strict.min_statements, 5)
        self.assertEqual(detector_lenient.min_statements, 2)
        
        # Test variable name ignoring
        detector_ignore_vars = BlockCloneDetector(ignore_variable_names=True)
        detector_consider_vars = BlockCloneDetector(ignore_variable_names=False)
        
        self.assertTrue(detector_ignore_vars.ignore_variable_names)
        self.assertFalse(detector_consider_vars.ignore_variable_names)


class TestSemanticDetector(unittest.TestCase):
    """Test cases for the SemanticDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = SemanticDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "semantic_equivalence")
        self.assertEqual(self.detector.name, "Semantic Detector")
        self.assertIn("equivalent", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_builtin_equivalence_detection(self):
        """Test detection of manual implementations vs builtins."""
        code = '''
def sum_numbers_manual(numbers):
    total = 0
    for num in numbers:
        total += num
    return total

def sum_numbers_builtin(numbers):
    return sum(numbers)

def concatenate_manual(strings):
    result = ""
    for s in strings:
        result += s
    return result

def concatenate_optimized(strings):
    return "".join(strings)
'''
        # Parse the code and create symbols
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbol = Symbol(
                    fqname=f"test.{node.name}",
                    ast_node=node,
                    location=Location(file=Path("test.py"), line=node.lineno, column=node.col_offset)
                )
                self.graph.add_symbol(symbol)
        
        # Run detector
        issues = self.detector._analyze(self.graph)
        
        # Should detect semantic equivalences
        self.assertGreater(len(issues), 0)
        
        # Check for manual implementation messages
        manual_issues = [issue for issue in issues if "manual" in issue.message.lower()]
        self.assertGreater(len(manual_issues), 0)


class TestPatternDetector(unittest.TestCase):
    """Test cases for the PatternDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = PatternDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "advanced_patterns")
        self.assertEqual(self.detector.name, "Pattern Detector")
        self.assertIn("pattern", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_factory_pattern_detection(self):
        """Test detection of factory patterns."""
        code = '''
class UserFactory:
    @staticmethod
    def create_admin(name, email):
        return {'type': 'admin', 'name': name, 'email': email, 'permissions': ['all']}
    
    @staticmethod  
    def create_user(name, email):
        return {'type': 'user', 'name': name, 'email': email, 'permissions': ['read']}

class ProductFactory:
    @staticmethod
    def create_physical(name, price):
        return {'type': 'physical', 'name': name, 'price': price, 'shipping': True}
    
    @staticmethod
    def create_digital(name, price):
        return {'type': 'digital', 'name': name, 'price': price, 'shipping': False}
'''
        # Parse the code and create symbols
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                symbol = Symbol(
                    fqname=f"test.{node.name}",
                    ast_node=node,
                    location=Location(file=Path("test.py"), line=node.lineno, column=node.col_offset)
                )
                self.graph.add_symbol(symbol)
        
        # Run detector
        issues = self.detector._analyze(self.graph)
        
        # Should detect factory patterns
        self.assertGreater(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
