"""
MCP server session management.

This module handles client sessions, connection state, and session lifecycle
management for the MCP server.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pythonium.common.lifecycle import ComponentState

from .protocol import (
    ClientCapabilities,
    InitializeParams,
    MCPNotification,
    MCPRequest,
    MCPResponse,
)

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Connection types."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"
    TCP = "tcp"


@dataclass
class SessionInfo:
    """Session information."""

    session_id: str
    client_info: Dict[str, Any]
    capabilities: ClientCapabilities
    created_at: datetime
    last_activity: datetime
    state: ComponentState
    connection_type: ConnectionType
    remote_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionMetrics:
    """Session metrics."""

    requests_received: int = 0
    responses_sent: int = 0
    notifications_sent: int = 0
    errors_count: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    average_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    last_response_time: Optional[datetime] = None


class SessionManager:
    """
    Manages MCP client sessions.

    Handles session lifecycle, state management, and provides utilities
    for session monitoring and cleanup.
    """

    def __init__(
        self,
        session_timeout_minutes: int = 60,
        max_sessions: int = 1000,
        cleanup_interval_minutes: int = 5,
    ):
        self.session_timeout_minutes = session_timeout_minutes
        self.max_sessions = max_sessions
        self.cleanup_interval_minutes = cleanup_interval_minutes

        # Session storage
        self._sessions: Dict[str, SessionInfo] = {}
        self._session_metrics: Dict[str, SessionMetrics] = {}
        self._session_contexts: Dict[str, Dict[str, Any]] = {}

        # Connection management
        self._connection_handlers: Dict[str, Callable] = {}
        self._message_queues: Dict[str, asyncio.Queue] = {}

        # Event handlers
        self._session_created_handlers: List[Callable] = []
        self._session_destroyed_handlers: List[Callable] = []
        self._session_state_changed_handlers: List[Callable] = []

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Synchronization
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the session manager."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")

    async def stop(self) -> None:
        """Stop the session manager."""
        if not self._running:
            return

        self._running = False

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        await self.close_all_sessions()

        logger.info("Session manager stopped")

    async def create_session(
        self,
        connection_type: ConnectionType,
        remote_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new session.

        Args:
            connection_type: Type of connection
            remote_address: Remote client address
            metadata: Additional session metadata

        Returns:
            Session ID

        Raises:
            RuntimeError: If maximum sessions exceeded
        """
        async with self._lock:
            # Check session limit
            if len(self._sessions) >= self.max_sessions:
                raise RuntimeError("Maximum number of sessions exceeded")

            # Generate session ID
            session_id = f"session_{uuid.uuid4().hex}"

            # Create session info
            now = datetime.now()
            session_info = SessionInfo(
                session_id=session_id,
                client_info={},
                capabilities=ClientCapabilities(),
                created_at=now,
                last_activity=now,
                state=ComponentState.CONNECTING,
                connection_type=connection_type,
                remote_address=remote_address,
                metadata=metadata or {},
            )

            # Store session
            self._sessions[session_id] = session_info
            self._session_metrics[session_id] = SessionMetrics()
            self._session_contexts[session_id] = {}
            self._message_queues[session_id] = asyncio.Queue()

            # Notify handlers
            await self._notify_session_created(session_info)

            logger.debug(f"Created session {session_id} from {remote_address}")
            return session_id

    async def initialize_session(
        self, session_id: str, initialize_params: InitializeParams
    ) -> None:
        """
        Initialize a session with client information.

        Args:
            session_id: Session ID
            initialize_params: Initialize parameters from client

        Raises:
            KeyError: If session not found
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} not found")

            session = self._sessions[session_id]

            # Update session with client info
            session.client_info = initialize_params.clientInfo
            session.capabilities = initialize_params.capabilities
            session.last_activity = datetime.now()

            # Transition to ready state
            await self._transition_session_state(session_id, ComponentState.READY)

            logger.debug(f"Initialized session {session_id}")

    async def close_session(
        self, session_id: str, reason: str = "Normal closure"
    ) -> None:
        """
        Close a session.

        Args:
            session_id: Session ID
            reason: Reason for closure
        """
        async with self._lock:
            if session_id not in self._sessions:
                return

            session = self._sessions[session_id]

            # Transition to disconnecting state
            await self._transition_session_state(
                session_id, ComponentState.DISCONNECTING
            )

            # Close message queue
            if session_id in self._message_queues:
                queue = self._message_queues[session_id]
                # Signal queue closure
                await queue.put(None)

            # Clean up session data
            await self._cleanup_session(session_id)

            # Notify handlers
            await self._notify_session_destroyed(session, reason)

            logger.debug(f"Closed session {session_id}: {reason}")

    async def close_all_sessions(self) -> None:
        """Close all sessions."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id, "Server shutdown")

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        return self._sessions.get(session_id)

    async def update_session_activity(self, session_id: str) -> None:
        """Update session last activity timestamp."""
        if session_id in self._sessions:
            self._sessions[session_id].last_activity = datetime.now()

    async def set_session_context(self, session_id: str, key: str, value: Any) -> None:
        """Set session context value."""
        if session_id in self._session_contexts:
            self._session_contexts[session_id][key] = value

    async def get_session_context(
        self, session_id: str, key: str, default: Any = None
    ) -> Any:
        """Get session context value."""
        return self._session_contexts.get(session_id, {}).get(key, default)

    async def record_request(self, session_id: str, request: MCPRequest) -> None:
        """Record a request for metrics."""
        if session_id in self._session_metrics:
            metrics = self._session_metrics[session_id]
            metrics.requests_received += 1
            metrics.last_request_time = datetime.now()
            # Estimate bytes (rough calculation)
            metrics.bytes_received += len(str(request.model_dump_json()))

    async def record_response(
        self, session_id: str, response: MCPResponse, response_time_ms: float
    ) -> None:
        """Record a response for metrics."""
        if session_id in self._session_metrics:
            metrics = self._session_metrics[session_id]
            metrics.responses_sent += 1
            metrics.last_response_time = datetime.now()

            # Update average response time
            if metrics.average_response_time_ms == 0:
                metrics.average_response_time_ms = response_time_ms
            else:
                # Simple moving average
                metrics.average_response_time_ms = (
                    metrics.average_response_time_ms * 0.9 + response_time_ms * 0.1
                )

            # Estimate bytes
            metrics.bytes_sent += len(str(response.model_dump_json()))

            # Check for errors
            if response.error:
                metrics.errors_count += 1

    async def record_notification(
        self, session_id: str, notification: MCPNotification
    ) -> None:
        """Record a notification for metrics."""
        if session_id in self._session_metrics:
            metrics = self._session_metrics[session_id]
            metrics.notifications_sent += 1
            # Estimate bytes
            metrics.bytes_sent += len(str(notification.model_dump_json()))

    async def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Get session metrics."""
        return self._session_metrics.get(session_id)

    async def get_active_sessions(self) -> List[SessionInfo]:
        """Get all active sessions."""
        return [
            session
            for session in self._sessions.values()
            if session.state in [ComponentState.INITIALIZING, ComponentState.READY]
        ]

    async def get_session_count(self) -> int:
        """Get total session count."""
        return len(self._sessions)

    async def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary statistics."""
        active_sessions = await self.get_active_sessions()

        # Group by connection type
        by_connection_type: Dict[str, int] = {}
        for session in active_sessions:
            conn_type = session.connection_type.value
            by_connection_type[conn_type] = by_connection_type.get(conn_type, 0) + 1

        # Calculate total metrics
        total_metrics = SessionMetrics()
        for metrics in self._session_metrics.values():
            total_metrics.requests_received += metrics.requests_received
            total_metrics.responses_sent += metrics.responses_sent
            total_metrics.notifications_sent += metrics.notifications_sent
            total_metrics.errors_count += metrics.errors_count
            total_metrics.bytes_received += metrics.bytes_received
            total_metrics.bytes_sent += metrics.bytes_sent

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(active_sessions),
            "sessions_by_connection_type": by_connection_type,
            "total_requests": total_metrics.requests_received,
            "total_responses": total_metrics.responses_sent,
            "total_notifications": total_metrics.notifications_sent,
            "total_errors": total_metrics.errors_count,
            "total_bytes_received": total_metrics.bytes_received,
            "total_bytes_sent": total_metrics.bytes_sent,
        }

    def add_session_created_handler(
        self, handler: Callable[[SessionInfo], None]
    ) -> None:
        """Add session created event handler."""
        self._session_created_handlers.append(handler)

    def add_session_destroyed_handler(
        self, handler: Callable[[SessionInfo, str], None]
    ) -> None:
        """Add session destroyed event handler."""
        self._session_destroyed_handlers.append(handler)

    def add_session_state_changed_handler(
        self, handler: Callable[[str, ComponentState, ComponentState], None]
    ) -> None:
        """Add session state changed event handler."""
        self._session_state_changed_handlers.append(handler)

    async def _transition_session_state(
        self, session_id: str, new_state: ComponentState
    ) -> None:
        """Transition session to new state."""
        if session_id not in self._sessions:
            return

        session = self._sessions[session_id]
        old_state = session.state

        if old_state != new_state:
            session.state = new_state
            session.last_activity = datetime.now()

            # Notify handlers
            await self._notify_session_state_changed(session_id, old_state, new_state)

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up session data."""
        # Remove from all storage
        self._sessions.pop(session_id, None)
        self._session_metrics.pop(session_id, None)
        self._session_contexts.pop(session_id, None)
        self._message_queues.pop(session_id, None)
        self._connection_handlers.pop(session_id, None)

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        now = datetime.now()
        timeout_threshold = now - timedelta(minutes=self.session_timeout_minutes)

        expired_sessions = []

        async with self._lock:
            for session_id, session in self._sessions.items():
                if session.last_activity < timeout_threshold and session.state not in [
                    ComponentState.DISCONNECTING,
                    ComponentState.DISCONNECTED,
                ]:
                    expired_sessions.append(session_id)

        # Close expired sessions
        for session_id in expired_sessions:
            await self.close_session(session_id, "Session timeout")
            logger.debug(f"Closed expired session {session_id}")

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    async def _notify_session_created(self, session: SessionInfo) -> None:
        """Notify session created handlers."""
        for handler in self._session_created_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session)
                else:
                    handler(session)
            except Exception as e:
                logger.error(f"Error in session created handler: {e}")

    async def _notify_session_destroyed(
        self, session: SessionInfo, reason: str
    ) -> None:
        """Notify session destroyed handlers."""
        for handler in self._session_destroyed_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session, reason)
                else:
                    handler(session, reason)
            except Exception as e:
                logger.error(f"Error in session destroyed handler: {e}")

    async def _notify_session_state_changed(
        self, session_id: str, old_state: ComponentState, new_state: ComponentState
    ) -> None:
        """Notify session state changed handlers."""
        for handler in self._session_state_changed_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session_id, old_state, new_state)
                else:
                    handler(session_id, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in session state changed handler: {e}")
