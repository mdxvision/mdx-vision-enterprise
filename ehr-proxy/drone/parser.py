"""
Drone Voice Control - Intent Parser
Rule-based intent detection and slot extraction (no LLM).
"""

import re
from typing import Tuple, Optional
from .models import (
    DroneIntent, ParsedSlots, ParseResponse, DistanceUnit, SpeedLevel
)


# ═══════════════════════════════════════════════════════════════════════════
# SYNONYM MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════

# Map phrases to intents (order matters - more specific first)
INTENT_PATTERNS = {
    # STOP - Emergency (highest priority, check first)
    # Use negative lookahead to avoid matching "stop recording"
    DroneIntent.STOP: [
        r"\b(abort|halt|freeze|emergency\s*stop|kill|cancel)\b",
        r"\bstop\b(?!\s*recording)",  # "stop" but not "stop recording"
    ],

    # Flight commands
    DroneIntent.TAKEOFF: [
        r"\b(take\s*off|takeoff|lift\s*off|liftoff|launch|go\s*up\s*and\s*fly|start\s*flying)\b",
    ],
    DroneIntent.LAND: [
        r"\b(land|touch\s*down|set\s*down|come\s*down|bring\s*it\s*down)\b",
    ],
    DroneIntent.HOVER: [
        r"\b(hover|hold\s*position|maintain\s*position|stay\s*there|hold\s*steady)\b",
    ],
    DroneIntent.RETURN_HOME: [
        r"\b(return\s*home|go\s*home|come\s*back|return\s*to\s*base|rtb|come\s*home|fly\s*back)\b",
    ],

    # Movement - with direction
    DroneIntent.MOVE_LEFT: [
        r"\b(go\s*left|move\s*left|slide\s*left|strafe\s*left|drift\s*left|fly\s*left)\b",
    ],
    DroneIntent.MOVE_RIGHT: [
        r"\b(go\s*right|move\s*right|slide\s*right|strafe\s*right|drift\s*right|fly\s*right)\b",
    ],
    DroneIntent.MOVE_FORWARD: [
        r"\b(go\s*forward|move\s*forward|fly\s*forward|advance|go\s*ahead|move\s*ahead)\b",
    ],
    DroneIntent.MOVE_BACK: [
        r"\b(go\s*back|move\s*back|back\s*up|fly\s*back|reverse|retreat|go\s*backward|move\s*backward)\b",
    ],
    DroneIntent.MOVE_UP: [
        r"\b(go\s*up|move\s*up|fly\s*up|ascend|rise|climb|higher|gain\s*altitude)\b",
    ],
    DroneIntent.MOVE_DOWN: [
        r"\b(go\s*down|move\s*down|fly\s*down|descend|lower|drop|sink)\b",
    ],

    # Rotation
    DroneIntent.YAW_LEFT: [
        r"\b(turn\s*left|rotate\s*left|yaw\s*left|spin\s*left|pan\s*left)\b",
    ],
    DroneIntent.YAW_RIGHT: [
        r"\b(turn\s*right|rotate\s*right|yaw\s*right|spin\s*right|pan\s*right)\b",
    ],

    # Camera
    DroneIntent.RECORD_START: [
        r"\b(start\s*recording|record\s*video|begin\s*recording|start\s*video|record)\b",
    ],
    DroneIntent.RECORD_STOP: [
        r"\b(stop\s*recording|end\s*recording|finish\s*recording|stop\s*video)\b",
    ],
    DroneIntent.PHOTO_CAPTURE: [
        r"\b(take\s*a?\s*photo|take\s*a?\s*picture|capture\s*image|snapshot|shoot|photograph)\b",
    ],

    # Zoom
    DroneIntent.ZOOM_IN: [
        r"\b(zoom\s*in|magnify|closer\s*view|get\s*closer)\b",
    ],
    DroneIntent.ZOOM_OUT: [
        r"\b(zoom\s*out|wide\s*view|wider|pull\s*back)\b",
    ],
    DroneIntent.ZOOM_SET: [
        r"\b(zoom\s*to|set\s*zoom|zoom\s*level)\b",
    ],
    DroneIntent.ZOOM_RESET: [
        r"\b(reset\s*zoom|zoom\s*reset|normal\s*zoom|default\s*zoom|1x\s*zoom)\b",
    ],

    # Speed
    DroneIntent.SPEED_UP: [
        r"\b(speed\s*up|go\s*faster|faster|increase\s*speed|accelerate)\b",
    ],
    DroneIntent.SLOW_DOWN: [
        r"\b(slow\s*down|go\s*slower|slower|decrease\s*speed|decelerate)\b",
    ],
    DroneIntent.SPEED_SET: [
        r"\b(set\s*speed|speed\s*to|change\s*speed)\b",
    ],

    # Status queries
    DroneIntent.BATTERY: [
        r"\b(battery|power\s*level|charge|how\s*much\s*battery|battery\s*status)\b",
    ],
    DroneIntent.ALTITUDE: [
        r"\b(altitude|height|how\s*high|elevation)\b",
    ],
    DroneIntent.SIGNAL: [
        r"\b(signal|connection|signal\s*strength|link\s*quality)\b",
    ],
    DroneIntent.POSITION: [
        r"\b(position|location|where|coordinates|gps)\b",
    ],
}

# Commands requiring confirmation before execution
CONFIRMATION_REQUIRED = {
    DroneIntent.TAKEOFF,
    DroneIntent.LAND,
    DroneIntent.RETURN_HOME,
}

# STOP is immediate override - never needs confirmation
IMMEDIATE_OVERRIDE = {DroneIntent.STOP}


# ═══════════════════════════════════════════════════════════════════════════
# SLOT EXTRACTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

# Distance patterns: "3 feet", "5 meters", "10 ft", "2m"
DISTANCE_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(feet|foot|ft|meters?|m)\b',
    re.IGNORECASE
)

# Degrees pattern: "30 degrees", "45 deg", "90°"
DEGREES_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:degrees?|deg|°)',
    re.IGNORECASE
)

# Zoom level: "2x", "zoom to 4", "4 times"
ZOOM_PATTERN = re.compile(
    r'(?:zoom\s*(?:to|level)?\s*)?(\d+(?:\.\d+)?)\s*(?:x|times)?',
    re.IGNORECASE
)

# Speed patterns: "slow", "normal", "fast", or numeric "5 m/s"
SPEED_WORDS = {
    'slow': SpeedLevel.SLOW,
    'normal': SpeedLevel.NORMAL,
    'medium': SpeedLevel.NORMAL,
    'fast': SpeedLevel.FAST,
    'quick': SpeedLevel.FAST,
}

SPEED_NUMERIC_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:m/?s|mph|kph)?',
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════════════════
# PARSER IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════

def normalize_transcript(transcript: str) -> str:
    """Normalize transcript for matching."""
    # Lowercase and strip
    text = transcript.lower().strip()
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove punctuation except for degree symbol
    text = re.sub(r'[^\w\s°]', '', text)
    return text


def detect_intent(transcript: str) -> Tuple[DroneIntent, float]:
    """
    Detect intent from transcript using rule-based matching.
    Returns (intent, confidence).
    """
    normalized = normalize_transcript(transcript)

    # Check STOP first (immediate override)
    for pattern in INTENT_PATTERNS[DroneIntent.STOP]:
        if re.search(pattern, normalized):
            return DroneIntent.STOP, 1.0

    # Check other intents
    for intent, patterns in INTENT_PATTERNS.items():
        if intent == DroneIntent.STOP:
            continue
        for pattern in patterns:
            if re.search(pattern, normalized):
                return intent, 0.95

    return DroneIntent.UNKNOWN, 0.0


def extract_slots(transcript: str, intent: DroneIntent) -> ParsedSlots:
    """Extract slot values from transcript based on intent."""
    normalized = normalize_transcript(transcript)
    slots = ParsedSlots()

    # Extract distance for movement commands
    if intent in {
        DroneIntent.MOVE_LEFT, DroneIntent.MOVE_RIGHT,
        DroneIntent.MOVE_FORWARD, DroneIntent.MOVE_BACK,
        DroneIntent.MOVE_UP, DroneIntent.MOVE_DOWN
    }:
        match = DISTANCE_PATTERN.search(transcript)
        if match:
            slots.distance = float(match.group(1))
            unit_str = match.group(2).lower()
            if unit_str in ('feet', 'foot', 'ft'):
                slots.unit = DistanceUnit.FEET
            else:
                slots.unit = DistanceUnit.METERS

    # Extract degrees for rotation commands
    if intent in {DroneIntent.YAW_LEFT, DroneIntent.YAW_RIGHT}:
        match = DEGREES_PATTERN.search(transcript)
        if match:
            slots.degrees = float(match.group(1))

    # Extract zoom level
    if intent == DroneIntent.ZOOM_SET:
        match = ZOOM_PATTERN.search(normalized)
        if match:
            slots.zoom_level = float(match.group(1))

    # Extract speed
    if intent == DroneIntent.SPEED_SET:
        # Check for word-based speed
        for word, level in SPEED_WORDS.items():
            if word in normalized:
                slots.speed_level = level
                break
        # Check for numeric speed
        if not slots.speed_level:
            match = SPEED_NUMERIC_PATTERN.search(normalized)
            if match:
                slots.speed_numeric = float(match.group(1))

    return slots


def generate_normalized_command(intent: DroneIntent, slots: ParsedSlots) -> str:
    """Generate a normalized command string for display/logging."""
    parts = [intent.value]

    if slots.distance is not None:
        unit = slots.unit.value if slots.unit else "units"
        parts.append(f"{slots.distance} {unit}")

    if slots.degrees is not None:
        parts.append(f"{slots.degrees} degrees")

    if slots.zoom_level is not None:
        parts.append(f"{slots.zoom_level}x")

    if slots.speed_level is not None:
        parts.append(slots.speed_level.value)
    elif slots.speed_numeric is not None:
        parts.append(f"{slots.speed_numeric} m/s")

    return " ".join(parts)


def parse_voice_command(transcript: str, session_id: Optional[str] = None) -> ParseResponse:
    """
    Parse a voice command transcript into structured intent and slots.

    Args:
        transcript: Raw voice command text
        session_id: Optional session ID for state tracking

    Returns:
        ParseResponse with intent, slots, and metadata
    """
    intent, confidence = detect_intent(transcript)
    slots = extract_slots(transcript, intent)
    normalized = generate_normalized_command(intent, slots)

    # Determine if confirmation is required
    requires_confirmation = (
        intent in CONFIRMATION_REQUIRED and
        intent not in IMMEDIATE_OVERRIDE
    )

    return ParseResponse(
        intent=intent,
        slots=slots,
        requires_confirmation=requires_confirmation,
        normalized_command=normalized,
        confidence=confidence,
        original_transcript=transcript
    )
