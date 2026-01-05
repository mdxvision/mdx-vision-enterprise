# MDx Vision Testing Strategy

## Option B: Mock Tests + Real Integration Tests

This project uses a dual testing strategy:

1. **Mock Tests (Default)** - Fast, no external dependencies, run on every commit
2. **Integration Tests (Opt-in)** - Real API calls, verify actual behavior

### Why This Approach?

| Test Type | Speed | CI/CD | Confidence | Dependencies |
|-----------|-------|-------|------------|--------------|
| Mock | ~30 seconds | ✅ Every commit | Logic correctness | None |
| Integration | ~2-5 minutes | ✅ Main branch | Real-world behavior | API keys, network |

**Hospital Sales Point:**
> "Our test suite includes 500+ unit tests that run in 30 seconds on every commit, PLUS live integration tests against Epic, Cerner, and AssemblyAI that verify real-world behavior."

---

## Quick Start

### Run Fast Mock Tests (Default)

```bash
# EHR Proxy (489+ tests)
cd ehr-proxy
pytest tests/

# AI Service
cd ai-service
pytest tests/

# Web Dashboard
cd web
npm test

# All components
./run-tests.sh  # (if available)
```

### Run Real Integration Tests

```bash
# Set up credentials
export ASSEMBLYAI_API_KEY=your_key_here

# Run integration tests
cd ehr-proxy
pytest tests/ --live

# Run specific integration category
pytest tests/ --live -m ehr          # EHR FHIR APIs only
pytest tests/ --live -m assemblyai   # AssemblyAI only
pytest tests/ --live -m rag          # ChromaDB/RAG only

# Run ALL tests (mock + integration)
pytest tests/ --live --run-all
```

---

## Test Categories

### 1. Unit Tests (Mock)
Fast tests with mocked external services.

```python
# Example: Mocked AssemblyAI test
@patch.dict('sys.modules', {'assemblyai': MagicMock()})
def test_service_initialization(self, mock_settings):
    """Should initialize with session ID"""
    service = AssemblyAIService(session_id="test-123")
    assert service.session_id == "test-123"
```

**When to use:**
- Testing business logic
- Testing error handling
- Testing edge cases
- CI/CD pipelines

### 2. Integration Tests (Real)
Tests that call actual external APIs.

```python
# Example: Real Cerner FHIR test
@pytest.mark.integration
@pytest.mark.ehr
async def test_cerner_patient_read(self):
    """Should retrieve real patient from Cerner sandbox"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://fhir-open.cerner.com/r4/.../Patient/12724066"
        )
    assert response.status_code == 200
    assert response.json()["resourceType"] == "Patient"
```

**When to use:**
- Verifying API contracts haven't changed
- Testing authentication flows
- Performance benchmarking
- Pre-release validation

---

## Test Markers

| Marker | Description | Run Command |
|--------|-------------|-------------|
| `@pytest.mark.unit` | Fast mock tests | `pytest` (default) |
| `@pytest.mark.integration` | Real API tests | `pytest --live` |
| `@pytest.mark.slow` | Tests > 5 seconds | `pytest -m slow` |
| `@pytest.mark.ehr` | EHR FHIR tests | `pytest --live -m ehr` |
| `@pytest.mark.assemblyai` | AssemblyAI tests | `pytest --live -m assemblyai` |
| `@pytest.mark.rag` | ChromaDB tests | `pytest --live -m rag` |

---

## Environment Variables

### For Integration Tests

```bash
# Required for AssemblyAI tests
ASSEMBLYAI_API_KEY=your_assemblyai_key

# Optional: Override default sandbox URLs
EPIC_SANDBOX_URL=https://fhir.epic.com/...
CERNER_SANDBOX_URL=https://fhir-open.cerner.com/...
ATHENA_SANDBOX_URL=https://...
NEXTGEN_SANDBOX_URL=https://...

# Optional: ChromaDB persistence
CHROMA_PERSIST_DIR=/path/to/chroma/data
```

### Setting Up Locally

```bash
# Create .env file (not committed to git)
cat > ehr-proxy/.env << EOF
ASSEMBLYAI_API_KEY=your_key_here
EOF

# Load before running tests
export $(cat ehr-proxy/.env | xargs)
pytest tests/ --live
```

---

## CI/CD Pipeline

### GitHub Actions Configuration

The CI workflow runs:

| Job | Trigger | Tests |
|-----|---------|-------|
| `python-tests` | Every push | Mock tests only |
| `web-tests` | Every push | Vitest mock tests |
| `java-tests` | Every push | JUnit mock tests |
| `integration-tests` | Main branch | Real API tests |

### Setting Up GitHub Secrets

1. Go to Repository → Settings → Secrets → Actions
2. Add these secrets:
   - `ASSEMBLYAI_API_KEY`
   - (Optional) `EPIC_CLIENT_ID`, `EPIC_CLIENT_SECRET`
   - (Optional) `ATHENA_API_KEY`

---

## Test Coverage Goals

| Component | Current | Target | Strategy |
|-----------|---------|--------|----------|
| EHR Proxy | 71% | 85% | More unit tests for edge cases |
| AI Service | 95% | 95% | Maintain with mocks |
| Web Dashboard | 80% | 90% | Component + E2E tests |
| Backend Java | 75% | 85% | Service layer tests |

### Running Coverage Reports

```bash
# EHR Proxy
cd ehr-proxy
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# AI Service
cd ai-service
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Web
cd web
npm run test:coverage
open coverage/index.html
```

---

## Test File Structure

```
ehr-proxy/tests/
├── conftest.py                    # Fixtures and --live flag
├── pytest.ini                     # Pytest configuration
│
├── # Mock Tests (run by default)
├── test_auth.py                   # Device authentication
├── test_voiceprint.py             # Voiceprint API endpoints
├── test_voiceprint_unit.py        # Voiceprint module unit tests
├── test_clinical_safety.py        # Drug interactions, alerts
├── test_racial_medicine.py        # Health equity
├── test_maternal_health.py        # OB monitoring
├── test_sdoh.py                   # Social determinants
├── test_rag.py                    # RAG mocked tests
│
├── # Integration Tests (run with --live)
├── test_integration_ehr.py        # Real Cerner/Epic calls
├── test_integration_assemblyai.py # Real transcription
└── test_integration_rag.py        # Real ChromaDB
```

---

## Best Practices

### 1. Always Mock External Services in Unit Tests

```python
# Good - Mocked
@patch('app.services.assemblyai_service.aai')
def test_start_stream(self, mock_aai):
    # Fast, deterministic, no network
    pass

# Bad - Real API in unit test
def test_start_stream(self):
    # Slow, flaky, costs money
    service.start_stream()
```

### 2. Use Markers for Integration Tests

```python
# Always mark integration tests
@pytest.mark.integration
@pytest.mark.ehr
async def test_real_cerner_api(self):
    # This won't run without --live flag
    pass
```

### 3. Handle Rate Limits Gracefully

```python
try:
    result = await api.call()
except RateLimitError:
    pytest.skip("API rate limited")
```

### 4. Use Fixtures for Common Setup

```python
# conftest.py
@pytest.fixture
def mock_patient_data():
    return {"id": "12724066", "name": "Test Patient"}

# test file
def test_patient_display(mock_patient_data):
    assert mock_patient_data["id"] == "12724066"
```

### 5. Run Integration Tests Before Release

```bash
# Pre-release checklist
pytest tests/ --live --run-all -v
```

---

## Troubleshooting

### Tests Skipping with "Integration test - use --live to run"

This is expected! Integration tests are opt-in:
```bash
pytest tests/ --live  # Add this flag
```

### "ASSEMBLYAI_API_KEY not set"

```bash
export ASSEMBLYAI_API_KEY=your_key_here
pytest tests/ --live -m assemblyai
```

### ChromaDB Tests Failing

```bash
# Install dependencies
pip install chromadb sentence-transformers

# Run tests
pytest tests/ --live -m rag
```

### EHR API Returning 401

The Cerner open sandbox requires no auth. Epic may require OAuth:
```bash
# These tests will skip if auth is needed
pytest tests/ --live -m ehr -v
```

---

## Summary

**Option B gives you the best of both worlds:**

1. **Fast Feedback** - Mock tests catch bugs immediately
2. **Real Confidence** - Integration tests verify production behavior
3. **CI/CD Friendly** - Mocks run on every commit, integration on merge
4. **Cost Effective** - Only call paid APIs when needed

**For hospital demos:**
> "We test against real Cerner and Epic sandboxes to ensure FHIR compliance. Our 500+ automated tests run in under a minute on every code change."
