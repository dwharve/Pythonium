"""
Tests for the new detectors added in v2.0.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock

from pythonium.models import Symbol, Location, CodeGraph
from pythonium.detectors.deprecated import DeprecatedApiDetector
from pythonium.detectors.security import SecuritySmellDetector
from pythonium.detectors.complexity import ComplexityDetector
from pythonium.detectors.circular import CircularDependencyDetector


class TestDeprecatedApiDetector(unittest.TestCase):
    """Test cases for the DeprecatedApiDetector."""
    
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


class TestSecuritySmellDetector(unittest.TestCase):
    """Test cases for the SecuritySmellDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = SecuritySmellDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "security_smell")
        self.assertEqual(self.detector.name, "Security Smell Detector")
        self.assertIn("security", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)


class TestComplexityDetector(unittest.TestCase):
    """Test cases for the ComplexityDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = ComplexityDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "complexity_hotspot")
        self.assertEqual(self.detector.name, "Complexity Detector")
        self.assertIn("complexity", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_custom_thresholds(self):
        """Test detector with custom thresholds."""
        detector = ComplexityDetector(
            cyclomatic_threshold=15,
            loc_threshold=100
        )
        
        self.assertEqual(detector.cyclomatic_threshold, 15)
        self.assertEqual(detector.loc_threshold, 100)


class TestCircularDependencyDetector(unittest.TestCase):
    """Test cases for the CircularDependencyDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = CircularDependencyDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector basic properties."""
        self.assertEqual(self.detector.id, "circular_deps")
        self.assertEqual(self.detector.name, "Circular Dependency Detector")
        self.assertIn("cycles", self.detector.description.lower())
    
    def test_empty_graph(self):
        """Test detector with empty graph."""
        issues = self.detector._analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_custom_thresholds(self):
        """Test detector with custom thresholds."""
        detector = CircularDependencyDetector(
            max_cycle_length=5,
            high_fanin_threshold=10
        )
        
        self.assertEqual(detector.max_cycle_length, 5)
        self.assertEqual(detector.high_fanin_threshold, 10)


class TestAllNewDetectors(unittest.TestCase):
    """Integration tests for all new v2.0 detectors."""
    
    def test_all_detectors_loadable(self):
        """Test that all new detectors can be instantiated."""
        detectors = [
            DeprecatedApiDetector(),
            SecuritySmellDetector(),
            ComplexityDetector(),
            CircularDependencyDetector()
        ]
        
        # All should have proper IDs
        ids = [d.id for d in detectors]
        expected_ids = ['deprecated_api', 'security_smell', 'complexity_hotspot', 'circular_deps']
        
        for expected_id in expected_ids:
            self.assertIn(expected_id, ids)
    
    def test_all_detectors_analyze(self):
        """Test that all new detectors can run analysis without errors."""
        detectors = [
            DeprecatedApiDetector(),
            SecuritySmellDetector(),
            ComplexityDetector(),
            CircularDependencyDetector()
        ]
        
        graph = CodeGraph()
        
        for detector in detectors:
            # Should not raise an exception
            issues = detector._analyze(graph)
            self.assertIsInstance(issues, list)


if __name__ == '__main__':
    unittest.main()
