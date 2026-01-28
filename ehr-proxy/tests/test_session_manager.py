"""
Tests for TTL-based Session Manager (Issue #10 - Memory Leak Fix)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch


class TestSessionEntry:
    """Tests for SessionEntry dataclass"""

    def test_session_entry_creation(self):
        """Should create entry with default values"""
        from session_manager import SessionEntry

        data = {"key": "value"}
        entry = SessionEntry(data=data)

        assert entry.data == data
        assert entry.ttl_seconds == 7200  # Default 2 hours
        assert entry.created_at > 0
        assert entry.last_activity > 0

    def test_session_entry_custom_ttl(self):
        """Should accept custom TTL"""
        from session_manager import SessionEntry

        entry = SessionEntry(data={}, ttl_seconds=3600)
        assert entry.ttl_seconds == 3600

    def test_session_entry_is_expired(self):
        """Should correctly detect expired sessions"""
        from session_manager import SessionEntry

        # Create entry with 1 second TTL
        entry = SessionEntry(data={}, ttl_seconds=1)
        assert not entry.is_expired

        # Manually set last_activity to past
        entry.last_activity = time.time() - 2
        assert entry.is_expired

    def test_session_entry_touch(self):
        """Should update last_activity on touch"""
        from session_manager import SessionEntry

        entry = SessionEntry(data={})
        old_activity = entry.last_activity

        time.sleep(0.01)
        entry.touch()

        assert entry.last_activity > old_activity

    def test_session_entry_age_seconds(self):
        """Should calculate age correctly"""
        from session_manager import SessionEntry

        entry = SessionEntry(data={})
        entry.created_at = time.time() - 100

        assert 99 < entry.age_seconds < 101

    def test_session_entry_idle_seconds(self):
        """Should calculate idle time correctly"""
        from session_manager import SessionEntry

        entry = SessionEntry(data={})
        entry.last_activity = time.time() - 50

        assert 49 < entry.idle_seconds < 51

    def test_session_entry_expires_at(self):
        """Should calculate expiration timestamp correctly"""
        from session_manager import SessionEntry

        entry = SessionEntry(data={}, ttl_seconds=3600)
        expected_expiry = entry.last_activity + 3600

        assert abs(entry.expires_at - expected_expiry) < 0.01


class TestSessionManager:
    """Tests for SessionManager class"""

    @pytest.fixture
    def manager(self):
        """Create a session manager for testing"""
        from session_manager import SessionManager

        return SessionManager(
            default_ttl=60,  # 1 minute for faster testing
            cleanup_interval=1,  # 1 second cleanup
            max_sessions=100
        )

    @pytest.mark.asyncio
    async def test_set_and_get(self, manager):
        """Should store and retrieve sessions"""
        await manager.set("test-1", {"data": "value"})
        result = await manager.get("test-1")

        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, manager):
        """Should return None for nonexistent sessions"""
        result = await manager.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove(self, manager):
        """Should remove and return session"""
        await manager.set("test-1", {"data": "value"})
        result = await manager.remove("test-1")

        assert result == {"data": "value"}
        assert await manager.get("test-1") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, manager):
        """Should return None when removing nonexistent session"""
        result = await manager.remove("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, manager):
        """Should check session existence"""
        await manager.set("test-1", {})

        assert await manager.exists("test-1")
        assert not await manager.exists("nonexistent")

    @pytest.mark.asyncio
    async def test_touch_extends_ttl(self, manager):
        """Should extend TTL on touch"""
        await manager.set("test-1", {})

        # Get initial last_activity
        info1 = await manager.get_info("test-1")
        old_activity = info1["last_activity"]

        await asyncio.sleep(0.01)
        await manager.touch("test-1")

        info2 = await manager.get_info("test-1")
        assert info2["last_activity"] > old_activity

    @pytest.mark.asyncio
    async def test_touch_nonexistent(self, manager):
        """Should return False for nonexistent session"""
        result = await manager.touch("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_with_touch(self, manager):
        """Should touch session on get by default"""
        await manager.set("test-1", {})

        info1 = await manager.get_info("test-1")
        old_activity = info1["last_activity"]

        await asyncio.sleep(0.01)
        await manager.get("test-1", touch=True)

        info2 = await manager.get_info("test-1")
        assert info2["last_activity"] > old_activity

    @pytest.mark.asyncio
    async def test_get_without_touch(self, manager):
        """Should not touch when touch=False"""
        await manager.set("test-1", {})

        info1 = await manager.get_info("test-1")
        old_activity = info1["last_activity"]

        await asyncio.sleep(0.01)
        await manager.get("test-1", touch=False)

        info2 = await manager.get_info("test-1")
        assert info2["last_activity"] == old_activity

    @pytest.mark.asyncio
    async def test_custom_ttl(self, manager):
        """Should accept custom TTL per session"""
        await manager.set("test-1", {}, ttl=120)

        info = await manager.get_info("test-1")
        assert info["ttl_seconds"] == 120

    @pytest.mark.asyncio
    async def test_max_sessions_limit(self, manager):
        """Should reject new sessions when max reached"""
        from session_manager import SessionManager

        small_manager = SessionManager(max_sessions=3)

        assert await small_manager.set("s1", {})
        assert await small_manager.set("s2", {})
        assert await small_manager.set("s3", {})
        # Should reject 4th session
        assert not await small_manager.set("s4", {})

    @pytest.mark.asyncio
    async def test_update_existing_session(self, manager):
        """Should allow updating existing session even at max"""
        from session_manager import SessionManager

        small_manager = SessionManager(max_sessions=2)

        await small_manager.set("s1", {"v": 1})
        await small_manager.set("s2", {"v": 2})

        # Should allow update to existing
        assert await small_manager.set("s1", {"v": "updated"})
        result = await small_manager.get("s1")
        assert result == {"v": "updated"}

    @pytest.mark.asyncio
    async def test_count(self, manager):
        """Should track session count"""
        assert manager.count == 0

        await manager.set("s1", {})
        assert manager.count == 1

        await manager.set("s2", {})
        assert manager.count == 2

        await manager.remove("s1")
        assert manager.count == 1

    @pytest.mark.asyncio
    async def test_stats(self, manager):
        """Should track statistics"""
        await manager.set("s1", {})
        await manager.set("s2", {})
        await manager.remove("s1")

        stats = manager.stats
        assert stats["sessions_created"] == 2
        assert stats["sessions_removed"] == 1
        assert stats["active_sessions"] == 1

    @pytest.mark.asyncio
    async def test_list_sessions(self, manager):
        """Should list active session IDs"""
        await manager.set("s1", {})
        await manager.set("s2", {})
        await manager.set("s3", {})

        sessions = await manager.list_sessions()
        assert set(sessions) == {"s1", "s2", "s3"}

    @pytest.mark.asyncio
    async def test_get_info(self, manager):
        """Should return session metadata"""
        await manager.set("test-1", {}, ttl=3600)

        info = await manager.get_info("test-1")

        assert info["session_id"] == "test-1"
        assert info["ttl_seconds"] == 3600
        assert "created_at" in info
        assert "last_activity" in info
        assert "age_seconds" in info
        assert "idle_seconds" in info
        assert "expires_at" in info
        assert info["is_expired"] is False

    @pytest.mark.asyncio
    async def test_get_info_nonexistent(self, manager):
        """Should return None for nonexistent session info"""
        info = await manager.get_info("nonexistent")
        assert info is None


class TestSessionManagerCleanup:
    """Tests for automatic cleanup functionality"""

    @pytest.mark.asyncio
    async def test_expired_session_returns_none(self):
        """Should return None for expired sessions"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=1)  # 1 second TTL

        await manager.set("test-1", {"data": "value"})
        assert await manager.get("test-1") is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should return None and remove expired session
        result = await manager.get("test-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired(self):
        """Should remove expired sessions during cleanup"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=1, cleanup_interval=0.5)
        await manager.start()

        try:
            await manager.set("test-1", {})
            assert manager.count == 1

            # Wait for expiration and cleanup
            await asyncio.sleep(2)

            # Should be cleaned up
            assert manager.count == 0
            assert manager.stats["sessions_expired"] > 0
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_on_expire_callback(self):
        """Should call on_expire callback when session expires"""
        from session_manager import SessionManager

        expired_sessions = []

        async def on_expire(session_id, data):
            expired_sessions.append((session_id, data))

        manager = SessionManager(
            default_ttl=1,
            cleanup_interval=0.5,
            on_expire=on_expire
        )
        await manager.start()

        try:
            await manager.set("test-1", {"key": "value"})

            # Wait for expiration and cleanup
            await asyncio.sleep(2)

            assert len(expired_sessions) == 1
            assert expired_sessions[0][0] == "test-1"
            assert expired_sessions[0][1] == {"key": "value"}
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Should start and stop cleanup task"""
        from session_manager import SessionManager

        manager = SessionManager()
        assert manager._cleanup_task is None

        await manager.start()
        assert manager._cleanup_task is not None
        assert manager._running is True

        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_stop_clears_sessions(self):
        """Should clear all sessions on stop"""
        from session_manager import SessionManager

        manager = SessionManager()
        await manager.start()

        await manager.set("s1", {})
        await manager.set("s2", {})
        assert manager.count == 2

        await manager.stop()
        assert manager.count == 0

    @pytest.mark.asyncio
    async def test_stop_calls_on_expire(self):
        """Should call on_expire for all sessions on stop"""
        from session_manager import SessionManager

        expired = []

        async def on_expire(session_id, data):
            expired.append(session_id)

        manager = SessionManager(on_expire=on_expire)
        await manager.start()

        await manager.set("s1", {})
        await manager.set("s2", {})

        await manager.stop()

        assert set(expired) == {"s1", "s2"}


class TestSingletonManagers:
    """Tests for singleton session manager instances"""

    @pytest.mark.asyncio
    async def test_get_transcription_session_manager(self):
        """Should return singleton instance"""
        from session_manager import get_transcription_session_manager, shutdown_session_managers

        try:
            manager1 = await get_transcription_session_manager()
            manager2 = await get_transcription_session_manager()

            assert manager1 is manager2
        finally:
            await shutdown_session_managers()

    @pytest.mark.asyncio
    async def test_get_general_session_manager(self):
        """Should return singleton instance"""
        from session_manager import get_general_session_manager, shutdown_session_managers

        try:
            manager1 = await get_general_session_manager()
            manager2 = await get_general_session_manager()

            assert manager1 is manager2
        finally:
            await shutdown_session_managers()

    @pytest.mark.asyncio
    async def test_shutdown_session_managers(self):
        """Should shutdown all managers"""
        from session_manager import (
            get_transcription_session_manager,
            get_general_session_manager,
            shutdown_session_managers,
            _transcription_session_manager,
            _general_session_manager
        )
        import session_manager

        # Initialize both
        await get_transcription_session_manager()
        await get_general_session_manager()

        assert session_manager._transcription_session_manager is not None
        assert session_manager._general_session_manager is not None

        # Shutdown
        await shutdown_session_managers()

        assert session_manager._transcription_session_manager is None
        assert session_manager._general_session_manager is None


class TestTranscriptionIntegration:
    """Integration tests with transcription module"""

    @pytest.mark.asyncio
    async def test_create_session_uses_manager(self):
        """Should store session in TTL manager"""
        from transcription import create_session, _active_sessions, get_session_stats
        from session_manager import shutdown_session_managers

        try:
            # Create a mock session that doesn't need real provider
            with patch('transcription.TranscriptionSession') as MockSession:
                mock_instance = MagicMock()
                mock_instance.start = AsyncMock()
                MockSession.return_value = mock_instance

                session = await create_session("test-session-001")

                # Should be in legacy dict
                assert "test-session-001" in _active_sessions

                # Should be tracked in stats
                stats = await get_session_stats()
                assert stats["active_sessions"] >= 1
        finally:
            # Cleanup
            _active_sessions.pop("test-session-001", None)
            await shutdown_session_managers()

    @pytest.mark.asyncio
    async def test_touch_session(self):
        """Should extend session TTL"""
        from transcription import touch_session
        from session_manager import shutdown_session_managers, get_transcription_session_manager

        try:
            manager = await get_transcription_session_manager()
            await manager.set("touch-test", {"data": "value"})

            result = await touch_session("touch-test")
            assert result is True

            result = await touch_session("nonexistent")
            assert result is False
        finally:
            await shutdown_session_managers()
