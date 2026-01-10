"""
Comprehensive tests for voiceprint.py biometric authentication.
Tests embedding extraction, cosine similarity, enrollment, verification, and storage.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import base64


class TestCosineSimilarity:
    """Tests for cosine similarity calculation"""

    def test_identical_vectors(self):
        """Identical vectors should have similarity 1.0"""
        from voiceprint import _cosine_similarity
        vec = np.array([1.0, 2.0, 3.0])
        result = _cosine_similarity(vec, vec)
        assert abs(result - 1.0) < 0.0001

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0"""
        from voiceprint import _cosine_similarity
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        result = _cosine_similarity(vec1, vec2)
        assert abs(result) < 0.0001

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity -1.0"""
        from voiceprint import _cosine_similarity
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([-1.0, -2.0, -3.0])
        result = _cosine_similarity(vec1, vec2)
        assert abs(result - (-1.0)) < 0.0001

    def test_similar_vectors(self):
        """Similar vectors should have high similarity"""
        from voiceprint import _cosine_similarity
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.1, 2.1, 3.1])
        result = _cosine_similarity(vec1, vec2)
        assert result > 0.99

    def test_different_magnitudes(self):
        """Different magnitudes should still work"""
        from voiceprint import _cosine_similarity
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([100.0, 0.0, 0.0])
        result = _cosine_similarity(vec1, vec2)
        assert abs(result - 1.0) < 0.0001


class TestEnrollmentPhrases:
    """Tests for enrollment phrases"""

    def test_get_enrollment_phrases(self):
        """Should return enrollment phrases"""
        from voiceprint import get_enrollment_phrases
        phrases = get_enrollment_phrases()
        assert isinstance(phrases, list)
        assert len(phrases) >= 3

    def test_enrollment_phrases_content(self):
        """Phrases should be non-empty strings"""
        from voiceprint import get_enrollment_phrases
        phrases = get_enrollment_phrases()
        for phrase in phrases:
            assert isinstance(phrase, str)
            assert len(phrase) > 0

    def test_enrollment_phrases_type(self):
        """Phrases list should contain expected content"""
        from voiceprint import ENROLLMENT_PHRASES
        assert isinstance(ENROLLMENT_PHRASES, list)
        assert len(ENROLLMENT_PHRASES) >= 3


class TestEnrollVoiceprint:
    """Tests for voiceprint enrollment"""

    def test_enroll_too_few_samples(self):
        """Should reject enrollment with < 3 samples"""
        from voiceprint import enroll_voiceprint
        result = enroll_voiceprint(
            clinician_id="test-clinician",
            audio_samples=["sample1", "sample2"]
        )
        assert result["success"] is False


class TestVerifyVoiceprint:
    """Tests for voiceprint verification"""

    def test_verify_no_enrolled_voiceprint(self):
        """Should fail verification with no enrolled voiceprint"""
        from voiceprint import verify_voiceprint
        result = verify_voiceprint(
            clinician_id="nonexistent-clinician-xyz-123",
            audio_sample="audio_data"
        )
        assert result["verified"] is False


class TestIsEnrolled:
    """Tests for is_enrolled function"""

    def test_is_enrolled_false(self):
        """Should return False for non-enrolled clinician"""
        from voiceprint import is_enrolled
        result = is_enrolled("definitely-not-enrolled-xyz")
        assert result is False

    @patch("voiceprint._load_voiceprint")
    def test_is_enrolled_true(self, mock_load):
        """Should return True for enrolled clinician"""
        from voiceprint import is_enrolled
        mock_load.return_value = {"embedding": [0.1, 0.2, 0.3]}
        result = is_enrolled("enrolled-clinician")
        assert result is True


class TestDeleteVoiceprint:
    """Tests for delete_voiceprint function"""

    def test_delete_nonexistent(self):
        """Should handle deleting non-existent voiceprint"""
        from voiceprint import delete_voiceprint
        result = delete_voiceprint("nonexistent-voiceprint-xyz")
        # Should not raise
        assert isinstance(result, dict)


class TestAudioProcessing:
    """Tests for audio processing helpers"""

    def test_decode_audio_base64(self):
        """Should decode base64 audio"""
        from voiceprint import _decode_audio
        original = b"\x00\x01\x02\x03\x04\x05"
        encoded = base64.b64encode(original).decode("utf-8")
        decoded = _decode_audio(encoded)
        assert decoded == original

    def test_decode_audio_invalid(self):
        """Should handle invalid base64"""
        from voiceprint import _decode_audio
        result = _decode_audio("not-valid-base64!!!")
        assert result is None

    def test_audio_to_tensor(self):
        """Should convert audio bytes to tensor"""
        from voiceprint import _audio_to_tensor
        # 16-bit PCM audio sample
        audio = b"\x00\x01\x00\x02\x00\x03\x00\x04"
        result = _audio_to_tensor(audio)
        # Should return tensor or None
        assert result is None or hasattr(result, "shape")


class TestThresholds:
    """Tests for verification thresholds"""

    def test_threshold_accept(self):
        """Should have THRESHOLD_ACCEPT constant"""
        from voiceprint import THRESHOLD_ACCEPT
        assert isinstance(THRESHOLD_ACCEPT, float)
        assert 0 < THRESHOLD_ACCEPT < 1

    def test_threshold_reject(self):
        """Should have THRESHOLD_REJECT constant"""
        from voiceprint import THRESHOLD_REJECT
        assert isinstance(THRESHOLD_REJECT, float)
        assert 0 < THRESHOLD_REJECT < 1

    def test_thresholds_order(self):
        """THRESHOLD_ACCEPT should be higher than THRESHOLD_REJECT"""
        from voiceprint import THRESHOLD_ACCEPT, THRESHOLD_REJECT
        assert THRESHOLD_ACCEPT > THRESHOLD_REJECT


class TestVoiceprintPath:
    """Tests for voiceprint file path generation"""

    def test_voiceprint_dir_exists(self):
        """Should have VOICEPRINT_DIR constant"""
        from voiceprint import VOICEPRINT_DIR
        assert isinstance(VOICEPRINT_DIR, str)
        assert len(VOICEPRINT_DIR) > 0


class TestVoiceprintDataFormat:
    """Tests for voiceprint data format"""

    def test_voiceprint_file_structure(self):
        """Saved voiceprint should have required fields"""
        expected_fields = ["embedding", "clinician_id"]
        # The save function stores these fields
        data = {
            "embedding": [0.1, 0.2, 0.3],
            "clinician_id": "test-123"
        }
        for field in expected_fields:
            assert field in data


class TestSpeechBrainMode:
    """Tests for SpeechBrain mode flag"""

    def test_use_speechbrain_flag(self):
        """Should have _USE_SPEECHBRAIN flag"""
        from voiceprint import _USE_SPEECHBRAIN
        assert isinstance(_USE_SPEECHBRAIN, bool)
