"""
Pytest configuration for AI Service tests

This file patches OpenAI clients before any test modules import the app,
ensuring that services are created with mocked clients.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import asyncio
import sys

# ============================================================================
# CRITICAL: Patch OpenAI before any imports
# This must happen at module load time, before pytest collects tests
# ============================================================================

# Create mock clients that will be used by all services
_mock_nlp_client = Mock()
_mock_nlp_client.chat = Mock()
_mock_nlp_client.chat.completions = Mock()
_mock_nlp_client.chat.completions.create = Mock()

_mock_drug_client = Mock()
_mock_drug_client.chat = Mock()
_mock_drug_client.chat.completions = Mock()
_mock_drug_client.chat.completions.create = Mock()

# Patch OpenAI and AzureOpenAI classes before any imports
_openai_patch = patch('openai.OpenAI', return_value=_mock_drug_client)
_azure_openai_patch = patch('openai.AzureOpenAI', return_value=_mock_nlp_client)

# Start patches immediately at module load
_openai_patch.start()
_azure_openai_patch.start()


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins loaded."""
    pass  # Patches already started above


def pytest_unconfigure(config):
    """Called before test process is exited."""
    _openai_patch.stop()
    _azure_openai_patch.stop()


# ============================================================================
# Fixtures for accessing mock clients in tests
# ============================================================================

@pytest.fixture(scope="session")
def mock_openai_client():
    """Get the mock OpenAI client used by drug interaction service"""
    return _mock_drug_client


@pytest.fixture(scope="session")
def mock_azure_openai_client():
    """Get the mock Azure OpenAI client used by NLP service"""
    return _mock_nlp_client


@pytest.fixture
def drug_mock():
    """Get the mock drug service client - resets call history between tests"""
    _mock_drug_client.reset_mock()
    return _mock_drug_client


@pytest.fixture
def nlp_mock():
    """Get the mock NLP service client - resets call history between tests"""
    _mock_nlp_client.reset_mock()
    return _mock_nlp_client


@pytest.fixture
def app_client():
    """Get the FastAPI app after OpenAI is mocked"""
    from app.main import app
    return app


# ============================================================================
# Sample data fixtures
# ============================================================================

@pytest.fixture
def sample_transcription():
    """Sample transcription text for testing"""
    return """
    Doctor: Good morning, how are you feeling today?
    Patient: I've been having a headache for the past three days. It's mostly on the right side of my head.
    Doctor: Any nausea or sensitivity to light?
    Patient: Yes, bright lights seem to make it worse.
    Doctor: And are you taking any medications currently?
    Patient: Just ibuprofen for the headache and lisinopril for blood pressure.
    Doctor: Okay, based on your symptoms, this sounds like a migraine. I'm going to prescribe sumatriptan.
    """


@pytest.fixture
def sample_patient_context():
    """Sample patient context for testing"""
    return {
        "name": "SMITH, JOHN",
        "mrn": "12345678",
        "dob": "1980-05-15",
        "allergies": ["Penicillin"],
        "medications": ["Lisinopril 10mg daily"],
        "conditions": ["Hypertension", "Migraine"]
    }


@pytest.fixture
def sample_soap_response():
    """Sample SOAP note response for testing"""
    return {
        "subjective": "Patient reports 3-day history of right-sided headache with photophobia. Currently taking ibuprofen and lisinopril.",
        "objective": "Patient appears in mild distress. Vital signs stable.",
        "assessment": "Migraine without aura",
        "plan": "1. Prescribe sumatriptan 50mg PRN for acute migraine\n2. Continue lisinopril\n3. Follow up in 2 weeks if symptoms persist",
        "summary": "Patient with migraine presents with typical symptoms. Starting abortive therapy.",
        "icd10Codes": ["G43.909"],
        "cptCodes": ["99213"]
    }


@pytest.fixture
def sample_drug_list():
    """Sample list of drugs for interaction testing"""
    return ["lisinopril", "metformin", "aspirin", "warfarin"]


@pytest.fixture
def sample_interactions():
    """Sample drug interactions for testing"""
    return [
        {
            "drug1": "aspirin",
            "drug2": "warfarin",
            "severity": "HIGH",
            "description": "Increased bleeding risk",
            "clinicalEffect": "Additive anticoagulant effects may lead to serious bleeding",
            "recommendation": "Monitor INR closely, consider aspirin alternatives"
        }
    ]


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
