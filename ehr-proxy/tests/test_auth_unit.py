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


class TestDevice:
    """Tests for Device model"""

    def test_device_init(self):
        """Should initialize device correctly"""
        from auth import Device

        device = Device("device-001", "clinician-001")

        assert device.device_id == "device-001"
        assert device.clinician_id == "clinician-001"
        assert device.is_active is True
        assert device.is_wiped is False

    def test_device_to_dict(self):
        """Should serialize device to dict"""
        from auth import Device

        device = Device("device-001", "clinician-001")
        device.device_name = "Test Device"
        device.device_type = "vuzix_blade_2"

        data = device.to_dict()

        assert data["device_id"] == "device-001"
        assert data["clinician_id"] == "clinician-001"
        assert data["device_name"] == "Test Device"
        assert data["is_active"] is True
        assert data["is_wiped"] is False

    def test_device_from_dict(self):
        """Should deserialize device from dict"""
        from auth import Device
        from datetime import datetime, timezone

        data = {
            "device_id": "device-001",
            "clinician_id": "clinician-001",
            "device_name": "AR Glasses",
            "device_type": "vuzix_blade_2",
            "paired_at": "2024-01-01T10:00:00+00:00",
            "last_seen": "2024-01-15T15:30:00+00:00",
            "is_active": True,
            "is_wiped": False,
            "session_token": "test-token",
            "session_expires": "2024-01-16T15:30:00+00:00"
        }

        device = Device.from_dict(data)

        assert device.device_id == "device-001"
        assert device.device_name == "AR Glasses"
        assert device.session_token == "test-token"
        assert device.is_active is True

    def test_device_from_dict_minimal(self):
        """Should handle minimal data"""
        from auth import Device

        data = {
            "device_id": "device-001",
            "clinician_id": "clinician-001"
        }

        device = Device.from_dict(data)

        assert device.device_id == "device-001"
        assert device.device_name == "AR Glasses"  # default


class TestGetDevice:
    """Tests for get_device function"""

    @patch("auth._load_json")
    def test_get_device_found(self, mock_load):
        """Should return device when found"""
        from auth import get_device

        mock_load.return_value = {
            "devices": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "device_name": "Test Device"
                }
            }
        }

        device = get_device("device-001")

        assert device is not None
        assert device.device_id == "device-001"
        assert device.device_name == "Test Device"

    @patch("auth._load_json")
    def test_get_device_not_found(self, mock_load):
        """Should return None when not found"""
        from auth import get_device

        mock_load.return_value = {"devices": {}}

        device = get_device("unknown-device")

        assert device is None


class TestSaveDevice:
    """Tests for save_device function"""

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_save_device(self, mock_load, mock_save):
        """Should save device data"""
        from auth import save_device, Device

        mock_load.return_value = {"devices": {}}

        device = Device("device-001", "clinician-001")
        device.device_name = "Test Device"
        save_device(device)

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][1]
        assert "device-001" in saved_data["devices"]


class TestDeleteDevice:
    """Tests for delete_device function"""

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_delete_device_exists(self, mock_load, mock_save):
        """Should delete existing device"""
        from auth import delete_device

        mock_load.return_value = {
            "devices": {
                "device-001": {"device_id": "device-001"}
            }
        }

        delete_device("device-001")

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][1]
        assert "device-001" not in saved_data["devices"]

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_delete_device_not_exists(self, mock_load, mock_save):
        """Should handle non-existent device gracefully"""
        from auth import delete_device

        mock_load.return_value = {"devices": {}}

        delete_device("unknown-device")  # Should not raise

        # Should not save if device didn't exist
        mock_save.assert_not_called()


class TestVoiceprintSessionFunctions:
    """Tests for voiceprint session management functions"""

    @patch("auth._load_json")
    def test_get_voiceprint_session_from_file(self, mock_load):
        """Should load voiceprint session from file"""
        from auth import get_voiceprint_session, _voiceprint_sessions

        # Clear cache
        _voiceprint_sessions.clear()

        mock_load.return_value = {
            "sessions": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "last_verified_at": "2024-01-15T10:00:00+00:00",
                    "confidence_score": 0.9,
                    "re_verify_interval_seconds": 300,
                    "verification_count": 5,
                    "session_start": "2024-01-15T08:00:00+00:00"
                }
            }
        }

        session = get_voiceprint_session("device-001")

        assert session is not None
        assert session.device_id == "device-001"
        assert session.confidence_score == 0.9

    @patch("auth._load_json")
    def test_get_voiceprint_session_not_found(self, mock_load):
        """Should return None when session not found"""
        from auth import get_voiceprint_session, _voiceprint_sessions

        _voiceprint_sessions.clear()
        mock_load.return_value = {"sessions": {}}

        session = get_voiceprint_session("unknown-device")

        assert session is None

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_create_voiceprint_session(self, mock_load, mock_save):
        """Should create new voiceprint session"""
        from auth import create_voiceprint_session, _voiceprint_sessions

        _voiceprint_sessions.clear()
        mock_load.return_value = {"sessions": {}}

        session = create_voiceprint_session("device-001", "clinician-001", 0.95)

        assert session is not None
        assert session.device_id == "device-001"
        assert session.confidence_score == 0.95
        assert session.verification_count == 1

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_update_voiceprint_verification(self, mock_load, mock_save):
        """Should update verification timestamp"""
        from auth import update_voiceprint_verification, _voiceprint_sessions, VoiceprintSession
        from datetime import datetime, timezone

        _voiceprint_sessions.clear()
        _voiceprint_sessions["device-001"] = VoiceprintSession(
            device_id="device-001",
            clinician_id="clinician-001",
            confidence_score=0.8,
            verification_count=3
        )
        mock_load.return_value = {"sessions": {}}

        session = update_voiceprint_verification("device-001", 0.92)

        assert session is not None
        assert session.confidence_score == 0.92
        assert session.verification_count == 4

    @patch("auth._load_json")
    def test_update_voiceprint_verification_not_found(self, mock_load):
        """Should return None when session not found"""
        from auth import update_voiceprint_verification, _voiceprint_sessions

        _voiceprint_sessions.clear()
        mock_load.return_value = {"sessions": {}}

        result = update_voiceprint_verification("unknown-device", 0.9)

        assert result is None

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_delete_voiceprint_session(self, mock_load, mock_save):
        """Should delete voiceprint session"""
        from auth import delete_voiceprint_session, _voiceprint_sessions, VoiceprintSession

        _voiceprint_sessions["device-001"] = VoiceprintSession(
            device_id="device-001",
            clinician_id="clinician-001"
        )
        mock_load.return_value = {
            "sessions": {
                "device-001": {"device_id": "device-001"}
            }
        }

        delete_voiceprint_session("device-001")

        assert "device-001" not in _voiceprint_sessions
        mock_save.assert_called_once()

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_set_re_verify_interval(self, mock_load, mock_save):
        """Should set re-verification interval"""
        from auth import set_re_verify_interval, _voiceprint_sessions, VoiceprintSession

        _voiceprint_sessions["device-001"] = VoiceprintSession(
            device_id="device-001",
            clinician_id="clinician-001",
            re_verify_interval_seconds=300
        )
        mock_load.return_value = {"sessions": {}}

        session = set_re_verify_interval("device-001", 600)

        assert session is not None
        assert session.re_verify_interval_seconds == 600

    @patch("auth._load_json")
    def test_set_re_verify_interval_clamped(self, mock_load):
        """Should clamp interval to valid range"""
        from auth import set_re_verify_interval, _voiceprint_sessions, VoiceprintSession

        _voiceprint_sessions["device-001"] = VoiceprintSession(
            device_id="device-001",
            clinician_id="clinician-001"
        )
        mock_load.return_value = {"sessions": {}}

        # Test minimum clamping
        session = set_re_verify_interval("device-001", 10)
        assert session.re_verify_interval_seconds == 60  # min is 60

    @patch("auth._load_json")
    def test_set_re_verify_interval_not_found(self, mock_load):
        """Should return None when session not found"""
        from auth import set_re_verify_interval, _voiceprint_sessions

        _voiceprint_sessions.clear()
        mock_load.return_value = {"sessions": {}}

        result = set_re_verify_interval("unknown-device", 300)

        assert result is None


class TestSessionManagement:
    """Tests for session creation and verification"""

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_create_session(self, mock_load, mock_save):
        """Should create session token"""
        from auth import create_session, Device

        mock_load.return_value = {"devices": {}}

        device = Device("device-001", "clinician-001")
        token = create_session(device)

        assert token is not None
        assert len(token) > 0
        assert device.session_token == token
        assert device.session_expires is not None

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_verify_session_valid(self, mock_load, mock_save):
        """Should verify valid session"""
        from auth import verify_session, Device
        from datetime import datetime, timezone, timedelta

        future_time = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

        mock_load.return_value = {
            "devices": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "session_token": "valid-token",
                    "session_expires": future_time,
                    "is_wiped": False
                }
            }
        }

        result = verify_session("device-001", "valid-token")

        assert result is True

    @patch("auth._load_json")
    def test_verify_session_invalid_token(self, mock_load):
        """Should reject invalid token"""
        from auth import verify_session
        from datetime import datetime, timezone, timedelta

        mock_load.return_value = {
            "devices": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "session_token": "valid-token",
                    "session_expires": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                    "is_wiped": False
                }
            }
        }

        result = verify_session("device-001", "wrong-token")

        assert result is False

    @patch("auth._load_json")
    def test_verify_session_wiped_device(self, mock_load):
        """Should reject wiped device"""
        from auth import verify_session
        from datetime import datetime, timezone, timedelta

        mock_load.return_value = {
            "devices": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "session_token": "valid-token",
                    "session_expires": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                    "is_wiped": True  # Device was wiped
                }
            }
        }

        result = verify_session("device-001", "valid-token")

        assert result is False

    @patch("auth._load_json")
    def test_verify_session_expired(self, mock_load):
        """Should reject expired session"""
        from auth import verify_session
        from datetime import datetime, timezone, timedelta

        mock_load.return_value = {
            "devices": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "session_token": "valid-token",
                    "session_expires": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),  # Expired
                    "is_wiped": False
                }
            }
        }

        result = verify_session("device-001", "valid-token")

        assert result is False

    @patch("auth._save_json")
    @patch("auth._load_json")
    def test_invalidate_session(self, mock_load, mock_save):
        """Should invalidate session"""
        from auth import invalidate_session
        from datetime import datetime, timezone, timedelta

        mock_load.return_value = {
            "devices": {
                "device-001": {
                    "device_id": "device-001",
                    "clinician_id": "clinician-001",
                    "session_token": "old-token",
                    "session_expires": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
                }
            }
        }

        invalidate_session("device-001")

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][1]
        assert saved_data["devices"]["device-001"]["session_token"] is None


class TestUnlockSession:
    """Tests for unlock_session function"""

    @patch("auth.save_clinician")
    @patch("auth.create_session")
    @patch("auth.verify_totp")
    @patch("auth.get_clinician")
    @patch("auth.get_device")
    def test_unlock_session_success(self, mock_get_device, mock_get_clinician,
                                     mock_verify_totp, mock_create_session, mock_save):
        """Should unlock with valid TOTP"""
        from auth import unlock_session, Device, Clinician

        mock_device = Device("device-001", "clinician-001")
        mock_get_device.return_value = mock_device

        mock_clinician = Clinician("clinician-001", "Dr. Smith", "dr@test.com")
        mock_get_clinician.return_value = mock_clinician

        mock_verify_totp.return_value = True
        mock_create_session.return_value = "new-session-token"

        result = unlock_session("device-001", "123456")

        assert result["success"] is True
        assert result["session_token"] == "new-session-token"
        assert result["clinician_name"] == "Dr. Smith"

    @patch("auth.get_device")
    def test_unlock_session_device_not_found(self, mock_get_device):
        """Should fail when device not found"""
        from auth import unlock_session
        import auth

        # Disable debug auto-creation
        original_debug = auth.DEBUG_SKIP_AUTH
        auth.DEBUG_SKIP_AUTH = False

        mock_get_device.return_value = None

        result = unlock_session("unknown-device", "123456")

        assert result["success"] is False
        assert "not registered" in result["error"]

        auth.DEBUG_SKIP_AUTH = original_debug

    @patch("auth.get_clinician")
    @patch("auth.get_device")
    def test_unlock_session_wiped_device(self, mock_get_device, mock_get_clinician):
        """Should fail for wiped device"""
        from auth import unlock_session, Device

        mock_device = Device("device-001", "clinician-001")
        mock_device.is_wiped = True
        mock_get_device.return_value = mock_device

        result = unlock_session("device-001", "123456")

        assert result["success"] is False
        assert "wiped" in result["error"]

    @patch("auth.verify_totp")
    @patch("auth.get_clinician")
    @patch("auth.get_device")
    def test_unlock_session_invalid_totp(self, mock_get_device, mock_get_clinician, mock_verify_totp):
        """Should fail with invalid TOTP"""
        from auth import unlock_session, Device, Clinician

        mock_get_device.return_value = Device("device-001", "clinician-001")
        mock_get_clinician.return_value = Clinician("clinician-001", "Dr. Smith", "dr@test.com")
        mock_verify_totp.return_value = False

        result = unlock_session("device-001", "000000")

        assert result["success"] is False
        assert "Invalid code" in result["error"]
