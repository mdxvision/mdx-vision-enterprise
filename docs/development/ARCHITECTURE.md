# MDx Vision - System Architecture

## System Overview

MDx Vision is an AR smart glasses platform for healthcare documentation built on a microservices architecture with voice-first interaction.

## Architecture Diagram

```
┌─────────────────┐
│  Vuzix Blade 2  │  (AR Smart Glasses)
│  Android App    │
└────────┬────────┘
         │ HTTPS + WebSocket
         ▼
┌─────────────────┐
│   EHR Proxy     │  (Python FastAPI, Port 8002)
│  - Transcription│
│  - RAG/AI       │
│  - Health Equity│
└────────┬────────┘
         │ FHIR R4
         ▼
┌─────────────────┐
│  EHR Systems    │  (Cerner, Epic, etc.)
│  FHIR APIs      │
└─────────────────┘

         ┌────────────────┐
         │ Web Dashboard  │  (Next.js 14, Port 5173)
         │ - Billing      │
         │ - Device Mgmt  │
         │ - Audit Logs   │
         └────────────────┘
```

## Technology Stack

### Mobile (Vuzix Blade 2)
- **Platform:** Android 11 (API Level 30)
- **Language:** Kotlin
- **UI:** Native Android Views (voice-first, minimal UI)
- **SDK:** Vuzix HUD SDK 2.9.0
- **Hardware:** Vuzix Blade 2 AR glasses (1280x720 display)

### EHR Proxy (Backend API)
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **AI:** Anthropic Claude API (claude-3-5-sonnet)
- **Transcription:** AssemblyAI / Deepgram
- **Noise Reduction:** RNNoise (Mozilla)
- **RAG:** ChromaDB + SentenceTransformers
- **Port:** 8002

### Web Dashboard
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **UI:** Tailwind CSS
- **Charts:** Recharts
- **Port:** 5173

### Backend (Legacy)
- **Language:** Java 17
- **Framework:** Spring Boot
- **FHIR:** HAPI FHIR R4
- **Port:** 8080
- **Note:** Being replaced by EHR Proxy

## Data Flow

### 1. Voice Recognition Flow
```
Mic → AudioStreamingService → WebSocket → RNNoise → AssemblyAI/Deepgram → Android Display
```

### 2. Patient Lookup Flow
```
Voice Command → MainActivity → EHR Proxy → FHIR API → EHR System → Patient Data Display
```

### 3. Note Generation Flow
```
Transcript → EHR Proxy → RAG Query → Claude API → SOAP Note → Display → Push to EHR
```

### 4. Proactive Alerts Flow
```
Patient Load → Minerva Proactive Endpoint → Analyze Labs/Vitals/Gaps → TTS Alert → Vuzix HUD
```

## Network Configuration

### Android Emulator
- **Localhost Access:** `10.0.2.2` (Android emulator's host loopback)
- **EHR Proxy:** `http://10.0.2.2:8002`
- **Web Dashboard:** `http://10.0.2.2:5173`
- **Backend:** `http://10.0.2.2:8080`

### Vuzix Device
- **Wi-Fi Required:** Device and development machine must be on same network
- **EHR Proxy:** `http://<your-machine-ip>:8002`
- **Discovery:** Use mDNS or configure static IP

## Key Components

### Android App (`/mobile/android`)

#### MainActivity.kt
- Central activity for all app functionality
- Voice command parsing and routing
- Patient data display
- Minerva wake word detection
- TTS management
- Vuzix HUD integration

#### AudioStreamingService.kt
- Foreground service for continuous audio streaming
- WebSocket connection to transcription endpoint
- RNNoise noise reduction
- Wake word detection ("Hey MDx", "Hey Minerva")

#### BarcodeScannerActivity.kt
- QR code and barcode scanning
- Patient wristband scanning
- Device pairing via QR code

#### VoiceCommandProcessor.kt
- Intent parsing from voice commands
- Multi-command chaining
- Indirect command resolution

#### GestureDetector.kt
- Head gesture recognition (nod, shake, wink)
- Touchpad DPAD navigation
- Proximity sensor for auto-lock

### EHR Proxy (`/ehr-proxy`)

#### main.py
- FastAPI application entry point
- All API route definitions
- WebSocket transcription endpoint
- CORS configuration

#### transcription.py
- AssemblyAI and Deepgram integration
- Real-time streaming transcription
- Speaker diarization
- Medical vocabulary boost

#### noise_reduction.py
- RNNoise integration
- Audio preprocessing
- Sample rate conversion

#### medical_vocabulary.py
- 500+ medical term dictionary
- Specialty-specific vocabularies
- Keyword detection for code mapping

#### rag_knowledge.py
- ChromaDB vector database
- Clinical guideline ingestion
- Semantic search for SOAP notes
- Citation generation

#### health_equity.py
- Racial medicine alerts
- Cultural care preferences
- SDOH screening
- Health literacy assessment
- Interpreter integration

### Web Dashboard (`/web`)

#### /app/dashboard/
- `billing/` - Claims submission, ICD-10/CPT lookup
- `dnfb/` - Discharged Not Final Billed tracking
- `devices/` - Device management, pairing, remote wipe
- `audit/` - HIPAA audit log viewer
- `knowledge/` - RAG update management
- `settings/` - Health equity preferences

### Backend (Legacy) (`/backend`)

#### UnifiedEhrService.java
- Unified interface for all EHR connections
- FHIR R4 resource mapping

#### CernerFhirService.java
- Cerner/Oracle Health integration
- OAuth 2.0 authentication

#### EpicFhirService.java
- Epic integration (in progress)
- MyChart patient access

## Database & Storage

### ChromaDB (Vector Database)
- **Location:** `./data/chroma_db`
- **Purpose:** RAG knowledge base
- **Embeddings:** SentenceTransformer (all-MiniLM-L6-v2)
- **Collections:** clinical_guidelines, pubmed_articles

### Android Local Storage
- **EncryptedSharedPreferences:** PHI data (AES-256-GCM)
- **Room Database:** Offline note drafts
- **File Storage:** Audit logs, voiceprint embeddings

### Web Dashboard
- **Backend:** To be implemented (currently mock data)
- **Planned:** PostgreSQL for audit logs, user management

## Security

### Device Authentication
- **TOTP:** Google Authenticator/Authy integration
- **Voiceprint:** SpeechBrain ECAPA-TDNN embeddings
- **Proximity Lock:** Auto-lock when glasses removed
- **Session Tokens:** 12-hour expiration

### Data Encryption
- **At Rest:** AES-256-GCM via Android Keystore
- **In Transit:** HTTPS/TLS for all API calls
- **WebSocket:** WSS for transcription stream

### HIPAA Compliance
- **Audit Logging:** All PHI access logged with timestamps
- **Session Timeout:** 5-minute inactivity lock
- **Remote Wipe:** From web dashboard
- **No Hard Deletes:** Soft deletes with audit trail

## Supported Hardware

### Primary Target
- **Vuzix Blade 2** (1280x720, Android 11, Vuzix SDK 2.9.0)

### Also Supports
- Vuzix Shield
- Google Glass Enterprise Edition 2
- RealWear Navigator 500
- Android XR devices (future)
- Ray-Ban Meta smart glasses (companion app in development)

## Integration Points

### FHIR R4 Resources Used
- Patient
- Observation (vitals, labs)
- AllergyIntolerance
- MedicationRequest
- Condition
- DocumentReference (clinical notes)
- CarePlan
- ServiceRequest (orders)
- Claim (billing)

### External APIs
- **Anthropic Claude API:** SOAP note generation, Minerva AI
- **AssemblyAI:** Real-time transcription, speaker diarization
- **Deepgram:** Alternative transcription provider
- **NCBI E-utilities:** PubMed integration for RAG

## Deployment

### Development
- EHR Proxy: `python main.py` (localhost:8002)
- Web: `npm run dev` (localhost:5173)
- Android: Build and install APK via ADB

### Production (Planned)
- EHR Proxy: Docker container on AWS/GCP
- Web: Vercel/Netlify deployment
- Android: Google Play Store (enterprise distribution)

## Performance Characteristics

### Transcription Latency
- **Interim Results:** ~200-500ms
- **Final Results:** ~1-2 seconds
- **RNNoise Processing:** <50ms overhead

### API Response Times
- **Patient Lookup:** ~500ms (depends on EHR)
- **SOAP Note Generation:** ~3-5 seconds (Claude API)
- **RAG Query:** ~100-200ms (ChromaDB)
- **Minerva Chat:** ~2-4 seconds

### Resource Usage
- **Android App:** ~150MB RAM, minimal battery impact (voice-activated)
- **EHR Proxy:** ~500MB RAM, 1-2% CPU idle
- **ChromaDB:** ~200MB RAM, grows with knowledge base

## Monitoring & Logging

### Android Logs
- **Logcat:** Standard Android logging
- **File Logging:** `ehr-proxy/logs/audit.log` (HIPAA audit trail)

### EHR Proxy Logs
- **Console:** FastAPI server logs
- **File:** Rotating logs in `logs/` directory
- **Audit:** Structured JSON logs for PHI access

### Error Tracking
- **Planned:** Sentry integration for production
