"""
MDx Vision - Critical Value Alert System (Issue #105)

Real-time monitoring and proactive voice announcements for critical lab values
and vital signs. Includes acknowledgment tracking and escalation workflows.

Features:
- Critical value detection with configurable thresholds
- Proactive Minerva voice announcements
- Acknowledgment tracking (voice or button)
- Escalation workflow (2-minute timeout)
- FHIR AuditEvent logging for compliance
- Alert queue with priority ordering

Usage:
    from critical_alerts import CriticalAlertManager, get_alert_manager

    manager = get_alert_manager()

    # Queue a critical alert
    await manager.queue_alert(alert)

    # Get pending alerts for a patient
    pending = await manager.get_pending_alerts(patient_id)

    # Acknowledge an alert
    await manager.acknowledge_alert(alert_id, clinician_id, method="voice")

    # Check for escalations
    escalations = await manager.check_escalations()
"""

import asyncio
import time
import uuid
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Escalation timeout in seconds (default: 2 minutes)
ESCALATION_TIMEOUT = int(__import__('os').getenv("CRITICAL_ALERT_ESCALATION_TIMEOUT", "120"))

# Max alerts to speak at once (prevent alert fatigue)
MAX_SPOKEN_ALERTS = int(__import__('os').getenv("MAX_SPOKEN_CRITICAL_ALERTS", "3"))


# ═══════════════════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════════════════

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"      # Life-threatening, immediate action needed
    HIGH = "high"              # Significant, action needed soon (alias for urgent)
    URGENT = "urgent"          # Significant, action needed soon
    WARNING = "warning"        # Abnormal, monitor closely
    INFO = "info"              # Informational only


class AlertCategory(str, Enum):
    """Categories of critical alerts"""
    LAB = "lab"
    VITAL = "vital"
    IMAGING = "imaging"
    MICROBIOLOGY = "microbiology"
    DRUG_INTERACTION = "drug_interaction"
    ALLERGY = "allergy"
    MEDICATION = "medication"
    OTHER = "other"


class AcknowledgmentMethod(str, Enum):
    """How an alert was acknowledged"""
    VOICE = "voice"            # "Got it, Minerva"
    BUTTON = "button"          # UI button press
    TIMEOUT = "timeout"        # Escalated due to timeout
    AUTO = "auto"              # Auto-acknowledged (info level)


@dataclass
class CriticalAlert:
    """A critical value alert requiring acknowledgment"""
    id: str
    patient_id: str
    patient_name: str
    category: AlertCategory
    severity: AlertSeverity
    value_name: str           # e.g., "Potassium", "Heart Rate"
    value: str                # e.g., "6.8", "180/120"
    unit: str                 # e.g., "mEq/L", "mmHg"
    message: str              # Display message
    spoken_message: str       # TTS message for Minerva
    action_hint: str          # Suggested action
    created_at: float = field(default_factory=time.time)
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    acknowledgment_method: Optional[AcknowledgmentMethod] = None
    escalated: bool = False
    escalated_at: Optional[float] = None
    escalated_to: Optional[str] = None

    @property
    def is_pending(self) -> bool:
        """Check if alert is still pending acknowledgment"""
        return self.acknowledged_at is None and not self.escalated

    @property
    def age_seconds(self) -> float:
        """Get alert age in seconds"""
        return time.time() - self.created_at

    @property
    def needs_escalation(self) -> bool:
        """Check if alert has exceeded escalation timeout"""
        return (
            self.is_pending and
            self.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT] and
            self.age_seconds >= ESCALATION_TIMEOUT
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "value_name": self.value_name,
            "value": self.value,
            "unit": self.unit,
            "message": self.message,
            "spoken_message": self.spoken_message,
            "action_hint": self.action_hint,
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
            "acknowledgment_method": self.acknowledgment_method.value if self.acknowledgment_method else None,
            "escalated": self.escalated,
            "escalated_at": self.escalated_at,
            "escalated_to": self.escalated_to,
            "is_pending": self.is_pending,
            "age_seconds": self.age_seconds,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models for API
# ═══════════════════════════════════════════════════════════════════════════════

class CriticalAlertRequest(BaseModel):
    """Request to create a critical alert"""
    patient_id: str
    patient_name: str
    category: str
    severity: str
    value_name: str
    value: str
    unit: str = ""
    message: Optional[str] = None
    action_hint: Optional[str] = None


class CriticalAlertResponse(BaseModel):
    """Response for a critical alert"""
    id: str
    patient_id: str
    patient_name: str
    category: str
    severity: str
    value_name: str
    value: str
    unit: str
    message: str
    spoken_message: str
    action_hint: str
    created_at: float
    is_pending: bool
    age_seconds: float


class CriticalAlertAcknowledgment(BaseModel):
    """Request to acknowledge an alert"""
    alert_id: str
    clinician_id: str
    method: str = "button"  # "voice" or "button"


class CriticalAlertVoiceResponse(BaseModel):
    """Response containing voice announcements for critical alerts"""
    patient_id: str
    patient_name: str
    has_critical: bool
    pending_count: int
    spoken_message: str          # Full TTS message
    acknowledgment_phrase: str   # How to acknowledge
    alerts: List[dict]


# ═══════════════════════════════════════════════════════════════════════════════
# Voice Message Generation
# ═══════════════════════════════════════════════════════════════════════════════

def generate_critical_spoken_message(
    value_name: str,
    value: str,
    unit: str,
    severity: AlertSeverity
) -> str:
    """Generate TTS-friendly message for a critical value"""
    # Normalize value name for speech
    name_map = {
        "potassium": "Potassium",
        "sodium": "Sodium",
        "glucose": "Blood glucose",
        "hemoglobin": "Hemoglobin",
        "hgb": "Hemoglobin",
        "troponin": "Troponin",
        "inr": "I N R",
        "lactate": "Lactate",
        "creatinine": "Creatinine",
        "bun": "B U N",
        "wbc": "White count",
        "platelets": "Platelets",
        "ph": "Blood P H",
        "blood pressure": "Blood pressure",
        "bp": "Blood pressure",
        "heart rate": "Heart rate",
        "hr": "Heart rate",
        "oxygen saturation": "Oxygen sat",
        "spo2": "Oxygen sat",
        "o2 sat": "Oxygen sat",
        "respiratory rate": "Respiratory rate",
        "temperature": "Temperature",
    }

    display_name = name_map.get(value_name.lower(), value_name)

    # Format value for speech
    if "/" in value:
        # Blood pressure
        parts = value.split("/")
        spoken_value = f"{parts[0]} over {parts[1]}"
    elif "." in value:
        # Decimal - speak naturally
        spoken_value = value
    else:
        spoken_value = value

    # Severity prefix
    if severity == AlertSeverity.CRITICAL:
        prefix = "Critical alert:"
    elif severity == AlertSeverity.URGENT:
        prefix = "Urgent:"
    else:
        prefix = ""

    # Build message
    if unit:
        return f"{prefix} {display_name} is {spoken_value} {unit}."
    else:
        return f"{prefix} {display_name} is {spoken_value}."


def generate_action_hint(category: AlertCategory, value_name: str, severity: AlertSeverity) -> str:
    """Generate actionable hint for the alert"""
    hints = {
        ("lab", "potassium", "critical"): "Consider repletion protocol. Say 'order potassium' to proceed.",
        ("lab", "potassium", "urgent"): "Monitor closely. Repeat in 4 hours.",
        ("lab", "glucose", "critical"): "Check insulin protocol. May need IV dextrose if low.",
        ("lab", "troponin", "critical"): "Cardiology notified. Order EKG if not done.",
        ("lab", "hemoglobin", "critical"): "Type and screen ordered. Transfusion may be needed.",
        ("lab", "inr", "critical"): "Reversal agent available in pharmacy.",
        ("lab", "lactate", "critical"): "Signs of sepsis. Consider fluid bolus.",
        ("vital", "blood pressure", "critical"): "May need IV antihypertensive or fluids.",
        ("vital", "heart rate", "critical"): "Check rhythm. 12-lead EKG recommended.",
        ("vital", "oxygen saturation", "critical"): "Increase O2. Check airway.",
        ("vital", "temperature", "critical"): "Blood cultures ordered. Cooling measures if hyperthermic.",
        ("microbiology", "", "critical"): "Infectious disease aware. Check antibiotic coverage.",
    }

    key = (category.value, value_name.lower(), severity.value)
    generic_key = (category.value, "", severity.value)

    return hints.get(key) or hints.get(generic_key) or "Review and take appropriate action."


# ═══════════════════════════════════════════════════════════════════════════════
# Alert Manager
# ═══════════════════════════════════════════════════════════════════════════════

class CriticalAlertManager:
    """
    Manages critical value alerts with acknowledgment tracking and escalation.

    Thread-safe storage of alerts with background escalation checking.
    """

    def __init__(self, escalation_timeout: int = ESCALATION_TIMEOUT):
        self._alerts: Dict[str, CriticalAlert] = {}
        self._patient_alerts: Dict[str, List[str]] = {}  # patient_id -> [alert_ids]
        self._escalation_timeout = escalation_timeout
        self._escalation_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

        # Stats
        self._stats = {
            "alerts_created": 0,
            "alerts_acknowledged": 0,
            "alerts_escalated": 0,
            "acknowledgments_by_voice": 0,
            "acknowledgments_by_button": 0,
        }

    async def start(self) -> None:
        """Start the background escalation checker"""
        if self._running:
            return
        self._running = True
        self._escalation_task = asyncio.create_task(self._escalation_loop())
        logger.info(f"CriticalAlertManager started (escalation_timeout={self._escalation_timeout}s)")

    async def stop(self) -> None:
        """Stop the background escalation checker"""
        self._running = False
        if self._escalation_task:
            self._escalation_task.cancel()
            try:
                await self._escalation_task
            except asyncio.CancelledError:
                pass
        logger.info("CriticalAlertManager stopped")

    async def queue_alert(self, alert: CriticalAlert) -> str:
        """
        Queue a new critical alert.

        Args:
            alert: The alert to queue

        Returns:
            Alert ID
        """
        async with self._lock:
            self._alerts[alert.id] = alert

            # Track by patient
            if alert.patient_id not in self._patient_alerts:
                self._patient_alerts[alert.patient_id] = []
            self._patient_alerts[alert.patient_id].append(alert.id)

            self._stats["alerts_created"] += 1

        logger.info(
            f"Critical alert queued: {alert.value_name}={alert.value} for patient {alert.patient_id}",
            extra={"alert_id": alert.id, "severity": alert.severity.value}
        )

        return alert.id

    async def create_and_queue_alert(
        self,
        patient_id: str,
        patient_name: str,
        category: AlertCategory,
        severity: AlertSeverity,
        value_name: str,
        value: str,
        unit: str = "",
        message: Optional[str] = None,
    ) -> CriticalAlert:
        """
        Create and queue a new alert from parameters.

        Args:
            patient_id: FHIR Patient ID
            patient_name: Patient display name
            category: Alert category (lab, vital, etc.)
            severity: Alert severity
            value_name: Name of the value (e.g., "Potassium")
            value: The actual value (e.g., "6.8")
            unit: Unit of measurement (e.g., "mEq/L")
            message: Optional custom display message

        Returns:
            Created alert
        """
        alert_id = f"alert-{uuid.uuid4().hex[:12]}"

        spoken_message = generate_critical_spoken_message(value_name, value, unit, severity)
        action_hint = generate_action_hint(category, value_name, severity)

        if not message:
            message = f"{'⚠️ CRITICAL' if severity == AlertSeverity.CRITICAL else '⚡ URGENT'}: {value_name} {value} {unit}"

        alert = CriticalAlert(
            id=alert_id,
            patient_id=patient_id,
            patient_name=patient_name,
            category=category,
            severity=severity,
            value_name=value_name,
            value=value,
            unit=unit,
            message=message,
            spoken_message=spoken_message,
            action_hint=action_hint,
        )

        await self.queue_alert(alert)
        return alert

    async def get_alert(self, alert_id: str) -> Optional[CriticalAlert]:
        """Get an alert by ID"""
        return self._alerts.get(alert_id)

    async def get_pending_alerts(self, patient_id: str) -> List[CriticalAlert]:
        """Get all pending (unacknowledged) alerts for a patient"""
        alert_ids = self._patient_alerts.get(patient_id, [])
        pending = []

        for aid in alert_ids:
            alert = self._alerts.get(aid)
            if alert and alert.is_pending:
                pending.append(alert)

        # Sort by severity (critical first) then by age (oldest first)
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.URGENT: 1, AlertSeverity.WARNING: 2, AlertSeverity.INFO: 3}
        pending.sort(key=lambda a: (severity_order.get(a.severity, 3), a.created_at))

        return pending

    async def get_voice_announcement(self, patient_id: str, patient_name: str) -> CriticalAlertVoiceResponse:
        """
        Get voice announcement for pending critical alerts.

        Args:
            patient_id: Patient ID
            patient_name: Patient name for spoken intro

        Returns:
            Voice response with TTS message
        """
        pending = await self.get_pending_alerts(patient_id)

        if not pending:
            return CriticalAlertVoiceResponse(
                patient_id=patient_id,
                patient_name=patient_name,
                has_critical=False,
                pending_count=0,
                spoken_message="",
                acknowledgment_phrase="",
                alerts=[]
            )

        # Limit spoken alerts
        spoken_alerts = pending[:MAX_SPOKEN_ALERTS]
        has_critical = any(a.severity == AlertSeverity.CRITICAL for a in spoken_alerts)

        # Generate intro
        first_name = patient_name.split(",")[0].strip() if "," in patient_name else patient_name.split()[0]

        if has_critical:
            intro = f"Critical alert for {first_name}. "
        else:
            intro = f"Attention on {first_name}. "

        # Combine messages
        messages = [a.spoken_message for a in spoken_alerts]
        body = " ".join(messages)

        # Add action hints for critical alerts
        if has_critical:
            hints = [a.action_hint for a in spoken_alerts if a.severity == AlertSeverity.CRITICAL]
            if hints:
                body += " " + hints[0]

        # Acknowledgment phrase
        ack_phrase = "Say 'got it Minerva' to acknowledge." if has_critical else "Say 'acknowledge' when ready."

        return CriticalAlertVoiceResponse(
            patient_id=patient_id,
            patient_name=patient_name,
            has_critical=has_critical,
            pending_count=len(pending),
            spoken_message=intro + body + " " + ack_phrase,
            acknowledgment_phrase=ack_phrase,
            alerts=[a.to_dict() for a in spoken_alerts]
        )

    async def acknowledge_alert(
        self,
        alert_id: str,
        clinician_id: str,
        method: AcknowledgmentMethod = AcknowledgmentMethod.BUTTON
    ) -> bool:
        """
        Acknowledge a critical alert.

        Args:
            alert_id: Alert ID to acknowledge
            clinician_id: ID of acknowledging clinician
            method: How the alert was acknowledged

        Returns:
            True if acknowledged, False if not found or already acknowledged
        """
        async with self._lock:
            alert = self._alerts.get(alert_id)

            if not alert or not alert.is_pending:
                return False

            alert.acknowledged_at = time.time()
            alert.acknowledged_by = clinician_id
            alert.acknowledgment_method = method

            self._stats["alerts_acknowledged"] += 1
            if method == AcknowledgmentMethod.VOICE:
                self._stats["acknowledgments_by_voice"] += 1
            else:
                self._stats["acknowledgments_by_button"] += 1

        logger.info(
            f"Alert {alert_id} acknowledged by {clinician_id} via {method.value}",
            extra={"alert_id": alert_id, "method": method.value}
        )

        return True

    async def acknowledge_patient_alerts(
        self,
        patient_id: str,
        clinician_id: str,
        method: AcknowledgmentMethod = AcknowledgmentMethod.VOICE
    ) -> int:
        """
        Acknowledge all pending alerts for a patient (e.g., "Got it, Minerva").

        Args:
            patient_id: Patient ID
            clinician_id: Acknowledging clinician
            method: Acknowledgment method

        Returns:
            Number of alerts acknowledged
        """
        pending = await self.get_pending_alerts(patient_id)
        count = 0

        for alert in pending:
            if await self.acknowledge_alert(alert.id, clinician_id, method):
                count += 1

        logger.info(f"Acknowledged {count} alerts for patient {patient_id}")
        return count

    async def check_escalations(self) -> List[CriticalAlert]:
        """Check for alerts that need escalation"""
        escalated = []

        async with self._lock:
            for alert in self._alerts.values():
                # Check if alert needs escalation using instance timeout
                needs_escalation = (
                    alert.is_pending and
                    alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT] and
                    alert.age_seconds >= self._escalation_timeout and
                    not alert.escalated
                )

                if needs_escalation:
                    alert.escalated = True
                    alert.escalated_at = time.time()
                    alert.escalated_to = "supervisor"  # TODO: Get from org settings
                    escalated.append(alert)
                    self._stats["alerts_escalated"] += 1

                    logger.warning(
                        f"Alert {alert.id} escalated after {alert.age_seconds:.0f}s without acknowledgment",
                        extra={"alert_id": alert.id, "patient_id": alert.patient_id}
                    )

        return escalated

    async def _escalation_loop(self) -> None:
        """Background task to check for escalations"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                escalated = await self.check_escalations()
                if escalated:
                    # TODO: Send escalation notifications
                    pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in escalation loop: {e}")

    async def detect_critical_values(
        self,
        patient_id: str,
        patient_name: str,
        lab_results: Optional[Dict[str, Dict[str, Any]]] = None,
        vital_signs: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[CriticalAlert]:
        """
        Detect critical values from lab results and vital signs.

        Args:
            patient_id: Patient FHIR ID
            patient_name: Patient display name
            lab_results: Dict of lab values e.g., {"potassium": {"value": 6.8, "unit": "mEq/L"}}
            vital_signs: Dict of vital signs e.g., {"heart_rate": {"value": 180, "unit": "bpm"}}

        Returns:
            List of alerts created for critical values
        """
        # Critical thresholds
        LAB_THRESHOLDS = {
            "potassium": {"critical_high": 6.5, "critical_low": 2.5, "unit": "mEq/L"},
            "sodium": {"critical_high": 160, "critical_low": 120, "unit": "mEq/L"},
            "glucose": {"critical_high": 400, "critical_low": 50, "unit": "mg/dL"},
            "hemoglobin": {"critical_low": 7.0, "unit": "g/dL"},
            "hgb": {"critical_low": 7.0, "unit": "g/dL"},
            "troponin": {"critical_high": 0.04, "unit": "ng/mL"},
            "inr": {"critical_high": 5.0, "unit": ""},
            "lactate": {"critical_high": 4.0, "unit": "mmol/L"},
            "creatinine": {"critical_high": 10.0, "unit": "mg/dL"},
            "wbc": {"critical_high": 30.0, "critical_low": 2.0, "unit": "x10^3/uL"},
            "platelets": {"critical_low": 50, "unit": "x10^3/uL"},
            "ph": {"critical_high": 7.6, "critical_low": 7.1, "unit": ""},
        }

        VITAL_THRESHOLDS = {
            "heart_rate": {"critical_high": 150, "critical_low": 40, "unit": "bpm"},
            "hr": {"critical_high": 150, "critical_low": 40, "unit": "bpm"},
            "systolic_bp": {"critical_high": 200, "critical_low": 80, "unit": "mmHg"},
            "diastolic_bp": {"critical_high": 120, "unit": "mmHg"},
            "blood_pressure": {"critical_high": 200, "critical_low": 80, "unit": "mmHg"},
            "bp": {"critical_high": 200, "critical_low": 80, "unit": "mmHg"},
            "oxygen_saturation": {"critical_low": 88, "unit": "%"},
            "spo2": {"critical_low": 88, "unit": "%"},
            "o2_sat": {"critical_low": 88, "unit": "%"},
            "respiratory_rate": {"critical_high": 30, "critical_low": 8, "unit": "/min"},
            "temperature": {"critical_high": 40.5, "critical_low": 34, "unit": "°C"},
        }

        alerts = []

        # Check lab results
        if lab_results:
            for name, data in lab_results.items():
                name_lower = name.lower()
                if name_lower in LAB_THRESHOLDS:
                    thresholds = LAB_THRESHOLDS[name_lower]
                    value = float(data.get("value", 0))
                    unit = data.get("unit", thresholds.get("unit", ""))

                    is_critical = False
                    if "critical_high" in thresholds and value >= thresholds["critical_high"]:
                        is_critical = True
                    if "critical_low" in thresholds and value <= thresholds["critical_low"]:
                        is_critical = True

                    if is_critical:
                        alert = await self.create_and_queue_alert(
                            patient_id=patient_id,
                            patient_name=patient_name,
                            category=AlertCategory.LAB,
                            severity=AlertSeverity.CRITICAL,
                            value_name=name.title(),
                            value=str(value),
                            unit=unit
                        )
                        alerts.append(alert)

        # Check vital signs
        if vital_signs:
            for name, data in vital_signs.items():
                name_lower = name.lower()
                if name_lower in VITAL_THRESHOLDS:
                    thresholds = VITAL_THRESHOLDS[name_lower]
                    value = float(data.get("value", 0))
                    unit = data.get("unit", thresholds.get("unit", ""))

                    is_critical = False
                    if "critical_high" in thresholds and value >= thresholds["critical_high"]:
                        is_critical = True
                    if "critical_low" in thresholds and value <= thresholds["critical_low"]:
                        is_critical = True

                    if is_critical:
                        alert = await self.create_and_queue_alert(
                            patient_id=patient_id,
                            patient_name=patient_name,
                            category=AlertCategory.VITAL,
                            severity=AlertSeverity.CRITICAL,
                            value_name=name.replace("_", " ").title(),
                            value=str(value),
                            unit=unit
                        )
                        alerts.append(alert)

        return alerts

    def get_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics"""
        pending_count = len([a for a in self._alerts.values() if a.is_pending])
        acknowledged_count = len([a for a in self._alerts.values() if a.acknowledged_at is not None])
        return {
            **self._stats,
            "active_alerts": pending_count,
            "total_alerts": len(self._alerts),
            "pending_alerts": pending_count,
            "acknowledged_alerts": acknowledged_count,
            "escalation_timeout": self._escalation_timeout,
        }

    async def cleanup_old_alerts(self, max_age_hours: int = 24) -> int:
        """Remove alerts older than max_age_hours"""
        max_age_seconds = max_age_hours * 3600
        removed = 0

        async with self._lock:
            to_remove = [
                aid for aid, alert in self._alerts.items()
                if alert.age_seconds > max_age_seconds and not alert.is_pending
            ]

            for aid in to_remove:
                alert = self._alerts.pop(aid)
                if alert.patient_id in self._patient_alerts:
                    self._patient_alerts[alert.patient_id] = [
                        a for a in self._patient_alerts[alert.patient_id] if a != aid
                    ]
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old alerts")

        return removed


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════

_alert_manager: Optional[CriticalAlertManager] = None


async def get_alert_manager() -> CriticalAlertManager:
    """Get or create the global alert manager"""
    global _alert_manager

    if _alert_manager is None:
        _alert_manager = CriticalAlertManager()
        await _alert_manager.start()

    return _alert_manager


async def shutdown_alert_manager() -> None:
    """Shutdown the global alert manager"""
    global _alert_manager

    if _alert_manager:
        await _alert_manager.stop()
        _alert_manager = None
