"""
Tests for the settings and configuration system.
"""

import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from pythonium.settings import Settings


class TestSettings(unittest.TestCase):
    """Test cases for the Settings class."""
    
    def test_default_settings(self):
        """Test that default settings are created properly."""
        settings = Settings()
        
        # Check default thresholds
        self.assertEqual(settings.thresholds['complexity_cyclomatic'], 10)
        self.assertEqual(settings.thresholds['clone_similarity'], 0.9)
        self.assertEqual(settings.thresholds['clone_min_lines'], 5)
        
        # Check default ignored paths
        self.assertIn('**/tests/**', settings.ignored_paths)
        self.assertIn('**/__pycache__/**', settings.ignored_paths)
    
    def test_from_dict(self):
        """Test creating settings from a dictionary."""
        config = {
            'severity': {
                'dead_code': 'error',
                'clone': 'warn'
            },
            'options': {
                'dead_code': {
                    'entry_points': ['custom_main']
                },
                'clone': {
                    'similarity_threshold': 0.8
                }
            },
            'ignored_paths': ['**/custom/**']
        }
        
        settings = Settings.from_dict(config)
        
        # Check overridden severities
        self.assertEqual(settings.severity_overrides['dead_code'], 'error')
        self.assertEqual(settings.severity_overrides['clone'], 'warn')
        
        # Check detector options
        self.assertEqual(settings.get_detector_setting('dead_code', 'entry_points'), ['custom_main'])
        self.assertEqual(settings.get_detector_setting('clone', 'similarity_threshold'), 0.8)
        
        # Check ignored paths
        self.assertIn('**/custom/**', settings.ignored_paths)
    
    def test_get_detector_severity(self):
        """Test getting detector severity with fallback."""
        settings = Settings()
        
        # Test unknown detector without override (should return None)
        self.assertIsNone(settings.get_severity_override('unknown'))
        
        # Add a severity override and test
        settings.severity_overrides['test_detector'] = 'error'
        self.assertEqual(settings.get_severity_override('test_detector'), 'error')
    
    def test_get_detector_options(self):
        """Test getting detector options."""
        config = {
            'options': {
                'dead_code': {
                    'entry_points': ['main', 'app:main']
                }
            }
        }
        
        settings = Settings.from_dict(config)
        
        # Test getting existing options
        entry_points = settings.get_detector_setting('dead_code', 'entry_points')
        self.assertEqual(entry_points, ['main', 'app:main'])
        
        # Test getting non-existent options
        nonexistent = settings.get_detector_setting('nonexistent', 'some_option', 'default')
        self.assertEqual(nonexistent, 'default')
    
    def test_should_ignore_path(self):
        """Test path ignore functionality."""
        settings = Settings()
        
        # Test paths that should be ignored
        self.assertTrue(settings.is_path_ignored(Path('some/tests/test_file.py')))  # matches **/tests/**
        self.assertTrue(settings.is_path_ignored(Path('src/__pycache__/module.pyc')))  # matches **/__pycache__/**
        self.assertTrue(settings.is_path_ignored(Path('src/test_module.py')))  # matches **/test_*.py
        
        # Test paths that should not be ignored
        self.assertFalse(settings.is_path_ignored(Path('src/main.py')))
        self.assertFalse(settings.is_path_ignored(Path('pythonium/analyzer.py')))


if __name__ == '__main__':
    unittest.main()
