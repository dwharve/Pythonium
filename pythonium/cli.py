"""Command-line interface for the Pythonium Crawler."""

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, DefaultDict
from collections import defaultdict

import click
import yaml

from .analyzer import Analyzer
from .models import Issue
from .version import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path: Optional[Path] = None, auto_create: bool = True) -> dict:
    """Load configuration from a YAML file.
    
    Args:
        config_path: Path to the config file. If None, looks for .pythonium.yml in the current directory.
        auto_create: Whether to automatically create a default config file if none exists.
        
    Returns:
        Dictionary containing the configuration
    """
    if config_path is None:
        # Look for config in common locations
        config_path = Path.cwd() / ".pythonium.yml"
        if not config_path.exists():
            if auto_create:
                logger.info("No config file found, creating default: %s", config_path)
                try:
                    create_default_config(config_path)
                except Exception as e:
                    logger.warning("Failed to create default config: %s", e)
                    return {}
            else:
                return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load config from %s: %s", config_path, str(e))
        return {}

def format_issue(issue: Issue) -> str:
    """Format an issue for console output."""
    location = issue.location or (issue.symbol.location if issue.symbol else None)
    
    if location:
        loc_str = f"{location.file}:{location.line}"
        if location.column:
            loc_str += f":{location.column}"
    else:
        loc_str = "<unknown location>"
    
    symbol_name = issue.symbol.fqname if issue.symbol else ""
    
    return f"{loc_str}: {issue.severity.upper()}: {issue.message} ({symbol_name})"

@click.group()
@click.version_option(version=__version__)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output."
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to config file."
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[Path]) -> None:
    """Pythonium Crawler - A static analysis tool for Python code health metrics."""
    # Set log level
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger().setLevel(log_level)
    
    # Load config
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)

@cli.command()
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
    required=False
)
@click.option(
    "--format",
    type=click.Choice(["text", "json", "sarif", "html"], case_sensitive=False),
    default="text",
    help="Output format."
)
@click.option(
    "--output", "-o",
    type=click.Path(writable=True, dir_okay=False, path_type=Path),
    help="Output file. If not specified, writes to stdout."
)
@click.option(
    "--fail-on",
    type=click.Choice(["never", "error", "warn"], case_sensitive=False),
    default="error",
    help="Exit with non-zero status if issues of this severity or higher are found."
)
@click.option(
    "--silent", "-s",
    is_flag=True,
    help="Silent mode - only output issues, no progress messages."
)
@click.option(
    "--detectors", "-d",
    help="Comma-separated list of detector IDs to run. Available: dead_code, clone, inconsistent_api, alt_implementation, circular_deps, complexity_hotspot, security_smell, deprecated_api, block_clone, semantic_equivalence, advanced_patterns."
)
@click.pass_context
def crawl(
    ctx: click.Context,
    paths: List[Path],
    format: str,
    output: Optional[Path],
    fail_on: str,
    silent: bool,
    detectors: Optional[str]
) -> None:
    """Analyze Python source files for code health issues."""
    config = ctx.obj["config"]
    
    # Handle silent mode - disable progress logging
    if silent:
        # Set logging level to WARNING to suppress INFO messages
        logging.getLogger().setLevel(logging.WARNING)
        # Also disable logging for the analyzer and related modules
        logging.getLogger("pythonium").setLevel(logging.WARNING)
    
    # Handle detector filtering
    if detectors:
        # Parse detector list
        detector_list = [d.strip() for d in detectors.split(",")]
        
        # Configure only specified detectors in config
        if "detectors" not in config:
            config["detectors"] = {}
        
        # Available detector IDs (based on actual detector ids)
        available_detectors = [
            "dead_code", "clone", "inconsistent_api", "alt_implementation", 
            "circular_deps", "complexity_hotspot", "security_smell", 
            "deprecated_api", "block_clone", "semantic_equivalence", 
            "advanced_patterns"
        ]
        
        # Disable all detectors first, then enable only specified ones
        for detector_id in available_detectors:
            config["detectors"][detector_id] = {"enabled": False}
        
        # Enable specified detectors
        for detector_id in detector_list:
            if detector_id not in available_detectors:
                if not silent:
                    logger.warning("Unknown detector: %s. Available detectors: %s", 
                                  detector_id, ", ".join(available_detectors))
                continue
            config["detectors"][detector_id] = {"enabled": True}
    
    # Use current directory if no paths provided
    if not paths:
        paths = [Path.cwd()]
    
    # Determine root path (first path if it's a directory, otherwise its parent)
    root_path = paths[0]
    if not root_path.is_dir():
        root_path = root_path.parent
    
    # Initialize analyzer
    analyzer = Analyzer(root_path=root_path, config=config)
    
    # Run analysis
    issues = analyzer.analyze(paths)
    
    # Filter issues by severity for exit code
    severity_levels = {"info": 0, "warn": 1, "error": 2}
    min_severity = severity_levels.get(fail_on, 2)
    fail_issues = [
        issue for issue in issues
        if severity_levels.get(issue.severity.lower(), 0) >= min_severity
    ]
    
    # Output results (show all issues)
    output_file = sys.stdout if output is None else open(output, 'w', encoding='utf-8')
    
    try:
        if format == "json":
            # Convert issues to JSON-serializable format
            issues_data = []
            for issue in issues:  # Show all issues, not just filtered ones
                issue_data = {
                    "id": issue.id,
                    "severity": issue.severity,
                    "message": issue.message,
                    "metadata": issue.metadata,
                }
                
                if issue.location:
                    issue_data["location"] = {
                        "file": str(issue.location.file),
                        "line": issue.location.line,
                        "column": issue.location.column,
                    }
                
                if issue.symbol:
                    issue_data["symbol"] = issue.symbol.fqname
                
                issues_data.append(issue_data)
            
            json.dump(issues_data, output_file, indent=2)
            output_file.write("\n")
        elif format == "sarif":
            # Convert issues to SARIF format
            sarif_report = _create_sarif_report(issues, root_path)  # Show all issues
            json.dump(sarif_report, output_file, indent=2)
            output_file.write("\n")
        elif format == "html":
            # Generate HTML dashboard
            from .dashboard import generate_html_report
            if output is None:
                output = Path("pythonium-report.html")
            generate_html_report(issues, output, root_path)  # Show all issues
            print(f"HTML report generated: {output}")
            return  # Don't close output_file since we wrote directly
        else:
            # Text format
            for issue in issues:  # Show all issues
                print(format_issue(issue), file=output_file)
            
            if not silent:
                print(f"\nFound {len(issues)} issues", file=output_file)
    finally:
        if output_file is not sys.stdout:
            output_file.close()
    
    # Exit with appropriate status code based on filtered issues
    if fail_issues:
        ctx.exit(1)

# Add version command
@cli.command()
def version() -> None:
    """Show the version and exit."""
    click.echo(f"Pythonium Crawler v{__version__}")

# List available detectors
@cli.command("list-detectors")
@click.pass_context
def list_detectors(ctx: click.Context) -> None:
    """List all available detectors."""
    config = ctx.obj["config"]
    
    # Create analyzer to load detectors
    analyzer = Analyzer(root_path=Path.cwd(), config=config)
    
    # Load detectors
    analyzer.load_detectors_from_entry_points()
    if not analyzer.detectors:
        analyzer.load_default_detectors()
    
    # Get detector metadata
    detectors_info = analyzer.list_detectors()
    
    if not detectors_info:
        click.echo("No detectors found.")
        return
    
    # Display detectors
    click.echo("Available detectors:")
    click.echo()
    
    for detector_id, info in sorted(detectors_info.items()):
        status = f"[{info['type']}]"
        click.echo(f"  {detector_id:<20} {status:<8} {info['name']}")
        if info['description']:
            # Wrap description at 60 chars
            desc_lines = []
            words = info['description'].split()
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= 60:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        desc_lines.append(current_line)
                    current_line = word
            if current_line:
                desc_lines.append(current_line)
            
            for line in desc_lines:
                click.echo(f"    {line}")
        click.echo()

# SARIF report creation
def _create_sarif_report(issues: List[Issue], root_path: Path) -> dict:
    """Create a SARIF (Static Analysis Results Interchange Format) report."""
    from .version import __version__
    
    # Group issues by detector
    issues_by_detector: DefaultDict[str, List[Issue]] = defaultdict(list)
    for issue in issues:
        detector_id = issue.detector_id or "unknown"
        issues_by_detector[detector_id].append(issue)
    
    # Create SARIF rules for each detector
    rules = []
    results = []
    
    for detector_id, detector_issues in issues_by_detector.items():
        if not detector_issues:
            continue
        
        # Get detector info from first issue
        first_issue = detector_issues[0]
        detector_name = first_issue.metadata.get("detector_name", detector_id)
        detector_description = first_issue.metadata.get("detector_description", "")
        
        # Create rule
        rule = {
            "id": detector_id,
            "name": detector_name,
            "shortDescription": {"text": detector_name},
            "fullDescription": {"text": detector_description},
            "defaultConfiguration": {"level": "warning"},
            "helpUri": f"https://github.com/dwharve/pythonium/docs/{detector_id}"
        }
        rules.append(rule)
        
        # Create results for this detector
        for issue in detector_issues:
            result = {
                "ruleId": detector_id,
                "ruleIndex": len(rules) - 1,
                "message": {"text": issue.message},
                "level": _map_severity_to_sarif(issue.severity)
            }
            
            # Add location if available
            if issue.location:
                try:
                    # Make path relative to root
                    relative_path = issue.location.file.relative_to(root_path)
                    result["locations"] = [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": str(relative_path)},
                            "region": {
                                "startLine": issue.location.line,
                                "startColumn": issue.location.column or 1,
                            }
                        }
                    }]
                    
                    if issue.location.end_line:
                        result["locations"][0]["physicalLocation"]["region"]["endLine"] = issue.location.end_line
                    if issue.location.end_column:
                        result["locations"][0]["physicalLocation"]["region"]["endColumn"] = issue.location.end_column
                        
                except ValueError:
                    # Path is not relative to root, use absolute
                    result["locations"] = [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": str(issue.location.file)},
                            "region": {
                                "startLine": issue.location.line,
                                "startColumn": issue.location.column or 1,
                            }
                        }
                    }]
            
            # Add additional metadata as properties
            if issue.metadata:
                properties = {}
                for key, value in issue.metadata.items():
                    if key not in ["detector_name", "detector_description"]:
                        properties[key] = value
                if properties:
                    result["properties"] = properties
            
            results.append(result)
    
    # Create the full SARIF report
    sarif_report = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "pythonium",
                    "version": __version__,
                    "informationUri": "https://github.com/dwharve/pythonium",
                    "rules": rules
                }
            },
            "results": results,
            "columnKind": "utf16CodeUnits"
        }]
    }
    
    return sarif_report


def _map_severity_to_sarif(severity: str) -> str:
    """Map internal severity levels to SARIF levels."""
    mapping = {
        "error": "error",
        "warn": "warning", 
        "warning": "warning",
        "info": "note"
    }
    return mapping.get(severity.lower(), "warning")


# Main entry point
def main() -> None:
    """Entry point for the CLI."""
    try:
        cli(obj={})
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)
        sys.exit(1)

@cli.command("mcp-server")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"], case_sensitive=False),
    default="stdio",
    help="Transport protocol to use (stdio or sse)."
)
@click.option(
    "--host",
    default="localhost",
    help="Host for SSE transport (default: localhost)."
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port for SSE transport (default: 8000)."
)
@click.pass_context
def mcp_server(ctx: click.Context, transport: str, host: str, port: int) -> None:
    """Start the Model Context Protocol (MCP) server for LLM agent integration."""
    from .mcp_server import PythoniumMCPServer
    
    import asyncio
    
    async def run_server():
        server = PythoniumMCPServer()
        if transport.lower() == "stdio":
            click.echo("Starting MCP server with stdio transport...", err=True)
            await server.run_stdio()
        else:
            click.echo(f"Starting MCP server with SSE transport on {host}:{port}...", err=True)
            await server.run_sse(host, port)
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        click.echo("\nMCP server stopped.", err=True)
    except Exception as e:
        click.echo(f"Error running MCP server: {e}", err=True)
        ctx.exit(1)

def create_default_config(config_path: Optional[Path] = None) -> Path:
    """
    Create a default .pythonium.yml configuration file.
    
    Args:
        config_path: Path where to create the config file. If None, creates in current directory.
        
    Returns:
        Path to the created config file
    """
    if config_path is None:
        config_path = Path.cwd() / ".pythonium.yml"
    
    default_config = """# Pythonium Crawler Configuration - Optimized Defaults
# See https://github.com/dwharve/pythonium for full documentation
# This configuration uses optimized settings for better detection coverage and performance

# Performance settings
performance:
  cache_enabled: true          # Enable caching for faster analysis
  parallel: true               # Run detectors in parallel
  cache_ttl_hours: 24         # Cache time-to-live in hours
  max_workers: 4              # Number of parallel workers

# Enable/disable specific detectors with optimized configuration
detectors:
  dead_code:
    enabled: true
    entry_points:              # Expanded entry points list
      - "main"
      - "run"
      - "start"
      - "app"
      - "create_app"
      - "wsgi_app"
      - "application"
      - "__main__"
    cache_enabled: true
  
  clone:
    enabled: true
    similarity_threshold: 0.85    # Reduced from 0.9 - better coverage
    min_code_length: 4           # Reduced from 5 - catch smaller clones
    exact_mode: false            # Enable near-clone detection
    enhanced_semantic: true      # Enable enhanced semantic detection
    cache_enabled: true
  
  inconsistent_api:
    enabled: true
    min_functions: 3
    check_parameter_order: true
    check_naming_patterns: true
    check_return_patterns: true
    cache_enabled: true
  
  alt_implementation:
    enabled: true
    min_similarity: 0.8          # Slightly increased for better precision
    min_functions: 2
    cache_enabled: true
  
  circular_deps:
    enabled: true
    max_cycle_length: 8          # Reduced from 10 - focus on shorter cycles
    high_fanin_threshold: 15     # Reduced from 20 - catch high dependencies
    cache_enabled: true
  
  complexity_hotspot:
    enabled: true
    cyclomatic_threshold: 8      # Reduced from 10 - catch complexity earlier
    loc_threshold: 45            # Reduced from 50 - encourage smaller functions
    halstead_difficulty_threshold: 18.0  # Reduced for better detection
    cache_enabled: true
  
  security_smell:
    enabled: true
    check_hardcoded_credentials: true
    check_weak_crypto: true
    check_dangerous_functions: true
    check_sql_injection: true
    check_command_injection: true
    check_insecure_random: true
    cache_enabled: true

  block_clone:
    enabled: true
    min_statements: 3
    max_statements: 25           # Increased from 20 - analyze larger blocks
    similarity_threshold: 0.88   # Slightly relaxed for better coverage
    ignore_variable_names: true
    ignore_string_literals: true
    ignore_numeric_literals: true
    cross_function_only: false   # Detect within and across functions
    cache_enabled: true
    
  semantic_equivalence:
    enabled: true
    detect_builtin_equivalents: true
    detect_control_flow_equivalents: true
    detect_algorithmic_patterns: true
    similarity_threshold: 0.85   # Optimized threshold
    cache_enabled: true
    
  advanced_patterns:
    enabled: true
    detect_algorithmic_patterns: true
    detect_design_patterns: true
    detect_validation_patterns: true
    detect_factory_patterns: true
    min_pattern_size: 3
    similarity_threshold: 0.8    # Optimized threshold
    max_lines: 50
    cache_enabled: true
  
  deprecated_api:
    enabled: true
    python_version: "3.9"        # Adjust based on your target version
    ignore_external: false
    check_patterns: true
    cache_enabled: true
    
  stub_implementation:
    enabled: true
    check_hardcoded_returns: true
    check_empty_implementations: true
    check_placeholder_patterns: true
    cache_enabled: true

# Set optimized severity levels (based on analysis impact)
severity:
  dead_code: "warn"
  clone: "warn"                  # Changed from error - less disruptive
  inconsistent_api: "warn"
  alt_implementation: "info"
  circular_deps: "error"         # Critical architectural issue
  complexity_hotspot: "warn"     # Changed from info - more important
  security_smell: "error"        # Critical security issue
  deprecated_api: "warn"
  block_clone: "warn"            # Changed from error - block clones are significant but not critical
  semantic_equivalence: "info"   # Suggestions for improvement
  advanced_patterns: "info"      # Refactoring suggestions
  stub_implementation: "info"    # Development indicators

# Global ignore patterns (applied to all detectors)
ignore:
  - "**/tests/**"          # Test directories
  - "**/test_*.py"         # Test files
  - "**/*_test.py"         # Test files
  - "**/migrations/**"     # Database migrations
  - "**/venv/**"           # Virtual environments
  - "**/__pycache__/**"    # Python cache
  - "**/node_modules/**"   # Node.js dependencies
  - "**/dist/**"           # Build artifacts
  - "**/build/**"          # Build artifacts
  - "**/.git/**"           # Git repository
  - "**/.tox/**"           # Tox environments
  - ".pythonium/"          # Pythonium data directory (includes cache.db and issues.db)
"""
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(default_config)
        logger.info("Created default configuration file: %s", config_path)
        return config_path
    except Exception as e:
        logger.error("Failed to create config file %s: %s", config_path, e)
        raise


@cli.command("init-config")
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Overwrite existing config file if it exists."
)
@click.option(
    "--output", "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path for config file (default: .pythonium.yml in current directory)."
)
def init_config(force: bool, output: Optional[Path]) -> None:
    """Create a default .pythonium.yml configuration file."""
    config_path = output or Path.cwd() / ".pythonium.yml"
    
    if config_path.exists() and not force:
        click.echo(f"Config file already exists: {config_path}")
        click.echo("Use --force to overwrite it.")
        return
    
    try:
        created_path = create_default_config(config_path)
        click.echo(f"Created configuration file: {created_path}")
        click.echo("Edit the file to customize detector settings and thresholds.")
    except Exception as e:
        click.echo(f"Error creating config file: {e}", err=True)
        raise click.Abort()

def get_or_create_config(root_path: Path, auto_create: bool = True) -> dict:
    """Get configuration for a project, creating default config if needed.
    
    Args:
        root_path: Root directory of the project to analyze
        auto_create: Whether to automatically create a default config file if none exists
        
    Returns:
        Dictionary containing the configuration
    """
    config_path = root_path / ".pythonium.yml"
    
    # Check if config file exists, create if not
    if not config_path.exists() and auto_create:
        logger.info("No config file found, creating default: %s", config_path)
        try:
            create_default_config(config_path)
        except Exception as e:
            logger.warning("Failed to create default config: %s", e)
            return {}
    
    # Load the config from the project root
    return load_config(config_path, auto_create=False)

def find_project_root(start_path: Path) -> Path:
    """Find the project root directory by looking for common project indicators.
    
    Args:
        start_path: Path to start searching from (file or directory)
        
    Returns:
        Path to the project root, or the start_path's parent if no indicators found
    """
    # Convert to absolute path and resolve
    start_path = start_path.resolve()
    
    # If start_path is a file, start from its directory
    if start_path.is_file():
        current_path = start_path.parent
    else:
        current_path = start_path
    
    # Common project root indicators
    root_indicators = [
        'pyproject.toml',
        'setup.py',
        'setup.cfg',
        'requirements.txt',
        'Pipfile',
        'poetry.lock',
        '.git',
        '.gitignore',
        'package.json',
        'Cargo.toml',
        'go.mod'
    ]
    
    # Search up the directory tree
    while current_path != current_path.parent:  # Not at filesystem root
        # Check if any project indicators exist in current directory
        for indicator in root_indicators:
            if (current_path / indicator).exists():
                return current_path
        current_path = current_path.parent
    
    # If no project root found, use the original directory
    return start_path.parent if start_path.is_file() else start_path
