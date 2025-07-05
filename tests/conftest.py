"""
Base test utilities and classes for the Pythonium test suite.

This module provides common test utilities, fixtures, and base classes
used across all test modules in the Pythonium project.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    from pythonium.core.tools import ToolRegistry

    registry = Mock(spec=ToolRegistry)
    registry.get_all_tools = Mock(return_value=[])
    registry.get_tool = Mock(return_value=None)
    registry.register_tool = Mock()
    registry.unregister_tool = Mock()

    return registry


@pytest.fixture
def temporary_config_file():
    """Create a temporary configuration file for testing."""
    import json

    config_data = {
        "server": {
            "name": "test-server",
            "version": "1.0.0",
            "description": "Test server",
        },
        "transport": {"type": "stdio", "timeout": 30},
        "security": {"enabled": True, "max_request_size": 1024000},
        "logging": {"level": "INFO"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        yield f.name

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Create a performance monitor for testing."""

    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.start_times = {}

        def start_timer(self, name: str):
            import time

            self.start_times[name] = time.perf_counter()

        def end_timer(self, name: str):
            import time

            if name in self.start_times:
                duration = time.perf_counter() - self.start_times[name]
                self.metrics[name] = duration
                del self.start_times[name]
                return duration
            return None

        def get_metric(self, name: str):
            return self.metrics.get(name)

        def get_memory_usage(self):
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB

    return PerformanceMonitor()


# Mark decorators for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow


# Test data utilities
class TestDataManager:
    """Manages test data files and resources."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)

    def get_test_file(self, filename: str) -> Path:
        """Get path to test data file."""
        return self.data_dir / filename

    def create_test_file(self, filename: str, content: str) -> Path:
        """Create a test data file."""
        file_path = self.data_dir / filename
        file_path.write_text(content)
        return file_path

    def cleanup(self):
        """Clean up test data files."""
        import shutil

        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)


@pytest.fixture
def test_data_manager():
    """Create a test data manager."""
    data_dir = Path(tempfile.mkdtemp())
    manager = TestDataManager(data_dir)
    yield manager
    manager.cleanup()


class TestConfig(BaseModel):
    """Test configuration model."""

    test_data_dir: Path = Path(__file__).parent / "data"
    temp_dir: Optional[Path] = None
    log_level: str = "DEBUG"
    timeout: int = 30


class BaseTestCase:
    """Base test case class with common utilities."""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Set up test environment."""
        self.test_config = TestConfig()

    def create_mock_manager(self, manager_class: type) -> Mock:
        """Create a mock manager instance."""
        mock_manager = Mock(spec=manager_class)
        mock_manager.name = manager_class.__name__.lower()
        mock_manager.initialize = AsyncMock()
        mock_manager.shutdown = AsyncMock()
        mock_manager.health_check = AsyncMock(return_value=True)
        return mock_manager

    def create_mock_tool(self, tool_class: type) -> Mock:
        """Create a mock tool instance."""
        mock_tool = Mock(spec=tool_class)
        mock_tool.name = tool_class.__name__.lower()
        mock_tool.description = f"Mock {tool_class.__name__}"
        mock_tool.execute = AsyncMock()
        return mock_tool


class AsyncTestCase(BaseTestCase):
    """Base test case for async functionality."""

    @pytest.fixture(autouse=True)
    def setup_async_test(self):
        """Set up async test environment."""
        super().setup_test()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def teardown_method(self):
        """Clean up after async tests."""
        if hasattr(self, "loop") and self.loop:
            self.loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config() -> TestConfig:
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture
def mock_logger():
    """Provide a mock logger."""
    return Mock()


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Provide sample configuration data."""
    return {
        "server": {"host": "localhost", "port": 8080, "transport": "stdio"},
        "tools": {"categories": ["filesystem", "network", "system"]},
        "logging": {"level": "INFO", "format": "structured"},
    }


async def wait_for_condition(
    condition_func, timeout: float = 5.0, interval: float = 0.1
):
    """Wait for a condition to become true."""
    start_time = asyncio.get_event_loop().time()
    while True:
        if (
            await condition_func()
            if asyncio.iscoroutinefunction(condition_func)
            else condition_func()
        ):
            return True

        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Condition not met within {timeout} seconds")

        await asyncio.sleep(interval)


class MockAsyncContext:
    """Mock async context manager for testing."""

    def __init__(self, return_value=None):
        self.return_value = return_value
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.return_value

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        self.exited = True
        return False


def assert_valid_response(response: Dict[str, Any], expected_keys: list):
    """Assert that a response has the expected structure."""
    assert isinstance(response, dict)
    for key in expected_keys:
        assert key in response
    assert "error" not in response or response["error"] is None


def assert_error_response(response: Dict[str, Any], expected_error_type: str = None):
    """Assert that a response contains an error."""
    assert isinstance(response, dict)
    assert "error" in response
    assert response["error"] is not None
    if expected_error_type:
        assert expected_error_type in str(response["error"]).lower()
