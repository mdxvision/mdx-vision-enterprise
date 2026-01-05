"""
Unit tests for auth.py - Device Authentication & Security

Covers:
- VoiceprintSession model methods
- Clinician model serialization
- TOTP generation/verification
- Device registration
- Storage functions
- Edge cases
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta
import json
import os


class TestVoiceprintSession:
    """Tests for VoiceprintSession model (Feature #77)"""

    def test_needs_re_verification_when_never_verified(self):
        """Should need verification when never verified"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician"
        )
        assert session.needs_re_verification() is True

    def test_needs_re_verification_after_interval(self):
        """Should need verification after interval expires"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            last_verified_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            re_verify_interval_seconds=300  # 5 minutes
        )
        assert session.needs_re_verification() is True

    def test_no_re_verification_within_interval(self):
        """Should not need verification within interval"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            last_verified_at=datetime.now(timezone.utc) - timedelta(minutes=2),
            re_verify_interval_seconds=300  # 5 minutes
        )
        assert session.needs_re_verification() is False

    def test_confidence_decay_no_verification(self):
        """Should return 0 confidence when never verified"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            confidence_score=0.95
        )
        assert session.confidence_decay() == 0.0

    def test_confidence_decay_over_time(self):
        """Should decay confidence over time"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            last_verified_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            confidence_score=0.95,
            re_verify_interval_seconds=300
        )
        decayed = session.confidence_decay()
        # Should lose 5% over 5 minutes (1% per minute)
        assert 0.85 < decayed < 0.95

    def test_confidence_decay_floor_at_zero(self):
        """Should not go below zero confidence"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            last_verified_at=datetime.now(timezone.utc) - timedelta(hours=2),
            confidence_score=0.5,
            re_verify_interval_seconds=300
        )
        decayed = session.confidence_decay()
        assert decayed == 0.0

    def test_seconds_until_re_verification_never_verified(self):
        """Should return 0 when never verified"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician"
        )
        assert session.seconds_until_re_verification() == 0

    def test_seconds_until_re_verification_active(self):
        """Should return remaining seconds"""
        from auth import VoiceprintSession

        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            last_verified_at=datetime.now(timezone.utc) - timedelta(minutes=2),
            re_verify_interval_seconds=300
        )
        remaining = session.seconds_until_re_verification()
        assert 170 < remaining < 190  # ~3 minutes remaining

    def test_naive_datetime_handling(self):
        """Should handle naive datetimes correctly"""
        from auth import VoiceprintSession

        # Create session with naive datetime (no timezone)
        naive_time = datetime.now() - timedelta(minutes=3)
        session = VoiceprintSession(
            device_id="test-device",
            clinician_id="test-clinician",
            last_verified_at=naive_time,
            confidence_score=0.9,
            re_verify_interval_seconds=300
        )

        # Should handle without error
        assert session.needs_re_verification() is False
        assert 0 < session.confidence_decay() < 1.0
        assert session.seconds_until_re_verification() > 0


class TestClinician:
    """Tests for Clinician model"""

    def test_clinician_init(self):
        """Should initialize clinician correctly"""
        from auth import Clinician

        clinician = Clinician(
            clinician_id="DR001",
            name="Dr. Smith",
            email="dr.smith@hospital.com"
        )

        assert clinician.clinician_id == "DR001"
        assert clinician.name == "Dr. Smith"
        assert clinician.email == "dr.smith@hospital.com"
        assert clinician.totp_secret is None
        assert clinician.devices == []

    def test_clinician_to_dict(self):
        """Should serialize to dict correctly"""
        from auth import Clinician

        clinician = Clinician("DR001", "Dr. Smith", "dr.smith@hospital.com")
        clinician.totp_secret = "SECRET123"
        clinician.devices = ["device-1", "device-2"]

        data = clinician.to_dict()

        assert data["clinician_id"] == "DR001"
        assert data["name"] == "Dr. Smith"
        assert data["totp_secret"] == "SECRET123"
        assert data["devices"] == ["device-1", "device-2"]
        assert "created_at" in data

    def test_clinician_from_dict(self):
        """Should deserialize from dict correctly"""
        from auth import Clinician

        data = {
            "clinician_id": "DR001",
            "name": "Dr. Smith",
            "email": "dr.smith@hospital.com",
            "totp_secret": "SECRET123",
            "devices": ["device-1"],
            "voiceprint_hash": "hash123",
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_login": "2024-01-15T10:30:00+00:00"
        }

        clinician = Clinician.from_dict(data)

        assert clinician.clinician_id == "DR001"
        assert clinician.totp_secret == "SECRET123"
        assert clinician.devices == ["device-1"]
        assert clinician.voiceprint_hash == "hash123"
        assert clinician.last_login is not None

    def test_clinician_from_dict_missing_optional_fields(self):
        """Should handle missing optional fields"""
        from auth import Clinician

        data = {
            "clinician_id": "DR001",
            "name": "Dr. Smith",
            "email": "dr.smith@hospital.com"
        }

        clinician = Clinician.from_dict(data)

        assert clinician.clinician_id == "DR001"
        assert clinician.totp_secret is None
        assert clinician.devices == []
        assert clinician.last_login is None


class TestStorageFunctions:
    """Tests for JSON storage functions"""

    @patch("builtins.open", mock_open(read_data='{"test": "data"}'))
    @patch("os.path.exists", return_value=True)
    def test_load_json_existing_file(self, mock_exists):
        """Should load JSON from existing file"""
        from auth import _load_json

        data = _load_json("test.json")
        assert data == {"test": "data"}

    @patch("os.path.exists", return_value=False)
    def test_load_json_missing_file_returns_default(self, mock_exists):
        """Should return default when file missing"""
        from auth import _load_json

        data = _load_json("missing.json", {"default": True})
        assert data == {"default": True}

    @patch("os.path.exists", return_value=False)
    def test_load_json_missing_file_empty_default(self, mock_exists):
        """Should return empty dict when no default"""
        from auth import _load_json

        data = _load_json("missing.json")
        assert data == {}

    @patch("builtins.open", mock_open())
    def test_save_json(self):
        """Should save JSON to file"""
        from auth import _save_json

        test_data = {"key": "value", "date": datetime.now(timezone.utc)}
        _save_json("test.json", test_data)

        # Verify file was written
        open.assert_called_once()


class TestTOTPFunctions:
    """Tests for TOTP generation and verification"""

    def test_generate_totp_secret(self):
        """Should generate valid TOTP secret"""
        import pyotp

        secret = pyotp.random_base32()
        assert len(secret) == 32
        assert secret.isalnum()

    def test_verify_valid_totp_code(self):
        """Should verify valid TOTP code"""
        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()

        assert totp.verify(current_code) is True

    def test_reject_invalid_totp_code(self):
        """Should reject invalid TOTP code"""
        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        assert totp.verify("000000") is False
        assert totp.verify("123456") is False

    def test_totp_window_tolerance(self):
        """Should handle clock drift with window"""
        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()

        # Should verify within window
        assert totp.verify(current_code, valid_window=1) is True


class TestDeviceRegistration:
    """Tests for device registration"""

    def test_device_registration_model(self):
        """Should create device registration"""
        from auth import DeviceRegistration

        reg = DeviceRegistration(
            device_id="vuzix-001",
            device_name="Dr. Smith's Glasses",
            device_type="vuzix_blade_2"
        )

        assert reg.device_id == "vuzix-001"
        assert reg.device_name == "Dr. Smith's Glasses"
        assert reg.device_type == "vuzix_blade_2"

    def test_device_registration_defaults(self):
        """Should use default values"""
        from auth import DeviceRegistration

        reg = DeviceRegistration(device_id="test-123")

        assert reg.device_id == "test-123"
        assert reg.device_name == "AR Glasses"
        assert reg.device_type == "vuzix_blade_2"


class TestSessionUnlockRequest:
    """Tests for session unlock request model"""

    def test_session_unlock_with_voiceprint(self):
        """Should create unlock request with voiceprint"""
        from auth import SessionUnlockRequest

        req = SessionUnlockRequest(
            device_id="device-001",
            totp_code="123456",
            voiceprint_audio="base64audiodata"
        )

        assert req.device_id == "device-001"
        assert req.totp_code == "123456"
        assert req.voiceprint_audio == "base64audiodata"

    def test_session_unlock_without_voiceprint(self):
        """Should allow unlock without voiceprint"""
        from auth import SessionUnlockRequest

        req = SessionUnlockRequest(
            device_id="device-001",
            totp_code="123456"
        )

        assert req.voiceprint_audio is None


class TestQRCodeGeneration:
    """Tests for QR code generation"""

    def test_qrcode_generation(self):
        """Should generate QR code"""
        import qrcode
        import io

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data("test-data")
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        assert buffer.getvalue()[:4] == b'\x89PNG'  # PNG magic bytes


class TestRemoteWipeRequest:
    """Tests for remote wipe request model"""

    def test_remote_wipe_request(self):
        """Should create remote wipe request"""
        from auth import RemoteWipeRequest

        req = RemoteWipeRequest(
            device_id="lost-device-001",
            admin_token="admin-secret-token"
        )

        assert req.device_id == "lost-device-001"
        assert req.admin_token == "admin-secret-token"


class TestVoiceprintEnrollRequest:
    """Tests for voiceprint enrollment request"""

    def test_voiceprint_enroll_request(self):
        """Should create enrollment request"""
        from auth import VoiceprintEnrollRequest

        req = VoiceprintEnrollRequest(
            device_id="device-001",
            audio_samples=["sample1base64", "sample2base64", "sample3base64"]
        )

        assert req.device_id == "device-001"
        assert len(req.audio_samples) == 3


class TestVoiceprintVerifyRequest:
    """Tests for voiceprint verification request"""

    def test_voiceprint_verify_request(self):
        """Should create verification request"""
        from auth import VoiceprintVerifyRequest

        req = VoiceprintVerifyRequest(
            device_id="device-001",
            audio_sample="verifyaudiobase64"
        )

        assert req.device_id == "device-001"
        assert req.audio_sample == "verifyaudiobase64"


class TestGetClinician:
    """Tests for get_clinician function"""

    @patch("auth._load_json")
    def test_get_clinician_found(self, mock_load):
        """Should return clinician when found"""
        from auth import get_clinician

        mock_load.return_value = {
            "clinicians": {
                "DR001": {
                    "clinician_id": "DR001",
                    "name": "Dr. Smith",
                    "email": "dr.smith@hospital.com",
                    "created_at": "2024-01-01T00:00:00+00:00"
                }
            }
        }

        clinician = get_clinician("DR001")

        assert clinician is not None
        assert clinician.clinician_id == "DR001"
        assert clinician.name == "Dr. Smith"

    @patch("auth._load_json")
    def test_get_clinician_not_found(self, mock_load):
        """Should return None when not found"""
        from auth import get_clinician

        mock_load.return_value = {"clinicians": {}}

        clinician = get_clinician("UNKNOWN")
        assert clinician is None

    @patch("auth._load_json")
    def test_get_clinician_empty_storage(self, mock_load):
        """Should handle empty storage"""
        from auth import get_clinician

        mock_load.return_value = {}

        clinician = get_clinician("DR001")
        assert clinician is None


class TestSaveClinician:
    """Tests for save_clinician function"""

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_save_new_clinician(self, mock_load, mock_save):
        """Should save new clinician"""
        from auth import save_clinician, Clinician

        mock_load.return_value = {"clinicians": {}}

        clinician = Clinician("DR001", "Dr. Smith", "dr.smith@hospital.com")
        save_clinician(clinician)

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][1]
        assert "DR001" in saved_data["clinicians"]

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_save_update_clinician(self, mock_load, mock_save):
        """Should update existing clinician"""
        from auth import save_clinician, Clinician

        mock_load.return_value = {
            "clinicians": {
                "DR001": {
                    "clinician_id": "DR001",
                    "name": "Old Name",
                    "email": "old@hospital.com"
                }
            }
        }

        clinician = Clinician("DR001", "New Name", "new@hospital.com")
        save_clinician(clinician)

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][1]
        assert saved_data["clinicians"]["DR001"]["name"] == "New Name"
