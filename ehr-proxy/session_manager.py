"""
MDx Vision - TTL-Based Session Manager

Provides memory-safe session storage with automatic cleanup of stale sessions.
Prevents memory leaks from orphaned sessions (client crashes, network drops).

Usage:
    manager = SessionManager(default_ttl=7200)  # 2 hour TTL
    await manager.start()  # Start background cleanup

    # Store session
    await manager.set("session-123", session_data)

    # Get session (extends TTL on access)
    session = await manager.get("session-123")

    # Touch session (extend TTL without retrieving)
    await manager.touch("session-123")

    # Remove session
    await manager.remove("session-123")

    # Shutdown
    await manager.stop()
"""

import asyncio
import time
import logging
from typing import TypeVar, Generic, Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class SessionEntry(Generic[T]):
    """Wrapper for session data with TTL tracking"""
    data: T
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    ttl_seconds: int = 7200  # 2 hours default

    @property
    def expires_at(self) -> float:
        """Calculate expiration timestamp"""
        return self.last_activity + self.ttl_seconds

    @property
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Get session age in seconds"""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """Get seconds since last activity"""
        return time.time() - self.last_activity

    def touch(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = time.time()


class SessionManager(Generic[T]):
    """
    Thread-safe session manager with TTL-based automatic cleanup.

    Features:
    - Configurable TTL per session
    - Automatic background cleanup of expired sessions
    - Touch-on-access to extend session lifetime
    - Async cleanup callbacks for proper resource disposal
    - Stats and monitoring support
    """

    def __init__(
        self,
        default_ttl: int = 7200,  # 2 hours
        cleanup_interval: int = 300,  # 5 minutes
        max_sessions: int = 10000,  # Maximum concurrent sessions
        on_expire: Optional[Callable[[str, T], Awaitable[None]]] = None
    ):
        """
        Initialize the session manager.

        Args:
            default_ttl: Default session TTL in seconds (default: 2 hours)
            cleanup_interval: How often to run cleanup in seconds (default: 5 minutes)
            max_sessions: Maximum number of concurrent sessions
            on_expire: Async callback when session expires (for cleanup)
        """
        self._sessions: Dict[str, SessionEntry[T]] = {}
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._max_sessions = max_sessions
        self._on_expire = on_expire
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False

        # Stats
        self._stats = {
            "sessions_created": 0,
            "sessions_expired": 0,
            "sessions_removed": 0,
            "cleanup_runs": 0,
        }

    async def start(self) -> None:
        """Start the background cleanup task"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"SessionManager started (TTL={self._default_ttl}s, cleanup_interval={self._cleanup_interval}s)")

    async def stop(self) -> None:
        """Stop the background cleanup task and clear all sessions"""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Clean up all remaining sessions
        async with self._lock:
            for session_id, entry in list(self._sessions.items()):
                if self._on_expire:
                    try:
                        await self._on_expire(session_id, entry.data)
                    except Exception as e:
                        logger.error(f"Error in on_expire callback for {session_id}: {e}")
            self._sessions.clear()

        logger.info("SessionManager stopped")

    async def set(
        self,
        session_id: str,
        data: T,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store a session with TTL.

        Args:
            session_id: Unique session identifier
            data: Session data to store
            ttl: Optional custom TTL (uses default if not specified)

        Returns:
            True if stored, False if max sessions reached
        """
        async with self._lock:
            # Check max sessions limit (unless updating existing)
            if session_id not in self._sessions and len(self._sessions) >= self._max_sessions:
                logger.warning(f"Max sessions ({self._max_sessions}) reached, rejecting new session {session_id}")
                return False

            entry = SessionEntry(
                data=data,
                ttl_seconds=ttl or self._default_ttl
            )
            self._sessions[session_id] = entry
            self._stats["sessions_created"] += 1

        logger.debug(f"Session {session_id} created (TTL={entry.ttl_seconds}s)")
        return True

    async def get(
        self,
        session_id: str,
        touch: bool = True
    ) -> Optional[T]:
        """
        Get session data by ID.

        Args:
            session_id: Session identifier
            touch: Whether to extend TTL on access (default: True)

        Returns:
            Session data or None if not found/expired
        """
        async with self._lock:
            entry = self._sessions.get(session_id)

            if entry is None:
                return None

            if entry.is_expired:
                # Remove expired session
                await self._expire_session(session_id, entry)
                return None

            if touch:
                entry.touch()

            return entry.data

    async def touch(self, session_id: str) -> bool:
        """
        Extend session TTL without retrieving data.

        Args:
            session_id: Session identifier

        Returns:
            True if session found and touched, False otherwise
        """
        async with self._lock:
            entry = self._sessions.get(session_id)

            if entry is None or entry.is_expired:
                return False

            entry.touch()
            return True

    async def remove(self, session_id: str) -> Optional[T]:
        """
        Remove a session and return its data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        async with self._lock:
            entry = self._sessions.pop(session_id, None)

            if entry is None:
                return None

            self._stats["sessions_removed"] += 1
            logger.debug(f"Session {session_id} removed (age={entry.age_seconds:.1f}s)")
            return entry.data

    async def exists(self, session_id: str) -> bool:
        """Check if a session exists and is not expired"""
        async with self._lock:
            entry = self._sessions.get(session_id)
            return entry is not None and not entry.is_expired

    async def get_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata without touching it"""
        async with self._lock:
            entry = self._sessions.get(session_id)

            if entry is None:
                return None

            return {
                "session_id": session_id,
                "created_at": entry.created_at,
                "last_activity": entry.last_activity,
                "age_seconds": entry.age_seconds,
                "idle_seconds": entry.idle_seconds,
                "ttl_seconds": entry.ttl_seconds,
                "expires_at": entry.expires_at,
                "is_expired": entry.is_expired,
            }

    @property
    def count(self) -> int:
        """Get current number of sessions"""
        return len(self._sessions)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        return {
            **self._stats,
            "active_sessions": len(self._sessions),
            "max_sessions": self._max_sessions,
            "default_ttl": self._default_ttl,
            "cleanup_interval": self._cleanup_interval,
        }

    async def list_sessions(self) -> list:
        """List all active session IDs"""
        async with self._lock:
            return [
                session_id for session_id, entry in self._sessions.items()
                if not entry.is_expired
            ]

    async def _cleanup_loop(self) -> None:
        """Background task that periodically cleans up expired sessions"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count of removed sessions."""
        expired_sessions = []

        async with self._lock:
            self._stats["cleanup_runs"] += 1

            # Find expired sessions
            for session_id, entry in list(self._sessions.items()):
                if entry.is_expired:
                    expired_sessions.append((session_id, entry))

        # Process expired sessions (outside lock to allow callbacks)
        for session_id, entry in expired_sessions:
            await self._expire_session(session_id, entry)

        if expired_sessions:
            logger.info(f"Cleanup removed {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    async def _expire_session(self, session_id: str, entry: SessionEntry[T]) -> None:
        """Handle session expiration"""
        # Remove from dict
        async with self._lock:
            self._sessions.pop(session_id, None)
            self._stats["sessions_expired"] += 1

        # Call cleanup callback
        if self._on_expire:
            try:
                await self._on_expire(session_id, entry.data)
            except Exception as e:
                logger.error(f"Error in on_expire callback for {session_id}: {e}")

        logger.debug(f"Session {session_id} expired (age={entry.age_seconds:.1f}s, idle={entry.idle_seconds:.1f}s)")


# Singleton instances for different session types
_transcription_session_manager: Optional[SessionManager] = None
_general_session_manager: Optional[SessionManager] = None


async def get_transcription_session_manager() -> SessionManager:
    """Get or create the transcription session manager singleton"""
    global _transcription_session_manager

    if _transcription_session_manager is None:
        async def on_transcription_expire(session_id: str, session: Any) -> None:
            """Cleanup callback for expired transcription sessions"""
            logger.info(f"Cleaning up expired transcription session: {session_id}")
            try:
                if hasattr(session, 'stop'):
                    await session.stop()
                elif hasattr(session, 'is_active'):
                    session.is_active = False
            except Exception as e:
                logger.error(f"Error stopping expired session {session_id}: {e}")

        _transcription_session_manager = SessionManager(
            default_ttl=7200,  # 2 hours
            cleanup_interval=300,  # 5 minutes
            max_sessions=1000,
            on_expire=on_transcription_expire
        )
        await _transcription_session_manager.start()

    return _transcription_session_manager


async def get_general_session_manager() -> SessionManager:
    """Get or create the general session manager singleton"""
    global _general_session_manager

    if _general_session_manager is None:
        _general_session_manager = SessionManager(
            default_ttl=3600,  # 1 hour
            cleanup_interval=300,  # 5 minutes
            max_sessions=5000,
        )
        await _general_session_manager.start()

    return _general_session_manager


async def shutdown_session_managers() -> None:
    """Shutdown all session managers (call on app shutdown)"""
    global _transcription_session_manager, _general_session_manager

    if _transcription_session_manager:
        await _transcription_session_manager.stop()
        _transcription_session_manager = None

    if _general_session_manager:
        await _general_session_manager.stop()
        _general_session_manager = None

    logger.info("All session managers shut down")
