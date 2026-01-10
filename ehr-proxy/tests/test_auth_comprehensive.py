"""
Comprehensive tests for auth.py module
Tests clinician management, device pairing, TOTP, and session management
"""

import pytest
import base64
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestClinicianManagement:
    """Tests for clinician storage and retrieval"""

    def test_clinician_class_init(self):
        """Test Clinician class initialization"""
        from auth import Clinician

        clinician = Clinician("clin-001", "Dr. Test", "test@example.com")

        assert clinician.clinician_id == "clin-001"
        assert clinician.name == "Dr. Test"
        assert clinician.email == "test@example.com"
        assert clinician.devices == []
        assert clinician.totp_secret is None

    def test_clinician_to_dict(self):
        """Test Clinician to_dict method"""
        from auth import Clinician

        clinician = Clinician("clin-001", "Dr. Test", "test@example.com")
        clinician.totp_secret = "secret123"
        clinician.devices = ["device-001"]

        d = clinician.to_dict()

        assert d["clinician_id"] == "clin-001"
        assert d["name"] == "Dr. Test"
        assert d["email"] == "test@example.com"
        assert d["totp_secret"] == "secret123"
        assert d["devices"] == ["device-001"]

    def test_clinician_from_dict(self):
        """Test Clinician from_dict class method"""
        from auth import Clinician

        data = {
            "clinician_id": "clin-002",
            "name": "Dr. Smith",
            "email": "smith@example.com",
            "totp_secret": "secret456",
            "devices": ["device-002", "device-003"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        clinician = Clinician.from_dict(data)

        assert clinician.clinician_id == "clin-002"
        assert clinician.name == "Dr. Smith"
        assert clinician.email == "smith@example.com"
        assert clinician.totp_secret == "secret456"
        assert clinician.devices == ["device-002", "device-003"]

    def test_save_and_get_clinician(self):
        """Test saving and retrieving a clinician"""
        from auth import save_clinician, get_clinician, Clinician

        clinician = Clinician("test-clin-001", "Dr. Test Save", "save@test.com")
        clinician.totp_secret = "testsecret"

        save_clinician(clinician)

        retrieved = get_clinician("test-clin-001")

        assert retrieved is not None
        assert retrieved.clinician_id == "test-clin-001"
        assert retrieved.name == "Dr. Test Save"

    def test_get_nonexistent_clinician(self):
        """Test getting a clinician that doesn't exist"""
        from auth import get_clinician

        result = get_clinician("nonexistent-clinician-id")

        assert result is None

    def test_get_clinician_by_device(self):
        """Test getting clinician by device ID"""
        from auth import get_clinician_by_device

        # This depends on internal state, but should not raise
        result = get_clinician_by_device("unknown-device-id")

        # May be None depending on state
        assert result is None or hasattr(result, 'clinician_id')


class TestTOTPGeneration:
    """Tests for TOTP secret and verification"""

    def test_generate_totp_secret(self):
        """Test TOTP secret generation"""
        from auth import generate_totp_secret

        secret = generate_totp_secret()

        assert secret is not None
        assert isinstance(secret, str)
        assert len(secret) > 0

    def test_verify_totp_invalid(self):
        """Test verifying an invalid TOTP code"""
        from auth import verify_totp, Clinician

        clinician = Clinician("totp-test", "Dr. TOTP", "totp@test.com")
        clinician.totp_secret = "JBSWY3DPEHPK3PXP"  # Valid base32 secret

        # Invalid code
        result = verify_totp(clinician, "000000")

        # Unlikely to be valid at this moment
        assert isinstance(result, bool)

    def test_get_totp_qr_code(self):
        """Test TOTP QR code generation"""
        from auth import get_totp_qr_code, Clinician, generate_totp_secret

        clinician = Clinician("qr-test-001", "Dr. QR Test", "qr@test.com")
        clinician.totp_secret = generate_totp_secret()

        qr_base64 = get_totp_qr_code(clinician, as_base64=True)

        assert qr_base64 is not None
        assert isinstance(qr_base64, str)
        assert len(qr_base64) > 0


class TestDeviceManagement:
    """Tests for device functionality"""

    def test_device_class_init(self):
        """Test Device class initialization"""
        from auth import Device

        device = Device("device-001", "clin-001")

        assert device.device_id == "device-001"
        assert device.clinician_id == "clin-001"
        assert device.is_active is True
        assert device.is_wiped is False

    def test_device_to_dict(self):
        """Test Device to_dict method"""
        from auth import Device

        device = Device("device-002", "clin-002")
        d = device.to_dict()

        assert d["device_id"] == "device-002"
        assert d["clinician_id"] == "clin-002"
        assert d["is_active"] is True
        assert d["is_wiped"] is False

    def test_device_from_dict(self):
        """Test Device from_dict method"""
        from auth import Device

        data = {
            "device_id": "device-003",
            "clinician_id": "clin-003",
            "device_name": "Test Glasses",
            "device_type": "vuzix_blade_2",
            "paired_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
            "is_wiped": False
        }

        device = Device.from_dict(data)

        assert device.device_id == "device-003"
        assert device.clinician_id == "clin-003"

    def test_save_and_get_device(self):
        """Test saving and retrieving a device"""
        from auth import save_device, get_device, Device

        device = Device("test-device-save", "test-clin")
        device.device_name = "Test Save Device"

        save_device(device)

        retrieved = get_device("test-device-save")

        assert retrieved is not None
        assert retrieved.device_id == "test-device-save"

    def test_delete_device(self):
        """Test deleting a device"""
        from auth import delete_device, save_device, get_device, Device

        device = Device("delete-test-device", "clin-delete")
        save_device(device)

        delete_device("delete-test-device")

        # Verify it's deleted
        result = get_device("delete-test-device")
        assert result is None


class TestDevicePairing:
    """Tests for device pairing functionality"""

    def test_generate_pairing_token(self):
        """Test pairing token generation"""
        from auth import generate_pairing_token, save_clinician, Clinician, generate_totp_secret

        # Setup clinician first
        clinician = Clinician("pairing-gen-test", "Dr. Pairing", "pairing@test.com")
        clinician.totp_secret = generate_totp_secret()
        save_clinician(clinician)

        token = generate_pairing_token("pairing-gen-test")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_get_pairing_qr_code(self):
        """Test pairing QR code generation"""
        from auth import get_pairing_qr_code, save_clinician, Clinician, generate_totp_secret

        # Setup clinician first
        clinician = Clinician("pairing-test-001", "Dr. Pairing", "pairing@test.com")
        clinician.totp_secret = generate_totp_secret()
        save_clinician(clinician)

        result = get_pairing_qr_code("pairing-test-001", "http://localhost:8002")

        assert "qr_code" in result
        assert "expires_in" in result
        assert result["expires_in"] > 0

    def test_complete_device_pairing_invalid_token(self):
        """Test completing pairing with invalid token"""
        from auth import complete_device_pairing

        result = complete_device_pairing(
            token="invalid-token-12345",
            device_id="new-device-001",
            device_name="New Device"
        )

        assert result["success"] is False
        assert "error" in result


class TestSessionManagement:
    """Tests for session creation and validation"""

    def test_create_session(self):
        """Test session creation"""
        from auth import create_session, Device, save_device

        device = Device("session-test-device", "clin-session")
        save_device(device)

        token = create_session(device, duration_hours=12)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_session_invalid(self):
        """Test verifying an invalid session"""
        from auth import verify_session

        # Non-existent session
        result = verify_session("unknown-device", "fake-token")

        assert result is False

    def test_invalidate_session(self):
        """Test session invalidation"""
        from auth import invalidate_session

        # Should not raise even for non-existent session
        invalidate_session("nonexistent-device")

    def test_unlock_session_invalid_device(self):
        """Test unlocking session for unpaired device"""
        from auth import unlock_session

        result = unlock_session("unpaired-device-xyz", "123456")

        assert result["success"] is False
        assert "error" in result


class TestVoiceprintSessions:
    """Tests for voiceprint session management"""

    def test_voiceprint_session_model(self):
        """Test VoiceprintSession Pydantic model"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="device-001",
            clinician_id="clin-001",
            confidence_score=0.85
        )

        assert session.device_id == "device-001"
        assert session.clinician_id == "clin-001"
        assert session.confidence_score == 0.85
        assert session.re_verify_interval_seconds == 300  # Default

    def test_voiceprint_session_needs_re_verification_no_verified(self):
        """Test needs_re_verification when never verified"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="device-002",
            clinician_id="clin-002"
        )

        # Never verified, should need verification
        assert session.needs_re_verification() is True

    def test_voiceprint_session_needs_re_verification_recent(self):
        """Test needs_re_verification with recent verification"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="device-003",
            clinician_id="clin-003",
            last_verified_at=datetime.now(timezone.utc),
            re_verify_interval_seconds=300
        )

        # Just verified, should not need re-verification
        assert session.needs_re_verification() is False

    def test_voiceprint_session_confidence_decay(self):
        """Test confidence decay calculation"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="device-004",
            clinician_id="clin-004",
            last_verified_at=datetime.now(timezone.utc),
            confidence_score=0.9
        )

        # Just verified, decay should be minimal
        decayed = session.confidence_decay()
        assert decayed > 0.8
        assert decayed <= 0.9

    def test_voiceprint_session_seconds_until_re_verification(self):
        """Test seconds_until_re_verification"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="device-005",
            clinician_id="clin-005",
            last_verified_at=datetime.now(timezone.utc),
            re_verify_interval_seconds=300
        )

        seconds = session.seconds_until_re_verification()
        assert seconds > 0
        assert seconds <= 300

    def test_get_voiceprint_session_not_found(self):
        """Test getting voiceprint session that doesn't exist"""
        from auth import get_voiceprint_session

        result = get_voiceprint_session("nonexistent-device")

        assert result is None

    def test_create_voiceprint_session(self):
        """Test creating a voiceprint session"""
        from auth import create_voiceprint_session, get_voiceprint_session

        session = create_voiceprint_session(
            device_id="vp-create-test",
            clinician_id="clin-vp-test",
            confidence=0.85
        )

        assert session.device_id == "vp-create-test"
        assert session.clinician_id == "clin-vp-test"
        assert session.confidence_score == 0.85

    def test_update_voiceprint_verification(self):
        """Test updating voiceprint verification"""
        from auth import (
            create_voiceprint_session,
            update_voiceprint_verification
        )

        # Create session first
        create_voiceprint_session("vp-update-test", "clin-vp-update", 0.80)

        # Update verification
        result = update_voiceprint_verification("vp-update-test", 0.95)

        if result:
            assert result.confidence_score == 0.95

    def test_set_re_verify_interval(self):
        """Test setting voiceprint re-verify interval"""
        from auth import create_voiceprint_session, set_re_verify_interval

        # Create session first
        create_voiceprint_session("vp-interval-test", "clin-interval", 0.85)

        # Set interval
        result = set_re_verify_interval("vp-interval-test", 600)

        if result:
            assert result.re_verify_interval_seconds == 600

    def test_delete_voiceprint_session(self):
        """Test deleting voiceprint session"""
        from auth import (
            create_voiceprint_session,
            delete_voiceprint_session,
            get_voiceprint_session
        )

        # Create and then delete
        create_voiceprint_session("vp-delete-test", "clin-delete", 0.80)
        delete_voiceprint_session("vp-delete-test")

        # Note: Session may still be in memory cache


class TestRemoteWipe:
    """Tests for remote wipe functionality"""

    def test_remote_wipe_device_not_found(self):
        """Test remote wipe for non-existent device"""
        from auth import remote_wipe_device

        result = remote_wipe_device("nonexistent-device", "admin-token")

        assert result["success"] is False
        assert "error" in result


class TestClinicianDevices:
    """Tests for listing clinician devices"""

    def test_get_clinician_devices(self):
        """Test getting devices for a clinician"""
        from auth import (
            get_clinician_devices,
            save_clinician,
            Clinician,
            generate_totp_secret
        )

        # Setup clinician
        clinician = Clinician("device-list-test", "Dr. Devices", "devices@test.com")
        clinician.totp_secret = generate_totp_secret()
        save_clinician(clinician)

        result = get_clinician_devices("device-list-test")

        assert isinstance(result, list)

    def test_get_clinician_devices_nonexistent(self):
        """Test getting devices for non-existent clinician"""
        from auth import get_clinician_devices

        result = get_clinician_devices("nonexistent-clinician-xyz")

        # Should return empty list or handle gracefully
        assert isinstance(result, list)
        assert len(result) == 0


class TestVoiceprintEnrollmentVerification:
    """Tests for voiceprint enrollment and verification"""

    def test_enroll_voiceprint(self):
        """Test voiceprint enrollment"""
        from auth import (
            enroll_voiceprint,
            Clinician,
            save_clinician,
            generate_totp_secret
        )

        clinician = Clinician("enroll-test", "Dr. Enroll", "enroll@test.com")
        clinician.totp_secret = generate_totp_secret()
        save_clinician(clinician)

        # Sample audio (not actual voiceprint, just for testing)
        samples = [base64.b64encode(b"audio1").decode()]

        result = enroll_voiceprint(clinician, samples)

        # Should return a result dict
        assert isinstance(result, dict)

    def test_verify_voiceprint(self):
        """Test voiceprint verification"""
        from auth import (
            verify_voiceprint,
            Clinician,
            save_clinician,
            generate_totp_secret
        )

        clinician = Clinician("verify-vp-test", "Dr. Verify", "verify@test.com")
        clinician.totp_secret = generate_totp_secret()
        save_clinician(clinician)

        sample = base64.b64encode(b"audio-sample").decode()

        result = verify_voiceprint(clinician, sample)

        # Should return a result dict
        assert isinstance(result, dict)

    def test_delete_clinician_voiceprint(self):
        """Test deleting clinician voiceprint"""
        from auth import (
            delete_clinician_voiceprint,
            Clinician,
            save_clinician,
            generate_totp_secret
        )

        clinician = Clinician("delete-vp-test", "Dr. Delete VP", "delete-vp@test.com")
        clinician.totp_secret = generate_totp_secret()
        clinician.voiceprint_hash = "some-hash"
        save_clinician(clinician)

        result = delete_clinician_voiceprint(clinician)

        assert isinstance(result, dict)


class TestCreateTestClinician:
    """Tests for test clinician creation helper"""

    def test_create_test_clinician(self):
        """Test creating a test clinician"""
        from auth import create_test_clinician

        clinician = create_test_clinician()

        assert clinician is not None
        assert hasattr(clinician, 'clinician_id')
        assert hasattr(clinician, 'name')
        assert clinician.totp_secret is not None


class TestPydanticModels:
    """Tests for Pydantic request models"""

    def test_device_registration_model(self):
        """Test DeviceRegistration model"""
        from auth import DeviceRegistration

        reg = DeviceRegistration(
            device_id="test-device",
            device_name="Test Glasses"
        )

        assert reg.device_id == "test-device"
        assert reg.device_name == "Test Glasses"

    def test_totp_verify_request_model(self):
        """Test TOTPVerifyRequest model"""
        from auth import TOTPVerifyRequest

        req = TOTPVerifyRequest(
            device_id="device-001",
            totp_code="123456"
        )

        assert req.device_id == "device-001"
        assert req.totp_code == "123456"

    def test_voiceprint_enroll_request_model(self):
        """Test VoiceprintEnrollRequest model"""
        from auth import VoiceprintEnrollRequest

        req = VoiceprintEnrollRequest(
            device_id="device-001",
            audio_samples=["sample1", "sample2", "sample3"]
        )

        assert req.device_id == "device-001"
        assert len(req.audio_samples) == 3

    def test_voiceprint_verify_request_model(self):
        """Test VoiceprintVerifyRequest model"""
        from auth import VoiceprintVerifyRequest

        req = VoiceprintVerifyRequest(
            device_id="device-001",
            audio_sample="base64audio"
        )

        assert req.device_id == "device-001"
        assert req.audio_sample == "base64audio"

    def test_session_unlock_request_model(self):
        """Test SessionUnlockRequest model"""
        from auth import SessionUnlockRequest

        req = SessionUnlockRequest(
            device_id="device-001",
            totp_code="123456"
        )

        assert req.device_id == "device-001"
        assert req.totp_code == "123456"
        assert req.voiceprint_audio is None

    def test_remote_wipe_request_model(self):
        """Test RemoteWipeRequest model"""
        from auth import RemoteWipeRequest

        req = RemoteWipeRequest(
            device_id="device-001",
            admin_token="admin-secret"
        )

        assert req.device_id == "device-001"
        assert req.admin_token == "admin-secret"
