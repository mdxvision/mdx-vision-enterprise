"""
MDx Vision - Device Authentication & Security
TOTP, Device Pairing, Voiceprint, Remote Wipe

Security Model:
1. Device pairing via QR code (one-time setup)
2. TOTP verification (daily unlock)
3. Voiceprint verification (sensitive commands)
4. Proximity sensor lock (glasses removed)
5. Remote wipe (lost/stolen)
"""

import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
import hashlib
import secrets
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class DeviceRegistration(BaseModel):
    """Request to register a new device"""
    device_id: str  # Unique device identifier
    device_name: str = "AR Glasses"
    device_type: str = "vuzix_blade_2"


class TOTPVerifyRequest(BaseModel):
    """Request to verify TOTP code"""
    device_id: str
    totp_code: str  # 6-digit code from authenticator app


class VoiceprintEnrollRequest(BaseModel):
    """Request to enroll voiceprint"""
    device_id: str
    audio_samples: List[str]  # Base64 encoded audio samples


class VoiceprintVerifyRequest(BaseModel):
    """Request to verify voiceprint"""
    device_id: str
    audio_sample: str  # Base64 encoded audio


class SessionUnlockRequest(BaseModel):
    """Request to unlock a session with TOTP + optional voiceprint"""
    device_id: str
    totp_code: str
    voiceprint_audio: Optional[str] = None  # Base64 encoded audio


class RemoteWipeRequest(BaseModel):
    """Request to remotely wipe a device"""
    device_id: str
    admin_token: str  # Admin authentication


class VoiceprintSession(BaseModel):
    """
    Voiceprint verification session state for continuous authentication (Feature #77).
    Tracks when voiceprint was last verified and calculates confidence decay.
    """
    device_id: str
    clinician_id: str
    last_verified_at: Optional[datetime] = None
    confidence_score: float = 0.0
    verification_count: int = 0
    session_start: Optional[datetime] = None
    re_verify_interval_seconds: int = 300  # 5 minutes default

    def needs_re_verification(self) -> bool:
        """Check if re-verification is required based on elapsed time"""
        if not self.last_verified_at:
            return True
        now = datetime.now(timezone.utc)
        # Handle naive datetime
        last_verified = self.last_verified_at
        if last_verified.tzinfo is None:
            last_verified = last_verified.replace(tzinfo=timezone.utc)
        elapsed = (now - last_verified).total_seconds()
        return elapsed > self.re_verify_interval_seconds

    def confidence_decay(self) -> float:
        """
        Calculate decayed confidence based on time since last verification.
        Confidence decreases by 1% per minute since last verification.
        """
        if not self.last_verified_at:
            return 0.0
        now = datetime.now(timezone.utc)
        last_verified = self.last_verified_at
        if last_verified.tzinfo is None:
            last_verified = last_verified.replace(tzinfo=timezone.utc)
        elapsed_seconds = (now - last_verified).total_seconds()
        decay_rate = 0.01  # Lose 1% per minute
        decayed = self.confidence_score - (elapsed_seconds / 60 * decay_rate)
        return max(0.0, min(1.0, decayed))

    def seconds_until_re_verification(self) -> int:
        """Get seconds remaining until re-verification is required"""
        if not self.last_verified_at:
            return 0
        now = datetime.now(timezone.utc)
        last_verified = self.last_verified_at
        if last_verified.tzinfo is None:
            last_verified = last_verified.replace(tzinfo=timezone.utc)
        elapsed = (now - last_verified).total_seconds()
        remaining = self.re_verify_interval_seconds - elapsed
        return max(0, int(remaining))


# ═══════════════════════════════════════════════════════════════════════════
# DEVICE & USER STORAGE
# Simple file-based storage - replace with database in production
# ═══════════════════════════════════════════════════════════════════════════

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data", "auth")
os.makedirs(STORAGE_DIR, exist_ok=True)

def _get_storage_path(filename: str) -> str:
    return os.path.join(STORAGE_DIR, filename)


def _load_json(filename: str, default: dict = None) -> dict:
    path = _get_storage_path(filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default or {}


def _save_json(filename: str, data: dict):
    path = _get_storage_path(filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# CLINICIAN MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

class Clinician:
    """Represents a registered clinician"""

    def __init__(self, clinician_id: str, name: str, email: str):
        self.clinician_id = clinician_id
        self.name = name
        self.email = email
        self.totp_secret: Optional[str] = None
        self.devices: List[str] = []  # Device IDs
        self.voiceprint_hash: Optional[str] = None  # Hash of voiceprint features
        self.created_at = datetime.now(timezone.utc)
        self.last_login: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "clinician_id": self.clinician_id,
            "name": self.name,
            "email": self.email,
            "totp_secret": self.totp_secret,
            "devices": self.devices,
            "voiceprint_hash": self.voiceprint_hash,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Clinician":
        c = cls(data["clinician_id"], data["name"], data["email"])
        c.totp_secret = data.get("totp_secret")
        c.devices = data.get("devices", [])
        c.voiceprint_hash = data.get("voiceprint_hash")
        c.created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        c.last_login = datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None
        return c


def get_clinician(clinician_id: str) -> Optional[Clinician]:
    """Get clinician by ID"""
    clinicians = _load_json("clinicians.json", {"clinicians": {}})
    if clinician_id in clinicians.get("clinicians", {}):
        return Clinician.from_dict(clinicians["clinicians"][clinician_id])
    return None


def save_clinician(clinician: Clinician):
    """Save clinician data"""
    clinicians = _load_json("clinicians.json", {"clinicians": {}})
    clinicians["clinicians"][clinician.clinician_id] = clinician.to_dict()
    _save_json("clinicians.json", clinicians)


def get_clinician_by_device(device_id: str) -> Optional[Clinician]:
    """Find clinician that owns a device"""
    devices = _load_json("devices.json", {"devices": {}})
    if device_id in devices.get("devices", {}):
        clinician_id = devices["devices"][device_id].get("clinician_id")
        if clinician_id:
            return get_clinician(clinician_id)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# DEVICE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

class Device:
    """Represents a paired AR glasses device"""

    def __init__(self, device_id: str, clinician_id: str):
        self.device_id = device_id
        self.clinician_id = clinician_id
        self.device_name = "AR Glasses"
        self.device_type = "vuzix_blade_2"
        self.paired_at = datetime.now(timezone.utc)
        self.last_seen: Optional[datetime] = None
        self.is_active = True
        self.is_wiped = False
        self.session_token: Optional[str] = None
        self.session_expires: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "clinician_id": self.clinician_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "paired_at": self.paired_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_active": self.is_active,
            "is_wiped": self.is_wiped,
            "session_token": self.session_token,
            "session_expires": self.session_expires.isoformat() if self.session_expires else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Device":
        d = cls(data["device_id"], data["clinician_id"])
        d.device_name = data.get("device_name", "AR Glasses")
        d.device_type = data.get("device_type", "vuzix_blade_2")
        d.paired_at = datetime.fromisoformat(data["paired_at"]) if data.get("paired_at") else datetime.now(timezone.utc)
        d.last_seen = datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None
        d.is_active = data.get("is_active", True)
        d.is_wiped = data.get("is_wiped", False)
        d.session_token = data.get("session_token")
        d.session_expires = datetime.fromisoformat(data["session_expires"]) if data.get("session_expires") else None
        return d


def get_device(device_id: str) -> Optional[Device]:
    """Get device by ID"""
    devices = _load_json("devices.json", {"devices": {}})
    if device_id in devices.get("devices", {}):
        return Device.from_dict(devices["devices"][device_id])
    return None


def save_device(device: Device):
    """Save device data"""
    devices = _load_json("devices.json", {"devices": {}})
    devices["devices"][device.device_id] = device.to_dict()
    _save_json("devices.json", devices)


def delete_device(device_id: str):
    """Remove device (for remote wipe)"""
    devices = _load_json("devices.json", {"devices": {}})
    if device_id in devices.get("devices", {}):
        del devices["devices"][device_id]
        _save_json("devices.json", devices)


# ═══════════════════════════════════════════════════════════════════════════
# VOICEPRINT SESSION MANAGEMENT (Feature #77 - Continuous Auth)
# ═══════════════════════════════════════════════════════════════════════════

# In-memory cache for active sessions (for performance)
_voiceprint_sessions: Dict[str, VoiceprintSession] = {}


def get_voiceprint_session(device_id: str) -> Optional[VoiceprintSession]:
    """Get voiceprint session for a device"""
    # Check in-memory cache first
    if device_id in _voiceprint_sessions:
        return _voiceprint_sessions[device_id]

    # Load from file storage
    sessions = _load_json("voiceprint_sessions.json", {"sessions": {}})
    if device_id in sessions.get("sessions", {}):
        data = sessions["sessions"][device_id]
        # Parse datetime fields
        if data.get("last_verified_at"):
            data["last_verified_at"] = datetime.fromisoformat(data["last_verified_at"])
        if data.get("session_start"):
            data["session_start"] = datetime.fromisoformat(data["session_start"])
        session = VoiceprintSession(**data)
        _voiceprint_sessions[device_id] = session
        return session

    return None


def save_voiceprint_session(session: VoiceprintSession):
    """Save voiceprint session state"""
    # Update in-memory cache
    _voiceprint_sessions[session.device_id] = session

    # Persist to file
    sessions = _load_json("voiceprint_sessions.json", {"sessions": {}})
    session_data = session.model_dump()
    # Convert datetime to ISO format for JSON
    if session_data.get("last_verified_at"):
        session_data["last_verified_at"] = session_data["last_verified_at"].isoformat()
    if session_data.get("session_start"):
        session_data["session_start"] = session_data["session_start"].isoformat()
    sessions["sessions"][session.device_id] = session_data
    _save_json("voiceprint_sessions.json", sessions)


def create_voiceprint_session(device_id: str, clinician_id: str, confidence: float = 0.0) -> VoiceprintSession:
    """Create a new voiceprint session after successful verification"""
    now = datetime.now(timezone.utc)
    session = VoiceprintSession(
        device_id=device_id,
        clinician_id=clinician_id,
        last_verified_at=now if confidence > 0 else None,
        confidence_score=confidence,
        verification_count=1 if confidence > 0 else 0,
        session_start=now
    )
    save_voiceprint_session(session)
    return session


def update_voiceprint_verification(device_id: str, confidence: float) -> Optional[VoiceprintSession]:
    """Update session after successful re-verification"""
    session = get_voiceprint_session(device_id)
    if not session:
        return None

    session.last_verified_at = datetime.now(timezone.utc)
    session.confidence_score = confidence
    session.verification_count += 1
    save_voiceprint_session(session)
    return session


def delete_voiceprint_session(device_id: str):
    """Delete voiceprint session (logout/wipe)"""
    if device_id in _voiceprint_sessions:
        del _voiceprint_sessions[device_id]

    sessions = _load_json("voiceprint_sessions.json", {"sessions": {}})
    if device_id in sessions.get("sessions", {}):
        del sessions["sessions"][device_id]
        _save_json("voiceprint_sessions.json", sessions)


def set_re_verify_interval(device_id: str, interval_seconds: int) -> Optional[VoiceprintSession]:
    """Configure re-verification interval for a device"""
    session = get_voiceprint_session(device_id)
    if not session:
        return None

    session.re_verify_interval_seconds = max(60, min(3600, interval_seconds))  # 1-60 minutes
    save_voiceprint_session(session)
    return session


# ═══════════════════════════════════════════════════════════════════════════
# TOTP AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════

def generate_totp_secret() -> str:
    """Generate a new TOTP secret"""
    return pyotp.random_base32()


def get_totp_qr_code(clinician: Clinician, as_base64: bool = True) -> str:
    """
    Generate QR code for TOTP setup.
    User scans this with Google Authenticator / Authy / etc.
    """
    if not clinician.totp_secret:
        clinician.totp_secret = generate_totp_secret()
        save_clinician(clinician)

    totp = pyotp.TOTP(clinician.totp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=clinician.email,
        issuer_name="MDx Vision"
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    if as_base64:
        # Return as base64 PNG for embedding in web/app
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    else:
        # Return as SVG string
        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        buffer = io.BytesIO()
        img.save(buffer)
        buffer.seek(0)
        return buffer.read().decode('utf-8')


def verify_totp(clinician: Clinician, code: str) -> bool:
    """Verify a TOTP code"""
    # DEBUG: Allow test code "000000" in debug mode
    if DEBUG_SKIP_AUTH and code == TEST_TOTP_CODE:
        print(f"⚠️ DEBUG: Accepting test TOTP code for {clinician.name}")
        return True

    if not clinician.totp_secret:
        return False

    totp = pyotp.TOTP(clinician.totp_secret)
    # valid_window=1 allows 1 step before/after for clock drift
    return totp.verify(code, valid_window=1)


# ═══════════════════════════════════════════════════════════════════════════
# DEVICE PAIRING
# ═══════════════════════════════════════════════════════════════════════════

def generate_pairing_token(clinician_id: str) -> str:
    """Generate a one-time pairing token"""
    token = secrets.token_urlsafe(32)

    # Store token with expiration (5 minutes)
    tokens = _load_json("pairing_tokens.json", {"tokens": {}})
    tokens["tokens"][token] = {
        "clinician_id": clinician_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    }
    _save_json("pairing_tokens.json", tokens)

    return token


def get_pairing_qr_code(clinician_id: str, base_url: str = "https://mdxvision.local") -> dict:
    """
    Generate QR code for device pairing.
    Glasses scan this to register with the clinician's account.
    """
    token = generate_pairing_token(clinician_id)

    # QR contains JSON with pairing info
    pairing_data = {
        "action": "pair_device",
        "token": token,
        "api_url": base_url,
        "expires_in": 300  # 5 minutes
    }

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(pairing_data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    return {
        "qr_code": qr_base64,
        "token": token,
        "expires_in": 300
    }


def complete_device_pairing(token: str, device_id: str, device_name: str = "AR Glasses") -> dict:
    """
    Complete device pairing after QR scan.
    Returns success/failure and session token if successful.
    """
    tokens = _load_json("pairing_tokens.json", {"tokens": {}})

    if token not in tokens.get("tokens", {}):
        return {"success": False, "error": "Invalid pairing token"}

    token_data = tokens["tokens"][token]
    expires_at = datetime.fromisoformat(token_data["expires_at"])

    if datetime.now(timezone.utc) > expires_at:
        # Clean up expired token
        del tokens["tokens"][token]
        _save_json("pairing_tokens.json", tokens)
        return {"success": False, "error": "Pairing token expired"}

    clinician_id = token_data["clinician_id"]
    clinician = get_clinician(clinician_id)

    if not clinician:
        return {"success": False, "error": "Clinician not found"}

    # Create device
    device = Device(device_id, clinician_id)
    device.device_name = device_name
    device.last_seen = datetime.now(timezone.utc)
    save_device(device)

    # Add device to clinician's list
    if device_id not in clinician.devices:
        clinician.devices.append(device_id)
        save_clinician(clinician)

    # Clean up used token
    del tokens["tokens"][token]
    _save_json("pairing_tokens.json", tokens)

    return {
        "success": True,
        "clinician_name": clinician.name,
        "device_id": device_id,
        "message": "Device paired successfully. Please set up TOTP on your authenticator app."
    }


# ═══════════════════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def create_session(device: Device, duration_hours: int = 12) -> str:
    """Create a new session for a device"""
    session_token = secrets.token_urlsafe(32)
    device.session_token = session_token
    device.session_expires = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
    device.last_seen = datetime.now(timezone.utc)
    save_device(device)
    return session_token


def verify_session(device_id: str, session_token: str) -> bool:
    """Verify a session is valid"""
    device = get_device(device_id)
    if not device:
        return False

    if device.is_wiped:
        return False

    if device.session_token != session_token:
        return False

    if device.session_expires and datetime.now(timezone.utc) > device.session_expires:
        return False

    # Update last seen
    device.last_seen = datetime.now(timezone.utc)
    save_device(device)

    return True


def invalidate_session(device_id: str):
    """Invalidate a device session (logout/lock)"""
    device = get_device(device_id)
    if device:
        device.session_token = None
        device.session_expires = None
        save_device(device)


# ═══════════════════════════════════════════════════════════════════════════
# UNLOCK FLOW
# ═══════════════════════════════════════════════════════════════════════════

def unlock_session(device_id: str, totp_code: str) -> dict:
    """
    Unlock a session with TOTP verification.
    Called when user says the 6-digit code.
    """
    device = get_device(device_id)

    # DEBUG: Auto-create test device and clinician if not exists
    if not device and DEBUG_SKIP_AUTH:
        print(f"⚠️ DEBUG: Auto-creating test device and clinician for {device_id}")
        # Create or get test clinician
        test_clinician = get_clinician("test-clinician-001")
        if not test_clinician:
            test_clinician = create_test_clinician()
        # Create device
        device = Device(device_id, test_clinician.clinician_id)
        device.device_name = "Debug Test Device"
        save_device(device)
        test_clinician.devices.append(device_id)
        save_clinician(test_clinician)

    if not device:
        return {"success": False, "error": "Device not registered"}

    if device.is_wiped:
        return {"success": False, "error": "Device has been wiped. Re-pair required."}

    clinician = get_clinician(device.clinician_id)
    if not clinician:
        return {"success": False, "error": "Clinician not found"}

    # Verify TOTP
    if not verify_totp(clinician, totp_code):
        return {"success": False, "error": "Invalid code. Check your authenticator app."}

    # Create session
    session_token = create_session(device)
    clinician.last_login = datetime.now(timezone.utc)
    save_clinician(clinician)

    return {
        "success": True,
        "session_token": session_token,
        "clinician_name": clinician.name,
        "expires_in": 12 * 60 * 60  # 12 hours in seconds
    }


# ═══════════════════════════════════════════════════════════════════════════
# REMOTE WIPE
# ═══════════════════════════════════════════════════════════════════════════

# Admin token for remote wipe - in production, use proper admin auth
ADMIN_TOKEN = os.environ.get("MDX_ADMIN_TOKEN", "mdx-admin-secret-change-in-prod")

# DEBUG: Set to True to allow "000000" as a test TOTP code (bypasses real verification)
DEBUG_SKIP_AUTH = os.environ.get("DEBUG_SKIP_AUTH", "true").lower() == "true"
TEST_TOTP_CODE = "000000"  # Magic code for testing


def remote_wipe_device(device_id: str, admin_token: str) -> dict:
    """
    Remotely wipe a device.
    Marks device as wiped - next time it connects, it will be locked out.
    """
    if admin_token != ADMIN_TOKEN:
        return {"success": False, "error": "Invalid admin token"}

    device = get_device(device_id)
    if not device:
        return {"success": False, "error": "Device not found"}

    # Mark as wiped
    device.is_wiped = True
    device.is_active = False
    device.session_token = None
    device.session_expires = None
    save_device(device)

    # Remove from clinician's device list
    clinician = get_clinician(device.clinician_id)
    if clinician and device_id in clinician.devices:
        clinician.devices.remove(device_id)
        save_clinician(clinician)

    return {
        "success": True,
        "message": f"Device {device_id} has been wiped. It cannot be used until re-paired."
    }


def get_clinician_devices(clinician_id: str) -> List[dict]:
    """Get all devices for a clinician"""
    clinician = get_clinician(clinician_id)
    if not clinician:
        return []

    devices = []
    for device_id in clinician.devices:
        device = get_device(device_id)
        if device:
            devices.append({
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "paired_at": device.paired_at.isoformat(),
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "is_active": device.is_active,
                "is_wiped": device.is_wiped,
                "has_active_session": device.session_token is not None and (
                    device.session_expires is None or datetime.now(timezone.utc) < device.session_expires
                )
            })

    return devices


# ═══════════════════════════════════════════════════════════════════════════
# VOICEPRINT (SpeechBrain ECAPA-TDNN Speaker Recognition)
# ═══════════════════════════════════════════════════════════════════════════

# Import real voiceprint module
from voiceprint import (
    enroll_voiceprint as vp_enroll,
    verify_voiceprint as vp_verify,
    is_enrolled as vp_is_enrolled,
    delete_voiceprint as vp_delete,
    get_enrollment_phrases
)


def enroll_voiceprint(clinician: Clinician, audio_samples: List[str]) -> dict:
    """
    Enroll voiceprint from audio samples using SpeechBrain ECAPA-TDNN.

    Requires 3+ audio samples of the clinician speaking enrollment phrases.
    Extracts speaker embeddings and stores the average for verification.
    """
    result = vp_enroll(
        clinician_id=clinician.clinician_id,
        audio_samples=audio_samples,
        clinician_name=clinician.name
    )

    if result.get("success"):
        # Mark clinician as having voiceprint enrolled
        clinician.voiceprint_hash = f"enrolled:{clinician.clinician_id}"
        save_clinician(clinician)

    return result


def verify_voiceprint(clinician: Clinician, audio_sample: str) -> dict:
    """
    Verify voiceprint matches enrolled sample using SpeechBrain.

    Compares the audio sample's speaker embedding against the stored
    enrollment embedding using cosine similarity.

    Returns confidence score (0-1) and verification result.
    """
    if not vp_is_enrolled(clinician.clinician_id):
        return {"success": False, "error": "No voiceprint enrolled", "confidence": 0}

    result = vp_verify(
        clinician_id=clinician.clinician_id,
        audio_sample=audio_sample
    )

    return result


def delete_clinician_voiceprint(clinician: Clinician) -> dict:
    """Delete a clinician's voiceprint enrollment."""
    result = vp_delete(clinician.clinician_id)
    if result.get("success"):
        clinician.voiceprint_hash = None
        save_clinician(clinician)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY: Create test clinician for development
# ═══════════════════════════════════════════════════════════════════════════

def create_test_clinician() -> Clinician:
    """Create a test clinician for development"""
    clinician = Clinician(
        clinician_id="test-clinician-001",
        name="Dr. Test User",
        email="test@mdxvision.com"
    )
    clinician.totp_secret = generate_totp_secret()
    save_clinician(clinician)

    print(f"✅ Test clinician created: {clinician.name}")
    print(f"   TOTP Secret: {clinician.totp_secret}")
    print(f"   Add to authenticator app or use: pyotp.TOTP('{clinician.totp_secret}').now()")

    return clinician


if __name__ == "__main__":
    # Create test clinician when run directly
    clinician = create_test_clinician()

    # Show current TOTP code
    totp = pyotp.TOTP(clinician.totp_secret)
    print(f"   Current TOTP code: {totp.now()}")
