"""
Advanced Pattern Recognition Detector

This detector identifies similar algorithmic patterns with different variable names,
structural similarities, and design pattern opportunities. It goes beyond simple
naming patterns to detect deep structural and behavioral similarities.

Features:
- AST-based structural pattern matching
- Variable name normalization for pattern comparison
- Design pattern detection (Factory, Strategy, Template Method, etc.)
- Algorithmic pattern recognition (sorting, searching, validation, etc.)
- Refactoring opportunity identification
"""

import ast
import logging
import re
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Optional, Any
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector

logger = logging.getLogger(__name__)


class PatternDetector(BaseDetector):
    """
    Detector for advanced code patterns and structural similarities.
    
    This detector identifies similar algorithmic patterns, design patterns,
    and refactoring opportunities across the codebase.
    """
    
    id = "advanced_patterns"
    name = "Pattern Detector"
    description = "Finds similar algorithmic patterns and design pattern opportunities"
    
    # Enhanced metadata for MCP server
    category = "Architecture & Design"
    usage_tips = "Use to identify design patterns and architectural improvements"
    related_detectors = ["semantic_equivalence", "alt_implementation"]
    typical_severity = "info"
    detailed_description = ("Recognizes common algorithmic patterns and design opportunities for better "
                           "code organization and architectural improvements.")
    
    def __init__(
        self,
        detect_algorithmic_patterns: bool = True,
        detect_design_patterns: bool = True,
        detect_validation_patterns: bool = True,
        detect_factory_patterns: bool = True,
        min_pattern_size: int = 3,
        similarity_threshold: float = 0.8,
        **options
    ):
        """
        Initialize the advanced pattern detector.
        
        Args:
            detect_algorithmic_patterns: Detect similar algorithms
            detect_design_patterns: Detect design pattern opportunities
            detect_validation_patterns: Detect similar validation logic
            detect_factory_patterns: Detect factory-like patterns
            min_pattern_size: Minimum size for pattern consideration
            similarity_threshold: Similarity threshold for pattern matching
            **options: Additional options passed to BaseDetector
        """
        super().__init__(**options)
        self.detect_algorithmic_patterns = detect_algorithmic_patterns
        self.detect_design_patterns = detect_design_patterns
        self.detect_validation_patterns = detect_validation_patterns
        self.detect_factory_patterns = detect_factory_patterns
        self.min_pattern_size = max(2, min_pattern_size)
        self.similarity_threshold = max(0.0, min(1.0, similarity_threshold))

    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph for advanced pattern issues."""
        issues = []
        
        # Get all symbols for analysis
        functions = [s for s in graph.symbols.values() 
                    if isinstance(s.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes = [s for s in graph.symbols.values() 
                  if isinstance(s.ast_node, ast.ClassDef)]
        
        if self.detect_algorithmic_patterns:
            issues.extend(self._detect_algorithmic_patterns(functions))
        
        if self.detect_design_patterns:
            issues.extend(self._detect_design_patterns(classes, functions))
        
        if self.detect_validation_patterns:
            issues.extend(self._detect_validation_patterns(functions))
        
        if self.detect_factory_patterns:
            issues.extend(self._detect_factory_patterns(functions, classes))
        
        return issues

    def _detect_algorithmic_patterns(self, functions: List[Symbol]) -> List[Issue]:
        """Detect similar algorithmic patterns across functions."""
        issues = []
        
        # Extract algorithmic signatures from functions
        algo_signatures = {}
        for func in functions:
            signature = self._extract_algorithmic_signature(func)
            if signature:
                algo_signatures[func] = signature
        
        # Find similar algorithmic patterns
        pattern_groups = self._group_by_algorithmic_similarity(algo_signatures)
        
        # Create issues for significant pattern groups
        for pattern_type, func_group in pattern_groups.items():
            if len(func_group) >= 2:
                issues.extend(self._create_algorithmic_pattern_issues(pattern_type, func_group))
        
        return issues

    def _extract_algorithmic_signature(self, func: Symbol) -> Optional[Dict]:
        """Extract an algorithmic signature from a function."""
        try:
            signature = {
                'control_flow': self._extract_control_flow_pattern(func.ast_node),
                'operation_sequence': self._extract_operation_sequence(func.ast_node),
                'data_flow': self._extract_data_flow_pattern(func.ast_node),
                'complexity_metrics': self._calculate_complexity_metrics(func.ast_node)
            }
            
            # Only return signature if it has meaningful content
            if any(signature.values()):
                return signature
            return None
            
        except Exception:
            return None

    def _extract_control_flow_pattern(self, node: ast.FunctionDef) -> List[str]:
        """Extract control flow pattern from function."""
        pattern = []
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.For):
                pattern.append('FOR')
            elif isinstance(stmt, ast.While):
                pattern.append('WHILE')
            elif isinstance(stmt, ast.If):
                pattern.append('IF')
            elif isinstance(stmt, ast.Try):
                pattern.append('TRY')
            elif isinstance(stmt, ast.With):
                pattern.append('WITH')
            elif isinstance(stmt, ast.Return):
                pattern.append('RETURN')
        
        return pattern

    def _extract_operation_sequence(self, node: ast.FunctionDef) -> List[str]:
        """Extract sequence of operations from function."""
        operations = []
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Assign):
                operations.append('ASSIGN')
            elif isinstance(stmt, ast.AugAssign):
                operations.append('AUG_ASSIGN')
            elif isinstance(stmt, ast.Call):
                operations.append('CALL')
            elif isinstance(stmt, ast.Compare):
                operations.append('COMPARE')
            elif isinstance(stmt, ast.BinOp):
                operations.append('BINOP')
        
        return operations

    def _extract_data_flow_pattern(self, node: ast.FunctionDef) -> Dict[str, int]:
        """Extract data flow pattern from function."""
        pattern = {
            'list_operations': 0,
            'dict_operations': 0,
            'string_operations': 0,
            'numeric_operations': 0,
            'file_operations': 0
        }
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Name):
                func_name = stmt.func.id
                
                # List operations
                if func_name in ('append', 'extend', 'insert', 'remove', 'pop', 'sort', 'reverse'):
                    pattern['list_operations'] += 1
                elif func_name in ('list', 'len', 'sum', 'sorted', 'reversed'):
                    pattern['list_operations'] += 1
                
                # Dict operations
                elif func_name in ('get', 'keys', 'values', 'items', 'update', 'pop'):
                    pattern['dict_operations'] += 1
                elif func_name in ('dict',):
                    pattern['dict_operations'] += 1
                
                # String operations
                elif func_name in ('split', 'join', 'replace', 'strip', 'upper', 'lower'):
                    pattern['string_operations'] += 1
                elif func_name in ('str', 'format'):
                    pattern['string_operations'] += 1
                
                # File operations
                elif func_name in ('open', 'read', 'write', 'close'):
                    pattern['file_operations'] += 1
        
        return pattern

    def _calculate_complexity_metrics(self, node: ast.FunctionDef) -> Dict[str, int]:
        """Calculate complexity metrics for the function."""
        metrics = {
            'cyclomatic_complexity': 1,  # Base complexity
            'nesting_depth': 0,
            'function_calls': 0,
            'branches': 0
        }
        
        # Calculate cyclomatic complexity
        for stmt in ast.walk(node):
            if isinstance(stmt, (ast.If, ast.For, ast.While, ast.Try)):
                metrics['cyclomatic_complexity'] += 1
                metrics['branches'] += 1
            elif isinstance(stmt, ast.Call):
                metrics['function_calls'] += 1
        
        # Calculate nesting depth
        metrics['nesting_depth'] = self._calculate_nesting_depth(node)
        
        return metrics

    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth."""
        def depth(node, current_depth=0):
            max_depth = current_depth
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    child_depth = depth(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = depth(child, current_depth)
                    max_depth = max(max_depth, child_depth)
            return max_depth
        
        return depth(node)

    def _group_by_algorithmic_similarity(self, algo_signatures: Dict) -> Dict[str, List[Symbol]]:
        """Group functions by algorithmic similarity."""
        groups = defaultdict(list)
        
        # Convert signatures to comparable format
        comparable_sigs = {}
        for func, sig in algo_signatures.items():
            comparable = self._make_signature_comparable(sig)
            comparable_sigs[func] = comparable
        
        # Group similar signatures
        processed = set()
        
        for func1, sig1 in comparable_sigs.items():
            if func1 in processed:
                continue
            
            similar_funcs = [func1]
            processed.add(func1)
            
            for func2, sig2 in comparable_sigs.items():
                if func2 in processed:
                    continue
                
                similarity = self._calculate_signature_similarity(sig1, sig2)
                if similarity >= self.similarity_threshold:
                    similar_funcs.append(func2)
                    processed.add(func2)
            
            if len(similar_funcs) >= 2:
                # Determine pattern type
                pattern_type = self._determine_pattern_type(sig1)
                groups[pattern_type].extend(similar_funcs)
        
        return dict(groups)

    def _make_signature_comparable(self, signature: Dict) -> Dict:
        """Convert signature to comparable format."""
        comparable = {}
        
        # Normalize control flow to ratios
        control_flow = signature.get('control_flow', [])
        if control_flow:
            flow_counter = Counter(control_flow)
            total = len(control_flow)
            comparable['control_flow_ratios'] = {k: v/total for k, v in flow_counter.items()}
        
        # Normalize operation sequence
        operations = signature.get('operation_sequence', [])
        if operations:
            op_counter = Counter(operations)
            total = len(operations)
            comparable['operation_ratios'] = {k: v/total for k, v in op_counter.items()}
        
        # Keep data flow and complexity as-is
        comparable['data_flow'] = signature.get('data_flow', {})
        comparable['complexity'] = signature.get('complexity_metrics', {})
        
        return comparable

    def _calculate_signature_similarity(self, sig1: Dict, sig2: Dict) -> float:
        """Calculate similarity between two algorithmic signatures."""
        similarities = []
        
        # Control flow similarity
        flow1 = sig1.get('control_flow_ratios', {})
        flow2 = sig2.get('control_flow_ratios', {})
        if flow1 or flow2:
            flow_sim = self._calculate_dict_similarity(flow1, flow2)
            similarities.append(flow_sim)
        
        # Operation similarity
        op1 = sig1.get('operation_ratios', {})
        op2 = sig2.get('operation_ratios', {})
        if op1 or op2:
            op_sim = self._calculate_dict_similarity(op1, op2)
            similarities.append(op_sim)
        
        # Data flow similarity
        data1 = sig1.get('data_flow', {})
        data2 = sig2.get('data_flow', {})
        if data1 or data2:
            data_sim = self._calculate_numeric_dict_similarity(data1, data2)
            similarities.append(data_sim)
        
        # Return average similarity
        return sum(similarities) / len(similarities) if similarities else 0.0

    def _calculate_dict_similarity(self, dict1: Dict, dict2: Dict) -> float:
        """Calculate similarity between two dictionaries."""
        if not dict1 and not dict2:
            return 1.0
        if not dict1 or not dict2:
            return 0.0
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        if not all_keys:
            return 1.0
        
        total_diff = 0.0
        for key in all_keys:
            val1 = dict1.get(key, 0)
            val2 = dict2.get(key, 0)
            total_diff += abs(val1 - val2)
        
        # Normalize by maximum possible difference
        max_diff = len(all_keys)
        return 1.0 - (total_diff / max_diff) if max_diff > 0 else 1.0

    def _calculate_numeric_dict_similarity(self, dict1: Dict, dict2: Dict) -> float:
        """Calculate similarity between dictionaries with numeric values."""
        if not dict1 and not dict2:
            return 1.0
        if not dict1 or not dict2:
            return 0.0
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        if not all_keys:
            return 1.0
        
        similarities = []
        for key in all_keys:
            val1 = dict1.get(key, 0)
            val2 = dict2.get(key, 0)
            
            if val1 == 0 and val2 == 0:
                similarities.append(1.0)
            elif val1 == 0 or val2 == 0:
                similarities.append(0.0)
            else:
                # Calculate relative similarity
                max_val = max(val1, val2)
                min_val = min(val1, val2)
                similarities.append(min_val / max_val)
        
        return sum(similarities) / len(similarities) if similarities else 0.0

    def _determine_pattern_type(self, signature: Dict) -> str:
        """Determine the type of algorithmic pattern."""
        control_flow = signature.get('control_flow_ratios', {})
        data_flow = signature.get('data_flow', {})
        
        # Determine pattern based on characteristics
        if control_flow.get('FOR', 0) > 0.5:
            if data_flow.get('list_operations', 0) > 2:
                return 'list_processing'
            elif data_flow.get('string_operations', 0) > 2:
                return 'string_processing'
            else:
                return 'iteration_heavy'
        
        elif control_flow.get('IF', 0) > 0.5:
            return 'conditional_logic'
        
        elif data_flow.get('dict_operations', 0) > 2:
            return 'dict_processing'
        
        elif data_flow.get('file_operations', 0) > 0:
            return 'file_processing'
        
        else:
            return 'general_algorithm'

    def _detect_design_patterns(self, classes: List[Symbol], functions: List[Symbol]) -> List[Issue]:
        """Detect design pattern opportunities."""
        issues = []
        
        # Factory pattern detection
        factory_candidates = self._detect_factory_pattern_candidates(functions)
        for candidates in factory_candidates:
            if len(candidates) >= 2:
                issues.extend(self._create_factory_pattern_issues(candidates))
        
        # Strategy pattern detection
        strategy_candidates = self._detect_strategy_pattern_candidates(classes, functions)
        for candidates in strategy_candidates:
            if len(candidates) >= 2:
                issues.extend(self._create_strategy_pattern_issues(candidates))
        
        return issues

    def _detect_factory_pattern_candidates(self, functions: List[Symbol]) -> List[List[Symbol]]:
        """Detect functions that could benefit from factory pattern."""
        candidates = []
        
        # Look for functions that create objects based on parameters
        factory_like = []
        for func in functions:
            if self._is_factory_like(func):
                factory_like.append(func)
        
        # Group by class or module
        class_groups = {}
        for func in factory_like:
            # Extract class name from fqname
            parts = func.fqname.split('.')
            if len(parts) >= 2:
                class_key = '.'.join(parts[:-1])  # Everything except the method name
            else:
                class_key = 'module_level'
            
            if class_key not in class_groups:
                class_groups[class_key] = []
            class_groups[class_key].append(func)
        
        # Add groups that have multiple factory methods
        for group in class_groups.values():
            if len(group) >= 2:
                candidates.append(group)
        
        return candidates

    def _is_factory_like(self, func: Symbol) -> bool:
        """Check if function is factory-like."""
        # Look for functions that create/return objects
        has_object_creation = False
        is_static_or_class_method = False
        
        # Check if it's a static method or class method
        if hasattr(func.ast_node, 'decorator_list'):
            for decorator in func.ast_node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id in ('staticmethod', 'classmethod'):
                    is_static_or_class_method = True
                    break
        
        # Check for object creation patterns
        for node in ast.walk(func.ast_node):
            if isinstance(node, ast.Return):
                if isinstance(node.value, (ast.Dict, ast.Call)):
                    has_object_creation = True
                    break
                elif isinstance(node.value, ast.Name) and node.value.id in ('self', 'cls'):
                    has_object_creation = True
                    break
        
        # Look for factory naming patterns
        factory_patterns = ['create', 'make', 'build', 'construct', 'generate', 'new']
        has_factory_name = any(pattern in func.fqname.lower() for pattern in factory_patterns)
        
        return (is_static_or_class_method and has_object_creation) or (has_factory_name and has_object_creation)

    def _detect_strategy_pattern_candidates(self, classes: List[Symbol], functions: List[Symbol]) -> List[List[Symbol]]:
        """Detect classes/functions that could benefit from strategy pattern."""
        candidates = []
        
        # Look for classes with similar method signatures
        similar_classes = []
        for cls in classes:
            methods = self._extract_class_methods(cls)
            if len(methods) >= 2:
                similar_classes.append((cls, methods))
        
        # Group classes with similar method patterns
        if len(similar_classes) >= 2:
            groups = self._group_similar_classes(similar_classes)
            candidates.extend(groups)
        
        return candidates

    def _extract_class_methods(self, cls: Symbol) -> List[str]:
        """Extract method names from a class."""
        methods = []
        for node in cls.ast_node.body:
            if isinstance(node, ast.FunctionDef):
                methods.append(node.name)
        return methods

    def _group_similar_classes(self, class_methods: List[Tuple]) -> List[List[Symbol]]:
        """Group classes with similar method patterns."""
        groups = []
        processed = set()
        
        for i, (cls1, methods1) in enumerate(class_methods):
            if i in processed:
                continue
            
            group = [cls1]
            processed.add(i)
            
            for j, (cls2, methods2) in enumerate(class_methods[i+1:], i+1):
                if j in processed:
                    continue
                
                # Check method similarity
                common = set(methods1) & set(methods2)
                total = set(methods1) | set(methods2)
                
                if len(common) / len(total) >= 0.5:  # 50% method overlap
                    group.append(cls2)
                    processed.add(j)
            
            if len(group) >= 2:
                groups.append(group)
        
        return groups

    def _detect_validation_patterns(self, functions: List[Symbol]) -> List[Issue]:
        """Detect similar validation patterns."""
        issues = []
        
        validation_functions = []
        for func in functions:
            if self._is_validation_function(func):
                validation_functions.append(func)
        
        if len(validation_functions) >= 2:
            # Group by validation type
            groups = self._group_validation_functions(validation_functions)
            for group_type, funcs in groups.items():
                if len(funcs) >= 2:
                    issues.extend(self._create_validation_pattern_issues(group_type, funcs))
        
        return issues

    def _is_validation_function(self, func: Symbol) -> bool:
        """Check if function appears to be for validation."""
        func_name = func.name if hasattr(func, 'name') else ''
        
        # Name-based detection
        validation_keywords = ['validate', 'check', 'verify', 'is_valid', 'ensure']
        if any(keyword in func_name.lower() for keyword in validation_keywords):
            return True
        
        # Pattern-based detection
        has_checks = False
        has_boolean_return = False
        
        for node in ast.walk(func.ast_node):
            if isinstance(node, ast.Compare):
                has_checks = True
            elif isinstance(node, ast.Return):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    has_boolean_return = True
        
        return has_checks and has_boolean_return

    def _group_validation_functions(self, functions: List[Symbol]) -> Dict[str, List[Symbol]]:
        """Group validation functions by type."""
        groups = defaultdict(list)
        
        for func in functions:
            validation_type = self._determine_validation_type(func)
            groups[validation_type].append(func)
        
        return dict(groups)

    def _determine_validation_type(self, func: Symbol) -> str:
        """Determine the type of validation."""
        func_name = func.name if hasattr(func, 'name') else ''
        
        if 'email' in func_name.lower():
            return 'email_validation'
        elif 'phone' in func_name.lower():
            return 'phone_validation'
        elif 'url' in func_name.lower():
            return 'url_validation'
        elif 'password' in func_name.lower():
            return 'password_validation'
        elif 'date' in func_name.lower():
            return 'date_validation'
        else:
            return 'general_validation'

    def _detect_factory_patterns(self, functions: List[Symbol], classes: List[Symbol]) -> List[Issue]:
        """Detect factory pattern opportunities."""
        # This is already covered in _detect_design_patterns
        return []

    # Issue creation methods

    def _create_algorithmic_pattern_issues(self, pattern_type: str, funcs: List[Symbol]) -> List[Issue]:
        """Create issues for algorithmic pattern groups."""
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
        
        message = f"Found {len(funcs)} functions with similar {pattern_type} patterns. Consider consolidating into a shared utility."
        
        issue = self.create_issue(
            issue_id=f"similar-{pattern_type.replace('_', '-')}",
            message=message,
            severity="info",
            symbol=primary_func,
            pattern_type=pattern_type,
            functions_affected=len(funcs),
            function_names=function_names,
            locations=locations
        )
        
        return [issue]

    def _create_factory_pattern_issues(self, candidates: List[Symbol]) -> List[Issue]:
        """Create issues for factory pattern opportunities."""
        primary_func = candidates[0]
        
        function_names = []
        locations = []
        
        for func in candidates:
            function_names.append(func.name if hasattr(func, 'name') else 'unknown')
            if func.location and func.location.file:
                file_name = Path(func.location.file).name
                locations.append(f"{file_name}:{func.location.line}")
        
        message = f"Found {len(candidates)} functions with factory-like patterns. Consider implementing Factory design pattern."
        
        issue = self.create_issue(
            issue_id="factory-pattern-opportunity",
            message=message,
            severity="info",
            symbol=primary_func,
            pattern_type="factory",
            functions_affected=len(candidates),
            function_names=function_names,
            locations=locations
        )
        
        return [issue]

    def _create_strategy_pattern_issues(self, candidates: List[Symbol]) -> List[Issue]:
        """Create issues for strategy pattern opportunities."""
        primary_class = candidates[0]
        
        class_names = []
        locations = []
        
        for cls in candidates:
            class_names.append(cls.name if hasattr(cls, 'name') else 'unknown')
            if cls.location and cls.location.file:
                file_name = Path(cls.location.file).name
                locations.append(f"{file_name}:{cls.location.line}")
        
        message = f"Found {len(candidates)} classes with similar method patterns. Consider implementing Strategy design pattern."
        
        issue = self.create_issue(
            issue_id="strategy-pattern-opportunity",
            message=message,
            severity="info",
            symbol=primary_class,
            pattern_type="strategy",
            classes_affected=len(candidates),
            class_names=class_names,
            locations=locations
        )
        
        return [issue]

    def _create_validation_pattern_issues(self, group_type: str, funcs: List[Symbol]) -> List[Issue]:
        """Create issues for validation pattern groups."""
        primary_func = funcs[0]
        
        function_names = []
        locations = []
        
        for func in funcs:
            function_names.append(func.name if hasattr(func, 'name') else 'unknown')
            if func.location and func.location.file:
                file_name = Path(func.location.file).name
                locations.append(f"{file_name}:{func.location.line}")
        
        message = f"Found {len(funcs)} similar {group_type} functions. Consider consolidating into a validation framework."
        
        issue = self.create_issue(
            issue_id=f"validation-{group_type.replace('_', '-')}",
            message=message,
            severity="info",
            symbol=primary_func,
            validation_type=group_type,
            functions_affected=len(funcs),
            function_names=function_names,
            locations=locations
        )
        
        return [issue]
