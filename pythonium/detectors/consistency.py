"""
Inconsistent API Detector

This module detects inconsistent API patterns across similar functions in a codebase.
Inconsistent APIs can lead to confusion, bugs, and reduced developer productivity.

The detector identifies functions with similar purposes but inconsistent:
- Parameter names and ordering
- Naming conventions and patterns
- Return value patterns
- Function signatures and argument structures

Analysis approach:
1. Group functions by similarity (name patterns, purpose)
2. Analyze parameter ordering within each group
3. Check naming convention consistency
4. Identify return pattern inconsistencies
5. Report deviations from established patterns

Features:
- Configurable pattern recognition thresholds
- Support for various naming convention checks
- Parameter order analysis
- Return pattern consistency checks
- Grouping of similar functions for comparison

Example:
    ```python
    detector = InconsistentApiDetector(
        check_parameter_order=True,
        check_naming_patterns=True,
        min_functions_for_pattern=3
    )
    issues = detector.analyze(graph)
    ```
"""

import ast
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector

logger = logging.getLogger(__name__)


class InconsistentApiDetector(BaseDetector):
    """
    Detects inconsistent API patterns across similar functions.
    
    This detector identifies functions with similar names or purposes
    but inconsistent parameter orders, naming conventions, or signatures.
    Such inconsistencies can lead to developer confusion, increased cognitive
    load, and potential bugs from incorrect assumptions.
    
    The analysis process:
    1. Groups functions by similarity patterns (naming, purpose)
    2. Analyzes parameter consistency within each group
    3. Checks naming convention adherence
    4. Identifies return pattern inconsistencies
    5. Reports deviations from established patterns
    
    Configuration options:
    - check_parameter_order: Enable parameter order consistency checks
    - check_naming_patterns: Enable naming convention consistency checks
    - check_return_patterns: Enable return pattern consistency checks
    - min_functions_for_pattern: Minimum functions needed to establish a pattern
    
    Attributes:
        check_parameter_order: Whether to check parameter order consistency
        check_naming_patterns: Whether to check naming pattern consistency
        check_return_patterns: Whether to check return pattern consistency        min_functions_for_pattern: Minimum functions required for pattern analysis
    """
    
    id = "inconsistent_api"
    name = "Inconsistent API Detector"
    description = "Finds inconsistent function signatures and parameter patterns"
    
    # Enhanced metadata for MCP server
    category = "API Consistency"
    usage_tips = "Valuable for API design reviews and interface standardization"
    related_detectors = ["alt_implementation", "circular_deps"]
    typical_severity = "warn"
    detailed_description = ("Spots inconsistencies in function signatures, naming patterns, and API design "
                           "across similar functions that could confuse developers and lead to bugs.")
    
    def __init__(self, **options):
        """
        Initialize the inconsistent API detector.
        
        Args:
            check_parameter_order: Whether to analyze parameter order consistency
            check_naming_patterns: Whether to analyze naming pattern consistency
            check_return_patterns: Whether to analyze return pattern consistency            min_functions_for_pattern: Minimum number of functions required to
            establish a pattern for comparison
        """
        super().__init__(**options)
        self.check_parameter_order = options.get("check_parameter_order", True)
        self.check_naming_patterns = options.get("check_naming_patterns", True)
        self.check_return_patterns = options.get("check_return_patterns", True)
        self.min_functions_for_pattern = options.get("min_functions_for_pattern", 3)
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """
        Analyze the code graph for inconsistent API patterns.
        
        Args:
            graph: The code graph to analyze
              Returns:
            List of issues representing API inconsistencies
        """
        if not graph.symbols:
            return []
        
        issues = []
        
        # Group functions by similarity patterns
        function_groups = self._group_similar_functions(graph)
        
        for group_pattern, functions in function_groups.items():
            if len(functions) < self.min_functions_for_pattern:
                continue
            
            # Check parameter order consistency
            if self.check_parameter_order:
                parameter_issues = self._check_parameter_consistency(functions, group_pattern)
                issues.extend(parameter_issues)
            
            # Check naming pattern consistency
            if self.check_naming_patterns:
                issues.extend(self._check_naming_consistency(functions, group_pattern))
            
            # Check return pattern consistency
            if self.check_return_patterns:
                issues.extend(self._check_return_consistency(functions, group_pattern))
        
        return issues
    
    def _group_similar_functions(self, graph: CodeGraph) -> Dict[str, List[Symbol]]:
        """Group functions by similar naming patterns or purposes."""
        groups = defaultdict(list)
        
        for symbol in graph.symbols.values():
            if not isinstance(symbol.ast_node, ast.FunctionDef):
                continue
            
            func_name = symbol.ast_node.name
            
            # Skip special methods
            if func_name.startswith('__') and func_name.endswith('__'):
                continue
            
            # Group by common prefixes/suffixes
            group_key = self._extract_function_pattern(func_name)
            if group_key:
                groups[group_key].append(symbol)
        return dict(groups)
    
    def _extract_function_pattern(self, func_name: str) -> Optional[str]:
        """Extract a pattern from function name for grouping."""
        # Common patterns to look for
        patterns = [
            # CRUD operations
            ('create_', 'crud'),
            ('read_', 'crud'),
            ('update_', 'crud'),
            ('delete_', 'crud'),
            ('get_', 'getter'),
            ('set_', 'setter'),
            ('find_', 'finder'),
            ('search_', 'finder'),
            # Validation
            ('validate_', 'validator'),
            ('check_', 'validator'),
            ('verify_', 'validator'),
            ('is_', 'predicate'),
            ('has_', 'predicate'),
            ('can_', 'predicate'),
            # Processing
            ('process_', 'processor'),
            ('handle_', 'handler'),
            ('parse_', 'parser'),
            ('convert_', 'converter'),
            ('transform_', 'transformer'),
            # I/O operations
            ('load_', 'loader'),
            ('save_', 'saver'),
            ('write_', 'writer'),
            ('read_', 'reader'),
        ]
        
        for prefix, pattern in patterns:
            if func_name.startswith(prefix):
                # Extract entity type for more specific grouping
                # e.g., get_user_by_id, get_user_by_email -> get_user_by_*
                parts = func_name[len(prefix):].split('_')
                if len(parts) > 0:
                    entity_type = parts[0]  # e.g., "user" from "get_user_by_id"
                    if entity_type:
                        return f"{pattern}_{entity_type}"
                return pattern
        
        # Group by suffix patterns
        suffix_patterns = [
            ('_handler', 'handler'),
            ('_processor', 'processor'),
            ('_validator', 'validator'),
            ('_parser', 'parser'),
        ]
        
        for suffix, pattern in suffix_patterns:
            if func_name.endswith(suffix):
                return pattern
                
        # Check for camelCase vs snake_case in similar named functions
        # This helps group functions like getUserById and get_user_by_id
        normalized_name = ''
        if '_' in func_name:  # Snake case
            normalized_name = func_name.replace('_', '').lower()
        else:  # Possibly camelCase
            # Convert camelCase to lowercase
            normalized_name = ''.join([c.lower() for c in func_name])
            
        return f"normalized_{normalized_name}" if normalized_name else None
    def _check_parameter_consistency(self, functions: List[Symbol], group_pattern: str) -> List[Issue]:
        """Check if functions in the group have consistent parameter orders."""
        issues = []
        
        # Extract parameter signatures
        signatures = []
        for func_symbol in functions:
            func_node = func_symbol.ast_node
            if not isinstance(func_node, ast.FunctionDef):
                continue
            
            # Extract parameter names and types (if annotated)
            params = []
            for arg in func_node.args.args:
                param_info = {
                    'name': arg.arg,
                    'annotation': ast.unparse(arg.annotation) if arg.annotation else None
                }
                params.append(param_info)
            
            signatures.append({
                'symbol': func_symbol,
                'params': params,
                'param_names': [p['name'] for p in params]
            })
        
        # Check for specific parameter patterns (like id vs item_id vs order_id)
        param_patterns = defaultdict(list)
        for sig in signatures:
            for param in sig['params']:
                param_name = param['name']
                # Check for common parameter naming patterns
                if param_name.endswith('_id') or param_name == 'id':
                    param_patterns['id_param'].append((sig['symbol'], param_name))
                elif param_name.endswith('_name') or param_name == 'name':
                    param_patterns['name_param'].append((sig['symbol'], param_name))
                elif param_name.endswith('_number') or param_name.endswith('_num'):
                    param_patterns['number_param'].append((sig['symbol'], param_name))
        
        # Find inconsistent parameter naming
        for pattern_type, params in param_patterns.items():
            if len(set(p[1] for p in params)) > 1:
                issue = self.create_issue(
                    issue_id="inconsistent-parameter-naming",
                    message=f"Inconsistent parameter naming for {pattern_type.replace('_', ' ')} in {group_pattern} functions",
                    symbol=params[0][0],  # First occurrence
                    severity="warn",
                    pattern_type=pattern_type,
                    group_pattern=group_pattern,
                    inconsistent_params=[p[1] for p in params]
                )
                issues.append(issue)
        
        # Find common parameter patterns
        all_param_names = set()
        for sig in signatures:
            all_param_names.update(sig['param_names'])
        
        # Check for inconsistent ordering of common parameters
        common_params = []
        for param_name in all_param_names:
            appearances = 0
            for sig in signatures:
                if param_name in sig['param_names']:
                    appearances += 1
            
            # Consider it common if it appears in at least half the functions
            if appearances >= len(signatures) // 2:
                common_params.append(param_name)
        
        if len(common_params) >= 2:
            # Check if common parameters appear in consistent order
            param_orders = {}
            for sig in signatures:
                for i, param_name in enumerate(sig['param_names']):
                    if param_name in common_params:
                        if param_name not in param_orders:
                            param_orders[param_name] = []
                        param_orders[param_name].append((sig['symbol'], i))
            
            # Find inconsistencies
            for param_name, positions in param_orders.items():
                if len(set(pos for _, pos in positions)) > 1:
                    # Parameter appears at different positions
                    issue = self.create_issue(
                        issue_id="inconsistent-parameter-order",
                        message=f"Parameter '{param_name}' appears at different positions in {group_pattern} functions",
                        symbol=positions[0][0],  # First occurrence
                        severity="warn",
                        parameter_name=param_name,
                        group_pattern=group_pattern,
                        inconsistent_functions=[pos[0].fqname for pos in positions]
                    )
                    issues.append(issue)
        
        return issues
    def _check_naming_consistency(self, functions: List[Symbol], group_pattern: str) -> List[Issue]:
        """Check if functions follow consistent naming patterns."""
        issues = []
        
        # Extract naming patterns
        naming_styles = {
            'snake_case': 0,
            'camelCase': 0,
            'PascalCase': 0,
            'inconsistent': 0
        }
        
        style_examples = {
            'snake_case': [],
            'camelCase': [],
            'PascalCase': [],
            'inconsistent': []
        }
        
        for func_symbol in functions:
            func_name = func_symbol.ast_node.name
            
            # Determine naming style
            if '_' in func_name and func_name.islower():
                naming_styles['snake_case'] += 1
                style_examples['snake_case'].append(func_symbol)
            elif func_name[0].islower() and any(c.isupper() for c in func_name):
                naming_styles['camelCase'] += 1
                style_examples['camelCase'].append(func_symbol)
            elif func_name[0].isupper():
                naming_styles['PascalCase'] += 1
                style_examples['PascalCase'].append(func_symbol)
            else:
                naming_styles['inconsistent'] += 1
                style_examples['inconsistent'].append(func_symbol)
        
        # Find the dominant style
        dominant_style = max(naming_styles.items(), key=lambda x: x[1])
        
        # Always report if there are at least two different styles
        if any(count > 0 for style, count in naming_styles.items() if style != dominant_style[0]):
            styles_in_use = []
            examples = []
            
            for style, count in naming_styles.items():
                if count > 0 and len(style_examples[style]) > 0:
                    styles_in_use.append(style)
                    examples.append(f"{style}: {style_examples[style][0].ast_node.name}")
            
            issue = self.create_issue(
                issue_id="inconsistent-naming-style",
                message=f"Inconsistent naming styles in {group_pattern} functions: {', '.join(examples)}",
                symbol=functions[0],  # Representative function
                severity="info",
                group_pattern=group_pattern,
                dominant_style=dominant_style[0],
                function_count=len(functions),
                style_distribution=dict(naming_styles)
            )
            issues.append(issue)
        
        return issues
    
    def _check_return_consistency(self, functions: List[Symbol], group_pattern: str) -> List[Issue]:
        """Check if functions have consistent return patterns."""
        issues = []
        
        # Extract return patterns
        return_patterns = defaultdict(list)
        
        for func_symbol in functions:
            func_node = func_symbol.ast_node
            if not isinstance(func_node, ast.FunctionDef):
                continue
            
            # Check return annotation
            return_annotation = None
            if func_node.returns:
                return_annotation = ast.unparse(func_node.returns)
            
            # Analyze return statements
            return_types = set()
            for node in ast.walk(func_node):
                if isinstance(node, ast.Return):
                    if node.value is None:
                        return_types.add('None')
                    elif isinstance(node.value, ast.Constant):
                        return_types.add(type(node.value.value).__name__)
                    elif isinstance(node.value, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
                        return_types.add(type(node.value).__name__.lower())
                    else:
                        return_types.add('expression')
            
            pattern_key = (return_annotation, tuple(sorted(return_types)))
            return_patterns[pattern_key].append(func_symbol)
        
        # Check for inconsistencies
        if len(return_patterns) > 1:
            # Multiple return patterns found
            dominant_pattern = max(return_patterns.items(), key=lambda x: len(x[1]))
            
            if len(dominant_pattern[1]) < len(functions) * 0.8:
                issue = self.create_issue(
                    issue_id="inconsistent-return-pattern",
                    message=f"Inconsistent return patterns in {group_pattern} functions",
                    symbol=functions[0],  # Representative function
                    severity="info",
                    group_pattern=group_pattern,
                    pattern_count=len(return_patterns),
                    function_count=len(functions)
                )
                issues.append(issue)
        
        return issues
