"""
Drone Voice Control - Adapter Interface & Implementations
Abstract adapter interface with Mock, MAVLink, and DJI stubs.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set
from .models import DroneIntent, ParsedSlots, DroneCapability


# ═══════════════════════════════════════════════════════════════════════════
# CAPABILITY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

class CapabilitySet:
    """Standard capability categories."""
    FLIGHT = "flight"  # takeoff, land, hover, return_home, stop
    MOVEMENT = "movement"  # move directions
    ROTATION = "rotation"  # yaw left/right
    CAMERA = "camera"  # record, photo
    ZOOM = "zoom"  # zoom in/out/set/reset
    SPEED = "speed"  # speed control
    STATUS = "status"  # battery, altitude, signal, position


# Intent to capability mapping
INTENT_CAPABILITY_MAP = {
    DroneIntent.TAKEOFF: CapabilitySet.FLIGHT,
    DroneIntent.LAND: CapabilitySet.FLIGHT,
    DroneIntent.HOVER: CapabilitySet.FLIGHT,
    DroneIntent.RETURN_HOME: CapabilitySet.FLIGHT,
    DroneIntent.STOP: CapabilitySet.FLIGHT,

    DroneIntent.MOVE_LEFT: CapabilitySet.MOVEMENT,
    DroneIntent.MOVE_RIGHT: CapabilitySet.MOVEMENT,
    DroneIntent.MOVE_FORWARD: CapabilitySet.MOVEMENT,
    DroneIntent.MOVE_BACK: CapabilitySet.MOVEMENT,
    DroneIntent.MOVE_UP: CapabilitySet.MOVEMENT,
    DroneIntent.MOVE_DOWN: CapabilitySet.MOVEMENT,

    DroneIntent.YAW_LEFT: CapabilitySet.ROTATION,
    DroneIntent.YAW_RIGHT: CapabilitySet.ROTATION,

    DroneIntent.RECORD_START: CapabilitySet.CAMERA,
    DroneIntent.RECORD_STOP: CapabilitySet.CAMERA,
    DroneIntent.PHOTO_CAPTURE: CapabilitySet.CAMERA,

    DroneIntent.ZOOM_IN: CapabilitySet.ZOOM,
    DroneIntent.ZOOM_OUT: CapabilitySet.ZOOM,
    DroneIntent.ZOOM_SET: CapabilitySet.ZOOM,
    DroneIntent.ZOOM_RESET: CapabilitySet.ZOOM,

    DroneIntent.SPEED_UP: CapabilitySet.SPEED,
    DroneIntent.SLOW_DOWN: CapabilitySet.SPEED,
    DroneIntent.SPEED_SET: CapabilitySet.SPEED,

    DroneIntent.BATTERY: CapabilitySet.STATUS,
    DroneIntent.ALTITUDE: CapabilitySet.STATUS,
    DroneIntent.SIGNAL: CapabilitySet.STATUS,
    DroneIntent.POSITION: CapabilitySet.STATUS,
}


# ═══════════════════════════════════════════════════════════════════════════
# ABSTRACT ADAPTER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

class DroneAdapter(ABC):
    """
    Abstract interface for drone control adapters.

    Implementations should handle communication with specific drone platforms
    (MAVLink/ArduPilot, DJI SDK, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        pass

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Adapter type identifier (mock, mavlink, dji)."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if drone is connected."""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, DroneCapability]:
        """Get supported capabilities."""
        pass

    @abstractmethod
    def supports_intent(self, intent: DroneIntent) -> bool:
        """Check if adapter supports a specific intent."""
        pass

    @abstractmethod
    async def execute(
        self,
        intent: DroneIntent,
        slots: ParsedSlots
    ) -> Dict[str, Any]:
        """
        Execute a drone command.

        Args:
            intent: The command intent
            slots: Extracted slot values

        Returns:
            Dict with execution results (success, message, data)
        """
        pass

    def get_supported_intents(self) -> Set[DroneIntent]:
        """Get all supported intents based on capabilities."""
        supported = set()
        caps = self.get_capabilities()
        for intent, cap_name in INTENT_CAPABILITY_MAP.items():
            if cap_name in caps and caps[cap_name].supported:
                supported.add(intent)
        return supported


# ═══════════════════════════════════════════════════════════════════════════
# MOCK ADAPTER (for development/testing)
# ═══════════════════════════════════════════════════════════════════════════

class MockDroneAdapter(DroneAdapter):
    """
    Mock adapter for development and testing.
    Simulates all drone operations without real hardware.
    """

    def __init__(self, connected: bool = True):
        self._connected = connected
        self._is_flying = False
        self._altitude = 0.0
        self._battery = 85.0
        self._recording = False
        self._zoom_level = 1.0
        self._speed = "normal"
        self._position = {"lat": 37.7749, "lon": -122.4194}

    @property
    def name(self) -> str:
        return "Mock Drone Simulator"

    @property
    def adapter_type(self) -> str:
        return "mock"

    def is_connected(self) -> bool:
        return self._connected

    def get_capabilities(self) -> Dict[str, DroneCapability]:
        return {
            CapabilitySet.FLIGHT: DroneCapability(
                supported=True,
                description="Takeoff, land, hover, return home, emergency stop"
            ),
            CapabilitySet.MOVEMENT: DroneCapability(
                supported=True,
                description="Move in all directions with distance control"
            ),
            CapabilitySet.ROTATION: DroneCapability(
                supported=True,
                description="Yaw rotation with degree control"
            ),
            CapabilitySet.CAMERA: DroneCapability(
                supported=True,
                description="Video recording and photo capture"
            ),
            CapabilitySet.ZOOM: DroneCapability(
                supported=True,
                description="Optical zoom control"
            ),
            CapabilitySet.SPEED: DroneCapability(
                supported=True,
                description="Speed adjustment"
            ),
            CapabilitySet.STATUS: DroneCapability(
                supported=True,
                description="Battery, altitude, signal, position queries"
            ),
        }

    def supports_intent(self, intent: DroneIntent) -> bool:
        cap_name = INTENT_CAPABILITY_MAP.get(intent)
        if not cap_name:
            return False
        caps = self.get_capabilities()
        return cap_name in caps and caps[cap_name].supported

    async def execute(
        self,
        intent: DroneIntent,
        slots: ParsedSlots
    ) -> Dict[str, Any]:
        """Execute mock drone command."""
        if not self._connected:
            return {"success": False, "message": "Drone not connected"}

        # Flight commands
        if intent == DroneIntent.TAKEOFF:
            self._is_flying = True
            self._altitude = 10.0
            return {"success": True, "message": "Takeoff complete", "altitude": self._altitude}

        if intent == DroneIntent.LAND:
            self._is_flying = False
            self._altitude = 0.0
            return {"success": True, "message": "Landing complete"}

        if intent == DroneIntent.HOVER:
            return {"success": True, "message": "Hovering in place"}

        if intent == DroneIntent.RETURN_HOME:
            self._is_flying = False
            self._altitude = 0.0
            return {"success": True, "message": "Returned home"}

        if intent == DroneIntent.STOP:
            return {"success": True, "message": "Emergency stop executed"}

        # Movement commands
        if intent in {
            DroneIntent.MOVE_LEFT, DroneIntent.MOVE_RIGHT,
            DroneIntent.MOVE_FORWARD, DroneIntent.MOVE_BACK,
            DroneIntent.MOVE_UP, DroneIntent.MOVE_DOWN
        }:
            direction = intent.value.replace("MOVE_", "").lower()
            distance = slots.distance or 1.0
            unit = slots.unit.value if slots.unit else "meters"
            if intent == DroneIntent.MOVE_UP:
                self._altitude += distance
            elif intent == DroneIntent.MOVE_DOWN:
                self._altitude = max(0, self._altitude - distance)
            return {
                "success": True,
                "message": f"Moved {direction} {distance} {unit}",
                "altitude": self._altitude
            }

        # Rotation commands
        if intent in {DroneIntent.YAW_LEFT, DroneIntent.YAW_RIGHT}:
            direction = "left" if intent == DroneIntent.YAW_LEFT else "right"
            degrees = slots.degrees or 90.0
            return {"success": True, "message": f"Rotated {direction} {degrees} degrees"}

        # Camera commands
        if intent == DroneIntent.RECORD_START:
            self._recording = True
            return {"success": True, "message": "Recording started"}

        if intent == DroneIntent.RECORD_STOP:
            self._recording = False
            return {"success": True, "message": "Recording stopped"}

        if intent == DroneIntent.PHOTO_CAPTURE:
            return {"success": True, "message": "Photo captured", "filename": "photo_001.jpg"}

        # Zoom commands
        if intent == DroneIntent.ZOOM_IN:
            self._zoom_level = min(10.0, self._zoom_level + 1.0)
            return {"success": True, "message": f"Zoomed in to {self._zoom_level}x"}

        if intent == DroneIntent.ZOOM_OUT:
            self._zoom_level = max(1.0, self._zoom_level - 1.0)
            return {"success": True, "message": f"Zoomed out to {self._zoom_level}x"}

        if intent == DroneIntent.ZOOM_SET:
            self._zoom_level = slots.zoom_level or 1.0
            return {"success": True, "message": f"Zoom set to {self._zoom_level}x"}

        if intent == DroneIntent.ZOOM_RESET:
            self._zoom_level = 1.0
            return {"success": True, "message": "Zoom reset to 1x"}

        # Speed commands
        if intent == DroneIntent.SPEED_UP:
            self._speed = "fast"
            return {"success": True, "message": "Speed increased"}

        if intent == DroneIntent.SLOW_DOWN:
            self._speed = "slow"
            return {"success": True, "message": "Speed decreased"}

        if intent == DroneIntent.SPEED_SET:
            if slots.speed_level:
                self._speed = slots.speed_level.value
            elif slots.speed_numeric:
                self._speed = f"{slots.speed_numeric} m/s"
            return {"success": True, "message": f"Speed set to {self._speed}"}

        # Status queries
        if intent == DroneIntent.BATTERY:
            return {"success": True, "message": f"Battery: {self._battery}%", "battery": self._battery}

        if intent == DroneIntent.ALTITUDE:
            return {"success": True, "message": f"Altitude: {self._altitude}m", "altitude": self._altitude}

        if intent == DroneIntent.SIGNAL:
            return {"success": True, "message": "Signal: Strong (95%)", "signal": 95}

        if intent == DroneIntent.POSITION:
            return {
                "success": True,
                "message": f"Position: {self._position['lat']}, {self._position['lon']}",
                "position": self._position
            }

        return {"success": False, "message": f"Unknown intent: {intent}"}


# ═══════════════════════════════════════════════════════════════════════════
# MAVLINK ADAPTER STUB
# ═══════════════════════════════════════════════════════════════════════════

class MAVLinkAdapter(DroneAdapter):
    """
    MAVLink adapter stub for ArduPilot/PX4 drones.

    TODO: Implement real MAVLink integration using pymavlink.
    - Connect via serial or UDP
    - Send MAVLink commands (SET_MODE, NAV_TAKEOFF, etc.)
    - Handle telemetry streams
    """

    def __init__(self, connection_string: Optional[str] = None):
        self._connection_string = connection_string
        self._connected = False

    @property
    def name(self) -> str:
        return "MAVLink (ArduPilot/PX4)"

    @property
    def adapter_type(self) -> str:
        return "mavlink"

    def is_connected(self) -> bool:
        return self._connected

    def get_capabilities(self) -> Dict[str, DroneCapability]:
        # MAVLink typically supports all flight capabilities
        # Camera/zoom depends on specific hardware
        return {
            CapabilitySet.FLIGHT: DroneCapability(
                supported=True,
                description="Full flight control via MAVLink"
            ),
            CapabilitySet.MOVEMENT: DroneCapability(
                supported=True,
                description="Position and velocity control"
            ),
            CapabilitySet.ROTATION: DroneCapability(
                supported=True,
                description="Yaw control via attitude commands"
            ),
            CapabilitySet.CAMERA: DroneCapability(
                supported=False,  # Depends on gimbal/camera setup
                description="Camera control requires compatible gimbal"
            ),
            CapabilitySet.ZOOM: DroneCapability(
                supported=False,
                description="Zoom not supported via MAVLink"
            ),
            CapabilitySet.SPEED: DroneCapability(
                supported=True,
                description="Speed control via parameters"
            ),
            CapabilitySet.STATUS: DroneCapability(
                supported=True,
                description="Full telemetry via MAVLink"
            ),
        }

    def supports_intent(self, intent: DroneIntent) -> bool:
        cap_name = INTENT_CAPABILITY_MAP.get(intent)
        if not cap_name:
            return False
        caps = self.get_capabilities()
        return cap_name in caps and caps[cap_name].supported

    async def execute(
        self,
        intent: DroneIntent,
        slots: ParsedSlots
    ) -> Dict[str, Any]:
        """
        Execute MAVLink command.

        TODO: Implement actual MAVLink protocol:
        - TAKEOFF: MAV_CMD_NAV_TAKEOFF
        - LAND: MAV_CMD_NAV_LAND
        - MOVE: MAV_CMD_NAV_WAYPOINT or SET_POSITION_TARGET
        - etc.
        """
        return {
            "success": False,
            "message": "MAVLink adapter not implemented. This is a stub."
        }


# ═══════════════════════════════════════════════════════════════════════════
# DJI ADAPTER STUB
# ═══════════════════════════════════════════════════════════════════════════

class DJIAdapter(DroneAdapter):
    """
    DJI SDK adapter stub for DJI drones.

    TODO: Implement real DJI integration using DJI Mobile SDK.
    - Requires DJI developer account
    - Use DJI MSDK for Android/iOS
    - Or DJI Onboard SDK for embedded systems
    """

    def __init__(self):
        self._connected = False

    @property
    def name(self) -> str:
        return "DJI Mobile SDK"

    @property
    def adapter_type(self) -> str:
        return "dji"

    def is_connected(self) -> bool:
        return self._connected

    def get_capabilities(self) -> Dict[str, DroneCapability]:
        # DJI drones typically have full capabilities
        return {
            CapabilitySet.FLIGHT: DroneCapability(
                supported=True,
                description="Full flight control via DJI SDK"
            ),
            CapabilitySet.MOVEMENT: DroneCapability(
                supported=True,
                description="Virtual stick control"
            ),
            CapabilitySet.ROTATION: DroneCapability(
                supported=True,
                description="Gimbal and aircraft rotation"
            ),
            CapabilitySet.CAMERA: DroneCapability(
                supported=True,
                description="Full camera control"
            ),
            CapabilitySet.ZOOM: DroneCapability(
                supported=True,
                description="Optical and digital zoom"
            ),
            CapabilitySet.SPEED: DroneCapability(
                supported=True,
                description="Flight speed control"
            ),
            CapabilitySet.STATUS: DroneCapability(
                supported=True,
                description="Full telemetry via SDK"
            ),
        }

    def supports_intent(self, intent: DroneIntent) -> bool:
        cap_name = INTENT_CAPABILITY_MAP.get(intent)
        if not cap_name:
            return False
        caps = self.get_capabilities()
        return cap_name in caps and caps[cap_name].supported

    async def execute(
        self,
        intent: DroneIntent,
        slots: ParsedSlots
    ) -> Dict[str, Any]:
        """
        Execute DJI SDK command.

        TODO: Implement actual DJI SDK calls.
        """
        return {
            "success": False,
            "message": "DJI adapter not implemented. This is a stub."
        }


# ═══════════════════════════════════════════════════════════════════════════
# ADAPTER FACTORY
# ═══════════════════════════════════════════════════════════════════════════

_active_adapter: Optional[DroneAdapter] = None


def get_adapter() -> DroneAdapter:
    """Get the active drone adapter."""
    global _active_adapter
    if _active_adapter is None:
        # Default to mock adapter
        _active_adapter = MockDroneAdapter()
    return _active_adapter


def set_adapter(adapter: DroneAdapter) -> None:
    """Set the active drone adapter."""
    global _active_adapter
    _active_adapter = adapter


def reset_adapter() -> None:
    """Reset to default adapter (for testing)."""
    global _active_adapter
    _active_adapter = None
