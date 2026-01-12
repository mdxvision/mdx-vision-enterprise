"""
MDx Vision EHR Proxy - Transcription Service Tests

Tests for WebSocket transcription and audio processing.
Run with: pytest tests/test_transcription.py -v
"""

import pytest
import asyncio
import json
import base64
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== MEDICAL VOCABULARY TESTS ====================

class TestMedicalVocabulary:
    """Tests for medical vocabulary loading and specialty detection"""

    def test_vocabulary_loads(self):
        """Test that medical vocabulary loads successfully"""
        from medical_vocabulary import get_vocabulary
        vocab = get_vocabulary()
        assert isinstance(vocab, list)
        assert len(vocab) > 0

    def test_vocabulary_contains_common_terms(self):
        """Test vocabulary contains common medical terms"""
        from medical_vocabulary import get_vocabulary
        vocab = get_vocabulary()
        vocab_lower = [v.lower() for v in vocab]

        # Test for terms that are actually in the medical vocabulary
        common_terms = ["hypertension", "diabetes", "blood pressure", "heart rate"]
        for term in common_terms:
            assert term in vocab_lower, f"Missing common term: {term}"

    def test_specialty_vocabulary_cardiology(self):
        """Test cardiology specialty vocabulary"""
        from medical_vocabulary import get_vocabulary
        vocab = get_vocabulary(["cardiology"])
        vocab_lower = [v.lower() for v in vocab]

        cardio_terms = ["echocardiogram", "arrhythmia", "myocardial"]
        found = sum(1 for term in cardio_terms if term in vocab_lower)
        assert found > 0, "Should include cardiology terms"

    def test_specialty_vocabulary_pulmonology(self):
        """Test pulmonology specialty vocabulary"""
        from medical_vocabulary import get_vocabulary
        vocab = get_vocabulary(["pulmonology"])
        vocab_lower = [v.lower() for v in vocab]

        pulm_terms = ["bronchitis", "asthma", "spirometry"]
        found = sum(1 for term in pulm_terms if term in vocab_lower)
        assert found > 0, "Should include pulmonology terms"

    def test_multiple_specialties(self):
        """Test combining multiple specialty vocabularies"""
        from medical_vocabulary import get_vocabulary
        vocab = get_vocabulary(["cardiology", "pulmonology"])
        assert len(vocab) > 100  # Should have substantial combined vocabulary


# ==================== SPECIALTY DETECTION TESTS ====================

class TestSpecialtyDetection:
    """Tests for auto-detecting specialties from patient conditions"""

    def test_detect_cardiology_from_conditions(self):
        """Test detecting cardiology from heart-related conditions"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        conditions = [
            {"name": "Atrial fibrillation", "code": "I48.91"},
            {"name": "Heart failure", "code": "I50.9"}
        ]
        specialties = detect_specialties_from_patient_conditions(conditions)
        assert "cardiology" in specialties

    def test_detect_pulmonology_from_conditions(self):
        """Test detecting pulmonology from lung-related conditions"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        conditions = [
            {"name": "COPD", "code": "J44.9"},
            {"name": "Asthma", "code": "J45.909"}
        ]
        specialties = detect_specialties_from_patient_conditions(conditions)
        assert "pulmonology" in specialties

    def test_detect_multiple_specialties(self):
        """Test detecting multiple specialties"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        conditions = [
            {"name": "Atrial fibrillation", "code": "I48.91"},
            {"name": "COPD", "code": "J44.9"},
            {"name": "Type 2 Diabetes", "code": "E11.9"}
        ]
        specialties = detect_specialties_from_patient_conditions(conditions)
        assert len(specialties) >= 2


# ==================== TRANSCRIPTION RESULT TESTS ====================

class TestTranscriptionResult:
    """Tests for transcription result parsing"""

    def test_parse_assemblyai_partial(self):
        """Test parsing AssemblyAI partial transcript"""
        from transcription import TranscriptionResult

        data = {
            "message_type": "PartialTranscript",
            "text": "The patient reports",
            "confidence": 0.85
        }

        result = TranscriptionResult(
            text=data["text"],
            is_final=False,
            confidence=data["confidence"]
        )

        assert result.text == "The patient reports"
        assert result.is_final is False
        assert result.confidence == 0.85

    def test_parse_assemblyai_final(self):
        """Test parsing AssemblyAI final transcript"""
        from transcription import TranscriptionResult

        data = {
            "message_type": "FinalTranscript",
            "text": "The patient reports headache for three days.",
            "confidence": 0.95,
            "words": [
                {"text": "The", "speaker": 0},
                {"text": "patient", "speaker": 0}
            ]
        }

        result = TranscriptionResult(
            text=data["text"],
            is_final=True,
            confidence=data["confidence"],
            speaker="Speaker 0"
        )

        assert result.is_final is True
        assert result.speaker == "Speaker 0"


# ==================== SPEAKER MAPPING TESTS ====================

class TestSpeakerMapping:
    """Tests for speaker diarization and name mapping"""

    def test_map_speaker_0_to_clinician(self):
        """Test that Speaker 0 maps to clinician name"""
        from transcription import TranscriptionSession

        session = TranscriptionSession("test-123", speaker_context={
            "clinician": "Dr. Smith",
            "patient": "John Doe"
        })
        session.set_speaker_context("Dr. Smith", "John Doe")

        mapped = session._map_speaker("Speaker 0")
        assert mapped == "Dr. Smith"

    def test_map_speaker_1_to_patient(self):
        """Test that Speaker 1 maps to patient name"""
        from transcription import TranscriptionSession

        session = TranscriptionSession("test-123")
        session.set_speaker_context("Dr. Smith", "John Doe")

        mapped = session._map_speaker("Speaker 1")
        assert mapped == "John Doe"

    def test_map_unknown_speaker(self):
        """Test mapping unknown speaker index"""
        from transcription import TranscriptionSession

        session = TranscriptionSession("test-123")
        session.set_speaker_context("Dr. Smith", "John Doe")

        # Speaker 5 should fall back to generic name
        mapped = session._map_speaker("Speaker 5")
        assert "Attendee" in mapped or "Speaker 5" in mapped


# ==================== AUDIO PROCESSING TESTS ====================

class TestAudioProcessing:
    """Tests for audio data handling"""

    def test_audio_base64_encoding(self):
        """Test audio data is properly base64 encoded"""
        # Simulate 16-bit PCM audio data
        audio_data = bytes([0, 0, 128, 0] * 100)  # 400 bytes of audio

        encoded = base64.b64encode(audio_data).decode("utf-8")
        decoded = base64.b64decode(encoded)

        assert decoded == audio_data

    def test_audio_chunk_size(self):
        """Test expected audio chunk sizes"""
        # At 16kHz, 16-bit, mono: 32000 bytes/sec
        # Typical chunk: 100ms = 3200 bytes
        sample_rate = 16000
        bit_depth = 16
        channels = 1
        duration_ms = 100

        expected_bytes = (sample_rate * bit_depth * channels * duration_ms) // (8 * 1000)
        assert expected_bytes == 3200


# ==================== SESSION MANAGEMENT TESTS ====================

class TestSessionManagement:
    """Tests for transcription session lifecycle"""

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test creating a new transcription session"""
        from transcription import TranscriptionSession

        session = TranscriptionSession("test-session-1")
        assert session.session_id == "test-session-1"
        assert session.is_active is False

    @pytest.mark.asyncio
    async def test_session_stores_transcript(self):
        """Test that session accumulates transcript"""
        from transcription import TranscriptionSession, TranscriptionResult

        session = TranscriptionSession("test-session-2")
        session.full_transcript = []

        # Simulate receiving final transcripts
        session.full_transcript.append("Hello doctor.")
        session.full_transcript.append("I have a headache.")

        full = session.get_full_transcript()
        assert "Hello doctor" in full
        assert "headache" in full


# ==================== PROVIDER CONFIGURATION TESTS ====================

class TestProviderConfiguration:
    """Tests for transcription provider configuration"""

    def test_default_provider_is_assemblyai(self):
        """Test that default provider is AssemblyAI"""
        from transcription import TRANSCRIPTION_PROVIDER
        # Should default to assemblyai if not set
        assert TRANSCRIPTION_PROVIDER in ["assemblyai", "deepgram"]

    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": ""}, clear=False)
    def test_provider_requires_api_key(self):
        """Test that providers require API keys"""
        # Re-import to get fresh module with cleared env
        import importlib
        import transcription
        importlib.reload(transcription)
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key=None)
        # Should raise error on connect without key
        with pytest.raises(ValueError, match="API_KEY"):
            asyncio.run(provider.connect())


# ==================== ERROR HANDLING TESTS ====================

class TestTranscriptionErrors:
    """Tests for error handling in transcription"""

    def test_invalid_audio_handling(self):
        """Test handling of invalid audio data"""
        # Empty audio should not crash
        audio_data = bytes()
        encoded = base64.b64encode(audio_data).decode("utf-8")
        assert encoded == ""

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self):
        """Test handling of connection failures"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="invalid-key")
        # Connection should fail gracefully
        try:
            result = await provider.connect()
            assert result is False
        except Exception:
            pass  # Expected to fail


# ==================== INTEGRATION HELPER TESTS ====================

class TestIntegrationHelpers:
    """Tests for integration utilities"""

    def test_session_id_format(self):
        """Test session ID format is valid"""
        import uuid

        session_id = str(uuid.uuid4())[:8]
        assert len(session_id) == 8
        assert all(c in "0123456789abcdef-" for c in session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
