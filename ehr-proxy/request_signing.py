"""
Request Signing for Device Authentication (Issue #97)

Implements HMAC-SHA256 request signing to:
- Prevent replay attacks
- Prevent man-in-the-middle tampering
- Ensure requests originate from authenticated devices
- Provide non-repudiation for HIPAA compliance

Signature format:
    X-MDx-Device-ID: device_12345
    X-MDx-Timestamp: 2026-01-22T10:30:00Z
    X-MDx-Signature: base64(HMAC-SHA256(canonical_request))

Canonical request:
    HTTP_METHOD + "\n" +
    REQUEST_PATH + "\n" +
    TIMESTAMP + "\n" +
    SHA256(REQUEST_BODY)
"""

import hmac
import hashlib
import base64
import secrets
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignatureError(Exception):
    """Base exception for signature errors."""
    pass


class InvalidSignatureError(SignatureError):
    """Signature verification failed."""
    pass


class ExpiredTimestampError(SignatureError):
    """Request timestamp is outside acceptable window."""
    pass


class UnknownDeviceError(SignatureError):
    """Device ID not found in registry."""
    pass


class RevokedDeviceError(SignatureError):
    """Device has been revoked."""
    pass


class DeviceStatus(str, Enum):
    """Device registration status."""
    ACTIVE = "active"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class DeviceRegistration:
    """Registered device with signing credentials."""
    device_id: str
    device_name: str
    device_type: str  # "glasses", "web", "mobile"
    secret_key: str  # Base64-encoded HMAC secret
    status: DeviceStatus = DeviceStatus.ACTIVE
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used_at: Optional[str] = None
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary (excludes secret for safety)."""
        d = asdict(self)
        d["status"] = self.status.value
        # Don't expose secret key in API responses
        d.pop("secret_key", None)
        return d

    def to_dict_with_secret(self) -> Dict:
        """Convert to dictionary including secret (for storage)."""
        d = asdict(self)
        d["status"] = self.status.value
        return d


class RequestSigner:
    """Client-side request signing utility."""

    def __init__(self, device_id: str, secret_key: str):
        """
        Initialize signer with device credentials.

        Args:
            device_id: Unique device identifier
            secret_key: Base64-encoded HMAC secret key
        """
        self.device_id = device_id
        self.secret_key = base64.b64decode(secret_key)

    def sign_request(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, str]:
        """
        Generate signature headers for a request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path (e.g., /api/v1/patient/123)
            body: Request body bytes (optional)
            timestamp: Request timestamp (defaults to now)

        Returns:
            Dictionary of headers to add to request
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Create canonical request
        canonical = self._create_canonical_request(method, path, timestamp_str, body)

        # Sign with HMAC-SHA256
        signature = hmac.new(
            self.secret_key,
            canonical.encode("utf-8"),
            hashlib.sha256
        ).digest()

        signature_b64 = base64.b64encode(signature).decode("utf-8")

        return {
            "X-MDx-Device-ID": self.device_id,
            "X-MDx-Timestamp": timestamp_str,
            "X-MDx-Signature": signature_b64
        }

    def _create_canonical_request(
        self,
        method: str,
        path: str,
        timestamp: str,
        body: Optional[bytes]
    ) -> str:
        """Create canonical request string for signing."""
        # Hash the body (empty string if no body)
        if body:
            body_hash = hashlib.sha256(body).hexdigest()
        else:
            body_hash = hashlib.sha256(b"").hexdigest()

        return f"{method.upper()}\n{path}\n{timestamp}\n{body_hash}"


class DeviceRegistry:
    """
    Registry of authenticated devices and their signing keys.

    In production, this would be backed by a database.
    For now, uses in-memory storage with file persistence.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize device registry.

        Args:
            storage_path: Path to JSON file for persistence (optional)
        """
        self.storage_path = storage_path or os.environ.get(
            "DEVICE_REGISTRY_PATH",
            "data/device_registry.json"
        )
        self._devices: Dict[str, DeviceRegistration] = {}
        self._load()

    def _load(self):
        """Load devices from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for device_id, device_data in data.items():
                        device_data["status"] = DeviceStatus(device_data["status"])
                        self._devices[device_id] = DeviceRegistration(**device_data)
                logger.info(f"Loaded {len(self._devices)} devices from registry")
        except Exception as e:
            logger.warning(f"Could not load device registry: {e}")

    def _save(self):
        """Persist devices to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                data = {
                    device_id: device.to_dict_with_secret()
                    for device_id, device in self._devices.items()
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save device registry: {e}")

    def register_device(
        self,
        device_name: str,
        device_type: str
    ) -> Tuple[str, str]:
        """
        Register a new device and generate signing credentials.

        Args:
            device_name: Human-readable device name
            device_type: Device type (glasses, web, mobile)

        Returns:
            Tuple of (device_id, secret_key)
        """
        # Generate unique device ID
        device_id = f"mdx_{device_type}_{secrets.token_hex(8)}"

        # Generate 256-bit secret key
        secret_key = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")

        # Create registration
        registration = DeviceRegistration(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            secret_key=secret_key
        )

        self._devices[device_id] = registration
        self._save()

        logger.info(f"Registered new device: {device_id} ({device_name})")

        return device_id, secret_key

    def get_device(self, device_id: str) -> Optional[DeviceRegistration]:
        """Get device by ID."""
        return self._devices.get(device_id)

    def list_devices(self, include_revoked: bool = False) -> list:
        """List all registered devices."""
        devices = []
        for device in self._devices.values():
            if include_revoked or device.status != DeviceStatus.REVOKED:
                devices.append(device.to_dict())
        return devices

    def revoke_device(self, device_id: str, reason: str = "Manual revocation"):
        """
        Revoke a device's signing credentials.

        Args:
            device_id: Device to revoke
            reason: Reason for revocation
        """
        device = self._devices.get(device_id)
        if device:
            device.status = DeviceStatus.REVOKED
            device.revoked_at = datetime.now(timezone.utc).isoformat()
            device.revocation_reason = reason
            self._save()
            logger.warning(f"Revoked device {device_id}: {reason}")

    def rotate_key(self, device_id: str) -> Optional[str]:
        """
        Rotate a device's signing key.

        Args:
            device_id: Device to rotate key for

        Returns:
            New secret key, or None if device not found
        """
        device = self._devices.get(device_id)
        if device and device.status == DeviceStatus.ACTIVE:
            new_secret = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
            device.secret_key = new_secret
            self._save()
            logger.info(f"Rotated key for device {device_id}")
            return new_secret
        return None

    def update_last_used(self, device_id: str):
        """Update device's last used timestamp."""
        device = self._devices.get(device_id)
        if device:
            device.last_used_at = datetime.now(timezone.utc).isoformat()
            # Don't save on every request - too expensive
            # Could batch these updates


class SignatureVerifier:
    """Server-side request signature verification."""

    # Maximum age of request timestamp (prevents replay attacks)
    MAX_TIMESTAMP_AGE = timedelta(minutes=5)

    def __init__(self, device_registry: DeviceRegistry):
        """
        Initialize verifier with device registry.

        Args:
            device_registry: Registry of authenticated devices
        """
        self.registry = device_registry

    def verify_request(
        self,
        device_id: str,
        timestamp: str,
        signature: str,
        method: str,
        path: str,
        body: Optional[bytes] = None
    ) -> DeviceRegistration:
        """
        Verify a signed request.

        Args:
            device_id: Device ID from X-MDx-Device-ID header
            timestamp: Timestamp from X-MDx-Timestamp header
            signature: Signature from X-MDx-Signature header
            method: HTTP method
            path: Request path
            body: Request body bytes

        Returns:
            DeviceRegistration if verification succeeds

        Raises:
            UnknownDeviceError: Device not found
            RevokedDeviceError: Device has been revoked
            ExpiredTimestampError: Timestamp outside acceptable window
            InvalidSignatureError: Signature verification failed
        """
        # 1. Look up device
        device = self.registry.get_device(device_id)
        if not device:
            logger.warning(f"Unknown device attempted request: {device_id}")
            raise UnknownDeviceError(f"Device not found: {device_id}")

        # 2. Check device status
        if device.status == DeviceStatus.REVOKED:
            logger.warning(f"Revoked device attempted request: {device_id}")
            raise RevokedDeviceError(f"Device has been revoked: {device_id}")

        # 3. Verify timestamp is within acceptable window
        try:
            request_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            request_time = request_time.replace(tzinfo=timezone.utc)
        except ValueError:
            raise ExpiredTimestampError("Invalid timestamp format")

        now = datetime.now(timezone.utc)
        age = abs(now - request_time)

        if age > self.MAX_TIMESTAMP_AGE:
            logger.warning(f"Expired timestamp from device {device_id}: {timestamp}")
            raise ExpiredTimestampError(
                f"Request timestamp too old: {age.total_seconds():.0f}s"
            )

        # 4. Recreate canonical request and verify signature
        secret_key = base64.b64decode(device.secret_key)

        # Hash the body
        if body:
            body_hash = hashlib.sha256(body).hexdigest()
        else:
            body_hash = hashlib.sha256(b"").hexdigest()

        canonical = f"{method.upper()}\n{path}\n{timestamp}\n{body_hash}"

        expected_signature = hmac.new(
            secret_key,
            canonical.encode("utf-8"),
            hashlib.sha256
        ).digest()

        try:
            provided_signature = base64.b64decode(signature)
        except Exception:
            raise InvalidSignatureError("Invalid signature encoding")

        if not hmac.compare_digest(expected_signature, provided_signature):
            logger.warning(f"Invalid signature from device {device_id}")
            raise InvalidSignatureError("Signature verification failed")

        # 5. Update last used timestamp
        self.registry.update_last_used(device_id)

        logger.debug(f"Verified request from device {device_id}")
        return device


# Global registry instance (initialized lazily)
_device_registry: Optional[DeviceRegistry] = None
_signature_verifier: Optional[SignatureVerifier] = None


def get_device_registry() -> DeviceRegistry:
    """Get the global device registry instance."""
    global _device_registry
    if _device_registry is None:
        _device_registry = DeviceRegistry()
    return _device_registry


def get_signature_verifier() -> SignatureVerifier:
    """Get the global signature verifier instance."""
    global _signature_verifier
    if _signature_verifier is None:
        _signature_verifier = SignatureVerifier(get_device_registry())
    return _signature_verifier


# Utility function for generating test credentials
def generate_test_device() -> Tuple[str, str, RequestSigner]:
    """
    Generate a test device with signing credentials.

    Returns:
        Tuple of (device_id, secret_key, RequestSigner)
    """
    registry = get_device_registry()
    device_id, secret_key = registry.register_device(
        device_name="Test Device",
        device_type="test"
    )
    signer = RequestSigner(device_id, secret_key)
    return device_id, secret_key, signer
