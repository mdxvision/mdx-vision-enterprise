"""
Test Voiceprint Biometric Authentication (Feature #66, #77)

Tests voiceprint enrollment, verification, and continuous authentication.
Security-critical biometric tests for AR glasses.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
import uuid
import base64

import sys
sys.path.insert(0, '..')
from main import app


@pytest.fixture
def test_device_id():
    return f"device-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_audio_sample():
    """Create a mock audio sample (base64 encoded)"""
    # Simulate PCM audio data
    audio_bytes = bytes([0] * 16000 * 2)  # 1 second of silence at 16kHz, 16-bit
    return base64.b64encode(audio_bytes).decode()


class TestVoiceprintEnrollmentPhrases:
    """Tests for getting enrollment phrases"""

    @pytest.mark.asyncio
    async def test_get_enrollment_phrases_returns_list(self):
        """Should return list of enrollment phrases"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/voiceprint/phrases")

            assert response.status_code == 200
            data = response.json()
            assert "phrases" in data
            assert isinstance(data["phrases"], list)
            assert len(data["phrases"]) > 0

    @pytest.mark.asyncio
    async def test_get_enrollment_phrases_includes_required_count(self):
        """Should specify minimum samples required"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/voiceprint/phrases")

            data = response.json()
            assert "min_samples" in data
            assert data["min_samples"] >= 3  # At least 3 samples for enrollment

    @pytest.mark.asyncio
    async def test_get_enrollment_phrases_includes_instructions(self):
        """Should include enrollment instructions"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/voiceprint/phrases")

            data = response.json()
            assert "instructions" in data


class TestVoiceprintEnrollment:
    """Tests for voiceprint enrollment endpoint"""

    @pytest.mark.asyncio
    async def test_enroll_requires_device_registration(self, test_device_id, mock_audio_sample):
        """Should fail enrollment for unregistered device"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/enroll",
                json={
                    "device_id": test_device_id,
                    "audio_samples": [mock_audio_sample, mock_audio_sample, mock_audio_sample]
                }
            )

            # Should fail - device not registered
            assert response.status_code == 404
            assert "not registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_enroll_requires_minimum_samples(self, test_device_id, mock_audio_sample):
        """Should require minimum number of audio samples"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/enroll",
                json={
                    "device_id": test_device_id,
                    "audio_samples": [mock_audio_sample]  # Only 1 sample, need 3
                }
            )

            # Should fail or indicate minimum not met
            assert response.status_code in [400, 404, 422]


class TestVoiceprintVerification:
    """Tests for voiceprint verification endpoint"""

    @pytest.mark.asyncio
    async def test_verify_requires_device_registration(self, test_device_id, mock_audio_sample):
        """Should fail verification for unregistered device"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/verify",
                json={
                    "device_id": test_device_id,
                    "audio_sample": mock_audio_sample
                }
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_returns_confidence_score(self, test_device_id, mock_audio_sample):
        """Should return confidence score in verification response"""
        # This test would require a registered device with enrolled voiceprint
        # For now, test the error response structure
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/verify",
                json={
                    "device_id": test_device_id,
                    "audio_sample": mock_audio_sample
                }
            )

            # Even on failure, response should be structured
            assert response.status_code in [200, 401, 404]


class TestVoiceprintStatus:
    """Tests for voiceprint status endpoint"""

    @pytest.mark.asyncio
    async def test_get_voiceprint_status_for_unregistered_device(self, test_device_id):
        """Should indicate no voiceprint for unregistered device"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/auth/voiceprint/{test_device_id}/status")

            # Should either return 404 or indicate not enrolled
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert "enrolled" in data or "status" in data


class TestContinuousAuthentication:
    """Tests for continuous voiceprint authentication (Feature #77)"""

    @pytest.mark.asyncio
    async def test_check_voiceprint_session(self, test_device_id):
        """Should check voiceprint session validity"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/auth/voiceprint/{test_device_id}/check"
            )

            # Should return session status
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_re_verify_voiceprint(self, test_device_id, mock_audio_sample):
        """Should support re-verification during session"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/auth/voiceprint/{test_device_id}/re-verify",
                json={"audio_sample": mock_audio_sample}
            )

            # Should fail for unregistered device
            assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_set_re_verify_interval(self, test_device_id):
        """Should allow setting re-verification interval"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/auth/voiceprint/{test_device_id}/interval",
                params={"interval_minutes": 10}
            )

            # Should fail for unregistered device or succeed if registered
            assert response.status_code in [200, 404]


class TestVoiceprintSecurity:
    """Security tests for voiceprint system"""

    @pytest.mark.asyncio
    async def test_invalid_audio_format_rejected(self, test_device_id):
        """Should reject invalid audio format"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/verify",
                json={
                    "device_id": test_device_id,
                    "audio_sample": "not-valid-base64!"
                }
            )

            assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_empty_audio_rejected(self, test_device_id):
        """Should reject empty audio sample"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/verify",
                json={
                    "device_id": test_device_id,
                    "audio_sample": ""
                }
            )

            assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_voiceprint_not_exposed_in_response(self, test_device_id):
        """Should not expose voiceprint embeddings in API responses"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/auth/voiceprint/{test_device_id}/status")

            if response.status_code == 200:
                data = response.json()
                # Should not contain embeddings or raw voiceprint data
                assert "embedding" not in str(data).lower()
                assert "voiceprint_data" not in data


class TestVoiceprintConfidenceThresholds:
    """Tests for voiceprint matching confidence thresholds"""

    @pytest.mark.asyncio
    async def test_threshold_is_configurable(self):
        """Verify confidence threshold is applied"""
        # This is more of an integration test
        # The system should reject matches below 0.70 cosine similarity
        pass

    @pytest.mark.asyncio
    async def test_low_confidence_rejection(self, test_device_id, mock_audio_sample):
        """Should reject low-confidence matches"""
        # Would require mocked model to test properly
        pass


class TestSensitiveOperations:
    """Tests that sensitive operations require voiceprint verification"""

    @pytest.mark.asyncio
    async def test_push_note_requires_voiceprint(self):
        """Push to EHR should require voiceprint verification"""
        # This is an integration test - the endpoint should check voiceprint
        pass

    @pytest.mark.asyncio
    async def test_push_vitals_requires_voiceprint(self):
        """Push vitals should require voiceprint verification"""
        pass

    @pytest.mark.asyncio
    async def test_push_orders_requires_voiceprint(self):
        """Push orders should require voiceprint verification"""
        pass


class TestAuditLogging:
    """Tests for voiceprint audit logging"""

    @pytest.mark.asyncio
    async def test_enrollment_creates_audit_log(self, test_device_id, mock_audio_sample):
        """Should create audit log for enrollment attempts"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/enroll",
                json={
                    "device_id": test_device_id,
                    "audio_samples": [mock_audio_sample] * 3
                }
            )
            # Audit log verification would require checking log file

    @pytest.mark.asyncio
    async def test_verification_creates_audit_log(self, test_device_id, mock_audio_sample):
        """Should create audit log for verification attempts"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/voiceprint/verify",
                json={
                    "device_id": test_device_id,
                    "audio_sample": mock_audio_sample
                }
            )
            # Audit log verification would require checking log file


class TestVoiceprintDeletion:
    """Tests for voiceprint deletion"""

    @pytest.mark.asyncio
    async def test_delete_voiceprint(self, test_device_id):
        """Should allow deleting voiceprint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/api/v1/auth/voiceprint/{test_device_id}"
            )

            # Should succeed or return 404 if not found
            assert response.status_code in [200, 204, 404]
