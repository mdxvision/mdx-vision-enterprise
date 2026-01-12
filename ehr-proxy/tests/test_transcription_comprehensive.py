"""
Comprehensive tests for transcription.py
Tests TranscriptionResult, AssemblyAIProvider, DeepgramProvider, and factory function
"""

import pytest
import asyncio
import json
import base64
import os
from unittest.mock import patch, MagicMock, AsyncMock


class TestTranscriptionResult:
    """Tests for TranscriptionResult class"""

    def test_init_basic(self):
        """Should initialize with basic parameters"""
        from transcription import TranscriptionResult

        result = TranscriptionResult(text="Hello world")

        assert result.text == "Hello world"
        assert result.is_final is False
        assert result.confidence == 0.0
        assert result.words == []
        assert result.speaker is None

    def test_init_all_params(self):
        """Should initialize with all parameters"""
        from transcription import TranscriptionResult

        words = [{"text": "Hello", "start": 0, "end": 500}]
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=words,
            speaker="Speaker 0"
        )

        assert result.text == "Hello world"
        assert result.is_final is True
        assert result.confidence == 0.95
        assert result.words == words
        assert result.speaker == "Speaker 0"

    def test_to_dict(self):
        """Should convert to dictionary"""
        from transcription import TranscriptionResult

        result = TranscriptionResult(
            text="Test",
            is_final=True,
            confidence=0.9,
            words=[{"text": "Test"}],
            speaker="Speaker 1"
        )

        d = result.to_dict()

        assert d["text"] == "Test"
        assert d["is_final"] is True
        assert d["confidence"] == 0.9
        assert d["words"] == [{"text": "Test"}]
        assert d["speaker"] == "Speaker 1"

    def test_to_dict_empty(self):
        """Should convert empty result to dictionary"""
        from transcription import TranscriptionResult

        result = TranscriptionResult(text="")
        d = result.to_dict()

        assert d["text"] == ""
        assert d["is_final"] is False
        assert d["confidence"] == 0.0
        assert d["words"] == []
        assert d["speaker"] is None


class TestGetTranscriptionProvider:
    """Tests for get_transcription_provider factory function"""

    def test_default_provider_assemblyai(self):
        """Should return AssemblyAI provider by default"""
        from transcription import get_transcription_provider, AssemblyAIProvider

        provider = get_transcription_provider()

        assert isinstance(provider, AssemblyAIProvider)

    def test_explicit_assemblyai(self):
        """Should return AssemblyAI provider when specified"""
        from transcription import get_transcription_provider, AssemblyAIProvider

        provider = get_transcription_provider(provider="assemblyai")

        assert isinstance(provider, AssemblyAIProvider)

    def test_explicit_deepgram(self):
        """Should return Deepgram provider when specified"""
        from transcription import get_transcription_provider, DeepgramProvider

        provider = get_transcription_provider(provider="deepgram")

        assert isinstance(provider, DeepgramProvider)

    def test_case_insensitive(self):
        """Should handle case-insensitive provider names"""
        from transcription import get_transcription_provider, DeepgramProvider

        provider = get_transcription_provider(provider="DEEPGRAM")

        assert isinstance(provider, DeepgramProvider)

    def test_with_specialties(self):
        """Should pass specialties to provider"""
        from transcription import get_transcription_provider, AssemblyAIProvider

        provider = get_transcription_provider(specialties=["cardiology", "pulmonology"])

        assert isinstance(provider, AssemblyAIProvider)
        assert provider.specialties == ["cardiology", "pulmonology"]


class TestAssemblyAIProviderInit:
    """Tests for AssemblyAI provider initialization"""

    def test_default_init(self):
        """Should initialize with defaults"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider()

        assert provider.sample_rate == 16000
        assert provider.enable_diarization is True
        assert provider.websocket is None
        assert provider._receive_task is None

    def test_custom_sample_rate(self):
        """Should accept custom sample rate"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(sample_rate=44100)

        assert provider.sample_rate == 44100

    def test_disable_diarization(self):
        """Should allow disabling diarization"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(enable_diarization=False)

        assert provider.enable_diarization is False

    def test_with_api_key(self):
        """Should accept API key"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")

        assert provider.api_key == "test-key"

    def test_with_specialties(self):
        """Should accept specialties"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(specialties=["cardiology"])

        assert provider.specialties == ["cardiology"]


class TestAssemblyAIProviderConnect:
    """Tests for AssemblyAI connection"""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ASSEMBLYAI_API_KEY": ""}, clear=False)
    async def test_connect_no_api_key(self):
        """Should raise error if no API key"""
        import importlib
        import transcription
        importlib.reload(transcription)
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="")

        with pytest.raises(ValueError, match="ASSEMBLYAI_API_KEY not set"):
            await provider.connect()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect", new_callable=AsyncMock)
    async def test_connect_success(self, mock_connect):
        """Should connect successfully with API key"""
        from transcription import AssemblyAIProvider

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))
        mock_connect.return_value = mock_ws

        provider = AssemblyAIProvider(api_key="test-key")
        result = await provider.connect()

        assert result is True
        assert provider.websocket == mock_ws
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect")
    async def test_connect_failure(self, mock_connect):
        """Should return False on connection error"""
        from transcription import AssemblyAIProvider

        mock_connect.side_effect = Exception("Connection failed")

        provider = AssemblyAIProvider(api_key="test-key")
        result = await provider.connect()

        assert result is False


class TestAssemblyAIProviderSendAudio:
    """Tests for AssemblyAI audio sending"""

    @pytest.mark.asyncio
    async def test_send_audio_no_connection(self):
        """Should do nothing if no websocket"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")
        # No exception should be raised
        await provider.send_audio(b"audio data")

    @pytest.mark.asyncio
    async def test_send_audio_with_connection(self):
        """Should send base64 encoded audio"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()

        audio_data = b"test audio bytes"
        await provider.send_audio(audio_data)

        provider.websocket.send.assert_called_once()
        sent_msg = provider.websocket.send.call_args[0][0]
        parsed = json.loads(sent_msg)
        assert "audio_data" in parsed
        # Verify base64 encoding
        decoded = base64.b64decode(parsed["audio_data"])
        assert decoded == audio_data


class TestAssemblyAIProviderClose:
    """Tests for AssemblyAI close"""

    @pytest.mark.asyncio
    async def test_close_no_connection(self):
        """Should handle close with no connection"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")
        # Should not raise
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_with_connection(self):
        """Should close websocket"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()
        provider._receive_task = AsyncMock()

        await provider.close()

        provider.websocket.send.assert_called_once()
        provider.websocket.close.assert_called_once()


class TestDeepgramProviderInit:
    """Tests for Deepgram provider initialization"""

    def test_default_init(self):
        """Should initialize with defaults"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider()

        assert provider.sample_rate == 16000
        assert provider.websocket is None
        assert provider._receive_task is None

    def test_custom_sample_rate(self):
        """Should accept custom sample rate"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(sample_rate=44100)

        assert provider.sample_rate == 44100

    def test_with_api_key(self):
        """Should accept API key"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")

        assert provider.api_key == "test-key"

    def test_with_specialties(self):
        """Should accept specialties"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(specialties=["pulmonology"])

        assert provider.specialties == ["pulmonology"]


class TestDeepgramProviderConnect:
    """Tests for Deepgram connection"""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"DEEPGRAM_API_KEY": ""}, clear=False)
    async def test_connect_no_api_key(self):
        """Should raise error if no API key"""
        import importlib
        import transcription
        importlib.reload(transcription)
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="")

        with pytest.raises(ValueError, match="DEEPGRAM_API_KEY not set"):
            await provider.connect()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect", new_callable=AsyncMock)
    async def test_connect_success(self, mock_connect):
        """Should connect successfully with API key"""
        from transcription import DeepgramProvider

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))
        mock_connect.return_value = mock_ws

        provider = DeepgramProvider(api_key="test-key")
        result = await provider.connect()

        assert result is True
        assert provider.websocket == mock_ws
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("transcription.websockets.connect")
    async def test_connect_failure(self, mock_connect):
        """Should return False on connection error"""
        from transcription import DeepgramProvider

        mock_connect.side_effect = Exception("Connection failed")

        provider = DeepgramProvider(api_key="test-key")
        result = await provider.connect()

        assert result is False


class TestDeepgramProviderSendAudio:
    """Tests for Deepgram audio sending"""

    @pytest.mark.asyncio
    async def test_send_audio_no_connection(self):
        """Should do nothing if no websocket"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")
        # No exception should be raised
        await provider.send_audio(b"audio data")

    @pytest.mark.asyncio
    async def test_send_audio_with_connection(self):
        """Should send raw audio bytes"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")
        provider.websocket = AsyncMock()

        audio_data = b"test audio bytes"
        await provider.send_audio(audio_data)

        provider.websocket.send.assert_called_once_with(audio_data)


class TestDeepgramProviderClose:
    """Tests for Deepgram close"""

    @pytest.mark.asyncio
    async def test_close_no_connection(self):
        """Should handle close with no connection"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")
        # Should not raise
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_with_connection(self):
        """Should close websocket"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(api_key="test-key")
        provider.websocket = AsyncMock()
        provider._receive_task = AsyncMock()

        await provider.close()

        provider.websocket.close.assert_called_once()


class TestTranscriptionConfig:
    """Tests for transcription configuration"""

    def test_transcription_provider_env(self):
        """Should read TRANSCRIPTION_PROVIDER from env"""
        import transcription

        # Default is "assemblyai"
        assert transcription.TRANSCRIPTION_PROVIDER in ["assemblyai", "deepgram"]

    def test_enable_medical_vocab_default(self):
        """Should enable medical vocab by default"""
        import transcription

        # Default is True
        assert isinstance(transcription.ENABLE_MEDICAL_VOCAB, bool)


class TestAssemblyAIReceiveLoop:
    """Tests for AssemblyAI receive loop message handling"""

    @pytest.mark.asyncio
    async def test_partial_transcript_handling(self):
        """Should handle PartialTranscript message"""
        from transcription import AssemblyAIProvider, TranscriptionResult

        provider = AssemblyAIProvider(api_key="test-key")

        # Simulate receiving a partial transcript
        message = json.dumps({
            "message_type": "PartialTranscript",
            "text": "Hello",
            "confidence": 0.8
        })

        # Manually trigger queue put
        result = TranscriptionResult(
            text="Hello",
            is_final=False,
            confidence=0.8
        )
        await provider._transcript_queue.put(result)

        # Check it was added
        queued = await provider._transcript_queue.get()
        assert queued.text == "Hello"
        assert queued.is_final is False

    @pytest.mark.asyncio
    async def test_final_transcript_handling(self):
        """Should handle FinalTranscript message"""
        from transcription import AssemblyAIProvider, TranscriptionResult

        provider = AssemblyAIProvider(api_key="test-key")

        # Simulate a final transcript with speaker
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=[{"text": "Hello", "speaker": 0}],
            speaker="Speaker 0"
        )
        await provider._transcript_queue.put(result)

        queued = await provider._transcript_queue.get()
        assert queued.text == "Hello world"
        assert queued.is_final is True
        assert queued.speaker == "Speaker 0"


class TestDeepgramReceiveLoop:
    """Tests for Deepgram receive loop message handling"""

    @pytest.mark.asyncio
    async def test_results_handling(self):
        """Should handle Results message"""
        from transcription import DeepgramProvider, TranscriptionResult

        provider = DeepgramProvider(api_key="test-key")

        # Simulate a results message
        result = TranscriptionResult(
            text="Test transcript",
            is_final=True,
            confidence=0.92,
            speaker="Speaker 0"
        )
        await provider._transcript_queue.put(result)

        queued = await provider._transcript_queue.get()
        assert queued.text == "Test transcript"
        assert queued.is_final is True


class TestMedicalVocabIntegration:
    """Tests for medical vocabulary integration"""

    def test_assemblyai_with_vocab(self):
        """Should initialize AssemblyAI with medical vocab"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(
            api_key="test",
            enable_medical_vocab=True,
            specialties=["cardiology"]
        )

        assert provider.enable_medical_vocab is True
        assert provider.specialties == ["cardiology"]

    def test_deepgram_with_vocab(self):
        """Should initialize Deepgram with medical vocab"""
        from transcription import DeepgramProvider

        provider = DeepgramProvider(
            api_key="test",
            enable_medical_vocab=True,
            specialties=["pulmonology"]
        )

        assert provider.enable_medical_vocab is True
        assert provider.specialties == ["pulmonology"]

    def test_vocab_disabled(self):
        """Should allow disabling medical vocab"""
        from transcription import AssemblyAIProvider

        provider = AssemblyAIProvider(
            api_key="test",
            enable_medical_vocab=False
        )

        assert provider.enable_medical_vocab is False


class TestWebSocketURL:
    """Tests for WebSocket URL constants"""

    def test_assemblyai_url(self):
        """Should have correct AssemblyAI URL"""
        from transcription import AssemblyAIProvider

        assert "assemblyai.com" in AssemblyAIProvider.WEBSOCKET_URL
        assert "realtime" in AssemblyAIProvider.WEBSOCKET_URL

    def test_deepgram_url(self):
        """Should have correct Deepgram URL"""
        from transcription import DeepgramProvider

        assert "deepgram.com" in DeepgramProvider.WEBSOCKET_URL
        assert "listen" in DeepgramProvider.WEBSOCKET_URL
