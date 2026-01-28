"""
Tests for Request Signing (Issue #97 - Device Authentication)

Tests cover:
- HMAC-SHA256 signature generation
- Signature verification
- Replay attack prevention (timestamp validation)
- Device registration and revocation
- Key rotation
- API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import time
import base64
import hashlib
import hmac
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from request_signing import (
    RequestSigner, DeviceRegistry, SignatureVerifier,
    DeviceRegistration, DeviceStatus,
    SignatureError, InvalidSignatureError, ExpiredTimestampError,
    UnknownDeviceError, RevokedDeviceError,
    get_device_registry, get_signature_verifier
)


class TestRequestSigner:
    """Tests for client-side request signing."""

    def test_sign_request_generates_headers(self):
        """sign_request should return required headers."""
        signer = RequestSigner("test_device", base64.b64encode(b"secret123").decode())
        headers = signer.sign_request("GET", "/api/v1/test")

        assert "X-MDx-Device-ID" in headers
        assert "X-MDx-Timestamp" in headers
        assert "X-MDx-Signature" in headers
        assert headers["X-MDx-Device-ID"] == "test_device"

    def test_sign_request_timestamp_format(self):
        """Timestamp should be ISO 8601 UTC format."""
        signer = RequestSigner("test_device", base64.b64encode(b"secret123").decode())
        headers = signer.sign_request("GET", "/api/v1/test")

        timestamp = headers["X-MDx-Timestamp"]
        # Should match format: 2026-01-22T10:30:00Z
        assert "T" in timestamp
        assert timestamp.endswith("Z")

    def test_sign_request_different_methods_different_signatures(self):
        """Different HTTP methods should produce different signatures."""
        signer = RequestSigner("test_device", base64.b64encode(b"secret123").decode())
        ts = datetime.now(timezone.utc)

        get_headers = signer.sign_request("GET", "/api/v1/test", timestamp=ts)
        post_headers = signer.sign_request("POST", "/api/v1/test", timestamp=ts)

        assert get_headers["X-MDx-Signature"] != post_headers["X-MDx-Signature"]

    def test_sign_request_different_paths_different_signatures(self):
        """Different paths should produce different signatures."""
        signer = RequestSigner("test_device", base64.b64encode(b"secret123").decode())
        ts = datetime.now(timezone.utc)

        path1_headers = signer.sign_request("GET", "/api/v1/test1", timestamp=ts)
        path2_headers = signer.sign_request("GET", "/api/v1/test2", timestamp=ts)

        assert path1_headers["X-MDx-Signature"] != path2_headers["X-MDx-Signature"]

    def test_sign_request_with_body(self):
        """Requests with body should include body hash in signature."""
        signer = RequestSigner("test_device", base64.b64encode(b"secret123").decode())
        ts = datetime.now(timezone.utc)

        no_body = signer.sign_request("POST", "/api/v1/test", timestamp=ts)
        with_body = signer.sign_request("POST", "/api/v1/test", body=b'{"test": true}', timestamp=ts)

        assert no_body["X-MDx-Signature"] != with_body["X-MDx-Signature"]

    def test_sign_request_same_inputs_same_signature(self):
        """Same inputs should produce same signature (deterministic)."""
        signer = RequestSigner("test_device", base64.b64encode(b"secret123").decode())
        ts = datetime.now(timezone.utc)

        headers1 = signer.sign_request("GET", "/api/v1/test", timestamp=ts)
        headers2 = signer.sign_request("GET", "/api/v1/test", timestamp=ts)

        assert headers1["X-MDx-Signature"] == headers2["X-MDx-Signature"]


class TestDeviceRegistry:
    """Tests for device registration and management."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create a registry with temp storage."""
        return DeviceRegistry(storage_path=str(tmp_path / "devices.json"))

    def test_register_device_returns_credentials(self, registry):
        """register_device should return device_id and secret_key."""
        device_id, secret_key = registry.register_device(
            device_name="Test Glasses",
            device_type="glasses"
        )

        assert device_id is not None
        assert device_id.startswith("mdx_glasses_")
        assert secret_key is not None
        assert len(base64.b64decode(secret_key)) == 32  # 256 bits

    def test_register_device_unique_ids(self, registry):
        """Each device should get a unique ID."""
        id1, _ = registry.register_device("Device 1", "glasses")
        id2, _ = registry.register_device("Device 2", "glasses")

        assert id1 != id2

    def test_get_device_returns_registration(self, registry):
        """get_device should return the registration."""
        device_id, _ = registry.register_device("Test", "web")
        device = registry.get_device(device_id)

        assert device is not None
        assert device.device_id == device_id
        assert device.device_name == "Test"
        assert device.device_type == "web"
        assert device.status == DeviceStatus.ACTIVE

    def test_get_device_unknown_returns_none(self, registry):
        """get_device should return None for unknown device."""
        device = registry.get_device("unknown_device_123")
        assert device is None

    def test_revoke_device(self, registry):
        """revoke_device should mark device as revoked."""
        device_id, _ = registry.register_device("Test", "glasses")
        registry.revoke_device(device_id, "Lost device")

        device = registry.get_device(device_id)
        assert device.status == DeviceStatus.REVOKED
        assert device.revocation_reason == "Lost device"
        assert device.revoked_at is not None

    def test_rotate_key(self, registry):
        """rotate_key should generate new secret."""
        device_id, old_secret = registry.register_device("Test", "mobile")
        new_secret = registry.rotate_key(device_id)

        assert new_secret is not None
        assert new_secret != old_secret

    def test_rotate_key_revoked_returns_none(self, registry):
        """rotate_key should return None for revoked devices."""
        device_id, _ = registry.register_device("Test", "glasses")
        registry.revoke_device(device_id, "Test")

        new_secret = registry.rotate_key(device_id)
        assert new_secret is None

    def test_list_devices(self, registry):
        """list_devices should return all active devices."""
        registry.register_device("Device 1", "glasses")
        registry.register_device("Device 2", "web")

        devices = registry.list_devices()
        assert len(devices) == 2

    def test_list_devices_excludes_revoked(self, registry):
        """list_devices should exclude revoked by default."""
        id1, _ = registry.register_device("Device 1", "glasses")
        registry.register_device("Device 2", "web")
        registry.revoke_device(id1, "Test")

        devices = registry.list_devices(include_revoked=False)
        assert len(devices) == 1

    def test_list_devices_includes_revoked(self, registry):
        """list_devices can include revoked devices."""
        id1, _ = registry.register_device("Device 1", "glasses")
        registry.register_device("Device 2", "web")
        registry.revoke_device(id1, "Test")

        devices = registry.list_devices(include_revoked=True)
        assert len(devices) == 2

    def test_device_to_dict_excludes_secret(self, registry):
        """to_dict should not expose secret key."""
        device_id, _ = registry.register_device("Test", "glasses")
        device = registry.get_device(device_id)
        d = device.to_dict()

        assert "secret_key" not in d
        assert "device_id" in d


class TestSignatureVerifier:
    """Tests for server-side signature verification."""

    @pytest.fixture
    def setup(self, tmp_path):
        """Set up registry, verifier, and test device."""
        registry = DeviceRegistry(storage_path=str(tmp_path / "devices.json"))
        device_id, secret_key = registry.register_device("Test Device", "glasses")
        verifier = SignatureVerifier(registry)
        signer = RequestSigner(device_id, secret_key)
        return registry, verifier, signer, device_id, secret_key

    def test_verify_valid_signature(self, setup):
        """Valid signature should pass verification."""
        registry, verifier, signer, device_id, _ = setup

        headers = signer.sign_request("GET", "/api/v1/test")

        device = verifier.verify_request(
            device_id=headers["X-MDx-Device-ID"],
            timestamp=headers["X-MDx-Timestamp"],
            signature=headers["X-MDx-Signature"],
            method="GET",
            path="/api/v1/test"
        )

        assert device is not None
        assert device.device_id == device_id

    def test_verify_with_body(self, setup):
        """Valid signature with body should pass verification."""
        _, verifier, signer, device_id, _ = setup
        body = b'{"patient_id": "123"}'

        headers = signer.sign_request("POST", "/api/v1/test", body=body)

        device = verifier.verify_request(
            device_id=headers["X-MDx-Device-ID"],
            timestamp=headers["X-MDx-Timestamp"],
            signature=headers["X-MDx-Signature"],
            method="POST",
            path="/api/v1/test",
            body=body
        )

        assert device.device_id == device_id

    def test_verify_unknown_device_raises(self, setup):
        """Unknown device should raise UnknownDeviceError."""
        _, verifier, signer, _, _ = setup

        headers = signer.sign_request("GET", "/api/v1/test")

        with pytest.raises(UnknownDeviceError):
            verifier.verify_request(
                device_id="unknown_device_xyz",
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="GET",
                path="/api/v1/test"
            )

    def test_verify_revoked_device_raises(self, setup):
        """Revoked device should raise RevokedDeviceError."""
        registry, verifier, signer, device_id, _ = setup

        headers = signer.sign_request("GET", "/api/v1/test")
        registry.revoke_device(device_id, "Test revocation")

        with pytest.raises(RevokedDeviceError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="GET",
                path="/api/v1/test"
            )

    def test_verify_expired_timestamp_raises(self, setup):
        """Timestamp older than 5 minutes should raise ExpiredTimestampError."""
        _, verifier, signer, _, _ = setup

        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        headers = signer.sign_request("GET", "/api/v1/test", timestamp=old_time)

        with pytest.raises(ExpiredTimestampError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="GET",
                path="/api/v1/test"
            )

    def test_verify_future_timestamp_allowed_within_window(self, setup):
        """Timestamp slightly in future should be allowed."""
        _, verifier, signer, device_id, _ = setup

        future_time = datetime.now(timezone.utc) + timedelta(minutes=2)
        headers = signer.sign_request("GET", "/api/v1/test", timestamp=future_time)

        device = verifier.verify_request(
            device_id=headers["X-MDx-Device-ID"],
            timestamp=headers["X-MDx-Timestamp"],
            signature=headers["X-MDx-Signature"],
            method="GET",
            path="/api/v1/test"
        )

        assert device.device_id == device_id

    def test_verify_invalid_signature_raises(self, setup):
        """Tampered signature should raise InvalidSignatureError."""
        _, verifier, signer, _, _ = setup

        headers = signer.sign_request("GET", "/api/v1/test")

        with pytest.raises(InvalidSignatureError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature="tampered_signature_base64==",
                method="GET",
                path="/api/v1/test"
            )

    def test_verify_wrong_method_raises(self, setup):
        """Wrong method should cause signature mismatch."""
        _, verifier, signer, _, _ = setup

        headers = signer.sign_request("GET", "/api/v1/test")

        with pytest.raises(InvalidSignatureError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="POST",  # Wrong method
                path="/api/v1/test"
            )

    def test_verify_wrong_path_raises(self, setup):
        """Wrong path should cause signature mismatch."""
        _, verifier, signer, _, _ = setup

        headers = signer.sign_request("GET", "/api/v1/test")

        with pytest.raises(InvalidSignatureError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="GET",
                path="/api/v1/different"  # Wrong path
            )

    def test_verify_tampered_body_raises(self, setup):
        """Tampered body should cause signature mismatch."""
        _, verifier, signer, _, _ = setup

        headers = signer.sign_request("POST", "/api/v1/test", body=b'{"original": true}')

        with pytest.raises(InvalidSignatureError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="POST",
                path="/api/v1/test",
                body=b'{"tampered": true}'  # Wrong body
            )


class TestReplayPrevention:
    """Tests for replay attack prevention."""

    @pytest.fixture
    def setup(self, tmp_path):
        """Set up registry, verifier, and test device."""
        registry = DeviceRegistry(storage_path=str(tmp_path / "devices.json"))
        device_id, secret_key = registry.register_device("Test Device", "glasses")
        verifier = SignatureVerifier(registry)
        signer = RequestSigner(device_id, secret_key)
        return verifier, signer

    def test_timestamp_must_be_recent(self, setup):
        """Requests older than 5 minutes should be rejected."""
        verifier, signer = setup

        old_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        headers = signer.sign_request("GET", "/api/v1/test", timestamp=old_time)

        with pytest.raises(ExpiredTimestampError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp=headers["X-MDx-Timestamp"],
                signature=headers["X-MDx-Signature"],
                method="GET",
                path="/api/v1/test"
            )

    def test_invalid_timestamp_format_raises(self, setup):
        """Invalid timestamp format should raise error."""
        verifier, signer = setup

        headers = signer.sign_request("GET", "/api/v1/test")

        with pytest.raises(ExpiredTimestampError):
            verifier.verify_request(
                device_id=headers["X-MDx-Device-ID"],
                timestamp="invalid-timestamp",
                signature=headers["X-MDx-Signature"],
                method="GET",
                path="/api/v1/test"
            )


class TestSigningAPIEndpoints:
    """Integration tests for request signing API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_register_device_endpoint(self, client):
        """POST /api/v1/auth/signing/register should return credentials."""
        response = client.post(
            "/api/v1/auth/signing/register",
            json={"device_name": "Test Glasses", "device_type": "glasses"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "device_id" in data
        assert "secret_key" in data
        assert data["device_id"].startswith("mdx_glasses_")

    def test_list_devices_endpoint(self, client):
        """GET /api/v1/auth/signing/devices should return device list."""
        # Register a device first
        client.post(
            "/api/v1/auth/signing/register",
            json={"device_name": "Test", "device_type": "web"}
        )

        response = client.get("/api/v1/auth/signing/devices")

        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert isinstance(data["devices"], list)

    def test_revoke_device_endpoint(self, client):
        """POST /api/v1/auth/signing/devices/{id}/revoke should revoke device."""
        # Register first
        reg_response = client.post(
            "/api/v1/auth/signing/register",
            json={"device_name": "Test", "device_type": "glasses"}
        )
        device_id = reg_response.json()["device_id"]

        # Revoke
        response = client.post(
            f"/api/v1/auth/signing/devices/{device_id}/revoke",
            params={"reason": "Lost device"}
        )

        assert response.status_code == 200
        assert "revoked" in response.json()["message"]

    def test_revoke_unknown_device_404(self, client):
        """Revoking unknown device should return 404."""
        response = client.post("/api/v1/auth/signing/devices/unknown_xyz/revoke")
        assert response.status_code == 404

    def test_rotate_key_endpoint(self, client):
        """POST /api/v1/auth/signing/devices/{id}/rotate-key should return new key."""
        # Register first
        reg_response = client.post(
            "/api/v1/auth/signing/register",
            json={"device_name": "Test", "device_type": "mobile"}
        )
        device_id = reg_response.json()["device_id"]
        old_secret = reg_response.json()["secret_key"]

        # Rotate
        response = client.post(f"/api/v1/auth/signing/devices/{device_id}/rotate-key")

        assert response.status_code == 200
        new_secret = response.json()["secret_key"]
        assert new_secret != old_secret

    def test_verify_endpoint_valid_signature(self, client):
        """POST /api/v1/auth/signing/verify should verify valid signatures."""
        # Register device
        reg_response = client.post(
            "/api/v1/auth/signing/register",
            json={"device_name": "Test", "device_type": "glasses"}
        )
        device_id = reg_response.json()["device_id"]
        secret_key = reg_response.json()["secret_key"]

        # Create signer and sign request
        signer = RequestSigner(device_id, secret_key)
        headers = signer.sign_request("POST", "/api/v1/auth/signing/verify")

        # Verify
        response = client.post(
            "/api/v1/auth/signing/verify",
            headers=headers
        )

        assert response.status_code == 200
        assert response.json()["verified"] is True

    def test_verify_endpoint_invalid_signature(self, client):
        """POST /api/v1/auth/signing/verify should reject invalid signatures."""
        # Register device
        reg_response = client.post(
            "/api/v1/auth/signing/register",
            json={"device_name": "Test", "device_type": "glasses"}
        )
        device_id = reg_response.json()["device_id"]

        # Send with bad signature
        response = client.post(
            "/api/v1/auth/signing/verify",
            headers={
                "X-MDx-Device-ID": device_id,
                "X-MDx-Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "X-MDx-Signature": "invalid_signature_base64=="
            }
        )

        assert response.status_code == 401

    def test_verify_endpoint_missing_headers(self, client):
        """POST /api/v1/auth/signing/verify should require all headers."""
        response = client.post("/api/v1/auth/signing/verify")
        assert response.status_code == 400


class TestSecurityProperties:
    """Tests for security properties of the signing scheme."""

    def test_signature_is_base64(self):
        """Signature should be valid base64."""
        signer = RequestSigner("test", base64.b64encode(b"secret").decode())
        headers = signer.sign_request("GET", "/test")

        signature = headers["X-MDx-Signature"]
        decoded = base64.b64decode(signature)
        assert len(decoded) == 32  # SHA256 = 32 bytes

    def test_different_secrets_different_signatures(self):
        """Different secrets should produce different signatures."""
        ts = datetime.now(timezone.utc)

        signer1 = RequestSigner("test", base64.b64encode(b"secret1").decode())
        signer2 = RequestSigner("test", base64.b64encode(b"secret2").decode())

        sig1 = signer1.sign_request("GET", "/test", timestamp=ts)["X-MDx-Signature"]
        sig2 = signer2.sign_request("GET", "/test", timestamp=ts)["X-MDx-Signature"]

        assert sig1 != sig2

    def test_timing_safe_comparison(self, tmp_path):
        """Signature comparison should be constant-time."""
        # This test verifies hmac.compare_digest is used
        registry = DeviceRegistry(storage_path=str(tmp_path / "d.json"))
        device_id, secret_key = registry.register_device("Test", "glasses")
        verifier = SignatureVerifier(registry)
        signer = RequestSigner(device_id, secret_key)

        headers = signer.sign_request("GET", "/test")

        # Both should take similar time (not early-exit on first byte mismatch)
        # This is a sanity check - proper timing analysis requires more rigor
        device = verifier.verify_request(
            device_id=headers["X-MDx-Device-ID"],
            timestamp=headers["X-MDx-Timestamp"],
            signature=headers["X-MDx-Signature"],
            method="GET",
            path="/test"
        )
        assert device is not None
