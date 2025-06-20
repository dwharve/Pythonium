"""
Tests for the __main__ module entry point.
"""

import unittest
import subprocess
import sys
from pathlib import Path


class TestMainModule(unittest.TestCase):
    """Test cases for the __main__ module entry point."""
    
    def test_main_module_import(self):
        """Test that the main module can be imported."""
        try:
            import pythonium.__main__
            self.assertTrue(hasattr(pythonium.__main__, 'main'))
        except ImportError as e:
            self.fail(f"Failed to import pythonium.__main__: {e}")
    
    def test_main_module_execution(self):
        """Test that the main module can be executed via python -m."""
        # Test with --help flag to avoid full analysis
        result = subprocess.run(
            [sys.executable, "-m", "pythonium", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should exit successfully and show help
        self.assertEqual(result.returncode, 0)
        self.assertIn("pythonium", result.stdout.lower())
        self.assertIn("usage", result.stdout.lower())
    
    def test_main_module_version(self):
        """Test that the main module can show version."""
        result = subprocess.run(
            [sys.executable, "-m", "pythonium", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should exit successfully and show version
        self.assertEqual(result.returncode, 0)
        # Version output should contain version number
        self.assertTrue(len(result.stdout.strip()) > 0)


if __name__ == "__main__":
    unittest.main()
