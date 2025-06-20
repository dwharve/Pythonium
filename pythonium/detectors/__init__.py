"""Code health issue detectors."""

from typing import Optional, Protocol, runtime_checkable, List
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
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph and return a list of issues.
        
        Subclasses should override _analyze() instead of this method.
        """
        return self._analyze(graph)
    
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
        **metadata,
    ) -> Issue:
        """Helper method to create a new issue with consistent metadata."""
        if location is None and symbol is not None:
            location = symbol.location
        
        # Apply severity override if configured
        severity_override = self.settings.get_severity_override(self.id, issue_id)
        if severity_override:
            severity = severity_override
            
        return Issue(
            id=f"{self.id}.{issue_id}",
            severity=severity,
            message=message,
            symbol=symbol,
            location=location,
            detector_id=self.id,
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
