"""
Drone Voice Control - Safety & Policy Gate
Handles confirmations, rate limiting, and safety overrides.
"""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from .models import (
    DroneIntent, ParsedSlots, ConfirmationState, ExecutionStatus
)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Confirmation timeout in seconds
CONFIRMATION_TIMEOUT = 30.0

# Rate limiting: max commands per time window
RATE_LIMIT_WINDOW = 60.0  # seconds
RATE_LIMIT_MAX_COMMANDS = 30  # commands per window

# Commands requiring confirmation
CONFIRMATION_REQUIRED = {
    DroneIntent.TAKEOFF,
    DroneIntent.LAND,
    DroneIntent.RETURN_HOME,
}

# STOP is always allowed - immediate override
IMMEDIATE_OVERRIDE = {DroneIntent.STOP}


# ═══════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SessionState:
    """State for a single session."""
    pending_confirmation: Optional[ConfirmationState] = None
    command_timestamps: list = field(default_factory=list)


class PolicyGate:
    """
    Safety and policy enforcement for drone commands.

    Handles:
    - Confirmation flow for risky commands
    - Rate limiting per session
    - STOP override (always allowed)
    """

    def __init__(
        self,
        confirmation_timeout: float = CONFIRMATION_TIMEOUT,
        rate_limit_window: float = RATE_LIMIT_WINDOW,
        rate_limit_max: int = RATE_LIMIT_MAX_COMMANDS
    ):
        self.confirmation_timeout = confirmation_timeout
        self.rate_limit_window = rate_limit_window
        self.rate_limit_max = rate_limit_max
        self._sessions: Dict[str, SessionState] = {}

    def _get_session(self, session_id: str) -> SessionState:
        """Get or create session state."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState()
        return self._sessions[session_id]

    def _cleanup_old_timestamps(self, session: SessionState) -> None:
        """Remove timestamps outside the rate limit window."""
        now = time.time()
        cutoff = now - self.rate_limit_window
        session.command_timestamps = [
            ts for ts in session.command_timestamps if ts > cutoff
        ]

    def check_rate_limit(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if session is rate limited.

        Returns:
            (is_allowed, error_message)
        """
        session = self._get_session(session_id)
        self._cleanup_old_timestamps(session)

        if len(session.command_timestamps) >= self.rate_limit_max:
            wait_time = self.rate_limit_window - (time.time() - session.command_timestamps[0])
            return False, f"Rate limited. Too many commands. Wait {wait_time:.0f} seconds."

        return True, None

    def record_command(self, session_id: str) -> None:
        """Record a command execution for rate limiting."""
        session = self._get_session(session_id)
        session.command_timestamps.append(time.time())

    def requires_confirmation(self, intent: DroneIntent) -> bool:
        """Check if intent requires confirmation."""
        return intent in CONFIRMATION_REQUIRED and intent not in IMMEDIATE_OVERRIDE

    def is_immediate_override(self, intent: DroneIntent) -> bool:
        """Check if intent is an immediate override (e.g., STOP)."""
        return intent in IMMEDIATE_OVERRIDE

    def set_pending_confirmation(
        self,
        session_id: str,
        intent: DroneIntent,
        slots: ParsedSlots,
        normalized_command: str
    ) -> None:
        """Store a command pending confirmation."""
        session = self._get_session(session_id)
        session.pending_confirmation = ConfirmationState(
            intent=intent,
            slots=slots,
            normalized_command=normalized_command,
            timestamp=time.time()
        )

    def get_pending_confirmation(self, session_id: str) -> Optional[ConfirmationState]:
        """Get pending confirmation if not expired."""
        session = self._get_session(session_id)
        pending = session.pending_confirmation

        if pending is None:
            return None

        # Check timeout
        if time.time() - pending.timestamp > self.confirmation_timeout:
            session.pending_confirmation = None
            return None

        return pending

    def clear_pending_confirmation(self, session_id: str) -> None:
        """Clear pending confirmation."""
        session = self._get_session(session_id)
        session.pending_confirmation = None

    def evaluate(
        self,
        session_id: str,
        intent: DroneIntent,
        slots: ParsedSlots,
        normalized_command: str,
        confirm: Optional[bool] = None
    ) -> Tuple[ExecutionStatus, str, Optional[ConfirmationState]]:
        """
        Evaluate a command against safety policies.

        Args:
            session_id: Session identifier
            intent: The parsed intent
            slots: The parsed slots
            normalized_command: Human-readable command string
            confirm: True if user is confirming a previous command

        Returns:
            (status, message, pending_state if needs_confirm)
        """
        # STOP is always allowed - immediate override
        if self.is_immediate_override(intent):
            self.clear_pending_confirmation(session_id)  # Cancel any pending
            return ExecutionStatus.OK, "Emergency stop - executing immediately", None

        # Check rate limit
        allowed, error_msg = self.check_rate_limit(session_id)
        if not allowed:
            return ExecutionStatus.RATE_LIMITED, error_msg, None

        # Handle confirmation flow
        if confirm is True:
            # User is confirming - check for pending command
            pending = self.get_pending_confirmation(session_id)
            if pending is None:
                return (
                    ExecutionStatus.BLOCKED,
                    "No pending command to confirm (may have expired)",
                    None
                )
            # Clear and allow execution
            self.clear_pending_confirmation(session_id)
            return (
                ExecutionStatus.OK,
                f"Confirmed: {pending.normalized_command}",
                pending
            )

        # Check if this command requires confirmation
        if self.requires_confirmation(intent):
            self.set_pending_confirmation(session_id, intent, slots, normalized_command)
            return (
                ExecutionStatus.NEEDS_CONFIRM,
                f"Confirm '{normalized_command}'? Say 'confirm' or set confirm=true",
                self.get_pending_confirmation(session_id)
            )

        # Command allowed without confirmation
        return ExecutionStatus.OK, f"Executing: {normalized_command}", None

    def clear_session(self, session_id: str) -> None:
        """Clear all state for a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]


# Global policy gate instance
_policy_gate: Optional[PolicyGate] = None


def get_policy_gate() -> PolicyGate:
    """Get or create the global policy gate instance."""
    global _policy_gate
    if _policy_gate is None:
        _policy_gate = PolicyGate()
    return _policy_gate


def reset_policy_gate() -> None:
    """Reset the global policy gate (for testing)."""
    global _policy_gate
    _policy_gate = None
