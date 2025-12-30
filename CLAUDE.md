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

## Next Up (Recommended)

### Quick Wins
| Feature | Notes |
|---------|-------|
| All medium effort items completed! | 50 features implemented |

### Larger Features
1. Epic/Veradigm live integration (needs credentials)
2. OAuth2/SMART on FHIR authentication
3. Vuzix HUD native overlay
4. Data encryption at rest (local storage)
5. Android XR SDK support (Jetpack Compose Glimmer, Gemini integration) - backlog
