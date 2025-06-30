"""
Test suite for the managers package.

This module contains comprehensive tests for all manager implementations
including the core framework, configuration, plugin, resource, and security managers.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from pythonium.common.exceptions import ManagerError, SecurityError
from pythonium.managers import (
    AuthenticationMethod,
    BaseManager,
    ComponentState,
    ConfigurationManager,
    ManagerPriority,
    ManagerRegistry,
    PluginManager,
    ResourceManager,
    SecurityManager,
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


class TestConfigurationManager:
    """Test the configuration manager."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "app": {"name": "Pythonium", "version": "1.0.0"},
                "plugins": {"enabled": ["test1", "test2"]},
            }
            json.dump(config, f)
            return Path(f.name)

    @pytest.fixture
    def config_manager(self):
        """Create configuration manager."""
        return ConfigurationManager()

    @pytest.mark.asyncio
    async def test_initialization(self, config_manager):
        """Test configuration manager initialization."""
        await config_manager.initialize()
        assert config_manager.state == ComponentState.INITIALIZED

    @pytest.mark.asyncio
    async def test_add_configuration_source(self, config_manager, temp_config):
        """Test adding configuration sources."""
        await config_manager.initialize()

        await config_manager.add_configuration_source(temp_config)

        # Verify configuration is loaded
        assert config_manager.get("app.name") == "Pythonium"
        assert config_manager.get("app.version") == "1.0.0"
        assert config_manager.get("plugins.enabled") == ["test1", "test2"]

    def test_configuration_access(self, config_manager):
        """Test configuration get/set operations."""
        # Test default values
        assert config_manager.get("nonexistent.key", "default") == "default"

        # Test setting values
        config_manager.set("test.key", "test_value")
        assert config_manager.get("test.key") == "test_value"

        # Test nested access
        config_manager.set("nested.deep.key", "deep_value")
        assert config_manager.get("nested.deep.key") == "deep_value"


class TestResourceManager:
    """Test the resource manager."""

    @pytest.fixture
    def resource_manager(self):
        """Create resource manager."""
        return ResourceManager()

    @pytest.mark.asyncio
    async def test_initialization(self, resource_manager):
        """Test resource manager initialization."""
        await resource_manager.initialize()
        assert resource_manager.state == ComponentState.INITIALIZED

    def test_resource_usage_tracking(self, resource_manager):
        """Test resource usage tracking."""
        usage = resource_manager.get_resource_usage()
        assert isinstance(usage.memory_bytes, int)
        assert isinstance(usage.memory_percent, float)
        assert isinstance(usage.cpu_percent, float)

    def test_resource_limits(self, resource_manager):
        """Test resource limits configuration."""
        from pythonium.managers.resource_manager import ResourceLimits

        limits = ResourceLimits(
            max_memory=1024 * 1024 * 100, max_cpu_percent=80.0  # 100MB
        )

        resource_manager.set_resource_limits(limits)
        retrieved_limits = resource_manager.get_resource_limits()

        assert retrieved_limits.max_memory == limits.max_memory
        assert retrieved_limits.max_cpu_percent == limits.max_cpu_percent

    @pytest.mark.asyncio
    async def test_connection_pool(self, resource_manager):
        """Test connection pool functionality."""
        await resource_manager.initialize()

        # Create a simple connection factory
        def create_connection():
            return {"id": "test_connection", "active": True}

        # Create pool
        pool = await resource_manager.create_pool(
            "test_pool", create_connection, max_size=5, min_size=1
        )

        assert pool is not None
        assert resource_manager.get_pool("test_pool") is pool

        # Test pool statistics
        stats = resource_manager.get_pool_stats()
        assert "test_pool" in stats


class TestSecurityManager:
    """Test the security manager."""

    @pytest.fixture
    def security_manager(self):
        """Create security manager."""
        return SecurityManager()

    @pytest.mark.asyncio
    async def test_initialization(self, security_manager):
        """Test security manager initialization."""
        await security_manager.initialize()
        assert security_manager.state == ComponentState.INITIALIZED

        # Start the manager to trigger default admin creation
        await security_manager.start()
        assert security_manager.state == ComponentState.RUNNING

        # Should create default admin user
        users = security_manager.list_users()
        assert len(users) > 0
        admin_user = next((u for u in users if u.username == "admin"), None)
        assert admin_user is not None
        assert admin_user.is_admin

        # Clean up
        await security_manager.stop()
        await security_manager.dispose()

    @pytest.mark.asyncio
    async def test_api_key_management(self, security_manager):
        """Test API key creation and management."""
        await security_manager.initialize()

        # Create API key
        raw_key, api_key = await security_manager.create_api_key(
            "test_key", permissions={"read:system", "write:system"}
        )

        assert isinstance(raw_key, str)
        assert api_key.name == "test_key"
        assert "read:system" in api_key.permissions

        # Test authentication with API key
        auth_result = await security_manager.authenticate(
            AuthenticationMethod.API_KEY, {"api_key": raw_key}
        )

        assert auth_result.success
        assert auth_result.api_key_id == api_key.key_id
        assert "read:system" in auth_result.permissions

        # Revoke API key
        await security_manager.revoke_api_key(api_key.key_id)

        # Authentication should fail now
        auth_result = await security_manager.authenticate(
            AuthenticationMethod.API_KEY, {"api_key": raw_key}
        )

        assert not auth_result.success

    @pytest.mark.asyncio
    async def test_user_management(self, security_manager):
        """Test user creation and management."""
        await security_manager.initialize()

        from pythonium.managers.security_manager import User

        # Create user
        user = User(
            user_id="test_user",
            username="testuser",
            email="test@example.com",
            password_hash=security_manager._hash_password("password123"),
            permissions={"read:system"},
        )

        await security_manager.create_user(user)

        # Test authentication
        auth_result = await security_manager.authenticate(
            AuthenticationMethod.BASIC_AUTH,
            {"username": "testuser", "password": "password123"},
        )

        assert auth_result.success
        assert auth_result.user_id == "test_user"
        assert "read:system" in auth_result.permissions

        # Test wrong password
        auth_result = await security_manager.authenticate(
            AuthenticationMethod.BASIC_AUTH,
            {"username": "testuser", "password": "wrongpassword"},
        )

        assert not auth_result.success

    def test_permissions_and_authorization(self, security_manager):
        """Test permission checking and authorization."""
        from pythonium.managers.security_manager import User

        # Create user with specific permissions
        user = User(
            user_id="test_user",
            username="testuser",
            permissions={"read:system", "write:plugins"},
        )

        security_manager._users[user.user_id] = user

        # Test permission checks
        assert security_manager.check_permission("test_user", "read:system")
        assert security_manager.check_permission("test_user", "write:plugins")
        assert not security_manager.check_permission("test_user", "admin:system")

        # Test admin user (should have all permissions)
        admin_user = User(user_id="admin_user", username="admin", is_admin=True)
        security_manager._users[admin_user.user_id] = admin_user

        assert security_manager.check_permission("admin_user", "read:system")
        assert security_manager.check_permission("admin_user", "admin:system")
        assert security_manager.check_permission("admin_user", "any:permission")

    @pytest.mark.asyncio
    async def test_rate_limiting(self, security_manager):
        """Test rate limiting functionality."""
        # Test rate limit check
        allowed, count = await security_manager.check_rate_limit(
            "test_key", limit=5, window=timedelta(minutes=1)
        )

        assert allowed
        assert count == 1

        # Make multiple requests
        for i in range(4):
            allowed, count = await security_manager.check_rate_limit(
                "test_key", limit=5, window=timedelta(minutes=1)
            )
            assert allowed
            assert count == i + 2

        # Should hit limit
        allowed, count = await security_manager.check_rate_limit(
            "test_key", limit=5, window=timedelta(minutes=1)
        )

        assert not allowed
        assert count == 5

    def test_audit_logging(self, security_manager):
        """Test audit logging functionality."""
        # Audit log should initially be empty
        assert len(security_manager.get_audit_log()) == 0

        # Add audit callback to capture events
        captured_events = []

        def audit_callback(entry):
            captured_events.append(entry)

        security_manager.add_audit_callback(audit_callback)

        # This would normally be called internally, but we'll call it directly for testing
        asyncio.run(
            security_manager._log_audit_event(
                "test_event",
                user_id="test_user",
                action="test_action",
                result="success",
            )
        )

        # Check audit log
        audit_entries = security_manager.get_audit_log()
        assert len(audit_entries) == 1
        assert audit_entries[0].event_type == "test_event"
        assert audit_entries[0].user_id == "test_user"

        # Check callback was called
        assert len(captured_events) == 1
        assert captured_events[0].event_type == "test_event"


class TestManagerIntegration:
    """Test manager integration and interactions."""

    @pytest.mark.asyncio
    async def test_full_system_initialization(self):
        """Test initializing a complete manager system."""
        registry = ManagerRegistry()

        # Register all managers
        registry.register_manager(
            "config", ConfigurationManager, priority=ManagerPriority.CRITICAL
        )
        registry.register_manager(
            "security", SecurityManager, priority=ManagerPriority.HIGH
        )
        registry.register_manager(
            "resource", ResourceManager, priority=ManagerPriority.HIGH
        )
        registry.register_manager(
            "plugin", PluginManager, priority=ManagerPriority.NORMAL
        )

        # Initialize all managers
        await registry.initialize_all()

        # Verify all managers are running
        assert len(registry._instances) == 4
        assert all(m.is_running for m in registry._instances.values())

        # Test health status
        health_status = await registry.get_system_health()
        assert health_status["overall_status"] == "healthy"
        assert health_status["total_managers"] == 4
        assert health_status["running_managers"] == 4

        # Shutdown all managers
        await registry.shutdown_all()

        # Verify all managers are stopped
        assert len(registry._instances) == 0

    @pytest.mark.asyncio
    async def test_manager_dependencies(self):
        """Test manager dependency injection."""
        registry = ManagerRegistry()

        # Create managers with dependencies
        config_manager = ConfigurationManager()
        security_manager = SecurityManager()

        # Set up dependency
        security_manager.add_dependency(
            ManagerDependency(ConfigurationManager, required=True)
        )

        # Register managers
        registry.register_manager(
            "config", ConfigurationManager, factory=lambda: config_manager
        )
        registry.register_manager(
            "security", SecurityManager, factory=lambda: security_manager
        )

        # Initialize - should work with dependency resolution
        await registry.initialize_all()

        # Verify dependency is set
        security_instance = await registry.get_manager("security")
        config_dependency = security_instance.get_dependency(ConfigurationManager)
        assert config_dependency is not None

        await registry.shutdown_all()


if __name__ == "__main__":
    pytest.main([__file__])
