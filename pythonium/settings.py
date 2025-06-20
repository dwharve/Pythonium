"""
Settings management for Pythonium.

This module provides a shared Settings object that detectors can use
to read thresholds, ignored paths, and severity overrides.
"""

import glob
import re
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union


@dataclass
class DetectorSettings:
    """Settings for a specific detector."""
    enabled: bool = True
    severity_override: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Settings:
    """
    Shared settings object for all detectors.
    
    This provides a centralized way for detectors to access:
    - Threshold configurations
    - Ignored paths and patterns
    - Severity overrides
    - Detector-specific options
    - Issue suppression rules
    - Output filtering configuration
    
    Attributes:
        detector_settings: Per-detector configuration
        ignored_paths: List of glob patterns for files/paths to ignore
        severity_overrides: Global severity level overrides
        thresholds: Common threshold values
        python_version: Target Python version
        suppression_patterns: Patterns for suppressing false positives
        output_limits: Limits for filtering output
    """
    detector_settings: Dict[str, DetectorSettings] = field(default_factory=dict)
    ignored_paths: List[str] = field(default_factory=list)
    severity_overrides: Dict[str, str] = field(default_factory=dict)
    thresholds: Dict[str, Any] = field(default_factory=dict)
    python_version: str = "3.8"
    
    # Suppression configuration
    suppression_patterns: Dict[str, List[str]] = field(default_factory=dict)
    enable_builtin_suppressions: bool = True
    
    # Output filtering configuration
    output_limits: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default settings."""
        if not self.ignored_paths:
            self.ignored_paths = [
                "**/tests/**",
                "**/test_*.py",
                "**/*_test.py",
                "**/migrations/**",
                "**/__pycache__/**",
                "**/.pytest_cache/**",
                "**/venv/**",
                "**/env/**",
                "**/.tox/**",
                "**/build/**",
                "**/dist/**",
            ]
        
        if not self.thresholds:
            self.thresholds = {
                "complexity_cyclomatic": 10,
                "complexity_halstead": 15,
                "clone_similarity": 0.9,
                "clone_min_lines": 5,
                "high_fanin": 10,
                "dead_code_min_references": 0,
            }
        
        if not self.suppression_patterns:
            self.suppression_patterns = {
                "entry_points": [
                    "*.main",
                    "*.cli", 
                    "*.app",
                    "*.run",
                    "*.serve",
                ],
                "framework_functions": [
                    "*.__*__",  # Dunder methods
                    "*.setup",
                    "*.teardown", 
                    "*.configure",
                    "*.handle_*",  # Event handlers
                ],
                "test_files": [
                    "test_*",
                    "*_test",
                    "tests.*",
                    "examples.*",
                ]
            }
        
        if not self.output_limits:
            self.output_limits = {
                "max_issues_per_detector": 50,
                "max_total_issues": 200,
                "min_confidence": 0.2,
                "enable_deduplication": True,
                "enable_noise_reduction": True,
            }
    
    def is_path_ignored(self, file_path: Union[str, Path]) -> bool:
        """
        Check if a file path should be ignored based on ignore patterns.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if the path should be ignored
        """
        path_str = str(file_path)
        
        for pattern in self.ignored_paths:
            # Convert glob pattern to regex for more flexible matching
            if self._matches_pattern(path_str, pattern):
                return True
        
        return False
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a glob pattern."""
        import fnmatch
        
        # Normalize path separators to forward slashes for consistent matching
        normalized_path = path.replace("\\", "/")
        
        # Use fnmatch for simpler patterns first
        if fnmatch.fnmatch(normalized_path, pattern):
            return True
        
        # For patterns with **, try pathlib as a fallback
        if "**" in pattern:
            try:
                from pathlib import PurePath
                path_obj = PurePath(normalized_path)
                return path_obj.match(pattern)
            except (ValueError, NotImplementedError):
                # Fallback to regex-based matching
                import re
                regex_pattern = pattern.replace("**", ".*").replace("*", "[^/]*")
                return bool(re.search(regex_pattern, normalized_path))
        
        return False
    
    def get_detector_setting(self, detector_id: str, setting_name: str, default: Any = None) -> Any:
        """
        Get a setting for a specific detector.
        
        Args:
            detector_id: ID of the detector
            setting_name: Name of the setting
            default: Default value if setting not found
            
        Returns:
            The setting value or default
        """
        if detector_id not in self.detector_settings:
            return default
        
        return self.detector_settings[detector_id].options.get(setting_name, default)
    
    def is_detector_enabled(self, detector_id: str) -> bool:
        """
        Check if a detector is enabled.
        
        Args:
            detector_id: ID of the detector
            
        Returns:
            True if detector is enabled
        """
        if detector_id not in self.detector_settings:
            return True  # Default to enabled
        
        return self.detector_settings[detector_id].enabled
    
    def get_severity_override(self, detector_id: str, issue_id: str = None) -> Optional[str]:
        """
        Get severity override for a detector or specific issue.
        
        Args:
            detector_id: ID of the detector
            issue_id: Optional specific issue ID
            
        Returns:
            Override severity level or None
        """
        # Check specific issue override first
        if issue_id:
            full_issue_id = f"{detector_id}.{issue_id}"
            if full_issue_id in self.severity_overrides:
                return self.severity_overrides[full_issue_id]
        
        # Check detector override
        if detector_id in self.detector_settings:
            return self.detector_settings[detector_id].severity_override
        
        # Check global detector override
        return self.severity_overrides.get(detector_id)
    
    def get_threshold(self, name: str, default: Any = None) -> Any:
        """
        Get a threshold value.
        
        Args:
            name: Name of the threshold
            default: Default value if threshold not found
            
        Returns:
            The threshold value or default
        """
        return self.thresholds.get(name, default)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "Settings":
        """
        Create Settings from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Settings instance
        """
        settings = cls()
        
        # Parse detector settings
        detectors_config = config.get("detectors", {})
        for detector_id, detector_config in detectors_config.items():
            if isinstance(detector_config, bool):
                # Simple enabled/disabled
                settings.detector_settings[detector_id] = DetectorSettings(enabled=detector_config)
            elif isinstance(detector_config, dict):
                # Full configuration
                enabled = detector_config.get("enabled", True)
                severity_override = detector_config.get("severity")
                options = {k: v for k, v in detector_config.items() 
                          if k not in ("enabled", "severity")}
                
                settings.detector_settings[detector_id] = DetectorSettings(
                    enabled=enabled,
                    severity_override=severity_override,
                    options=options
                )
        
        # Parse ignored paths (support both 'ignore' and 'ignored_paths' keys)
        if "ignore" in config:
            settings.ignored_paths.extend(config["ignore"])
        if "ignored_paths" in config:
            settings.ignored_paths.extend(config["ignored_paths"])
        
        # Parse severity overrides
        if "severity" in config:
            settings.severity_overrides.update(config["severity"])
        
        # Parse thresholds
        if "thresholds" in config:
            settings.thresholds.update(config["thresholds"])
        
        # Parse detector options (top-level 'options' key)
        if "options" in config:
            options_config = config["options"]
            for detector_id, options in options_config.items():
                if detector_id not in settings.detector_settings:
                    settings.detector_settings[detector_id] = DetectorSettings()
                settings.detector_settings[detector_id].options.update(options)
            
        # Parse suppression patterns
        if "suppression" in config:
            suppression_config = config["suppression"]
            if "patterns" in suppression_config:
                settings.suppression_patterns.update(suppression_config["patterns"])
            if "enable_builtin_suppressions" in suppression_config:
                settings.enable_builtin_suppressions = suppression_config["enable_builtin_suppressions"]
                
        # Parse output limits
        if "output" in config:
            settings.output_limits.update(config["output"])
        
        return settings
