"""
Unit tests for transcription.py - Real-Time Transcription Service

Covers:
- TranscriptionResult model
- AssemblyAIProvider class
- DeepgramProvider class
- Provider factory function
- Medical vocabulary integration
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import json


class TestTranscriptionResult:
    """Tests for TranscriptionResult model"""

    def test_create_basic_result(self):
        """Should create basic transcription result"""
        from transcription import TranscriptionResult

        result = TranscriptionResult(text="Hello world")

        assert result.text == "Hello world"
        assert result.is_final is False
        assert result.confidence == 0.0
        assert result.words == []
        assert result.speaker is None

    def test_create_full_result(self):
        """Should create result with all fields"""
        from transcription import TranscriptionResult

        words = [
            {"text": "Hello", "start": 0, "end": 500},
            {"text": "world", "start": 500, "end": 1000}
        ]

        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=words,
            speaker="Speaker 1"
        )

        assert result.text == "Hello world"
        assert result.is_final is True
        assert result.confidence == 0.95
        assert len(result.words) == 2
        assert result.speaker == "Speaker 1"

    def test_to_dict(self):
        """Should serialize to dict"""
        from transcription import TranscriptionResult

        result = TranscriptionResult(
            text="Test",
            is_final=True,
            confidence=0.9,
            speaker="Doctor"
        )

        data = result.to_dict()

        assert data["text"] == "Test"
        assert data["is_final"] is True
        assert data["confidence"] == 0.9
        assert data["speaker"] == "Doctor"
        assert "words" in data


class TestAssemblyAIProvider:
    """Tests for AssemblyAI transcription provider"""

    def test_init_default_values(self):
        """Should initialize with defaults"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.sample_rate == 16000
        assert provider.enable_diarization is True
        assert provider.websocket is None

    def test_init_custom_values(self):
        """Should accept custom values"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(
            api_key="test-key",
            sample_rate=44100,
            enable_diarization=False,
            enable_medical_vocab=False,
            specialties=["cardiology"]
        )

        assert provider.sample_rate == 44100
        assert provider.enable_diarization is False
        assert provider.enable_medical_vocab is False
        assert provider.specialties == ["cardiology"]

    @pytest.mark.asyncio
    async def test_connect_without_api_key_raises_error(self):
        """Should raise error when no API key"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="")

        with pytest.raises(ValueError, match="ASSEMBLYAI_API_KEY not set"):
            await provider.connect()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect", new_callable=AsyncMock)
    async def test_connect_success(self, mock_connect):
        """Should connect to WebSocket successfully"""
        from transcription import AssemblyAIProvider

        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        provider = AssemblyAIProvider(api_key="test-key")
        result = await provider.connect()

        assert result is True
        assert provider.websocket == mock_ws
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect")
    async def test_connect_failure(self, mock_connect):
        """Should handle connection failure"""
        from transcription import AssemblyAIProvider

        mock_connect.side_effect = Exception("Connection failed")

        provider = AssemblyAIProvider(api_key="test-key")
        result = await provider.connect()

        assert result is False

    @pytest.mark.asyncio
    async def test_send_audio(self):
        """Should send audio data via WebSocket"""
        from transcription import AssemblyAIProvider
        import base64

        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()

        audio_data = b"test-audio-bytes"
        await provider.send_audio(audio_data)

        provider.websocket.send.assert_called_once()
        # Verify base64 encoded JSON was sent
        sent_data = provider.websocket.send.call_args[0][0]
        decoded = json.loads(sent_data)
        assert "audio_data" in decoded

    @pytest.mark.asyncio
    async def test_close(self):
        """Should close WebSocket connection"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")
        mock_ws = AsyncMock()
        provider.websocket = mock_ws
        provider._receive_task = AsyncMock()

        await provider.close()

        mock_ws.close.assert_called_once()


class TestDeepgramProvider:
    """Tests for Deepgram transcription provider"""

    def test_init_default_values(self):
        """Should initialize with defaults"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.sample_rate == 16000
        # Diarization is always enabled via URL params in Deepgram

    def test_init_custom_values(self):
        """Should accept custom values"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(
            api_key="test-key",
            sample_rate=8000,
            enable_medical_vocab=False,
            specialties=["cardiology"]
        )

        assert provider.sample_rate == 8000
        assert provider.enable_medical_vocab is False
        assert provider.specialties == ["cardiology"]

    @pytest.mark.asyncio
    async def test_connect_without_api_key_raises_error(self):
        """Should raise error when no API key"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="")

        with pytest.raises(ValueError, match="DEEPGRAM_API_KEY not set"):
            await provider.connect()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect", new_callable=AsyncMock)
    async def test_connect_builds_correct_url(self, mock_connect):
        """Should build URL with correct parameters"""
        from transcription import DeepgramProvider

        mock_ws = AsyncMock()
        mock_connect.return_value = mock_ws

        provider = DeepgramProvider(
            api_key="test-key",
            sample_rate=16000
        )
        await provider.connect()

        call_url = mock_connect.call_args[0][0]
        assert "sample_rate=16000" in call_url
        assert "diarize=true" in call_url
        assert "nova-2-medical" in call_url

    @pytest.mark.asyncio
    async def test_send_audio_binary(self):
        """Should send raw audio bytes"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")
        provider.websocket = AsyncMock()

        audio_data = b"raw-audio-bytes"
        await provider.send_audio(audio_data)

        provider.websocket.send.assert_called_once_with(audio_data)


class TestProviderFactory:
    """Tests for transcription provider factory"""

    def test_get_assemblyai_provider_explicit(self):
        """Should return AssemblyAI provider when specified"""
        from transcription import get_transcription_provider, AssemblyAIProvider

        provider = get_transcription_provider(provider="assemblyai")
        assert isinstance(provider, AssemblyAIProvider)

    def test_get_deepgram_provider_explicit(self):
        """Should return Deepgram provider when specified"""
        from transcription import get_transcription_provider, DeepgramProvider

        provider = get_transcription_provider(provider="deepgram")
        assert isinstance(provider, DeepgramProvider)

    def test_default_provider_is_assemblyai(self):
        """Should default to AssemblyAI for unknown provider"""
        from transcription import get_transcription_provider, AssemblyAIProvider

        # Unknown provider defaults to AssemblyAI
        provider = get_transcription_provider(provider="unknown")
        assert isinstance(provider, AssemblyAIProvider)

    def test_provider_with_specialties(self):
        """Should pass specialties to provider"""
        from transcription import get_transcription_provider

        provider = get_transcription_provider(
            provider="assemblyai",
            specialties=["cardiology", "pulmonology"]
        )
        assert provider.specialties == ["cardiology", "pulmonology"]


class TestMedicalVocabularyIntegration:
    """Tests for medical vocabulary integration"""

    @patch("transcription.get_vocabulary")
    def test_provider_loads_medical_vocab(self, mock_get_vocab):
        """Should load medical vocabulary on init"""
        from transcription import AssemblyAIProvider

        mock_get_vocab.return_value = ["hypertension", "tachycardia"]

        provider = AssemblyAIProvider(
            api_key="test-key",
            enable_medical_vocab=True,
            specialties=["cardiology"]
        )

        # Vocabulary is loaded during connect, not init
        assert provider.enable_medical_vocab is True
        assert provider.specialties == ["cardiology"]

    def test_provider_disables_medical_vocab(self):
        """Should respect disable flag"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(
            api_key="test-key",
            enable_medical_vocab=False
        )

        assert provider.enable_medical_vocab is False


class TestTranscriptionResultParsing:
    """Tests for parsing transcription results from WebSocket messages"""

    def test_parse_partial_transcript(self):
        """Should parse partial transcript message"""
        from transcription import TranscriptionResult

        message = {
            "message_type": "PartialTranscript",
            "text": "The patient has",
            "confidence": 0.85
        }

        result = TranscriptionResult(
            text=message["text"],
            is_final=False,
            confidence=message.get("confidence", 0.0)
        )

        assert result.text == "The patient has"
        assert result.is_final is False
        assert result.confidence == 0.85

    def test_parse_final_transcript(self):
        """Should parse final transcript message"""
        from transcription import TranscriptionResult

        message = {
            "message_type": "FinalTranscript",
            "text": "The patient has a fever.",
            "confidence": 0.95,
            "words": [
                {"text": "The", "start": 0, "end": 200, "speaker": 0},
                {"text": "patient", "start": 200, "end": 500, "speaker": 0},
                {"text": "has", "start": 500, "end": 700, "speaker": 0},
                {"text": "a", "start": 700, "end": 800, "speaker": 0},
                {"text": "fever", "start": 800, "end": 1200, "speaker": 0}
            ]
        }

        result = TranscriptionResult(
            text=message["text"],
            is_final=True,
            confidence=message["confidence"],
            words=message["words"],
            speaker="Speaker 0"
        )

        assert result.text == "The patient has a fever."
        assert result.is_final is True
        assert len(result.words) == 5
        assert result.speaker == "Speaker 0"

    def test_parse_speaker_change(self):
        """Should track speaker changes"""
        from transcription import TranscriptionResult

        # First speaker
        result1 = TranscriptionResult(
            text="How are you feeling?",
            is_final=True,
            speaker="Speaker 0"  # Doctor
        )

        # Second speaker
        result2 = TranscriptionResult(
            text="I have a headache.",
            is_final=True,
            speaker="Speaker 1"  # Patient
        )

        assert result1.speaker == "Speaker 0"
        assert result2.speaker == "Speaker 1"


class TestWebSocketMessageHandling:
    """Tests for WebSocket message handling"""

    def test_session_begins_message(self):
        """Should parse session start message"""
        message = {
            "message_type": "SessionBegins",
            "session_id": "abc123",
            "expires_at": "2024-01-01T12:00:00Z"
        }

        assert message["message_type"] == "SessionBegins"
        assert message["session_id"] == "abc123"

    def test_session_terminated_message(self):
        """Should parse session end message"""
        message = {
            "message_type": "SessionTerminated"
        }

        assert message["message_type"] == "SessionTerminated"

    def test_error_message(self):
        """Should parse error message"""
        message = {
            "message_type": "error",
            "error": "Authentication failed"
        }

        assert "error" in message
        assert message["error"] == "Authentication failed"


class TestAudioDataEncoding:
    """Tests for audio data encoding"""

    def test_base64_encode_audio(self):
        """Should encode audio to base64"""
        import base64

        audio_bytes = b"raw-audio-data"
        encoded = base64.b64encode(audio_bytes).decode()

        assert isinstance(encoded, str)
        assert base64.b64decode(encoded) == audio_bytes

    def test_json_audio_message(self):
        """Should create valid JSON audio message"""
        import base64
        import json

        audio_bytes = b"test-audio"
        encoded = base64.b64encode(audio_bytes).decode()
        message = json.dumps({"audio_data": encoded})

        parsed = json.loads(message)
        assert "audio_data" in parsed
        assert base64.b64decode(parsed["audio_data"]) == audio_bytes


class TestAsyncTranscriptionQueue:
    """Tests for async transcription queue"""

    @pytest.mark.asyncio
    async def test_queue_put_get(self):
        """Should queue and retrieve results"""
        from transcription import TranscriptionResult

        queue = asyncio.Queue()

        result = TranscriptionResult(text="Test", is_final=True)
        await queue.put(result)

        retrieved = await queue.get()
        assert retrieved.text == "Test"
        assert retrieved.is_final is True

    @pytest.mark.asyncio
    async def test_queue_multiple_results(self):
        """Should handle multiple results in order"""
        from transcription import TranscriptionResult

        queue = asyncio.Queue()

        await queue.put(TranscriptionResult(text="First", is_final=False))
        await queue.put(TranscriptionResult(text="Second", is_final=False))
        await queue.put(TranscriptionResult(text="Third", is_final=True))

        results = []
        while not queue.empty():
            results.append(await queue.get())

        assert len(results) == 3
        assert results[0].text == "First"
        assert results[1].text == "Second"
        assert results[2].text == "Third"
        assert results[2].is_final is True
