import logging
from pythonium.mcp.tools import configuration


def test_validate_detectors():
    available = ["a", "b"]
    assert configuration.validate_detectors(["a", "x"], available) == ["a"]
    assert configuration.validate_detectors([], available) == []


def test_merge_configs_and_configure_detectors():
    default = {"ignore": ["*.py"], "thresholds": {"t": 1}}
    user = {"ignore": ["test"], "thresholds": {"t": 2}, "extra": True}
    merged = configuration.merge_configs(default, user)
    assert merged["ignore"] == ["test"]  # replaced
    assert merged["thresholds"]["t"] == 2
    assert merged["extra"] is True

    result = configuration.configure_detectors(merged, ["a"], ["a", "b"])
    assert result["detectors"]["a"]["enabled"] is True
    assert result["detectors"]["b"]["enabled"] is False


def test_configure_analyzer_logging(monkeypatch):
    logger = logging.getLogger("pythonium.analyzer")
    for h in logger.handlers[:]:
        logger.removeHandler(h)

    configuration.configure_analyzer_logging(True)
    assert logger.level == logging.INFO
    configuration.configure_analyzer_logging(False)
    assert logger.level == logging.WARNING
