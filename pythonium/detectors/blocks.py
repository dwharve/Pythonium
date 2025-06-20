"""
Block-Level Clone Detector

This detector finds duplicate code blocks within and across functions, not just 
complete function clones. It can detect duplicated logic within function bodies,
initialization patterns, validation blocks, etc.

Features:
- Detects clones at arbitrary code block levels (statements, expressions)
- Finds duplicated patterns within functions (e.g., repeated validation logic)
- Cross-function block detection (same logic in different functions)
- Configurable minimum block size and similarity thresholds
- Advanced AST-based comparison with normalization
"""

import ast
import hashlib
from collections import defaultdict, deque
from typing import List, Dict, Tuple, Set, Optional
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector


class BlockCloneDetector(BaseDetector):
    """
    Detector for block-level code clones within and across functions.
    
    This detector analyzes arbitrary code blocks (sequences of statements) rather
    than just complete functions, enabling detection of duplicated logic patterns
    within function bodies.
    """
    
    id = "block_clone"
    name = "Block Clone Detector"
    description = "Finds duplicate code blocks within and across functions"
    
    # Enhanced metadata for MCP server
    category = "Code Duplication"
    usage_tips = "Use for fine-grained duplicate detection at statement level"
    related_detectors = ["clone", "semantic_equivalence"]
    typical_severity = "warn"
    detailed_description = ("Detects duplicate code blocks within function bodies and across functions "
                           "to identify fine-grained refactoring opportunities.")
    
    def __init__(
        self,
        min_statements: int = 3,
        max_statements: int = 20,
        similarity_threshold: float = 0.9,
        ignore_variable_names: bool = True,
        ignore_string_literals: bool = True,
        ignore_numeric_literals: bool = True,
        cross_function_only: bool = False,
        **options
    ):
        """
        Initialize the block-level clone detector.
        
        Args:
            min_statements: Minimum number of statements in a block to consider
            max_statements: Maximum number of statements to analyze at once
            similarity_threshold: Similarity threshold for near-clone detection
            ignore_variable_names: Whether to ignore variable name differences
            ignore_string_literals: Whether to ignore string literal differences
            ignore_numeric_literals: Whether to ignore numeric literal differences
            cross_function_only: Only detect clones across different functions
            **options: Additional options passed to BaseDetector
        """
        super().__init__(**options)
        self.min_statements = max(2, min_statements)
        self.max_statements = max(self.min_statements, max_statements)
        self.similarity_threshold = max(0.0, min(1.0, similarity_threshold))
        self.ignore_variable_names = ignore_variable_names
        self.ignore_string_literals = ignore_string_literals
        self.ignore_numeric_literals = ignore_numeric_literals
        self.cross_function_only = cross_function_only

    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph for block-level clone issues."""
        # Extract all code blocks from functions
        all_blocks = self._extract_code_blocks(graph)
        
        if len(all_blocks) < 2:
            return []
        
        # Find similar blocks
        clone_groups = self._find_clone_groups(all_blocks)
        
        # Create issues for clone groups
        issues = []
        for clone_group in clone_groups:
            if len(clone_group) >= 2:
                issues.extend(self._create_block_clone_issues(clone_group))
        
        return issues

    def _extract_code_blocks(self, graph: CodeGraph) -> List[Dict]:
        """Extract all meaningful code blocks from the graph."""
        blocks = []
        
        for symbol in graph.symbols.values():
            if not isinstance(symbol.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            
            # Extract blocks from function body
            function_blocks = self._extract_blocks_from_function(symbol)
            blocks.extend(function_blocks)
        
        return blocks

    def _extract_blocks_from_function(self, symbol: Symbol) -> List[Dict]:
        """Extract code blocks from a single function."""
        blocks = []
        body = symbol.ast_node.body
        
        # Sliding window approach to extract blocks
        for start_idx in range(len(body)):
            for end_idx in range(start_idx + self.min_statements, 
                                min(start_idx + self.max_statements + 1, len(body) + 1)):
                
                block_statements = body[start_idx:end_idx]
                
                # Skip blocks with only docstrings or pass statements
                if self._is_trivial_block(block_statements):
                    continue
                
                # Create block info
                block_info = {
                    'statements': block_statements,
                    'function_symbol': symbol,
                    'start_line': getattr(block_statements[0], 'lineno', 0),
                    'end_line': getattr(block_statements[-1], 'lineno', 0),
                    'normalized_source': self._normalize_block(block_statements),
                    'fingerprint': self._compute_block_fingerprint(block_statements)
                }
                
                blocks.append(block_info)
        
        return blocks

    def _is_trivial_block(self, statements: List[ast.stmt]) -> bool:
        """Check if a block is trivial (only docstrings, pass, etc.)."""
        meaningful_count = 0
        
        for stmt in statements:
            # Skip docstrings (first statement that's a string)
            if (isinstance(stmt, ast.Expr) and 
                isinstance(stmt.value, ast.Constant) and 
                isinstance(stmt.value.value, str)):
                continue
            
            # Skip pass statements
            if isinstance(stmt, ast.Pass):
                continue
            
            meaningful_count += 1
        
        return meaningful_count < 2

    def _normalize_block(self, statements: List[ast.stmt]) -> str:
        """Normalize a block of statements for comparison."""
        try:
            # Create a temporary module with the statements
            temp_module = ast.Module(body=statements, type_ignores=[])
            
            # Apply normalization
            if self.ignore_variable_names:
                temp_module = self._normalize_variable_names(temp_module)
            
            if self.ignore_string_literals:
                temp_module = self._normalize_string_literals(temp_module)
            
            if self.ignore_numeric_literals:
                temp_module = self._normalize_numeric_literals(temp_module)
            
            # Convert back to source
            normalized_source = ast.unparse(temp_module)
            
            # Remove extra whitespace
            return ' '.join(normalized_source.split())
            
        except Exception:
            # Fallback: just unparse the original
            try:
                temp_module = ast.Module(body=statements, type_ignores=[])
                return ast.unparse(temp_module)
            except:
                return ""

    def _normalize_variable_names(self, node: ast.AST) -> ast.AST:
        """Replace variable names with normalized placeholders."""
        class VariableNormalizer(ast.NodeTransformer):
            def __init__(self):
                self.var_map = {}
                self.counter = 0
            
            def visit_Name(self, node):
                if isinstance(node.ctx, (ast.Store, ast.Load)):
                    if node.id not in self.var_map:
                        self.var_map[node.id] = f"var_{self.counter}"
                        self.counter += 1
                    node.id = self.var_map[node.id]
                return node
        
        normalizer = VariableNormalizer()
        return normalizer.visit(node)

    def _normalize_string_literals(self, node: ast.AST) -> ast.AST:
        """Replace string literals with placeholders."""
        class StringNormalizer(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, str):
                    node.value = "STRING_LITERAL"
                return node
        
        normalizer = StringNormalizer()
        return normalizer.visit(node)

    def _normalize_numeric_literals(self, node: ast.AST) -> ast.AST:
        """Replace numeric literals with placeholders."""
        class NumericNormalizer(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, (int, float)):
                    node.value = 0 if isinstance(node.value, int) else 0.0
                return node
        
        normalizer = NumericNormalizer()
        return normalizer.visit(node)

    def _compute_block_fingerprint(self, statements: List[ast.stmt]) -> str:
        """Compute a fingerprint for the block structure."""
        try:
            # Create a structural representation
            structure_parts = []
            
            for stmt in statements:
                # Get the type and key structural elements
                stmt_type = type(stmt).__name__
                
                if isinstance(stmt, ast.Assign):
                    # Track assignment patterns
                    targets = len(stmt.targets)
                    structure_parts.append(f"Assign_{targets}")
                elif isinstance(stmt, ast.If):
                    # Track conditional structure
                    has_else = bool(stmt.orelse)
                    structure_parts.append(f"If_{has_else}")
                elif isinstance(stmt, ast.For):
                    # Track loop structure
                    has_else = bool(stmt.orelse)
                    structure_parts.append(f"For_{has_else}")
                elif isinstance(stmt, ast.While):
                    # Track loop structure
                    has_else = bool(stmt.orelse)
                    structure_parts.append(f"While_{has_else}")
                else:
                    structure_parts.append(stmt_type)
            
            # Create fingerprint from structure
            structure_str = "_".join(structure_parts)
            return hashlib.md5(structure_str.encode()).hexdigest()[:8]
            
        except Exception:
            return "unknown"

    def _find_clone_groups(self, blocks: List[Dict]) -> List[List[Dict]]:
        """Find groups of similar blocks."""
        if self.similarity_threshold >= 1.0:
            # Exact matching
            return self._find_exact_clone_groups(blocks)
        else:
            # Similarity matching
            return self._find_similar_clone_groups(blocks)

    def _find_exact_clone_groups(self, blocks: List[Dict]) -> List[List[Dict]]:
        """Find groups of exactly identical blocks."""
        groups_by_source = defaultdict(list)
        
        for block in blocks:
            normalized_source = block['normalized_source']
            if normalized_source:  # Skip empty/invalid blocks
                groups_by_source[normalized_source].append(block)
        
        # Filter groups and apply cross-function constraint
        clone_groups = []
        for source, group in groups_by_source.items():
            if len(group) >= 2:
                if self.cross_function_only:
                    # Only include if blocks are from different functions
                    functions = {block['function_symbol'] for block in group}
                    if len(functions) > 1:
                        clone_groups.append(group)
                else:
                    clone_groups.append(group)
        
        return clone_groups

    def _find_similar_clone_groups(self, blocks: List[Dict]) -> List[List[Dict]]:
        """Find groups of similar blocks using fingerprints."""
        # Group by fingerprint first (structural similarity)
        groups_by_fingerprint = defaultdict(list)
        
        for block in blocks:
            fingerprint = block['fingerprint']
            groups_by_fingerprint[fingerprint].append(block)
        
        clone_groups = []
        
        # For each fingerprint group, check source similarity
        for fingerprint, candidates in groups_by_fingerprint.items():
            if len(candidates) < 2:
                continue
            
            # Find similar pairs within the fingerprint group
            similar_groups = self._cluster_similar_blocks(candidates)
            
            for group in similar_groups:
                if len(group) >= 2:
                    if self.cross_function_only:
                        functions = {block['function_symbol'] for block in group}
                        if len(functions) > 1:
                            clone_groups.append(group)
                    else:
                        clone_groups.append(group)
        
        return clone_groups

    def _cluster_similar_blocks(self, blocks: List[Dict]) -> List[List[Dict]]:
        """Cluster blocks by source similarity."""
        # Simple clustering: if similarity >= threshold, group together
        groups = []
        used = set()
        
        for i, block1 in enumerate(blocks):
            if i in used:
                continue
            
            group = [block1]
            used.add(i)
            
            for j, block2 in enumerate(blocks[i+1:], i+1):
                if j in used:
                    continue
                
                similarity = self._calculate_source_similarity(
                    block1['normalized_source'], 
                    block2['normalized_source']
                )
                
                if similarity >= self.similarity_threshold:
                    group.append(block2)
                    used.add(j)
            
            if len(group) >= 2:
                groups.append(group)
        
        return groups

    def _calculate_source_similarity(self, source1: str, source2: str) -> float:
        """Calculate similarity between two normalized source strings."""
        if not source1 or not source2:
            return 0.0
        
        if source1 == source2:
            return 1.0
        
        # Use token-based Jaccard similarity
        tokens1 = set(source1.split())
        tokens2 = set(source2.split())
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0

    def _create_block_clone_issues(self, clone_group: List[Dict]) -> List[Issue]:
        """Create issues for a group of cloned blocks."""
        if len(clone_group) < 2:
            return []
        
        # Use the first block as the primary location
        primary_block = clone_group[0]
        primary_symbol = primary_block['function_symbol']
        
        # Collect all locations
        locations = []
        function_names = set()
        
        for block in clone_group:
            symbol = block['function_symbol']
            function_names.add(symbol.name if hasattr(symbol, 'name') else 'unknown')
            
            if symbol.location and symbol.location.file:
                file_name = Path(symbol.location.file).name
                start_line = block['start_line']
                end_line = block['end_line']
                locations.append(f"{file_name}:{start_line}-{end_line}")
        
        # Create descriptive message
        block_size = len(primary_block['statements'])
        if len(function_names) > 1:
            message = f"Found {len(clone_group)} duplicate code blocks ({block_size} statements each) across {len(function_names)} functions"
        else:
            message = f"Found {len(clone_group)} duplicate code blocks ({block_size} statements each) within the same function"
        
        # Create source preview
        try:
            temp_module = ast.Module(body=primary_block['statements'], type_ignores=[])
            source_preview = ast.unparse(temp_module)
            preview_lines = source_preview.splitlines()[:3]
            source_preview = '\n'.join(preview_lines)
            if len(primary_block['statements']) > 3:
                source_preview += '\n...'
        except:
            source_preview = f"{block_size} statements"
        
        issue = self.create_issue(
            issue_id="duplicate-block",
            message=message,
            severity="warn",
            symbol=primary_symbol,
            block_size=block_size,
            clone_count=len(clone_group),
            functions_affected=len(function_names),
            locations=locations,
            source_preview=source_preview
        )
        
        return [issue]
