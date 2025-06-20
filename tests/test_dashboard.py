"""
Tests for the dashboard module.
"""

import unittest
import tempfile
import json
import os
import shutil
import ast
from pathlib import Path

from pythonium.models import Issue, Location, Symbol
from pythonium.dashboard import _prepare_dashboard_data, _generate_html_content, generate_html_report


class TestDashboard(unittest.TestCase):
    """Test cases for the dashboard module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_path = Path(self.temp_dir)
        self.output_path = self.root_path / "report.html"
        
        # Create test file
        self.test_file = self.root_path / "test.py"
        self.test_file.write_text("# test file\ndef test_function():\n    pass\n")
        
        # Create test issues
        # Create Symbol with appropriate parameters for the new Symbol class
        # fqname, ast_node, location
        test_ast_node = ast.parse("def test_function(): pass").body[0]
        self.test_symbol = Symbol(
            fqname="test_module.test_function",
            ast_node=test_ast_node,
            location=Location(self.test_file, 2, 0)
        )
        
        self.test_issues = [
            Issue(
                id="issue-1",
                detector_id="dead_code",
                severity="error",
                message="Error issue",
                location=Location(self.test_file, 1, 1),
                symbol=self.test_symbol
            ),
            Issue(
                id="issue-2",
                detector_id="dead_code",
                severity="warn",
                message="Warning issue",
                location=Location(self.test_file, 2, 5)
            ),
            Issue(
                id="issue-3",
                detector_id="clone",
                severity="info",
                message="Info issue",
                location=Location(self.test_file, 3, 10)
            ),
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_prepare_dashboard_data(self):
        """Test the dashboard data preparation function."""
        data = _prepare_dashboard_data(self.test_issues, self.root_path)
        
        # Verify summary data
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["total_issues"], 3)
        self.assertEqual(data["summary"]["files_affected"], 1)
        
        # Verify severity counts
        self.assertEqual(data["summary"]["severity_counts"]["error"], 1)
        self.assertEqual(data["summary"]["severity_counts"]["warn"], 1)
        self.assertEqual(data["summary"]["severity_counts"]["info"], 1)
        
        # Verify detector counts
        self.assertEqual(data["summary"]["detector_counts"]["dead_code"], 2)
        self.assertEqual(data["summary"]["detector_counts"]["clone"], 1)
        
        # Verify file data
        self.assertEqual(len(data["files"]), 1)
        self.assertEqual(data["files"][0]["name"], "test.py")
        self.assertEqual(data["files"][0]["size"], 3)
        
        # Verify issue data
        test_file_issues = data["files"][0]["issues"]
        self.assertEqual(len(test_file_issues), 3)
        
        # Verify symbol is properly included
        self.assertEqual(test_file_issues[0]["symbol"], "test_module.test_function")
    
    def test_generate_html_content(self):
        """Test HTML content generation."""
        data = _prepare_dashboard_data(self.test_issues, self.root_path)
        html_content = _generate_html_content(data)
        
        # Basic checks for the generated HTML
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("Pythonium Code Health Dashboard", html_content)
        self.assertIn("Total Issues Found", html_content)
        self.assertIn("test.py", html_content)
        
        # Check for charts
        self.assertIn("severityChart", html_content)
        self.assertIn("detectorChart", html_content)
        self.assertIn("treemap", html_content)
        
        # Check dashboard data is included as JSON
        self.assertIn("dashboardData =", html_content)
    
    def test_generate_html_report(self):
        """Test the full HTML report generation function."""
        generate_html_report(self.test_issues, self.output_path, self.root_path)
        
        # Verify file was created
        self.assertTrue(self.output_path.exists())
        
        # Read the content
        content = self.output_path.read_text(encoding='utf-8')
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("Pythonium Code Health Dashboard", content)


if __name__ == "__main__":
    unittest.main()
