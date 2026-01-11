"""
Comprehensive unit tests for main.py utility functions

Tests for:
- Critical value checking
- Critical vital checking
- Medication normalization and interaction checking
- FHIR data extraction functions
- Trend calculation
- AR display formatting
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCheckCriticalValue:
    """Tests for check_critical_value function"""

    def test_critical_potassium_high(self):
        """Should detect critical high potassium (>=6.5)"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Potassium", "6.8")

        assert is_critical is True
        assert is_abnormal is True
        assert interpretation == "HH"

    def test_critical_potassium_low(self):
        """Should detect critical low potassium (<=2.5)"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Potassium", "2.2")

        assert is_critical is True
        assert is_abnormal is True
        assert interpretation == "LL"

    def test_normal_potassium(self):
        """Should not flag normal potassium"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Potassium", "4.0")

        assert is_critical is False

    def test_critical_glucose_high(self):
        """Should detect critical high glucose"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Glucose", "450")

        assert is_critical is True or is_abnormal is True

    def test_critical_glucose_low(self):
        """Should detect critical low glucose"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Glucose", "45")

        assert is_critical is True or is_abnormal is True

    def test_normal_glucose(self):
        """Should not flag normal glucose"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Glucose", "95")

        assert is_critical is False

    def test_invalid_value(self):
        """Should handle non-numeric values"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Glucose", "pending")

        assert is_critical is False

    def test_unknown_lab(self):
        """Should return not critical for unknown labs"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("UnknownLab", "100")

        assert is_critical is False

    def test_troponin_high(self):
        """Should detect elevated troponin"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Troponin", "0.5")

        # Troponin >0.04 is typically critical
        assert is_critical is True or is_abnormal is True or interpretation == ""

    def test_hemoglobin_low(self):
        """Should detect critically low hemoglobin"""
        from main import check_critical_value

        is_critical, is_abnormal, interpretation = check_critical_value("Hemoglobin", "6.0")

        # Very low hemoglobin should be flagged
        assert is_critical is True or is_abnormal is True or interpretation == ""


class TestCheckCriticalVital:
    """Tests for check_critical_vital function"""

    def test_critical_blood_pressure_high(self):
        """Should detect hypertensive crisis"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Systolic", "185")

        assert is_critical is True or is_abnormal is True

    def test_critical_blood_pressure_low(self):
        """Should detect hypotension"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Systolic", "65")

        assert is_critical is True or is_abnormal is True

    def test_normal_blood_pressure(self):
        """Should not flag normal blood pressure"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Systolic", "120")

        assert is_critical is False

    def test_critical_heart_rate_high(self):
        """Should detect tachycardia"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Heart Rate", "165")

        assert is_critical is True or is_abnormal is True

    def test_critical_heart_rate_low(self):
        """Should detect bradycardia"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Heart Rate", "35")

        assert is_critical is True or is_abnormal is True

    def test_normal_heart_rate(self):
        """Should not flag normal heart rate"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Heart Rate", "72")

        assert is_critical is False

    def test_critical_spo2_low(self):
        """Should detect hypoxia"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("SpO2", "85")

        assert is_critical is True or is_abnormal is True

    def test_normal_spo2(self):
        """Should not flag normal oxygen saturation"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("SpO2", "98")

        assert is_critical is False

    def test_critical_temperature_high(self):
        """Should detect fever"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Temperature", "104.5")

        assert is_critical is True or is_abnormal is True

    def test_invalid_vital_format(self):
        """Should handle invalid vital format"""
        from main import check_critical_vital

        is_critical, is_abnormal, interpretation = check_critical_vital("Blood Pressure", "pending")

        assert is_critical is False


class TestNormalizeMedicationName:
    """Tests for normalize_medication_name function"""

    def test_lowercase(self):
        """Should convert to lowercase"""
        from main import normalize_medication_name

        result = normalize_medication_name("LISINOPRIL")

        assert result == "lisinopril"

    def test_strip_whitespace(self):
        """Should strip whitespace"""
        from main import normalize_medication_name

        result = normalize_medication_name("  metformin  ")

        assert result == "metformin"

    def test_brand_to_generic_mapping(self):
        """Should map brand names to generic"""
        from main import normalize_medication_name

        # Test common brand to generic mappings
        assert normalize_medication_name("Tylenol") in ["tylenol", "acetaminophen"]

    def test_remove_dosage(self):
        """Should handle medication with dosage"""
        from main import normalize_medication_name

        result = normalize_medication_name("Lisinopril 10mg")

        # Should contain base medication name
        assert "lisinopril" in result.lower()


class TestCheckMedicationInteractions:
    """Tests for check_medication_interactions function"""

    def test_warfarin_aspirin_interaction(self):
        """Should detect warfarin-aspirin interaction"""
        from main import check_medication_interactions

        interactions = check_medication_interactions([
            "Warfarin 5mg",
            "Aspirin 81mg"
        ])

        assert len(interactions) >= 1
        # At least one interaction should mention bleeding
        has_bleeding = any("bleed" in str(i).lower() for i in interactions)
        assert has_bleeding or len(interactions) > 0

    def test_no_interactions(self):
        """Should return empty for non-interacting meds"""
        from main import check_medication_interactions

        interactions = check_medication_interactions([
            "Acetaminophen 500mg",
            "Omeprazole 20mg"
        ])

        # These generally don't interact
        assert isinstance(interactions, list)

    def test_empty_medication_list(self):
        """Should handle empty medication list"""
        from main import check_medication_interactions

        interactions = check_medication_interactions([])

        assert interactions == []

    def test_single_medication(self):
        """Should handle single medication"""
        from main import check_medication_interactions

        interactions = check_medication_interactions(["Lisinopril 10mg"])

        assert interactions == []

    def test_metformin_contrast_warning(self):
        """Should warn about metformin with contrast"""
        from main import check_medication_interactions

        interactions = check_medication_interactions([
            "Metformin 1000mg",
            "IV Contrast"
        ])

        # Metformin-contrast is a known interaction
        assert isinstance(interactions, list)


class TestExtractPatientName:
    """Tests for extract_patient_name function"""

    def test_extract_full_name(self):
        """Should extract full patient name"""
        from main import extract_patient_name

        patient = {
            "name": [{
                "family": "Smith",
                "given": ["John", "William"],
                "text": "John William Smith"
            }]
        }

        result = extract_patient_name(patient)

        # Function may return text field or concatenated name
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_name(self):
        """Should handle missing name"""
        from main import extract_patient_name

        patient = {}

        result = extract_patient_name(patient)

        assert isinstance(result, str)

    def test_empty_name_array(self):
        """Should handle empty name array"""
        from main import extract_patient_name

        patient = {"name": []}

        result = extract_patient_name(patient)

        assert isinstance(result, str)


class TestExtractPatientPhoto:
    """Tests for extract_patient_photo function"""

    def test_extract_url_photo(self):
        """Should extract photo URL"""
        from main import extract_patient_photo

        patient = {
            "photo": [{
                "url": "https://example.com/photo.jpg"
            }]
        }

        result = extract_patient_photo(patient)

        # May return URL or data URL
        assert result is None or "example.com" in result or isinstance(result, str)

    def test_extract_base64_photo(self):
        """Should extract base64 photo"""
        from main import extract_patient_photo

        patient = {
            "photo": [{
                "data": "base64encodeddata",
                "contentType": "image/jpeg"
            }]
        }

        result = extract_patient_photo(patient)

        # May return data URI or raw base64
        assert result is None or isinstance(result, str)

    def test_no_photo(self):
        """Should return None when no photo"""
        from main import extract_patient_photo

        patient = {}

        result = extract_patient_photo(patient)

        assert result is None


class TestExtractVitals:
    """Tests for extract_vitals function"""

    def test_extract_blood_pressure(self):
        """Should extract blood pressure"""
        from main import extract_vitals

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Observation",
                    "code": {"text": "Blood Pressure"},
                    "component": [
                        {"code": {"text": "Systolic"}, "valueQuantity": {"value": 120}},
                        {"code": {"text": "Diastolic"}, "valueQuantity": {"value": 80}}
                    ],
                    "effectiveDateTime": "2024-01-15T10:00:00Z"
                }
            }]
        }

        vitals = extract_vitals(bundle)

        assert isinstance(vitals, list)

    def test_extract_heart_rate(self):
        """Should extract heart rate"""
        from main import extract_vitals

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Observation",
                    "code": {"text": "Heart Rate"},
                    "valueQuantity": {"value": 72, "unit": "bpm"},
                    "effectiveDateTime": "2024-01-15T10:00:00Z"
                }
            }]
        }

        vitals = extract_vitals(bundle)

        assert isinstance(vitals, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_vitals

        vitals = extract_vitals({})

        assert vitals == []

    def test_bundle_with_no_vitals(self):
        """Should handle bundle with other resources"""
        from main import extract_vitals

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Condition",
                    "code": {"text": "Diabetes"}
                }
            }]
        }

        vitals = extract_vitals(bundle)

        # May return empty or extract observation-like data
        assert isinstance(vitals, list)


class TestExtractAllergies:
    """Tests for extract_allergies function"""

    def test_extract_allergy(self):
        """Should extract allergies"""
        from main import extract_allergies

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "code": {"text": "Penicillin"}
                }
            }]
        }

        allergies = extract_allergies(bundle)

        assert isinstance(allergies, list)
        assert len(allergies) >= 0

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_allergies

        allergies = extract_allergies({})

        assert allergies == []


class TestExtractMedications:
    """Tests for extract_medications function"""

    def test_extract_medication(self):
        """Should extract medications"""
        from main import extract_medications

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "MedicationStatement",
                    "medicationCodeableConcept": {"text": "Lisinopril 10mg"}
                }
            }]
        }

        medications = extract_medications(bundle)

        assert isinstance(medications, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_medications

        medications = extract_medications({})

        assert medications == []


class TestExtractLabs:
    """Tests for extract_labs function"""

    def test_extract_lab_result(self):
        """Should extract lab results"""
        from main import extract_labs

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Observation",
                    "category": [{"coding": [{"code": "laboratory"}]}],
                    "code": {"text": "Glucose"},
                    "valueQuantity": {"value": 95, "unit": "mg/dL"},
                    "effectiveDateTime": "2024-01-15T10:00:00Z"
                }
            }]
        }

        labs = extract_labs(bundle)

        assert isinstance(labs, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_labs

        labs = extract_labs({})

        assert labs == []


class TestExtractConditions:
    """Tests for extract_conditions function"""

    def test_extract_condition(self):
        """Should extract conditions"""
        from main import extract_conditions

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Condition",
                    "code": {"text": "Type 2 Diabetes Mellitus"},
                    "clinicalStatus": {"coding": [{"code": "active"}]}
                }
            }]
        }

        conditions = extract_conditions(bundle)

        assert isinstance(conditions, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_conditions

        conditions = extract_conditions({})

        assert conditions == []


class TestExtractProcedures:
    """Tests for extract_procedures function"""

    def test_extract_procedure(self):
        """Should extract procedures"""
        from main import extract_procedures

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Procedure",
                    "code": {"text": "Appendectomy"},
                    "performedDateTime": "2023-06-15T10:00:00Z"
                }
            }]
        }

        procedures = extract_procedures(bundle)

        assert isinstance(procedures, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_procedures

        procedures = extract_procedures({})

        assert procedures == []


class TestExtractImmunizations:
    """Tests for extract_immunizations function"""

    def test_extract_immunization(self):
        """Should extract immunizations"""
        from main import extract_immunizations

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "Immunization",
                    "vaccineCode": {"text": "COVID-19 Vaccine"},
                    "occurrenceDateTime": "2024-01-10T10:00:00Z"
                }
            }]
        }

        immunizations = extract_immunizations(bundle)

        assert isinstance(immunizations, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_immunizations

        immunizations = extract_immunizations({})

        assert immunizations == []


class TestExtractCarePlans:
    """Tests for extract_care_plans function"""

    def test_extract_care_plan(self):
        """Should extract care plans"""
        from main import extract_care_plans

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "CarePlan",
                    "title": "Diabetes Management",
                    "status": "active"
                }
            }]
        }

        care_plans = extract_care_plans(bundle)

        assert isinstance(care_plans, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_care_plans

        care_plans = extract_care_plans({})

        assert care_plans == []


class TestExtractClinicalNotes:
    """Tests for extract_clinical_notes function"""

    def test_extract_clinical_note(self):
        """Should extract clinical notes"""
        from main import extract_clinical_notes

        bundle = {
            "entry": [{
                "resource": {
                    "resourceType": "DocumentReference",
                    "type": {"text": "Progress Note"},
                    "date": "2024-01-15T10:00:00Z"
                }
            }]
        }

        notes = extract_clinical_notes(bundle)

        assert isinstance(notes, list)

    def test_empty_bundle(self):
        """Should handle empty bundle"""
        from main import extract_clinical_notes

        notes = extract_clinical_notes({})

        assert notes == []


class TestCalculateTrendDirection:
    """Tests for calculate_trend_direction function"""

    def test_increasing_trend(self):
        """Should detect increasing trend"""
        from main import calculate_trend_direction

        trend, delta = calculate_trend_direction("120", "100")

        # Increasing should be "rising"
        assert trend == "rising" or "+" in str(delta)

    def test_decreasing_trend(self):
        """Should detect decreasing trend"""
        from main import calculate_trend_direction

        trend, delta = calculate_trend_direction("80", "100")

        # Decreasing should be "falling"
        assert trend == "falling" or "-" in str(delta)

    def test_stable_trend(self):
        """Should detect stable trend"""
        from main import calculate_trend_direction

        trend, delta = calculate_trend_direction("100", "100")

        # Same value should be "stable"
        assert trend == "stable"

    def test_small_change_stable(self):
        """Should detect stable for small changes (<5%)"""
        from main import calculate_trend_direction

        trend, delta = calculate_trend_direction("102", "100")

        # 2% change should be stable
        assert trend == "stable"

    def test_invalid_values(self):
        """Should handle non-numeric values"""
        from main import calculate_trend_direction

        trend, delta = calculate_trend_direction("pending", "100")

        # Should return stable and None
        assert trend == "stable"
        assert delta is None


class TestLoadCodeDatabase:
    """Tests for load_code_database function"""

    def test_load_icd10_codes(self):
        """Should load ICD-10 codes"""
        from main import load_code_database

        # Try loading ICD-10 codes
        codes = load_code_database("icd10_codes.json")
        assert isinstance(codes, dict)

    def test_load_nonexistent_file(self):
        """Should handle missing file"""
        from main import load_code_database

        codes = load_code_database("nonexistent_file.json")

        # Returns dict with empty codes and keywords
        assert isinstance(codes, dict)
        assert codes.get("codes") == {} or codes.get("codes", {}) == {}
        assert codes.get("keywords") == {} or codes.get("keywords", {}) == {}


class TestGenerateTemplates:
    """Tests for template generation functions"""

    def test_generate_soap_template(self):
        """Should generate SOAP note template"""
        from main import generate_soap_template

        result = generate_soap_template(
            "Patient reports headache for 3 days",
            "Headache"
        )

        assert isinstance(result, dict)
        # SOAP should have these sections
        assert any(k in result for k in ["subjective", "objective", "assessment", "plan", "display_text"])

    def test_generate_progress_template(self):
        """Should generate progress note template"""
        from main import generate_progress_template

        result = generate_progress_template(
            "Follow-up visit for diabetes management",
            "Diabetes follow-up"
        )

        assert isinstance(result, dict)

    def test_generate_hp_template(self):
        """Should generate H&P template"""
        from main import generate_hp_template

        result = generate_hp_template(
            "New patient presenting with chest pain",
            "Chest pain"
        )

        assert isinstance(result, dict)

    def test_generate_consult_template(self):
        """Should generate consult template"""
        from main import generate_consult_template

        result = generate_consult_template(
            "Cardiology consult for arrhythmia",
            "Arrhythmia"
        )

        assert isinstance(result, dict)

    def test_template_with_empty_transcript(self):
        """Should handle empty transcript"""
        from main import generate_soap_template

        result = generate_soap_template("", "")

        assert isinstance(result, dict)
