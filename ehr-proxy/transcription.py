"""
MDx Vision - Real-Time Transcription Service
Supports both AssemblyAI and Deepgram for medical transcription

Usage:
    provider = get_transcription_provider()
    async for transcript in provider.stream_transcription(audio_generator):
        print(transcript)
"""

import os
import asyncio
import json
import base64
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import websockets

# Configuration
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "assemblyai")  # or "deepgram"
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")


class TranscriptionResult:
    """Unified transcription result from any provider"""
    def __init__(self, text: str, is_final: bool = False, confidence: float = 0.0,
                 words: list = None, speaker: str = None):
        self.text = text
        self.is_final = is_final
        self.confidence = confidence
        self.words = words or []
        self.speaker = speaker  # For multi-speaker detection

    def to_dict(self):
        return {
            "text": self.text,
            "is_final": self.is_final,
            "confidence": self.confidence,
            "words": self.words,
            "speaker": self.speaker
        }


class TranscriptionProvider(ABC):
    """Abstract base class for transcription providers"""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the transcription service"""
        pass

    @abstractmethod
    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to the service"""
        pass

    @abstractmethod
    async def receive_transcription(self) -> AsyncGenerator[TranscriptionResult, None]:
        """Receive transcription results as they come"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection"""
        pass


class AssemblyAIProvider(TranscriptionProvider):
    """
    AssemblyAI Real-Time Transcription with Speaker Diarization
    Docs: https://www.assemblyai.com/docs/speech-to-text/streaming
    """

    WEBSOCKET_URL = "wss://api.assemblyai.com/v2/realtime/ws"

    def __init__(self, api_key: str = None, sample_rate: int = 16000, enable_diarization: bool = True):
        self.api_key = api_key or ASSEMBLYAI_API_KEY
        self.sample_rate = sample_rate
        self.enable_diarization = enable_diarization
        self.websocket = None
        self._receive_task = None
        self._transcript_queue = asyncio.Queue()
        self._current_speaker = None

    async def connect(self) -> bool:
        """Connect to AssemblyAI real-time WebSocket"""
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY not set")

        # Build URL with parameters
        params = [f"sample_rate={self.sample_rate}"]
        if self.enable_diarization:
            params.append("speaker_labels=true")

        url = f"{self.WEBSOCKET_URL}?{'&'.join(params)}"
        headers = {"Authorization": self.api_key}
        print(f"🔌 AssemblyAI: Connecting with diarization={self.enable_diarization}...")

        try:
            self.websocket = await websockets.connect(url, additional_headers=headers)
            print("✅ AssemblyAI: WebSocket connected!")
            # Start background receiver
            self._receive_task = asyncio.create_task(self._receive_loop())
            print("AssemblyAI: Connected")
            return True
        except Exception as e:
            print(f"AssemblyAI connection error: {e}")
            return False

    async def _receive_loop(self):
        """Background task to receive transcriptions"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("message_type", "")

                if msg_type == "PartialTranscript":
                    result = TranscriptionResult(
                        text=data.get("text", ""),
                        is_final=False,
                        confidence=data.get("confidence", 0.0),
                        speaker=self._current_speaker  # Use last known speaker
                    )
                    await self._transcript_queue.put(result)

                elif msg_type == "FinalTranscript":
                    words = []
                    speaker = None

                    for word in data.get("words", []):
                        word_speaker = word.get("speaker")
                        if word_speaker is not None:
                            speaker = f"Speaker {word_speaker}"
                            self._current_speaker = speaker

                        words.append({
                            "text": word.get("text", ""),
                            "start": word.get("start", 0),
                            "end": word.get("end", 0),
                            "confidence": word.get("confidence", 0.0),
                            "speaker": word_speaker
                        })

                    result = TranscriptionResult(
                        text=data.get("text", ""),
                        is_final=True,
                        confidence=data.get("confidence", 0.0),
                        words=words,
                        speaker=speaker or self._current_speaker
                    )
                    await self._transcript_queue.put(result)

                elif msg_type == "SessionBegins":
                    session_id = data.get('session_id')
                    expires = data.get('expires_at')
                    print(f"AssemblyAI session started: {session_id} (diarization enabled)")

                elif msg_type == "SessionTerminated":
                    print("AssemblyAI session ended")
                    break

        except websockets.exceptions.ConnectionClosed:
            print("AssemblyAI: Connection closed")
        except Exception as e:
            print(f"AssemblyAI receive error: {e}")

    _audio_chunk_count = 0

    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk (base64 encoded)"""
        if self.websocket:
            self._audio_chunk_count += 1
            if self._audio_chunk_count == 1:
                print(f"📤 AssemblyAI: Receiving audio (first chunk: {len(audio_data)} bytes)")
            elif self._audio_chunk_count % 50 == 0:
                print(f"📤 AssemblyAI: Sent {self._audio_chunk_count} audio chunks")
            # AssemblyAI expects base64 encoded audio
            encoded = base64.b64encode(audio_data).decode("utf-8")
            message = json.dumps({"audio_data": encoded})
            await self.websocket.send(message)

    async def receive_transcription(self) -> AsyncGenerator[TranscriptionResult, None]:
        """Yield transcription results from the queue"""
        while True:
            try:
                result = await asyncio.wait_for(
                    self._transcript_queue.get(),
                    timeout=0.1
                )
                yield result
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def close(self) -> None:
        """Close the WebSocket connection"""
        if self._receive_task:
            self._receive_task.cancel()
        if self.websocket:
            # Send terminate message
            try:
                await self.websocket.send(json.dumps({"terminate_session": True}))
                await self.websocket.close()
            except:
                pass
        print("AssemblyAI: Disconnected")


class DeepgramProvider(TranscriptionProvider):
    """
    Deepgram Nova-3 Medical Real-Time Transcription
    Docs: https://developers.deepgram.com/docs/streaming
    """

    WEBSOCKET_URL = "wss://api.deepgram.com/v1/listen"

    def __init__(self, api_key: str = None, sample_rate: int = 16000):
        self.api_key = api_key or DEEPGRAM_API_KEY
        self.sample_rate = sample_rate
        self.websocket = None
        self._receive_task = None
        self._transcript_queue = asyncio.Queue()

    async def connect(self) -> bool:
        """Connect to Deepgram real-time WebSocket"""
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not set")

        # Deepgram URL with parameters for medical model
        params = [
            f"sample_rate={self.sample_rate}",
            "encoding=linear16",
            "channels=1",
            "model=nova-2-medical",  # Medical-optimized model
            "punctuate=true",
            "interim_results=true",
            "endpointing=300",  # 300ms silence = end of utterance
            "smart_format=true",
            "diarize=true",  # Speaker detection
        ]
        url = f"{self.WEBSOCKET_URL}?{'&'.join(params)}"
        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            self.websocket = await websockets.connect(url, additional_headers=headers)
            # Start background receiver
            self._receive_task = asyncio.create_task(self._receive_loop())
            print("Deepgram Nova-3 Medical: Connected")
            return True
        except Exception as e:
            print(f"Deepgram connection error: {e}")
            return False

    async def _receive_loop(self):
        """Background task to receive transcriptions"""
        try:
            async for message in self.websocket:
                data = json.loads(message)

                # Check for transcription results
                if data.get("type") == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [])

                    if alternatives:
                        alt = alternatives[0]
                        text = alt.get("transcript", "")

                        if text:  # Only emit if there's actual text
                            is_final = data.get("is_final", False)
                            confidence = alt.get("confidence", 0.0)

                            # Extract words with timing
                            words = []
                            for word in alt.get("words", []):
                                words.append({
                                    "text": word.get("word", ""),
                                    "start": word.get("start", 0),
                                    "end": word.get("end", 0),
                                    "confidence": word.get("confidence", 0.0),
                                    "speaker": word.get("speaker", None)
                                })

                            # Get speaker from first word if diarization enabled
                            speaker = None
                            if words and words[0].get("speaker") is not None:
                                speaker = f"Speaker {words[0]['speaker']}"

                            result = TranscriptionResult(
                                text=text,
                                is_final=is_final,
                                confidence=confidence,
                                words=words,
                                speaker=speaker
                            )
                            await self._transcript_queue.put(result)

                elif data.get("type") == "Metadata":
                    print(f"Deepgram session: {data.get('request_id')}")

                elif data.get("type") == "Error":
                    print(f"Deepgram error: {data.get('message')}")

        except websockets.exceptions.ConnectionClosed:
            print("Deepgram: Connection closed")
        except Exception as e:
            print(f"Deepgram receive error: {e}")

    async def send_audio(self, audio_data: bytes) -> None:
        """Send raw audio bytes (Deepgram accepts raw PCM)"""
        if self.websocket:
            await self.websocket.send(audio_data)

    async def receive_transcription(self) -> AsyncGenerator[TranscriptionResult, None]:
        """Yield transcription results from the queue"""
        while True:
            try:
                result = await asyncio.wait_for(
                    self._transcript_queue.get(),
                    timeout=0.1
                )
                yield result
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def close(self) -> None:
        """Close the WebSocket connection"""
        if self._receive_task:
            self._receive_task.cancel()
        if self.websocket:
            try:
                # Send close message (empty bytes)
                await self.websocket.send(b'')
                await self.websocket.close()
            except:
                pass
        print("Deepgram: Disconnected")


def get_transcription_provider(provider: str = None) -> TranscriptionProvider:
    """Factory function to get the configured transcription provider"""
    provider = provider or TRANSCRIPTION_PROVIDER

    if provider.lower() == "deepgram":
        return DeepgramProvider()
    else:  # Default to AssemblyAI
        return AssemblyAIProvider()


# Transcription session manager for handling multiple concurrent sessions
class TranscriptionSession:
    """Manages a single transcription session"""

    def __init__(self, session_id: str, provider: str = None):
        self.session_id = session_id
        self.provider = get_transcription_provider(provider)
        self.is_active = False
        self.full_transcript = []  # Store all final transcripts

    async def start(self) -> bool:
        """Start the transcription session"""
        success = await self.provider.connect()
        self.is_active = success
        return success

    async def send_audio(self, audio_data: bytes):
        """Send audio to the provider"""
        if self.is_active:
            await self.provider.send_audio(audio_data)

    async def get_transcriptions(self) -> AsyncGenerator[TranscriptionResult, None]:
        """Get transcription results"""
        async for result in self.provider.receive_transcription():
            if result.is_final:
                self.full_transcript.append(result.text)
            yield result

    def get_full_transcript(self) -> str:
        """Get the complete transcript so far"""
        return " ".join(self.full_transcript)

    async def stop(self):
        """Stop the session"""
        self.is_active = False
        await self.provider.close()


# Active sessions storage
_active_sessions: dict[str, TranscriptionSession] = {}


async def create_session(session_id: str, provider: str = None) -> TranscriptionSession:
    """Create and start a new transcription session"""
    session = TranscriptionSession(session_id, provider)
    await session.start()
    _active_sessions[session_id] = session
    return session


async def get_session(session_id: str) -> Optional[TranscriptionSession]:
    """Get an existing session"""
    return _active_sessions.get(session_id)


async def end_session(session_id: str) -> Optional[str]:
    """End a session and return the full transcript"""
    session = _active_sessions.pop(session_id, None)
    if session:
        await session.stop()
        return session.get_full_transcript()
    return None
