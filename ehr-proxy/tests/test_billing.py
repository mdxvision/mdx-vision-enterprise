"""
MDx Vision EHR Proxy - Billing/Coding Submission Tests

Tests for billing claim creation, submission, and FHIR Claim resource generation.
Run with: pytest tests/test_billing.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, billing_claims


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_billing_claims():
    """Clear billing claims before each test"""
    billing_claims.clear()
    yield
    billing_claims.clear()


# ==================== CLAIM CREATION TESTS ====================

class TestClaimCreation:
    """Tests for creating billing claims"""

    def test_create_claim_basic(self, client):
        """Test creating a basic claim"""
        response = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "claim" in data
        claim = data["claim"]
        assert claim["patient_id"] == "12724066"
        assert claim["service_date"] == "2024-01-15"
        assert claim["status"] == "draft"
        assert "claim_id" in claim

    def test_create_claim_with_codes(self, client):
        """Test creating a claim with ICD-10 and CPT codes"""
        response = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [
                {"code": "J06.9", "description": "Acute upper respiratory infection"},
                {"code": "R50.9", "description": "Fever"}
            ],
            "cpt_codes": [
                {"code": "99213", "description": "Office visit, established patient"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        claim = data["claim"]
        assert len(claim["diagnoses"]) == 2
        assert len(claim["service_lines"]) == 1
        assert claim["diagnoses"][0]["code"] == "J06.9"
        assert claim["diagnoses"][0]["is_principal"] is True
        assert claim["service_lines"][0]["procedure"]["code"] == "99213"

    def test_create_claim_from_note(self, client):
        """Test creating a claim associated with a note ID"""
        response = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "note_id": "note_123456",
            "service_date": "2024-01-15"
        })
        assert response.status_code == 200
        data = response.json()

        assert data["claim"]["note_id"] == "note_123456"

    def test_create_claim_requires_patient_id(self, client):
        """Test that patient_id is required"""
        response = client.post("/api/v1/billing/claims", json={
            "service_date": "2024-01-15"
        })
        assert response.status_code == 422  # Validation error

    def test_create_claim_requires_service_date(self, client):
        """Test that service_date is required"""
        response = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066"
        })
        assert response.status_code == 422  # Validation error


# ==================== CLAIM RETRIEVAL TESTS ====================

class TestClaimRetrieval:
    """Tests for retrieving billing claims"""

    def test_get_claim_by_id(self, client):
        """Test retrieving a claim by ID"""
        # First create a claim
        create_response = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        claim_id = create_response.json()["claim"]["claim_id"]

        # Then retrieve it
        response = client.get(f"/api/v1/billing/claims/{claim_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["claim"]["claim_id"] == claim_id
        assert data["claim"]["patient_id"] == "12724066"

    def test_get_claim_not_found(self, client):
        """Test 404 for non-existent claim"""
        response = client.get("/api/v1/billing/claims/nonexistent123")
        assert response.status_code == 404

    def test_list_all_claims(self, client):
        """Test listing all claims"""
        # Create multiple claims
        client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        client.post("/api/v1/billing/claims", json={
            "patient_id": "12724067",
            "service_date": "2024-01-16"
        })

        response = client.get("/api/v1/billing/claims")
        assert response.status_code == 200
        data = response.json()

        assert len(data["claims"]) == 2

    def test_list_claims_by_status(self, client):
        """Test filtering claims by status"""
        # Create and submit a claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Submit the claim
        client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})

        # Create another draft claim
        client.post("/api/v1/billing/claims", json={
            "patient_id": "12724067",
            "service_date": "2024-01-16"
        })

        # Filter by submitted status
        response = client.get("/api/v1/billing/claims?status=submitted")
        assert response.status_code == 200
        data = response.json()

        assert len(data["claims"]) == 1
        assert data["claims"][0]["status"] == "submitted"

    def test_get_patient_claims(self, client):
        """Test getting claims for a specific patient"""
        # Create claims for different patients
        client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-16"
        })
        client.post("/api/v1/billing/claims", json={
            "patient_id": "12724067",
            "service_date": "2024-01-17"
        })

        response = client.get("/api/v1/patient/12724066/claims")
        assert response.status_code == 200
        data = response.json()

        assert len(data["claims"]) == 2
        for claim in data["claims"]:
            assert claim["patient_id"] == "12724066"


# ==================== CLAIM UPDATE TESTS ====================

class TestClaimUpdate:
    """Tests for updating billing claims"""

    def test_update_claim_diagnoses(self, client):
        """Test updating claim diagnoses"""
        # Create claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Update diagnoses
        response = client.put(f"/api/v1/billing/claims/{claim_id}", json={
            "diagnoses": [
                {"code": "I10", "description": "Hypertension", "sequence": 1, "is_principal": True},
                {"code": "E11.9", "description": "Type 2 diabetes", "sequence": 2, "is_principal": False}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["claim"]["diagnoses"]) == 2
        assert data["claim"]["diagnoses"][0]["code"] == "I10"
        assert data["claim"]["diagnoses"][0]["is_principal"] is True

    def test_update_claim_service_lines(self, client):
        """Test updating claim service lines (procedures)"""
        # Create claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Update service lines
        response = client.put(f"/api/v1/billing/claims/{claim_id}", json={
            "service_lines": [
                {
                    "line_number": 1,
                    "service_date": "2024-01-15",
                    "procedure": {
                        "code": "99214",
                        "description": "Office visit, level 4",
                        "modifiers": ["25"],
                        "units": 1
                    },
                    "diagnosis_pointers": [1]
                }
            ]
        })
        assert response.status_code == 200
        data = response.json()

        assert len(data["claim"]["service_lines"]) == 1
        assert data["claim"]["service_lines"][0]["procedure"]["code"] == "99214"
        assert "25" in data["claim"]["service_lines"][0]["procedure"]["modifiers"]

    def test_cannot_update_submitted_claim(self, client):
        """Test that submitted claims cannot be updated"""
        # Create and submit claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]
        client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})

        # Try to update
        response = client.put(f"/api/v1/billing/claims/{claim_id}", json={
            "diagnoses": [{"code": "I10", "description": "HTN", "sequence": 1, "is_principal": True}]
        })
        assert response.status_code == 400
        assert "submitted" in response.json()["detail"].lower()

    def test_update_claim_not_found(self, client):
        """Test 404 for updating non-existent claim"""
        response = client.put("/api/v1/billing/claims/nonexistent123", json={
            "diagnoses": []
        })
        assert response.status_code == 404


# ==================== CLAIM SUBMISSION TESTS ====================

class TestClaimSubmission:
    """Tests for submitting billing claims"""

    def test_submit_claim_success(self, client):
        """Test successful claim submission"""
        # Create claim with codes
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "Acute URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Submit claim
        response = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={
            "confirm": True
        })
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["status"] == "submitted"
        assert "fhir_claim_id" in data

    def test_submit_claim_requires_diagnoses(self, client):
        """Test that submission requires at least one diagnosis"""
        # Create claim without codes
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Try to submit
        response = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={
            "confirm": True
        })
        assert response.status_code == 400
        assert "diagnosis" in response.json()["detail"].lower()

    def test_submit_claim_requires_procedures(self, client):
        """Test that submission requires at least one procedure"""
        # Create claim without CPT codes
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "Acute URI"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Try to submit
        response = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={
            "confirm": True
        })
        assert response.status_code == 400
        assert "procedure" in response.json()["detail"].lower()

    def test_submit_claim_with_confirmation(self, client):
        """Test that submission works with explicit confirmation"""
        # Create claim with codes
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "Acute URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Submit with confirm flag
        response = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={
            "confirm": True
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_resubmit_already_submitted_claim(self, client):
        """Test resubmitting an already submitted claim (allowed for re-processing)"""
        # Create and submit claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]
        first_submit = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})
        assert first_submit.status_code == 200

        # Resubmit (for re-processing workflows)
        response = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})
        # API allows resubmission for re-processing
        assert response.status_code == 200


# ==================== CLAIM DELETE TESTS ====================

class TestClaimDelete:
    """Tests for deleting billing claims"""

    def test_delete_draft_claim(self, client):
        """Test deleting a draft claim"""
        # Create claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Delete
        response = client.delete(f"/api/v1/billing/claims/{claim_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        get_response = client.get(f"/api/v1/billing/claims/{claim_id}")
        assert get_response.status_code == 404

    def test_cannot_delete_submitted_claim(self, client):
        """Test that submitted claims cannot be deleted"""
        # Create and submit claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]
        client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})

        # Try to delete
        response = client.delete(f"/api/v1/billing/claims/{claim_id}")
        assert response.status_code == 400
        assert "cannot delete" in response.json()["detail"].lower()


# ==================== CODE SEARCH TESTS ====================

class TestCodeSearch:
    """Tests for ICD-10 and CPT code search"""

    def test_search_icd10_codes(self, client):
        """Test searching ICD-10 codes"""
        response = client.get("/api/v1/billing/codes/icd10/search?q=hypertension")
        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert len(data["results"]) > 0
        # I10 should be in results
        codes = [r["code"] for r in data["results"]]
        assert any("I10" in c or "hypertension" in r["description"].lower()
                   for r, c in zip(data["results"], codes))

    def test_search_icd10_by_code(self, client):
        """Test searching ICD-10 by code number"""
        response = client.get("/api/v1/billing/codes/icd10/search?q=J06.9")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) > 0
        assert data["results"][0]["code"] == "J06.9"

    def test_search_cpt_codes(self, client):
        """Test searching CPT codes"""
        response = client.get("/api/v1/billing/codes/cpt/search?q=office visit")
        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert len(data["results"]) > 0

    def test_search_cpt_by_code(self, client):
        """Test searching CPT by code number"""
        response = client.get("/api/v1/billing/codes/cpt/search?q=99213")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) > 0
        assert data["results"][0]["code"] == "99213"

    def test_search_limit_parameter(self, client):
        """Test search limit parameter"""
        response = client.get("/api/v1/billing/codes/icd10/search?q=diabetes&limit=3")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) <= 3


# ==================== FHIR CLAIM TESTS ====================

class TestFHIRClaim:
    """Tests for FHIR Claim resource generation"""

    def test_get_fhir_claim(self, client):
        """Test getting FHIR Claim representation"""
        # Create claim with codes
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [
                {"code": "J06.9", "description": "Acute URI", "is_principal": True},
                {"code": "R50.9", "description": "Fever"}
            ],
            "cpt_codes": [
                {"code": "99213", "description": "Office visit"}
            ]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Get FHIR representation
        response = client.get(f"/api/v1/billing/claims/{claim_id}/fhir")
        assert response.status_code == 200
        data = response.json()

        # Check FHIR Claim structure
        assert data["resourceType"] == "Claim"
        assert data["status"] in ["draft", "active"]  # FHIR uses "active" for ready-to-submit
        assert data["type"]["coding"][0]["code"] == "professional"
        assert "patient" in data
        assert "diagnosis" in data
        assert len(data["diagnosis"]) == 2
        assert data["diagnosis"][0]["diagnosisCodeableConcept"]["coding"][0]["code"] == "J06.9"

    def test_fhir_claim_has_procedures(self, client):
        """Test FHIR Claim includes procedure items"""
        # Create claim with CPT codes
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [
                {"code": "99213", "description": "Office visit"},
                {"code": "87880", "description": "Strep test"}
            ]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Get FHIR representation
        response = client.get(f"/api/v1/billing/claims/{claim_id}/fhir")
        data = response.json()

        assert "item" in data
        assert len(data["item"]) == 2
        assert data["item"][0]["productOrService"]["coding"][0]["code"] == "99213"

    def test_fhir_claim_with_modifiers(self, client):
        """Test FHIR Claim includes CPT modifiers"""
        # Create claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        # Update with modifiers
        client.put(f"/api/v1/billing/claims/{claim_id}", json={
            "service_lines": [
                {
                    "line_number": 1,
                    "service_date": "2024-01-15",
                    "procedure": {
                        "code": "99214",
                        "description": "Office visit",
                        "modifiers": ["25", "59"],
                        "units": 1
                    },
                    "diagnosis_pointers": [1]
                }
            ]
        })

        # Get FHIR representation
        response = client.get(f"/api/v1/billing/claims/{claim_id}/fhir")
        data = response.json()

        item = data["item"][0]
        assert "modifier" in item
        modifier_codes = [m["coding"][0]["code"] for m in item["modifier"]]
        assert "25" in modifier_codes
        assert "59" in modifier_codes


# ==================== BILLING AUDIT TESTS ====================

class TestBillingAudit:
    """Tests for HIPAA audit logging of billing operations"""

    def test_create_claim_logged(self, client):
        """Test that claim creation is audit logged"""
        with patch('main.audit_logger.log_note_operation') as mock_audit:
            client.post("/api/v1/billing/claims", json={
                "patient_id": "12724066",
                "service_date": "2024-01-15"
            })

            # Verify audit was called
            mock_audit.assert_called()
            call_args = mock_audit.call_args
            assert call_args.kwargs.get('action') == 'CREATE_CLAIM' or \
                   call_args.args[0] == 'CREATE_CLAIM'

    def test_submit_claim_logged(self, client):
        """Test that claim submission is audit logged"""
        # Create claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [{"code": "99213", "description": "Office visit"}]
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        with patch('main.audit_logger.log_note_operation') as mock_audit:
            client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})

            # Verify audit was called for submission
            mock_audit.assert_called()
            call_args = mock_audit.call_args
            assert call_args.kwargs.get('action') == 'SUBMIT_CLAIM' or \
                   call_args.args[0] == 'SUBMIT_CLAIM'

    def test_view_claim_logged(self, client):
        """Test that viewing claims is audit logged"""
        # Create claim
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })
        claim_id = create_resp.json()["claim"]["claim_id"]

        with patch('main.audit_logger.log_note_operation') as mock_audit:
            client.get(f"/api/v1/billing/claims/{claim_id}")

            mock_audit.assert_called()


# ==================== EDGE CASES ====================

class TestBillingEdgeCases:
    """Tests for edge cases and error handling"""

    def test_diagnosis_sequencing(self, client):
        """Test that diagnoses are properly sequenced"""
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [
                {"code": "J06.9", "description": "URI"},
                {"code": "R50.9", "description": "Fever"},
                {"code": "R05.9", "description": "Cough"}
            ]
        })

        claim = create_resp.json()["claim"]

        # First diagnosis should be principal
        assert claim["diagnoses"][0]["is_principal"] is True
        assert claim["diagnoses"][1]["is_principal"] is False

        # Sequences should be ordered
        for i, dx in enumerate(claim["diagnoses"]):
            assert dx["sequence"] == i + 1

    def test_service_line_numbering(self, client):
        """Test that service lines are properly numbered"""
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15",
            "icd10_codes": [{"code": "J06.9", "description": "URI"}],
            "cpt_codes": [
                {"code": "99213", "description": "Office visit"},
                {"code": "87880", "description": "Strep test"},
                {"code": "94640", "description": "Nebulizer"}
            ]
        })

        claim = create_resp.json()["claim"]

        # Line numbers should be sequential
        for i, line in enumerate(claim["service_lines"]):
            assert line["line_number"] == i + 1

    def test_empty_code_search(self, client):
        """Test code search with no results"""
        response = client.get("/api/v1/billing/codes/icd10/search?q=xyznonexistent123")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0

    def test_claim_timestamps(self, client):
        """Test that claims have proper timestamps"""
        create_resp = client.post("/api/v1/billing/claims", json={
            "patient_id": "12724066",
            "service_date": "2024-01-15"
        })

        claim = create_resp.json()["claim"]
        assert "created_at" in claim
        assert claim["submitted_at"] is None  # Not submitted yet

        # Submit the claim
        claim_id = claim["claim_id"]
        client.put(f"/api/v1/billing/claims/{claim_id}", json={
            "diagnoses": [{"code": "J06.9", "description": "URI", "sequence": 1, "is_principal": True}],
            "service_lines": [{
                "line_number": 1,
                "service_date": "2024-01-15",
                "procedure": {"code": "99213", "description": "Office visit"},
                "diagnosis_pointers": [1]
            }]
        })
        submit_resp = client.post(f"/api/v1/billing/claims/{claim_id}/submit", json={"confirm": True})

        # Check submitted_at is now set
        get_resp = client.get(f"/api/v1/billing/claims/{claim_id}")
        updated_claim = get_resp.json()["claim"]
        assert updated_claim["submitted_at"] is not None
