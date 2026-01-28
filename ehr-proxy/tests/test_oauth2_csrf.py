"""
Tests for OAuth2 CSRF Protection (Issue #19)
RFC 6749 Section 10.12 - Cross-Site Request Forgery

Tests state parameter generation, storage, validation, and expiration.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    generate_oauth2_state,
    validate_oauth2_state,
    _cleanup_expired_oauth2_states,
    _oauth2_states,
    OAUTH2_STATE_EXPIRY_SECONDS
)


class TestOAuth2StateGeneration:
    """Tests for OAuth2 state parameter generation."""

    def test_generate_state_returns_string(self):
        """State should be a non-empty string."""
        state = generate_oauth2_state(ehr="epic")
        assert isinstance(state, str)
        assert len(state) > 0

    def test_generate_state_is_unique(self):
        """Each generated state should be unique."""
        states = set()
        for _ in range(100):
            state = generate_oauth2_state(ehr="epic")
            assert state not in states, "Generated duplicate state"
            states.add(state)

    def test_generate_state_is_url_safe(self):
        """State should only contain URL-safe characters."""
        import re
        for _ in range(10):
            state = generate_oauth2_state(ehr="epic")
            # URL-safe base64 uses only alphanumeric, hyphen, underscore
            assert re.match(r'^[A-Za-z0-9_-]+$', state), f"State contains non-URL-safe chars: {state}"

    def test_generate_state_has_sufficient_entropy(self):
        """State should have at least 256 bits of entropy (32 bytes = 43+ chars in base64)."""
        state = generate_oauth2_state(ehr="epic")
        # 32 bytes -> ~43 chars in URL-safe base64
        assert len(state) >= 40, f"State too short: {len(state)} chars"

    def test_generate_state_stores_metadata(self):
        """State should be stored with EHR and timestamp."""
        # Clear any existing states
        _oauth2_states.clear()

        state = generate_oauth2_state(ehr="veradigm", user_hint="dr_smith")

        assert state in _oauth2_states
        stored = _oauth2_states[state]
        assert stored["ehr"] == "veradigm"
        assert stored["user_hint"] == "dr_smith"
        assert isinstance(stored["timestamp"], datetime)


class TestOAuth2StateValidation:
    """Tests for OAuth2 state parameter validation."""

    def setup_method(self):
        """Clear state store before each test."""
        _oauth2_states.clear()

    def test_validate_valid_state(self):
        """Valid state should pass validation."""
        state = generate_oauth2_state(ehr="epic")
        is_valid, error = validate_oauth2_state(state, expected_ehr="epic")
        assert is_valid is True
        assert "success" in error.lower()

    def test_validate_missing_state(self):
        """Missing state should fail validation."""
        is_valid, error = validate_oauth2_state(None, expected_ehr="epic")
        assert is_valid is False
        assert "missing" in error.lower() or "csrf" in error.lower()

    def test_validate_empty_state(self):
        """Empty state should fail validation."""
        is_valid, error = validate_oauth2_state("", expected_ehr="epic")
        assert is_valid is False

    def test_validate_unknown_state(self):
        """Unknown state should fail validation."""
        is_valid, error = validate_oauth2_state("unknown_state_12345", expected_ehr="epic")
        assert is_valid is False
        assert "not found" in error.lower() or "invalid" in error.lower()

    def test_validate_ehr_mismatch(self):
        """State with wrong EHR should fail validation."""
        state = generate_oauth2_state(ehr="epic")
        is_valid, error = validate_oauth2_state(state, expected_ehr="veradigm")
        assert is_valid is False
        assert "mismatch" in error.lower()

    def test_validate_state_one_time_use(self):
        """State should only be valid once (prevent replay attacks)."""
        state = generate_oauth2_state(ehr="epic")

        # First validation should succeed
        is_valid1, _ = validate_oauth2_state(state, expected_ehr="epic")
        assert is_valid1 is True

        # Second validation should fail (state consumed)
        is_valid2, error = validate_oauth2_state(state, expected_ehr="epic")
        assert is_valid2 is False
        assert "not found" in error.lower() or "invalid" in error.lower()

    def test_validate_expired_state(self):
        """Expired state should fail validation."""
        state = generate_oauth2_state(ehr="epic")

        # Manually set timestamp to past expiry
        _oauth2_states[state]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=OAUTH2_STATE_EXPIRY_SECONDS + 60)

        is_valid, error = validate_oauth2_state(state, expected_ehr="epic")
        assert is_valid is False
        assert "expired" in error.lower()


class TestOAuth2StateCleanup:
    """Tests for expired state cleanup."""

    def setup_method(self):
        """Clear state store before each test."""
        _oauth2_states.clear()

    def test_cleanup_removes_expired_states(self):
        """Cleanup should remove expired states."""
        # Generate some states
        state1 = generate_oauth2_state(ehr="epic")
        state2 = generate_oauth2_state(ehr="veradigm")

        # Make state1 expired
        _oauth2_states[state1]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=OAUTH2_STATE_EXPIRY_SECONDS + 60)

        # Run cleanup
        _cleanup_expired_oauth2_states()

        # state1 should be removed, state2 should remain
        assert state1 not in _oauth2_states
        assert state2 in _oauth2_states

    def test_cleanup_preserves_valid_states(self):
        """Cleanup should preserve non-expired states."""
        states = [generate_oauth2_state(ehr="epic") for _ in range(5)]

        _cleanup_expired_oauth2_states()

        # All states should still exist
        for state in states:
            assert state in _oauth2_states


class TestOAuth2CSRFAttackPrevention:
    """Tests simulating CSRF attack scenarios."""

    def setup_method(self):
        """Clear state store before each test."""
        _oauth2_states.clear()

    def test_attacker_crafted_state_rejected(self):
        """Attacker-crafted state values should be rejected."""
        # Attacker tries various crafted state values
        attacker_states = [
            "attacker_state",
            "12345678901234567890123456789012",  # 32 chars
            "../../../etc/passwd",
            "<script>alert(1)</script>",
            "null",
            "undefined",
            "true",
            "1; DROP TABLE users;--"
        ]

        for attacker_state in attacker_states:
            is_valid, _ = validate_oauth2_state(attacker_state, expected_ehr="epic")
            assert is_valid is False, f"Attacker state accepted: {attacker_state}"

    def test_stolen_state_wrong_ehr(self):
        """Attacker using stolen state for wrong EHR should fail."""
        # Victim initiates Epic auth
        victim_state = generate_oauth2_state(ehr="epic")

        # Attacker tries to use victim's state for Veradigm callback
        is_valid, error = validate_oauth2_state(victim_state, expected_ehr="veradigm")
        assert is_valid is False
        assert "mismatch" in error.lower()

    def test_replay_attack_prevented(self):
        """Replaying a used state should fail."""
        state = generate_oauth2_state(ehr="epic")

        # Legitimate user completes auth
        is_valid1, _ = validate_oauth2_state(state, expected_ehr="epic")
        assert is_valid1 is True

        # Attacker tries to replay the same state
        is_valid2, _ = validate_oauth2_state(state, expected_ehr="epic")
        assert is_valid2 is False


class TestOAuth2EndpointIntegration:
    """Integration tests for OAuth2 endpoints with CSRF protection."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_epic_authorize_returns_state(self, client):
        """Epic authorize endpoint should return state parameter."""
        response = client.get("/auth/epic/authorize")
        data = response.json()

        assert "state" in data
        assert len(data["state"]) >= 40
        assert data["state"] in _oauth2_states

    def test_epic_callback_validates_state(self, client):
        """Epic callback should validate state parameter."""
        # Get authorization URL with state
        auth_response = client.get("/auth/epic/authorize")
        state = auth_response.json()["state"]

        # Callback without state should fail
        response = client.get("/auth/epic/callback?code=test_code")
        data = response.json()
        assert data["success"] is False
        assert "csrf" in data.get("error", "").lower()

    def test_epic_callback_rejects_invalid_state(self, client):
        """Epic callback should reject invalid state."""
        response = client.get("/auth/epic/callback?code=test_code&state=invalid_state_12345")
        data = response.json()
        assert data["success"] is False
        assert "csrf" in data.get("error", "").lower()

    def test_veradigm_authorize_returns_state(self, client):
        """Veradigm authorize endpoint should return state parameter."""
        response = client.get("/auth/veradigm/authorize")
        data = response.json()
        assert "state" in data

    def test_athena_authorize_returns_state(self, client):
        """athenahealth authorize endpoint should return state parameter."""
        response = client.get("/auth/athena/authorize")
        data = response.json()
        # May return error if not configured, but shouldn't crash
        if "authorization_url" in data:
            assert "state" in data

    def test_nextgen_authorize_returns_state(self, client):
        """NextGen authorize endpoint should return state parameter."""
        response = client.get("/auth/nextgen/authorize")
        data = response.json()
        if "authorization_url" in data:
            assert "state" in data

    def test_ecw_authorize_returns_state(self, client):
        """eClinicalWorks authorize endpoint should return state parameter."""
        response = client.get("/auth/ecw/authorize")
        data = response.json()
        if "authorization_url" in data:
            assert "state" in data

    def test_meditech_authorize_returns_state(self, client):
        """MEDITECH authorize endpoint should return state parameter."""
        response = client.get("/auth/meditech/authorize")
        data = response.json()
        if "authorization_url" in data:
            assert "state" in data
            assert data.get("pkce_enabled") is True
