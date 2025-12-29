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
- `ehr-proxy/transcription.py` - AssemblyAI/Deepgram dual-provider abstraction
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

## Environment Variables

```bash
# Transcription
TRANSCRIPTION_PROVIDER=assemblyai  # or "deepgram"
ASSEMBLYAI_API_KEY=your_key
DEEPGRAM_API_KEY=your_key

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
