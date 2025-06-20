"""
Performance optimizations for Pythonium.

This module implements caching and parallel processing features:
- SQLite caching for call-graph edges keyed by file SHA + Python version
- Parallel detector execution via ProcessPoolExecutor
- File-level parsing optimizations
"""

import hashlib
import pickle
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

from .models import CodeGraph, Issue, Symbol
from .detectors import Detector

logger = logging.getLogger(__name__)


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
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_sha ON file_cache(file_sha)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_python_version ON file_cache(python_version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_call_graph_file ON call_graph_cache(file_sha)")
            
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
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached symbols or None if cache miss/invalid
        """
        try:
            file_sha = self.get_file_sha(file_path)
            if not file_sha:
                return None
            
            file_stat = file_path.stat()
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            with sqlite3.connect(self.cache_path) as conn:
                cursor = conn.execute("""
                    SELECT symbols, last_modified 
                    FROM file_cache 
                    WHERE file_path = ? AND file_sha = ? AND python_version = ?
                """, (str(file_path), file_sha, python_version))
                
                row = cursor.fetchone()
                if row:
                    cached_symbols_blob, cached_modified = row
                    
                    # Check if file hasn't been modified since cache
                    if abs(cached_modified - file_stat.st_mtime) < 1.0:  # 1 second tolerance
                        try:
                            symbols = pickle.loads(cached_symbols_blob)
                            logger.debug("Cache hit for %s", file_path)
                            return symbols
                        except (pickle.PickleError, AttributeError) as e:
                            logger.warning("Failed to deserialize cached symbols for %s: %s", file_path, e)
                
            return None
            
        except Exception as e:
            logger.warning("Cache lookup failed for %s: %s", file_path, e)
            return None
    
    def cache_symbols(self, file_path: Path, symbols: List[Symbol]):
        """
        Cache symbols for a file.
        
        Args:
            file_path: Path to the file
            symbols: Symbols to cache
        """
        try:
            file_sha = self.get_file_sha(file_path)
            if not file_sha:
                return
            
            file_stat = file_path.stat()
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            # Serialize symbols
            symbols_blob = pickle.dumps(symbols)
            
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO file_cache 
                    (file_path, file_sha, python_version, symbols, last_modified, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (str(file_path), file_sha, python_version, symbols_blob, 
                      file_stat.st_mtime, time.time()))
                
                conn.commit()
                logger.debug("Cached symbols for %s", file_path)
                
        except Exception as e:
            logger.warning("Failed to cache symbols for %s: %s", file_path, e)
    
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
    
    def cleanup_old_entries(self, max_age_days: int = 30):
        """
        Clean up cache entries older than specified age.
        
        Args:
            max_age_days: Maximum age in days
        """
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 3600)
            
            with sqlite3.connect(self.cache_path) as conn:
                file_deleted = conn.execute("""
                    DELETE FROM file_cache WHERE created_at < ?
                """, (cutoff_time,)).rowcount
                
                call_deleted = conn.execute("""
                    DELETE FROM call_graph_cache WHERE created_at < ?
                """, (cutoff_time,)).rowcount
                
                conn.commit()
                
                if file_deleted > 0 or call_deleted > 0:
                    logger.info("Cleaned up %d file cache entries and %d call graph entries", 
                               file_deleted, call_deleted)
                
        except Exception as e:
            logger.warning("Cache cleanup failed: %s", e)


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
        return issues, elapsed


# Global cache instance
_cache_instance: Optional[AnalysisCache] = None


def get_cache() -> AnalysisCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AnalysisCache()
    return _cache_instance


def set_cache_path(cache_path: Path):
    """Set a custom cache path."""
    global _cache_instance
    _cache_instance = AnalysisCache(cache_path)
