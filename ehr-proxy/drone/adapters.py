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

class DJIAir3Adapter(DroneAdapter):
    """
    DJI Air 3 Adapter via Bridge App.

    Architecture:
    - Phone runs DJI Bridge App (connected to RC controller)
    - Bridge exposes HTTP API on local network
    - This adapter sends commands to the bridge

    DJI Air 3 Specs:
    - Dual cameras: Wide (24mm) + 3x Medium Tele (70mm)
    - 48MP photos, 4K/60fps HDR video
    - 46 min flight time
    - O4 video transmission (20km range)
    - Omnidirectional obstacle sensing

    Bridge App Setup:
    1. Install MDx DJI Bridge app on Android phone
    2. Connect phone to DJI RC 2 controller via USB
    3. Phone creates local WiFi hotspot or connects to same network
    4. Configure bridge_url to phone's IP

    Video Stream:
    - RTMP stream from bridge app: rtmp://<phone_ip>:1935/live/drone
    - Or WebRTC for lower latency
    """

    DEFAULT_BRIDGE_URL = "http://192.168.1.100:8080"  # Phone's IP

    def __init__(self, bridge_url: str = None):
        self._bridge_url = bridge_url or self.DEFAULT_BRIDGE_URL
        self._connected = False
        self._is_flying = False
        self._battery = 0
        self._altitude = 0
        self._zoom_level = 1.0
        self._active_camera = "wide"  # "wide" or "tele"
        self._gimbal_pitch = 0  # -90 to +30 degrees
        self._recording = False

        # Telemetry cache
        self._telemetry = {}

        # HTTP client for bridge communication
        import httpx
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "DJI Air 3"

    @property
    def adapter_type(self) -> str:
        return "dji_air3"

    def is_connected(self) -> bool:
        return self._connected

    def get_capabilities(self) -> Dict[str, DroneCapability]:
        return {
            CapabilitySet.FLIGHT: DroneCapability(
                supported=True,
                description="Takeoff, land, RTH, hover with obstacle avoidance"
            ),
            CapabilitySet.MOVEMENT: DroneCapability(
                supported=True,
                description="Virtual stick control, waypoint missions"
            ),
            CapabilitySet.ROTATION: DroneCapability(
                supported=True,
                description="Aircraft yaw + 3-axis gimbal control"
            ),
            CapabilitySet.CAMERA: DroneCapability(
                supported=True,
                description="Dual cameras: 24mm wide + 70mm 3x tele, 4K/60fps HDR"
            ),
            CapabilitySet.ZOOM: DroneCapability(
                supported=True,
                description="3x optical (tele camera) + 4x digital = 12x total"
            ),
            CapabilitySet.SPEED: DroneCapability(
                supported=True,
                description="Normal/Sport/Cine modes, 0-21 m/s"
            ),
            CapabilitySet.STATUS: DroneCapability(
                supported=True,
                description="Full telemetry: battery, GPS, altitude, signal, obstacles"
            ),
        }

    def supports_intent(self, intent: DroneIntent) -> bool:
        cap_name = INTENT_CAPABILITY_MAP.get(intent)
        if not cap_name:
            return False
        caps = self.get_capabilities()
        return cap_name in caps and caps[cap_name].supported

    async def connect(self) -> bool:
        """Connect to DJI Bridge App."""
        try:
            response = await self._client.get(f"{self._bridge_url}/api/status")
            if response.status_code == 200:
                data = response.json()
                self._connected = data.get("drone_connected", False)
                self._battery = data.get("battery", 0)

                if self._connected:
                    logger.info(f"Connected to DJI Air 3 via bridge at {self._bridge_url}")
                    return True
                else:
                    logger.warning("Bridge connected but drone not linked")
                    return False
            else:
                logger.error(f"Bridge connection failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to DJI bridge: {e}")
            return False

    async def disconnect(self):
        """Disconnect from bridge."""
        self._connected = False
        await self._client.aclose()
        logger.info("Disconnected from DJI Air 3")

    async def _send_command(self, endpoint: str, data: dict = None) -> Dict[str, Any]:
        """Send command to bridge app."""
        try:
            if data:
                response = await self._client.post(
                    f"{self._bridge_url}/api/{endpoint}",
                    json=data
                )
            else:
                response = await self._client.post(f"{self._bridge_url}/api/{endpoint}")

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"Bridge error: {response.status_code}"}

        except Exception as e:
            logger.error(f"Bridge command failed: {e}")
            return {"success": False, "message": str(e)}

    async def execute(
        self,
        intent: DroneIntent,
        slots: ParsedSlots
    ) -> Dict[str, Any]:
        """Execute DJI Air 3 command via bridge."""
        if not self._connected:
            return {"success": False, "message": "Not connected to DJI Air 3"}

        # Flight commands
        if intent == DroneIntent.TAKEOFF:
            result = await self._send_command("flight/takeoff")
            if result.get("success"):
                self._is_flying = True
            return result

        if intent == DroneIntent.LAND:
            result = await self._send_command("flight/land")
            if result.get("success"):
                self._is_flying = False
            return result

        if intent == DroneIntent.STOP:
            # Emergency brake
            result = await self._send_command("flight/emergency_stop")
            return result

        if intent == DroneIntent.HOVER:
            result = await self._send_command("flight/hover")
            return result

        if intent == DroneIntent.RETURN_HOME:
            result = await self._send_command("flight/rth")
            return result

        # Movement commands (virtual stick)
        movement_map = {
            DroneIntent.MOVE_FORWARD: {"pitch": 1, "roll": 0},
            DroneIntent.MOVE_BACK: {"pitch": -1, "roll": 0},
            DroneIntent.MOVE_LEFT: {"pitch": 0, "roll": -1},
            DroneIntent.MOVE_RIGHT: {"pitch": 0, "roll": 1},
            DroneIntent.MOVE_UP: {"throttle": 1},
            DroneIntent.MOVE_DOWN: {"throttle": -1},
        }

        if intent in movement_map:
            distance = slots.distance or 1.0
            direction = movement_map[intent]

            result = await self._send_command("flight/move", {
                "direction": direction,
                "distance_meters": distance
            })
            return result

        # Rotation commands
        if intent == DroneIntent.YAW_LEFT:
            degrees = slots.degrees or 90
            result = await self._send_command("flight/rotate", {
                "direction": "ccw",
                "degrees": degrees
            })
            return result

        if intent == DroneIntent.YAW_RIGHT:
            degrees = slots.degrees or 90
            result = await self._send_command("flight/rotate", {
                "direction": "cw",
                "degrees": degrees
            })
            return result

        # Camera commands - Air 3 has dual cameras
        if intent == DroneIntent.PHOTO_CAPTURE:
            result = await self._send_command("camera/photo", {
                "camera": self._active_camera  # wide or tele
            })
            return result

        if intent == DroneIntent.RECORD_START:
            result = await self._send_command("camera/record_start", {
                "camera": self._active_camera
            })
            if result.get("success"):
                self._recording = True
            return result

        if intent == DroneIntent.RECORD_STOP:
            result = await self._send_command("camera/record_stop")
            self._recording = False
            return result

        # Zoom commands - Air 3: 3x optical on tele, up to 12x with digital
        if intent == DroneIntent.ZOOM_IN:
            # Switch to tele camera if on wide
            if self._zoom_level < 3:
                self._active_camera = "tele"
            self._zoom_level = min(12.0, self._zoom_level + 1.0)

            result = await self._send_command("camera/zoom", {
                "level": self._zoom_level,
                "camera": "tele" if self._zoom_level >= 3 else "wide"
            })
            return result

        if intent == DroneIntent.ZOOM_OUT:
            self._zoom_level = max(1.0, self._zoom_level - 1.0)
            if self._zoom_level < 3:
                self._active_camera = "wide"

            result = await self._send_command("camera/zoom", {
                "level": self._zoom_level,
                "camera": self._active_camera
            })
            return result

        if intent == DroneIntent.ZOOM_SET:
            level = slots.zoom_level or 1.0
            self._zoom_level = max(1.0, min(12.0, level))
            self._active_camera = "tele" if self._zoom_level >= 3 else "wide"

            result = await self._send_command("camera/zoom", {
                "level": self._zoom_level,
                "camera": self._active_camera
            })
            return result

        if intent == DroneIntent.ZOOM_RESET:
            self._zoom_level = 1.0
            self._active_camera = "wide"
            result = await self._send_command("camera/zoom", {
                "level": 1.0,
                "camera": "wide"
            })
            return result

        # Speed commands
        if intent == DroneIntent.SPEED_SET:
            speed = slots.speed_numeric or 5.0  # m/s
            speed = max(1.0, min(21.0, speed))  # Air 3 max: 21 m/s
            result = await self._send_command("flight/set_speed", {"speed_ms": speed})
            return result

        if intent == DroneIntent.SPEED_UP:
            result = await self._send_command("flight/speed_mode", {"mode": "sport"})
            return result

        if intent == DroneIntent.SLOW_DOWN:
            result = await self._send_command("flight/speed_mode", {"mode": "cine"})
            return result

        # Status queries
        if intent == DroneIntent.BATTERY:
            result = await self._send_command("status/battery")
            self._battery = result.get("battery", self._battery)
            return {
                "success": True,
                "message": f"Battery: {self._battery}%",
                "battery": self._battery
            }

        if intent == DroneIntent.ALTITUDE:
            result = await self._send_command("status/altitude")
            self._altitude = result.get("altitude", self._altitude)
            return {
                "success": True,
                "message": f"Altitude: {self._altitude}m",
                "altitude": self._altitude
            }

        if intent == DroneIntent.SIGNAL:
            result = await self._send_command("status/signal")
            return {
                "success": True,
                "message": f"Signal: {result.get('signal', 'Unknown')}%",
                "signal": result.get("signal")
            }

        if intent == DroneIntent.POSITION:
            result = await self._send_command("status/gps")
            return {
                "success": True,
                "message": f"Position: {result.get('lat')}, {result.get('lon')}",
                "position": {"lat": result.get("lat"), "lon": result.get("lon")}
            }

        return {"success": False, "message": f"Unknown intent: {intent}"}

    # ═══════════════════════════════════════════════════════════════════════
    # AIR 3 SPECIFIC FEATURES
    # ═══════════════════════════════════════════════════════════════════════

    async def switch_camera(self, camera: str) -> Dict[str, Any]:
        """Switch between wide and tele cameras."""
        if camera not in ["wide", "tele"]:
            return {"success": False, "message": "Camera must be 'wide' or 'tele'"}

        result = await self._send_command("camera/switch", {"camera": camera})
        if result.get("success"):
            self._active_camera = camera
            self._zoom_level = 1.0 if camera == "wide" else 3.0
        return result

    async def set_gimbal_pitch(self, pitch: float) -> Dict[str, Any]:
        """Set gimbal pitch angle (-90 to +30 degrees)."""
        pitch = max(-90, min(30, pitch))
        result = await self._send_command("gimbal/pitch", {"angle": pitch})
        if result.get("success"):
            self._gimbal_pitch = pitch
        return result

    async def look_down(self) -> Dict[str, Any]:
        """Point camera straight down (-90°)."""
        return await self.set_gimbal_pitch(-90)

    async def look_forward(self) -> Dict[str, Any]:
        """Point camera forward (0°)."""
        return await self.set_gimbal_pitch(0)

    async def start_video_stream(self) -> Dict[str, Any]:
        """Start RTMP video stream for facial recognition."""
        result = await self._send_command("video/start_stream")
        if result.get("success"):
            return {
                "success": True,
                "message": "Video stream started",
                "stream_url": result.get("stream_url", f"rtmp://{self._bridge_url.split('//')[1].split(':')[0]}:1935/live/drone")
            }
        return result

    async def get_video_frame_base64(self) -> Optional[str]:
        """Get current video frame as base64 for facial recognition."""
        try:
            response = await self._client.get(f"{self._bridge_url}/api/video/frame")
            if response.status_code == 200:
                return response.json().get("frame_base64")
        except:
            pass
        return None

    async def track_face(self, bbox: tuple) -> Dict[str, Any]:
        """
        Use Air 3's ActiveTrack to follow a detected face.

        Args:
            bbox: (x, y, width, height) of face in frame
        """
        result = await self._send_command("tracking/start", {
            "bbox": bbox,
            "mode": "trace"  # trace, parallel, or spotlight
        })
        return result


# Alias for backwards compatibility
DJIAdapter = DJIAir3Adapter


# ═══════════════════════════════════════════════════════════════════════════
# DJI TELLO ADAPTER (Real Hardware)
# ═══════════════════════════════════════════════════════════════════════════

import socket
import threading
import time
import logging

logger = logging.getLogger(__name__)


class TelloAdapter(DroneAdapter):
    """
    DJI Tello / Tello EDU adapter using UDP commands.

    Tello Protocol:
    - Command port: 8889 (send commands, receive responses)
    - State port: 8890 (receive telemetry)
    - Video port: 11111 (receive H.264 video stream)

    Usage:
        adapter = TelloAdapter()
        await adapter.connect()
        await adapter.execute(DroneIntent.TAKEOFF, ParsedSlots())
    """

    # Tello IP when connected to its WiFi
    TELLO_IP = "192.168.10.1"
    COMMAND_PORT = 8889
    STATE_PORT = 8890
    VIDEO_PORT = 11111

    # Command timeout
    TIMEOUT = 7.0

    def __init__(self, tello_ip: str = None):
        self._tello_ip = tello_ip or self.TELLO_IP
        self._connected = False
        self._is_flying = False
        self._battery = 0
        self._altitude = 0
        self._speed = 50  # cm/s default

        # UDP sockets
        self._command_socket: Optional[socket.socket] = None
        self._state_socket: Optional[socket.socket] = None
        self._video_socket: Optional[socket.socket] = None

        # State tracking
        self._state_data = {}
        self._state_thread: Optional[threading.Thread] = None
        self._running = False

        # Response tracking
        self._last_response = None
        self._response_event = threading.Event()

    @property
    def name(self) -> str:
        return "DJI Tello EDU"

    @property
    def adapter_type(self) -> str:
        return "tello"

    def is_connected(self) -> bool:
        return self._connected

    def get_capabilities(self) -> Dict[str, DroneCapability]:
        return {
            CapabilitySet.FLIGHT: DroneCapability(
                supported=True,
                description="Takeoff, land, emergency stop"
            ),
            CapabilitySet.MOVEMENT: DroneCapability(
                supported=True,
                description="Move in all directions (20-500 cm)"
            ),
            CapabilitySet.ROTATION: DroneCapability(
                supported=True,
                description="Rotate clockwise/counter-clockwise (1-360°)"
            ),
            CapabilitySet.CAMERA: DroneCapability(
                supported=True,
                description="720p video stream, photo capture"
            ),
            CapabilitySet.ZOOM: DroneCapability(
                supported=False,
                description="Tello does not support zoom"
            ),
            CapabilitySet.SPEED: DroneCapability(
                supported=True,
                description="Speed control (10-100 cm/s)"
            ),
            CapabilitySet.STATUS: DroneCapability(
                supported=True,
                description="Battery, altitude, flight time, temperature"
            ),
        }

    def supports_intent(self, intent: DroneIntent) -> bool:
        cap_name = INTENT_CAPABILITY_MAP.get(intent)
        if not cap_name:
            return False
        caps = self.get_capabilities()
        return cap_name in caps and caps[cap_name].supported

    async def connect(self) -> bool:
        """Initialize connection to Tello."""
        try:
            # Create command socket
            self._command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._command_socket.bind(('', self.COMMAND_PORT))
            self._command_socket.settimeout(self.TIMEOUT)

            # Send SDK mode command
            response = self._send_command("command")
            if response == "ok":
                self._connected = True
                logger.info(f"Connected to Tello at {self._tello_ip}")

                # Start state receiver thread
                self._start_state_receiver()

                # Get initial battery level
                battery_response = self._send_command("battery?")
                try:
                    self._battery = int(battery_response)
                except:
                    pass

                return True
            else:
                logger.error(f"Tello connection failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Tello connection error: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from Tello."""
        self._running = False
        self._connected = False

        if self._command_socket:
            self._command_socket.close()
            self._command_socket = None
        if self._state_socket:
            self._state_socket.close()
            self._state_socket = None
        if self._video_socket:
            self._video_socket.close()
            self._video_socket = None

        logger.info("Disconnected from Tello")

    def _send_command(self, command: str) -> str:
        """Send UDP command and wait for response."""
        if not self._command_socket:
            return "error: not connected"

        try:
            logger.info(f"Tello TX: {command}")
            self._command_socket.sendto(
                command.encode('utf-8'),
                (self._tello_ip, self.COMMAND_PORT)
            )

            # Wait for response
            response, _ = self._command_socket.recvfrom(1024)
            response_str = response.decode('utf-8').strip()
            logger.info(f"Tello RX: {response_str}")
            return response_str

        except socket.timeout:
            logger.warning(f"Tello command timeout: {command}")
            return "error: timeout"
        except Exception as e:
            logger.error(f"Tello command error: {e}")
            return f"error: {e}"

    def _start_state_receiver(self):
        """Start thread to receive state data."""
        try:
            self._state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._state_socket.bind(('', self.STATE_PORT))
            self._state_socket.settimeout(1.0)

            self._running = True
            self._state_thread = threading.Thread(target=self._state_receiver_loop, daemon=True)
            self._state_thread.start()
        except Exception as e:
            logger.error(f"Failed to start state receiver: {e}")

    def _state_receiver_loop(self):
        """Background thread to receive telemetry."""
        while self._running:
            try:
                data, _ = self._state_socket.recvfrom(1024)
                state_str = data.decode('utf-8').strip()
                self._parse_state(state_str)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"State receiver error: {e}")

    def _parse_state(self, state_str: str):
        """Parse Tello state string (key:value;key:value;...)"""
        try:
            for item in state_str.split(';'):
                if ':' in item:
                    key, value = item.split(':')
                    self._state_data[key] = value

            # Update cached values
            if 'bat' in self._state_data:
                self._battery = int(self._state_data['bat'])
            if 'h' in self._state_data:
                self._altitude = int(self._state_data['h'])
        except Exception as e:
            logger.debug(f"State parse error: {e}")

    def _meters_to_cm(self, meters: float) -> int:
        """Convert meters to cm, clamped to Tello limits (20-500 cm)."""
        cm = int(meters * 100)
        return max(20, min(500, cm))

    async def execute(
        self,
        intent: DroneIntent,
        slots: ParsedSlots
    ) -> Dict[str, Any]:
        """Execute Tello command."""
        if not self._connected:
            return {"success": False, "message": "Tello not connected"}

        # Flight commands
        if intent == DroneIntent.TAKEOFF:
            response = self._send_command("takeoff")
            if response == "ok":
                self._is_flying = True
                return {"success": True, "message": "Takeoff complete"}
            return {"success": False, "message": f"Takeoff failed: {response}"}

        if intent == DroneIntent.LAND:
            response = self._send_command("land")
            if response == "ok":
                self._is_flying = False
                return {"success": True, "message": "Landing complete"}
            return {"success": False, "message": f"Landing failed: {response}"}

        if intent == DroneIntent.STOP:
            response = self._send_command("emergency")
            self._is_flying = False
            return {"success": True, "message": "Emergency stop executed"}

        if intent == DroneIntent.HOVER:
            # Tello hovers by default when no commands sent
            response = self._send_command("stop")
            return {"success": True, "message": "Hovering in place"}

        # Movement commands - Tello uses cm
        movement_map = {
            DroneIntent.MOVE_LEFT: "left",
            DroneIntent.MOVE_RIGHT: "right",
            DroneIntent.MOVE_FORWARD: "forward",
            DroneIntent.MOVE_BACK: "back",
            DroneIntent.MOVE_UP: "up",
            DroneIntent.MOVE_DOWN: "down",
        }

        if intent in movement_map:
            direction = movement_map[intent]
            distance_m = slots.distance or 1.0
            distance_cm = self._meters_to_cm(distance_m)

            command = f"{direction} {distance_cm}"
            response = self._send_command(command)

            if response == "ok":
                return {
                    "success": True,
                    "message": f"Moved {direction} {distance_m} meters ({distance_cm} cm)"
                }
            return {"success": False, "message": f"Move failed: {response}"}

        # Rotation commands
        if intent == DroneIntent.YAW_LEFT:
            degrees = int(slots.degrees or 90)
            degrees = max(1, min(360, degrees))
            response = self._send_command(f"ccw {degrees}")
            if response == "ok":
                return {"success": True, "message": f"Rotated left {degrees}°"}
            return {"success": False, "message": f"Rotation failed: {response}"}

        if intent == DroneIntent.YAW_RIGHT:
            degrees = int(slots.degrees or 90)
            degrees = max(1, min(360, degrees))
            response = self._send_command(f"cw {degrees}")
            if response == "ok":
                return {"success": True, "message": f"Rotated right {degrees}°"}
            return {"success": False, "message": f"Rotation failed: {response}"}

        # Camera commands
        if intent == DroneIntent.RECORD_START:
            response = self._send_command("streamon")
            if response == "ok":
                return {"success": True, "message": "Video stream started on UDP 11111"}
            return {"success": False, "message": f"Stream failed: {response}"}

        if intent == DroneIntent.RECORD_STOP:
            response = self._send_command("streamoff")
            return {"success": True, "message": "Video stream stopped"}

        # Speed commands
        if intent == DroneIntent.SPEED_SET:
            speed = int(slots.speed_numeric or 50)
            speed = max(10, min(100, speed))
            response = self._send_command(f"speed {speed}")
            if response == "ok":
                self._speed = speed
                return {"success": True, "message": f"Speed set to {speed} cm/s"}
            return {"success": False, "message": f"Speed set failed: {response}"}

        if intent == DroneIntent.SPEED_UP:
            new_speed = min(100, self._speed + 20)
            return await self.execute(DroneIntent.SPEED_SET, ParsedSlots(speed_numeric=new_speed))

        if intent == DroneIntent.SLOW_DOWN:
            new_speed = max(10, self._speed - 20)
            return await self.execute(DroneIntent.SPEED_SET, ParsedSlots(speed_numeric=new_speed))

        # Status queries
        if intent == DroneIntent.BATTERY:
            response = self._send_command("battery?")
            try:
                battery = int(response)
                self._battery = battery
                return {"success": True, "message": f"Battery: {battery}%", "battery": battery}
            except:
                return {"success": True, "message": f"Battery: {self._battery}%", "battery": self._battery}

        if intent == DroneIntent.ALTITUDE:
            # Get from state data
            altitude = self._state_data.get('h', self._altitude)
            return {"success": True, "message": f"Altitude: {altitude} cm", "altitude": altitude}

        if intent == DroneIntent.SIGNAL:
            # Tello doesn't report signal strength
            return {"success": True, "message": "Signal: Connected", "signal": 100}

        return {"success": False, "message": f"Unsupported intent: {intent}"}

    def start_video_stream(self) -> bool:
        """Start video stream and return True if successful."""
        response = self._send_command("streamon")
        return response == "ok"

    def get_video_frame(self):
        """
        Get a video frame from the stream.
        Returns raw H.264 data or None.

        Note: For actual video processing, use cv2.VideoCapture('udp://0.0.0.0:11111')
        """
        if not self._video_socket:
            self._video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._video_socket.bind(('', self.VIDEO_PORT))
            self._video_socket.settimeout(2.0)

        try:
            data, _ = self._video_socket.recvfrom(2048)
            return data
        except:
            return None


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
