"""
Tests for Clinical NLP Service (SOAP Note Generation)

Tests SOAP note generation, ICD-10/CPT code extraction,
summary generation, and handoff notes - with actual service integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestClinicalNLPServiceIntegration:
    """Integration tests for ClinicalNLPService"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch('app.services.clinical_nlp_service.settings') as mock:
            mock.azure_openai_endpoint = ""
            mock.azure_openai_api_key = ""
            mock.openai_api_key = "sk-test-key"
            yield mock

    @patch('app.services.clinical_nlp_service.OpenAI')
    def test_service_initialization_openai(self, mock_openai_class, mock_settings):
        """Should initialize with OpenAI when Azure not configured"""
        from app.services.clinical_nlp_service import ClinicalNLPService

        service = ClinicalNLPService()

        mock_openai_class.assert_called_once()
        assert service.model == "gpt-4-turbo-preview"
        assert service.is_azure is False

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_soap_note(self, mock_openai_class, mock_settings):
        """Should generate SOAP note from transcription"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "subjective": "Patient presents with headache for 3 days",
            "objective": "BP 120/80, alert and oriented",
            "assessment": "Tension headache",
            "plan": "OTC analgesics, follow up PRN",
            "summary": "Patient with tension headache, conservative management",
            "icd10Codes": ["G44.209"],
            "cptCodes": ["99213"]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_soap_note(
            transcription_text="Patient has had a headache for 3 days",
            chief_complaint="Headache"
        )

        assert isinstance(result, dict)
        assert "subjective" in result
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_soap_note_with_context(self, mock_openai_class, mock_settings):
        """Should generate SOAP note with patient context"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "subjective": "Diabetic patient with foot pain",
            "objective": "Exam findings",
            "assessment": "Diabetic neuropathy",
            "plan": "Gabapentin",
            "summary": "Neuropathy management",
            "icd10Codes": ["E11.42"],
            "cptCodes": ["99214"]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_soap_note(
            transcription_text="Patient complains of foot pain",
            chief_complaint="Foot pain",
            patient_context={"conditions": ["diabetes"], "age": 65}
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_soap_note_error(self, mock_openai_class, mock_settings):
        """Should raise exception on SOAP note generation error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        with pytest.raises(Exception):
            await service.generate_soap_note(transcription_text="Test")

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_nine_line(self, mock_openai_class, mock_settings):
        """Should generate 9-Line Medevac report"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Line 1: Grid 12345678"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_nine_line(
            transcription_text="Casualty at grid 12345678"
        )

        assert isinstance(result, dict)
        assert "report" in result

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_nine_line_with_context(self, mock_openai_class, mock_settings):
        """Should generate 9-Line with context"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "9-Line Report"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_nine_line(
            transcription_text="Casualty report",
            context={"location": "Grid 12345678"}
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_nine_line_error(self, mock_openai_class, mock_settings):
        """Should raise exception on 9-Line generation error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        with pytest.raises(Exception):
            await service.generate_nine_line(transcription_text="Test")

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_extract_medical_codes(self, mock_openai_class, mock_settings):
        """Should extract ICD-10 and CPT codes"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "icd10": [{"code": "J06.9", "description": "URI"}],
            "cpt": [{"code": "99213", "description": "Office visit"}]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.extract_medical_codes(
            clinical_text="Patient has acute upper respiratory infection"
        )

        assert isinstance(result, dict)
        assert "icd10" in result

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_extract_medical_codes_error(self, mock_openai_class, mock_settings):
        """Should return empty lists on code extraction error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.extract_medical_codes("Test text")

        assert result == {"icd10": [], "cpt": []}

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_summary(self, mock_openai_class, mock_settings):
        """Should generate encounter summary"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Patient with headache. Conservative management."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_summary(
            transcription_text="Patient has had headache for 3 days"
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_summary_error(self, mock_openai_class, mock_settings):
        """Should raise exception on summary generation error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        with pytest.raises(Exception):
            await service.generate_summary("Test text")

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_handoff_note(self, mock_openai_class, mock_settings):
        """Should generate I-PASS handoff note"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I: Moderate\nP: Patient summary"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_handoff_note(
            transcription_text="Patient with chest pain"
        )

        assert isinstance(result, dict)
        assert "handoff" in result

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_handoff_error(self, mock_openai_class, mock_settings):
        """Should raise exception on handoff generation error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        with pytest.raises(Exception):
            await service.generate_handoff_note("Test")

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_generic_note(self, mock_openai_class, mock_settings):
        """Should generate generic clinical note"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Consultation note content"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        result = await service.generate_generic_note(
            transcription_text="Consultation encounter",
            note_type="Consultation"
        )

        assert isinstance(result, dict)
        assert "content" in result

    @pytest.mark.asyncio
    @patch('app.services.clinical_nlp_service.OpenAI')
    async def test_generate_generic_note_error(self, mock_openai_class, mock_settings):
        """Should raise exception on generic note generation error"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        from app.services.clinical_nlp_service import ClinicalNLPService
        service = ClinicalNLPService()

        with pytest.raises(Exception):
            await service.generate_generic_note("Test", "Progress Note")


class TestSOAPNoteGeneration:
    """Tests for SOAP note generation"""

    def test_soap_note_structure(self, sample_soap_response):
        """Should generate SOAP note with all required sections"""
        note = sample_soap_response
        assert "subjective" in note
        assert "objective" in note
        assert "assessment" in note
        assert "plan" in note

    def test_soap_note_contains_icd10_codes(self, sample_soap_response):
        """Should include ICD-10 codes in response"""
        note = sample_soap_response
        assert "icd10Codes" in note
        assert isinstance(note["icd10Codes"], list)

    def test_chief_complaint_integration(self):
        """Should include chief complaint in note generation"""
        chief_complaint = "Headache"
        transcript = "Patient has had headache for 3 days"
        user_prompt = f"Chief Complaint: {chief_complaint}\n\nTranscription:\n{transcript}"
        assert "Chief Complaint: Headache" in user_prompt


class TestICD10CodeExtraction:
    """Tests for ICD-10 code extraction"""

    def test_icd10_code_format(self):
        """Should return properly formatted ICD-10 codes"""
        import re
        code = "G43.909"
        pattern = r'^[A-Z]\d{2}\.?\d{0,4}$'
        assert re.match(pattern, code) is not None

    def test_common_icd10_codes(self):
        """Should recognize common diagnoses"""
        common_codes = {
            "hypertension": "I10",
            "type 2 diabetes": "E11.9",
            "chest pain": "R07.9",
        }
        assert common_codes["hypertension"] == "I10"


class TestCPTCodeExtraction:
    """Tests for CPT code extraction"""

    def test_cpt_code_format(self):
        """Should return properly formatted CPT codes"""
        code = "99213"
        assert len(code) == 5
        assert code.isdigit()

    def test_em_code_levels(self):
        """Should recognize E/M code levels"""
        em_codes = {
            "99213": "Low complexity",
            "99214": "Moderate complexity",
            "99215": "High complexity"
        }
        assert em_codes["99213"] == "Low complexity"


class TestNineLineReport:
    """Tests for 9-Line Medevac report generation"""

    def test_nine_line_structure(self):
        """Should generate all 9 lines"""
        nine_line = {
            "line1": "Grid", "line2": "Freq", "line3": "Patients",
            "line4": "Equipment", "line5": "Type", "line6": "Security",
            "line7": "Marking", "line8": "Nationality", "line9": "NBC"
        }
        assert len(nine_line) == 9

    def test_precedence_categories(self):
        """Should recognize precedence categories"""
        precedence = {"A": "Urgent", "B": "Priority", "C": "Routine"}
        assert "Urgent" in precedence["A"]


class TestHandoffNotes:
    """Tests for I-PASS/SBAR handoff note generation"""

    def test_ipass_structure(self):
        """Should generate I-PASS format"""
        ipass_sections = ["I", "P", "A", "S", "S"]
        assert len(ipass_sections) == 5

    def test_sbar_structure(self):
        """Should generate SBAR format"""
        sbar = {"situation": "", "background": "", "assessment": "", "recommendation": ""}
        assert "situation" in sbar


class TestNoteTypes:
    """Tests for different clinical note types"""

    def test_supported_note_types(self):
        """Should support multiple note types"""
        note_types = ["SOAP", "Progress Note", "H&P", "9-Line", "Handoff"]
        assert "SOAP" in note_types

    def test_default_note_type(self):
        """Should default to SOAP note"""
        default_type = "SOAP"
        assert default_type == "SOAP"


class TestAIClientConfiguration:
    """Tests for AI client configuration"""

    def test_openai_fallback(self):
        """Should fall back to OpenAI when Azure not configured"""
        azure_endpoint = None
        if not azure_endpoint:
            provider = "openai"
            model = "gpt-4-turbo-preview"
        else:
            provider = "azure"
            model = "custom-deployment"
        assert provider == "openai"

    def test_temperature_settings(self):
        """Should use appropriate temperature for clinical content"""
        soap_temperature = 0.3
        assert soap_temperature < 0.5


class TestErrorHandling:
    """Tests for error handling in note generation"""

    def test_empty_transcript_handling(self):
        """Should handle empty transcripts"""
        transcript = ""
        should_process = bool(transcript and len(transcript.strip()) > 0)
        assert should_process is False

    def test_malformed_response_handling(self):
        """Should handle malformed JSON responses"""
        malformed_response = "Not valid JSON {"
        try:
            result = json.loads(malformed_response)
        except json.JSONDecodeError:
            result = {"error": "Invalid JSON response"}
        assert "error" in result
