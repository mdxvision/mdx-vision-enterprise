#!/usr/bin/env python3
"""
Drone Voice Control - Interactive Simulator

A CLI tool for testing drone voice commands without a real drone.
Uses the MockDroneAdapter to simulate all operations.

Usage:
    python tools/drone_simulator.py

Commands:
    - Type any voice command (e.g., "take off", "go left 5 meters", "stop")
    - 'confirm' to confirm pending commands
    - 'status' to see drone state
    - 'caps' to see capabilities
    - 'help' to see all commands
    - 'quit' or 'exit' to stop

Examples:
    > take off
    [NEEDS_CONFIRM] Confirm 'TAKEOFF'? Say 'confirm' or set confirm=true
    > confirm
    [OK] Confirmed: TAKEOFF - Takeoff complete

    > go left 3 meters
    [OK] Executing: MOVE_LEFT 3.0 meters - Moved left 3.0 meters

    > stop
    [OK] Emergency stop - executing immediately - Emergency stop executed
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from drone.parser import parse_voice_command, generate_normalized_command
from drone.policy import PolicyGate, reset_policy_gate
from drone.adapters import MockDroneAdapter, set_adapter, reset_adapter
from drone.models import ExecutionStatus


class DroneSimulator:
    """Interactive drone voice control simulator."""

    def __init__(self, session_id: str = "simulator"):
        self.session_id = session_id
        self.adapter = MockDroneAdapter(connected=True)
        self.policy = PolicyGate()
        set_adapter(self.adapter)

    def print_header(self):
        """Print welcome banner."""
        print("\n" + "=" * 60)
        print(" DRONE VOICE CONTROL SIMULATOR")
        print(" Type commands like 'take off', 'go left 5 meters', 'stop'")
        print(" Type 'help' for all commands, 'quit' to exit")
        print("=" * 60 + "\n")

    def print_status(self):
        """Print current drone state."""
        print("\n--- Drone Status ---")
        print(f"  Connected: {self.adapter._connected}")
        print(f"  Flying: {self.adapter._is_flying}")
        print(f"  Altitude: {self.adapter._altitude}m")
        print(f"  Battery: {self.adapter._battery}%")
        print(f"  Recording: {self.adapter._recording}")
        print(f"  Zoom: {self.adapter._zoom_level}x")
        print(f"  Speed: {self.adapter._speed}")
        print(f"  Position: {self.adapter._position}")
        print("-------------------\n")

    def print_capabilities(self):
        """Print adapter capabilities."""
        print("\n--- Capabilities ---")
        caps = self.adapter.get_capabilities()
        for name, cap in caps.items():
            status = "[Y]" if cap.supported else "[N]"
            print(f"  {status} {name}: {cap.description}")
        print("\n--- Supported Intents ---")
        intents = sorted([i.value for i in self.adapter.get_supported_intents()])
        for i, intent in enumerate(intents):
            print(f"  {intent}", end="")
            if (i + 1) % 4 == 0:
                print()
        print("\n-------------------\n")

    def print_help(self):
        """Print help information."""
        print("""
--- Drone Voice Commands ---

FLIGHT:
  take off, lift off, launch      - Start flying (requires confirm)
  land, touch down               - Land the drone (requires confirm)
  hover, hold position           - Hold current position
  return home, go home           - Return to home position (requires confirm)
  stop, abort, halt              - Emergency stop (IMMEDIATE)

MOVEMENT:
  go left/right/forward/back [N meters/feet]
  go up/down [N meters/feet]
  Examples: "go left 5 meters", "move forward", "fly up 10 feet"

ROTATION:
  turn left/right [N degrees]
  Examples: "turn left 90 degrees", "rotate right"

CAMERA:
  start recording, record        - Start video recording
  stop recording                 - Stop video recording
  take a photo, snapshot         - Capture a photo

ZOOM:
  zoom in / zoom out
  zoom to [N]x                   - Set specific zoom level
  reset zoom                     - Reset to 1x

SPEED:
  speed up, go faster
  slow down, go slower
  set speed to slow/normal/fast

STATUS:
  battery                        - Check battery level
  altitude                       - Check current altitude
  signal                         - Check signal strength
  position                       - Get GPS coordinates

SIMULATOR COMMANDS:
  confirm                        - Confirm pending command
  status                         - Show drone state
  caps                           - Show capabilities
  help                           - Show this help
  quit / exit                    - Exit simulator
""")

    async def process_command(self, text: str) -> None:
        """Process a voice command or simulator command."""
        text = text.strip().lower()

        # Simulator commands
        if text in ("quit", "exit", "q"):
            print("Goodbye!")
            sys.exit(0)
        if text == "help":
            self.print_help()
            return
        if text == "status":
            self.print_status()
            return
        if text in ("caps", "capabilities"):
            self.print_capabilities()
            return

        # Check for confirm
        is_confirm = text == "confirm"

        if is_confirm:
            # Handle confirmation
            pending = self.policy.get_pending_confirmation(self.session_id)
            if not pending:
                print("[ERROR] No pending command to confirm")
                return

            status, message, confirmed = self.policy.evaluate(
                session_id=self.session_id,
                intent=pending.intent,
                slots=pending.slots,
                normalized_command=pending.normalized_command,
                confirm=True
            )

            if status == ExecutionStatus.OK and confirmed:
                # Execute the confirmed command
                result = await self.adapter.execute(confirmed.intent, confirmed.slots)
                self.policy.record_command(self.session_id)
                print(f"[{status.value.upper()}] {message} - {result.get('message', 'Done')}")
            else:
                print(f"[{status.value.upper()}] {message}")
            return

        # Parse voice command
        parsed = parse_voice_command(text, self.session_id)

        if parsed.intent.value == "UNKNOWN":
            print(f"[UNKNOWN] Could not understand: '{text}'")
            print("  Try 'help' to see available commands")
            return

        print(f"  Parsed: {parsed.intent.value} | Confidence: {parsed.confidence:.0%}")
        if parsed.slots.distance:
            unit = parsed.slots.unit.value if parsed.slots.unit else "units"
            print(f"  Slots: distance={parsed.slots.distance} {unit}")
        if parsed.slots.degrees:
            print(f"  Slots: degrees={parsed.slots.degrees}")
        if parsed.slots.zoom_level:
            print(f"  Slots: zoom={parsed.slots.zoom_level}x")

        # Check capability
        if not self.adapter.supports_intent(parsed.intent):
            print(f"[UNSUPPORTED] Adapter does not support {parsed.intent.value}")
            return

        # Evaluate policy
        status, message, pending = self.policy.evaluate(
            session_id=self.session_id,
            intent=parsed.intent,
            slots=parsed.slots,
            normalized_command=parsed.normalized_command,
            confirm=None
        )

        if status == ExecutionStatus.NEEDS_CONFIRM:
            print(f"[{status.value.upper()}] {message}")
            return

        if status != ExecutionStatus.OK:
            print(f"[{status.value.upper()}] {message}")
            return

        # Execute
        result = await self.adapter.execute(parsed.intent, parsed.slots)
        self.policy.record_command(self.session_id)
        print(f"[{status.value.upper()}] {message} - {result.get('message', 'Done')}")

    def run(self):
        """Run the interactive simulator loop."""
        self.print_header()
        self.print_status()

        while True:
            try:
                text = input("> ").strip()
                if not text:
                    continue
                asyncio.run(self.process_command(text))
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"[ERROR] {e}")


def main():
    """Entry point."""
    simulator = DroneSimulator()
    simulator.run()


if __name__ == "__main__":
    main()
