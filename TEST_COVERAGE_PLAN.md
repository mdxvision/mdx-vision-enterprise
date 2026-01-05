# MDx Vision Enterprise - Test Coverage Plan

> **Created:** 2025-01-05
> **Status:** In Progress
> **Goal:** Comprehensive test coverage across all components

---

## Overview

This document tracks the implementation of comprehensive test coverage for the MDx Vision Enterprise platform. Tests are organized by component with clear status tracking.

---

## Test Status Legend

- [ ] Not started
- [x] Completed
- [~] In progress

---

## 1. Backend (Java Spring Boot)

**Location:** `/backend/src/test/java/com/mdxvision/`
**Framework:** JUnit 5 + Spring Boot Test + Mockito

### Unit Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `fhir/UnifiedEhrServiceTest.java` | [ ] | Multi-EHR service abstraction |
| `fhir/CernerFhirServiceTest.java` | [ ] | Cerner FHIR R4 client |
| `fhir/EpicFhirServiceTest.java` | [ ] | Epic FHIR R4 client |
| `fhir/VeradigmFhirServiceTest.java` | [ ] | Veradigm FHIR R4 client |
| `service/SessionServiceTest.java` | [ ] | Recording session management |
| `service/AuditServiceTest.java` | [ ] | HIPAA audit logging |
| `service/AiPipelineServiceTest.java` | [ ] | AI pipeline integration |

### Controller Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `controller/SessionControllerTest.java` | [ ] | Session REST endpoints |
| `controller/PatientControllerTest.java` | [ ] | Patient REST endpoints |
| `controller/EncounterControllerTest.java` | [ ] | Encounter REST endpoints |

### Integration Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `integration/FhirIntegrationTest.java` | [ ] | End-to-end FHIR workflow |

---

## 2. EHR Proxy (Python FastAPI)

**Location:** `/ehr-proxy/tests/`
**Framework:** pytest + pytest-asyncio + httpx

### Authentication Tests (Security Critical)

| Test File | Status | Description |
|-----------|--------|-------------|
| `test_auth.py` | [ ] | Device authentication, TOTP, pairing |
| `test_voiceprint.py` | [ ] | Voiceprint enrollment & verification |

### Clinical Safety Tests (Patient Safety Critical)

| Test File | Status | Description |
|-----------|--------|-------------|
| `test_clinical_safety.py` | [ ] | Critical alerts, medication interactions |
| `test_racial_medicine.py` | [ ] | Racial disparity awareness (Feature #79) |
| `test_maternal_health.py` | [ ] | Maternal health monitoring (Feature #82) |
| `test_implicit_bias.py` | [ ] | Implicit bias alerts (Feature #81) |

### Health Equity Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `test_cultural_care.py` | [ ] | Cultural/religious preferences (Feature #80) |
| `test_sdoh.py` | [ ] | Social determinants (Feature #84) |
| `test_literacy.py` | [ ] | Health literacy assessment (Feature #85) |
| `test_interpreter.py` | [ ] | Interpreter integration (Feature #86) |

### AI/ML Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `test_copilot.py` | [ ] | AI Clinical Co-pilot (Feature #78) |
| `test_rag.py` | [ ] | RAG knowledge system (Feature #88) |
| `test_knowledge.py` | [ ] | Knowledge management (Feature #89) |
| `test_updates.py` | [ ] | Scheduled RAG updates (Feature #90) |

---

## 3. Web Dashboard (Next.js/React)

**Location:** `/web/src/__tests__/`
**Framework:** Vitest + React Testing Library

### Setup Required

| Task | Status | Description |
|------|--------|-------------|
| Install Vitest | [ ] | Testing framework |
| Install React Testing Library | [ ] | Component testing |
| Configure vitest.config.ts | [ ] | Test configuration |
| Add test scripts to package.json | [ ] | npm test commands |

### Page Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `app/login/page.test.tsx` | [ ] | Authentication flow |
| `app/dashboard/page.test.tsx` | [ ] | Main dashboard |
| `app/dashboard/settings/page.test.tsx` | [ ] | Settings including Health Equity |
| `app/dashboard/billing/page.test.tsx` | [ ] | Billing claims |
| `app/dashboard/devices/page.test.tsx` | [ ] | Device management |
| `app/dashboard/knowledge/page.test.tsx` | [ ] | RAG knowledge UI |
| `app/dashboard/audit/page.test.tsx` | [ ] | Audit log viewer |

### Component Tests

| Test File | Status | Description |
|-----------|--------|-------------|
| `components/Header.test.tsx` | [ ] | Header component |
| `components/Sidebar.test.tsx` | [ ] | Navigation sidebar |

---

## 4. Android Mobile App (Kotlin)

**Location:** `/mobile/android/app/src/test/java/com/mdxvision/`
**Framework:** JUnit 4 + Mockito + Robolectric

### Existing Tests (Already Implemented)

| Test File | Status | Description |
|-----------|--------|-------------|
| `HeadGestureDetectorTest.kt` | [x] | Gesture recognition (45 tests) |
| `VuzixHudTest.kt` | [x] | HUD state management |

### New Tests Needed

| Test File | Status | Description |
|-----------|--------|-------------|
| `MainActivityTest.kt` | [ ] | Voice commands, wake word |
| `AudioStreamingServiceTest.kt` | [ ] | WebSocket audio streaming |
| `BarcodeScannerActivityTest.kt` | [ ] | ML Kit barcode scanning |
| `QrPairingActivityTest.kt` | [ ] | Device pairing workflow |
| `ImageCaptureActivityTest.kt` | [ ] | Medical image capture |
| `EncryptedStorageTest.kt` | [ ] | Data encryption at rest |

---

## 5. AI Service (Python)

**Location:** `/ai-service/tests/`
**Framework:** pytest + pytest-asyncio

### Tests Needed

| Test File | Status | Description |
|-----------|--------|-------------|
| `test_transcription_service.py` | [ ] | AssemblyAI integration |
| `test_notes_service.py` | [ ] | SOAP note generation |
| `test_drug_interaction.py` | [ ] | Drug interaction checking |
| `test_clinical_nlp.py` | [ ] | Clinical NLP entity extraction |
| `test_translation.py` | [ ] | Multi-language translation |

---

## 6. Ray-Ban Companion App

**Location:** `/mobile/rayban-companion/app/src/test/`
**Framework:** JUnit 4 + Mockito

### Tests Needed

| Test File | Status | Description |
|-----------|--------|-------------|
| `MainActivityTest.kt` | [ ] | Companion app main flow |
| `GlassesConnectionTest.kt` | [ ] | Meta glasses connection |

---

## Priority Order

### Phase 1: Security & Authentication (High Priority)
1. `test_auth.py` - Device authentication endpoints
2. `test_voiceprint.py` - Biometric voice auth
3. Backend `AuditServiceTest.java` - HIPAA compliance

### Phase 2: Clinical Safety (Critical)
4. `test_clinical_safety.py` - Medication interactions, critical alerts
5. `test_maternal_health.py` - OB safety monitoring
6. `test_racial_medicine.py` - Disparity awareness

### Phase 3: Core Functionality
7. Backend FHIR tests - Multi-EHR integration
8. Web setup + login test
9. Android MainActivity tests

### Phase 4: Health Equity Features
10. `test_cultural_care.py`
11. `test_sdoh.py`
12. `test_literacy.py`
13. `test_interpreter.py`
14. `test_implicit_bias.py`

### Phase 5: AI/ML Features
15. `test_copilot.py`
16. `test_rag.py`
17. AI Service tests

---

## Test Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| Backend (Java) | 0% | 70% |
| EHR Proxy (Python) | ~40% | 80% |
| Web (Next.js) | 0% | 60% |
| Android (Kotlin) | ~15% | 50% |
| AI Service (Python) | 0% | 60% |

---

## Running Tests

### Backend
```bash
cd backend
./mvnw test
```

### EHR Proxy
```bash
cd ehr-proxy
pytest -v
```

### Web Dashboard
```bash
cd web
npm test
```

### Android
```bash
cd mobile/android
./gradlew test
```

### AI Service
```bash
cd ai-service
pytest -v
```

---

## CI/CD Integration

Future enhancement: Add GitHub Actions workflow for automated testing on PR.

```yaml
# .github/workflows/test.yml (to be created)
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Backend Tests
        run: cd backend && ./mvnw test
      - name: Run EHR Proxy Tests
        run: cd ehr-proxy && pip install -r requirements.txt && pytest
      - name: Run Web Tests
        run: cd web && npm ci && npm test
```

---

## Notes

- All tests should mock external dependencies (EHR sandboxes, AI APIs)
- HIPAA compliance: Never log real PHI in test output
- Use test fixtures for consistent test data
- Critical safety tests should include edge cases

---

*Last updated: 2025-01-05*
