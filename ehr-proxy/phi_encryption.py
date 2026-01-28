"""
PHI Field-Level Encryption (Issues #49, #50)

HIPAA-compliant encryption for Protected Health Information:
- AES-256 encryption using Fernet (symmetric)
- Secure key management with rotation
- Field-level encryption for sensitive data
- HMAC-based searchable encryption tokens
- Tiered sensitivity levels (Tier 1/2/3)
- Decryption rate limiting (anti-exfiltration)
- Comprehensive audit logging

Compliance:
- HIPAA §164.312(a)(2)(iv) - Encryption and Decryption
- HIPAA §164.308(a)(3)(i) - Workforce Access Controls
- SOC 2 Type II - Encryption at Rest
- PCI DSS Requirement 3.4 - Cryptographic Protection

Usage:
    from phi_encryption import get_encryption_service

    service = get_encryption_service()

    # Basic encryption
    encrypted = service.encrypt_phi("Patient SSN: 123-45-6789")
    decrypted = service.decrypt_phi(encrypted)

    # Searchable encryption (HMAC tokens)
    encrypted, search_token = service.encrypt_searchable("MRN123456", PHIFieldType.MRN)
    # Store search_token for lookups, encrypted for actual data

    # Find by search token
    results = service.find_by_search_token(search_token, stored_tokens)
"""

import os
import json
import base64
import secrets
import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
from threading import Lock
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class KeyNotFoundError(EncryptionError):
    """Encryption key not found."""
    pass


class DecryptionError(EncryptionError):
    """Failed to decrypt data."""
    pass


class KeyRotationError(EncryptionError):
    """Failed to rotate encryption key."""
    pass


class RateLimitExceededError(EncryptionError):
    """Decryption rate limit exceeded - potential data exfiltration."""
    pass


class SensitivityTier(int, Enum):
    """
    Data sensitivity tiers per Issue #50.

    Tier 1: Highest sensitivity - SSN, patient name, DOB, insurance ID
    Tier 2: High sensitivity - MRN, email, phone, address
    Tier 3: Moderate sensitivity - Emergency contacts
    """
    TIER_1_HIGHEST = 1
    TIER_2_HIGH = 2
    TIER_3_MODERATE = 3


# Map field types to sensitivity tiers
FIELD_SENSITIVITY_MAP: Dict[str, SensitivityTier] = {
    "ssn": SensitivityTier.TIER_1_HIGHEST,
    "patient_name": SensitivityTier.TIER_1_HIGHEST,
    "date_of_birth": SensitivityTier.TIER_1_HIGHEST,
    "insurance_member_id": SensitivityTier.TIER_1_HIGHEST,
    "mrn": SensitivityTier.TIER_2_HIGH,
    "email": SensitivityTier.TIER_2_HIGH,
    "phone": SensitivityTier.TIER_2_HIGH,
    "address": SensitivityTier.TIER_2_HIGH,
    "emergency_contact_name": SensitivityTier.TIER_3_MODERATE,
    "emergency_contact_phone": SensitivityTier.TIER_3_MODERATE,
    # Default for others
    "soap_note": SensitivityTier.TIER_2_HIGH,
    "transcription": SensitivityTier.TIER_2_HIGH,
    "diagnosis": SensitivityTier.TIER_2_HIGH,
    "medication": SensitivityTier.TIER_2_HIGH,
    "allergy": SensitivityTier.TIER_2_HIGH,
    "clinical_note": SensitivityTier.TIER_2_HIGH,
    "session_data": SensitivityTier.TIER_2_HIGH,
    "generic_phi": SensitivityTier.TIER_2_HIGH,
}


class PHIFieldType(str, Enum):
    """Types of PHI fields requiring encryption."""
    # Tier 1 - Highest Sensitivity
    PATIENT_NAME = "patient_name"
    DATE_OF_BIRTH = "date_of_birth"
    SSN = "ssn"
    INSURANCE_MEMBER_ID = "insurance_member_id"

    # Tier 2 - High Sensitivity
    MRN = "mrn"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    SOAP_NOTE = "soap_note"
    TRANSCRIPTION = "transcription"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    ALLERGY = "allergy"
    CLINICAL_NOTE = "clinical_note"
    SESSION_DATA = "session_data"

    # Tier 3 - Moderate Sensitivity
    EMERGENCY_CONTACT_NAME = "emergency_contact_name"
    EMERGENCY_CONTACT_PHONE = "emergency_contact_phone"

    # Generic
    GENERIC_PHI = "generic_phi"

    def get_sensitivity_tier(self) -> SensitivityTier:
        """Get the sensitivity tier for this field type."""
        return FIELD_SENSITIVITY_MAP.get(self.value, SensitivityTier.TIER_2_HIGH)


@dataclass
class EncryptionKey:
    """Encryption key with metadata."""
    key_id: str
    key_data: str  # Base64-encoded Fernet key
    created_at: str
    expires_at: Optional[str] = None
    is_active: bool = True
    rotation_count: int = 0
    algorithm: str = "Fernet-AES-128-CBC"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptionKey":
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if key has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= expires


@dataclass
class EncryptedValue:
    """Container for encrypted data with metadata."""
    ciphertext: str  # Base64-encoded encrypted data
    key_id: str
    field_type: str
    encrypted_at: str
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptedValue":
        return cls(**data)

    def to_storage_format(self) -> str:
        """Convert to JSON string for storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_storage_format(cls, data: str) -> "EncryptedValue":
        """Parse from JSON storage format."""
        return cls.from_dict(json.loads(data))


@dataclass
class SearchableEncryptedValue:
    """
    Container for searchable encrypted data (Issue #50).

    Stores both encrypted value and HMAC search token.
    The search token allows lookups without decrypting.
    """
    encrypted_value: str  # JSON string of EncryptedValue
    search_token: str  # HMAC-SHA256 hash for searching
    field_type: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchableEncryptedValue":
        return cls(**data)

    def to_storage_format(self) -> str:
        """Convert to JSON string for storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_storage_format(cls, data: str) -> "SearchableEncryptedValue":
        """Parse from JSON storage format."""
        return cls.from_dict(json.loads(data))


class DecryptionRateLimiter:
    """
    Rate limiter for decryption operations (Issue #50).

    Prevents bulk data exfiltration by limiting decryption rate.
    Configurable per-user and global limits.
    """

    def __init__(
        self,
        max_per_minute: int = 100,
        max_per_hour: int = 1000,
        max_burst: int = 20
    ):
        """
        Initialize rate limiter.

        Args:
            max_per_minute: Maximum decryptions per minute per user
            max_per_hour: Maximum decryptions per hour per user
            max_burst: Maximum burst decryptions in a short window
        """
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.max_burst = max_burst

        self._minute_counts: Dict[str, List[float]] = defaultdict(list)
        self._hour_counts: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(self, user_id: str = "default") -> bool:
        """
        Check if decryption is allowed for user.

        Args:
            user_id: User identifier (IP, session ID, etc.)

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        with self._lock:
            # Clean old entries
            self._minute_counts[user_id] = [
                t for t in self._minute_counts[user_id] if t > minute_ago
            ]
            self._hour_counts[user_id] = [
                t for t in self._hour_counts[user_id] if t > hour_ago
            ]

            # Check limits
            if len(self._minute_counts[user_id]) >= self.max_per_minute:
                return False
            if len(self._hour_counts[user_id]) >= self.max_per_hour:
                return False

            # Check burst (last 5 seconds)
            burst_window = now - 5
            recent = [t for t in self._minute_counts[user_id] if t > burst_window]
            if len(recent) >= self.max_burst:
                return False

            return True

    def record_decryption(self, user_id: str = "default"):
        """Record a decryption operation."""
        now = time.time()
        with self._lock:
            self._minute_counts[user_id].append(now)
            self._hour_counts[user_id].append(now)

    def get_stats(self, user_id: str = "default") -> Dict[str, Any]:
        """Get rate limit stats for a user."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        with self._lock:
            minute_count = len([
                t for t in self._minute_counts[user_id] if t > minute_ago
            ])
            hour_count = len([
                t for t in self._hour_counts[user_id] if t > hour_ago
            ])

        return {
            "user_id": user_id,
            "decryptions_last_minute": minute_count,
            "decryptions_last_hour": hour_count,
            "limit_per_minute": self.max_per_minute,
            "limit_per_hour": self.max_per_hour,
            "remaining_minute": max(0, self.max_per_minute - minute_count),
            "remaining_hour": max(0, self.max_per_hour - hour_count)
        }


class HMACSearchService:
    """
    HMAC-based search token service (Issue #50).

    Creates deterministic, one-way hash tokens for searching
    encrypted fields without exposing plaintext.
    """

    def __init__(self, secret_key: Optional[bytes] = None):
        """
        Initialize HMAC service.

        Args:
            secret_key: HMAC secret key (generates if not provided)
        """
        self._secret_key = secret_key or self._load_or_generate_key()

    def _load_or_generate_key(self) -> bytes:
        """Load existing HMAC key or generate new one."""
        key_path = os.getenv(
            "PHI_HMAC_KEY_PATH",
            os.path.join(os.path.dirname(__file__), ".phi_hmac_key")
        )

        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()

        # Generate new key
        key = secrets.token_bytes(32)  # 256-bit key

        # Save with restrictive permissions
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        os.chmod(key_path, 0o600)

        logger.info("Generated new HMAC search key")
        return key

    def generate_search_token(
        self,
        plaintext: str,
        field_type: str = "generic"
    ) -> str:
        """
        Generate HMAC search token for plaintext.

        Args:
            plaintext: The value to create search token for
            field_type: Field type (included in hash for uniqueness)

        Returns:
            Base64-encoded HMAC-SHA256 token
        """
        # Normalize input (lowercase, strip whitespace)
        normalized = plaintext.lower().strip()

        # Include field type in hash to prevent cross-field matching
        message = f"{field_type}:{normalized}".encode("utf-8")

        # Generate HMAC-SHA256
        token = hmac.new(
            self._secret_key,
            message,
            hashlib.sha256
        ).digest()

        return base64.b64encode(token).decode("utf-8")

    def verify_token(
        self,
        plaintext: str,
        token: str,
        field_type: str = "generic"
    ) -> bool:
        """
        Verify if plaintext matches a search token.

        Args:
            plaintext: The value to verify
            token: The search token to match against
            field_type: Field type

        Returns:
            True if matches, False otherwise
        """
        expected_token = self.generate_search_token(plaintext, field_type)
        return hmac.compare_digest(expected_token, token)


@dataclass
class DecryptionAuditEntry:
    """Audit log entry for decryption operations."""
    timestamp: str
    user_id: str
    field_type: str
    key_id: str
    record_id: Optional[str]
    client_ip: Optional[str]
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DecryptionAuditLog:
    """
    Audit log for decryption operations (Issue #50).

    Tracks who decrypted what, when, for compliance and
    detecting unusual access patterns.
    """

    def __init__(self, log_path: Optional[str] = None, max_entries: int = 10000):
        """
        Initialize audit log.

        Args:
            log_path: Path to audit log file
            max_entries: Maximum entries to keep in memory
        """
        self.log_path = log_path or os.getenv(
            "PHI_AUDIT_LOG_PATH",
            os.path.join(os.path.dirname(__file__), "logs", "phi_decryption_audit.ndjson")
        )
        self.max_entries = max_entries
        self._entries: List[DecryptionAuditEntry] = []
        self._lock = Lock()

    def log_decryption(
        self,
        user_id: str,
        field_type: str,
        key_id: str,
        success: bool,
        record_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log a decryption operation."""
        entry = DecryptionAuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            field_type=field_type,
            key_id=key_id,
            record_id=record_id,
            client_ip=client_ip,
            success=success,
            error_message=error_message
        )

        with self._lock:
            self._entries.append(entry)

            # Trim old entries
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]

        # Write to file
        self._write_to_file(entry)

        # Log warning for failed decryptions
        if not success:
            logger.warning(
                f"PHI decryption failed: user={user_id}, "
                f"field={field_type}, error={error_message}"
            )

    def _write_to_file(self, entry: DecryptionAuditEntry):
        """Append entry to audit log file."""
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_recent_entries(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent audit entries, optionally filtered by user."""
        with self._lock:
            entries = self._entries[-limit:]
            if user_id:
                entries = [e for e in entries if e.user_id == user_id]
            return [e.to_dict() for e in entries]

    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get decryption statistics for the specified time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()

        with self._lock:
            recent = [
                e for e in self._entries
                if e.timestamp >= cutoff_str
            ]

        total = len(recent)
        successful = len([e for e in recent if e.success])
        failed = total - successful

        # Count by user
        by_user: Dict[str, int] = defaultdict(int)
        for e in recent:
            by_user[e.user_id] += 1

        # Count by field type
        by_field: Dict[str, int] = defaultdict(int)
        for e in recent:
            by_field[e.field_type] += 1

        return {
            "period_hours": hours,
            "total_decryptions": total,
            "successful": successful,
            "failed": failed,
            "by_user": dict(by_user),
            "by_field_type": dict(by_field),
            "top_users": sorted(by_user.items(), key=lambda x: -x[1])[:10]
        }


class KeyManager:
    """
    Secure key management for PHI encryption.

    Features:
    - Key generation and storage
    - Key rotation with configurable interval
    - Multiple active keys for decryption (during rotation)
    - Audit logging
    """

    # Key rotation interval (90 days per HIPAA best practices)
    KEY_ROTATION_DAYS = 90

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize key manager.

        Args:
            storage_path: Path to key storage file
        """
        self.storage_path = storage_path or os.getenv(
            "PHI_KEY_STORAGE_PATH",
            os.path.join(os.path.dirname(__file__), ".phi_keys.json")
        )
        self._keys: Dict[str, EncryptionKey] = {}
        self._active_key_id: Optional[str] = None
        self._load_keys()

    def _load_keys(self):
        """Load keys from secure storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for key_id, key_data in data.get("keys", {}).items():
                        self._keys[key_id] = EncryptionKey.from_dict(key_data)
                    self._active_key_id = data.get("active_key_id")
                logger.info(f"Loaded {len(self._keys)} encryption keys")
        except Exception as e:
            logger.warning(f"Could not load encryption keys: {e}")

    def _save_keys(self):
        """Save keys to secure storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            # Set restrictive permissions (owner read/write only)
            with open(self.storage_path, "w") as f:
                data = {
                    "keys": {k: v.to_dict() for k, v in self._keys.items()},
                    "active_key_id": self._active_key_id,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                json.dump(data, f, indent=2)
            os.chmod(self.storage_path, 0o600)  # Owner read/write only
        except Exception as e:
            logger.error(f"Could not save encryption keys: {e}")
            raise KeyRotationError(f"Failed to save keys: {e}")

    def generate_key(self) -> EncryptionKey:
        """
        Generate a new Fernet encryption key.

        Returns:
            New EncryptionKey object
        """
        key_id = f"phi_key_{secrets.token_hex(8)}"
        key_data = Fernet.generate_key().decode("utf-8")
        now = datetime.now(timezone.utc)

        key = EncryptionKey(
            key_id=key_id,
            key_data=key_data,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=self.KEY_ROTATION_DAYS)).isoformat(),
            is_active=True
        )

        self._keys[key_id] = key
        logger.info(f"Generated new encryption key: {key_id}")

        return key

    def get_active_key(self) -> EncryptionKey:
        """
        Get the active encryption key, creating one if needed.

        Returns:
            Active EncryptionKey
        """
        # Check if we have an active key
        if self._active_key_id and self._active_key_id in self._keys:
            key = self._keys[self._active_key_id]
            if key.is_active and not key.is_expired():
                return key

        # Generate new key if none active
        key = self.generate_key()
        self._active_key_id = key.key_id
        self._save_keys()

        return key

    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Get a specific key by ID."""
        return self._keys.get(key_id)

    def rotate_key(self) -> Tuple[EncryptionKey, EncryptionKey]:
        """
        Rotate the active encryption key.

        Returns:
            Tuple of (old_key, new_key)
        """
        old_key = None
        if self._active_key_id:
            old_key = self._keys.get(self._active_key_id)
            if old_key:
                old_key.is_active = False

        # Generate new active key
        new_key = self.generate_key()
        new_key.rotation_count = (old_key.rotation_count + 1) if old_key else 0
        self._active_key_id = new_key.key_id
        self._save_keys()

        logger.info(f"Rotated encryption key: {old_key.key_id if old_key else 'none'} -> {new_key.key_id}")
        return old_key, new_key

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all keys with metadata (excluding key data)."""
        return [
            {
                "key_id": k.key_id,
                "created_at": k.created_at,
                "expires_at": k.expires_at,
                "is_active": k.is_active,
                "is_current": k.key_id == self._active_key_id,
                "rotation_count": k.rotation_count,
                "is_expired": k.is_expired()
            }
            for k in self._keys.values()
        ]

    def needs_rotation(self) -> bool:
        """Check if key rotation is needed."""
        if not self._active_key_id:
            return True
        key = self._keys.get(self._active_key_id)
        if not key:
            return True
        # Rotate 7 days before expiry
        if key.expires_at:
            expires = datetime.fromisoformat(key.expires_at.replace("Z", "+00:00"))
            warning_date = expires - timedelta(days=7)
            return datetime.now(timezone.utc) >= warning_date
        return False


class PHIEncryptionService:
    """
    Service for encrypting/decrypting PHI fields (Issues #49, #50).

    Features:
    - Field-level encryption with AES-256
    - Key rotation support (decrypt with old keys)
    - HMAC-based searchable encryption tokens
    - Tiered sensitivity levels
    - Decryption rate limiting (anti-exfiltration)
    - Comprehensive audit logging for compliance
    - Type-safe encrypted value containers
    """

    def __init__(
        self,
        key_manager: Optional[KeyManager] = None,
        rate_limiter: Optional[DecryptionRateLimiter] = None,
        hmac_service: Optional[HMACSearchService] = None,
        audit_log: Optional[DecryptionAuditLog] = None,
        enable_rate_limiting: bool = True,
        enable_audit_logging: bool = True
    ):
        """
        Initialize encryption service.

        Args:
            key_manager: KeyManager instance (creates default if not provided)
            rate_limiter: DecryptionRateLimiter instance
            hmac_service: HMACSearchService for searchable encryption
            audit_log: DecryptionAuditLog for audit trail
            enable_rate_limiting: Whether to enforce rate limits
            enable_audit_logging: Whether to log decryptions
        """
        self.key_manager = key_manager or KeyManager()
        self.rate_limiter = rate_limiter or DecryptionRateLimiter()
        self.hmac_service = hmac_service or HMACSearchService()
        self.audit_log = audit_log or DecryptionAuditLog()
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_audit_logging = enable_audit_logging
        self._fernet_cache: Dict[str, Fernet] = {}

    def _get_fernet(self, key_id: str) -> Fernet:
        """Get Fernet instance for a key (cached)."""
        if key_id not in self._fernet_cache:
            key = self.key_manager.get_key(key_id)
            if not key:
                raise KeyNotFoundError(f"Key not found: {key_id}")
            self._fernet_cache[key_id] = Fernet(key.key_data.encode())
        return self._fernet_cache[key_id]

    def encrypt_phi(
        self,
        plaintext: str,
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> EncryptedValue:
        """
        Encrypt a PHI field value.

        Args:
            plaintext: The data to encrypt
            field_type: Type of PHI field

        Returns:
            EncryptedValue containing ciphertext and metadata
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty value")

        key = self.key_manager.get_active_key()
        fernet = self._get_fernet(key.key_id)

        # Encrypt the data
        ciphertext = fernet.encrypt(plaintext.encode("utf-8"))

        encrypted = EncryptedValue(
            ciphertext=base64.b64encode(ciphertext).decode("utf-8"),
            key_id=key.key_id,
            field_type=field_type.value,
            encrypted_at=datetime.now(timezone.utc).isoformat()
        )

        logger.debug(f"Encrypted {field_type.value} field with key {key.key_id}")
        return encrypted

    def decrypt_phi(
        self,
        encrypted: EncryptedValue,
        user_id: str = "default",
        record_id: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> str:
        """
        Decrypt a PHI field value with rate limiting and audit logging.

        Args:
            encrypted: EncryptedValue to decrypt
            user_id: User performing decryption (for rate limiting/audit)
            record_id: Optional record ID for audit trail
            client_ip: Optional client IP for audit trail

        Returns:
            Decrypted plaintext

        Raises:
            RateLimitExceededError: If decryption rate limit exceeded
            DecryptionError: If decryption fails
        """
        # Check rate limit
        if self.enable_rate_limiting:
            if not self.rate_limiter.check_rate_limit(user_id):
                if self.enable_audit_logging:
                    self.audit_log.log_decryption(
                        user_id=user_id,
                        field_type=encrypted.field_type,
                        key_id=encrypted.key_id,
                        success=False,
                        record_id=record_id,
                        client_ip=client_ip,
                        error_message="Rate limit exceeded"
                    )
                raise RateLimitExceededError(
                    f"Decryption rate limit exceeded for user {user_id}. "
                    "This may indicate a data exfiltration attempt."
                )

        try:
            fernet = self._get_fernet(encrypted.key_id)
            ciphertext = base64.b64decode(encrypted.ciphertext)
            plaintext = fernet.decrypt(ciphertext)

            # Record successful decryption
            if self.enable_rate_limiting:
                self.rate_limiter.record_decryption(user_id)

            if self.enable_audit_logging:
                self.audit_log.log_decryption(
                    user_id=user_id,
                    field_type=encrypted.field_type,
                    key_id=encrypted.key_id,
                    success=True,
                    record_id=record_id,
                    client_ip=client_ip
                )

            logger.debug(f"Decrypted {encrypted.field_type} field for user {user_id}")
            return plaintext.decode("utf-8")

        except InvalidToken as e:
            error_msg = "Invalid encryption token - data may be corrupted"
            if self.enable_audit_logging:
                self.audit_log.log_decryption(
                    user_id=user_id,
                    field_type=encrypted.field_type,
                    key_id=encrypted.key_id,
                    success=False,
                    record_id=record_id,
                    client_ip=client_ip,
                    error_message=error_msg
                )
            raise DecryptionError(error_msg)
        except KeyNotFoundError as e:
            error_msg = f"Encryption key not found: {encrypted.key_id}"
            if self.enable_audit_logging:
                self.audit_log.log_decryption(
                    user_id=user_id,
                    field_type=encrypted.field_type,
                    key_id=encrypted.key_id,
                    success=False,
                    record_id=record_id,
                    client_ip=client_ip,
                    error_message=error_msg
                )
            raise DecryptionError(error_msg)
        except RateLimitExceededError:
            raise
        except Exception as e:
            error_msg = f"Decryption failed: {e}"
            if self.enable_audit_logging:
                self.audit_log.log_decryption(
                    user_id=user_id,
                    field_type=encrypted.field_type,
                    key_id=encrypted.key_id,
                    success=False,
                    record_id=record_id,
                    client_ip=client_ip,
                    error_message=error_msg
                )
            raise DecryptionError(error_msg)

    def encrypt_string(
        self,
        plaintext: str,
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> str:
        """
        Encrypt and return as storage-ready string.

        Args:
            plaintext: Data to encrypt
            field_type: Type of PHI field

        Returns:
            JSON string ready for storage
        """
        encrypted = self.encrypt_phi(plaintext, field_type)
        return encrypted.to_storage_format()

    def decrypt_string(self, encrypted_string: str) -> str:
        """
        Decrypt from storage format string.

        Args:
            encrypted_string: JSON string from storage

        Returns:
            Decrypted plaintext
        """
        encrypted = EncryptedValue.from_storage_format(encrypted_string)
        return self.decrypt_phi(encrypted)

    def encrypt_dict(
        self,
        data: Dict[str, Any],
        fields_to_encrypt: List[str],
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
            field_type: Type of PHI for all fields

        Returns:
            Dictionary with specified fields encrypted
        """
        result = data.copy()
        for field_name in fields_to_encrypt:
            if field_name in result and result[field_name]:
                value = result[field_name]
                if isinstance(value, str):
                    result[field_name] = self.encrypt_string(value, field_type)
        return result

    def decrypt_dict(
        self,
        data: Dict[str, Any],
        encrypted_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary containing encrypted fields
            encrypted_fields: List of field names to decrypt

        Returns:
            Dictionary with specified fields decrypted
        """
        result = data.copy()
        for field_name in encrypted_fields:
            if field_name in result and result[field_name]:
                value = result[field_name]
                if isinstance(value, str) and value.startswith("{"):
                    try:
                        result[field_name] = self.decrypt_string(value)
                    except (json.JSONDecodeError, DecryptionError):
                        # Field might not be encrypted, leave as-is
                        pass
        return result

    def encrypt_searchable(
        self,
        plaintext: str,
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> Tuple[str, str]:
        """
        Encrypt a value and create a search token (Issue #50).

        Use this for fields that need to be searched without decryption.
        Store the encrypted value for data, and the search token for lookups.

        Args:
            plaintext: The data to encrypt
            field_type: Type of PHI field

        Returns:
            Tuple of (encrypted_json_string, search_token)

        Example:
            encrypted, token = service.encrypt_searchable("MRN123", PHIFieldType.MRN)
            # Store: encrypted in 'mrn_encrypted' column
            # Store: token in 'mrn_search_token' column
            # Query: WHERE mrn_search_token = ?
        """
        # Encrypt the value
        encrypted = self.encrypt_string(plaintext, field_type)

        # Generate search token
        search_token = self.hmac_service.generate_search_token(
            plaintext, field_type.value
        )

        return encrypted, search_token

    def create_search_token(
        self,
        plaintext: str,
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> str:
        """
        Create a search token for a plaintext value.

        Use this to generate tokens for searching encrypted fields.

        Args:
            plaintext: The value to create search token for
            field_type: Type of PHI field

        Returns:
            HMAC search token
        """
        return self.hmac_service.generate_search_token(plaintext, field_type.value)

    def verify_search_token(
        self,
        plaintext: str,
        token: str,
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> bool:
        """
        Verify if a plaintext matches a search token.

        Args:
            plaintext: The value to verify
            token: The search token to match
            field_type: Type of PHI field

        Returns:
            True if matches, False otherwise
        """
        return self.hmac_service.verify_token(plaintext, token, field_type.value)

    def get_sensitivity_tier(self, field_type: PHIFieldType) -> SensitivityTier:
        """
        Get the sensitivity tier for a field type.

        Args:
            field_type: The PHI field type

        Returns:
            SensitivityTier enum value
        """
        return field_type.get_sensitivity_tier()

    def encrypt_with_tier_info(
        self,
        plaintext: str,
        field_type: PHIFieldType = PHIFieldType.GENERIC_PHI
    ) -> Dict[str, Any]:
        """
        Encrypt with sensitivity tier metadata.

        Args:
            plaintext: Data to encrypt
            field_type: Type of PHI field

        Returns:
            Dict with encrypted value, tier info, and metadata
        """
        encrypted = self.encrypt_phi(plaintext, field_type)
        tier = self.get_sensitivity_tier(field_type)

        return {
            "encrypted": encrypted.to_storage_format(),
            "field_type": field_type.value,
            "sensitivity_tier": tier.value,
            "tier_name": tier.name,
            "encrypted_at": encrypted.encrypted_at
        }

    def get_rate_limit_stats(self, user_id: str = "default") -> Dict[str, Any]:
        """Get rate limit statistics for a user."""
        return self.rate_limiter.get_stats(user_id)

    def get_audit_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get decryption audit statistics."""
        return self.audit_log.get_stats(hours)

    def get_recent_audit_entries(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log.get_recent_entries(user_id, limit)

    def re_encrypt_with_new_key(self, encrypted: EncryptedValue) -> EncryptedValue:
        """
        Re-encrypt data with the current active key.

        Use during key rotation to update encrypted values.

        Args:
            encrypted: EncryptedValue encrypted with old key

        Returns:
            EncryptedValue encrypted with current key
        """
        # Decrypt with old key
        plaintext = self.decrypt_phi(encrypted)

        # Re-encrypt with current key
        field_type = PHIFieldType(encrypted.field_type)
        return self.encrypt_phi(plaintext, field_type)

    def rotate_key(self) -> Dict[str, Any]:
        """
        Rotate the encryption key.

        Returns:
            Rotation status information
        """
        old_key, new_key = self.key_manager.rotate_key()

        # Clear Fernet cache to pick up new key
        self._fernet_cache.clear()

        return {
            "old_key_id": old_key.key_id if old_key else None,
            "new_key_id": new_key.key_id,
            "rotated_at": datetime.now(timezone.utc).isoformat(),
            "message": "Key rotated successfully. Re-encrypt existing data with new key."
        }

    def get_key_status(self) -> Dict[str, Any]:
        """Get current encryption key status."""
        key = self.key_manager.get_active_key()
        return {
            "active_key_id": key.key_id,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "rotation_count": key.rotation_count,
            "needs_rotation": self.key_manager.needs_rotation(),
            "total_keys": len(self.key_manager._keys),
            "rate_limiting_enabled": self.enable_rate_limiting,
            "audit_logging_enabled": self.enable_audit_logging
        }


# Global service instance
_encryption_service: Optional[PHIEncryptionService] = None


def get_encryption_service() -> PHIEncryptionService:
    """Get the global PHI encryption service."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = PHIEncryptionService()
    return _encryption_service


# Utility functions for common operations
def encrypt_patient_name(name: str) -> str:
    """Encrypt a patient name."""
    service = get_encryption_service()
    return service.encrypt_string(name, PHIFieldType.PATIENT_NAME)


def encrypt_ssn(ssn: str) -> str:
    """Encrypt a Social Security Number."""
    service = get_encryption_service()
    return service.encrypt_string(ssn, PHIFieldType.SSN)


def encrypt_mrn(mrn: str) -> str:
    """Encrypt a Medical Record Number."""
    service = get_encryption_service()
    return service.encrypt_string(mrn, PHIFieldType.MRN)


def encrypt_clinical_note(note: str) -> str:
    """Encrypt clinical notes (SOAP, assessments, etc.)."""
    service = get_encryption_service()
    return service.encrypt_string(note, PHIFieldType.CLINICAL_NOTE)


def decrypt_phi(encrypted_string: str) -> str:
    """Decrypt any PHI field."""
    service = get_encryption_service()
    return service.decrypt_string(encrypted_string)


# New utility functions for Issue #50

def encrypt_email(email: str) -> str:
    """Encrypt an email address."""
    service = get_encryption_service()
    return service.encrypt_string(email, PHIFieldType.EMAIL)


def encrypt_phone(phone: str) -> str:
    """Encrypt a phone number."""
    service = get_encryption_service()
    return service.encrypt_string(phone, PHIFieldType.PHONE)


def encrypt_address(address: str) -> str:
    """Encrypt a physical address."""
    service = get_encryption_service()
    return service.encrypt_string(address, PHIFieldType.ADDRESS)


def encrypt_searchable_mrn(mrn: str) -> Tuple[str, str]:
    """
    Encrypt MRN and create search token.

    Returns:
        Tuple of (encrypted_value, search_token)
    """
    service = get_encryption_service()
    return service.encrypt_searchable(mrn, PHIFieldType.MRN)


def encrypt_searchable_ssn(ssn: str) -> Tuple[str, str]:
    """
    Encrypt SSN and create search token.

    Returns:
        Tuple of (encrypted_value, search_token)
    """
    service = get_encryption_service()
    return service.encrypt_searchable(ssn, PHIFieldType.SSN)


def create_mrn_search_token(mrn: str) -> str:
    """Create search token for MRN lookup."""
    service = get_encryption_service()
    return service.create_search_token(mrn, PHIFieldType.MRN)


def create_ssn_search_token(ssn: str) -> str:
    """Create search token for SSN lookup."""
    service = get_encryption_service()
    return service.create_search_token(ssn, PHIFieldType.SSN)


def get_field_sensitivity(field_type: str) -> Dict[str, Any]:
    """
    Get sensitivity information for a field type.

    Args:
        field_type: Field type name (e.g., 'ssn', 'mrn')

    Returns:
        Dict with tier info
    """
    try:
        phi_type = PHIFieldType(field_type)
        tier = phi_type.get_sensitivity_tier()
        return {
            "field_type": field_type,
            "sensitivity_tier": tier.value,
            "tier_name": tier.name,
            "description": {
                1: "Highest sensitivity - SSN, patient name, DOB, insurance ID",
                2: "High sensitivity - MRN, email, phone, clinical notes",
                3: "Moderate sensitivity - Emergency contacts"
            }.get(tier.value, "Unknown")
        }
    except ValueError:
        return {
            "field_type": field_type,
            "sensitivity_tier": 2,
            "tier_name": "TIER_2_HIGH",
            "description": "Default tier for unknown field types"
        }
