"""
WebSocket Connection Leak Tests (Issue #58)

Tests to detect and prevent WebSocket connection leaks in the ehr-proxy service.
Ensures proper connection cleanup and resource management.

Test Categories:
1. Connection Lifecycle - normal open/close, abnormal disconnection
2. Resource Tracking - session tracking, cleanup verification
3. Load Testing - sequential/concurrent connections, abandonment
4. Memory Leak Detection - heap growth, garbage collection
"""

import pytest
import asyncio
import gc
import sys
import time
import tracemalloc
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    """Tests for WebSocket connection lifecycle management"""

    @pytest.fixture
    def session_manager(self):
        """Create a test session manager"""
        from session_manager import SessionManager
        return SessionManager(
            default_ttl=60,
            cleanup_interval=1,
            max_sessions=100
        )

    @pytest.mark.asyncio
    async def test_normal_connection_open_close(self, session_manager):
        """Should properly handle normal connection open/close cycle"""
        await session_manager.start()

        try:
            # Simulate connection open
            session_id = "test-session-1"
            await session_manager.set(session_id, {"websocket": "mock_ws"})

            assert await session_manager.exists(session_id)
            assert session_manager.count == 1

            # Simulate connection close
            await session_manager.remove(session_id)

            assert not await session_manager.exists(session_id)
            assert session_manager.count == 0
        finally:
            await session_manager.stop()

    @pytest.mark.asyncio
    async def test_abnormal_disconnection_cleanup(self, session_manager):
        """Should cleanup on abnormal disconnection (network failure simulation)"""
        from session_manager import SessionManager

        await session_manager.start()

        try:
            # Create session with short TTL
            short_ttl_manager = SessionManager(
                default_ttl=1,  # 1 second TTL
                cleanup_interval=1,
                max_sessions=100
            )
            await short_ttl_manager.start()

            # Simulate connection
            session_id = "abandoned-session"
            await short_ttl_manager.set(session_id, {"websocket": "mock_ws"})

            assert await short_ttl_manager.exists(session_id)

            # Wait for TTL to expire (simulating client disappearing)
            await asyncio.sleep(2.5)

            # Session should be cleaned up
            assert not await short_ttl_manager.exists(session_id)
            assert short_ttl_manager.stats["sessions_expired"] >= 1

            await short_ttl_manager.stop()
        finally:
            await session_manager.stop()

    @pytest.mark.asyncio
    async def test_client_initiated_close(self, session_manager):
        """Should handle client-initiated close properly"""
        await session_manager.start()

        try:
            session_id = "client-close-session"
            session_data = {"websocket": "mock_ws", "client_id": "test-client"}

            await session_manager.set(session_id, session_data)

            # Client initiates close
            removed_data = await session_manager.remove(session_id)

            assert removed_data == session_data
            assert session_manager.stats["sessions_removed"] >= 1
            assert session_manager.count == 0
        finally:
            await session_manager.stop()

    @pytest.mark.asyncio
    async def test_server_initiated_close(self, session_manager):
        """Should handle server-initiated close properly"""
        from session_manager import SessionManager

        cleanup_called = []

        async def on_expire(session_id: str, data: Any):
            cleanup_called.append(session_id)

        manager = SessionManager(
            default_ttl=1,
            cleanup_interval=1,
            max_sessions=100,
            on_expire=on_expire
        )
        await manager.start()

        try:
            session_id = "server-close-session"
            await manager.set(session_id, {"websocket": "mock_ws"})

            # Wait for server-side TTL expiration
            await asyncio.sleep(2.5)

            # Callback should have been called
            assert session_id in cleanup_called
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_connection_timeout_scenario(self, session_manager):
        """Should handle connection timeout scenarios"""
        await session_manager.start()

        try:
            # Create multiple sessions
            sessions = []
            for i in range(5):
                session_id = f"timeout-session-{i}"
                await session_manager.set(session_id, {"index": i}, ttl=1)
                sessions.append(session_id)

            # All sessions should exist initially
            assert session_manager.count == 5

            # Wait for timeout
            await asyncio.sleep(2.5)

            # All sessions should be cleaned up
            for session_id in sessions:
                assert not await session_manager.exists(session_id)

            assert session_manager.stats["sessions_expired"] >= 5
        finally:
            await session_manager.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE TRACKING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestResourceTracking:
    """Tests for resource tracking and cleanup verification"""

    @pytest.mark.asyncio
    async def test_all_connections_tracked(self):
        """Should track all connections in active sessions"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=100)
        await manager.start()

        try:
            # Create multiple sessions
            for i in range(10):
                await manager.set(f"tracked-{i}", {"data": i})

            assert manager.count == 10

            # Verify all are listed
            sessions = await manager.list_sessions()
            assert len(sessions) == 10
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_connections_removed_on_close(self):
        """Should remove connections from tracking on close"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=100)
        await manager.start()

        try:
            # Create sessions
            for i in range(10):
                await manager.set(f"remove-{i}", {"data": i})

            assert manager.count == 10

            # Remove half
            for i in range(5):
                await manager.remove(f"remove-{i}")

            assert manager.count == 5
            assert manager.stats["sessions_removed"] == 5
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_no_orphaned_sessions(self):
        """Should have no orphaned session objects after cleanup"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=1, cleanup_interval=1, max_sessions=100)
        await manager.start()

        try:
            # Create and abandon sessions
            for i in range(20):
                await manager.set(f"orphan-{i}", {"data": i})

            # Wait for cleanup
            await asyncio.sleep(3)

            # No sessions should remain
            assert manager.count == 0
            sessions = await manager.list_sessions()
            assert len(sessions) == 0
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_session_info_tracking(self):
        """Should accurately track session metadata"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=3600, cleanup_interval=60, max_sessions=100)
        await manager.start()

        try:
            session_id = "info-track-session"
            await manager.set(session_id, {"test": "data"})

            info = await manager.get_info(session_id)

            assert info is not None
            assert info["session_id"] == session_id
            assert info["ttl_seconds"] == 3600
            assert info["age_seconds"] < 1
            assert info["idle_seconds"] < 1
            assert not info["is_expired"]
        finally:
            await manager.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD TESTING SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadScenarios:
    """Load testing scenarios for WebSocket connections"""

    @pytest.mark.asyncio
    async def test_sequential_connections_100(self):
        """Should handle 100 sequential connections (open/close rapidly)"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=1000)
        await manager.start()

        try:
            start_time = time.time()

            # Rapidly open and close 100 connections
            for i in range(100):
                session_id = f"seq-{i}"
                await manager.set(session_id, {"index": i})
                await manager.remove(session_id)

            elapsed = time.time() - start_time

            # Should complete quickly and have no remaining sessions
            assert manager.count == 0
            assert manager.stats["sessions_created"] == 100
            assert manager.stats["sessions_removed"] == 100
            assert elapsed < 5.0  # Should complete in under 5 seconds
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_concurrent_connections_50(self):
        """Should handle 50 concurrent connections"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=1000)
        await manager.start()

        try:
            # Create 50 concurrent sessions
            async def create_session(i):
                session_id = f"concurrent-{i}"
                await manager.set(session_id, {"index": i})
                await asyncio.sleep(0.1)  # Simulate some work
                return session_id

            sessions = await asyncio.gather(*[create_session(i) for i in range(50)])

            assert manager.count == 50
            assert len(sessions) == 50

            # Close all concurrently
            await asyncio.gather(*[manager.remove(s) for s in sessions])

            assert manager.count == 0
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_connection_abandonment(self):
        """Should handle connection abandonment (client disappears)"""
        from session_manager import SessionManager

        abandoned_sessions = []

        async def on_expire(session_id: str, data: Any):
            abandoned_sessions.append(session_id)

        manager = SessionManager(
            default_ttl=1,
            cleanup_interval=1,
            max_sessions=100,
            on_expire=on_expire
        )
        await manager.start()

        try:
            # Create sessions and "abandon" them
            for i in range(20):
                await manager.set(f"abandoned-{i}", {"index": i})

            assert manager.count == 20

            # Wait for TTL expiration (simulating abandoned connections)
            await asyncio.sleep(3)

            # All should be cleaned up via callback
            assert len(abandoned_sessions) == 20
            assert manager.count == 0
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_reconnection_scenario(self):
        """Should handle reconnection scenarios properly"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=100)
        await manager.start()

        try:
            session_id = "reconnect-session"

            # Initial connection
            await manager.set(session_id, {"version": 1})
            assert (await manager.get(session_id))["version"] == 1

            # Disconnect
            await manager.remove(session_id)
            assert not await manager.exists(session_id)

            # Reconnect with new data
            await manager.set(session_id, {"version": 2})
            assert await manager.exists(session_id)
            assert (await manager.get(session_id))["version"] == 2
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_max_sessions_limit(self):
        """Should enforce max sessions limit"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=10)
        await manager.start()

        try:
            # Create max sessions
            for i in range(10):
                result = await manager.set(f"max-{i}", {"index": i})
                assert result is True

            assert manager.count == 10

            # Try to exceed limit
            result = await manager.set("overflow", {"extra": True})
            assert result is False
            assert manager.count == 10
        finally:
            await manager.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY LEAK DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryLeakDetection:
    """Tests for memory leak detection"""

    @pytest.mark.asyncio
    async def test_memory_stable_during_churn(self):
        """Should have stable memory during connection churn"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=1, max_sessions=1000)
        await manager.start()

        try:
            # Force garbage collection and get baseline
            gc.collect()
            tracemalloc.start()

            # Create and destroy many sessions
            for cycle in range(5):
                for i in range(100):
                    await manager.set(f"churn-{cycle}-{i}", {"data": "x" * 100})

                for i in range(100):
                    await manager.remove(f"churn-{cycle}-{i}")

                gc.collect()

            # Check memory growth
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Memory should not grow excessively (allow 5MB peak)
            assert peak < 5 * 1024 * 1024, f"Memory peak too high: {peak / 1024 / 1024:.2f}MB"
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_garbage_collection_of_closed_sessions(self):
        """Should properly garbage collect closed sessions"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=1, cleanup_interval=1, max_sessions=100)
        await manager.start()

        try:
            # Create sessions with large data
            for i in range(50):
                large_data = {"buffer": "x" * 10000}
                await manager.set(f"gc-{i}", large_data)

            initial_count = manager.count
            assert initial_count == 50

            # Wait for expiration and cleanup
            await asyncio.sleep(3)

            # Force garbage collection
            gc.collect()

            # All sessions should be cleaned
            assert manager.count == 0
            assert manager.stats["sessions_expired"] == 50
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_no_lingering_references(self):
        """Should not have lingering references after cleanup"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=100)
        await manager.start()

        try:
            # Create and remove sessions
            session_id = "linger-test"
            await manager.set(session_id, {"test": "data"})

            # Get reference
            data = await manager.get(session_id)
            assert data is not None

            # Remove session
            await manager.remove(session_id)

            # Verify not in manager
            assert not await manager.exists(session_id)
            assert await manager.get(session_id) is None
        finally:
            await manager.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP CALLBACK TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCleanupCallbacks:
    """Tests for cleanup callback behavior"""

    @pytest.mark.asyncio
    async def test_on_expire_callback_called(self):
        """Should call on_expire callback when session expires"""
        from session_manager import SessionManager

        expired_sessions = []

        async def on_expire(session_id: str, data: Any):
            expired_sessions.append((session_id, data))

        manager = SessionManager(
            default_ttl=1,
            cleanup_interval=1,
            max_sessions=100,
            on_expire=on_expire
        )
        await manager.start()

        try:
            await manager.set("callback-test", {"value": 42})

            # Wait for expiration
            await asyncio.sleep(3)

            assert len(expired_sessions) == 1
            assert expired_sessions[0][0] == "callback-test"
            assert expired_sessions[0][1]["value"] == 42
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_callback_error_handling(self):
        """Should handle errors in cleanup callback gracefully"""
        from session_manager import SessionManager

        async def bad_callback(session_id: str, data: Any):
            raise ValueError("Callback error!")

        manager = SessionManager(
            default_ttl=1,
            cleanup_interval=1,
            max_sessions=100,
            on_expire=bad_callback
        )
        await manager.start()

        try:
            await manager.set("error-callback-test", {"data": 1})

            # Wait for expiration - should not crash
            await asyncio.sleep(3)

            # Manager should still be functional
            assert manager.count == 0
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_callback_called_on_shutdown(self):
        """Should call callbacks for all sessions on shutdown"""
        from session_manager import SessionManager

        shutdown_sessions = []

        async def on_expire(session_id: str, data: Any):
            shutdown_sessions.append(session_id)

        manager = SessionManager(
            default_ttl=3600,  # Long TTL
            cleanup_interval=60,
            max_sessions=100,
            on_expire=on_expire
        )
        await manager.start()

        # Create sessions
        for i in range(5):
            await manager.set(f"shutdown-{i}", {"index": i})

        # Stop manager - should cleanup all sessions
        await manager.stop()

        assert len(shutdown_sessions) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS AND MONITORING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticsMonitoring:
    """Tests for statistics and monitoring capabilities"""

    @pytest.mark.asyncio
    async def test_stats_accuracy(self):
        """Should maintain accurate statistics"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=1, cleanup_interval=1, max_sessions=100)
        await manager.start()

        try:
            # Create sessions
            for i in range(10):
                await manager.set(f"stats-{i}", {"index": i})

            stats = manager.stats
            assert stats["sessions_created"] == 10
            assert stats["active_sessions"] == 10

            # Remove some
            for i in range(5):
                await manager.remove(f"stats-{i}")

            stats = manager.stats
            assert stats["sessions_removed"] == 5
            assert stats["active_sessions"] == 5

            # Wait for expiration of remaining
            await asyncio.sleep(3)

            stats = manager.stats
            assert stats["sessions_expired"] >= 5
            assert stats["active_sessions"] == 0
            assert stats["cleanup_runs"] >= 1
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_count_property(self):
        """Should accurately report session count"""
        from session_manager import SessionManager

        manager = SessionManager(default_ttl=60, cleanup_interval=60, max_sessions=100)
        await manager.start()

        try:
            assert manager.count == 0

            await manager.set("count-1", {})
            assert manager.count == 1

            await manager.set("count-2", {})
            assert manager.count == 2

            await manager.remove("count-1")
            assert manager.count == 1
        finally:
            await manager.stop()
