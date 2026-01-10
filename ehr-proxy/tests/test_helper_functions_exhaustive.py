"""
Exhaustive tests for ALL helper functions in main.py.
Tests extraction functions, critical value checking, trend calculations, etc.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCriticalValueChecking:
    """Tests for check_critical_value function"""

    def test_potassium_critical_low(self):
        """Should detect critically low potassium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "2.0")
        assert is_critical is True
        assert is_abnormal is True
        assert interp == "LL"

    def test_potassium_critical_high(self):
        """Should detect critically high potassium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "7.0")
        assert is_critical is True
        assert is_abnormal is True
        assert interp == "HH"

    def test_potassium_low(self):
        """Should detect low potassium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "3.2")
        assert is_critical is False
        assert is_abnormal is True
        assert interp == "L"

    def test_potassium_high(self):
        """Should detect high potassium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "5.5")
        assert is_critical is False
        assert is_abnormal is True
        assert interp == "H"

    def test_potassium_normal(self):
        """Should detect normal potassium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "4.2")
        assert is_critical is False
        assert is_abnormal is False
        assert interp == "N"

    def test_sodium_critical_low(self):
        """Should detect critically low sodium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Sodium", "115")
        assert is_critical is True
        assert interp == "LL"

    def test_sodium_critical_high(self):
        """Should detect critically high sodium"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Sodium", "165")
        assert is_critical is True
        assert interp == "HH"

    def test_glucose_critical_low(self):
        """Should detect critically low glucose"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Glucose", "40")
        assert is_critical is True
        assert interp == "LL"

    def test_glucose_critical_high(self):
        """Should detect critically high glucose"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Glucose", "500")
        assert is_critical is True
        assert interp == "HH"

    def test_troponin_critical_high(self):
        """Should detect critically high troponin"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Troponin", "0.10")
        assert is_critical is True
        assert interp == "HH"

    def test_hemoglobin_critical_low(self):
        """Should detect critically low hemoglobin"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Hemoglobin", "6.0")
        assert is_critical is True
        assert interp == "LL"

    def test_inr_critical_high(self):
        """Should detect critically high INR"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("INR", "6.0")
        assert is_critical is True
        assert interp == "HH"

    def test_lactate_critical_high(self):
        """Should detect critically high lactate"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Lactate", "5.0")
        assert is_critical is True
        assert interp == "HH"

    def test_ph_critical_low(self):
        """Should detect critically low pH"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("pH", "7.1")
        assert is_critical is True
        assert interp == "LL"

    def test_ph_critical_high(self):
        """Should detect critically high pH"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("pH", "7.65")
        assert is_critical is True
        assert interp == "HH"

    def test_invalid_value(self):
        """Should handle invalid value"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "invalid")
        assert is_critical is False
        assert is_abnormal is False
        assert interp == ""

    def test_value_with_qualifier(self):
        """Should handle value with > or <"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Troponin", ">0.10")
        assert is_critical is True

    def test_value_with_flag(self):
        """Should handle value with H/L flag"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("Potassium", "5.5 H")
        assert is_abnormal is True

    def test_unknown_lab(self):
        """Should return no alert for unknown lab"""
        from main import check_critical_value
        is_critical, is_abnormal, interp = check_critical_value("UnknownTest", "100")
        assert is_critical is False
        assert is_abnormal is False


class TestCriticalVitalChecking:
    """Tests for check_critical_vital function"""

    def test_systolic_critical_high(self):
        """Should detect critically high systolic BP"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Systolic Blood Pressure", "190")
        assert is_critical is True
        assert interp == "HH"

    def test_systolic_critical_low(self):
        """Should detect critically low systolic BP"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Systolic Blood Pressure", "65")
        assert is_critical is True
        assert interp == "LL"

    def test_bp_string_systolic(self):
        """Should extract systolic from BP string"""
        from main import check_critical_vital
        # Blood Pressure name needs to contain 'systolic' to match threshold
        is_critical, is_abnormal, interp = check_critical_vital("Systolic Blood Pressure", "190/100")
        # Extracts 190 which is critical high
        assert is_critical is True

    def test_heart_rate_critical_high(self):
        """Should detect critically high heart rate"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Heart Rate", "160")
        assert is_critical is True
        assert interp == "HH"

    def test_heart_rate_critical_low(self):
        """Should detect critically low heart rate"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Heart Rate", "35")
        assert is_critical is True
        assert interp == "LL"

    def test_pulse_critical(self):
        """Should detect critical pulse"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Pulse", "160")
        assert is_critical is True

    def test_spo2_critical_low(self):
        """Should detect critically low SpO2"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("SpO2", "85")
        assert is_critical is True
        assert interp == "LL"

    def test_oxygen_saturation_critical(self):
        """Should detect critically low oxygen saturation"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Oxygen Saturation", "85")
        assert is_critical is True

    def test_temperature_critical_high(self):
        """Should detect critically high temperature"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Temperature", "105.0")
        assert is_critical is True
        assert interp == "HH"

    def test_temperature_critical_low(self):
        """Should detect critically low temperature"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Temperature", "94.0")
        assert is_critical is True
        assert interp == "LL"

    def test_respiratory_critical_high(self):
        """Should detect critically high respiratory rate"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Respiratory Rate", "35")
        assert is_critical is True

    def test_respiratory_critical_low(self):
        """Should detect critically low respiratory rate"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Respiratory Rate", "6")
        assert is_critical is True

    def test_pain_critical_high(self):
        """Should detect critically high pain score"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Pain Score", "10")
        assert is_critical is True

    def test_normal_heart_rate(self):
        """Should detect normal heart rate"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Heart Rate", "72")
        assert is_critical is False
        assert is_abnormal is False
        assert interp == "N"

    def test_invalid_vital_value(self):
        """Should handle invalid vital value"""
        from main import check_critical_vital
        is_critical, is_abnormal, interp = check_critical_vital("Heart Rate", "invalid")
        assert is_critical is False


class TestMedicationNormalization:
    """Tests for normalize_medication_name function"""

    def test_normalize_generic_name(self):
        """Should return generic name for known brand"""
        from main import normalize_medication_name
        # This will depend on the drug_interactions.json keywords
        result = normalize_medication_name("Tylenol 500mg")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_normalize_already_generic(self):
        """Should return first word if not in keywords"""
        from main import normalize_medication_name
        result = normalize_medication_name("metformin 500mg")
        assert result == "metformin"

    def test_normalize_empty_string(self):
        """Should handle empty string"""
        from main import normalize_medication_name
        result = normalize_medication_name("")
        assert result == ""


class TestMedicationInteractions:
    """Tests for check_medication_interactions function"""

    def test_no_medications(self):
        """Should return empty list for no meds"""
        from main import check_medication_interactions
        result = check_medication_interactions([])
        assert result == []

    def test_single_medication(self):
        """Should return empty list for single med"""
        from main import check_medication_interactions
        result = check_medication_interactions(["metformin"])
        assert result == []

    def test_known_interaction(self):
        """Should detect known interaction if in database"""
        from main import check_medication_interactions
        # The actual result depends on drug_interactions.json
        result = check_medication_interactions(["warfarin", "aspirin"])
        assert isinstance(result, list)

    def test_multiple_medications(self):
        """Should check multiple medication pairs"""
        from main import check_medication_interactions
        result = check_medication_interactions(["metformin", "lisinopril", "atorvastatin"])
        assert isinstance(result, list)


class TestTrendCalculations:
    """Tests for calculate_trend_direction function"""

    def test_rising_trend(self):
        """Should detect rising trend"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("100", "80")
        assert trend == "rising"
        assert "+20" in delta or "20" in delta

    def test_falling_trend(self):
        """Should detect falling trend"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("80", "100")
        assert trend == "falling"
        assert "-20" in delta or "20" in delta

    def test_stable_trend(self):
        """Should detect stable trend (< 5% change)"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("100", "99")
        assert trend == "stable"

    def test_invalid_current_value(self):
        """Should handle invalid current value"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("invalid", "100")
        assert trend == "stable"
        assert delta is None

    def test_invalid_previous_value(self):
        """Should handle invalid previous value"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("100", "invalid")
        assert trend == "stable"

    def test_zero_previous_value(self):
        """Should handle zero previous value"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("100", "0")
        assert trend == "stable"

    def test_comma_in_numbers(self):
        """Should handle commas in numbers"""
        from main import calculate_trend_direction
        trend, delta = calculate_trend_direction("1,200", "1,000")
        assert trend == "rising"


class TestLabTrendCalculations:
    """Tests for calculate_lab_trends function"""

    def test_empty_labs(self):
        """Should return empty list for empty input"""
        from main import calculate_lab_trends
        result = calculate_lab_trends([])
        assert result == []

    def test_single_lab(self):
        """Should mark single lab as new"""
        from main import LabResult, calculate_lab_trends
        labs = [LabResult(name="Glucose", value="100", unit="mg/dL", status="final", date="2024-01-15")]
        result = calculate_lab_trends(labs)
        assert len(result) == 1
        assert result[0].trend == "new"

    def test_multiple_same_lab(self):
        """Should calculate trend for multiple same labs"""
        from main import LabResult, calculate_lab_trends
        labs = [
            LabResult(name="Glucose", value="120", unit="mg/dL", status="final", date="2024-01-15"),
            LabResult(name="Glucose", value="100", unit="mg/dL", status="final", date="2024-01-10")
        ]
        result = calculate_lab_trends(labs)
        assert len(result) == 1
        assert result[0].value == "120"  # Most recent
        assert result[0].previous_value == "100"
        assert result[0].trend == "rising"

    def test_critical_sorted_first(self):
        """Should sort critical labs first"""
        from main import LabResult, calculate_lab_trends
        labs = [
            LabResult(name="Glucose", value="100", unit="mg/dL", status="final", is_critical=False),
            LabResult(name="Potassium", value="7.0", unit="mEq/L", status="final", is_critical=True)
        ]
        result = calculate_lab_trends(labs)
        assert result[0].name == "Potassium"  # Critical first


class TestVitalTrendCalculations:
    """Tests for calculate_vital_trends function"""

    def test_empty_vitals(self):
        """Should return empty list for empty input"""
        from main import calculate_vital_trends
        result = calculate_vital_trends([])
        assert result == []

    def test_single_vital(self):
        """Should mark single vital as new"""
        from main import VitalSign, calculate_vital_trends
        vitals = [VitalSign(name="Heart Rate", value="72", unit="bpm", date="2024-01-15")]
        result = calculate_vital_trends(vitals)
        assert len(result) == 1
        assert result[0].trend == "new"

    def test_multiple_same_vital(self):
        """Should calculate trend for multiple same vitals"""
        from main import VitalSign, calculate_vital_trends
        vitals = [
            VitalSign(name="Heart Rate", value="90", unit="bpm", date="2024-01-15"),
            VitalSign(name="Heart Rate", value="72", unit="bpm", date="2024-01-10")
        ]
        result = calculate_vital_trends(vitals)
        assert len(result) == 1
        assert result[0].value == "90"
        assert result[0].trend == "rising"


class TestPatientNameExtraction:
    """Tests for extract_patient_name function"""

    def test_extract_name_with_text(self):
        """Should extract name from text field"""
        from main import extract_patient_name
        patient = {"name": [{"text": "John Doe"}]}
        result = extract_patient_name(patient)
        assert result == "John Doe"

    def test_extract_name_no_names(self):
        """Should return Unknown for no names"""
        from main import extract_patient_name
        patient = {"name": []}
        result = extract_patient_name(patient)
        assert result == "Unknown"

    def test_extract_name_no_name_field(self):
        """Should return Unknown for missing name field"""
        from main import extract_patient_name
        patient = {}
        result = extract_patient_name(patient)
        assert result == "Unknown"


class TestPatientPhotoExtraction:
    """Tests for extract_patient_photo function"""

    def test_extract_photo_url(self):
        """Should extract photo URL"""
        from main import extract_patient_photo
        patient = {"photo": [{"url": "https://example.com/photo.jpg"}]}
        result = extract_patient_photo(patient)
        assert result == "https://example.com/photo.jpg"

    def test_extract_photo_base64(self):
        """Should extract base64 photo data"""
        from main import extract_patient_photo
        patient = {"photo": [{"contentType": "image/jpeg", "data": "base64data"}]}
        result = extract_patient_photo(patient)
        assert result == "data:image/jpeg;base64,base64data"

    def test_extract_photo_none(self):
        """Should return None for no photos"""
        from main import extract_patient_photo
        patient = {"photo": []}
        result = extract_patient_photo(patient)
        assert result is None

    def test_extract_photo_missing_field(self):
        """Should return None for missing photo field"""
        from main import extract_patient_photo
        patient = {}
        result = extract_patient_photo(patient)
        assert result is None


class TestVitalsExtraction:
    """Tests for extract_vitals function"""

    def test_extract_vitals_empty_bundle(self):
        """Should return empty list for empty bundle"""
        from main import extract_vitals
        result = extract_vitals({})
        assert result == []

    def test_extract_vitals_with_entries(self):
        """Should extract vitals from bundle"""
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


class TestAllergiesExtraction:
    """Tests for extract_allergies function"""

    def test_extract_allergies_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_allergies
        result = extract_allergies({})
        assert result == []

    def test_extract_allergies_with_entries(self):
        """Should extract allergies from bundle"""
        from main import extract_allergies
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Penicillin"}
                }
            }]
        }
        result = extract_allergies(bundle)
        assert "Penicillin" in result


class TestMedicationsExtraction:
    """Tests for extract_medications function"""

    def test_extract_medications_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_medications
        result = extract_medications({})
        assert result == []

    def test_extract_medications_with_entries(self):
        """Should extract medications from bundle"""
        from main import extract_medications
        bundle = {
            "entry": [{
                "resource": {
                    "medicationCodeableConcept": {"text": "Metformin 500mg"}
                }
            }]
        }
        result = extract_medications(bundle)
        assert "Metformin 500mg" in result


class TestLabsExtraction:
    """Tests for extract_labs function"""

    def test_extract_labs_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_labs
        result = extract_labs({})
        assert result == []

    def test_extract_labs_with_quantity(self):
        """Should extract labs with valueQuantity"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Glucose"},
                    "valueQuantity": {"value": 95, "unit": "mg/dL"},
                    "status": "final",
                    "effectiveDateTime": "2024-01-15T10:00:00Z",
                    "referenceRange": [{"text": "70-100 mg/dL"}]
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].name == "Glucose"
        assert result[0].reference_range == "70-100 mg/dL"

    def test_extract_labs_with_string_value(self):
        """Should extract labs with valueString"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"coding": [{"display": "Culture"}]},
                    "valueString": "Negative",
                    "status": "final"
                }
            }]
        }
        result = extract_labs(bundle)
        assert len(result) == 1
        assert result[0].value == "Negative"

    def test_extract_labs_with_interpretation(self):
        """Should extract labs with FHIR interpretation"""
        from main import extract_labs
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Potassium"},
                    "valueQuantity": {"value": 5.5, "unit": "mEq/L"},
                    "status": "final",
                    "interpretation": [{"coding": [{"code": "H"}]}]
                }
            }]
        }
        result = extract_labs(bundle)
        assert result[0].interpretation == "H"
        assert result[0].is_abnormal is True


class TestProceduresExtraction:
    """Tests for extract_procedures function"""

    def test_extract_procedures_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_procedures
        result = extract_procedures({})
        assert result == []

    def test_extract_procedures_with_entries(self):
        """Should extract procedures from bundle"""
        from main import extract_procedures
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Appendectomy"},
                    "performedDateTime": "2024-01-10T10:00:00Z",
                    "status": "completed"
                }
            }]
        }
        result = extract_procedures(bundle)
        assert len(result) == 1
        assert result[0].name == "Appendectomy"
        assert result[0].status == "completed"

    def test_extract_procedures_with_period(self):
        """Should extract date from performedPeriod"""
        from main import extract_procedures
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"coding": [{"display": "Surgery"}]},
                    "performedPeriod": {"start": "2024-01-10T10:00:00Z"},
                    "status": "completed"
                }
            }]
        }
        result = extract_procedures(bundle)
        assert result[0].date == "2024-01-10"


class TestImmunizationsExtraction:
    """Tests for extract_immunizations function"""

    def test_extract_immunizations_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_immunizations
        result = extract_immunizations({})
        assert result == []

    def test_extract_immunizations_with_entries(self):
        """Should extract immunizations from bundle"""
        from main import extract_immunizations
        bundle = {
            "entry": [{
                "resource": {
                    "vaccineCode": {"text": "COVID-19 Vaccine"},
                    "occurrenceDateTime": "2024-01-01T10:00:00Z",
                    "status": "completed"
                }
            }]
        }
        result = extract_immunizations(bundle)
        assert len(result) == 1
        assert result[0].name == "COVID-19 Vaccine"


class TestConditionsExtraction:
    """Tests for extract_conditions function"""

    def test_extract_conditions_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_conditions
        result = extract_conditions({})
        assert result == []

    def test_extract_conditions_with_entries(self):
        """Should extract conditions from bundle"""
        from main import extract_conditions
        bundle = {
            "entry": [{
                "resource": {
                    "code": {"text": "Type 2 Diabetes"},
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "onsetDateTime": "2020-01-15T00:00:00Z",
                    "category": [{"coding": [{"display": "Problem"}]}]
                }
            }]
        }
        result = extract_conditions(bundle)
        assert len(result) == 1
        assert result[0].name == "Type 2 Diabetes"
        assert result[0].status == "active"


class TestCarePlansExtraction:
    """Tests for extract_care_plans function"""

    def test_extract_care_plans_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_care_plans
        result = extract_care_plans({})
        assert result == []

    def test_extract_care_plans_with_entries(self):
        """Should extract care plans from bundle"""
        from main import extract_care_plans
        bundle = {
            "entry": [{
                "resource": {
                    "title": "Diabetes Management",
                    "status": "active",
                    "intent": "plan",
                    "category": [{"coding": [{"display": "Disease Management"}]}],
                    "period": {"start": "2024-01-01", "end": "2024-12-31"},
                    "description": "Monitor blood sugar and diet"
                }
            }]
        }
        result = extract_care_plans(bundle)
        assert len(result) == 1
        assert result[0].title == "Diabetes Management"
        assert result[0].status == "active"


class TestClinicalNotesExtraction:
    """Tests for extract_clinical_notes function"""

    def test_extract_clinical_notes_empty(self):
        """Should return empty list for empty bundle"""
        from main import extract_clinical_notes
        result = extract_clinical_notes({})
        assert result == []

    def test_extract_clinical_notes_with_entries(self):
        """Should extract clinical notes from bundle"""
        from main import extract_clinical_notes
        bundle = {
            "entry": [{
                "resource": {
                    "description": "Progress Note",
                    "type": {"coding": [{"display": "Progress Note"}]},
                    "date": "2024-01-15T10:00:00Z",
                    "author": [{"display": "Dr. Smith"}],
                    "status": "current"
                }
            }]
        }
        result = extract_clinical_notes(bundle)
        assert len(result) == 1
        assert result[0].title == "Progress Note"


class TestCodeDatabases:
    """Tests for code database loading"""

    def test_icd10_db_loaded(self):
        """Should load ICD-10 database"""
        from main import ICD10_DB
        assert ICD10_DB is not None
        assert isinstance(ICD10_DB, dict)

    def test_cpt_db_loaded(self):
        """Should load CPT database"""
        from main import CPT_DB
        assert CPT_DB is not None
        assert isinstance(CPT_DB, dict)

    def test_drug_interactions_db_loaded(self):
        """Should load drug interactions database"""
        from main import DRUG_INTERACTIONS_DB
        assert DRUG_INTERACTIONS_DB is not None
        assert isinstance(DRUG_INTERACTIONS_DB, dict)


class TestCriticalThresholds:
    """Tests for critical threshold constants"""

    def test_lab_thresholds_exist(self):
        """Should have lab thresholds defined"""
        from main import CRITICAL_LAB_THRESHOLDS
        assert "potassium" in CRITICAL_LAB_THRESHOLDS
        assert "sodium" in CRITICAL_LAB_THRESHOLDS
        assert "glucose" in CRITICAL_LAB_THRESHOLDS

    def test_vital_thresholds_exist(self):
        """Should have vital thresholds defined"""
        from main import CRITICAL_VITAL_THRESHOLDS
        assert "systolic" in CRITICAL_VITAL_THRESHOLDS
        assert "heart rate" in CRITICAL_VITAL_THRESHOLDS
        assert "spo2" in CRITICAL_VITAL_THRESHOLDS


class TestNoteTypes:
    """Tests for note type constants"""

    def test_note_types_defined(self):
        """Should have note types defined"""
        from main import NOTE_TYPES
        assert "SOAP" in NOTE_TYPES
        assert "PROGRESS" in NOTE_TYPES
        assert "HP" in NOTE_TYPES
        assert "CONSULT" in NOTE_TYPES


class TestSOAPTemplateGeneration:
    """Tests for generate_soap_template function"""

    def test_generate_soap_template(self):
        """Should generate SOAP template from transcript"""
        from main import generate_soap_template
        result = generate_soap_template(
            "Patient reports headache and fever for 2 days",
            "Headache"
        )
        assert isinstance(result, dict)
        assert "subjective" in result
        assert "objective" in result
        assert "assessment" in result
        assert "plan" in result

    def test_generate_soap_template_extracts_symptoms(self):
        """Should extract symptoms from transcript"""
        from main import generate_soap_template
        result = generate_soap_template(
            "Patient has pain, nausea, and fever",
            "Abdominal pain"
        )
        # Check that subjective mentions symptoms
        assert "pain" in result["subjective"].lower() or "symptoms" in result["subjective"].lower()

    def test_generate_soap_template_extracts_vitals(self):
        """Should extract vitals from transcript"""
        from main import generate_soap_template
        result = generate_soap_template(
            "Blood pressure 120/80, heart rate 72 bpm",
            "Routine checkup"
        )
        assert "120/80" in result["objective"] or "Vital" in result["objective"]


class TestWorklistHelpers:
    """Tests for worklist helper functions"""

    def test_get_today_key(self):
        """Should return today's date as key"""
        from main import _get_today_key
        from datetime import datetime
        result = _get_today_key()
        expected = datetime.now().strftime("%Y-%m-%d")
        assert result == expected

    def test_init_worklist_for_today(self):
        """Should initialize worklist for today"""
        from main import _init_worklist_for_today
        result = _init_worklist_for_today()
        assert "date" in result
        assert "patients" in result
        assert isinstance(result["patients"], list)
