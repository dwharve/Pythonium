"""
Extended tests for the CLI functionality to improve coverage.
"""

import tempfile
import unittest
import json
import yaml
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import io
import click
from click.testing import CliRunner

from pythonium.cli import (
    load_config, create_default_config, get_or_create_config,
    find_project_root, format_issue, cli
)
from pythonium.models import Issue, Location, Symbol
import pythonium.cli as cli_module


class TestCLIExtended(unittest.TestCase):
    """Extended test cases for CLI functionality to improve coverage."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.test_file = self.temp_path / "test_code.py"
        
        # Create a simple test file
        test_content = '''
def test_function():
    """A test function."""
    return "hello"

def unused_function():
    """This function is not used."""
    return "unused"
'''
        self.test_file.write_text(test_content)
        
        # Create a runner for CLI tests
        self.runner = CliRunner()
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_with_file(self):
        """Test loading config from an existing file."""
        config_path = self.temp_path / ".pythonium.yml"
        config_content = """
detectors:
  - dead_code
  - clone
exclude:
  - "*/tests/*"
        """
        config_path.write_text(config_content)
        
        # Load the config
        config = load_config(config_path)
        
        # Verify config content
        self.assertIn("detectors", config)
        self.assertIn("dead_code", config["detectors"])
        self.assertIn("exclude", config)

    def test_load_config_auto_create(self):
        """Test auto-creating config if not exists."""
        config_path = self.temp_path / ".pythonium.yml"
        
        # Ensure file doesn't exist
        if config_path.exists():
            config_path.unlink()
        
        # Change working directory to temp path
        with patch('pathlib.Path.cwd', return_value=self.temp_path):
            config = load_config(auto_create=True)
            
            # Verify file was created
            self.assertTrue(config_path.exists())
            
            # Load and verify content
            with open(config_path) as f:
                content = f.read()
                self.assertIn("detectors:", content)
    
    def test_create_default_config(self):
        """Test creating default config file."""
        config_path = self.temp_path / ".pythonium.yml"
        
        # Create default config
        create_default_config(config_path)
        
        # Verify file exists
        self.assertTrue(config_path.exists())
        
        # Load and verify content
        with open(config_path) as f:
            content = f.read()
            self.assertIn("detectors:", content)
    
    def test_get_or_create_config(self):
        """Test getting or creating config."""
        # Create config file
        config_path = self.temp_path / ".pythonium.yml"
        config_content = """
detectors:
  - dead_code
        """
        config_path.write_text(config_content)
        
        # Get the config - pass a Path object instead of None
        with patch('os.getcwd', return_value=str(self.temp_path)):
            config = get_or_create_config(self.temp_path)
            
            # Verify config was loaded
            self.assertIn("detectors", config)
            self.assertIn("dead_code", config["detectors"])
    
    def test_find_project_root(self):
        """Test finding project root."""
        # Create a fake project structure
        project_root = self.temp_path / "project"
        project_root.mkdir()
        (project_root / ".git").mkdir()
        (project_root / "src").mkdir()
        test_file = project_root / "src" / "test.py"
        test_file.touch()
        
        # Find project root
        found_root = find_project_root(test_file)
        
        # Verify root was found correctly
        self.assertEqual(found_root, project_root)
    
    def test_format_issue(self):
        """Test formatting an issue for display."""
        # Create test issue
        test_file = self.temp_path / "test.py"
        test_file.touch()
        
        issue = Issue(
            id="test-issue-1",
            detector_id="dead_code",
            severity="error",
            message="Test error message",
            location=Location(test_file, 10, 5)
        )
        
        # Format the issue
        formatted = format_issue(issue)
        
        # Verify format
        self.assertIn(str(test_file), formatted)
        self.assertIn("10:5", formatted)
        self.assertIn("error", formatted)
        self.assertIn("Test error message", formatted)
    
    def test_main_help(self):
        """Test main function shows help."""
        runner = CliRunner()
        result = runner.invoke(cli_module.cli, ['--help'])
        
        # Verify help output was generated
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Pythonium Crawler", result.output)
        self.assertIn("Options:", result.output)
        self.assertIn("Commands:", result.output)
    
    @patch('pythonium.cli.cli.invoke')
    def test_version_command(self, mock_invoke):
        """Test version command."""
        from pythonium.version import __version__
        
        # Use CliRunner to test click commands
        runner = CliRunner()
        result = runner.invoke(cli_module.version)
        
        # Verify version was shown
        self.assertIn(f"Pythonium Crawler v{__version__}", result.output)

    @patch('pythonium.cli.Analyzer')
    def test_list_detectors_command(self, mock_analyzer):
        """Test list-detectors command."""
        # Setup mock analyzer
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.list_detectors.return_value = {
            "dead_code": {
                "name": "Dead Code Detector",
                "description": "Finds unused code",
                "type": "core"
            },
            "clone": {
                "name": "Clone Detector",
                "description": "Finds code duplicates",
                "type": "core"
            }
        }
        mock_analyzer.return_value = mock_analyzer_instance
        
        # Use CliRunner to test click commands
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create config file
            with open('.pythonium.yml', 'w') as f:
                f.write('detectors: [dead_code]\n')
            
            result = runner.invoke(cli_module.list_detectors, obj={"config": {}})
            
            # Verify output
            self.assertIn("Available detectors:", result.output)
            self.assertIn("dead_code", result.output)
            self.assertIn("clone", result.output)

    def test_create_sarif_report(self):
        """Test creating SARIF report from issues."""
        # Create test issues
        test_file = self.temp_path / "test.py"
        test_file.touch()
        
        issues = [
            Issue(
                id="test-issue-1",
                detector_id="dead_code",
                severity="error",
                message="Test error message",
                location=Location(test_file, 10, 5)
            ),
            Issue(
                id="test-issue-2",
                detector_id="clone",
                severity="warn",  # Use valid severity: info, warn, error
                message="Test warning message",
                location=Location(test_file, 20, 10)
            )
        ]
          # Create SARIF report
        sarif_report = cli_module._create_sarif_report(issues, self.temp_path)
        
        # Verify SARIF report structure
        self.assertEqual(sarif_report["$schema"], "https://json.schemastore.org/sarif-2.1.0.json")
        self.assertEqual(sarif_report["version"], "2.1.0")
        self.assertIn("runs", sarif_report)
        self.assertEqual(len(sarif_report["runs"]), 1)
        
        run = sarif_report["runs"][0]
        self.assertIn("tool", run)
        self.assertIn("results", run)
        self.assertEqual(len(run["results"]), 2)

    def test_analyze_command_basic(self):
        """Test basic analyze command functionality."""
        # Test analyze command with minimal arguments
        result = self.runner.invoke(cli, ['crawl', str(self.test_file)])
        
        # Should complete without errors
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_with_output_formats(self):
        """Test analyze command with different output formats."""        # Test JSON output
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file),
            '--format', 'json'
        ])
        self.assertEqual(result.exit_code, 0)
          # Test SARIF output
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file), 
            '--format', 'sarif'
        ])
        self.assertEqual(result.exit_code, 0)
        
        # Test HTML output
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file), 
            '--format', 'html'
        ])
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_with_specific_detectors(self):
        """Test analyze command with specific detector selection."""
        # Test with specific detectors
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file),
            '--detectors', 'dead_code,clone'
        ])
        self.assertEqual(result.exit_code, 0)
        
        # Test with single detector
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file),
            '--detectors', 'dead_code'
        ])
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_with_silent_mode(self):
        """Test analyze command with silent mode."""
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file),
            '--silent'
        ])
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_with_config_file(self):
        """Test analyze command with custom config file."""
        # Create a custom config file
        config_file = self.temp_path / "custom_config.yml"
        config_content = """
detectors:
  dead_code:
    enabled: true
  clone:
    enabled: false
"""
        with open(config_file, 'w') as f:
            f.write(config_content)        
        result = self.runner.invoke(cli, [
            '--config', str(config_file),
            'crawl', str(self.test_file)
        ])
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_with_output_file(self):
        """Test analyze command with output file."""
        output_file = self.temp_path / "output.json"
        
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file),
            '--format', 'json',
            '--output', str(output_file)
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(output_file.exists())
    
    def test_analyze_command_with_directory(self):
        """Test analyze command with directory input."""
        # Create additional test files in the directory
        (self.temp_path / "module1.py").write_text("def func1(): pass")
        (self.temp_path / "module2.py").write_text("def func2(): pass")
        
        result = self.runner.invoke(cli, [
            'crawl', str(self.temp_path)
        ])
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_with_exclude_patterns(self):
        """Test analyze command with exclude patterns."""
        # Create files that should be excluded
        (self.temp_path / "test_exclude.py").write_text("def test(): pass")
        (self.temp_path / "__pycache__").mkdir()
        (self.temp_path / "__pycache__" / "cache.pyc").write_text("cache")
        
        result = self.runner.invoke(cli, [
            'crawl', str(self.temp_path)
        ])
        self.assertEqual(result.exit_code, 0)
    
    def test_analyze_command_error_handling(self):
        """Test analyze command error handling."""
        # Test with non-existent file
        result = self.runner.invoke(cli, [
            'crawl', '/nonexistent/file.py'
        ])
        self.assertNotEqual(result.exit_code, 0)    
    def test_crawl_command_with_additional_options(self):
        """Test crawl command with additional options."""
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file),
            '--fail-on', 'warn'
        ])
        self.assertEqual(result.exit_code, 0)
    
    @patch('pythonium.cli.Analyzer')
    def test_analyze_command_with_mocked_analyzer(self, mock_analyzer):
        """Test analyze command with mocked analyzer for better control."""
        # Mock the analyzer to return predictable results
        mock_instance = MagicMock()
        mock_analyzer.return_value = mock_instance
        mock_instance.analyze.return_value = []
        
        result = self.runner.invoke(cli, [
            'crawl', str(self.test_file)
        ])
        self.assertEqual(result.exit_code, 0)
        mock_instance.analyze.assert_called_once()
    
    def test_cli_format_issue(self):
        """Test the format_issue function."""
        # Create a test issue
        location = Location(Path("test.py"), 10, 5)
        symbol = Symbol(
            fqname="test.function",
            location=location,
            ast_node=None
        )
        issue = Issue(
            id="test.TEST_ISSUE",
            severity="warn",
            message="Test issue message",
            symbol=symbol,
            location=location        )
        
        # Test format_issue function
        formatted = format_issue(issue)
        self.assertIsInstance(formatted, str)
        self.assertIn("test.py", formatted)
        self.assertIn("Test issue message", formatted)
    
    def test_cli_config_loading_edge_cases(self):
        """Test config loading edge cases."""
        # Test loading config from non-existent file
        config = load_config("/nonexistent/config.yml")
        self.assertIsInstance(config, dict)
        
        # Test loading malformed YAML
        malformed_config = self.temp_path / "malformed.yml"
        malformed_config.write_text("invalid: yaml: content: [")
        
        config = load_config(str(malformed_config))
        self.assertIsInstance(config, dict)
    
    def test_find_project_root_edge_cases(self):
        """Test find_project_root with various scenarios."""
        # Test with a directory that has no project markers
        temp_subdir = self.temp_path / "subdir"
        temp_subdir.mkdir()
        
        root = find_project_root(temp_subdir)
        self.assertIsInstance(root, Path)
          # Test with a file as input
        root = find_project_root(self.test_file)
        self.assertIsInstance(root, Path)
    
    def test_create_default_config_functionality(self):
        """Test create_default_config function."""
        config_path = self.temp_path / "test_config.yml"
        created_path = create_default_config(config_path)
        self.assertIsInstance(created_path, Path)
        self.assertTrue(config_path.exists())
        
        # Verify the config file content
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('detectors:', content)
        self.assertIn('dead_code:', content)
    
    def test_get_or_create_config_scenarios(self):
        """Test get_or_create_config in various scenarios."""
        # Test with existing config file
        config_file = self.temp_path / ".pythonium.yml"
        config_content = {'test': 'value'}
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        config = get_or_create_config(self.temp_path)
        self.assertIsInstance(config, dict)
        
        # Test with directory that has no config
        new_dir = self.temp_path / "new_dir"
        new_dir.mkdir()
        
        config = get_or_create_config(new_dir)
        self.assertIsInstance(config, dict)

if __name__ == "__main__":
    unittest.main()
