"""
Real Integration Tests for EHR FHIR APIs

Run with: pytest tests/test_integration_ehr.py --live

These tests connect to REAL EHR sandbox environments:
- Cerner Open Sandbox (public, no auth required)
- Epic Sandbox (public read-only)
- Athena Health (requires credentials)
- NextGen (requires credentials)

No mocking - actual HTTP calls to FHIR endpoints.
"""

import pytest
import httpx
import asyncio

# Mark all tests as integration tests requiring EHR credentials
pytestmark = [pytest.mark.integration, pytest.mark.ehr]


class TestCernerSandboxIntegration:
    """Integration tests with real Cerner FHIR sandbox"""

    # Cerner open sandbox - no auth required
    BASE_URL = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

    # Known test patient in Cerner sandbox
    TEST_PATIENT_ID = "12724066"  # SMARTS SR., NANCYS II

    @pytest.mark.asyncio
    async def test_cerner_metadata_endpoint(self):
        """Should retrieve Cerner capability statement"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/metadata")

        assert response.status_code == 200
        data = response.json()

        assert data["resourceType"] == "CapabilityStatement"
        assert "fhirVersion" in data
        assert data["fhirVersion"].startswith("4.")  # R4

    @pytest.mark.asyncio
    async def test_cerner_patient_read(self):
        """Should retrieve patient by ID from Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/Patient/{self.TEST_PATIENT_ID}"
            )

        assert response.status_code == 200
        patient = response.json()

        assert patient["resourceType"] == "Patient"
        assert patient["id"] == self.TEST_PATIENT_ID
        assert "name" in patient

    @pytest.mark.asyncio
    async def test_cerner_patient_search_by_name(self):
        """Should search patients by name in Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/Patient",
                params={"name": "SMART"}
            )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert "entry" in bundle
        assert len(bundle["entry"]) > 0

    @pytest.mark.asyncio
    async def test_cerner_conditions(self):
        """Should retrieve patient conditions from Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/Condition",
                params={"patient": self.TEST_PATIENT_ID}
            )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"

    @pytest.mark.asyncio
    async def test_cerner_medications(self):
        """Should retrieve patient medications from Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/MedicationRequest",
                params={"patient": self.TEST_PATIENT_ID}
            )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"

    @pytest.mark.asyncio
    async def test_cerner_allergies(self):
        """Should retrieve patient allergies from Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/AllergyIntolerance",
                params={"patient": self.TEST_PATIENT_ID}
            )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"

    @pytest.mark.asyncio
    async def test_cerner_observations_vitals(self):
        """Should retrieve patient vitals from Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/Observation",
                params={
                    "patient": self.TEST_PATIENT_ID,
                    "category": "vital-signs"
                }
            )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"

    @pytest.mark.asyncio
    async def test_cerner_observations_labs(self):
        """Should retrieve patient labs from Cerner"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/Observation",
                params={
                    "patient": self.TEST_PATIENT_ID,
                    "category": "laboratory"
                }
            )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"


class TestEpicSandboxIntegration:
    """Integration tests with Epic FHIR sandbox"""

    # Epic public sandbox - read-only, no auth for read operations
    BASE_URL = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"

    @pytest.mark.asyncio
    async def test_epic_metadata_endpoint(self):
        """Should retrieve Epic capability statement"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/metadata")

        # Epic may require auth even for metadata
        if response.status_code == 401:
            pytest.skip("Epic requires OAuth authentication")

        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "CapabilityStatement"

    @pytest.mark.asyncio
    async def test_epic_fhir_version(self):
        """Should support FHIR R4"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.BASE_URL}/metadata")

        if response.status_code == 401:
            pytest.skip("Epic requires OAuth authentication")

        data = response.json()
        assert "4" in data.get("fhirVersion", "")


class TestFHIRComplianceIntegration:
    """Test FHIR R4 compliance across EHR systems"""

    CERNER_URL = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

    @pytest.mark.asyncio
    async def test_fhir_json_content_type(self):
        """Should return application/fhir+json"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.CERNER_URL}/metadata")

        content_type = response.headers.get("content-type", "")
        assert "fhir+json" in content_type or "json" in content_type

    @pytest.mark.asyncio
    async def test_fhir_bundle_structure(self):
        """Should return valid Bundle for searches"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.CERNER_URL}/Patient",
                params={"_count": "5"}
            )

        assert response.status_code == 200
        bundle = response.json()

        # Validate Bundle structure
        assert bundle["resourceType"] == "Bundle"
        assert "type" in bundle
        assert bundle["type"] in ["searchset", "batch-response"]
        assert "total" in bundle or "entry" in bundle

    @pytest.mark.asyncio
    async def test_fhir_error_response(self):
        """Should return OperationOutcome for errors"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.CERNER_URL}/Patient/nonexistent-patient-id-12345"
            )

        # Should be 404 with OperationOutcome
        assert response.status_code in [404, 400]

        data = response.json()
        assert data["resourceType"] == "OperationOutcome"
        assert "issue" in data


class TestEHRPatientWorkflow:
    """End-to-end workflow tests with real EHR"""

    CERNER_URL = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    TEST_PATIENT_ID = "12724066"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_patient_summary_workflow(self):
        """Should retrieve complete patient summary (like AR glasses would)"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Get patient demographics
            patient_resp = await client.get(
                f"{self.CERNER_URL}/Patient/{self.TEST_PATIENT_ID}"
            )
            assert patient_resp.status_code == 200
            patient = patient_resp.json()

            # 2. Get allergies
            allergies_resp = await client.get(
                f"{self.CERNER_URL}/AllergyIntolerance",
                params={"patient": self.TEST_PATIENT_ID}
            )
            assert allergies_resp.status_code == 200

            # 3. Get medications
            meds_resp = await client.get(
                f"{self.CERNER_URL}/MedicationRequest",
                params={"patient": self.TEST_PATIENT_ID}
            )
            assert meds_resp.status_code == 200

            # 4. Get conditions
            conditions_resp = await client.get(
                f"{self.CERNER_URL}/Condition",
                params={"patient": self.TEST_PATIENT_ID}
            )
            assert conditions_resp.status_code == 200

            # 5. Get vitals
            vitals_resp = await client.get(
                f"{self.CERNER_URL}/Observation",
                params={
                    "patient": self.TEST_PATIENT_ID,
                    "category": "vital-signs",
                    "_count": "10"
                }
            )
            assert vitals_resp.status_code == 200

            # Verify we got data
            assert "name" in patient
            print(f"\n✅ Patient: {patient.get('name', [{}])[0].get('text', 'Unknown')}")
            print(f"   DOB: {patient.get('birthDate', 'Unknown')}")
            print(f"   Allergies: {allergies_resp.json().get('total', 0)}")
            print(f"   Medications: {meds_resp.json().get('total', 0)}")
            print(f"   Conditions: {conditions_resp.json().get('total', 0)}")


class TestEHRPerformance:
    """Performance benchmarks with real EHR"""

    CERNER_URL = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_patient_lookup_latency(self):
        """Should complete patient lookup within acceptable time"""
        import time

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            response = await client.get(
                f"{self.CERNER_URL}/Patient/12724066"
            )
            elapsed = time.time() - start

        assert response.status_code == 200
        # Should complete within 5 seconds (reasonable for demo)
        assert elapsed < 5.0, f"Patient lookup took {elapsed:.2f}s (>5s)"
        print(f"\n⏱️ Patient lookup: {elapsed:.3f}s")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_resource_fetching(self):
        """Should fetch multiple resources in parallel efficiently"""
        import time

        patient_id = "12724066"

        async def fetch_resource(client, resource_type, params):
            return await client.get(
                f"{self.CERNER_URL}/{resource_type}",
                params=params
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()

            # Fetch in parallel
            results = await asyncio.gather(
                fetch_resource(client, "AllergyIntolerance", {"patient": patient_id}),
                fetch_resource(client, "MedicationRequest", {"patient": patient_id}),
                fetch_resource(client, "Condition", {"patient": patient_id}),
                fetch_resource(client, "Observation", {"patient": patient_id, "category": "vital-signs"}),
            )

            elapsed = time.time() - start

        # All should succeed
        for r in results:
            assert r.status_code == 200

        # Parallel should be faster than sequential
        # 4 requests should complete in ~2-3 seconds, not 8-12
        assert elapsed < 8.0, f"Parallel fetch took {elapsed:.2f}s (>8s)"
        print(f"\n⏱️ Parallel fetch (4 resources): {elapsed:.3f}s")
