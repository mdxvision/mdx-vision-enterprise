"""
Tests for Token Refresh Service (Issue #65)

Tests cover:
- Token storage and retrieval
- Token expiration detection
- Token refresh logic
- Retry with exponential backoff
- Background refresh job
- API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os
import time
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from token_refresh import (
    TokenRefreshService, TokenRefreshJob, EHRToken, TokenStatus,
    get_token_service
)


class TestEHRToken:
    """Tests for EHRToken dataclass."""

    def test_token_creation(self):
        """Should create token with all fields."""
        token = EHRToken(
            ehr="cerner",
            access_token="test_access_token",
            expires_in=3600,
            expires_at=time.time() + 3600,
            refresh_token="test_refresh_token"
        )

        assert token.ehr == "cerner"
        assert token.access_token == "test_access_token"
        assert token.refresh_token == "test_refresh_token"

    def test_is_expired_false(self):
        """Non-expired token should return False."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() + 3600
        )

        assert not token.is_expired()

    def test_is_expired_true(self):
        """Expired token should return True."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() - 100
        )

        assert token.is_expired()

    def test_is_expiring_soon_true(self):
        """Token expiring within buffer should return True."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() + 60  # Expires in 60 seconds
        )

        assert token.is_expiring_soon(buffer_seconds=300)

    def test_is_expiring_soon_false(self):
        """Token not expiring within buffer should return False."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() + 3600  # Expires in 1 hour
        )

        assert not token.is_expiring_soon(buffer_seconds=300)

    def test_time_until_expiry(self):
        """Should return seconds until expiry."""
        future_time = time.time() + 1800  # 30 minutes
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=future_time
        )

        time_left = token.time_until_expiry()
        assert 1790 < time_left <= 1800

    def test_time_until_expiry_expired(self):
        """Should return 0 for expired token."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() - 100
        )

        assert token.time_until_expiry() == 0

    def test_get_status_valid(self):
        """Should return VALID for non-expiring token."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() + 3600
        )

        assert token.get_status() == TokenStatus.VALID

    def test_get_status_expiring_soon(self):
        """Should return EXPIRING_SOON for token expiring within buffer."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() + 60
        )

        assert token.get_status(buffer_seconds=300) == TokenStatus.EXPIRING_SOON

    def test_get_status_expired(self):
        """Should return EXPIRED for expired token."""
        token = EHRToken(
            ehr="test",
            access_token="token",
            expires_at=time.time() - 100
        )

        assert token.get_status() == TokenStatus.EXPIRED

    def test_to_dict(self):
        """Should convert to dictionary."""
        token = EHRToken(
            ehr="test",
            access_token="token123",
            expires_at=1234567890.0
        )

        d = token.to_dict()
        assert d["ehr"] == "test"
        assert d["access_token"] == "token123"
        assert d["expires_at"] == 1234567890.0

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "ehr": "epic",
            "access_token": "token_xyz",
            "expires_in": 3600,
            "expires_at": 9999999999.0,
            "refresh_token": "refresh_xyz"
        }

        token = EHRToken.from_dict(data)
        assert token.ehr == "epic"
        assert token.access_token == "token_xyz"
        assert token.refresh_token == "refresh_xyz"


class TestTokenRefreshService:
    """Tests for TokenRefreshService."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create service with temp storage."""
        return TokenRefreshService(storage_path=str(tmp_path / "tokens.json"))

    def test_store_token(self, service):
        """Should store token from OAuth response."""
        token_data = {
            "access_token": "access_123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_456"
        }

        token = service.store_token("cerner", token_data)

        assert token.access_token == "access_123"
        assert token.refresh_token == "refresh_456"
        assert token.ehr == "cerner"

    def test_get_token(self, service):
        """Should retrieve stored token."""
        service.store_token("epic", {
            "access_token": "epic_token",
            "expires_in": 3600
        })

        token = service.get_token("epic")
        assert token is not None
        assert token.access_token == "epic_token"

    def test_get_token_unknown(self, service):
        """Should return None for unknown EHR."""
        assert service.get_token("unknown") is None

    def test_get_valid_token(self, service):
        """Should return access token if valid."""
        service.store_token("test", {
            "access_token": "valid_token",
            "expires_in": 3600
        })

        token = service.get_valid_token("test")
        assert token == "valid_token"

    def test_get_valid_token_expired(self, service):
        """Should return None if token expired."""
        # Store token that's already expired
        service.store_token("test", {
            "access_token": "expired_token",
            "expires_in": -100  # Negative = already expired
        })

        token = service.get_valid_token("test")
        assert token is None

    def test_get_token_status(self, service):
        """Should return detailed token status."""
        service.store_token("cerner", {
            "access_token": "test_token",
            "expires_in": 3600,
            "refresh_token": "refresh_token"
        })

        status = service.get_token_status("cerner")

        assert status["ehr"] == "cerner"
        assert status["status"] == "valid"
        assert status["has_refresh_token"] is True
        assert "expires_in_seconds" in status
        assert "expires_in_human" in status

    def test_get_token_status_not_found(self, service):
        """Should return not_found status for unknown EHR."""
        status = service.get_token_status("unknown")
        assert status["status"] == "not_found"

    def test_list_tokens(self, service):
        """Should list all stored tokens."""
        service.store_token("cerner", {"access_token": "a", "expires_in": 3600})
        service.store_token("epic", {"access_token": "b", "expires_in": 3600})

        tokens = service.list_tokens()
        assert len(tokens) == 2
        ehrs = [t["ehr"] for t in tokens]
        assert "cerner" in ehrs
        assert "epic" in ehrs

    def test_revoke_token(self, service):
        """Should remove token."""
        service.store_token("test", {"access_token": "token", "expires_in": 3600})

        assert service.revoke_token("test") is True
        assert service.get_token("test") is None

    def test_revoke_token_not_found(self, service):
        """Should return False for unknown token."""
        assert service.revoke_token("unknown") is False

    def test_persistence(self, tmp_path):
        """Tokens should persist to file."""
        storage_path = str(tmp_path / "tokens.json")

        # Create service and store token
        service1 = TokenRefreshService(storage_path=storage_path)
        service1.store_token("persist_test", {
            "access_token": "persistent_token",
            "expires_in": 3600
        })

        # Create new service instance
        service2 = TokenRefreshService(storage_path=storage_path)
        token = service2.get_token("persist_test")

        assert token is not None
        assert token.access_token == "persistent_token"

    def test_format_duration_seconds(self, service):
        """Should format seconds correctly."""
        assert "seconds" in service._format_duration(45)

    def test_format_duration_minutes(self, service):
        """Should format minutes correctly."""
        assert "minutes" in service._format_duration(300)

    def test_format_duration_hours(self, service):
        """Should format hours correctly."""
        assert "hours" in service._format_duration(7200)

    def test_format_duration_days(self, service):
        """Should format days correctly."""
        assert "days" in service._format_duration(172800)

    def test_format_duration_expired(self, service):
        """Should return 'expired' for zero or negative."""
        assert service._format_duration(0) == "expired"
        assert service._format_duration(-10) == "expired"


class TestTokenRefreshJob:
    """Tests for background refresh job."""

    @pytest.fixture
    def service(self, tmp_path):
        return TokenRefreshService(storage_path=str(tmp_path / "tokens.json"))

    @pytest.fixture
    def job(self, service):
        return TokenRefreshJob(service, check_interval=0.1)

    def test_job_init(self, job):
        """Job should initialize correctly."""
        assert job.check_interval == 0.1
        assert not job._running

    @pytest.mark.asyncio
    async def test_start_stop(self, job):
        """Job should start and stop."""
        await job.start()
        assert job._running

        await job.stop()
        assert not job._running


class TestTokenRefreshEndpoints:
    """Integration tests for token refresh API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_list_tokens_endpoint(self, client):
        """GET /api/v1/auth/tokens should return token list."""
        response = client.get("/api/v1/auth/tokens")

        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert isinstance(data["tokens"], list)

    def test_get_token_status_not_found(self, client):
        """GET /api/v1/auth/tokens/{ehr} should return 404 for unknown."""
        response = client.get("/api/v1/auth/tokens/nonexistent_ehr")
        assert response.status_code == 404

    def test_refresh_token_not_found(self, client):
        """POST /api/v1/auth/tokens/{ehr}/refresh should return 404."""
        response = client.post("/api/v1/auth/tokens/nonexistent/refresh")
        assert response.status_code == 404

    def test_refresh_all_endpoint(self, client):
        """POST /api/v1/auth/tokens/refresh-all should return results."""
        response = client.post("/api/v1/auth/tokens/refresh-all")

        assert response.status_code == 200
        data = response.json()
        assert "checked" in data
        assert "refreshed" in data
        assert "failed" in data
        assert "skipped" in data

    def test_revoke_token_not_found(self, client):
        """DELETE /api/v1/auth/tokens/{ehr} should return 404."""
        response = client.delete("/api/v1/auth/tokens/nonexistent")
        assert response.status_code == 404


class TestTokenStatus:
    """Tests for TokenStatus enum."""

    def test_status_values(self):
        """TokenStatus should have expected values."""
        assert TokenStatus.VALID.value == "valid"
        assert TokenStatus.EXPIRING_SOON.value == "expiring_soon"
        assert TokenStatus.EXPIRED.value == "expired"
        assert TokenStatus.REFRESH_FAILED.value == "refresh_failed"
        assert TokenStatus.NO_REFRESH_TOKEN.value == "no_refresh_token"


class TestTokenRefreshLogic:
    """Tests for token refresh logic."""

    @pytest.fixture
    def service(self, tmp_path):
        return TokenRefreshService(storage_path=str(tmp_path / "tokens.json"))

    @pytest.mark.asyncio
    async def test_refresh_without_refresh_token(self, service):
        """Should fail if no refresh token."""
        service.store_token("test", {
            "access_token": "token",
            "expires_in": 60  # Expiring soon
            # No refresh_token
        })

        success, message = await service.refresh_token("test")

        assert not success
        assert "No refresh token" in message

    @pytest.mark.asyncio
    async def test_refresh_unknown_ehr(self, service):
        """Should fail for unknown EHR."""
        success, message = await service.refresh_token("unknown")

        assert not success
        assert "No token found" in message

    @pytest.mark.asyncio
    async def test_check_and_refresh_expiring(self, service):
        """Should identify expiring tokens."""
        # Store a token that's expiring soon
        service.store_token("expiring", {
            "access_token": "token",
            "expires_in": 60,  # 1 minute - within 5 min buffer
            "refresh_token": "refresh"
        })

        # Store a token that's not expiring
        service.store_token("valid", {
            "access_token": "token2",
            "expires_in": 7200  # 2 hours
        })

        results = await service.check_and_refresh_expiring()

        assert results["checked"] == 2
        # The expiring one should be attempted (will fail without real endpoint)
        # The valid one should be skipped


class TestTokenRefreshRetry:
    """Tests for retry logic."""

    def test_retry_settings(self):
        """Service should have retry settings."""
        service = TokenRefreshService()

        assert service.MAX_RETRIES == 3
        assert service.INITIAL_RETRY_DELAY == 1.0
        assert service.MAX_RETRY_DELAY == 30.0

    def test_refresh_buffer(self):
        """Service should have refresh buffer setting."""
        service = TokenRefreshService()
        assert service.REFRESH_BUFFER_SECONDS == 300  # 5 minutes
