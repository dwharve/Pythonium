"""
Complexity Hotspot Detector

Detects functions with high cyclomatic complexity or excessive lines of code.
Uses radon for complexity analysis.
"""

import ast
import logging
from typing import List, Dict, Any
from pathlib import Path

try:
    from radon.complexity import cc_visit
    from radon.metrics import h_visit, mi_visit
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

from ..models import CodeGraph, Issue, Symbol
from . import BaseDetector

logger = logging.getLogger(__name__)


class ComplexityDetector(BaseDetector):
    """Detects functions with high complexity that need refactoring."""
    
    id = "complexity_hotspot"
    name = "Complexity Detector"
    description = "Finds functions with excessive cyclomatic complexity or length"
    
    # Enhanced metadata for MCP server
    category = "Code Quality & Maintainability"
    usage_tips = "Apply when reviewing complex modules or planning refactoring"
    related_detectors = ["dead_code", "alt_implementation"]
    typical_severity = "warn"
    detailed_description = ("Finds overly complex functions that may be difficult to understand, test, "
                           "or maintain based on cyclomatic complexity and lines of code metrics.")
    
    def __init__(self,
                 cyclomatic_threshold: int = 10,
                 loc_threshold: int = 50,
                 halstead_difficulty_threshold: float = 20.0,
                 **options):
        super().__init__(**options)
        self.cyclomatic_threshold = cyclomatic_threshold
        self.loc_threshold = loc_threshold
        self.halstead_difficulty_threshold = halstead_difficulty_threshold
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Find complexity hotspots in the codebase."""
        issues = []
        
        # Group symbols by file for batch processing
        files_symbols = {}
        for symbol in graph.symbols.values():
            if (symbol.location and symbol.location.file and 
                isinstance(symbol.ast_node, ast.FunctionDef)):
                
                file_path = symbol.location.file
                if file_path not in files_symbols:
                    files_symbols[file_path] = []
                files_symbols[file_path].append(symbol)
        
        # Analyze each file
        for file_path, symbols in files_symbols.items():
            try:
                # Read the file for radon analysis
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                  # Perform complexity analysis
                file_issues = self._analyze_file_complexity(content, symbols, file_path)
                issues.extend(file_issues)
                
            except Exception as e:
                pass
        
        return issues
    
    def _analyze_file_complexity(self, content: str, symbols: List[Symbol], file_path: Path) -> List[Issue]:
        """Analyze complexity for a single file."""
        issues = []
        
        # Basic AST-based analysis (always available)
        for symbol in symbols:
            if isinstance(symbol.ast_node, ast.FunctionDef):
                func_issues = self._analyze_function_basic(symbol)
                issues.extend(func_issues)
        
        # Enhanced analysis with radon (if available)
        if RADON_AVAILABLE:
            radon_issues = self._analyze_with_radon(content, symbols, file_path)
            issues.extend(radon_issues)        
        return issues
    
    def _analyze_function_basic(self, symbol: Symbol) -> List[Issue]:
        """Basic complexity analysis using AST."""
        issues = []
        func_node = symbol.ast_node
        
        # Count lines of code (excluding docstrings and comments)
        loc = self._count_loc(func_node)
        if loc > self.loc_threshold:
            # Extract simple name from fqname for display
            simple_name = symbol.fqname.split('.')[-1]
            issues.append(self.create_issue(
                issue_id="high-loc",
                message=f"Function '{simple_name}' has {loc} lines of code. "
                       f"Consider breaking it into smaller functions (threshold: {self.loc_threshold}).",
                severity="info",
                symbol=symbol,
                metadata={
                    "loc": loc,
                    "threshold": self.loc_threshold,
                    "metric": "lines_of_code"
                }
            ))
        # Basic cyclomatic complexity (simplified)
        complexity = self._calculate_basic_complexity(func_node)
        if complexity > self.cyclomatic_threshold:
            simple_name = symbol.fqname.split('.')[-1]
            issues.append(self.create_issue(
                issue_id="high-complexity",
                message=f"Function '{simple_name}' has cyclomatic complexity of {complexity}. "
                       f"Consider simplifying (threshold: {self.cyclomatic_threshold}).",
                severity="info",
                symbol=symbol,
                metadata={
                    "complexity": complexity,
                    "threshold": self.cyclomatic_threshold,
                    "metric": "cyclomatic_complexity"
                }
            ))        
        return issues
    
    def _analyze_with_radon(self, content: str, symbols: List[Symbol], file_path: Path) -> List[Issue]:
        """Enhanced analysis using radon library."""
        issues = []
        
        try:
            # Cyclomatic complexity analysis
            cc_results = cc_visit(content)
            
            # Create a mapping from function names to symbols
            func_symbols = {s.fqname.split('.')[-1]: s for s in symbols if isinstance(s.ast_node, ast.FunctionDef)}
            
            for cc_result in cc_results:
                if cc_result.name in func_symbols:
                    symbol = func_symbols[cc_result.name]
                    
                    if cc_result.complexity > self.cyclomatic_threshold:
                        simple_name = symbol.fqname.split('.')[-1]
                        issues.append(self.create_issue(
                            issue_id="radon-complexity",
                            message=f"Function '{simple_name}' has cyclomatic complexity of "
                                   f"{cc_result.complexity} (radon analysis). "
                                   f"Consider simplifying (threshold: {self.cyclomatic_threshold}).",
                            severity="warn" if cc_result.complexity > self.cyclomatic_threshold * 2 else "info",
                            symbol=symbol,
                            metadata={
                                "complexity": cc_result.complexity,
                                "threshold": self.cyclomatic_threshold,
                                "metric": "radon_cyclomatic",
                                "rank": getattr(cc_result, 'rank', 'unknown')
                            }
                        ))
            
            # Halstead complexity analysis
            try:
                h_results = h_visit(content)
                for h_result in h_results:
                    if (hasattr(h_result, 'difficulty') and 
                        h_result.difficulty > self.halstead_difficulty_threshold and
                        h_result.name in func_symbols):
                        
                        symbol = func_symbols[h_result.name]
                        simple_name = symbol.fqname.split('.')[-1]
                        issues.append(self.create_issue(
                            issue_id="halstead-difficulty",
                            message=f"Function '{simple_name}' has high Halstead difficulty "
                                   f"({h_result.difficulty:.1f}). Consider simplifying variable usage.",                            severity="info",
                            symbol=symbol,
                            metadata={
                                "difficulty": h_result.difficulty,
                                "threshold": self.halstead_difficulty_threshold,
                                "metric": "halstead_difficulty",
                                "volume": getattr(h_result, 'volume', None),
                                "effort": getattr(h_result, 'effort', None)
                            }
                        ))
                        
            except Exception as e:
                pass
                
        except Exception as e:
            pass
        
        return issues
    
    def _count_loc(self, node: ast.FunctionDef) -> int:
        """Count lines of code in a function, excluding docstrings."""
        if not hasattr(node, 'lineno') or not hasattr(node, 'end_lineno'):
            return 0
        
        total_lines = node.end_lineno - node.lineno + 1
        
        # Subtract docstring lines if present
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            
            docstring_node = node.body[0]
            if hasattr(docstring_node, 'lineno') and hasattr(docstring_node, 'end_lineno'):
                docstring_lines = docstring_node.end_lineno - docstring_node.lineno + 1
                total_lines -= docstring_lines
        
        return max(1, total_lines)  # At least 1 line
    
    def _calculate_basic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate basic cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points that increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.Try):
                complexity += 1
                # Each except handler adds complexity
                complexity += len(child.handlers)
            elif isinstance(child, (ast.BoolOp, ast.Compare)):
                # Boolean operations add complexity
                if isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
                elif isinstance(child, ast.Compare):
                    complexity += len(child.comparators)
            elif isinstance(child, ast.comprehension):
                # List/dict/set comprehensions add complexity
                complexity += 1
                complexity += len(child.ifs)  # Each if in comprehension
        
        return complexity
