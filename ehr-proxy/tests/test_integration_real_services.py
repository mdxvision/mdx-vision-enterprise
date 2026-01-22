"""
Real Integration Tests - Hits actual services (not mocked)

Requirements:
- OPENAI_API_KEY or AZURE_OPENAI_API_KEY
- ASSEMBLYAI_API_KEY
- ANTHROPIC_API_KEY (Claude)
- Network access to Cerner/Epic sandboxes

Run with: pytest tests/test_integration_real_services.py -v -s
"""

import pytest
import httpx
import os
import json
import asyncio
from typing import Optional

# Skip all tests if no API keys
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
ASSEMBLYAI_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

# EHR Sandbox URLs
CERNER_BASE = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
EPIC_BASE = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"

# Test patient IDs
CERNER_PATIENT_ID = "12724066"  # SMARTS SR., NANCYS II


class TestCernerFHIRIntegration:
    """Real tests against Cerner sandbox"""

    @pytest.mark.asyncio
    async def test_patient_read(self):
        """Fetch real patient from Cerner sandbox"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{CERNER_BASE}/Patient/{CERNER_PATIENT_ID}",
                headers={"Accept": "application/fhir+json"}
            )

        assert response.status_code == 200, f"Cerner returned {response.status_code}: {response.text}"
        patient = response.json()

        assert patient["resourceType"] == "Patient"
        assert patient["id"] == CERNER_PATIENT_ID
        assert "name" in patient
        print(f"✓ Patient: {patient['name'][0]['family']}, {patient['name'][0]['given'][0]}")

    @pytest.mark.asyncio
    async def test_patient_search_by_name(self):
        """Search patients by name in Cerner sandbox"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{CERNER_BASE}/Patient",
                params={"name": "SMART"},
                headers={"Accept": "application/fhir+json"}
            )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle.get("total", 0) > 0 or len(bundle.get("entry", [])) > 0
        print(f"✓ Found {bundle.get('total', len(bundle.get('entry', [])))} patients matching 'SMART'")

    @pytest.mark.asyncio
    async def test_patient_conditions(self):
        """Fetch conditions for patient"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = None
            last_error = None
            for attempt in range(3):
                try:
                    response = await client.get(
                        f"{CERNER_BASE}/Condition",
                        params={"patient": CERNER_PATIENT_ID},
                        headers={"Accept": "application/fhir+json"}
                    )
                    break
                except httpx.ReadTimeout as exc:
                    last_error = exc
                    await asyncio.sleep(1 + attempt)

            if response is None:
                pytest.xfail("Cerner sandbox timed out fetching conditions after retries")

        if response.status_code >= 500:
            pytest.xfail(f"Cerner sandbox error: HTTP {response.status_code}")

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        entries = bundle.get("entry", [])
        print(f"✓ Found {len(entries)} conditions for patient")

        for entry in entries[:3]:  # Show first 3
            condition = entry.get("resource", {})
            code = condition.get("code", {}).get("coding", [{}])[0]
            print(f"  - {code.get('display', 'Unknown')}")

    @pytest.mark.asyncio
    async def test_patient_medications(self):
        """Fetch medications for patient"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{CERNER_BASE}/MedicationRequest",
                params={"patient": CERNER_PATIENT_ID},
                headers={"Accept": "application/fhir+json"}
            )

        assert response.status_code == 200
        bundle = response.json()
        entries = bundle.get("entry", [])
        print(f"✓ Found {len(entries)} medication requests")

    @pytest.mark.asyncio
    async def test_patient_allergies(self):
        """Fetch allergies for patient"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{CERNER_BASE}/AllergyIntolerance",
                params={"patient": CERNER_PATIENT_ID},
                headers={"Accept": "application/fhir+json"}
            )

        assert response.status_code == 200
        bundle = response.json()
        entries = bundle.get("entry", [])
        print(f"✓ Found {len(entries)} allergies")

    @pytest.mark.asyncio
    async def test_patient_vitals(self):
        """Fetch vital signs for patient"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{CERNER_BASE}/Observation",
                params={
                    "patient": CERNER_PATIENT_ID,
                    "category": "vital-signs"
                },
                headers={"Accept": "application/fhir+json"}
            )

        assert response.status_code == 200
        bundle = response.json()
        entries = bundle.get("entry", [])
        print(f"✓ Found {len(entries)} vital sign observations")

    @pytest.mark.asyncio
    async def test_patient_labs(self):
        """Fetch lab results for patient"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{CERNER_BASE}/Observation",
                params={
                    "patient": CERNER_PATIENT_ID,
                    "category": "laboratory"
                },
                headers={"Accept": "application/fhir+json"}
            )

        assert response.status_code == 200
        bundle = response.json()
        entries = bundle.get("entry", [])
        print(f"✓ Found {len(entries)} lab observations")


class TestEpicFHIRIntegration:
    """Real tests against Epic sandbox"""

    @pytest.mark.asyncio
    async def test_epic_metadata(self):
        """Verify Epic FHIR endpoint is accessible"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{EPIC_BASE}/metadata",
                headers={"Accept": "application/fhir+json"}
            )

        # Epic may require auth for some endpoints
        assert response.status_code in [200, 401, 403], f"Epic returned {response.status_code}"
        if response.status_code == 200:
            capability = response.json()
            assert capability["resourceType"] == "CapabilityStatement"
            print(f"✓ Epic FHIR server: {capability.get('software', {}).get('name', 'Unknown')}")
        else:
            print(f"✓ Epic endpoint reachable (requires auth: {response.status_code})")


@pytest.mark.skipif(not OPENAI_KEY, reason="OPENAI_API_KEY not set")
class TestOpenAINoteGeneration:
    """Real tests against OpenAI for clinical note generation"""

    @pytest.mark.asyncio
    async def test_soap_note_generation(self):
        """Generate SOAP note using real OpenAI"""
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_KEY)

        transcript = """
        Doctor: Good morning, how are you feeling today?
        Patient: I've had a headache for the past three days. It's mainly on the right side.
        Doctor: On a scale of 1-10, how would you rate the pain?
        Patient: About a 6. It gets worse when I look at bright lights.
        Doctor: Have you taken anything for it?
        Patient: Just some ibuprofen, but it only helps a little.
        Doctor: Any nausea or visual changes?
        Patient: Some nausea, no visual changes.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Generate a SOAP note from this clinical encounter. Return JSON with keys: subjective, objective, assessment, plan"},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content
        assert content is not None
        assert len(content) > 100
        print(f"✓ Generated SOAP note ({len(content)} chars)")
        print(f"  Preview: {content[:200]}...")

    @pytest.mark.asyncio
    async def test_icd10_extraction(self):
        """Extract ICD-10 codes using real OpenAI"""
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_KEY)

        clinical_text = "Patient presents with tension headache and photophobia. History of migraines."

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract ICD-10 codes from this clinical text. Return JSON array with code and description."},
                {"role": "user", "content": clinical_text}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        assert content is not None
        print(f"✓ Extracted ICD-10 codes: {content[:200]}")

    @pytest.mark.asyncio
    async def test_drug_interaction_check(self):
        """Check drug interactions using real OpenAI"""
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_KEY)

        medications = ["warfarin", "aspirin", "ibuprofen"]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Check for drug interactions. Return JSON array with drug1, drug2, severity, description."},
                {"role": "user", "content": f"Check interactions between: {', '.join(medications)}"}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        assert content is not None
        assert "warfarin" in content.lower() or "interaction" in content.lower()
        print(f"✓ Drug interaction check: {content[:300]}")


@pytest.mark.skipif(not ANTHROPIC_KEY, reason="ANTHROPIC_API_KEY not set")
class TestClaudeIntegration:
    """Real tests against Claude API"""

    @pytest.mark.asyncio
    async def test_clinical_copilot(self):
        """Test AI Clinical Co-pilot with Claude"""
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": "Patient has BP 180/110, headache, and blurry vision. What should I consider?"}
                ]
            )
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e):
                pytest.skip("Anthropic API credits exhausted")
            raise

        content = message.content[0].text
        assert content is not None
        assert len(content) > 50
        print(f"✓ Claude copilot response: {content[:300]}...")

    @pytest.mark.asyncio
    async def test_differential_diagnosis(self):
        """Generate differential diagnosis with Claude"""
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": "Generate differential diagnosis for: 45yo male, chest pain radiating to left arm, diaphoresis, shortness of breath. Return top 5 with likelihood."}
                ]
            )
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e):
                pytest.skip("Anthropic API credits exhausted")
            raise

        content = message.content[0].text
        assert content is not None
        assert "infarction" in content.lower() or "cardiac" in content.lower() or "heart" in content.lower()
        print(f"✓ DDx generated: {content[:400]}...")


@pytest.mark.skipif(not ASSEMBLYAI_KEY, reason="ASSEMBLYAI_API_KEY not set")
class TestAssemblyAIIntegration:
    """Real tests against AssemblyAI"""

    @pytest.mark.asyncio
    async def test_api_connectivity(self):
        """Verify AssemblyAI API is accessible"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.assemblyai.com/v2/transcript",
                headers={"Authorization": ASSEMBLYAI_KEY}
            )

        # Should get 200 with empty list or 400 for bad request, not 401
        assert response.status_code != 401, "AssemblyAI API key is invalid"
        print(f"✓ AssemblyAI API accessible (status: {response.status_code})")


class TestEHRProxyEndpoints:
    """Integration tests for EHR Proxy endpoints hitting real Cerner"""

    @pytest.fixture(scope="session")
    def base_url(self):
        """EHR Proxy base URL"""
        return os.getenv("EHR_PROXY_URL", "http://localhost:8002")

    @pytest.mark.asyncio
    async def test_patient_endpoint(self, base_url):
        """Test /api/v1/patient/{id} endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{base_url}/api/v1/patient/{CERNER_PATIENT_ID}")
                if response.status_code == 200:
                    patient = response.json()
                    assert "id" in patient or "name" in patient
                    print(f"✓ EHR Proxy patient endpoint works")
                else:
                    pytest.skip(f"EHR Proxy not running or returned {response.status_code}")
            except httpx.ConnectError:
                pytest.skip("EHR Proxy not running at " + base_url)

    @pytest.mark.asyncio
    async def test_patient_search_endpoint(self, base_url):
        """Test /api/v1/patient/search endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{base_url}/api/v1/patient/search",
                    params={"name": "SMART"}
                )
                if response.status_code == 200:
                    results = response.json()
                    print(f"✓ EHR Proxy search endpoint works")
                else:
                    pytest.skip(f"EHR Proxy returned {response.status_code}")
            except httpx.ConnectError:
                pytest.skip("EHR Proxy not running")

    @pytest.mark.asyncio
    async def test_health_endpoint(self, base_url):
        """Test /health endpoint"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{base_url}/health")
                assert response.status_code == 200
                print(f"✓ EHR Proxy health check passed")
            except httpx.ConnectError:
                pytest.skip("EHR Proxy not running")


class TestEndToEndWorkflow:
    """Full end-to-end workflow tests"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not OPENAI_KEY, reason="OPENAI_API_KEY not set")
    async def test_patient_to_soap_note_workflow(self):
        """
        Full workflow:
        1. Fetch patient from Cerner
        2. Get conditions, meds, allergies
        3. Generate SOAP note with AI
        """
        from openai import OpenAI

        # Step 1: Fetch patient
        async with httpx.AsyncClient(timeout=30.0) as client:
            patient_resp = await client.get(
                f"{CERNER_BASE}/Patient/{CERNER_PATIENT_ID}",
                headers={"Accept": "application/fhir+json"}
            )
        assert patient_resp.status_code == 200
        patient = patient_resp.json()
        patient_name = f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}"
        print(f"✓ Step 1: Fetched patient {patient_name}")

        # Step 2: Fetch conditions
        async with httpx.AsyncClient(timeout=30.0) as client:
            conditions_resp = await client.get(
                f"{CERNER_BASE}/Condition",
                params={"patient": CERNER_PATIENT_ID},
                headers={"Accept": "application/fhir+json"}
            )
        conditions = []
        if conditions_resp.status_code == 200:
            for entry in conditions_resp.json().get("entry", [])[:5]:
                code = entry.get("resource", {}).get("code", {}).get("coding", [{}])[0]
                conditions.append(code.get("display", "Unknown"))
        print(f"✓ Step 2: Fetched {len(conditions)} conditions")

        # Step 3: Generate SOAP note
        openai_client = OpenAI(api_key=OPENAI_KEY)

        context = f"""
        Patient: {patient_name}
        Known conditions: {', '.join(conditions) if conditions else 'None documented'}

        Today's encounter transcript:
        Patient reports feeling well today. Here for routine follow-up.
        Vitals stable. No new complaints.
        """

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Generate a SOAP note for this patient encounter."},
                {"role": "user", "content": context}
            ],
            temperature=0.3
        )

        soap_note = response.choices[0].message.content
        assert soap_note is not None
        assert len(soap_note) > 100
        print(f"✓ Step 3: Generated SOAP note ({len(soap_note)} chars)")
        print(f"\n--- SOAP Note Preview ---\n{soap_note[:500]}...")

        print("\n✓ Full E2E workflow completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
