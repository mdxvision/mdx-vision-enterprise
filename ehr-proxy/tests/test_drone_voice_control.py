"""
Drone Voice Control - Unit Tests

Comprehensive tests for:
- Intent parsing with synonyms
- Slot extraction (distance, degrees, zoom, speed)
- Confirmation flow
- STOP override
- Rate limiting
- Adapter capabilities
"""

import pytest
import time
from unittest.mock import AsyncMock, patch

# Import drone module components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from drone.models import (
    DroneIntent, ParsedSlots, ExecutionStatus, DistanceUnit, SpeedLevel
)
from drone.parser import (
    parse_voice_command, detect_intent, extract_slots,
    normalize_transcript, generate_normalized_command
)
from drone.policy import PolicyGate, get_policy_gate, reset_policy_gate
from drone.adapters import (
    MockDroneAdapter, MAVLinkAdapter, DJIAdapter,
    get_adapter, set_adapter, reset_adapter, CapabilitySet
)


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    reset_policy_gate()
    reset_adapter()
    yield
    reset_policy_gate()
    reset_adapter()


@pytest.fixture
def mock_adapter():
    """Create a fresh mock adapter."""
    return MockDroneAdapter(connected=True)


@pytest.fixture
def policy_gate():
    """Create a fresh policy gate."""
    return PolicyGate()


# ═══════════════════════════════════════════════════════════════════════════
# PARSER TESTS - Intent Detection
# ═══════════════════════════════════════════════════════════════════════════

class TestIntentDetection:
    """Test intent detection from voice transcripts."""

    @pytest.mark.unit
    @pytest.mark.parametrize("transcript,expected_intent", [
        # STOP - highest priority
        ("stop", DroneIntent.STOP),
        ("abort", DroneIntent.STOP),
        ("halt", DroneIntent.STOP),
        ("emergency stop", DroneIntent.STOP),
        ("kill", DroneIntent.STOP),
        ("freeze", DroneIntent.STOP),

        # Flight commands
        ("take off", DroneIntent.TAKEOFF),
        ("takeoff", DroneIntent.TAKEOFF),
        ("lift off", DroneIntent.TAKEOFF),
        ("launch", DroneIntent.TAKEOFF),
        ("land", DroneIntent.LAND),
        ("touch down", DroneIntent.LAND),
        ("hover", DroneIntent.HOVER),
        ("hold position", DroneIntent.HOVER),
        ("return home", DroneIntent.RETURN_HOME),
        ("go home", DroneIntent.RETURN_HOME),
        ("come back", DroneIntent.RETURN_HOME),

        # Movement
        ("go left", DroneIntent.MOVE_LEFT),
        ("move left", DroneIntent.MOVE_LEFT),
        ("slide left", DroneIntent.MOVE_LEFT),
        ("go right", DroneIntent.MOVE_RIGHT),
        ("move right", DroneIntent.MOVE_RIGHT),
        ("go forward", DroneIntent.MOVE_FORWARD),
        ("move forward", DroneIntent.MOVE_FORWARD),
        ("advance", DroneIntent.MOVE_FORWARD),
        ("go back", DroneIntent.MOVE_BACK),
        ("back up", DroneIntent.MOVE_BACK),
        ("reverse", DroneIntent.MOVE_BACK),
        ("go up", DroneIntent.MOVE_UP),
        ("ascend", DroneIntent.MOVE_UP),
        ("climb", DroneIntent.MOVE_UP),
        ("go down", DroneIntent.MOVE_DOWN),
        ("descend", DroneIntent.MOVE_DOWN),

        # Rotation
        ("turn left", DroneIntent.YAW_LEFT),
        ("rotate left", DroneIntent.YAW_LEFT),
        ("yaw left", DroneIntent.YAW_LEFT),
        ("turn right", DroneIntent.YAW_RIGHT),
        ("rotate right", DroneIntent.YAW_RIGHT),

        # Camera
        ("start recording", DroneIntent.RECORD_START),
        ("record video", DroneIntent.RECORD_START),
        ("stop recording", DroneIntent.RECORD_STOP),
        ("take a photo", DroneIntent.PHOTO_CAPTURE),
        ("snapshot", DroneIntent.PHOTO_CAPTURE),

        # Zoom
        ("zoom in", DroneIntent.ZOOM_IN),
        ("zoom out", DroneIntent.ZOOM_OUT),
        ("reset zoom", DroneIntent.ZOOM_RESET),

        # Speed
        ("speed up", DroneIntent.SPEED_UP),
        ("go faster", DroneIntent.SPEED_UP),
        ("slow down", DroneIntent.SLOW_DOWN),
        ("go slower", DroneIntent.SLOW_DOWN),

        # Status
        ("battery", DroneIntent.BATTERY),
        ("altitude", DroneIntent.ALTITUDE),
        ("signal", DroneIntent.SIGNAL),
        ("position", DroneIntent.POSITION),
    ])
    def test_intent_detection(self, transcript, expected_intent):
        """Test that various synonyms map to correct intents."""
        intent, confidence = detect_intent(transcript)
        assert intent == expected_intent
        assert confidence >= 0.9

    @pytest.mark.unit
    def test_unknown_intent(self):
        """Test that gibberish returns UNKNOWN."""
        intent, confidence = detect_intent("blah blah random words")
        assert intent == DroneIntent.UNKNOWN
        assert confidence == 0.0

    @pytest.mark.unit
    def test_stop_overrides_other_intents(self):
        """STOP should be detected even with other keywords."""
        # "stop" takes priority even in complex sentences
        intent, _ = detect_intent("stop the takeoff")
        assert intent == DroneIntent.STOP


# ═══════════════════════════════════════════════════════════════════════════
# PARSER TESTS - Slot Extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestSlotExtraction:
    """Test slot value extraction from transcripts."""

    @pytest.mark.unit
    @pytest.mark.parametrize("transcript,expected_distance,expected_unit", [
        ("go left 5 meters", 5.0, DistanceUnit.METERS),
        ("move right 3 feet", 3.0, DistanceUnit.FEET),
        ("go forward 10 m", 10.0, DistanceUnit.METERS),
        ("go back 2.5 ft", 2.5, DistanceUnit.FEET),
        ("go up 100 meters", 100.0, DistanceUnit.METERS),
    ])
    def test_distance_extraction(self, transcript, expected_distance, expected_unit):
        """Test distance and unit extraction."""
        parsed = parse_voice_command(transcript)
        assert parsed.slots.distance == expected_distance
        assert parsed.slots.unit == expected_unit

    @pytest.mark.unit
    @pytest.mark.parametrize("transcript,expected_degrees", [
        ("turn left 90 degrees", 90.0),
        ("rotate right 45 deg", 45.0),
        ("yaw left 180°", 180.0),
    ])
    def test_degrees_extraction(self, transcript, expected_degrees):
        """Test degree extraction for rotation commands."""
        parsed = parse_voice_command(transcript)
        assert parsed.slots.degrees == expected_degrees

    @pytest.mark.unit
    def test_no_slots_when_not_provided(self):
        """Test that missing slots are None."""
        parsed = parse_voice_command("go left")
        assert parsed.slots.distance is None
        assert parsed.slots.unit is None

    @pytest.mark.unit
    def test_speed_level_extraction(self):
        """Test speed level extraction."""
        # Test word-based speeds
        parsed = parse_voice_command("set speed to slow")
        assert parsed.intent == DroneIntent.SPEED_SET

        parsed = parse_voice_command("set speed to fast")
        assert parsed.intent == DroneIntent.SPEED_SET


# ═══════════════════════════════════════════════════════════════════════════
# PARSER TESTS - Normalization
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalization:
    """Test transcript normalization."""

    @pytest.mark.unit
    def test_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        lower = parse_voice_command("take off")
        upper = parse_voice_command("TAKE OFF")
        mixed = parse_voice_command("Take Off")
        assert lower.intent == upper.intent == mixed.intent == DroneIntent.TAKEOFF

    @pytest.mark.unit
    def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        normal = parse_voice_command("go left")
        spaced = parse_voice_command("  go   left  ")
        assert normal.intent == spaced.intent == DroneIntent.MOVE_LEFT

    @pytest.mark.unit
    def test_punctuation_removal(self):
        """Test that punctuation doesn't affect parsing."""
        normal = parse_voice_command("take off")
        with_punct = parse_voice_command("take off!")
        assert normal.intent == with_punct.intent == DroneIntent.TAKEOFF

    @pytest.mark.unit
    def test_normalized_command_format(self):
        """Test normalized command string format."""
        parsed = parse_voice_command("go left 5 meters")
        assert "MOVE_LEFT" in parsed.normalized_command
        assert "5" in parsed.normalized_command
        assert "meters" in parsed.normalized_command


# ═══════════════════════════════════════════════════════════════════════════
# POLICY GATE TESTS - Confirmation Flow
# ═══════════════════════════════════════════════════════════════════════════

class TestConfirmationFlow:
    """Test confirmation requirement and flow."""

    @pytest.mark.unit
    def test_takeoff_requires_confirmation(self, policy_gate):
        """TAKEOFF should require confirmation."""
        slots = ParsedSlots()
        status, msg, _ = policy_gate.evaluate(
            "test-session", DroneIntent.TAKEOFF, slots, "TAKEOFF"
        )
        assert status == ExecutionStatus.NEEDS_CONFIRM
        assert "confirm" in msg.lower()

    @pytest.mark.unit
    def test_land_requires_confirmation(self, policy_gate):
        """LAND should require confirmation."""
        slots = ParsedSlots()
        status, msg, _ = policy_gate.evaluate(
            "test-session", DroneIntent.LAND, slots, "LAND"
        )
        assert status == ExecutionStatus.NEEDS_CONFIRM

    @pytest.mark.unit
    def test_return_home_requires_confirmation(self, policy_gate):
        """RETURN_HOME should require confirmation."""
        slots = ParsedSlots()
        status, msg, _ = policy_gate.evaluate(
            "test-session", DroneIntent.RETURN_HOME, slots, "RETURN_HOME"
        )
        assert status == ExecutionStatus.NEEDS_CONFIRM

    @pytest.mark.unit
    def test_confirmation_flow_complete(self, policy_gate):
        """Test full confirmation flow: request -> pending -> confirm."""
        session = "confirm-test"
        slots = ParsedSlots()

        # First call - should need confirmation
        status, _, _ = policy_gate.evaluate(
            session, DroneIntent.TAKEOFF, slots, "TAKEOFF"
        )
        assert status == ExecutionStatus.NEEDS_CONFIRM

        # Check pending state exists
        pending = policy_gate.get_pending_confirmation(session)
        assert pending is not None
        assert pending.intent == DroneIntent.TAKEOFF

        # Confirm the command
        status, msg, confirmed = policy_gate.evaluate(
            session, DroneIntent.TAKEOFF, slots, "TAKEOFF", confirm=True
        )
        assert status == ExecutionStatus.OK
        assert confirmed is not None
        assert confirmed.intent == DroneIntent.TAKEOFF

        # Pending should be cleared
        assert policy_gate.get_pending_confirmation(session) is None

    @pytest.mark.unit
    def test_confirmation_timeout(self, policy_gate):
        """Test that confirmation expires after timeout."""
        # Use short timeout for testing
        policy_gate.confirmation_timeout = 0.1
        session = "timeout-test"
        slots = ParsedSlots()

        # Request confirmation
        policy_gate.evaluate(session, DroneIntent.TAKEOFF, slots, "TAKEOFF")

        # Wait for timeout
        time.sleep(0.2)

        # Confirm should fail - expired
        status, msg, _ = policy_gate.evaluate(
            session, DroneIntent.TAKEOFF, slots, "TAKEOFF", confirm=True
        )
        assert status == ExecutionStatus.BLOCKED
        assert "expired" in msg.lower() or "no pending" in msg.lower()

    @pytest.mark.unit
    def test_movement_no_confirmation(self, policy_gate):
        """Movement commands should not require confirmation."""
        slots = ParsedSlots()
        for intent in [
            DroneIntent.MOVE_LEFT, DroneIntent.MOVE_RIGHT,
            DroneIntent.MOVE_FORWARD, DroneIntent.MOVE_BACK,
            DroneIntent.MOVE_UP, DroneIntent.MOVE_DOWN
        ]:
            status, _, _ = policy_gate.evaluate(
                "test", intent, slots, intent.value
            )
            assert status == ExecutionStatus.OK


# ═══════════════════════════════════════════════════════════════════════════
# POLICY GATE TESTS - STOP Override
# ═══════════════════════════════════════════════════════════════════════════

class TestStopOverride:
    """Test STOP as immediate override."""

    @pytest.mark.unit
    def test_stop_never_needs_confirmation(self, policy_gate):
        """STOP should never need confirmation."""
        slots = ParsedSlots()
        status, msg, _ = policy_gate.evaluate(
            "test", DroneIntent.STOP, slots, "STOP"
        )
        assert status == ExecutionStatus.OK
        assert "immediately" in msg.lower() or "emergency" in msg.lower()

    @pytest.mark.unit
    def test_stop_clears_pending(self, policy_gate):
        """STOP should clear any pending confirmation."""
        session = "stop-test"
        slots = ParsedSlots()

        # Request takeoff confirmation
        policy_gate.evaluate(session, DroneIntent.TAKEOFF, slots, "TAKEOFF")
        assert policy_gate.get_pending_confirmation(session) is not None

        # STOP should clear it
        policy_gate.evaluate(session, DroneIntent.STOP, slots, "STOP")
        assert policy_gate.get_pending_confirmation(session) is None

    @pytest.mark.unit
    def test_stop_bypasses_rate_limit(self, policy_gate):
        """STOP should work even when rate limited."""
        session = "rate-test"
        policy_gate.rate_limit_max = 1

        # Use up rate limit
        slots = ParsedSlots()
        policy_gate.evaluate(session, DroneIntent.MOVE_LEFT, slots, "MOVE_LEFT")
        policy_gate.record_command(session)

        # STOP should still work
        status, _, _ = policy_gate.evaluate(
            session, DroneIntent.STOP, slots, "STOP"
        )
        assert status == ExecutionStatus.OK


# ═══════════════════════════════════════════════════════════════════════════
# POLICY GATE TESTS - Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════

class TestRateLimiting:
    """Test rate limiting by session."""

    @pytest.mark.unit
    def test_rate_limit_enforced(self, policy_gate):
        """Test that rate limiting is enforced."""
        session = "rate-test"
        policy_gate.rate_limit_max = 3
        policy_gate.rate_limit_window = 60.0
        slots = ParsedSlots()

        # First 3 commands should work
        for _ in range(3):
            policy_gate.record_command(session)

        # 4th command should be rate limited
        status, msg, _ = policy_gate.evaluate(
            session, DroneIntent.MOVE_LEFT, slots, "MOVE_LEFT"
        )
        assert status == ExecutionStatus.RATE_LIMITED
        assert "rate" in msg.lower()

    @pytest.mark.unit
    def test_rate_limit_per_session(self, policy_gate):
        """Rate limit should be per-session."""
        policy_gate.rate_limit_max = 1
        slots = ParsedSlots()

        # Session 1 uses up limit
        policy_gate.record_command("session1")

        # Session 2 should still work
        allowed, _ = policy_gate.check_rate_limit("session2")
        assert allowed

    @pytest.mark.unit
    def test_rate_limit_window_expires(self, policy_gate):
        """Rate limit should reset after window expires."""
        session = "window-test"
        policy_gate.rate_limit_max = 1
        policy_gate.rate_limit_window = 0.1  # 100ms window
        slots = ParsedSlots()

        # Use up limit
        policy_gate.record_command(session)

        # Should be rate limited
        allowed, _ = policy_gate.check_rate_limit(session)
        assert not allowed

        # Wait for window to expire
        time.sleep(0.2)

        # Should be allowed again
        allowed, _ = policy_gate.check_rate_limit(session)
        assert allowed


# ═══════════════════════════════════════════════════════════════════════════
# ADAPTER TESTS - Mock Adapter
# ═══════════════════════════════════════════════════════════════════════════

class TestMockAdapter:
    """Test MockDroneAdapter functionality."""

    @pytest.mark.unit
    def test_adapter_connected(self, mock_adapter):
        """Test adapter connection state."""
        assert mock_adapter.is_connected()

        disconnected = MockDroneAdapter(connected=False)
        assert not disconnected.is_connected()

    @pytest.mark.unit
    def test_adapter_name_and_type(self, mock_adapter):
        """Test adapter metadata."""
        assert mock_adapter.name == "Mock Drone Simulator"
        assert mock_adapter.adapter_type == "mock"

    @pytest.mark.unit
    def test_all_capabilities_supported(self, mock_adapter):
        """Mock adapter should support all capabilities."""
        caps = mock_adapter.get_capabilities()
        assert all(cap.supported for cap in caps.values())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_takeoff_execution(self, mock_adapter):
        """Test takeoff command execution."""
        slots = ParsedSlots()
        result = await mock_adapter.execute(DroneIntent.TAKEOFF, slots)
        assert result["success"]
        assert mock_adapter._is_flying
        assert mock_adapter._altitude > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_land_execution(self, mock_adapter):
        """Test land command execution."""
        mock_adapter._is_flying = True
        mock_adapter._altitude = 10.0
        slots = ParsedSlots()
        result = await mock_adapter.execute(DroneIntent.LAND, slots)
        assert result["success"]
        assert not mock_adapter._is_flying
        assert mock_adapter._altitude == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_movement_with_distance(self, mock_adapter):
        """Test movement command with distance slot."""
        slots = ParsedSlots(distance=5.0, unit=DistanceUnit.METERS)
        result = await mock_adapter.execute(DroneIntent.MOVE_LEFT, slots)
        assert result["success"]
        assert "5" in result["message"]
        assert "meters" in result["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_zoom_state(self, mock_adapter):
        """Test zoom commands update state."""
        slots = ParsedSlots()

        # Zoom in
        await mock_adapter.execute(DroneIntent.ZOOM_IN, slots)
        assert mock_adapter._zoom_level == 2.0

        # Zoom out
        await mock_adapter.execute(DroneIntent.ZOOM_OUT, slots)
        assert mock_adapter._zoom_level == 1.0

        # Set zoom
        slots = ParsedSlots(zoom_level=5.0)
        await mock_adapter.execute(DroneIntent.ZOOM_SET, slots)
        assert mock_adapter._zoom_level == 5.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_recording_state(self, mock_adapter):
        """Test recording commands update state."""
        slots = ParsedSlots()

        await mock_adapter.execute(DroneIntent.RECORD_START, slots)
        assert mock_adapter._recording

        await mock_adapter.execute(DroneIntent.RECORD_STOP, slots)
        assert not mock_adapter._recording

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_status_queries(self, mock_adapter):
        """Test status query commands."""
        slots = ParsedSlots()

        battery = await mock_adapter.execute(DroneIntent.BATTERY, slots)
        assert battery["success"]
        assert "battery" in battery

        altitude = await mock_adapter.execute(DroneIntent.ALTITUDE, slots)
        assert altitude["success"]
        assert "altitude" in altitude

        signal = await mock_adapter.execute(DroneIntent.SIGNAL, slots)
        assert signal["success"]
        assert "signal" in signal

        position = await mock_adapter.execute(DroneIntent.POSITION, slots)
        assert position["success"]
        assert "position" in position

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disconnected_fails(self):
        """Test that commands fail when disconnected."""
        adapter = MockDroneAdapter(connected=False)
        slots = ParsedSlots()
        result = await adapter.execute(DroneIntent.TAKEOFF, slots)
        assert not result["success"]
        assert "not connected" in result["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# ADAPTER TESTS - Capability Degradation
# ═══════════════════════════════════════════════════════════════════════════

class TestCapabilityDegradation:
    """Test capability checking and graceful degradation."""

    @pytest.mark.unit
    def test_mavlink_no_camera(self):
        """MAVLink adapter should not support camera by default."""
        adapter = MAVLinkAdapter()
        caps = adapter.get_capabilities()
        assert not caps[CapabilitySet.CAMERA].supported
        assert not caps[CapabilitySet.ZOOM].supported

    @pytest.mark.unit
    def test_mavlink_supports_flight(self):
        """MAVLink adapter should support flight."""
        adapter = MAVLinkAdapter()
        caps = adapter.get_capabilities()
        assert caps[CapabilitySet.FLIGHT].supported
        assert caps[CapabilitySet.MOVEMENT].supported

    @pytest.mark.unit
    def test_dji_full_capabilities(self):
        """DJI adapter should support all capabilities."""
        adapter = DJIAdapter()
        caps = adapter.get_capabilities()
        assert all(cap.supported for cap in caps.values())

    @pytest.mark.unit
    def test_supports_intent_check(self, mock_adapter):
        """Test intent support checking."""
        assert mock_adapter.supports_intent(DroneIntent.TAKEOFF)
        assert mock_adapter.supports_intent(DroneIntent.PHOTO_CAPTURE)

    @pytest.mark.unit
    def test_get_supported_intents(self, mock_adapter):
        """Test getting all supported intents."""
        intents = mock_adapter.get_supported_intents()
        assert DroneIntent.TAKEOFF in intents
        assert DroneIntent.LAND in intents
        assert DroneIntent.MOVE_LEFT in intents
        assert DroneIntent.UNKNOWN not in intents


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL STATE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestGlobalState:
    """Test global adapter and policy gate management."""

    @pytest.mark.unit
    def test_get_adapter_default(self):
        """get_adapter should return mock by default."""
        adapter = get_adapter()
        assert adapter.adapter_type == "mock"

    @pytest.mark.unit
    def test_set_adapter(self):
        """Test setting a custom adapter."""
        custom = MAVLinkAdapter()
        set_adapter(custom)
        assert get_adapter().adapter_type == "mavlink"

    @pytest.mark.unit
    def test_reset_adapter(self):
        """Test resetting to default adapter."""
        set_adapter(DJIAdapter())
        reset_adapter()
        assert get_adapter().adapter_type == "mock"

    @pytest.mark.unit
    def test_get_policy_gate_singleton(self):
        """Policy gate should be a singleton."""
        gate1 = get_policy_gate()
        gate2 = get_policy_gate()
        assert gate1 is gate2

    @pytest.mark.unit
    def test_reset_policy_gate(self):
        """Test resetting policy gate."""
        gate1 = get_policy_gate()
        gate1.rate_limit_max = 999
        reset_policy_gate()
        gate2 = get_policy_gate()
        assert gate2.rate_limit_max != 999


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION-STYLE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEndFlow:
    """Test complete command flow."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_command_flow(self, mock_adapter, policy_gate):
        """Test parsing, policy check, and execution."""
        session = "e2e-test"
        set_adapter(mock_adapter)

        # Parse a movement command
        parsed = parse_voice_command("go left 5 meters")
        assert parsed.intent == DroneIntent.MOVE_LEFT
        assert parsed.slots.distance == 5.0

        # Check policy (movement doesn't need confirm)
        status, _, _ = policy_gate.evaluate(
            session, parsed.intent, parsed.slots, parsed.normalized_command
        )
        assert status == ExecutionStatus.OK

        # Execute
        result = await mock_adapter.execute(parsed.intent, parsed.slots)
        assert result["success"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_confirmation_flow(self, mock_adapter, policy_gate):
        """Test full confirmation flow end to end."""
        session = "confirm-e2e"
        set_adapter(mock_adapter)

        # Parse takeoff command
        parsed = parse_voice_command("take off")
        assert parsed.intent == DroneIntent.TAKEOFF
        assert parsed.requires_confirmation

        # First policy check - needs confirm
        status, _, _ = policy_gate.evaluate(
            session, parsed.intent, parsed.slots, parsed.normalized_command
        )
        assert status == ExecutionStatus.NEEDS_CONFIRM

        # Confirm and execute
        status, _, confirmed = policy_gate.evaluate(
            session, parsed.intent, parsed.slots, parsed.normalized_command,
            confirm=True
        )
        assert status == ExecutionStatus.OK

        result = await mock_adapter.execute(confirmed.intent, confirmed.slots)
        assert result["success"]
        assert mock_adapter._is_flying
