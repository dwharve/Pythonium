"""
Configuration documentation tools for the Pythonium MCP server.
Contains methods for providing configuration schema documentation.
"""

from typing import Any, Dict, List

import mcp.types as types


async def get_configuration_schema(server, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Get comprehensive configuration schema documentation."""
    section = arguments.get("section", "overview")
    
    if section == "overview":
        return await get_schema_overview(server)
    elif section == "detectors":
        return await get_detector_configurations(server)
    elif section == "global":
        return await get_global_configurations(server)
    elif section == "examples":
        return await get_configuration_examples(server)
    elif section == "precedence":
        return await get_configuration_precedence(server)
    elif section == "validation":
        return await get_configuration_validation(server)
    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown configuration section: {section}. Available sections: overview, detectors, global, examples, precedence, validation"
        )]


async def get_schema_overview(server) -> List[types.TextContent]:
    """Get complete configuration schema overview."""
    from pythonium.settings import Settings
    
    # Get actual defaults from Settings
    default_settings = Settings()
    sample_thresholds = {k: v for k, v in list(default_settings.thresholds.items())[:3]}
    sample_patterns = default_settings.ignored_paths[:3]
    
    output_lines = [
        "Pythonium Configuration Schema",
        "=" * 35,
        "",
        "Pythonium uses intelligent configuration loading with this hierarchy:",
        "1. Hardcoded defaults → 2. .gitignore patterns → 3. .pythonium.yml overrides",
        "",
        "MAIN CONFIGURATION SECTIONS:",
        "",
        "1. DETECTORS - Per-detector configuration and options",
        "   • Enable/disable specific detectors",
        "   • Configure detector-specific thresholds and behavior",
        "   • Set detector-specific severity overrides",
        "",
        "2. GLOBAL SETTINGS - Project-wide configuration",
        "   • severity: Override default severity levels",
        "   • ignore: Global ignore patterns for files/directories",
        "   • thresholds: Common threshold values",
        "   • suppression: Pattern-based issue suppression",
        "   • output: Output formatting and limits",
        "",
        "CURRENT DEFAULTS (from Settings class):",
        f"• Default ignore patterns: {len(default_settings.ignored_paths)} patterns",
        f"  Examples: {sample_patterns}",
        f"• Default thresholds: {len(default_settings.thresholds)} thresholds",
        f"  Examples: {sample_thresholds}",
        f"• Output limits: max_issues_per_detector={default_settings.output_limits.get('max_issues_per_detector', 50)}",
        "",
        "CONFIGURATION STRUCTURE:",
        "",
        "```yaml",
        "# Basic structure of .pythonium.yml",
        "detectors:",
        "  detector_name:",
        "    enabled: true|false",
        "    options: detector_specific_values",
        "",
        "ignore:  # Replaces all default patterns",
        "  - \"**/custom/**\"",
        "",
        "thresholds:  # Merges with defaults",
        "  complexity_cyclomatic: 8",
        "",
        "severity:  # Global overrides",
        "  detector_name: error|warn|info",
        "```",
        "",
        "INTELLIGENT CONFIGURATION LOADING:",
        "• If .gitignore exists: ignore patterns replaced with gitignore",
        "• If .pythonium.yml exists: configuration merged (replaces, not extends)",
        "• Values always replace previous settings, ensuring predictable behavior",
        "",
        f"AVAILABLE DETECTORS: {len(server.available_detectors)}",
        f"Detector IDs: {', '.join(sorted(server.available_detectors))}"
    ]
    
    return [types.TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def get_detector_configurations(server) -> List[types.TextContent]:
    """Get detailed detector configuration options."""
    output_lines = [
        "Detector Configuration Options",
        "=" * 30,
        "",
        "Each detector can be configured with specific options in the .pythonium.yml file.",
        "All detector settings use replacement semantics (values replace, don't extend).",
        "",
        "COMMON DETECTOR CONFIGURATION:",
        "```yaml",
        "detectors:",
        "  detector_name:",
        "    enabled: true                 # Enable/disable this detector",
        "    options:                      # Detector-specific options",
        "      threshold_name: value",
        "```",
        "",
        "AVAILABLE DETECTORS WITH ACTUAL INFO:",
        ""
    ]
    
    # Add documentation for each actual detector
    for detector_id in sorted(server.available_detectors[:5]):  # Show first 5 to avoid too much output
        detector_info = server._detector_info.get(detector_id, {})
        output_lines.extend([
            f"{detector_id.upper()}:",
            f"  Description: {detector_info.get('description', 'No description available')}",
            f"  Category: {detector_info.get('category', 'Code Analysis')}",
            f"  Typical severity: {detector_info.get('typical_severity', 'warn')}",
            "  Configuration:",
            "  ```yaml",
            "  detectors:",
            f"    {detector_id}:",
            "      enabled: true",
        ])
        
        # Add detector-specific realistic options
        if "complexity" in detector_id:
            from pythonium.settings import Settings
            default_settings = Settings()
            complexity_threshold = default_settings.thresholds.get('complexity_cyclomatic', 8)
            output_lines.extend([
                "      options:",
                f"        max_complexity: {complexity_threshold}",
            ])
        elif "clone" in detector_id:
            from pythonium.settings import Settings
            default_settings = Settings()
            similarity = default_settings.thresholds.get('clone_similarity', 0.85)
            min_lines = default_settings.thresholds.get('clone_min_lines', 4)
            output_lines.extend([
                "      options:",
                f"        similarity_threshold: {similarity}",
                f"        min_lines: {min_lines}",
            ])
        elif "dead_code" in detector_id:
            output_lines.extend([
                "      options:",
                "        ignore_private: false",
                "        ignore_test_files: true",
            ])
        
        output_lines.extend(["  ```", ""])
    
    if len(server.available_detectors) > 5:
        output_lines.extend([
            f"... and {len(server.available_detectors) - 5} more detectors.",
            "Use 'get_detector_info <detector_id>' for specific detector details.",
            ""
        ])
    
    output_lines.extend([
        "CENTRALIZED CONFIGURATION:",
        "• All default values come from the Settings class",
        "• Settings.create_with_intelligent_defaults() loads configuration",
        "• Use 'list_detectors' to see all available detectors",
        "• Use 'get_detector_info' for detailed detector information"
    ])
    
    return [types.TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def get_global_configurations(server) -> List[types.TextContent]:
    """Get global configuration options documentation."""
    from pythonium.settings import Settings
    
    # Get actual defaults from Settings
    default_settings = Settings()
    
    output_lines = [
        "Global Configuration Options",
        "=" * 30,
        "",
        "Global settings apply across all detectors and analysis runs.",
        "These settings use intelligent configuration loading with replacement semantics.",
        "",
        "CURRENT DEFAULTS (from centralized Settings):",
        f"• Ignore patterns: {len(default_settings.ignored_paths)} patterns",
        f"• Thresholds: {len(default_settings.thresholds)} configured",
        f"• Output limits: {default_settings.output_limits}",
        "",
        "```yaml",
        "# Example .pythonium.yml configuration",
        "# Note: ignore patterns REPLACE defaults completely",
        "ignore:",
        f"  - \"{default_settings.ignored_paths[0]}\"  # Example from defaults",
        f"  - \"{default_settings.ignored_paths[1]}\"  # Example from defaults", 
        "  - \"**/custom/**\"                    # Your custom patterns",
        "",
        "# Threshold values MERGE with defaults",
        "thresholds:",
        f"  complexity_cyclomatic: {default_settings.thresholds.get('complexity_cyclomatic', 8)}",
        f"  clone_similarity: {default_settings.thresholds.get('clone_similarity', 0.85)}",
        f"  high_fanin: {default_settings.thresholds.get('high_fanin', 15)}",
        "",
        "# Detector severity overrides",
        "severity:",
        "  dead_code: error",
        "  security_smell: error",
        "  complexity_hotspot: warn",
        "",
        "# Output configuration",
        "output:",
        f"  max_issues_per_detector: {default_settings.output_limits.get('max_issues_per_detector', 50)}",
        f"  enable_deduplication: {default_settings.output_limits.get('enable_deduplication', True)}",
        f"  min_confidence: {default_settings.output_limits.get('min_confidence', 0.2)}",
        "```",
        "",
        "INTELLIGENT CONFIGURATION HIERARCHY:",
        "1. Settings class provides hardcoded defaults",
        "2. .gitignore replaces ignore patterns (if exists)",
        "3. .pythonium.yml merges configuration (replaces specific values)",
        "",
        "KEY FEATURES:",
        "• Ignore patterns: Complete replacement at each level",
        "• Thresholds: Individual value replacement",
        "• Detector settings: Complete replacement per detector",
        "• Suppression patterns: Complete replacement",
        ""
    ]
    
    return [types.TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def get_configuration_examples(server) -> List[types.TextContent]:
    """Get practical configuration examples using actual Settings defaults."""
    from pythonium.settings import Settings
    
    # Get actual defaults to show realistic examples
    default_settings = Settings()
    
    output_lines = [
        "Configuration Examples",
        "=" * 20,
        "",
        "All examples use the intelligent configuration system with replacement semantics.",
        "",
        "BASIC CONFIGURATION (.pythonium.yml):",
        "```yaml",
        "# Enable only specific detectors",
        "detectors:",
        "  dead_code:",
        "    enabled: true",
        "  security_smell:",
        "    enabled: true",
        "  complexity_hotspot:",
        "    enabled: false",
        "",
        "# Override just a few ignore patterns (replaces all defaults)",
        "ignore:",
        "  - \"**/tests/**\"",
        "  - \"**/__pycache__/**\"",
        "  - \"**/node_modules/**\"",
        "```",
        "",
        "USING GITIGNORE + OVERRIDES:",
        "```yaml",
        "# Let .gitignore handle most ignore patterns",
        "# Only override specific settings",
        "detectors:",
        "  security_smell:",
        "    enabled: true",
        "",
        "thresholds:",
        f"  complexity_cyclomatic: {default_settings.thresholds.get('complexity_cyclomatic', 8)}",
        f"  clone_similarity: {default_settings.thresholds.get('clone_similarity', 0.85)}",
        "",
        "severity:",
        "  dead_code: error",
        "```",
        "",
        "LIBRARY/PACKAGE CONFIGURATION:",
        "```yaml",
        "# Strict quality standards",
        "detectors:",
        "  dead_code:",
        "    enabled: true",
        "  clone:",
        "    enabled: true",
        "  security_smell:",
        "    enabled: true",
        "",
        "# Custom ignore patterns for library",
        "ignore:",
        f"  - \"{default_settings.ignored_paths[0]}\"  # Keep some defaults",
        f"  - \"{default_settings.ignored_paths[1]}\"",
        "  - \"**/examples/**\"          # Library-specific",
        "  - \"**/docs/**\"",
        "",
        "# Stricter thresholds",
        "thresholds:",
        "  complexity_cyclomatic: 6     # Stricter than default",
        f"  clone_similarity: {min(0.95, default_settings.thresholds.get('clone_similarity', 0.85) + 0.1)}",
        "",
        "output:",
        "  max_issues_per_detector: 100",
        "  enable_deduplication: true",
        "```",
        "",
        "EXISTING CODEBASE (GRADUAL IMPROVEMENT):",
        "```yaml",
        "# More tolerant settings for existing code",
        "detectors:",
        "  security_smell:",
        "    enabled: true    # Security is always important",
        "  dead_code:",
        "    enabled: true",
        "  complexity_hotspot:",
        "    enabled: true",
        "",
        "# More permissive thresholds",
        "thresholds:",
        "  complexity_cyclomatic: 15   # More lenient",
        f"  high_fanin: {default_settings.thresholds.get('high_fanin', 15) + 5}",
        "",
        "# Manageable output",
        "output:",
        "  max_issues_per_detector: 20",
        "```",
        "",
        "NOTES:",
        f"• Default settings provide {len(default_settings.ignored_paths)} ignore patterns",
        f"• Default thresholds: {len(default_settings.thresholds)} preconfigured values",
        "• Use Settings.create_with_intelligent_defaults() in code",
        "• Ignore patterns always replace completely (no merging)"
    ]
    
    return [types.TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def get_configuration_precedence(server) -> List[types.TextContent]:
    """Get configuration precedence documentation."""
    output_lines = [
        "Configuration Precedence & Hierarchy",
        "=" * 35,
        "",
        "Pythonium uses intelligent configuration loading with REPLACEMENT semantics:",
        "",
        "1. HARDCODED DEFAULTS (Settings class)",
        "   • Built into the Settings class",
        "   • 24 default ignore patterns (venv, __pycache__, tests, etc.)",
        "   • Optimized thresholds for common use cases",
        "   • Standard suppression patterns",
        "",
        "2. GITIGNORE REPLACEMENT (if .gitignore exists)",
        "   • REPLACES all default ignore patterns",
        "   • Converts gitignore syntax to glob patterns",
        "   • Maintains project-specific ignore logic",
        "",
        "3. PYTHONIUM.YML OVERRIDE (if .pythonium.yml exists)",
        "   • REPLACES values from previous steps",
        "   • Individual settings replace completely (no merging)",
        "   • Ignore patterns: complete replacement",
        "   • Thresholds: individual value replacement",
        "",
        "4. MCP TOOL PARAMETERS (highest priority)",
        "   • Runtime configuration overrides",
        "   • Tool-specific detector selection",
        "   • Temporary analysis configuration",
        "",
        "REPLACEMENT BEHAVIOR EXAMPLES:",
        "",
        "Default: 24 ignore patterns from Settings",
        "↓",
        "With .gitignore: Replaced with gitignore patterns (e.g., 112 patterns)",
        "↓",
        "With .pythonium.yml ignore section: Replaced with yml patterns (e.g., 12 patterns)",
        "",
        "IMPLEMENTATION:",
        "```python",
        "# This is how the system works internally:",
        "settings = Settings()  # Hardcoded defaults",
        "if gitignore_exists:",
        "    settings.ignored_paths = load_gitignore_patterns()",
        "if pythonium_yml_exists:",
        "    settings = merge_settings(settings, yml_config)  # Replacement",
        "```",
        "",
        "BEST PRACTICES:",
        "• Use .gitignore for file ignore patterns when possible",
        "• Use .pythonium.yml only for detector-specific overrides",
        "• Remember: ignore patterns are replaced, not merged",
        "• Test configuration with list_detectors and debug tools"
    ]
    
    return [types.TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def get_configuration_validation(server) -> List[types.TextContent]:
    """Get configuration validation documentation."""
    output_lines = [
        "Configuration Validation",
        "=" * 25,
        "",
        "Pythonium validates configuration files to prevent common errors and misconfigurations.",
        "",
        "VALIDATION RULES:",
        "",
        "1. SCHEMA VALIDATION",
        "   • All configuration keys must be recognized",
        "   • Values must match expected types",
        "   • Required fields must be present",
        "",
        "2. DETECTOR VALIDATION",
        "   • Detector names must exist in available detectors",
        "   • Detector-specific options must be valid",
        "   • Severity levels must be: error, warn, or info",
        "",
        "3. PATH VALIDATION",
        "   • Ignore patterns must use valid glob syntax",
        "   • File paths must be relative to project root",
        "   • Circular dependencies in configuration not allowed",
        "",
        "4. VALUE RANGE VALIDATION",
        "   • Thresholds must be within valid ranges",
        "   • Similarity values must be between 0.0 and 1.0",
        "   • Complexity limits must be positive integers",
        "",
        "COMMON VALIDATION ERRORS:",
        "",
        "Invalid detector name:",
        "```yaml",
        "detectors:",
        "  invalid_detector:  # ERROR: Unknown detector",
        "    enabled: true",
        "```",
        "",
        "Invalid severity level:",
        "```yaml",
        "severity:",
        "  dead_code: critical  # ERROR: Must be error|warn|info",
        "```",
        "",
        "Invalid threshold:",
        "```yaml",
        "thresholds:",
        "  similarity_threshold: 1.5  # ERROR: Must be 0.0-1.0",
        "```",
        "",
        "Invalid ignore pattern:",
        "```yaml",
        "ignore:",
        "  - \"[invalid\"  # ERROR: Invalid glob pattern",
        "```",
        "",
        "VALID CONFIGURATION:",
        "```yaml",
        "detectors:",
        "  dead_code:",
        "    enabled: true",
        "    severity: error",
        "    ignore_private: false",
        "",
        "severity:",
        "  complexity_hotspot: warn",
        "",
        "thresholds:",
        "  similarity_threshold: 0.8",
        "  complexity_threshold: 10",
        "",
        "ignore:",
        "  - \"**/test/**\"",
        "  - \"build/**\"",
        "```",
        "",
        "VALIDATION PROCESS:",
        "1. Parse YAML syntax",
        "2. Validate against schema",
        "3. Check detector existence",
        "4. Validate value ranges",
        "5. Test ignore patterns",
        "6. Report all errors with suggestions",
        "",
        "GETTING HELP:",
        "• Use 'analyze_code' with invalid config to see validation errors",
        "• Check the debug log for detailed validation messages",
        "• Use 'get_configuration_schema examples' for working examples"
    ]
    
    return [types.TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


# =============================================================================
# Configuration Utilities (merged from config_utilities.py)
# =============================================================================

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.debug import logger, warning_log


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
