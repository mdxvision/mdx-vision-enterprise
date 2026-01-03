"""
MDx Vision EHR Proxy - DNFB (Discharged Not Final Billed) Tests

Tests for DNFB tracking, prior authorization, and revenue cycle management.
Run with: pytest tests/test_dnfb.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, dnfb_accounts


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dnfb_accounts():
    """Clear DNFB accounts before each test"""
    dnfb_accounts.clear()
    yield
    dnfb_accounts.clear()


# ==================== DNFB CREATION TESTS ====================

class TestDNFBCreation:
    """Tests for creating DNFB accounts"""

    def test_create_dnfb_basic(self, client):
        """Test creating a basic DNFB account"""
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "dnfb" in data
        dnfb = data["dnfb"]
        assert dnfb["patient_id"] == "12724066"
        assert dnfb["discharge_date"] == "2024-01-10"
        assert dnfb["reason"] == "coding_incomplete"
        assert dnfb["is_resolved"] is False

    def test_create_dnfb_with_details(self, client):
        """Test creating DNFB with full details"""
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "patient_name": "John Smith",
            "mrn": "MRN123456",
            "discharge_date": "2024-01-10",
            "reason": "prior_auth_missing",
            "reason_detail": "Awaiting auth for MRI",
            "estimated_charges": 15000.00,
            "service_type": "inpatient",
            "attending_physician": "Dr. Jones"
        })
        assert response.status_code == 200
        data = response.json()

        dnfb = data["dnfb"]
        assert dnfb["patient_name"] == "John Smith"
        assert dnfb["mrn"] == "MRN123456"
        assert dnfb["reason"] == "prior_auth_missing"
        assert dnfb["estimated_charges"] == 15000.00
        assert dnfb["attending_physician"] == "Dr. Jones"

    def test_create_dnfb_calculates_aging(self, client):
        """Test that aging is calculated correctly"""
        # Create account with discharge date 5 days ago
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": past_date
        })
        data = response.json()

        dnfb = data["dnfb"]
        assert dnfb["days_since_discharge"] >= 4  # Allow for timing
        assert dnfb["aging_bucket"] in ["4-7", "0-3"]

    def test_create_dnfb_prior_auth_denied(self, client):
        """Test creating DNFB with prior auth denied reason"""
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10",
            "reason": "prior_auth_denied",
            "reason_detail": "Auth denied by UHC"
        })
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["reason"] == "prior_auth_denied"


# ==================== DNFB RETRIEVAL TESTS ====================

class TestDNFBRetrieval:
    """Tests for retrieving DNFB accounts"""

    def test_get_dnfb_by_id(self, client):
        """Test retrieving a DNFB account by ID"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Retrieve it
        response = client.get(f"/api/v1/dnfb/{dnfb_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["dnfb_id"] == dnfb_id

    def test_get_dnfb_not_found(self, client):
        """Test 404 for non-existent DNFB"""
        response = client.get("/api/v1/dnfb/nonexistent123")
        assert response.status_code == 404

    def test_list_all_dnfb(self, client):
        """Test listing all DNFB accounts"""
        # Create multiple accounts
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": "2024-01-11"
        })

        response = client.get("/api/v1/dnfb")
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        assert len(data["accounts"]) == 2

    def test_list_dnfb_by_reason(self, client):
        """Test filtering DNFB by reason"""
        # Create accounts with different reasons
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10",
            "reason": "coding_incomplete"
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": "2024-01-11",
            "reason": "prior_auth_missing"
        })

        response = client.get("/api/v1/dnfb?reason=prior_auth_missing")
        assert response.status_code == 200
        data = response.json()

        assert len(data["accounts"]) == 1
        assert data["accounts"][0]["reason"] == "prior_auth_missing"

    def test_list_dnfb_prior_auth_issues(self, client):
        """Test filtering by prior auth issues"""
        # Create accounts
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10",
            "reason": "coding_incomplete"
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": "2024-01-11",
            "reason": "prior_auth_denied"
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724068",
            "discharge_date": "2024-01-12",
            "reason": "prior_auth_expired"
        })

        response = client.get("/api/v1/dnfb?prior_auth_issue=true")
        assert response.status_code == 200
        data = response.json()

        assert len(data["accounts"]) == 2
        for acc in data["accounts"]:
            assert "prior_auth" in acc["reason"]


# ==================== DNFB UPDATE TESTS ====================

class TestDNFBUpdate:
    """Tests for updating DNFB accounts"""

    def test_update_dnfb_reason(self, client):
        """Test updating DNFB reason"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Update reason
        response = client.put(f"/api/v1/dnfb/{dnfb_id}", json={
            "reason": "documentation_missing",
            "reason_detail": "Missing op note"
        })
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["reason"] == "documentation_missing"
        assert data["dnfb"]["reason_detail"] == "Missing op note"

    def test_update_dnfb_assign_coder(self, client):
        """Test assigning coder to DNFB"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Assign coder
        response = client.put(f"/api/v1/dnfb/{dnfb_id}", json={
            "assigned_coder": "Jane Coder"
        })
        assert response.status_code == 200
        assert response.json()["dnfb"]["assigned_coder"] == "Jane Coder"

    def test_update_dnfb_add_notes(self, client):
        """Test adding notes to DNFB"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Add notes
        response = client.put(f"/api/v1/dnfb/{dnfb_id}", json={
            "notes": ["Called physician for clarification", "Awaiting callback"]
        })
        assert response.status_code == 200
        assert len(response.json()["dnfb"]["notes"]) == 2


# ==================== PRIOR AUTH TESTS ====================

class TestPriorAuth:
    """Tests for prior authorization tracking"""

    def test_add_prior_auth_approved(self, client):
        """Test adding approved prior auth"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10",
            "reason": "prior_auth_missing"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Add prior auth
        response = client.post(f"/api/v1/dnfb/{dnfb_id}/prior-auth", json={
            "auth_number": "AUTH123456",
            "status": "approved",
            "payer_name": "Blue Cross",
            "procedure_codes": ["70553"],
            "approval_date": "2024-01-15",
            "expiration_date": "2024-04-15",
            "approved_units": 1
        })
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["prior_auth"]["auth_number"] == "AUTH123456"
        assert data["dnfb"]["prior_auth"]["status"] == "approved"
        # Reason should update since prior auth was the issue
        assert data["dnfb"]["reason"] == "coding_incomplete"

    def test_add_prior_auth_denied(self, client):
        """Test adding denied prior auth"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Add denied auth
        response = client.post(f"/api/v1/dnfb/{dnfb_id}/prior-auth", json={
            "status": "denied",
            "payer_name": "UHC",
            "procedure_codes": ["70553"],
            "denial_reason": "Medical necessity not met"
        })
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["prior_auth"]["status"] == "denied"
        assert data["dnfb"]["prior_auth"]["denial_reason"] == "Medical necessity not met"
        assert data["dnfb"]["reason"] == "prior_auth_denied"

    def test_add_prior_auth_expired(self, client):
        """Test adding expired prior auth"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Add expired auth
        response = client.post(f"/api/v1/dnfb/{dnfb_id}/prior-auth", json={
            "auth_number": "AUTH999",
            "status": "expired",
            "payer_name": "Aetna",
            "expiration_date": "2023-12-31"
        })
        assert response.status_code == 200
        assert response.json()["dnfb"]["reason"] == "prior_auth_expired"


# ==================== DNFB RESOLUTION TESTS ====================

class TestDNFBResolution:
    """Tests for resolving DNFB accounts"""

    def test_resolve_dnfb(self, client):
        """Test resolving a DNFB account"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Resolve it
        response = client.post(f"/api/v1/dnfb/{dnfb_id}/resolve")
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["is_resolved"] is True
        assert data["dnfb"]["resolved_date"] is not None

    def test_resolve_dnfb_with_claim(self, client):
        """Test resolving DNFB with linked claim"""
        # Create account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]

        # Resolve with claim ID
        response = client.post(f"/api/v1/dnfb/{dnfb_id}/resolve?claim_id=CLAIM-12345")
        assert response.status_code == 200
        data = response.json()

        assert data["dnfb"]["claim_id"] == "CLAIM-12345"

    def test_resolved_not_in_list(self, client):
        """Test that resolved accounts are not in active list"""
        # Create and resolve an account
        create_resp = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10"
        })
        dnfb_id = create_resp.json()["dnfb"]["dnfb_id"]
        client.post(f"/api/v1/dnfb/{dnfb_id}/resolve")

        # Create active account
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": "2024-01-11"
        })

        # List should only show active
        response = client.get("/api/v1/dnfb")
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["accounts"][0]["patient_id"] == "12724067"


# ==================== DNFB SUMMARY TESTS ====================

class TestDNFBSummary:
    """Tests for DNFB summary metrics"""

    def test_dnfb_summary(self, client):
        """Test DNFB summary endpoint"""
        # Create multiple accounts
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "estimated_charges": 5000
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            "estimated_charges": 15000,
            "reason": "prior_auth_denied"
        })

        response = client.get("/api/v1/dnfb/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["total_accounts"] == 2
        assert data["total_estimated_charges"] == 20000
        assert data["prior_auth_issues"]["count"] == 1
        assert data["prior_auth_issues"]["charges"] == 15000
        assert "by_reason" in data
        assert "by_aging" in data

    def test_dnfb_summary_aging_counts(self, client):
        """Test aging bucket counts in summary"""
        # Create accounts with different ages
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724068",
            "discharge_date": (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
        })

        response = client.get("/api/v1/dnfb/summary")
        data = response.json()

        assert data["aging_over_7_days"] >= 2
        assert data["aging_over_14_days"] >= 1


# ==================== PATIENT DNFB TESTS ====================

class TestPatientDNFB:
    """Tests for patient-specific DNFB queries"""

    def test_get_patient_dnfb(self, client):
        """Test getting DNFB for specific patient"""
        # Create accounts for different patients
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-10",
            "estimated_charges": 5000
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": "2024-01-15",
            "estimated_charges": 8000
        })
        client.post("/api/v1/dnfb", json={
            "patient_id": "12724067",
            "discharge_date": "2024-01-12"
        })

        response = client.get("/api/v1/patient/12724066/dnfb")
        assert response.status_code == 200
        data = response.json()

        assert data["patient_id"] == "12724066"
        assert len(data["accounts"]) == 2
        assert data["active_count"] == 2
        assert data["total_unbilled_charges"] == 13000

    def test_patient_dnfb_no_accounts(self, client):
        """Test patient with no DNFB accounts"""
        response = client.get("/api/v1/patient/99999999/dnfb")
        assert response.status_code == 200
        data = response.json()

        assert data["active_count"] == 0
        assert len(data["accounts"]) == 0


# ==================== AGING CALCULATION TESTS ====================

class TestAgingCalculation:
    """Tests for aging bucket calculation"""

    def test_aging_bucket_0_3(self, client):
        """Test 0-3 day aging bucket"""
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": datetime.now().strftime("%Y-%m-%d")
        })
        assert response.json()["dnfb"]["aging_bucket"] == "0-3"

    def test_aging_bucket_4_7(self, client):
        """Test 4-7 day aging bucket"""
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": past_date
        })
        assert response.json()["dnfb"]["aging_bucket"] == "4-7"

    def test_aging_bucket_8_14(self, client):
        """Test 8-14 day aging bucket"""
        past_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": past_date
        })
        assert response.json()["dnfb"]["aging_bucket"] == "8-14"

    def test_aging_bucket_15_30(self, client):
        """Test 15-30 day aging bucket"""
        past_date = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": past_date
        })
        assert response.json()["dnfb"]["aging_bucket"] == "15-30"

    def test_aging_bucket_31_plus(self, client):
        """Test 31+ day aging bucket"""
        past_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        response = client.post("/api/v1/dnfb", json={
            "patient_id": "12724066",
            "discharge_date": past_date
        })
        assert response.json()["dnfb"]["aging_bucket"] == "31+"
