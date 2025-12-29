"""
AssemblyAI Real-time Transcription Service
"""

import assemblyai as aai
from typing import AsyncGenerator, Optional
from dataclasses import dataclass
import structlog
import asyncio

from app.config import settings

logger = structlog.get_logger()


@dataclass
class TranscriptionResult:
    text: str
    speaker_label: Optional[str] = None
    is_final: bool = False
    confidence: Optional[float] = None
    offset_ms: Optional[int] = None


class AssemblyAIService:
    """Real-time transcription using AssemblyAI"""
    
    def __init__(
        self, 
        session_id: str,
        language_code: str = "en-US",
        translation_target: Optional[str] = None
    ):
        self.session_id = session_id
        self.language_code = language_code
        self.translation_target = translation_target
        self.transcriber = None
        self._results_queue: asyncio.Queue = asyncio.Queue()
        self._is_streaming = False
        
        # Configure AssemblyAI
        aai.settings.api_key = settings.assemblyai_api_key
    
    async def start_stream(self):
        """Start the real-time transcription stream"""
        try:
            # Configure transcription settings
            config = aai.TranscriptionConfig(
                language_code=self.language_code,
                speaker_labels=True,  # Enable speaker diarization
                punctuate=True,
                format_text=True,
            )
            
            # Create real-time transcriber
            self.transcriber = aai.RealtimeTranscriber(
                sample_rate=16000,
                on_data=self._on_transcription_data,
                on_error=self._on_error,
                on_open=self._on_open,
                on_close=self._on_close,
            )
            
            # Connect to AssemblyAI
            self.transcriber.connect()
            self._is_streaming = True
            
            logger.info("AssemblyAI stream started", session_id=self.session_id)
            
        except Exception as e:
            logger.error("Failed to start AssemblyAI stream", error=str(e))
            raise
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to the transcription stream"""
        if self.transcriber and self._is_streaming:
            self.transcriber.stream(audio_data)
    
    async def stop(self):
        """Stop the transcription stream"""
        if self.transcriber:
            self.transcriber.close()
            self._is_streaming = False
            logger.info("AssemblyAI stream stopped", session_id=self.session_id)
    
    async def get_transcriptions(self) -> AsyncGenerator[TranscriptionResult, None]:
        """Async generator for transcription results"""
        while self._is_streaming:
            try:
                result = await asyncio.wait_for(
                    self._results_queue.get(), 
                    timeout=1.0
                )
                yield result
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Error getting transcription", error=str(e))
                break
    
    def _on_transcription_data(self, transcript: aai.RealtimeTranscript):
        """Callback for transcription data"""
        if not transcript.text:
            return
        
        result = TranscriptionResult(
            text=transcript.text,
            speaker_label=getattr(transcript, 'speaker', None),
            is_final=isinstance(transcript, aai.RealtimeFinalTranscript),
            confidence=getattr(transcript, 'confidence', None),
            offset_ms=getattr(transcript, 'audio_start', None)
        )
        
        # Add to queue (non-blocking)
        try:
            self._results_queue.put_nowait(result)
        except asyncio.QueueFull:
            logger.warning("Transcription queue full, dropping result")
    
    def _on_error(self, error: aai.RealtimeError):
        """Callback for errors"""
        logger.error("AssemblyAI error", 
                    error=str(error), 
                    session_id=self.session_id)
    
    def _on_open(self, session_opened: aai.RealtimeSessionOpened):
        """Callback when session opens"""
        logger.info("AssemblyAI session opened", 
                   session_id=self.session_id,
                   assemblyai_session=session_opened.session_id)
    
    def _on_close(self):
        """Callback when session closes"""
        self._is_streaming = False
        logger.info("AssemblyAI session closed", session_id=self.session_id)
