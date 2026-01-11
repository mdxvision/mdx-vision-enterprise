"""
HIPAA Audit Logging for MDx Vision EHR Proxy

Provides structured JSON logging for all PHI access, note operations,
and safety-critical events for HIPAA compliance.

Log files are stored in ./logs/audit.log with automatic rotation.
"""

import logging
from logging.handlers import RotatingFileHandler
import json
import os
from datetime import datetime, timezone
from typing import Optional


class AuditAction:
    """Audit action types for HIPAA compliance tracking"""
    # PHI Access
    PHI_ACCESS = "PHI_ACCESS"
    VIEW_PATIENT = "VIEW_PATIENT"
    SEARCH_PATIENT = "SEARCH_PATIENT"
    LOOKUP_MRN = "LOOKUP_MRN"
    VIEW_NOTES = "VIEW_NOTES"

    # Note Operations
    GENERATE_NOTE = "GENERATE_NOTE"
    GENERATE_DDX = "GENERATE_DDX"
    ANALYZE_IMAGE = "ANALYZE_IMAGE"
    SAVE_NOTE = "SAVE_NOTE"
    PUSH_NOTE = "PUSH_NOTE"

    # CRUD Write-Back Operations
    PUSH_VITAL = "PUSH_VITAL"
    PUSH_ORDER = "PUSH_ORDER"
    PUSH_ALLERGY = "PUSH_ALLERGY"
    UPDATE_MEDICATION = "UPDATE_MEDICATION"
    DISCONTINUE_MEDICATION = "DISCONTINUE_MEDICATION"

    # Billing Operations
    CREATE_CLAIM = "CREATE_CLAIM"
    UPDATE_CLAIM = "UPDATE_CLAIM"
    SUBMIT_CLAIM = "SUBMIT_CLAIM"
    VIEW_CLAIM = "VIEW_CLAIM"

    # Worklist Operations
    VIEW_WORKLIST = "VIEW_WORKLIST"
    CHECK_IN_PATIENT = "CHECK_IN_PATIENT"
    UPDATE_WORKLIST_STATUS = "UPDATE_WORKLIST_STATUS"
    ADD_TO_WORKLIST = "ADD_TO_WORKLIST"

    # Transcription
    START_TRANSCRIPTION = "START_TRANSCRIPTION"
    END_TRANSCRIPTION = "END_TRANSCRIPTION"

    # Safety Events
    CRITICAL_ALERT = "CRITICAL_ALERT"
    DRUG_INTERACTION = "DRUG_INTERACTION"
    SAFETY_CHECK_BLOCKED = "SAFETY_CHECK_BLOCKED"


class AuditLogger:
    """
    HIPAA-compliant audit logger with rotating file storage.

    Logs are written in JSON Lines format for easy parsing and analysis.
    File rotation: 10MB max size, keeps 10 backup files.
    """

    def __init__(self, log_dir: str = "logs", log_file: str = "audit.log"):
        """
        Initialize the audit logger.

        Args:
            log_dir: Directory for log files (created if doesn't exist)
            log_file: Name of the audit log file
        """
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, log_file)

        # Create logger
        self.logger = logging.getLogger("hipaa_audit")
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Rotating file handler: 10MB max, keep 10 backups
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=10,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.INFO)

            # JSON formatter (just the message, we build JSON ourselves)
            file_handler.setFormatter(logging.Formatter("%(message)s"))

            self.logger.addHandler(file_handler)

        print(f"📋 HIPAA Audit Logger initialized: {log_path}")

    def log(
        self,
        action: str,
        patient_id: Optional[str] = None,
        details: Optional[dict] = None,
        **kwargs
    ) -> None:
        """
        Generic log method for audit events.

        Args:
            action: Action from AuditAction class
            patient_id: Patient identifier
            details: Additional details dict
            **kwargs: Extra fields
        """
        self._log_event(
            event_type="AUDIT",
            action=action,
            patient_id=patient_id,
            details=details,
            **kwargs
        )
        detail_str = f" - {details.get('endpoint', '')}" if details else ""
        patient_str = f" - Patient {patient_id}" if patient_id else ""
        print(f"📋 AUDIT: {action}{patient_str}{detail_str}")

    def _log_event(self, event_type: str, action: str, **kwargs) -> None:
        """
        Log an audit event in JSON format.

        Args:
            event_type: Category of event (PHI_ACCESS, NOTE_OPERATION, etc.)
            action: Specific action (VIEW_PATIENT, SAVE_NOTE, etc.)
            **kwargs: Additional event-specific fields
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "action": action,
        }

        # Add all additional fields, filtering out None values
        for key, value in kwargs.items():
            if value is not None:
                event[key] = value

        # Log as JSON line
        self.logger.info(json.dumps(event, default=str))

    def log_phi_access(
        self,
        action: str,
        patient_id: str,
        patient_name: Optional[str] = None,
        endpoint: Optional[str] = None,
        status: str = "success",
        details: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_type: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log PHI (Protected Health Information) access event.

        Args:
            action: Type of access (VIEW_PATIENT, SEARCH_PATIENT, etc.)
            patient_id: Patient identifier accessed
            patient_name: Patient name (for audit trail)
            endpoint: API endpoint accessed
            status: success or failure
            details: Additional context (resources accessed, etc.)
            user_id: Identifier of user accessing data
            user_name: Name of clinician
            ip_address: Source IP address
            device_type: Type of device (android_glasses, web, etc.)
            user_agent: User-Agent header
        """
        self._log_event(
            event_type="PHI_ACCESS",
            action=action,
            patient_id=patient_id,
            patient_name=patient_name,
            endpoint=endpoint,
            status=status,
            details=details,
            user_id=user_id,
            user_name=user_name,
            ip_address=ip_address,
            device_type=device_type,
            user_agent=user_agent
        )

        # Also print for console visibility
        print(f"🔐 AUDIT: {action} - Patient {patient_id} - {status}")

    def log_note_operation(
        self,
        action: str,
        note_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        note_type: Optional[str] = None,
        status: str = "success",
        details: Optional[str] = None,
        signed_by: Optional[str] = None,
        was_edited: Optional[bool] = None,
        fhir_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log clinical note operation.

        Args:
            action: Type of operation (GENERATE_NOTE, SAVE_NOTE, PUSH_NOTE)
            note_id: Internal note identifier
            patient_id: Associated patient
            note_type: SOAP, PROGRESS, HP, CONSULT
            status: success or failure
            details: Additional context
            signed_by: Clinician who signed the note
            was_edited: Whether note was manually edited
            fhir_id: FHIR DocumentReference ID if pushed
            user_id: User performing operation
            ip_address: Source IP
        """
        self._log_event(
            event_type="NOTE_OPERATION",
            action=action,
            note_id=note_id,
            patient_id=patient_id,
            note_type=note_type,
            status=status,
            details=details,
            signed_by=signed_by,
            was_edited=was_edited,
            fhir_id=fhir_id,
            user_id=user_id,
            ip_address=ip_address
        )

        print(f"📝 AUDIT: {action} - Note {note_id or 'new'} - {status}")

    def log_safety_event(
        self,
        action: str,
        patient_id: str,
        details: str,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        value: Optional[str] = None,
        threshold: Optional[str] = None
    ) -> None:
        """
        Log safety-critical clinical event.

        Args:
            action: CRITICAL_ALERT or DRUG_INTERACTION
            patient_id: Patient with the alert
            details: Description of the alert
            severity: high, moderate, low
            alert_type: Specific type (vital, lab, drug pair)
            value: Actual value detected
            threshold: Threshold that was exceeded
        """
        self._log_event(
            event_type="SAFETY_ALERT",
            action=action,
            patient_id=patient_id,
            details=details,
            severity=severity,
            alert_type=alert_type,
            value=value,
            threshold=threshold
        )

        print(f"🚨 AUDIT: {action} - Patient {patient_id} - {details[:50]}")

    def log_session_event(
        self,
        action: str,
        session_id: str,
        patient_id: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log transcription session event.

        Args:
            action: START_TRANSCRIPTION or END_TRANSCRIPTION
            session_id: Transcription session identifier
            patient_id: Associated patient
            duration_seconds: Session duration (for END events)
            user_id: User who started session
            ip_address: Source IP
        """
        self._log_event(
            event_type="SESSION",
            action=action,
            session_id=session_id,
            patient_id=patient_id,
            duration_seconds=duration_seconds,
            user_id=user_id,
            ip_address=ip_address
        )

        duration_str = f" ({duration_seconds}s)" if duration_seconds else ""
        print(f"🎙️ AUDIT: {action} - Session {session_id}{duration_str}")


# Global audit logger instance
audit_logger = AuditLogger()


def log_audit_event(
    event_type: str,
    action: str,
    patient_id: Optional[str] = None,
    details: Optional[dict] = None,
    **kwargs
) -> None:
    """
    Convenience function to log audit events using the global audit_logger.

    This provides a simplified interface for logging various event types
    without needing to call specific methods on the AuditLogger instance.

    Args:
        event_type: Category of event (e.g., "implicit_bias_check", "maternal_health_assessment")
        action: Specific action being performed
        patient_id: Patient identifier (optional)
        details: Dictionary of additional details
        **kwargs: Additional fields to include in the log
    """
    audit_logger._log_event(
        event_type=event_type,
        action=action,
        patient_id=patient_id,
        details=details,
        **kwargs
    )

    # Console output for visibility
    detail_str = f" - {action}" if action else ""
    patient_str = f" - Patient {patient_id}" if patient_id else ""
    print(f"📋 AUDIT: {event_type}{detail_str}{patient_str}")


def log_phi_access(
    action: str,
    patient_id: str,
    patient_name: Optional[str] = None,
    endpoint: Optional[str] = None,
    status: str = "success",
    details: Optional[str] = None,
    **kwargs
) -> None:
    """
    Convenience function to log PHI access using the global audit_logger.

    Args:
        action: Type of access (VIEW_PATIENT, SEARCH_PATIENT, etc.)
        patient_id: Patient identifier accessed
        patient_name: Patient name (for audit trail)
        endpoint: API endpoint accessed
        status: success or failure
        details: Additional context
        **kwargs: Extra fields
    """
    audit_logger.log_phi_access(
        action=action,
        patient_id=patient_id,
        patient_name=patient_name,
        endpoint=endpoint,
        status=status,
        details=details,
        **kwargs
    )
