"""
Pytest Configuration for EHR Proxy - Option B Testing Strategy

Option B: Mock Tests (fast, CI/CD) + Real Integration Tests (opt-in)

Usage:
    # Run only fast mock tests (default - for CI/CD)
    pytest tests/

    # Run integration tests with real APIs
    pytest tests/ --live

    # Run specific integration category
    pytest tests/ --live -m ehr
    pytest tests/ --live -m assemblyai
    pytest tests/ --live -m rag

    # Run all tests (mock + integration)
    pytest tests/ --live --run-all

Environment Variables (for integration tests):
    ASSEMBLYAI_API_KEY     - AssemblyAI real-time transcription
    EPIC_SANDBOX_URL       - Epic FHIR R4 sandbox
    CERNER_SANDBOX_URL     - Cerner FHIR R4 sandbox
    ATHENA_SANDBOX_URL     - Athena Health sandbox
    NEXTGEN_SANDBOX_URL    - NextGen Healthcare sandbox
    CHROMA_PERSIST_DIR     - ChromaDB storage directory
"""

import pytest
import os
import sys
from typing import Optional

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def pytest_addoption(parser):
    """Add command-line options for integration testing."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run integration tests with real APIs"
    )
    parser.addoption(
        "--run-all",
        action="store_true",
        default=False,
        help="Run both mock and integration tests"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests with mocks")
    config.addinivalue_line("markers", "integration: Real API integration tests")
    config.addinivalue_line("markers", "slow: Tests taking > 5 seconds")
    config.addinivalue_line("markers", "ehr: Tests requiring EHR credentials")
    config.addinivalue_line("markers", "assemblyai: Tests requiring AssemblyAI key")
    config.addinivalue_line("markers", "rag: Tests requiring ChromaDB")


def pytest_collection_modifyitems(config, items):
    """
    Skip integration tests unless --live flag is provided.
    This is the core of Option B: mocks run by default, integration opt-in.
    """
    if config.getoption("--live"):
        # Running with --live: run integration tests
        # If --run-all, run everything; otherwise skip unit tests
        if not config.getoption("--run-all"):
            # Only run integration tests
            skip_unit = pytest.mark.skip(reason="Running only integration tests (use --run-all for both)")
            for item in items:
                if "integration" not in [m.name for m in item.iter_markers()]:
                    item.add_marker(skip_unit)
    else:
        # Default: skip integration tests
        skip_integration = pytest.mark.skip(reason="Integration test - use --live to run")
        for item in items:
            if "integration" in [m.name for m in item.iter_markers()]:
                item.add_marker(skip_integration)


# ═══════════════════════════════════════════════════════════════════════════
# ENVIRONMENT FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def live_mode(request):
    """Check if running in live integration mode."""
    return request.config.getoption("--live")


@pytest.fixture(scope="session")
def assemblyai_api_key():
    """Get AssemblyAI API key from environment."""
    key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not key:
        pytest.skip("ASSEMBLYAI_API_KEY not set")
    return key


@pytest.fixture(scope="session")
def epic_sandbox_url():
    """Get Epic FHIR sandbox URL."""
    # Default to public Epic sandbox
    return os.environ.get(
        "EPIC_SANDBOX_URL",
        "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
    )


@pytest.fixture(scope="session")
def cerner_sandbox_url():
    """Get Cerner FHIR sandbox URL."""
    # Default to public Cerner sandbox
    return os.environ.get(
        "CERNER_SANDBOX_URL",
        "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    )


@pytest.fixture(scope="session")
def athena_sandbox_url():
    """Get Athena Health sandbox URL."""
    return os.environ.get("ATHENA_SANDBOX_URL")


@pytest.fixture(scope="session")
def nextgen_sandbox_url():
    """Get NextGen Healthcare sandbox URL."""
    return os.environ.get("NEXTGEN_SANDBOX_URL")


# ═══════════════════════════════════════════════════════════════════════════
# MOCK FIXTURES (for unit tests)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_audio_sample():
    """Create mock audio data (base64 encoded)."""
    import base64
    # 1 second of silence at 16kHz, 16-bit
    audio_bytes = bytes([0] * 16000 * 2)
    return base64.b64encode(audio_bytes).decode()


@pytest.fixture
def mock_patient_data():
    """Sample patient data for testing."""
    return {
        "id": "12724066",
        "name": "SMARTS SR., NANCYS II",
        "mrn": "12724066",
        "dob": "1990-09-15",
        "gender": "female",
        "allergies": ["Penicillin"],
        "medications": ["Lisinopril 10mg daily"],
        "conditions": ["Hypertension", "Type 2 Diabetes"]
    }


@pytest.fixture
def mock_vital_signs():
    """Sample vital signs for testing."""
    return {
        "bloodPressure": "120/80",
        "heartRate": 72,
        "respiratoryRate": 16,
        "temperature": 98.6,
        "oxygenSaturation": 98
    }


@pytest.fixture
def mock_transcript():
    """Sample transcription for testing."""
    return """
    Doctor: Good morning, how are you feeling today?
    Patient: I've been having chest pain for the past two days.
    Doctor: Can you describe the pain?
    Patient: It's a dull ache in my chest, worse when I breathe deeply.
    Doctor: Any shortness of breath?
    Patient: Yes, especially when climbing stairs.
    """


# ═══════════════════════════════════════════════════════════════════════════
# CHROMADB/RAG FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def chroma_test_dir(tmp_path_factory):
    """Create temporary directory for ChromaDB in tests."""
    return tmp_path_factory.mktemp("chroma_test")


@pytest.fixture
def mock_rag_documents():
    """Sample documents for RAG testing."""
    return [
        {
            "content": "Chest pain evaluation should include ECG, troponin levels, and risk stratification using HEART score.",
            "source": "AHA Guidelines 2024",
            "specialty": "cardiology"
        },
        {
            "content": "Type 2 diabetes management: Start metformin as first-line therapy. Target A1c < 7% for most adults.",
            "source": "ADA Standards 2024",
            "specialty": "endocrinology"
        },
        {
            "content": "Community-acquired pneumonia: Amoxicillin for low-risk, add macrolide for moderate risk.",
            "source": "IDSA Guidelines 2023",
            "specialty": "infectious_disease"
        }
    ]


# ═══════════════════════════════════════════════════════════════════════════
# ASYNC HELPERS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ═══════════════════════════════════════════════════════════════════════════
# TEST HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def assert_fhir_response(response: dict, resource_type: str):
    """Helper to validate FHIR response structure."""
    assert "resourceType" in response or "entry" in response, \
        f"Invalid FHIR response: missing resourceType or entry"

    if "resourceType" in response:
        assert response["resourceType"] == resource_type, \
            f"Expected {resource_type}, got {response['resourceType']}"


def assert_soap_note(note: dict):
    """Helper to validate SOAP note structure."""
    required_sections = ["subjective", "objective", "assessment", "plan"]
    for section in required_sections:
        assert section in note, f"SOAP note missing {section} section"
