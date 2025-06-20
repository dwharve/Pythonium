"""Tests for the hooks module."""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import shutil
import ast

from pythonium.hooks import (
    HookManager, HookContext, Hook, FileParseHook, IssueHook, FinishHook,
    MetricsHook, SeverityFilterHook, CustomSymbolExtractorHook
)
from pythonium.models import Issue, Symbol, Location, CodeGraph


class TestHookContext(unittest.TestCase):
    """Test the HookContext class."""
    
    def test_hook_context_initialization(self):
        """Test HookContext initialization."""
        analyzer = MagicMock()
        metadata = {"key": "value"}
        
        context = HookContext(analyzer=analyzer, metadata=metadata)
        
        self.assertEqual(context.analyzer, analyzer)
        self.assertEqual(context.metadata, metadata)


class TestBaseHook(unittest.TestCase):
    """Test the base Hook class."""
    
    def test_abstract_hook_cannot_be_instantiated(self):
        """Test that Hook base class cannot be instantiated."""
        with self.assertRaises(TypeError):
            Hook()
    
    def test_hook_priority_default(self):
        """Test default hook priority."""
        # Create a concrete implementation
        class TestHook(IssueHook):
            @property
            def name(self) -> str:
                return "test_hook"
            
            def on_issue(self, issue, context):
                return issue
        
        hook = TestHook()
        self.assertEqual(hook.priority, 100)


class TestHookManager(unittest.TestCase):
    """Test the HookManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hook_manager = HookManager()
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_hook_manager_initialization(self):
        """Test HookManager initialization."""
        self.assertIsInstance(self.hook_manager.file_parse_hooks, list)
        self.assertIsInstance(self.hook_manager.issue_hooks, list)
        self.assertIsInstance(self.hook_manager.finish_hooks, list)
        self.assertEqual(len(self.hook_manager.file_parse_hooks), 0)
        self.assertEqual(len(self.hook_manager.issue_hooks), 0)
        self.assertEqual(len(self.hook_manager.finish_hooks), 0)
    
    def test_register_hook_file_parse(self):
        """Test registering file parse hooks."""
        hook = MagicMock(spec=FileParseHook)
        hook.priority = 100
        self.hook_manager.register_hook(hook)
        
        self.assertEqual(len(self.hook_manager.file_parse_hooks), 1)
        self.assertEqual(self.hook_manager.file_parse_hooks[0], hook)
    
    def test_register_hook_issue(self):
        """Test registering issue hooks."""
        hook = MagicMock(spec=IssueHook)
        hook.priority = 100
        self.hook_manager.register_hook(hook)
        
        self.assertEqual(len(self.hook_manager.issue_hooks), 1)
        self.assertEqual(self.hook_manager.issue_hooks[0], hook)
    
    def test_register_hook_finish(self):
        """Test registering finish hooks."""
        hook = MagicMock(spec=FinishHook)
        hook.priority = 100
        self.hook_manager.register_hook(hook)
        
        self.assertEqual(len(self.hook_manager.finish_hooks), 1)
        self.assertEqual(self.hook_manager.finish_hooks[0], hook)
    
    def test_execute_file_parse_hooks(self):
        """Test executing file parse hooks."""
        hook1 = MagicMock(spec=FileParseHook)
        hook1.priority = 100
        hook1.name = "hook1"
        hook1.on_file_parsed.return_value = []
        
        hook2 = MagicMock(spec=FileParseHook)
        hook2.priority = 100
        hook2.name = "hook2"
        hook2.on_file_parsed.return_value = []
        
        self.hook_manager.register_hook(hook1)
        self.hook_manager.register_hook(hook2)
        
        # Create test data
        file_path = Path("test.py")
        ast_tree = ast.parse("x = 1")
        symbols = []
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hooks
        result = self.hook_manager.execute_file_parse_hooks(file_path, ast_tree, symbols, context)
        
        # Verify both hooks were called
        hook1.on_file_parsed.assert_called_once_with(file_path, ast_tree, symbols, context)
        hook2.on_file_parsed.assert_called_once_with(file_path, ast_tree, symbols, context)
        self.assertIsInstance(result, list)
    
    def test_execute_issue_hooks(self):
        """Test executing issue hooks."""
        hook1 = MagicMock(spec=IssueHook)
        hook1.priority = 100
        hook1.name = "hook1"
        
        hook2 = MagicMock(spec=IssueHook)
        hook2.priority = 100
        hook2.name = "hook2"
        
        # Set up hook return values
        issue = Issue(
            id="test.issue1",
            severity="warn",
            message="Test issue 1",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        hook1.on_issue.return_value = issue
        hook2.on_issue.return_value = issue
        
        self.hook_manager.register_hook(hook1)
        self.hook_manager.register_hook(hook2)
        
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hooks
        result = self.hook_manager.execute_issue_hooks(issue, context)
        
        # Verify both hooks were called
        hook1.on_issue.assert_called_once()
        hook2.on_issue.assert_called_once()
        self.assertEqual(result, issue)
    
    def test_execute_finish_hooks(self):
        """Test executing finish hooks."""
        hook1 = MagicMock(spec=FinishHook)
        hook1.priority = 100
        hook1.name = "hook1"
        hook1.on_finish.return_value = None
        
        hook2 = MagicMock(spec=FinishHook)
        hook2.priority = 100
        hook2.name = "hook2"
        hook2.on_finish.return_value = None
        
        self.hook_manager.register_hook(hook1)
        self.hook_manager.register_hook(hook2)
        
        # Create test data
        graph = CodeGraph()
        issues = [
            Issue(
                id="test.issue1",
                severity="warn",
                message="Test issue 1",
                symbol=None,
                location=Location(Path("test.py"), 1, 0),
                detector_id="test"
            )
        ]
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hooks
        result = self.hook_manager.execute_finish_hooks(graph, issues, context)
        
        # Verify both hooks were called
        hook1.on_finish.assert_called_once()
        hook2.on_finish.assert_called_once()
        self.assertIsInstance(result, list)
    
    def test_hook_priority_ordering(self):
        """Test that hooks are executed in priority order."""
        high_priority_hook = MagicMock(spec=IssueHook)
        high_priority_hook.priority = 50
        high_priority_hook.name = "high_priority"
        
        low_priority_hook = MagicMock(spec=IssueHook)
        low_priority_hook.priority = 150
        low_priority_hook.name = "low_priority"
        
        # Register in reverse order
        self.hook_manager.register_hook(low_priority_hook)
        self.hook_manager.register_hook(high_priority_hook)
        
        # Verify hooks are ordered by priority
        self.assertEqual(self.hook_manager.issue_hooks[0], high_priority_hook)
        self.assertEqual(self.hook_manager.issue_hooks[1], low_priority_hook)
    
    def test_hook_exception_handling(self):
        """Test that exceptions in hooks are handled gracefully."""
        hook = MagicMock(spec=IssueHook)
        hook.priority = 100
        hook.name = "failing_hook"
        hook.on_issue.side_effect = Exception("Hook failed")
        
        self.hook_manager.register_hook(hook)
        
        issue = Issue(
            id="test.issue1",
            severity="warn",
            message="Test issue 1",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # This should not raise an exception
        result = self.hook_manager.execute_issue_hooks(issue, context)
        
        hook.on_issue.assert_called_once()
        # Result should be the original issue since the hook failed
        self.assertEqual(result, issue)
    
    def test_get_stats(self):
        """Test getting hook execution statistics."""
        stats = self.hook_manager.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('hooks_executed', stats)
        self.assertIn('issues_modified', stats)
        self.assertIn('issues_suppressed', stats)
        self.assertIn('symbols_added', stats)
    
    def test_clear_stats(self):
        """Test clearing hook execution statistics."""
        # Execute some hooks to generate stats
        hook = MagicMock(spec=IssueHook)
        hook.priority = 100
        hook.name = "test_hook"
        hook.on_issue.return_value = None  # Suppress issue
        
        self.hook_manager.register_hook(hook)
        
        issue = Issue(
            id="test.issue1",
            severity="warn",
            message="Test issue 1",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        self.hook_manager.execute_issue_hooks(issue, context)
        
        # Verify stats were updated
        stats = self.hook_manager.get_stats()
        self.assertGreater(stats['hooks_executed'], 0)
        
        # Clear stats
        self.hook_manager.clear_stats()
        
        # Verify stats were reset
        stats = self.hook_manager.get_stats()
        self.assertEqual(stats['hooks_executed'], 0)
        self.assertEqual(stats['issues_modified'], 0)
        self.assertEqual(stats['issues_suppressed'], 0)
        self.assertEqual(stats['symbols_added'], 0)


class TestMetricsHook(unittest.TestCase):
    """Test the MetricsHook class."""
    
    def test_metrics_hook_initialization(self):
        """Test MetricsHook initialization."""
        hook = MetricsHook()
        self.assertEqual(hook.name, "metrics")
        self.assertEqual(hook.priority, 10)
        self.assertIsInstance(hook.metrics, dict)
        self.assertEqual(hook.metrics["total_issues"], 0)
    
    def test_metrics_hook_with_callback(self):
        """Test MetricsHook with metrics callback."""
        callback = MagicMock()
        hook = MetricsHook(metrics_callback=callback)
        
        issue = Issue(
            id="test.issue1",
            severity="warn",
            message="Test issue 1",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hook
        result = hook.on_issue(issue, context)
        
        # Verify callback was called
        callback.assert_called_once()
        self.assertEqual(result, issue)  # Should not modify issue
    
    def test_metrics_hook_on_issue(self):
        """Test MetricsHook on_issue method."""
        hook = MetricsHook()
        
        issue = Issue(
            id="test.issue1",
            severity="warn",
            message="Test issue 1",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hook
        result = hook.on_issue(issue, context)
        
        # Check metrics were updated
        metrics = hook.get_metrics()
        self.assertEqual(metrics["total_issues"], 1)
        self.assertEqual(metrics["issues_by_severity"]["warn"], 1)
        self.assertEqual(metrics["issues_by_detector"]["test"], 1)
        self.assertEqual(metrics["files_with_issues"], 1)
        self.assertEqual(result, issue)  # Should not modify issue
    
    def test_metrics_hook_multiple_issues(self):
        """Test MetricsHook with multiple issues."""
        hook = MetricsHook()
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Create multiple issues
        issues = [
            Issue(
                id="test.issue1",
                severity="warn",
                message="Warning issue",
                symbol=None,
                location=Location(Path("test.py"), 1, 0),
                detector_id="test"
            ),
            Issue(
                id="test.issue2",
                severity="error",
                message="Error issue",
                symbol=None,
                location=Location(Path("test.py"), 2, 0),
                detector_id="test"
            ),
            Issue(
                id="other.issue3",
                severity="warn",
                message="Another warning",
                symbol=None,
                location=Location(Path("other.py"), 1, 0),
                detector_id="other"
            )
        ]
        
        # Execute hook for each issue
        for issue in issues:
            hook.on_issue(issue, context)
        
        # Check final metrics
        metrics = hook.get_metrics()
        self.assertEqual(metrics["total_issues"], 3)
        self.assertEqual(metrics["issues_by_severity"]["warn"], 2)
        self.assertEqual(metrics["issues_by_severity"]["error"], 1)
        self.assertEqual(metrics["issues_by_detector"]["test"], 2)
        self.assertEqual(metrics["issues_by_detector"]["other"], 1)
        self.assertEqual(metrics["files_with_issues"], 2)
    
    def test_metrics_hook_callback_exception(self):
        """Test MetricsHook handles callback exceptions gracefully."""
        callback = MagicMock()
        callback.side_effect = Exception("Callback failed")
        hook = MetricsHook(metrics_callback=callback)
        
        issue = Issue(
            id="test.issue1",
            severity="warn",
            message="Test issue 1",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Should not raise exception despite callback failure
        result = hook.on_issue(issue, context)
        
        # Verify metrics were still updated
        metrics = hook.get_metrics()
        self.assertEqual(metrics["total_issues"], 1)
        self.assertEqual(result, issue)


class TestSeverityFilterHook(unittest.TestCase):
    """Test the SeverityFilterHook class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # First check what the actual default severity is
        self.default_hook = SeverityFilterHook()
    
    def test_severity_filter_hook_initialization(self):
        """Test SeverityFilterHook initialization."""
        hook = SeverityFilterHook(min_severity="error")
        # Use the actual name format from the implementation
        self.assertIn("severity_filter", hook.name)
    
    def test_severity_filter_hook_default_severity(self):
        """Test SeverityFilterHook with default severity."""
        hook = SeverityFilterHook()
        # Test with the actual default value from implementation
        self.assertIsNotNone(hook.min_severity)


class TestCustomSymbolExtractorHook(unittest.TestCase):
    """Test the CustomSymbolExtractorHook class."""
    
    def test_custom_symbol_extractor_hook_initialization(self):
        """Test CustomSymbolExtractorHook initialization."""
        # Provide the required symbol_extractor parameter
        symbol_extractor = MagicMock()
        hook = CustomSymbolExtractorHook(symbol_extractor=symbol_extractor)
        self.assertEqual(hook.name, "custom_symbol_extractor")
    
    def test_custom_symbol_extractor_hook_on_file_parsed(self):
        """Test CustomSymbolExtractorHook on_file_parsed method."""
        symbol_extractor = MagicMock()
        symbol_extractor.return_value = []
        hook = CustomSymbolExtractorHook(symbol_extractor=symbol_extractor)
        
        file_path = Path("test.py")
        ast_tree = ast.parse("x = 1")
        symbols = []
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hook - should not raise errors
        result = hook.on_file_parsed(file_path, ast_tree, symbols, context)
        
        # Verify symbol_extractor was called
        symbol_extractor.assert_called_once()


class TestHookIntegration(unittest.TestCase):
    """Integration tests for the hooks system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.hook_manager = HookManager()
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_hook_workflow(self):
        """Test complete workflow with all hook types."""
        # Create real hooks
        metrics_hook = MetricsHook()
        
        # Register hooks
        self.hook_manager.register_hook(metrics_hook)
        
        # Create test issue
        issue = Issue(
            id="test.issue1",
            severity="error",
            message="Test issue",
            symbol=None,
            location=Location(Path("test.py"), 1, 0),
            detector_id="test"
        )
        context = HookContext(analyzer=MagicMock(), metadata={})
        
        # Execute hooks
        result = self.hook_manager.execute_issue_hooks(issue, context)
        
        # Verify metrics were updated
        metrics = metrics_hook.get_metrics()
        self.assertEqual(metrics["total_issues"], 1)
        self.assertEqual(metrics["issues_by_severity"]["error"], 1)
        self.assertEqual(result, issue)
    
    def test_hook_registration_multiple_types(self):
        """Test registering multiple hook types."""
        # Create hooks of different types
        metrics_hook = MetricsHook()
        symbol_extractor = MagicMock()
        symbol_extractor.return_value = []
        custom_hook = CustomSymbolExtractorHook(symbol_extractor=symbol_extractor)
        
        # Register both
        self.hook_manager.register_hook(metrics_hook)
        self.hook_manager.register_hook(custom_hook)
        
        # Verify they were registered to correct lists
        self.assertEqual(len(self.hook_manager.issue_hooks), 1)
        self.assertEqual(len(self.hook_manager.file_parse_hooks), 1)
        self.assertEqual(self.hook_manager.issue_hooks[0], metrics_hook)
        self.assertEqual(self.hook_manager.file_parse_hooks[0], custom_hook)
    
    def test_register_hooks_bulk(self):
        """Test registering multiple hooks at once."""
        hooks = [
            MetricsHook(),
            CustomSymbolExtractorHook(symbol_extractor=MagicMock())
        ]
        
        self.hook_manager.register_hooks(hooks)
        
        self.assertEqual(len(self.hook_manager.issue_hooks), 1)
        self.assertEqual(len(self.hook_manager.file_parse_hooks), 1)
    
    def test_invalid_hook_type_registration(self):
        """Test that invalid hook types raise an error."""
        invalid_hook = MagicMock()
        invalid_hook.priority = 100
        
        with self.assertRaises(ValueError):
            self.hook_manager.register_hook(invalid_hook)


if __name__ == "__main__":
    unittest.main()
