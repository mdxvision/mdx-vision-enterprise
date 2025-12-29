"""
WebSocket Connection Manager
"""

from fastapi import WebSocket
from typing import Dict, List
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections for real-time transcription"""
    
    def __init__(self):
        # Map session_id to list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        self.active_connections[session_id].append(websocket)
        logger.info("WebSocket connected", 
                   session_id=session_id, 
                   total_connections=len(self.active_connections[session_id]))
    
    def disconnect(self, session_id: str, websocket: WebSocket = None):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            if websocket:
                try:
                    self.active_connections[session_id].remove(websocket)
                except ValueError:
                    pass
            
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        logger.info("WebSocket disconnected", session_id=session_id)
    
    async def send_to_session(self, session_id: str, message: dict):
        """Send a message to all connections in a session"""
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("Failed to send message", error=str(e))
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(session_id, conn)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connections"""
        for session_id in self.active_connections:
            await self.send_to_session(session_id, message)
