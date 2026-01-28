"""
Drone Voice Control - Pydantic Models
Data models for drone voice command parsing and execution.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class DroneIntent(str, Enum):
    """Supported drone command intents."""
    # Flight commands
    TAKEOFF = "TAKEOFF"
    LAND = "LAND"
    HOVER = "HOVER"
    RETURN_HOME = "RETURN_HOME"
    STOP = "STOP"  # Emergency stop - immediate override

    # Movement commands
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    MOVE_FORWARD = "MOVE_FORWARD"
    MOVE_BACK = "MOVE_BACK"
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"

    # Rotation commands
    YAW_LEFT = "YAW_LEFT"
    YAW_RIGHT = "YAW_RIGHT"

    # Camera commands
    RECORD_START = "RECORD_START"
    RECORD_STOP = "RECORD_STOP"
    PHOTO_CAPTURE = "PHOTO_CAPTURE"

    # Zoom commands
    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"
    ZOOM_SET = "ZOOM_SET"
    ZOOM_RESET = "ZOOM_RESET"

    # Speed commands
    SPEED_UP = "SPEED_UP"
    SLOW_DOWN = "SLOW_DOWN"
    SPEED_SET = "SPEED_SET"

    # Status queries
    BATTERY = "BATTERY"
    ALTITUDE = "ALTITUDE"
    SIGNAL = "SIGNAL"
    POSITION = "POSITION"

    # Unknown
    UNKNOWN = "UNKNOWN"


class DistanceUnit(str, Enum):
    """Supported distance units."""
    FEET = "feet"
    METERS = "meters"


class SpeedLevel(str, Enum):
    """Supported speed levels."""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class ParsedSlots(BaseModel):
    """Extracted slots from voice command."""
    distance: Optional[float] = None
    unit: Optional[DistanceUnit] = None
    degrees: Optional[float] = None
    zoom_level: Optional[float] = None
    speed_level: Optional[SpeedLevel] = None
    speed_numeric: Optional[float] = None


class ParseRequest(BaseModel):
    """Request to parse a voice transcript."""
    transcript: str = Field(..., description="Voice command transcript")
    session_id: Optional[str] = Field(None, description="Session ID for state tracking")


class ParseResponse(BaseModel):
    """Response from voice command parsing."""
    intent: DroneIntent
    slots: ParsedSlots
    requires_confirmation: bool
    normalized_command: str
    confidence: float = Field(ge=0.0, le=1.0)
    original_transcript: str


class ExecuteRequest(BaseModel):
    """Request to execute a parsed drone command."""
    intent: str = Field(..., description="The intent to execute")
    slots: Dict[str, Any] = Field(default_factory=dict, description="Slot values")
    confirm: Optional[bool] = Field(None, description="Confirmation for risky actions")
    session_id: Optional[str] = Field(None, description="Session ID for state tracking")


class ExecutionStatus(str, Enum):
    """Execution result status."""
    OK = "ok"
    BLOCKED = "blocked"
    NEEDS_CONFIRM = "needs_confirm"
    UNSUPPORTED = "unsupported"
    RATE_LIMITED = "rate_limited"
    DISABLED = "disabled"


class ExecuteResponse(BaseModel):
    """Response from command execution."""
    status: ExecutionStatus
    message: str
    command_executed: Optional[str] = None
    adapter_response: Optional[Dict[str, Any]] = None


class DroneCapability(BaseModel):
    """Single capability description."""
    supported: bool
    description: str


class CapabilitiesResponse(BaseModel):
    """Drone capabilities matrix."""
    adapter_name: str
    adapter_type: str
    connected: bool
    capabilities: Dict[str, DroneCapability]
    supported_intents: List[str]


class DisabledResponse(BaseModel):
    """Response when feature is disabled."""
    enabled: bool = False
    message: str = "Drone voice control is disabled. Set DRONE_CONTROL_ENABLED=true to enable."


class ConfirmationState(BaseModel):
    """Pending confirmation state for a session."""
    intent: DroneIntent
    slots: ParsedSlots
    normalized_command: str
    timestamp: float
