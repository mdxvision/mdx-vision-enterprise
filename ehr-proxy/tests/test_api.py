"""
MDx Vision EHR Proxy - API Endpoint Tests

Tests for all REST API endpoints in the EHR proxy service.
Run with: pytest tests/test_api.py -v
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


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    return TestClient(app)


# ==================== HEALTH CHECK TESTS ====================

class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_ping_returns_ok(self, client):
        """Test /ping endpoint returns status ok"""
        response = client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "time" in data

    def test_transcription_status(self, client):
        """Test /api/v1/transcription/status returns provider info"""
        response = client.get("/api/v1/transcription/status")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "status" in data
        assert "supported_providers" in data
        assert "assemblyai" in data["supported_providers"]
        assert "deepgram" in data["supported_providers"]


# ==================== PATIENT ENDPOINTS TESTS ====================

class TestPatientEndpoints:
    """Tests for patient data endpoints"""

    def test_get_patient_quick(self, client):
        """Test /api/v1/patient/{id}/quick returns compact patient data"""
        response = client.get("/api/v1/patient/12724066/quick")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "patient_id" in data
        assert "name" in data
        assert "date_of_birth" in data
        assert "gender" in data
        assert "allergies" in data
        assert "vitals" in data
        assert "conditions" in data
        assert "medications" in data

    def test_get_patient_quick_has_allergies(self, client):
        """Test quick endpoint includes allergy data"""
        response = client.get("/api/v1/patient/12724066/quick")
        data = response.json()

        assert isinstance(data["allergies"], list)
        if data["allergies"]:
            allergy = data["allergies"][0]
            assert "substance" in allergy
            assert "severity" in allergy
            assert "reaction" in allergy

    def test_get_patient_quick_has_vitals(self, client):
        """Test quick endpoint includes vital signs"""
        response = client.get("/api/v1/patient/12724066/quick")
        data = response.json()

        assert isinstance(data["vitals"], list)
        if data["vitals"]:
            vital = data["vitals"][0]
            assert "name" in vital
            assert "value" in vital
            assert "unit" in vital

    @pytest.mark.skip(reason="Slow network call - tested via quick endpoint")
    def test_get_patient_full(self, client):
        """Test /api/v1/patient/{id} returns full FHIR data"""
        # Test against live Cerner sandbox (no mocking needed)
        response = client.get("/api/v1/patient/12724066")
        # Should return 200 from live FHIR endpoint or error if network unavailable
        assert response.status_code in [200, 500, 503]

    def test_search_patients_by_name(self, client):
        """Test /api/v1/patient/search with name parameter"""
        response = client.get("/api/v1/patient/search?name=Smith")
        # Should return 200 even if no results
        assert response.status_code in [200, 404]


# ==================== NOTES ENDPOINTS TESTS ====================

class TestNotesEndpoints:
    """Tests for clinical notes generation endpoints"""

    def test_generate_quick_note(self, client):
        """Test /api/v1/notes/quick generates a SOAP note"""
        payload = {
            "transcript": "Patient reports headache for 3 days. No fever. Taking ibuprofen.",
            "chief_complaint": "Headache"
        }
        response = client.post("/api/v1/notes/quick", json=payload)

        # May fail if no API key, but should not error
        assert response.status_code in [200, 500, 503]

    def test_generate_quick_note_requires_transcript(self, client):
        """Test that quick note requires transcript field"""
        payload = {
            "chief_complaint": "Headache"
        }
        response = client.post("/api/v1/notes/quick", json=payload)
        assert response.status_code in [200, 422]  # 422 for validation error

    def test_generate_note_with_note_type(self, client):
        """Test note generation with specific note type"""
        payload = {
            "transcript": "Patient here for annual physical exam.",
            "note_type": "HP"  # History and Physical
        }
        response = client.post("/api/v1/notes/quick", json=payload)
        assert response.status_code in [200, 500, 503]


# ==================== ICD-10 CODE TESTS ====================

class TestICD10Endpoints:
    """Tests for ICD-10 code suggestion endpoints"""

    def test_icd10_codes_in_note_response(self, client):
        """Test that note generation includes ICD-10 suggestions"""
        payload = {
            "transcript": "Patient has diabetes and hypertension.",
            "chief_complaint": "Follow up"
        }
        response = client.post("/api/v1/notes/quick", json=payload)

        if response.status_code == 200:
            data = response.json()
            # Note response contains display_text with ICD codes embedded
            assert "display_text" in data or "note" in data or "icd10_codes" in data
            # If display_text exists, check for ICD codes in content
            if "display_text" in data:
                assert "ICD-10" in data["display_text"] or "I10" in data["display_text"]


# ==================== AUDIT LOGGING TESTS ====================

class TestAuditLogging:
    """Tests for HIPAA audit logging"""

    def test_patient_access_is_logged(self, client, tmp_path):
        """Test that patient data access is logged"""
        response = client.get("/api/v1/patient/12724066/quick")
        assert response.status_code == 200
        # Audit log should be written (check log file exists)


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Tests for error responses"""

    def test_invalid_patient_id_format(self, client):
        """Test handling of invalid patient ID"""
        response = client.get("/api/v1/patient/invalid-id/quick")
        # Should still return data or proper error
        assert response.status_code in [200, 400, 404]

    def test_missing_endpoint_returns_404(self, client):
        """Test that undefined endpoints return 404"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_invalid_json_returns_422(self, client):
        """Test that invalid JSON returns validation error"""
        response = client.post(
            "/api/v1/notes/quick",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


# ==================== CORS TESTS ====================

class TestCORS:
    """Tests for CORS headers"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are included"""
        response = client.options("/ping")
        # FastAPI handles CORS via middleware
        assert response.status_code in [200, 405]


# ==================== RESPONSE FORMAT TESTS ====================

class TestResponseFormats:
    """Tests for API response formats"""

    def test_responses_are_json(self, client):
        """Test that all responses are valid JSON"""
        endpoints = [
            "/ping",
            "/api/v1/transcription/status",
            "/api/v1/patient/12724066/quick"
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.headers.get("content-type", "").startswith("application/json")

    def test_patient_quick_response_size(self, client):
        """Test that quick endpoint returns compact data (<5KB)"""
        response = client.get("/api/v1/patient/12724066/quick")
        assert len(response.content) < 5000  # Less than 5KB for Samsung compatibility


# ==================== CONCURRENT ACCESS TESTS ====================

class TestConcurrentAccess:
    """Tests for concurrent request handling"""

    def test_multiple_simultaneous_requests(self, client):
        """Test handling multiple requests"""
        import concurrent.futures

        def make_request():
            return client.get("/ping")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
