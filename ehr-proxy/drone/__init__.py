"""
Drone Voice Control Module

Voice command parsing, safety policy enforcement, and drone adapter integration.

Usage:
    from drone import router
    app.include_router(router)

Or access components directly:
    from drone import parse_voice_command, get_adapter, get_policy_gate
"""

from .routes import router, DRONE_CONTROL_ENABLED
from .parser import (
    parse_voice_command,
    detect_intent,
    extract_slots,
    normalize_transcript,
    generate_normalized_command
)
from .policy import PolicyGate, get_policy_gate, reset_policy_gate
from .adapters import (
    DroneAdapter,
    MockDroneAdapter,
    MAVLinkAdapter,
    DJIAdapter,
    get_adapter,
    set_adapter,
    reset_adapter
)
from .models import (
    DroneIntent,
    ParsedSlots,
    ParseRequest,
    ParseResponse,
    ExecuteRequest,
    ExecuteResponse,
    ExecutionStatus,
    CapabilitiesResponse,
    DroneCapability,
    DistanceUnit,
    SpeedLevel,
    ConfirmationState,
    DisabledResponse
)

__all__ = [
    # Router
    "router",
    "DRONE_CONTROL_ENABLED",
    # Parser
    "parse_voice_command",
    "detect_intent",
    "extract_slots",
    "normalize_transcript",
    "generate_normalized_command",
    # Policy
    "PolicyGate",
    "get_policy_gate",
    "reset_policy_gate",
    # Adapters
    "DroneAdapter",
    "MockDroneAdapter",
    "MAVLinkAdapter",
    "DJIAdapter",
    "get_adapter",
    "set_adapter",
    "reset_adapter",
    # Models
    "DroneIntent",
    "ParsedSlots",
    "ParseRequest",
    "ParseResponse",
    "ExecuteRequest",
    "ExecuteResponse",
    "ExecutionStatus",
    "CapabilitiesResponse",
    "DroneCapability",
    "DistanceUnit",
    "SpeedLevel",
    "ConfirmationState",
    "DisabledResponse",
]
