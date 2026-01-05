"""
Unit Tests for Voiceprint Module

Direct tests for voiceprint.py functions to achieve high coverage.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import base64
import json
import numpy as np
import os
import tempfile
import sys

sys.path.insert(0, '..')


class TestVoiceprintHelpers:
    """Tests for voiceprint helper functions"""

    def test_get_voiceprint_path(self):
        """Should generate consistent path for clinician ID"""
        from voiceprint import _get_voiceprint_path

        path1 = _get_voiceprint_path("clinician-123")
        path2 = _get_voiceprint_path("clinician-123")

        assert path1 == path2
        assert path1.endswith(".json")

    def test_get_voiceprint_path_different_ids(self):
        """Should generate different paths for different IDs"""
        from voiceprint import _get_voiceprint_path

        path1 = _get_voiceprint_path("clinician-123")
        path2 = _get_voiceprint_path("clinician-456")

        assert path1 != path2

    def test_decode_audio_valid_base64(self):
        """Should decode valid base64 audio"""
        from voiceprint import _decode_audio

        original = b"test audio data"
        encoded = base64.b64encode(original).decode()

        decoded = _decode_audio(encoded)

        assert decoded == original

    def test_decode_audio_invalid_base64(self):
        """Should return None for invalid base64"""
        from voiceprint import _decode_audio

        result = _decode_audio("not-valid-base64!")

        assert result is None

    def test_cosine_similarity_identical_vectors(self):
        """Should return 1.0 for identical vectors"""
        from voiceprint import _cosine_similarity

        vec = np.array([1.0, 2.0, 3.0])
        similarity = _cosine_similarity(vec, vec)

        assert abs(similarity - 1.0) < 0.0001

    def test_cosine_similarity_orthogonal_vectors(self):
        """Should return 0 for orthogonal vectors"""
        from voiceprint import _cosine_similarity

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])

        similarity = _cosine_similarity(vec1, vec2)

        assert abs(similarity) < 0.0001

    def test_cosine_similarity_opposite_vectors(self):
        """Should return -1 for opposite vectors"""
        from voiceprint import _cosine_similarity

        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = -vec1

        similarity = _cosine_similarity(vec1, vec2)

        assert abs(similarity + 1.0) < 0.0001

    def test_cosine_similarity_zero_vector(self):
        """Should return 0 for zero vector"""
        from voiceprint import _cosine_similarity

        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([0.0, 0.0, 0.0])

        similarity = _cosine_similarity(vec1, vec2)

        assert similarity == 0.0


class TestEnrollmentPhrases:
    """Tests for enrollment phrases"""

    def test_get_enrollment_phrases_returns_list(self):
        """Should return list of phrases"""
        from voiceprint import get_enrollment_phrases

        phrases = get_enrollment_phrases()

        assert isinstance(phrases, list)
        assert len(phrases) > 0

    def test_get_enrollment_phrases_returns_copy(self):
        """Should return copy, not original"""
        from voiceprint import get_enrollment_phrases, ENROLLMENT_PHRASES

        phrases = get_enrollment_phrases()
        phrases.append("extra phrase")

        assert len(ENROLLMENT_PHRASES) < len(phrases)


class TestVoiceprintStorage:
    """Tests for voiceprint storage functions"""

    def test_save_and_load_voiceprint(self, tmp_path):
        """Should save and load voiceprint correctly"""
        from voiceprint import _save_voiceprint, _load_voiceprint, VOICEPRINT_DIR

        # Mock the voiceprint directory
        with patch('voiceprint.VOICEPRINT_DIR', str(tmp_path)):
            with patch('voiceprint._get_voiceprint_path') as mock_path:
                test_path = tmp_path / "test.json"
                mock_path.return_value = str(test_path)

                test_data = {
                    "clinician_id": "test-123",
                    "embedding": [0.1, 0.2, 0.3],
                    "enrolled_at": "2024-01-01T00:00:00"
                }

                _save_voiceprint("test-123", test_data)

                # Verify file was created
                assert test_path.exists()

                # Load and verify
                loaded = _load_voiceprint("test-123")
                assert loaded == test_data

    def test_load_nonexistent_voiceprint(self, tmp_path):
        """Should return None for non-existent voiceprint"""
        from voiceprint import _load_voiceprint

        with patch('voiceprint._get_voiceprint_path') as mock_path:
            mock_path.return_value = str(tmp_path / "nonexistent.json")

            result = _load_voiceprint("nonexistent")

            assert result is None


class TestEnrollment:
    """Tests for voiceprint enrollment"""

    def test_enroll_requires_minimum_samples(self):
        """Should require at least 3 audio samples"""
        from voiceprint import enroll_voiceprint

        audio = base64.b64encode(b"test").decode()
        result = enroll_voiceprint("test-id", [audio])

        assert result["success"] is False
        assert "at least 3" in result["error"]

    def test_enroll_with_two_samples_fails(self):
        """Should fail with only 2 samples"""
        from voiceprint import enroll_voiceprint

        audio = base64.b64encode(b"test").decode()
        result = enroll_voiceprint("test-id", [audio, audio])

        assert result["success"] is False

    @patch('voiceprint._extract_embedding')
    @patch('voiceprint._decode_audio')
    @patch('voiceprint._save_voiceprint')
    def test_enroll_success(self, mock_save, mock_decode, mock_extract):
        """Should successfully enroll with valid samples"""
        from voiceprint import enroll_voiceprint

        mock_decode.return_value = b"audio data"
        mock_extract.return_value = np.array([0.1, 0.2, 0.3])

        audio = base64.b64encode(b"test").decode()
        result = enroll_voiceprint(
            "test-id",
            [audio, audio, audio],
            clinician_name="Dr. Test"
        )

        assert result["success"] is True
        assert result["samples_used"] == 3
        mock_save.assert_called_once()

    @patch('voiceprint._decode_audio')
    def test_enroll_decode_failure(self, mock_decode):
        """Should fail if audio decode fails"""
        from voiceprint import enroll_voiceprint

        mock_decode.return_value = None

        audio = "invalid-audio"
        result = enroll_voiceprint("test-id", [audio, audio, audio])

        assert result["success"] is False
        assert "decode" in result["error"].lower()

    @patch('voiceprint._extract_embedding')
    @patch('voiceprint._decode_audio')
    def test_enroll_embedding_failure(self, mock_decode, mock_extract):
        """Should fail if embedding extraction fails"""
        from voiceprint import enroll_voiceprint

        mock_decode.return_value = b"audio data"
        mock_extract.return_value = None

        audio = base64.b64encode(b"test").decode()
        result = enroll_voiceprint("test-id", [audio, audio, audio])

        assert result["success"] is False
        assert "extract" in result["error"].lower() or "voiceprint" in result["error"].lower()


class TestVerification:
    """Tests for voiceprint verification"""

    @patch('voiceprint._load_voiceprint')
    def test_verify_no_enrollment(self, mock_load):
        """Should fail if not enrolled"""
        from voiceprint import verify_voiceprint

        mock_load.return_value = None

        audio = base64.b64encode(b"test").decode()
        result = verify_voiceprint("test-id", audio)

        assert result["success"] is False
        assert result["verified"] is False
        assert "no voiceprint" in result["error"].lower()

    @patch('voiceprint._load_voiceprint')
    @patch('voiceprint._decode_audio')
    def test_verify_decode_failure(self, mock_decode, mock_load):
        """Should fail if audio decode fails"""
        from voiceprint import verify_voiceprint

        mock_load.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_decode.return_value = None

        result = verify_voiceprint("test-id", "invalid")

        assert result["success"] is False
        assert result["verified"] is False

    @patch('voiceprint._load_voiceprint')
    @patch('voiceprint._decode_audio')
    @patch('voiceprint._extract_embedding')
    def test_verify_extraction_failure(self, mock_extract, mock_decode, mock_load):
        """Should fail if embedding extraction fails"""
        from voiceprint import verify_voiceprint

        mock_load.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_decode.return_value = b"audio"
        mock_extract.return_value = None

        audio = base64.b64encode(b"test").decode()
        result = verify_voiceprint("test-id", audio)

        assert result["success"] is False
        assert result["verified"] is False

    @patch('voiceprint._load_voiceprint')
    @patch('voiceprint._decode_audio')
    @patch('voiceprint._extract_embedding')
    def test_verify_high_similarity_accepted(self, mock_extract, mock_decode, mock_load):
        """Should accept high similarity"""
        from voiceprint import verify_voiceprint

        embedding = np.array([1.0, 0.0, 0.0])
        mock_load.return_value = {
            "embedding": embedding.tolist(),
            "clinician_name": "Dr. Test"
        }
        mock_decode.return_value = b"audio"
        # Return same embedding for high similarity
        mock_extract.return_value = embedding

        audio = base64.b64encode(b"test").decode()
        result = verify_voiceprint("test-id", audio)

        assert result["success"] is True
        assert result["verified"] is True
        assert result["confidence"] > 0.7
        assert result["status"] == "accepted"

    @patch('voiceprint._load_voiceprint')
    @patch('voiceprint._decode_audio')
    @patch('voiceprint._extract_embedding')
    def test_verify_low_similarity_rejected(self, mock_extract, mock_decode, mock_load):
        """Should reject low similarity"""
        from voiceprint import verify_voiceprint

        mock_load.return_value = {
            "embedding": [1.0, 0.0, 0.0],
            "clinician_name": "Dr. Test"
        }
        mock_decode.return_value = b"audio"
        # Return opposite embedding for low similarity
        mock_extract.return_value = np.array([-1.0, 0.0, 0.0])

        audio = base64.b64encode(b"test").decode()
        result = verify_voiceprint("test-id", audio)

        assert result["success"] is True
        assert result["verified"] is False
        assert result["status"] == "rejected"


class TestIsEnrolled:
    """Tests for is_enrolled check"""

    @patch('voiceprint._load_voiceprint')
    def test_is_enrolled_true(self, mock_load):
        """Should return True when enrolled"""
        from voiceprint import is_enrolled

        mock_load.return_value = {"embedding": [0.1]}

        assert is_enrolled("test-id") is True

    @patch('voiceprint._load_voiceprint')
    def test_is_enrolled_false(self, mock_load):
        """Should return False when not enrolled"""
        from voiceprint import is_enrolled

        mock_load.return_value = None

        assert is_enrolled("test-id") is False


class TestDeleteVoiceprint:
    """Tests for voiceprint deletion"""

    def test_delete_existing_voiceprint(self, tmp_path):
        """Should delete existing voiceprint"""
        from voiceprint import delete_voiceprint

        # Create a test file
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": true}')

        with patch('voiceprint._get_voiceprint_path', return_value=str(test_file)):
            result = delete_voiceprint("test-id")

            assert result["success"] is True
            assert not test_file.exists()

    def test_delete_nonexistent_voiceprint(self, tmp_path):
        """Should return error for nonexistent voiceprint"""
        from voiceprint import delete_voiceprint

        with patch('voiceprint._get_voiceprint_path', return_value=str(tmp_path / "nonexistent.json")):
            result = delete_voiceprint("test-id")

            assert result["success"] is False
            assert "found" in result["error"].lower()  # "No voiceprint found"


class TestEmbeddingExtraction:
    """Tests for embedding extraction with mocked model"""

    @patch('voiceprint._get_speaker_model')
    def test_extract_embedding_placeholder_mode(self, mock_model):
        """Should return placeholder embedding when model unavailable"""
        from voiceprint import _extract_embedding

        mock_model.return_value = None

        embedding = _extract_embedding(b"audio data")

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 192  # Placeholder size

    @patch('voiceprint._get_speaker_model')
    @patch('voiceprint._audio_to_tensor')
    def test_extract_embedding_with_model(self, mock_tensor, mock_model):
        """Should extract embedding using model"""
        from voiceprint import _extract_embedding

        # Mock the model with a tensor-like object
        mock_speaker_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.squeeze.return_value.numpy.return_value = np.array([0.1, 0.2, 0.3])
        mock_speaker_model.encode_batch.return_value = mock_embedding
        mock_model.return_value = mock_speaker_model

        # Mock tensor conversion (not None)
        mock_tensor.return_value = MagicMock()

        embedding = _extract_embedding(b"audio data")

        assert embedding is not None
        mock_speaker_model.encode_batch.assert_called_once()

    @patch('voiceprint._get_speaker_model')
    @patch('voiceprint._audio_to_tensor')
    def test_extract_embedding_tensor_failure(self, mock_tensor, mock_model):
        """Should return None if tensor conversion fails"""
        from voiceprint import _extract_embedding

        mock_model.return_value = MagicMock()
        mock_tensor.return_value = None

        embedding = _extract_embedding(b"audio data")

        assert embedding is None


class TestModelLoading:
    """Tests for speaker model loading"""

    @patch('voiceprint._USE_SPEECHBRAIN', False)
    def test_model_disabled(self):
        """Should return None when SpeechBrain disabled"""
        from voiceprint import _get_speaker_model
        import voiceprint

        # Reset model cache
        voiceprint._speaker_model = None
        voiceprint._USE_SPEECHBRAIN = False

        model = _get_speaker_model()

        # When disabled, should return None
        assert model is None or voiceprint._speaker_model is None
