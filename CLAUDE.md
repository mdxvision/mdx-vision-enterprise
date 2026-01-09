# CLAUDE.md - MDx Vision Development Context

This file provides context for Claude Code when working on this project.

## Project Overview

MDx Vision is an AR smart glasses platform for healthcare documentation. It implements **US Patent 15/237,980** - voice-activated AR glasses that connect to EHR systems.

**Key Features:**
- Voice-activated patient lookup from EHR
- Wake word detection ("Hey MDx")
- Real-time transcription via AssemblyAI/Deepgram
- AI-powered SOAP note generation
- ICD-10 code suggestions from conversation
- Barcode scanning for patient wristbands

## Key Directories

```
/backend                    # Java Spring Boot + HAPI FHIR
/ai-service                 # Python AI pipeline (transcription + notes)
/ehr-proxy                  # Python FastAPI proxy for AR glasses
/mobile/android             # Native Android app (Vuzix Blade 2)
/web                        # Next.js admin dashboard
```

## Session History

See [CONVERSATIONS.md](CONVERSATIONS.md) for session history, decisions, and progress tracking.

## Sales & Marketing Materials

See [SALES_MATERIALS.md](SALES_MATERIALS.md) for complete index.

### Investor Decks
| File | Description |
|------|-------------|
| `web/public/investor-deck.html` | Dark theme (11 slides) |
| `web/public/investor-deck-light.html` | Light theme (11 slides) |

### Hospital Sales Decks
| File | Description |
|------|-------------|
| `web/public/hospital-sales-deck.html` | US market (English) |
| `web/public/hospital-sales-deck-russia.html` | Russia market (Russian) |

### One-Sheets & Capability Statements
| File | Description |
|------|-------------|
| `web/public/onesheet.html` | Single-page overview (printable) |
| `web/public/capability-statement.html` | Enterprise/government procurement |

### Strategic Documents
| File | Description |
|------|-------------|
| `MDX_GLASSES_PRD.md` | Proprietary hardware PRD |
| `STRATEGIC_ROADMAP.md` | Product and business roadmap |
| `GAP_CLOSURE_PLAN.md` | Competitive gap analysis |
| `INTERNAL_COMPETITIVE_ANALYSIS.md` | Competitor analysis |
| `INTERNATIONAL_EHR_EXPANSION.md` | International expansion strategy |
| `PRICING.md` | **Pricing strategy, Redox costs, ROI calculations** |
| `INVESTOR.md` | **Investor deck content, market size, path to $100M ARR** |

### EHR Integration Documents
| File | Description |
|------|-------------|
| `EHR_IMPLEMENTATIONS.md` | Implementation status for all EHRs |
| `EHR_ACCESS_GUIDE.md` | Detailed EHR registration instructions |
| `EHR_AMBULATORY_RESEARCH.md` | DrChrono, Practice Fusion, CPSI research |
| `EHR_AGGREGATOR_PLATFORMS.md` | Redox, Particle Health, Health Gorilla research |

### How to View HTML Decks
```bash
# Quick open in Chrome
open -a "Google Chrome" web/public/investor-deck.html

# Or via local server
cd web && npm run dev  # Then visit http://localhost:5173/[filename].html
```

## Current Development Focus

### Working Components
- **Android App**: Native Kotlin app with voice recognition, patient lookup, live transcription
- **Cerner Integration**: Live FHIR R4 sandbox connection
- **EHR Proxy**: FastAPI service bridging AR glasses to EHR
- **Real-time Transcription**: AssemblyAI/Deepgram WebSocket streaming
- **SOAP Note Generation**: AI-powered clinical documentation with ICD-10 codes
- **Web Dashboard**: Next.js 14 running on port 5173

### Voice Commands (12 buttons)
| Command | Action |
|---------|--------|
| HEY MDX MODE | Toggle wake word listening |
| LOAD PATIENT | Load test patient |
| FIND PATIENT | Search by name |
| SCAN WRISTBAND | Barcode scanner |
| SHOW VITALS | Display vitals |
| SHOW ALLERGIES | Display allergies |
| SHOW MEDS | Display medications |
| SHOW LABS | Display lab results |
| SHOW PROCEDURES | Display procedures |
| START NOTE | Begin documentation mode |
| LIVE TRANSCRIBE | Real-time transcription |
| (Immunizations) | "Show immunizations" voice command |

## Development Commands

### Android Build
```bash
cd mobile/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
./gradlew assembleDebug
```

### EHR Proxy with Transcription
```bash
cd ehr-proxy
ASSEMBLYAI_API_KEY=your_key python main.py  # Port 8002

# Or with Deepgram
TRANSCRIPTION_PROVIDER=deepgram DEEPGRAM_API_KEY=your_key python main.py
```

### Web Dashboard
```bash
cd web
npm run dev  # Runs on port 5173
```

### Android Emulator
```bash
# ADB path on this machine
/opt/homebrew/share/android-commandlinetools/platform-tools/adb

# Install APK
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk

# Launch app
adb shell am start -n com.mdxvision.glasses/com.mdxvision.MainActivity
```

## Testing

### Test Coverage Overview

| Component | Framework | Test Count | Key Coverage Areas |
|-----------|-----------|------------|-------------------|
| Backend (Java) | JUnit 5, Spring Boot Test, Mockito | 4 files | EHR services, sessions, audit logging |
| EHR Proxy (Python) | pytest, pytest-asyncio | 18+ files | Auth, safety, health equity, RAG |
| Web Dashboard | Vitest, React Testing Library | 6 files | Login, dashboard, settings, billing |
| Android App | JUnit 4, Mockito | 3 files | Voice commands, audio, barcode |
| AI Service | pytest | 3 files | Transcription, notes, drug interactions |

### Running Tests

```bash
# Backend (Java)
cd backend
./mvnw test

# EHR Proxy (Python)
cd ehr-proxy
pytest tests/ -v

# Web Dashboard
cd web
npm test           # Watch mode
npm run test:run   # Single run
npm run test:coverage  # With coverage

# Android
cd mobile/android
./gradlew test

# AI Service
cd ai-service
pytest tests/ -v
```

### Test File Locations

```
backend/src/test/java/com/mdxvision/
├── fhir/
│   ├── UnifiedEhrServiceTest.java    # Multi-EHR abstraction
│   └── CernerFhirServiceTest.java    # Cerner FHIR client
├── controller/
│   └── SessionControllerTest.java    # REST endpoints
└── service/
    └── AuditServiceTest.java         # HIPAA audit logging

ehr-proxy/tests/
├── test_auth.py              # Device authentication (Feature #64)
├── test_voiceprint.py        # Biometric auth (Features #66, #77)
├── test_clinical_safety.py   # Critical alerts, drug interactions
├── test_racial_medicine.py   # Health equity (Feature #79)
├── test_maternal_health.py   # OB monitoring (Feature #82)
├── test_cultural_care.py     # Religious/cultural preferences
├── test_sdoh.py              # Social determinants (Feature #84)
├── test_copilot.py           # AI Clinical Co-pilot (Feature #78)
├── test_literacy.py          # Health literacy (Feature #85)
├── test_interpreter.py       # Interpreter integration (Feature #86)
└── test_rag.py               # RAG knowledge system (Features #88-90)

web/src/__tests__/
├── setup.ts                  # Test configuration
├── login.test.tsx            # Authentication
├── dashboard.test.tsx        # Main dashboard
├── settings.test.tsx         # Settings + Health Equity
├── billing.test.tsx          # Billing/coding (Feature #71)
└── devices.test.tsx          # Device management (Feature #65)

mobile/android/app/src/test/java/com/mdxvision/
├── MainActivityTest.kt       # Voice commands, wake word
├── AudioStreamingServiceTest.kt  # Audio processing, Vuzix
└── BarcodeScannerActivityTest.kt # MRN extraction, validation

ai-service/tests/
├── conftest.py               # Test fixtures
├── test_transcription_service.py  # Real-time transcription
├── test_notes_service.py     # SOAP note generation
└── test_drug_interaction.py  # Drug interaction checking
```

### Test Patterns

**Backend Java**: Uses `@MockBean` and `@WebMvcTest` for Spring Boot testing
```java
@WebMvcTest(SessionController.class)
class SessionControllerTest {
    @MockBean private SessionService sessionService;
    @Autowired private MockMvc mockMvc;
}
```

**EHR Proxy Python**: Uses pytest fixtures and `httpx.AsyncClient`
```python
@pytest.fixture
def client():
    return TestClient(app)

def test_device_auth(client):
    response = client.post("/api/v1/auth/device", json={"device_id": "test"})
    assert response.status_code == 200
```

**Web Dashboard**: Uses Vitest with React Testing Library
```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

describe('Dashboard', () => {
  it('should render', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('dashboard')).toBeInTheDocument()
  })
})
```

**Android Kotlin**: Uses JUnit 4 with nested test classes
```kotlin
@RunWith(MockitoJUnitRunner::class)
class MainActivityTest {
    class VoiceCommandTests {
        @Test
        fun `should recognize LOAD PATIENT command`() { ... }
    }
}
```

## Key Files

### Android App
- `MainActivity.kt` - Main activity with voice recognition, wake word, live transcription
- `AudioStreamingService.kt` - WebSocket audio streaming to backend
- `BarcodeScannerActivity.kt` - ML Kit barcode scanning

### EHR Proxy
- `ehr-proxy/main.py` - FastAPI proxy, SOAP notes, ICD-10 codes, WebSocket endpoints
- `ehr-proxy/transcription.py` - AssemblyAI/Deepgram dual-provider abstraction with diarization
- `ehr-proxy/medical_vocabulary.py` - 500+ medical terms for transcription boost
- `ehr-proxy/.env.example` - API key configuration template

### Backend (Java)
- `backend/src/main/java/com/mdxvision/fhir/UnifiedEhrService.java` - Multi-EHR abstraction
- `backend/src/main/java/com/mdxvision/fhir/CernerFhirService.java` - Cerner client
- `backend/src/main/java/com/mdxvision/fhir/EpicFhirService.java` - Epic client

### Web Dashboard (Next.js 14)
```
web/src/app/
├── dashboard/
│   ├── page.tsx           # Main dashboard with stats, charts, quick actions
│   ├── analytics/         # Usage analytics and metrics
│   ├── billing/           # Billing claims management (Feature #71)
│   ├── devices/           # AR glasses device management (Feature #65)
│   ├── dnfb/              # DNFB revenue cycle (Feature #72)
│   ├── encounters/        # Patient encounters list
│   ├── notes/             # Clinical notes management
│   ├── patients/          # Patient list and search
│   ├── sessions/          # Transcription sessions
│   └── settings/          # App configuration
├── login/                 # Authentication
└── layout.tsx             # Root layout with dark mode support
```

**Dashboard URLs:**
| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/dashboard` | Overview, stats, quick actions |
| Sessions | `/dashboard/sessions` | Transcription session history |
| Patients | `/dashboard/patients` | Patient list and search |
| Encounters | `/dashboard/encounters` | Today's patient encounters |
| Notes | `/dashboard/notes` | Clinical documentation |
| Billing | `/dashboard/billing` | Claims creation and submission |
| DNFB | `/dashboard/dnfb` | Discharged Not Final Billed |
| Audit Log | `/dashboard/audit` | HIPAA audit log viewer |
| Devices | `/dashboard/devices` | AR glasses pairing and management |
| Analytics | `/dashboard/analytics` | Usage metrics and trends |
| Knowledge | `/dashboard/knowledge` | RAG updates, schedules, checklists |
| Settings | `/dashboard/settings` | Configuration options |

## API Endpoints

### EHR Proxy (port 8002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/patient/{id}` | GET | Get patient summary |
| `/api/v1/patient/search?name=` | GET | Search patients by name |
| `/api/v1/patient/mrn/{mrn}` | GET | Get patient by MRN |
| `/api/v1/notes/generate` | POST | Generate SOAP note |
| `/api/v1/notes/quick` | POST | Quick note for AR display |
| `/api/v1/transcription/status` | GET | Check transcription config |
| `/ws/transcribe` | WebSocket | Real-time transcription |
| `/ws/transcribe/{provider}` | WebSocket | Transcription with specific provider |

### Test Requests
```bash
# Get patient
curl http://localhost:8002/api/v1/patient/12724066

# Generate SOAP note with ICD-10 codes
curl -X POST http://localhost:8002/api/v1/notes/quick \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Patient has headache and fever", "chief_complaint": "Headache"}'

# Check transcription status
curl http://localhost:8002/api/v1/transcription/status
```

## EHR Sandbox URLs

| EHR | Base URL |
|-----|----------|
| Cerner | `https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d` |
| Epic | `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` |
| Veradigm | `https://fhir.fhirpoint.open.allscripts.com/fhirroute/open/sandbox/r4` |

## Test Data

### Cerner Sandbox Patient
- **Patient ID**: 12724066
- **Name**: SMARTS SR., NANCYS II
- **DOB**: 1990-09-15

## Architecture

### Real-Time Transcription Flow
```
[Android Mic]
    ↓ PCM Audio (16kHz, 16-bit)
[AudioStreamingService.kt]
    ↓ WebSocket
[EHR Proxy /ws/transcribe]
    ↓ WebSocket
[AssemblyAI / Deepgram]
    ↓ Transcript JSON
[Android App - Live Display]
    ↓ On Stop
[SOAP Note Generator + ICD-10]
```

### AR Glasses Data Flow
```
[Vuzix Blade 2]
    ↓ Voice Command / Wake Word
[Android App]
    ↓ HTTP Request
[EHR Proxy :8002]
    ↓ FHIR R4
[Cerner/Epic/Veradigm]
    ↓ Patient Data
[AR Display]
```

### Network Configuration
- Android emulator uses `10.0.2.2` to reach host machine's localhost
- EHR Proxy runs on port 8002
- Web dashboard runs on port 5173
- Backend API runs on port 8080

### HMD Compatibility
The Android app is designed to work with any Android-based head-mounted display (HMD):

| Device | Status | Notes |
|--------|--------|-------|
| Vuzix Blade 2 | Primary Target | Full SDK integration ready |
| Vuzix Shield | Compatible | Industrial model |
| Google Glass Enterprise | Compatible | Standard Android |
| RealWear Navigator | Compatible | Voice-first design matches |
| Android XR devices | Future Ready | Standard Android platform |
| Magic Leap 2 | Planned | Enterprise AR |
| Meta Quest Pro | Planned | Passthrough AR mode |

**Design Principles for HMD Compatibility:**
- Voice-first interface (no touch required)
- High-contrast UI for outdoor/bright environments
- Large fonts and icons for small displays
- Minimal UI chrome to maximize content area
- TTS feedback for eyes-free operation
- Standard Android APIs (no proprietary dependencies in core)

## Environment Variables

```bash
# Transcription
TRANSCRIPTION_PROVIDER=assemblyai  # or "deepgram"
ASSEMBLYAI_API_KEY=your_key
DEEPGRAM_API_KEY=your_key
ENABLE_MEDICAL_VOCAB=true  # Enable medical vocabulary boost

# AI Notes
CLAUDE_API_KEY=your_key
```

## Common Issues

### Java not found
```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
```

### ADB path
```bash
/opt/homebrew/share/android-commandlinetools/platform-tools/adb
```

### Port already in use
```bash
lsof -ti:8002 | xargs kill -9
```

### Emulator mic not working
Enable "Virtual microphone uses host audio input" in emulator Extended Controls → Microphone

### websockets library compatibility
Use `additional_headers` instead of `extra_headers` for newer versions.

## Patent Claims Implementation

See `FEATURES.md` for detailed checklist of patent claim implementations.

## Recent Changes (Jan 2025)

1. **Real-time Transcription** - AssemblyAI/Deepgram WebSocket streaming
2. **Wake Word Detection** - "Hey MDx" hands-free activation
3. **ICD-10 Code Suggestions** - Auto-detect diagnosis codes from transcript
4. **Live Transcription UI** - Full-screen overlay with real-time text
5. **Voice Commands in Transcription** - Say "close" or "stop transcription"
6. **12-Button Command Grid** - All voice commands as tappable buttons
7. **ICD-10/CPT JSON Databases** - Full code lookup with keyword mapping
8. **Font Size Adjustment** - Voice commands for accessibility (small/medium/large/extra-large)
9. **Patient Conditions Display** - FHIR Condition resource with voice command
10. **Auto-Scroll Transcription** - Automatic scroll to latest text with voice toggle
11. **Multiple Note Templates** - SOAP, Progress Note, H&P, Consult Note with voice selection
12. **Auto Note Type Detection** - Keyword analysis to suggest appropriate note format
13. **Speaker Diarization** - Multi-speaker detection with speaker labels in transcript
14. **Medical Vocabulary Boost** - 500+ medical terms for improved transcription accuracy
15. **Speaker Context from Chart** - Maps "Speaker 0/1" to patient/clinician names from loaded chart
16. **Specialty Vocabulary Auto-Load** - Detects cardiology/pulmonology/etc from patient conditions
17. **Edit Note Before Save** - EditText overlay with reset button, voice commands ("edit note", "reset note")
18. **Care Plans Display** - FHIR CarePlan resource with voice command ("show care plans")
19. **Note Sign-Off Workflow** - Confirmation dialog with checkbox, signed_by/signed_at tracking
20. **Clinical Notes Read** - FHIR DocumentReference with voice command ("show notes", "clinical notes")
21. **Voice Command Help** - Say "Help" or "What can I say" to see all available commands
22. **Quick Patient Summary** - Visual summary with "patient summary" voice command (demographics, allergies, conditions, meds, vitals)
23. **Hands-Free Patient Briefing** - Text-to-Speech reads patient summary aloud ("brief me", "tell me about patient") while walking to next room
24. **Transcript Preview Before Generate** - Shows word count, detected topics, transcript preview before AI note generation ("generate note", "re-record")
25. **Speech Feedback for Actions** - TTS confirms key actions ("Patient loaded", "Recording started", "Note saved") with toggle
26. **Allergy Warnings Spoken** - Critical allergies automatically spoken aloud when patient loads (bypasses speech feedback toggle for safety)
27. **Offline Note Drafts** - Notes saved locally when offline or save fails, auto-sync when connectivity restores ("sync notes", "show drafts", "delete draft [N]")
28. **CPT Modifier Support** - 20+ modifiers (-25, -59, LT/RT, etc.) with keyword detection and auto-suggest -25 for E/M + procedure combinations
29. **Critical Lab Alerts** - Auto-detect critical lab values (potassium, glucose, troponin, etc.) with spoken TTS alerts on patient load (safety-first, bypasses toggle)
30. **Critical Vital Alerts** - Auto-detect critical vitals (BP >180, HR <40/>150, SpO2 <88%, Temp >104F) with spoken TTS alerts (safety-first, spoken before labs/allergies)
31. **Medication Interaction Alerts** - Drug-drug interaction checking with 18+ medications, brand name recognition, severity levels, spoken TTS alerts for high-severity interactions
32. **Push Notes to EHR** - Push generated notes to EHR via FHIR DocumentReference POST ("push note", "send to EHR"), with LOINC codes and status tracking
33. **HIPAA Audit Logging** - JSON-structured audit logs for all PHI access, note operations, safety alerts with rotating file storage (ehr-proxy/logs/audit.log)
34. **Lab Trends** - Historical lab value comparison with trend icons (↗️↘️→🆕), delta display, TTS alerts for rising/falling values
35. **Vital Trends** - Historical vital value comparison (BP, HR, SpO2, etc.) with trend icons, delta display, TTS alerts
36. **Patient Photo Display** - FHIR photo extraction with base64/URL support, initials placeholder, circular avatar in header
37. **Patient Search History** - Recently viewed patients list, quick load by number ("load 1"), voice commands, relative timestamps
38. **Session Timeout** - HIPAA compliance auto-lock after 5 min inactivity, configurable timeout, voice commands ("lock session", "unlock", "timeout N min")
39. **Voice Note Editing** - Voice commands to edit notes: change/set sections, add to sections, delete last sentence/line/item, clear sections, insert macros (normal exam, normal vitals, negative ROS, follow up), 10-level undo history
40. **Voice Navigation** - Scroll up/down, go to top/bottom, jump to SOAP sections ("go to assessment"), show section only, TTS read-back of sections/entire note
41. **Voice Dictation Mode** - Dictate directly into sections ("dictate to plan"), continuous speech capture, "stop dictating" to insert, visual indicator, word count display
42. **Voice Templates** - 8 built-in templates (diabetes, hypertension, URI, physical, back pain, UTI, well child, chest pain) with auto-fill patient data, user-created templates, variable substitution ({{patient_name}}, {{medications}}, etc.)
43. **Voice Orders** - Order labs (12), imaging (10), medications (10) by voice; safety checks for allergies, drug interactions, duplicates, metformin+contrast; confirmation workflow; auto-add to Plan section; "show orders", "cancel order"
44. **Encounter Timer** - Track time spent with patients; voice commands "start timer", "stop timer", "how long", "reset timer"; visual indicator in top-right corner; TTS time reports; auto-include duration in notes for billing
45. **Order Sets** - 12 clinical order bundles (chest pain, sepsis, stroke, CHF, COPD, DKA, PE, pneumonia, UTI, abdominal pain, admission labs, preop labs); "order chest pain workup", "list order sets", "what's in [set]" to preview
46. **Voice Vitals Entry** - Capture vitals by voice ("BP 120 over 80", "pulse 72", "temp 98.6"); 8 vital types with range validation; critical value warnings; "show captured vitals", "add vitals to note"
47. **Vital History Display** - View historical vital readings timeline; "vital history", "past vitals"; shows last 10 readings per vital type with trend icons (↗️↘️→🆕), dates, and interpretation flags
48. **Custom Voice Commands** - Create user-defined command macros; "create command [name] that does [actions]", "when I say [phrase] do [action]", "teach [name] to [actions]"; chain multiple actions with "then"/"and"; "my commands" to list, "delete command" to remove; persistent storage
49. **Medical Calculator** - Voice-activated clinical calculations; auto-pull values from patient chart; BMI, eGFR (CKD-EPI 2021), corrected calcium, anion gap, A1c↔glucose, MAP, CrCl (Cockcroft-Gault), CHADS₂-VASc; interpretations and clinical ranges included
50. **SBAR Handoff Report** - Structured shift handoff reports; SBAR format (Situation, Background, Assessment, Recommendation); visual display + TTS spoken report; includes critical vitals, allergies, meds, pending orders, care plans; voice commands ("handoff report", "speak handoff", "SBAR")
51. **Discharge Summary** - Patient discharge instructions with diagnoses, medications (current + new prescriptions), allergy warnings, follow-up instructions (care plans, pending labs/imaging), return precautions, activity/diet guidance; TTS spoken instructions for patient education; voice commands ("discharge summary", "read discharge", "patient education")
52. **Procedure Checklists** - Safety workflows for common procedures; 6 built-in checklists (timeout, central line, intubation, lumbar puncture, blood transfusion, sedation); pre/post-procedure items; voice commands ("show checklists", "start timeout checklist", "check 1", "check all", "read checklist")
53. **Clinical Reminders** - Preventive care prompts based on patient data; age-based screening (colonoscopy, mammogram, DEXA); condition-based monitoring (diabetes A1c, CHF weight, CKD labs); medication monitoring (warfarin INR, lithium levels); USPSTF/CDC/ADA guideline sources
54. **Medication Reconciliation** - Compare home meds vs EHR meds; add/remove home medications by voice; highlight discrepancies (EHR-only, home-only, matched); voice commands ("med reconciliation", "add home med [name]", "compare meds", "clear home meds")
55. **Referral Tracking** - Track specialist referrals; 16 common specialties; urgency levels (routine, urgent, stat); status tracking (pending, scheduled, completed); voice commands ("refer to cardiology for chest pain", "urgent referral to neurology", "mark referral 1 scheduled")
56. **Specialty-Specific Templates** - 14 clinical templates by specialty: Cardiology (chest pain, heart failure, afib), Orthopedics (joint pain, fracture), Neurology (headache, stroke), GI (abdominal pain, GERD), Pulmonology (COPD, asthma), Psychiatry (depression, anxiety), Emergency (trauma, sepsis); voice commands ("specialty templates", "use cardiology chest pain template")
57. **Note Versioning** - Track note revision history; save versions on edits; restore previous versions; compare current vs previous; version timestamps and change descriptions; voice commands ("version history", "restore version 3", "compare versions", "clear version history")
58. **ICD-10-CM Database** - 150+ diagnostic codes with keyword mapping; categories include infectious diseases, neoplasms, endocrine, circulatory, respiratory, digestive, musculoskeletal, symptoms/signs, injury, and external causes; auto-suggest from transcript
59. **CPT Database** - 100+ procedure codes covering E/M services (99201-99215, 99281-99285), preventive visits, labs (80048-80076, 85025), procedures (10060-69990), imaging (71045-74177); modifier support (-25, -59, LT/RT, etc.)
60. **Data Encryption at Rest** - AES-256-GCM encryption via Android Keystore; EncryptedSharedPreferences for PHI storage; secure patient data caching; note drafts encryption; voice commands ("encryption status", "wipe data"); HIPAA compliant hardware-backed encryption
61. **Multi-Language Support** - Voice recognition and TTS in English, Spanish, Russian, Mandarin Chinese, and Portuguese; 80+ Spanish translations, 70+ Russian translations; accent-insensitive matching (á→a, ñ→n, etc.); bilingual TTS feedback; persistent language preference; voice commands ("switch to Russian", "русский", "language options"); section name translations for SOAP editing
62. **Ambient Clinical Intelligence (ACI)** - Passive room audio capture for auto-documentation; continuous background listening mode; multi-speaker diarization (clinician vs patient identification); clinical entity extraction (100+ symptoms, 50+ medications, 20+ allergies, vital signs, medical history, social/family history, ROS, physical exam findings, assessments, plans); real-time entity overlay display; auto-SOAP note generation from ambient transcript; speaker segment tracking with timestamps; voice commands ("ambient mode", "start ambient", "stop ambient", "show entities", "generate note")
63. **CRUD Write-Back to EHR** - Full 2-way voice documentation; push vitals as FHIR Observations (LOINC codes); push orders as ServiceRequest/MedicationRequest (CPT/RxNorm codes); add allergies as AllergyIntolerance; discontinue/hold medications via status updates; HIPAA-compliant soft deletes (no hard deletes); offline sync queues for all data types; confirmation workflows for safety-critical operations; voice commands ("push vitals", "push orders", "add allergy to [substance]", "discontinue [med]", "hold [med]", "confirm", "sync all")
64. **Device Authentication (TOTP + Proximity Lock)** - Multi-layer security for AR glasses: QR code device pairing from web dashboard; TOTP (Google Authenticator/Authy) voice code entry ("4 7 2 9 1 5"); proximity sensor auto-lock when glasses removed from face; 12-hour session tokens; remote wipe from dashboard; spoken digit recognition with homophones (won/one, two/too/to, for/four, etc.); voice commands ("pair device", "device status", say 6-digit TOTP code to unlock); prevents unauthorized access if glasses lost/stolen
65. **Device Management Dashboard** - Web UI for managing AR glasses: view all paired devices with status (active/locked/wiped); pair new devices via QR code; setup TOTP authenticator with QR code; remote wipe lost/stolen devices; device stats (total, active sessions, idle, wiped); last seen timestamps; security info panel; accessible at /dashboard/devices
66. **Voiceprint Speaker Recognition** - SpeechBrain ECAPA-TDNN model for biometric voice authentication; enrollment via 3 spoken phrases ("My voice is my password", "MDx Vision unlock my session", "I authorize this clinical action"); server-side embedding extraction with cosine similarity matching (threshold 0.70); verification required for sensitive operations (push notes to EHR, push vitals/orders, add allergies, discontinue medications); voice commands ("enroll my voice", "voiceprint status", "delete voiceprint"); prevents unauthorized EHR writes even with stolen device
67. **Patient Worklist** - Daily patient schedule with check-in workflow; scheduled/checked_in/in_room/in_progress/completed statuses; priority levels (normal, urgent, STAT); room assignment; chief complaint tracking; critical alert indicators; "who's next" queue management; voice commands ("show worklist", "check in 1", "check in 2 to room 5", "who's next", "mark 1 completed", "start seeing 2", "load 1"); API endpoints (/api/v1/worklist, /api/v1/worklist/check-in, /api/v1/worklist/status, /api/v1/worklist/next)
68. **Order Update/Modify** - Full inpatient order management workflow; show numbered order list; update by number or medication name ("update 1 to 500mg every 6 hours", "update tylenol to 650mg PRN"); delete by number ("delete 2", "remove 3"); confirmation workflow before applying changes; parses dose, frequency, duration, PRN status; integrates with existing order placement and push to EHR
69. **AI Differential Diagnosis (DDx)** - AI-powered differential diagnosis from clinical findings; ranked DDx list (top 5) with ICD-10 codes; likelihood levels (high/moderate/low); supporting findings, red flags, recommended next steps; clinical reasoning explanation; urgent considerations; integration with ambient mode entities; voice commands ("differential diagnosis", "ddx", "what could this be", "read differential", "speak ddx"); safety disclaimer "For clinical decision support only"; rule-based fallback when AI unavailable; HIPAA audit logging for all DDx requests
70. **Medical Image Recognition** - Claude Vision-powered image analysis (claude-3-5-sonnet) for medical images; captures wounds, rashes, X-rays via camera activity; returns clinical assessment, findings with confidence levels, ICD-10 codes, recommendations, red flags, differential considerations; context types: wound, rash, xray, general; voice commands ("take photo", "capture image", "analyze wound", "analyze rash", "analyze xray", "read analysis", "image results"); safety disclaimer "For clinical decision support only"; 15MB size limit; HIPAA audit logging (no image data in logs)
71. **Billing/Coding Submission** - Create billing claims from saved clinical notes; auto-populate ICD-10 diagnoses and CPT procedures; review/edit codes before submission; add/remove diagnoses by voice ("add diagnosis J06.9", "remove diagnosis 2"); add/remove procedures ("add procedure 99213"); CPT modifier support ("add modifier 25 to 1"); code search ("search icd hypertension", "search cpt office visit"); submit with confirmation workflow; FHIR Claim resource generation (R4); claim history per patient ("show claims", "claim history"); voice commands ("create claim", "bill this", "submit claim", "confirm", "close billing"); HIPAA audit logging for all billing operations
72. **DNFB (Discharged Not Final Billed)** - Revenue cycle management for unbilled discharged accounts; aging bucket tracking (0-3, 4-7, 8-14, 15-30, 31+ days); reason codes (coding incomplete, documentation missing, charges pending, prior auth issues); prior authorization tracking (pending, approved, denied, expired, not obtained); prior auth issue filtering with at-risk revenue calculation; DNFB summary metrics with breakdown by reason and aging; patient-specific DNFB status; resolve accounts and link to billing claims; voice commands ("show DNFB", "DNFB summary", "prior auth issues", "over 7 days", "resolve 1", "patient DNFB"); HIPAA audit logging
73. **Vuzix HUD Native Overlay** - Always-on patient info HUD for Vuzix Blade 2 AR glasses (1280x720); Foreground Service with WindowManager overlay; two modes: compact (320x180dp) showing patient name, allergies, meds count, room, and expanded (768x400dp) with full details; auto-updates when patient data changes; voice commands ("show HUD", "hide HUD", "expand HUD", "minimize HUD", "toggle HUD"); non-blocking FLAG_NOT_FOCUSABLE overlay; dark theme (#0A1628) with high-contrast text; Vuzix SDK integration (hud-actionmenu:2.9.0, hud-resources:2.3.0); auto-detects Vuzix device; graceful fallback on non-Vuzix devices
74. **Audit Log Viewer Dashboard** - Web UI for viewing HIPAA audit logs; stats cards (PHI Access, Note Operations, Safety Alerts, Unique Patients); filterable log table with search by patient ID, event type, and action filters; date range selection; pagination (25/50/100 per page); real-time refresh; 4 API endpoints (/api/v1/audit/logs, /api/v1/audit/stats, /api/v1/audit/actions, /api/v1/audit/patient/{id}); accessible at /dashboard/audit
75. **Gesture Control** - Head gesture recognition for Vuzix Blade 2 AR glasses; gyroscope-based state machine detection; nod (yes) for confirm/approve actions, shake (no) for cancel/dismiss, double nod for HUD toggle; touchpad DPAD navigation (left/right for worklist, up/down for HUD expand/minimize, center for select); integrates with order confirmations, billing submissions, worklist navigation; voice commands ("enable gestures", "disable gestures", "gesture status"); cooldown timers prevent false positives; TTS feedback for all gesture actions
76. **Wink Gesture (Micro-Tilt)** - Quick head dip gesture for rapid selection on Vuzix Blade 2; alternative to full nod for faster interaction; lower threshold (0.8-1.5 rad/s vs 1.8+ for nod); faster duration requirement (<200ms); 300ms cooldown for rapid selection; dismisses overlays, selects worklist patients, acknowledges alerts; voice commands ("enable wink", "disable wink", "wink status"); distinct from full nod to prevent gesture confusion; 14 unit tests for wink detection
77. **Voice Biometric Continuous Auth** - Extends Feature #66 with periodic re-verification during active sessions; VoiceprintSession model with confidence decay (1% per minute); configurable re-verify interval (default 5 minutes); server-side session storage with timestamps; background monitoring during transcription/ambient modes; auto-prompt when verification expires; sensitive operations require fresh voiceprint (push notes, vitals, orders, allergies, medication updates); X-Device-ID header enables enforcement; voice commands ("verify me", "verify my voice", "verification status", "set verify interval [N] minutes"); API endpoints (/api/v1/auth/voiceprint/{device_id}/check, /api/v1/auth/voiceprint/{device_id}/re-verify, /api/v1/auth/voiceprint/{device_id}/interval)
78. **AI Clinical Co-pilot** - Interactive AI dialogue during clinical documentation; conversational context with 6-message history; patient context integration (conditions, medications, allergies, chief complaint); TTS-optimized responses (3 bullets, 15 words each); actionable suggestions (orders, calculators) with voice prompts; natural language triggers ("what should I...", "what do you think..."); follow-up support ("tell me more", "what next"); Claude claude-3-haiku for fast responses; voice commands ("hey copilot", "copilot [question]", "tell me more", "elaborate", "suggest next", "clear copilot"); API endpoint (/api/v1/copilot/chat); HIPAA audit logging (chief complaint only, no full PHI)
79. **Racial Medicine Awareness** - Clinical decision support addressing the "white default" problem in medicine; Fitzpatrick skin type tracking (I-VI); pulse oximeter accuracy alerts for darker skin (1-4% overestimation warning); skin assessment guidance for melanin-rich skin (cyanosis, jaundice, pallor, erythema, petechiae, bruising, rash, melanoma with modified examination techniques); pharmacogenomic medication considerations (ACE inhibitors, beta-blockers for African ancestry; warfarin, clopidogrel for Asian ancestry); maternal mortality risk alerts (3-4x higher for Black women); sickle cell pain crisis protocol (60-minute treatment target); pain assessment bias reminders; calculator bias warnings (race-free eGFR CKD-EPI 2021); API endpoints (/api/v1/racial-medicine/alerts, /api/v1/racial-medicine/skin-guidance, /api/v1/racial-medicine/medication-considerations/{ancestry}); HIPAA audit logging; first-of-its-kind feature not available in any commercial EHR or AR system
80. **Cultural Care Preferences** - Comprehensive religious and cultural healthcare preferences; religion-specific care considerations (Jehovah's Witness blood products, Islam dietary/fasting/modesty, Judaism kosher/Sabbath, Hinduism, Buddhism, Sikhism); blood product preference tracking with individual conscience items; dietary medication concerns (gelatin, alcohol, lactose, animal-derived); Ramadan fasting medication timing; modesty requirements and same-gender provider preferences; family decision-making styles (individual, family-centered, patriarch-led, shared); communication preferences (direct, indirect, family-first); end-of-life preferences; traditional medicine tracking (TCM, Ayurveda, curanderismo); API endpoints (/api/v1/cultural-care/alerts, /api/v1/cultural-care/preferences/{patient_id}, /api/v1/cultural-care/religious-guidance/{religion}); HIPAA audit logging
81. **Implicit Bias Alerts** - Gentle, evidence-based reminders during clinical documentation to support equitable care; triggered during pain assessment, pain medication prescribing, triage, cardiac symptoms, psychiatric evaluation, substance use assessment; context-aware keyword detection; research citations (Hoffman 2016, Pletcher 2008, FitzGerald 2017); reflection prompts to encourage self-awareness; educational resources (Project Implicit, AAMC, NIH, CDC); non-accusatory framing focused on awareness not blame; once-per-session alerts to avoid alert fatigue; toggle on/off with voice commands; voice commands ("bias check", "bias alert", "enable bias", "disable bias", "bias status", "bias resources", "acknowledge bias"); API endpoints (/api/v1/implicit-bias/check, /api/v1/implicit-bias/contexts, /api/v1/implicit-bias/resources); HIPAA audit logging
82. **Maternal Health Monitoring** - High-risk OB alerts addressing 3-4x maternal mortality for Black women; maternal status tracking (pregnant, postpartum); risk stratification (standard, elevated, high) based on ancestry and conditions; 15+ warning signs database with urgency levels (emergency, urgent, routine); preeclampsia monitoring (BP thresholds, symptoms, labs); postpartum hemorrhage protocol; postpartum depression screening (Edinburgh Scale); 10-item postpartum checklist; disparity awareness alerts with CDC 2023 data; voice commands ("maternal health", "patient is pregnant", "patient is postpartum", "warning signs", "postpartum checklist", "preeclampsia", "hemorrhage", "ppd screen", "maternal disparity"); API endpoints (/api/v1/maternal-health/assess, /api/v1/maternal-health/warning-signs, /api/v1/maternal-health/postpartum-checklist, /api/v1/maternal-health/disparity-data); HIPAA audit logging; life-saving feature based on research showing most maternal deaths are preventable
83. **Web Dashboard Equity UI** - Settings page for configuring health equity preferences; "Health Equity" tab in settings navigation; Fitzpatrick skin type dropdown (I-VI) for pulse oximeter alerts and skin assessment; ancestry selection for pharmacogenomic considerations; religion dropdown with Jehovah's Witness blood product preferences (individual conscience items: whole blood, red cells, plasma, platelets, albumin, immunoglobulins, cell salvage); dietary restrictions checkboxes (Halal, Kosher, vegetarian, vegan, no pork/beef/gelatin, no alcohol in meds); same-gender provider toggle; decision-making style (individual, family-centered, patriarch-led, shared); maternal status (pregnant, postpartum); implicit bias alerts toggle; save with confirmation feedback; dark mode support; accessible at /dashboard/settings → Health Equity tab
84. **SDOH Integration** - Social Determinants of Health screening and intervention tracking; 5 SDOH domains (economic stability, education, healthcare access, neighborhood, social/community); 14+ risk factors with clinical impact descriptions (food insecurity, housing instability, transportation barriers, no insurance, financial strain, health literacy, limited English, social isolation, domestic violence, discrimination); risk stratification (low, moderate, high, critical); 20+ interventions with referrals, resources, and care modifications; ICD-10 Z-codes for billing (Z59.41 food, Z59.0 homeless, Z59.82 transportation, etc.); medication adherence barrier identification; voice commands ("SDOH", "food insecurity", "housing unstable", "transportation barrier", "no insurance", "financial strain", "lives alone", "SDOH screen", "SDOH interventions", "adherence barriers", "Z codes", "clear SDOH"); API endpoints (/api/v1/sdoh/screen, /api/v1/sdoh/factors, /api/v1/sdoh/screening-questions, /api/v1/sdoh/z-codes, /api/v1/sdoh/interventions, /api/v1/sdoh/adherence-risks); HIPAA audit logging; based on validated tools (PRAPARE, AHC-HRSN, NACHC)
85. **Health Literacy Assessment** - Adjusts discharge instruction complexity based on patient literacy level; 4 literacy levels (inadequate, marginal, adequate, proficient); validated BRIEF/SILS single-question screening ("How confident filling out medical forms?"); 13 observable risk indicators (asks to take materials home, identifies pills by color, avoids reading, etc.); 40+ plain language translations for medical terms (hypertension→high blood pressure, dyspnea→trouble breathing, QID→four times a day); 6 simplified discharge templates (diabetes, heart failure, hypertension, anticoagulation, infection, post-surgery) with key points, red flags, and teach-back questions; level-specific accommodations (inadequate: pictures only, verbal, 1-2 messages; marginal: 5th grade, bullet points, 3-4 messages); teach-back checklist for medications, warning signs, follow-up; voice commands ("literacy", "literacy screen", "low literacy", "marginal", "diabetes instructions", "teach back", "plain language", "accommodations"); API endpoints (/api/v1/literacy/assess, /api/v1/literacy/screening-question, /api/v1/literacy/accommodations/{level}, /api/v1/literacy/plain-language, /api/v1/literacy/simplify-instructions, /api/v1/literacy/teach-back-checklist); HIPAA audit logging
86. **Interpreter Integration** - Real-time language services for LEP (Limited English Proficiency) patients; 16 supported languages including ASL; interpreter types (in-person, video/VRI, phone/OPI, staff, ad-hoc); language preference tracking with interpreter required flag; family interpreter declined documentation (Title VI compliance); pre-translated clinical phrases for Spanish, Chinese, Vietnamese with phonetic pronunciation guides; interpreter service directory (Language Line 1-800-526-7625, CyraCom 1-844-797-2266, Stratus Video VRI); session management (start/end with duration tracking); Title VI compliance checklist (never use children, document language preference, offer qualified interpreter); vital documents requiring translation (consent forms, discharge instructions, HIPAA notices); voice commands ("need interpreter", "Spanish interpreter", "set language Spanish", "clinical phrases", "interpreter services", "Title VI", "document interpreter", "start interpreter", "end interpreter"); API endpoints (/api/v1/interpreter/languages, /api/v1/interpreter/request, /api/v1/interpreter/start-session, /api/v1/interpreter/end-session, /api/v1/interpreter/phrases/{language}, /api/v1/interpreter/set-preference, /api/v1/interpreter/services, /api/v1/interpreter/compliance-checklist); HIPAA audit logging
87. **Ray-Ban Meta Companion App** - Phone companion app for Meta Ray-Ban smart glasses; connects via Meta Wearables Device Access Toolkit; receives audio from glasses mic for transcription; displays patient data on glasses HUD; TTS feedback through glasses speakers; voice commands mirrored from main app (patient lookup, vitals, allergies, meds, labs); AI Clinical Co-pilot integration with conversation history; health equity features (interpreter requests, literacy screening, SDOH documentation); camera capture for medical image analysis (wounds, rashes, X-rays); documentation mode with start/stop note; vital signs capture by voice; help command listing all available voice commands; dark theme UI matching main app; simulated glasses connection for development; located at mobile/rayban-companion/
88. **RAG Clinical Knowledge System** - Retrieval-Augmented Generation for evidence-based SOAP notes; ChromaDB vector database for medical document storage; SentenceTransformer embeddings (all-MiniLM-L6-v2) for semantic search; 12 built-in clinical guidelines (AHA chest pain/heart failure/afib, GOLD COPD, ATS pneumonia, ADA diabetes, IDSA UTI, Surviving Sepsis, AHA stroke, USPSTF preventive, warfarin management, opioid equivalence); citation injection in assessment/plan sections ([1], [2], etc.); relevance scoring with cosine similarity; configurable result count; custom document ingestion with metadata (source, publication date, category, specialty); auto-initialization with persistent storage (./data/chroma_db); graceful fallback when dependencies unavailable; API endpoints (/api/v1/rag/status, /api/v1/rag/initialize, /api/v1/rag/query, /api/v1/rag/retrieve, /api/v1/rag/add-document, /api/v1/rag/guidelines); SOAP note integration via use_rag parameter; rag_enhanced flag in responses; reduces AI hallucination by grounding in medical sources; HIPAA audit logging for all RAG operations
89. **RAG Knowledge Management** - Continuous improvement system for the clinical knowledge base; guideline versioning with automatic supersession tracking (current, superseded, deprecated, draft, archived statuses); PubMed ingestion pipeline via NCBI E-utilities API (free, no API key for <3 req/sec); clinician citation feedback loop (very_helpful, helpful, neutral, not_helpful, incorrect ratings); quality scoring based on feedback; low-quality document detection for review; specialty-specific collections with curators; conflict detection between guidelines (dosing, contraindication, recommendation patterns); RSS feed monitoring for medical updates (AHA, CDC MMWR, NEJM, JAMA); scheduled update checks for major sources; analytics tracking (usage patterns, top documents, specialty usage); HIPAA audit logging for all knowledge operations; API endpoints (/api/v1/knowledge/analytics, /api/v1/knowledge/feedback, /api/v1/knowledge/version, /api/v1/knowledge/versions/{id}, /api/v1/knowledge/pubmed/ingest, /api/v1/knowledge/pubmed/search, /api/v1/knowledge/collections, /api/v1/knowledge/conflicts, /api/v1/knowledge/check-updates, /api/v1/knowledge/rss-feeds, /api/v1/knowledge/deprecate/{id})
90. **Scheduled RAG Updates** - Automated knowledge base updates with review checklists; 5 default schedules (Cardiology Daily, Diabetes Daily, Infectious Disease Daily, CDC MMWR Hourly, Major Sources Weekly); configurable frequency (hourly to weekly); PubMed query schedules, RSS feed monitors, comprehensive guideline checks; pending update queue with priority levels (critical, high, medium, low); 7-item review checklist per update (quality, safety, conflicts, clinical accuracy - 5 required, 2 optional); reviewer sign-off with notes; approve/reject workflow with audit trail; auto-ingest approved updates; bulk ingest all approved; dashboard with status breakdown, priority counts, specialty distribution, next scheduled runs, run history; cron-compatible `/api/v1/updates/run-due` endpoint; HIPAA audit logging; API endpoints (/api/v1/updates/dashboard, /api/v1/updates/pending, /api/v1/updates/schedules, /api/v1/updates/checklist/{id}, /api/v1/updates/{id}/approve, /api/v1/updates/{id}/reject, /api/v1/updates/{id}/ingest, /api/v1/updates/run-due, /api/v1/updates/ingest-all-approved)
91. **Knowledge Updates Dashboard** - Web UI for managing RAG updates at /dashboard/knowledge; stats cards (Pending Review, Approved, Ingested, Active Schedules); 3 tabs (Pending Updates, Schedules, Run History); pending updates list with priority/status badges, checklist progress indicators; interactive checklist panel with click-to-complete items, reviewer name tracking; approve/reject buttons (approve requires all required checklist items); ingest button for approved updates; bulk "Ingest All Approved" action; schedules table with source type, frequency, last/next run times; play/pause toggle per schedule; manual "Run Now" button per schedule; "Run Due Schedules" bulk action; run history table with timestamps and update counts; dark mode support; responsive grid layout
92. **Pre-Visit Prep Alert (Jarvis Wave 1)** - Proactive AI briefing when loading a patient; analyzes patient data for care gaps, critical values, trends, and safety concerns; categories: critical (abnormal vitals/labs), care_gap (overdue screenings), trend (worsening values), reminder (polypharmacy, allergy alerts); age/gender-based screening detection (mammogram, colonoscopy, A1c); spoken TTS summary for hands-free operation; HUD-formatted display summary for AR glasses; quick action suggestions (voice commands to act on alerts); auto-triggered on patient load; voice commands ("prep me", "patient prep", "heads up", "what should I know"); critical alerts bypass speech toggle for safety; API endpoint GET /api/v1/patient/{id}/prep; HIPAA audit logging; Android integration with Vuzix HUD support
93. **Chief Complaint Workflows (Jarvis Wave 1)** - Detects chief complaint and suggests relevant workups/orders; 12 complaint mappings (chest pain, shortness of breath, abdominal pain, fever, headache, altered mental status, syncope, back pain, diabetic emergency, respiratory distress, urinary symptoms, cough); each complaint maps to order_set, suggested_orders, protocols, and clinical considerations; keyword detection from patient conditions and ambient conversation text; TTS-friendly spoken suggestions with voice commands; display summary for HUD; voice commands ("suggest workup", "what workup", "workflow", "workup for [complaint]"); API endpoints GET /api/v1/patient/{id}/workflow and POST /api/v1/workflow/suggest; integrates with existing Order Sets (Feature #45); HIPAA audit logging; Android integration with Vuzix support
94. **Multi-Turn Clinical Reasoning (Jarvis Wave 1)** - Enhanced AI copilot with multiple reasoning modes for clinical decision support; Teaching mode explains clinical reasoning with educational context and step-by-step logic; Second Opinion mode provides alternative diagnoses, challenges assumptions, and highlights considerations you may have missed; Clarify mode identifies gaps in clinical information and suggests questions to ask; conversation history maintained for contextual back-and-forth dialogue; patient context (conditions, medications, allergies) automatically included; TTS-friendly spoken responses with follow-up prompts; voice commands ("explain why", "teach me", "why do you think", "second opinion", "what else could it be", "challenge", "what am I missing", "clarify", "what should I ask"); API endpoints POST /api/v1/copilot/reason, /api/v1/copilot/teach, /api/v1/copilot/challenge; Android integration with sendCopilotTeachingMode(), sendCopilotSecondOpinion(), sendCopilotClarifyMode(); HIPAA audit logging
95. **Indirect Commands (Jarvis Wave 1)** - Natural language parsing for conversational queries; translates informal requests like "check that potassium" or "what's his blood pressure" into actionable commands; 25+ lab items with LOINC codes (potassium, sodium, creatinine, hemoglobin, glucose, a1c, troponin, BNP, INR, TSH, CBC, CMP, BMP, lipid panel, etc.); 9 vital items (blood pressure, heart rate, temperature, SpO2, respiratory rate, weight, height, BMI, pain); category keywords for meds, allergies, conditions, procedures, immunizations, care plans, clinical notes; temporal parsing (last, latest, recent, trend, history); alias support (k->potassium, bp->blood pressure, hgb->hemoglobin, o2 sat->oxygen saturation); confidence scoring (high/medium/low); filtered display highlights matching item; TTS spoken results; voice commands ("check the potassium", "what's his blood pressure", "get the cbc", "what was the last creatinine"); API endpoints POST /api/v1/commands/parse, GET /api/v1/commands/suggestions; HIPAA audit logging; Android integration with parseAndExecuteIndirectCommand()
96. **Care Gap Detection (Jarvis Wave 2)** - Proactive identification of missing screenings, labs, vaccines, and preventive care; comprehensive rules engine with 31 care gap rules based on clinical guidelines; USPSTF screening recommendations (colonoscopy, mammogram, pap smear, lung cancer, AAA screening, depression/anxiety); ADA diabetes care standards (A1c, eye exam, foot exam, urine albumin); AHA/ACC cardiovascular guidelines (lipid panel, blood pressure, heart failure monitoring); CDC/ACIP vaccine recommendations (influenza, pneumococcal, shingles, Tdap, COVID, hepatitis B); KDIGO kidney disease guidelines (eGFR, CKD monitoring); Medicare Annual Wellness Visit; age/gender-based eligibility filtering; condition-based requirements (diabetes, hypertension, CKD, CHF, warfarin therapy); interval tracking (years, months, weeks) with overdue detection; priority scoring (high/medium/low) based on due status; TTS-friendly spoken summary; HUD-formatted display with priority icons (🔴🟡🟢); voice commands ("care gaps", "screenings due", "overdue items", "vaccines due", "labs due", "high priority gaps"); API endpoints GET /api/v1/patient/{id}/care-gaps (with category/priority filters), GET /api/v1/care-gaps/rules; Android integration with fetchCareGaps(), displayCareGaps(); Vuzix HUD support; HIPAA audit logging

## Research Documents

| Document | Description |
|----------|-------------|
| `RACIAL_MEDICINE_DISPARITIES.md` | Comprehensive research on racial disparities in medicine with implementation guidance |
| `CULTURAL_CARE_PREFERENCES.md` | Research on cultural/religious care preferences with clinical recommendations |

## Next Up (Recommended)

### Quick Wins
| Feature | Notes |
|---------|-------|
| All medium effort items completed! | 91 features implemented |

### EHR Integration Status (Jan 4, 2025)

**Priority Focus (95% hospital + 80% ambulatory market):**
| EHR Platform | Status | Cost | Notes |
|--------------|--------|------|-------|
| **Cerner/Oracle** | READY | FREE | Client ID: `0fab9b20-adc8-4940-bbf6-82034d1d39ab` |
| **Epic** | Pending | FREE | User has credentials |
| **Veradigm** | Pending | $99/mo | User has credentials |
| **athenahealth** | Available | FREE | Self-service sandbox |
| **eClinicalWorks** | Available | FREE | FHIR APIs available |
| **NextGen** | Available | FREE | Developer program |
| **MEDITECH** | Available | FREE | Greenfield Workspace |
| **DrChrono** | Available | FREE | Cloud EHR |

**Total platforms documented:** 29 (see EHR_ACCESS_GUIDE.md)

See `EHR_ACCESS_GUIDE.md` for detailed setup instructions.

### Larger Features
1. Epic/Veradigm live integration (credentials being gathered)
2. Android XR SDK support (Jetpack Compose Glimmer, Gemini integration) - backlog
