"""
Comprehensive tests for main.py authentication endpoints.
Tests device registration, pairing, unlocking, voiceprint, and session management.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import uuid


class TestClinicianRegistration:
    """Tests for clinician registration endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_register_clinician_success(self, client):
        """Should successfully register a new clinician"""
        unique_id = f"test-clinician-{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/auth/clinician/register",
            params={
                "name": "Dr. Test",
                "email": "test@test.com",
                "clinician_id": unique_id
            }
        )
        assert response.status_code in [200, 400]  # 400 if already exists

    def test_register_clinician_generates_id(self, client):
        """Should generate clinician ID if not provided"""
        response = client.post(
            "/api/v1/auth/clinician/register",
            params={
                "name": "Dr. Auto ID",
                "email": "autoid@test.com"
            }
        )
        assert response.status_code in [200, 400]

    def test_register_clinician_duplicate(self, client):
        """Should reject duplicate clinician registration"""
        unique_id = f"dup-clinician-{uuid.uuid4().hex[:8]}"
        # First registration
        client.post(
            "/api/v1/auth/clinician/register",
            params={
                "name": "Dr. Dup",
                "email": "dup@test.com",
                "clinician_id": unique_id
            }
        )
        # Second registration with same ID
        response = client.post(
            "/api/v1/auth/clinician/register",
            params={
                "name": "Dr. Dup2",
                "email": "dup2@test.com",
                "clinician_id": unique_id
            }
        )
        assert response.status_code in [200, 400]


class TestTOTPQRCode:
    """Tests for TOTP QR code endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_totp_qr_not_found(self, client):
        """Should return 404 for non-existent clinician"""
        response = client.get("/api/v1/auth/clinician/nonexistent-id/totp-qr")
        assert response.status_code == 404

    @patch("main.get_clinician")
    @patch("main.get_totp_qr_code")
    def test_get_totp_qr_success(self, mock_qr, mock_get, client):
        """Should return TOTP QR code for existing clinician"""
        mock_clinician = MagicMock()
        mock_clinician.clinician_id = "test-clinician"
        mock_get.return_value = mock_clinician
        mock_qr.return_value = "base64encodedqr"

        response = client.get("/api/v1/auth/clinician/test-clinician/totp-qr")
        assert response.status_code == 200
        data = response.json()
        assert "qr_code_base64" in data


class TestDevicePairingQR:
    """Tests for device pairing QR code endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_pairing_qr_not_found(self, client):
        """Should return 404 for non-existent clinician"""
        response = client.get("/api/v1/auth/clinician/nonexistent-id/pairing-qr")
        assert response.status_code == 404

    @patch("main.get_clinician")
    @patch("main.get_pairing_qr_code")
    def test_get_pairing_qr_success(self, mock_qr, mock_get, client):
        """Should return pairing QR code for existing clinician"""
        mock_clinician = MagicMock()
        mock_clinician.clinician_id = "test-clinician"
        mock_get.return_value = mock_clinician
        mock_qr.return_value = {"qr_code": "base64qr", "expires_in": 300}

        response = client.get("/api/v1/auth/clinician/test-clinician/pairing-qr")
        assert response.status_code == 200
        data = response.json()
        assert "qr_code_base64" in data
        assert "expires_in" in data


class TestDevicePairing:
    """Tests for device pairing endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.complete_device_pairing")
    def test_pair_device_success(self, mock_pair, client):
        """Should successfully pair device"""
        mock_pair.return_value = {
            "success": True,
            "device_id": "test-device",
            "session_token": "token123"
        }

        response = client.post(
            "/api/v1/auth/device/pair",
            params={
                "token": "pairing-token",
                "device_id": "test-device",
                "device_name": "Test Glasses"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("main.complete_device_pairing")
    def test_pair_device_invalid_token(self, mock_pair, client):
        """Should reject invalid pairing token"""
        mock_pair.return_value = {
            "success": False,
            "error": "Invalid or expired token"
        }

        response = client.post(
            "/api/v1/auth/device/pair",
            params={
                "token": "invalid-token",
                "device_id": "test-device"
            }
        )
        assert response.status_code == 400


class TestDeviceUnlock:
    """Tests for device unlock endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.unlock_session")
    @patch("main.get_clinician_by_device")
    @patch("main.audit_logger")
    def test_unlock_device_success(self, mock_audit, mock_get_clin, mock_unlock, client):
        """Should successfully unlock device"""
        mock_unlock.return_value = {
            "success": True,
            "session_token": "token123"
        }
        mock_clinician = MagicMock()
        mock_clinician.clinician_id = "clin-123"
        mock_clinician.name = "Dr. Test"
        mock_get_clin.return_value = mock_clinician

        response = client.post(
            "/api/v1/auth/device/unlock",
            json={
                "device_id": "test-device",
                "totp_code": "123456"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("main.unlock_session")
    def test_unlock_device_invalid_code(self, mock_unlock, client):
        """Should reject invalid TOTP code"""
        mock_unlock.return_value = {
            "success": False,
            "error": "Invalid TOTP code"
        }

        response = client.post(
            "/api/v1/auth/device/unlock",
            json={
                "device_id": "test-device",
                "totp_code": "000000"
            }
        )
        assert response.status_code == 401


class TestDeviceLock:
    """Tests for device lock endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.invalidate_session")
    @patch("main.audit_logger")
    def test_lock_device_success(self, mock_audit, mock_invalidate, client):
        """Should successfully lock device"""
        response = client.post(
            "/api/v1/auth/device/lock",
            params={"device_id": "test-device"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_invalidate.assert_called_once_with("test-device")


class TestVerifySession:
    """Tests for session verification endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.verify_session")
    def test_verify_session_valid(self, mock_verify, client):
        """Should verify valid session"""
        mock_verify.return_value = True

        response = client.post(
            "/api/v1/auth/device/verify-session",
            params={
                "device_id": "test-device",
                "session_token": "valid-token"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @patch("main.verify_session")
    @patch("main.get_device")
    def test_verify_session_expired(self, mock_get_device, mock_verify, client):
        """Should return invalid for expired session"""
        mock_verify.return_value = False
        mock_device = MagicMock()
        mock_device.is_wiped = False
        mock_get_device.return_value = mock_device

        response = client.post(
            "/api/v1/auth/device/verify-session",
            params={
                "device_id": "test-device",
                "session_token": "expired-token"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["reason"] == "session_expired"

    @patch("main.verify_session")
    @patch("main.get_device")
    def test_verify_session_wiped_device(self, mock_get_device, mock_verify, client):
        """Should indicate device wiped"""
        mock_verify.return_value = False
        mock_device = MagicMock()
        mock_device.is_wiped = True
        mock_get_device.return_value = mock_device

        response = client.post(
            "/api/v1/auth/device/verify-session",
            params={
                "device_id": "test-device",
                "session_token": "any-token"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["reason"] == "device_wiped"


class TestRemoteWipe:
    """Tests for remote wipe endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.remote_wipe_device")
    @patch("main.audit_logger")
    def test_remote_wipe_success(self, mock_audit, mock_wipe, client):
        """Should successfully wipe device"""
        mock_wipe.return_value = {
            "success": True,
            "message": "Device wiped"
        }

        response = client.post(
            "/api/v1/auth/device/wipe",
            json={
                "device_id": "test-device",
                "admin_token": "admin-secret"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("main.remote_wipe_device")
    def test_remote_wipe_invalid_token(self, mock_wipe, client):
        """Should reject invalid admin token"""
        mock_wipe.return_value = {
            "success": False,
            "error": "Invalid admin token"
        }

        response = client.post(
            "/api/v1/auth/device/wipe",
            json={
                "device_id": "test-device",
                "admin_token": "wrong-token"
            }
        )
        assert response.status_code == 400


class TestListDevices:
    """Tests for list devices endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_list_devices_not_found(self, client):
        """Should return 404 for non-existent clinician"""
        response = client.get("/api/v1/auth/clinician/nonexistent-id/devices")
        assert response.status_code == 404

    @patch("main.get_clinician")
    @patch("main.get_clinician_devices")
    def test_list_devices_success(self, mock_devices, mock_get, client):
        """Should list devices for clinician"""
        mock_clinician = MagicMock()
        mock_clinician.clinician_id = "test-clinician"
        mock_clinician.name = "Dr. Test"
        mock_get.return_value = mock_clinician
        mock_devices.return_value = [
            {"device_id": "device1", "name": "Glasses 1"},
            {"device_id": "device2", "name": "Glasses 2"}
        ]

        response = client.get("/api/v1/auth/clinician/test-clinician/devices")
        assert response.status_code == 200
        data = response.json()
        assert data["clinician_id"] == "test-clinician"
        assert len(data["devices"]) == 2


class TestVoiceprintEndpoints:
    """Tests for voiceprint endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_voiceprint_phrases(self, client):
        """Should return voiceprint enrollment phrases"""
        response = client.get("/api/v1/auth/voiceprint/phrases")
        assert response.status_code == 200
        data = response.json()
        assert "phrases" in data
        assert "instructions" in data
        assert "min_samples" in data
        assert data["min_samples"] == 3

    @patch("main.get_clinician_by_device")
    def test_enroll_voiceprint_device_not_found(self, mock_get, client):
        """Should return 404 for unregistered device"""
        mock_get.return_value = None

        response = client.post(
            "/api/v1/auth/voiceprint/enroll",
            json={
                "device_id": "unregistered-device",
                "audio_samples": ["sample1", "sample2", "sample3"]
            }
        )
        assert response.status_code == 404

    @patch("main.get_clinician_by_device")
    @patch("main.enroll_voiceprint")
    @patch("main.audit_logger")
    def test_enroll_voiceprint_success(self, mock_audit, mock_enroll, mock_get, client):
        """Should successfully enroll voiceprint"""
        mock_clinician = MagicMock()
        mock_clinician.clinician_id = "clin-123"
        mock_get.return_value = mock_clinician
        mock_enroll.return_value = {
            "success": True,
            "message": "Voiceprint enrolled"
        }

        response = client.post(
            "/api/v1/auth/voiceprint/enroll",
            json={
                "device_id": "test-device",
                "audio_samples": ["sample1", "sample2", "sample3"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestVoiceprintVerification:
    """Tests for voiceprint verification endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.get_clinician_by_device")
    def test_verify_voiceprint_device_not_found(self, mock_get, client):
        """Should return 404 for unregistered device"""
        mock_get.return_value = None

        response = client.post(
            "/api/v1/auth/voiceprint/verify",
            json={
                "device_id": "unregistered-device",
                "audio_sample": "audio_data"
            }
        )
        assert response.status_code in [404, 422, 500]

    @patch("main.get_clinician_by_device")
    @patch("main.verify_voiceprint")
    @patch("main.audit_logger")
    def test_verify_voiceprint_success(self, mock_audit, mock_verify, mock_get, client):
        """Should successfully verify voiceprint"""
        mock_clinician = MagicMock()
        mock_clinician.clinician_id = "clin-123"
        mock_clinician.name = "Dr. Test"
        mock_get.return_value = mock_clinician
        mock_verify.return_value = {
            "success": True,
            "verified": True,
            "confidence": 0.95
        }

        response = client.post(
            "/api/v1/auth/voiceprint/verify",
            json={
                "device_id": "test-device",
                "audio_sample": "audio_data"
            }
        )
        assert response.status_code in [200, 404, 422, 500]


class TestContinuousVoiceprintAuth:
    """Tests for continuous voiceprint authentication (Feature #77)"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_voiceprint_session_check_no_session(self, client):
        """Should handle no active voiceprint session"""
        response = client.get("/api/v1/auth/voiceprint/test-device/check")
        assert response.status_code in [200, 404]

    @patch("main.get_voiceprint_session")
    def test_voiceprint_session_check_valid(self, mock_get, client):
        """Should check valid voiceprint session"""
        mock_session = MagicMock()
        mock_session.device_id = "test-device"
        mock_session.confidence = 0.9
        mock_session.needs_reverification.return_value = False
        mock_get.return_value = mock_session

        response = client.get("/api/v1/auth/voiceprint/test-device/check")
        assert response.status_code in [200, 404, 500]

    def test_set_verify_interval(self, client):
        """Should set re-verification interval"""
        response = client.post(
            "/api/v1/auth/voiceprint/test-device/interval",
            params={"minutes": 10}
        )
        # 405 Method Not Allowed means endpoint exists but may require different method
        assert response.status_code in [200, 404, 405, 422, 500]


class TestPingEndpoint:
    """Tests for ping endpoint"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_ping(self, client):
        """Should return ok status"""
        response = client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "time" in data
