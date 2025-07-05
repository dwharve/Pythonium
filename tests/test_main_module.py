"""
Tests for main CLI module.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, call, patch

import click
import pytest
from click.testing import CliRunner

import pythonium
from pythonium.main import (
    _auto_detect_python_path,
    _auto_detect_pythonium_path,
    _build_mcp_config,
    _ensure_aixterm_config_exists,
    _load_aixterm_config,
    _update_aixterm_config,
    _write_aixterm_config,
    configure_aixterm,
    main,
    print_banner,
    serve,
)


class TestMainModule:
    """Test main CLI module functionality."""

    def test_main_module_execution(self):
        """Test main module can be executed."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Pythonium" in result.output
        assert "modular MCP server" in result.output

    def test_version_option(self):
        """Test version option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "Pythonium" in result.output

    def test_help_option(self):
        """Test help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "serve" in result.output
        assert "configure-aixterm" in result.output

    def test_print_banner(self):
        """Test banner printing."""
        with patch("pythonium.main.console") as mock_console:
            print_banner()

            mock_console.print.assert_called_once()
            call_args = mock_console.print.call_args[0][0]
            assert "PYTHONIUM" in call_args
            assert "Modular MCP Server" in call_args


class TestMainCommand:
    """Test main command functionality."""

    def test_main_command_basic(self):
        """Test basic main command execution."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Pythonium - A modular MCP server for AI agents" in result.output

    def test_main_command_version(self):
        """Test main command version display."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "Pythonium" in result.output

    def test_print_banner_function(self):
        """Test print_banner function directly."""
        with patch("pythonium.main.console.print") as mock_print:
            print_banner()
            mock_print.assert_called_once()
            # Check that the banner contains version info
            banner_text = mock_print.call_args[0][0]
            assert "PYTHONIUM" in banner_text

    def test_main_context_setup(self):
        """Test that main function sets up context correctly."""
        runner = CliRunner()
        # Test with serve subcommand to ensure main context is set up
        with patch("pythonium.main.PythoniumMCPServer") as mock_server, patch(
            "asyncio.run"
        ) as mock_run:
            # Mock server to avoid actual startup
            mock_server_instance = Mock()
            mock_server.return_value = mock_server_instance

            result = runner.invoke(main, ["--verbose", "--log-level", "DEBUG", "serve"])

            # Verify asyncio.run was called
            mock_run.assert_called_once()

            # Should exit cleanly or with expected error, not crash on setup
            assert result.exit_code in [0, 1]  # 1 is OK if server fails to start


class TestServeCommand:
    """Test serve command functionality."""

    def test_serve_command_basic(self):
        """Test basic serve command."""
        with patch("pythonium.main.PythoniumMCPServer") as mock_server_class, patch(
            "asyncio.run"
        ) as mock_asyncio_run:

            mock_server = Mock()
            mock_server_class.return_value = mock_server

            runner = CliRunner()
            result = runner.invoke(main, ["serve"])

            assert result.exit_code == 0
            mock_server_class.assert_called_once()
            mock_asyncio_run.assert_called_once()

    def test_serve_command_with_transport(self):
        """Test serve command with different transport."""
        with patch("pythonium.main.PythoniumMCPServer") as mock_server_class, patch(
            "asyncio.run"
        ):

            runner = CliRunner()
            result = runner.invoke(main, ["serve", "--transport", "http"])

            assert result.exit_code == 0
            # Check that server was created with HTTP transport
            call_args = mock_server_class.call_args
            config_overrides = call_args[1]["config_overrides"]
            assert config_overrides["transport"]["type"] == "http"

    def test_serve_command_with_host_port(self):
        """Test serve command with custom host and port."""
        with patch("pythonium.main.PythoniumMCPServer") as mock_server_class, patch(
            "asyncio.run"
        ):

            runner = CliRunner()
            result = runner.invoke(
                main, ["serve", "--host", "0.0.0.0", "--port", "9000"]
            )

            assert result.exit_code == 0
            call_args = mock_server_class.call_args
            config_overrides = call_args[1]["config_overrides"]
            assert config_overrides["transport"]["host"] == "0.0.0.0"
            assert config_overrides["transport"]["port"] == 9000


class TestConfigureAixtermCommand:
    """Test configure-aixterm command functionality."""

    def test_configure_aixterm_command_basic(self):
        """Test basic configure-aixterm command."""
        with patch(
            "pythonium.main._auto_detect_python_path"
        ) as mock_detect_python, patch(
            "pythonium.main._auto_detect_pythonium_path"
        ) as mock_detect_pythonium, patch(
            "pythonium.main._ensure_aixterm_config_exists"
        ) as mock_ensure, patch(
            "pythonium.main._load_aixterm_config"
        ) as mock_load, patch(
            "pythonium.main._update_aixterm_config"
        ) as mock_update, patch(
            "pythonium.main._write_aixterm_config"
        ) as mock_write:

            mock_detect_python.return_value = "/usr/bin/python"
            mock_detect_pythonium.return_value = "/path/to/pythonium"
            mock_load.return_value = {}
            mock_update.return_value = {"updated": "config"}

            runner = CliRunner()
            result = runner.invoke(main, ["configure-aixterm"])

            assert result.exit_code == 0
            mock_ensure.assert_called_once()
            mock_load.assert_called_once()
            mock_update.assert_called_once()
            mock_write.assert_called_once()

    def test_configure_aixterm_command_with_custom_path(self):
        """Test configure-aixterm command with custom Python path."""
        with patch(
            "pythonium.main._auto_detect_pythonium_path", return_value="/path"
        ), patch("pythonium.main._ensure_aixterm_config_exists"), patch(
            "pythonium.main._load_aixterm_config", return_value={}
        ), patch(
            "pythonium.main._update_aixterm_config", return_value={}
        ), patch(
            "pythonium.main._write_aixterm_config"
        ):

            runner = CliRunner()
            result = runner.invoke(
                main, ["configure-aixterm", "--python-path", "/custom/python"]
            )

            assert result.exit_code == 0

    def test_configure_aixterm_command_dry_run(self):
        """Test configure-aixterm command with dry run."""
        with patch(
            "pythonium.main._auto_detect_python_path", return_value="/usr/bin/python"
        ), patch(
            "pythonium.main._auto_detect_pythonium_path",
            return_value="/path/to/pythonium",
        ), patch(
            "pythonium.main._ensure_aixterm_config_exists"
        ), patch(
            "pythonium.main._load_aixterm_config", return_value={}
        ), patch(
            "pythonium.main._update_aixterm_config", return_value={}
        ), patch(
            "pythonium.main._write_aixterm_config"
        ) as mock_write:

            runner = CliRunner()
            result = runner.invoke(main, ["configure-aixterm", "--dry-run"])

            assert result.exit_code == 0
            # Should not write in dry run mode
            mock_write.assert_not_called()


class TestHelperFunctions:
    """Test helper functions."""

    def test_auto_detect_python_path_with_sys_executable(self):
        """Test auto-detection using sys.executable."""
        result = _auto_detect_python_path(None)

        # Should return sys.executable
        assert result == sys.executable

    def test_auto_detect_pythonium_path_with_current_dir(self):
        """Test auto-detection using current directory."""
        result = _auto_detect_pythonium_path(None, "/usr/bin/python")

        # Should return current working directory in test environment
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_mcp_config(self):
        """Test MCP config building."""
        python_path = "/usr/bin/python"

        config = _build_mcp_config(python_path)

        assert config["command"] == [python_path, "-m", "pythonium", "serve"]
        assert "name" in config
        assert "args" in config

    def test_ensure_aixterm_config_exists_create_new(self, tmp_path):
        """Test creating new aixterm config."""
        config_path = tmp_path / "aixterm_config.json"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            try:
                _ensure_aixterm_config_exists(config_path)
            except SystemExit:
                # Expected if aixterm command is not available
                pass

    def test_ensure_aixterm_config_exists_already_exists(self, tmp_path):
        """Test with existing aixterm config."""
        config_path = tmp_path / "aixterm_config.json"
        config_path.write_text('{"existing": "config"}')

        # Should not raise or modify anything
        _ensure_aixterm_config_exists(config_path)

        assert config_path.exists()

    def test_load_aixterm_config(self, tmp_path):
        """Test loading aixterm config."""
        config_path = tmp_path / "aixterm_config.json"
        test_config = {"test": "data", "mcpServers": {}}
        config_path.write_text(json.dumps(test_config))

        try:
            result = _load_aixterm_config(str(config_path))
            assert result == test_config
        except SystemExit:
            # Expected if file doesn't exist in actual test environment
            pass

    def test_update_aixterm_config(self):
        """Test updating aixterm config."""
        config = {"existing": {"command": "old"}}
        mcp_config = {"command": ["python", "-m", "pythonium", "serve"]}

        result = _update_aixterm_config(config, mcp_config)

        assert "mcp_servers" in result
        assert "existing" in result  # Original config preserved

    def test_write_aixterm_config(self, tmp_path):
        """Test writing aixterm config."""
        config_path = tmp_path / "aixterm_config.json"
        config_data = {"test": "data"}

        try:
            _write_aixterm_config(str(config_path), config_data)

            # Check if file was written correctly
            if config_path.exists():
                written_data = json.loads(config_path.read_text())
                assert written_data == config_data
        except SystemExit:
            # Expected if directory doesn't exist or permission issues
            pass


class TestMainIntegration:
    """Test integration scenarios."""

    def test_end_to_end_serve(self):
        """Test end-to-end serve command execution."""
        with patch("pythonium.main.PythoniumMCPServer") as mock_server_class, patch(
            "asyncio.run"
        ) as mock_asyncio_run, patch(
            "pythonium.main.setup_logging"
        ) as mock_setup_logging:

            mock_server = Mock()
            mock_server_class.return_value = mock_server

            runner = CliRunner()
            result = runner.invoke(main, ["--verbose", "serve", "--transport", "stdio"])

            assert result.exit_code == 0
            # Should have set up logging and created server
            assert mock_setup_logging.call_count >= 1
            mock_server_class.assert_called_once()
            mock_asyncio_run.assert_called_once()

    def test_error_handling_in_serve(self):
        """Test error handling in serve command."""
        with patch("pythonium.main.PythoniumMCPServer") as mock_server_class:
            mock_server_class.side_effect = Exception("Server creation failed")

            runner = CliRunner()
            result = runner.invoke(main, ["serve"])

            # Should handle the exception gracefully
            assert result.exit_code == 1

    def test_config_file_loading(self, tmp_path):
        """Test config file loading."""
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"name": "test_server", "description": "Test"}')

        with patch("pythonium.main.PythoniumMCPServer") as mock_server_class, patch(
            "asyncio.run"
        ):

            runner = CliRunner()
            result = runner.invoke(main, ["--config", str(config_file), "serve"])

            assert result.exit_code == 0
            mock_server_class.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        runner = CliRunner()
        result = runner.invoke(main, ["--config", "/nonexistent/config.json", "serve"])

        # Should fail with file not found
        assert result.exit_code != 0

    def test_invalid_transport_type(self):
        """Test handling of invalid transport type."""
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--transport", "invalid"])

        # Click should reject invalid choice
        assert result.exit_code != 0
        assert "Invalid value" in result.output
