"""
Configuration utilities for the Pythonium MCP server.
Contains helper methods for configuration processing and validation.
"""

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .debug import logger, warning_log


def validate_detectors(detector_ids: List[str], available_detectors: List[str]) -> List[str]:
    """Validate detector IDs against available detectors."""
    if not detector_ids:
        return []
    
    valid_detectors = [d for d in detector_ids if d in available_detectors]
    
    if not valid_detectors:
        logger.warning("No valid detectors from: %s. Available: %s", 
                      detector_ids, ", ".join(available_detectors))
    
    return valid_detectors


def get_default_config_dict(available_detectors: List[str]) -> Dict[str, Any]:
    """Get default configuration as a dictionary using Settings class with intelligent defaults."""
    from pythonium.settings import Settings
    from pythonium.cli import find_project_root
    
    # Find project root for intelligent configuration loading
    project_root = find_project_root(Path.cwd())
    
    # Create settings with intelligent defaults (hardcoded -> gitignore -> .pythonium.yml)
    settings = Settings.create_with_intelligent_defaults(project_root)
    
    # Convert to MCP config format
    return settings.to_mcp_config_dict(
        enable_all_detectors=True, 
        available_detectors=available_detectors
    )


def merge_configs(default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge user configuration with default configuration, with user config taking precedence."""
    # Deep copy the default config to avoid modifying the original
    merged = copy.deepcopy(default_config)
    
    def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively merge source into target."""
        for key, value in source.items():
            if key == "ignore" and isinstance(value, list):
                # Special handling for ignore patterns - replace instead of merge
                # This allows users to completely override default ignore patterns
                target[key] = list(value)
            elif key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge(target[key], value)
            else:
                target[key] = value
    
    deep_merge(merged, user_config)
    return merged


def configure_detectors(config: Dict[str, Any], detector_ids: Optional[List[str]], available_detectors: List[str]) -> Dict[str, Any]:
    """Configure detectors in config based on detector IDs."""
    if not detector_ids:
        return config
    
    valid_detector_ids = validate_detectors(detector_ids, available_detectors)
    if not valid_detector_ids:
        return config
    
    if "detectors" not in config:
        config["detectors"] = {}
    
    # Disable all detectors first, then enable specified ones
    for detector_id in available_detectors:
        config["detectors"][detector_id] = {"enabled": False}
    
    for detector_id in valid_detector_ids:
        config["detectors"][detector_id] = {"enabled": True}
    
    return config


def configure_analyzer_logging(debug: bool) -> None:
    """Configure logging for the analyzer module to respect debug mode."""
    analyzer_logger = logging.getLogger("pythonium.analyzer")
    
    # Remove existing handlers to avoid duplicates
    for handler in analyzer_logger.handlers[:]:
        analyzer_logger.removeHandler(handler)
    
    if debug:
        # In debug mode, allow INFO level and above
        analyzer_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        analyzer_logger.addHandler(console_handler)
    else:
        # In normal mode, only WARNING level and above
        analyzer_logger.setLevel(logging.WARNING)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        analyzer_logger.addHandler(console_handler)
    
    # Prevent propagation to root logger to avoid duplicate messages
    analyzer_logger.propagate = False
