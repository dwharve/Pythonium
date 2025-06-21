"""Code health issue detectors."""

from typing import Optional, Protocol, runtime_checkable, List, Any
from pathlib import Path
from ..models import CodeGraph, Issue, Symbol, Location


@runtime_checkable
class Detector(Protocol):
    """Protocol that all pythonium detectors must implement.
    
    Detectors analyze the code graph and return a list of issues.
    """
    
    #: Unique identifier for this detector (e.g., "dead_code")
    id: str
    
    #: Human-readable name for this detector
    name: str
    
    #: Description of what this detector checks for
    description: str
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph and return a list of issues.
        
        Args:
            graph: The code graph to analyze
            
        Returns:
            List of issues found during analysis
        """
        ...


class BaseDetector:
    """Base class for detectors that provides common functionality."""
    
    id: str
    name: str
    description: str = ""
    
    # Metadata that detectors should provide for better agent understanding
    category: str = "Code Analysis"  # e.g., "Security & Safety", "Code Duplication", etc.
    usage_tips: str = ""  # How to best use this detector
    related_detectors: List[str] = []  # IDs of related detectors
    typical_severity: str = "info"  # Typical severity: "error", "warn", "info"
    detailed_description: str = ""  # Extended description of what it detects
    
    def __init__(self, settings=None, **options):
        """
        Initialize the detector.
        
        Args:
            settings: Shared settings object for configuration
        """
        from ..settings import Settings  # Import here to avoid circular imports
        
        if settings is None:
            settings = Settings()
        self.settings = settings
        
        # Set default detailed_description from description if not provided
        if not self.detailed_description:
            self.detailed_description = self.description
        
        # Initialize cache reference for smart caching
        self._cache = None
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        """
        Analyze the code graph and return a list of issues.
        
        This method handles automatic smart caching for expensive detectors.
        Subclasses should override _analyze() instead of this method.
        """
        if not graph.symbols:
            return []
        
        # Check cache for expensive detectors
        cached_issues = self._try_get_cached_results(graph)
        if cached_issues is not None:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Using cached results for detector {self.id}")
            return cached_issues
        
        # Perform actual analysis
        result = self._analyze(graph)
        
        # Ensure result is always a list
        if not isinstance(result, list):
            if hasattr(result, '__iter__') and not isinstance(result, str):
                result = list(result)
            else:
                # Single issue, wrap in list
                result = [result] if result is not None else []
        
        # Cache results for expensive detectors
        self._try_cache_results(graph, result)
        
        return result
    
    def _try_get_cached_results(self, graph: CodeGraph) -> Optional[List[Issue]]:
        """Try to get cached results if this is an expensive detector."""
        if not self._is_cacheable():
            return None
        
        # Initialize cache if needed
        if self._cache is None:
            from ..performance import get_cache
            self._cache = get_cache()
        
        if not self._cache:
            return None
        
        # All detectors use unified caching since they all analyze the full graph
        files_involved = self._get_involved_files(graph)
        return self._cache.get_detector_issues(self.id, files_involved)
    
    def _try_cache_results(self, graph: CodeGraph, issues: List[Issue]) -> None:
        """Try to cache results if this is an expensive detector."""
        if not self._is_cacheable():
            return
        
        # Initialize cache if needed
        if self._cache is None:
            from ..performance import get_cache
            self._cache = get_cache()
        
        if not self._cache:
            return
        
        # All detectors use unified caching since they all analyze the full graph
        files_involved = self._get_involved_files(graph)
        self._cache.set_detector_issues(self.id, files_involved, issues)
    
    def _is_cacheable(self) -> bool:
        """Check if this detector should be cached (expensive detectors only)."""
        expensive_detectors = {
            'complexity_hotspot', 'clone', 'block_clone', 
            'semantic_equivalence', 'security_smell', 'circular_deps',
            'alt_implementation', 'advanced_patterns'
        }
        return self.id in expensive_detectors
    
    def _get_involved_files(self, graph: CodeGraph) -> List[Path]:
        """Get list of files involved in the analysis."""
        files = set()
        for symbol in graph.symbols.values():
            if symbol.location and symbol.location.file:
                files.add(symbol.location.file)
        return list(files)
    
    # Utility methods for accessing the shared parsed repository
    
    def get_file_ast(self, graph: CodeGraph, file_path) -> Optional[Any]:
        """Get the parsed AST for a file from the shared repository."""
        file_key = str(file_path)
        return graph.parsed_files.get(file_key)
    
    def get_file_content(self, graph: CodeGraph, file_path) -> Optional[str]:
        """Get the source content for a file from the shared repository."""
        file_key = str(file_path)
        return graph.file_contents.get(file_key)
    
    def get_file_symbols(self, graph: CodeGraph, file_path) -> List[Symbol]:
        """Get all symbols defined in a specific file."""
        return graph.get_symbols_by_file(str(file_path))
    
    def get_symbols_by_type(self, graph: CodeGraph, ast_type) -> List[Symbol]:
        """Get symbols of a specific AST node type."""
        return graph.get_symbols_by_type(ast_type)
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Subclasses should implement this method to perform the actual analysis."""
        raise NotImplementedError("Subclasses must implement _analyze()")
    
    def create_issue(
        self,
        issue_id: str,
        message: str,
        severity: str = "warn",
        symbol: Optional[Symbol] = None,
        location: Optional[Location] = None,
        related_files: Optional[List] = None,
        **metadata,
    ) -> Issue:
        """Helper method to create a new issue with consistent metadata."""
        if location is None and symbol is not None:
            location = symbol.location
        
        # Apply severity override if configured
        severity_override = self.settings.get_severity_override(self.id, issue_id)
        if severity_override:
            severity = severity_override
        
        # Handle related files
        if related_files is None:
            related_files = []
        
        # Auto-detect multi-file from metadata if not explicitly set
        if metadata:
            if 'locations' in metadata:
                files = set()
                for loc in metadata['locations']:
                    if ':' in str(loc):
                        file_part = str(loc).split(':')[0]
                        files.add(file_part)
                if len(files) > 1:
                    related_files = [Path(f) for f in files]
        
        return Issue(
            id=f"{self.id}.{issue_id}",
            severity=severity,
            message=message,
            symbol=symbol,
            location=location,
            detector_id=self.id,
            related_files=related_files,
            metadata={
                "detector_name": self.name,
                "detector_description": self.description,
                **metadata,
            },
        )


# Note: Detector classes are now dynamically discovered by the analyzer
# No need for static imports - the analyzer scans the detectors directory automatically

__all__ = [
    "Detector",
    "BaseDetector", 
]
