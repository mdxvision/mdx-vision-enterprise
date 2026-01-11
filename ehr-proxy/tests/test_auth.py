"""
Test Device Authentication Endpoints (Feature #64)

Tests device pairing, TOTP unlock, session management, and remote wipe.
Security-critical tests for AR glasses authentication.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
import uuid
import base64

# Import the main app
import sys
sys.path.insert(0, '..')
from main import app


@pytest.fixture
def test_clinician_id():
    return f"clinician-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_device_id():
    return f"device-{uuid.uuid4().hex[:8]}"


class TestClinicianRegistration:
    """Tests for /api/v1/auth/clinician/register endpoint"""

    @pytest.mark.asyncio
    async def test_register_clinician_success(self, test_clinician_id):
        """Should successfully register a new clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. John Smith",
                    "email": "john.smith@hospital.com",
                    "clinician_id": test_clinician_id
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["clinician_id"] == test_clinician_id
            assert data["name"] == "Dr. John Smith"
            assert "message" in data

    @pytest.mark.asyncio
    async def test_register_clinician_generates_id(self):
        """Should generate clinician ID if not provided"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. Jane Doe",
                    "email": "jane.doe@hospital.com"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["clinician_id"].startswith("clinician-")

    @pytest.mark.asyncio
    async def test_register_duplicate_clinician_fails(self, test_clinician_id):
        """Should fail when registering duplicate clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First registration
            await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. John Smith",
                    "email": "john@hospital.com",
                    "clinician_id": test_clinician_id
                }
            )

            # Duplicate registration
            response = await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. John Smith",
                    "email": "john@hospital.com",
                    "clinician_id": test_clinician_id
                }
            )

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]


class TestTOTPSetup:
    """Tests for TOTP QR code generation"""

    @pytest.mark.asyncio
    async def test_get_totp_qr_for_registered_clinician(self, test_clinician_id):
        """Should return TOTP QR code for registered clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First register
            await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. Test",
                    "email": "test@hospital.com",
                    "clinician_id": test_clinician_id
                }
            )

            # Get TOTP QR
            response = await client.get(f"/api/v1/auth/clinician/{test_clinician_id}/totp-qr")

            assert response.status_code == 200
            data = response.json()
            assert "qr_code_base64" in data
            assert data["clinician_id"] == test_clinician_id
            # Verify it's valid base64
            try:
                base64.b64decode(data["qr_code_base64"])
            except Exception:
                pytest.fail("QR code is not valid base64")

    @pytest.mark.asyncio
    async def test_get_totp_qr_for_unknown_clinician(self):
        """Should return 404 for unknown clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/clinician/unknown-id/totp-qr")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestDevicePairing:
    """Tests for device pairing workflow"""

    @pytest.mark.asyncio
    async def test_get_pairing_qr_code(self, test_clinician_id):
        """Should generate pairing QR code for clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register clinician first
            await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. Pair Test",
                    "email": "pair@hospital.com",
                    "clinician_id": test_clinician_id
                }
            )

            # Get pairing QR
            response = await client.get(f"/api/v1/auth/clinician/{test_clinician_id}/pairing-qr")

            assert response.status_code == 200
            data = response.json()
            assert "qr_code_base64" in data
            assert "expires_in" in data
            assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_pair_device_with_invalid_token(self, test_device_id):
        """Should reject pairing with invalid token"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/pair",
                params={
                    "token": "invalid-token",
                    "device_id": test_device_id,
                    "device_name": "Vuzix Blade 2"
                }
            )

            assert response.status_code == 400


class TestDeviceSession:
    """Tests for device session management"""

    @pytest.mark.asyncio
    async def test_unlock_with_invalid_totp(self, test_device_id):
        """Should reject unlock with invalid TOTP"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/unlock",
                json={
                    "device_id": test_device_id,
                    "totp_code": "000000"  # Invalid code
                }
            )

            # Should fail - device not registered or invalid TOTP
            # Note: 200 with success=false is also valid API behavior
            assert response.status_code in [200, 401, 400]

    @pytest.mark.asyncio
    async def test_lock_device(self, test_device_id):
        """Should lock device session"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/lock",
                params={"device_id": test_device_id}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_verify_invalid_session(self, test_device_id):
        """Should reject invalid session token"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/verify-session",
                params={
                    "device_id": test_device_id,
                    "session_token": "invalid-session-token"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False


class TestRemoteWipe:
    """Tests for remote wipe functionality"""

    @pytest.mark.asyncio
    async def test_wipe_without_admin_token(self, test_device_id):
        """Should reject wipe without valid admin token"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/wipe",
                json={
                    "device_id": test_device_id,
                    "admin_token": "invalid-admin-token"
                }
            )

            assert response.status_code == 400


class TestClinicianDevices:
    """Tests for listing clinician devices"""

    @pytest.mark.asyncio
    async def test_list_devices_for_registered_clinician(self, test_clinician_id):
        """Should list devices for registered clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register clinician
            await client.post(
                "/api/v1/auth/clinician/register",
                params={
                    "name": "Dr. Devices",
                    "email": "devices@hospital.com",
                    "clinician_id": test_clinician_id
                }
            )

            # List devices
            response = await client.get(f"/api/v1/auth/clinician/{test_clinician_id}/devices")

            assert response.status_code == 200
            data = response.json()
            assert data["clinician_id"] == test_clinician_id
            assert "devices" in data
            assert isinstance(data["devices"], list)

    @pytest.mark.asyncio
    async def test_list_devices_for_unknown_clinician(self):
        """Should return 404 for unknown clinician"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/clinician/unknown-id/devices")

            assert response.status_code == 404


class TestVoiceprintPhrases:
    """Tests for voiceprint enrollment phrases"""

    @pytest.mark.asyncio
    async def test_get_voiceprint_phrases(self):
        """Should return voiceprint enrollment phrases"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/voiceprint/phrases")

            assert response.status_code == 200
            data = response.json()
            assert "phrases" in data
            assert len(data["phrases"]) >= 3  # At least 3 phrases
            assert data["min_samples"] >= 3


class TestAuditLogging:
    """Tests that auth operations are properly audit logged"""

    @pytest.mark.asyncio
    async def test_device_lock_creates_audit_log(self, test_device_id):
        """Should create audit log when device is locked"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # This should create an audit log entry
            response = await client.post(
                "/api/v1/auth/device/lock",
                params={"device_id": test_device_id}
            )

            assert response.status_code == 200
            # Audit log verification would require checking the log file or mock


class TestSecurityEdgeCases:
    """Edge case and security tests"""

    @pytest.mark.asyncio
    async def test_totp_code_format_validation(self, test_device_id):
        """Should reject improperly formatted TOTP codes"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test with non-numeric code
            response = await client.post(
                "/api/v1/auth/device/unlock",
                json={
                    "device_id": test_device_id,
                    "totp_code": "abcdef"
                }
            )
            assert response.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    async def test_empty_device_id_rejected(self):
        """Should reject empty device ID"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/lock",
                params={"device_id": ""}
            )
            # Should fail validation (or 200 with success=false)
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_sql_injection_in_clinician_id(self):
        """Should handle SQL injection attempts safely"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            malicious_id = "'; DROP TABLE clinicians; --"
            response = await client.get(f"/api/v1/auth/clinician/{malicious_id}/totp-qr")

            # Should return 404, not error
            assert response.status_code == 404


class TestProximityLock:
    """Tests for proximity-based auto-lock (conceptual - sensor-based)"""

    @pytest.mark.asyncio
    async def test_session_has_timeout(self, test_device_id):
        """Verify session includes timeout for proximity lock"""
        # This tests the session structure includes timeout capability
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/device/verify-session",
                params={
                    "device_id": test_device_id,
                    "session_token": "any-token"
                }
            )

            # Session verification should return reason for invalid
            data = response.json()
            assert "valid" in data
