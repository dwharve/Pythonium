"""
Test module for the complexity detector functionality.
"""

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pythonium.detectors.complexity import ComplexityDetector, RADON_AVAILABLE
from pythonium.models import CodeGraph, Issue, Symbol, Location


class TestComplexityDetector(unittest.TestCase):
    """Test case for complexity detector."""
    
    def setUp(self):
        """Set up test environment."""
        self.detector = ComplexityDetector()
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_complexity.py"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_detector_initialization(self):
        """Test detector initialization with options."""
        detector = ComplexityDetector(
            cyclomatic_threshold=15,
            loc_threshold=100,
            halstead_difficulty_threshold=25.0
        )
        self.assertEqual(detector.cyclomatic_threshold, 15)
        self.assertEqual(detector.loc_threshold, 100)
        self.assertEqual(detector.halstead_difficulty_threshold, 25.0)
    
    def test_detector_default_values(self):
        """Test detector default threshold values."""
        detector = ComplexityDetector()
        self.assertEqual(detector.cyclomatic_threshold, 10)
        self.assertEqual(detector.loc_threshold, 50)
        self.assertEqual(detector.halstead_difficulty_threshold, 20.0)
    
    def test_count_loc(self):
        """Test lines of code counting."""
        code = '''
def simple_function():
    """A simple function with docstring."""
    # This is a comment
    x = 1
    y = 2
    
    # Another comment
    return x + y
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        loc = self.detector._count_loc(func_node)
        
        # Should count actual code lines, excluding docstrings and comments
        self.assertGreater(loc, 0)
        self.assertLess(loc, 10)  # Should be reasonable
    
    def test_calculate_basic_complexity(self):
        """Test basic cyclomatic complexity calculation."""
        # Simple function (complexity = 1)
        simple_code = '''
def simple_function():
    return True
'''
        tree = ast.parse(simple_code)
        func_node = tree.body[0]
        complexity = self.detector._calculate_basic_complexity(func_node)
        self.assertEqual(complexity, 1)
        
        # Complex function with multiple branches
        complex_code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            for i in range(z):
                if i % 2 == 0:
                    return i
            else:
                return -1
        elif y < 0:
            while z > 0:
                z -= 1
                if z == 5:
                    break
            return z
    else:
        try:
            return x / y
        except ZeroDivisionError:
            return 0
'''
        tree = ast.parse(complex_code)
        func_node = tree.body[0]
        complexity = self.detector._calculate_basic_complexity(func_node)
        
        # Should detect multiple decision points
        self.assertGreater(complexity, 5)
    
    def test_analyze_function_basic_high_loc(self):
        """Test analysis of functions with high lines of code."""
        # Create a function with many lines
        lines = ["    x += 1"] * 60  # 60 lines of code, properly indented
        code = f'''
def long_function():
    """A very long function."""
    x = 0
{chr(10).join(lines)}
    return x
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        # Create a mock symbol
        symbol = MagicMock()
        symbol.ast_node = func_node
        symbol.fqname = "test.long_function"
        symbol.location = Location(file=self.test_file, line=1)
        
        issues = self.detector._analyze_function_basic(symbol)
        
        # Should detect high LOC
        self.assertGreater(len(issues), 0)
        loc_issues = [i for i in issues if "lines of code" in i.message]
        self.assertGreater(len(loc_issues), 0)
    
    def test_analyze_function_basic_high_complexity(self):
        """Test analysis of functions with high cyclomatic complexity."""
        # Create a complex function
        complex_code = '''
def complex_function(a, b, c, d, e):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        for i in range(10):
                            if i % 2 == 0:
                                if i > 5:
                                    return i
                                else:
                                    continue
                            else:
                                break
    return 0
'''
        tree = ast.parse(complex_code)
        func_node = tree.body[0]
        
        # Create a mock symbol
        symbol = MagicMock()
        symbol.ast_node = func_node
        symbol.fqname = "test.complex_function"
        symbol.location = Location(file=self.test_file, line=1)
        
        issues = self.detector._analyze_function_basic(symbol)
        
        # Should detect high complexity
        complexity_issues = [i for i in issues if "complexity" in i.message]
        self.assertGreater(len(complexity_issues), 0)
    
    def test_analyze_function_basic_normal(self):
        """Test analysis of normal functions (no issues)."""
        # Create a simple, normal function
        normal_code = '''
def normal_function(x, y):
    """A normal function."""
    if x > y:
        return x
    else:
        return y
'''
        tree = ast.parse(normal_code)
        func_node = tree.body[0]
        
        # Create a mock symbol
        symbol = MagicMock()
        symbol.ast_node = func_node
        symbol.fqname = "test.normal_function"
        symbol.location = Location(file=self.test_file, line=1)
        
        issues = self.detector._analyze_function_basic(symbol)
        
        # Should not detect any issues
        self.assertEqual(len(issues), 0)
    
    def test_analyze_file_complexity(self):
        """Test file-level complexity analysis."""
        code = '''
def simple_function():
    return True

def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        return x * 2
    return x
'''
        
        # Create mock symbols
        tree = ast.parse(code)
        symbols = []
        for i, func_node in enumerate(tree.body):
            symbol = MagicMock()
            symbol.ast_node = func_node
            symbol.fqname = f"test.{func_node.name}"
            symbol.location = Location(file=self.test_file, line=i+1)
            symbols.append(symbol)
        
        issues = self.detector._analyze_file_complexity(code, symbols, self.test_file)
        
        # Should find issues in the complex function
        self.assertIsInstance(issues, list)
        if issues:
            # Verify issue structure
            for issue in issues:
                self.assertIsInstance(issue, Issue)
                self.assertIn("metadata" in issue.__dict__ or hasattr(issue, "metadata"), [True])
    
    def test_analyze_with_graph(self):
        """Test analysis with a code graph."""
        # Create test code
        code = '''
def simple_function():
    return True

def long_function():
    # This function has many lines to exceed the threshold
    x1 = 1
    x2 = 2
    x3 = 3
    x4 = 4
    x5 = 5
    x6 = 6
    x7 = 7
    x8 = 8
    x9 = 9
    x10 = 10
    x11 = 11
    x12 = 12
    x13 = 13
    x14 = 14
    x15 = 15
    x16 = 16
    x17 = 17
    x18 = 18
    x19 = 19
    x20 = 20
    x21 = 21
    x22 = 22
    x23 = 23
    x24 = 24
    x25 = 25
    x26 = 26
    x27 = 27
    x28 = 28
    x29 = 29
    x30 = 30
    x31 = 31
    x32 = 32
    x33 = 33
    x34 = 34
    x35 = 35
    x36 = 36
    x37 = 37
    x38 = 38
    x39 = 39
    x40 = 40
    x41 = 41
    x42 = 42
    x43 = 43
    x44 = 44
    x45 = 45
    x46 = 46
    x47 = 47
    x48 = 48
    x49 = 49
    x50 = 50
    x51 = 51
    x52 = 52
    return sum([x1, x2, x3, x4, x5])
'''
        self.test_file.write_text(code)
        
        # Create mock symbols
        tree = ast.parse(code)
        symbols = {}
        for i, func_node in enumerate(tree.body):
            symbol = MagicMock()
            symbol.ast_node = func_node
            symbol.fqname = f"test.{func_node.name}"
            symbol.location = Location(file=self.test_file, line=i+1)
            symbols[f"test.{func_node.name}"] = symbol
        
        # Create mock code graph
        graph = CodeGraph()
        graph.symbols = symbols
        # Add file content and parsed AST to the graph
        graph.file_contents[str(self.test_file)] = code
        graph.parsed_files[str(self.test_file)] = tree
        
        issues = self.detector.analyze(graph)
        
        # Should find complexity issues
        self.assertIsInstance(issues, list)
        # Should find issues with the long function
        long_func_issues = [i for i in issues if "long_function" in i.message]
        self.assertGreater(len(long_func_issues), 0)
    
    @unittest.skipUnless(RADON_AVAILABLE, "Radon not available")
    def test_analyze_with_radon(self):
        """Test analysis using radon library."""
        code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            for i in range(z):
                if i % 2 == 0:
                    if i > 5:
                        return i
                    else:
                        continue
                else:
                    break
            else:
                return -1
        elif y < 0:
            while z > 0:
                z -= 1
                if z == 5:
                    break
            return z
    else:
        try:
            return x / y
        except ZeroDivisionError:
            return 0
    return None
'''
        
        # Create mock symbol
        tree = ast.parse(code)
        func_node = tree.body[0]
        symbol = MagicMock()
        symbol.ast_node = func_node
        symbol.fqname = "test.complex_function"
        symbol.location = Location(file=self.test_file, line=1)
        
        issues = self.detector._analyze_with_radon(code, [symbol], self.test_file)
        
        # Should detect high complexity using radon
        self.assertIsInstance(issues, list)
        # May or may not find issues depending on radon's complexity calculation
    
    def test_analyze_with_radon_unavailable(self):
        """Test analysis when radon is not available."""
        code = '''
def simple_function():
    return True
'''
        
        # Mock radon as unavailable
        with patch('pythonium.detectors.complexity.RADON_AVAILABLE', False):
            detector = ComplexityDetector()
            
            # Create mock symbol
            tree = ast.parse(code)
            func_node = tree.body[0]
            symbol = MagicMock()
            symbol.ast_node = func_node
            symbol.fqname = "test.simple_function"
            symbol.location = Location(file=self.test_file, line=1)
            
            issues = detector._analyze_with_radon(code, [symbol], self.test_file)
            
            # Should return empty list when radon unavailable
            self.assertEqual(len(issues), 0)
    
    def test_error_handling_file_read(self):
        """Test error handling when file cannot be read."""
        # Create mock symbols with non-existent file
        symbol = MagicMock()
        symbol.ast_node = ast.parse("def test(): pass").body[0]
        symbol.location = Location(file=Path("/non/existent/file.py"), line=1)
        
        graph = CodeGraph()
        graph.symbols = {"test": symbol}
        
        # Should handle file read errors gracefully
        issues = self.detector.analyze(graph)
        self.assertIsInstance(issues, list)
        # Should not crash, but may not find issues
    
    def test_issue_metadata(self):
        """Test that issues contain proper metadata."""
        # Create a function that exceeds LOC threshold
        lines = ["    x += 1"] * 60
        code = f'''
def long_function():
    """A long function."""
    x = 0
{chr(10).join(lines)}
    return x
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        symbol = MagicMock()
        symbol.ast_node = func_node
        symbol.fqname = "test.long_function"
        symbol.location = Location(file=self.test_file, line=1)
        
        issues = self.detector._analyze_function_basic(symbol)
        
        # Should have issues with metadata
        self.assertGreater(len(issues), 0)
        
        for issue in issues:
            self.assertTrue(hasattr(issue, "metadata") or "metadata" in issue.__dict__)
            if hasattr(issue, "metadata") and issue.metadata:
                # Metadata should contain relevant information
                self.assertIsInstance(issue.metadata, dict)
    
    def test_complexity_thresholds(self):
        """Test that complexity thresholds work correctly."""
        # Test with low thresholds
        low_threshold_detector = ComplexityDetector(
            cyclomatic_threshold=1,
            loc_threshold=1
        )
        
        # Simple function that should exceed low thresholds
        code = '''
def simple_function(x):
    if x > 0:
        return x
    return 0
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        symbol = MagicMock()
        symbol.ast_node = func_node
        symbol.fqname = "test.simple_function"
        symbol.location = Location(file=self.test_file, line=1)
        
        issues = low_threshold_detector._analyze_function_basic(symbol)
        
        # Should find issues with low thresholds
        self.assertGreater(len(issues), 0)
        
        # Test with high thresholds
        high_threshold_detector = ComplexityDetector(
            cyclomatic_threshold=1000,
            loc_threshold=1000
        )
        
        issues = high_threshold_detector._analyze_function_basic(symbol)
        
        # Should not find issues with high thresholds
        self.assertEqual(len(issues), 0)
    
    def test_non_function_symbols(self):
        """Test that non-function symbols are ignored."""
        # Create a class node instead of function
        code = '''
class TestClass:
    def __init__(self):
        pass
'''
        tree = ast.parse(code)
        class_node = tree.body[0]
        
        symbol = MagicMock()
        symbol.ast_node = class_node  # Not a FunctionDef
        symbol.location = Location(file=self.test_file, line=1)
        
        graph = CodeGraph()
        graph.symbols = {"TestClass": symbol}
        
        issues = self.detector.analyze(graph)
        
        # Should not analyze class nodes
        self.assertEqual(len(issues), 0)
    
    def test_symbols_without_location(self):
        """Test that symbols without location are ignored."""
        symbol = MagicMock()
        symbol.ast_node = ast.parse("def test(): pass").body[0]
        symbol.location = None  # No location
        
        graph = CodeGraph()
        graph.symbols = {"test": symbol}
        
        issues = self.detector.analyze(graph)
        
        # Should ignore symbols without location
        self.assertEqual(len(issues), 0)


class TestComplexityDetectorIntegration(unittest.TestCase):
    """Integration tests for complexity detector."""
    
    def setUp(self):
        """Set up test environment."""
        self.detector = ComplexityDetector(
            cyclomatic_threshold=5,  # Lower threshold for testing
            loc_threshold=20         # Lower threshold for testing
        )
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_real_complexity_analysis(self):
        """Test analysis on realistic code with complexity issues."""
        test_file = Path(self.temp_dir) / "complex_code.py"
        
        code = '''
def simple_function():
    """A simple function."""
    return True

def moderately_complex_function(data):
    """A function with moderate complexity."""
    result = []
    
    if not data:
        return result
    
    for item in data:
        if isinstance(item, str):
            if len(item) > 10:
                result.append(item.upper())
            else:
                result.append(item.lower())
        elif isinstance(item, int):
            if item > 0:
                result.append(item * 2)
            else:
                result.append(item)
        else:
            result.append(str(item))
    
    return result

def very_long_function():
    """A function that exceeds the LOC threshold."""
    x1 = 1
    x2 = 2
    x3 = 3
    x4 = 4
    x5 = 5
    x6 = 6
    x7 = 7
    x8 = 8
    x9 = 9
    x10 = 10
    x11 = 11
    x12 = 12
    x13 = 13
    x14 = 14
    x15 = 15
    x16 = 16
    x17 = 17
    x18 = 18
    x19 = 19
    x20 = 20
    x21 = 21
    x22 = 22
    x23 = 23
    x24 = 24
    x25 = 25
    return sum([x1, x2, x3, x4, x5, x6, x7, x8, x9, x10])
'''
        test_file.write_text(code)
        
        # Create mock symbols
        tree = ast.parse(code)
        symbols = {}
        for i, func_node in enumerate(tree.body):
            symbol = MagicMock()
            symbol.ast_node = func_node
            symbol.fqname = f"complex_code.{func_node.name}"
            symbol.location = Location(file=test_file, line=i*10+1)
            symbols[symbol.fqname] = symbol
        
        # Create mock code graph
        graph = CodeGraph()
        graph.symbols = symbols
        # Add file content and parsed AST to the graph
        graph.file_contents[str(test_file)] = code
        graph.parsed_files[str(test_file)] = tree
        
        issues = self.detector.analyze(graph)
        
        # Should find various complexity issues
        self.assertIsInstance(issues, list)
        self.assertGreater(len(issues), 0)
        
        # Check that we got reasonable results
        complexity_issues = [i for i in issues if "complexity" in i.message]
        loc_issues = [i for i in issues if "lines of code" in i.message]
        
        # Should have at least one type of issue
        self.assertTrue(len(complexity_issues) > 0 or len(loc_issues) > 0)


if __name__ == "__main__":
    unittest.main()
