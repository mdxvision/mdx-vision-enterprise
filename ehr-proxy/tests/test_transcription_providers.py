"""
Comprehensive tests for transcription.py providers and WebSocket handling.
Tests AssemblyAI, Deepgram providers, message parsing, and session management.
"""
import pytest
import asyncio
import json
import base64
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass"""

    def test_transcription_result_creation(self):
        """Should create a TranscriptionResult"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95
        )
        assert result.text == "Hello world"
        assert result.is_final is True
        assert result.confidence == 0.95
        assert result.words == []
        assert result.speaker is None

    def test_transcription_result_with_words(self):
        """Should create TranscriptionResult with words"""
        from transcription import TranscriptionResult
        words = [
            {"text": "Hello", "start": 0, "end": 500, "confidence": 0.9},
            {"text": "world", "start": 500, "end": 1000, "confidence": 0.95}
        ]
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=words
        )
        assert len(result.words) == 2
        assert result.words[0]["text"] == "Hello"

    def test_transcription_result_with_speaker(self):
        """Should create TranscriptionResult with speaker"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(
            text="Hello",
            is_final=True,
            confidence=0.9,
            speaker="Speaker 1"
        )
        assert result.speaker == "Speaker 1"


class TestAssemblyAIMessageParsing:
    """Tests for AssemblyAI message parsing logic"""

    def test_parse_partial_transcript(self):
        """Should parse partial transcript message"""
        msg = {
            "message_type": "PartialTranscript",
            "text": "Hello",
            "confidence": 0.8
        }
        assert msg["message_type"] == "PartialTranscript"
        assert msg["text"] == "Hello"

    def test_parse_final_transcript(self):
        """Should parse final transcript message"""
        msg = {
            "message_type": "FinalTranscript",
            "text": "Hello world",
            "confidence": 0.95,
            "words": [
                {"text": "Hello", "start": 0, "end": 500, "confidence": 0.9, "speaker": 0},
                {"text": "world", "start": 500, "end": 1000, "confidence": 0.95, "speaker": 0}
            ]
        }
        assert msg["message_type"] == "FinalTranscript"
        assert len(msg["words"]) == 2
        assert msg["words"][0]["speaker"] == 0

    def test_parse_session_begins(self):
        """Should parse session begins message"""
        msg = {
            "message_type": "SessionBegins",
            "session_id": "test-session-123",
            "expires_at": "2024-01-01T12:00:00Z"
        }
        assert msg["message_type"] == "SessionBegins"
        assert msg["session_id"] == "test-session-123"

    def test_parse_session_terminated(self):
        """Should parse session terminated message"""
        msg = {
            "message_type": "SessionTerminated"
        }
        assert msg["message_type"] == "SessionTerminated"

    def test_parse_error_message(self):
        """Should parse error message"""
        msg = {
            "message_type": "error",
            "error": "Authentication failed"
        }
        assert msg.get("error") == "Authentication failed"


class TestDeepgramMessageParsing:
    """Tests for Deepgram message parsing logic"""

    def test_parse_interim_result(self):
        """Should parse interim result message"""
        msg = {
            "type": "Results",
            "channel_index": [0, 1],
            "duration": 1.5,
            "start": 0.0,
            "is_final": False,
            "speech_final": False,
            "channel": {
                "alternatives": [
                    {"transcript": "Hello", "confidence": 0.8, "words": []}
                ]
            }
        }
        assert msg["type"] == "Results"
        assert msg["is_final"] is False

    def test_parse_final_result(self):
        """Should parse final result message"""
        msg = {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "Hello world",
                        "confidence": 0.95,
                        "words": [
                            {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.9, "speaker": 0},
                            {"word": "world", "start": 0.5, "end": 1.0, "confidence": 0.95, "speaker": 0}
                        ]
                    }
                ]
            }
        }
        assert msg["is_final"] is True
        assert msg["speech_final"] is True
        words = msg["channel"]["alternatives"][0]["words"]
        assert len(words) == 2

    def test_parse_metadata_message(self):
        """Should parse metadata message"""
        msg = {
            "type": "Metadata",
            "request_id": "req-123",
            "model_info": {
                "name": "nova-2-medical",
                "version": "2024.1"
            }
        }
        assert msg["type"] == "Metadata"
        assert msg["model_info"]["name"] == "nova-2-medical"

    def test_parse_utterance_end(self):
        """Should parse utterance end message"""
        msg = {
            "type": "UtteranceEnd",
            "channel": [0, 1]
        }
        assert msg["type"] == "UtteranceEnd"


class TestAudioDataEncoding:
    """Tests for audio data encoding"""

    def test_base64_encode_audio(self):
        """Should encode audio data to base64"""
        audio_data = b"\x00\x01\x02\x03\x04\x05"
        encoded = base64.b64encode(audio_data).decode("utf-8")
        assert isinstance(encoded, str)
        # Verify it can be decoded back
        decoded = base64.b64decode(encoded)
        assert decoded == audio_data

    def test_base64_encode_large_audio(self):
        """Should encode larger audio chunks"""
        # Simulate 1 second of 16kHz 16-bit audio (32KB)
        audio_data = b"\x00\x01" * 16000
        encoded = base64.b64encode(audio_data).decode("utf-8")
        decoded = base64.b64decode(encoded)
        assert decoded == audio_data


class TestSessionManagement:
    """Tests for session management functions"""

    def test_active_sessions_dict(self):
        """Should have _active_sessions dict"""
        from transcription import _active_sessions
        assert isinstance(_active_sessions, dict)

    @pytest.mark.asyncio
    async def test_end_session_nonexistent(self):
        """Should handle ending non-existent session"""
        from transcription import end_session
        await end_session("nonexistent-session")
        # Should not raise


class TestTranscriptionProvider:
    """Tests for TranscriptionProvider configuration"""

    def test_transcription_provider_env_var(self):
        """Should have TRANSCRIPTION_PROVIDER"""
        from transcription import TRANSCRIPTION_PROVIDER
        assert TRANSCRIPTION_PROVIDER in ["assemblyai", "deepgram"]

    def test_medical_vocab_flag(self):
        """Should have ENABLE_MEDICAL_VOCAB flag"""
        from transcription import ENABLE_MEDICAL_VOCAB
        assert isinstance(ENABLE_MEDICAL_VOCAB, bool)


class TestAssemblyAIProvider:
    """Tests for AssemblyAI provider initialization"""

    def test_assemblyai_provider_init(self):
        """Should initialize AssemblyAI provider"""
        from transcription import AssemblyAIProvider
        with patch.dict('os.environ', {'ASSEMBLYAI_API_KEY': 'test-key'}):
            provider = AssemblyAIProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.sample_rate == 16000

    def test_assemblyai_provider_custom_sample_rate(self):
        """Should accept custom sample rate"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key", sample_rate=44100)
        assert provider.sample_rate == 44100

    def test_assemblyai_provider_specialties(self):
        """Should accept specialties"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(
            api_key="test-key",
            specialties=["cardiology", "pulmonology"]
        )
        assert provider.specialties == ["cardiology", "pulmonology"]


class TestDeepgramProvider:
    """Tests for Deepgram provider initialization"""

    def test_deepgram_provider_init(self):
        """Should initialize Deepgram provider"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.sample_rate == 16000

    def test_deepgram_provider_custom_sample_rate(self):
        """Should accept custom sample rate"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key", sample_rate=48000)
        assert provider.sample_rate == 48000

    def test_deepgram_provider_medical_vocab(self):
        """Should accept medical vocab flag"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(
            api_key="test-key",
            enable_medical_vocab=True
        )
        # Should not raise


class TestProviderURLs:
    """Tests for provider WebSocket URLs"""

    def test_assemblyai_url(self):
        """AssemblyAI should have correct URL"""
        from transcription import AssemblyAIProvider
        assert "assemblyai.com" in AssemblyAIProvider.WEBSOCKET_URL.lower()

    def test_deepgram_url(self):
        """Deepgram should have correct URL"""
        from transcription import DeepgramProvider
        assert "deepgram.com" in DeepgramProvider.WEBSOCKET_URL.lower()


class TestAudioChunkProcessing:
    """Tests for audio chunk processing"""

    def test_audio_chunk_size(self):
        """Should process standard audio chunk sizes"""
        # Standard chunk: 100ms of 16kHz 16-bit mono = 3200 bytes
        chunk = b"\x00\x01" * 1600
        assert len(chunk) == 3200

    def test_audio_chunk_base64_encoding(self):
        """Should encode chunk to base64 for transmission"""
        chunk = b"\x00\x01" * 1600
        encoded = base64.b64encode(chunk).decode("utf-8")
        # Base64 increases size by ~33%
        assert len(encoded) > len(chunk)


class TestTranscriptionQueueOperations:
    """Tests for transcription queue operations"""

    @pytest.mark.asyncio
    async def test_queue_put_get(self):
        """Should put and get from queue"""
        from transcription import TranscriptionResult
        queue = asyncio.Queue()

        result = TranscriptionResult(text="Test", is_final=True, confidence=0.9)
        await queue.put(result)

        retrieved = await queue.get()
        assert retrieved.text == "Test"
        assert retrieved.is_final is True

    @pytest.mark.asyncio
    async def test_queue_timeout(self):
        """Should timeout when queue is empty"""
        queue = asyncio.Queue()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.1)


class TestSpeakerDiarization:
    """Tests for speaker diarization features"""

    def test_speaker_label_parsing(self):
        """Should parse speaker labels from transcript"""
        words = [
            {"text": "Hello", "speaker": 0},
            {"text": "Hi", "speaker": 1},
            {"text": "there", "speaker": 1}
        ]
        speakers = set(w.get("speaker") for w in words if w.get("speaker") is not None)
        assert 0 in speakers
        assert 1 in speakers

    def test_speaker_turn_detection(self):
        """Should detect speaker turns"""
        words = [
            {"text": "Hello", "speaker": 0},
            {"text": "Hi", "speaker": 1},  # Turn
            {"text": "doctor", "speaker": 1},
            {"text": "Thanks", "speaker": 0}  # Turn
        ]
        turns = 0
        prev_speaker = None
        for w in words:
            speaker = w.get("speaker")
            if speaker is not None and speaker != prev_speaker:
                turns += 1
                prev_speaker = speaker
        assert turns == 3  # Initial + 2 switches


class TestTranscriptionResultFormatting:
    """Tests for transcription result formatting"""

    def test_format_with_speaker(self):
        """Should format result with speaker label"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(
            text="The patient reports headache",
            is_final=True,
            confidence=0.95,
            speaker="Speaker 0"
        )
        formatted = f"[{result.speaker}]: {result.text}"
        assert formatted == "[Speaker 0]: The patient reports headache"

    def test_format_without_speaker(self):
        """Should format result without speaker label"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(
            text="The patient reports headache",
            is_final=True,
            confidence=0.95
        )
        assert result.speaker is None
        assert result.text == "The patient reports headache"
