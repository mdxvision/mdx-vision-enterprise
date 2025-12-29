# CLAUDE.md - MDx Vision Development Context

This file provides context for Claude Code when working on this project.

## Project Overview

MDx Vision is an AR smart glasses platform for healthcare documentation. It implements **US Patent 15/237,980** - voice-activated AR glasses that connect to EHR systems.

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
- **Android App**: Native Kotlin app with voice recognition, patient lookup
- **Cerner Integration**: Live FHIR R4 sandbox connection
- **EHR Proxy**: FastAPI service bridging AR glasses to EHR
- **Web Dashboard**: Next.js 14 running on port 5173

### In Progress
- Epic FHIR integration (awaiting credentials)
- Camera barcode scanning for patient wristbands

## Development Commands

### Android Build
```bash
cd mobile/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
./gradlew assembleDebug
```

### EHR Proxy
```bash
cd ehr-proxy
python main.py  # Runs on port 8002
```

### Web Dashboard
```bash
cd web
npm run dev  # Runs on port 5173
```

### Android Emulator
```bash
# Start emulator
emulator -avd MDxVision

# Install APK
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk

# Launch app
adb shell am start -n com.mdxvision.glasses/com.mdxvision.MainActivity
```

## Key Files

### Android App
- `mobile/android/app/src/main/java/com/mdxvision/MainActivity.kt` - Main activity with voice recognition
- `mobile/android/app/src/main/AndroidManifest.xml` - Permissions and Vuzix config

### EHR Integration
- `ehr-proxy/main.py` - FastAPI proxy for Cerner FHIR
- `backend/src/main/java/com/mdxvision/fhir/UnifiedEhrService.java` - Multi-EHR abstraction
- `backend/src/main/java/com/mdxvision/fhir/CernerFhirService.java` - Cerner client
- `backend/src/main/java/com/mdxvision/fhir/EpicFhirService.java` - Epic client
- `backend/src/main/java/com/mdxvision/fhir/VeradigmFhirService.java` - Veradigm client

### Configuration
- `backend/src/main/resources/application.yml` - All EHR endpoints and credentials

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

```bash
curl http://localhost:8002/api/v1/patient/12724066
```

## Patent Claims Implementation

See `FEATURES.md` for detailed checklist of patent claim implementations.

## Architecture Notes

### AR Glasses Data Flow
```
[Vuzix Blade 2]
    ↓ Voice Command
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

## Common Issues

### Java not found
```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
```

### ADB device not found
```bash
adb kill-server && adb start-server
```

### Port already in use
```bash
lsof -i :8002  # Find process
kill -9 <PID>  # Kill it
```
