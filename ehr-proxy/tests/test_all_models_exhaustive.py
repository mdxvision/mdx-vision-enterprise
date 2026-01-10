"""
Exhaustive tests for ALL Pydantic models in main.py.
Tests every model class with all field combinations.
"""
import pytest
from datetime import datetime


class TestVitalSignModel:
    """Tests for VitalSign model"""

    def test_vital_sign_all_fields(self):
        """Should create VitalSign with all fields"""
        from main import VitalSign
        vital = VitalSign(
            name="Heart Rate",
            value="72",
            unit="bpm",
            date="2024-01-15",
            interpretation="N",
            is_critical=False,
            is_abnormal=False,
            previous_value="68",
            previous_date="2024-01-14",
            trend="rising",
            delta="+4"
        )
        assert vital.name == "Heart Rate"
        assert vital.value == "72"
        assert vital.unit == "bpm"
        assert vital.date == "2024-01-15"
        assert vital.interpretation == "N"
        assert vital.is_critical is False
        assert vital.is_abnormal is False
        assert vital.previous_value == "68"
        assert vital.previous_date == "2024-01-14"
        assert vital.trend == "rising"
        assert vital.delta == "+4"

    def test_vital_sign_minimal(self):
        """Should create VitalSign with minimal fields"""
        from main import VitalSign
        vital = VitalSign(name="BP", value="120/80", unit="mmHg")
        assert vital.name == "BP"
        assert vital.date == ""
        assert vital.interpretation == ""
        assert vital.is_critical is False

    def test_vital_sign_critical(self):
        """Should create critical vital sign"""
        from main import VitalSign
        vital = VitalSign(
            name="SpO2",
            value="85",
            unit="%",
            is_critical=True,
            is_abnormal=True,
            interpretation="LL"
        )
        assert vital.is_critical is True
        assert vital.interpretation == "LL"


class TestLabResultModel:
    """Tests for LabResult model"""

    def test_lab_result_all_fields(self):
        """Should create LabResult with all fields"""
        from main import LabResult
        lab = LabResult(
            name="Potassium",
            value="5.2",
            unit="mEq/L",
            status="final",
            date="2024-01-15",
            reference_range="3.5-5.0 mEq/L",
            interpretation="H",
            is_critical=False,
            is_abnormal=True,
            previous_value="4.8",
            previous_date="2024-01-10",
            trend="rising",
            delta="+0.4"
        )
        assert lab.name == "Potassium"
        assert lab.value == "5.2"
        assert lab.unit == "mEq/L"
        assert lab.status == "final"
        assert lab.reference_range == "3.5-5.0 mEq/L"
        assert lab.is_abnormal is True
        assert lab.trend == "rising"

    def test_lab_result_minimal(self):
        """Should create LabResult with minimal fields"""
        from main import LabResult
        lab = LabResult(name="Glucose", value="95", unit="mg/dL", status="final")
        assert lab.name == "Glucose"
        assert lab.reference_range == ""
        assert lab.is_critical is False

    def test_lab_result_critical(self):
        """Should create critical lab result"""
        from main import LabResult
        lab = LabResult(
            name="Troponin",
            value="0.15",
            unit="ng/mL",
            status="final",
            is_critical=True,
            is_abnormal=True,
            interpretation="HH"
        )
        assert lab.is_critical is True
        assert lab.interpretation == "HH"


class TestProcedureModel:
    """Tests for Procedure model"""

    def test_procedure_all_fields(self):
        """Should create Procedure with all fields"""
        from main import Procedure
        proc = Procedure(
            name="Appendectomy",
            date="2024-01-10",
            status="completed"
        )
        assert proc.name == "Appendectomy"
        assert proc.date == "2024-01-10"
        assert proc.status == "completed"

    def test_procedure_minimal(self):
        """Should create Procedure with minimal fields"""
        from main import Procedure
        proc = Procedure(name="Blood draw")
        assert proc.name == "Blood draw"
        assert proc.date == ""
        assert proc.status == ""


class TestImmunizationModel:
    """Tests for Immunization model"""

    def test_immunization_all_fields(self):
        """Should create Immunization with all fields"""
        from main import Immunization
        imm = Immunization(
            name="COVID-19 Vaccine",
            date="2024-01-01",
            status="completed"
        )
        assert imm.name == "COVID-19 Vaccine"
        assert imm.date == "2024-01-01"
        assert imm.status == "completed"

    def test_immunization_minimal(self):
        """Should create Immunization with minimal fields"""
        from main import Immunization
        imm = Immunization(name="Flu Shot")
        assert imm.name == "Flu Shot"


class TestConditionModel:
    """Tests for Condition model"""

    def test_condition_all_fields(self):
        """Should create Condition with all fields"""
        from main import Condition
        cond = Condition(
            name="Type 2 Diabetes",
            status="active",
            onset="2020-05-15",
            category="encounter-diagnosis"
        )
        assert cond.name == "Type 2 Diabetes"
        assert cond.status == "active"
        assert cond.onset == "2020-05-15"
        assert cond.category == "encounter-diagnosis"

    def test_condition_minimal(self):
        """Should create Condition with minimal fields"""
        from main import Condition
        cond = Condition(name="Hypertension")
        assert cond.name == "Hypertension"
        assert cond.status == ""


class TestCarePlanModel:
    """Tests for CarePlan model"""

    def test_care_plan_all_fields(self):
        """Should create CarePlan with all fields"""
        from main import CarePlan
        plan = CarePlan(
            title="Diabetes Management",
            status="active",
            intent="plan",
            category="Disease Management",
            period_start="2024-01-01",
            period_end="2024-12-31",
            description="Monitor blood sugar and take medications as prescribed"
        )
        assert plan.title == "Diabetes Management"
        assert plan.status == "active"
        assert plan.intent == "plan"
        assert plan.category == "Disease Management"
        assert plan.period_start == "2024-01-01"
        assert plan.period_end == "2024-12-31"
        assert plan.description == "Monitor blood sugar and take medications as prescribed"

    def test_care_plan_minimal(self):
        """Should create CarePlan with minimal fields"""
        from main import CarePlan
        plan = CarePlan(title="Follow-up Care")
        assert plan.title == "Follow-up Care"
        assert plan.status == ""


class TestClinicalNoteModel:
    """Tests for ClinicalNote model"""

    def test_clinical_note_all_fields(self):
        """Should create ClinicalNote with all fields"""
        from main import ClinicalNote
        note = ClinicalNote(
            title="Progress Note",
            doc_type="Progress Note",
            date="2024-01-15",
            author="Dr. Smith",
            status="current",
            content_preview="Patient reports improvement in symptoms..."
        )
        assert note.title == "Progress Note"
        assert note.doc_type == "Progress Note"
        assert note.date == "2024-01-15"
        assert note.author == "Dr. Smith"
        assert note.status == "current"
        assert note.content_preview.startswith("Patient reports")

    def test_clinical_note_minimal(self):
        """Should create ClinicalNote with minimal fields"""
        from main import ClinicalNote
        note = ClinicalNote(title="Office Visit")
        assert note.title == "Office Visit"
        assert note.doc_type == ""


class TestMedicationInteractionModel:
    """Tests for MedicationInteraction model"""

    def test_interaction_all_fields(self):
        """Should create MedicationInteraction with all fields"""
        from main import MedicationInteraction
        interaction = MedicationInteraction(
            drug1="Warfarin",
            drug2="Aspirin",
            severity="high",
            effect="Increased bleeding risk"
        )
        assert interaction.drug1 == "Warfarin"
        assert interaction.drug2 == "Aspirin"
        assert interaction.severity == "high"
        assert interaction.effect == "Increased bleeding risk"

    def test_interaction_minimal(self):
        """Should create MedicationInteraction with minimal fields"""
        from main import MedicationInteraction
        interaction = MedicationInteraction(drug1="DrugA", drug2="DrugB")
        assert interaction.severity == "moderate"  # default
        assert interaction.effect == ""


class TestPatientSummaryModel:
    """Tests for PatientSummary model"""

    def test_patient_summary_all_fields(self):
        """Should create PatientSummary with all fields"""
        from main import PatientSummary, VitalSign, LabResult, MedicationInteraction
        summary = PatientSummary(
            patient_id="12345",
            name="John Doe",
            date_of_birth="1990-01-15",
            gender="male",
            mrn="MRN-12345",
            photo_url="data:image/jpeg;base64,abc123",
            vitals=[VitalSign(name="HR", value="72", unit="bpm")],
            critical_vitals=[],
            abnormal_vitals=[],
            has_critical_vitals=False,
            allergies=["Penicillin"],
            medications=["Metformin 500mg"],
            medication_interactions=[MedicationInteraction(drug1="A", drug2="B")],
            has_interactions=True,
            labs=[LabResult(name="Glucose", value="95", unit="mg/dL", status="final")],
            critical_labs=[],
            abnormal_labs=[],
            has_critical_labs=False,
            display_text="John Doe - 34yo M"
        )
        assert summary.patient_id == "12345"
        assert summary.name == "John Doe"
        assert summary.mrn == "MRN-12345"
        assert summary.has_interactions is True
        assert len(summary.vitals) == 1
        assert len(summary.medications) == 1

    def test_patient_summary_minimal(self):
        """Should create PatientSummary with minimal fields"""
        from main import PatientSummary
        summary = PatientSummary(
            patient_id="12345",
            name="Jane Doe",
            date_of_birth="1985-05-20",
            gender="female"
        )
        assert summary.patient_id == "12345"
        assert summary.mrn is None
        assert summary.vitals == []


class TestSearchResultModel:
    """Tests for SearchResult model"""

    def test_search_result(self):
        """Should create SearchResult"""
        from main import SearchResult
        result = SearchResult(
            patient_id="12345",
            name="John Doe",
            date_of_birth="1990-01-15",
            gender="male"
        )
        assert result.patient_id == "12345"
        assert result.name == "John Doe"


class TestWorklistPatientModel:
    """Tests for WorklistPatient model"""

    def test_worklist_patient_all_fields(self):
        """Should create WorklistPatient with all fields"""
        from main import WorklistPatient
        patient = WorklistPatient(
            patient_id="12345",
            name="John Doe",
            date_of_birth="1990-01-15",
            gender="male",
            mrn="MRN-12345",
            room="Room 5",
            appointment_time="09:00",
            appointment_type="Follow-up",
            chief_complaint="Chest pain",
            provider="Dr. Smith",
            status="checked_in",
            checked_in_at="2024-01-15T09:05:00",
            encounter_started_at=None,
            has_critical_alerts=True,
            priority=2
        )
        assert patient.patient_id == "12345"
        assert patient.room == "Room 5"
        assert patient.status == "checked_in"
        assert patient.priority == 2

    def test_worklist_patient_minimal(self):
        """Should create WorklistPatient with minimal fields"""
        from main import WorklistPatient
        patient = WorklistPatient(
            patient_id="12345",
            name="Jane Doe",
            date_of_birth="1985-05-20",
            gender="female"
        )
        assert patient.status == "scheduled"
        assert patient.priority == 0


class TestWorklistResponseModel:
    """Tests for WorklistResponse model"""

    def test_worklist_response(self):
        """Should create WorklistResponse"""
        from main import WorklistResponse, WorklistPatient
        response = WorklistResponse(
            date="2024-01-15",
            provider="Dr. Smith",
            location="Clinic A",
            patients=[
                WorklistPatient(
                    patient_id="12345",
                    name="John Doe",
                    date_of_birth="1990-01-15",
                    gender="male"
                )
            ],
            total_scheduled=5,
            checked_in=2,
            in_progress=1,
            completed=1
        )
        assert response.date == "2024-01-15"
        assert response.total_scheduled == 5
        assert len(response.patients) == 1


class TestCheckInRequestModel:
    """Tests for CheckInRequest model"""

    def test_check_in_request_all_fields(self):
        """Should create CheckInRequest with all fields"""
        from main import CheckInRequest
        req = CheckInRequest(
            patient_id="12345",
            room="Room 3",
            chief_complaint="Headache"
        )
        assert req.patient_id == "12345"
        assert req.room == "Room 3"
        assert req.chief_complaint == "Headache"

    def test_check_in_request_minimal(self):
        """Should create CheckInRequest with minimal fields"""
        from main import CheckInRequest
        req = CheckInRequest(patient_id="12345")
        assert req.patient_id == "12345"
        assert req.room is None


class TestUpdateWorklistStatusRequestModel:
    """Tests for UpdateWorklistStatusRequest model"""

    def test_update_status_request(self):
        """Should create UpdateWorklistStatusRequest"""
        from main import UpdateWorklistStatusRequest
        req = UpdateWorklistStatusRequest(
            patient_id="12345",
            status="in_progress",
            room="Room 5",
            notes="Started exam"
        )
        assert req.patient_id == "12345"
        assert req.status == "in_progress"


class TestOrderUpdateRequestModel:
    """Tests for OrderUpdateRequest model"""

    def test_order_update_request(self):
        """Should create OrderUpdateRequest"""
        from main import OrderUpdateRequest
        req = OrderUpdateRequest(
            order_id="order-123",
            patient_id="patient-456",
            priority="urgent",
            dose="500mg",
            frequency="BID",
            notes="Updated per physician order",
            cancel=False
        )
        assert req.order_id == "order-123"
        assert req.priority == "urgent"
        assert req.cancel is False


class TestDdxModels:
    """Tests for Differential Diagnosis models"""

    def test_ddx_request(self):
        """Should create DdxRequest"""
        from main import DdxRequest
        req = DdxRequest(
            chief_complaint="Chest pain",
            symptoms=["shortness of breath", "diaphoresis"],
            vitals={"hr": "110", "bp": "140/90"},
            age=55,
            gender="male",
            medical_history=["hypertension", "diabetes"],
            medications=["metformin", "lisinopril"],
            allergies=["penicillin"]
        )
        assert req.chief_complaint == "Chest pain"
        assert len(req.symptoms) == 2
        assert req.age == 55

    def test_differential_diagnosis(self):
        """Should create DifferentialDiagnosis"""
        from main import DifferentialDiagnosis
        ddx = DifferentialDiagnosis(
            rank=1,
            diagnosis="Acute Coronary Syndrome",
            icd10_code="I21.9",
            likelihood="high",
            supporting_findings=["chest pain", "diaphoresis", "risk factors"],
            red_flags=["ST elevation", "troponin elevation"],
            next_steps=["ECG", "troponin", "cardiology consult"]
        )
        assert ddx.rank == 1
        assert ddx.icd10_code == "I21.9"

    def test_ddx_response(self):
        """Should create DdxResponse"""
        from main import DdxResponse, DifferentialDiagnosis
        response = DdxResponse(
            differentials=[
                DifferentialDiagnosis(
                    rank=1,
                    diagnosis="ACS",
                    icd10_code="I21.9",
                    likelihood="high",
                    supporting_findings=["chest pain"]
                )
            ],
            clinical_reasoning="Patient presents with classic ACS symptoms",
            urgent_considerations=["Rule out STEMI"],
            timestamp="2024-01-15T10:00:00"
        )
        assert len(response.differentials) == 1
        assert response.clinical_reasoning.startswith("Patient")


class TestImageAnalysisModels:
    """Tests for Image Analysis models"""

    def test_image_analysis_request(self):
        """Should create ImageAnalysisRequest"""
        from main import ImageAnalysisRequest
        req = ImageAnalysisRequest(
            image_base64="base64imagedata",
            media_type="image/png",
            patient_id="12345",
            analysis_context="wound",
            chief_complaint="Leg wound",
            patient_age=65,
            patient_gender="male"
        )
        assert req.image_base64 == "base64imagedata"
        assert req.analysis_context == "wound"

    def test_image_finding(self):
        """Should create ImageFinding"""
        from main import ImageFinding
        finding = ImageFinding(
            finding="Erythema",
            confidence="high",
            location="Left lower leg",
            characteristics=["circular", "raised border", "central clearing"]
        )
        assert finding.finding == "Erythema"
        assert finding.confidence == "high"

    def test_image_analysis_response(self):
        """Should create ImageAnalysisResponse"""
        from main import ImageAnalysisResponse, ImageFinding
        response = ImageAnalysisResponse(
            assessment="Consistent with cellulitis",
            findings=[ImageFinding(finding="Erythema", confidence="high")],
            icd10_codes=[{"code": "L03.90", "description": "Cellulitis"}],
            recommendations=["Oral antibiotics", "Elevation"],
            red_flags=["Fever", "Spreading erythema"],
            differential_considerations=["Abscess", "DVT"],
            disclaimer="For clinical decision support only",
            timestamp="2024-01-15T10:00:00"
        )
        assert response.assessment == "Consistent with cellulitis"
        assert len(response.findings) == 1


class TestCopilotModels:
    """Tests for AI Clinical Co-pilot models (Feature #78)"""

    def test_copilot_message(self):
        """Should create CopilotMessage"""
        from main import CopilotMessage
        msg = CopilotMessage(role="user", content="What should I order for chest pain?")
        assert msg.role == "user"
        assert "chest pain" in msg.content

    def test_copilot_action(self):
        """Should create CopilotAction"""
        from main import CopilotAction
        action = CopilotAction(
            action_type="order",
            label="Order ECG",
            command="order ECG"
        )
        assert action.action_type == "order"
        assert action.command == "order ECG"

    def test_copilot_request(self):
        """Should create CopilotRequest"""
        from main import CopilotRequest, CopilotMessage
        req = CopilotRequest(
            message="What tests should I order?",
            patient_context={"conditions": ["diabetes"]},
            conversation_history=[
                CopilotMessage(role="user", content="Patient has chest pain")
            ],
            include_actions=True
        )
        assert req.message == "What tests should I order?"
        assert len(req.conversation_history) == 1

    def test_copilot_response(self):
        """Should create CopilotResponse"""
        from main import CopilotResponse, CopilotAction
        response = CopilotResponse(
            response="Based on the symptoms, I recommend ECG and troponin.",
            suggestions=["What about imaging?", "Should I consult cardiology?"],
            actions=[CopilotAction(action_type="order", label="ECG", command="order ECG")],
            references=["I21.9"],
            timestamp="2024-01-15T10:00:00"
        )
        assert "ECG" in response.response
        assert len(response.actions) == 1


class TestRacialMedicineModels:
    """Tests for Racial Medicine Awareness models (Feature #79)"""

    def test_fitzpatrick_skin_type_enum(self):
        """Should have all Fitzpatrick types"""
        from main import FitzpatrickSkinType
        assert FitzpatrickSkinType.TYPE_I.value == "I"
        assert FitzpatrickSkinType.TYPE_VI.value == "VI"

    def test_racial_medicine_alert(self):
        """Should create RacialMedicineAlert"""
        from main import RacialMedicineAlert
        alert = RacialMedicineAlert(
            alert_type="pulse_ox",
            severity="warning",
            title="Pulse Oximeter Accuracy",
            message="SpO2 may overestimate by 1-4% in darker skin tones",
            recommendation="Consider ABG if clinical concern",
            evidence_source="Sjoding et al., NEJM 2020"
        )
        assert alert.alert_type == "pulse_ox"
        assert "overestimate" in alert.message

    def test_patient_physiologic_profile(self):
        """Should create PatientPhysiologicProfile"""
        from main import PatientPhysiologicProfile, FitzpatrickSkinType
        profile = PatientPhysiologicProfile(
            fitzpatrick_type=FitzpatrickSkinType.TYPE_V,
            self_reported_ancestry=["African"],
            pharmacogenomic_tested=True,
            known_genetic_variants=["CYP2D6"],
            sickle_cell_status="trait",
            g6pd_status="normal"
        )
        assert profile.fitzpatrick_type == FitzpatrickSkinType.TYPE_V
        assert profile.sickle_cell_status == "trait"

    def test_racial_medicine_request(self):
        """Should create RacialMedicineRequest"""
        from main import RacialMedicineRequest, FitzpatrickSkinType
        req = RacialMedicineRequest(
            patient_id="12345",
            fitzpatrick_type=FitzpatrickSkinType.TYPE_IV,
            self_reported_ancestry=["Hispanic"],
            clinical_context="vitals",
            current_readings={"spo2": 94},
            pending_orders=["lisinopril"]
        )
        assert req.patient_id == "12345"
        assert req.clinical_context == "vitals"

    def test_racial_medicine_response(self):
        """Should create RacialMedicineResponse"""
        from main import RacialMedicineResponse, RacialMedicineAlert
        response = RacialMedicineResponse(
            alerts=[
                RacialMedicineAlert(
                    alert_type="medication",
                    severity="info",
                    title="ACE Inhibitor Consideration",
                    message="May be less effective in certain populations",
                    recommendation="Consider alternative if inadequate response"
                )
            ],
            skin_assessment_guidance={"cyanosis": "Check nail beds and conjunctiva"},
            medication_considerations=[{"drug": "lisinopril", "note": "May need dose adjustment"}],
            calculator_warnings=["Using race-free eGFR formula"],
            timestamp="2024-01-15T10:00:00"
        )
        assert len(response.alerts) == 1
        assert response.skin_assessment_guidance is not None


class TestCulturalCareModels:
    """Tests for Cultural Care Preferences models (Feature #80)"""

    def test_blood_product_preference(self):
        """Should create BloodProductPreference"""
        from main import BloodProductPreference
        prefs = BloodProductPreference(
            whole_blood=False,
            red_cells=False,
            white_cells=False,
            platelets=False,
            plasma=False,
            albumin=True,  # Individual conscience
            immunoglobulins=True,
            cell_salvage=True,
            hemodilution=None
        )
        assert prefs.whole_blood is False
        assert prefs.albumin is True

    def test_decision_making_style_enum(self):
        """Should have all decision making styles"""
        from main import DecisionMakingStyle
        assert DecisionMakingStyle.INDIVIDUAL.value == "individual"
        assert DecisionMakingStyle.FAMILY_CENTERED.value == "family_centered"
        assert DecisionMakingStyle.PATRIARCH_LED.value == "patriarch_led"

    def test_communication_preference_enum(self):
        """Should have all communication preferences"""
        from main import CommunicationPreference
        assert CommunicationPreference.DIRECT.value == "direct"
        assert CommunicationPreference.FAMILY_FIRST.value == "family_first"

    def test_cultural_care_preferences(self):
        """Should create CulturalCarePreferences"""
        from main import CulturalCarePreferences, DecisionMakingStyle, CommunicationPreference, BloodProductPreference
        prefs = CulturalCarePreferences(
            religion="Islam",
            dietary_restrictions=["halal", "no pork"],
            blood_product_preferences=BloodProductPreference(whole_blood=True),
            decision_making_style=DecisionMakingStyle.FAMILY_CENTERED,
            primary_decision_maker="Father",
            communication_preference=CommunicationPreference.FAMILY_PRESENT,
            provider_gender_preference="female",
            interpreter_needed=False,
            preferred_language="en",
            modesty_requirements=["same_gender_provider"],
            religious_garments=["hijab"],
            fasting_status="ramadan",
            traditional_medicine=["curanderismo"],
            end_of_life_preferences={"dnr": True},
            family_contacts_for_decisions=[{"name": "Ahmed", "relationship": "father", "phone": "555-1234"}]
        )
        assert prefs.religion == "Islam"
        assert "halal" in prefs.dietary_restrictions
        assert prefs.fasting_status == "ramadan"

    def test_cultural_care_alert(self):
        """Should create CulturalCareAlert"""
        from main import CulturalCareAlert
        alert = CulturalCareAlert(
            alert_type="dietary",
            severity="warning",
            title="Halal Diet Required",
            message="Patient requires halal meals",
            recommendation="Order halal meal tray"
        )
        assert alert.alert_type == "dietary"


class TestImplicitBiasModels:
    """Tests for Implicit Bias models (Feature #81)"""

    def test_implicit_bias_context_enum(self):
        """Should have all bias contexts"""
        from main import ImplicitBiasContext
        assert ImplicitBiasContext.PAIN_ASSESSMENT.value == "pain_assessment"
        assert ImplicitBiasContext.TRIAGE.value == "triage"
        assert ImplicitBiasContext.CARDIAC_SYMPTOMS.value == "cardiac_symptoms"

    def test_implicit_bias_alert(self):
        """Should create ImplicitBiasAlert"""
        from main import ImplicitBiasAlert, ImplicitBiasContext
        alert = ImplicitBiasAlert(
            context=ImplicitBiasContext.PAIN_ASSESSMENT,
            title="Pain Assessment Reminder",
            reminder="Research shows pain may be undertreated in certain populations",
            evidence="Hoffman et al., PNAS 2016",
            reflection_prompt="Am I applying the same pain assessment standards?",
            resources=["Project Implicit", "AAMC resources"]
        )
        assert alert.context == ImplicitBiasContext.PAIN_ASSESSMENT
        assert "Hoffman" in alert.evidence

    def test_implicit_bias_request(self):
        """Should create ImplicitBiasRequest"""
        from main import ImplicitBiasRequest, ImplicitBiasContext
        req = ImplicitBiasRequest(
            patient_id="12345",
            patient_ancestry="African",
            patient_gender="female",
            clinical_context=ImplicitBiasContext.PAIN_MEDICATION,
            transcript_keywords=["pain", "medication"],
            chief_complaint="Abdominal pain",
            documented_pain_score=8,
            medications_ordered=["acetaminophen"]
        )
        assert req.documented_pain_score == 8

    def test_implicit_bias_response(self):
        """Should create ImplicitBiasResponse"""
        from main import ImplicitBiasResponse, ImplicitBiasAlert, ImplicitBiasContext
        response = ImplicitBiasResponse(
            should_show_reminder=True,
            alerts=[
                ImplicitBiasAlert(
                    context=ImplicitBiasContext.PAIN_MEDICATION,
                    title="Pain Management",
                    reminder="Consider equivalent analgesia",
                    evidence="Research citation",
                    reflection_prompt="Am I treating this pain appropriately?"
                )
            ],
            context_detected=ImplicitBiasContext.PAIN_MEDICATION,
            timestamp="2024-01-15T10:00:00"
        )
        assert response.should_show_reminder is True


class TestMaternalHealthModels:
    """Tests for Maternal Health models (Feature #82)"""

    def test_maternal_status_enum(self):
        """Should have all maternal statuses"""
        from main import MaternalStatus
        assert MaternalStatus.PREGNANT.value == "pregnant"
        assert MaternalStatus.POSTPARTUM.value == "postpartum"

    def test_maternal_risk_level_enum(self):
        """Should have all risk levels"""
        from main import MaternalRiskLevel
        assert MaternalRiskLevel.STANDARD.value == "standard"
        assert MaternalRiskLevel.HIGH.value == "high"

    def test_maternal_warning_sign(self):
        """Should create MaternalWarningSign"""
        from main import MaternalWarningSign
        sign = MaternalWarningSign(
            symptom="Severe headache",
            description="May indicate preeclampsia",
            urgency="emergency",
            action="Check BP immediately",
            ask_patient="Have you had any severe headaches?"
        )
        assert sign.urgency == "emergency"

    def test_maternal_health_alert(self):
        """Should create MaternalHealthAlert"""
        from main import MaternalHealthAlert, MaternalWarningSign
        alert = MaternalHealthAlert(
            alert_type="preeclampsia",
            severity="critical",
            title="Preeclampsia Risk",
            message="Patient has elevated BP and headache",
            recommendation="Check urine protein, consider magnesium",
            warning_signs=[
                MaternalWarningSign(
                    symptom="Headache",
                    description="Severe",
                    urgency="emergency",
                    action="Check BP",
                    ask_patient="How severe?"
                )
            ],
            evidence="ACOG Guidelines 2020"
        )
        assert alert.alert_type == "preeclampsia"
        assert len(alert.warning_signs) == 1

    def test_maternal_health_request(self):
        """Should create MaternalHealthRequest"""
        from main import MaternalHealthRequest, MaternalStatus
        req = MaternalHealthRequest(
            patient_id="12345",
            patient_ancestry="African",
            maternal_status=MaternalStatus.PREGNANT,
            gestational_weeks=32,
            postpartum_weeks=None,
            current_symptoms=["headache", "swelling"],
            vital_signs={"bp": "150/95"},
            conditions=["gestational diabetes"]
        )
        assert req.gestational_weeks == 32
        assert req.maternal_status == MaternalStatus.PREGNANT

    def test_maternal_health_response(self):
        """Should create MaternalHealthResponse"""
        from main import MaternalHealthResponse, MaternalRiskLevel, MaternalHealthAlert
        response = MaternalHealthResponse(
            risk_level=MaternalRiskLevel.HIGH,
            alerts=[
                MaternalHealthAlert(
                    alert_type="disparity_awareness",
                    severity="warning",
                    title="Maternal Mortality Disparity",
                    message="Black women have 3-4x higher maternal mortality",
                    recommendation="Enhanced monitoring recommended"
                )
            ],
            warning_signs_to_check=[],
            disparity_context="CDC data shows significant disparities",
            postpartum_checklist=["BP check", "Mental health screen"],
            timestamp="2024-01-15T10:00:00"
        )
        assert response.risk_level == MaternalRiskLevel.HIGH


class TestSDOHModels:
    """Tests for SDOH models (Feature #84)"""

    def test_sdoh_domain_enum(self):
        """Should have all SDOH domains"""
        from main import SDOHDomain
        assert SDOHDomain.ECONOMIC_STABILITY.value == "economic_stability"
        assert SDOHDomain.HEALTHCARE_ACCESS.value == "healthcare_access"

    def test_sdoh_risk_level_enum(self):
        """Should have all risk levels"""
        from main import SDOHRiskLevel
        assert SDOHRiskLevel.CRITICAL.value == "critical"

    def test_sdoh_factor(self):
        """Should create SDOHFactor"""
        from main import SDOHFactor, SDOHDomain, SDOHRiskLevel
        factor = SDOHFactor(
            domain=SDOHDomain.ECONOMIC_STABILITY,
            factor="Food insecurity",
            description="Patient reports difficulty affording food",
            risk_level=SDOHRiskLevel.HIGH,
            clinical_impact="May affect medication adherence and diet compliance",
            screening_question="Do you have enough food to eat?",
            icd10_code="Z59.41"
        )
        assert factor.domain == SDOHDomain.ECONOMIC_STABILITY
        assert factor.icd10_code == "Z59.41"

    def test_sdoh_intervention(self):
        """Should create SDOHIntervention"""
        from main import SDOHIntervention
        intervention = SDOHIntervention(
            factor="Food insecurity",
            intervention_type="referral",
            title="Food Bank Referral",
            description="Refer to local food bank",
            resources=["Local Food Bank 555-1234"],
            urgency="urgent"
        )
        assert intervention.intervention_type == "referral"

    def test_sdoh_alert(self):
        """Should create SDOHAlert"""
        from main import SDOHAlert, SDOHDomain, SDOHIntervention
        alert = SDOHAlert(
            alert_type="adherence_risk",
            severity="warning",
            title="Medication Adherence Risk",
            message="Patient may have difficulty affording medications",
            domain=SDOHDomain.ECONOMIC_STABILITY,
            clinical_impact="May skip doses",
            recommendations=["Consider generic alternatives"],
            interventions=[
                SDOHIntervention(
                    factor="cost",
                    intervention_type="resource",
                    title="Patient Assistance Program",
                    description="Apply for manufacturer assistance"
                )
            ],
            z_codes=["Z59.41"]
        )
        assert alert.alert_type == "adherence_risk"

    def test_sdoh_screening_request(self):
        """Should create SDOHScreeningRequest"""
        from main import SDOHScreeningRequest
        req = SDOHScreeningRequest(
            patient_id="12345",
            responses={"food_security": "sometimes_worried"},
            known_factors=["transportation_barrier"],
            current_medications=["metformin"],
            upcoming_appointments=["endocrinology"]
        )
        assert req.patient_id == "12345"

    def test_sdoh_screening_response(self):
        """Should create SDOHScreeningResponse"""
        from main import SDOHScreeningResponse, SDOHRiskLevel, SDOHDomain, SDOHFactor
        response = SDOHScreeningResponse(
            patient_id="12345",
            overall_risk=SDOHRiskLevel.MODERATE,
            domain_risks={SDOHDomain.ECONOMIC_STABILITY.value: SDOHRiskLevel.HIGH.value},
            identified_factors=[
                SDOHFactor(
                    domain=SDOHDomain.ECONOMIC_STABILITY,
                    factor="Food insecurity",
                    description="Worried about food",
                    risk_level=SDOHRiskLevel.HIGH,
                    clinical_impact="Affects diet",
                    screening_question="Do you have enough food?"
                )
            ],
            alerts=[],
            recommended_interventions=[],
            z_codes_for_billing=[{"code": "Z59.41", "description": "Food insecurity"}],
            screening_complete=True,
            timestamp="2024-01-15T10:00:00"
        )
        assert response.overall_risk == SDOHRiskLevel.MODERATE


class TestLiteracyModels:
    """Tests for Health Literacy models (Feature #85)"""

    def test_literacy_level_enum(self):
        """Should have all literacy levels"""
        from main import LiteracyLevel
        assert LiteracyLevel.INADEQUATE.value == "inadequate"
        assert LiteracyLevel.PROFICIENT.value == "proficient"

    def test_reading_level_enum(self):
        """Should have all reading levels"""
        from main import ReadingLevel
        assert ReadingLevel.GRADE_3_5.value == "3-5"
        assert ReadingLevel.COLLEGE.value == "college"

    def test_literacy_screening_method_enum(self):
        """Should have all screening methods"""
        from main import LiteracyScreeningMethod
        assert LiteracyScreeningMethod.BRIEF.value == "brief"
        assert LiteracyScreeningMethod.NVS.value == "nvs"

    def test_teach_back_status_enum(self):
        """Should have all teach back statuses"""
        from main import TeachBackStatus
        assert TeachBackStatus.COMPLETE.value == "complete"

    def test_literacy_assessment(self):
        """Should create LiteracyAssessment"""
        from main import LiteracyAssessment, LiteracyLevel, ReadingLevel, LiteracyScreeningMethod
        assessment = LiteracyAssessment(
            patient_id="12345",
            literacy_level=LiteracyLevel.MARGINAL,
            recommended_reading_level=ReadingLevel.GRADE_5_6,
            screening_method=LiteracyScreeningMethod.BRIEF,
            confidence_score=0.8,
            risk_factors=["asks to take materials home", "identifies pills by color"],
            accommodations=["use pictures", "verbal instructions"],
            teach_back_required=True,
            assessed_at="2024-01-15T10:00:00"
        )
        assert assessment.literacy_level == LiteracyLevel.MARGINAL

    def test_discharge_instruction(self):
        """Should create DischargeInstruction"""
        from main import DischargeInstruction, ReadingLevel
        instruction = DischargeInstruction(
            topic="Diabetes Management",
            standard_text="Monitor blood glucose levels and administer insulin as prescribed",
            simplified_text="Check your blood sugar. Take your insulin shot.",
            reading_level=ReadingLevel.GRADE_5_6,
            key_points=["Check blood sugar", "Take insulin"],
            visual_aids=["blood_sugar_chart.png"],
            teach_back_questions=["How often will you check your blood sugar?"]
        )
        assert instruction.topic == "Diabetes Management"

    def test_literacy_adapted_instructions(self):
        """Should create LiteracyAdaptedInstructions"""
        from main import LiteracyAdaptedInstructions, LiteracyLevel, ReadingLevel, DischargeInstruction
        instructions = LiteracyAdaptedInstructions(
            patient_id="12345",
            literacy_level=LiteracyLevel.MARGINAL,
            reading_level=ReadingLevel.GRADE_5_6,
            instructions=[
                DischargeInstruction(
                    topic="Medications",
                    standard_text="Take as prescribed",
                    simplified_text="Take your pills",
                    reading_level=ReadingLevel.GRADE_5_6
                )
            ],
            general_tips=["Speak slowly", "Use pictures"],
            red_flags_simplified=["Go to ER if you have trouble breathing"],
            medication_instructions=[{"med": "Metformin", "instruction": "Take with food"}],
            follow_up_simplified="Come back in 2 weeks",
            teach_back_checklist=["Can repeat medication instructions"]
        )
        assert instructions.literacy_level == LiteracyLevel.MARGINAL


class TestInterpreterModels:
    """Tests for Interpreter models (Feature #86)"""

    def test_interpreter_type_enum(self):
        """Should have all interpreter types"""
        from main import InterpreterType
        assert InterpreterType.IN_PERSON.value == "in_person"
        assert InterpreterType.VIDEO.value == "video"

    def test_interpreter_status_enum(self):
        """Should have all interpreter statuses"""
        from main import InterpreterStatus
        assert InterpreterStatus.REQUESTED.value == "requested"
        assert InterpreterStatus.COMPLETED.value == "completed"

    def test_language_preference(self):
        """Should create LanguagePreference"""
        from main import LanguagePreference
        pref = LanguagePreference(
            preferred_language="es",
            preferred_language_name="Spanish",
            english_proficiency="limited",
            reads_preferred_language=True,
            writes_preferred_language=True,
            sign_language=None,
            interpreter_required=True,
            family_interpreter_declined=True
        )
        assert pref.preferred_language == "es"
        assert pref.family_interpreter_declined is True

    def test_interpreter_request(self):
        """Should create InterpreterRequest"""
        from main import InterpreterRequest, InterpreterType, InterpreterStatus
        req = InterpreterRequest(
            request_id="req-123",
            patient_id="12345",
            language="es",
            language_name="Spanish",
            interpreter_type=InterpreterType.VIDEO,
            urgency="urgent",
            encounter_type="ED",
            estimated_duration=60,
            special_needs=["medical_terminology"],
            requested_at="2024-01-15T10:00:00",
            status=InterpreterStatus.REQUESTED
        )
        assert req.language == "es"
        assert req.interpreter_type == InterpreterType.VIDEO

    def test_interpreter_session(self):
        """Should create InterpreterSession"""
        from main import InterpreterSession, InterpreterType, InterpreterStatus
        session = InterpreterSession(
            session_id="session-123",
            request_id="req-123",
            patient_id="12345",
            language="es",
            interpreter_type=InterpreterType.VIDEO,
            interpreter_id="int-456",
            interpreter_name="Maria Garcia",
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T11:00:00",
            duration_minutes=60,
            topics_covered=["consent", "discharge"],
            status=InterpreterStatus.COMPLETED
        )
        assert session.duration_minutes == 60

    def test_interpreter_documentation(self):
        """Should create InterpreterDocumentation"""
        from main import InterpreterDocumentation, InterpreterType
        doc = InterpreterDocumentation(
            patient_id="12345",
            encounter_id="enc-789",
            language="es",
            interpreter_type=InterpreterType.VIDEO,
            interpreter_id="int-456",
            session_start="2024-01-15T10:00:00",
            session_end="2024-01-15T11:00:00",
            duration_minutes=60,
            topics=["consent", "discharge"],
            patient_understanding_confirmed=True,
            notes="Patient understood all instructions",
            documented_by="Dr. Smith",
            documented_at="2024-01-15T11:05:00"
        )
        assert doc.patient_understanding_confirmed is True

    def test_translated_phrase(self):
        """Should create TranslatedPhrase"""
        from main import TranslatedPhrase
        phrase = TranslatedPhrase(
            category="greeting",
            english="Hello, how are you feeling today?",
            translated="Hola, ¿cómo se siente hoy?",
            phonetic="OH-lah KOH-moh seh see-EN-teh oy",
            audio_url="/audio/greeting_es.mp3",
            context_notes="Use formal 'usted' form"
        )
        assert phrase.category == "greeting"
        assert phrase.phonetic is not None


class TestBillingModels:
    """Tests for Billing models (Feature #71)"""

    def test_claim_status_enum(self):
        """Should have all claim statuses"""
        from main import ClaimStatus
        assert ClaimStatus.DRAFT.value == "draft"
        assert ClaimStatus.SUBMITTED.value == "submitted"

    def test_billing_diagnosis_code(self):
        """Should create BillingDiagnosisCode"""
        from main import BillingDiagnosisCode
        code = BillingDiagnosisCode(
            code="J06.9",
            description="Acute upper respiratory infection",
            sequence=1,
            is_principal=True
        )
        assert code.code == "J06.9"
        assert code.is_principal is True

    def test_billing_procedure_code(self):
        """Should create BillingProcedureCode"""
        from main import BillingProcedureCode
        code = BillingProcedureCode(
            code="99213",
            description="Office visit, established patient",
            modifiers=["-25"],
            units=1
        )
        assert code.code == "99213"
        assert "-25" in code.modifiers

    def test_billing_service_line(self):
        """Should create BillingServiceLine"""
        from main import BillingServiceLine, BillingProcedureCode
        line = BillingServiceLine(
            line_number=1,
            service_date="2024-01-15",
            procedure=BillingProcedureCode(code="99213", description="Office visit"),
            diagnosis_pointers=[1, 2]
        )
        assert line.line_number == 1

    def test_billing_claim(self):
        """Should create BillingClaim"""
        from main import BillingClaim, ClaimStatus, BillingDiagnosisCode, BillingServiceLine, BillingProcedureCode
        claim = BillingClaim(
            claim_id="claim-123",
            status=ClaimStatus.DRAFT,
            patient_id="12345",
            patient_name="John Doe",
            note_id="note-456",
            service_date="2024-01-15",
            provider_name="Dr. Smith",
            provider_npi="1234567890",
            diagnoses=[BillingDiagnosisCode(code="J06.9", description="URI")],
            service_lines=[
                BillingServiceLine(
                    line_number=1,
                    service_date="2024-01-15",
                    procedure=BillingProcedureCode(code="99213", description="Office visit")
                )
            ],
            total_charge=150.00,
            created_at="2024-01-15T10:00:00",
            submitted_at=None,
            fhir_claim_id=None
        )
        assert claim.status == ClaimStatus.DRAFT
        assert claim.total_charge == 150.00


class TestDNFBModels:
    """Tests for DNFB models (Feature #72)"""

    def test_dnfb_reason_enum(self):
        """Should have all DNFB reasons"""
        from main import DNFBReason
        assert DNFBReason.CODING_INCOMPLETE.value == "coding_incomplete"
        assert DNFBReason.PRIOR_AUTH_DENIED.value == "prior_auth_denied"

    def test_prior_auth_status_enum(self):
        """Should have all prior auth statuses"""
        from main import PriorAuthStatus
        assert PriorAuthStatus.APPROVED.value == "approved"
        assert PriorAuthStatus.EXPIRED.value == "expired"

    def test_prior_auth_info(self):
        """Should create PriorAuthInfo"""
        from main import PriorAuthInfo, PriorAuthStatus
        auth = PriorAuthInfo(
            auth_number="AUTH-12345",
            status=PriorAuthStatus.APPROVED,
            requested_date="2024-01-10",
            approval_date="2024-01-12",
            expiration_date="2024-04-12",
            approved_units=10,
            used_units=3,
            payer_name="Blue Cross",
            procedure_codes=["99213", "99214"],
            denial_reason=None
        )
        assert auth.status == PriorAuthStatus.APPROVED
        assert auth.approved_units == 10

    def test_dnfb_account(self):
        """Should create DNFBAccount"""
        from main import DNFBAccount, DNFBReason, PriorAuthInfo, PriorAuthStatus
        account = DNFBAccount(
            dnfb_id="dnfb-123",
            patient_id="12345",
            patient_name="John Doe",
            mrn="MRN-12345",
            encounter_id="enc-789",
            admission_date="2024-01-10",
            discharge_date="2024-01-15",
            discharge_disposition="home",
            attending_physician="Dr. Smith",
            service_type="inpatient",
            principal_diagnosis="J18.9",
            principal_diagnosis_desc="Pneumonia",
            estimated_charges=5000.00,
            reason=DNFBReason.PRIOR_AUTH_MISSING,
            reason_detail="Authorization not obtained before admission",
            prior_auth=PriorAuthInfo(
                status=PriorAuthStatus.NOT_OBTAINED,
                payer_name="Aetna"
            ),
            days_since_discharge=5,
            aging_bucket="4-7",
            assigned_coder="Jane Coder",
            last_updated="2024-01-20T10:00:00",
            notes=["Called payer", "Waiting for response"],
            is_resolved=False,
            resolved_date=None,
            claim_id=None
        )
        assert account.reason == DNFBReason.PRIOR_AUTH_MISSING
        assert account.aging_bucket == "4-7"


class TestNoteModels:
    """Tests for Clinical Note models"""

    def test_note_request(self):
        """Should create NoteRequest"""
        from main import NoteRequest
        req = NoteRequest(
            transcript="Patient reports headache and fever",
            patient_id="12345",
            note_type="SOAP",
            chief_complaint="Headache"
        )
        assert req.transcript.startswith("Patient")
        assert req.note_type == "SOAP"

    def test_soap_note(self):
        """Should create SOAPNote"""
        from main import SOAPNote
        note = SOAPNote(
            subjective="Patient reports headache",
            objective="Vitals stable",
            assessment="Tension headache",
            plan="OTC analgesics",
            summary="Headache workup",
            timestamp="2024-01-15T10:00:00",
            display_text="S: Headache\nO: Stable\nA: Tension\nP: OTC"
        )
        assert note.subjective == "Patient reports headache"

    def test_progress_note(self):
        """Should create ProgressNote"""
        from main import ProgressNote
        note = ProgressNote(
            interval_history="Patient improving",
            current_status="Better",
            physical_exam="Normal",
            assessment="Improving",
            plan="Continue treatment",
            summary="Follow-up visit",
            timestamp="2024-01-15T10:00:00",
            display_text="Progress note content"
        )
        assert note.interval_history == "Patient improving"

    def test_hp_note(self):
        """Should create HPNote"""
        from main import HPNote
        note = HPNote(
            chief_complaint="Chest pain",
            history_present_illness="2 days of chest pain",
            past_medical_history="HTN, DM",
            medications="Metformin, Lisinopril",
            allergies="NKDA",
            family_history="Father with MI",
            social_history="Non-smoker",
            review_of_systems="Negative",
            physical_exam="Normal",
            assessment="Chest pain, r/o ACS",
            plan="ECG, troponin",
            summary="New patient with chest pain",
            timestamp="2024-01-15T10:00:00",
            display_text="H&P content"
        )
        assert note.chief_complaint == "Chest pain"

    def test_consult_note(self):
        """Should create ConsultNote"""
        from main import ConsultNote
        note = ConsultNote(
            reason_for_consult="Evaluate chest pain",
            history_present_illness="2 days of chest pain",
            relevant_history="HTN, DM",
            physical_exam="Normal",
            diagnostic_findings="ECG normal",
            impression="Low risk for ACS",
            recommendations="Stress test outpatient",
            summary="Cardiology consult",
            timestamp="2024-01-15T10:00:00",
            display_text="Consult content"
        )
        assert note.reason_for_consult == "Evaluate chest pain"
