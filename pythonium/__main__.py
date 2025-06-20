"""
Pythonium - Main module entry point.

This module provides the command-line entry point for Pythonium
when it's run as a module (python -m pythonium).

The main functionality is delegated to the CLI module which provides the
full command-line interface with argument parsing and subcommands.

Usage:
    python -m pythonium [options] [path]
    python -m pythonium --help
"""

from .cli import main

if __name__ == "__main__":
    main()
