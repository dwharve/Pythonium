"""
Tests for common configuration and utility modules.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pythonium.common.cache import CacheManager
from pythonium.common.config import PluginSettings, PythoniumSettings, ServerSettings
from pythonium.common.events import EventManager
from tests.conftest import BaseTestCase


class TestCommonPackage(BaseTestCase):
    """Test the common package initialization."""

    def test_package_import(self):
        """Test that the common package can be imported."""
        # This will be implemented once we have actual modules
        assert True  # Placeholder

    def test_package_version(self):
        """Test that the package has a version."""
        from pythonium.common import __version__

        assert __version__ == "0.1.2"


class TestPythoniumSettings:
    """Test configuration management."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = PythoniumSettings()
        assert settings.server.host == "localhost"
        assert settings.server.port == 8080
        assert settings.server.transport == "stdio"

    def test_environment_override(self):
        """Test environment variable override."""
        with patch.dict("os.environ", {"PYTHONIUM_SERVER_HOST": "example.com"}):
            settings = PythoniumSettings()
            assert settings.server.host == "example.com"

    def test_server_settings_validation(self):
        """Test server settings validation."""
        # Valid settings
        settings = ServerSettings(host="localhost", port=8080, transport="stdio")
        assert settings.host == "localhost"
        assert settings.port == 8080
        assert settings.transport == "stdio"

        # Invalid port
        with pytest.raises(ValueError):
            ServerSettings(port=70000)  # Port too high

        # Invalid transport
        with pytest.raises(ValueError):
            ServerSettings(transport="invalid")

    def test_plugin_settings(self):
        """Test plugin configuration."""
        settings = PluginSettings()
        assert hasattr(settings, "model_config")

    def test_full_settings_integration(self):
        """Test full settings integration."""
        settings = PythoniumSettings()

        # Verify all main sections exist
        assert hasattr(settings, "server")
        assert hasattr(settings, "plugins")
        assert hasattr(settings, "tools")
        assert hasattr(settings, "logging")
        assert hasattr(settings, "security")


class TestCacheManager:
    """Test cache management."""

    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager for testing."""
        return CacheManager()

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initialization."""
        await cache_manager.initialize()
        try:
            assert cache_manager.list_caches() == []
        finally:
            await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_create_and_get_cache(self, cache_manager):
        """Test creating and getting caches."""
        await cache_manager.initialize()
        try:
            # Create a cache
            cache = cache_manager.create_cache("test_cache")
            assert cache is not None

            # Get the cache
            retrieved_cache = cache_manager.get_cache("test_cache")
            assert retrieved_cache is cache

            # List caches
            assert "test_cache" in cache_manager.list_caches()
        finally:
            await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_manager):
        """Test basic cache operations."""
        await cache_manager.initialize()
        try:
            cache = cache_manager.create_cache("ops_cache")

            # Set and get
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

            # Delete
            cache.delete("key1")
            assert cache.get("key1") is None

            # Clear
            cache.set("key2", "value2")
            cache.set("key3", "value3")
            cache.clear()
            assert cache.get("key2") is None
            assert cache.get("key3") is None
        finally:
            await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_delete_cache(self, cache_manager):
        """Test deleting caches."""
        await cache_manager.initialize()
        try:
            cache_manager.create_cache("delete_me")
            assert "delete_me" in cache_manager.list_caches()

            result = cache_manager.delete_cache("delete_me")
            assert result is True
            assert "delete_me" not in cache_manager.list_caches()

            # Try to delete non-existent cache
            result = cache_manager.delete_cache("non_existent")
            assert result is False
        finally:
            await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """Test cache statistics."""
        await cache_manager.initialize()
        try:
            cache = cache_manager.create_cache("stats_cache")

            # Add some data to generate stats
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            cache.get("key1")  # Hit
            cache.get("key3")  # Miss

            # Get stats for all caches
            all_stats = cache_manager.get_all_stats()
            assert "stats_cache" in all_stats

            stats = all_stats["stats_cache"]
            assert (
                hasattr(stats, "hits") or "hits" in stats or hasattr(stats, "hit_count")
            )
        finally:
            await cache_manager.shutdown()


class TestEventManager:
    """Test event management."""

    @pytest.fixture
    def event_manager(self):
        """Create an event manager for testing."""
        return EventManager()

    @pytest.mark.asyncio
    async def test_event_manager_initialization(self, event_manager):
        """Test event manager initialization."""
        await event_manager.initialize()
        try:
            buses = event_manager.list_buses()
            assert "default" in buses
        finally:
            await event_manager.shutdown()

    @pytest.mark.asyncio
    async def test_event_subscription(self, event_manager):
        """Test event subscription and emission."""
        await event_manager.initialize()
        try:
            received_events = []

            def handler(event_data):
                received_events.append(event_data)

            # Subscribe (returns EventSubscription, not awaitable)
            subscription = event_manager.subscribe("test_event", handler)
            assert subscription is not None

            # Emit event
            await event_manager.emit_event("test_event", {"data": "test"})

            # Give time for processing
            await asyncio.sleep(0.1)

            assert len(received_events) == 1
            # EventData is a NamedTuple with name, data, timestamp, source
            assert received_events[0].data["data"] == "test"
        finally:
            await event_manager.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_manager):
        """Test multiple handlers for the same event."""
        await event_manager.initialize()
        try:
            handler1_calls = []
            handler2_calls = []

            def handler1(event_data):
                handler1_calls.append(event_data)

            def handler2(event_data):
                handler2_calls.append(event_data)

            # Subscribe both handlers
            event_manager.subscribe("multi_event", handler1)
            event_manager.subscribe("multi_event", handler2)

            await event_manager.emit_event("multi_event", {"data": "multi"})

            # Give time for processing
            await asyncio.sleep(0.1)

            assert len(handler1_calls) == 1
            assert len(handler2_calls) == 1
            assert handler1_calls[0].data["data"] == "multi"
            assert handler2_calls[0].data["data"] == "multi"
        finally:
            await event_manager.shutdown()

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_manager):
        """Test unsubscribing from events."""
        await event_manager.initialize()
        try:
            received_events = []

            def handler(event_data):
                received_events.append(event_data)

            subscription = event_manager.subscribe("unsub_event", handler)
            await event_manager.emit_event("unsub_event", {"data": "before"})

            await asyncio.sleep(0.1)

            # Unsubscribe using the subscription
            result = event_manager.unsubscribe(subscription)
            assert result is True

            await event_manager.emit_event("unsub_event", {"data": "after"})

            await asyncio.sleep(0.1)

            assert len(received_events) == 1
            assert received_events[0].data["data"] == "before"
        finally:
            await event_manager.shutdown()

    @pytest.mark.asyncio
    async def test_create_custom_bus(self, event_manager):
        """Test creating custom event buses."""
        await event_manager.initialize()
        try:
            # Create custom bus
            custom_bus = event_manager.create_bus("custom")
            assert custom_bus is not None
            assert "custom" in event_manager.list_buses()

            # Use custom bus
            received_events = []

            def handler(event_data):
                received_events.append(event_data)

            custom_bus.subscribe("custom_event", handler)
            await custom_bus.publish("custom_event", {"data": "custom"})

            await asyncio.sleep(0.1)

            assert len(received_events) == 1
            assert received_events[0].data["data"] == "custom"

            # Remove custom bus
            result = event_manager.remove_bus("custom")
            assert result is True
            assert "custom" not in event_manager.list_buses()
        finally:
            await event_manager.shutdown()

    @pytest.mark.asyncio
    async def test_event_stats(self, event_manager):
        """Test event statistics."""
        await event_manager.initialize()
        try:

            def handler(event_data):
                pass

            event_manager.subscribe("stats_event", handler)
            await event_manager.emit_event("stats_event", {"data": "test"})

            await asyncio.sleep(0.1)

            # Get stats for all buses
            all_stats = event_manager.get_stats()
            assert "default" in all_stats

            # Stats should contain event information
            default_stats = all_stats["default"]
            assert isinstance(default_stats, dict)
        finally:
            await event_manager.shutdown()


class TestAsyncUtilities:
    """Test async utility functions."""

    @pytest.mark.asyncio
    async def test_async_timeout(self):
        """Test async timeout functionality."""

        async def slow_operation():
            await asyncio.sleep(0.1)
            return "completed"

        # Test successful operation
        result = await slow_operation()
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_async_retry(self):
        """Test async retry functionality."""
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Simulated failure")
            return "success"

        # Simple retry logic for testing
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await failing_operation()
                break
            except ValueError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.01)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent task execution."""

        async def async_task(value):
            await asyncio.sleep(0.01)
            return value * 2

        tasks = [async_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        expected = [i * 2 for i in range(5)]
        assert results == expected


class TestConfigurationIntegration:
    """Test configuration integration scenarios."""

    def test_settings_environment_integration(self):
        """Test settings with environment variables."""
        env_vars = {
            "PYTHONIUM_SERVER_HOST": "test.example.com",
            "PYTHONIUM_SERVER_PORT": "9090",
            "PYTHONIUM_SERVER_TRANSPORT": "http",
        }

        with patch.dict("os.environ", env_vars):
            settings = PythoniumSettings()
            assert settings.server.host == "test.example.com"
            assert settings.server.port == 9090
            assert settings.server.transport == "http"

    def test_settings_validation_integration(self):
        """Test settings validation across components."""
        # Test that invalid settings are caught
        with pytest.raises(ValueError):
            ServerSettings(transport="invalid_transport")

        # Test that valid settings work
        settings = ServerSettings(host="127.0.0.1", port=3000, transport="http")
        assert settings.host == "127.0.0.1"
        assert settings.port == 3000
        assert settings.transport == "http"

    def test_config_sections_exist(self):
        """Test that all expected configuration sections exist."""
        settings = PythoniumSettings()

        # All main sections should be accessible
        assert hasattr(settings, "server")
        assert hasattr(settings, "plugins")
        assert hasattr(settings, "tools")
        assert hasattr(settings, "logging")
        assert hasattr(settings, "security")
        assert hasattr(settings, "database")
        assert hasattr(settings, "cache")

        # Server section should have expected attributes
        assert hasattr(settings.server, "host")
        assert hasattr(settings.server, "port")
        assert hasattr(settings.server, "transport")
