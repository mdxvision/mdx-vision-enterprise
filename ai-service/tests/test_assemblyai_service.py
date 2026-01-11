"""
Tests for AssemblyAI Transcription Service

Integration tests with mocked AssemblyAI SDK for full coverage.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAssemblyAIServiceIntegration:
    """Integration tests for AssemblyAIService"""

    @pytest.fixture
    def mock_aai(self):
        """Mock the assemblyai module"""
        mock_module = MagicMock()
        mock_module.settings = MagicMock()
        mock_module.TranscriptionConfig = MagicMock()
        mock_module.RealtimeTranscriber = MagicMock()
        mock_module.RealtimeTranscript = MagicMock()
        mock_module.RealtimeFinalTranscript = MagicMock()
        mock_module.RealtimeError = Exception
        mock_module.RealtimeSessionOpened = MagicMock()
        return mock_module

    @pytest.fixture
    def mock_settings(self):
        """Mock settings"""
        with patch('app.services.assemblyai_service.settings') as mock:
            mock.assemblyai_api_key = "test-api-key"
            yield mock

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_service_initialization(self, mock_settings):
        """Should initialize with session ID and language"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(
                session_id="test-session-123",
                language_code="en-US"
            )

            assert service.session_id == "test-session-123"
            assert service.language_code == "en-US"
            assert service.translation_target is None
            assert service._is_streaming is False

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_service_initialization_with_translation(self, mock_settings):
        """Should initialize with translation target"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(
                session_id="test-session",
                language_code="es-ES",
                translation_target="en"
            )

            assert service.language_code == "es-ES"
            assert service.translation_target == "en"

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_start_stream(self, mock_settings):
        """Should start transcription stream"""
        import sys
        mock_aai = sys.modules['assemblyai']
        mock_transcriber = MagicMock()
        mock_aai.RealtimeTranscriber.return_value = mock_transcriber

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")
            await service.start_stream()

            mock_aai.RealtimeTranscriber.assert_called_once()
            mock_transcriber.connect.assert_called_once()
            assert service._is_streaming is True

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_start_stream_error(self, mock_settings):
        """Should handle stream start errors"""
        import sys
        mock_aai = sys.modules['assemblyai']
        mock_aai.RealtimeTranscriber.side_effect = Exception("Connection failed")

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")

            with pytest.raises(Exception, match="Connection failed"):
                await service.start_stream()

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_send_audio(self, mock_settings):
        """Should send audio data to transcriber"""
        import sys
        mock_aai = sys.modules['assemblyai']
        mock_transcriber = MagicMock()
        mock_aai.RealtimeTranscriber.return_value = mock_transcriber

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")
            await service.start_stream()

            audio_data = b'\x00\x01\x02\x03' * 1000  # 4KB of audio
            await service.send_audio(audio_data)

            mock_transcriber.stream.assert_called_once_with(audio_data)

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_send_audio_not_streaming(self, mock_settings):
        """Should not send audio when not streaming"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")
            # Don't start stream

            await service.send_audio(b'\x00\x01\x02\x03')
            # Should not raise, just silently ignore

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_stop_stream(self, mock_settings):
        """Should stop transcription stream"""
        import sys
        mock_aai = sys.modules['assemblyai']
        mock_transcriber = MagicMock()
        mock_aai.RealtimeTranscriber.return_value = mock_transcriber

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")
            await service.start_stream()
            await service.stop()

            mock_transcriber.close.assert_called_once()
            assert service._is_streaming is False

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_on_transcription_data_callback(self, mock_settings):
        """Should process transcription data callback"""
        import sys
        mock_aai = sys.modules['assemblyai']

        # Create a proper mock class for isinstance check
        class MockFinalTranscript:
            pass
        mock_aai.RealtimeFinalTranscript = MockFinalTranscript

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")

            # Create mock transcript (not final)
            mock_transcript = MagicMock()
            mock_transcript.text = "Hello world"
            mock_transcript.speaker = "Speaker 0"
            mock_transcript.confidence = 0.95
            mock_transcript.audio_start = 1000

            service._on_transcription_data(mock_transcript)

            # Check result was queued
            assert not service._results_queue.empty()

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_on_transcription_data_empty_text(self, mock_settings):
        """Should skip empty transcription text"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")

            # Create mock transcript with empty text
            mock_transcript = MagicMock()
            mock_transcript.text = ""

            service._on_transcription_data(mock_transcript)

            # Queue should be empty
            assert service._results_queue.empty()

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_on_error_callback(self, mock_settings):
        """Should handle error callback"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")

            # Should not raise
            mock_error = MagicMock()
            mock_error.__str__ = lambda self: "Test error"
            service._on_error(mock_error)

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_on_open_callback(self, mock_settings):
        """Should handle session open callback"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")

            mock_session = MagicMock()
            mock_session.session_id = "assemblyai-session-123"
            service._on_open(mock_session)
            # Should not raise

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_on_close_callback(self, mock_settings):
        """Should handle session close callback"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.aai', mock_aai):
            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")
            service._is_streaming = True

            service._on_close()

            assert service._is_streaming is False


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass"""

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_transcription_result_creation(self):
        """Should create TranscriptionResult with all fields"""
        with patch('app.services.assemblyai_service.settings') as mock_settings:
            mock_settings.assemblyai_api_key = "test"

            from app.services.assemblyai_service import TranscriptionResult

            result = TranscriptionResult(
                text="Patient reports headache",
                speaker_label="Speaker 0",
                is_final=True,
                confidence=0.95,
                offset_ms=1500
            )

            assert result.text == "Patient reports headache"
            assert result.speaker_label == "Speaker 0"
            assert result.is_final is True
            assert result.confidence == 0.95
            assert result.offset_ms == 1500

    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    def test_transcription_result_defaults(self):
        """Should use default values"""
        with patch('app.services.assemblyai_service.settings') as mock_settings:
            mock_settings.assemblyai_api_key = "test"

            from app.services.assemblyai_service import TranscriptionResult

            result = TranscriptionResult(text="Test")

            assert result.text == "Test"
            assert result.speaker_label is None
            assert result.is_final is False
            assert result.confidence is None
            assert result.offset_ms is None


class TestAsyncTranscriptionGenerator:
    """Tests for async transcription generator"""

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_get_transcriptions_yields_results(self):
        """Should yield transcription results"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.settings') as mock_settings:
            mock_settings.assemblyai_api_key = "test"

            from app.services.assemblyai_service import AssemblyAIService, TranscriptionResult

            service = AssemblyAIService(session_id="test-session")
            service._is_streaming = True

            # Add a result to queue
            test_result = TranscriptionResult(text="Hello", is_final=True)
            await service._results_queue.put(test_result)

            # Stop streaming after first result
            async def stop_after_first():
                await asyncio.sleep(0.1)
                service._is_streaming = False

            asyncio.create_task(stop_after_first())

            results = []
            async for result in service.get_transcriptions():
                results.append(result)
                break  # Only get first result

            assert len(results) == 1
            assert results[0].text == "Hello"

    @pytest.mark.asyncio
    @patch.dict('sys.modules', {'assemblyai': MagicMock()})
    async def test_get_transcriptions_handles_timeout(self):
        """Should handle queue timeout gracefully"""
        import sys
        mock_aai = sys.modules['assemblyai']

        with patch('app.services.assemblyai_service.settings') as mock_settings:
            mock_settings.assemblyai_api_key = "test"

            from app.services.assemblyai_service import AssemblyAIService

            service = AssemblyAIService(session_id="test-session")
            service._is_streaming = True

            # Stop streaming after brief delay
            async def stop_soon():
                await asyncio.sleep(0.2)
                service._is_streaming = False

            asyncio.create_task(stop_soon())

            results = []
            async for result in service.get_transcriptions():
                results.append(result)

            # Should complete without error even with no results
            assert len(results) == 0
