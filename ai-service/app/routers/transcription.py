"""
Real-time transcription router using AssemblyAI
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, Dict, Any
import structlog
import asyncio
import json
import time
from dataclasses import dataclass, field

from app.services.assemblyai_service import AssemblyAIService
from app.services.websocket_manager import ConnectionManager

router = APIRouter()
logger = structlog.get_logger()

# WebSocket connection manager
manager = ConnectionManager()


# ============================================================================
# TTL-Based Session Management (prevents memory leaks)
# ============================================================================

@dataclass
class SessionEntry:
    """Session wrapper with TTL tracking"""
    data: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    ttl_seconds: int = 7200  # 2 hours default

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.last_activity + self.ttl_seconds)

    def touch(self) -> None:
        self.last_activity = time.time()


class SessionStore:
    """TTL-managed session storage with automatic cleanup"""

    def __init__(self, default_ttl: int = 7200, cleanup_interval: int = 300):
        self._sessions: Dict[str, SessionEntry] = {}
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._stats = {"created": 0, "expired": 0, "removed": 0, "cleanups": 0}

    async def start(self) -> None:
        """Start background cleanup task"""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("SessionStore cleanup started", ttl=self._default_ttl)

    async def stop(self) -> None:
        """Stop cleanup and clear sessions"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        # Cleanup remaining sessions
        for sid, entry in list(self._sessions.items()):
            if "service" in entry.data:
                try:
                    await entry.data["service"].stop()
                except Exception:
                    pass
        self._sessions.clear()
        logger.info("SessionStore stopped")

    def set(self, session_id: str, data: Dict[str, Any], ttl: int = None) -> None:
        """Store session with TTL"""
        self._sessions[session_id] = SessionEntry(
            data=data,
            ttl_seconds=ttl or self._default_ttl
        )
        self._stats["created"] += 1

    def get(self, session_id: str, touch: bool = True) -> Optional[Dict[str, Any]]:
        """Get session data (extends TTL on access)"""
        entry = self._sessions.get(session_id)
        if entry is None:
            return None
        if entry.is_expired:
            self._expire_session(session_id)
            return None
        if touch:
            entry.touch()
        return entry.data

    def remove(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Remove and return session data"""
        entry = self._sessions.pop(session_id, None)
        if entry:
            self._stats["removed"] += 1
            return entry.data
        return None

    def __contains__(self, session_id: str) -> bool:
        entry = self._sessions.get(session_id)
        return entry is not None and not entry.is_expired

    @property
    def stats(self) -> Dict[str, Any]:
        return {**self._stats, "active": len(self._sessions)}

    async def _cleanup_loop(self) -> None:
        """Background cleanup of expired sessions"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error", error=str(e))

    async def _cleanup_expired(self) -> None:
        """Remove expired sessions"""
        self._stats["cleanups"] += 1
        expired = [sid for sid, e in self._sessions.items() if e.is_expired]
        for sid in expired:
            await self._expire_session_async(sid)
        if expired:
            logger.info("Cleaned up expired sessions", count=len(expired))

    def _expire_session(self, session_id: str) -> None:
        """Synchronously expire a session"""
        entry = self._sessions.pop(session_id, None)
        if entry:
            self._stats["expired"] += 1

    async def _expire_session_async(self, session_id: str) -> None:
        """Async expire with cleanup callback"""
        entry = self._sessions.pop(session_id, None)
        if entry:
            self._stats["expired"] += 1
            if "service" in entry.data:
                try:
                    await entry.data["service"].stop()
                except Exception as e:
                    logger.error("Error stopping expired session", session_id=session_id, error=str(e))


# Global session store (replaces plain dict)
active_sessions = SessionStore(default_ttl=7200, cleanup_interval=300)


class TranscriptionStartRequest(BaseModel):
    sessionId: str
    audioChannelId: str
    languageCode: str = "en-US"
    translationTarget: Optional[str] = None
    encounterId: Optional[str] = None


class TranscriptionResult(BaseModel):
    sessionId: str
    text: str
    speakerLabel: Optional[str] = None
    isFinal: bool = False
    confidence: Optional[float] = None
    offsetMs: Optional[int] = None


@router.on_event("startup")
async def startup_session_store():
    """Start the session store cleanup task on app startup"""
    await active_sessions.start()


@router.on_event("shutdown")
async def shutdown_session_store():
    """Stop the session store on app shutdown"""
    await active_sessions.stop()


@router.post("/start")
async def start_transcription(request: TranscriptionStartRequest):
    """Initialize a new transcription session"""
    try:
        logger.info("Starting transcription session",
                   session_id=request.sessionId,
                   language=request.languageCode)

        # Initialize AssemblyAI service for this session
        service = AssemblyAIService(
            session_id=request.sessionId,
            language_code=request.languageCode,
            translation_target=request.translationTarget
        )

        # Store with TTL-based management
        active_sessions.set(request.sessionId, {
            "service": service,
            "audio_channel_id": request.audioChannelId,
            "encounter_id": request.encounterId,
            "status": "initialized"
        })

        return {
            "status": "initialized",
            "sessionId": request.sessionId,
            "audioChannelId": request.audioChannelId,
            "websocketUrl": f"/v1/transcription/ws/{request.sessionId}"
        }

    except Exception as e:
        logger.error("Failed to start transcription", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{session_id}")
async def stop_transcription(session_id: str):
    """Stop a transcription session"""
    try:
        session = active_sessions.remove(session_id)
        if session and "service" in session:
            await session["service"].stop()

        logger.info("Transcription session stopped", session_id=session_id)
        return {"status": "stopped", "sessionId": session_id}

    except Exception as e:
        logger.error("Failed to stop transcription", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{session_id}")
async def websocket_transcription(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio streaming and transcription"""
    await manager.connect(websocket, session_id)

    try:
        logger.info("WebSocket connected for transcription", session_id=session_id)

        session = active_sessions.get(session_id)
        if session is None:
            await websocket.send_json({"error": "Session not initialized"})
            await websocket.close()
            return

        service: AssemblyAIService = session["service"]

        # Start the transcription stream
        await service.start_stream()
        session["status"] = "streaming"

        # Handle incoming audio data
        async def receive_audio():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    await service.send_audio(data)
                    # Touch session on activity to extend TTL
                    active_sessions.get(session_id, touch=True)
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", session_id=session_id)

        # Handle outgoing transcription results
        async def send_transcriptions():
            try:
                async for result in service.get_transcriptions():
                    await manager.send_to_session(session_id, {
                        "type": "transcription",
                        "sessionId": session_id,
                        "text": result.text,
                        "speakerLabel": result.speaker_label,
                        "isFinal": result.is_final,
                        "confidence": result.confidence,
                        "offsetMs": result.offset_ms
                    })
            except Exception as e:
                logger.error("Error sending transcription", error=str(e))

        # Run both tasks concurrently
        await asyncio.gather(receive_audio(), send_transcriptions())

    except WebSocketDisconnect:
        logger.info("Client disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), session_id=session_id)
    finally:
        manager.disconnect(session_id)
        session = active_sessions.get(session_id, touch=False)
        if session:
            session["status"] = "disconnected"


@router.get("/status/{session_id}")
async def get_session_status(session_id: str):
    """Get the status of a transcription session"""
    session = active_sessions.get(session_id, touch=False)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "sessionId": session_id,
        "status": session.get("status", "unknown"),
        "encounterId": session.get("encounter_id")
    }


@router.get("/stats")
async def get_session_stats():
    """Get session store statistics (for monitoring)"""
    return active_sessions.stats
