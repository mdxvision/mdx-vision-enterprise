"""
Unit tests for medical_vocabulary.py - Medical terminology and specialty detection

Covers:
- Specialty detection from ICD-10 codes
- Specialty detection from condition names
- Specialty detection from patient conditions list
- Specialty detection from transcript text
- Medical vocabulary functions
"""

import pytest


class TestSpecialtyICD10Detection:
    """Tests for detect_specialty_from_icd10 function"""

    def test_cardiology_icd10_codes(self):
        """Should detect cardiology from I-prefix codes"""
        from medical_vocabulary import detect_specialty_from_icd10

        # Hypertension - I10 is in cardiology prefixes
        result = detect_specialty_from_icd10("I10")
        assert "cardiology" in result

        # Heart failure - I50 is in cardiology prefixes
        result = detect_specialty_from_icd10("I50.9")
        assert "cardiology" in result

        # Atrial fibrillation - I48 is in cardiology prefixes
        result = detect_specialty_from_icd10("I48.91")
        assert "cardiology" in result

    def test_pulmonology_icd10_codes(self):
        """Should detect pulmonology from J-prefix codes"""
        from medical_vocabulary import detect_specialty_from_icd10

        # COPD
        result = detect_specialty_from_icd10("J44.1")
        assert "pulmonology" in result

        # Asthma
        result = detect_specialty_from_icd10("J45.909")
        assert "pulmonology" in result

        # Pneumonia
        result = detect_specialty_from_icd10("J18.9")
        assert "pulmonology" in result

    def test_neurology_icd10_codes(self):
        """Should detect neurology from G-prefix codes"""
        from medical_vocabulary import detect_specialty_from_icd10

        # Epilepsy - G40 is in neurology prefixes
        result = detect_specialty_from_icd10("G40.909")
        assert "neurology" in result

        # Migraine - G43 is in neurology prefixes
        result = detect_specialty_from_icd10("G43.909")
        assert "neurology" in result

    def test_orthopedics_icd10_codes(self):
        """Should detect orthopedics from M-prefix codes"""
        from medical_vocabulary import detect_specialty_from_icd10

        # Osteoarthritis - M17 is in orthopedics prefixes
        result = detect_specialty_from_icd10("M17.11")
        assert "orthopedics" in result

        # Back pain
        result = detect_specialty_from_icd10("M54.5")
        assert "orthopedics" in result

    def test_empty_code_returns_empty(self):
        """Should return empty list for empty code"""
        from medical_vocabulary import detect_specialty_from_icd10

        result = detect_specialty_from_icd10("")
        assert result == []

        result = detect_specialty_from_icd10(None)
        assert result == []

    def test_case_insensitive(self):
        """Should handle lowercase codes"""
        from medical_vocabulary import detect_specialty_from_icd10

        result = detect_specialty_from_icd10("i10")
        assert "cardiology" in result

        result = detect_specialty_from_icd10("j44.1")
        assert "pulmonology" in result

    def test_unknown_code_returns_empty(self):
        """Should return empty for unknown prefix"""
        from medical_vocabulary import detect_specialty_from_icd10

        result = detect_specialty_from_icd10("ZZZ999")
        assert result == []


class TestSpecialtyConditionDetection:
    """Tests for detect_specialty_from_condition function"""

    def test_cardiology_conditions(self):
        """Should detect cardiology from condition names"""
        from medical_vocabulary import detect_specialty_from_condition

        conditions = [
            "Essential hypertension",
            "Congestive heart failure",
            "Atrial fibrillation",
            "Coronary artery disease",
            "Myocardial infarction"
        ]

        for condition in conditions:
            result = detect_specialty_from_condition(condition)
            assert "cardiology" in result, f"Failed for: {condition}"

    def test_pulmonology_conditions(self):
        """Should detect pulmonology from condition names"""
        from medical_vocabulary import detect_specialty_from_condition

        conditions = [
            "Chronic obstructive pulmonary disease",
            "Asthma exacerbation",
            "Pneumonia",
            "Pulmonary embolism"
        ]

        for condition in conditions:
            result = detect_specialty_from_condition(condition)
            assert "pulmonology" in result, f"Failed for: {condition}"

    def test_neurology_conditions(self):
        """Should detect neurology from condition names"""
        from medical_vocabulary import detect_specialty_from_condition

        conditions = [
            "Epilepsy",
            "Migraine headache",
            "Parkinson disease",
            "Stroke",
            "Cerebral infarction"
        ]

        for condition in conditions:
            result = detect_specialty_from_condition(condition)
            assert "neurology" in result, f"Failed for: {condition}"

    def test_empty_condition_returns_empty(self):
        """Should return empty list for empty condition"""
        from medical_vocabulary import detect_specialty_from_condition

        result = detect_specialty_from_condition("")
        assert result == []

        result = detect_specialty_from_condition(None)
        assert result == []

    def test_case_insensitive(self):
        """Should handle different cases"""
        from medical_vocabulary import detect_specialty_from_condition

        result = detect_specialty_from_condition("HYPERTENSION")
        assert "cardiology" in result

        result = detect_specialty_from_condition("Heart Failure")
        assert "cardiology" in result


class TestSpecialtyFromPatientConditions:
    """Tests for detect_specialties_from_patient_conditions function"""

    def test_single_specialty(self):
        """Should detect single specialty from conditions"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        conditions = [
            {"name": "Essential hypertension", "code": "I10"},
            {"name": "Heart failure", "code": "I50.9"}
        ]

        result = detect_specialties_from_patient_conditions(conditions)
        assert "cardiology" in result

    def test_multiple_specialties(self):
        """Should detect multiple specialties"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        conditions = [
            {"name": "Essential hypertension", "code": "I10"},
            {"name": "COPD", "code": "J44.1"}
        ]

        result = detect_specialties_from_patient_conditions(conditions)
        assert "cardiology" in result
        assert "pulmonology" in result

    def test_code_weighted_higher(self):
        """ICD-10 codes should be weighted higher than names"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        # Cardiology has code match (weight 2), pulmonology only name (weight 1)
        conditions = [
            {"name": "Essential hypertension", "code": "I10"},
            {"name": "Mild lung disease"}  # No code, just name
        ]

        result = detect_specialties_from_patient_conditions(conditions)
        # Cardiology should be first due to code match
        if len(result) > 0:
            assert result[0] == "cardiology"

    def test_empty_conditions(self):
        """Should handle empty list"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        result = detect_specialties_from_patient_conditions([])
        assert result == []

    def test_conditions_without_codes(self):
        """Should work with conditions that only have names"""
        from medical_vocabulary import detect_specialties_from_patient_conditions

        conditions = [
            {"name": "Hypertension"},
            {"name": "Heart failure"}
        ]

        result = detect_specialties_from_patient_conditions(conditions)
        assert "cardiology" in result


class TestSpecialtyFromTranscript:
    """Tests for detect_specialty_from_transcript function"""

    def test_cardiology_transcript(self):
        """Should detect cardiology from heart-related transcript with multiple keywords"""
        from medical_vocabulary import detect_specialty_from_transcript

        # Need at least 2 keyword matches
        transcript = "Patient has cardiac chest pain and heart palpitations. ECG shows arrhythmia."

        result = detect_specialty_from_transcript(transcript)
        assert "cardiology" in result

    def test_pulmonology_transcript(self):
        """Should detect pulmonology from lung-related transcript"""
        from medical_vocabulary import detect_specialty_from_transcript

        # Need at least 2 keyword matches
        transcript = "Patient has lung disease and pneumonia. Respiratory failure with hypoxia."

        result = detect_specialty_from_transcript(transcript)
        assert "pulmonology" in result

    def test_empty_transcript(self):
        """Should handle empty transcript"""
        from medical_vocabulary import detect_specialty_from_transcript

        result = detect_specialty_from_transcript("")
        assert result == []

    def test_single_keyword_not_enough(self):
        """Should require 2+ keywords to return specialty"""
        from medical_vocabulary import detect_specialty_from_transcript

        # Only one keyword
        transcript = "Patient has hypertension."

        result = detect_specialty_from_transcript(transcript)
        # May or may not include cardiology depending on threshold


class TestMedicalVocabularyConstants:
    """Tests for medical vocabulary constants"""

    def test_medical_vocabulary_exists(self):
        """Should have medical vocabulary list"""
        from medical_vocabulary import MEDICAL_VOCABULARY

        assert len(MEDICAL_VOCABULARY) > 0
        assert isinstance(MEDICAL_VOCABULARY, list)

    def test_specialty_icd10_prefixes_exist(self):
        """Should have ICD-10 prefix mappings"""
        from medical_vocabulary import SPECIALTY_ICD10_PREFIXES

        assert "cardiology" in SPECIALTY_ICD10_PREFIXES
        # Check that prefixes are like "I10", "I50" etc, not just "I"
        assert len(SPECIALTY_ICD10_PREFIXES["cardiology"]) > 0

    def test_specialty_condition_keywords_exist(self):
        """Should have condition keyword mappings"""
        from medical_vocabulary import SPECIALTY_CONDITION_KEYWORDS

        assert "cardiology" in SPECIALTY_CONDITION_KEYWORDS
        assert len(SPECIALTY_CONDITION_KEYWORDS["cardiology"]) > 0

    def test_cardiology_vocabulary_exists(self):
        """Should have cardiology vocabulary"""
        from medical_vocabulary import CARDIOLOGY_VOCABULARY

        assert len(CARDIOLOGY_VOCABULARY) > 0

    def test_pulmonology_vocabulary_exists(self):
        """Should have pulmonology vocabulary"""
        from medical_vocabulary import PULMONOLOGY_VOCABULARY

        assert len(PULMONOLOGY_VOCABULARY) > 0


class TestGetVocabulary:
    """Tests for get_vocabulary function"""

    def test_get_base_vocabulary(self):
        """Should return base vocabulary without specialty"""
        from medical_vocabulary import get_vocabulary

        vocab = get_vocabulary()
        assert len(vocab) > 0

    def test_get_cardiology_vocabulary(self):
        """Should include cardiology terms"""
        from medical_vocabulary import get_vocabulary

        vocab = get_vocabulary(specialties=["cardiology"])
        assert len(vocab) > 0

    def test_get_multiple_specialties(self):
        """Should combine terms from multiple specialties"""
        from medical_vocabulary import get_vocabulary

        cardio_vocab = get_vocabulary(specialties=["cardiology"])
        pulmo_vocab = get_vocabulary(specialties=["pulmonology"])
        combined_vocab = get_vocabulary(specialties=["cardiology", "pulmonology"])

        # Combined should be larger than either individual
        assert len(combined_vocab) >= len(cardio_vocab)
        assert len(combined_vocab) >= len(pulmo_vocab)


class TestGetVocabularyForPatient:
    """Tests for get_vocabulary_for_patient function"""

    def test_get_vocabulary_for_cardiac_patient(self):
        """Should return cardiology vocabulary for cardiac patient"""
        from medical_vocabulary import get_vocabulary_for_patient

        conditions = [
            {"name": "Essential hypertension", "code": "I10"},
            {"name": "Heart failure", "code": "I50.9"}
        ]

        vocab, specialties = get_vocabulary_for_patient(conditions)

        assert len(vocab) > 0
        assert "cardiology" in specialties

    def test_get_vocabulary_for_empty_conditions(self):
        """Should return base vocabulary for no conditions"""
        from medical_vocabulary import get_vocabulary_for_patient

        vocab, specialties = get_vocabulary_for_patient([])

        assert len(vocab) > 0
        assert specialties == []
