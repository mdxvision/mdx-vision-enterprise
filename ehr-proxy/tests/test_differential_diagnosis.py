"""
Tests for Differential Diagnosis with RAG (Issue #116)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, '/Users/rafaelrodriguez/projects/mdx-vision-enterprise/ehr-proxy')


class TestDiagnosisLikelihood:
    """Tests for DiagnosisLikelihood enum"""

    def test_likelihood_values(self):
        """Should have expected likelihood levels"""
        from differential_diagnosis import DiagnosisLikelihood

        assert DiagnosisLikelihood.MOST_LIKELY.value == "most_likely"
        assert DiagnosisLikelihood.LIKELY.value == "likely"
        assert DiagnosisLikelihood.POSSIBLE.value == "possible"
        assert DiagnosisLikelihood.LESS_LIKELY.value == "less_likely"
        assert DiagnosisLikelihood.UNLIKELY_BUT_IMPORTANT.value == "unlikely_but_important"


class TestDiagnosisSeverity:
    """Tests for DiagnosisSeverity enum"""

    def test_severity_values(self):
        """Should have expected severity levels"""
        from differential_diagnosis import DiagnosisSeverity

        assert DiagnosisSeverity.CRITICAL.value == "critical"
        assert DiagnosisSeverity.SERIOUS.value == "serious"
        assert DiagnosisSeverity.MODERATE.value == "moderate"
        assert DiagnosisSeverity.MILD.value == "mild"


class TestDiagnosis:
    """Tests for Diagnosis dataclass"""

    def test_diagnosis_creation(self):
        """Should create diagnosis with required fields"""
        from differential_diagnosis import Diagnosis, DiagnosisLikelihood, DiagnosisSeverity

        diagnosis = Diagnosis(
            name="Acute Coronary Syndrome",
            icd10_code="I21.9",
            likelihood=DiagnosisLikelihood.MOST_LIKELY,
            likelihood_percentage=65.0,
            severity=DiagnosisSeverity.CRITICAL,
            supporting_features=["chest pain", "diaphoresis"],
            against_features=["young age"],
            distinguishing_tests=["troponin", "ECG"],
            next_steps=["Obtain 12-lead ECG", "Serial troponins"],
            red_flags=["ST elevation", "hypotension"],
            citations=[{"index": "1", "source": "AHA", "title": "STEMI Guidelines"}],
            rationale="Classic presentation with cardiac risk factors",
            is_cant_miss=True
        )

        assert diagnosis.name == "Acute Coronary Syndrome"
        assert diagnosis.icd10_code == "I21.9"
        assert diagnosis.likelihood == DiagnosisLikelihood.MOST_LIKELY
        assert diagnosis.likelihood_percentage == 65.0
        assert diagnosis.is_cant_miss is True
        assert "chest pain" in diagnosis.supporting_features

    def test_diagnosis_to_dict(self):
        """Should convert to dictionary"""
        from differential_diagnosis import Diagnosis, DiagnosisLikelihood, DiagnosisSeverity

        diagnosis = Diagnosis(
            name="GERD",
            icd10_code="K21.0",
            likelihood=DiagnosisLikelihood.POSSIBLE,
            likelihood_percentage=20.0,
            severity=DiagnosisSeverity.MILD,
            supporting_features=["burning sensation"],
            against_features=[],
            distinguishing_tests=["trial of PPI"],
            next_steps=["Lifestyle modifications"],
            red_flags=[],
            citations=[],
            rationale="Typical symptoms"
        )

        result = diagnosis.to_dict()

        assert result["name"] == "GERD"
        assert result["likelihood"] == "possible"
        assert result["severity"] == "mild"


class TestPatientContext:
    """Tests for PatientContext model"""

    def test_patient_context_minimal(self):
        """Should create context with minimal fields"""
        from differential_diagnosis import PatientContext

        ctx = PatientContext(
            patient_id="12724066",
            chief_complaint="chest pain"
        )

        assert ctx.patient_id == "12724066"
        assert ctx.chief_complaint == "chest pain"
        assert ctx.symptoms == []

    def test_patient_context_full(self):
        """Should create context with all fields"""
        from differential_diagnosis import PatientContext

        ctx = PatientContext(
            patient_id="12724066",
            name="John Doe",
            age=55,
            gender="male",
            chief_complaint="chest pain",
            symptoms=["chest pain", "shortness of breath", "diaphoresis"],
            symptom_duration="2 hours",
            vital_signs={
                "heart_rate": {"value": 110, "unit": "bpm"},
                "blood_pressure": {"value": "150/90", "unit": "mmHg"}
            },
            lab_results={
                "troponin": {"value": 0.08, "unit": "ng/mL"}
            },
            past_medical_history=["hypertension", "diabetes", "hyperlipidemia"],
            medications=["metformin", "lisinopril", "atorvastatin"],
            allergies=["penicillin"]
        )

        assert ctx.age == 55
        assert len(ctx.symptoms) == 3
        assert "diabetes" in ctx.past_medical_history


class TestDifferentialDiagnosisEngine:
    """Tests for DifferentialDiagnosisEngine"""

    @pytest.fixture
    def engine(self):
        """Create engine for tests"""
        from differential_diagnosis import DifferentialDiagnosisEngine
        return DifferentialDiagnosisEngine()

    @pytest.mark.asyncio
    async def test_initialize(self, engine):
        """Should initialize successfully"""
        result = await engine.initialize()
        assert result is True
        assert engine._initialized is True

    def test_build_patient_context_string(self, engine):
        """Should build formatted patient context"""
        from differential_diagnosis import PatientContext

        ctx = PatientContext(
            patient_id="test-123",
            name="Jane Smith",
            age=45,
            gender="female",
            chief_complaint="headache",
            symptoms=["severe headache", "photophobia", "nausea"],
            vital_signs={"blood_pressure": {"value": "140/90", "unit": "mmHg"}}
        )

        result = engine._build_patient_context_string(ctx)

        assert "Jane Smith" in result
        assert "45" in result
        assert "female" in result
        assert "headache" in result
        assert "photophobia" in result

    def test_generate_spoken_summary(self, engine):
        """Should generate TTS-friendly summary"""
        from differential_diagnosis import Diagnosis, DiagnosisLikelihood, DiagnosisSeverity

        diagnoses = [
            Diagnosis(
                name="Migraine",
                icd10_code="G43.9",
                likelihood=DiagnosisLikelihood.MOST_LIKELY,
                likelihood_percentage=60.0,
                severity=DiagnosisSeverity.MODERATE,
                supporting_features=["photophobia"],
                against_features=[],
                distinguishing_tests=["clinical diagnosis"],
                next_steps=["Triptans"],
                red_flags=[],
                citations=[],
                rationale="Classic migraine features"
            )
        ]

        result = engine._generate_spoken_summary(diagnoses, "headache")

        assert "headache" in result
        assert "Migraine" in result
        assert "60" in result

    def test_extract_red_flags(self, engine):
        """Should extract red flags from diagnoses"""
        from differential_diagnosis import Diagnosis, DiagnosisLikelihood, DiagnosisSeverity

        diagnoses = [
            Diagnosis(
                name="Subarachnoid hemorrhage",
                icd10_code="I60.9",
                likelihood=DiagnosisLikelihood.POSSIBLE,
                likelihood_percentage=15.0,
                severity=DiagnosisSeverity.CRITICAL,
                supporting_features=["sudden onset"],
                against_features=[],
                distinguishing_tests=["CT head", "LP"],
                next_steps=["Emergent imaging"],
                red_flags=["thunderclap headache", "worst headache of life"],
                citations=[],
                rationale="Can't miss diagnosis"
            )
        ]

        result = engine._extract_red_flags("", diagnoses)

        assert result is not None
        assert "thunderclap" in result or "worst headache" in result


class TestDifferentialResult:
    """Tests for DifferentialResult"""

    def test_result_creation(self):
        """Should create result with diagnoses"""
        from differential_diagnosis import DifferentialResult, Diagnosis, DiagnosisLikelihood, DiagnosisSeverity

        diagnoses = [
            Diagnosis(
                name="Pneumonia",
                icd10_code="J18.9",
                likelihood=DiagnosisLikelihood.MOST_LIKELY,
                likelihood_percentage=55.0,
                severity=DiagnosisSeverity.MODERATE,
                supporting_features=["cough", "fever"],
                against_features=[],
                distinguishing_tests=["chest X-ray"],
                next_steps=["Antibiotics"],
                red_flags=[],
                citations=[],
                rationale="Typical pneumonia presentation"
            )
        ]

        result = DifferentialResult(
            patient_id="test-456",
            chief_complaint="cough and fever",
            diagnoses=diagnoses,
            clinical_summary="Likely lower respiratory infection",
            spoken_summary="For cough and fever, pneumonia is most likely at 55%.",
            confidence=0.8,
            rag_enhanced=True
        )

        assert result.patient_id == "test-456"
        assert len(result.diagnoses) == 1
        assert result.rag_enhanced is True

    def test_result_to_dict(self):
        """Should convert result to dictionary"""
        from differential_diagnosis import DifferentialResult, Diagnosis, DiagnosisLikelihood, DiagnosisSeverity

        diagnoses = [
            Diagnosis(
                name="COPD Exacerbation",
                icd10_code="J44.1",
                likelihood=DiagnosisLikelihood.LIKELY,
                likelihood_percentage=40.0,
                severity=DiagnosisSeverity.SERIOUS,
                supporting_features=["dyspnea", "wheezing"],
                against_features=[],
                distinguishing_tests=["ABG", "chest X-ray"],
                next_steps=["Bronchodilators", "steroids"],
                red_flags=["severe dyspnea", "altered mental status"],
                citations=[],
                rationale="History of COPD with acute worsening"
            )
        ]

        result = DifferentialResult(
            patient_id="test-789",
            chief_complaint="shortness of breath",
            diagnoses=diagnoses,
            clinical_summary="COPD exacerbation",
            spoken_summary="Test summary",
            confidence=0.75,
            rag_enhanced=False
        )

        dict_result = result.to_dict()

        assert dict_result["patient_id"] == "test-789"
        assert len(dict_result["diagnoses"]) == 1
        assert dict_result["diagnoses"][0]["name"] == "COPD Exacerbation"


class TestFollowUpQuestions:
    """Tests for follow-up question handling"""

    @pytest.fixture
    def engine(self):
        from differential_diagnosis import DifferentialDiagnosisEngine
        return DifferentialDiagnosisEngine()

    @pytest.mark.asyncio
    async def test_follow_up_no_previous(self, engine):
        """Should handle follow-up without previous differential"""
        await engine.initialize()

        result = await engine.answer_follow_up(
            patient_id="no-prev",
            question="Why do you think that?"
        )

        assert result.patient_id == "no-prev"
        assert "first" in result.spoken_response.lower() or "need" in result.spoken_response.lower()


class TestCaching:
    """Tests for differential caching"""

    @pytest.fixture
    def engine(self):
        from differential_diagnosis import DifferentialDiagnosisEngine
        return DifferentialDiagnosisEngine()

    def test_get_cached_empty(self, engine):
        """Should return None for uncached patient"""
        result = engine.get_cached_differential("uncached-patient")
        assert result is None

    def test_clear_cache_specific(self, engine):
        """Should clear cache for specific patient"""
        from differential_diagnosis import DifferentialResult

        # Add to cache manually
        engine._session_cache["test-patient"] = DifferentialResult(
            patient_id="test-patient",
            chief_complaint="test",
            diagnoses=[],
            clinical_summary="test",
            spoken_summary="test",
            confidence=0.5,
            rag_enhanced=False
        )

        engine.clear_cache("test-patient")

        assert engine.get_cached_differential("test-patient") is None

    def test_clear_cache_all(self, engine):
        """Should clear entire cache"""
        from differential_diagnosis import DifferentialResult

        # Add multiple patients
        for i in range(3):
            engine._session_cache[f"patient-{i}"] = DifferentialResult(
                patient_id=f"patient-{i}",
                chief_complaint="test",
                diagnoses=[],
                clinical_summary="test",
                spoken_summary="test",
                confidence=0.5,
                rag_enhanced=False
            )

        engine.clear_cache()

        assert len(engine._session_cache) == 0


class TestGlobalFunctions:
    """Tests for module-level functions"""

    @pytest.mark.asyncio
    async def test_get_differential_engine(self):
        """Should return global engine instance"""
        from differential_diagnosis import get_differential_engine, shutdown_differential_engine

        engine = await get_differential_engine()
        assert engine is not None
        assert engine._initialized is True

        # Same instance on second call
        engine2 = await get_differential_engine()
        assert engine is engine2

        # Cleanup
        await shutdown_differential_engine()

    @pytest.mark.asyncio
    async def test_shutdown_engine(self):
        """Should shutdown cleanly"""
        from differential_diagnosis import get_differential_engine, shutdown_differential_engine

        await get_differential_engine()
        await shutdown_differential_engine()

        # Should be able to get new instance
        engine = await get_differential_engine()
        assert engine is not None

        await shutdown_differential_engine()


class TestParseResponse:
    """Tests for AI response parsing"""

    @pytest.fixture
    def engine(self):
        from differential_diagnosis import DifferentialDiagnosisEngine
        return DifferentialDiagnosisEngine()

    def test_parse_numbered_diagnoses(self, engine):
        """Should parse numbered diagnosis list"""
        response = """
Clinical Summary: Patient presents with typical chest pain symptoms.

1. Acute Coronary Syndrome - 45%
   Supporting: chest pain, diaphoresis, cardiac risk factors
   Against: young age
   Test: troponin, ECG

2. GERD - 25%
   Supporting: burning sensation, worse after meals
   Test: PPI trial

3. Costochondritis - 20%
   Supporting: reproducible pain
   Test: clinical exam
"""
        citations = [{"index": "1", "source": "AHA", "title": "Chest Pain Guidelines"}]

        result = engine._parse_differential_response(response, citations)

        assert len(result) >= 1
        # First diagnosis should be ACS
        assert "coronary" in result[0].name.lower() or "acs" in result[0].name.lower()

    def test_parse_empty_response(self, engine):
        """Should handle empty response gracefully"""
        result = engine._parse_differential_response("", [])

        assert len(result) >= 1
        assert "unable" in result[0].name.lower() or result[0].rationale

    def test_extract_clinical_summary(self, engine):
        """Should extract summary from response"""
        response = """
Clinical Assessment Summary:
This 55-year-old male presents with concerning cardiac symptoms requiring urgent evaluation.

Differential Diagnosis:
1. ACS - 50%
2. PE - 20%
"""
        result = engine._extract_clinical_summary(response)

        assert "cardiac" in result.lower() or "55" in result
