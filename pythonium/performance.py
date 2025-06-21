"""
Performance optimizations for Pythonium.

This module implements caching and parallel processing features:
- SQLite caching for call-graph edges keyed by file SHA + Python version
- Parallel detector execution via ProcessPoolExecutor
- File-level parsing optimizations
- AST caching for improved performance
"""

import ast
import hashlib
import os
import pickle
import sqlite3
import sys
import time
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

from .models import CodeGraph, Issue, Symbol
from .detectors import Detector

logger = logging.getLogger(__name__)


class ASTCache:
    """Cache for parsed AST objects."""
    
    def __init__(self, max_cache_size: int = 1000):
        """
        Initialize the AST cache.
        
        Args:
            max_cache_size: Maximum number of AST objects to cache
        """
        self._cache: Dict[str, Tuple[ast.AST, str, float]] = {}  # file_path -> (ast, file_hash, timestamp)
        self._max_cache_size = max_cache_size
        self._lock = threading.RLock()
    
    def get_ast(self, file_path: str) -> Optional[ast.AST]:
        """
        Get cached AST for a file, checking if file has changed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached AST or None if cache miss/invalid
        """
        with self._lock:
            if file_path not in self._cache:
                return None
                
            cached_ast, cached_hash, cached_time = self._cache[file_path]
            
            try:
                # Check if file has been modified
                current_stat = os.stat(file_path)
                if current_stat.st_mtime > cached_time:
                    # File modified, remove from cache
                    del self._cache[file_path]
                    return None
                    
                # Verify content hash for extra safety
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    current_hash = hashlib.sha256(content.encode()).hexdigest()
                    
                if current_hash != cached_hash:
                    del self._cache[file_path]
                    return None
                    
                # Return a copy to prevent mutations to cached AST
                import copy
                return copy.deepcopy(cached_ast)
                
            except (OSError, IOError):
                # File doesn't exist or can't be read
                if file_path in self._cache:
                    del self._cache[file_path]
                return None
    
    def set_ast(self, file_path: str, ast_node: ast.AST, content: str) -> None:
        """
        Cache an AST for a file.
        
        Args:
            file_path: Path to the file
            ast_node: Parsed AST object
            content: File content used to compute hash
        """
        with self._lock:
            # Implement simple LRU eviction if cache is full
            if len(self._cache) >= self._max_cache_size:
                # Remove oldest entry based on timestamp
                oldest_file = min(self._cache.keys(), 
                                key=lambda f: self._cache[f][2])
                del self._cache[oldest_file]
                logger.debug(f"Evicted {oldest_file} from AST cache (LRU)")
            
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            timestamp = time.time()
            self._cache[file_path] = (ast_node, file_hash, timestamp)
            logger.debug(f"Cached AST for {file_path}")
    
    def invalidate_file(self, file_path: str) -> None:
        """
        Remove a file from the AST cache.
        
        Args:
            file_path: Path to the file to invalidate
        """
        with self._lock:
            if file_path in self._cache:
                del self._cache[file_path]
                logger.debug(f"Invalidated AST cache for {file_path}")
    
    def clear(self) -> None:
        """Clear the entire AST cache."""
        with self._lock:
            self._cache.clear()
            logger.debug("Cleared AST cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self._max_cache_size,
                'files': list(self._cache.keys())
            }


@dataclass
class CacheEntry:
    """Cache entry for file analysis results."""
    file_sha: str
    python_version: str
    symbols: List[Symbol]
    last_modified: float
    

class AnalysisCache:
    """
    SQLite-based cache for analysis results.
    
    Caches symbols and call-graph edges keyed by file SHA and Python version
    to avoid re-parsing unchanged files.
    """
    
    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize the cache.
        
        Args:
            cache_path: Path to SQLite cache file. If None, uses default location.
        """
        if cache_path is None:
            cache_path = Path.home() / ".pythonium" / "cache.db"
        
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_hits = 0
        self._cache_misses = 0
        self._init_db()
    
    def _init_db(self):
        """Initialize the cache database."""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    file_path TEXT PRIMARY KEY,
                    file_sha TEXT NOT NULL,
                    python_version TEXT NOT NULL,
                    symbols BLOB NOT NULL,
                    last_modified REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_graph_cache (
                    edge_id TEXT PRIMARY KEY,
                    caller TEXT NOT NULL,
                    callee TEXT NOT NULL,
                    file_sha TEXT NOT NULL,
                    python_version TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            
            # File dependency tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_dependencies (
                    dependent_file TEXT NOT NULL,
                    dependency_file TEXT NOT NULL,
                    dependency_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (dependent_file, dependency_file, dependency_type)
                )
            """)
            
            # Detector issue caching
            conn.execute("""
                CREATE TABLE IF NOT EXISTS detector_issues (
                    issue_id TEXT PRIMARY KEY,
                    detector_id TEXT NOT NULL,
                    files_involved TEXT NOT NULL,
                    files_hash TEXT NOT NULL,
                    issue_data BLOB NOT NULL,
                    python_version TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_sha ON file_cache(file_sha)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_python_version ON file_cache(python_version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_call_graph_file ON call_graph_cache(file_sha)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_deps_dependent ON file_dependencies(dependent_file)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_deps_dependency ON file_dependencies(dependency_file)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detector_issues_detector ON detector_issues(detector_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detector_issues_hash ON detector_issues(files_hash)")
            
            conn.commit()
    
    def get_file_sha(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ""
    
    def get_cached_symbols(self, file_path: Path) -> Optional[List[Symbol]]:
        """
        Get cached symbols for a file if available and valid.
        
        DEPRECATED: Symbol caching is no longer needed since symbol extraction
        is now fast via the AST cache. This method returns None to force
        symbol re-extraction from the cached AST.
        
        Args:
            file_path: Path to the file
            
        Returns:
            None (always returns None to force re-extraction)
        """
        # Symbol extraction is now fast via AST cache, no need for symbol caching
        logger.debug("Symbol caching deprecated, returning None to force AST-based extraction")
        return None
    
    def cache_symbols(self, file_path: Path, symbols: List[Symbol]):
        """
        Cache symbols for a file.
        
        DEPRECATED: Symbol caching is no longer needed since symbol extraction
        is now fast via the AST cache. This method does nothing.
        
        Args:
            file_path: Path to the file
            symbols: Symbols to cache (ignored)
        """
        # Symbol extraction is now fast via AST cache, no need for symbol caching
        logger.debug("Symbol caching deprecated, skipping cache for %s", file_path)
        return
    
    def cache_call_edges(self, file_path: Path, edges: List[Tuple[str, str]]):
        """
        Cache call graph edges for a file.
        
        Args:
            file_path: Path to the file
            edges: List of (caller, callee) tuples
        """
        try:
            file_sha = self.get_file_sha(file_path)
            if not file_sha:
                return
            
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            with sqlite3.connect(self.cache_path) as conn:
                # First, remove old edges for this file
                conn.execute("""
                    DELETE FROM call_graph_cache 
                    WHERE file_sha = ? AND python_version = ?
                """, (file_sha, python_version))
                
                # Insert new edges
                for caller, callee in edges:
                    edge_id = f"{file_sha}:{caller}:{callee}"
                    conn.execute("""
                        INSERT OR REPLACE INTO call_graph_cache
                        (edge_id, caller, callee, file_sha, python_version, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (edge_id, caller, callee, file_sha, python_version, time.time()))
                
                conn.commit()
                logger.debug("Cached %d call edges for %s", len(edges), file_path)
                
        except Exception as e:
            logger.warning("Failed to cache call edges for %s: %s", file_path, e)
    
    def invalidate_dependents(self, file_path: Path) -> List[str]:
        """
        Invalidate cache entries for files that depend on the given file.
        
        Args:
            file_path: Path of the file that changed
            
        Returns:
            List of invalidated file paths
        """
        file_path_str = str(file_path)
        invalidated_files = []
        
        try:
            with sqlite3.connect(self.cache_path) as conn:
                # Find all files that depend on the changed file
                cursor = conn.execute("""
                    SELECT DISTINCT dependent_file FROM file_dependencies 
                    WHERE dependency_file = ?
                """, (file_path_str,))
                
                dependent_files = [row[0] for row in cursor.fetchall()]
                
                if dependent_files:
                    # Invalidate cache entries for dependent files
                    placeholders = ','.join(['?'] * len(dependent_files))
                    conn.execute(f"""
                        DELETE FROM file_cache 
                        WHERE file_path IN ({placeholders})
                    """, dependent_files)
                    
                    # Invalidate call graph cache for dependent files
                    conn.execute(f"""
                        DELETE FROM call_graph_cache 
                        WHERE caller IN ({placeholders}) OR callee IN ({placeholders})
                    """, dependent_files + dependent_files)
                    
                    # Also remove dependency entries for changed file
                    conn.execute("""
                        DELETE FROM file_dependencies 
                        WHERE dependency_file = ?
                    """, (file_path_str,))
                    
                    invalidated_files = dependent_files
                    
                # Invalidate the changed file itself
                conn.execute("DELETE FROM file_cache WHERE file_path = ?", (file_path_str,))
                conn.execute("DELETE FROM call_graph_cache WHERE caller = ? OR callee = ?", 
                           (file_path_str, file_path_str))
                conn.execute("DELETE FROM file_dependencies WHERE dependent_file = ?", (file_path_str,))
                
                # Invalidate detector issues that involve this file
                cursor = conn.execute("""
                    SELECT issue_id FROM detector_issues 
                    WHERE files_involved LIKE ?
                """, (f'%{file_path_str}%',))
                
                issue_ids = []
                for row in cursor.fetchall():
                    issue_id = row[0]
                    # Verify file is actually involved (not just a substring match)
                    cursor2 = conn.execute("SELECT files_involved FROM detector_issues WHERE issue_id = ?", 
                                         (issue_id,))
                    files_result = cursor2.fetchone()
                    if files_result:
                        files_involved = files_result[0]
                        involved_files = files_involved.split('|')
                        if file_path_str in involved_files:
                            issue_ids.append(issue_id)
                
                if issue_ids:
                    placeholders = ','.join(['?'] * len(issue_ids))
                    conn.execute(f"DELETE FROM detector_issues WHERE issue_id IN ({placeholders})", issue_ids)
                
                conn.commit()
                
        except Exception as e:
            logger.warning("Failed to invalidate dependents for %s: %s", file_path, e)
        
        # Also invalidate AST cache for the changed file and its dependents
        ast_cache = get_ast_cache()
        if ast_cache:
            ast_cache.invalidate_file(file_path_str)
            for dep_file in invalidated_files:
                ast_cache.invalidate_file(dep_file)
            
        return invalidated_files

    def record_file_dependencies(self, file_path: Path, dependencies: List[Path], 
                                dependency_type: str = 'import') -> None:
        """
        Record dependencies between files for cache invalidation.
        
        Args:
            file_path: The file that has dependencies
            dependencies: List of files that this file depends on
            dependency_type: Type of dependency ('import', 'inheritance', etc.)
        """
        file_path_str = str(file_path)
        current_time = time.time()
        
        try:
            with sqlite3.connect(self.cache_path) as conn:
                # Remove existing dependencies of this type for this file
                conn.execute("""
                    DELETE FROM file_dependencies 
                    WHERE dependent_file = ? AND dependency_type = ?
                """, (file_path_str, dependency_type))
                
                # Insert new dependencies
                for dep_path in dependencies:
                    dep_path_str = str(dep_path)
                    conn.execute("""
                        INSERT OR REPLACE INTO file_dependencies 
                        (dependent_file, dependency_file, dependency_type, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (file_path_str, dep_path_str, dependency_type, current_time))
                
                conn.commit()
                
        except Exception as e:
            logger.warning("Failed to record dependencies for %s: %s", file_path, e)

    def get_detector_issues(self, detector_id: str, files_involved: List[Path]) -> Optional[List[Issue]]:
        """
        Get cached issues for a detector across the specified files.
        Only returns cached results for expensive detectors.
        
        Args:
            detector_id: ID of the detector
            files_involved: List of files involved in the analysis
            
        Returns:
            Cached issues or None if not found/invalid or detector not cacheable
        """
        # Only cache expensive detectors
        if not self._should_cache_detector(detector_id):
            return None
            
        try:
            files_hash = self._calculate_files_hash(files_involved)
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            with sqlite3.connect(self.cache_path) as conn:
                cursor = conn.execute("""
                    SELECT issue_data FROM detector_issues
                    WHERE detector_id = ? AND files_hash = ? AND python_version = ?
                """, (detector_id, files_hash, python_version))
                
                row = cursor.fetchone()
                if row:
                    result = pickle.loads(row[0])
                    # Ensure result is always a list
                    if not isinstance(result, list):
                        if hasattr(result, '__iter__') and not isinstance(result, str):
                            result = list(result)
                        else:
                            result = [result] if result is not None else []
                    return result
                    
        except Exception as e:
            logger.warning("Failed to get cached issues for %s: %s", detector_id, e)
            
        return None

    def set_detector_issues(self, detector_id: str, files_involved: List[Path], 
                            issues: List[Issue]) -> None:
        """
        Cache issues for a detector across the specified files.
        Only caches expensive detectors to optimize cache efficiency.
        
        Args:
            detector_id: ID of the detector
            files_involved: List of files involved in the analysis
            issues: Issues to cache
        """
        # Only cache expensive detectors
        if not self._should_cache_detector(detector_id):
            logger.debug(f"Skipping cache for fast detector: {detector_id}")
            return
            
        try:
            files_hash = self._calculate_files_hash(files_involved)
            files_involved_str = '|'.join(str(f) for f in files_involved)
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            current_time = time.time()
            
            # Store the entire list of issues as a single cache entry
            cache_id = f"{detector_id}_{files_hash}"
            
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO detector_issues
                    (issue_id, detector_id, files_involved, files_hash,
                     issue_data, python_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cache_id, detector_id, files_involved_str, files_hash,
                     pickle.dumps(issues), python_version, current_time))
                
                conn.commit()
                logger.debug(f"Cached {len(issues)} issues for {detector_id}")
                    
        except Exception as e:
            logger.warning("Failed to cache issues for %s: %s", detector_id, e)

    def clear_detector_issues(self, detector_id: Optional[str] = None) -> None:
        """
        Clear detector issues cache.
        
        Args:
            detector_id: If provided, clear only for this detector. If None, clear all.
        """
        try:
            with sqlite3.connect(self.cache_path) as conn:
                if detector_id:
                    conn.execute("DELETE FROM detector_issues WHERE detector_id = ?", (detector_id,))
                    logger.debug("Cleared detector issues cache for: %s", detector_id)
                else:
                    conn.execute("DELETE FROM detector_issues")
                    logger.debug("Cleared all detector issues cache")
                conn.commit()
        except Exception as e:            logger.warning("Failed to clear detector issues cache: %s", e)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash for a single file."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ""

    def _calculate_files_hash(self, files: List[Path]) -> str:
        """Calculate a hash representing the current state of multiple files."""
        file_hashes = []
        for file_path in sorted(files):  # Sort for consistent ordering
            file_hash = self.get_file_sha(file_path)
            if file_hash:
                file_hashes.append(f"{file_path}:{file_hash}")
        
        combined = '|'.join(file_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()

    def cleanup_old_entries(self, max_age_days: int = 30) -> None:
        """
        Clean up old cache entries to prevent unbounded growth.
        
        Args:
            max_age_days: Maximum age in days for cache entries
        """
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        try:
            with sqlite3.connect(self.cache_path) as conn:
                # Clean up old file cache entries
                conn.execute("DELETE FROM file_cache WHERE created_at < ?", (cutoff_time,))
                
                # Clean up old call graph cache entries
                conn.execute("DELETE FROM call_graph_cache WHERE created_at < ?", (cutoff_time,))
                
                # Clean up old dependency entries
                conn.execute("DELETE FROM file_dependencies WHERE created_at < ?", (cutoff_time,))
                
                # Clean up old detector issues
                conn.execute("DELETE FROM detector_issues WHERE created_at < ?", (cutoff_time,))
                
                conn.commit()
                
        except Exception as e:
            logger.warning("Failed to cleanup old cache entries: %s", e)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'file_cache_entries': 0,
            'call_graph_entries': 0,
            'dependency_entries': 0,
            'detector_issues': 0,
            'cache_hits': getattr(self, '_cache_hits', 0),
            'cache_misses': getattr(self, '_cache_misses', 0),
        }
        
        try:
            with sqlite3.connect(self.cache_path) as conn:
                # File cache entries
                cursor = conn.execute("SELECT COUNT(*) FROM file_cache")
                stats['file_cache_entries'] = cursor.fetchone()[0]
                
                # Call graph entries
                cursor = conn.execute("SELECT COUNT(*) FROM call_graph_cache")
                stats['call_graph_entries'] = cursor.fetchone()[0]
                
                # Dependency entries
                cursor = conn.execute("SELECT COUNT(*) FROM file_dependencies")
                stats['dependency_entries'] = cursor.fetchone()[0]
                
                # Detector issues entries
                cursor = conn.execute("SELECT COUNT(*) FROM detector_issues")
                stats['detector_issues'] = cursor.fetchone()[0]
                
        except Exception as e:
            logger.warning("Failed to get cache stats: %s", e)
            
        return stats
    
    def _should_cache_detector(self, detector_id: str) -> bool:
        """
        Determine if a detector's results should be cached based on computational cost.
        
        Fast detectors that rely on AST parsing are not cached since the AST
        cache makes them very fast. Only expensive detectors that do complex
        analysis are cached.
        
        Args:
            detector_id: ID of the detector
            
        Returns:
            True if the detector results should be cached
        """
        # Expensive detectors that should be cached
        expensive_detectors = {
            'complexity_hotspot',  # Complex metrics calculation
            'clone',               # Code similarity analysis
            'block_clone',         # Block-level similarity analysis
            'semantic_equivalence', # Semantic analysis
            'security_smell',      # Security pattern analysis
            'circular_deps',       # Dependency cycle detection
        }
        
        return detector_id in expensive_detectors


class ParallelAnalyzer:
    """
    Parallel detector execution using ProcessPoolExecutor.
    
    Executes detectors in parallel while falling back to single-process
    on Windows or when parallel execution fails.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the parallel analyzer.
        
        Args:
            max_workers: Maximum number of worker processes. If None, uses default.
        """
        self.max_workers = max_workers
        self.use_parallel = sys.platform != "win32"  # Disable on Windows by default
    
    def analyze_parallel(
        self, 
        detectors: List[Detector], 
        graph: CodeGraph,
        timeout: Optional[float] = None
    ) -> List[Issue]:
        """
        Run detectors in parallel.
        
        Args:
            detectors: List of detectors to run
            graph: Code graph to analyze
            timeout: Optional timeout for each detector
            
        Returns:
            Combined list of issues from all detectors
        """
        if not self.use_parallel or len(detectors) <= 1:
            return self._analyze_sequential(detectors, graph)
        
        try:
            return self._analyze_with_executor(detectors, graph, timeout)
        except Exception as e:
            logger.warning("Parallel execution failed, falling back to sequential: %s", e)
            return self._analyze_sequential(detectors, graph)
    
    def _analyze_sequential(self, detectors: List[Detector], graph: CodeGraph) -> List[Issue]:
        """Run detectors sequentially (fallback mode)."""
        all_issues = []
        
        for detector in detectors:
            try:
                start_time = time.time()
                issues = detector.analyze(graph)
                elapsed = time.time() - start_time
                
                # Ensure issues is a list
                if not isinstance(issues, list):
                    if hasattr(issues, '__iter__') and not isinstance(issues, str):
                        issues = list(issues)
                    else:
                        # Single issue, wrap in list
                        issues = [issues] if issues is not None else []
                
                logger.info("Found %d issues with detector %s (%.2fs)", 
                           len(issues), detector.name, elapsed)
                all_issues.extend(issues)
                
            except Exception as e:
                logger.error("Detector %s failed: %s", detector.name, e)
        
        return all_issues
    
    def _analyze_with_executor(
        self, 
        detectors: List[Detector], 
        graph: CodeGraph,
        timeout: Optional[float]
    ) -> List[Issue]:
        """Run detectors using ProcessPoolExecutor."""
        all_issues = []
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all detector tasks
            future_to_detector = {}
            for detector in detectors:
                future = executor.submit(self._run_detector, detector, graph)
                future_to_detector[future] = detector
            
            # Collect results as they complete
            for future in as_completed(future_to_detector, timeout=timeout):
                detector = future_to_detector[future]
                
                try:
                    issues, elapsed = future.result()
                    logger.info("Found %d issues with detector %s (%.2fs)", 
                               len(issues), detector.name, elapsed)
                    all_issues.extend(issues)
                    
                except Exception as e:
                    logger.error("Detector %s failed: %s", detector.name, e)
        
        return all_issues
    
    @staticmethod
    def _run_detector(detector: Detector, graph: CodeGraph) -> Tuple[List[Issue], float]:
        """Run a single detector and return issues with timing."""
        start_time = time.time()
        issues = detector.analyze(graph)
        elapsed = time.time() - start_time
        
        # Ensure issues is a list
        if not isinstance(issues, list):
            if hasattr(issues, '__iter__') and not isinstance(issues, str):
                issues = list(issues)
            else:
                # Single issue, wrap in list
                issues = [issues] if issues is not None else []
        
        return issues, elapsed


# Global cache instance
_cache_instance: Optional[AnalysisCache] = None

# Global AST cache instance
_ast_cache_instance: Optional[ASTCache] = None


def get_cache() -> AnalysisCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AnalysisCache()
    return _cache_instance


def get_ast_cache() -> Optional[ASTCache]:
    """Get the global AST cache instance."""
    global _ast_cache_instance
    if _ast_cache_instance is None:
        _ast_cache_instance = ASTCache()
    return _ast_cache_instance


def set_cache_path(cache_path: Path):
    """Set a custom cache path."""
    global _cache_instance
    _cache_instance = AnalysisCache(cache_path)
