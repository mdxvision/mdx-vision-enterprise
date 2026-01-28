"""
Tests for Differential Diagnosis (DDx) API endpoint.

Tests the AI-powered differential diagnosis feature that generates ranked
diagnoses with ICD-10 codes from clinical findings.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


class TestDdxEndpointValidation:
    """Test input validation for DDx endpoint"""

    def test_ddx_requires_chief_complaint(self):
        """Chief complaint is required"""
        response = client.post("/api/v1/ddx/generate", json={
            "symptoms": ["cough", "fever"]
        })
        assert response.status_code == 422  # Validation error

    def test_ddx_empty_chief_complaint_rejected(self):
        """Empty chief complaint is rejected"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "",
            "symptoms": ["cough"]
        })
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_ddx_whitespace_chief_complaint_rejected(self):
        """Whitespace-only chief complaint is rejected"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "   ",
            "symptoms": []
        })
        assert response.status_code == 400

    def test_ddx_accepts_minimal_request(self):
        """Accepts request with just chief complaint"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "headache"
        })
        assert response.status_code == 200
        data = response.json()
        assert "differentials" in data
        assert "clinical_reasoning" in data
        assert "timestamp" in data


class TestDdxRuleBasedFallback:
    """Test rule-based DDx when Claude is unavailable"""

    @patch('main.CLAUDE_API_KEY', None)
    def test_ddx_respiratory_symptoms(self):
        """Test DDx for respiratory symptoms"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "cough and fever",
            "symptoms": ["cough", "fever", "productive sputum"]
        })
        assert response.status_code == 200
        data = response.json()
        diagnoses = [d["diagnosis"] for d in data["differentials"]]
        # Should include common respiratory diagnoses
        assert any("bronchitis" in d.lower() or "pneumonia" in d.lower() for d in diagnoses)

    @patch('main.CLAUDE_API_KEY', None)
    def test_ddx_cardiac_symptoms(self):
        """Test DDx for cardiac symptoms"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "chest pain",
            "symptoms": ["chest pain", "shortness of breath"]
        })
        assert response.status_code == 200
        data = response.json()
        diagnoses = [d["diagnosis"] for d in data["differentials"]]
        # Should include cardiac considerations
        assert any("coronary" in d.lower() or "chest pain" in d.lower() for d in diagnoses)

    @patch('main.CLAUDE_API_KEY', None)
    def test_ddx_gi_symptoms(self):
        """Test DDx for GI symptoms"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "abdominal pain",
            "symptoms": ["abdominal pain", "nausea", "vomiting"]
        })
        assert response.status_code == 200
        data = response.json()
        diagnoses = [d["diagnosis"] for d in data["differentials"]]
        assert any("gastro" in d.lower() or "abdom" in d.lower() for d in diagnoses)

    @patch('main.CLAUDE_API_KEY', None)
    def test_ddx_neuro_symptoms(self):
        """Test DDx for neurological symptoms"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "headache",
            "symptoms": ["headache", "dizziness"]
        })
        assert response.status_code == 200
        data = response.json()
        diagnoses = [d["diagnosis"] for d in data["differentials"]]
        assert any("headache" in d.lower() or "migraine" in d.lower() for d in diagnoses)


class TestDdxResponseFormat:
    """Test DDx response format and structure"""

    def test_ddx_response_has_differentials(self):
        """Response includes differentials array"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "fever"
        })
        assert response.status_code == 200
        data = response.json()
        assert "differentials" in data
        assert isinstance(data["differentials"], list)

    def test_ddx_differential_structure(self):
        """Each differential has required fields"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "cough",
            "symptoms": ["cough", "fever"]
        })
        assert response.status_code == 200
        data = response.json()

        for diff in data["differentials"]:
            assert "rank" in diff
            assert "diagnosis" in diff
            assert "icd10_code" in diff
            assert "likelihood" in diff
            assert "supporting_findings" in diff
            assert isinstance(diff["supporting_findings"], list)

    def test_ddx_icd10_codes_valid_format(self):
        """ICD-10 codes are in valid format"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "back pain",
            "symptoms": ["back pain"]
        })
        assert response.status_code == 200
        data = response.json()

        for diff in data["differentials"]:
            code = diff["icd10_code"]
            # ICD-10 codes start with letter, followed by digits and optionally period
            assert len(code) >= 3
            assert code[0].isalpha()

    def test_ddx_likelihood_levels_valid(self):
        """Likelihood levels are high, moderate, or low"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "fatigue",
            "symptoms": ["fatigue", "weakness"]
        })
        assert response.status_code == 200
        data = response.json()

        valid_levels = ["high", "moderate", "low"]
        for diff in data["differentials"]:
            assert diff["likelihood"].lower() in valid_levels

    def test_ddx_ranks_are_sequential(self):
        """Ranks are sequential from 1"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "cough and fever",
            "symptoms": ["cough", "fever"]
        })
        assert response.status_code == 200
        data = response.json()

        if data["differentials"]:
            ranks = [d["rank"] for d in data["differentials"]]
            for i, rank in enumerate(sorted(ranks), 1):
                assert rank == i

    def test_ddx_has_timestamp(self):
        """Response includes timestamp"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "headache"
        })
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"]  # Not empty


class TestDdxWithPatientContext:
    """Test DDx with full patient context"""

    def test_ddx_with_vitals(self):
        """DDx accepts vitals data"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "shortness of breath",
            "symptoms": ["dyspnea", "cough"],
            "vitals": {
                "blood_pressure": "180/100",
                "heart_rate": "110",
                "spo2": "88%"
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["differentials"]) > 0

    def test_ddx_with_age_and_gender(self):
        """DDx accepts demographics"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "chest pain",
            "symptoms": ["chest pain"],
            "age": 65,
            "gender": "male"
        })
        assert response.status_code == 200

    def test_ddx_with_medical_history(self):
        """DDx accepts medical history"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "shortness of breath",
            "symptoms": ["dyspnea"],
            "medical_history": ["COPD", "hypertension", "diabetes"]
        })
        assert response.status_code == 200

    def test_ddx_with_medications(self):
        """DDx accepts current medications"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "fatigue",
            "symptoms": ["fatigue", "weakness"],
            "medications": ["metformin", "lisinopril", "atorvastatin"]
        })
        assert response.status_code == 200

    def test_ddx_with_allergies(self):
        """DDx accepts allergies"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "rash",
            "symptoms": ["rash", "itching"],
            "allergies": ["penicillin", "sulfa"]
        })
        assert response.status_code == 200

    def test_ddx_with_full_patient_context(self):
        """DDx with complete patient context"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "chest pain and shortness of breath",
            "symptoms": ["chest pain", "dyspnea", "diaphoresis"],
            "vitals": {
                "blood_pressure": "160/95",
                "heart_rate": "105",
                "respiratory_rate": "22",
                "spo2": "92%"
            },
            "age": 58,
            "gender": "male",
            "medical_history": ["hypertension", "hyperlipidemia", "smoking"],
            "medications": ["lisinopril", "aspirin"],
            "allergies": []
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["differentials"]) > 0


class TestDdxUrgentConsiderations:
    """Test urgent considerations in DDx"""

    def test_ddx_returns_urgent_considerations(self):
        """Response includes urgent_considerations field"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "chest pain"
        })
        assert response.status_code == 200
        data = response.json()
        assert "urgent_considerations" in data
        assert isinstance(data["urgent_considerations"], list)


class TestDdxClinicalReasoning:
    """Test clinical reasoning in DDx"""

    def test_ddx_returns_clinical_reasoning(self):
        """Response includes clinical_reasoning field"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "fever"
        })
        assert response.status_code == 200
        data = response.json()
        assert "clinical_reasoning" in data
        assert isinstance(data["clinical_reasoning"], str)


class TestDdxAuditLogging:
    """Test HIPAA audit logging for DDx"""

    def test_ddx_audit_logged(self):
        """DDx requests are audit logged"""
        # This test verifies the endpoint doesn't crash with audit logging
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "headache",
            "symptoms": ["headache", "photophobia"]
        })
        assert response.status_code == 200


class TestDdxEdgeCases:
    """Test edge cases for DDx"""

    def test_ddx_with_unknown_symptoms(self):
        """DDx handles unknown symptoms gracefully"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "vague discomfort",
            "symptoms": ["something weird", "general malaise"]
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["differentials"]) > 0

    def test_ddx_with_many_symptoms(self):
        """DDx handles many symptoms"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "multiple complaints",
            "symptoms": ["headache", "fever", "cough", "fatigue", "nausea",
                        "dizziness", "chest pain", "back pain", "joint pain"]
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["differentials"]) <= 5  # Should be top 5

    def test_ddx_long_chief_complaint(self):
        """DDx handles long chief complaint"""
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "Patient presents with a 3-day history of progressive shortness of breath, initially on exertion but now at rest, associated with a productive cough with yellowish sputum and intermittent low-grade fever"
        })
        assert response.status_code == 200


class TestDdxIntegration:
    """Integration tests for DDx feature"""

    def test_ddx_end_to_end_workflow(self):
        """Complete DDx workflow"""
        # 1. Generate DDx
        response = client.post("/api/v1/ddx/generate", json={
            "chief_complaint": "cough and fever for 3 days",
            "symptoms": ["cough", "fever", "productive sputum"],
            "age": 45,
            "gender": "female"
        })
        assert response.status_code == 200
        data = response.json()

        # 2. Verify structure
        assert "differentials" in data
        assert len(data["differentials"]) > 0

        # 3. Verify top diagnosis
        top_diagnosis = data["differentials"][0]
        assert top_diagnosis["rank"] == 1
        assert "icd10_code" in top_diagnosis

        # 4. Verify timestamp
        assert "timestamp" in data

        # 5. Verify clinical reasoning
        assert "clinical_reasoning" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
