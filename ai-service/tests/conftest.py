"""
Pytest configuration for AI Service tests

This file patches OpenAI clients before any test modules import the app,
ensuring that services are created with mocked clients.
"""

import sys
from unittest.mock import Mock, MagicMock, AsyncMock

# ============================================================================
# CRITICAL: Create mock openai module BEFORE any other imports
# This must happen at the very top of conftest.py
# ============================================================================

# Create a SINGLE shared mock client for ALL OpenAI usage
# This is critical because in CI without env vars, both services use OpenAI()
# (not AzureOpenAI), so they both get the same client
_mock_openai_client = Mock()
_mock_openai_client.chat = Mock()
_mock_openai_client.chat.completions = Mock()
_mock_openai_client.chat.completions.create = Mock()

# Create a mock openai module and inject it into sys.modules
# BOTH OpenAI and AzureOpenAI return the SAME mock client
_mock_openai_module = MagicMock()
_mock_openai_module.OpenAI = Mock(return_value=_mock_openai_client)
_mock_openai_module.AzureOpenAI = Mock(return_value=_mock_openai_client)

# Inject mock module BEFORE any imports can happen
sys.modules['openai'] = _mock_openai_module

# Now we can safely import pytest and other modules
import pytest
import asyncio


def pytest_configure(config):
    """Called after command line options have been parsed and all plugins loaded."""
    pass  # Mock module already injected above


def pytest_unconfigure(config):
    """Called before test process is exited."""
    # Restore original openai module if it was cached
    pass


# ============================================================================
# Fixtures for accessing mock clients in tests
# ============================================================================

@pytest.fixture
def openai_mock():
    """Get the shared mock OpenAI client - resets call history between tests"""
    _mock_openai_client.reset_mock()
    return _mock_openai_client


# Aliases for backwards compatibility - all point to the same mock
@pytest.fixture
def drug_mock():
    """Alias for openai_mock - used by drug interaction tests"""
    _mock_openai_client.reset_mock()
    return _mock_openai_client


@pytest.fixture
def nlp_mock():
    """Alias for openai_mock - used by notes tests"""
    _mock_openai_client.reset_mock()
    return _mock_openai_client


@pytest.fixture
def openai_module():
    """Get the mock openai module"""
    return _mock_openai_module


@pytest.fixture
def app_client():
    """Get the FastAPI app after OpenAI is mocked"""
    from app.main import app
    return app


@pytest.fixture
def test_client():
    """Get a TestClient for the FastAPI app"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


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
