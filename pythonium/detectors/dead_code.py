"""
Dead Code Detector

This module detects dead (unreferenced) code in Python projects including:
- Unused functions and methods
- Unused classes
- Unused imports
- Unused variables and constants

The detector performs comprehensive analysis by tracking symbol definitions and
references throughout the codebase, with support for entry points and configurable
ignore patterns.

Example:
    ```python
    detector = DeadCodeDetector(
        entry_points=["main", "app.run"],
        ignore=["**/test_*.py", "**/__init__.py"]
    )
    issues = detector.analyze(graph)
    ```
"""

import ast
import logging
import fnmatch
from typing import List, Set, Dict, Optional
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol
from . import BaseDetector

logger = logging.getLogger(__name__)

class DeadCodeDetector(BaseDetector):
    """
    Detects dead (unused) code in Python projects.
    
    This detector identifies functions, classes, and methods that are defined but never
    referenced in the codebase. It performs a comprehensive analysis by tracking
    symbol definitions and references throughout the project.
    
    The detector supports:
    - Configurable entry points to preserve main functions and API endpoints
    - Ignore patterns to exclude test files and special modules
    - Detection of unused imports, functions, classes, and methods
    - Smart handling of special methods (dunder methods) and __init__.py files
    
    Attributes:
        entry_points: Set of function names to treat as entry points
        ignore_patterns: List of glob patterns for files to ignore
    """
    
    id = "dead_code"
    name = "Dead Code Detector"
    description = "Finds code that is defined but never used"
    
    # Enhanced metadata for MCP server
    category = "Code Quality & Maintainability"
    usage_tips = "Execute during code cleanup phases and before releases to remove unused code"
    related_detectors = ["clone", "complexity_hotspot"]
    typical_severity = "warn"
    detailed_description = ("Locates unused functions, classes, variables, and imports that can be safely "
                           "removed to improve code clarity and maintainability.")
    
    def __init__(self, **options):
        """
        Initialize the dead code detector.
        
        Args:
            entry_points: List of function names to treat as entry points.
                         These functions won't be marked as dead even if unused.
            ignore: List of glob patterns for files to ignore during analysis.
        """
        super().__init__(**options)
        self.entry_points = set(options.get("entry_points", ["main"]))
        self.ignore_patterns = options.get("ignore", [
            "**/tests/**",
            "**/test_*.py",
            "**/conftest.py",
            "**/__init__.py",        ])

    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """
        Analyze the code graph for dead code.
        
        Args:
            graph: The code graph to analyze
            
        Returns:
            List of issues representing dead code findings
        """
        if not graph.symbols:
            return []
        
        # Get all defined symbols
        all_symbols = set(graph.symbols.keys())
        
        # Get all referenced symbols
        referenced_symbols = self._find_referenced_symbols(graph)
        
        # Add entry points to referenced symbols
        entry_point_count = 0
        for entry_point in self.entry_points:
            # Try to find the entry point in the graph
            entry_symbols = graph.find_symbols(entry_point)
            if entry_symbols:
                for symbol in entry_symbols:
                    referenced_symbols.add(symbol.fqname)
                entry_point_count += len(entry_symbols)
        
        # Find dead symbols (defined but never referenced)
        dead_symbols = all_symbols - referenced_symbols
        
        # Filter out ignored patterns
        dead_symbols = {
            sym for sym in dead_symbols
            if not self._is_ignored(sym, graph)
        }
        
        # Create issues for dead symbols
        issues: List[Issue] = []
        for sym_name in sorted(dead_symbols):
            symbol = graph.get_symbol(sym_name)
            if symbol is None:
                continue
                
            # Skip __init__ methods as they're called implicitly
            if symbol.fqname.endswith('.__init__'):
                continue
                
            # Skip special methods (dunder methods) as they're called implicitly
            simple_name = symbol.fqname.split('.')[-1]
            if simple_name.startswith('__') and simple_name.endswith('__'):
                continue
            
            # Skip if the symbol is part of a test file (additional check)
            if symbol.location and symbol.location.file:
                file_parts = Path(symbol.location.file).parts
                if any(part in ('tests', 'test') for part in file_parts):
                    continue
            
            # Create issue
            issue = self.create_issue(
                issue_id="unused-symbol",
                message=f"{self._get_symbol_type(symbol)} '{symbol.fqname}' is defined but never used",
                symbol=symbol,
                severity="warn",
                metadata={
                    "symbol_type": self._get_symbol_type(symbol).lower(),
                    "file": str(symbol.location.file) if symbol.location else "unknown",
                    "line": symbol.location.line if symbol.location else 0,
                    "simple_name": simple_name,
                }
            )
            issues.append(issue)
        
        return issues
    
    def _find_referenced_symbols(self, graph: CodeGraph) -> Set[str]:
        """
        Find all symbols that are referenced in the codebase.
        
        This method performs a comprehensive search for symbol references by:
        1. Collecting direct references from symbol.references
        2. Searching AST nodes for name references
        3. Adding parent scope references for nested symbols
        
        Args:
            graph: The code graph to search
            
        Returns:
            Set of fully qualified symbol names that are referenced
        """
        referenced = set()
        
        # First pass: collect all direct references from symbol.references
        for symbol in graph.symbols.values():
            # Add all references from this symbol
            for ref in symbol.references:
                # Resolve the reference to a fully qualified name
                if ref in graph.symbols:
                    referenced.add(ref)
                    
                    # Also add references to parent scopes
                    parts = ref.split('.')
                    for i in range(1, len(parts)):
                        parent = '.'.join(parts[:-i])
                        if parent in graph.symbols:
                            referenced.add(parent)
        
        # Second pass: find references in the AST nodes
        for symbol in graph.symbols.values():
            if symbol.ast_node:
                self._find_references_in_ast(
                    symbol.ast_node, 
                    referenced, 
                    graph
                )
        
        return referenced
    
    def _find_references_in_ast(
        self,
        node: ast.AST,
        referenced: Set[str],
        graph: CodeGraph,
        current_scope: Optional[str] = None
    ) -> None:
        """
        Recursively find symbol references in an AST node.
        
        Args:
            node: AST node to search
            referenced: Set to add found references to
            graph: Code graph for symbol resolution
            current_scope: Current scope for relative reference resolution
        """
        try:
            if isinstance(node, ast.Name):
                # This is a name reference
                name = node.id
                
                # Try to resolve the name in the current scope
                if current_scope:
                    # Check for relative imports (e.g., from . import module)
                    parts = current_scope.split('.')
                    for i in range(len(parts), 0, -1):
                        candidate = '.'.join(parts[:i]) + '.' + name
                        if candidate in graph.symbols:
                            referenced.add(candidate)
                            break
                
                # Also check the global scope
                if name in graph.symbols:
                    referenced.add(name)
            
            # Process child nodes
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self._find_references_in_ast(item, referenced, graph, current_scope)
                elif isinstance(value, ast.AST):
                    self._find_references_in_ast(value, referenced, graph, current_scope)
                    
        except Exception as e:
            pass
    
    def _is_ignored(self, symbol_name: str, graph: CodeGraph) -> bool:
        """
        Check if a symbol should be ignored based on ignore patterns.
        
        Args:
            symbol_name: Fully qualified symbol name
            graph: Code graph for symbol lookup
            
        Returns:
            True if the symbol should be ignored, False otherwise
        """
        symbol = graph.get_symbol(symbol_name)
        if symbol is None or not symbol.location or not symbol.location.file:
            return True
            
        file_path = str(symbol.location.file)
        
        for pattern in self.ignore_patterns:
            # Convert glob pattern to match
            if fnmatch.fnmatch(file_path, pattern):
                return True
                
        return False
    
    @staticmethod
    def _get_symbol_type(symbol: Symbol) -> str:
        """
        Get a human-readable type name for a symbol.
        
        Args:
            symbol: Symbol to get type for
            
        Returns:
            Human-readable type name (e.g., "Class", "Function", "Method")
        """
        if not symbol.ast_node:
            return "Symbol"
            
        if isinstance(symbol.ast_node, ast.ClassDef):
            return "Class"
        elif isinstance(symbol.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Determine if it's a method or function based on nesting
            if symbol.fqname.count('.') > 1 and not symbol.fqname.endswith('.__init__'):
                return "Method"
            return "Function"
        elif isinstance(symbol.ast_node, ast.ImportFrom):
            return "Import"
        elif isinstance(symbol.ast_node, ast.Import):
            return "Import"
        elif isinstance(symbol.ast_node, ast.Assign):
            return "Variable"
        else:
            return "Symbol"
