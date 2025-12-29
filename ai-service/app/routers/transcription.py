"""
Real-time transcription router using AssemblyAI
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
import structlog
import asyncio
import json

from app.services.assemblyai_service import AssemblyAIService
from app.services.websocket_manager import ConnectionManager

router = APIRouter()
logger = structlog.get_logger()

# WebSocket connection manager
manager = ConnectionManager()

# Active transcription sessions
active_sessions: dict = {}


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
        
        active_sessions[request.sessionId] = {
            "service": service,
            "audio_channel_id": request.audioChannelId,
            "encounter_id": request.encounterId,
            "status": "initialized"
        }
        
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
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if "service" in session:
                await session["service"].stop()
            del active_sessions[session_id]
            
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
        
        if session_id not in active_sessions:
            await websocket.send_json({"error": "Session not initialized"})
            await websocket.close()
            return
        
        session = active_sessions[session_id]
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
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "disconnected"


@router.get("/status/{session_id}")
async def get_session_status(session_id: str):
    """Get the status of a transcription session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    return {
        "sessionId": session_id,
        "status": session.get("status", "unknown"),
        "encounterId": session.get("encounter_id")
    }
