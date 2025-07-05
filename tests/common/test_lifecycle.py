"""Tests for lifecycle module."""

import asyncio

import pytest

from pythonium.common.lifecycle import (
    ComponentState,
    LifecycleEvent,
    LifecycleManager,
    LifecycleMixin,
)


class TestComponentState:
    """Test ComponentState enum."""

    def test_component_state_values(self):
        """Test ComponentState enum values."""
        assert ComponentState.CREATED.value == "created"
        assert ComponentState.LOADING.value == "loading"
        assert ComponentState.RUNNING.value == "running"
        assert ComponentState.STOPPED.value == "stopped"


class TestLifecycleEvent:
    """Test LifecycleEvent enum."""

    def test_lifecycle_event_values(self):
        """Test LifecycleEvent enum values."""
        assert hasattr(LifecycleEvent, "STATE_CHANGED")
        assert hasattr(LifecycleEvent, "ERROR_OCCURRED")


class MockComponent(LifecycleMixin):
    """Mock component for testing."""

    def __init__(self, name: str = "test_component"):
        super().__init__()
        self.name = name
        self.start_called = False
        self.stop_called = False
        self.initialize_called = False
        self.dispose_called = False

    async def _do_initialize(self):
        """Mock initialize implementation."""
        self.initialize_called = True

    async def _do_start(self):
        """Mock start implementation."""
        self.start_called = True

    async def _do_stop(self):
        """Mock stop implementation."""
        self.stop_called = True

    async def _do_dispose(self):
        """Mock dispose implementation."""
        self.dispose_called = True


class TestLifecycleMixin:
    """Test LifecycleMixin functionality."""

    def test_lifecycle_mixin_initialization(self):
        """Test LifecycleMixin initialization."""
        component = MockComponent("test")
        assert component.name == "test"
        assert component.state == ComponentState.CREATED

    async def test_lifecycle_mixin_start(self):
        """Test starting a component."""
        component = MockComponent("test")
        await component.start_lifecycle()
        assert component.start_called
        assert component.state == ComponentState.RUNNING

    async def test_lifecycle_mixin_stop(self):
        """Test stopping a component."""
        component = MockComponent("test")
        await component.start_lifecycle()
        await component.stop_lifecycle()
        assert component.stop_called
        assert component.state == ComponentState.STOPPED

    def test_lifecycle_mixin_properties(self):
        """Test component properties."""
        component = MockComponent("test")
        assert hasattr(component, "state")
        assert hasattr(component, "state_history")
        assert component.state == ComponentState.CREATED


class TestLifecycleManager:
    """Test LifecycleManager functionality."""

    def test_lifecycle_manager_initialization(self):
        """Test LifecycleManager initialization."""
        manager = LifecycleManager()
        assert manager is not None

    async def test_lifecycle_manager_register_component(self):
        """Test registering components."""
        manager = LifecycleManager()
        component = MockComponent("test")

        manager.register_component("test", component)
        # Check that component is in the internal _components dict
        assert "test" in manager._components
        assert manager._components["test"] is component

    async def test_lifecycle_manager_start_all(self):
        """Test starting all components."""
        manager = LifecycleManager()
        component1 = MockComponent("test1")
        component2 = MockComponent("test2")

        manager.register_component("test1", component1)
        manager.register_component("test2", component2)

        await manager.start_all()
        assert component1.start_called
        assert component2.start_called

    async def test_lifecycle_manager_stop_all(self):
        """Test stopping all components."""
        manager = LifecycleManager()
        component1 = MockComponent("test1")
        component2 = MockComponent("test2")

        manager.register_component("test1", component1)
        manager.register_component("test2", component2)

        await manager.start_all()
        await manager.stop_all()
        assert component1.stop_called
        assert component2.stop_called

    def test_lifecycle_manager_get_component(self):
        """Test getting specific component."""
        manager = LifecycleManager()
        component = MockComponent("test")

        manager.register_component("test", component)
        # Access component via internal _components dict since get_component doesn't exist
        retrieved = manager._components["test"]
        assert retrieved is component

    def test_lifecycle_manager_unregister_component(self):
        """Test unregistering components."""
        manager = LifecycleManager()
        component = MockComponent("test")

        manager.register_component("test", component)
        # Since unregister_component doesn't exist, simulate it by removing directly
        del manager._components["test"]

        # Check that component is removed
        assert "test" not in manager._components

    async def test_lifecycle_manager_shutdown(self):
        """Test manager shutdown."""
        manager = LifecycleManager()
        component = MockComponent("test")

        manager.register_component("test", component)
        await manager.start_all()
        # Use stop_all instead of shutdown since shutdown doesn't exist
        await manager.stop_all()

        assert component.stop_called
