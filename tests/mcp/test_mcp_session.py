"""
Comprehensive unit tests for MCP session management.

Tests session creation, lifecycle management, state transitions,
and session manager functionality.
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from pythonium.common.lifecycle import ComponentState
from pythonium.mcp.protocol import ClientCapabilities, InitializeParams
from pythonium.mcp.session import (
    ConnectionType,
    SessionInfo,
    SessionManager,
    SessionMetrics,
)


@pytest.mark.unit
class TestMCPSession:
    """Test MCP session data structures."""

    def test_session_creation(self):
        """Test session info creation."""
        now = datetime.now()
        client_info = {"name": "test-client", "version": "1.0.0"}
        capabilities = ClientCapabilities()

        session = SessionInfo(
            session_id="test-session",
            client_info=client_info,
            capabilities=capabilities,
            created_at=now,
            last_activity=now,
            state=ComponentState.CREATED,
            connection_type=ConnectionType.STDIO,
            remote_address="127.0.0.1",
        )

        assert session.session_id == "test-session"
        assert session.client_info == client_info
        assert session.capabilities == capabilities
        assert session.state == ComponentState.CREATED
        assert session.connection_type == ConnectionType.STDIO
        assert session.remote_address == "127.0.0.1"

    def test_session_initialization(self):
        """Test session initialization update."""
        now = datetime.now()
        capabilities = ClientCapabilities()

        session = SessionInfo(
            session_id="test-session",
            client_info={},
            capabilities=capabilities,
            created_at=now,
            last_activity=now,
            state=ComponentState.CONNECTING,
            connection_type=ConnectionType.STDIO,
        )

        # Update for initialization
        new_client_info = {"name": "initialized-client", "version": "2.0.0"}
        session.client_info = new_client_info
        session.state = ComponentState.READY
        session.last_activity = datetime.now()

        assert session.client_info == new_client_info
        assert session.state == ComponentState.READY

    def test_session_update_activity(self):
        """Test session activity tracking."""
        now = datetime.now()
        capabilities = ClientCapabilities()

        session = SessionInfo(
            session_id="test-session",
            client_info={},
            capabilities=capabilities,
            created_at=now,
            last_activity=now,
            state=ComponentState.READY,
            connection_type=ConnectionType.STDIO,
        )

        # Simulate time passing
        later = now + timedelta(minutes=5)
        session.last_activity = later

        assert session.last_activity == later

    def test_session_termination(self):
        """Test session termination."""
        now = datetime.now()
        capabilities = ClientCapabilities()

        session = SessionInfo(
            session_id="test-session",
            client_info={},
            capabilities=capabilities,
            created_at=now,
            last_activity=now,
            state=ComponentState.READY,
            connection_type=ConnectionType.STDIO,
        )

        # Terminate session
        session.state = ComponentState.DISCONNECTING
        assert session.state == ComponentState.DISCONNECTING

    def test_session_metrics(self):
        """Test session metrics tracking."""
        metrics = SessionMetrics()

        assert metrics.requests_received == 0
        assert metrics.responses_sent == 0
        assert metrics.notifications_sent == 0
        assert metrics.errors_count == 0
        assert metrics.bytes_received == 0
        assert metrics.bytes_sent == 0
        assert metrics.average_response_time_ms == 0.0


@pytest.mark.asyncio
class TestMCPSessionManager:
    """Test MCP session manager."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_manager_creation(self):
        """Test session manager initialization."""
        session_manager = SessionManager(
            session_timeout_minutes=30, max_sessions=50, cleanup_interval_minutes=10
        )

        assert session_manager.session_timeout_minutes == 30
        assert session_manager.max_sessions == 50
        assert session_manager.cleanup_interval_minutes == 10

    async def test_start_stop_session_manager(self):
        """Test session manager start/stop lifecycle."""
        session_manager = SessionManager()

        # Start
        await session_manager.start()
        assert session_manager._running is True

        # Stop
        await session_manager.stop()
        assert session_manager._running is False

    async def test_create_session(self):
        """Test session creation."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO,
                remote_address="127.0.0.1",
                metadata={"test": "data"},
            )

            assert session_id.startswith("session_")

            # Verify session exists
            session = await session_manager.get_session(session_id)
            assert session is not None
            assert session.session_id == session_id
            assert session.connection_type == ConnectionType.STDIO
            assert session.remote_address == "127.0.0.1"
            assert session.state == ComponentState.CONNECTING

        finally:
            await session_manager.stop()

    async def test_get_session(self):
        """Test session retrieval."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            # Non-existent session
            session = await session_manager.get_session("nonexistent")
            assert session is None

            # Create and retrieve session
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )

            session = await session_manager.get_session(session_id)
            assert session is not None
            assert session.session_id == session_id

        finally:
            await session_manager.stop()

    async def test_initialize_session(self):
        """Test session initialization."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )

            # Initialize session
            client_info = {"name": "test-client", "version": "1.0.0"}
            capabilities = ClientCapabilities()

            initialize_params = InitializeParams(
                protocolVersion="2024-11-05",
                clientInfo=client_info,
                capabilities=capabilities,
            )

            await session_manager.initialize_session(session_id, initialize_params)

            # Check session was updated
            session = await session_manager.get_session(session_id)
            assert session.client_info == client_info
            assert session.capabilities == capabilities
            assert session.state == ComponentState.READY

        finally:
            await session_manager.stop()

    async def test_close_session(self):
        """Test session closure."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )

            # Verify session exists
            session = await session_manager.get_session(session_id)
            assert session is not None

            # Close session
            await session_manager.close_session(session_id, "Test closure")

            # Verify session is removed
            session = await session_manager.get_session(session_id)
            assert session is None

        finally:
            await session_manager.stop()

    async def test_get_session_count(self):
        """Test session count tracking."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            # Initially zero
            count = await session_manager.get_session_count()
            assert count == 0

            # Create sessions
            session_id1 = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )
            count = await session_manager.get_session_count()
            assert count == 1

            await session_manager.create_session(
                connection_type=ConnectionType.WEBSOCKET
            )
            count = await session_manager.get_session_count()
            assert count == 2

            # Close session
            await session_manager.close_session(session_id1)
            count = await session_manager.get_session_count()
            assert count == 1

        finally:
            await session_manager.stop()

    async def test_session_limit_enforcement(self):
        """Test session limit enforcement."""
        session_manager = SessionManager(max_sessions=2)
        await session_manager.start()

        try:
            # Create maximum sessions
            await session_manager.create_session(connection_type=ConnectionType.STDIO)
            await session_manager.create_session(
                connection_type=ConnectionType.WEBSOCKET
            )

            # Try to exceed limit
            with pytest.raises(
                RuntimeError, match="Maximum number of sessions exceeded"
            ):
                await session_manager.create_session(
                    connection_type=ConnectionType.HTTP
                )

        finally:
            await session_manager.stop()

    async def test_session_activity_update(self):
        """Test session activity tracking."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )

            session = await session_manager.get_session(session_id)
            original_activity = session.last_activity

            # Simulate some delay
            await asyncio.sleep(0.01)

            # Update activity
            await session_manager.update_session_activity(session_id)

            session = await session_manager.get_session(session_id)
            assert session.last_activity > original_activity

        finally:
            await session_manager.stop()

    async def test_session_context(self):
        """Test session context management."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )

            # Set context values
            await session_manager.set_session_context(
                session_id, "user_id", "test_user"
            )
            await session_manager.set_session_context(session_id, "role", "admin")

            # Get context values
            user_id = await session_manager.get_session_context(session_id, "user_id")
            role = await session_manager.get_session_context(session_id, "role")
            missing = await session_manager.get_session_context(
                session_id, "missing", "default"
            )

            assert user_id == "test_user"
            assert role == "admin"
            assert missing == "default"

        finally:
            await session_manager.stop()

    async def test_subscriptions(self):
        """Test resource subscriptions."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )

            # Add subscriptions
            await session_manager.add_subscription(session_id, "file://test.txt")
            await session_manager.add_subscription(session_id, "http://example.com")

            # Get subscriptions
            subscriptions = await session_manager.get_subscriptions(session_id)
            assert "file://test.txt" in subscriptions
            assert "http://example.com" in subscriptions
            assert len(subscriptions) == 2

            # Get subscribers
            subscribers = await session_manager.get_subscribers("file://test.txt")
            assert session_id in subscribers

            # Remove subscription
            await session_manager.remove_subscription(session_id, "file://test.txt")
            subscriptions = await session_manager.get_subscriptions(session_id)
            assert "file://test.txt" not in subscriptions
            assert "http://example.com" in subscriptions

        finally:
            await session_manager.stop()

    async def test_get_active_sessions(self):
        """Test getting active sessions."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            session_id1 = await session_manager.create_session(
                connection_type=ConnectionType.STDIO
            )
            await session_manager.create_session(
                connection_type=ConnectionType.WEBSOCKET
            )

            # Initialize one session (make it active)
            initialize_params = InitializeParams(
                protocolVersion="2024-11-05",
                clientInfo={"name": "test"},
                capabilities=ClientCapabilities(),
            )
            await session_manager.initialize_session(session_id1, initialize_params)

            # Get active sessions
            active_sessions = await session_manager.get_active_sessions()
            assert len(active_sessions) == 1
            assert active_sessions[0].session_id == session_id1
            assert active_sessions[0].state == ComponentState.READY

        finally:
            await session_manager.stop()

    async def test_session_summary(self):
        """Test session summary statistics."""
        session_manager = SessionManager()
        await session_manager.start()

        try:
            await session_manager.create_session(connection_type=ConnectionType.STDIO)

            summary = await session_manager.get_session_summary()

            assert summary["total_sessions"] == 1
            assert summary["active_sessions"] == 0  # Not initialized yet
            assert "sessions_by_connection_type" in summary
            assert "total_requests" in summary
            assert "total_responses" in summary

        finally:
            await session_manager.stop()

    async def test_concurrent_session_creation(self):
        """Test concurrent session creation."""
        session_manager = SessionManager(max_sessions=10)
        await session_manager.start()

        try:

            async def create_session_task():
                try:
                    return await session_manager.create_session(
                        connection_type=ConnectionType.STDIO
                    )
                except Exception as e:
                    return e

            # Create multiple sessions concurrently
            tasks = [create_session_task() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # Check that all sessions were created successfully
            session_ids = [r for r in results if isinstance(r, str)]
            errors = [r for r in results if isinstance(r, Exception)]

            assert len(session_ids) == 5
            assert len(errors) == 0
            assert len(set(session_ids)) == 5  # All unique

        finally:
            await session_manager.stop()
