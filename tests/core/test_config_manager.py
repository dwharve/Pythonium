import os
from pathlib import Path

import pytest

from pythonium.common.config import AuthenticationMethod, TransportType
from pythonium.core.config import (
    ConfigurationManager,
    get_config_manager,
    set_config_manager,
)


class TestConfigurationManager:
    def test_overrides_and_get(self, tmp_path):
        overrides = {
            "server": {
                "host": "127.0.0.1",
                "port": 9999,
            },
            "security": {
                "authentication_method": AuthenticationMethod.NONE.value,
            },
        }
        cm = ConfigurationManager(config_overrides=overrides)
        assert cm.get_settings().server.host == "127.0.0.1"
        assert cm.get("server.port") == 9999
        assert cm.get("security.authentication_method") == AuthenticationMethod.NONE
        assert cm.get("nonexistent", "default") == "default"

        # write to file and reload
        config_file = tmp_path / "config.json"
        cm.get_settings().save_to_file(config_file)
        cm.reload_config(config_file)
        assert cm.get_settings().server.port == 9999

    def test_validate_config_issues(self):
        overrides = {
            "server": {
                "transport": TransportType.HTTP.value,
                "host": "",
            },
            "security": {
                "authentication_method": AuthenticationMethod.API_KEY.value,
                "api_keys": [],
            },
        }
        cm = ConfigurationManager(config_overrides=overrides)
        issues = cm.validate_config()
        assert any("Host" in issue for issue in issues)
        assert any("API keys" in issue for issue in issues)
        assert cm.is_debug_mode() is False
        assert cm.are_experimental_features_enabled() is False

    def test_convenience_and_globals(self):
        cm = ConfigurationManager(
            config_overrides={
                "server": {
                    "transport": TransportType.HTTP.value,
                    "host": "x",
                    "port": 80,
                }
            }
        )
        assert cm.get_server_config().transport == TransportType.HTTP
        assert cm.get_security_config() is cm.get_settings().security
        assert cm.get_logging_config() is cm.get_settings().logging
        assert cm.get_tool_config() is cm.get_settings().tools
        set_config_manager(cm)
        assert get_config_manager() is cm
