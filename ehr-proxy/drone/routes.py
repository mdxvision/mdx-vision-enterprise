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
