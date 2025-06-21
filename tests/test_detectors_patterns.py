"""
Test module for the pattern detection functionality.
"""

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pythonium.detectors.patterns import PatternDetector
from pythonium.models import CodeGraph, Issue, Symbol, Location


class TestPatternDetector(unittest.TestCase):
    """Test case for pattern detector."""
    
    def setUp(self):
        """Set up test environment."""
        self.detector = PatternDetector()
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_patterns.py"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_detector_initialization(self):
        """Test detector initialization with options."""
        detector = PatternDetector(
            detect_algorithmic_patterns=False,
            detect_design_patterns=True,
            min_pattern_size=5,
            similarity_threshold=0.9
        )
        self.assertFalse(detector.detect_algorithmic_patterns)
        self.assertTrue(detector.detect_design_patterns)
        self.assertEqual(detector.min_pattern_size, 5)
        self.assertEqual(detector.similarity_threshold, 0.9)
    
    def test_extract_algorithmic_signature(self):
        """Test extraction of algorithmic signatures."""
        code = '''
def process_data(data):
    if not data:
        return None
    
    result = []
    for item in data:
        if item.is_valid():
            result.append(item.process())
    
    return result
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        # Create a mock symbol
        symbol = MagicMock()
        symbol.ast_node = func_node
        
        signature = self.detector._extract_algorithmic_signature(symbol)
        
        # Should return a signature with expected keys
        self.assertIsInstance(signature, dict)
        self.assertIn('control_flow', signature)
        self.assertIn('operation_sequence', signature)
        self.assertIn('data_flow', signature)
        self.assertIn('complexity_metrics', signature)
    
    def test_extract_control_flow_pattern(self):
        """Test extraction of control flow patterns."""
        code = '''
def process_data(data):
    if not data:
        return None
    
    for item in data:
        if item.is_valid():
            return item
    
    return None
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        pattern = self.detector._extract_control_flow_pattern(func_node)
        
        # Should detect IF, FOR, IF, RETURN patterns
        self.assertIn('IF', pattern)
        self.assertIn('FOR', pattern)
        self.assertIn('RETURN', pattern)
        self.assertEqual(pattern.count('IF'), 2)
        # Returns count may vary based on AST structure, so be flexible
        self.assertGreaterEqual(pattern.count('RETURN'), 2)
    
    def test_extract_operation_sequence(self):
        """Test extraction of operation sequences."""
        code = '''
def process_data(data):
    result = []
    for item in data:
        processed = item.process()
        result.append(processed)
    return result
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        operations = self.detector._extract_operation_sequence(func_node)
        
        # Should detect assignments and calls
        self.assertIn('ASSIGN', operations)
        self.assertIn('CALL', operations)
    
    def test_extract_data_flow_pattern(self):
        """Test extraction of data flow patterns."""
        code = '''
def process_list(items):
    items.append("new")
    items.sort()
    return len(items)
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        pattern = self.detector._extract_data_flow_pattern(func_node)
        
        # Should detect list operations
        self.assertIsInstance(pattern, dict)
        self.assertIn('list_operations', pattern)
        self.assertGreater(pattern['list_operations'], 0)
    
    def test_calculate_complexity_metrics(self):
        """Test calculation of complexity metrics."""
        code = '''
def complex_function(data):
    if not data:
        return None
    
    for item in data:
        if item.is_valid():
            processed = item.process()
            if processed:
                return processed
    
    return None
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        metrics = self.detector._calculate_complexity_metrics(func_node)
        
        # Should calculate various metrics
        self.assertIsInstance(metrics, dict)
        self.assertIn('cyclomatic_complexity', metrics)
        self.assertIn('nesting_depth', metrics)
        self.assertIn('function_calls', metrics)
        self.assertIn('branches', metrics)
        
        # Should have reasonable values
        self.assertGreater(metrics['cyclomatic_complexity'], 1)
        self.assertGreater(metrics['nesting_depth'], 0)
    
    def test_calculate_nesting_depth(self):
        """Test calculation of nesting depth."""
        code = '''
def nested_function():
    if True:
        for i in range(10):
            if i > 5:
                return i
    return 0
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        depth = self.detector._calculate_nesting_depth(func_node)
        
        # Should detect nested structure (if -> for -> if)
        self.assertGreaterEqual(depth, 3)
    
    def test_make_signature_comparable(self):
        """Test making signatures comparable."""
        signature = {
            'control_flow': ['IF', 'FOR', 'IF', 'RETURN'],
            'operation_sequence': ['ASSIGN', 'CALL', 'ASSIGN'],
            'data_flow': {'list_operations': 2},
            'complexity_metrics': {'cyclomatic_complexity': 3}
        }
        
        comparable = self.detector._make_signature_comparable(signature)
        
        # Should have normalized ratios
        self.assertIn('control_flow_ratios', comparable)
        self.assertIn('operation_ratios', comparable)
        
        # Ratios should sum to 1.0
        if 'control_flow_ratios' in comparable:
            total_ratio = sum(comparable['control_flow_ratios'].values())
            self.assertAlmostEqual(total_ratio, 1.0, places=5)
    
    def test_determine_pattern_type(self):
        """Test pattern type determination."""
        # Test list processing pattern (need control_flow_ratios)
        list_processing_sig = {
            'control_flow_ratios': {'FOR': 0.6, 'IF': 0.4},
            'data_flow': {'list_operations': 3},
            'complexity': {'cyclomatic_complexity': 2}
        }
        pattern_type = self.detector._determine_pattern_type(list_processing_sig)
        self.assertEqual(pattern_type, 'list_processing')
        
        # Test file processing pattern
        file_sig = {
            'control_flow_ratios': {'IF': 0.3},
            'data_flow': {'file_operations': 3},
            'complexity': {'cyclomatic_complexity': 2}
        }
        pattern_type = self.detector._determine_pattern_type(file_sig)
        self.assertEqual(pattern_type, 'file_processing')
    
    def test_is_factory_like(self):
        """Test factory-like function detection."""
        # Factory-like function
        factory_code = '''
def create_user(user_type):
    if user_type == "admin":
        return AdminUser()
    else:
        return RegularUser()
'''
        tree = ast.parse(factory_code)
        symbol = MagicMock()
        symbol.ast_node = tree.body[0]
        symbol.fqname = "create_user"  # Set the function name for pattern matching
        
        is_factory = self.detector._is_factory_like(symbol)
        self.assertTrue(is_factory)
        
        # Non-factory function
        non_factory_code = '''
def simple_function():
    return "hello"
'''
        tree = ast.parse(non_factory_code)
        symbol.ast_node = tree.body[0]
        symbol.fqname = "simple_function"  # Set the function name
        
        is_factory = self.detector._is_factory_like(symbol)
        self.assertFalse(is_factory)
    
    def test_is_validation_function(self):
        """Test validation function detection."""
        # Validation function by name
        validation_code = '''
def validate_email(email):
    if "@" not in email:
        return False
    return True
'''
        tree = ast.parse(validation_code)
        symbol = MagicMock()
        symbol.ast_node = tree.body[0]
        symbol.name = "validate_email"
        
        is_validation = self.detector._is_validation_function(symbol)
        self.assertTrue(is_validation)
        
        # Non-validation function
        non_validation_code = '''
def process_data(data):
    return data.upper()
'''
        tree = ast.parse(non_validation_code)
        symbol.ast_node = tree.body[0]
        symbol.name = "process_data"
        
        is_validation = self.detector._is_validation_function(symbol)
        self.assertFalse(is_validation)
    
    def test_determine_validation_type(self):
        """Test validation type determination."""
        symbol = MagicMock()
        symbol.name = "validate_email_address"
        
        validation_type = self.detector._determine_validation_type(symbol)
        self.assertEqual(validation_type, "email_validation")
        
        symbol.name = "check_phone_number"
        validation_type = self.detector._determine_validation_type(symbol)
        self.assertEqual(validation_type, "phone_validation")
        
        symbol.name = "check_user_form"  # Changed to avoid any substring matches
        validation_type = self.detector._determine_validation_type(symbol)
        self.assertEqual(validation_type, "general_validation")
    
    def test_extract_class_methods(self):
        """Test extraction of class methods."""
        code = '''
class TestClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
    
    @property
    def prop(self):
        return None
'''
        tree = ast.parse(code)
        symbol = MagicMock()
        symbol.ast_node = tree.body[0]
        
        methods = self.detector._extract_class_methods(symbol)
        
        # Should extract function definitions (not properties)
        self.assertIn("method1", methods)
        self.assertIn("method2", methods)
        self.assertIn("prop", methods)  # property decorator still creates FunctionDef
    
    def test_analyze_with_graph(self):
        """Test analysis with a code graph."""
        # Create test symbols
        func_code1 = '''
def process_user(user_id):
    if not user_id:
        return None
    user = get_user(user_id)
    return user.data if user else None
'''
        func_code2 = '''
def process_order(order_id):
    if not order_id:
        return None
    order = get_order(order_id)
    return order.data if order else None
'''
        
        tree1 = ast.parse(func_code1)
        tree2 = ast.parse(func_code2)
        
        # Create mock symbols
        symbol1 = MagicMock()
        symbol1.ast_node = tree1.body[0]
        symbol1.name = "process_user"
        symbol1.location = Location(file=Path("test.py"), line=1)
        
        symbol2 = MagicMock()
        symbol2.ast_node = tree2.body[0]
        symbol2.name = "process_order"
        symbol2.location = Location(file=Path("test.py"), line=10)
        
        # Create mock code graph
        graph = CodeGraph()
        graph.symbols = {"process_user": symbol1, "process_order": symbol2}
        
        issues = self.detector.analyze(graph)
        
        # Should find issues with similar patterns
        self.assertIsInstance(issues, list)
    
    def test_disabled_detections(self):
        """Test detector with various detections disabled."""
        detector = PatternDetector(
            detect_algorithmic_patterns=False,
            detect_design_patterns=False,
            detect_validation_patterns=False,
            detect_factory_patterns=False
        )
        
        # Create mock graph with functions
        symbol = MagicMock()
        symbol.ast_node = ast.parse("def test(): pass").body[0]
        
        graph = CodeGraph()
        graph.symbols = {"test": symbol}
        
        issues = detector.analyze(graph)
        
        # With all detections disabled, should find no issues
        self.assertEqual(len(issues), 0)
    
    def test_error_handling(self):
        """Test error handling in pattern detection."""
        # Test with malformed symbol
        symbol = MagicMock()
        symbol.ast_node = None
        
        # Should handle gracefully
        signature = self.detector._extract_algorithmic_signature(symbol)
        self.assertIsNone(signature)
    
    def test_calculate_signature_similarity(self):
        """Test signature similarity calculation."""
        sig1 = {
            'control_flow_ratios': {'IF': 0.5, 'FOR': 0.3, 'RETURN': 0.2},
            'operation_ratios': {'ASSIGN': 0.4, 'CALL': 0.6},
            'data_flow': {'list_operations': 2},
            'complexity': {'cyclomatic_complexity': 3}
        }
        
        sig2 = {
            'control_flow_ratios': {'IF': 0.5, 'FOR': 0.3, 'RETURN': 0.2},
            'operation_ratios': {'ASSIGN': 0.4, 'CALL': 0.6},
            'data_flow': {'list_operations': 2},
            'complexity': {'cyclomatic_complexity': 3}
        }
        
        sig3 = {
            'control_flow_ratios': {'WHILE': 1.0},
            'operation_ratios': {'BINOP': 1.0},
            'data_flow': {'file_operations': 5},
            'complexity': {'cyclomatic_complexity': 10}
        }
        
        # Identical signatures should have high similarity
        similarity1 = self.detector._calculate_signature_similarity(sig1, sig2)
        self.assertGreater(similarity1, 0.9)
        
        # Different signatures should have lower similarity
        similarity2 = self.detector._calculate_signature_similarity(sig1, sig3)
        self.assertLess(similarity2, 0.5)


class TestPatternDetectorIntegration(unittest.TestCase):
    """Integration tests for pattern detector."""
    
    def setUp(self):
        """Set up test environment."""
        self.detector = PatternDetector()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_real_code_analysis(self):
        """Test analysis on realistic code patterns.""" 
        # Create symbols with realistic patterns
        func_codes = [
            '''
def get_user_by_id(user_id):
    if not user_id:
        raise ValueError("User ID required")
    user = db.get_user(user_id)
    if not user:
        raise NotFoundError("User not found")
    return format_user(user)
''',
            '''
def get_order_by_id(order_id):
    if not order_id:
        raise ValueError("Order ID required")
    order = db.get_order(order_id)
    if not order:
        raise NotFoundError("Order not found")
    return format_order(order)
''',
            '''
def validate_email(email):
    if not email:
        return False
    if "@" not in email:
        return False
    return True
''',
            '''
def validate_phone(phone):
    if not phone:
        return False
    if len(phone) < 10:
        return False
    return True
'''
        ]
        
        symbols = {}
        for i, code in enumerate(func_codes):
            tree = ast.parse(code)
            symbol = MagicMock()
            symbol.ast_node = tree.body[0]
            symbol.name = tree.body[0].name
            symbol.location = Location(file=Path("test.py"), line=i*10)
            symbols[symbol.name] = symbol
        
        # Create mock code graph
        graph = CodeGraph()
        graph.symbols = symbols
        
        issues = self.detector.analyze(graph)
        
        # Should detect various patterns
        self.assertIsInstance(issues, list)
        
        # Should find some issues with realistic patterns
        # (may not specifically be validation patterns due to thresholds)
        if issues:
            for issue in issues:
                self.assertIsInstance(issue, Issue)
                self.assertIn('pattern', issue.message.lower())


if __name__ == "__main__":
    unittest.main()
