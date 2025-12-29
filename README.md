# MDx Vision - Enterprise Healthcare Platform

Real-time AI-powered clinical documentation system with AR smart glasses integration.

**Patent:** US 15/237,980 - Voice-activated AR glasses for healthcare documentation

## Current Status (Dec 2024)

| Component | Status | Notes |
|-----------|--------|-------|
| Android/Vuzix App | **Working** | 30+ voice commands, patient lookup, live transcription |
| Cerner Integration | **Working** | Live sandbox data |
| Epic Integration | Pending | Credentials needed |
| Veradigm Integration | Ready | Service implemented |
| Real-time Transcription | **Working** | AssemblyAI/Deepgram with speaker diarization |
| AI Clinical Notes | **Working** | SOAP, Progress, H&P, Consult notes with preview |
| Medical Coding | **Working** | ICD-10 (90+) & CPT (100+) with modifiers |
| Text-to-Speech | **Working** | Patient briefings, action confirmations |
| Web Dashboard | **Working** | localhost:5173 |
| Camera/Barcode | **Working** | Patient wristband scan via ML Kit |

## Key Features

### Voice Commands (30+)
- **Wake Word**: "Hey MDx" for hands-free activation
- **12-Button Grid**: Tap or speak commands for all functions
- **Patient Data**: Load, search, scan wristband
- **Clinical**: Show vitals/meds/allergies/labs/conditions/care plans/notes
- **Documentation**: Start note, live transcribe, generate, save
- **Settings**: Font size, auto-scroll, speech feedback, clinician name
- **Help**: Say "Help" to see all available voice commands

### Hands-Free Patient Briefing (NEW)
- **Quick Summary**: "Patient summary" shows key info at a glance
- **Spoken Briefing**: "Brief me" reads patient info aloud while walking
- **Safety First**: Allergies always spoken first
- **Natural Speech**: Dates and vitals formatted for clarity ("September 15th, 1990")

### Real-Time Transcription
- **Dual Provider**: AssemblyAI or Deepgram
- **Speaker Diarization**: Multi-speaker detection with labels
- **Speaker Context**: Maps Speaker 0/1 to patient/clinician names from chart
- **Medical Vocabulary**: 500+ terms for improved accuracy
- **Specialty Auto-Detection**: Detects cardiology/pulmonology/orthopedics/neurology/pediatrics from ICD-10
- **Transcript Preview**: Review word count, detected topics before generating note

### AI Clinical Documentation
- **Note Types**: SOAP, Progress Note, H&P, Consult Note
- **Auto-Detection**: Analyzes transcript to suggest appropriate note format
- **Medical Coding**: ICD-10 (90+ codes) and CPT (100+ codes) with modifier support
- **CPT Modifiers**: 20+ modifiers (-25, -59, LT/RT, etc.) with auto-detection
- **Preview Before Generate**: See captured topics, word count, re-record option
- **Edit Before Save**: Modify AI-generated notes before saving
- **Sign-Off Workflow**: Confirmation dialog with clinician attestation
- **Template + AI**: Works with or without Claude API

### Speech Feedback (NEW)
- **Action Confirmations**: "Patient loaded", "Recording started", "Note saved"
- **Allergy Warnings**: Critical allergies automatically spoken aloud when patient loads
- **Safety-First**: Allergy warnings always active, even when feedback disabled
- **Error Announcements**: Spoken alerts for connection issues
- **Toggleable**: Say "speech feedback" to enable/disable
- **Conversational EHR**: True hands-free, eyes-free operation

### EHR Integration
- **FHIR R4**: Standard compliance for all endpoints
- **Cerner**: Live sandbox connection
- **Multi-EHR**: Epic and Veradigm ready (credentials needed)
- **Clinical Notes**: Read existing notes from EHR (DocumentReference)
- **Care Plans**: Display patient care plans from EHR

### Offline Note Drafts (NEW)
- **Never Lose Work**: Notes automatically saved locally when offline or save fails
- **Auto-Sync**: Drafts upload automatically when connectivity restores
- **Voice Commands**: "sync notes", "show drafts", "delete draft [N]"
- **Retry Logic**: Up to 5 attempts per draft with error tracking
- **Persistent**: Drafts survive app restarts

## Architecture

```
mdx-vision-enterprise/
├── backend/          # Java Spring Boot + HAPI FHIR (Core API)
├── ai-service/       # Python AI Pipeline (AssemblyAI + Azure OpenAI)
├── ehr-proxy/        # Python FastAPI (EHR FHIR Proxy for AR glasses)
├── mobile/
│   └── android/      # Native Android (Vuzix Blade 2 compatible)
├── web/              # Next.js Dashboard (Admin + Clinician Portal)
├── infrastructure/   # Docker, Kubernetes, Azure configs
└── docs/             # API documentation, architecture diagrams
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Java 17, Spring Boot 3.2, HAPI FHIR 7.x |
| AI Pipeline | Python 3.11, FastAPI, AssemblyAI, Azure OpenAI |
| EHR Proxy | Python 3.11, FastAPI, httpx |
| Mobile | Native Android (Kotlin), Vuzix SDK |
| Web | Next.js 14, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 (Azure SQL compatible) |
| Cache | Redis 7 |
| Message Queue | Azure Service Bus |
| Real-time | Azure SignalR |

## Quick Start

### Prerequisites
- Java 17+ (OpenJDK)
- Node.js 20+
- Python 3.11+
- Android SDK 34
- PostgreSQL 16

### Run EHR Proxy (for AR glasses)

```bash
cd ehr-proxy
pip install fastapi uvicorn httpx pydantic websockets

# Set API keys for transcription (optional)
export ASSEMBLYAI_API_KEY=your_key
# OR
export TRANSCRIPTION_PROVIDER=deepgram
export DEEPGRAM_API_KEY=your_key

# Enable medical vocabulary boost (default: true)
export ENABLE_MEDICAL_VOCAB=true

python main.py
# API: http://localhost:8002
# Android emulator: http://10.0.2.2:8002
```

### Run Web Dashboard

```bash
cd web
npm install
npm run dev
# Dashboard: http://localhost:5173
```

### Build Android App

```bash
cd mobile/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

### Install on Emulator/Device

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.mdxvision.glasses/com.mdxvision.MainActivity
```

## EHR Systems Supported

| EHR | Status | Sandbox URL |
|-----|--------|-------------|
| Cerner (Oracle Health) | **Working** | fhir-open.cerner.com |
| Epic | Ready | fhir.epic.com |
| Veradigm (Allscripts) | Ready | fhir.fhirpoint.open.allscripts.com |
| MEDITECH | Planned | - |
| athenahealth | Planned | - |

## API Endpoints

### EHR Proxy (Port 8002)

```
# Patient Data
GET  /api/v1/patient/{id}          # Get patient summary
GET  /api/v1/patient/{id}/display  # AR-optimized display
GET  /api/v1/patient/search?name=  # Search by name
GET  /api/v1/patient/mrn/{mrn}     # Lookup by MRN (wristband)
GET  /api/v1/patient/{id}/notes    # Get patient's saved notes

# Clinical Notes
POST /api/v1/notes/generate        # Generate full clinical note
POST /api/v1/notes/quick           # Quick note for AR display
POST /api/v1/notes/detect-type     # Auto-detect note type from transcript
POST /api/v1/notes/save            # Save note
GET  /api/v1/notes/{id}            # Retrieve saved note

# Transcription
GET  /api/v1/transcription/status  # Check transcription config
POST /api/v1/transcription/detect-specialty  # Detect specialties from conditions
WS   /ws/transcribe                # Real-time transcription (default provider)
WS   /ws/transcribe?specialties=   # With specialty vocabulary (cardiology,pulmonology,etc)
WS   /ws/transcribe/{provider}     # Transcription with specific provider
```

### Test Cerner

```bash
# Get patient
curl http://localhost:8002/api/v1/patient/12724066

# Generate SOAP note with ICD-10/CPT codes
curl -X POST http://localhost:8002/api/v1/notes/quick \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Patient has chest pain and shortness of breath"}'
```

## Verticals

1. **Healthcare** - Physicians, Nurses, EMTs
2. **Military** - Combat Medics, Medevac, Infantry
3. **First Responders** - Firefighters, Police, EMS
4. **Accessibility** - Vision impaired, Dementia care

## Compliance

- HIPAA (Healthcare)
- SOC 2 Type II (Enterprise)
- DoD IL4/IL5 (Military)
- ADA Section 508 (Accessibility)

## License

Proprietary - MDx Vision Inc.
