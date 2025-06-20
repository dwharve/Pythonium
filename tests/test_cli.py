"""
Test module for the CLI functionality.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import io


class TestCLI(unittest.TestCase):
    """Test case for CLI functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_code.py"
        
        # Create a simple test file
        test_content = '''
def test_function():
    """A test function."""
    return "hello"

def unused_function():
    """This function is not used."""
    return "unused"

# Use test_function
result = test_function()
'''
        self.test_file.write_text(test_content)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_import(self):
        """Test that CLI module can be imported."""
        from pythonium import cli
        self.assertIsNotNone(cli)
    
    def test_cli_main_function_exists(self):
        """Test that main function exists."""
        from pythonium.cli import main
        self.assertIsNotNone(main)
    
    def test_cli_functions_exist(self):
        """Test that CLI functions exist."""
        from pythonium.cli import crawl, list_detectors, init_config
        self.assertIsNotNone(crawl)
        self.assertIsNotNone(list_detectors)
        self.assertIsNotNone(init_config)
    
    def test_cli_config_loading(self):
        """Test config loading function."""
        from pythonium.cli import load_config
        
        # Test loading config from non-existent file
        config = load_config(Path("/non/existent/config.yml"))
        self.assertIsInstance(config, dict)
    
    def test_cli_format_issue(self):
        """Test issue formatting function."""
        from pythonium.cli import format_issue
        from pythonium.models import Issue, Location
        
        # Create a test issue
        location = Location(file=Path("test.py"), line=10)
        issue = Issue(
            id="test.issue",
            severity="warn",
            message="Test issue message",
            location=location,
            detector_id="test_detector"
        )
        
        formatted = format_issue(issue)
        self.assertIsInstance(formatted, str)
        self.assertIn("test.py", formatted)
        self.assertIn("Test issue message", formatted)
    
    def test_create_default_config(self):
        """Test default config creation."""
        from pythonium.cli import create_default_config
        
        # Test in temp directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            config_path = create_default_config()
            self.assertIsInstance(config_path, Path)
            self.assertTrue(config_path.exists())
        finally:
            os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
