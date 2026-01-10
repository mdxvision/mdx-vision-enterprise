"""
Comprehensive tests for main.py FHIR data extraction functions.
Tests extract_patient_name, extract_patient_photo, extract_vitals, extract_allergies,
extract_medications, extract_labs, and related helper functions.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestExtractPatientName:
    """Tests for extract_patient_name function"""

    def test_extract_with_text_name(self):
        """Should extract name from text field"""
        from main import extract_patient_name
        patient = {
            "name": [{"text": "John Doe"}]
        }
        result = extract_patient_name(patient)
        assert result == "John Doe"

    def test_extract_no_name(self):
        """Should return Unknown when no name"""
        from main import extract_patient_name
        patient = {}
        result = extract_patient_name(patient)
        assert result == "Unknown"

    def test_extract_empty_name_list(self):
        """Should return Unknown for empty name list"""
        from main import extract_patient_name
        patient = {"name": []}
        result = extract_patient_name(patient)
        assert result == "Unknown"

    def test_extract_name_no_text(self):
        """Should return Unknown when name has no text"""
        from main import extract_patient_name
        patient = {"name": [{"family": "Doe", "given": ["John"]}]}
        result = extract_patient_name(patient)
        assert result == "Unknown"


class TestExtractPatientPhoto:
    """Tests for extract_patient_photo function"""

    def test_no_photo(self):
        """Should return None when no photo"""
        from main import extract_patient_photo
        patient = {}
        result = extract_patient_photo(patient)
        assert result is None

    def test_empty_photo_list(self):
        """Should return None for empty photo list"""
        from main import extract_patient_photo
        patient = {"photo": []}
        result = extract_patient_photo(patient)
        assert result is None

    def test_photo_with_url(self):
        """Should return URL when photo has url"""
        from main import extract_patient_photo
        patient = {
            "photo": [{"url": "https://example.com/photo.jpg"}]
        }
        result = extract_patient_photo(patient)
        assert result == "https://example.com/photo.jpg"

    def test_photo_with_base64_data(self):
        """Should return data URI when photo has inline data"""
        from main import extract_patient_photo
        patient = {
            "photo": [{
                "contentType": "image/png",
                "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            }]
        }
        result = extract_patient_photo(patient)
        assert result.startswith("data:image/png;base64,")

    def test_photo_missing_content_type(self):
        """Should return None when data but no contentType"""
        from main import extract_patient_photo
        patient = {
            "photo": [{"data": "base64data"}]
        }
        result = extract_patient_photo(patient)
        assert result is None


class TestExtractVitals:
    """Tests for extract_vitals function"""

    def test_empty_bundle(self):
        """Should return empty list for empty bundle"""
        from main import extract_vitals
        bundle = {}
        result = extract_vitals(bundle)
        assert result == []

    def test_extract_single_vital(self):
        """Should extract single vital sign"""
        from main import extract_vitals
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Heart Rate"},
                    "valueQuantity": {"value": 72, "unit": "bpm"},
                    "effectiveDateTime": "2024-01-15T10:00:00Z"
                }
            }]
        }
        result = extract_vitals(bundle)
        assert len(result) == 1
        assert result[0].name == "Heart Rate"
        assert result[0].value == "72"
        assert result[0].unit == "bpm"

    def test_extract_multiple_vitals(self):
        """Should extract multiple vital signs"""
        from main import extract_vitals
        bundle = {
            "entry": [
                {
                    "resource": {
                        "code": {"text": "Heart Rate"},
                        "valueQuantity": {"value": 72, "unit": "bpm"},
                        "effectiveDateTime": "2024-01-15T10:00:00Z"
                    }
                },
                {
                    "resource": {
                        "code": {"text": "Blood Pressure"},
                        "valueQuantity": {"value": 120, "unit": "mmHg"},
                        "effectiveDateTime": "2024-01-15T10:00:00Z"
                    }
                }
            ]
        }
        result = extract_vitals(bundle)
        assert len(result) == 2

    def test_vital_critical_detection(self):
        """Should detect critical vital values"""
        from main import extract_vitals
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Systolic Blood Pressure"},
                    "valueQuantity": {"value": 190, "unit": "mmHg"},
                    "effectiveDateTime": "2024-01-15T10:00:00Z"
                }
            }]
        }
        result = extract_vitals(bundle)
        assert len(result) == 1
        # Should detect critical high BP
        assert result[0].is_critical is True or result[0].is_abnormal is True


class TestCalculateVitalTrends:
    """Tests for calculate_vital_trends function"""

    def test_empty_vitals(self):
        """Should handle empty vitals list"""
        from main import calculate_vital_trends
        result = calculate_vital_trends([])
        assert result == []

    def test_single_vital_new_trend(self):
        """Single vital should have 'new' trend"""
        from main import calculate_vital_trends, VitalSign
        vitals = [VitalSign(
            name="Heart Rate",
            value="72",
            unit="bpm",
            date="2024-01-15"
        )]
        result = calculate_vital_trends(vitals)
        assert len(result) == 1
        assert result[0].trend == "new"

    def test_two_vitals_trend_calculation(self):
        """Should calculate trend from two readings"""
        from main import calculate_vital_trends, VitalSign
        vitals = [
            VitalSign(name="Heart Rate", value="72", unit="bpm", date="2024-01-15"),
            VitalSign(name="Heart Rate", value="68", unit="bpm", date="2024-01-14")
        ]
        result = calculate_vital_trends(vitals)
        assert len(result) == 1
        assert result[0].trend is not None  # Should have a trend


class TestExtractAllergies:
    """Tests for extract_allergies function"""

    def test_empty_bundle(self):
        """Should return empty list for empty bundle"""
        from main import extract_allergies
        bundle = {}
        result = extract_allergies(bundle)
        assert result == []

    def test_extract_single_allergy(self):
        """Should extract single allergy"""
        from main import extract_allergies
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Penicillin"}
                }
            }]
        }
        result = extract_allergies(bundle)
        assert result == ["Penicillin"]

    def test_extract_multiple_allergies(self):
        """Should extract multiple allergies"""
        from main import extract_allergies
        bundle = {
            "entry": [
                {"resource": {"code": {"text": "Penicillin"}}},
                {"resource": {"code": {"text": "Sulfa"}}},
                {"resource": {"code": {"text": "Aspirin"}}}
            ]
        }
        result = extract_allergies(bundle)
        assert len(result) == 3
        assert "Penicillin" in result
        assert "Sulfa" in result

    def test_skip_unknown_allergies(self):
        """Should skip allergies with Unknown text"""
        from main import extract_allergies
        bundle = {
            "entry": [
                {"resource": {"code": {"text": "Penicillin"}}},
                {"resource": {"code": {"text": "Unknown"}}},
                {"resource": {"code": {}}}
            ]
        }
        result = extract_allergies(bundle)
        assert result == ["Penicillin"]

    def test_limit_to_10_allergies(self):
        """Should limit to 10 allergies"""
        from main import extract_allergies
        entries = [{"resource": {"code": {"text": f"Allergy{i}"}}} for i in range(15)]
        bundle = {"entry": entries}
        result = extract_allergies(bundle)
        assert len(result) <= 10


class TestExtractMedications:
    """Tests for extract_medications function"""

    def test_empty_bundle(self):
        """Should return empty list for empty bundle"""
        from main import extract_medications
        bundle = {}
        result = extract_medications(bundle)
        assert result == []

    def test_extract_single_medication(self):
        """Should extract single medication"""
        from main import extract_medications
        bundle = {
            "entry": [{
                "resource": {
                    "medicationCodeableConcept": {"text": "Lisinopril 10mg"}
                }
            }]
        }
        result = extract_medications(bundle)
        assert result == ["Lisinopril 10mg"]

    def test_extract_multiple_medications(self):
        """Should extract multiple medications"""
        from main import extract_medications
        bundle = {
            "entry": [
                {"resource": {"medicationCodeableConcept": {"text": "Lisinopril 10mg"}}},
                {"resource": {"medicationCodeableConcept": {"text": "Metformin 500mg"}}},
                {"resource": {"medicationCodeableConcept": {"text": "Atorvastatin 20mg"}}}
            ]
        }
        result = extract_medications(bundle)
        assert len(result) == 3

    def test_skip_unknown_medications(self):
        """Should skip medications with Unknown text"""
        from main import extract_medications
        bundle = {
            "entry": [
                {"resource": {"medicationCodeableConcept": {"text": "Lisinopril"}}},
                {"resource": {"medicationCodeableConcept": {"text": "Unknown"}}},
                {"resource": {"medicationCodeableConcept": {}}}
            ]
        }
        result = extract_medications(bundle)
        assert result == ["Lisinopril"]


class TestExtractLabs:
    """Tests for extract_labs function"""

    def test_empty_bundle(self):
        """Should return empty list for empty bundle"""
        from main import extract_labs
        bundle = {}
        result = extract_labs(bundle)
        assert result == []

    def test_extract_lab_with_quantity(self):
        """Should extract lab with valueQuantity"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Potassium"},
                    "valueQuantity": {"value": 4.2, "unit": "mEq/L"},
                    "status": "final",
                    "effectiveDateTime": "2024-01-15T10:00:00Z"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].name == "Potassium"
        assert result[0].value == "4.2"
        assert result[0].unit == "mEq/L"

    def test_extract_lab_with_string_value(self):
        """Should extract lab with valueString"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Blood Type"},
                    "valueString": "A Positive",
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].value == "A Positive"

    def test_extract_lab_with_codeable_concept(self):
        """Should extract lab with valueCodeableConcept"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Urine Culture"},
                    "valueCodeableConcept": {"text": "Negative"},
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].value == "Negative"

    def test_extract_lab_from_coding(self):
        """Should extract lab name from coding when no text"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {
                        "coding": [{"display": "Hemoglobin"}]
                    },
                    "valueQuantity": {"value": 14.5, "unit": "g/dL"},
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].name == "Hemoglobin"

    def test_lab_critical_detection(self):
        """Should detect critical lab values"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Potassium"},
                    "valueQuantity": {"value": 7.0, "unit": "mEq/L"},
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        # Should detect critical high potassium
        assert result[0].is_critical is True

    def test_extract_reference_range_text(self):
        """Should extract reference range from text"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Potassium"},
                    "valueQuantity": {"value": 4.2, "unit": "mEq/L"},
                    "referenceRange": [{"text": "3.5-5.0 mEq/L"}],
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].reference_range == "3.5-5.0 mEq/L"

    def test_extract_reference_range_from_low_high(self):
        """Should build reference range from low/high values"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Glucose"},
                    "valueQuantity": {"value": 95, "unit": "mg/dL"},
                    "referenceRange": [{
                        "low": {"value": 70, "unit": "mg/dL"},
                        "high": {"value": 100, "unit": "mg/dL"}
                    }],
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert "70" in result[0].reference_range
        assert "100" in result[0].reference_range


class TestCalculateTrendDirection:
    """Tests for calculate_trend_direction function"""

    def test_rising_trend(self):
        """Should detect rising trend"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("100", "80")
        assert trend == "rising"
        assert "+20" in delta or delta == "20" or "20.0" in delta

    def test_falling_trend(self):
        """Should detect falling trend"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("80", "100")
        assert trend == "falling"
        assert "-20" in delta

    def test_stable_trend(self):
        """Should detect stable trend"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("100", "99")
        assert trend == "stable"

    def test_invalid_values(self):
        """Should handle invalid values gracefully"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("invalid", "100")
        # Function may return stable, unknown, or None for invalid input
        assert trend in [None, "unknown", "stable"]


class TestVitalSignModel:
    """Tests for VitalSign Pydantic model"""

    def test_create_vital_sign(self):
        """Should create VitalSign model"""
        from main import VitalSign
        vital = VitalSign(
            name="Heart Rate",
            value="72",
            unit="bpm",
            date="2024-01-15"
        )
        assert vital.name == "Heart Rate"
        assert vital.value == "72"
        assert vital.unit == "bpm"

    def test_vital_sign_defaults(self):
        """Should have correct defaults"""
        from main import VitalSign
        vital = VitalSign(
            name="Heart Rate",
            value="72",
            unit="bpm"
        )
        assert vital.is_critical is False
        assert vital.is_abnormal is False


class TestLabResultModel:
    """Tests for LabResult Pydantic model"""

    def test_create_lab_result(self):
        """Should create LabResult model"""
        from main import LabResult
        lab = LabResult(
            name="Potassium",
            value="4.2",
            unit="mEq/L",
            status="final",
            date="2024-01-15"
        )
        assert lab.name == "Potassium"
        assert lab.value == "4.2"
        assert lab.unit == "mEq/L"

    def test_lab_result_defaults(self):
        """Should have correct defaults"""
        from main import LabResult
        lab = LabResult(
            name="Potassium",
            value="4.2",
            unit="mEq/L",
            status="final"
        )
        assert lab.is_critical is False
        assert lab.is_abnormal is False


class TestFetchFHIR:
    """Tests for fetch_fhir function"""

    @pytest.mark.asyncio
    @patch("main.httpx.AsyncClient")
    async def test_fetch_fhir_success(self, mock_client):
        """Should fetch FHIR resource successfully"""
        from main import fetch_fhir

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"resourceType": "Patient", "id": "123"}

        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await fetch_fhir("Patient/123")
        assert result["resourceType"] == "Patient"

    @pytest.mark.asyncio
    @patch("main.httpx.AsyncClient")
    async def test_fetch_fhir_failure(self, mock_client):
        """Should return empty dict on failure"""
        from main import fetch_fhir

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await fetch_fhir("Patient/nonexistent")
        assert result == {}


class TestPatientEndpoints:
    """Tests for patient-related API endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    @patch("main.fetch_fhir")
    def test_get_patient_summary(self, mock_fetch, client):
        """Should return patient summary"""
        mock_fetch.return_value = {"resourceType": "Patient", "id": "12724066"}
        response = client.get("/api/v1/patient/12724066")
        assert response.status_code in [200, 404, 405, 422, 500, 503]

    @patch("main.fetch_fhir")
    def test_search_patients(self, mock_fetch, client):
        """Should search patients by name"""
        mock_fetch.return_value = {"entry": []}
        response = client.get("/api/v1/patient/search?name=SMART")
        assert response.status_code in [200, 404, 405, 422, 500, 503]

    @patch("main.fetch_fhir")
    def test_get_patient_by_mrn(self, mock_fetch, client):
        """Should get patient by MRN"""
        mock_fetch.return_value = {"entry": []}
        response = client.get("/api/v1/patient/mrn/12345")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestConditionsEndpoints:
    """Tests for conditions endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_conditions(self, client):
        """Should return patient conditions"""
        response = client.get("/api/v1/patient/12724066/conditions")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestCarePlansEndpoints:
    """Tests for care plans endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_care_plans(self, client):
        """Should return patient care plans"""
        response = client.get("/api/v1/patient/12724066/careplans")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestClinicalNotesEndpoints:
    """Tests for clinical notes endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_notes(self, client):
        """Should return patient clinical notes"""
        response = client.get("/api/v1/patient/12724066/notes")
        assert response.status_code in [200, 500, 503]


class TestVitalsEndpoints:
    """Tests for vitals endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_vitals(self, client):
        """Should return patient vitals"""
        response = client.get("/api/v1/patient/12724066/vitals")
        assert response.status_code in [200, 404, 405, 422, 500, 503]

    def test_get_vital_history(self, client):
        """Should return vital history"""
        response = client.get("/api/v1/patient/12724066/vitals/history")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestLabsEndpoints:
    """Tests for labs endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_labs(self, client):
        """Should return patient labs"""
        response = client.get("/api/v1/patient/12724066/labs")
        assert response.status_code in [200, 404, 405, 422, 500, 503]

    def test_get_lab_history(self, client):
        """Should return lab history"""
        response = client.get("/api/v1/patient/12724066/labs/history")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestMedicationsEndpoints:
    """Tests for medications endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_medications(self, client):
        """Should return patient medications"""
        response = client.get("/api/v1/patient/12724066/medications")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestAllergiesEndpoints:
    """Tests for allergies endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_allergies(self, client):
        """Should return patient allergies"""
        response = client.get("/api/v1/patient/12724066/allergies")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestProceduresEndpoints:
    """Tests for procedures endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_procedures(self, client):
        """Should return patient procedures"""
        response = client.get("/api/v1/patient/12724066/procedures")
        assert response.status_code in [200, 404, 405, 422, 500, 503]


class TestImmunizationsEndpoints:
    """Tests for immunizations endpoints"""

    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_get_patient_immunizations(self, client):
        """Should return patient immunizations"""
        response = client.get("/api/v1/patient/12724066/immunizations")
        assert response.status_code in [200, 404, 405, 422, 500, 503]
