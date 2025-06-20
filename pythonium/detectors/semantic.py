"""
Semantic Equivalence Detector

This detector identifies functionally equivalent code that achieves the same result
through different implementations. Examples:
- for loop vs sum() builtin
- manual string concatenation vs join()
- explicit condition checks vs all()/any()
- manual sorting vs sorted() with key functions

Features:
- Pattern-based semantic analysis
- Control flow equivalence detection
- Algorithmic pattern recognition
- Performance/style recommendations
"""

import ast
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional, Any
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector


class SemanticDetector(BaseDetector):
    """
    Detector for semantically equivalent code patterns.
    
    This detector identifies different implementations that achieve the same
    functional result, helping spot opportunities for standardization and
    performance improvements.
    """
    
    id = "semantic_equivalence"
    name = "Semantic Detector"
    description = "Finds functionally equivalent code implemented differently"
    
    # Enhanced metadata for MCP server
    category = "Code Quality & Maintainability"
    usage_tips = "Apply to find functionally equivalent code with different implementations"
    related_detectors = ["clone", "alt_implementation", "advanced_patterns"]
    typical_severity = "info"
    detailed_description = ("Identifies functionally equivalent code implemented in different ways, "
                           "suggesting opportunities for standardization and performance improvements.")
    
    def __init__(
        self,
        detect_builtin_equivalents: bool = True,
        detect_control_flow_equivalents: bool = True,
        detect_algorithmic_patterns: bool = True,
        min_confidence: float = 0.7,
        **options
    ):
        """
        Initialize the semantic equivalence detector.
        
        Args:
            detect_builtin_equivalents: Detect manual implementations of builtins
            detect_control_flow_equivalents: Detect equivalent control structures
            detect_algorithmic_patterns: Detect equivalent algorithms
            min_confidence: Minimum confidence threshold for reporting
            **options: Additional options passed to BaseDetector
        """
        super().__init__(**options)
        self.detect_builtin_equivalents = detect_builtin_equivalents
        self.detect_control_flow_equivalents = detect_control_flow_equivalents
        self.detect_algorithmic_patterns = detect_algorithmic_patterns
        self.min_confidence = max(0.0, min(1.0, min_confidence))

    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph for semantic equivalence issues."""
        issues = []
        
        # Get all function symbols
        functions = [s for s in graph.symbols.values() 
                    if isinstance(s.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        
        if len(functions) < 2:
            return issues
        
        # Analyze each function for semantic patterns
        function_patterns = {}
        for func in functions:
            patterns = self._extract_semantic_patterns(func)
            if patterns:
                function_patterns[func] = patterns
        
        # Find equivalent patterns across functions
        if self.detect_builtin_equivalents:
            issues.extend(self._find_builtin_equivalents(function_patterns))
        
        if self.detect_control_flow_equivalents:
            issues.extend(self._find_control_flow_equivalents(function_patterns))
        
        if self.detect_algorithmic_patterns:
            issues.extend(self._find_algorithmic_equivalents(function_patterns))
        
        return issues

    def _extract_semantic_patterns(self, func: Symbol) -> Dict[str, Any]:
        """Extract semantic patterns from a function."""
        patterns = {}
        
        # Walk through the function body
        for node in ast.walk(func.ast_node):
            # Pattern 1: Manual sum implementation
            if self._is_manual_sum_pattern(node):
                patterns['manual_sum'] = {
                    'type': 'builtin_equivalent',
                    'pattern': 'manual_sum',
                    'suggestion': 'Use sum() builtin',
                    'confidence': 0.9,
                    'node': node
                }
            
            # Pattern 2: Manual string join
            elif self._is_manual_string_join(node):
                patterns['manual_join'] = {
                    'type': 'builtin_equivalent',
                    'pattern': 'manual_string_join',
                    'suggestion': 'Use str.join() method',
                    'confidence': 0.8,
                    'node': node
                }
            
            # Pattern 3: Manual all/any implementation
            elif self._is_manual_all_any_pattern(node):
                patterns['manual_all_any'] = {
                    'type': 'builtin_equivalent',
                    'pattern': 'manual_all_any',
                    'suggestion': 'Use all() or any() builtin',
                    'confidence': 0.85,
                    'node': node
                }
            
            # Pattern 4: Manual min/max finding
            elif self._is_manual_min_max_pattern(node):
                patterns['manual_min_max'] = {
                    'type': 'builtin_equivalent',
                    'pattern': 'manual_min_max',
                    'suggestion': 'Use min() or max() builtin',
                    'confidence': 0.85,
                    'node': node
                }
            
            # Pattern 5: Nested loop for filtering
            elif self._is_nested_filter_pattern(node):
                patterns['nested_filter'] = {
                    'type': 'control_flow_equivalent',
                    'pattern': 'nested_filter',
                    'suggestion': 'Use list comprehension or filter()',
                    'confidence': 0.75,
                    'node': node
                }
        
        return patterns

    def _is_manual_sum_pattern(self, node: ast.AST) -> bool:
        """Detect manual sum implementation pattern."""
        if not isinstance(node, ast.For):
            return False
        
        # Look for: for item in iterable: total += item
        if not node.body or len(node.body) != 1:
            return False
        
        stmt = node.body[0]
        if not isinstance(stmt, ast.AugAssign):
            return False
        
        # Check if it's += operation
        if not isinstance(stmt.op, ast.Add):
            return False
        
        # Check if the target is used consistently
        if isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Name):
            # This could be a sum pattern
            return True
        
        return False

    def _is_manual_string_join(self, node: ast.AST) -> bool:
        """Detect manual string concatenation that could use join."""
        if not isinstance(node, ast.For):
            return False
        
        # Look for string concatenation in loops
        for stmt in node.body:
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
                # Check if we're concatenating strings
                return True
        
        return False

    def _is_manual_all_any_pattern(self, node: ast.AST) -> bool:
        """Detect manual all/any implementation."""
        if not isinstance(node, ast.For):
            return False
        
        # Look for patterns like:
        # for item in items:
        #     if not condition(item):
        #         return False
        # return True
        
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                # Check if there's an early return pattern
                if (stmt.body and len(stmt.body) == 1 and 
                    isinstance(stmt.body[0], ast.Return)):
                    return True
        
        return False

    def _is_manual_min_max_pattern(self, node: ast.AST) -> bool:
        """Detect manual min/max finding."""
        if not isinstance(node, ast.For):
            return False
        
        # Look for comparison and assignment patterns
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                # Check for comparison followed by assignment
                if (stmt.test and isinstance(stmt.test, ast.Compare) and
                    stmt.body and isinstance(stmt.body[0], ast.Assign)):
                    return True
        
        return False

    def _is_nested_filter_pattern(self, node: ast.AST) -> bool:
        """Detect nested loops that could be list comprehensions."""
        if not isinstance(node, ast.For):
            return False
        
        # Look for nested for loops or if statements that build lists
        for stmt in node.body:
            if isinstance(stmt, (ast.For, ast.If)):
                # Nested structure that might be simplifiable
                return True
        
        return False

    def _find_builtin_equivalents(self, function_patterns: Dict) -> List[Issue]:
        """Find functions with equivalent builtin patterns."""
        issues = []
        
        # Group functions by pattern type
        pattern_groups = defaultdict(list)
        
        for func, patterns in function_patterns.items():
            for pattern_name, pattern_info in patterns.items():
                if pattern_info['type'] == 'builtin_equivalent':
                    pattern_groups[pattern_info['pattern']].append((func, pattern_info))
        
        # Create issues for groups with multiple functions
        for pattern_type, func_patterns in pattern_groups.items():
            if len(func_patterns) >= 2:
                issues.extend(self._create_builtin_equivalent_issues(pattern_type, func_patterns))
        
        # Also create issues for individual patterns above confidence threshold
        for func, patterns in function_patterns.items():
            for pattern_name, pattern_info in patterns.items():
                if (pattern_info['type'] == 'builtin_equivalent' and 
                    pattern_info['confidence'] >= self.min_confidence):
                    
                    # Check if not already reported in a group
                    already_reported = any(
                        func in [fp[0] for fp in func_patterns] 
                        for pattern_type, func_patterns in pattern_groups.items()
                        if len(func_patterns) >= 2 and pattern_type == pattern_info['pattern']
                    )
                    
                    if not already_reported:
                        issues.extend(self._create_single_builtin_issue(func, pattern_info))
        
        return issues

    def _find_control_flow_equivalents(self, function_patterns: Dict) -> List[Issue]:
        """Find functions with equivalent control flow patterns."""
        issues = []
        
        # Group by control flow patterns
        pattern_groups = defaultdict(list)
        
        for func, patterns in function_patterns.items():
            for pattern_name, pattern_info in patterns.items():
                if pattern_info['type'] == 'control_flow_equivalent':
                    pattern_groups[pattern_info['pattern']].append((func, pattern_info))
        
        # Create issues for groups
        for pattern_type, func_patterns in pattern_groups.items():
            if len(func_patterns) >= 2:
                issues.extend(self._create_control_flow_issues(pattern_type, func_patterns))
        
        return issues

    def _find_algorithmic_equivalents(self, function_patterns: Dict) -> List[Issue]:
        """Find functions with equivalent algorithmic patterns."""
        issues = []
        
        # This would analyze higher-level algorithmic patterns
        # For now, we'll implement a simplified version
        
        # Group functions by their overall structure/complexity
        structural_groups = defaultdict(list)
        
        for func, patterns in function_patterns.items():
            # Create a structural signature
            signature = self._get_structural_signature(func)
            if signature:
                structural_groups[signature].append(func)
        
        # Look for groups that might be algorithmic equivalents
        for signature, funcs in structural_groups.items():
            if len(funcs) >= 2:
                # Analyze if they're truly equivalent
                equivalent_groups = self._analyze_algorithmic_equivalence(funcs)
                for group in equivalent_groups:
                    if len(group) >= 2:
                        issues.extend(self._create_algorithmic_equivalent_issues(group))
        
        return issues

    def _get_structural_signature(self, func: Symbol) -> Optional[str]:
        """Get a structural signature for algorithmic comparison."""
        try:
            # Count different types of nodes
            node_counts = defaultdict(int)
            for node in ast.walk(func.ast_node):
                node_counts[type(node).__name__] += 1
            
            # Create signature from key structural elements
            key_elements = ['For', 'While', 'If', 'Compare', 'Call', 'Return']
            signature_parts = []
            
            for element in key_elements:
                count = node_counts.get(element, 0)
                if count > 0:
                    signature_parts.append(f"{element}:{count}")
            
            return "_".join(signature_parts) if signature_parts else None
            
        except Exception:
            return None

    def _analyze_algorithmic_equivalence(self, funcs: List[Symbol]) -> List[List[Symbol]]:
        """Analyze if functions are algorithmically equivalent."""
        # Simplified implementation - could be much more sophisticated
        
        # For now, just group functions with very similar signatures
        # In a full implementation, this would do deep semantic analysis
        
        groups = []
        used = set()
        
        for i, func1 in enumerate(funcs):
            if i in used:
                continue
            
            group = [func1]
            used.add(i)
            
            for j, func2 in enumerate(funcs[i+1:], i+1):
                if j in used:
                    continue
                
                # Simple similarity check (could be much more sophisticated)
                if self._are_algorithmically_similar(func1, func2):
                    group.append(func2)
                    used.add(j)
            
            if len(group) >= 2:
                groups.append(group)
        
        return groups

    def _are_algorithmically_similar(self, func1: Symbol, func2: Symbol) -> bool:
        """Check if two functions are algorithmically similar."""
        # Very simplified check - in practice this would be much more sophisticated
        try:
            # Compare function signatures
            sig1 = self._get_function_signature(func1.ast_node)
            sig2 = self._get_function_signature(func2.ast_node)
            
            # Compare body complexity
            body1_complexity = len(list(ast.walk(func1.ast_node)))
            body2_complexity = len(list(ast.walk(func2.ast_node)))
            
            # Similar if signatures are similar and complexity is similar
            sig_similar = len(sig1.intersection(sig2)) / max(len(sig1), len(sig2), 1) > 0.5
            complexity_similar = abs(body1_complexity - body2_complexity) / max(body1_complexity, body2_complexity, 1) < 0.3
            
            return sig_similar and complexity_similar
            
        except Exception:
            return False

    def _get_function_signature(self, func_node: ast.FunctionDef) -> Set[str]:
        """Get a semantic signature of a function."""
        signature = set()
        
        # Add argument types
        for arg in func_node.args.args:
            signature.add(f"arg:{arg.arg}")
        
        # Add node types in body
        for node in ast.walk(func_node):
            signature.add(type(node).__name__)
        
        return signature

    def _create_builtin_equivalent_issues(self, pattern_type: str, func_patterns: List) -> List[Issue]:
        """Create issues for builtin equivalent patterns."""
        if len(func_patterns) < 2:
            return []
        
        # Use the first function as primary location
        primary_func, primary_pattern = func_patterns[0]
        
        # Collect all function names and locations
        function_names = []
        locations = []
        
        for func, pattern_info in func_patterns:
            function_names.append(func.name if hasattr(func, 'name') else 'unknown')
            if func.location and func.location.file:
                file_name = Path(func.location.file).name
                locations.append(f"{file_name}:{func.location.line}")
        
        message = f"Found {len(func_patterns)} functions with manual {pattern_type} implementation. {primary_pattern['suggestion']}"
        
        issue = self.create_issue(
            issue_id=f"manual-{pattern_type.replace('_', '-')}",
            message=message,
            severity="info",
            symbol=primary_func,
            pattern_type=pattern_type,
            suggestion=primary_pattern['suggestion'],
            confidence=primary_pattern['confidence'],
            functions_affected=len(func_patterns),
            function_names=function_names,
            locations=locations
        )
        
        return [issue]

    def _create_single_builtin_issue(self, func: Symbol, pattern_info: Dict) -> List[Issue]:
        """Create issue for a single builtin equivalent pattern."""
        message = f"Manual {pattern_info['pattern']} implementation detected. {pattern_info['suggestion']}"
        
        issue = self.create_issue(
            issue_id=f"manual-{pattern_info['pattern'].replace('_', '-')}",
            message=message,
            severity="info",
            symbol=func,
            pattern_type=pattern_info['pattern'],
            suggestion=pattern_info['suggestion'],
            confidence=pattern_info['confidence']
        )
        
        return [issue]

    def _create_control_flow_issues(self, pattern_type: str, func_patterns: List) -> List[Issue]:
        """Create issues for control flow equivalent patterns."""
        if len(func_patterns) < 2:
            return []
        
        primary_func, primary_pattern = func_patterns[0]
        
        function_names = []
        locations = []
        
        for func, pattern_info in func_patterns:
            function_names.append(func.name if hasattr(func, 'name') else 'unknown')
            if func.location and func.location.file:
                file_name = Path(func.location.file).name
                locations.append(f"{file_name}:{func.location.line}")
        
        message = f"Found {len(func_patterns)} functions with similar {pattern_type} control flow. {primary_pattern['suggestion']}"
        
        issue = self.create_issue(
            issue_id=f"control-flow-{pattern_type.replace('_', '-')}",
            message=message,
            severity="info",
            symbol=primary_func,
            pattern_type=pattern_type,
            suggestion=primary_pattern['suggestion'],
            functions_affected=len(func_patterns),
            function_names=function_names,
            locations=locations
        )
        
        return [issue]

    def _create_algorithmic_equivalent_issues(self, funcs: List[Symbol]) -> List[Issue]:
        """Create issues for algorithmically equivalent functions."""
        if len(funcs) < 2:
            return []
        
        primary_func = funcs[0]
        
        function_names = []
        locations = []
        
        for func in funcs:
            function_names.append(func.name if hasattr(func, 'name') else 'unknown')
            if func.location and func.location.file:
                file_name = Path(func.location.file).name
                locations.append(f"{file_name}:{func.location.line}")
        
        message = f"Found {len(funcs)} functions with similar algorithmic patterns. Consider consolidating into a single implementation."
        
        issue = self.create_issue(
            issue_id="algorithmic-equivalent",
            message=message,
            severity="info",
            symbol=primary_func,
            functions_affected=len(funcs),
            function_names=function_names,
            locations=locations
        )
        
        return [issue]
