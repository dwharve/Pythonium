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

    @patch("pythonium.main.main")
    def test_main_entrypoint_execution(self, mock_main):
        """Test that __main__.py calls main() when executed."""
        # Import the __main__ module which should trigger main() call
        import importlib.util
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "__main__", repo_root / "pythonium" / "__main__.py"
        )
        module = importlib.util.module_from_spec(spec)

        # Set __name__ to simulate running as main
        module.__name__ = "__main__"

        with patch.dict(sys.modules, {"__main__": module}):
            spec.loader.exec_module(module)

        # Verify main was called
        mock_main.assert_called_once()

    def test_module_execution_via_python_m(self):
        """Test running the module via python -m pythonium."""
        # Test that the module can be executed via python -m
        # This will test the actual __main__.py functionality
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "pythonium", "--help"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        # Should exit successfully and show help
        assert result.returncode == 0
        assert "Pythonium" in result.stdout
        assert "modular MCP server" in result.stdout
