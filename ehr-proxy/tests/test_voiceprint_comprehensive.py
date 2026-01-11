"""
Comprehensive unit tests for voiceprint.py - Voice biometric authentication

Covers:
- Audio decoding and processing
- Embedding extraction
- Cosine similarity calculation
- Enrollment flow
- Verification flow
- Voiceprint storage and retrieval
"""

import pytest
import numpy as np
import base64
from unittest.mock import patch, MagicMock
import io


class TestAudioDecoding:
    """Tests for _decode_audio function"""

    def test_decode_valid_base64(self):
        """Should decode valid base64 audio"""
        from voiceprint import _decode_audio

        # Create some test data
        test_data = b"test audio data"
        encoded = base64.b64encode(test_data).decode()

        result = _decode_audio(encoded)

        assert result == test_data

    def test_decode_invalid_base64(self):
        """Should return None for invalid base64"""
        from voiceprint import _decode_audio

        result = _decode_audio("not-valid-base64!!!")

        assert result is None

    def test_decode_empty_string(self):
        """Should handle empty string"""
        from voiceprint import _decode_audio

        result = _decode_audio("")

        # Empty base64 decodes to empty bytes
        assert result == b""


class TestAudioToTensor:
    """Tests for _audio_to_tensor function"""

    def test_audio_to_tensor_invalid_bytes(self):
        """Should return None for invalid audio bytes"""
        from voiceprint import _audio_to_tensor

        result = _audio_to_tensor(b"not real audio")

        assert result is None

    def test_audio_to_tensor_empty_bytes(self):
        """Should return None for empty bytes"""
        from voiceprint import _audio_to_tensor

        result = _audio_to_tensor(b"")

        assert result is None

    def test_audio_to_tensor_failure(self):
        """Should return None on failure"""
        from voiceprint import _audio_to_tensor

        # Invalid audio bytes should cause failure
        result = _audio_to_tensor(b"not real audio")

        assert result is None


class TestCosineSimilarity:
    """Tests for _cosine_similarity function"""

    def test_identical_vectors(self):
        """Should return 1.0 for identical vectors"""
        from voiceprint import _cosine_similarity

        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])

        result = _cosine_similarity(a, b)

        assert result == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Should return 0.0 for orthogonal vectors"""
        from voiceprint import _cosine_similarity

        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])

        result = _cosine_similarity(a, b)

        assert result == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Should return -1.0 for opposite vectors"""
        from voiceprint import _cosine_similarity

        a = np.array([1.0, 0.0, 0.0])
        b = np.array([-1.0, 0.0, 0.0])

        result = _cosine_similarity(a, b)

        assert result == pytest.approx(-1.0)

    def test_zero_vector(self):
        """Should return 0.0 if either vector is zero"""
        from voiceprint import _cosine_similarity

        a = np.array([1.0, 2.0, 3.0])
        b = np.array([0.0, 0.0, 0.0])

        result = _cosine_similarity(a, b)

        assert result == 0.0

    def test_similar_vectors(self):
        """Should return high similarity for similar vectors"""
        from voiceprint import _cosine_similarity

        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.1, 2.1, 3.1])

        result = _cosine_similarity(a, b)

        assert result > 0.99


class TestEnrollmentPhrases:
    """Tests for enrollment phrase functions"""

    def test_get_enrollment_phrases(self):
        """Should return enrollment phrases"""
        from voiceprint import get_enrollment_phrases

        phrases = get_enrollment_phrases()

        assert len(phrases) == 3
        assert all(isinstance(p, str) for p in phrases)

    def test_phrases_are_copy(self):
        """Should return a copy, not original"""
        from voiceprint import get_enrollment_phrases, ENROLLMENT_PHRASES

        phrases = get_enrollment_phrases()
        phrases.append("new phrase")

        # Original should be unchanged
        assert len(ENROLLMENT_PHRASES) == 3


class TestEnrollVoiceprint:
    """Tests for enroll_voiceprint function"""

    def test_enroll_insufficient_samples(self):
        """Should fail with less than 3 samples"""
        from voiceprint import enroll_voiceprint

        result = enroll_voiceprint(
            clinician_id="test-001",
            audio_samples=["sample1", "sample2"],  # Only 2
            clinician_name="Dr. Test"
        )

        assert result["success"] is False
        assert "3 audio samples" in result["error"]

    @patch("voiceprint._save_voiceprint")
    @patch("voiceprint._extract_embedding")
    @patch("voiceprint._decode_audio")
    def test_enroll_success(self, mock_decode, mock_extract, mock_save):
        """Should successfully enroll with valid samples"""
        from voiceprint import enroll_voiceprint

        # Mock audio decoding
        mock_decode.return_value = b"audio bytes"

        # Mock embedding extraction - return consistent embeddings
        mock_extract.return_value = np.random.randn(192).astype(np.float32)

        # Create 3 base64 encoded "audio" samples
        samples = [base64.b64encode(b"sample1").decode(),
                   base64.b64encode(b"sample2").decode(),
                   base64.b64encode(b"sample3").decode()]

        result = enroll_voiceprint(
            clinician_id="test-clinician-001",
            audio_samples=samples,
            clinician_name="Dr. Test"
        )

        assert result["success"] is True
        assert result["samples_used"] == 3
        mock_save.assert_called_once()

    @patch("voiceprint._extract_embedding")
    @patch("voiceprint._decode_audio")
    def test_enroll_failed_extraction(self, mock_decode, mock_extract):
        """Should fail if embedding extraction fails"""
        from voiceprint import enroll_voiceprint

        mock_decode.return_value = b"audio bytes"
        mock_extract.return_value = None  # Extraction fails

        samples = [base64.b64encode(b"s1").decode(),
                   base64.b64encode(b"s2").decode(),
                   base64.b64encode(b"s3").decode()]

        result = enroll_voiceprint(
            clinician_id="test-002",
            audio_samples=samples
        )

        assert result["success"] is False


class TestVerifyVoiceprint:
    """Tests for verify_voiceprint function"""

    @patch("voiceprint._load_voiceprint")
    def test_verify_no_enrollment(self, mock_load):
        """Should fail if clinician not enrolled"""
        from voiceprint import verify_voiceprint

        mock_load.return_value = None

        result = verify_voiceprint(
            clinician_id="unknown-clinician",
            audio_sample=base64.b64encode(b"audio").decode()
        )

        assert result["success"] is False
        assert result["verified"] is False
        assert "No voiceprint enrolled" in result["error"]

    @patch("voiceprint._cosine_similarity")
    @patch("voiceprint._extract_embedding")
    @patch("voiceprint._decode_audio")
    @patch("voiceprint._load_voiceprint")
    def test_verify_success(self, mock_load, mock_decode, mock_extract, mock_cosine):
        """Should verify matching voiceprint"""
        from voiceprint import verify_voiceprint

        # Mock stored voiceprint
        mock_load.return_value = {
            "clinician_id": "test-001",
            "embedding": np.random.randn(192).astype(np.float32).tolist(),
            "clinician_name": "Dr. Test"
        }

        mock_decode.return_value = b"audio bytes"
        mock_extract.return_value = np.random.randn(192).astype(np.float32)
        mock_cosine.return_value = 0.85  # Above threshold

        result = verify_voiceprint(
            clinician_id="test-001",
            audio_sample=base64.b64encode(b"audio").decode()
        )

        assert result["success"] is True
        assert result["verified"] is True
        assert result["confidence"] >= 0.7

    @patch("voiceprint._cosine_similarity")
    @patch("voiceprint._extract_embedding")
    @patch("voiceprint._decode_audio")
    @patch("voiceprint._load_voiceprint")
    def test_verify_failed_low_similarity(self, mock_load, mock_decode, mock_extract, mock_cosine):
        """Should fail verification with low similarity"""
        from voiceprint import verify_voiceprint

        mock_load.return_value = {
            "clinician_id": "test-001",
            "embedding": np.random.randn(192).astype(np.float32).tolist()
        }

        mock_decode.return_value = b"audio bytes"
        mock_extract.return_value = np.random.randn(192).astype(np.float32)
        mock_cosine.return_value = 0.4  # Below threshold

        result = verify_voiceprint(
            clinician_id="test-001",
            audio_sample=base64.b64encode(b"audio").decode()
        )

        assert result["verified"] is False


class TestVoiceprintStorage:
    """Tests for voiceprint storage functions"""

    @patch("voiceprint.os.path.exists")
    @patch("builtins.open", create=True)
    def test_load_voiceprint_exists(self, mock_open, mock_exists):
        """Should load existing voiceprint"""
        from voiceprint import _load_voiceprint
        import json

        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "clinician_id": "test-001",
            "embedding": [0.1, 0.2, 0.3],
            "clinician_name": "Dr. Test"
        })

        result = _load_voiceprint("test-001")

        assert result is not None

    @patch("voiceprint.os.path.exists")
    def test_load_voiceprint_not_exists(self, mock_exists):
        """Should return None for non-existent voiceprint"""
        from voiceprint import _load_voiceprint

        mock_exists.return_value = False

        result = _load_voiceprint("unknown-001")

        assert result is None

    @patch("voiceprint.os.path.exists")
    @patch("voiceprint.os.remove")
    def test_delete_voiceprint_exists(self, mock_remove, mock_exists):
        """Should delete existing voiceprint"""
        from voiceprint import delete_voiceprint

        mock_exists.return_value = True

        result = delete_voiceprint("test-001")

        assert result["success"] is True
        mock_remove.assert_called_once()

    @patch("voiceprint.os.path.exists")
    def test_delete_voiceprint_not_exists(self, mock_exists):
        """Should return error for non-existent voiceprint"""
        from voiceprint import delete_voiceprint

        mock_exists.return_value = False

        result = delete_voiceprint("unknown-001")

        assert result["success"] is False
        assert "No voiceprint found" in result["error"]


class TestSpeakerModel:
    """Tests for speaker model loading"""

    def test_get_model_placeholder_mode(self):
        """Should handle placeholder mode"""
        from voiceprint import _get_speaker_model
        import voiceprint

        # Save original state
        original_use = voiceprint._USE_SPEECHBRAIN
        original_model = voiceprint._speaker_model

        # Test with SpeechBrain disabled
        voiceprint._USE_SPEECHBRAIN = False
        voiceprint._speaker_model = None

        result = _get_speaker_model()

        # When disabled, returns None (placeholder mode uses random embeddings)
        assert result is None

        # Restore original state
        voiceprint._USE_SPEECHBRAIN = original_use
        voiceprint._speaker_model = original_model


class TestExtractEmbedding:
    """Tests for _extract_embedding function"""

    @patch("voiceprint._get_speaker_model")
    def test_extract_embedding_no_model(self, mock_get_model):
        """Should return placeholder embedding if no model"""
        from voiceprint import _extract_embedding

        mock_get_model.return_value = None

        result = _extract_embedding(b"audio bytes")

        # Should return random placeholder embedding
        assert result is not None
        assert len(result) == 192

    @patch("voiceprint._audio_to_tensor")
    @patch("voiceprint._get_speaker_model")
    def test_extract_embedding_tensor_failure(self, mock_get_model, mock_to_tensor):
        """Should return None if tensor conversion fails"""
        from voiceprint import _extract_embedding

        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_to_tensor.return_value = None  # Tensor conversion fails

        result = _extract_embedding(b"audio bytes")

        assert result is None

    @patch("voiceprint._audio_to_tensor")
    @patch("voiceprint._get_speaker_model")
    def test_extract_embedding_success(self, mock_get_model, mock_to_tensor):
        """Should extract embedding successfully"""
        from voiceprint import _extract_embedding

        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.squeeze.return_value.numpy.return_value = np.random.randn(192)
        mock_model.encode_batch.return_value = mock_embedding
        mock_get_model.return_value = mock_model

        mock_waveform = MagicMock()
        mock_to_tensor.return_value = mock_waveform

        result = _extract_embedding(b"audio bytes")

        assert result is not None
        mock_model.encode_batch.assert_called_once_with(mock_waveform)


class TestVerificationThreshold:
    """Tests for verification threshold constants"""

    def test_threshold_accept_value(self):
        """Should have appropriate accept threshold value"""
        from voiceprint import THRESHOLD_ACCEPT

        # Accept threshold should be between 0.5 and 0.9 for security
        assert 0.5 <= THRESHOLD_ACCEPT <= 0.9
        assert THRESHOLD_ACCEPT == 0.70

    def test_threshold_reject_value(self):
        """Should have appropriate reject threshold value"""
        from voiceprint import THRESHOLD_REJECT, THRESHOLD_ACCEPT

        # Reject threshold should be below accept threshold
        assert THRESHOLD_REJECT < THRESHOLD_ACCEPT
        assert THRESHOLD_REJECT == 0.50

    def test_is_enrolled(self):
        """Should check enrollment status"""
        from voiceprint import is_enrolled

        # Non-existent clinician should not be enrolled
        result = is_enrolled("nonexistent-clinician-xyz")
        assert result is False
