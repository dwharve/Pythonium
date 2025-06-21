"""
Clone Detector

This module detects both exact and near code clones in Python source files.
Code clones are blocks of code that are identical or similar across the codebase
and can often be refactored into shared functions to reduce duplication and
improve maintainability.

The detector performs analysis by:
- Tokenizing source code blocks and computing fingerprints
- Using configurable similarity thresholds (1.0 for exact, <1.0 for near clones)
- Supporting various normalization options (comments, whitespace, imports, etc.)
- Finding clone groups with similarity metadata
- Reporting groups with location information and similarity scores

Features:
- Exact and near clone detection via similarity threshold
- Configurable minimum line threshold to avoid noise
- Multiple similarity algorithms (token-based, n-gram with winnowing)
- Optional ignoring of imports, docstrings, comments, and whitespace
- Clone group metadata with similarity scores and locations

Example:
    ```python
    # Exact clones only
    detector = CloneDetector(similarity_threshold=1.0, min_lines=5)
    
    # Near clones (80% similarity)
    detector = CloneDetector(similarity_threshold=0.8, min_lines=5)
    
    issues = detector.analyze(graph)
    ```
"""

import ast
import hashlib
import logging
import tokenize
from collections import defaultdict
from io import BytesIO
from typing import List, Dict, Tuple, Set, Optional
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector

logger = logging.getLogger(__name__)


class CloneDetector(BaseDetector):
    """
    Detector for both exact and near code clones.
    
    This detector identifies blocks of code that are identical or similar across
    the codebase. The similarity threshold parameter controls whether to detect
    exact clones (1.0) or near clones (< 1.0).
    
    Attributes:
        id: Detector identifier 'clone'
        name: Human-readable detector name
        description: What this detector checks for
    """
    
    id = "clone"
    name = "Clone Detector"
    description = "Finds duplicate and similar code blocks with configurable similarity threshold"
    
    # Enhanced metadata for MCP server
    category = "Code Duplication"
    usage_tips = "Use to identify refactoring opportunities and reduce technical debt"
    related_detectors = ["semantic_equivalence", "advanced_patterns", "block_clone"]
    typical_severity = "warn"
    detailed_description = ("Detects duplicate code blocks that could be refactored into shared functions "
                           "or modules to reduce maintenance burden and improve code organization.")
    
    def __init__(
        self,
        similarity_threshold: float = 0.9,
        min_lines: int = 5,
        ngram_size: int = 4,
        ignore_imports: bool = True,
        ignore_docstrings: bool = True,
        ignore_comments: bool = True,
        ignore_whitespace: bool = True,
        **options
    ):
        """
        Initialize the clone detector.
        
        Args:
            similarity_threshold: Similarity threshold (1.0 = exact, < 1.0 = near clones)
            min_lines: Minimum number of lines to consider for clone detection
            ngram_size: Size of n-grams for similarity computation (for near clones)
            ignore_imports: Whether to ignore import statements in similarity
            ignore_docstrings: Whether to ignore docstrings in similarity
            ignore_comments: Whether to ignore comments in similarity
            ignore_whitespace: Whether to ignore whitespace differences
            **options: Additional options passed to BaseDetector
        """
        super().__init__(**options)
        self.similarity_threshold = max(0.0, min(1.0, similarity_threshold))
        self.min_lines = max(1, min_lines)
        self.ngram_size = max(2, ngram_size)
        self.ignore_imports = ignore_imports
        self.ignore_docstrings = ignore_docstrings
        self.ignore_comments = ignore_comments
        self.ignore_whitespace = ignore_whitespace
        
        # Determine detection mode based on threshold
        self.exact_mode = self.similarity_threshold >= 1.0

    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph for clone issues."""
        issues = []
        
        # Regular clone detection
        if self.exact_mode:
            issues.extend(self._detect_exact_clones(graph))
        else:
            issues.extend(self._detect_near_clones(graph))
        
        # Enhanced across file semantic clone detection
        if self.similarity_threshold < 1.0:  # Only for near-clone mode
            semantic_issues = self._detect_semantic_clones(graph)
            issues.extend(semantic_issues)
        
        return issues

    def _extract_meaningful_code(self, symbol) -> str:
        """Extract the meaningful code content from a symbol for clone detection.
        
        For functions and methods, this extracts just the body.
        For classes, this extracts the methods and attributes.
        This allows detection of clones with different names but identical logic.
        """
        if not symbol.ast_node:
            return ""
        
        try:
            # For function definitions, extract just the body
            if isinstance(symbol.ast_node, ast.FunctionDef):
                # Create a module with just the function body statements
                body_module = ast.Module(body=symbol.ast_node.body, type_ignores=[])
                return ast.unparse(body_module)
            
            # For class definitions, extract methods and class variables
            elif isinstance(symbol.ast_node, ast.ClassDef):
                # Extract meaningful class content (methods, class vars)
                meaningful_body = []
                for node in symbol.ast_node.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign)):
                        meaningful_body.append(node)
                
                if meaningful_body:
                    body_module = ast.Module(body=meaningful_body, type_ignores=[])
                    return ast.unparse(body_module)
            
            # For other nodes, use the original approach
            return ast.unparse(symbol.ast_node)
            
        except Exception as e:
            # Fallback to original approach
            try:
                return ast.unparse(symbol.ast_node)
            except:
                return ""

    def _detect_exact_clones(self, graph: CodeGraph) -> List[Issue]:
        """Detect exact code clones using normalized source comparison."""
        # Group symbols by their normalized source code
        source_to_symbols = {}
        processed_count = 0
        
        for symbol in graph.symbols.values():
            # Skip symbols without AST node or location
            if not symbol.ast_node or not symbol.location or not symbol.location.file:
                continue
                
            try:
                # Extract meaningful code content (body for functions, etc.)
                source_code = self._extract_meaningful_code(symbol)
                
                # Skip symbols that are too small
                source_lines = len(source_code.splitlines())
                if source_lines < self.min_lines:
                    continue
                
                normalized_source = self._normalize_source(source_code)
                if not normalized_source:
                    continue
                    
                if normalized_source not in source_to_symbols:
                    source_to_symbols[normalized_source] = []
                source_to_symbols[normalized_source].append((symbol, source_code))
                processed_count += 1
                            
            except Exception as e:
                pass
        
        # Find clone groups (symbols with identical normalized source)
        clone_groups = []
        for source, symbol_data in source_to_symbols.items():
            if len(symbol_data) > 1:  # Found clones
                clone_groups.append(symbol_data)
        
        # Create issues for clone groups
        issues = []
        for clone_group in clone_groups:
            issues.extend(self._create_clone_issues(clone_group, 1.0))  # Exact = 100% similarity
        
        return issues

    def _detect_near_clones(self, graph: CodeGraph) -> List[Issue]:
        """Detect near code clones using n-gram similarity analysis."""
        # Generate fingerprints for all symbols
        symbol_fingerprints = {}
        processed_count = 0
        
        for symbol in graph.symbols.values():
            if not symbol.ast_node or not symbol.location or not symbol.location.file:
                continue
                
            try:
                # Extract meaningful code content
                source_code = self._extract_meaningful_code(symbol)
                source_lines = len(source_code.splitlines())
                if source_lines < self.min_lines:
                    continue
                
                fingerprint = self._generate_fingerprint(source_code)
                if fingerprint:
                    symbol_fingerprints[symbol] = (fingerprint, source_code)
                    processed_count += 1
                            
            except Exception as e:
                pass
        
        # Find similar pairs
        similar_pairs = self._find_similar_pairs(symbol_fingerprints)
        
        # Group similar symbols into clone groups
        clone_groups = self._group_similar_symbols(similar_pairs)
        
        # Create issues for clone groups
        issues = []
        for clone_group, similarity in clone_groups:
            symbol_data = [(symbol, symbol_fingerprints[symbol][1]) for symbol in clone_group]
            issues.extend(self._create_clone_issues(symbol_data, similarity))
        
        return issues

    def _normalize_source(self, source: str) -> str:
        """Normalize source code for exact comparison."""
        try:
            # Parse and reformat to normalize structure
            tree = ast.parse(source)
            
            # Apply normalization options
            if self.ignore_docstrings:
                tree = self._remove_docstrings(tree)
            
            # Unparse to get normalized source
            normalized = ast.unparse(tree)
            
            if self.ignore_comments or self.ignore_whitespace:
                # Further normalize by tokenizing and reconstructing
                tokens = []
                try:
                    from io import StringIO
                    token_gen = tokenize.generate_tokens(StringIO(normalized).readline)
                    for token in token_gen:
                        # Skip comments if ignore_comments is True
                        if self.ignore_comments and token.type == tokenize.COMMENT:
                            continue
                        # Skip import-related tokens if ignore_imports is True
                        if (self.ignore_imports and token.type == tokenize.NAME and 
                            token.string in ('import', 'from')):
                            continue
                        # Only include meaningful tokens
                        if token.type not in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL):
                            if token.type == tokenize.INDENT or token.type == tokenize.DEDENT:
                                if not self.ignore_whitespace:
                                    tokens.append(token.string)
                            else:
                                tokens.append(token.string)
                except tokenize.TokenError:
                    # Fall back to original if tokenization fails
                    normalized = normalized
                
                if tokens:
                    if self.ignore_whitespace:
                        # Join without spaces for whitespace-insensitive comparison
                        normalized = ''.join(tokens)
                    else:
                        # Join with spaces to maintain readability
                        normalized = ' '.join(tokens)
            
            return normalized
            
        except Exception as e:
            return source  # Return original source instead of empty string

    def _remove_docstrings(self, tree: ast.AST) -> ast.AST:
        """Remove docstrings from AST."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    # Remove docstring
                    node.body = node.body[1:]
        return tree

    def _generate_fingerprint(self, source: str) -> Set[int]:
        """Generate fingerprint for near clone detection using n-grams."""
        try:
            # For fingerprinting, we always need properly tokenized source
            # Don't use the heavily normalized version that removes all spaces
            
            # Apply minimal normalization for fingerprinting
            try:
                tree = ast.parse(source)
                if self.ignore_docstrings:
                    tree = self._remove_docstrings(tree)
                normalized_source = ast.unparse(tree)
            except:
                normalized_source = source
            
            if not normalized_source:
                return set()
            
            # Use tokenization to get proper tokens
            tokens = []
            try:
                from io import StringIO
                token_gen = tokenize.generate_tokens(StringIO(normalized_source).readline)
                for token in token_gen:
                    if token.type == tokenize.NAME:  # Only use identifier tokens
                        tokens.append(token.string)
                    elif token.type == tokenize.NUMBER:  # Include numbers
                        tokens.append('NUM')  # Normalize numbers for better similarity
                    elif token.type == tokenize.STRING:  # Include strings  
                        tokens.append('STR')  # Normalize strings for better similarity
                    elif token.type == tokenize.OP:  # Include operators
                        tokens.append(token.string)
                    elif token.type == 1:  # KEYWORD (token.KEYWORD doesn't exist, use value)
                        tokens.append(token.string)
            except tokenize.TokenError:
                # Fallback to simple word-based tokenization
                import re
                # Split on whitespace and common separators, but keep meaningful tokens
                tokens = re.findall(r'\w+|[^\w\s]', normalized_source)
            
            if len(tokens) < self.ngram_size:
                return set()
            
            # Generate n-grams
            ngrams = []
            for i in range(len(tokens) - self.ngram_size + 1):
                ngram = tuple(tokens[i:i + self.ngram_size])
                ngrams.append(hash(ngram))
            
            if not ngrams:
                return set()
            
            # Apply winnowing to reduce noise
            return self._winnow(ngrams)
            
        except Exception as e:
            return set()

    def _winnow(self, hashes: List[int], window_size: int = 4) -> Set[int]:
        """Apply winnowing algorithm to reduce fingerprint size."""
        if len(hashes) < window_size:
            return set(hashes)
        
        fingerprint = set()
        for i in range(len(hashes) - window_size + 1):
            window = hashes[i:i + window_size]
            min_hash = min(window)
            fingerprint.add(min_hash)
        
        return fingerprint

    def _find_similar_pairs(self, symbol_fingerprints: Dict) -> List[Tuple]:
        """Find pairs of symbols that meet the similarity threshold."""
        similar_pairs = []
        symbols = list(symbol_fingerprints.keys())
        
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                symbol1, symbol2 = symbols[i], symbols[j]
                fingerprint1 = symbol_fingerprints[symbol1][0]
                fingerprint2 = symbol_fingerprints[symbol2][0]
                
                similarity = self._calculate_similarity(fingerprint1, fingerprint2)
                
                if similarity >= self.similarity_threshold:
                    similar_pairs.append((symbol1, symbol2, similarity))
        
        return similar_pairs

    def _calculate_similarity(self, fp1: Set[int], fp2: Set[int]) -> float:
        """Calculate Jaccard similarity between two fingerprints."""
        if not fp1 and not fp2:
            return 1.0
        if not fp1 or not fp2:
            return 0.0
        
        intersection = len(fp1.intersection(fp2))
        union = len(fp1.union(fp2))
        
        return intersection / union if union > 0 else 0.0

    def _group_similar_symbols(self, similar_pairs: List[Tuple]) -> List[Tuple]:
        """Group similar symbols into clone groups using union-find."""
        if not similar_pairs:
            return []
        
        # Union-find data structure
        parent = {}
        similarities = {}
        
        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y, sim):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
                similarities[(px, py)] = sim
        
        # Build groups
        for symbol1, symbol2, similarity in similar_pairs:
            union(symbol1, symbol2, similarity)
        
        # Collect groups
        groups = defaultdict(list)
        group_similarities = {}
        
        for symbol1, symbol2, similarity in similar_pairs:
            root = find(symbol1)
            groups[root].append(symbol1)
            groups[root].append(symbol2)
            
            # Track maximum similarity for the group
            if root not in group_similarities or similarity > group_similarities[root]:
                group_similarities[root] = similarity
        
        # Remove duplicates and filter small groups
        result = []
        for root, symbols in groups.items():
            unique_symbols = list(set(symbols))
            if len(unique_symbols) > 1:
                similarity = group_similarities.get(root, self.similarity_threshold)
                result.append((unique_symbols, similarity))
        
        return result

    def _create_clone_issues(self, clone_group: List[Tuple], similarity: float) -> List[Issue]:
        """Create issues for a clone group."""
        if len(clone_group) < 2:
            return []
        
        # Use the first symbol as the primary location
        primary_symbol, primary_source = clone_group[0]
        
        # Collect all locations
        locations = []
        for symbol, _ in clone_group:
            if symbol.location and symbol.location.file:
                file_name = Path(symbol.location.file).name
                locations.append(f"{file_name}:{symbol.location.line}")
        
        # Create the issue
        if similarity >= 1.0:
            # Exact clone
            message = f"Found {len(clone_group)} identical code blocks ({len(primary_source.splitlines())} lines each)"
            issue_id = "identical-code"
        else:
            # Near clone  
            message = f"Found {len(clone_group)} similar code blocks ({similarity:.0%} similarity, {len(primary_source.splitlines())} lines each)"
            issue_id = "similar-code"
        
        # Calculate source preview (first few lines)
        source_lines = primary_source.splitlines()
        preview_lines = source_lines[:3]  # First 3 lines
        source_preview = '\n'.join(preview_lines)
        if len(source_lines) > 3:
            source_preview += '\n...'
        
        issue = self.create_issue(
            issue_id=issue_id,
            message=message,
            severity="error" if similarity >= 0.9 else "warn",
            symbol=primary_symbol,
            clone_size=len(primary_source.splitlines()),
            clone_count=len(clone_group),
            similarity=similarity,
            locations=locations,
            source_preview=source_preview
        )
        
        return [issue]

    def _get_structural_signature(self, symbol) -> str:
        """Generate a structural signature for semantic comparison across files."""
        if not symbol.ast_node:
            return ""
        
        try:
            # For functions, create a signature based on structure
            if isinstance(symbol.ast_node, ast.FunctionDef):
                return self._function_structural_signature(symbol.ast_node)
            elif isinstance(symbol.ast_node, ast.ClassDef):
                return self._class_structural_signature(symbol.ast_node)
            else:
                return ""
        except Exception:
            return ""
    
    def _function_structural_signature(self, func_node: ast.FunctionDef) -> str:
        """Create structural signature for a function based on control flow and operations."""
        signature_parts = []
        
        # Parameter count and types
        signature_parts.append(f"params:{len(func_node.args.args)}")
        
        # Control flow structures
        for node in ast.walk(func_node):
            if isinstance(node, ast.If):
                signature_parts.append("if")
            elif isinstance(node, ast.For):
                signature_parts.append("for")
            elif isinstance(node, ast.While):
                signature_parts.append("while")
            elif isinstance(node, ast.Try):
                signature_parts.append("try")
            elif isinstance(node, ast.Return):
                signature_parts.append("return")
            elif isinstance(node, ast.Assign):
                signature_parts.append("assign")
            elif isinstance(node, ast.Call):
                # Track function calls but normalize names
                signature_parts.append("call")
        
        return ":".join(signature_parts)
    
    def _class_structural_signature(self, class_node: ast.ClassDef) -> str:
        """Create structural signature for a class."""
        signature_parts = []
        
        # Count methods and attributes
        methods = sum(1 for node in class_node.body if isinstance(node, ast.FunctionDef))
        attributes = sum(1 for node in class_node.body if isinstance(node, ast.Assign))
        
        signature_parts.append(f"methods:{methods}")
        signature_parts.append(f"attrs:{attributes}")
        
        # Base classes
        signature_parts.append(f"bases:{len(class_node.bases)}")
        
        return ":".join(signature_parts)
    
    def _detect_semantic_clones(self, graph: CodeGraph) -> List[Issue]:
        """Detect semantic clones using structural analysis."""
        # Group symbols by structural signature
        signature_to_symbols = defaultdict(list)
        
        for symbol in graph.symbols.values():
            if not symbol.ast_node or not symbol.location or not symbol.location.file:
                continue
            
            # Only analyze functions and classes
            if not isinstance(symbol.ast_node, (ast.FunctionDef, ast.ClassDef)):
                continue
            
            try:
                # Check min_lines requirement first
                source_code = self._extract_meaningful_code(symbol)
                source_lines = len(source_code.splitlines())
                if source_lines < self.min_lines:
                    continue
                
                structural_sig = self._get_structural_signature(symbol)
                if structural_sig:
                    signature_to_symbols[structural_sig].append(symbol)
            except Exception:
                continue
        
        # Find groups with same structural signature
        issues = []
        for signature, symbols in signature_to_symbols.items():
            if len(symbols) > 1:
                # Filter by across file requirement
                files = set(str(s.location.file) for s in symbols if s.location and s.location.file)
                if len(files) > 1:  # Cross-file clones only
                    # Additional similarity check
                    similar_groups = self._group_by_content_similarity(symbols)
                    for group in similar_groups:
                        if len(group) > 1:
                            symbol_data = [(s, self._extract_meaningful_code(s)) for s in group]
                            issues.extend(self._create_semantic_clone_issues(symbol_data, signature))
        
        return issues
    
    def _group_by_content_similarity(self, symbols: List) -> List[List]:
        """Group symbols by content similarity within structural matches."""
        if len(symbols) <= 1:
            return [symbols]
        
        # Use simple content comparison for now
        groups = []
        processed = set()
        
        for i, symbol1 in enumerate(symbols):
            if symbol1 in processed:
                continue
            
            group = [symbol1]
            processed.add(symbol1)
            content1 = self._extract_meaningful_code(symbol1)
            normalized1 = self._normalize_source(content1)
            
            for j, symbol2 in enumerate(symbols[i+1:], i+1):
                if symbol2 in processed:
                    continue
                
                content2 = self._extract_meaningful_code(symbol2)
                normalized2 = self._normalize_source(content2)
                
                # Check content similarity
                if self._content_similarity(normalized1, normalized2) >= self.similarity_threshold:
                    group.append(symbol2)
                    processed.add(symbol2)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate content similarity between two code blocks."""
        if not content1 or not content2:
            return 0.0
        
        # Simple token-based similarity
        tokens1 = set(content1.split())
        tokens2 = set(content2.split())
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _create_semantic_clone_issues(self, clone_group: List[Tuple], signature: str) -> List[Issue]:
        """Create issues for semantic clone groups."""
        if len(clone_group) < 2:
            return []
        
        primary_symbol, primary_source = clone_group[0]
        
        # Count across file clones
        files = set()
        locations = []
        for symbol, _ in clone_group:
            if symbol.location and symbol.location.file:
                file_path = Path(symbol.location.file)
                files.add(str(file_path))
                locations.append(f"{file_path.name}:{symbol.location.line}")
        
        # Only report if truly across files
        if len(files) < 2:
            return []
        
        # Create the issue
        message = f"Found {len(clone_group)} semantically similar code blocks across {len(files)} files"
        
        source_lines = primary_source.splitlines()
        preview_lines = source_lines[:3]
        source_preview = '\n'.join(preview_lines)
        if len(source_lines) > 3:
            source_preview += '\n...'
        
        issue = self.create_issue(
            issue_id="semantic-clone",
            message=message,
            severity="warn",
            symbol=primary_symbol,
            metadata={
                "clone_count": len(clone_group),
                "files": len(files),
                "locations": locations,
                "structural_signature": signature,
                "source_preview": source_preview
            }
        )
        
        return [issue]
