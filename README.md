# MDx Vision - Enterprise Healthcare Platform

Real-time AI-powered clinical documentation system with AR smart glasses integration.

**Patent:** US 15/237,980 - Voice-activated AR glasses for healthcare documentation

## Current Status (Dec 2024)

| Component | Status | Notes |
|-----------|--------|-------|
| Android/Vuzix App | **Working** | Voice commands, patient lookup |
| Cerner Integration | **Working** | Live sandbox data |
| Epic Integration | Pending | Credentials needed |
| Veradigm Integration | Ready | Service implemented |
| AI Clinical Notes | Ready | Python service ready |
| Web Dashboard | **Working** | localhost:5173 |
| Camera/Barcode | Pending | Patient wristband scan |

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
pip install fastapi uvicorn httpx pydantic
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
GET  /api/v1/patient/{id}        # Get patient summary
GET  /api/v1/patient/{id}/display # AR-optimized display
GET  /api/v1/patient/search?name= # Search by name
GET  /api/v1/patient/mrn/{mrn}   # Lookup by MRN (wristband)
```

### Test Cerner

```bash
curl http://localhost:8002/api/v1/patient/12724066
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
