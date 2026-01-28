"""
FHIR R4 AuditEvent Resource Implementation (Issue #108)

Provides FHIR-compliant audit event logging for all PHI access and modifications.
Implements the FHIR R4 AuditEvent resource specification.

References:
- https://www.hl7.org/fhir/auditevent.html
- HIPAA Security Rule §164.312(b) - Audit Controls
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field
from logging.handlers import RotatingFileHandler
import logging


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR AuditEvent Enums and Types
# ═══════════════════════════════════════════════════════════════════════════════

class AuditEventAction(str, Enum):
    """FHIR AuditEvent action codes."""
    CREATE = "C"
    READ = "R"
    UPDATE = "U"
    DELETE = "D"
    EXECUTE = "E"


class AuditEventOutcome(str, Enum):
    """FHIR AuditEvent outcome codes."""
    SUCCESS = "0"
    MINOR_FAILURE = "4"
    SERIOUS_FAILURE = "8"
    MAJOR_FAILURE = "12"


class AuditEventType(str, Enum):
    """Common audit event type codes."""
    REST = "rest"
    EXPORT = "export"
    IMPORT = "import"
    QUERY = "query"
    APPLICATION = "application-activity"


class FHIRInteraction(str, Enum):
    """FHIR RESTful interaction types."""
    READ = "read"
    VREAD = "vread"
    UPDATE = "update"
    PATCH = "patch"
    DELETE = "delete"
    CREATE = "create"
    SEARCH = "search"
    BATCH = "batch"
    TRANSACTION = "transaction"
    OPERATION = "operation"


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR AuditEvent Models (Pydantic)
# ═══════════════════════════════════════════════════════════════════════════════

class Coding(BaseModel):
    """FHIR Coding element."""
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None


class CodeableConcept(BaseModel):
    """FHIR CodeableConcept element."""
    coding: Optional[List[Coding]] = None
    text: Optional[str] = None


class Identifier(BaseModel):
    """FHIR Identifier element."""
    system: Optional[str] = None
    value: Optional[str] = None


class Reference(BaseModel):
    """FHIR Reference element."""
    reference: Optional[str] = None
    identifier: Optional[Identifier] = None
    display: Optional[str] = None


class AuditEventAgent(BaseModel):
    """FHIR AuditEvent.agent element - Who was involved."""
    type: Optional[CodeableConcept] = None
    who: Optional[Reference] = None
    requestor: bool = True
    network: Optional[Dict[str, str]] = None


class AuditEventSource(BaseModel):
    """FHIR AuditEvent.source element - Audit event reporter."""
    observer: Reference
    type: Optional[List[Coding]] = None


class AuditEventEntity(BaseModel):
    """FHIR AuditEvent.entity element - Data or objects used."""
    what: Optional[Reference] = None
    type: Optional[Coding] = None
    role: Optional[Coding] = None
    name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None  # Base64 encoded query


class FHIRAuditEvent(BaseModel):
    """
    FHIR R4 AuditEvent Resource.

    A record of an event made for purposes of maintaining a security log.
    """
    resourceType: str = "AuditEvent"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Coding
    subtype: Optional[List[Coding]] = None
    action: Optional[str] = None  # C | R | U | D | E
    recorded: str  # ISO 8601 timestamp
    outcome: Optional[str] = None  # 0 | 4 | 8 | 12
    outcomeDesc: Optional[str] = None
    agent: List[AuditEventAgent]
    source: AuditEventSource
    entity: Optional[List[AuditEventEntity]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to FHIR-compliant dictionary."""
        return self.model_dump(exclude_none=True, by_alias=True)

    def to_json(self) -> str:
        """Convert to FHIR JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR AuditEvent Factory
# ═══════════════════════════════════════════════════════════════════════════════

class FHIRAuditEventFactory:
    """Factory for creating FHIR-compliant AuditEvent resources."""

    # System URIs for coding
    AUDIT_EVENT_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/audit-event-type"
    FHIR_INTERACTION_SYSTEM = "http://hl7.org/fhir/restful-interaction"
    SECURITY_ROLE_SYSTEM = "http://terminology.hl7.org/CodeSystem/extra-security-role-type"
    SECURITY_SOURCE_SYSTEM = "http://terminology.hl7.org/CodeSystem/security-source-type"
    ENTITY_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/audit-entity-type"
    OBJECT_ROLE_SYSTEM = "http://terminology.hl7.org/CodeSystem/object-role"

    # MDx Vision specific systems
    MDX_CLINICIAN_SYSTEM = "http://mdxvision.com/clinician"
    MDX_DEVICE_SYSTEM = "http://mdxvision.com/device"

    @classmethod
    def create_rest_audit_event(
        cls,
        action: AuditEventAction,
        interaction: FHIRInteraction,
        outcome: AuditEventOutcome,
        resource_type: str,
        resource_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        clinician_id: Optional[str] = None,
        clinician_name: Optional[str] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        outcome_desc: Optional[str] = None
    ) -> FHIRAuditEvent:
        """
        Create a FHIR AuditEvent for a RESTful operation.

        Args:
            action: CRUD action (C, R, U, D, E)
            interaction: FHIR interaction type (read, search, create, etc.)
            outcome: Success or failure code
            resource_type: FHIR resource type accessed (Patient, Observation, etc.)
            resource_id: Specific resource ID if applicable
            patient_id: Patient ID if applicable
            clinician_id: Clinician performing the action
            clinician_name: Clinician display name
            device_id: Device ID if from glasses/mobile
            ip_address: Source IP address
            outcome_desc: Human-readable outcome description
        """
        now = datetime.now(timezone.utc).isoformat()

        # Build agent (who performed the action)
        agents = []

        # Human user agent
        if clinician_id or clinician_name:
            agents.append(AuditEventAgent(
                type=CodeableConcept(coding=[Coding(
                    system=cls.SECURITY_ROLE_SYSTEM,
                    code="humanuser",
                    display="Human User"
                )]),
                who=Reference(
                    identifier=Identifier(
                        system=cls.MDX_CLINICIAN_SYSTEM,
                        value=clinician_id or "unknown"
                    ),
                    display=clinician_name
                ),
                requestor=True,
                network={"address": ip_address, "type": "2"} if ip_address else None
            ))

        # Device agent (if from glasses)
        if device_id:
            agents.append(AuditEventAgent(
                type=CodeableConcept(coding=[Coding(
                    system=cls.SECURITY_ROLE_SYSTEM,
                    code="dataprocessor",
                    display="Data Processor"
                )]),
                who=Reference(
                    identifier=Identifier(
                        system=cls.MDX_DEVICE_SYSTEM,
                        value=device_id
                    ),
                    display="MDx Vision Glasses"
                ),
                requestor=False
            ))

        # If no agents specified, use anonymous
        if not agents:
            agents.append(AuditEventAgent(
                type=CodeableConcept(coding=[Coding(
                    system=cls.SECURITY_ROLE_SYSTEM,
                    code="humanuser",
                    display="Human User"
                )]),
                who=Reference(display="Anonymous"),
                requestor=True,
                network={"address": ip_address, "type": "2"} if ip_address else None
            ))

        # Build source (the system reporting)
        source = AuditEventSource(
            observer=Reference(
                identifier=Identifier(value="ehr-proxy-service"),
                display="MDx Vision EHR Proxy"
            ),
            type=[Coding(
                system=cls.SECURITY_SOURCE_SYSTEM,
                code="4",
                display="Application Server"
            )]
        )

        # Build entities (what was accessed)
        entities = []

        # Patient entity if applicable
        if patient_id:
            entities.append(AuditEventEntity(
                what=Reference(reference=f"Patient/{patient_id}"),
                type=Coding(
                    system=cls.ENTITY_TYPE_SYSTEM,
                    code="1",
                    display="Person"
                ),
                role=Coding(
                    system=cls.OBJECT_ROLE_SYSTEM,
                    code="1",
                    display="Patient"
                )
            ))

        # Resource entity
        resource_ref = f"{resource_type}/{resource_id}" if resource_id else resource_type
        entity_type_code = "2" if resource_type == "Patient" else "2"  # System Object
        entities.append(AuditEventEntity(
            what=Reference(reference=resource_ref),
            type=Coding(
                system=cls.ENTITY_TYPE_SYSTEM,
                code=entity_type_code,
                display="System Object"
            ),
            role=Coding(
                system=cls.OBJECT_ROLE_SYSTEM,
                code="4",
                display="Domain Resource"
            ),
            name=resource_type
        ))

        return FHIRAuditEvent(
            type=Coding(
                system=cls.AUDIT_EVENT_TYPE_SYSTEM,
                code="rest",
                display="RESTful Operation"
            ),
            subtype=[Coding(
                system=cls.FHIR_INTERACTION_SYSTEM,
                code=interaction.value,
                display=interaction.value
            )],
            action=action.value,
            recorded=now,
            outcome=outcome.value,
            outcomeDesc=outcome_desc,
            agent=agents,
            source=source,
            entity=entities if entities else None
        )

    @classmethod
    def create_patient_access_event(
        cls,
        patient_id: str,
        interaction: FHIRInteraction = FHIRInteraction.READ,
        success: bool = True,
        clinician_id: Optional[str] = None,
        clinician_name: Optional[str] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> FHIRAuditEvent:
        """Convenience method for patient access events."""
        return cls.create_rest_audit_event(
            action=AuditEventAction.READ,
            interaction=interaction,
            outcome=AuditEventOutcome.SUCCESS if success else AuditEventOutcome.MINOR_FAILURE,
            resource_type="Patient",
            resource_id=patient_id,
            patient_id=patient_id,
            clinician_id=clinician_id,
            clinician_name=clinician_name,
            device_id=device_id,
            ip_address=ip_address
        )

    @classmethod
    def create_observation_access_event(
        cls,
        patient_id: str,
        observation_type: str,
        success: bool = True,
        clinician_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> FHIRAuditEvent:
        """Convenience method for observation (vitals/labs) access events."""
        return cls.create_rest_audit_event(
            action=AuditEventAction.READ,
            interaction=FHIRInteraction.SEARCH,
            outcome=AuditEventOutcome.SUCCESS if success else AuditEventOutcome.MINOR_FAILURE,
            resource_type="Observation",
            patient_id=patient_id,
            clinician_id=clinician_id,
            ip_address=ip_address,
            outcome_desc=f"Accessed {observation_type} for patient"
        )

    @classmethod
    def create_write_event(
        cls,
        action: AuditEventAction,
        resource_type: str,
        resource_id: Optional[str],
        patient_id: str,
        success: bool = True,
        clinician_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        description: Optional[str] = None
    ) -> FHIRAuditEvent:
        """Create audit event for write operations (create/update/delete)."""
        interaction_map = {
            AuditEventAction.CREATE: FHIRInteraction.CREATE,
            AuditEventAction.UPDATE: FHIRInteraction.UPDATE,
            AuditEventAction.DELETE: FHIRInteraction.DELETE,
        }
        return cls.create_rest_audit_event(
            action=action,
            interaction=interaction_map.get(action, FHIRInteraction.OPERATION),
            outcome=AuditEventOutcome.SUCCESS if success else AuditEventOutcome.MINOR_FAILURE,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            clinician_id=clinician_id,
            ip_address=ip_address,
            outcome_desc=description
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR AuditEvent Logger
# ═══════════════════════════════════════════════════════════════════════════════

class FHIRAuditLogger:
    """
    FHIR-compliant AuditEvent logger with immutable storage.

    Stores AuditEvents in NDJSON format (newline-delimited JSON).
    Events are immutable - no updates or deletes allowed.
    """

    def __init__(self, log_dir: str = "logs", log_file: str = "fhir_audit.ndjson"):
        """
        Initialize the FHIR audit logger.

        Args:
            log_dir: Directory for log files
            log_file: Name of the FHIR audit log file
        """
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, log_file)
        self.factory = FHIRAuditEventFactory

        # Create logger with rotation
        self.logger = logging.getLogger("fhir_audit")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            # 50MB max, keep 20 backups (1GB total, ~7 years at typical usage)
            file_handler = RotatingFileHandler(
                self.log_path,
                maxBytes=50 * 1024 * 1024,
                backupCount=20,
                encoding="utf-8"
            )
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(file_handler)

        # In-memory index for quick queries (last 10000 events)
        self._recent_events: List[Dict[str, Any]] = []
        self._max_recent = 10000

        print(f"📋 FHIR AuditEvent Logger initialized: {self.log_path}")

    def log_event(self, event: FHIRAuditEvent) -> str:
        """
        Log a FHIR AuditEvent (immutable).

        Args:
            event: FHIRAuditEvent to log

        Returns:
            Event ID
        """
        event_dict = event.to_dict()
        self.logger.info(json.dumps(event_dict, separators=(',', ':')))

        # Add to recent events index
        self._recent_events.append(event_dict)
        if len(self._recent_events) > self._max_recent:
            self._recent_events.pop(0)

        return event.id

    def log_patient_access(
        self,
        patient_id: str,
        success: bool = True,
        clinician_id: Optional[str] = None,
        clinician_name: Optional[str] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log patient record access."""
        event = self.factory.create_patient_access_event(
            patient_id=patient_id,
            success=success,
            clinician_id=clinician_id,
            clinician_name=clinician_name,
            device_id=device_id,
            ip_address=ip_address
        )
        return self.log_event(event)

    def log_observation_access(
        self,
        patient_id: str,
        observation_type: str,
        success: bool = True,
        clinician_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log observation (vitals/labs) access."""
        event = self.factory.create_observation_access_event(
            patient_id=patient_id,
            observation_type=observation_type,
            success=success,
            clinician_id=clinician_id,
            ip_address=ip_address
        )
        return self.log_event(event)

    def log_resource_write(
        self,
        action: AuditEventAction,
        resource_type: str,
        patient_id: str,
        resource_id: Optional[str] = None,
        success: bool = True,
        clinician_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Log resource write operation (create/update/delete)."""
        event = self.factory.create_write_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            success=success,
            clinician_id=clinician_id,
            ip_address=ip_address,
            description=description
        )
        return self.log_event(event)

    def query_events(
        self,
        patient_id: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query audit events with filters.

        Args:
            patient_id: Filter by patient
            action: Filter by action (C, R, U, D, E)
            outcome: Filter by outcome (0, 4, 8, 12)
            start_date: Filter by start date (ISO 8601)
            end_date: Filter by end date (ISO 8601)
            limit: Maximum results
            offset: Skip first N results

        Returns:
            FHIR Bundle of matching AuditEvents
        """
        results = []

        for event in reversed(self._recent_events):
            # Apply filters
            if patient_id:
                entities = event.get("entity", [])
                patient_match = any(
                    e.get("what", {}).get("reference", "").endswith(f"Patient/{patient_id}")
                    for e in entities
                )
                if not patient_match:
                    continue

            if action and event.get("action") != action:
                continue

            if outcome and event.get("outcome") != outcome:
                continue

            if start_date:
                recorded = event.get("recorded", "")
                if recorded < start_date:
                    continue

            if end_date:
                recorded = event.get("recorded", "")
                if recorded > end_date:
                    continue

            results.append(event)

        # Apply pagination
        total = len(results)
        results = results[offset:offset + limit]

        # Return as FHIR Bundle
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
            "entry": [{"resource": r} for r in results]
        }

    def get_event_count(self) -> int:
        """Get total number of events in recent cache."""
        return len(self._recent_events)


# Global FHIR audit logger instance
fhir_audit_logger = FHIRAuditLogger()
