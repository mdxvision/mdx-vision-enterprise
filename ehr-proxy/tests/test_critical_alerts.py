"""
Tests for Critical Value Alert System (Issue #105)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, '/Users/rafaelrodriguez/projects/mdx-vision-enterprise/ehr-proxy')


class TestAlertSeverity:
    """Tests for AlertSeverity enum"""

    def test_severity_values(self):
        """Should have expected severity levels"""
        from critical_alerts import AlertSeverity

        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.URGENT.value == "urgent"


class TestAlertCategory:
    """Tests for AlertCategory enum"""

    def test_category_values(self):
        """Should have expected categories"""
        from critical_alerts import AlertCategory

        assert AlertCategory.LAB.value == "lab"
        assert AlertCategory.VITAL.value == "vital"
        assert AlertCategory.ALLERGY.value == "allergy"
        assert AlertCategory.MEDICATION.value == "medication"
        assert AlertCategory.OTHER.value == "other"


class TestCriticalAlert:
    """Tests for CriticalAlert dataclass"""

    def test_alert_creation(self):
        """Should create alert with required fields"""
        from critical_alerts import CriticalAlert, AlertSeverity, AlertCategory

        alert = CriticalAlert(
            id="alert-123",
            patient_id="patient-123",
            patient_name="John Doe",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="6.5",
            unit="mEq/L",
            message="Critical potassium level detected",
            spoken_message="Critical alert: Potassium is 6.5 mEq/L.",
            action_hint="Consider repletion protocol."
        )

        assert alert.patient_id == "patient-123"
        assert alert.patient_name == "John Doe"
        assert alert.category == AlertCategory.LAB
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.value_name == "Potassium"
        assert alert.value == "6.5"
        assert alert.unit == "mEq/L"
        assert alert.acknowledged_at is None
        assert alert.id == "alert-123"

    def test_alert_is_pending(self):
        """Should correctly identify pending status"""
        from critical_alerts import CriticalAlert, AlertSeverity, AlertCategory

        alert = CriticalAlert(
            id="alert-456",
            patient_id="patient-123",
            patient_name="John Doe",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="6.5",
            unit="mEq/L",
            message="Test",
            spoken_message="Test",
            action_hint="Test"
        )

        assert alert.is_pending is True

        # Acknowledge the alert
        alert.acknowledged_at = time.time()
        assert alert.is_pending is False


class TestCriticalAlertManager:
    """Tests for CriticalAlertManager"""

    @pytest.fixture
    def manager(self):
        """Create fresh manager for each test"""
        from critical_alerts import CriticalAlertManager
        return CriticalAlertManager()

    @pytest.mark.asyncio
    async def test_queue_alert(self, manager):
        """Should queue an alert"""
        from critical_alerts import CriticalAlert, AlertSeverity, AlertCategory

        alert = CriticalAlert(
            id="alert-test-1",
            patient_id="patient-123",
            patient_name="John Doe",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="6.5",
            unit="mEq/L",
            message="Test",
            spoken_message="Test",
            action_hint="Test"
        )

        alert_id = await manager.queue_alert(alert)

        assert alert_id == alert.id
        pending = await manager.get_pending_alerts("patient-123")
        assert len(pending) == 1
        assert pending[0].id == alert_id

    @pytest.mark.asyncio
    async def test_create_and_queue_alert(self, manager):
        """Should create and queue alert in one call"""
        from critical_alerts import AlertSeverity, AlertCategory

        alert = await manager.create_and_queue_alert(
            patient_id="patient-456",
            patient_name="Jane Smith",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Glucose",
            value="450",
            unit="mg/dL",
            message="Critically high glucose"
        )

        assert alert.patient_id == "patient-456"
        assert alert.value_name == "Glucose"
        assert alert.value == "450"

        pending = await manager.get_pending_alerts("patient-456")
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_get_pending_alerts_empty(self, manager):
        """Should return empty list for patient with no alerts"""
        pending = await manager.get_pending_alerts("nonexistent-patient")
        assert pending == []

    @pytest.mark.asyncio
    async def test_get_pending_alerts_excludes_acknowledged(self, manager):
        """Should not include acknowledged alerts in pending list"""
        from critical_alerts import AcknowledgmentMethod, AlertSeverity, AlertCategory

        alert = await manager.create_and_queue_alert(
            patient_id="patient-789",
            patient_name="Bob Wilson",
            category=AlertCategory.VITAL,
            severity=AlertSeverity.HIGH,
            value_name="Heart Rate",
            value="150",
            unit="bpm"
        )

        # Acknowledge the alert
        await manager.acknowledge_alert(
            alert_id=alert.id,
            clinician_id="dr-smith",
            method=AcknowledgmentMethod.VOICE
        )

        pending = await manager.get_pending_alerts("patient-789")
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, manager):
        """Should acknowledge alert with clinician info"""
        from critical_alerts import AcknowledgmentMethod, AlertSeverity, AlertCategory

        alert = await manager.create_and_queue_alert(
            patient_id="patient-ack",
            patient_name="Alice Brown",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Sodium",
            value="160",
            unit="mEq/L"
        )

        result = await manager.acknowledge_alert(
            alert_id=alert.id,
            clinician_id="dr-jones",
            method=AcknowledgmentMethod.BUTTON
        )

        assert result is True

        # Verify alert was acknowledged
        acknowledged_alert = await manager.get_alert(alert.id)
        assert acknowledged_alert is not None
        assert acknowledged_alert.acknowledged_at is not None
        assert acknowledged_alert.acknowledged_by == "dr-jones"
        assert acknowledged_alert.acknowledgment_method == AcknowledgmentMethod.BUTTON

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self, manager):
        """Should return False for nonexistent alert"""
        from critical_alerts import AcknowledgmentMethod

        result = await manager.acknowledge_alert(
            alert_id="nonexistent-alert-id",
            clinician_id="dr-smith",
            method=AcknowledgmentMethod.VOICE
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_acknowledge_all_patient_alerts(self, manager):
        """Should acknowledge all pending alerts for a patient"""
        from critical_alerts import AcknowledgmentMethod, AlertSeverity, AlertCategory

        # Create multiple alerts
        await manager.create_and_queue_alert(
            patient_id="patient-multi",
            patient_name="Multi Alert",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="6.8"
        )
        await manager.create_and_queue_alert(
            patient_id="patient-multi",
            patient_name="Multi Alert",
            category=AlertCategory.VITAL,
            severity=AlertSeverity.HIGH,
            value_name="BP Systolic",
            value="200"
        )
        await manager.create_and_queue_alert(
            patient_id="patient-multi",
            patient_name="Multi Alert",
            category=AlertCategory.LAB,
            severity=AlertSeverity.WARNING,
            value_name="Creatinine",
            value="2.5"
        )

        count = await manager.acknowledge_patient_alerts(
            patient_id="patient-multi",
            clinician_id="dr-all",
            method=AcknowledgmentMethod.VOICE
        )

        assert count == 3

        # Verify all are acknowledged
        pending = await manager.get_pending_alerts("patient-multi")
        assert len(pending) == 0


class TestVoiceAnnouncement:
    """Tests for voice announcement generation"""

    @pytest.fixture
    def manager(self):
        from critical_alerts import CriticalAlertManager
        return CriticalAlertManager()

    @pytest.mark.asyncio
    async def test_voice_announcement_critical(self, manager):
        """Should generate urgent voice announcement for critical alerts"""
        from critical_alerts import AlertSeverity, AlertCategory

        await manager.create_and_queue_alert(
            patient_id="voice-patient",
            patient_name="Voice Test",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="7.0",
            unit="mEq/L"
        )

        response = await manager.get_voice_announcement(
            patient_id="voice-patient",
            patient_name="Voice Test"
        )

        assert response.has_critical is True
        assert response.pending_count == 1
        assert "critical" in response.spoken_message.lower()
        assert "potassium" in response.spoken_message.lower()

    @pytest.mark.asyncio
    async def test_voice_announcement_no_alerts(self, manager):
        """Should indicate no alerts when none pending"""
        response = await manager.get_voice_announcement(
            patient_id="no-alerts-patient",
            patient_name="No Alerts"
        )

        assert response.has_critical is False
        assert response.pending_count == 0

    @pytest.mark.asyncio
    async def test_voice_announcement_multiple_alerts(self, manager):
        """Should combine multiple alerts in announcement"""
        from critical_alerts import AlertSeverity, AlertCategory

        await manager.create_and_queue_alert(
            patient_id="multi-voice",
            patient_name="Multi Voice",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="6.5"
        )
        await manager.create_and_queue_alert(
            patient_id="multi-voice",
            patient_name="Multi Voice",
            category=AlertCategory.VITAL,
            severity=AlertSeverity.HIGH,
            value_name="Heart Rate",
            value="160"
        )

        response = await manager.get_voice_announcement(
            patient_id="multi-voice",
            patient_name="Multi Voice"
        )

        assert response.has_critical is True
        assert response.pending_count == 2


class TestEscalationWorkflow:
    """Tests for alert escalation"""

    @pytest.fixture
    def manager(self):
        from critical_alerts import CriticalAlertManager
        # Use short escalation timeout for testing
        return CriticalAlertManager(escalation_timeout=1)

    @pytest.mark.asyncio
    async def test_escalation_after_timeout(self, manager):
        """Should escalate unacknowledged alerts after timeout"""
        from critical_alerts import AlertSeverity, AlertCategory

        alert = await manager.create_and_queue_alert(
            patient_id="escalate-patient",
            patient_name="Escalate Test",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Troponin",
            value="5.0"
        )

        # Force alert timestamp to be in the past
        alert.created_at = time.time() - 5

        escalated = await manager.check_escalations()

        assert len(escalated) == 1
        assert escalated[0].id == alert.id

    @pytest.mark.asyncio
    async def test_no_escalation_if_acknowledged(self, manager):
        """Should not escalate acknowledged alerts"""
        from critical_alerts import AcknowledgmentMethod, AlertSeverity, AlertCategory

        alert = await manager.create_and_queue_alert(
            patient_id="no-escalate",
            patient_name="No Escalate",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="BNP",
            value="1500"
        )

        # Acknowledge immediately
        await manager.acknowledge_alert(
            alert_id=alert.id,
            clinician_id="dr-quick",
            method=AcknowledgmentMethod.VOICE
        )

        # Force timestamp to be in the past
        alert.created_at = time.time() - 5

        escalated = await manager.check_escalations()
        assert len(escalated) == 0


class TestAlertStats:
    """Tests for alert statistics"""

    @pytest.fixture
    def manager(self):
        from critical_alerts import CriticalAlertManager
        return CriticalAlertManager()

    @pytest.mark.asyncio
    async def test_stats_initial(self, manager):
        """Should have zero stats initially"""
        stats = manager.get_stats()

        assert stats["total_alerts"] == 0
        assert stats["acknowledged_alerts"] == 0
        assert stats["pending_alerts"] == 0

    @pytest.mark.asyncio
    async def test_stats_after_alerts(self, manager):
        """Should track alert statistics"""
        from critical_alerts import AcknowledgmentMethod, AlertSeverity, AlertCategory

        await manager.create_and_queue_alert(
            patient_id="stats-patient",
            patient_name="Stats Test",
            category=AlertCategory.LAB,
            severity=AlertSeverity.CRITICAL,
            value_name="Potassium",
            value="6.5"
        )

        alert2 = await manager.create_and_queue_alert(
            patient_id="stats-patient",
            patient_name="Stats Test",
            category=AlertCategory.VITAL,
            severity=AlertSeverity.HIGH,
            value_name="Heart Rate",
            value="140"
        )

        # Acknowledge one
        await manager.acknowledge_alert(
            alert_id=alert2.id,
            clinician_id="dr-stats",
            method=AcknowledgmentMethod.BUTTON
        )

        stats = manager.get_stats()

        assert stats["total_alerts"] == 2
        assert stats["acknowledged_alerts"] == 1
        assert stats["pending_alerts"] == 1


class TestDetectCriticalValues:
    """Tests for critical value detection from patient data"""

    @pytest.fixture
    def manager(self):
        from critical_alerts import CriticalAlertManager
        return CriticalAlertManager()

    @pytest.mark.asyncio
    async def test_detect_critical_potassium(self, manager):
        """Should detect critical potassium level"""
        lab_results = {
            "potassium": {"value": 6.8, "unit": "mEq/L"},
            "sodium": {"value": 140, "unit": "mEq/L"}  # Normal
        }

        alerts = await manager.detect_critical_values(
            patient_id="detect-patient",
            patient_name="Detect Test",
            lab_results=lab_results
        )

        assert len(alerts) == 1
        assert alerts[0].value_name.lower() == "potassium"
        assert alerts[0].value == "6.8"

    @pytest.mark.asyncio
    async def test_detect_critical_glucose(self, manager):
        """Should detect critically high glucose"""
        lab_results = {
            "glucose": {"value": 500, "unit": "mg/dL"}
        }

        alerts = await manager.detect_critical_values(
            patient_id="glucose-patient",
            patient_name="Glucose Test",
            lab_results=lab_results
        )

        assert len(alerts) >= 1
        glucose_alert = next((a for a in alerts if "glucose" in a.value_name.lower()), None)
        assert glucose_alert is not None

    @pytest.mark.asyncio
    async def test_detect_multiple_critical(self, manager):
        """Should detect multiple critical values"""
        lab_results = {
            "potassium": {"value": 7.0, "unit": "mEq/L"},
            "sodium": {"value": 165, "unit": "mEq/L"},
            "glucose": {"value": 40, "unit": "mg/dL"}  # Critically low
        }

        alerts = await manager.detect_critical_values(
            patient_id="multi-critical",
            patient_name="Multi Critical",
            lab_results=lab_results
        )

        assert len(alerts) >= 2  # At least potassium and sodium/glucose

    @pytest.mark.asyncio
    async def test_detect_normal_values(self, manager):
        """Should not alert for normal values"""
        lab_results = {
            "potassium": {"value": 4.0, "unit": "mEq/L"},
            "sodium": {"value": 140, "unit": "mEq/L"},
            "glucose": {"value": 100, "unit": "mg/dL"}
        }

        alerts = await manager.detect_critical_values(
            patient_id="normal-patient",
            patient_name="Normal Test",
            lab_results=lab_results
        )

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_detect_vital_signs(self, manager):
        """Should detect critical vital signs"""
        vitals = {
            "heart_rate": {"value": 180, "unit": "bpm"},
            "systolic_bp": {"value": 220, "unit": "mmHg"}
        }

        alerts = await manager.detect_critical_values(
            patient_id="vital-patient",
            patient_name="Vital Test",
            vital_signs=vitals
        )

        assert len(alerts) >= 1


class TestGlobalFunctions:
    """Tests for module-level functions"""

    @pytest.mark.asyncio
    async def test_get_alert_manager(self):
        """Should return global manager instance"""
        from critical_alerts import get_alert_manager, shutdown_alert_manager

        manager = await get_alert_manager()
        assert manager is not None

        # Same instance on second call
        manager2 = await get_alert_manager()
        assert manager is manager2

        # Cleanup
        await shutdown_alert_manager()

    @pytest.mark.asyncio
    async def test_shutdown_alert_manager(self):
        """Should shutdown cleanly"""
        from critical_alerts import get_alert_manager, shutdown_alert_manager

        await get_alert_manager()
        await shutdown_alert_manager()

        # Should be able to get new instance
        manager = await get_alert_manager()
        assert manager is not None

        await shutdown_alert_manager()


class TestVoiceMessageGeneration:
    """Tests for voice message generation functions"""

    def test_generate_critical_spoken_message(self):
        """Should generate TTS-friendly message"""
        from critical_alerts import generate_critical_spoken_message, AlertSeverity

        message = generate_critical_spoken_message(
            value_name="Potassium",
            value="6.8",
            unit="mEq/L",
            severity=AlertSeverity.CRITICAL
        )

        assert "Critical" in message
        assert "Potassium" in message
        assert "6.8" in message
        assert "mEq/L" in message

    def test_generate_blood_pressure_message(self):
        """Should format blood pressure correctly for speech"""
        from critical_alerts import generate_critical_spoken_message, AlertSeverity

        message = generate_critical_spoken_message(
            value_name="blood pressure",
            value="180/120",
            unit="mmHg",
            severity=AlertSeverity.CRITICAL
        )

        assert "180 over 120" in message

    def test_generate_action_hint(self):
        """Should generate appropriate action hints"""
        from critical_alerts import generate_action_hint, AlertCategory, AlertSeverity

        hint = generate_action_hint(
            category=AlertCategory.LAB,
            value_name="Potassium",
            severity=AlertSeverity.CRITICAL
        )

        assert "repletion" in hint.lower() or "order" in hint.lower()
