"""
Security Manager for the Pythonium MCP server.

This manager provides authentication, authorization, API key management,
rate limiting, and audit logging for the system.
"""

import asyncio
import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from pythonium.common.cache import CacheManager, get_cache_manager
from pythonium.common.exceptions import (
    SecurityError,
)
from pythonium.common.logging import get_logger
from pythonium.common.types import MetadataDict
from pythonium.managers.base import BaseManager, ManagerPriority
from pythonium.managers.config_manager import ConfigurationManager

logger = get_logger(__name__)


class AuthenticationMethod(Enum):
    """Authentication methods."""

    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"


class PermissionLevel(Enum):
    """Permission levels."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    FULL = "full"


@dataclass
class APIKey:
    """API key information."""

    key_id: str
    key_hash: str  # Hashed version of the actual key
    name: str
    user_id: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    scopes: Set[str] = field(default_factory=set)
    rate_limit: Optional[int] = None  # requests per hour
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0
    is_active: bool = True
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class User:
    """User information."""

    user_id: str
    username: str
    email: Optional[str] = None
    password_hash: Optional[str] = None  # For basic auth
    permissions: Set[str] = field(default_factory=set)
    roles: Set[str] = field(default_factory=set)
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    login_count: int = 0
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class AuthenticationResult:
    """Result of authentication attempt."""

    success: bool
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    scopes: Set[str] = field(default_factory=set)
    method: Optional[AuthenticationMethod] = None
    error: Optional[str] = None
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class RateLimitInfo:
    """Rate limiting information."""

    key: str
    limit: int
    window: timedelta
    current_count: int = 0
    window_start: datetime = field(default_factory=datetime.utcnow)
    last_request: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AuditLogEntry:
    """Audit log entry."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: str = ""
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: str = ""  # success, failure, error
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: MetadataDict = field(default_factory=dict)


class Authenticator(ABC):
    """Base class for authentication methods."""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationResult:
        """Authenticate using the provided credentials."""
        pass


class APIKeyAuthenticator(Authenticator):
    """API key based authentication."""

    def __init__(self, security_manager: "SecurityManager"):
        self.security_manager = security_manager

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationResult:
        """Authenticate using API key."""
        api_key = credentials.get("api_key")
        if not api_key:
            return AuthenticationResult(success=False, error="API key not provided")

        # Find API key
        key_info = await self.security_manager._find_api_key(api_key)
        if not key_info:
            return AuthenticationResult(success=False, error="Invalid API key")

        # Check if key is active
        if not key_info.is_active:
            return AuthenticationResult(success=False, error="API key is disabled")

        # Check expiration
        if key_info.expires_at and datetime.utcnow() > key_info.expires_at:
            return AuthenticationResult(success=False, error="API key has expired")

        # Update usage
        key_info.last_used = datetime.utcnow()
        key_info.usage_count += 1

        return AuthenticationResult(
            success=True,
            user_id=key_info.user_id,
            api_key_id=key_info.key_id,
            permissions=key_info.permissions,
            scopes=key_info.scopes,
            method=AuthenticationMethod.API_KEY,
        )


class BasicAuthenticator(Authenticator):
    """Basic authentication using username/password."""

    def __init__(self, security_manager: "SecurityManager"):
        self.security_manager = security_manager

    async def authenticate(self, credentials: Dict[str, Any]) -> AuthenticationResult:
        """Authenticate using username/password."""
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            return AuthenticationResult(
                success=False, error="Username or password not provided"
            )

        # Find user
        user = await self.security_manager._find_user_by_username(username)
        if not user:
            return AuthenticationResult(success=False, error="Invalid credentials")

        # Check if user is active
        if not user.is_active:
            return AuthenticationResult(success=False, error="User account is disabled")

        # Verify password
        if not self.security_manager._verify_password(password, user.password_hash):
            return AuthenticationResult(success=False, error="Invalid credentials")

        # Update login info
        user.last_login = datetime.utcnow()
        user.login_count += 1

        return AuthenticationResult(
            success=True,
            user_id=user.user_id,
            permissions=user.permissions,
            method=AuthenticationMethod.BASIC_AUTH,
        )


class RateLimiter:
    """Rate limiting implementation."""

    def __init__(self):
        self._limits: Dict[str, RateLimitInfo] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self, key: str, limit: int, window: timedelta
    ) -> Tuple[bool, int]:
        """Check if request is within rate limits."""
        async with self._lock:
            now = datetime.utcnow()

            if key not in self._limits:
                self._limits[key] = RateLimitInfo(key, limit, window)

            rate_info = self._limits[key]

            # Check if window has expired
            if now - rate_info.window_start > window:
                rate_info.current_count = 0
                rate_info.window_start = now

            # Check limit
            if rate_info.current_count >= limit:
                return False, rate_info.current_count

            # Increment count
            rate_info.current_count += 1
            rate_info.last_request = now

            return True, rate_info.current_count

    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key."""
        async with self._lock:
            if key in self._limits:
                self._limits[key].current_count = 0
                self._limits[key].window_start = datetime.utcnow()

    def get_rate_limit_info(self, key: str) -> Optional[RateLimitInfo]:
        """Get rate limit information for a key."""
        return self._limits.get(key)


class SecurityManager(BaseManager):
    """Comprehensive security management system."""

    def __init__(self):
        super().__init__(
            name="security",
            version="1.0.0",
            description="Authentication, authorization, and security management",
        )
        self._info.priority = ManagerPriority.HIGH

        # Authentication
        self._authenticators: Dict[AuthenticationMethod, Authenticator] = {}
        self._api_keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._api_key_lookup: Dict[str, str] = {}  # key_hash -> key_id
        self._users: Dict[str, User] = {}  # user_id -> User
        self._username_lookup: Dict[str, str] = {}  # username -> user_id

        # Authorization
        self._permissions: Set[str] = set()
        self._roles: Dict[str, Set[str]] = {}  # role -> permissions

        # Rate limiting
        self._rate_limiter = RateLimiter()
        self._default_rate_limits: Dict[str, Tuple[int, timedelta]] = {}

        # Audit logging
        self._audit_log: List[AuditLogEntry] = []
        self._audit_callbacks: List[Callable[[AuditLogEntry], None]] = []
        self._max_audit_entries = 10000

        # Security settings
        self._password_min_length = 8
        self._api_key_length = 32
        self._session_timeout = timedelta(hours=24)
        self._max_login_attempts = 5
        self._lockout_duration = timedelta(minutes=15)

        # Caching
        self._cache_manager: Optional[CacheManager] = None

    async def _initialize(self) -> None:
        """Initialize the security manager."""
        # Set up authenticators
        self._authenticators[AuthenticationMethod.API_KEY] = APIKeyAuthenticator(self)
        self._authenticators[AuthenticationMethod.BASIC_AUTH] = BasicAuthenticator(self)

        # Load configuration
        config_manager = self.get_dependency(ConfigurationManager)
        if config_manager and isinstance(config_manager, ConfigurationManager):
            await self._load_configuration(config_manager)

        # Set up caching
        self._cache_manager = get_cache_manager()

        # Initialize default permissions
        self._permissions.update(
            [
                "read:system",
                "write:system",
                "admin:system",
                "read:plugins",
                "write:plugins",
                "admin:plugins",
                "read:config",
                "write:config",
                "admin:config",
            ]
        )

        # Initialize default roles
        self._roles.update(
            {
                "viewer": {"read:system", "read:plugins", "read:config"},
                "user": {
                    "read:system",
                    "read:plugins",
                    "read:config",
                    "write:plugins",
                },
                "admin": self._permissions.copy(),
            }
        )

    async def _start(self) -> None:
        """Start the security manager."""
        # Create default admin user if none exists
        if not self._users:
            await self._create_default_admin()

        # Emit security manager started event
        await self.emit_event(
            "security_started",
            {
                "authenticators": list(self._authenticators.keys()),
                "users": len(self._users),
                "api_keys": len(self._api_keys),
            },
        )

    async def _stop(self) -> None:
        """Stop the security manager."""
        pass

    async def _cleanup(self) -> None:
        """Cleanup security manager resources."""
        self._api_keys.clear()
        self._api_key_lookup.clear()
        self._users.clear()
        self._username_lookup.clear()
        self._audit_log.clear()
        self._audit_callbacks.clear()

    async def _load_configuration(self, config_manager: ConfigurationManager) -> None:
        """Load security configuration."""
        security_config = config_manager.get("security", {})

        # Authentication settings
        auth_config = security_config.get("authentication", {})
        self._password_min_length = auth_config.get("password_min_length", 8)
        self._api_key_length = auth_config.get("api_key_length", 32)
        self._session_timeout = timedelta(
            hours=auth_config.get("session_timeout_hours", 24)
        )
        self._max_login_attempts = auth_config.get("max_login_attempts", 5)
        self._lockout_duration = timedelta(
            minutes=auth_config.get("lockout_duration_minutes", 15)
        )

        # Rate limiting
        rate_limit_config = security_config.get("rate_limiting", {})
        for key, config in rate_limit_config.items():
            limit = config.get("limit", 100)
            window_minutes = config.get("window_minutes", 60)
            self._default_rate_limits[key] = (
                limit,
                timedelta(minutes=window_minutes),
            )

        # Audit logging
        audit_config = security_config.get("audit", {})
        self._max_audit_entries = audit_config.get("max_entries", 10000)

    async def _create_default_admin(self) -> None:
        """Create default admin user."""
        default_password = "admin123"  # Should be changed immediately

        admin_user = User(
            user_id="admin",
            username="admin",
            email="admin@pythonium.local",
            password_hash=self._hash_password(default_password),
            permissions=self._permissions.copy(),
            is_admin=True,
        )

        await self.create_user(admin_user)
        logger.warning(
            "Created default admin user with password 'admin123' - CHANGE IMMEDIATELY!"
        )

    # Authentication methods

    async def authenticate(
        self, method: AuthenticationMethod, credentials: Dict[str, Any]
    ) -> AuthenticationResult:
        """Authenticate using the specified method."""
        if method not in self._authenticators:
            return AuthenticationResult(
                success=False,
                error=f"Authentication method {method.value} not supported",
            )

        authenticator = self._authenticators[method]
        result = await authenticator.authenticate(credentials)

        # Log authentication attempt
        await self._log_audit_event(
            "authentication",
            user_id=result.user_id,
            api_key_id=result.api_key_id,
            action=method.value,
            result="success" if result.success else "failure",
            details={"error": result.error} if result.error else {},
        )

        return result

    # API Key management

    async def create_api_key(
        self,
        name: str,
        user_id: Optional[str] = None,
        permissions: Optional[Set[str]] = None,
        scopes: Optional[Set[str]] = None,
        rate_limit: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[str, APIKey]:
        """Create a new API key."""
        # Generate key
        raw_key = secrets.token_urlsafe(self._api_key_length)
        key_hash = self._hash_api_key(raw_key)
        key_id = f"ak_{secrets.token_hex(8)}"

        # Create API key object
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            permissions=permissions or set(),
            scopes=scopes or set(),
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        # Store key
        self._api_keys[key_id] = api_key
        self._api_key_lookup[key_hash] = key_id

        # Log creation
        await self._log_audit_event(
            "api_key_created",
            user_id=user_id,
            api_key_id=key_id,
            action="create",
            result="success",
            details={"name": name, "permissions": list(permissions or [])},
        )

        logger.info(f"Created API key: {key_id}")
        return raw_key, api_key

    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id not in self._api_keys:
            return False

        api_key = self._api_keys[key_id]
        api_key.is_active = False

        # Log revocation
        await self._log_audit_event(
            "api_key_revoked",
            api_key_id=key_id,
            action="revoke",
            result="success",
            details={"name": api_key.name},
        )

        logger.info(f"Revoked API key: {key_id}")
        return True

    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key."""
        if key_id not in self._api_keys:
            return False

        api_key = self._api_keys[key_id]

        # Remove from lookups
        self._api_key_lookup.pop(api_key.key_hash, None)
        del self._api_keys[key_id]

        # Log deletion
        await self._log_audit_event(
            "api_key_deleted",
            api_key_id=key_id,
            action="delete",
            result="success",
            details={"name": api_key.name},
        )

        logger.info(f"Deleted API key: {key_id}")
        return True

    async def _find_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Find API key by raw key value."""
        key_hash = self._hash_api_key(raw_key)
        key_id = self._api_key_lookup.get(key_hash)
        if key_id:
            return self._api_keys.get(key_id)
        return None

    def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        return self._api_keys.get(key_id)

    def list_api_keys(self, user_id: Optional[str] = None) -> List[APIKey]:
        """List API keys."""
        keys = list(self._api_keys.values())
        if user_id:
            keys = [key for key in keys if key.user_id == user_id]
        return keys

    # User management

    async def create_user(self, user: User) -> None:
        """Create a new user."""
        if user.user_id in self._users:
            raise SecurityError(f"User {user.user_id} already exists")

        if user.username in self._username_lookup:
            raise SecurityError(f"Username {user.username} already exists")

        self._users[user.user_id] = user
        self._username_lookup[user.username] = user.user_id

        # Log creation
        await self._log_audit_event(
            "user_created",
            user_id=user.user_id,
            action="create",
            result="success",
            details={"username": user.username, "is_admin": user.is_admin},
        )

        logger.info(f"Created user: {user.username}")

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user information."""
        if user_id not in self._users:
            return False

        user = self._users[user_id]
        old_username = user.username

        # Update fields
        for field_name, value in updates.items():
            if hasattr(user, field_name):
                setattr(user, field_name, value)

        # Update username lookup if username changed
        if "username" in updates and updates["username"] != old_username:
            self._username_lookup.pop(old_username, None)
            self._username_lookup[user.username] = user_id

        # Log update
        await self._log_audit_event(
            "user_updated",
            user_id=user_id,
            action="update",
            result="success",
            details={"fields": list(updates.keys())},
        )

        return True

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        if user_id not in self._users:
            return False

        user = self._users[user_id]

        # Remove from lookups
        self._username_lookup.pop(user.username, None)
        del self._users[user_id]

        # Revoke all API keys for this user
        for api_key in list(self._api_keys.values()):
            if api_key.user_id == user_id:
                await self.revoke_api_key(api_key.key_id)

        # Log deletion
        await self._log_audit_event(
            "user_deleted",
            user_id=user_id,
            action="delete",
            result="success",
            details={"username": user.username},
        )

        logger.info(f"Deleted user: {user.username}")
        return True

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    async def _find_user_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        user_id = self._username_lookup.get(username)
        if user_id:
            return self._users.get(user_id)
        return None

    def list_users(self) -> List[User]:
        """List all users."""
        return list(self._users.values())

    # Authorization

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return False

        # Admin users have all permissions
        if user.is_admin:
            return True

        # Check direct permissions
        if permission in user.permissions:
            return True

        # Check role-based permissions
        for role in user.roles:
            role_permissions = self._roles.get(role, set())
            if permission in role_permissions:
                return True

        return False

    def check_api_key_permission(self, api_key_id: str, permission: str) -> bool:
        """Check if API key has a specific permission."""
        api_key = self.get_api_key(api_key_id)
        if not api_key or not api_key.is_active:
            return False

        # Check API key permissions
        if permission in api_key.permissions:
            return True

        # Check user permissions if API key is associated with a user
        if api_key.user_id:
            return self.check_permission(api_key.user_id, permission)

        return False

    def add_permission(self, permission: str) -> None:
        """Add a new permission to the system."""
        self._permissions.add(permission)

    def create_role(self, role: str, permissions: Set[str]) -> None:
        """Create a new role."""
        self._roles[role] = permissions.copy()

    def assign_role_to_user(self, user_id: str, role: str) -> bool:
        """Assign a role to a user."""
        user = self.get_user(user_id)
        if user and role in self._roles:
            user.roles.add(role)
            return True
        return False

    # Rate limiting

    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[timedelta] = None,
    ) -> Tuple[bool, int]:
        """Check rate limit for a key."""
        # Use provided limits or defaults
        if limit is None or window is None:
            default_limit, default_window = self._default_rate_limits.get(
                "default", (100, timedelta(hours=1))
            )
            limit = limit or default_limit
            window = window or default_window

        return await self._rate_limiter.check_rate_limit(key, limit, window)

    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key."""
        await self._rate_limiter.reset_rate_limit(key)

    # Audit logging

    async def _log_audit_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[MetadataDict] = None,
    ) -> None:
        """Log an audit event."""
        entry = AuditLogEntry(
            event_type=event_type,
            user_id=user_id,
            api_key_id=api_key_id,
            resource=resource,
            action=action,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )

        # Add to audit log
        self._audit_log.append(entry)

        # Trim log if it gets too large
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries :]

        # Call audit callbacks
        for callback in self._audit_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(entry)
                else:
                    callback(entry)
            except Exception as e:
                logger.error(f"Error in audit callback: {e}")

    def get_audit_log(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[AuditLogEntry]:
        """Get audit log entries."""
        entries = self._audit_log.copy()

        # Apply filters
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        if user_id:
            entries = [e for e in entries if e.user_id == user_id]

        if since:
            entries = [e for e in entries if e.timestamp >= since]

        # Sort by timestamp (newest first)
        entries.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            entries = entries[:limit]

        return entries

    def add_audit_callback(self, callback: Callable[[AuditLogEntry], None]) -> None:
        """Add an audit log callback."""
        self._audit_callbacks.append(callback)

    def remove_audit_callback(self, callback: Callable[[AuditLogEntry], None]) -> None:
        """Remove an audit log callback."""
        if callback in self._audit_callbacks:
            self._audit_callbacks.remove(callback)

    # Utility methods

    def _hash_password(self, password: str) -> str:
        """Hash a password."""
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return f"{salt}:{pwdhash.hex()}"

    def _verify_password(self, password: str, password_hash: Optional[str]) -> bool:
        """Verify a password against its hash."""
        if not password_hash:
            return False

        try:
            salt, stored_hash = password_hash.split(":")
            pwdhash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                100000,
            )
            return hmac.compare_digest(stored_hash, pwdhash.hex())
        except ValueError:
            return False

    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    # Security utilities

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)

    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password strength."""
        errors = []

        if len(password) < self._password_min_length:
            errors.append(
                f"Password must be at least {self._password_min_length} characters long"
            )

        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors
