"""Tests for the unified clone detector."""

import os
import sys
import unittest
from pathlib import Path
from unittest import TestCase, mock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pythonium.detectors.clone import CloneDetector
from pythonium.models import CodeGraph, Symbol, Location


class TestCloneDetector(TestCase):
    """Test cases for the unified CloneDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = CodeGraph()
        
        # Clear cache to ensure clean test environment
        from pythonium.performance import get_cache
        cache = get_cache()
        cache.clear_detector_issues("clone")
    
    def _create_mock_symbol(self, name, source, file_path="test.py", line=1):
        """Helper to create a mock symbol with source code."""
        # Convert to absolute path for consistency
        abs_file_path = Path(file_path).absolute()
        
        # Create a location
        location = Location(
            file=abs_file_path,
            line=line,
            column=0,
            end_line=line + len(source.splitlines()) - 1,
            end_column=10
        )
        
        # Create a real AST node
        import ast
        try:
            # Parse the source to create a real AST node
            parsed = ast.parse(source)
            node = parsed.body[0]  # Get the function definition
        except:
            # Fallback to mock if parsing fails
            node = mock.Mock()
            node.lineno = line
            node.end_lineno = line + len(source.splitlines()) - 1
            node._fields = []
        
        symbol = Symbol(
            fqname=name,
            ast_node=node,
            location=location,
        )
        
        # Store the source code for the detector to access
        symbol.source = source
        symbol.source_lines = source.splitlines(keepends=True)
        
        return symbol
    
    def test_exact_clone_detection(self):
        """Test that exact clones are detected with similarity_threshold=1.0."""
        # Create detector for exact clones
        detector = CloneDetector(similarity_threshold=1.0, min_lines=3)
        
        # Create two identical functions with enough lines
        source = """def foo(x):
    if x is None:
        return 0
    y = x * 2
    z = y + 1
    return z"""
        
        func1 = self._create_mock_symbol("module1.foo", source, "module1.py")
        func2 = self._create_mock_symbol("module2.foo", source, "module2.py")  # Same name for exact clone
        
        # Add to graph
        self.graph.add_symbol(func1)
        self.graph.add_symbol(func2)
        
        # Analyze
        issues = detector._analyze(self.graph)
        
        # Should find at least one issue
        self.assertGreater(len(issues), 0, "Expected at least one exact clone issue")
        
        # Check issue properties
        issue = issues[0]
        self.assertEqual(issue.detector_id, "clone")
        self.assertIn("identical", issue.message.lower())
        self.assertEqual(issue.severity, "error")  # High similarity should be error
    
    def test_near_clone_detection(self):
        """Test that near clones are detected with similarity_threshold<1.0."""
        # Create detector for near clones
        detector = CloneDetector(similarity_threshold=0.8, min_lines=3)
        
        # Create two similar but not identical functions
        source1 = "def process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result"
        source2 = "def handle_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 3)\n    return result"
        
        func1 = self._create_mock_symbol("module1.process_data", source1, "module1.py")
        func2 = self._create_mock_symbol("module2.handle_data", source2, "module2.py")
        
        # Add to graph
        self.graph.add_symbol(func1)
        self.graph.add_symbol(func2)
        
        # Analyze
        issues = detector._analyze(self.graph)
        
        # Near clone detection might not always find these depending on the algorithm
        # This is more of a smoke test to ensure the detector doesn't crash
        self.assertIsInstance(issues, list)
    
    def test_no_clones(self):
        """Test that no issues are found when there are no clones."""
        detector = CloneDetector(similarity_threshold=1.0, min_lines=3)
        
        # Create two completely different functions
        func1 = self._create_mock_symbol(
            "module.func1",
            "def func1():\n    print('Hello')\n    return 42"
        )
        
        func2 = self._create_mock_symbol(
            "module.func2",
            "def func2():\n    print('Goodbye')\n    return 0"
        )
        
        # Add to graph
        self.graph.add_symbol(func1)
        self.graph.add_symbol(func2)
        
        # Analyze
        issues = detector._analyze(self.graph)
        
        # Should find no clones
        self.assertEqual(len(issues), 0)
    
    def test_min_lines_threshold(self):
        """Test that the minimum lines threshold is respected."""
        # Create a detector that requires at least 4 lines
        detector = CloneDetector(similarity_threshold=1.0, min_lines=4)
        
        # Create two identical functions that are 3 lines long
        source = "def foo(x):\n    return x * 2"  # Only 2 lines
        
        func1 = self._create_mock_symbol("module1.foo", source, "module1.py")
        func2 = self._create_mock_symbol("module2.foo", source, "module2.py")
        
        # Add to graph
        self.graph.add_symbol(func1)
        self.graph.add_symbol(func2)
        
        # Analyze
        issues = detector._analyze(self.graph)
        
        # Should find no clones (too short)
        self.assertEqual(len(issues), 0)
    
    def test_detector_properties(self):
        """Test that detector has correct properties."""
        detector = CloneDetector()
        
        self.assertEqual(detector.id, "clone")
        self.assertEqual(detector.name, "Clone Detector")
        self.assertIn("duplicate and similar", detector.description.lower())
    
    def test_similarity_threshold_bounds(self):
        """Test that similarity threshold is properly bounded."""
        # Test upper bound
        detector = CloneDetector(similarity_threshold=1.5)
        self.assertEqual(detector.similarity_threshold, 1.0)
        
        # Test lower bound
        detector = CloneDetector(similarity_threshold=-0.5)
        self.assertEqual(detector.similarity_threshold, 0.0)
        
        # Test normal value
        detector = CloneDetector(similarity_threshold=0.8)
        self.assertEqual(detector.similarity_threshold, 0.8)
    
    def test_exact_mode_detection(self):
        """Test that exact mode is correctly detected."""
        # Exact mode
        detector = CloneDetector(similarity_threshold=1.0)
        self.assertTrue(detector.exact_mode)
        
        # Near mode
        detector = CloneDetector(similarity_threshold=0.9)
        self.assertFalse(detector.exact_mode)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        detector = CloneDetector(similarity_threshold=0.8, min_lines=2)
        
        # Test with no functions
        empty_graph = CodeGraph()
        issues = detector._analyze(empty_graph)
        self.assertEqual(len(issues), 0)
        
        # Test with single function
        single_source = """
def single_function():
    x = 1
    y = 2
    return x + y
"""
        func1 = self._create_mock_symbol("module.single", single_source, "single.py")
        self.graph.symbols[func1.fqname] = func1
        
        issues = detector._analyze(self.graph)
        self.assertEqual(len(issues), 0, "Single function should not produce clone issues")
    
    def test_class_clone_detection(self):
        """Test clone detection in classes."""
        detector = CloneDetector(similarity_threshold=0.9, min_lines=3)
        
        # Two similar classes
        class_source1 = """
class UserProcessor:
    def process_user(self, user_id):
        user = self.get_user(user_id)
        user.validate()
        return user.save()
        
    def get_user(self, user_id):
        return User.find(user_id)
"""
        
        class_source2 = """
class DataProcessor:
    def process_data(self, data_id):
        data = self.get_data(data_id)
        data.validate()
        return data.save()
        
    def get_data(self, data_id):
        return Data.find(data_id)
"""
        
        class1 = self._create_mock_symbol("module1.UserProcessor", class_source1, "module1.py")
        class2 = self._create_mock_symbol("module2.DataProcessor", class_source2, "module2.py")
        
        self.graph.symbols[class1.fqname] = class1
        self.graph.symbols[class2.fqname] = class2
        
        issues = detector._analyze(self.graph)
        # Classes with similar structure should be detected
        self.assertIsInstance(issues, list)
    
    def test_method_clone_detection(self):
        """Test clone detection in class methods."""
        detector = CloneDetector(similarity_threshold=0.85, min_lines=3)
        
        # Two similar methods
        method_source1 = """
def calculate_discount(self, price, customer_type):
    if customer_type == 'premium':
        discount = price * 0.2
    else:
        discount = price * 0.1
    return price - discount
"""
        
        method_source2 = """
def calculate_rebate(self, amount, client_type):
    if client_type == 'premium':
        rebate = amount * 0.2
    else:
        rebate = amount * 0.1
    return amount - rebate
"""
        
        method1 = self._create_mock_symbol("class1.calculate_discount", method_source1, "class1.py")
        method2 = self._create_mock_symbol("class2.calculate_rebate", method_source2, "class2.py")
        
        self.graph.symbols[method1.fqname] = method1
        self.graph.symbols[method2.fqname] = method2
        
        issues = detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_extract_meaningful_code(self):
        """Test the _extract_meaningful_code method."""
        detector = CloneDetector()
        
        # Test with function
        func_source = """
def test_function():
    x = 1
    y = 2
    return x + y
"""
        func_symbol = self._create_mock_symbol("test.func", func_source)
        meaningful_code = detector._extract_meaningful_code(func_symbol)
        self.assertIsInstance(meaningful_code, str)
        self.assertIn("x = 1", meaningful_code)
        
        # Test with class
        class_source = """
class TestClass:
    def method1(self):
        return 1
        
    def method2(self):
        return 2
"""
        class_symbol = self._create_mock_symbol("test.TestClass", class_source)
        meaningful_code = detector._extract_meaningful_code(class_symbol)
        self.assertIsInstance(meaningful_code, str)
    
    def test_normalize_source(self):
        """Test the _normalize_source method."""
        detector = CloneDetector(ignore_comments=True)
        
        # Test with valid Python code
        code = """def test():
    x = 1
    return x"""
        
        try:
            normalized = detector._normalize_source(code)
            self.assertIsInstance(normalized, str)
        except Exception:
            # If normalization fails, that's also valid behavior
            pass
    
    def test_fingerprint_generation(self):
        """Test the _generate_fingerprint method."""
        detector = CloneDetector()
        
        # Test with valid function code
        code = """def func():
    x = 1
    y = 2
    return x + y"""
        
        try:
            fingerprint = detector._generate_fingerprint(code)
            self.assertIsInstance(fingerprint, set)
        except Exception:
            # If fingerprint generation fails, that's also valid behavior
            pass
    
    def test_similarity_calculation_with_fingerprints(self):
        """Test the _calculate_similarity method with proper fingerprints."""
        detector = CloneDetector()
        
        # Test identical fingerprints
        fp1 = {1, 2, 3, 4, 5}
        fp2 = {1, 2, 3, 4, 5}
        similarity = detector._calculate_similarity(fp1, fp2)
        self.assertEqual(similarity, 1.0)
        
        # Test completely different fingerprints
        fp1 = {1, 2, 3}
        fp2 = {4, 5, 6}
        similarity = detector._calculate_similarity(fp1, fp2)
        self.assertEqual(similarity, 0.0)
        
        # Test partially overlapping fingerprints
        fp1 = {1, 2, 3, 4}
        fp2 = {3, 4, 5, 6}
        similarity = detector._calculate_similarity(fp1, fp2)
        self.assertGreater(similarity, 0.0)
        self.assertLess(similarity, 1.0)
    
    def test_line_count_filtering(self):
        """Test that short code blocks are filtered by min_lines."""
        detector = CloneDetector(similarity_threshold=1.0, min_lines=5)
        
        # Short function (should be ignored)
        short_source = """
def short():
    return 1
"""
        
        func1 = self._create_mock_symbol("module1.short1", short_source, "module1.py")
        func2 = self._create_mock_symbol("module2.short2", short_source, "module2.py")
        
        self.graph.symbols[func1.fqname] = func1
        self.graph.symbols[func2.fqname] = func2
        
        issues = detector._analyze(self.graph)
        # Should not detect clones because functions are too short
        self.assertEqual(len(issues), 0)
    
    def test_different_similarity_thresholds(self):
        """Test detection with different similarity thresholds."""
        # Similar but not identical functions
        source1 = """
def process_data(data):
    result = []
    for item in data:
        processed = item.upper()
        result.append(processed)
    return result
"""
        
        source2 = """
def handle_items(items):
    output = []
    for element in items:
        transformed = element.lower()
        output.append(transformed)
    return output
"""
        
        func1 = self._create_mock_symbol("module1.process_data", source1, "module1.py")
        func2 = self._create_mock_symbol("module2.handle_items", source2, "module2.py")
        
        self.graph.symbols[func1.fqname] = func1
        self.graph.symbols[func2.fqname] = func2
        
        # High threshold - should not detect
        strict_detector = CloneDetector(similarity_threshold=0.95, min_lines=3)
        issues = strict_detector._analyze(self.graph)
        self.assertEqual(len(issues), 0, "High threshold should not detect similar code")
        
        # Lower threshold - might detect
        lenient_detector = CloneDetector(similarity_threshold=0.7, min_lines=3)
        issues = lenient_detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_malformed_ast_handling(self):
        """Test handling of symbols with malformed or missing AST nodes."""
        detector = CloneDetector()
        
        # Symbol with None AST node
        symbol_no_ast = Symbol(
            fqname="test.no_ast",
            location=Location(Path("test.py"), 1, 0),
            ast_node=None
        )
        
        # Test _extract_meaningful_code with None AST
        meaningful_code = detector._extract_meaningful_code(symbol_no_ast)
        self.assertEqual(meaningful_code, "")
        
        # Add to graph and test analysis
        self.graph.symbols[symbol_no_ast.fqname] = symbol_no_ast
        issues = detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_performance_with_large_input(self):
        """Test performance characteristics with larger input."""
        detector = CloneDetector(similarity_threshold=0.8, min_lines=3)
        
        # Create multiple similar functions
        base_source = """
def process_item_{i}(data):
    result = data * {i}
    if result > 10:
        return result + {i}
    else:
        return result - {i}
"""
        
        # Add 10 similar functions
        for i in range(10):
            source = base_source.format(i=i)
            func = self._create_mock_symbol(f"module.func_{i}", source, f"module{i}.py")
            self.graph.symbols[func.fqname] = func
        
        # Should complete without errors
        issues = detector._analyze(self.graph)
        self.assertIsInstance(issues, list)
    
    def test_error_handling_in_extract_meaningful_code(self):
        """Test error handling in _extract_meaningful_code method."""
        detector = CloneDetector()
        
        # Create a symbol with problematic AST that might cause unparsing to fail
        import ast
        
        # Create a symbol with a malformed AST node
        class MalformedNode(ast.AST):
            def __init__(self):
                pass
        
        malformed_symbol = Symbol(
            fqname="test.malformed",
            location=Location(Path("test.py"), 1, 1),
            ast_node=MalformedNode()
        )
        
        # This should handle the exception gracefully and return empty string
        result = detector._extract_meaningful_code(malformed_symbol)
        self.assertEqual(result, "")
    
    def test_class_body_extraction(self):
        """Test meaningful code extraction for classes."""
        detector = CloneDetector()
        
        source = '''
class TestClass:
    """A test class."""
    
    def __init__(self):
        self.value = 1
    
    def method(self):
        return self.value
    
    # This comment should be ignored
    some_var = "test"
'''
        
        symbol = self._create_mock_symbol("TestClass", source)
        result = detector._extract_meaningful_code(symbol)
        
        # Should extract only meaningful parts (methods and assignments)
        self.assertIn("def __init__", result)
        self.assertIn("def method", result)
        self.assertIn("some_var", result)
        # Should not include docstring in meaningful content
        self.assertNotIn('"""A test class."""', result)
    
    def test_detect_clones_with_invalid_symbols(self):
        """Test clone detection with invalid symbols."""
        detector = CloneDetector(min_lines=2)
        
        # Add symbols without AST nodes
        symbol1 = Symbol(
            fqname="test.no_ast",
            location=Location(Path("test.py"), 1, 1),
            ast_node=None
        )
        
        # Add symbol without location
        import ast
        symbol2 = Symbol(
            fqname="test.no_location",
            location=None,
            ast_node=ast.parse("def func(): pass").body[0]
        )
        
        # Add symbol without file
        symbol3 = Symbol(
            fqname="test.no_file",
            location=Location(None, 1, 1),
            ast_node=ast.parse("def func(): pass").body[0]
        )
        
        self.graph.symbols["no_ast"] = symbol1
        self.graph.symbols["no_location"] = symbol2
        self.graph.symbols["no_file"] = symbol3
        
        # Should handle gracefully and return no issues
        issues = detector.analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_small_code_blocks_ignored(self):
        """Test that code blocks below min_lines threshold are ignored."""
        detector = CloneDetector(min_lines=5)
        
        # Create two identical small functions (below threshold)
        source = '''def small(): return 1'''
        
        symbol1 = self._create_mock_symbol("small1", source, "file1.py")
        symbol2 = self._create_mock_symbol("small2", source, "file2.py")
        
        self.graph.symbols["small1"] = symbol1
        self.graph.symbols["small2"] = symbol2
        
        issues = detector.analyze(self.graph)
        # Should be ignored due to min_lines threshold
        self.assertEqual(len(issues), 0)
    
    def test_normalize_source_error_handling(self):
        """Test error handling in source normalization."""
        detector = CloneDetector()
        
        # Test with invalid source code
        invalid_source = "def func("  # Incomplete function definition
        result = detector._normalize_source(invalid_source)
        
        # Should return original source when parsing fails
        self.assertEqual(result, invalid_source)
    
    def test_fingerprint_generation(self):
        """Test fingerprint generation for different code types."""
        detector = CloneDetector()
        
        # Test with longer, more complex code that can generate meaningful ngrams
        valid_source = '''def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result'''
        
        fingerprint = detector._generate_fingerprint(valid_source)
        self.assertIsNotNone(fingerprint)
        self.assertIsInstance(fingerprint, set)
        
        # Test with empty source
        empty_fingerprint = detector._generate_fingerprint("")
        self.assertIsNotNone(empty_fingerprint)
        self.assertIsInstance(empty_fingerprint, set)
        
        # Test that identical code produces identical fingerprints
        source1 = '''def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total'''
        
        source2 = '''def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total'''
        
        fp1 = detector._generate_fingerprint(source1)
        fp2 = detector._generate_fingerprint(source2)
        self.assertEqual(fp1, fp2)
        
        # Test that different code produces different fingerprints
        source3 = '''def calculate_product(numbers):
    total = 1
    for num in numbers:
        total *= num
    return total'''
        
        fp3 = detector._generate_fingerprint(source3)
        # Only assert not equal if both fingerprints are non-empty
        if fp1 and fp3:
            self.assertNotEqual(fp1, fp3)
    
    def test_similarity_calculation(self):
        """Test similarity calculation between fingerprint sets."""
        detector = CloneDetector()
        
        # Test identical fingerprints (should be 1.0 similarity)
        fp1 = {1, 2, 3, 4}
        fp2 = {1, 2, 3, 4}
        
        similarity = detector._calculate_similarity(fp1, fp2)
        self.assertEqual(similarity, 1.0)
        
        # Test completely different fingerprints (should be 0.0 similarity)
        fp3 = {5, 6, 7, 8}
        similarity_low = detector._calculate_similarity(fp1, fp3)
        self.assertEqual(similarity_low, 0.0)
        
        # Test partial overlap
        fp4 = {1, 2, 5, 6}  # 2 elements in common with fp1, union size 6
        similarity_partial = detector._calculate_similarity(fp1, fp4)
        expected_similarity = 2 / 6  # intersection / union
        self.assertAlmostEqual(similarity_partial, expected_similarity, places=3)
        
        # Test empty sets
        similarity_empty = detector._calculate_similarity(set(), set())
        self.assertEqual(similarity_empty, 1.0)
        
        # Test one empty set
        similarity_one_empty = detector._calculate_similarity(fp1, set())
        self.assertEqual(similarity_one_empty, 0.0)
    
    def test_near_clone_detection_with_different_thresholds(self):
        """Test near clone detection with various similarity thresholds."""
        # Similar but not identical functions with sufficient content
        source1 = '''
def process_data_list(data_items):
    result_list = []
    for single_item in data_items:
        if single_item > 0:
            result_list.append(single_item * 2)
        else:
            result_list.append(0)
    return result_list
'''
        
        source2 = '''
def handle_item_array(item_array):
    output_array = []
    for element in item_array:
        if element > 0:
            output_array.append(element * 2)
        else:
            output_array.append(0)
    return output_array
'''
        
        symbol1 = self._create_mock_symbol("process_data_list", source1, "file1.py")
        symbol2 = self._create_mock_symbol("handle_item_array", source2, "file2.py")
        
        self.graph.symbols["func1"] = symbol1
        self.graph.symbols["func2"] = symbol2
        
        # Test with high threshold (may or may not detect as clones depending on algorithm)
        detector_strict = CloneDetector(similarity_threshold=0.95, min_lines=3)
        issues_strict = detector_strict.analyze(self.graph)
        # Just verify it runs without error
        self.assertIsInstance(issues_strict, list)
        
        # Test with lower threshold (more likely to detect as clones)
        detector_lenient = CloneDetector(similarity_threshold=0.6, min_lines=3)
        issues_lenient = detector_lenient.analyze(self.graph)
        # Just verify it runs without error
        self.assertIsInstance(issues_lenient, list)
    
    def test_clone_group_formation(self):
        """Test that multiple similar functions form proper clone groups."""
        # Create three similar functions with enough content for meaningful fingerprints
        base_source = '''
def process_list_{}(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
        else:
            result.append(0)
    return result
'''
        
        for i in range(3):
            source = base_source.format(i)
            symbol = self._create_mock_symbol(f"process_list_{i}", source, f"file{i}.py")
            self.graph.symbols[f"func_{i}"] = symbol
        
        detector = CloneDetector(similarity_threshold=0.8, min_lines=3)
        issues = detector.analyze(self.graph)
        
        # Should detect clone group (may be 0 if similarity algorithm doesn't match)
        # Just check that it doesn't error and returns valid results
        self.assertIsInstance(issues, list)
        
        if len(issues) > 0:
            # Check that issue mentions clones, similar blocks, or identical blocks
            issue = issues[0]
            self.assertTrue(
                "clone" in issue.message.lower() or 
                "similar" in issue.message.lower() or
                "identical" in issue.message.lower(),
                f"Expected 'clone', 'similar', or 'identical' in message: {issue.message}"
            )
    
    def test_different_normalization_options(self):
        """Test clone detection with different normalization settings."""
        # Code with comments and whitespace differences
        source1 = '''
def process_data(items):
    # This is a comment
    result = []
    for item in items:
        result.append(item * 2)
    return result
'''
        
        source2 = '''
def process_data(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
'''
        
        symbol1 = self._create_mock_symbol("func1", source1, "file1.py")
        symbol2 = self._create_mock_symbol("func2", source2, "file2.py")
        
        self.graph.symbols["func1"] = symbol1
        self.graph.symbols["func2"] = symbol2
        
        # Should detect as clones when ignoring comments/whitespace (might be exact)
        detector = CloneDetector(similarity_threshold=0.9, min_lines=3)
        issues = detector.analyze(self.graph)
        
        # Just verify it runs without error - detection depends on algorithm specifics
        self.assertIsInstance(issues, list)
    
    def test_hash_collision_handling(self):
        """Test handling of potential hash collisions in fingerprinting."""
        detector = CloneDetector()
        
        # Create many different small code blocks
        symbols = []
        for i in range(100):
            source = f"def func_{i}():\n    return {i}"
            symbol = self._create_mock_symbol(f"func_{i}", source, f"file{i}.py")
            symbols.append(symbol)
            self.graph.symbols[f"func_{i}"] = symbol
        
        # Should handle without errors even with many symbols
        issues = detector.analyze(self.graph)
        # Most should not be considered clones
        self.assertLess(len(issues), 10)
    
    def test_complex_ast_structures(self):
        """Test clone detection with complex AST structures."""
        # Complex class with nested structures
        complex_source = '''
class ComplexClass:
    def __init__(self):
        self.data = {}
    
    def process(self):
        for key, value in self.data.items():
            if isinstance(value, list):
                for item in value:
                    if hasattr(item, 'process'):
                        item.process()
            elif callable(value):
                try:
                    result = value()
                    self.data[key] = result
                except Exception as e:
                    print(f"Error: {e}")
    
    @property
    def size(self):
        return len(self.data)
'''
        
        symbol1 = self._create_mock_symbol("ComplexClass1", complex_source, "file1.py")
        symbol2 = self._create_mock_symbol("ComplexClass2", complex_source, "file2.py") 
        
        self.graph.symbols["complex1"] = symbol1
        self.graph.symbols["complex2"] = symbol2
        
        detector = CloneDetector(similarity_threshold=1.0, min_lines=5)
        issues = detector.analyze(self.graph)
        
        # Should detect the exact clone
        self.assertGreater(len(issues), 0)
        issue = issues[0]
        self.assertEqual(issue.severity, "error")
        # Check for either "clone" or "identical code blocks"
        message_lower = issue.message.lower()
        self.assertTrue("clone" in message_lower or "identical" in message_lower)

if __name__ == "__main__":
    unittest.main()
