"""
Tests for PHI Field-Level Encryption (Issue #49)

Tests cover:
- Key generation and management
- Encryption/decryption operations
- Key rotation
- Dictionary field encryption
- Error handling
- API endpoints

HIPAA Compliance:
- §164.312(a)(2)(iv) - Encryption and Decryption
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from phi_encryption import (
    PHIEncryptionService, KeyManager, EncryptionKey, EncryptedValue,
    PHIFieldType, EncryptionError, DecryptionError, KeyNotFoundError,
    get_encryption_service, encrypt_patient_name, encrypt_ssn,
    encrypt_mrn, encrypt_clinical_note, decrypt_phi
)


class TestEncryptionKey:
    """Tests for EncryptionKey dataclass."""

    def test_key_creation(self):
        """Should create key with all fields."""
        key = EncryptionKey(
            key_id="test_key_123",
            key_data="dGVzdGtleWRhdGE=",
            created_at="2024-01-15T10:00:00+00:00",
            expires_at="2024-04-15T10:00:00+00:00"
        )

        assert key.key_id == "test_key_123"
        assert key.is_active
        assert key.rotation_count == 0

    def test_is_expired_false(self):
        """Non-expired key should return False."""
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        key = EncryptionKey(
            key_id="test",
            key_data="data",
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=future
        )

        assert not key.is_expired()

    def test_is_expired_true(self):
        """Expired key should return True."""
        past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        key = EncryptionKey(
            key_id="test",
            key_data="data",
            created_at=past,
            expires_at=past
        )

        assert key.is_expired()

    def test_is_expired_no_expiry(self):
        """Key without expiry should not be expired."""
        key = EncryptionKey(
            key_id="test",
            key_data="data",
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=None
        )

        assert not key.is_expired()

    def test_to_dict(self):
        """Should convert to dictionary."""
        key = EncryptionKey(
            key_id="test_123",
            key_data="keydata",
            created_at="2024-01-15T10:00:00+00:00"
        )

        d = key.to_dict()
        assert d["key_id"] == "test_123"
        assert d["key_data"] == "keydata"
        assert d["is_active"] is True

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "key_id": "from_dict_key",
            "key_data": "datavalue",
            "created_at": "2024-01-15T10:00:00+00:00",
            "expires_at": None,
            "is_active": True,
            "rotation_count": 2,
            "algorithm": "Fernet-AES-128-CBC"
        }

        key = EncryptionKey.from_dict(data)
        assert key.key_id == "from_dict_key"
        assert key.rotation_count == 2


class TestEncryptedValue:
    """Tests for EncryptedValue dataclass."""

    def test_encrypted_value_creation(self):
        """Should create encrypted value container."""
        ev = EncryptedValue(
            ciphertext="base64ciphertext",
            key_id="key_123",
            field_type="patient_name",
            encrypted_at="2024-01-15T10:00:00+00:00"
        )

        assert ev.ciphertext == "base64ciphertext"
        assert ev.key_id == "key_123"
        assert ev.version == 1

    def test_to_storage_format(self):
        """Should convert to JSON storage format."""
        ev = EncryptedValue(
            ciphertext="cipher",
            key_id="key",
            field_type="ssn",
            encrypted_at="2024-01-15T10:00:00+00:00"
        )

        storage = ev.to_storage_format()
        assert isinstance(storage, str)

        parsed = json.loads(storage)
        assert parsed["ciphertext"] == "cipher"
        assert parsed["field_type"] == "ssn"

    def test_from_storage_format(self):
        """Should parse from JSON storage format."""
        storage = json.dumps({
            "ciphertext": "stored_cipher",
            "key_id": "stored_key",
            "field_type": "mrn",
            "encrypted_at": "2024-01-15T10:00:00+00:00",
            "version": 1
        })

        ev = EncryptedValue.from_storage_format(storage)
        assert ev.ciphertext == "stored_cipher"
        assert ev.field_type == "mrn"


class TestKeyManager:
    """Tests for KeyManager."""

    @pytest.fixture
    def key_manager(self, tmp_path):
        """Create key manager with temp storage."""
        return KeyManager(storage_path=str(tmp_path / "keys.json"))

    def test_generate_key(self, key_manager):
        """Should generate valid Fernet key."""
        key = key_manager.generate_key()

        assert key.key_id.startswith("phi_key_")
        assert len(key.key_data) > 20  # Fernet keys are base64 encoded
        assert key.is_active

    def test_get_active_key_creates_if_none(self, key_manager):
        """Should create key if none exists."""
        key = key_manager.get_active_key()

        assert key is not None
        assert key.is_active

    def test_get_active_key_returns_same(self, key_manager):
        """Should return same active key on multiple calls."""
        key1 = key_manager.get_active_key()
        key2 = key_manager.get_active_key()

        assert key1.key_id == key2.key_id

    def test_get_key_by_id(self, key_manager):
        """Should retrieve key by ID."""
        key = key_manager.generate_key()
        retrieved = key_manager.get_key(key.key_id)

        assert retrieved is not None
        assert retrieved.key_id == key.key_id

    def test_get_unknown_key_returns_none(self, key_manager):
        """Unknown key ID should return None."""
        assert key_manager.get_key("nonexistent") is None

    def test_rotate_key(self, key_manager):
        """Should rotate to new key."""
        old_key = key_manager.get_active_key()
        old_id = old_key.key_id

        _, new_key = key_manager.rotate_key()

        assert new_key.key_id != old_id
        assert new_key.is_active
        assert key_manager.get_active_key().key_id == new_key.key_id

    def test_old_key_deactivated_on_rotation(self, key_manager):
        """Old key should be deactivated after rotation."""
        old_key = key_manager.get_active_key()
        old_id = old_key.key_id

        key_manager.rotate_key()

        old = key_manager.get_key(old_id)
        assert not old.is_active

    def test_list_keys(self, key_manager):
        """Should list all keys metadata."""
        key_manager.generate_key()
        key_manager.generate_key()

        keys = key_manager.list_keys()
        assert len(keys) >= 2
        # Should not include key_data
        assert all("key_data" not in k for k in keys)

    def test_needs_rotation_new_key(self, key_manager):
        """New key should not need rotation."""
        key_manager.get_active_key()
        assert not key_manager.needs_rotation()

    def test_persistence(self, tmp_path):
        """Keys should persist to file."""
        storage_path = str(tmp_path / "persist_keys.json")

        # Create manager and generate key
        manager1 = KeyManager(storage_path=storage_path)
        key = manager1.get_active_key()
        key_id = key.key_id

        # Create new manager with same storage
        manager2 = KeyManager(storage_path=storage_path)
        loaded_key = manager2.get_key(key_id)

        assert loaded_key is not None
        assert loaded_key.key_id == key_id


class TestPHIEncryptionService:
    """Tests for PHIEncryptionService."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create service with temp storage."""
        km = KeyManager(storage_path=str(tmp_path / "keys.json"))
        return PHIEncryptionService(key_manager=km)

    def test_encrypt_phi(self, service):
        """Should encrypt PHI value."""
        encrypted = service.encrypt_phi("John Doe", PHIFieldType.PATIENT_NAME)

        assert isinstance(encrypted, EncryptedValue)
        assert encrypted.ciphertext != "John Doe"
        assert encrypted.field_type == "patient_name"

    def test_decrypt_phi(self, service):
        """Should decrypt PHI value."""
        original = "123-45-6789"
        encrypted = service.encrypt_phi(original, PHIFieldType.SSN)
        decrypted = service.decrypt_phi(encrypted)

        assert decrypted == original

    def test_encrypt_empty_raises(self, service):
        """Should raise on empty value."""
        with pytest.raises(ValueError):
            service.encrypt_phi("", PHIFieldType.GENERIC_PHI)

    def test_encrypt_string(self, service):
        """Should encrypt to storage-ready string."""
        encrypted = service.encrypt_string("test data", PHIFieldType.CLINICAL_NOTE)

        assert isinstance(encrypted, str)
        assert encrypted.startswith("{")  # JSON format

    def test_decrypt_string(self, service):
        """Should decrypt from storage format."""
        original = "Medical Record Number: MRN123456"
        encrypted = service.encrypt_string(original, PHIFieldType.MRN)
        decrypted = service.decrypt_string(encrypted)

        assert decrypted == original

    def test_encrypt_dict(self, service):
        """Should encrypt specific dict fields."""
        data = {
            "patient_name": "Jane Smith",
            "dob": "1990-05-15",
            "ssn": "987-65-4321",
            "notes": "Annual checkup"
        }

        result = service.encrypt_dict(
            data,
            ["patient_name", "ssn"],
            PHIFieldType.GENERIC_PHI
        )

        # Encrypted fields should be JSON strings
        assert result["patient_name"].startswith("{")
        assert result["ssn"].startswith("{")
        # Non-encrypted fields unchanged
        assert result["dob"] == "1990-05-15"
        assert result["notes"] == "Annual checkup"

    def test_decrypt_dict(self, service):
        """Should decrypt specific dict fields."""
        original = {"name": "Test Patient", "mrn": "MRN789"}
        encrypted = service.encrypt_dict(original, ["name", "mrn"], PHIFieldType.GENERIC_PHI)
        decrypted = service.decrypt_dict(encrypted, ["name", "mrn"])

        assert decrypted["name"] == "Test Patient"
        assert decrypted["mrn"] == "MRN789"

    def test_decrypt_dict_handles_non_encrypted(self, service):
        """Should handle non-encrypted fields gracefully."""
        data = {"plain": "not encrypted", "also_plain": 123}
        result = service.decrypt_dict(data, ["plain"])

        assert result["plain"] == "not encrypted"

    def test_re_encrypt_with_new_key(self, service):
        """Should re-encrypt with current key."""
        original = "Sensitive data"
        encrypted = service.encrypt_phi(original, PHIFieldType.SESSION_DATA)
        old_key_id = encrypted.key_id

        # Rotate key
        service.rotate_key()

        # Re-encrypt
        re_encrypted = service.re_encrypt_with_new_key(encrypted)

        assert re_encrypted.key_id != old_key_id
        assert service.decrypt_phi(re_encrypted) == original

    def test_rotate_key(self, service):
        """Should rotate encryption key."""
        result = service.rotate_key()

        assert result["success"] if "success" in result else "new_key_id" in result
        assert "new_key_id" in result

    def test_get_key_status(self, service):
        """Should return key status."""
        status = service.get_key_status()

        assert "active_key_id" in status
        assert "needs_rotation" in status
        assert "total_keys" in status

    def test_decrypt_with_old_key(self, service):
        """Should decrypt data encrypted with old key after rotation."""
        original = "Data encrypted with old key"
        encrypted = service.encrypt_phi(original, PHIFieldType.TRANSCRIPTION)

        # Rotate key multiple times
        service.rotate_key()
        service.rotate_key()

        # Should still decrypt
        decrypted = service.decrypt_phi(encrypted)
        assert decrypted == original


class TestUtilityFunctions:
    """Tests for convenience encryption functions."""

    @pytest.fixture(autouse=True)
    def setup_service(self, tmp_path):
        """Reset global service for each test."""
        import phi_encryption
        km = KeyManager(storage_path=str(tmp_path / "util_keys.json"))
        phi_encryption._encryption_service = PHIEncryptionService(key_manager=km)

    def test_encrypt_patient_name(self):
        """Should encrypt patient name."""
        encrypted = encrypt_patient_name("John Smith")
        assert encrypted.startswith("{")

    def test_encrypt_ssn(self):
        """Should encrypt SSN."""
        encrypted = encrypt_ssn("123-45-6789")
        assert encrypted.startswith("{")

    def test_encrypt_mrn(self):
        """Should encrypt MRN."""
        encrypted = encrypt_mrn("MRN12345")
        assert encrypted.startswith("{")

    def test_encrypt_clinical_note(self):
        """Should encrypt clinical note."""
        encrypted = encrypt_clinical_note("Patient presents with...")
        assert encrypted.startswith("{")

    def test_decrypt_phi_function(self):
        """Should decrypt any PHI."""
        original = "Test value"
        encrypted = encrypt_patient_name(original)
        decrypted = decrypt_phi(encrypted)
        assert decrypted == original


class TestPHIFieldType:
    """Tests for PHIFieldType enum."""

    def test_field_types_exist(self):
        """All expected field types should exist."""
        assert PHIFieldType.PATIENT_NAME.value == "patient_name"
        assert PHIFieldType.DATE_OF_BIRTH.value == "date_of_birth"
        assert PHIFieldType.SSN.value == "ssn"
        assert PHIFieldType.MRN.value == "mrn"
        assert PHIFieldType.SOAP_NOTE.value == "soap_note"
        assert PHIFieldType.TRANSCRIPTION.value == "transcription"
        assert PHIFieldType.CLINICAL_NOTE.value == "clinical_note"


class TestEncryptionEndpoints:
    """Integration tests for encryption API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_encryption_status(self, client):
        """GET /api/v1/encryption/status should return status."""
        response = client.get("/api/v1/encryption/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["encryption_enabled"] is True
        assert "algorithm" in data
        assert "compliance" in data

    def test_list_encryption_keys(self, client):
        """GET /api/v1/encryption/keys should list keys."""
        response = client.get("/api/v1/encryption/keys")

        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert "total" in data
        assert "rotation_policy" in data

    def test_rotate_key_endpoint(self, client):
        """POST /api/v1/encryption/rotate should rotate key."""
        response = client.post("/api/v1/encryption/rotate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "new_key_id" in data

    def test_encrypt_endpoint(self, client):
        """POST /api/v1/encryption/encrypt should encrypt value."""
        response = client.post(
            "/api/v1/encryption/encrypt",
            json={"plaintext": "Test PHI data", "field_type": "patient_name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "encrypted" in data

    def test_encrypt_invalid_field_type(self, client):
        """Invalid field type should return 400."""
        response = client.post(
            "/api/v1/encryption/encrypt",
            json={"plaintext": "data", "field_type": "invalid_type"}
        )

        assert response.status_code == 400
        data = response.json()
        # Check for error message in either 'detail' or 'error' field
        error_msg = data.get("detail") or data.get("error", "")
        assert "Invalid field_type" in error_msg or "invalid" in error_msg.lower()

    def test_decrypt_endpoint(self, client):
        """POST /api/v1/encryption/decrypt should decrypt value."""
        # First encrypt
        encrypt_response = client.post(
            "/api/v1/encryption/encrypt",
            json={"plaintext": "Decrypt me", "field_type": "generic_phi"}
        )
        encrypted = encrypt_response.json()["encrypted"]

        # Then decrypt
        response = client.post(
            "/api/v1/encryption/decrypt",
            json={"encrypted": encrypted}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["plaintext"] == "Decrypt me"

    def test_decrypt_invalid_data(self, client):
        """Invalid encrypted data should return 400 or 500."""
        response = client.post(
            "/api/v1/encryption/decrypt",
            json={"encrypted": "not valid encrypted data"}
        )

        assert response.status_code in [400, 500]

    def test_roundtrip_encryption(self, client):
        """Full encrypt-decrypt cycle should preserve data."""
        original = "Patient SSN: 123-45-6789"

        # Encrypt
        enc_response = client.post(
            "/api/v1/encryption/encrypt",
            json={"plaintext": original, "field_type": "ssn"}
        )
        encrypted = enc_response.json()["encrypted"]

        # Decrypt
        dec_response = client.post(
            "/api/v1/encryption/decrypt",
            json={"encrypted": encrypted}
        )

        assert dec_response.json()["plaintext"] == original


class TestEncryptionSecurity:
    """Security-focused tests."""

    @pytest.fixture
    def service(self, tmp_path):
        km = KeyManager(storage_path=str(tmp_path / "sec_keys.json"))
        return PHIEncryptionService(key_manager=km)

    def test_same_plaintext_different_ciphertext(self, service):
        """Same plaintext should produce different ciphertext (due to IV)."""
        plaintext = "Repeated data"

        enc1 = service.encrypt_phi(plaintext, PHIFieldType.GENERIC_PHI)
        enc2 = service.encrypt_phi(plaintext, PHIFieldType.GENERIC_PHI)

        # Fernet uses random IV, so ciphertext should differ
        assert enc1.ciphertext != enc2.ciphertext

        # But both should decrypt to same value
        assert service.decrypt_phi(enc1) == plaintext
        assert service.decrypt_phi(enc2) == plaintext

    def test_key_file_permissions(self, tmp_path):
        """Key storage file should have restricted permissions."""
        storage_path = str(tmp_path / "perm_keys.json")
        km = KeyManager(storage_path=storage_path)
        km.get_active_key()  # This saves the file

        import stat
        mode = os.stat(storage_path).st_mode
        # Check owner-only read/write (0o600)
        assert mode & 0o777 == 0o600

    def test_decryption_with_wrong_key_fails(self, tmp_path):
        """Should not decrypt with different key."""
        # Create two separate services with different keys
        service1 = PHIEncryptionService(
            key_manager=KeyManager(storage_path=str(tmp_path / "keys1.json"))
        )
        service2 = PHIEncryptionService(
            key_manager=KeyManager(storage_path=str(tmp_path / "keys2.json"))
        )

        encrypted = service1.encrypt_phi("Secret", PHIFieldType.GENERIC_PHI)

        # Service2 doesn't have service1's key
        with pytest.raises(DecryptionError):
            service2.decrypt_phi(encrypted)

    def test_tampered_ciphertext_fails(self, service):
        """Tampered ciphertext should fail decryption."""
        encrypted = service.encrypt_phi("Original", PHIFieldType.GENERIC_PHI)

        # Tamper with ciphertext
        import base64
        cipher_bytes = base64.b64decode(encrypted.ciphertext)
        tampered = base64.b64encode(cipher_bytes[:-1] + b'X').decode()
        encrypted.ciphertext = tampered

        with pytest.raises(DecryptionError):
            service.decrypt_phi(encrypted)


class TestEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def service(self, tmp_path):
        km = KeyManager(storage_path=str(tmp_path / "edge_keys.json"))
        return PHIEncryptionService(key_manager=km)

    def test_encrypt_unicode(self, service):
        """Should handle Unicode characters."""
        text = "Patiënt José García 中文 🏥"
        encrypted = service.encrypt_phi(text, PHIFieldType.PATIENT_NAME)
        decrypted = service.decrypt_phi(encrypted)

        assert decrypted == text

    def test_encrypt_long_text(self, service):
        """Should handle long clinical notes."""
        long_text = "A" * 10000  # 10KB of text
        encrypted = service.encrypt_phi(long_text, PHIFieldType.CLINICAL_NOTE)
        decrypted = service.decrypt_phi(encrypted)

        assert decrypted == long_text

    def test_encrypt_special_chars(self, service):
        """Should handle special characters."""
        text = "Tab:\tNewline:\nQuote:\"Backslash:\\"
        encrypted = service.encrypt_phi(text, PHIFieldType.TRANSCRIPTION)
        decrypted = service.decrypt_phi(encrypted)

        assert decrypted == text

    def test_encrypt_dict_missing_field(self, service):
        """Should handle missing fields gracefully."""
        data = {"present": "value"}
        result = service.encrypt_dict(data, ["present", "missing"], PHIFieldType.GENERIC_PHI)

        assert "present" in result
        assert "missing" not in result

    def test_encrypt_dict_non_string_field(self, service):
        """Should skip non-string fields."""
        data = {"name": "John", "age": 42, "active": True}
        result = service.encrypt_dict(data, ["name", "age"], PHIFieldType.GENERIC_PHI)

        # String field encrypted
        assert result["name"].startswith("{")
        # Non-string field unchanged
        assert result["age"] == 42
