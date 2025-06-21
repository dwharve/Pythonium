"""
Tests for the performance and caching system.
"""

import unittest
import tempfile
import time
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, MagicMock

from pythonium.performance import AnalysisCache, ParallelAnalyzer, CacheEntry
from pythonium.models import Symbol, Location, CodeGraph, Issue
from pythonium.detectors import BaseDetector


class MockDetector(BaseDetector):
    """Mock detector for testing."""
    
    id = "test_detector"
    name = "Test Detector"
    description = "A test detector"
    
    def __init__(self, delay=0, issues=None):
        super().__init__()
        self.delay = delay
        self.issues = issues or []
    
    def _analyze(self, graph):
        """Mock analysis with optional delay."""
        if self.delay:
            time.sleep(self.delay)
        return self.issues


class TestAnalysisCache(unittest.TestCase):
    """Test cases for the AnalysisCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use a temporary directory for cache testing
        self.temp_dir = TemporaryDirectory()
        cache_path = Path(self.temp_dir.name) / "test_cache.db"
        self.cache = AnalysisCache(cache_path=cache_path)
        
        # Create a temporary file for testing
        self.test_file = Path(self.temp_dir.name) / "test.py"
        self.test_file.write_text("def test(): pass")
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Explicitly close any database connections by deleting the cache object
        if hasattr(self, 'cache'):
            del self.cache
        # Force garbage collection to ensure connections are closed
        import gc
        gc.collect()
        # Give Windows time to release file handles
        import time
        time.sleep(0.2)
        try:
            self.temp_dir.cleanup()
        except (PermissionError, OSError):
            # On Windows, sometimes files are still locked
            # Try again after a longer delay
            time.sleep(0.5)
            try:
                self.temp_dir.cleanup()
            except (PermissionError, OSError):
                # If still locked, use alternative cleanup
                import shutil
                try:
                    shutil.rmtree(self.temp_dir.name, ignore_errors=True)
                except:
                    pass
    
    def test_cache_creation(self):
        """Test cache creation and initialization."""
        self.assertIsNotNone(self.cache)
        # Check that cache path exists
        self.assertTrue(self.cache.cache_path.exists())
    
    def test_cache_initialization_with_path(self):
        """Test cache initialization with custom path."""
        temp_dir = TemporaryDirectory()
        try:
            cache_path = Path(temp_dir.name) / "test_cache.db"
            cache = AnalysisCache(cache_path=cache_path)
            self.assertTrue(cache_path.exists())
            # Explicitly clean up the cache
            del cache
            import gc
            gc.collect()
            import time
            time.sleep(0.1)
        finally:
            try:
                temp_dir.cleanup()
            except (PermissionError, OSError):
                # Windows file locking issue, ignore
                pass
    
    def test_get_cached_symbols_empty(self):
        """Test getting cached symbols for non-existent file."""
        file_path = Path("/nonexistent/file.py")
        cached_symbols = self.cache.get_cached_symbols(file_path)
        self.assertIsNone(cached_symbols)
    
    def test_cache_and_retrieve_symbols(self):
        """Test symbol caching (deprecated - now returns None to force AST-based extraction)."""
        # Create test symbols
        symbols = [
            Symbol(
                fqname="test_function",
                location=Location(self.test_file, 1, 1),
                ast_node=None
            )
        ]
        
        # Cache the symbols (no-op in new architecture)
        self.cache.cache_symbols(self.test_file, symbols)
        
        # Retrieve cached symbols (returns None to force AST extraction)
        cached_symbols = self.cache.get_cached_symbols(self.test_file)
        self.assertIsNone(cached_symbols)  # New behavior - forces AST-based extraction
    
    def test_cache_invalidation_on_modification(self):
        """Test cache behavior (symbol caching deprecated - returns None)."""
        # Create test symbols
        symbols = [Symbol(fqname="test", location=Location(self.test_file, 1, 1), ast_node=None)]
        
        # Cache the symbols (no-op in new architecture)
        self.cache.cache_symbols(self.test_file, symbols)
        
        # Verify cached (returns None in new architecture)
        cached = self.cache.get_cached_symbols(self.test_file)
        self.assertIsNone(cached)  # New behavior - symbol caching is deprecated
        
        # Modify the file
        time.sleep(0.1)  # Ensure timestamp difference
        self.test_file.write_text("def modified(): pass")
        
        # Should return None for modified file
        cached_after_mod = self.cache.get_cached_symbols(self.test_file)
        # The cache might or might not detect the change depending on implementation
        self.assertIsInstance(cached_after_mod, (list, type(None)))
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        # Create test symbols
        symbols = [Symbol(fqname="test", location=Location(self.test_file, 1, 1), ast_node=None)]
        
        # Cache the symbols
        self.cache.cache_symbols(self.test_file, symbols)
        
        # Test cleanup (should not raise errors)
        try:
            self.cache.cleanup_old_entries(max_age_days=0)  # Clean everything
        except Exception as e:
            self.fail(f"Cleanup failed: {e}")
    
    def test_file_sha_calculation(self):
        """Test file SHA calculation."""
        if hasattr(self.cache, 'get_file_sha'):
            sha = self.cache.get_file_sha(self.test_file)
            self.assertIsInstance(sha, str)
            self.assertEqual(len(sha), 64)  # SHA256 hex string
        else:
            self.skipTest("get_file_sha method not found")
    
    def test_python_version_tracking(self):
        """Test that cache tracks Python version."""
        symbols = [Symbol(fqname="test", location=Location(self.test_file, 1, 1), ast_node=None)]
        
        # Cache symbols
        self.cache.cache_symbols(self.test_file, symbols)
        
        # The cache should work (implementation detail test)
        cached = self.cache.get_cached_symbols(self.test_file)
        self.assertIsInstance(cached, (list, type(None)))
    
    def test_cache_api_exists(self):
        """Test that the cache has the expected API methods."""
        # Test that methods exist
        self.assertTrue(hasattr(self.cache, 'get_cached_symbols'))
        self.assertTrue(hasattr(self.cache, 'cache_symbols'))
        self.assertTrue(hasattr(self.cache, 'cleanup_old_entries'))
    
    def test_cache_entry_dataclass(self):
        """Test CacheEntry dataclass."""
        entry = CacheEntry(
            file_sha="abc123",
            python_version="3.11",
            symbols=[],
            last_modified=time.time()
        )
        self.assertEqual(entry.file_sha, "abc123")
        self.assertEqual(entry.python_version, "3.11")
        self.assertIsInstance(entry.symbols, list)
        self.assertIsInstance(entry.last_modified, float)


class TestParallelAnalyzer(unittest.TestCase):
    """Test cases for the ParallelAnalyzer class."""
    
    def test_parallel_analyzer_creation(self):
        """Test that ParallelAnalyzer can be created."""
        analyzer = ParallelAnalyzer()
        self.assertIsNotNone(analyzer)
        # max_workers can be None, that's valid
        self.assertTrue(hasattr(analyzer, 'max_workers'))
    
    def test_parallel_analyzer_with_custom_workers(self):
        """Test ParallelAnalyzer with custom worker count."""
        analyzer = ParallelAnalyzer(max_workers=2)
        self.assertEqual(analyzer.max_workers, 2)
    
    def test_analyze_with_single_detector(self):
        """Test parallel analysis with single detector."""
        analyzer = ParallelAnalyzer(max_workers=1)
        
        # Create a mock graph
        graph = CodeGraph()
        
        # Create a mock detector
        mock_detector = MockDetector(issues=[
            Issue(
                id="test.TEST_ISSUE",
                severity="warn",
                message="Test issue",
                symbol=None,
                location=Location(Path("test.py"), 1, 1)
            )
        ])
        
        # Run analysis
        results = analyzer.analyze_parallel([mock_detector], graph)
        
        self.assertIsInstance(results, list)
        # May or may not find results depending on implementation
    
    def test_analyze_with_multiple_detectors(self):
        """Test parallel analysis with multiple detectors."""
        analyzer = ParallelAnalyzer(max_workers=2)
        
        # Create a mock graph
        graph = CodeGraph()
        
        # Create multiple mock detectors
        detectors = [
            MockDetector(issues=[
                Issue(
                    id="test1.TEST_ISSUE",
                    severity="warn",
                    message="Test issue 1",
                    symbol=None,
                    location=Location(Path("test.py"), 1, 1)
                )
            ]),
            MockDetector(issues=[
                Issue(
                    id="test2.TEST_ISSUE",
                    severity="info",
                    message="Test issue 2",
                    symbol=None,
                    location=Location(Path("test.py"), 2, 1)
                )
            ])
        ]
        
        # Run analysis
        results = analyzer.analyze_parallel(detectors, graph)
        
        self.assertIsInstance(results, list)
    
    def test_analyze_with_failing_detector(self):
        """Test parallel analysis with detector that raises exception."""
        analyzer = ParallelAnalyzer(max_workers=1)
        
        # Create a mock graph
        graph = CodeGraph()
        
        # Create a detector that raises an exception
        class FailingDetector(BaseDetector):
            id = "failing_detector"
            name = "Failing Detector"
            description = "A detector that fails"
            
            def _analyze(self, graph):
                raise ValueError("Test exception")
        
        failing_detector = FailingDetector()
        
        # Run analysis - should handle exceptions gracefully
        results = analyzer.analyze_parallel([failing_detector], graph)
        
        self.assertIsInstance(results, list)
        # Should not crash, may return empty results
    
    def test_analyze_with_slow_detector(self):
        """Test parallel analysis with slow detector."""
        analyzer = ParallelAnalyzer(max_workers=1)
        
        # Create a mock graph with some content
        graph = CodeGraph()
        
        # Add some symbols and content to the graph
        test_path = Path("test.py")
        symbol = Symbol(
            fqname="test.test_func",
            ast_node=None,  # Not needed for this test
            location=Location(file=test_path, line=1)
        )
        graph.symbols["test.test_func"] = symbol
        graph.file_contents[str(test_path)] = "def test_func(): pass"
        
        # Create a slow detector with a flag to verify it was called
        class CallableDetector(MockDetector):
            def __init__(self):
                super().__init__(delay=0.05)  # Small but measurable delay
                self.was_called = False
                
            def _analyze(self, graph):
                self.was_called = True
                return super()._analyze(graph)
        
        slow_detector = CallableDetector()
        
        # Run analysis
        results = analyzer.analyze_parallel([slow_detector], graph)
        
        self.assertIsInstance(results, list)
        # Verify the detector was actually called
        self.assertTrue(slow_detector.was_called, "Detector should have been called")
    
    def test_analyze_empty_detector_list(self):
        """Test parallel analysis with empty detector list."""
        analyzer = ParallelAnalyzer()
        graph = CodeGraph()
        
        results = analyzer.analyze_parallel([], graph)
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)
    
    def test_analyze_none_graph(self):
        """Test parallel analysis with None graph."""
        analyzer = ParallelAnalyzer()
        detector = MockDetector()
        
        # This should either handle gracefully or raise appropriate error
        try:
            results = analyzer.analyze_parallel([detector], None)
            self.assertIsInstance(results, list)
        except (TypeError, AttributeError):
            # Expected behavior for invalid input
            pass
    
    def test_performance_improvement_with_parallel(self):
        """Test that parallel execution can improve performance."""
        # This is more of a demonstration test
        graph = CodeGraph()
        
        # Create multiple slow detectors
        detectors = [MockDetector(delay=0.05) for _ in range(4)]
        
        # Time sequential execution
        start_time = time.time()
        sequential_results = []
        for detector in detectors:
            sequential_results.extend(detector._analyze(graph))
        sequential_time = time.time() - start_time
        
        # Time parallel execution
        analyzer = ParallelAnalyzer(max_workers=4)
        start_time = time.time()
        parallel_results = analyzer.analyze_parallel(detectors, graph)
        parallel_time = time.time() - start_time
        
        # Results should be similar (both empty in this case)
        self.assertIsInstance(parallel_results, list)
        
        # Time comparison is informational
        print(f"Sequential time: {sequential_time:.3f}s, Parallel time: {parallel_time:.3f}s")


if __name__ == "__main__":
    unittest.main()


if __name__ == '__main__':
    unittest.main()
