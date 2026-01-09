# MDx Vision Enterprise - Conversation Log

> This file is continuously updated with session history, key decisions, and progress.
> **Session naming convention:** Use descriptive names for easy reference.

---

## Active Session: Minerva AI Assistant & EHR Completion (Jan 9, 2025)

**Started:** 2025-01-09
**Focus:** Minerva AI clinical assistant, Epic/Cerner EHR completion, token persistence

### Session Summary
- **Epic OAuth WORKING**: Full OAuth2 flow with token persistence
- **Cerner FHIR WORKING**: Live sandbox connection
- **EHR Voice Switching**: "Switch to Epic" / "Switch to Cerner" commands
- **Token Persistence**: OAuth tokens persist across proxy restarts (.ehr_tokens.json)
- **TTS Sanitization**: Fixed readback of JSON artifacts ("curly bracket" etc.)
- **Minerva AI Planning**: Created MINERVA.md implementation plan

### EHR Integration Status (Updated)
| Platform | Status | Notes |
|----------|--------|-------|
| **Cerner/Oracle** | **WORKING** | SMARTS SR., NANCYS II |
| **Epic** | **WORKING** | Camila Maria Lopez (FHIRTWO/EpicFhir11!) |
| **Veradigm** | Ready | Awaiting approval |
| **athenahealth** | Ready | OAuth configured |
| **NextGen** | Ready | OAuth configured |
| **MEDITECH** | Ready | OAuth configured |
| **eClinicalWorks** | Ready | OAuth configured |

### Token Persistence Implementation
- Added `save_tokens()` and `load_tokens()` functions
- Tokens saved to `ehr-proxy/.ehr_tokens.json`
- Auto-loads on proxy startup
- Saves after every OAuth callback (all 6 EHRs)
- Demo-ready: no re-login needed after restart

### Minerva AI Clinical Assistant (Feature #97)
> Named in honor of Minerva Diaz

Created `MINERVA.md` with:
- Full architecture diagram
- 6-phase implementation checklist
- API endpoint specifications
- Voice command definitions
- RAG integration plan for hallucination prevention
- Persona and speech patterns
- Security and compliance considerations

**Key Minerva Features:**
- "Hey Minerva" wake word activation
- RAG-grounded responses (citations from AHA, ADA, USPSTF)
- Multi-turn conversation with patient context
- Clinical reasoning modes (differential, teaching, challenge, clarify)
- Proactive alerts and briefings

### Files Created/Updated
- **Created**: `MINERVA.md` - Full implementation plan
- **Updated**: `CLAUDE.md` - Added Feature #97, updated Next Up section
- **Updated**: `FEATURES.md` - Added Minerva checklist, updated EHR status
- **Updated**: `README.md` - Jan 2025 status, 7 EHRs listed
- **Updated**: `ehr-proxy/main.py` - Token persistence, save_tokens() calls
- **Updated**: `MainActivity.kt` - EHR switching, TTS sanitization

### Git Commits
1. `feat: EHR switching + token persistence for demos`
2. `docs: update README with 7 EHR integrations and Jan 2025 status`

---

## Previous Session: C-Suite Demo & EHR Integration (Jan 4, 2025)

**Started:** 2025-01-04
**Focus:** C-suite hospital demo creation, EHR integration research, expanded TTS features

### Session Summary
- **Server-side TTS expanded**: All 7 TTS speak functions now use server fallback for Vuzix
- **C-Suite Demo Guide**: Created comprehensive DEMO_CSUITE.md (575 lines) for hospital presentations
- **Competitor Research**: DAX ($600/mo), Augmedix ($2,000/mo), Suki ($299-399/mo) - no AR, no equity
- **EHR Integration Research**: Researched access for 7 EHR platforms
- **Cerner Registration**: Guided user through Oracle Health Code Console registration
- **Feature Audit**: 8.5/10 demo-ready score with identified gaps

### Server-Side TTS Expansion
Updated 7 speak* functions to use server TTS fallback (Vuzix has no local TTS engines):
1. `speakFeedback()` - General action confirmations
2. `speakAllergyWarnings()` - Critical allergy alerts
3. `speakCriticalLabAlerts()` - Dangerous lab values
4. `speakLabTrends()` - Lab trend changes
5. `speakVitalTrends()` - Vital sign trends
6. `speakCriticalVitalAlerts()` - Dangerous vital values
7. `speakMedicationInteractions()` - Drug-drug interactions

### C-Suite Demo Guide Created
`DEMO_CSUITE.md` includes:
- Executive summary with competitor pricing comparison
- Feature readiness audit (8.5/10 score)
- 3 demo scripts: 5-minute, 15-minute, 30-minute deep dive
- Competitor analysis (DAX, Augmedix, Suki)
- Objection handling responses
- Technical setup checklist
- Fallback plans for demo failures

### EHR Integration Research Summary
| Platform | Access | Cost | Notes |
|----------|--------|------|-------|
| **Cerner/Oracle** | READY | $0 | Client ID: `0fab9b20-adc8-4940-bbf6-82034d1d39ab` |
| **Epic** | Pending | TBD | User has credentials |
| **Veradigm** | Pending | $99/mo | User has credentials |
| **athenahealth** | FREE | $0 | Self-service sandbox |
| **eClinicalWorks** | FREE | $0 | FHIR APIs available |
| **NextGen** | FREE | $0 | Developer program |
| **MEDITECH** | FREE | $0 | Greenfield Workspace |

**Total platforms researched:** 29 (see EHR_ACCESS_GUIDE.md)

### Cerner Registration Guidance
Provided recommendations for Oracle Health Code Console form:
- Application Type: Provider
- Type of Access: Offline
- Application Privacy: Confidential
- SMART Version: v2
- Intended Users: Clinical Team, Healthcare Administrator
- Intended Purposes: Clinical Tools, Administrative Tasks, Patient-Provider Communication
- Recommended APIs: Oracle Health EHR APIs + FHIR R4 APIs

### Commits This Session
| Commit | Description |
|--------|-------------|
| TBD | Extended server TTS to all voice features |
| TBD | Create C-suite demo guide |

---

## Previous Session: Vuzix Microphone & Ambient Mode Fix (Jan 4, 2025)

**Focus:** Fixing Vuzix Blade 2 microphone sensitivity, ambient mode, UI visibility, and crash fixes

### Session Summary
- **Diagnosed root cause**: Vuzix Blade 2 microphone outputs audio ~40dB too quiet
- **Added audio level logging**: RMS, max sample, dB metrics every 2 seconds for diagnostics
- **Changed audio source**: Use `VOICE_RECOGNITION` instead of `MIC` for Vuzix (enables AGC/noise suppression)
- **Added 10x software gain boost**: Amplifies Vuzix audio before sending to AssemblyAI
- **Fixed ambient mode command matching**: Added "starts ambient" pattern (transcription adds 's')
- **Fixed save note UI**: Changed from dark theme to light theme for AR visibility
- **Fixed JSONException crash**: Conditions array can contain strings OR JSONObjects - added handlers for both
- **Result**: Voice commands, ambient mode working; save note UI needs further refinement

### Technical Details
| Issue | Root Cause | Fix |
|-------|-----------|-----|
| No transcription | Mic level RMS=2, dB=-84 (silence) | 10x gain boost |
| Voice commands fail | Audio too quiet for speech recognition | VOICE_RECOGNITION audio source |
| Ambient mode not matching | Transcription says "starts ambient" not "start ambient" | Added "starts ambient" pattern |
| Save note UI too dark | Dark background on AR display | Light theme (#F8FAFC background, dark text) |
| Crash during ambient | conditions.getJSONObject() on string array | Try-catch in 7 locations |

### Fixes Applied
| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Brief me not speaking | speak() called after showQuickPatientSummary() which could crash | Call speak() FIRST, wrap visual display in try-catch |
| Save note allergies display | allergies.optString(i) fails on JSONObjects | Try-catch to extract name field from JSONObject or fall back to string |
| Save note PMH/conditions | conditions.optString(i) fails on JSONObjects | Same pattern - extract name from JSONObject or string |
| Plan section | Entity extraction from ambient transcript | Reviewed plan triggers - working as expected |
| **TTS "Speech not available"** | Vuzix has no local TTS engines (PicoTTS not functioning) | Server-side TTS via gTTS with base64 MP3 streaming |

### Server-Side TTS Solution
Vuzix Blade 2 has no working TTS engines despite PicoTTS being installed. Solution:
1. Added `/api/v1/tts/speak` endpoint to EHR proxy using gTTS (Google Text-to-Speech)
2. Android app falls back to server TTS when `isTtsReady = false`
3. Server returns base64-encoded MP3 audio
4. Android plays via MediaPlayer
5. **Result**: "Brief me" now speaks patient summary on Vuzix!

### Audio Level Diagnostics Added
```
🎤 Audio level: RMS=38, Max=150, dB=-58.7, chunks=491  (with speech)
🎤 Audio level: RMS=2, Max=8, dB=-84.3, chunks=260    (silence)
```

### Commits This Session
| Commit | Description |
|--------|-------------|
| a4e4164 | Add server-side TTS for Vuzix glasses (gTTS fallback) |
| 40cfd8b | Fix Brief me TTS and add robust JSON array handling |
| fc18b60 | Fix allergies and conditions display in save note UI |
| cd75eeb | Fix JSONException crash in conditions array parsing (7 locations) |
| 04a6ff5 | Update session log with ambient mode and UI fixes |
| 4c46157 | Fix save note UI for AR glasses visibility |
| 485cb22 | Fix ambient mode command matching for transcription variations |
| 6354a53 | Update session log: Vuzix Microphone Sensitivity Fix |
| c5b47b6 | Fix Vuzix microphone low sensitivity for voice recognition |

---

## Previous Session: Vuzix Blade 2 Voice Commands & Testing (Jan 4, 2025)

**Focus:** Vuzix glasses testing, voice command fixes, ambient mode

### Session Summary
- Fixed help command matching (uses `contains("help")` instead of exact match)
- Fixed ambient mode for Vuzix (uses WebSocket fallback, no Google Speech)
- Simplified Vuzix UI (hidden button grid, voice-first interface)
- Fixed "Brief me" crash (JSONException when conditions array contains strings)
- Fixed vitals command (accepts "vital" singular in addition to "vitals")
- Added "add med [name]" voice command to add medications directly to note
- Fixed order/prescribe commands (use `contains()` instead of `startsWith()`)
- Installed ADB via Homebrew for glasses deployment
- Tested voice recognition on Vuzix Blade 2 with AssemblyAI transcription

### Commits This Session
| Commit | Description |
|--------|-------------|
| 32b59bc | Update session log |
| 166e10c | Add medication to note and fix order command matching |
| e699db7 | Fix vitals command and Brief me crash |
| 58d6d93 | Fix Vuzix UX: help command, ambient mode, simplified UI |

---

## Previous Session: MDx Vision Enterprise (Jan 3, 2025)

**Focus:** Maintenance, documentation sync, continued development

### Session Summary
- Pushed 5 pending commits to origin/main
- Updated CLAUDE.md date to Jan 2025
- Created CONVERSATIONS.md for session tracking
- Synced all documentation files

---

## Project Status Overview

### Current State (January 2025)
| Metric | Value |
|--------|-------|
| **Features Implemented** | 91 |
| **Tests Passing** | 194 |
| **Test Coverage** | 100% |
| **Git Status** | Up to date with origin/main |

### Technology Stack
| Component | Technology | Port |
|-----------|------------|------|
| EHR Proxy | Python FastAPI | 8002 |
| Web Dashboard | Next.js 14 | 5173 |
| Android App | Kotlin + Vuzix SDK | - |
| Backend (Legacy) | Java Spring Boot | 8080 |

---

## Feature Development History

### December 2024 - January 2025

#### RAG Clinical Knowledge System (Features #88-91)
| Feature | Description | Status |
|---------|-------------|--------|
| #88 | RAG Clinical Knowledge System - ChromaDB + 12 built-in guidelines | Complete |
| #89 | RAG Knowledge Management - Versioning, PubMed ingestion, feedback | Complete |
| #90 | Scheduled RAG Updates - Automated updates with review checklists | Complete |
| #91 | Knowledge Updates Dashboard - Web UI at /dashboard/knowledge | Complete |

#### Health Equity Features (Features #79-87)
| Feature | Description | Status |
|---------|-------------|--------|
| #79 | Racial Medicine Awareness - Fitzpatrick skin type, pulse ox alerts | Complete |
| #80 | Cultural Care Preferences - Religious/dietary/modesty preferences | Complete |
| #81 | Implicit Bias Alerts - Evidence-based reminders during documentation | Complete |
| #82 | Maternal Health Monitoring - High-risk OB alerts, 3-4x mortality awareness | Complete |
| #83 | Web Dashboard Equity UI - Settings page for equity preferences | Complete |
| #84 | SDOH Integration - Social determinants screening, Z-codes | Complete |
| #85 | Health Literacy Assessment - Plain language, teach-back checklists | Complete |
| #86 | Interpreter Integration - 16 languages, Title VI compliance | Complete |
| #87 | Ray-Ban Meta Companion App - Phone companion for Meta glasses | Complete |

#### Device & Security Features (Features #73-78)
| Feature | Description | Status |
|---------|-------------|--------|
| #73 | Vuzix HUD Native Overlay - Always-on patient info for Blade 2 | Complete |
| #74 | Audit Log Viewer Dashboard - Web UI at /dashboard/audit | Complete |
| #75 | Gesture Control - Nod/shake for Vuzix glasses | Complete |
| #76 | Wink Gesture (Micro-Tilt) - Quick head dip for rapid selection | Complete |
| #77 | Voice Biometric Continuous Auth - Periodic re-verification | Complete |
| #78 | AI Clinical Co-pilot - Interactive AI dialogue during documentation | Complete |

#### Billing & Revenue Cycle (Features #71-72)
| Feature | Description | Status |
|---------|-------------|--------|
| #71 | Billing/Coding Submission - Create claims from clinical notes | Complete |
| #72 | DNFB (Discharged Not Final Billed) - Revenue cycle management | Complete |

---

## Key Decisions Made

### Architecture
1. **Primary Backend**: Python FastAPI (ehr-proxy) - handles all AR glasses communication
2. **Legacy Java Backend**: Minimal use, most logic migrated to Python
3. **Database**: PostgreSQL planned, currently using in-memory/file storage
4. **Transcription**: Dual provider support (AssemblyAI + Deepgram)

### Security & Compliance
1. **HIPAA Audit Logging**: JSON-structured logs for all PHI access
2. **Encryption**: AES-256-GCM via Android Keystore
3. **Authentication**: TOTP + Voiceprint biometric
4. **Session Management**: 12-hour tokens with proximity auto-lock

### Health Equity (Differentiator)
1. **First-of-its-kind**: Racial medicine awareness not in any commercial EHR
2. **Evidence-based**: All bias alerts include research citations
3. **Actionable**: Specific clinical guidance, not just warnings

---

## Files Reference

### Documentation
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Development context for Claude Code |
| `FEATURES.md` | Complete 91-feature checklist |
| `CONVERSATIONS.md` | This file - session history |
| `STRATEGIC_ROADMAP.md` | Product and business roadmap |
| `VOICE_COMMANDS.md` | All 100+ voice commands |
| `SALES_MATERIALS.md` | Index of investor/hospital decks |

### Research Documents
| File | Purpose |
|------|---------|
| `RACIAL_MEDICINE_DISPARITIES.md` | Research on racial disparities in medicine |
| `CULTURAL_CARE_PREFERENCES.md` | Religious/cultural care preferences research |

### Key Code Files
| File | Purpose |
|------|---------|
| `ehr-proxy/main.py` | Core API (434KB) - SOAP notes, ICD-10/CPT, transcription |
| `ehr-proxy/rag.py` | RAG clinical knowledge system |
| `ehr-proxy/auth.py` | Multi-EHR auth + voiceprint verification |
| `mobile/android/app/src/main/java/com/mdxvision/MainActivity.kt` | Android main activity |
| `web/src/app/dashboard/knowledge/page.tsx` | Knowledge Updates Dashboard |

---

## API Endpoints Quick Reference

### Patient Data
```
GET  /api/v1/patient/{id}
GET  /api/v1/patient/search?name=
GET  /api/v1/patient/mrn/{mrn}
```

### Clinical Notes
```
POST /api/v1/notes/generate        # SOAP note generation
POST /api/v1/notes/quick           # AR display optimization
POST /api/v1/notes/save
```

### Transcription
```
WS   /ws/transcribe                # Real-time streaming
WS   /ws/transcribe/{provider}     # Specific provider
GET  /api/v1/transcription/status
```

### Health Equity
```
GET  /api/v1/racial-medicine/alerts
GET  /api/v1/cultural-care/preferences/{patient_id}
GET  /api/v1/sdoh/screen
GET  /api/v1/literacy/assess
GET  /api/v1/interpreter/languages
```

### RAG Knowledge Base
```
GET  /api/v1/rag/status
POST /api/v1/rag/initialize
POST /api/v1/rag/query
GET  /api/v1/updates/dashboard
GET  /api/v1/updates/pending
```

---

## Test Data

### Cerner Sandbox Patient
- **Patient ID**: 12724066
- **Name**: SMARTS SR., NANCYS II
- **DOB**: 1990-09-15

### Test Commands
```bash
# Get patient
curl http://localhost:8002/api/v1/patient/12724066

# Generate SOAP note
curl -X POST http://localhost:8002/api/v1/notes/quick \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Patient has headache and fever", "chief_complaint": "Headache"}'

# Check transcription status
curl http://localhost:8002/api/v1/transcription/status

# RAG status
curl http://localhost:8002/api/v1/rag/status
```

---

## Run Commands

### Start Services
```bash
# EHR Proxy (main backend)
cd ehr-proxy && python main.py

# Web Dashboard
cd web && npm run dev

# Android Build
cd mobile/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
./gradlew assembleDebug
```

### Install APK
```bash
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.mdxvision.glasses/com.mdxvision.MainActivity
```

---

## Next Steps (Backlog)

### EHR Integration (Active - Jan 4, 2025)
- [x] Cerner/Oracle - Code Console registration COMPLETE
- [ ] Cerner - Receive Client ID and configure integration
- [ ] Epic - Receive credentials from user and configure
- [ ] Veradigm - Configure Silver plan credentials

### Free EHR Sandboxes Available
See `EHR_ACCESS_GUIDE.md` for complete details:
- athenahealth - FREE self-service
- eClinicalWorks - FREE FHIR APIs
- NextGen - FREE developer program
- MEDITECH - FREE Greenfield Workspace

### Production Readiness
- [ ] HIPAA compliance documentation
- [ ] SOC 2 Type II audit
- [ ] Cloud deployment (AWS/GCP/Azure with HIPAA BAA)

### Hardware
- [x] Vuzix Blade 2 physical device testing (completed Jan 4, 2025 - mic sensitivity fix)
- [ ] Ray-Ban Meta glasses validation
- [ ] Magic Leap 2 support

### AI Improvements
- [ ] Custom medical LLM fine-tuning
- [ ] Hospital-specific RAG content

---

## Git Commits (Recent)

| Commit | Date | Description |
|--------|------|-------------|
| 4c46157 | Jan 4, 2025 | Fix save note UI for AR glasses visibility |
| 485cb22 | Jan 4, 2025 | Fix ambient mode command matching for transcription variations |
| 6354a53 | Jan 4, 2025 | Update session log: Vuzix Microphone Sensitivity Fix |
| c5b47b6 | Jan 4, 2025 | Fix Vuzix microphone low sensitivity for voice recognition |
| 32b59bc | Jan 4, 2025 | Update session log |
| 166e10c | Jan 4, 2025 | Add medication to note and fix order command matching |
| e699db7 | Jan 4, 2025 | Fix vitals command and Brief me crash |
| 58d6d93 | Jan 4, 2025 | Fix Vuzix UX: help command, ambient mode, simplified UI |

---

*Last updated: 2025-01-04*
