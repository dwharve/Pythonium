"""
Tests for the new suppression, deduplication, and filtering systems.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pythonium.models import Issue, Symbol, Location, CodeGraph
from pythonium.suppression import SuppressionEngine, SuppressionConfig, SuppressionRule
from pythonium.deduplication import DeduplicationEngine, IssueGroup
from pythonium.filtering import OutputFilter, FilterConfig


class TestSuppressionEngine(unittest.TestCase):
    """Test the issue suppression system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = SuppressionEngine()
        
        # Create a test symbol
        self.symbol = Symbol(
            fqname="test.module.TestClass.test_method",
            ast_node=Mock(),
            location=Location(Path("test.py"), 10),
        )
        
        # Create a test issue
        self.issue = Issue(
            id="unused-symbol",
            severity="warn",
            message="Symbol is defined but never used",
            symbol=self.symbol,
            detector_id="dead_code"
        )
    
    def test_builtin_suppression_entry_points(self):
        """Test that entry point functions are suppressed."""
        # Test main function
        main_symbol = Symbol(
            fqname="app.main",
            ast_node=Mock(),
            location=Location(Path("app.py"), 5),
        )
        main_issue = Issue(
            id="unused-symbol",
            severity="warn", 
            message="Function 'main' is defined but never used",
            symbol=main_symbol,
            detector_id="dead_code"
        )
        
        should_suppress = self.engine.should_suppress_issue(main_issue)
        self.assertTrue(should_suppress, "Main function should be suppressed")
    
    def test_builtin_suppression_dunder_methods(self):
        """Test that dunder methods are suppressed."""
        dunder_symbol = Symbol(
            fqname="test.MyClass.__enter__",
            ast_node=Mock(),
            location=Location(Path("test.py"), 15),
        )
        dunder_issue = Issue(
            id="unused-symbol",
            severity="warn",
            message="Method '__enter__' is defined but never used",
            symbol=dunder_symbol,
            detector_id="dead_code"
        )
        
        should_suppress = self.engine.should_suppress_issue(dunder_issue)
        self.assertTrue(should_suppress, "Dunder methods should be suppressed")
    
    def test_inline_comment_suppression(self):
        """Test inline comment suppression."""
        source_lines = [
            "def test_function():  # pythonium: ignore",
            "    pass",
        ]
        
        # Update issue to have correct line number (1-indexed)
        self.issue.location = Location(Path("test.py"), 1)  # First line
        
        should_suppress = self.engine.should_suppress_issue(self.issue, source_lines)
        self.assertTrue(should_suppress, "Issues with inline comments should be suppressed")
    
    def test_config_rule_suppression(self):
        """Test configuration-based suppression rules."""
        config = SuppressionConfig(rules=[
            SuppressionRule(
                pattern="test.*",
                rule_type="symbol",
                reason="Test symbols"
            )
        ])
        engine = SuppressionEngine(config)
        
        should_suppress = engine.should_suppress_issue(self.issue)
        self.assertTrue(should_suppress, "Issues matching config rules should be suppressed")
    
    def test_no_suppression(self):
        """Test that regular issues are not suppressed."""
        regular_symbol = Symbol(
            fqname="business.logic.calculate",
            ast_node=Mock(),
            location=Location(Path("business.py"), 20),
        )
        regular_issue = Issue(
            id="unused-symbol",
            severity="warn",
            message="Function 'calculate' is defined but never used",
            symbol=regular_symbol,
            detector_id="dead_code"
        )
        
        should_suppress = self.engine.should_suppress_issue(regular_issue)
        self.assertFalse(should_suppress, "Regular business logic should not be suppressed")


class TestDeduplicationEngine(unittest.TestCase):
    """Test the issue deduplication system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = DeduplicationEngine()
        
        # Create test symbols
        self.symbol1 = Symbol(
            fqname="test.unused_function",
            ast_node=Mock(),
            location=Location(Path("test.py"), 10),
        )
        
        # Create duplicate issues for the same symbol
        self.issue1 = Issue(
            id="unused-symbol",
            severity="warn",
            message="Function is defined but never used",
            symbol=self.symbol1,
            detector_id="dead_code"
        )
        
        self.issue2 = Issue(
            id="unused-symbol",  # Same issue type to trigger deduplication
            severity="info",
            message="Code is not referenced anywhere",
            symbol=self.symbol1,
            detector_id="static_analysis"
        )
    
    def test_deduplication_same_symbol(self):
        """Test deduplication of issues for the same symbol."""
        issues = [self.issue1, self.issue2]
        
        deduplicated, groups = self.engine.deduplicate_issues(issues)
        
        self.assertEqual(len(deduplicated), 1, "Should deduplicate to one issue")
        self.assertEqual(len(groups), 1, "Should create one duplicate group")
        self.assertEqual(groups[0].total_count, 2, "Group should contain both issues")
        
        # Should prefer dead_code detector
        self.assertEqual(deduplicated[0].detector_id, "dead_code")
    
    def test_no_deduplication_different_symbols(self):
        """Test that different symbols are not deduplicated."""
        symbol2 = Symbol(
            fqname="test.another_function",
            ast_node=Mock(),
            location=Location(Path("test.py"), 20),
        )
        
        issue3 = Issue(
            id="unused-symbol",
            severity="warn",
            message="Another function is unused",
            symbol=symbol2,
            detector_id="dead_code"
        )
        
        issues = [self.issue1, issue3]
        
        deduplicated, groups = self.engine.deduplicate_issues(issues)
        
        self.assertEqual(len(deduplicated), 2, "Different symbols should not be deduplicated")
        self.assertEqual(len(groups), 0, "No duplicate groups should be created")
    
    def test_priority_selection(self):
        """Test that higher priority detector is selected."""
        # Create issues with different detectors
        high_priority = Issue(
            id="security-risk",
            severity="error",
            message="Security issue",
            symbol=self.symbol1,
            detector_id="security_smell"
        )
        
        low_priority = Issue(
            id="security-risk",
            severity="warn", 
            message="Security issue",
            symbol=self.symbol1,
            detector_id="other_detector"
        )
        
        issues = [low_priority, high_priority]
        
        deduplicated, groups = self.engine.deduplicate_issues(issues)
        
        # Should prefer security_smell detector (higher priority)
        self.assertEqual(deduplicated[0].detector_id, "security_smell")


class TestOutputFilter(unittest.TestCase):
    """Test the output filtering system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = FilterConfig(
            min_confidence=0.5,
            min_severity="info",  # Accept all severities for testing
            max_total_issues=10
        )
        self.filter = OutputFilter(self.config)
        
        # Create test issues with different properties
        self.issues = [
            Issue(
                id="security-risk",
                severity="error",
                message="Critical security issue",
                detector_id="security_smell",
                metadata={"confidence": 0.9}
            ),
            Issue(
                id="minor-issue",
                severity="info", 
                message="Minor style issue",
                detector_id="style_checker",
                metadata={"confidence": 0.3}
            ),
            Issue(
                id="complexity-issue",
                severity="warn",
                message="Function is complex",
                detector_id="complexity_hotspot",
                metadata={"confidence": 0.8}
            ),
        ]
    
    def test_confidence_filtering(self):
        """Test filtering by confidence threshold."""
        filtered, stats = self.filter.filter_issues(self.issues)
        
        # Should filter out the low-confidence AND info-level issue
        self.assertEqual(len(filtered), 1)  # Only the high-confidence warn+ issue remains
        self.assertEqual(stats.filtered_by_confidence, 1)
        
        # Remaining issues should have high confidence  
        for issue in filtered:
            confidence = issue.metadata.get("confidence", 1.0)
            self.assertGreaterEqual(confidence, 0.5)
    
    def test_severity_filtering(self):
        """Test filtering by severity level."""
        # Only keep warnings and errors
        filtered, stats = self.filter.filter_issues(self.issues)
        
        # Should filter out info-level issues
        severities = [issue.severity for issue in filtered]
        self.assertNotIn("info", severities)
    
    def test_total_limit(self):
        """Test total issue limit."""
        # Create many high-confidence, high-severity issues
        many_issues = []
        for i in range(20):
            issue = Issue(
                id="test-issue",
                severity="error",
                message=f"Issue {i}",
                detector_id="test_detector",
                metadata={"confidence": 0.9}
            )
            many_issues.append(issue)
        
        filtered, stats = self.filter.filter_issues(many_issues)
        
        # Should limit to max_total_issues
        self.assertLessEqual(len(filtered), self.config.max_total_issues)
        # If we have more issues than the limit, some should be filtered
        if len(many_issues) > self.config.max_total_issues:
            # Either by total limit or other filters
            total_removed = stats.filtered_by_total_limit + stats.filtered_by_noise_reduction
            self.assertGreater(total_removed, 0, f"Expected some filtering but got stats: {stats}")
    
    def test_priority_preservation(self):
        """Test that high-priority issues are preserved."""
        # Add priority detector to config
        self.config.priority_detectors = ["security_smell"]
        
        filtered, stats = self.filter.filter_issues(self.issues)
        
        # Security issue should be preserved even if filtered
        detector_ids = [issue.detector_id for issue in filtered]
        self.assertIn("security_smell", detector_ids)


if __name__ == "__main__":
    unittest.main()
