"""
Service registry for dependency injection in Pythonium MCP server.

Provides centralized service management and dependency injection
to improve testability and reduce coupling between components.
"""

from typing import Optional
from .analysis_service import AnalysisService
from .issue_service import IssueService
from .configuration_service import ConfigurationService


class ServiceRegistry:
    """
    Central registry for all services used by MCP handlers.
    
    This implements a simple dependency injection container that:
    - Manages service lifecycles
    - Provides easy access to services for handlers
    - Enables easy mocking for testing
    """
    
    def __init__(self):
        """Initialize the service registry with default services."""
        self._analysis_service: Optional[AnalysisService] = None
        self._issue_service: Optional[IssueService] = None
        self._configuration_service: Optional[ConfigurationService] = None
    
    @property
    def analysis(self) -> AnalysisService:
        """Get the analysis service, creating it if needed."""
        if self._analysis_service is None:
            self._analysis_service = AnalysisService(self)
        return self._analysis_service
    
    @property
    def issues(self) -> IssueService:
        """Get the issue service, creating it if needed."""
        if self._issue_service is None:
            self._issue_service = IssueService(self)
        return self._issue_service
    
    @property
    def configuration(self) -> ConfigurationService:
        """Get the configuration service, creating it if needed."""
        if self._configuration_service is None:
            self._configuration_service = ConfigurationService()
        return self._configuration_service
    
    def register_analysis_service(self, service: AnalysisService) -> None:
        """Register a custom analysis service (useful for testing)."""
        self._analysis_service = service
    
    def register_issue_service(self, service: IssueService) -> None:
        """Register a custom issue service (useful for testing)."""
        self._issue_service = service
    
    def register_configuration_service(self, service: ConfigurationService) -> None:
        """Register a custom configuration service (useful for testing)."""
        self._configuration_service = service
    
    def reset(self) -> None:
        """Reset all services (useful for testing)."""
        self._analysis_service = None
        self._issue_service = None
        self._configuration_service = None
