"""
Suppression system for filtering out false positives.

This module provides functionality to suppress issues based on:
- Inline code comments (# pythonium: ignore, # noqa, etc.)
- Configuration patterns (specific files, functions, issue types)
- Built-in heuristics for common false positives

The suppression system is designed to be flexible and extensible,
allowing users to reduce noise while maintaining detection quality.
"""

import re
import ast
import logging
from typing import List, Set, Dict, Optional, Pattern, Union
from pathlib import Path
from dataclasses import dataclass, field

from .models import Issue, Symbol, Location

logger = logging.getLogger(__name__)


@dataclass
class SuppressionRule:
    """A rule for suppressing issues."""
    pattern: str
    rule_type: str  # 'detector', 'issue', 'file', 'symbol'
    reason: Optional[str] = None
    enabled: bool = True


@dataclass
class SuppressionConfig:
    """Configuration for issue suppression."""
    rules: List[SuppressionRule] = field(default_factory=list)
    inline_comment_patterns: List[str] = field(default_factory=lambda: [
        r'#\s*pythonium:\s*ignore',
        r'#\s*noqa',
        r'#\s*pylint:\s*disable',
        r'#\s*type:\s*ignore',
    ])
    enable_builtin_suppressions: bool = True
    patterns: Optional[Dict[str, List[str]]] = None
    
    def __post_init__(self):
        """Compile regex patterns for performance."""
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.inline_comment_patterns
        ]
        
        # Convert patterns dict to suppression rules
        if self.patterns:
            for category, pattern_list in self.patterns.items():
                for pattern in pattern_list:
                    rule = SuppressionRule(
                        pattern=pattern,
                        rule_type='symbol',
                        reason=f'Built-in suppression for {category}'
                    )
                    self.rules.append(rule)


class SuppressionEngine:
    """
    Engine for filtering out suppressed issues.
    
    This class handles both inline comment-based suppression and
    configuration-based suppression rules. It's designed to be
    efficient and flexible for various suppression scenarios.
    """
    
    def __init__(self, config: SuppressionConfig = None):
        """
        Initialize the suppression engine.
        
        Args:
            config: Suppression configuration
        """
        self.config = config or SuppressionConfig()
        self._file_cache: Dict[Path, List[str]] = {}
        self._inline_suppressions: Dict[str, Set[int]] = {}
        
        # Built-in suppression patterns for common false positives
        self._builtin_suppressions = {
            # Framework and plugin entry points
            'entry_point_functions': [
                r'.*\.main$',
                r'.*\.app$', 
                r'.*\.run$',
                r'.*\.cli$',
                r'.*\.serve$',
            ],
            # Test and example code
            'test_patterns': [
                r'test_.*',
                r'.*_test.*',
                r'.*\.tests\..*',
                r'example_.*',
                r'.*_example.*',
            ],
            # Special methods and framework hooks
            'special_methods': [
                r'.*\.__.*__$',  # Dunder methods
                r'.*\.setup$',
                r'.*\.teardown$',
                r'.*\.configure$',
                r'.*\.initialize$',
            ],
            # MCP and Click decorators
            'decorator_functions': [
                r'.*\.tool$',
                r'.*\.command$',
                r'.*\.group$',
                r'.*\.option$',
            ]
        }
        
        # Compile builtin patterns
        self._compiled_builtins = {}
        for category, patterns in self._builtin_suppressions.items():
            self._compiled_builtins[category] = [
                re.compile(pattern) for pattern in patterns
            ]
    
    def should_suppress_issue(self, issue: Issue, source_lines: Optional[List[str]] = None) -> bool:
        """
        Check if an issue should be suppressed.
        
        Args:
            issue: The issue to check
            source_lines: Source code lines for inline comment checking
            
        Returns:
            True if the issue should be suppressed
        """
        # Check inline comment suppression
        if self._check_inline_suppression(issue, source_lines):
            return True
        
        # Check configuration-based suppression
        if self._check_config_suppression(issue):
            return True
        
        # Check builtin suppression patterns
        if self._check_builtin_suppression(issue):
            return True
        
        return False
    
    def _check_inline_suppression(self, issue: Issue, source_lines: Optional[List[str]]) -> bool:
        """Check for inline comment suppression."""
        if not issue.location or not source_lines:
            return False
        
        # Check current line and previous line for suppression comments
        lines_to_check = []
        
        # Current line
        if issue.location.line <= len(source_lines):
            lines_to_check.append(source_lines[issue.location.line - 1])
        
        # Previous line (for comments above the code)
        if issue.location.line > 1 and issue.location.line - 2 < len(source_lines):
            lines_to_check.append(source_lines[issue.location.line - 2])
        
        for line in lines_to_check:
            for pattern in self.config._compiled_patterns:
                if pattern.search(line):
                    return True
        
        return False
    
    def _check_config_suppression(self, issue: Issue) -> bool:
        """Check for configuration-based suppression."""
        for rule in self.config.rules:
            if not rule.enabled:
                continue
            
            if rule.rule_type == 'detector' and issue.detector_id == rule.pattern:
                return True
            elif rule.rule_type == 'issue' and issue.id == rule.pattern:
                return True
            elif rule.rule_type == 'file' and issue.location:
                if self._matches_file_pattern(str(issue.location.file), rule.pattern):
                    return True
            elif rule.rule_type == 'symbol' and issue.symbol:
                if self._matches_symbol_pattern(issue.symbol.fqname, rule.pattern):
                    return True
        
        return False
    
    def _check_builtin_suppression(self, issue: Issue) -> bool:
        """Check for builtin suppression patterns."""
        if not issue.symbol:
            return False
        
        symbol_name = issue.symbol.fqname
        
        # Check against all builtin pattern categories
        for category, patterns in self._compiled_builtins.items():
            for pattern in patterns:
                if pattern.match(symbol_name):
                    # Special handling for certain issue types
                    if self._should_apply_builtin_suppression(issue, category):
                        return True
        
        return False
    
    def _should_apply_builtin_suppression(self, issue: Issue, category: str) -> bool:
        """Determine if builtin suppression should apply for specific issue/category."""
        # Apply framework suppressions only to dead code issues
        if category in ['entry_point_functions', 'decorator_functions'] and 'unused' in issue.id:
            return True
        
        # Apply special method suppressions to dead code and complexity issues
        if category == 'special_methods' and issue.id in ['unused-symbol', 'complexity-high']:
            return True
        
        # Apply test suppressions to security and dead code issues
        if category == 'test_patterns' and issue.id in ['unused-symbol', 'security-risk']:
            return True
        
        return False
    
    def _matches_file_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches a pattern."""
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)
    
    def _matches_symbol_pattern(self, symbol_name: str, pattern: str) -> bool:
        """Check if symbol name matches a pattern."""
        import fnmatch
        return fnmatch.fnmatch(symbol_name, pattern)
    
    def filter_issues(self, issues: List[Issue], source_files: Optional[Dict[Path, List[str]]] = None) -> List[Issue]:
        """
        Filter a list of issues, removing suppressed ones.
        
        Args:
            issues: List of issues to filter
            source_files: Mapping of file paths to source lines
            
        Returns:
            Filtered list of issues
        """
        filtered = []
        suppressed_count = 0
        
        for issue in issues:
            source_lines = None
            if source_files and issue.location:
                source_lines = source_files.get(issue.location.file)
            
            if self.should_suppress_issue(issue, source_lines):
                suppressed_count += 1
            else:
                filtered.append(issue)
        
        return filtered
    
    def add_suppression_rule(self, rule: SuppressionRule) -> None:
        """Add a new suppression rule."""
        self.config.rules.append(rule)
    
    def load_file_source(self, file_path: Path) -> List[str]:
        """Load and cache source lines for a file."""
        if file_path not in self._file_cache:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._file_cache[file_path] = f.readlines()
            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read file {file_path} for suppression checking: {e}")
                self._file_cache[file_path] = []
        
        return self._file_cache[file_path]


def create_default_suppression_config() -> SuppressionConfig:
    """Create a default suppression configuration with common rules."""
    rules = [
        # Suppress dead code issues in test files
        SuppressionRule(
            pattern='**/test_*.py',
            rule_type='file',
            reason='Test files may have intentionally unused code'
        ),
        SuppressionRule(
            pattern='**/*_test.py',
            rule_type='file',
            reason='Test files may have intentionally unused code'
        ),
        
        # Suppress issues in example and demo code
        SuppressionRule(
            pattern='**/examples/**',
            rule_type='file',
            reason='Example code may be intentionally simple'
        ),
        SuppressionRule(
            pattern='**/demo/**',
            rule_type='file',
            reason='Demo code may be intentionally simple'
        ),
        
        # Suppress certain issues in __init__.py files
        SuppressionRule(
            pattern='**/__init__.py',
            rule_type='file',
            reason='Init files may have imports for API exposure'
        ),
    ]
    
    return SuppressionConfig(rules=rules)
