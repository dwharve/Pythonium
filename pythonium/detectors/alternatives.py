"""
Alternative Implementation Detector

This detector clusters functions by semantic vector & call-graph context, then ranks
clusters by popularity spread to spot real competition vs. deprecated code.
"""

import ast
import logging
import re
from collections import Counter, defaultdict
from math import log, sqrt
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from ..models import CodeGraph, Issue, Symbol
from . import BaseDetector

logger = logging.getLogger(__name__)


class AltImplementationDetector(BaseDetector):
    """Detects alternative implementations of similar functionality."""
    
    id = "alt_implementation"
    name = "Alternative Implementation Detector"
    description = "Finds semantically similar utilities competing for the same purpose"
    
    # Enhanced metadata for MCP server
    category = "Code Quality & Maintainability"
    usage_tips = "Helps consolidate redundant code and improve maintainability"
    related_detectors = ["clone", "semantic_equivalence"]
    typical_severity = "warn"
    detailed_description = ("Identifies multiple implementations of similar functionality that could be "
                           "consolidated to reduce code duplication and maintenance overhead.")
    
    def __init__(self, 
                 semantic_threshold: float = 0.8,      # Increased from 0.4 - better precision
                 pattern_threshold: float = 0.8,       # Increased from 0.7 - better precision
                 min_docstring_length: int = 10,
                 **options):
        super().__init__(**options)
        self.semantic_threshold = semantic_threshold
        self.pattern_threshold = pattern_threshold
        self.min_docstring_length = min_docstring_length
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Find alternative implementations in the codebase."""
        issues = []
        
        # Get all function symbols
        all_functions = [s for s in graph.symbols.values() 
                        if isinstance(s.ast_node, ast.FunctionDef)]
        
        if len(all_functions) < 2:
            return issues
        
        # Phase 1: Pattern-based clustering (from competing patterns)
        pattern_clusters = self._find_pattern_clusters(all_functions)
        
        # Phase 2: Semantic clustering (from duplicate effort)
        semantic_clusters = self._find_semantic_clusters(all_functions)
        
        # Phase 3: Merge and rank clusters
        merged_clusters = self._merge_clusters(pattern_clusters, semantic_clusters)
        
        # Create issues for significant clusters
        for cluster_id, cluster_info in merged_clusters.items():
            if len(cluster_info['functions']) >= 2:
                issues.extend(self._create_alt_implementation_issues(cluster_id, cluster_info))
        
        return issues
    
    def _find_pattern_clusters(self, functions: List[Symbol]) -> Dict[str, List[Symbol]]:
        """Find clusters based on naming patterns and signatures."""
        clusters = defaultdict(list)
        
        # Group by name patterns
        name_patterns = self._extract_name_patterns(functions)
        
        for pattern, funcs in name_patterns.items():
            if len(funcs) >= 2:
                # Further filter by signature similarity
                signature_groups = defaultdict(list)
                
                for func in funcs:
                    sig_key = self._get_signature_key(func.ast_node)
                    signature_groups[sig_key].append(func)
                
                # Add groups with multiple functions
                for sig_key, sig_funcs in signature_groups.items():
                    if len(sig_funcs) >= 2:
                        clusters[f"pattern_{pattern}_{sig_key}"] = sig_funcs
        
        return dict(clusters)
    
    def _find_semantic_clusters(self, functions: List[Symbol]) -> Dict[str, List[Symbol]]:
        """Find clusters based on semantic similarity using TF-IDF."""
        clusters = defaultdict(list)
        
        # Get functions with meaningful docstrings
        documented_functions = [f for f in functions 
                              if self._get_docstring(f.ast_node) and 
                              len(self._get_docstring(f.ast_node)) >= self.min_docstring_length]
        
        if len(documented_functions) < 2:
            return dict(clusters)
        
        # Build TF-IDF vectors
        tfidf_vectors = self._build_tfidf_vectors(documented_functions)
        
        # Find similar pairs and group them
        similar_pairs = self._find_similar_pairs(documented_functions, tfidf_vectors)
        
        # Use union-find to group similar functions
        function_groups = self._group_similar_functions(similar_pairs)
        
        for i, group in enumerate(function_groups):
            if len(group) >= 2:
                clusters[f"semantic_{i}"] = group
        
        return dict(clusters)
    
    def _merge_clusters(self, pattern_clusters: Dict[str, List[Symbol]], 
                       semantic_clusters: Dict[str, List[Symbol]]) -> Dict[str, Dict]:
        """Merge pattern and semantic clusters, ranking by significance."""
        merged = {}
        
        # Add pattern clusters with metadata
        for cluster_id, functions in pattern_clusters.items():
            merged[cluster_id] = {
                'functions': functions,
                'type': 'pattern',
                'confidence': self._calculate_pattern_confidence(functions),
                'modules': list(set(f.location.file.stem for f in functions))
            }
        
        # Add semantic clusters with metadata
        for cluster_id, functions in semantic_clusters.items():
            merged[cluster_id] = {
                'functions': functions,
                'type': 'semantic',
                'confidence': self._calculate_semantic_confidence(functions),
                'modules': list(set(f.location.file.stem for f in functions))
            }
        
        # Check for overlaps and merge if significant
        merged = self._resolve_cluster_overlaps(merged)
        
        return merged
    
    def _calculate_pattern_confidence(self, functions: List[Symbol]) -> float:
        """Calculate confidence score for pattern-based clusters."""
        # Higher confidence for:
        # - More functions in cluster
        # - Functions across different modules
        # - Similar signatures
        
        function_count = len(functions)
        module_count = len(set(f.location.file.stem for f in functions))
        
        # Base score from function count
        count_score = min(function_count / 5.0, 1.0)  # Cap at 5 functions
        
        # Bonus for cross-module patterns
        module_score = min(module_count / 3.0, 1.0)  # Cap at 3 modules
        
        return (count_score + module_score) / 2.0
    
    def _calculate_semantic_confidence(self, functions: List[Symbol]) -> float:
        """Calculate confidence score for semantic clusters."""
        if len(functions) < 2:
            return 0.0
        
        # Calculate average pairwise similarity
        similarities = []
        tfidf_vectors = self._build_tfidf_vectors(functions)
        
        for i in range(len(functions)):
            for j in range(i + 1, len(functions)):
                func1, func2 = functions[i], functions[j]
                similarity = self._cosine_similarity(
                    tfidf_vectors.get(func1.fqname, {}),
                    tfidf_vectors.get(func2.fqname, {})
                )
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _resolve_cluster_overlaps(self, clusters: Dict[str, Dict]) -> Dict[str, Dict]:
        """Resolve overlapping clusters by merging or keeping the highest confidence."""
        # Simple implementation: merge clusters with significant function overlap
        resolved = {}
        processed = set()
        
        cluster_items = list(clusters.items())
        
        for i, (cluster_id1, cluster1) in enumerate(cluster_items):
            if cluster_id1 in processed:
                continue
                
            merged_cluster = cluster1.copy()
            merged_with = [cluster_id1]
            
            # Check for overlaps with other clusters
            for j, (cluster_id2, cluster2) in enumerate(cluster_items[i+1:], i+1):
                if cluster_id2 in processed:
                    continue
                
                # Check overlap
                funcs1 = set(f.fqname for f in cluster1['functions'])
                funcs2 = set(f.fqname for f in cluster2['functions'])
                overlap = len(funcs1 & funcs2)
                
                # Merge if significant overlap (>50% of smaller cluster)
                if overlap > 0 and overlap / min(len(funcs1), len(funcs2)) > 0.5:
                    # Merge clusters
                    all_functions = cluster1['functions'] + cluster2['functions']
                    unique_functions = []
                    seen_fqnames = set()
                    
                    for func in all_functions:
                        if func.fqname not in seen_fqnames:
                            unique_functions.append(func)
                            seen_fqnames.add(func.fqname)
                    
                    merged_cluster['functions'] = unique_functions
                    merged_cluster['type'] = 'merged'
                    merged_cluster['confidence'] = max(cluster1['confidence'], cluster2['confidence'])
                    merged_cluster['modules'] = list(set(merged_cluster['modules'] + cluster2['modules']))
                    merged_with.append(cluster_id2)
                    processed.add(cluster_id2)
            
            # Add merged cluster
            new_id = f"merged_{'_'.join(merged_with)}" if len(merged_with) > 1 else cluster_id1
            resolved[new_id] = merged_cluster
            processed.add(cluster_id1)
        
        return resolved
    
    def _extract_name_patterns(self, functions: List[Symbol]) -> Dict[str, List[Symbol]]:
        """Extract naming patterns from function names."""
        patterns = defaultdict(list)
        
        for func in functions:
            func_name = func.ast_node.name.lower()
            
            # Common utility patterns
            if any(pattern in func_name for pattern in ['helper', 'util', 'utility']):
                domain = self._extract_domain_from_name(func_name)
                patterns[f"utility_{domain}"].append(func)
            
            elif any(pattern in func_name for pattern in ['manager', 'handler']):
                domain = self._extract_domain_from_name(func_name)
                patterns[f"manager_{domain}"].append(func)
            
            elif any(pattern in func_name for pattern in ['converter', 'transform']):
                domain = self._extract_domain_from_name(func_name)
                patterns[f"converter_{domain}"].append(func)
            
            elif func_name.startswith(('parse_', 'process_', 'handle_')):
                action = func_name.split('_')[0]
                patterns[f"action_{action}"].append(func)
        
        return patterns
    
    def _extract_domain_from_name(self, name: str) -> str:
        """Extract the domain/subject from a function name."""
        domains = ['json', 'xml', 'csv', 'file', 'data', 'config', 'db', 'api', 
                  'http', 'url', 'string', 'text', 'number', 'date', 'time']
        
        for domain in domains:
            if domain in name:
                return domain
        
        return "generic"
    
    def _get_signature_key(self, func_node: ast.FunctionDef) -> str:
        """Get a key representing the function signature."""
        param_count = len(func_node.args.args)
        returns = ""
        if func_node.returns:
            returns = ast.unparse(func_node.returns) if hasattr(ast, 'unparse') else str(func_node.returns)
        return f"({param_count}_params)->{returns}"
    
    def _get_docstring(self, func_node: ast.FunctionDef) -> str:
        """Extract and clean docstring from function."""
        docstring = ast.get_docstring(func_node)
        if not docstring:
            return ""
        
        # Clean the docstring
        docstring = re.sub(r'\s+', ' ', docstring)
        docstring = re.sub(r'[^\w\s]', '', docstring)
        docstring = docstring.lower().strip()
        
        return docstring
    
    def _build_tfidf_vectors(self, functions: List[Symbol]) -> Dict[str, Dict[str, float]]:
        """Build TF-IDF vectors for function docstrings."""
        docstrings = {}
        all_words = set()
        
        for func in functions:
            docstring = self._get_docstring(func.ast_node)
            words = self._tokenize(docstring)
            docstrings[func.fqname] = words
            all_words.update(words)
        
        # Calculate TF-IDF
        vocabulary = list(all_words)
        doc_count = len(docstrings)
        
        # Document frequency for each word
        df = {}
        for word in vocabulary:
            df[word] = sum(1 for words in docstrings.values() if word in words)
        
        # Build TF-IDF vectors
        tfidf_vectors = {}
        
        for fqname, words in docstrings.items():
            word_counts = Counter(words)
            total_words = len(words)
            
            vector = {}
            for word in vocabulary:
                tf = word_counts.get(word, 0) / total_words if total_words > 0 else 0
                idf = log(doc_count / df[word]) if df[word] > 0 else 0
                tfidf = tf * idf
                if tfidf > 0:
                    vector[word] = tfidf
            
            tfidf_vectors[fqname] = vector
        
        return tfidf_vectors
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into meaningful words."""
        words = [word for word in text.split() if len(word) >= 3]
        
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that',
            'with', 'have', 'from', 'they', 'will', 'been', 'each', 'like', 'were',
            'said', 'than', 'them', 'very', 'what', 'your'
        }
        
        return [word for word in words if word not in stop_words]
    
    def _find_similar_pairs(self, functions: List[Symbol], 
                           tfidf_vectors: Dict[str, Dict[str, float]]) -> List[Tuple[Symbol, Symbol, float]]:
        """Find pairs of functions with similar docstrings."""
        similar_pairs = []
        
        for i in range(len(functions)):
            for j in range(i + 1, len(functions)):
                func1, func2 = functions[i], functions[j]
                
                similarity = self._cosine_similarity(
                    tfidf_vectors.get(func1.fqname, {}),
                    tfidf_vectors.get(func2.fqname, {})
                )
                
                if similarity >= self.semantic_threshold:
                    similar_pairs.append((func1, func2, similarity))
        
        return similar_pairs
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two TF-IDF vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        common_words = set(vec1.keys()) & set(vec2.keys())
        if not common_words:
            return 0.0
        
        dot_product = sum(vec1[word] * vec2[word] for word in common_words)
        mag1 = sqrt(sum(val ** 2 for val in vec1.values()))
        mag2 = sqrt(sum(val ** 2 for val in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def _group_similar_functions(self, similar_pairs: List[Tuple[Symbol, Symbol, float]]) -> List[List[Symbol]]:
        """Group similar functions using union-find algorithm."""
        # Create union-find structure
        parent = {}
        rank = {}
        
        def find(x):
            if x not in parent:
                parent[x] = x
                rank[x] = 0
                return x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1
        
        # Union similar functions
        for func1, func2, similarity in similar_pairs:
            union(func1.fqname, func2.fqname)
        
        # Group by parent
        groups = defaultdict(list)
        all_functions = set()
        for func1, func2, _ in similar_pairs:
            all_functions.add(func1)
            all_functions.add(func2)
        
        for func in all_functions:
            root = find(func.fqname)
            groups[root].append(func)
        
        return list(groups.values())
    
    def _create_alt_implementation_issues(self, cluster_id: str, cluster_info: Dict) -> List[Issue]:
        """Create issues for alternative implementation clusters."""
        issues = []
        functions = cluster_info['functions']
        cluster_type = cluster_info['type']
        confidence = cluster_info['confidence']
        modules = cluster_info['modules']
        
        if len(functions) < 2:
            return issues
        
        # Use the first function as the primary symbol
        primary_func = functions[0]
        
        # Create descriptive message based on cluster type
        if cluster_type == 'pattern':
            message = (f"Found {len(functions)} competing implementations with similar patterns: "
                      f"{', '.join(f.ast_node.name for f in functions)}. "
                      f"Consider consolidating into a single implementation.")
        elif cluster_type == 'semantic':
            message = (f"Found {len(functions)} functions with similar semantic intent: "
                      f"{', '.join(f.ast_node.name for f in functions)}. "
                      f"Consider consolidating duplicate effort (confidence: {confidence:.2f}).")
        else:  # merged
            message = (f"Found {len(functions)} alternative implementations: "
                      f"{', '.join(f.ast_node.name for f in functions)}. "
                      f"Multiple approaches detected for the same functionality.")
        
        # Determine severity based on confidence and module spread
        if confidence >= 0.8 and len(modules) > 1:
            severity = "error"
        elif confidence >= 0.6:
            severity = "warn"
        else:
            severity = "info"
        
        issue = self.create_issue(
            issue_id="ALT_IMPLEMENTATION",
            severity=severity,
            symbol=primary_func,
            message=message,
            cluster_type=cluster_type,
            confidence=confidence,
            alternative_functions=[
                {
                    "name": func.ast_node.name,
                    "file": str(func.location.file),
                    "line": func.location.line,
                    "fqname": func.fqname
                }
                for func in functions
            ],
            module_count=len(modules),
            function_count=len(functions),
            modules=modules,
            recommendation=self._generate_recommendation(cluster_info)
        )        
        issues.append(issue)
        return issues
        
    def _generate_recommendation(self, cluster_info: Dict) -> str:
        """Generate a recommendation for resolving alternative implementations."""
        functions = cluster_info['functions']
        modules = cluster_info['modules']
        cluster_type = cluster_info['type']
        
        if len(modules) == 1:
            module = next(iter(modules))  # Get the single module from the set
            return f"Consider consolidating these functions within {module} module."
        elif any("util" in str(module).lower() for module in modules):
            util_module = next(module for module in modules if "util" in str(module).lower())
            return f"Consider moving all implementations to {util_module} as the utility module."
        elif cluster_type == 'semantic':
            return "Consider creating a shared utility module for this functionality and deprecating alternatives."
        else:
            return "Consider standardizing on one implementation and deprecating or removing the others."
