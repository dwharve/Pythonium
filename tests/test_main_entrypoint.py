"""
Tests for __main__.py entry point.
"""

import subprocess
import sys
from unittest.mock import patch

import pytest


class TestMainEntrypoint:
    """Test __main__.py entry point functionality."""

    def test_main_entrypoint_import(self):
        """Test that __main__.py can be imported without error."""
        # This test ensures the module can be imported
        import pythonium.__main__  # noqa: F401

    def test_module_execution_via_python_m(self):
        """Test running the module via python -m pythonium."""
        # Test that the module can be executed via python -m
        # This will test the actual __main__.py functionality
        result = subprocess.run(
            [sys.executable, "-m", "pythonium", "--help"],
            capture_output=True,
            text=True
        )

        # Should exit successfully and show help
        assert result.returncode == 0
        assert "Pythonium" in result.stdout
        assert "modular MCP server" in result.stdout
