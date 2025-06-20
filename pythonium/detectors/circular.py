"""
Circular Dependency Detector

This module detects circular dependencies and dependency tangles in Python codebases.
Circular dependencies can lead to import errors, testing difficulties, and tight
coupling that makes code harder to maintain and refactor.

The detector identifies:
- Direct circular imports (A imports B, B imports A)
- Indirect circular dependencies (A -> B -> C -> A)
- High fan-in modules that are dependencies of many other modules
- Dependency cycles of configurable maximum length

Analysis approach:
1. Build a module-level dependency graph from import statements
2. Use depth-first search to detect cycles
3. Calculate fan-in metrics for each module
4. Report cycles and high-dependency modules

Configuration options:
- max_cycle_length: Maximum cycle length to report (default: 10)
- high_fanin_threshold: Threshold for high fan-in reporting (default: 20)

Example:
    ```python
    detector = CircularDependencyDetector(
        max_cycle_length=5,
        high_fanin_threshold=15
    )
    issues = detector.analyze(graph)
    ```
"""

import ast
import logging
from collections import defaultdict, deque
from typing import List, Set, Dict, Tuple, Optional
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector

logger = logging.getLogger(__name__)


class CircularDependencyDetector(BaseDetector):
    """
    Detects circular dependencies and dependency tangles.
    
    This detector analyzes import relationships between modules to identify
    circular dependencies that can cause import errors and make code harder
    to maintain. It also identifies modules with high fan-in that may indicate
    over-centralization of dependencies.
    
    The detector performs the following analysis:
    1. Extracts import relationships from the code graph
    2. Builds a module-level dependency graph
    3. Uses depth-first search to detect cycles
    4. Calculates fan-in metrics for dependency analysis    5. Reports circular dependencies and high-dependency modules
    
    Configuration options:
    - max_cycle_length: Maximum length of cycles to report
    - high_fanin_threshold: Threshold for reporting high fan-in modules
    
    Attributes:
        max_cycle_length: Maximum cycle length to analyze and report
        high_fanin_threshold: Threshold for high fan-in module reporting
    """
    
    id = "circular_deps"
    name = "Circular Dependency Detector"
    description = "Detects import cycles and dependency tangles"
    
    # Enhanced metadata for MCP server
    category = "Architecture & Design"
    usage_tips = "Essential for large codebases with complex import structures"
    related_detectors = ["inconsistent_api"]
    typical_severity = "error"
    detailed_description = ("Identifies import dependency cycles that can cause runtime errors and make "
                           "code harder to understand, test, and maintain.")
    
    def __init__(self, 
                 max_cycle_length: int = 10,
                 high_fanin_threshold: int = 20,
                 **options):
        """
        Initialize the circular dependency detector.
          Args:
            max_cycle_length: Maximum length of dependency cycles to report.
                             Longer cycles are often less problematic.
            high_fanin_threshold: Number of incoming dependencies above which
                                 a module is considered to have high fan-in.
        """
        super().__init__(**options)
        self.max_cycle_length = max_cycle_length
        self.high_fanin_threshold = high_fanin_threshold
        
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """
        Find circular dependencies in the codebase.
        
        Args:
            graph: The code graph to analyze
            
        Returns:
            List of issues representing circular dependencies and high fan-in modules
        """
        if not graph.symbols:
            return []
        
        issues = []
        
        # Build module dependency graph
        module_deps = self._build_module_dependency_graph(graph)
        
        # Find cycles
        cycles = self._find_cycles(module_deps)
        
        for cycle in cycles:
            if len(cycle) <= self.max_cycle_length:
                issue = self._create_cycle_issue(cycle, graph)
                if issue:
                    issues.append(issue)
          # Find high fan-in modules
        high_fanin_modules = self._find_high_fanin_modules(module_deps)
        
        for module, fanin_count in high_fanin_modules:
            issue = self._create_high_fanin_issue(module, fanin_count, graph)
            if issue:
                issues.append(issue)
        
        return issues
    
    def _build_module_dependency_graph(self, graph: CodeGraph) -> Dict[str, Set[str]]:
        """Build a module-level dependency graph."""
        module_deps = defaultdict(set)
        
        # Group symbols by module
        modules = defaultdict(list)
        for symbol in graph.symbols.values():
            if symbol.location and symbol.location.file:
                module_name = self._get_module_name(symbol.location.file)
                modules[module_name].append(symbol)
        
        # Analyze imports for each module
        for module_name, symbols in modules.items():
            for symbol in symbols:
                if isinstance(symbol.ast_node, (ast.Import, ast.ImportFrom)):
                    imported_modules = self._extract_imported_modules(symbol.ast_node)
                    for imported_module in imported_modules:
                        # Only track internal dependencies
                        if imported_module in modules:
                            module_deps[module_name].add(imported_module)
        
        return dict(module_deps)
    
    def _get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        # Convert path to module-style name
        relative_path = file_path.stem
        if file_path.name == "__init__.py":
            relative_path = file_path.parent.name
        return relative_path.replace("/", ".").replace("\\", ".")
    
    def _extract_imported_modules(self, node: ast.AST) -> List[str]:
        """Extract module names from import statements."""
        modules = []
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module.split('.')[0])
        
        return modules
    
    def _find_cycles(self, deps: Dict[str, Set[str]]) -> List[List[str]]:
        """Find cycles in the dependency graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(module: str) -> None:
            if module in rec_stack:
                # Found a cycle
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]
                cycles.append(cycle)
                return
            
            if module in visited:
                return
                
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for neighbor in deps.get(module, []):
                dfs(neighbor)
            
            rec_stack.remove(module)
            path.pop()
        
        for module in deps:
            if module not in visited:
                dfs(module)
        
        return cycles
    
    def _find_high_fanin_modules(self, deps: Dict[str, Set[str]]) -> List[Tuple[str, int]]:
        """Find modules with high fan-in (many modules depend on them)."""
        fanin_count = defaultdict(int)
        
        for module, dependencies in deps.items():
            for dep in dependencies:
                fanin_count[dep] += 1
        
        high_fanin = [
            (module, count) for module, count in fanin_count.items()
            if count >= self.high_fanin_threshold
        ]
        
        return sorted(high_fanin, key=lambda x: x[1], reverse=True)
    
    def _create_cycle_issue(self, cycle: List[str], graph: CodeGraph) -> Issue:
        """Create an issue for a circular dependency."""
        cycle_str = " -> ".join(cycle)
        severity = "error"
        
        # Find a symbol in the first module for location
        symbol = None
        for s in graph.symbols.values():
            if (s.location and s.location.file and 
                self._get_module_name(s.location.file) == cycle[0]):
                symbol = s
                break
        
        return self.create_issue(
            issue_id="cycle",
            message=f"Circular dependency detected: {cycle_str}",
            severity=severity,
            symbol=symbol,
            metadata={
                "cycle": cycle,
                "cycle_length": len(cycle) - 1,  # -1 because last element repeats first
            }
        )
    
    def _create_high_fanin_issue(self, module: str, fanin_count: int, graph: CodeGraph) -> Issue:
        """Create an issue for high fan-in module."""
        # Find a symbol in the module for location
        symbol = None
        for s in graph.symbols.values():
            if (s.location and s.location.file and 
                self._get_module_name(s.location.file) == module):
                symbol = s
                break
        
        return self.create_issue(
            issue_id="high-fanin",
            message=f"Module '{module}' has high fan-in ({fanin_count} dependencies). "
                   f"Consider breaking it into smaller modules.",
            severity="warn",
            symbol=symbol,
            metadata={
                "module": module,
                "fanin_count": fanin_count,
                "threshold": self.high_fanin_threshold,
            }
        )
