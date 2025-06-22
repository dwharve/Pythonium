"""
Core analysis engine for running code health checks.

This module provides the main Analyzer class that coordinates the entire pythonium
analysis process. It loads code into a graph representation, manages detector
registration and execution, and aggregates issues found by all detectors.

The analyzer supports:
- Built-in and external detectors via entry points
- Performance optimizations (caching, parallel execution)
- Incremental analysis via Git integration
- Extensibility hooks for custom functionality
- Shared settings for configuration

Example:
    Basic usage:
    
    ```python
    from pythonium import Analyzer
    
    analyzer = Analyzer('/path/to/project')
    issues = analyzer.analyze()
    
    for issue in issues:
        print(f"{issue.severity}: {issue.message}")
    ```
    
    With custom configuration and performance features:
    
    ```python
    config = {
        'detectors': {
            'dead_code': {'enabled': True},
            'complexity_hotspot': {'cyclomatic_threshold': 15}
        },
        'performance': {
            'parallel': True,
            'cache_enabled': True
        }
    }
    
    analyzer = Analyzer('/path/to/project', config=config)
    issues = analyzer.analyze()
    ```
"""

import logging
import sqlite3
import time
from typing import Dict, List, Optional, Type, Union, Any
from pathlib import Path
import ast
import sqlite3

from .models import CodeGraph, Issue
from .detectors import Detector, BaseDetector
from .loader import CodeLoader
from .settings import Settings
from .performance import AnalysisCache, ParallelAnalyzer, get_cache
from .incremental import GitAnalyzer, IncrementalAnalysisConfig
from .hooks import HookManager, HookContext, get_hook_manager
from .suppression import SuppressionEngine, SuppressionConfig, create_default_suppression_config
from .deduplication import DeduplicationEngine, IssueGroup
from .filtering import OutputFilter, FilterConfig, create_production_filter_config

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Raised when analysis fails unexpectedly."""
    pass


class Analyzer:
    """
    Main analyzer class that coordinates the analysis process.
    
    The Analyzer integrates all components of the pythonium system:
    - Settings management for shared configuration
    - Performance optimizations (caching, parallel execution)
    - Incremental analysis for faster CI execution
    - Extensibility hooks for custom functionality
    - Detector management and execution
    
    Attributes:
        root_path: Root directory of the project being analyzed
        settings: Shared settings object for configuration
        detectors: Dictionary of registered detector instances
        loader: CodeLoader instance for reading source files
        graph: CodeGraph representation of the analyzed code
        cache: Analysis cache for performance optimization
        parallel_analyzer: Parallel execution manager
        git_analyzer: Git integration for incremental analysis
        hook_manager: Extensibility hook manager
    """
    
    def __init__(
        self,
        root_path: Union[str, Path],
        config: Optional[dict] = None,
        settings: Optional[Settings] = None,
        use_cache: bool = True,
        use_parallel: bool = True,
        use_incremental: bool = True,
        enable_suppression: bool = True,
        enable_deduplication: bool = True,
        enable_filtering: bool = True,
    ) -> None:
        """
        Initialize the analyzer.
        
        Args:
            root_path: Root directory of the project to analyze
            config: Configuration dictionary (will be converted to Settings)
            settings: Pre-configured Settings object (takes precedence over config)
            use_cache: Whether to enable performance caching
            use_parallel: Whether to enable parallel detector execution
            use_incremental: Whether to enable incremental analysis
            enable_suppression: Whether to enable issue suppression
            enable_deduplication: Whether to enable issue deduplication
            enable_filtering: Whether to enable output filtering
                   
        Raises:
            ValueError: If root_path does not exist or is not a directory
        """
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_path}")
          # Initialize settings and config
        self.config = config or {}
        if settings is not None:
            self.settings = settings
        elif config is not None:
            self.settings = Settings.from_dict(config)
        else:
            self.settings = Settings()
        
        # Initialize components
        self.detectors: Dict[str, Detector] = {}
        self.loader = CodeLoader(self.root_path)
        self.graph: Optional[CodeGraph] = None        # Performance features
        self.use_cache = use_cache
        if use_cache:
            # Use centralized path resolver for consistent cache location
            from .database_paths import DatabasePathResolver
            cache_path = DatabasePathResolver.get_cache_db_path(self.root_path)
            from .performance import set_cache_path, get_cache
            set_cache_path(cache_path)
            self.cache = get_cache()
        else:
            self.cache = None
        
        self.use_parallel = use_parallel
        self.parallel_analyzer = ParallelAnalyzer() if use_parallel else None
        
        # Incremental analysis
        self.use_incremental = use_incremental
        self.git_analyzer: Optional[GitAnalyzer] = None
        self.incremental_config = IncrementalAnalysisConfig()
        
        if use_incremental:
            try:
                self.git_analyzer = GitAnalyzer(self.root_path)
            except ValueError:
                self.use_incremental = False
        
        # Extensibility
        self.hook_manager = get_hook_manager()
        
        # Issue processing systems
        self.enable_suppression = enable_suppression
        self.enable_deduplication = enable_deduplication
        self.enable_filtering = enable_filtering
        
        # Initialize suppression system
        if enable_suppression:
            suppression_config = config.get('suppression') if config else None
            if suppression_config and isinstance(suppression_config, dict):
                self.suppression_config = SuppressionConfig(**suppression_config)
            else:
                self.suppression_config = create_default_suppression_config()
            self.suppression_engine = SuppressionEngine(self.suppression_config)
        else:
            self.suppression_engine = None
            
        # Initialize deduplication system
        if enable_deduplication:
            self.deduplication_engine = DeduplicationEngine()
        else:
            self.deduplication_engine = None
            
        # Initialize filtering system  
        if enable_filtering:
            filter_config = config.get('filtering') if config else None
            if filter_config and isinstance(filter_config, dict):
                self.filter_config = FilterConfig(**filter_config)
            else:
                self.filter_config = create_production_filter_config()
            self.output_filter = OutputFilter(self.filter_config)
        else:
            self.output_filter = None
        
        # Load default detectors
        self.load_default_detectors()
    
    def register_detector(self, detector: Detector) -> None:
        """
        Register a detector instance.
        
        Args:
            detector: Detector instance to register
            
        Raises:
            TypeError: If detector is not a valid Detector instance
        """
        if not isinstance(detector, Detector):
            raise TypeError(f"Expected a Detector instance, got {type(detector).__name__}")
        detector_id = detector.id
        if detector_id in self.detectors:
            logger.warning("Detector '%s' already registered, overwriting", detector_id)
        
        self.detectors[detector_id] = detector
    
    def load_detectors_from_entry_points(self) -> None:
        """
        Load detectors from entry points.
        
        This allows external packages to provide custom detectors by registering
        them under the 'pythonium.detectors' entry point group.
        
        Raises:
            AnalysisError: If critical errors occur during detector loading
        """
        try:
            from importlib.metadata import entry_points
            
            # Load detectors from entry points
            detector_eps = entry_points(group='pythonium.detectors')
            
            loaded_count = 0
            for ep in detector_eps:
                try:
                    detector_class = ep.load()
                    if not isinstance(detector_class, type) or not issubclass(detector_class, BaseDetector):
                        logger.warning("Entry point %s: invalid detector class", ep.name)
                        continue
                    
                    # Initialize detector with config
                    detector_config = self.config.get('detectors', {}).get(ep.name, {})
                    detector = detector_class(**detector_config)
                    self.register_detector(detector)
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning("Failed to load detector %s: %s", ep.name, str(e))
            
            if loaded_count > 0:
                logger.info("Loaded %d external detectors", loaded_count)
                    
        except ImportError:
            logger.warning("Could not load external detectors (requires Python 3.8+)")
    
    def load_default_detectors(self) -> None:
        """
        Load the default set of detectors by dynamically discovering them.
        
        This method scans the detectors directory and loads all detector classes
        automatically, applying any custom settings from the configuration.
        
        Raises:
            AnalysisError: If critical detectors fail to load
        """
        # Dynamically discover detector classes
        detector_classes = self._discover_detector_classes()
        
        if not detector_classes:
            logger.warning("No detector classes found in detectors directory")
            return
        
        # Get detector configurations from config
        detector_configs = self.config.get('detectors', {})
        
        loaded_count = 0
        failed_count = 0
        
        for detector_class in detector_classes:
            detector_id = detector_class.id
            detector_config = detector_configs.get(detector_id, {})
            
            # Handle different config formats
            if isinstance(detector_config, bool):
                if not detector_config:  # False means disabled
                    continue
                detector_config = {}  # True means enabled with default config
            elif isinstance(detector_config, dict):
                # Check if detector is explicitly disabled
                if detector_config.get('enabled') is False:
                    continue
            else:
                # Invalid config, use defaults
                detector_config = {}
            
            try:
                detector = detector_class(**detector_config)
                self.register_detector(detector)
                loaded_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning("Failed to load %s: %s", detector_class.__name__, str(e))
        
        if failed_count > 0:
            logger.info("Loaded %d detectors (%d failed)", loaded_count, failed_count)
        else:
            logger.info("Loaded %d detectors", loaded_count)
        
        if loaded_count == 0:
            raise AnalysisError("No detectors could be loaded - analysis cannot proceed")
    
    def analyze(
        self, 
        files: Optional[List[Union[str, Path]]] = None,
        force_full: bool = False
    ) -> List[Issue]:
        """
        Analyze the code and return a list of issues.
        
        Args:
            files: Optional list of specific files to analyze. If None, analyzes all Python files.
            force_full: Force full analysis even if incremental analysis is available
            
        Returns:        """
        start_time = time.time()
        
        try:
            # Determine which files to analyze
            files_to_analyze = self._determine_files_to_analyze(files, force_full)
            
            if not files_to_analyze:
                logger.info("No files to analyze")
                return []
            
            # Purge cache of excluded paths at the beginning of analysis
            if self.cache and self.settings.ignored_paths:
                logger.debug("Purging cache for excluded paths...")
                self.cache.purge_excluded_paths(self.settings.ignored_paths)
            
            # Invalidate cache for changed files and their dependents
            self._invalidate_changed_files(files_to_analyze)
            
            # Load code into graph
            self.graph = self._load_code_with_hooks(files_to_analyze)
            
            if not self.graph.symbols:
                logger.warning("No symbols found")
                return []
            
            # Record file dependencies for cache invalidation
            self._record_file_dependencies(files_to_analyze)
            
            # Calculate actual processed file count from the graph's file metadata
            processed_files_count = len(set(symbol.location.file for symbol in self.graph.symbols.values()))
            
            logger.info("Found %d symbols in %d files", len(self.graph.symbols), processed_files_count)
            
            # Run detectors
            raw_issues = self._run_detectors_with_hooks()
            
            # Process issues through the pipeline
            processed_issues = self._process_issues(raw_issues)
            
            # Apply finish hooks
            context = HookContext(analyzer=self, metadata={
                'files_intended': len(files_to_analyze),
                'files_processed': processed_files_count,
                'symbols_loaded': len(self.graph.symbols),
                'analysis_time': time.time() - start_time,
                'raw_issues_count': len(raw_issues),
                'processed_issues_count': len(processed_issues),
            })
            
            final_issues = self.hook_manager.execute_finish_hooks(self.graph, processed_issues, context)
            
            elapsed = time.time() - start_time
            logger.info("Analysis complete: %d issues in %d files (%.2fs)", 
                       len(final_issues), processed_files_count, elapsed)
            
            return final_issues
            
        except Exception as e:
            logger.error("Analysis failed: %s", e)
            raise AnalysisError(f"Analysis failed: {e}") from e

    def _process_issues(self, raw_issues: List[Issue]) -> List[Issue]:
        """
        Process raw issues through suppression, deduplication, and filtering pipeline.
        
        Args:
            raw_issues: Raw issues from detectors
            
        Returns:
            Processed and filtered issues
        """
        if not raw_issues:
            return raw_issues
        
        processed = raw_issues
        original_count = len(processed)
        
        # Step 1: Apply suppression rules
        if self.enable_suppression and self.suppression_engine:
            source_files = self._load_source_files_for_suppression(processed)
            processed = self.suppression_engine.filter_issues(processed, source_files)
        
        # Step 2: Deduplicate similar issues
        if self.enable_deduplication and self.deduplication_engine:
            processed, duplicate_groups = self.deduplication_engine.deduplicate_issues(processed)
        
        # Step 3: Apply output filtering
        if self.enable_filtering and self.output_filter:
            processed, filter_stats = self.output_filter.filter_issues(processed)
        
        return processed
    
    def _load_source_files_for_suppression(self, issues: List[Issue]) -> Dict[Path, List[str]]:
        """Load source file contents for suppression checking."""
        source_files = {}
        
        # Collect unique file paths from issues
        file_paths = set()
        for issue in issues:
            if issue.location and issue.location.file:
                file_paths.add(issue.location.file)
        
        # Load source content for each file
        for file_path in file_paths:
            try:
                if self.suppression_engine:
                    source_lines = self.suppression_engine.load_file_source(file_path)
                    source_files[file_path] = source_lines
            except Exception as e:
                logger.warning("Could not load source for suppression: %s", file_path)
        
        return source_files

    def _determine_files_to_analyze(
        self, 
        files: Optional[List[Union[str, Path]]], 
        force_full: bool
    ) -> List[Path]:
        """Determine which files should be analyzed."""
        if files is not None:
            # Specific files provided - expand directories and filter Python files
            all_files = []
            for file_path in files:
                path = Path(file_path).resolve()
                if path.is_file() and path.suffix == '.py':
                    all_files.append(path)
                elif path.is_dir():
                    # Use loader to discover Python files in directory
                    python_files = self.loader._discover_python_files(path)
                    all_files.extend(python_files)
                else:
                    logger.warning("Invalid path: %s", path)
            return all_files
        
        # Check if incremental analysis should be used
        if (not force_full and 
            self.use_incremental and 
            self.git_analyzer and
            self.incremental_config.enabled):
            
            if self.git_analyzer.should_analyze_incrementally(self.incremental_config.max_changed_files):
                changed_files = self.git_analyzer.get_python_files_changed(
                    branch=self.incremental_config.base_branch
                )
                
                if changed_files:
                    # Check if config files changed (force full analysis)
                    if self.incremental_config.should_force_full_analysis(changed_files):
                        logger.info("Config changed, using full analysis")
                    else:
                        logger.info("Using incremental analysis (%d files)", len(changed_files))
                        return changed_files
          # Fall back to full analysis
        all_files = self.loader._discover_python_files(self.root_path)
        # Filter out ignored files early to reduce noise in logs
        filtered_files = [f for f in all_files if not self.settings.is_path_ignored(f)]
        ignored_count = len(all_files) - len(filtered_files)
        
        if ignored_count > 0:
            logger.info("Found %d files (%d ignored)", len(all_files), ignored_count)
        else:
            logger.info("Found %d files", len(filtered_files))
        
        return filtered_files

    def _load_code_with_hooks(self, files_to_analyze: List[Path]) -> CodeGraph:
        """Load code with pre-load and post-load hooks."""
        graph = CodeGraph()
        processed_count = 0
        ignored_count = 0
        failed_count = 0
        
        # Pre-load hook
        context = HookContext(analyzer=self, metadata={'files_to_analyze': files_to_analyze})
        self.hook_manager.execute_pre_load_hooks(context)
        
        # Load the code
        self.graph = self.loader.load(files_to_analyze)
        
        # Record file dependencies if caching is enabled
        if self.cache:
            self._record_file_dependencies(files_to_analyze)
        
        # Post-load hook
        context = HookContext(analyzer=self, metadata={
            'files_loaded': len(files_to_analyze),
            'symbols_loaded': len(self.graph.symbols)
        })
        self.graph = self.hook_manager.execute_post_load_hooks(self.graph, context)
        
        return self.graph

    def _extract_file_dependencies(self, file_path: Path) -> List[Path]:
        """
        Extract dependencies (imports) from a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of file paths that this file depends on
        """
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep_path = self._resolve_import_to_file(alias.name, file_path)
                        if dep_path and dep_path.exists():
                            dependencies.append(dep_path)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dep_path = self._resolve_import_to_file(node.module, file_path)
                        if dep_path and dep_path.exists():
                            dependencies.append(dep_path)
                        
        except Exception as e:
            logger.debug("Failed to extract dependencies from %s: %s", file_path, e)
            
        return dependencies

    def _resolve_import_to_file(self, module_name: str, current_file: Path) -> Optional[Path]:
        """
        Resolve an import name to a file path.
        
        Args:
            module_name: The module name to resolve (e.g., 'os.path', 'mymodule')
            current_file: The file containing the import
            
        Returns:
            Path to the imported file, or None if not found/resolvable
        """
        # Skip standard library modules
        if module_name in {'os', 'sys', 'ast', 'pathlib', 'typing', 'collections', 
                          'itertools', 'functools', 'operator', 'json', 'pickle',
                          'sqlite3', 'logging', 'time', 'hashlib', 're', 'subprocess'}:
            return None
            
        # Handle relative imports within the project
        current_dir = current_file.parent
        
        # Try different resolution strategies
        module_parts = module_name.split('.')
        
        # Strategy 1: Relative to current file's directory
        potential_path = current_dir
        for part in module_parts:
            potential_path = potential_path / part
        
        # Check for .py file
        if (potential_path.with_suffix('.py')).exists():
            return potential_path.with_suffix('.py')
            
        # Check for package (__init__.py)
        if (potential_path / '__init__.py').exists():
            return potential_path / '__init__.py'
        
        # Strategy 2: Relative to project root
        potential_path = self.root_path
        for part in module_parts:
            potential_path = potential_path / part
            
        if (potential_path.with_suffix('.py')).exists():
            return potential_path.with_suffix('.py')
            
        if (potential_path / '__init__.py').exists():
            return potential_path / '__init__.py'
            
        # Strategy 3: Check if it's a local module in the same directory
        if len(module_parts) == 1:
            local_file = current_dir / f"{module_parts[0]}.py"
            if local_file.exists():
                return local_file
                
        return None

    def _record_file_dependencies(self, files_to_analyze: List[Path]) -> None:
        """
        Record dependencies for all files being analyzed.
        
        Args:
            files_to_analyze: List of files to extract dependencies from
        """
        if not self.cache:
            return
            
        for file_path in files_to_analyze:
            try:
                dependencies = self._extract_file_dependencies(file_path)
                if dependencies:
                    self.cache.record_file_dependencies(file_path, dependencies, 'import')
                    logger.debug("Recorded %d dependencies for %s", len(dependencies), file_path)
            except Exception as e:
                logger.debug("Failed to record dependencies for %s: %s", file_path, e)

    def _invalidate_changed_files(self, files_to_analyze: List[Path]) -> None:
        """
        Invalidate cache entries for changed files and their dependents.
        
        Args:
            files_to_analyze: List of files that might have changed
        """
        if not self.cache:
            return
            
        for file_path in files_to_analyze:
            try:
                # Check if file has actually changed
                current_sha = self.cache.get_file_sha(file_path)
                cached_symbols = self.cache.get_cached_symbols(file_path)
                
                if cached_symbols is not None:
                    # File was cached, check if it changed
                    with sqlite3.connect(self.cache.cache_path) as conn:
                        cursor = conn.execute(
                            "SELECT file_sha FROM file_cache WHERE file_path = ?",
                            (str(file_path),)
                        )
                        row = cursor.fetchone()
                        if row and row[0] != current_sha:
                            # File changed, invalidate it and its dependents
                            invalidated = self.cache.invalidate_dependents(file_path)
                            if invalidated:
                                logger.debug("Invalidated %d dependent files for %s", 
                                           len(invalidated), file_path)
                                           
            except Exception as e:
                logger.debug("Failed to check/invalidate %s: %s", file_path, e)
        
    def _run_detectors_with_hooks(self) -> List[Issue]:
        """Run detectors with hooks integration."""
        if not self.graph:
            return []
        
        # Filter enabled detectors
        enabled_detectors = [
            detector for detector in self.detectors.values()
            if self.settings.is_detector_enabled(detector.id)
        ]
        
        if not enabled_detectors:
            logger.warning("No detectors enabled")
            return []
        
        logger.info("Running %d detectors", len(enabled_detectors))
        
        # Run detectors (parallel or sequential)
        if self.use_parallel and self.parallel_analyzer and len(enabled_detectors) > 1:
            raw_issues = self.parallel_analyzer.analyze_parallel(enabled_detectors, self.graph)
        else:
            raw_issues = self._run_detectors_sequential(enabled_detectors)
        
        # Apply issue hooks to each issue
        final_issues = []
        context = HookContext(analyzer=self, metadata={'total_detectors': len(enabled_detectors)})
        
        for issue in raw_issues:
            processed_issue = self.hook_manager.execute_issue_hooks(issue, context)
            if processed_issue is not None:
                final_issues.append(processed_issue)
        
        return final_issues

    def _run_detectors_sequential(self, detectors: List[Detector]) -> List[Issue]:
        """Run detectors sequentially."""
        all_issues = []
        
        for detector in detectors:
            try:
                start_time = time.time()
                
                issues = detector.analyze(self.graph)
                elapsed = time.time() - start_time
                
                logger.info("Found %d issues with %s (%.2fs)", 
                           len(issues), detector.name, elapsed)
                all_issues.extend(issues)
                
            except Exception as e:
                logger.error("Detector %s failed: %s", detector.name, e)
        
        return all_issues

    def get_detector(self, detector_id: str) -> Optional[Detector]:
        """
        Get a detector by ID.
        
        Args:
            detector_id: ID of the detector to get
            
        Returns:
            The detector instance, or None if not found
        """
        return self.detectors.get(detector_id)
    
    def list_detectors(self) -> Dict[str, dict]:
        """
        List all available detectors with their metadata.
        
        Returns:
            Dictionary mapping detector IDs to their metadata including:
            - id: Detector identifier
            - name: Human-readable name
            - description: What the detector checks for
            - type: Detector type (core, plugin, etc.)
            - enabled: Whether the detector is currently enabled
        """
        result = {}
        for detector_id, detector in self.detectors.items():
            result[detector_id] = {
                "id": detector.id,
                "name": detector.name,
                "description": detector.description,
                "type": "core",  # All current detectors are core
                "enabled": True,  # All registered detectors are enabled
            }
        return result
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current analysis state.
        
        Returns:
            Dictionary containing analysis metadata including:
            - root_path: Project root directory
            - detectors_loaded: Number of loaded detectors
            - symbols_analyzed: Number of symbols in the code graph
            - files_analyzed: Number of files in the code graph
        """
        summary = {
            "root_path": str(self.root_path),
            "detectors_loaded": len(self.detectors),
            "symbols_analyzed": len(self.graph.symbols) if self.graph else 0,
            "files_analyzed": 0,
        }
        
        if self.graph:
            files = set()
            for symbol in self.graph.symbols.values():
                if symbol.location and symbol.location.file:
                    files.add(symbol.location.file)
            summary["files_analyzed"] = len(files)
        
        return summary

    def _discover_detector_classes(self) -> List[type]:
        """
        Dynamically discover all detector classes from the detectors directory.
        
        Returns:
            List of detector classes found in the detectors directory
        """
        import importlib
        import inspect
        from .detectors import BaseDetector
        
        detector_classes = []
        detectors_dir = Path(__file__).parent / "detectors"
        
        if not detectors_dir.exists():
            logger.warning("Detectors directory not found: %s", detectors_dir)
            return detector_classes
        
        # Scan all Python files in detectors directory
        for py_file in detectors_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
                
            module_name = f"pythonium.detectors.{py_file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # Find all detector classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (obj != BaseDetector and 
                        issubclass(obj, BaseDetector) and 
                        hasattr(obj, 'id') and
                        obj.__module__ == module_name):  # Only classes defined in this module
                        detector_classes.append(obj)
                        logger.debug("Discovered detector: %s from %s", name, module_name)
                        
            except ImportError as e:
                logger.warning("Could not import detector module %s: %s", module_name, e)
            except Exception as e:
                logger.warning("Error scanning detector module %s: %s", module_name, e)
        
        logger.info("Discovered %d detector classes", len(detector_classes))
        return detector_classes
