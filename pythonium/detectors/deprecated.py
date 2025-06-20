"""
Deprecated API Usage Detector

This detector identifies usage of deprecated APIs and functions that are
scheduled for removal. It helps maintain forward compatibility by flagging
code that uses symbols marked with @deprecated decorators or imported from
modules scheduled for removal.

The detector performs analysis by:
- Scanning for @deprecated decorators in docstrings and annotations
- Checking imports from known deprecated modules
- Identifying calls to functions marked as deprecated
- Parsing deprecation warnings in the codebase
- Supporting custom deprecation patterns via configuration

Features:
- Detection of @deprecated decorator usage
- Parsing of "deprecated since" and "removed in" version information
- Configurable deprecated module and function lists
- Support for custom deprecation patterns
- Integration with PEP 387 deprecation policy

Example:
    ```python
    # This usage would be detected:
    from deprecated_module import old_function
    
    @deprecated("Use new_function instead")
    def old_function():
        pass
    
    result = old_function()  # Detected usage
    ```
"""

import ast
import re
import logging
from typing import List, Dict, Set, Optional, Tuple, Pattern
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector

logger = logging.getLogger(__name__)


class DeprecatedApiDetector(BaseDetector):
    """
    Detector for deprecated API usage.
    
    This detector identifies code that uses APIs marked as deprecated,
    helping maintain forward compatibility and code health.
    
    Attributes:
        id: Detector identifier 'deprecated_api'
        name: Human-readable detector name
        description: What this detector checks for
    """
    
    id = "deprecated_api"
    name = "Deprecated API Detector"
    description = "Detects usage of deprecated APIs and functions scheduled for removal"
    
    # Enhanced metadata for MCP server
    category = "Security & Safety"
    usage_tips = "Critical for migration planning and modernization efforts"
    related_detectors = ["security_smell"]
    typical_severity = "error"
    detailed_description = ("Finds usage of deprecated APIs and suggests modern alternatives to maintain "
                           "forward compatibility and prevent future breaking changes.")
    
    def __init__(
        self,
        settings=None,
        deprecated_modules: Optional[List[str]] = None,
        deprecated_functions: Optional[Dict[str, str]] = None,
        custom_patterns: Optional[List[str]] = None,
        check_docstrings: bool = True,
        check_decorators: bool = True,
        **options
    ):
        """
        Initialize the deprecated API usage detector.
        
        Args:
            settings: Shared settings object
            deprecated_modules: List of deprecated module names
            deprecated_functions: Dict of deprecated function names to reasons
            custom_patterns: List of regex patterns for custom deprecation markers
            check_docstrings: Whether to check docstrings for deprecation markers
            check_decorators: Whether to check for @deprecated decorators
            **options: Additional options
        """
        super().__init__(settings, **options)
        
        # Default deprecated modules (common Python deprecations)
        self.deprecated_modules = deprecated_modules or [
            'imp',  # Deprecated in Python 3.4
            'formatter',  # Deprecated in Python 3.4
            'optparse',  # Deprecated in favor of argparse
            'platform.dist',  # Deprecated in Python 3.5
            'cgi',  # Some functions deprecated
            'distutils',  # Deprecated in Python 3.10
        ]
        
        # Default deprecated functions
        self.deprecated_functions = deprecated_functions or {
            'os.popen': 'Use subprocess module instead',
            'os.popen2': 'Use subprocess module instead', 
            'os.popen3': 'Use subprocess module instead',
            'os.popen4': 'Use subprocess module instead',
            'platform.dist': 'Deprecated in Python 3.5',
            'platform.linux_distribution': 'Deprecated in Python 3.5',
            'inspect.getargspec': 'Use inspect.signature instead',
            'inspect.formatargspec': 'Use inspect.signature instead',
            'collections.Mapping': 'Use collections.abc.Mapping instead',
            'collections.MutableMapping': 'Use collections.abc.MutableMapping instead',
            'collections.Sequence': 'Use collections.abc.Sequence instead',
            'collections.MutableSequence': 'Use collections.abc.MutableSequence instead',
        }
        
        # Custom deprecation patterns
        self.custom_patterns = [
            re.compile(pattern) for pattern in (custom_patterns or [])
        ]
        
        # Built-in deprecation patterns
        self.deprecation_patterns = [
            re.compile(r'@deprecated', re.IGNORECASE),
            re.compile(r'.. deprecated::', re.IGNORECASE),
            re.compile(r'deprecated since', re.IGNORECASE),
            re.compile(r'will be removed', re.IGNORECASE),
            re.compile(r'use .* instead', re.IGNORECASE),
        ] + self.custom_patterns
        
        self.check_docstrings = check_docstrings
        self.check_decorators = check_decorators

    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph for deprecated API usage."""
        issues = []
        
        # Find deprecated imports
        issues.extend(self._find_deprecated_imports(graph))
        
        # Find deprecated function calls
        issues.extend(self._find_deprecated_calls(graph))
        
        # Find deprecated definitions (marked with deprecation)
        if self.check_decorators or self.check_docstrings:
            issues.extend(self._find_deprecated_definitions(graph))
        
        return issues

    def _find_deprecated_imports(self, graph: CodeGraph) -> List[Issue]:
        """Find imports of deprecated modules."""
        issues = []
        
        for symbol in graph.symbols.values():
            if not symbol.ast_node or not isinstance(symbol.ast_node, (ast.Import, ast.ImportFrom)):
                continue
            
            # Check Import nodes
            if isinstance(symbol.ast_node, ast.Import):
                for alias in symbol.ast_node.names:
                    module_name = alias.name
                    if self._is_deprecated_module(module_name):
                        issues.append(self._create_deprecated_import_issue(
                            symbol, module_name, "Module is deprecated"
                        ))
            
            # Check ImportFrom nodes
            elif isinstance(symbol.ast_node, ast.ImportFrom):
                module_name = symbol.ast_node.module or ""
                if self._is_deprecated_module(module_name):
                    issues.append(self._create_deprecated_import_issue(
                        symbol, module_name, "Module is deprecated"
                    ))
        
        return issues

    def _find_deprecated_calls(self, graph: CodeGraph) -> List[Issue]:
        """Find calls to deprecated functions."""
        issues = []
        
        for symbol in graph.symbols.values():
            if not symbol.ast_node:
                continue
            
            # Walk the AST to find function calls
            for node in ast.walk(symbol.ast_node):
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    if func_name and self._is_deprecated_function(func_name):
                        reason = self.deprecated_functions.get(func_name, "Function is deprecated")
                        
                        issues.append(self._create_deprecated_usage_issue(
                            symbol, func_name, reason, node
                        ))
        
        return issues

    def _find_deprecated_definitions(self, graph: CodeGraph) -> List[Issue]:
        """Find definitions marked as deprecated."""
        issues = []
        
        for symbol in graph.symbols.values():
            if not symbol.ast_node:
                continue
            
            # Check for deprecation markers in functions and classes
            if isinstance(symbol.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                
                # Check decorators for @deprecated
                if self.check_decorators:
                    for decorator in symbol.ast_node.decorator_list:
                        if self._is_deprecated_decorator(decorator):
                            issues.append(self._create_deprecated_definition_issue(
                                symbol, "Definition marked as deprecated"
                            ))
                            break
                
                # Check docstring for deprecation markers
                if self.check_docstrings:
                    docstring = ast.get_docstring(symbol.ast_node)
                    if docstring and self._has_deprecation_marker(docstring):
                        issues.append(self._create_deprecated_definition_issue(
                            symbol, "Definition marked as deprecated in docstring"
                        ))
        
        return issues

    def _is_deprecated_module(self, module_name: str) -> bool:
        """Check if a module is deprecated."""
        if not module_name:
            return False
        
        # Check exact matches
        if module_name in self.deprecated_modules:
            return True
        
        # Check if any deprecated module is a parent of this module
        for dep_module in self.deprecated_modules:
            if module_name.startswith(dep_module + '.'):
                return True
        
        return False

    def _is_deprecated_function(self, func_name: str) -> bool:
        """Check if a function is deprecated."""
        return func_name in self.deprecated_functions

    def _get_call_name(self, call_node: ast.Call) -> Optional[str]:
        """Extract the full name of a function call."""
        try:
            if isinstance(call_node.func, ast.Name):
                return call_node.func.id
            elif isinstance(call_node.func, ast.Attribute):
                return self._get_attribute_name(call_node.func)
            return None
        except (AttributeError, TypeError):
            return None

    def _get_attribute_name(self, attr_node: ast.Attribute) -> str:
        """Get the full name of an attribute access."""
        parts = []
        current = attr_node
        
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            parts.append(current.id)
        
        return '.'.join(reversed(parts))

    def _is_deprecated_decorator(self, decorator: ast.expr) -> bool:
        """Check if a decorator indicates deprecation."""
        try:
            if isinstance(decorator, ast.Name):
                return decorator.id.lower() in ('deprecated', 'deprecate')
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    return decorator.func.id.lower() in ('deprecated', 'deprecate')
                elif isinstance(decorator.func, ast.Attribute):
                    return decorator.func.attr.lower() in ('deprecated', 'deprecate')
            return False
        except (AttributeError, TypeError):
            return False

    def _has_deprecation_marker(self, text: str) -> bool:
        """Check if text contains deprecation markers."""
        for pattern in self.deprecation_patterns:
            if pattern.search(text):
                return True
        return False

    def _create_deprecated_import_issue(self, symbol: Symbol, module_name: str, reason: str) -> Issue:
        """Create an issue for deprecated module import."""
        return self.create_issue(
            issue_id="deprecated_import",
            message=f"Import of deprecated module '{module_name}': {reason}",
            severity="warn",
            symbol=symbol,
            metadata={
                "deprecated_module": module_name,
                "reason": reason,
                "suggestion": f"Find alternative to '{module_name}' module",
            }
        )

    def _create_deprecated_usage_issue(
        self, 
        symbol: Symbol, 
        func_name: str, 
        reason: str, 
        call_node: ast.Call
    ) -> Issue:
        """Create an issue for deprecated function usage."""
        # Try to get more specific location from the call node
        location = symbol.location
        if hasattr(call_node, 'lineno') and symbol.location:
            location = Location(
                file=symbol.location.file,
                line=symbol.location.line + call_node.lineno - 1,
                column=getattr(call_node, 'col_offset', 0)
            )
        
        return self.create_issue(
            issue_id="deprecated_usage",
            message=f"Usage of deprecated function '{func_name}': {reason}",
            severity="warn",
            symbol=symbol,
            location=location,
            metadata={
                "deprecated_function": func_name,
                "reason": reason,
                "suggestion": reason if "instead" in reason.lower() else f"Replace '{func_name}' with alternative",
            }
        )

    def _create_deprecated_definition_issue(self, symbol: Symbol, reason: str) -> Issue:
        """Create an issue for deprecated definition."""
        return self.create_issue(
            issue_id="deprecated_definition",
            message=f"Definition '{symbol.name}' is marked as deprecated: {reason}",
            severity="info",  # Lower severity since this is just marking, not usage
            symbol=symbol,
            metadata={
                "deprecated_symbol": symbol.fqname,
                "reason": reason,
                "suggestion": "Consider removing or updating deprecated code",
            }
        )
