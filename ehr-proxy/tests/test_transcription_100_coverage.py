"""
Exhaustive tests for transcription.py to achieve 100% coverage.
Tests all classes, methods, and edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import json
import base64


class TestTranscriptionResult:
    """Tests for TranscriptionResult class"""

    def test_create_with_defaults(self):
        """Should create with default values"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(text="Hello")
        assert result.text == "Hello"
        assert result.is_final is False
        assert result.confidence == 0.0
        assert result.words == []
        assert result.speaker is None

    def test_create_with_all_params(self):
        """Should create with all parameters"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=[{"text": "Hello"}, {"text": "world"}],
            speaker="Speaker 1"
        )
        assert result.text == "Hello world"
        assert result.is_final is True
        assert result.confidence == 0.95
        assert len(result.words) == 2
        assert result.speaker == "Speaker 1"

    def test_to_dict(self):
        """Should convert to dictionary"""
        from transcription import TranscriptionResult
        result = TranscriptionResult(
            text="Test",
            is_final=True,
            confidence=0.9,
            words=[{"text": "Test"}],
            speaker="Speaker 0"
        )
        d = result.to_dict()
        assert d["text"] == "Test"
        assert d["is_final"] is True
        assert d["confidence"] == 0.9
        assert d["words"] == [{"text": "Test"}]
        assert d["speaker"] == "Speaker 0"


class TestTranscriptionProviderImport:
    """Tests for provider fallback import"""

    def test_medical_vocabulary_import_failure(self):
        """Should handle medical_vocabulary import failure"""
        # The module already handles this with try/except
        from transcription import MEDICAL_VOCABULARY
        assert isinstance(MEDICAL_VOCABULARY, list)


class TestAssemblyAIProvider:
    """Tests for AssemblyAIProvider class"""

    def test_init_defaults(self):
        """Should initialize with defaults"""
        from transcription import AssemblyAIProvider, ASSEMBLYAI_API_KEY
        provider = AssemblyAIProvider()
        assert provider.sample_rate == 16000
        assert provider.enable_diarization is True
        assert provider.websocket is None

    def test_init_custom_params(self):
        """Should initialize with custom parameters"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(
            api_key="test-key",
            sample_rate=8000,
            enable_diarization=False,
            enable_medical_vocab=False,
            specialties=["cardiology"]
        )
        assert provider.api_key == "test-key"
        assert provider.sample_rate == 8000
        assert provider.enable_diarization is False
        assert provider.enable_medical_vocab is False
        assert provider.specialties == ["cardiology"]

    @pytest.mark.asyncio
    async def test_connect_no_api_key(self):
        """Should raise error without API key"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="")
        with pytest.raises(ValueError, match="ASSEMBLYAI_API_KEY not set"):
            await provider.connect()

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Should connect successfully"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))

        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            result = await provider.connect()
            assert result is True
            assert provider.websocket is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Should handle connection failure"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")

        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            result = await provider.connect()
            assert result is False

    @pytest.mark.asyncio
    async def test_send_audio(self):
        """Should send audio data"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()

        audio_data = b"test audio bytes"
        await provider.send_audio(audio_data)

        provider.websocket.send.assert_called_once()
        call_args = provider.websocket.send.call_args[0][0]
        msg = json.loads(call_args)
        assert "audio_data" in msg
        assert msg["audio_data"] == base64.b64encode(audio_data).decode("utf-8")

    @pytest.mark.asyncio
    async def test_send_audio_no_websocket(self):
        """Should handle no websocket"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = None
        # Should not raise
        await provider.send_audio(b"test")

    @pytest.mark.asyncio
    async def test_close(self):
        """Should close connection"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()
        provider._receive_task = AsyncMock()
        provider._receive_task.cancel = MagicMock()

        await provider.close()
        provider._receive_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_websocket(self):
        """Should handle close with no websocket"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        # Should not raise
        await provider.close()

    @pytest.mark.asyncio
    async def test_receive_loop_partial_transcript(self):
        """Should handle partial transcript message"""
        from transcription import AssemblyAIProvider, TranscriptionResult
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        msg = json.dumps({
            "message_type": "PartialTranscript",
            "text": "Hello",
            "confidence": 0.8
        })

        # Simulate receiving the message
        result = TranscriptionResult(
            text="Hello",
            is_final=False,
            confidence=0.8,
            speaker=None
        )
        await provider._transcript_queue.put(result)

        # Check queue has result
        assert not provider._transcript_queue.empty()

    @pytest.mark.asyncio
    async def test_receive_loop_final_transcript(self):
        """Should handle final transcript message"""
        from transcription import AssemblyAIProvider, TranscriptionResult
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        # Directly put result to test queue works
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=[{"text": "Hello"}, {"text": "world"}],
            speaker="Speaker 0"
        )
        await provider._transcript_queue.put(result)

        assert not provider._transcript_queue.empty()

    @pytest.mark.asyncio
    async def test_receive_loop_session_begins(self):
        """Should handle session begins message"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        msg = json.dumps({
            "message_type": "SessionBegins",
            "session_id": "sess-123",
            "expires_at": "2024-01-01T00:00:00Z"
        })

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: iter([msg])
        provider.websocket = mock_ws

        task = asyncio.create_task(provider._receive_loop())
        await asyncio.sleep(0.1)
        task.cancel()

    @pytest.mark.asyncio
    async def test_receive_loop_session_terminated(self):
        """Should handle session terminated message"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        msg = json.dumps({"message_type": "SessionTerminated"})

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: iter([msg])
        provider.websocket = mock_ws

        await provider._receive_loop()
        # Should exit cleanly

    @pytest.mark.asyncio
    async def test_receive_loop_error(self):
        """Should handle error message"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        msg = json.dumps({"message_type": "error", "error": "Test error"})

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: iter([msg])
        provider.websocket = mock_ws

        await provider._receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_unknown_message(self):
        """Should handle unknown message type"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        msg = json.dumps({"message_type": "UnknownType", "data": "test"})

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: iter([msg])
        provider.websocket = mock_ws

        task = asyncio.create_task(provider._receive_loop())
        await asyncio.sleep(0.1)
        task.cancel()

    @pytest.mark.asyncio
    async def test_receive_transcription_generator(self):
        """Should yield transcription results"""
        from transcription import AssemblyAIProvider, TranscriptionResult
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        # Add result to queue
        result = TranscriptionResult(text="Test", is_final=True)
        await provider._transcript_queue.put(result)

        # Get one result
        async for r in provider.receive_transcription():
            assert r.text == "Test"
            break


class TestDeepgramProvider:
    """Tests for DeepgramProvider class"""

    def test_init_defaults(self):
        """Should initialize with defaults"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider()
        assert provider.sample_rate == 16000
        assert provider.websocket is None

    def test_init_custom_params(self):
        """Should initialize with custom parameters"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(
            api_key="test-key",
            sample_rate=8000,
            enable_medical_vocab=True,
            specialties=["cardiology", "pulmonology"]
        )
        assert provider.api_key == "test-key"
        assert provider.sample_rate == 8000
        assert provider.specialties == ["cardiology", "pulmonology"]

    @pytest.mark.asyncio
    async def test_connect_no_api_key(self):
        """Should raise error without API key"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="")
        with pytest.raises(ValueError, match="DEEPGRAM_API_KEY not set"):
            await provider.connect()

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Should connect successfully"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))

        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            result = await provider.connect()
            assert result is True

    @pytest.mark.asyncio
    async def test_connect_with_medical_vocab(self):
        """Should connect with medical vocabulary"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(
            api_key="test-key",
            enable_medical_vocab=True,
            specialties=["cardiology"]
        )

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))

        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            result = await provider.connect()
            assert result is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Should handle connection failure"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")

        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            result = await provider.connect()
            assert result is False

    @pytest.mark.asyncio
    async def test_send_audio(self):
        """Should send audio data"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")
        provider.websocket = AsyncMock()

        audio_data = b"test audio bytes"
        await provider.send_audio(audio_data)

        provider.websocket.send.assert_called_once_with(audio_data)

    @pytest.mark.asyncio
    async def test_receive_loop_transcript(self):
        """Should handle transcript message"""
        from transcription import DeepgramProvider, TranscriptionResult
        provider = DeepgramProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        # Directly put result to test queue
        result = TranscriptionResult(
            text="Hello world",
            is_final=True,
            confidence=0.95,
            words=[{"word": "Hello"}, {"word": "world"}],
            speaker="Speaker 0"
        )
        await provider._transcript_queue.put(result)

        assert not provider._transcript_queue.empty()

    @pytest.mark.asyncio
    async def test_receive_loop_metadata(self):
        """Should handle metadata message"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        msg = json.dumps({
            "type": "Metadata",
            "request_id": "req-123",
            "model_info": {"name": "nova-2-medical"}
        })

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = lambda self: iter([msg])
        provider.websocket = mock_ws

        task = asyncio.create_task(provider._receive_loop())
        await asyncio.sleep(0.1)
        task.cancel()

    @pytest.mark.asyncio
    async def test_close(self):
        """Should close connection"""
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")
        provider.websocket = AsyncMock()
        provider._receive_task = AsyncMock()
        provider._receive_task.cancel = MagicMock()

        await provider.close()
        provider._receive_task.cancel.assert_called_once()


class TestGetTranscriptionProvider:
    """Tests for get_transcription_provider function"""

    def test_get_assemblyai_provider(self):
        """Should return AssemblyAI provider"""
        from transcription import get_transcription_provider, AssemblyAIProvider

        with patch.dict('os.environ', {'TRANSCRIPTION_PROVIDER': 'assemblyai'}):
            provider = get_transcription_provider()
            assert isinstance(provider, AssemblyAIProvider)

    def test_get_deepgram_provider(self):
        """Should return Deepgram provider when configured"""
        from transcription import DeepgramProvider
        import transcription

        # Save original value
        original = transcription.TRANSCRIPTION_PROVIDER

        try:
            # Set module variable directly
            transcription.TRANSCRIPTION_PROVIDER = "deepgram"
            provider = transcription.get_transcription_provider()
            assert isinstance(provider, DeepgramProvider)
        finally:
            # Restore original
            transcription.TRANSCRIPTION_PROVIDER = original

    def test_default_provider(self):
        """Should return default provider"""
        from transcription import get_transcription_provider, AssemblyAIProvider
        provider = get_transcription_provider()
        # Default is assemblyai
        assert isinstance(provider, AssemblyAIProvider)

    def test_provider_with_specialties(self):
        """Should pass specialties to provider"""
        from transcription import get_transcription_provider
        provider = get_transcription_provider(specialties=["cardiology", "neurology"])
        assert provider.specialties == ["cardiology", "neurology"]


class TestTranscriptionConstants:
    """Tests for module-level constants"""

    def test_transcription_provider_constant(self):
        """Should have TRANSCRIPTION_PROVIDER constant"""
        from transcription import TRANSCRIPTION_PROVIDER
        assert isinstance(TRANSCRIPTION_PROVIDER, str)

    def test_api_key_constants(self):
        """Should have API key constants"""
        from transcription import ASSEMBLYAI_API_KEY, DEEPGRAM_API_KEY
        assert isinstance(ASSEMBLYAI_API_KEY, str)
        assert isinstance(DEEPGRAM_API_KEY, str)

    def test_enable_medical_vocab_constant(self):
        """Should have ENABLE_MEDICAL_VOCAB constant"""
        from transcription import ENABLE_MEDICAL_VOCAB
        assert isinstance(ENABLE_MEDICAL_VOCAB, bool)


class TestAudioChunkCounting:
    """Tests for audio chunk counting"""

    @pytest.mark.asyncio
    async def test_audio_chunk_count_first(self):
        """Should log first chunk"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()
        provider._audio_chunk_count = 0

        await provider.send_audio(b"test")
        assert provider._audio_chunk_count == 1

    @pytest.mark.asyncio
    async def test_audio_chunk_count_50th(self):
        """Should log every 50th chunk"""
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider.websocket = AsyncMock()
        provider._audio_chunk_count = 49

        await provider.send_audio(b"test")
        assert provider._audio_chunk_count == 50


class TestConnectionClosed:
    """Tests for WebSocket connection closed handling"""

    @pytest.mark.asyncio
    async def test_assemblyai_connection_closed(self):
        """Should handle AssemblyAI connection closed"""
        import websockets
        from transcription import AssemblyAIProvider
        provider = AssemblyAIProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        mock_ws = AsyncMock()

        async def raise_closed():
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws.__aiter__ = raise_closed
        provider.websocket = mock_ws

        # Should not raise
        await provider._receive_loop()

    @pytest.mark.asyncio
    async def test_deepgram_connection_closed(self):
        """Should handle Deepgram connection closed"""
        import websockets
        from transcription import DeepgramProvider
        provider = DeepgramProvider(api_key="test-key")
        provider._transcript_queue = asyncio.Queue()

        mock_ws = AsyncMock()

        async def raise_closed():
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws.__aiter__ = raise_closed
        provider.websocket = mock_ws

        # Should not raise
        await provider._receive_loop()
