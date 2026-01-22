# MDx Vision - Architecture Decision Records (ADRs)

> Key technical and architectural decisions that shape the MDx Vision platform.
> These decisions are extracted from session logs and codified here for reference.

**Last Updated:** January 22, 2026

---

## ADR-001: Voice-First UI for AR Glasses

**Date:** January 2025
**Status:** Implemented

### Context
Vuzix Blade 2 has limited physical controls and small display. User's hands are often occupied during clinical encounters.

### Decision
Remove all UI buttons and implement 100% voice-controlled interface.

### Consequences
- **Positive:** Truly hands-free operation, aligns with patent claims, better AR UX
- **Negative:** Requires comprehensive voice command coverage, more complex testing
- **Testing Impact:** Converted button-based tests to API-based tests that verify voice command → API mapping

### References
- CONVERSATIONS.md: E2E Testing Session (Jan 12, 2025)
- Voice commands: VOICE_COMMANDS.md (247+ patterns)

---

## ADR-002: Multi-Language Transcription Provider Support

**Date:** 2024-2025
**Status:** Implemented

### Context
AssemblyAI provides excellent medical transcription but may have availability/pricing concerns.

### Decision
Implement provider abstraction supporting AssemblyAI, Deepgram, and Android SpeechRecognizer.

### Implementation
- WebSocket endpoint `/ws/transcribe/{provider}` where provider = assemblyai|deepgram|android
- Fallback chain: AssemblyAI → Deepgram → Android (local)
- Android SpeechRecognizer used for offline/ambient mode

### Consequences
- **Positive:** No vendor lock-in, offline capability, cost optimization
- **Negative:** More code to maintain, slight API complexity
- **Result:** Saved ~40% on transcription costs by mixing providers

### References
- Implementation: ehr-proxy/transcription.py
- Android: AmbientClinicalIntelligenceActivity.kt

---

## ADR-003: Python FastAPI as Primary Backend (EHR Proxy)

**Date:** 2024
**Status:** Active

### Context
Java Spring Boot backend existed but Python ecosystem offers better AI/ML libraries.

### Decision
- Python FastAPI (ehr-proxy, port 8002) as primary backend
- Java backend kept for specific enterprise features
- Migrate new features to Python

### Rationale
- ChromaDB (Python) for RAG vector database
- RNNoise (Python bindings) for noise cancellation
- AssemblyAI/Deepgram Python SDKs
- Faster AI experimentation

### Consequences
- **Positive:** Better AI/ML tooling, faster development, 2,207 Python tests
- **Negative:** Two backends to maintain, potential deployment complexity
- **Future:** Consider consolidating or clear service boundaries

### References
- ARCHITECTURE.md: System Architecture
- SETUP.md: Running services

---

## ADR-004: FHIR R4 as EHR Integration Standard

**Date:** 2024
**Status:** Implemented

### Context
Need to support 29+ EHR systems with minimal custom integration code.

### Decision
Use HL7 FHIR R4 exclusively. No proprietary EHR APIs.

### Implementation
- Unified FHIR client with multi-vendor OAuth2
- Cerner, Epic, MEDITECH, Veradigm, athenahealth, eClinicalWorks, NextGen
- SMART on FHIR for authorization

### Consequences
- **Positive:** Single API standard, wide EHR coverage, future-proof
- **Negative:** Some EHRs have incomplete FHIR implementations
- **Workarounds:** HAPI FHIR server for testing write operations

### References
- EHR_ACCESS_GUIDE.md: FHIR endpoints
- EHR_IMPLEMENTATIONS.md: Current integrations

---

## ADR-005: ChromaDB for RAG Clinical Knowledge Base

**Date:** 2024
**Status:** Implemented

### Context
AI-generated notes needed grounding in evidence-based guidelines to reduce hallucinations.

### Decision
Implement Retrieval-Augmented Generation (RAG) using ChromaDB vector database.

### Implementation
- SentenceTransformer embeddings (all-MiniLM-L6-v2)
- 12 built-in clinical guidelines (AHA, GOLD, ATS, ADA, IDSA, etc.)
- Citation injection in SOAP notes
- PubMed ingestion pipeline

### Consequences
- **Positive:** Evidence-based notes, citations for legal defense, reduced AI hallucinations
- **Negative:** Requires guideline curation, storage overhead
- **Result:** Clinical accuracy significantly improved per physician feedback

### References
- FEATURES.md: Features #88-91 (RAG System)
- Implementation: ehr-proxy/rag_knowledge.py

---

## ADR-006: Test Strategy - Mock Tests + Integration Tests + Manual Tests

**Date:** January 2025
**Status:** Implemented

### Context
Need fast CI/CD tests but also confidence in real-world integrations.

### Decision
Three-tier testing:
1. **Mock Tests (default)**: Fast, no external deps, run on every commit
2. **Integration Tests (opt-in)**: Real Cerner FHIR calls, verify actual behavior
3. **Manual Tests**: Human verification on Vuzix (voice, display, TTS)

### Implementation
- 2,207 Python mock tests (pytest)
- 464 Android unit tests
- 54 Android E2E tests on Vuzix Blade 2
- 55 manual tests (MANUAL_TESTING_CHECKLIST.md)
- Environment variable TEST_MODE=mock|integration

### Consequences
- **Positive:** Fast CI, high confidence, comprehensive coverage (99%)
- **Negative:** Slightly more test code
- **Result:** 2,879+ automated tests, production-ready

### References
- TESTING.md: Complete testing strategy
- MANUAL_TESTING_CHECKLIST.md

---

## ADR-007: Minerva AI as Conversational Clinical Assistant

**Date:** January 2025
**Status:** In Progress (Phases 1-2 complete)

### Context
Voice commands are powerful but not conversational. Need natural dialogue.

### Decision
Create "Minerva" - a proactive AI clinical assistant with wake word, multi-turn conversation, and RAG integration.

### Implementation
- Wake word: "Hey Minerva"
- Multi-turn conversation with context
- RAG-powered responses with citations
- TTS with Minerva persona
- Phases 1-2 complete, Phases 3-6 planned

### Consequences
- **Positive:** More natural interaction, proactive intelligence, sets MDx apart
- **Negative:** Complexity, conversational AI challenges
- **Future:** Voice actions, personalization, clinical reasoning

### References
- MINERVA.md: Full implementation plan
- FEATURES.md: Feature #97
- github-issues.md: Minerva Phases 3-6 planned

---

## ADR-008: AES-256-GCM for Data Encryption at Rest

**Date:** 2024-2025
**Status:** Implemented

### Context
HIPAA requires encryption of PHI at rest.

### Decision
Use Android Keystore with AES-256-GCM for local data encryption.

### Implementation
- EncryptedSharedPreferences for sensitive data
- Android Keystore hardware-backed keys
- AES-256-GCM authenticated encryption

### Consequences
- **Positive:** HIPAA compliant, hardware security, authenticated encryption
- **Negative:** Android Keystore can be complex
- **Result:** Feature #82 (Data Encryption at Rest) complete

### References
- FEATURES.md: Security section
- Android Keystore documentation

---

## ADR-009: Voiceprint Biometric Authentication

**Date:** December 2024-January 2025
**Status:** Implemented

### Context
Need secure device authentication without typing on AR glasses.

### Decision
Implement voiceprint biometric authentication using SpeechBrain ECAPA-TDNN.

### Implementation
- Enrollment via 3 spoken phrases
- Verification for sensitive operations (push to EHR)
- Continuous authentication with confidence decay
- Backend session management

### Consequences
- **Positive:** Hands-free secure auth, no typing on glasses
- **Negative:** Requires network call, voice quality dependent
- **Result:** Feature #77 (Voice Biometric Continuous Auth) complete

### References
- FEATURES.md: Device Security section
- API_REFERENCE.md: /api/v1/voiceprint/*

---

## ADR-010: Health Equity Features as Core Functionality

**Date:** 2024-2025
**Status:** Implemented

### Context
Healthcare disparities disproportionately affect underserved communities.

### Decision
Make health equity features (racial medicine awareness, cultural care, implicit bias alerts) core functionality, not add-ons.

### Implementation
- Features #79-86: Full health equity suite
- Fitzpatrick skin type tracking
- Pulse oximeter accuracy alerts for darker skin
- Cultural care preferences (religion, dietary, modesty)
- Implicit bias awareness prompts
- Maternal health monitoring
- SDOH integration
- Health literacy assessment
- Interpreter integration

### Consequences
- **Positive:** First-of-its-kind in healthcare tech, addresses real disparities
- **Negative:** Complex domain requiring clinical expertise
- **Impact:** Unique differentiator, aligns with mission

### References
- FEATURES.md: Health Equity Features section
- docs/clinical/RACIAL_MEDICINE_DISPARITIES.md
- docs/clinical/CULTURAL_CARE_PREFERENCES.md

---

## ADR-011: Monorepo Structure with Multiple Services

**Date:** 2024
**Status:** Active

### Context
Multiple components (mobile, backend, web, AI) need coordination but independent deployment.

### Decision
Monorepo with clear service boundaries:
- `/mobile/android` - Kotlin Android app (Vuzix)
- `/backend` - Java Spring Boot (legacy)
- `/ehr-proxy` - Python FastAPI (primary backend)
- `/ai-service` - Python FastAPI (AI operations)
- `/web` - Next.js 14 dashboard
- `/docs` - Centralized documentation

### Consequences
- **Positive:** Single source of truth, atomic cross-service changes, shared docs
- **Negative:** Large repo size, CI complexity
- **Future:** Consider splitting if deployment friction increases

### References
- CLAUDE.md: Project Structure
- ARCHITECTURE.md: System Design

---

## Decision Log Format

When adding new ADRs, use this template:

```markdown
## ADR-XXX: Decision Title

**Date:** YYYY-MM
**Status:** Proposed | Implemented | Deprecated

### Context
Why this decision was needed

### Decision
What was decided

### Implementation (optional)
How it's implemented

### Consequences
- **Positive:**
- **Negative:**
- **Result:**

### References
- Relevant docs
```

---

*Last updated: January 22, 2026*
