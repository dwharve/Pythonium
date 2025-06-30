#!/usr/bin/env python3
"""
CLI module for Pythonium.
"""

import asyncio
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

__version__ = importlib.metadata.version("pythonium")

from .common.logging import get_logger, setup_logging
from .mcp.server import MCPServer

console = Console()
logger = get_logger(__name__)


def print_banner():
    """Print the Pythonium banner."""
    banner = f"""
╔═══════════════════════════════════════╗
║             PYTHONIUM v{__version__:<10}         ║
║      Modular MCP Server for AI        ║
╚═══════════════════════════════════════╝
"""
    console.print(banner, style="bold blue")


@click.group()
@click.version_option(__version__, prog_name="Pythonium")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Logging level",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def main(ctx, config: Optional[Path], log_level: str, verbose: bool):
    """Pythonium - A modular MCP server for AI agents."""
    ctx.ensure_object(dict)

    # Setup logging
    setup_logging(level=log_level, verbose=verbose)

    # Store configuration path
    ctx.obj["config_path"] = config
    ctx.obj["log_level"] = log_level
    ctx.obj["verbose"] = verbose

    if verbose:
        print_banner()


@main.command()
@click.option("--host", default="localhost", help="Server host address")
@click.option("--port", default=8080, help="Server port number")
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "http", "websocket"]),
    help="Transport protocol",
)
@click.option(
    "--workers",
    default=1,
    help="Number of worker processes",
)
@click.pass_context
def serve(ctx, host: str, port: int, transport: str, workers: int):
    """Start the MCP server."""
    config_path = ctx.obj.get("config_path")
    log_level = ctx.obj.get("log_level", "INFO")

    # Set up logging first
    setup_logging(level=log_level)

    logger.info(f"Starting Pythonium MCP Server v{__version__}")
    logger.info(f"Transport: {transport}")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")

    try:
        # Create transport configuration overrides
        transport_config_overrides = {
            "transport": {"type": transport, "host": host, "port": port}
        }

        # Create and start server with config overrides
        server = MCPServer(
            config_file=config_path,
            config_overrides=transport_config_overrides,
        )

        # Use the generic run method
        asyncio.run(server.run())

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


@main.command("configure-aixterm")
@click.option(
    "--aixterm-config",
    type=click.Path(path_type=Path),
    help="Path to aixterm configuration file (default: ~/.aixterm)",
)
@click.option(
    "--python-path",
    help="Python executable path for pythonium (auto-detected if not provided)",
)
@click.option(
    "--pythonium-path",
    help="Path to pythonium module (auto-detected if not provided)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be configured without making changes",
)
@click.pass_context
def configure_aixterm(
    ctx,
    aixterm_config: Optional[Path],
    python_path: Optional[str],
    pythonium_path: Optional[str],
    dry_run: bool,
):
    """Configure aixterm to use pythonium as an MCP server."""
    logger.info("Configuring aixterm to use pythonium...")

    # Determine aixterm config path - aixterm uses ~/.aixterm by default
    if not aixterm_config:
        aixterm_config = Path.home() / ".aixterm"

    # Auto-detect python path
    if not python_path:
        python_path = sys.executable
        logger.debug(f"Auto-detected Python path: {python_path}")

    # Auto-detect pythonium path
    if not pythonium_path:
        try:
            # Try to find pythonium module
            import pythonium

            pythonium_path = str(Path(pythonium.__file__).parent.parent)
            logger.debug(f"Auto-detected pythonium path: {pythonium_path}")
        except ImportError:
            # Try to find it via command line
            try:
                result = subprocess.run(
                    [python_path, "-c", "import pythonium; print(pythonium.__file__)"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                pythonium_file = result.stdout.strip()
                pythonium_path = str(Path(pythonium_file).parent.parent)
                logger.debug(f"Found pythonium via subprocess: {pythonium_path}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("Could not auto-detect pythonium path. Please specify --pythonium-path")
                sys.exit(1)

    # Build MCP server configuration
    pythonium_mcp_config = {
        "name": "pythonium",
        "command": [python_path, "-m", "pythonium", "serve"],
        "args": ["--transport", "stdio"],
        "cwd": str(Path.home()),
        "auto_start": True,
        "description": "Pythonium MCP server for Python code analysis and execution",
    }

    # Check if aixterm config exists, if not, initialize it first
    if not aixterm_config.exists():
        logger.info(f"AIxTerm config not found at {aixterm_config}, initializing...")
        try:
            # Run aixterm --init-config to create the default config
            result = subprocess.run(
                ["aixterm", "--init-config"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug(f"aixterm --init-config output: {result.stdout}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to initialize aixterm config: {e}")
            sys.exit(1)

    # Load existing aixterm config
    aixterm_config_data = {}
    try:
        with open(aixterm_config, "r") as f:
            aixterm_config_data = json.load(f)
        logger.debug(f"Loaded existing aixterm config from {aixterm_config}")
    except Exception as e:
        logger.error(f"Could not load aixterm config: {e}")
        sys.exit(1)

    # Update configuration
    if "mcp_servers" not in aixterm_config_data:
        aixterm_config_data["mcp_servers"] = []

    # Remove any existing pythonium server config
    aixterm_config_data["mcp_servers"] = [
        server
        for server in aixterm_config_data["mcp_servers"]
        if server.get("name") != "pythonium"
    ]

    # Add new pythonium server config
    aixterm_config_data["mcp_servers"].append(pythonium_mcp_config)

    if dry_run:
        console.print(
            "[bold yellow]DRY RUN - Configuration that would be written:[/bold yellow]"
        )
        console.print(json.dumps(aixterm_config_data, indent=2))
        console.print(f"\n[bold blue]Config file path:[/bold blue] {aixterm_config}")
        return

    # Write configuration
    try:
        # Create backup if file exists
        if aixterm_config.exists():
            backup_path = aixterm_config.with_suffix(".backup")
            shutil.copy2(aixterm_config, backup_path)
            logger.debug(f"Created backup at {backup_path}")

        # Write new configuration
        with open(aixterm_config, "w") as f:
            json.dump(aixterm_config_data, f, indent=2)

        console.print("[bold green]Pythonium MCP server configured for aixterm")

    except Exception as e:
        logger.error(f"Failed to write configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
