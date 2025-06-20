"""
Extensibility hooks for the Pythonium Crawler.

This module provides the hook system for extending
the crawler with custom functionality:
- on_file_parsed: Called after each file is parsed
- on_issue: Called when a detector yields an issue
- on_finish: Called before reporters run

These hooks enable custom symbol extractors, real-time metrics,
custom aggregation, and other extensions.
"""

import ast
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Union
from dataclasses import dataclass

from .models import CodeGraph, Issue, Symbol

logger = logging.getLogger(__name__)


@dataclass
class HookContext:
    """Context information passed to hooks."""
    analyzer: Any  # Analyzer instance
    metadata: Dict[str, Any]


class Hook(ABC):
    """Base class for all hooks."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Hook name for identification."""
        pass
    
    @property
    def priority(self) -> int:
        """Hook priority (lower numbers run first)."""
        return 100


class FileParseHook(Hook):
    """Hook called after a file is parsed."""
    
    @abstractmethod
    def on_file_parsed(
        self, 
        file_path: Path, 
        ast_tree: ast.AST, 
        symbols: List[Symbol],
        context: HookContext
    ) -> Optional[List[Symbol]]:
        """
        Called after a file is parsed.
        
        Args:
            file_path: Path to the parsed file
            ast_tree: Parsed AST tree
            symbols: Symbols extracted from the file
            context: Hook context
            
        Returns:
            Optional list of additional symbols to add to the graph
        """
        pass


class IssueHook(Hook):
    """Hook called when a detector yields an issue."""
    
    @abstractmethod
    def on_issue(self, issue: Issue, context: HookContext) -> Optional[Issue]:
        """
        Called immediately when a detector yields an issue.
        
        Args:
            issue: The issue that was found
            context: Hook context
            
        Returns:
            Optional modified issue (or None to suppress the issue)
        """
        pass


class FinishHook(Hook):
    """Hook called before reporters run."""
    
    @abstractmethod
    def on_finish(
        self, 
        graph: CodeGraph, 
        issues: List[Issue], 
        context: HookContext
    ) -> Optional[List[Issue]]:
        """
        Called before reporters run.
        
        Args:
            graph: Complete code graph
            issues: All issues found by detectors
            context: Hook context
            
        Returns:
            Optional modified list of issues
        """
        pass


class HookManager:
    """
    Manages and executes extensibility hooks.
    
    Provides registration and execution of hooks at various points
    in the analysis pipeline.
    """
    
    def __init__(self):
        """Initialize the hook manager."""
        self.file_parse_hooks: List[FileParseHook] = []
        self.issue_hooks: List[IssueHook] = []
        self.finish_hooks: List[FinishHook] = []
        
        # Statistics
        self.stats = {
            'hooks_executed': 0,
            'issues_modified': 0,
            'issues_suppressed': 0,
            'symbols_added': 0,
        }
    
    def register_hook(self, hook: Hook):
        """
        Register a hook.
        
        Args:
            hook: Hook instance to register
        """
        if isinstance(hook, FileParseHook):
            self.file_parse_hooks.append(hook)
            self.file_parse_hooks.sort(key=lambda h: h.priority)
        elif isinstance(hook, IssueHook):
            self.issue_hooks.append(hook)
            self.issue_hooks.sort(key=lambda h: h.priority)
        elif isinstance(hook, FinishHook):
            self.finish_hooks.append(hook)
            self.finish_hooks.sort(key=lambda h: h.priority)
        else:
            raise ValueError(f"Unknown hook type: {type(hook)}")
        
        logger.debug("Registered hook: %s (priority: %d)", hook.name, hook.priority)
    
    def register_hooks(self, hooks: List[Hook]):
        """Register multiple hooks."""
        for hook in hooks:
            self.register_hook(hook)
    
    def execute_file_parse_hooks(
        self, 
        file_path: Path, 
        ast_tree: ast.AST, 
        symbols: List[Symbol],
        context: HookContext
    ) -> List[Symbol]:
        """
        Execute file parse hooks.
        
        Args:
            file_path: Path to the parsed file
            ast_tree: Parsed AST tree
            symbols: Symbols extracted from the file
            context: Hook context
            
        Returns:
            Combined list of symbols (original + any added by hooks)
        """
        all_symbols = list(symbols)
        
        for hook in self.file_parse_hooks:
            try:
                self.stats['hooks_executed'] += 1
                additional_symbols = hook.on_file_parsed(file_path, ast_tree, symbols, context)
                
                if additional_symbols:
                    all_symbols.extend(additional_symbols)
                    self.stats['symbols_added'] += len(additional_symbols)
                    logger.debug("Hook %s added %d symbols for %s", 
                               hook.name, len(additional_symbols), file_path)
                
            except Exception as e:
                logger.error("File parse hook %s failed for %s: %s", hook.name, file_path, e)
        
        return all_symbols
    
    def execute_issue_hooks(self, issue: Issue, context: HookContext) -> Optional[Issue]:
        """
        Execute issue hooks.
        
        Args:
            issue: Issue to process
            context: Hook context
            
        Returns:
            Modified issue or None if suppressed
        """
        current_issue = issue
        
        for hook in self.issue_hooks:
            try:
                self.stats['hooks_executed'] += 1
                result = hook.on_issue(current_issue, context)
                
                if result is None:
                    # Issue was suppressed
                    self.stats['issues_suppressed'] += 1
                    logger.debug("Hook %s suppressed issue: %s", hook.name, issue.id)
                    return None
                elif result != current_issue:
                    # Issue was modified
                    current_issue = result
                    self.stats['issues_modified'] += 1
                    logger.debug("Hook %s modified issue: %s", hook.name, issue.id)
                
            except Exception as e:
                logger.error("Issue hook %s failed for issue %s: %s", hook.name, issue.id, e)
        
        return current_issue
    
    def execute_finish_hooks(
        self, 
        graph: CodeGraph, 
        issues: List[Issue], 
        context: HookContext
    ) -> List[Issue]:
        """
        Execute finish hooks.
        
        Args:
            graph: Complete code graph
            issues: All issues found
            context: Hook context
            
        Returns:
            Modified list of issues
        """
        current_issues = list(issues)
        
        for hook in self.finish_hooks:
            try:
                self.stats['hooks_executed'] += 1
                result = hook.on_finish(graph, current_issues, context)
                
                if result is not None:
                    if len(result) != len(current_issues):
                        diff = len(result) - len(current_issues)
                        if diff > 0:
                            self.stats['symbols_added'] += diff
                        else:
                            self.stats['issues_suppressed'] += abs(diff)
                    
                    current_issues = result
                    logger.debug("Hook %s processed %d issues, returned %d", 
                               hook.name, len(issues), len(result))
                
            except Exception as e:
                logger.error("Finish hook %s failed: %s", hook.name, e)
        
        return current_issues
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hook execution statistics."""
        return dict(self.stats)
    
    def clear_stats(self):
        """Clear hook execution statistics."""
        self.stats = {
            'hooks_executed': 0,
            'issues_modified': 0,
            'issues_suppressed': 0,
            'symbols_added': 0,
        }


# Built-in hooks for common functionality

class MetricsHook(IssueHook):
    """Hook that collects real-time metrics about issues."""
    
    def __init__(self, metrics_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize metrics hook.
        
        Args:
            metrics_callback: Optional callback function for metrics
        """
        self.metrics_callback = metrics_callback
        self.metrics = {
            'total_issues': 0,
            'issues_by_severity': {'error': 0, 'warn': 0, 'info': 0},
            'issues_by_detector': {},
            'files_with_issues': set(),
        }
    
    @property
    def name(self) -> str:
        return "metrics"
    
    @property
    def priority(self) -> int:
        return 10  # Run early
    
    def on_issue(self, issue: Issue, context: HookContext) -> Optional[Issue]:
        """Collect metrics from issues."""
        self.metrics['total_issues'] += 1
        
        # Count by severity
        severity = issue.severity.lower()
        if severity in self.metrics['issues_by_severity']:
            self.metrics['issues_by_severity'][severity] += 1
        
        # Count by detector
        detector_id = issue.detector_id or 'unknown'
        self.metrics['issues_by_detector'][detector_id] = \
            self.metrics['issues_by_detector'].get(detector_id, 0) + 1
        
        # Track files with issues
        if issue.location and issue.location.file:
            self.metrics['files_with_issues'].add(str(issue.location.file))
        
        # Call metrics callback if provided
        if self.metrics_callback:
            try:
                self.metrics_callback(self.get_metrics())
            except Exception as e:
                logger.warning("Metrics callback failed: %s", e)
        
        return issue  # Don't modify the issue
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        metrics = dict(self.metrics)
        metrics['files_with_issues'] = len(self.metrics['files_with_issues'])
        return metrics


class SeverityFilterHook(IssueHook):
    """Hook that filters issues based on severity level."""
    
    def __init__(self, min_severity: str = "info"):
        """
        Initialize severity filter hook.
        
        Args:
            min_severity: Minimum severity level to include ("error", "warn", "info")
        """
        self.min_severity = min_severity.lower()
        self.severity_order = {"error": 3, "warn": 2, "info": 1}
        
        if self.min_severity not in self.severity_order:
            raise ValueError(f"Invalid severity level: {min_severity}")
        
        self.min_level = self.severity_order[self.min_severity]
    
    @property
    def name(self) -> str:
        return f"severity_filter_{self.min_severity}"
    
    @property
    def priority(self) -> int:
        return 90  # Run late to filter final results
    
    def on_issue(self, issue: Issue, context: HookContext) -> Optional[Issue]:
        """Filter issues based on severity."""
        issue_level = self.severity_order.get(issue.severity.lower(), 0)
        
        if issue_level >= self.min_level:
            return issue
        else:
            return None  # Suppress the issue


class CustomSymbolExtractorHook(FileParseHook):
    """Example hook for custom symbol extraction."""
    
    def __init__(self, symbol_extractor: Callable[[ast.AST, Path], List[Symbol]]):
        """
        Initialize custom symbol extractor.
        
        Args:
            symbol_extractor: Function that extracts symbols from AST
        """
        self.symbol_extractor = symbol_extractor
    
    @property
    def name(self) -> str:
        return "custom_symbol_extractor"
    
    def on_file_parsed(
        self, 
        file_path: Path, 
        ast_tree: ast.AST, 
        symbols: List[Symbol],
        context: HookContext
    ) -> Optional[List[Symbol]]:
        """Extract additional symbols using custom logic."""
        try:
            additional_symbols = self.symbol_extractor(ast_tree, file_path)
            return additional_symbols
        except Exception as e:
            logger.error("Custom symbol extractor failed for %s: %s", file_path, e)
            return None


# Global hook manager instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance."""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def register_hook(hook: Hook):
    """Register a hook with the global hook manager."""
    get_hook_manager().register_hook(hook)


def register_hooks(hooks: List[Hook]):
    """Register multiple hooks with the global hook manager."""
    get_hook_manager().register_hooks(hooks)
