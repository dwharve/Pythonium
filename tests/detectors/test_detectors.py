"""
Test module for testing the Pythonium detectors.
"""

import os
import tempfile
import unittest
from pathlib import Path


class TestDetectors(unittest.TestCase):
    """Test case for Pythonium detectors."""
    
    def setUp(self):
        """Set up the test environment."""
        # Ensure we're in the project root directory
        self.project_root = Path(__file__).parent.parent
        
        # Create temporary test files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create test files with various patterns
        self._create_test_files()
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_files(self):
        """Create temporary test files for detector testing."""
        # Test file with dead code patterns
        dead_code_content = '''
def used_function():
    """This function is used."""
    return "used"

def unused_function():
    """This function is never called."""
    return "unused"

class UsedClass:
    """This class is used."""
    pass

class UnusedClass:
    """This class is never instantiated."""
    pass

# Use some of the above
instance = UsedClass()
result = used_function()
'''
          # Test file with exact clone patterns
        exact_clone_content = '''
def process_data_v1(data):
    """Process the data."""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def process_data_v2(data):
    """Process the data."""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def different_function(data):
    """This does something completely different."""
    return [item for item in data if item < 0]
'''
        
        # Test file with near clone patterns
        near_clone_content = '''
def calculate_total_price(items):
    """Calculate total price of items."""
    total = 0
    for item in items:
        total += item.price
    return total

def calculate_total_cost(products):
    """Calculate total cost of products."""
    total = 0
    for product in products:
        total += product.cost
    return total

def unrelated_function():
    """This is completely unrelated."""
    return "hello world"
'''
        
        # Create test files
        test_files = [
            ("dead_code_test.py", dead_code_content),
            ("exact_clone_test.py", exact_clone_content),
            ("near_clone_test.py", near_clone_content),
        ]
        
        for filename, content in test_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            self.test_files.append(filepath)
    
    def test_dead_code_detector(self):
        """Test that dead code detector can be loaded and runs without errors."""
        from pythonium.analyzer import Analyzer
        
        # Use a proper root path for the analyzer - the temp directory
        analyzer = Analyzer(root_path=Path(self.temp_dir))
        analyzer.load_default_detectors()
        
        # Check that detectors were loaded
        self.assertGreater(len(analyzer.detectors), 0, "Should load at least one detector")
        
        # Check that dead code detector is present
        detector_ids = list(analyzer.detectors.keys())
        self.assertIn("dead_code", detector_ids, "Dead code detector should be loaded")
        
        # Analyze dead code test file
        dead_code_file = [f for f in self.test_files if "dead_code" in f][0]
        
        # The main test is that analysis completes without errors
        try:
            issues = analyzer.analyze([Path(dead_code_file)])
            # Analysis should complete successfully (even if no issues found)
            self.assertIsInstance(issues, list, "Should return a list of issues")
        except Exception as e:
            self.fail(f"Analysis should not raise an exception: {e}")
        
    def test_multiple_detectors(self):
        """Test multiple detectors working together."""
        from pythonium.analyzer import Analyzer
        
        analyzer = Analyzer(root_path=Path(self.temp_dir))
        analyzer.load_default_detectors()
          # Analyze all test files
        issues = analyzer.analyze([Path(f) for f in self.test_files])
        
        # Test that multiple detectors were loaded and analysis ran successfully
        self.assertGreater(len(analyzer.detectors), 1, "Should load multiple detectors")
        self.assertIsInstance(issues, list, "Should return a list of issues")
    
    def test_detector_performance(self):
        """Test that detectors complete analysis in reasonable time."""
        import time
        from pythonium.analyzer import Analyzer
        
        analyzer = Analyzer(root_path=Path(self.temp_dir))
        analyzer.load_default_detectors()
        
        start_time = time.time()
        issues = analyzer.analyze([Path(f) for f in self.test_files])
        end_time = time.time()
        
        analysis_time = end_time - start_time
        
        # Analysis should complete in under 10 seconds for test files
        self.assertLess(
            analysis_time, 10,
            f"Analysis took {analysis_time:.2f} seconds, which may be too slow"
        )
        
        # Should complete successfully
        self.assertIsInstance(issues, list, "Analysis should return a list")
    
    def test_all_current_detectors_load(self):
        """Test that all current detectors can be loaded successfully."""
        from pythonium.analyzer import Analyzer
        
        analyzer = Analyzer(root_path=self.project_root)
        
        # Load detectors from entry points
        try:
            analyzer.load_detectors_from_entry_points()
        except Exception:
            # If entry points fail, try default detectors
            analyzer.load_default_detectors()
        
        # Should load at least one detector
        self.assertGreater(
            len(analyzer.detectors), 0,
            "Should load at least one detector"
        )        # Check that expected detector types are present
        detector_ids = [d.id for d in analyzer.detectors.values()]
        expected_detectors = ['dead_code']
        
        for expected_id in expected_detectors:
            self.assertIn(
                expected_id, detector_ids,
                f"Expected detector '{expected_id}' should be loaded"
            )
    
    def test_detector_error_handling(self):
        """Test that detectors handle errors gracefully."""
        from pythonium.analyzer import Analyzer
        from pythonium.detectors.dead_code import DeadCodeDetector
        
        analyzer = Analyzer(root_path=self.project_root)
        analyzer.register_detector(DeadCodeDetector())
        
        # Test with non-existent file (should not crash)
        non_existent_file = os.path.join(self.temp_dir, "non_existent.py")
        issues = analyzer.analyze([non_existent_file])
        
        # Should return empty list without crashing
        self.assertIsInstance(issues, list)
        
        # Test with invalid Python file
        invalid_file = os.path.join(self.temp_dir, "invalid.py")
        with open(invalid_file, 'w') as f:
            f.write("invalid python syntax $$$ !!!")
        
        # Should handle gracefully
        issues = analyzer.analyze([invalid_file])
        self.assertIsInstance(issues, list)


if __name__ == "__main__":
    unittest.main()
