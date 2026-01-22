# MDx Vision - API Reference

## Base URLs

- **EHR Proxy:** `http://localhost:8002` (development)
- **Backend:** `http://localhost:8080` (legacy)
- **Web Dashboard:** `http://localhost:5173` (frontend only)

## Authentication

### Headers
```
X-Device-ID: <device_uuid>           # For voiceprint enforcement
Authorization: Bearer <token>        # For web dashboard (future)
```

## EHR Proxy API (Port 8002)

### Patient Operations

#### Get Patient Summary
```
GET /api/v1/patient/{patient_id}
```

**Response:**
```json
{
  "id": "12724066",
  "name": "SMARTS SR., NANCYS II",
  "dob": "1990-09-15",
  "mrn": "12724066",
  "gender": "female",
  "phone": "816-555-1212",
  "address": "123 Main St, Kansas City, MO",
  "photo_url": "data:image/jpeg;base64,...",
  "allergies": [
    {"substance": "Penicillin", "severity": "severe", "reaction": "Anaphylaxis"}
  ],
  "medications": [
    {"name": "Lisinopril", "dose": "10mg", "frequency": "daily"}
  ],
  "conditions": [
    {"code": "I10", "display": "Essential hypertension"}
  ],
  "vitals": {
    "bp": "142/88",
    "hr": "78",
    "temp": "98.6F",
    "spo2": "97%"
  }
}
```

#### Search Patients
```
GET /api/v1/patient/search?name=Smith&dob=1990-01-01&mrn=12345
```

**Query Parameters:**
- `name` (optional): Patient name (first or last)
- `dob` (optional): Date of birth (YYYY-MM-DD)
- `mrn` (optional): Medical record number

**Response:**
```json
{
  "patients": [
    {"id": "123", "name": "Smith, John", "dob": "1990-01-01", "mrn": "12345"}
  ],
  "count": 1
}
```

### Clinical Documentation

#### Generate SOAP Note
```
POST /api/v1/notes/generate
Content-Type: application/json

{
  "transcript": "Patient complains of chest pain...",
  "patient_id": "12724066",
  "template": "soap",
  "use_rag": true
}
```

**Response:**
```json
{
  "note": {
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "..."
  },
  "icd10_codes": [
    {"code": "R07.9", "description": "Chest pain, unspecified"}
  ],
  "cpt_codes": [
    {"code": "99214", "description": "Office visit, level 4"}
  ],
  "rag_enhanced": true,
  "citations": [
    "[1] AHA Chest Pain Guidelines 2021"
  ]
}
```

#### Quick Note Generation
```
POST /api/v1/notes/quick
Content-Type: application/json

{
  "patient_id": "12724066",
  "chief_complaint": "Chest pain",
  "hpi": "Patient reports...",
  "exam": "Alert and oriented...",
  "assessment": "Likely GERD",
  "plan": "Start omeprazole..."
}
```

#### Push Note to EHR
```
POST /api/v1/notes/push
Content-Type: application/json

{
  "patient_id": "12724066",
  "note_content": "SOAP note text...",
  "note_type": "soap",
  "signed_by": "Dr. Jane Smith",
  "signed_at": "2026-01-22T10:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "document_id": "doc-12345",
  "status": "current"
}
```

### AI Assistants

#### Minerva Chat
```
POST /api/v1/minerva/chat
Content-Type: application/json

{
  "message": "What's the differential for chest pain?",
  "patient_id": "12724066",
  "conversation_history": [
    {"role": "user", "content": "Previous question"},
    {"role": "assistant", "content": "Previous answer"}
  ]
}
```

**Response:**
```json
{
  "response": "For chest pain, consider: 1) Cardiac (MI, angina)...",
  "sources": ["AHA Guidelines 2021", "JAMA 2023"],
  "conversation_id": "conv-123"
}
```

#### Minerva Proactive Alerts
```
GET /api/v1/minerva/proactive/{patient_id}
```

**Response:**
```json
{
  "alerts": [
    {
      "category": "critical",
      "type": "abnormal_lab",
      "message": "Potassium 6.8 mmol/L (critically high)",
      "priority": 10,
      "spoken_message": "Critical alert: Potassium is 6.8, well above normal range"
    }
  ],
  "spoken_summary": "I found 2 critical alerts and 1 care gap for this patient.",
  "priority": "critical"
}
```

#### Clinical Co-pilot
```
POST /api/v1/copilot/chat
Content-Type: application/json

{
  "question": "What should I order for suspected sepsis?",
  "patient_context": {
    "conditions": ["diabetes", "hypertension"],
    "medications": ["metformin", "lisinopril"],
    "allergies": ["penicillin"]
  }
}
```

**Response:**
```json
{
  "response": "For suspected sepsis, I recommend:\n• Blood cultures x2\n• CBC with diff\n• Lactate level",
  "follow_up_prompts": ["Tell me more about lactate", "What antibiotics?"],
  "actionable_items": [
    {"type": "order", "value": "Blood cultures"}
  ]
}
```

### Transcription

#### WebSocket Transcription
```
WebSocket: ws://localhost:8002/ws/transcribe?patient_id=12724066&noise_reduction=true
```

**Message Format (Client → Server):**
```json
{
  "audio": "base64_encoded_audio_chunk",
  "format": "pcm16",
  "sample_rate": 16000
}
```

**Message Format (Server → Client):**
```json
{
  "type": "interim",
  "text": "Patient complains of",
  "confidence": 0.95,
  "speaker": "Speaker 0"
}

{
  "type": "final",
  "text": "Patient complains of chest pain.",
  "confidence": 0.98,
  "speaker": "Speaker 0",
  "speaker_context": "Patient (Nancy Smarts)"
}

{
  "type": "voice_command",
  "command": "stop transcription"
}
```

### Clinical Data

#### Get Vitals
```
GET /api/v1/patient/{patient_id}/vitals?count=10
```

#### Get Allergies
```
GET /api/v1/patient/{patient_id}/allergies
```

#### Get Medications
```
GET /api/v1/patient/{patient_id}/medications
```

#### Get Lab Results
```
GET /api/v1/patient/{patient_id}/labs?category=chemistry
```

#### Get Conditions
```
GET /api/v1/patient/{patient_id}/conditions
```

#### Get Care Plans
```
GET /api/v1/patient/{patient_id}/care-plans
```

#### Get Clinical Notes
```
GET /api/v1/patient/{patient_id}/notes?count=5
```

### Orders

#### Create Orders
```
POST /api/v1/orders/create
Content-Type: application/json

{
  "patient_id": "12724066",
  "orders": [
    {
      "type": "lab",
      "code": "80048",
      "display": "Basic Metabolic Panel"
    },
    {
      "type": "medication",
      "code": "RxNorm:197361",
      "display": "Amoxicillin 500mg",
      "dosage": "500mg",
      "frequency": "TID",
      "duration": "10 days"
    }
  ]
}
```

#### Push Orders to EHR
```
POST /api/v1/orders/push
Content-Type: application/json

{
  "patient_id": "12724066",
  "order_ids": ["order-1", "order-2"]
}
```

### Alerts & Monitoring

#### Critical Lab/Vital Alerts
```
GET /api/v1/patient/{patient_id}/critical-alerts
```

**Response:**
```json
{
  "critical_labs": [
    {"name": "Potassium", "value": 6.8, "unit": "mmol/L", "range": "3.5-5.0"}
  ],
  "critical_vitals": [
    {"name": "BP", "value": "210/120", "threshold": "180/110"}
  ],
  "drug_interactions": [
    {"drug1": "Warfarin", "drug2": "Aspirin", "severity": "high"}
  ]
}
```

#### Care Gap Detection
```
GET /api/v1/patient/{patient_id}/care-gaps?priority=high
```

**Response:**
```json
{
  "gaps": [
    {
      "type": "screening",
      "name": "Mammogram",
      "overdue_by": "180 days",
      "priority": 5,
      "guideline": "USPSTF"
    }
  ],
  "spoken_summary": "3 high-priority care gaps identified"
}
```

#### Pre-Visit Prep
```
GET /api/v1/patient/{patient_id}/prep
```

**Response:**
```json
{
  "alerts": [
    {"category": "critical", "message": "..."},
    {"category": "care_gap", "message": "..."}
  ],
  "spoken_summary": "Heads up: 2 critical alerts and 3 care gaps",
  "hud_summary": "⚠️ 2 Critical | 📋 3 Gaps"
}
```

### Health Equity

#### Racial Medicine Alerts
```
GET /api/v1/racial-medicine/alerts?patient_id={patient_id}
```

#### Cultural Care Preferences
```
GET /api/v1/cultural-care/preferences/{patient_id}
```

#### SDOH Screening
```
POST /api/v1/sdoh/screen
Content-Type: application/json

{
  "patient_id": "12724066",
  "factors": ["food_insecurity", "housing_unstable"]
}
```

#### Health Literacy Assessment
```
POST /api/v1/literacy/assess
Content-Type: application/json

{
  "patient_id": "12724066",
  "confidence": "somewhat"
}
```

#### Interpreter Request
```
POST /api/v1/interpreter/request
Content-Type: application/json

{
  "patient_id": "12724066",
  "language": "spanish",
  "type": "video"
}
```

### Billing

#### Create Claim
```
POST /api/v1/billing/claim
Content-Type: application/json

{
  "patient_id": "12724066",
  "note_id": "note-123",
  "diagnoses": [
    {"code": "I10", "description": "Essential hypertension"}
  ],
  "procedures": [
    {"code": "99214", "description": "Office visit, level 4", "modifiers": ["-25"]}
  ]
}
```

#### DNFB Summary
```
GET /api/v1/dnfb/summary
```

**Response:**
```json
{
  "total_accounts": 42,
  "total_revenue": 125000,
  "aging": {
    "0-3_days": 5,
    "4-7_days": 12,
    "8-14_days": 15,
    "15-30_days": 8,
    "31_plus_days": 2
  },
  "by_reason": {
    "coding_incomplete": 18,
    "documentation_missing": 12,
    "charges_pending": 8,
    "prior_auth_issues": 4
  }
}
```

### Audit & Compliance

#### Audit Logs
```
GET /api/v1/audit/logs?patient_id={id}&event_type={type}&start_date={date}
```

#### Audit Statistics
```
GET /api/v1/audit/stats?start_date={date}&end_date={date}
```

### RAG Knowledge Base

#### Query Knowledge Base
```
POST /api/v1/rag/query
Content-Type: application/json

{
  "query": "hypertension treatment guidelines",
  "n_results": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "document": "AHA Guidelines recommend...",
      "source": "AHA 2023",
      "score": 0.92
    }
  ]
}
```

#### Add Document to Knowledge Base
```
POST /api/v1/rag/add-document
Content-Type: application/json

{
  "content": "Full text of medical guideline...",
  "metadata": {
    "source": "NEJM",
    "publication_date": "2023-05-15",
    "category": "cardiology"
  }
}
```

#### Knowledge Update Status
```
GET /api/v1/updates/dashboard
```

### Device Management

#### Pair Device
```
POST /api/v1/auth/device/pair
Content-Type: application/json

{
  "device_id": "vuzix-abc123",
  "device_name": "Dr. Smith's Glasses",
  "totp_secret": "BASE32_SECRET"
}
```

#### Verify TOTP
```
POST /api/v1/auth/device/verify
Content-Type: application/json

{
  "device_id": "vuzix-abc123",
  "totp_code": "472915"
}
```

#### Enroll Voiceprint
```
POST /api/v1/auth/voiceprint/enroll
Content-Type: application/json
X-Device-ID: vuzix-abc123

{
  "audio_samples": ["base64_audio1", "base64_audio2", "base64_audio3"]
}
```

**Response:**
```json
{
  "success": true,
  "embedding_id": "embed-123"
}
```

#### Verify Voiceprint
```
POST /api/v1/auth/voiceprint/verify
Content-Type: application/json
X-Device-ID: vuzix-abc123

{
  "audio_sample": "base64_audio"
}
```

**Response:**
```json
{
  "verified": true,
  "confidence": 0.87,
  "session_token": "token-abc123"
}
```

#### Remote Wipe Device
```
POST /api/v1/devices/{device_id}/wipe
```

## Test Data

### Cerner Sandbox

**Base URL:** `https://fhir-myrecord.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d`

**Patient IDs:**
- `12724066` - SMARTS SR., NANCYS II (DOB: 1990-09-15) ⭐ Primary test patient
- `12724067` - SMART, WILMA (DOB: 1965-01-01)
- `12724068` - SMART, NANCY (DOB: 1980-05-01)

**Client ID:** `0fab9b20-adc8-4940-bbf6-82034d1d39ab`

**Scopes:** `patient/Patient.read patient/Observation.read patient/AllergyIntolerance.read`

### Mock Data Patterns

#### Test Voice Commands
```
"load patient twelve million seven hundred twenty four thousand sixty six"
"load patient 12724066"
"load patient Nancy Smarts"
"show vitals"
"show allergies"
"show medications"
"start ambient mode"
"Hey Minerva what's the differential for chest pain"
```

#### Test Medical Terms
- ICD-10: `I10`, `E11.9`, `J44.0`, `N39.0`, `R07.9`
- CPT: `99213`, `99214`, `99215`, `80048`, `85025`
- LOINC: `2951-2` (sodium), `2823-3` (potassium), `2345-7` (glucose)
- RxNorm: `197361` (amoxicillin), `314076` (lisinopril)

## Error Responses

### Standard Error Format
```json
{
  "error": "Patient not found",
  "code": "PATIENT_NOT_FOUND",
  "details": "No patient with ID 99999999",
  "timestamp": "2026-01-22T10:30:00Z"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid auth)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error
- `503` - Service Unavailable (EHR down)

## Rate Limits

- **Transcription WebSocket:** No limit (continuous stream)
- **API Endpoints:** 100 requests/minute per device
- **AI Endpoints:** 10 requests/minute (Claude API limits)
- **PubMed Ingestion:** 3 requests/second (NCBI E-utilities)

## Deprecation Notice

### Legacy Backend (Port 8080)
The Java Spring Boot backend is being replaced by the Python EHR Proxy. All new features are implemented in the EHR Proxy only.

**Migration Timeline:**
- Q1 2026: EHR Proxy feature parity
- Q2 2026: Deprecate backend endpoints
- Q3 2026: Remove legacy backend
