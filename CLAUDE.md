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

## Recent Changes (Dec 2024)

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

## Research Documents

| Document | Description |
|----------|-------------|
| `RACIAL_MEDICINE_DISPARITIES.md` | Comprehensive research on racial disparities in medicine with implementation guidance |
| `CULTURAL_CARE_PREFERENCES.md` | Research on cultural/religious care preferences with clinical recommendations |

## Next Up (Recommended)

### Quick Wins
| Feature | Notes |
|---------|-------|
| All medium effort items completed! | 83 features implemented |

### Larger Features
1. Epic/Veradigm live integration (needs credentials)
2. Android XR SDK support (Jetpack Compose Glimmer, Gemini integration) - backlog
