"""
Drone Voice Control - FastAPI Routes
Endpoints for parsing voice commands, executing drone actions, and querying capabilities.
"""

import os
from fastapi import APIRouter, HTTPException
from typing import Union

from .models import (
    ParseRequest, ParseResponse, ExecuteRequest, ExecuteResponse,
    CapabilitiesResponse, DisabledResponse, DroneIntent, ParsedSlots,
    ExecutionStatus
)
from .parser import parse_voice_command
from .policy import get_policy_gate
from .adapters import get_adapter

# Feature flag - default OFF for safety
DRONE_CONTROL_ENABLED = os.getenv("DRONE_CONTROL_ENABLED", "false").lower() == "true"

router = APIRouter(prefix="/api/drone", tags=["drone"])


def check_enabled() -> Union[None, DisabledResponse]:
    """Check if drone control is enabled."""
    if not DRONE_CONTROL_ENABLED:
        return DisabledResponse()
    return None


# ═══════════════════════════════════════════════════════════════════════════
# PARSE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/voice/parse",
    response_model=Union[ParseResponse, DisabledResponse],
    summary="Parse voice transcript to intent and slots",
    description="Converts a voice command transcript into structured intent and slot values."
)
async def parse_voice_transcript(request: ParseRequest) -> Union[ParseResponse, DisabledResponse]:
    """
    Parse a voice transcript into structured drone command.

    Args:
        request: ParseRequest with transcript and optional session_id

    Returns:
        ParseResponse with intent, slots, confirmation requirement, and normalized command
    """
    disabled = check_enabled()
    if disabled:
        return disabled

    result = parse_voice_command(request.transcript, request.session_id)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/voice/execute",
    response_model=Union[ExecuteResponse, DisabledResponse],
    summary="Execute a drone command",
    description="Execute a parsed drone command with optional confirmation."
)
async def execute_drone_command(request: ExecuteRequest) -> Union[ExecuteResponse, DisabledResponse]:
    """
    Execute a drone command through the active adapter.

    Handles:
    - Confirmation flow for risky commands (TAKEOFF, LAND, RETURN_HOME)
    - Immediate override for STOP
    - Rate limiting by session
    - Capability checking

    Args:
        request: ExecuteRequest with intent, slots, optional confirm flag and session_id

    Returns:
        ExecuteResponse with status, message, and optional adapter response
    """
    disabled = check_enabled()
    if disabled:
        return disabled

    # Parse intent from string
    try:
        intent = DroneIntent(request.intent.upper())
    except ValueError:
        return ExecuteResponse(
            status=ExecutionStatus.UNSUPPORTED,
            message=f"Unknown intent: {request.intent}"
        )

    # Build slots from dict
    slots = ParsedSlots(**request.slots) if request.slots else ParsedSlots()

    # Generate normalized command for logging/display
    from .parser import generate_normalized_command
    normalized = generate_normalized_command(intent, slots)

    # Get adapter and check capability
    adapter = get_adapter()
    if not adapter.is_connected():
        return ExecuteResponse(
            status=ExecutionStatus.BLOCKED,
            message="Drone not connected"
        )

    if not adapter.supports_intent(intent):
        return ExecuteResponse(
            status=ExecutionStatus.UNSUPPORTED,
            message=f"Adapter '{adapter.name}' does not support {intent.value}",
            command_executed=normalized
        )

    # Evaluate against policy gate
    session_id = request.session_id or "default"
    policy = get_policy_gate()

    status, message, pending = policy.evaluate(
        session_id=session_id,
        intent=intent,
        slots=slots,
        normalized_command=normalized,
        confirm=request.confirm
    )

    # If needs confirmation, return without executing
    if status == ExecutionStatus.NEEDS_CONFIRM:
        return ExecuteResponse(
            status=status,
            message=message,
            command_executed=normalized
        )

    # If blocked or rate limited, return error
    if status in (ExecutionStatus.BLOCKED, ExecutionStatus.RATE_LIMITED):
        return ExecuteResponse(
            status=status,
            message=message,
            command_executed=normalized
        )

    # Execute the command
    # If we got here via confirmation, use the pending state's intent/slots
    exec_intent = pending.intent if pending else intent
    exec_slots = pending.slots if pending else slots
    exec_normalized = pending.normalized_command if pending else normalized

    try:
        adapter_result = await adapter.execute(exec_intent, exec_slots)
        policy.record_command(session_id)

        return ExecuteResponse(
            status=ExecutionStatus.OK,
            message=adapter_result.get("message", "Command executed"),
            command_executed=exec_normalized,
            adapter_response=adapter_result
        )
    except Exception as e:
        return ExecuteResponse(
            status=ExecutionStatus.BLOCKED,
            message=f"Execution failed: {str(e)}",
            command_executed=exec_normalized
        )


# ═══════════════════════════════════════════════════════════════════════════
# CAPABILITIES ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/capabilities",
    response_model=Union[CapabilitiesResponse, DisabledResponse],
    summary="Get drone capabilities",
    description="Returns the capability matrix for the active drone adapter."
)
async def get_capabilities() -> Union[CapabilitiesResponse, DisabledResponse]:
    """
    Get capabilities of the active drone adapter.

    Returns:
        CapabilitiesResponse with adapter info and supported capabilities
    """
    disabled = check_enabled()
    if disabled:
        return disabled

    adapter = get_adapter()

    return CapabilitiesResponse(
        adapter_name=adapter.name,
        adapter_type=adapter.adapter_type,
        connected=adapter.is_connected(),
        capabilities=adapter.get_capabilities(),
        supported_intents=[intent.value for intent in adapter.get_supported_intents()]
    )


# ═══════════════════════════════════════════════════════════════════════════
# STATUS ENDPOINT (bonus utility)
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/status",
    summary="Get drone control status",
    description="Check if drone control is enabled and adapter is connected."
)
async def get_status():
    """Get drone control system status."""
    if not DRONE_CONTROL_ENABLED:
        return {
            "enabled": False,
            "message": "Drone voice control is disabled. Set DRONE_CONTROL_ENABLED=true to enable."
        }

    adapter = get_adapter()
    return {
        "enabled": True,
        "adapter_name": adapter.name,
        "adapter_type": adapter.adapter_type,
        "connected": adapter.is_connected()
    }


# ═══════════════════════════════════════════════════════════════════════════
# ADAPTER MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

from .adapters import MockDroneAdapter, TelloAdapter, set_adapter

@router.post(
    "/adapter/set",
    summary="Set active drone adapter",
    description="Switch between mock, tello, mavlink adapters."
)
async def set_drone_adapter(adapter_type: str, tello_ip: str = None):
    """
    Set the active drone adapter.

    Args:
        adapter_type: "mock", "tello", "mavlink", "dji"
        tello_ip: IP address for Tello (default: 192.168.10.1)
    """
    disabled = check_enabled()
    if disabled:
        return disabled

    if adapter_type == "mock":
        adapter = MockDroneAdapter()
        set_adapter(adapter)
        return {"success": True, "message": "Switched to Mock adapter", "adapter": adapter.name}

    elif adapter_type == "tello":
        adapter = TelloAdapter(tello_ip)
        connected = await adapter.connect()
        if connected:
            set_adapter(adapter)
            return {"success": True, "message": "Connected to Tello", "adapter": adapter.name}
        else:
            return {"success": False, "message": "Failed to connect to Tello. Is it powered on and WiFi connected?"}

    else:
        return {"success": False, "message": f"Unknown adapter type: {adapter_type}. Use 'mock' or 'tello'."}


@router.post(
    "/adapter/connect",
    summary="Connect to Tello drone",
    description="Initialize connection to Tello drone."
)
async def connect_tello(ip: str = "192.168.10.1"):
    """Connect to Tello drone."""
    disabled = check_enabled()
    if disabled:
        return disabled

    adapter = TelloAdapter(ip)
    connected = await adapter.connect()

    if connected:
        set_adapter(adapter)
        return {
            "success": True,
            "message": "Connected to Tello",
            "adapter": adapter.name,
            "battery": adapter._battery
        }
    else:
        return {"success": False, "message": "Connection failed. Check WiFi connection to Tello."}


@router.post(
    "/adapter/disconnect",
    summary="Disconnect from drone",
    description="Disconnect from current drone adapter."
)
async def disconnect_drone():
    """Disconnect from current drone."""
    adapter = get_adapter()

    if hasattr(adapter, 'disconnect'):
        adapter.disconnect()

    # Switch back to mock
    set_adapter(MockDroneAdapter())
    return {"success": True, "message": "Disconnected. Switched to Mock adapter."}


# ═══════════════════════════════════════════════════════════════════════════
# FACIAL RECOGNITION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class RegisterFaceRequest(BaseModel):
    name: str
    role: str = "unknown"  # patient, clinician, staff, visitor
    image_base64: Optional[str] = None
    image_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class IdentifyFaceRequest(BaseModel):
    image_base64: str

try:
    from facial_recognition import get_face_service, FaceMatch
    FACIAL_RECOGNITION_AVAILABLE = True
except ImportError:
    FACIAL_RECOGNITION_AVAILABLE = False


@router.post(
    "/faces/register",
    summary="Register a face",
    description="Register a new face for recognition (patient, clinician, staff)."
)
async def register_face(request: RegisterFaceRequest):
    """Register a face in the recognition database."""
    if not FACIAL_RECOGNITION_AVAILABLE:
        return {"success": False, "message": "Facial recognition not available. Install: pip install face-recognition opencv-python"}

    service = get_face_service()

    face_id = service.register_face(
        name=request.name,
        role=request.role,
        image_base64=request.image_base64,
        image_path=request.image_path,
        metadata=request.metadata or {}
    )

    if face_id:
        return {"success": True, "face_id": face_id, "message": f"Registered {request.name}"}
    else:
        return {"success": False, "message": "Failed to register face. Ensure image contains a clear face."}


@router.post(
    "/faces/identify",
    summary="Identify faces in image",
    description="Identify faces in a base64-encoded image."
)
async def identify_faces(request: IdentifyFaceRequest):
    """Identify faces in an image."""
    if not FACIAL_RECOGNITION_AVAILABLE:
        return {"success": False, "message": "Facial recognition not available"}

    service = get_face_service()
    matches = service.identify_from_base64(request.image_base64)

    return {
        "success": True,
        "faces": [
            {
                "name": m.name,
                "role": m.role,
                "confidence": round(m.confidence, 3),
                "bbox": m.bbox,
                "metadata": m.metadata
            }
            for m in matches
        ]
    }


@router.get(
    "/faces/list",
    summary="List registered faces",
    description="Get all registered faces in the database."
)
async def list_faces():
    """List all registered faces."""
    if not FACIAL_RECOGNITION_AVAILABLE:
        return {"success": False, "message": "Facial recognition not available"}

    service = get_face_service()
    faces = service.get_registered_faces()
    return {"success": True, "faces": faces, "count": len(faces)}


@router.delete(
    "/faces/{face_id}",
    summary="Delete a registered face",
    description="Remove a face from the recognition database."
)
async def delete_face(face_id: str):
    """Delete a registered face."""
    if not FACIAL_RECOGNITION_AVAILABLE:
        return {"success": False, "message": "Facial recognition not available"}

    service = get_face_service()
    deleted = service.delete_face(face_id)

    if deleted:
        return {"success": True, "message": f"Deleted face {face_id}"}
    else:
        return {"success": False, "message": f"Face {face_id} not found"}


# ═══════════════════════════════════════════════════════════════════════════
# VIDEO STREAM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/video/start",
    summary="Start drone video stream",
    description="Start video streaming from drone camera."
)
async def start_video_stream():
    """Start video stream from drone."""
    disabled = check_enabled()
    if disabled:
        return disabled

    adapter = get_adapter()

    if hasattr(adapter, 'start_video_stream'):
        success = adapter.start_video_stream()
        if success:
            return {"success": True, "message": "Video stream started", "url": "udp://0.0.0.0:11111"}
        else:
            return {"success": False, "message": "Failed to start video stream"}
    else:
        return {"success": False, "message": f"Adapter {adapter.name} does not support video streaming"}
