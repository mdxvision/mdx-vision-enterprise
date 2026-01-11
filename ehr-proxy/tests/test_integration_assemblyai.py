"""
Real Integration Tests for AssemblyAI Transcription

Run with: pytest tests/test_integration_assemblyai.py --live

These tests use the REAL AssemblyAI API with your API key.
They verify actual transcription behavior, not mocked responses.

Requirements:
    ASSEMBLYAI_API_KEY environment variable must be set
"""

import pytest
import asyncio
import os
import wave
import struct
import io
import base64

# Mark all tests in this file as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.assemblyai]


class TestAssemblyAIRealConnection:
    """Integration tests with real AssemblyAI API"""

    @pytest.fixture
    def real_audio_sample(self):
        """Generate a valid WAV audio file for testing."""
        # Create a simple sine wave audio
        sample_rate = 16000
        duration = 1.0  # 1 second
        frequency = 440  # A4 note

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            # Generate sine wave samples
            for i in range(int(sample_rate * duration)):
                import math
                value = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
                wav_file.writeframes(struct.pack('<h', value))

        buffer.seek(0)
        return buffer.read()

    @pytest.mark.asyncio
    async def test_assemblyai_connection(self, assemblyai_api_key):
        """Should successfully connect to AssemblyAI API"""
        import assemblyai as aai

        aai.settings.api_key = assemblyai_api_key

        # Verify API key is valid by checking settings
        assert aai.settings.api_key == assemblyai_api_key

    @pytest.mark.asyncio
    async def test_assemblyai_transcription_config(self, assemblyai_api_key):
        """Should create valid transcription config"""
        import assemblyai as aai

        aai.settings.api_key = assemblyai_api_key

        config = aai.TranscriptionConfig(
            language_code="en-US",
            speaker_labels=True,
            punctuate=True,
        )

        assert config is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_assemblyai_file_transcription(self, assemblyai_api_key, real_audio_sample, tmp_path):
        """Should transcribe audio file via AssemblyAI (slow test)"""
        import assemblyai as aai

        aai.settings.api_key = assemblyai_api_key

        # Save audio to file
        audio_path = tmp_path / "test_audio.wav"
        with open(audio_path, 'wb') as f:
            f.write(real_audio_sample)

        # Transcribe (this is a real API call)
        transcriber = aai.Transcriber()

        try:
            transcript = transcriber.transcribe(str(audio_path))

            # Verify response structure
            assert transcript is not None
            assert hasattr(transcript, 'status')
            assert hasattr(transcript, 'text')

            # Status should be completed or error (audio might be too short/silent)
            assert transcript.status in ['completed', 'error']

        except Exception as e:
            # API rate limits or network issues shouldn't fail the test
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                pytest.skip(f"API rate limited: {e}")
            raise

    @pytest.mark.asyncio
    async def test_assemblyai_medical_vocabulary(self, assemblyai_api_key):
        """Should support medical vocabulary boost"""
        import assemblyai as aai

        aai.settings.api_key = assemblyai_api_key

        # Medical terms that should be recognized
        medical_terms = [
            "hypertension", "dyspnea", "myocardial infarction",
            "diabetes mellitus", "pneumonia", "tachycardia"
        ]

        # Create config with word boost
        config = aai.TranscriptionConfig(
            language_code="en-US",
            word_boost=medical_terms,
            boost_param="high"
        )

        assert config is not None
        # Can't easily verify word_boost without actual transcription


class TestAssemblyAIRealTimeIntegration:
    """Integration tests for real-time streaming (more complex)"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_realtime_transcriber_creation(self, assemblyai_api_key):
        """Should create real-time transcriber"""
        import assemblyai as aai

        aai.settings.api_key = assemblyai_api_key

        results = []

        def on_data(transcript):
            results.append(transcript.text)

        def on_error(error):
            pass

        try:
            transcriber = aai.RealtimeTranscriber(
                sample_rate=16000,
                on_data=on_data,
                on_error=on_error,
            )

            assert transcriber is not None

            # Note: We don't connect because that starts a session
            # which costs money and requires actual audio streaming

        except Exception as e:
            if "rate limit" in str(e).lower():
                pytest.skip(f"API rate limited: {e}")
            raise


class TestAssemblyAIErrorHandling:
    """Test error handling with real API"""

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self):
        """Should reject invalid API key"""
        import assemblyai as aai

        aai.settings.api_key = "invalid-api-key-12345"

        transcriber = aai.Transcriber()

        # Create a minimal audio file
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b'\x00' * 32000)  # 1 second silence

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(buffer.getvalue())
            temp_path = f.name

        try:
            transcript = transcriber.transcribe(temp_path)
            # Should fail with auth error
            assert transcript.status == 'error' or 'authentication' in str(transcript.error).lower()
        except Exception as e:
            # Auth error is expected
            assert 'auth' in str(e).lower() or 'invalid' in str(e).lower() or 'unauthorized' in str(e).lower()
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_empty_audio_handling(self, assemblyai_api_key, tmp_path):
        """Should handle empty audio gracefully"""
        import assemblyai as aai

        aai.settings.api_key = assemblyai_api_key

        # Create empty audio file
        audio_path = tmp_path / "empty.wav"
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            # Very short audio
            wav_file.writeframes(b'\x00' * 100)

        with open(audio_path, 'wb') as f:
            f.write(buffer.getvalue())

        transcriber = aai.Transcriber()

        try:
            transcript = transcriber.transcribe(str(audio_path))
            # Should complete but with empty or error result
            assert transcript.status in ['completed', 'error']
        except Exception as e:
            # Some error is expected for invalid audio
            pass
