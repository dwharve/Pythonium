"""
Configuration service for Pythonium MCP server.

Provides centralized configuration management with caching,
schema validation, and consistent configuration merging.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from pythonium.settings import Settings
from ..utils.debug import info_log, warning_log


class ConfigurationService:
    """
    Service for managing configuration operations.
    
    This service provides:
    - Centralized schema management with caching
    - Consistent configuration merging logic
    - Documentation and examples for configuration options
    """
    
    def __init__(self):
        """Initialize the configuration service."""
        self._schema_cache: Dict[str, Any] = {}
        self._default_settings: Optional[Settings] = None
    
    def get_default_settings(self) -> Settings:
        """Get default settings, creating them if needed."""
        if self._default_settings is None:
            self._default_settings = Settings()
        return self._default_settings
    
    def get_schema_documentation(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive configuration schema documentation.
        
        Args:
            section: Specific section to retrieve (overview, detectors, global, etc.)
            
        Returns:
            Dictionary with schema documentation
        """
        if section is None:
            section = "overview"
        
        # Check cache first
        cache_key = f"schema_{section}"
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]
        
        # Generate documentation based on section
        if section == "overview":
            doc = self._generate_schema_overview()
        elif section == "detectors":
            doc = self._generate_detector_configurations()
        elif section == "global":
            doc = self._generate_global_configurations()
        elif section == "examples":
            doc = self._generate_configuration_examples()
        elif section == "precedence":
            doc = self._generate_configuration_precedence()
        elif section == "validation":
            doc = self._generate_configuration_validation()
        else:
            doc = {
                "error": f"Unknown configuration section: {section}",
                "available_sections": ["overview", "detectors", "global", "examples", "precedence", "validation"]
            }
        
        # Cache the result
        self._schema_cache[cache_key] = doc
        return doc
    
    def merge_configurations(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries with proper precedence.
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                merged[key] = self.merge_configurations(merged[key], value)
            else:
                # Override value
                merged[key] = value
        
        return merged
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a configuration dictionary against the schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Create a Settings object to validate the configuration
            settings = Settings(**config)
            return {
                "valid": True,
                "errors": [],
                "warnings": [],
                "normalized_config": settings.model_dump()
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "normalized_config": None
            }
    
    def get_detector_schema(self, detector_id: str) -> Dict[str, Any]:
        """
        Get schema information for a specific detector.
        
        Args:
            detector_id: ID of the detector
            
        Returns:
            Dictionary with detector schema information
        """
        # Uses detector registry integration
        return {
            "detector_id": detector_id,
            "configuration_options": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether the detector is enabled"
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warn", "error"],
                    "default": "info",
                    "description": "Default severity level for issues from this detector"
                }
            }
        }
    
    def _generate_schema_overview(self) -> Dict[str, Any]:
        """Generate complete configuration schema overview."""
        default_settings = self.get_default_settings()
        
        return {
            "title": "Pythonium Configuration Schema",
            "description": "Complete configuration schema for Pythonium code health analysis",
            "structure": {
                "analysis": "Analysis behavior configuration",
                "detectors": "Detector-specific configurations",
                "filtering": "Path and file filtering options",
                "performance": "Performance and caching settings",
                "output": "Output formatting and reporting options"
            },
            "sample_configuration": {
                "analysis": {
                    "track_issues": True,
                    "incremental": False
                },
                "filtering": {
                    "ignored_paths": default_settings.ignored_paths[:3],
                    "file_extensions": [".py"]
                },
                "performance": {
                    "cache_enabled": True,
                    "parallel": True,
                    "max_workers": 4
                }
            }
        }
    
    def _generate_detector_configurations(self) -> Dict[str, Any]:
        """Generate detector-specific configuration documentation."""
        return {
            "title": "Detector Configurations",
            "description": "Configuration options for individual detectors",
            "structure": {
                "enabled": "Whether the detector is active",
                "severity": "Default severity level for issues",
                "config": "Detector-specific configuration options"
            },
            "examples": {
                "security_smell": {
                    "enabled": True,
                    "severity": "warn",
                    "config": {
                        "check_pickle": True,
                        "check_eval": True
                    }
                },
                "complexity_hotspot": {
                    "enabled": True,
                    "severity": "info",
                    "config": {
                        "complexity_threshold": 10,
                        "method_threshold": 20
                    }
                }
            }
        }
    
    def _generate_global_configurations(self) -> Dict[str, Any]:
        """Generate global configuration documentation."""
        return {
            "title": "Global Configuration Options",
            "description": "System-wide configuration settings",
            "options": {
                "analysis": {
                    "track_issues": "Whether to track issues in database",
                    "incremental": "Whether to use incremental analysis"
                },
                "performance": {
                    "cache_enabled": "Enable/disable result caching",
                    "parallel": "Enable/disable parallel processing",
                    "max_workers": "Maximum number of worker threads"
                },
                "filtering": {
                    "ignored_paths": "List of paths to ignore during analysis",
                    "file_extensions": "File extensions to analyze"
                }
            }
        }
    
    def _generate_configuration_examples(self) -> Dict[str, Any]:
        """Generate configuration examples."""
        return {
            "title": "Configuration Examples",
            "description": "Practical configuration examples for different use cases",
            "examples": {
                "development": {
                    "description": "Configuration for development environment",
                    "config": {
                        "analysis": {"track_issues": True},
                        "performance": {"parallel": True, "cache_enabled": True},
                        "detectors": {
                            "security_smell": {"enabled": True, "severity": "error"},
                            "complexity_hotspot": {"enabled": True, "severity": "warn"}
                        }
                    }
                },
                "ci_cd": {
                    "description": "Configuration for CI/CD pipeline",
                    "config": {
                        "analysis": {"track_issues": False},
                        "performance": {"parallel": False, "cache_enabled": False},
                        "output": {"format": "json", "verbose": False}
                    }
                }
            }
        }
    
    def _generate_configuration_precedence(self) -> Dict[str, Any]:
        """Generate configuration precedence documentation."""
        return {
            "title": "Configuration Precedence",
            "description": "How configuration values are resolved",
            "precedence_order": [
                "Command line arguments (highest priority)",
                "User-provided configuration",
                "Project configuration file",
                "Default configuration (lowest priority)"
            ],
            "merge_behavior": {
                "dictionaries": "Merged recursively, with higher precedence values overriding lower",
                "lists": "Higher precedence values completely replace lower precedence",
                "primitives": "Higher precedence values replace lower precedence"
            }
        }
    
    def _generate_configuration_validation(self) -> Dict[str, Any]:
        """Generate configuration validation documentation."""
        return {
            "title": "Configuration Validation",
            "description": "How configuration is validated and normalized",
            "validation_rules": {
                "required_fields": "Fields that must be present",
                "type_checking": "Ensures values match expected types",
                "enum_validation": "Validates enum values are from allowed set",
                "range_checking": "Ensures numeric values are within valid ranges"
            },
            "common_errors": {
                "invalid_detector_id": "Referenced detector does not exist",
                "invalid_severity": "Severity must be one of: info, warn, error",
                "invalid_path": "Path does not exist or is not accessible"
            }
        }
    
    def clear_cache(self) -> None:
        """Clear the schema documentation cache."""
        self._schema_cache.clear()
        info_log("Configuration schema cache cleared")
