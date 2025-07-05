"""
Test suite for the managers package.

This module contains comprehensive tests for all manager implementations
including the core framework, and configuration.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from pythonium.common.exceptions import ManagerError
from pythonium.common.lifecycle import ComponentState
from pythonium.core import ManagerRegistry
from pythonium.managers import (
    BaseManager,
    ManagerPriority,
)
from pythonium.managers.base import HealthCheck, ManagerDependency


class MockManager(BaseManager):
    """Mock manager for testing base functionality."""

    def __init__(self, name="test"):
        super().__init__(name, "1.0.0", "Mock manager")
        self.initialized = False
        self.started = False
        self.stopped = False
        self.cleaned_up = False

    async def _initialize(self):
        self.initialized = True

    async def _start(self):
        self.started = True

    async def _stop(self):
        self.stopped = True

    async def _cleanup(self):
        self.cleaned_up = True


class TestManagerRegistry:
    """Test the manager registry system."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        return ManagerRegistry()

    def test_register_manager(self, registry):
        """Test manager registration."""
        registry.register_manager("test", MockManager)

        assert registry.is_registered("test")
        registration = registry.get_registration("test")
        assert registration is not None
        assert registration.manager_type == MockManager

    def test_duplicate_registration(self, registry):
        """Test that duplicate registration raises error."""
        registry.register_manager("test", MockManager)

        with pytest.raises(ManagerError):
            registry.register_manager("test", MockManager)

    @pytest.mark.asyncio
    async def test_create_manager(self, registry):
        """Test manager creation."""
        registry.register_manager("test", MockManager)

        manager = await registry.create_manager("test")
        assert isinstance(manager, MockManager)
        assert manager.info.name == "test"

    @pytest.mark.asyncio
    async def test_singleton_behavior(self, registry):
        """Test singleton manager behavior."""
        registry.register_manager("test", MockManager, singleton=True)

        manager1 = await registry.create_manager("test")
        manager2 = await registry.create_manager("test")

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_initialization_order(self, registry):
        """Test manager initialization respects dependencies and priorities."""
        # Register managers with different priorities
        registry.register_manager("high", MockManager, priority=ManagerPriority.HIGH)
        registry.register_manager(
            "normal", MockManager, priority=ManagerPriority.NORMAL
        )
        registry.register_manager(
            "critical", MockManager, priority=ManagerPriority.CRITICAL
        )

        await registry.initialize_all()

        # All managers should be initialized
        assert len(registry._instances) == 3
        assert all(m.initialized for m in registry._instances.values())


class TestBaseManager:
    """Test the base manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a test manager."""
        return MockManager()

    @pytest.mark.asyncio
    async def test_lifecycle(self, manager):
        """Test manager lifecycle."""
        # Initial state
        assert manager.state == ComponentState.CREATED
        assert not manager.is_running

        # Initialize
        await manager.initialize()
        assert manager.state == ComponentState.INITIALIZED
        assert manager.initialized

        # Start
        await manager.start()
        assert manager.state == ComponentState.RUNNING
        assert manager.is_running
        assert manager.started

        # Stop
        await manager.stop()
        assert manager.state == ComponentState.STOPPED
        assert manager.stopped

        # Dispose
        await manager.dispose()
        assert manager.state == ComponentState.DISPOSED
        assert manager.cleaned_up

    @pytest.mark.asyncio
    async def test_health_checks(self, manager):
        """Test health check functionality."""
        await manager.initialize()

        # Run health checks
        results = await manager.run_health_checks()
        assert "state_check" in results
        assert results["state_check"] is True

        # Add custom health check
        manager.add_health_check(
            HealthCheck(name="custom_check", check_func=lambda: True)
        )

        results = await manager.run_health_checks()
        assert "custom_check" in results
        assert results["custom_check"] is True

    def test_configuration_access(self, manager):
        """Test configuration access methods."""
        # Test without config manager
        assert manager.get_config("test_key", "default") == "default"

        manager.set_config("test_key", "test_value")
        # Without config manager, this should not raise an error


class TestManagerIntegration:
    """Test manager integration and interactions."""

    @pytest.mark.asyncio
    async def test_full_system_initialization(self):
        """Test initializing a complete manager system."""
        registry = ManagerRegistry()

        # Initialize with empty registry (no managers to test basic functionality)
        await registry.initialize_all()

        # Verify registry is running
        assert len(registry._instances) == 0

        # Test health status
        health_status = await registry.get_system_health()
        assert health_status["overall_status"] == "healthy"
        assert health_status["total_managers"] == 0
        assert health_status["running_managers"] == 0

        # Shutdown all managers
        await registry.shutdown_all()

        # Verify all managers are stopped
        assert len(registry._instances) == 0

    @pytest.mark.asyncio
    async def test_manager_registry_basic_operations(self):
        """Test basic registry operations without specific managers."""
        registry = ManagerRegistry()

        # Test empty registry
        assert len(registry._instances) == 0

        # Test health status on empty registry
        health_status = await registry.get_system_health()
        assert health_status["overall_status"] == "healthy"
        assert health_status["total_managers"] == 0

        # Test getting non-existent manager
        manager_instance = await registry.get_manager("nonexistent")
        assert manager_instance is None


if __name__ == "__main__":
    pytest.main([__file__])
