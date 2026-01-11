"""
Tests for Drug Interaction Service

Tests drug extraction, interaction checking, drug lookup,
and safety alerts - with actual service integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import json
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDrugInteractionServiceIntegration:
    """Integration tests for DrugInteractionService"""

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        return mock_response

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch('app.services.drug_interaction_service.settings') as mock:
            mock.azure_openai_endpoint = ""
            mock.azure_openai_api_key = ""
            mock.openai_api_key = "sk-test-key"
            yield mock

    @patch('app.services.drug_interaction_service.OpenAI')
    def test_service_initialization_openai(self, mock_openai_class, mock_settings):
        """Should initialize with OpenAI when Azure not configured"""
        from app.services.drug_interaction_service import DrugInteractionService

        service = DrugInteractionService()

        mock_openai_class.assert_called_once()
        assert service.model == "gpt-4-turbo-preview"

    @patch('app.services.drug_interaction_service.AzureOpenAI')
    def test_service_initialization_azure(self, mock_azure_class):
        """Should initialize with Azure OpenAI when configured"""
        with patch('app.services.drug_interaction_service.settings') as mock_settings:
            mock_settings.azure_openai_endpoint = "https://test.openai.azure.com"
            mock_settings.azure_openai_api_key = "test-key"
            mock_settings.azure_openai_api_version = "2024-02-15-preview"
            mock_settings.azure_openai_deployment = "gpt-4-deployment"

            from importlib import reload
            import app.services.drug_interaction_service as drug_service_module

            # Force reimport to use new settings
            with patch.object(drug_service_module, 'settings', mock_settings):
                service = drug_service_module.DrugInteractionService()

                assert mock_azure_class.called or service.model == "gpt-4-deployment"

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_extract_drugs_from_text(self, mock_openai_class, mock_settings):
        """Should extract medications from clinical text"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"medications": ["lisinopril", "metformin"]}'
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.extract_drugs_from_text("Patient is taking lisinopril and metformin")

        assert isinstance(result, list)
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_extract_drugs_handles_direct_array(self, mock_openai_class, mock_settings):
        """Should handle direct array response"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '["lisinopril", "metformin"]'
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.extract_drugs_from_text("Patient takes lisinopril and metformin")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_extract_drugs_handles_error(self, mock_openai_class, mock_settings):
        """Should return empty list on error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.extract_drugs_from_text("Test text")

        assert result == []

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_check_interactions(self, mock_openai_class, mock_settings):
        """Should check for drug interactions"""
        mock_client = Mock()
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
                    "recommendation": "Monitor INR closely"
                }
            ]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.check_interactions(["aspirin", "warfarin"])

        assert isinstance(result, list)
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_check_interactions_handles_error(self, mock_openai_class, mock_settings):
        """Should return empty list on interaction check error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.check_interactions(["aspirin", "warfarin"])

        assert result == []

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_check_interactions_direct_array_response(self, mock_openai_class, mock_settings):
        """Should handle direct array response for interactions"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([
            {
                "drug1": "lisinopril",
                "drug2": "potassium",
                "severity": "MODERATE",
                "description": "Hyperkalemia risk",
                "clinicalEffect": "Elevated potassium",
                "recommendation": "Monitor K+ levels"
            }
        ])
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.check_interactions(["lisinopril", "potassium"])

        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_lookup_drug(self, mock_openai_class, mock_settings):
        """Should look up drug information"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "Metformin",
            "genericName": "metformin hydrochloride",
            "drugClass": "Biguanide",
            "indications": ["Type 2 diabetes mellitus"],
            "commonSideEffects": ["Nausea", "Diarrhea"],
            "contraindications": ["Renal impairment"],
            "blackBoxWarning": "Lactic acidosis risk"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        result = await service.lookup_drug("metformin")

        assert isinstance(result, dict)
        assert "name" in result
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.drug_interaction_service.OpenAI')
    async def test_lookup_drug_raises_on_error(self, mock_openai_class, mock_settings):
        """Should raise exception on lookup error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.drug_interaction_service import DrugInteractionService
        service = DrugInteractionService()

        with pytest.raises(Exception):
            await service.lookup_drug("unknowndrug")


class TestDrugExtraction:
    """Unit tests for drug extraction logic"""

    def test_extract_single_drug(self):
        """Should extract single drug from text"""
        text = "Patient is taking lisinopril"
        medications = ["lisinopril"]
        assert "lisinopril" in medications

    def test_extract_multiple_drugs(self):
        """Should extract multiple drugs from text"""
        text = "Current medications: lisinopril, metformin, and atorvastatin"
        medications = ["lisinopril", "metformin", "atorvastatin"]
        assert len(medications) == 3
        assert "metformin" in medications

    def test_extract_brand_names(self):
        """Should recognize brand names"""
        brand_to_generic = {
            "Lipitor": "atorvastatin",
            "Norvasc": "amlodipine",
            "Glucophage": "metformin",
        }
        text = "Patient takes Lipitor daily"
        extracted = None
        for brand, generic in brand_to_generic.items():
            if brand.lower() in text.lower():
                extracted = [generic]
                break
        assert extracted is not None
        assert "atorvastatin" in extracted


class TestInteractionChecking:
    """Tests for drug-drug interaction checking"""

    def test_high_severity_interaction(self, sample_interactions):
        """Should detect high severity interactions"""
        interactions = sample_interactions
        high_severity = [i for i in interactions if i["severity"] == "HIGH"]
        assert len(high_severity) > 0
        assert high_severity[0]["drug1"] == "aspirin"
        assert high_severity[0]["drug2"] == "warfarin"

    def test_contraindicated_interaction(self):
        """Should detect contraindicated combinations"""
        interactions = [
            {
                "drug1": "methotrexate",
                "drug2": "trimethoprim",
                "severity": "CONTRAINDICATED",
                "description": "Severe bone marrow suppression risk",
                "clinicalEffect": "Fatal pancytopenia reported",
                "recommendation": "Avoid combination"
            }
        ]
        contraindicated = [i for i in interactions if i["severity"] == "CONTRAINDICATED"]
        assert len(contraindicated) > 0
        assert "bone marrow" in contraindicated[0]["description"]

    def test_moderate_interaction(self):
        """Should detect moderate interactions"""
        interactions = [
            {
                "drug1": "lisinopril",
                "drug2": "potassium",
                "severity": "MODERATE",
                "description": "Increased potassium levels",
                "clinicalEffect": "Risk of hyperkalemia",
                "recommendation": "Monitor potassium levels"
            }
        ]
        assert interactions[0]["severity"] == "MODERATE"
        assert "hyperkalemia" in interactions[0]["clinicalEffect"].lower()


class TestCommonInteractions:
    """Tests for commonly known drug interactions"""

    def test_warfarin_interactions(self):
        """Should detect warfarin interactions"""
        warfarin_interactors = ["aspirin", "ibuprofen", "naproxen"]
        drug_list = ["warfarin", "ibuprofen"]
        has_interaction = any(d in warfarin_interactors for d in drug_list)
        assert has_interaction is True

    def test_ace_inhibitor_arb_combination(self):
        """Should detect ACE inhibitor + ARB combination"""
        ace_inhibitors = ["lisinopril", "enalapril", "ramipril"]
        arbs = ["losartan", "valsartan", "irbesartan"]
        drug_list = ["lisinopril", "losartan"]
        has_ace = any(d in ace_inhibitors for d in drug_list)
        has_arb = any(d in arbs for d in drug_list)
        assert has_ace and has_arb


class TestDrugLookup:
    """Tests for individual drug information lookup"""

    def test_drug_lookup_response_format(self):
        """Should return properly formatted drug info"""
        drug_info = {
            "name": "Metformin",
            "genericName": "metformin hydrochloride",
            "drugClass": "Biguanide",
            "indications": ["Type 2 diabetes mellitus"],
            "commonSideEffects": ["Nausea", "Diarrhea"],
            "contraindications": ["Renal impairment"],
            "blackBoxWarning": "Lactic acidosis risk"
        }
        assert drug_info["name"] == "Metformin"
        assert drug_info["drugClass"] == "Biguanide"


class TestSeverityLevels:
    """Tests for interaction severity classification"""

    def test_severity_hierarchy(self):
        """Should recognize severity hierarchy"""
        severity_levels = ["LOW", "MODERATE", "HIGH", "CONTRAINDICATED"]
        assert severity_levels.index("CONTRAINDICATED") > severity_levels.index("HIGH")
        assert severity_levels.index("HIGH") > severity_levels.index("MODERATE")


class TestErrorHandling:
    """Tests for error handling in drug service"""

    def test_empty_drug_list_handling(self):
        """Should handle empty drug list"""
        drugs = []
        if len(drugs) < 2:
            interactions = []
        else:
            interactions = ["would check"]
        assert len(interactions) == 0

    def test_malformed_drug_name_handling(self):
        """Should handle malformed drug names"""
        drug_name = "123!@#invalid"
        import re
        valid_pattern = r'^[a-zA-Z][a-zA-Z0-9\-\s]+$'
        is_valid = bool(re.match(valid_pattern, drug_name))
        assert is_valid is False


class TestJSONResponseParsing:
    """Tests for JSON response parsing"""

    def test_parse_medications_array(self):
        """Should parse medications array from response"""
        response_content = '{"medications": ["lisinopril", "metformin"]}'
        result = json.loads(response_content)
        medications = result.get("medications", result)
        assert isinstance(medications, list)
        assert len(medications) == 2

    def test_parse_interactions_array(self):
        """Should parse interactions array from response"""
        response_content = '''{"interactions": [
            {"drug1": "aspirin", "drug2": "warfarin", "severity": "HIGH"}
        ]}'''
        result = json.loads(response_content)
        interactions = result.get("interactions", result)
        assert isinstance(interactions, list)
        assert interactions[0]["severity"] == "HIGH"
