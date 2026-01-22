# CLAUDE.md - MDx Vision Development Context

This file provides context for Claude Code when working on this project.

## Project Overview

MDx Vision is an AR smart glasses platform for healthcare documentation. It implements **US Patent 15/237,980** - voice-activated AR glasses that connect to EHR systems.

**Key Features:**
- Voice-activated patient lookup from EHR
- Wake word detection ("Hey MDx" and "Hey Minerva")
- Real-time transcription via AssemblyAI/Deepgram with RNNoise
- AI-powered SOAP note generation with RAG
- Ambient Clinical Intelligence (ACI)
- Health equity features (racial medicine awareness, cultural care, SDOH)

## Key Directories

```
/backend                    # Java Spring Boot + HAPI FHIR
/ai-service                 # Python AI pipeline
/ehr-proxy                  # Python FastAPI proxy (port 8002)
/mobile/android             # Native Android app (Vuzix Blade 2)
/web                        # Next.js 14 dashboard (port 5173)
```

## Key Documents

**Development (docs/development/):**
- `FEATURES.md` - Complete feature checklist (98+ features)
- `MINERVA.md` - Minerva AI Assistant implementation plan
- `VOICE_COMMANDS.md` - Comprehensive voice command reference
- `TESTING.md` - Test strategy and manual testing checklist

**EHR Integration (docs/ehr/):**
- `EHR_ACCESS_GUIDE.md` - Detailed registration instructions (29 platforms)
- `EHR_IMPLEMENTATIONS.md` - Current integration status

**Clinical Research (docs/clinical/):**
- `RACIAL_MEDICINE_DISPARITIES.md` - Racial medicine disparities research
- `CULTURAL_CARE_PREFERENCES.md` - Cultural care implementation guide

**Business (docs/business/):**
- `SALES_MATERIALS.md` - Index of all sales/marketing materials
- `PRICING.md`, `INVESTOR.md`, `STRATEGIC_ROADMAP.md`, `GAP_CLOSURE_PLAN.md`

**Planning (docs/planning/):**
- `CONVERSATIONS.md` - Session logs, decisions, progress tracking
- `JARVIS_FEATURES_PLAN.md` - Future AI features roadmap

## Current Development Focus

### Working Components
- **Android App**: Voice recognition, patient lookup, transcription, ambient mode
- **Cerner Integration**: Live FHIR R4 sandbox (patient ID: 12724066)
- **EHR Proxy**: FastAPI service with transcription, RAG, health equity APIs
- **Web Dashboard**: Next.js 14 with billing, DNFB, audit logs, device management
- **Minerva AI**: Wake word activation, proactive alerts, RAG-grounded responses

### Core Voice Commands
Patient: "load patient", "find patient", "scan wristband", "show vitals/allergies/meds/labs"
Documentation: "start note", "live transcribe", "ambient mode", "generate note"
AI Assistant: "Hey Minerva [question]", "differential diagnosis", "suggest workup"
See `FEATURES.md` for complete command list.

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

**Test Coverage: 2,879+ automated tests (99% pass rate)**

```bash
# EHR Proxy (2,207 tests) - pytest
cd ehr-proxy && pytest tests/ -v

# Android Unit (464 tests) - JUnit
cd mobile/android && ./gradlew test

# Web Dashboard (106 tests) - Vitest
cd web && npm test

# Android E2E (54 tests) - requires device
cd mobile/android && ./gradlew connectedAndroidTest
```

**Test locations:** `backend/src/test/`, `ehr-proxy/tests/`, `web/src/__tests__/`, `mobile/android/app/src/test/`
**Manual testing checklist:** `docs/development/MANUAL_TESTING_CHECKLIST.md`

## Key Files

**Android:** `MainActivity.kt`, `AudioStreamingService.kt`, `BarcodeScannerActivity.kt`
**EHR Proxy:** `main.py`, `transcription.py`, `noise_reduction.py`, `medical_vocabulary.py`
**Backend:** `UnifiedEhrService.java`, `CernerFhirService.java`, `EpicFhirService.java`
**Web:** `web/src/app/dashboard/` - pages for billing, DNFB, devices, audit, knowledge

## API Endpoints

**EHR Proxy (port 8002):**
- `/api/v1/patient/{id}` - Get patient summary
- `/api/v1/patient/search?name=` - Search patients
- `/api/v1/notes/generate` - Generate SOAP note
- `/api/v1/minerva/chat` - Minerva AI assistant
- `/api/v1/copilot/chat` - Clinical co-pilot
- `/ws/transcribe` - Real-time transcription WebSocket

**Test patient:** Cerner sandbox patient ID `12724066` (SMARTS SR., NANCYS II, DOB: 1990-09-15)

## Architecture

**Data Flow:** Vuzix Glasses → Android App → EHR Proxy (port 8002) → FHIR APIs → EHR
**Transcription:** Mic → WebSocket → RNNoise → AssemblyAI/Deepgram → Android display
**Network:** Android emulator uses `10.0.2.2` to reach localhost, Web on port 5173, Backend on port 8080

**HMD Support:** Vuzix Blade 2 (primary), Vuzix Shield, Google Glass Enterprise, RealWear Navigator, Android XR devices

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

## Feature Status

**98 features implemented** - See `FEATURES.md` for complete checklist.

**Key feature categories:**
- Clinical Documentation: SOAP notes, templates, voice editing, ambient mode
- Safety & Alerts: Critical vitals/labs, drug interactions, maternal health monitoring
- Health Equity: Racial medicine awareness, cultural care, SDOH, health literacy, interpreter integration
- AI Intelligence: Minerva assistant, RAG knowledge system, differential diagnosis, clinical co-pilot
- Billing & Revenue: Claims submission, DNFB tracking, ICD-10/CPT databases
- Security: Voiceprint auth, device management, TOTP, encryption, audit logging
- Workflow: Patient worklist, care gap detection, pre-visit prep, procedure checklists

## Current Focus

**Minerva AI Assistant (Feature #97):**
- Phase 1-3: COMPLETE (RAG chat, wake word, proactive alerts)
- Phase 4-6: Pending (reasoning modes, voice actions, learning)
- See `MINERVA.md` for full implementation plan

**EHR Integration Status:**
- **Live:** Cerner/Oracle (client ID: 0fab9b20-adc8-4940-bbf6-82034d1d39ab)
- **Pending:** Epic, Veradigm
- **Documented:** 29 EHR platforms (see `EHR_ACCESS_GUIDE.md`)
