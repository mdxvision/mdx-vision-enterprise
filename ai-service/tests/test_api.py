"""
Tests for AI Service FastAPI API Routes

Tests all API endpoints with mocked services for full coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Module-level patches to mock OpenAI before any imports
@pytest.fixture(scope="module")
def mock_openai():
    """Mock OpenAI at module level before any imports"""
    with patch('app.services.clinical_nlp_service.OpenAI') as mock_nlp, \
         patch('app.services.clinical_nlp_service.AzureOpenAI') as mock_azure_nlp, \
         patch('app.services.drug_interaction_service.OpenAI') as mock_drug, \
         patch('app.services.drug_interaction_service.AzureOpenAI') as mock_azure_drug:
        # Create mock clients
        mock_nlp_client = Mock()
        mock_drug_client = Mock()
        mock_nlp.return_value = mock_nlp_client
        mock_azure_nlp.return_value = mock_nlp_client
        mock_drug.return_value = mock_drug_client
        mock_azure_drug.return_value = mock_drug_client
        yield {
            'nlp': mock_nlp_client,
            'drug': mock_drug_client
        }


@pytest.fixture
def app_client(mock_openai):
    """Get the FastAPI app after OpenAI is mocked"""
    from app.main import app
    return app


@pytest.fixture
def drug_mock(mock_openai):
    """Get the drug service mock client"""
    return mock_openai['drug']


@pytest.fixture
def nlp_mock(mock_openai):
    """Get the NLP service mock client"""
    return mock_openai['nlp']


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    @pytest.mark.asyncio
    async def test_health_check(self, app_client):
        """Should return healthy status"""
        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mdx-ai-pipeline"


class TestRootEndpoint:
    """Tests for root / endpoint"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, app_client):
        """Should return service info"""
        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "MDx Vision AI Pipeline"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"


class TestDrugInteractionRoutes:
    """Tests for /v1/drugs routes"""

    @pytest.mark.asyncio
    async def test_check_interactions_endpoint(self, app_client, drug_mock):
        """Should check drug interactions"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "interactions": [
                {
                    "drug1": "aspirin",
                    "drug2": "warfarin",
                    "severity": "HIGH",
                    "description": "Increased bleeding risk",
                    "clinicalEffect": "Enhanced anticoagulation",
                    "recommendation": "Monitor INR"
                }
            ]
        })
        drug_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/drugs/check-interactions",
                json={"drugs": ["aspirin", "warfarin"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert "drugsIdentified" in data
        assert "interactions" in data

    @pytest.mark.asyncio
    async def test_check_interactions_less_than_two_drugs(self, app_client, drug_mock):
        """Should return empty interactions for single drug"""
        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/drugs/check-interactions",
                json={"drugs": ["aspirin"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["interactions"] == []
        assert data["hasContraindications"] is False

    @pytest.mark.asyncio
    async def test_check_interactions_from_text(self, app_client, drug_mock):
        """Should extract drugs from text and check interactions"""
        # Mock drug extraction
        mock_response1 = Mock()
        mock_response1.choices = [Mock()]
        mock_response1.choices[0].message.content = '{"medications": ["lisinopril", "potassium"]}'

        # Mock interaction check
        mock_response2 = Mock()
        mock_response2.choices = [Mock()]
        mock_response2.choices[0].message.content = json.dumps({
            "interactions": [
                {
                    "drug1": "lisinopril",
                    "drug2": "potassium",
                    "severity": "MODERATE",
                    "description": "Hyperkalemia risk",
                    "clinicalEffect": "Elevated K+",
                    "recommendation": "Monitor"
                }
            ]
        })

        drug_mock.chat.completions.create.side_effect = [mock_response1, mock_response2]

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/drugs/check-interactions",
                json={"text": "Patient takes lisinopril and potassium supplement"}
            )

        assert response.status_code == 200
        # Reset side_effect for other tests
        drug_mock.chat.completions.create.side_effect = None

    @pytest.mark.asyncio
    async def test_extract_medications_endpoint(self, app_client, drug_mock):
        """Should extract medications from text"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"medications": ["metformin", "atorvastatin"]}'
        drug_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/drugs/extract-medications",
                json={"text": "Taking metformin and atorvastatin daily"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "medications" in data
        assert "count" in data

    @pytest.mark.asyncio
    async def test_extract_medications_no_text(self, app_client, drug_mock):
        """Should return 400 when no text provided"""
        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/drugs/extract-medications",
                json={}
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_drug_lookup_endpoint(self, app_client, drug_mock):
        """Should look up drug information"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "Metformin",
            "genericName": "metformin HCl",
            "drugClass": "Biguanide",
            "indications": ["Type 2 diabetes"],
            "commonSideEffects": ["Nausea"],
            "contraindications": ["Renal impairment"],
            "blackBoxWarning": "Lactic acidosis"
        })
        drug_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.get("/v1/drugs/lookup/metformin")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data


class TestNotesRoutes:
    """Tests for /v1/notes routes"""

    @pytest.mark.asyncio
    async def test_generate_soap_note_endpoint(self, app_client, nlp_mock):
        """Should generate SOAP note"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "subjective": "Patient with headache",
            "objective": "BP 120/80",
            "assessment": "Tension headache",
            "plan": "OTC analgesics",
            "summary": "Headache management",
            "icd10Codes": ["G44.209"],
            "cptCodes": ["99213"]
        })
        nlp_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/generate",
                json={
                    "encounterId": "test-123",
                    "noteType": "SOAP",
                    "transcriptionText": "Patient has headache",
                    "chiefComplaint": "Headache"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "subjective" in data

    @pytest.mark.asyncio
    async def test_generate_nine_line_endpoint(self, app_client, nlp_mock):
        """Should generate 9-Line report (returns SOAP format due to response_model)"""
        # Note: Endpoint uses response_model=SOAPNote, so NINE_LINE also returns SOAP format
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "subjective": "9-Line Medevac Request",
            "objective": "Grid 12345678, 1 urgent patient",
            "assessment": "Trauma requiring medevac",
            "plan": "Coordinate helicopter extraction",
            "summary": "Urgent medevac requested"
        })
        nlp_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/generate",
                json={
                    "encounterId": "test-123",
                    "noteType": "NINE_LINE",
                    "transcriptionText": "Casualty at grid 12345678"
                }
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_generic_note_endpoint(self, app_client, nlp_mock):
        """Should generate generic note for other types"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "subjective": "Patient reports follow up",
            "objective": "Vitals stable",
            "assessment": "Condition stable",
            "plan": "Continue current treatment"
        })
        nlp_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/generate",
                json={
                    "encounterId": "test-123",
                    "noteType": "SOAP",
                    "transcriptionText": "Follow up visit"
                }
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_extract_codes_endpoint(self, app_client, nlp_mock):
        """Should extract ICD-10 and CPT codes"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "icd10": [{"code": "J06.9", "description": "URI"}],
            "cpt": [{"code": "99213", "description": "Office visit"}]
        })
        nlp_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/extract-codes",
                json={
                    "encounterId": "test-123",
                    "transcriptionText": "Patient has URI"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "icd10Codes" in data
        assert "cptCodes" in data

    @pytest.mark.asyncio
    async def test_summarize_endpoint(self, app_client, nlp_mock):
        """Should generate encounter summary"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Patient with headache. Conservative management."
        nlp_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/summarize",
                json={
                    "encounterId": "test-123",
                    "transcriptionText": "Patient has had headache for 3 days"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_handoff_endpoint(self, app_client, nlp_mock):
        """Should generate handoff note"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I: Moderate\nP: Patient summary"
        nlp_mock.chat.completions.create.return_value = mock_response

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/handoff",
                json={
                    "encounterId": "test-123",
                    "transcriptionText": "Patient with chest pain"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "handoff" in data


class TestConfigSettings:
    """Tests for configuration settings"""

    def test_settings_defaults(self):
        """Should have default settings"""
        from app.config import Settings

        settings = Settings(
            assemblyai_api_key="",
            azure_openai_endpoint="",
            azure_openai_api_key="",
            openai_api_key=""
        )

        assert settings.service_name == "mdx-ai-pipeline"
        assert settings.environment == "development"
        assert settings.debug is True

    def test_get_settings_cached(self, mock_openai):
        """Should cache settings with lru_cache"""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestErrorHandling:
    """Tests for API error handling"""

    @pytest.mark.asyncio
    async def test_drug_interaction_error_handling(self, app_client, drug_mock):
        """Should handle drug interaction errors"""
        drug_mock.chat.completions.create.side_effect = Exception("API Error")

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/drugs/check-interactions",
                json={"drugs": ["aspirin", "warfarin"]}
            )

        # Returns 200 with empty interactions on error (graceful degradation)
        assert response.status_code == 200
        data = response.json()
        assert data["interactions"] == []

        # Reset side_effect
        drug_mock.chat.completions.create.side_effect = None

    @pytest.mark.asyncio
    async def test_note_generation_error_handling(self, app_client, nlp_mock):
        """Should handle note generation errors"""
        nlp_mock.chat.completions.create.side_effect = Exception("API Error")

        async with AsyncClient(transport=ASGITransport(app=app_client), base_url="http://test") as client:
            response = await client.post(
                "/v1/notes/generate",
                json={
                    "encounterId": "test-123",
                    "transcriptionText": "Test"
                }
            )

        assert response.status_code == 500

        # Reset side_effect
        nlp_mock.chat.completions.create.side_effect = None
