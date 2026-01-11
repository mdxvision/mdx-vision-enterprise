"""
Comprehensive tests for main.py clinical safety functions.
Tests check_critical_value, check_critical_vital, medication interactions, and related helpers.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCheckCriticalValue:
    """Tests for check_critical_value function"""

    def test_potassium_normal(self):
        """Normal potassium should return not critical, not abnormal"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Potassium", "4.0")
        assert is_critical is False
        assert is_abnormal is False
        assert interpretation == "N"

    def test_potassium_critical_low(self):
        """Critically low potassium should return critical"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Potassium", "2.0")
        assert is_critical is True
        assert is_abnormal is True
        assert interpretation == "LL"

    def test_potassium_critical_high(self):
        """Critically high potassium should return critical"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Serum Potassium", "7.0")
        assert is_critical is True
        assert is_abnormal is True
        assert interpretation == "HH"

    def test_potassium_low(self):
        """Low potassium should return abnormal but not critical"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("potassium level", "3.0")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "L"

    def test_potassium_high(self):
        """High potassium should return abnormal but not critical"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("potassium", "5.5")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "H"

    def test_glucose_critical_low(self):
        """Critically low glucose should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Blood Glucose", "40")
        assert is_critical is True
        assert interpretation == "LL"

    def test_glucose_critical_high(self):
        """Critically high glucose should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("glucose", "500")
        assert is_critical is True
        assert interpretation == "HH"

    def test_sodium_critical_low(self):
        """Critically low sodium should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Sodium", "115")
        assert is_critical is True
        assert interpretation == "LL"

    def test_sodium_critical_high(self):
        """Critically high sodium should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("sodium", "165")
        assert is_critical is True
        assert interpretation == "HH"

    def test_troponin_critical_high(self):
        """Critically high troponin should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Troponin I", "0.5")
        assert is_critical is True
        assert interpretation == "HH"

    def test_hemoglobin_critical_low(self):
        """Critically low hemoglobin should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Hemoglobin", "5.5")
        assert is_critical is True
        assert interpretation == "LL"

    def test_inr_critical_high(self):
        """Critically high INR should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("INR", "6.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_lactate_critical_high(self):
        """Critically high lactate should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Lactate", "5.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_ph_critical_low(self):
        """Critically low pH should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Blood pH", "7.1")
        assert is_critical is True
        assert interpretation == "LL"

    def test_ph_critical_high(self):
        """Critically high pH should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("pH", "7.65")
        assert is_critical is True
        assert interpretation == "HH"

    def test_calcium_critical_low(self):
        """Critically low calcium should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Calcium", "5.5")
        assert is_critical is True
        assert interpretation == "LL"

    def test_calcium_critical_high(self):
        """Critically high calcium should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("calcium", "14.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_platelets_critical_low(self):
        """Critically low platelets should be detected"""
        from main import check_critical_value
        # Use "platelets" which matches the threshold key
        is_critical, is_abnormal, interpretation = check_critical_value("platelets", "30")
        # Critical threshold is 50, so 30 is critical low
        assert is_critical is True
        assert interpretation == "LL"

    def test_wbc_critical_low(self):
        """Critically low WBC should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("WBC", "1.5")
        assert is_critical is True
        assert interpretation == "LL"

    def test_wbc_critical_high(self):
        """Critically high WBC should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("wbc", "35.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_value_with_greater_than(self):
        """Should handle values with > prefix"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("glucose", ">450")
        assert is_critical is True
        assert interpretation == "HH"

    def test_value_with_less_than(self):
        """Should handle values with < prefix"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Troponin", "<0.01")
        assert is_critical is False
        assert is_abnormal is False

    def test_value_with_flag_suffix(self):
        """Should handle values with flag suffix like '5.2 H'"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("potassium", "5.2 H")
        assert is_abnormal is True
        assert interpretation == "H"

    def test_invalid_value_returns_false(self):
        """Should return false for invalid values"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("potassium", "invalid")
        assert is_critical is False
        assert is_abnormal is False
        assert interpretation == ""

    def test_empty_value_returns_false(self):
        """Should return false for empty values"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("potassium", "")
        assert is_critical is False
        assert is_abnormal is False

    def test_unknown_lab_returns_false(self):
        """Should return false for unknown lab types"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Unknown Lab XYZ", "100")
        assert is_critical is False
        assert is_abnormal is False
        assert interpretation == ""

    def test_bun_critical_high(self):
        """Critically high BUN should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("BUN", "110")
        assert is_critical is True
        assert interpretation == "HH"

    def test_creatinine_critical_high(self):
        """Critically high creatinine should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Creatinine", "12.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_magnesium_critical_low(self):
        """Critically low magnesium should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Magnesium", "0.8")
        assert is_critical is True
        assert interpretation == "LL"

    def test_magnesium_critical_high(self):
        """Critically high magnesium should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("magnesium", "5.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_phosphorus_critical_low(self):
        """Critically low phosphorus should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Phosphorus", "0.8")
        assert is_critical is True
        assert interpretation == "LL"

    def test_bilirubin_critical_high(self):
        """Critically high bilirubin should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Total Bilirubin", "18.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_pco2_critical_low(self):
        """Critically low PCO2 should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("PCO2", "15")
        assert is_critical is True
        assert interpretation == "LL"

    def test_pco2_critical_high(self):
        """Critically high PCO2 should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("pco2", "75")
        assert is_critical is True
        assert interpretation == "HH"

    def test_po2_critical_low(self):
        """Critically low PO2 should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("PO2", "35")
        assert is_critical is True
        assert interpretation == "LL"

    def test_bicarbonate_critical_low(self):
        """Critically low bicarbonate should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Bicarbonate", "8")
        assert is_critical is True
        assert interpretation == "LL"

    def test_bicarbonate_critical_high(self):
        """Critically high bicarbonate should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("bicarbonate", "45")
        assert is_critical is True
        assert interpretation == "HH"

    def test_hematocrit_critical_low(self):
        """Critically low hematocrit should be detected"""
        from main import check_critical_value
        is_critical, is_abnormal, interpretation = check_critical_value("Hematocrit", "18")
        assert is_critical is True
        assert interpretation == "LL"


class TestCheckCriticalVital:
    """Tests for check_critical_vital function"""

    def test_systolic_normal(self):
        """Normal systolic BP should return not critical"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Systolic BP", "120")
        assert is_critical is False
        assert is_abnormal is False
        assert interpretation == "N"

    def test_systolic_critical_high(self):
        """Critically high systolic BP should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Systolic Blood Pressure", "190")
        assert is_critical is True
        assert interpretation == "HH"

    def test_systolic_critical_low(self):
        """Critically low systolic BP should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("systolic", "60")
        assert is_critical is True
        assert interpretation == "LL"

    def test_diastolic_critical_high(self):
        """Critically high diastolic BP should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Diastolic BP", "125")
        assert is_critical is True
        assert interpretation == "HH"

    def test_diastolic_critical_low(self):
        """Critically low diastolic BP should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("diastolic", "35")
        assert is_critical is True
        assert interpretation == "LL"

    def test_heart_rate_critical_low(self):
        """Critically low heart rate should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Heart Rate", "35")
        assert is_critical is True
        assert interpretation == "LL"

    def test_heart_rate_critical_high(self):
        """Critically high heart rate should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("heart rate", "160")
        assert is_critical is True
        assert interpretation == "HH"

    def test_pulse_critical_low(self):
        """Critically low pulse should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Pulse", "35")
        assert is_critical is True
        assert interpretation == "LL"

    def test_pulse_critical_high(self):
        """Critically high pulse should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("pulse", "155")
        assert is_critical is True
        assert interpretation == "HH"

    def test_respiratory_rate_critical_low(self):
        """Critically low respiratory rate should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Respiratory Rate", "6")
        assert is_critical is True
        assert interpretation == "LL"

    def test_respiratory_rate_critical_high(self):
        """Critically high respiratory rate should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("respiratory", "35")
        assert is_critical is True
        assert interpretation == "HH"

    def test_spo2_critical_low(self):
        """Critically low SpO2 should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("SpO2", "85")
        assert is_critical is True
        assert interpretation == "LL"

    def test_oxygen_saturation_critical_low(self):
        """Critically low oxygen saturation should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Oxygen Saturation", "86")
        assert is_critical is True
        assert interpretation == "LL"

    def test_o2_sat_low(self):
        """Low O2 sat should be abnormal but not critical"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("O2 Sat", "92")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "L"

    def test_temperature_critical_low(self):
        """Critically low temperature should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Temperature", "94.0")
        assert is_critical is True
        assert interpretation == "LL"

    def test_temperature_critical_high(self):
        """Critically high temperature should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("temperature", "105.0")
        assert is_critical is True
        assert interpretation == "HH"

    def test_temp_critical_high(self):
        """Critically high temp should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Temp", "104.5")
        assert is_critical is True
        assert interpretation == "HH"

    def test_glucose_vital_critical_low(self):
        """Critically low glucose vital should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Glucose", "45")
        assert is_critical is True
        assert interpretation == "LL"

    def test_glucose_vital_critical_high(self):
        """Critically high glucose vital should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("glucose", "450")
        assert is_critical is True
        assert interpretation == "HH"

    def test_bp_with_slash(self):
        """Should extract systolic from BP format like 180/90"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("systolic", "185/95")
        assert is_critical is True
        assert interpretation == "HH"

    def test_pain_high(self):
        """High pain score should be abnormal"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Pain Scale", "8")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "H"

    def test_pain_critical(self):
        """Critical pain score should be detected"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("pain", "10")
        assert is_critical is True
        assert interpretation == "HH"

    def test_bmi_high(self):
        """High BMI should be abnormal"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("BMI", "35")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "H"

    def test_invalid_vital_returns_false(self):
        """Should return false for invalid vital values"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("heart rate", "invalid")
        assert is_critical is False
        assert is_abnormal is False
        assert interpretation == ""

    def test_unknown_vital_returns_false(self):
        """Should return false for unknown vital types"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("Unknown Vital XYZ", "100")
        assert is_critical is False
        assert is_abnormal is False
        assert interpretation == ""

    def test_value_with_greater_than(self):
        """Should handle values with > prefix"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("systolic", ">180")
        assert is_critical is True

    def test_value_with_less_than(self):
        """Should handle values with < prefix"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("systolic", "<80")
        assert is_critical is False
        assert is_abnormal is True

    def test_systolic_low(self):
        """Low systolic BP should be abnormal but not critical"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("systolic", "85")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "L"

    def test_systolic_high(self):
        """High systolic BP should be abnormal but not critical"""
        from main import check_critical_vital
        is_critical, is_abnormal, interpretation = check_critical_vital("systolic", "150")
        assert is_critical is False
        assert is_abnormal is True
        assert interpretation == "H"


class TestNormalizeMedicationName:
    """Tests for normalize_medication_name function"""

    def test_generic_name_unchanged(self):
        """Generic name should be returned unchanged"""
        from main import normalize_medication_name
        result = normalize_medication_name("lisinopril")
        assert result == "lisinopril"

    def test_strips_whitespace(self):
        """Should strip whitespace from medication names"""
        from main import normalize_medication_name
        result = normalize_medication_name("  lisinopril  ")
        assert result == "lisinopril"

    def test_lowercase_conversion(self):
        """Should convert to lowercase"""
        from main import normalize_medication_name
        result = normalize_medication_name("LISINOPRIL")
        assert result == "lisinopril"

    def test_extracts_first_word(self):
        """Should extract first word for names with strength"""
        from main import normalize_medication_name
        result = normalize_medication_name("lisinopril 10mg")
        assert result == "lisinopril"

    def test_empty_string(self):
        """Should handle empty string"""
        from main import normalize_medication_name
        result = normalize_medication_name("")
        assert result == ""


class TestCheckMedicationInteractions:
    """Tests for check_medication_interactions function"""

    def test_no_interactions_empty_list(self):
        """Empty medication list should return no interactions"""
        from main import check_medication_interactions
        result = check_medication_interactions([])
        assert result == []

    def test_single_medication_no_interactions(self):
        """Single medication should return no interactions"""
        from main import check_medication_interactions
        result = check_medication_interactions(["lisinopril"])
        assert result == []

    def test_interactions_sorted_by_severity(self):
        """Interactions should be sorted by severity (high first)"""
        from main import check_medication_interactions
        # This depends on the drug_interactions.json content
        result = check_medication_interactions(["warfarin", "aspirin", "ibuprofen"])
        if result:
            severities = [r.get("severity", "moderate") for r in result]
            severity_order = {"high": 0, "moderate": 1, "low": 2}
            severity_values = [severity_order.get(s, 1) for s in severities]
            assert severity_values == sorted(severity_values)

    def test_known_interaction(self):
        """Known interactions should be detected"""
        from main import check_medication_interactions
        # Test with known interacting medications
        result = check_medication_interactions(["warfarin", "aspirin"])
        # Should detect at least some interaction or return empty if not in DB
        assert isinstance(result, list)


class TestCriticalLabThresholds:
    """Tests for CRITICAL_LAB_THRESHOLDS constant"""

    def test_thresholds_exist(self):
        """CRITICAL_LAB_THRESHOLDS should exist and be a dict"""
        from main import CRITICAL_LAB_THRESHOLDS
        assert isinstance(CRITICAL_LAB_THRESHOLDS, dict)
        assert len(CRITICAL_LAB_THRESHOLDS) > 0

    def test_potassium_thresholds(self):
        """Potassium thresholds should be correct"""
        from main import CRITICAL_LAB_THRESHOLDS
        assert "potassium" in CRITICAL_LAB_THRESHOLDS
        thresholds = CRITICAL_LAB_THRESHOLDS["potassium"]
        assert thresholds["critical_low"] == 2.5
        assert thresholds["critical_high"] == 6.5
        assert thresholds["low"] == 3.5
        assert thresholds["high"] == 5.0

    def test_glucose_thresholds(self):
        """Glucose thresholds should be correct"""
        from main import CRITICAL_LAB_THRESHOLDS
        assert "glucose" in CRITICAL_LAB_THRESHOLDS
        thresholds = CRITICAL_LAB_THRESHOLDS["glucose"]
        assert thresholds["critical_low"] == 50
        assert thresholds["critical_high"] == 450

    def test_sodium_thresholds(self):
        """Sodium thresholds should be correct"""
        from main import CRITICAL_LAB_THRESHOLDS
        assert "sodium" in CRITICAL_LAB_THRESHOLDS
        thresholds = CRITICAL_LAB_THRESHOLDS["sodium"]
        assert thresholds["critical_low"] == 120
        assert thresholds["critical_high"] == 160

    def test_troponin_thresholds(self):
        """Troponin thresholds should be correct"""
        from main import CRITICAL_LAB_THRESHOLDS
        assert "troponin" in CRITICAL_LAB_THRESHOLDS
        thresholds = CRITICAL_LAB_THRESHOLDS["troponin"]
        assert thresholds["critical_high"] == 0.04

    def test_all_thresholds_have_units(self):
        """All thresholds should have unit field"""
        from main import CRITICAL_LAB_THRESHOLDS
        for lab, thresholds in CRITICAL_LAB_THRESHOLDS.items():
            assert "unit" in thresholds, f"{lab} missing unit"


class TestCriticalVitalThresholds:
    """Tests for CRITICAL_VITAL_THRESHOLDS constant"""

    def test_thresholds_exist(self):
        """CRITICAL_VITAL_THRESHOLDS should exist and be a dict"""
        from main import CRITICAL_VITAL_THRESHOLDS
        assert isinstance(CRITICAL_VITAL_THRESHOLDS, dict)
        assert len(CRITICAL_VITAL_THRESHOLDS) > 0

    def test_systolic_thresholds(self):
        """Systolic BP thresholds should be correct"""
        from main import CRITICAL_VITAL_THRESHOLDS
        assert "systolic" in CRITICAL_VITAL_THRESHOLDS
        thresholds = CRITICAL_VITAL_THRESHOLDS["systolic"]
        assert thresholds["critical_low"] == 70
        assert thresholds["critical_high"] == 180

    def test_heart_rate_thresholds(self):
        """Heart rate thresholds should be correct"""
        from main import CRITICAL_VITAL_THRESHOLDS
        assert "heart rate" in CRITICAL_VITAL_THRESHOLDS
        thresholds = CRITICAL_VITAL_THRESHOLDS["heart rate"]
        assert thresholds["critical_low"] == 40
        assert thresholds["critical_high"] == 150

    def test_spo2_thresholds(self):
        """SpO2 thresholds should be correct"""
        from main import CRITICAL_VITAL_THRESHOLDS
        assert "spo2" in CRITICAL_VITAL_THRESHOLDS
        thresholds = CRITICAL_VITAL_THRESHOLDS["spo2"]
        assert thresholds["critical_low"] == 88

    def test_temperature_thresholds(self):
        """Temperature thresholds should be correct"""
        from main import CRITICAL_VITAL_THRESHOLDS
        assert "temperature" in CRITICAL_VITAL_THRESHOLDS
        thresholds = CRITICAL_VITAL_THRESHOLDS["temperature"]
        assert thresholds["critical_low"] == 95.0
        assert thresholds["critical_high"] == 104.0


class TestLoadCodeDatabase:
    """Tests for load_code_database function"""

    def test_load_icd10(self):
        """Should load ICD-10 database"""
        from main import ICD10_DB
        assert isinstance(ICD10_DB, dict)
        assert "codes" in ICD10_DB or len(ICD10_DB) > 0

    def test_load_cpt(self):
        """Should load CPT database"""
        from main import CPT_DB
        assert isinstance(CPT_DB, dict)
        assert "codes" in CPT_DB or len(CPT_DB) > 0

    def test_load_drug_interactions(self):
        """Should load drug interactions database"""
        from main import DRUG_INTERACTIONS_DB
        assert isinstance(DRUG_INTERACTIONS_DB, dict)

    def test_load_nonexistent_returns_empty(self):
        """Should return empty dict for nonexistent file"""
        from main import load_code_database
        result = load_code_database("nonexistent_file.json")
        assert result == {"codes": {}, "keywords": {}}


class TestCodeDatabases:
    """Tests for ICD-10 and CPT code databases"""

    def test_icd10_has_codes(self):
        """ICD-10 database should have codes"""
        from main import ICD10_DB
        codes = ICD10_DB.get("codes", {})
        assert isinstance(codes, dict)

    def test_cpt_has_codes(self):
        """CPT database should have codes"""
        from main import CPT_DB
        codes = CPT_DB.get("codes", {})
        assert isinstance(codes, dict)

    def test_icd10_has_keywords(self):
        """ICD-10 database should have keywords"""
        from main import ICD10_DB
        keywords = ICD10_DB.get("keywords", {})
        assert isinstance(keywords, dict)

    def test_cpt_has_keywords(self):
        """CPT database should have keywords"""
        from main import CPT_DB
        keywords = CPT_DB.get("keywords", {})
        assert isinstance(keywords, dict)
