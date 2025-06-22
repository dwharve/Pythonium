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
                "**/.venv/**",           # Common virtual env name
                "**/virtualenv/**",      # Another common virtual env name
                "**/.tox/**",
                "**/build/**",
                "**/dist/**",
                "**/.git/**",            # Git repository
                "**/node_modules/**",    # Node.js dependencies (common in Python projects with web frontends)
                "**/coverage_html/**",   # Coverage reports
                "**/.coverage",          # Coverage data
                "**/htmlcov/**",         # Coverage HTML reports
                "**/.mypy_cache/**",     # MyPy cache
                "**/.ruff_cache/**",     # Ruff cache
                "**/site-packages/**",   # Installed packages
                "**/.eggs/**",           # Setuptools eggs
                "**/*.egg-info/**",      # Package metadata
                ".pythonium/**"          # Pythonium cache directory
            ]
        
        if not self.thresholds:
            self.thresholds = {
                # Optimized thresholds based on analysis
                "complexity_cyclomatic": 8,        # Reduced from 10 - catch complexity earlier
                "complexity_halstead": 18.0,       # Reduced from 15 - more sensitive
                "complexity_loc": 45,              # New - lines of code threshold
                "clone_similarity": 0.85,          # Reduced from 0.9 - better coverage
                "clone_min_lines": 4,              # Reduced from 5 - catch smaller clones
                "block_clone_similarity": 0.88,    # Block-level clone threshold
                "block_clone_min_statements": 3,   # Minimum statements for block clones
                "high_fanin": 15,                  # Reduced from 10 - catch high dependencies
                "max_cycle_length": 8,             # Reduced from 10 - focus on shorter cycles
                "dead_code_min_references": 0,     # Keep as 0 for unused code detection
                # New optimized thresholds
                "alt_implementation_similarity": 0.8,      # Alternative implementation detection
                "semantic_equivalence_confidence": 0.85,   # Semantic analysis confidence
                "security_pattern_confidence": 0.7,        # Security smell detection
                "deprecated_api_confidence": 0.8,          # Deprecated API detection
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
        
        # Simple fnmatch for patterns without **
        if "**" not in pattern:
            return fnmatch.fnmatch(normalized_path, pattern)
        
        # For ** patterns, we need to handle them specially
        # Convert ** to match zero or more path segments
        parts = pattern.split("**")
        
        if len(parts) == 1:
            # No ** in pattern, use fnmatch
            return fnmatch.fnmatch(normalized_path, pattern)
        
        # Check if the path matches the pattern with **
        # Strategy: check if the path starts and ends with the right parts
        if len(parts) == 2:
            prefix = parts[0].rstrip("/")
            suffix = parts[1].lstrip("/")
            
            if not prefix and not suffix:
                # Pattern is just "**", matches everything
                return True
            elif not prefix:
                # Pattern like "**/something"
                return fnmatch.fnmatch(normalized_path, suffix) or any(
                    fnmatch.fnmatch(part, suffix) for part in normalized_path.split("/")
                ) or normalized_path.endswith("/" + suffix.replace("*", ""))
            elif not suffix:
                # Pattern like "something/**"
                return fnmatch.fnmatch(normalized_path, prefix) or normalized_path.startswith(prefix + "/")
            else:
                # Pattern like "prefix/**/suffix"
                # Check if path starts with prefix and ends matching suffix
                if prefix and not (normalized_path.startswith(prefix + "/") or normalized_path == prefix):
                    return False
                
                # Check if any segment matches the suffix
                segments = normalized_path.split("/")
                for i, segment in enumerate(segments):
                    remaining_path = "/".join(segments[i:])
                    if fnmatch.fnmatch(remaining_path, suffix):
                        return True
                
                return False
        
        # Handle patterns like "**/venv/**" (3 parts)
        elif len(parts) == 3:
            prefix = parts[0].rstrip("/")
            middle = parts[1].strip("/")
            suffix = parts[2].lstrip("/")
            
            # Pattern like "**/venv/**"
            if not prefix and not suffix:
                # Must have a directory named exactly 'middle' as a complete path segment
                path_segments = normalized_path.split("/")
                
                # Check if the middle part appears as a complete path segment
                for segment in path_segments:
                    if fnmatch.fnmatch(segment, middle):
                        # Found the middle segment, now check if there's content after it
                        segment_index = path_segments.index(segment)
                        if segment_index < len(path_segments) - 1:
                            # There are more segments after the middle one
                            return True
                
                return False
            else:
                # More complex pattern like "prefix/**/middle/**/suffix"
                # For now, fall back to a conservative approach
                return self._fallback_pattern_match(normalized_path, parts)
        
        # For more complex patterns with multiple **, use fallback
        else:
            return self._fallback_pattern_match(normalized_path, parts)
    
    def _fallback_pattern_match(self, path: str, pattern_parts: list) -> bool:
        """Fallback pattern matching for complex ** patterns."""
        # Extract meaningful parts (non-empty after cleaning)
        meaningful_parts = []
        for part in pattern_parts:
            clean_part = part.strip("/")
            if clean_part:
                meaningful_parts.append(clean_part)
        
        if not meaningful_parts:
            return True
        
        # Check if all meaningful parts appear in order in the path
        path_lower = path.lower()
        last_index = -1
        
        for part in meaningful_parts:
            # For each part, find it in the path after the last found position
            if "*" in part:
                # Use fnmatch for parts with wildcards
                segments = path.split("/")
                found = False
                for i, segment in enumerate(segments):
                    if i > last_index and fnmatch.fnmatch(segment.lower(), part.lower()):
                        last_index = i
                        found = True
                        break
                if not found:
                    return False
            else:
                # Simple substring search for exact parts
                index = path_lower.find(part.lower(), last_index + 1)
                if index == -1:
                    return False
                last_index = index
        
        return True
    
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
    
    def to_mcp_config_dict(self, enable_all_detectors: bool = True, available_detectors: List[str] = None) -> Dict[str, Any]:
        """
        Convert Settings object to MCP-compatible configuration dictionary.
        
        Args:
            enable_all_detectors: Whether to enable all available detectors by default
            available_detectors: List of available detector IDs
            
        Returns:
            Configuration dictionary compatible with MCP tools
        """
        config = {
            # Global ignore patterns from Settings
            "ignore": self.ignored_paths,
            
            # Performance settings (MCP-specific defaults)
            "performance": {
                "cache_enabled": True,
                "parallel": True,
                "cache_ttl_hours": 24,
                "max_workers": 4
            },
            
            # MCP-specific limits
            "mcp": {
                "max_files_to_analyze": 1000
            },
            
            # Convert detector settings to config format
            "detectors": {},
            
            # Thresholds from Settings
            "thresholds": self.thresholds,
            
            # Severity overrides from Settings
            "severity": self.severity_overrides,
            
            # Suppression patterns from Settings
            "suppression": {
                "patterns": self.suppression_patterns,
                "enable_builtin_suppressions": self.enable_builtin_suppressions
            },
            
            # Output limits from Settings
            "output": self.output_limits
        }
        
        # Enable detectors based on settings or enable all if requested
        if available_detectors:
            for detector_id in available_detectors:
                detector_settings = self.detector_settings.get(detector_id, DetectorSettings())
                config["detectors"][detector_id] = {
                    "enabled": detector_settings.enabled if not enable_all_detectors else True,
                    "cache_enabled": True  # MCP default
                }
                
                # Add detector-specific options
                if detector_settings.options:
                    config["detectors"][detector_id].update(detector_settings.options)
                
                # Add severity override if set
                if detector_settings.severity_override:
                    config["detectors"][detector_id]["severity"] = detector_settings.severity_override
        
        return config

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
        # User-provided ignore patterns replace defaults completely
        if "ignore" in config:
            settings.ignored_paths = list(config["ignore"])
        elif "ignored_paths" in config:
            settings.ignored_paths = list(config["ignored_paths"])
        
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
    
    @classmethod
    def create_with_intelligent_defaults(cls, project_root: Path = None) -> "Settings":
        """
        Create Settings with intelligent configuration loading:
        1. Start with hardcoded defaults
        2. If .gitignore exists, replace ignore paths with gitignore values
        3. If .pythonium.yml exists, merge with config (values replace, not extend)
        
        Args:
            project_root: Path to project root. If None, uses current working directory.
            
        Returns:
            Settings instance with intelligent defaults
        """
        if project_root is None:
            project_root = Path.cwd()
        
        # Step 1: Start with hardcoded defaults
        settings = cls()
        
        # Step 2: If .gitignore exists, replace ignore paths with gitignore values
        gitignore_path = project_root / ".gitignore"
        if gitignore_path.exists():
            gitignore_patterns = cls._load_gitignore_patterns(gitignore_path)
            if gitignore_patterns:
                # Replace defaults with gitignore patterns
                settings.ignored_paths = gitignore_patterns
        
        # Step 3: If .pythonium.yml exists, merge with config
        pythonium_config_path = project_root / ".pythonium.yml"
        if pythonium_config_path.exists():
            try:
                import yaml
                with open(pythonium_config_path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)
                
                if config_dict:
                    # Merge configuration (values replace, not extend)
                    settings = cls._merge_settings(settings, config_dict)
            except Exception as e:
                # If config loading fails, continue with current settings
                print(f"Warning: Failed to load .pythonium.yml: {e}")
        
        return settings
    
    @staticmethod
    def _load_gitignore_patterns(gitignore_path: Path) -> List[str]:
        """
        Load ignore patterns from .gitignore file.
        
        Args:
            gitignore_path: Path to .gitignore file
            
        Returns:
            List of ignore patterns adapted for Pythonium
        """
        patterns = []
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Skip negation patterns (!) for now
                    if line.startswith('!'):
                        continue
                    
                    # Convert gitignore patterns to glob patterns
                    if line.endswith('/'):
                        # Directory pattern
                        patterns.append(f"**/{line}**")
                        patterns.append(f"**/{line.rstrip('/')}/**")
                    elif '/' in line:
                        # Path-specific pattern
                        if line.startswith('/'):
                            # Root-relative pattern
                            patterns.append(line.lstrip('/'))
                        else:
                            # Can appear anywhere
                            patterns.append(f"**/{line}")
                    else:
                        # File/directory name pattern
                        patterns.append(f"**/{line}")
                        patterns.append(f"**/{line}/**")
        
        except Exception as e:
            print(f"Warning: Failed to load .gitignore: {e}")
        
        return patterns
    
    @classmethod 
    def _merge_settings(cls, base_settings: "Settings", config_dict: Dict[str, Any]) -> "Settings":
        """
        Merge configuration dictionary into settings (values replace, not extend).
        
        Args:
            base_settings: Base settings to merge into
            config_dict: Configuration dictionary to merge
            
        Returns:
            New Settings instance with merged configuration
        """
        # Use the existing from_dict method but start with base settings
        # Create a new settings instance to avoid modifying the original
        import copy
        merged_settings = copy.deepcopy(base_settings)
        
        # Parse detector settings
        detectors_config = config_dict.get("detectors", {})
        for detector_id, detector_config in detectors_config.items():
            if isinstance(detector_config, bool):
                merged_settings.detector_settings[detector_id] = DetectorSettings(enabled=detector_config)
            elif isinstance(detector_config, dict):
                enabled = detector_config.get("enabled", True)
                severity_override = detector_config.get("severity")
                options = {k: v for k, v in detector_config.items() 
                          if k not in ("enabled", "severity")}
                
                merged_settings.detector_settings[detector_id] = DetectorSettings(
                    enabled=enabled,
                    severity_override=severity_override,
                    options=options
                )
        
        # Parse ignored paths - REPLACE, not extend
        if "ignore" in config_dict:
            merged_settings.ignored_paths = list(config_dict["ignore"])
        elif "ignored_paths" in config_dict:
            merged_settings.ignored_paths = list(config_dict["ignored_paths"])
        
        # Parse severity overrides - REPLACE, not extend
        if "severity" in config_dict:
            merged_settings.severity_overrides = dict(config_dict["severity"])
        
        # Parse thresholds - REPLACE specific values, not extend
        if "thresholds" in config_dict:
            for key, value in config_dict["thresholds"].items():
                merged_settings.thresholds[key] = value
        
        # Parse detector options
        if "options" in config_dict:
            options_config = config_dict["options"]
            for detector_id, options in options_config.items():
                if detector_id not in merged_settings.detector_settings:
                    merged_settings.detector_settings[detector_id] = DetectorSettings()
                # REPLACE options, not extend
                merged_settings.detector_settings[detector_id].options = dict(options)
            
        # Parse suppression patterns - REPLACE, not extend
        if "suppression" in config_dict:
            suppression_config = config_dict["suppression"]
            if "patterns" in suppression_config:
                merged_settings.suppression_patterns = dict(suppression_config["patterns"])
            if "enable_builtin_suppressions" in suppression_config:
                merged_settings.enable_builtin_suppressions = suppression_config["enable_builtin_suppressions"]
                
        # Parse output limits - REPLACE specific values, not extend
        if "output" in config_dict:
            for key, value in config_dict["output"].items():
                merged_settings.output_limits[key] = value
        
        return merged_settings
