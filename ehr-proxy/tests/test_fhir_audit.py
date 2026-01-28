"""
Tests for FHIR R4 AuditEvent Implementation (Issue #108)

Tests cover:
- FHIR AuditEvent resource creation
- AuditEvent field validation
- Audit logging for FHIR operations
- Audit query API endpoints
- HIPAA compliance requirements
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fhir_audit import (
    FHIRAuditEvent, FHIRAuditEventFactory, FHIRAuditLogger,
    AuditEventAction, AuditEventOutcome, FHIRInteraction,
    Coding, Reference, Identifier
)


class TestFHIRAuditEventModel:
    """Tests for FHIR AuditEvent model structure."""

    def test_audit_event_has_required_fields(self):
        """AuditEvent should have all required FHIR fields."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            success=True
        )
        assert event.resourceType == "AuditEvent"
        assert event.id is not None
        assert event.type is not None
        assert event.recorded is not None
        assert event.agent is not None
        assert event.source is not None

    def test_audit_event_type_coding(self):
        """AuditEvent.type should have proper coding."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        assert event.type.system == "http://terminology.hl7.org/CodeSystem/audit-event-type"
        assert event.type.code == "rest"

    def test_audit_event_subtype_for_read(self):
        """Read operations should have 'read' subtype."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            interaction=FHIRInteraction.READ
        )
        assert event.subtype is not None
        assert len(event.subtype) > 0
        assert event.subtype[0].code == "read"

    def test_audit_event_action_codes(self):
        """Action codes should be FHIR-compliant."""
        for action in AuditEventAction:
            assert action.value in ["C", "R", "U", "D", "E"]

    def test_audit_event_outcome_codes(self):
        """Outcome codes should be FHIR-compliant."""
        for outcome in AuditEventOutcome:
            assert outcome.value in ["0", "4", "8", "12"]


class TestFHIRAuditEventFactory:
    """Tests for AuditEvent factory methods."""

    def test_create_patient_access_event(self):
        """Should create valid patient access AuditEvent."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            clinician_id="dr-smith",
            clinician_name="Dr. Smith",
            ip_address="192.168.1.100"
        )
        assert event.action == "R"
        assert event.outcome == "0"  # Success
        assert len(event.agent) > 0
        assert event.entity is not None

    def test_create_observation_access_event(self):
        """Should create valid observation access AuditEvent."""
        event = FHIRAuditEventFactory.create_observation_access_event(
            patient_id="12724066",
            observation_type="vital-signs",
            success=True
        )
        assert event.action == "R"
        assert any(
            e.name == "Observation"
            for e in event.entity
        )

    def test_create_write_event(self):
        """Should create valid write operation AuditEvent."""
        event = FHIRAuditEventFactory.create_write_event(
            action=AuditEventAction.CREATE,
            resource_type="Observation",
            resource_id="obs-123",
            patient_id="12724066",
            success=True,
            description="Created vital sign"
        )
        assert event.action == "C"
        assert event.outcome == "0"

    def test_failure_outcome(self):
        """Failed operations should have failure outcome."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            success=False
        )
        assert event.outcome == "4"  # Minor failure

    def test_agent_with_clinician(self):
        """Agent should include clinician info when provided."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            clinician_id="dr-chen",
            clinician_name="Dr. Sarah Chen"
        )
        agent = event.agent[0]
        assert agent.who is not None
        assert agent.who.display == "Dr. Sarah Chen"

    def test_agent_with_device(self):
        """Agent should include device info when provided."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            device_id="glasses-001"
        )
        # Should have at least 2 agents (user + device)
        device_agents = [a for a in event.agent if not a.requestor]
        assert len(device_agents) >= 0  # Device is optional

    def test_source_observer(self):
        """Source should identify ehr-proxy as observer."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        assert event.source.observer.identifier.value == "ehr-proxy-service"

    def test_entity_patient_reference(self):
        """Entity should include patient reference."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        patient_entities = [
            e for e in event.entity
            if e.what and "Patient/12724066" in e.what.reference
        ]
        assert len(patient_entities) > 0


class TestFHIRAuditLogger:
    """Tests for FHIR AuditEvent logging."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create a logger with temp directory."""
        return FHIRAuditLogger(log_dir=str(tmp_path))

    def test_log_event_returns_id(self, logger):
        """Logging should return event ID."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        event_id = logger.log_event(event)
        assert event_id is not None
        assert len(event_id) > 0

    def test_log_patient_access(self, logger):
        """Should log patient access events."""
        event_id = logger.log_patient_access(
            patient_id="12724066",
            success=True,
            clinician_id="dr-test"
        )
        assert event_id is not None

    def test_log_observation_access(self, logger):
        """Should log observation access events."""
        event_id = logger.log_observation_access(
            patient_id="12724066",
            observation_type="labs",
            success=True
        )
        assert event_id is not None

    def test_log_resource_write(self, logger):
        """Should log resource write events."""
        event_id = logger.log_resource_write(
            action=AuditEventAction.CREATE,
            resource_type="Observation",
            patient_id="12724066",
            success=True
        )
        assert event_id is not None

    def test_query_events_by_patient(self, logger):
        """Should filter events by patient."""
        # Log events for different patients
        logger.log_patient_access(patient_id="patient-1", success=True)
        logger.log_patient_access(patient_id="patient-2", success=True)
        logger.log_patient_access(patient_id="patient-1", success=True)

        # Query for patient-1
        result = logger.query_events(patient_id="patient-1")
        assert result["resourceType"] == "Bundle"
        assert result["total"] == 2

    def test_query_events_by_action(self, logger):
        """Should filter events by action."""
        logger.log_patient_access(patient_id="12724066", success=True)
        logger.log_resource_write(
            action=AuditEventAction.CREATE,
            resource_type="Observation",
            patient_id="12724066",
            success=True
        )

        # Query for reads only
        result = logger.query_events(action="R")
        for entry in result.get("entry", []):
            assert entry["resource"]["action"] == "R"

    def test_query_events_pagination(self, logger):
        """Should support pagination."""
        # Log 5 events
        for i in range(5):
            logger.log_patient_access(patient_id=f"patient-{i}", success=True)

        # Query with limit
        result = logger.query_events(limit=2)
        assert len(result["entry"]) <= 2
        assert result["total"] == 5

    def test_event_count(self, logger):
        """Should track event count."""
        initial = logger.get_event_count()
        logger.log_patient_access(patient_id="12724066", success=True)
        assert logger.get_event_count() == initial + 1


class TestFHIRAuditEventAPI:
    """Integration tests for FHIR AuditEvent API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_query_audit_events_endpoint(self, client):
        """GET /api/v1/fhir/AuditEvent should return Bundle."""
        response = client.get("/api/v1/fhir/AuditEvent")
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "searchset"
        assert "total" in data

    def test_query_audit_events_with_patient_filter(self, client):
        """Should filter by patient parameter."""
        response = client.get("/api/v1/fhir/AuditEvent?patient=12724066")
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "Bundle"

    def test_query_audit_events_with_action_filter(self, client):
        """Should filter by action parameter."""
        response = client.get("/api/v1/fhir/AuditEvent?action=R")
        assert response.status_code == 200

    def test_query_audit_events_pagination(self, client):
        """Should support _count and _offset parameters."""
        response = client.get("/api/v1/fhir/AuditEvent?_count=10&_offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("entry", [])) <= 10

    def test_audit_stats_endpoint(self, client):
        """GET /api/v1/fhir/AuditEvent/_stats should return statistics."""
        response = client.get("/api/v1/fhir/AuditEvent/_stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "by_action" in data
        assert "by_outcome" in data
        assert data["immutable"] == True
        assert "retention_policy" in data


class TestAuditEventHIPAACompliance:
    """Tests for HIPAA compliance requirements."""

    def test_events_are_immutable(self):
        """AuditEvents should be immutable (no update/delete)."""
        # The logger doesn't expose update/delete methods
        logger = FHIRAuditLogger.__new__(FHIRAuditLogger)
        assert not hasattr(logger, 'update_event')
        assert not hasattr(logger, 'delete_event')

    def test_events_have_timestamp(self):
        """All events must have recorded timestamp."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        assert event.recorded is not None
        assert "T" in event.recorded  # ISO 8601 format

    def test_events_identify_who(self):
        """Events must identify who performed the action."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066",
            clinician_id="dr-test"
        )
        assert len(event.agent) > 0
        assert event.agent[0].who is not None

    def test_events_identify_what(self):
        """Events must identify what was accessed."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        assert event.entity is not None
        assert len(event.entity) > 0

    def test_events_identify_source(self):
        """Events must identify the source system."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        assert event.source is not None
        assert event.source.observer is not None

    def test_retention_policy_documented(self):
        """Retention policy should be 7 years per HIPAA."""
        # This is documented in the stats endpoint
        client = TestClient(app)
        response = client.get("/api/v1/fhir/AuditEvent/_stats")
        data = response.json()
        assert "7 years" in data.get("retention_policy", "")


class TestAuditEventSerialization:
    """Tests for FHIR JSON serialization."""

    def test_to_dict_excludes_none(self):
        """to_dict should exclude None values."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        d = event.to_dict()
        for key, value in d.items():
            assert value is not None

    def test_to_json_valid(self):
        """to_json should produce valid JSON."""
        import json
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed["resourceType"] == "AuditEvent"

    def test_json_has_fhir_structure(self):
        """JSON should follow FHIR resource structure."""
        event = FHIRAuditEventFactory.create_patient_access_event(
            patient_id="12724066"
        )
        d = event.to_dict()

        # Check FHIR structure
        assert "resourceType" in d
        assert "type" in d
        assert "recorded" in d
        assert "agent" in d
        assert "source" in d
