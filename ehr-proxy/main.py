"""
MDx Vision - EHR Proxy Service
Connects AR glasses to Cerner (and other EHRs) via FHIR R4
Includes AI clinical note generation

Run: python main.py
Test: curl http://localhost:8002/api/v1/patient/12724066
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
import re
import json
import asyncio
import uuid
from datetime import datetime

# Import transcription service
from transcription import (
    create_session, get_session, end_session,
    TranscriptionSession, TRANSCRIPTION_PROVIDER
)

# Load code databases
def load_code_database(filename):
    """Load ICD-10 or CPT code database from JSON file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filename}: {e}")
        return {"codes": {}, "keywords": {}}

ICD10_DB = load_code_database("icd10_codes.json")
CPT_DB = load_code_database("cpt_codes.json")

app = FastAPI(
    title="MDx Vision EHR Proxy",
    description="Unified EHR access for AR glasses",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cerner Open Sandbox (no auth required)
CERNER_BASE_URL = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
FHIR_HEADERS = {"Accept": "application/fhir+json"}


class VitalSign(BaseModel):
    name: str
    value: str
    unit: str


class LabResult(BaseModel):
    name: str
    value: str
    unit: str
    status: str = ""
    date: str = ""


class Procedure(BaseModel):
    name: str
    date: str = ""
    status: str = ""


class Immunization(BaseModel):
    name: str
    date: str = ""
    status: str = ""


class Condition(BaseModel):
    name: str
    status: str = ""
    onset: str = ""
    category: str = ""


class PatientSummary(BaseModel):
    patient_id: str
    name: str
    date_of_birth: str
    gender: str
    mrn: Optional[str] = None
    vitals: List[VitalSign] = []
    allergies: List[str] = []
    medications: List[str] = []
    labs: List[LabResult] = []
    procedures: List[Procedure] = []
    immunizations: List[Immunization] = []
    conditions: List[Condition] = []
    display_text: str = ""


class SearchResult(BaseModel):
    patient_id: str
    name: str
    date_of_birth: str
    gender: str


# Clinical Notes Models
class NoteRequest(BaseModel):
    transcript: str
    patient_id: Optional[str] = None
    note_type: str = "SOAP"
    chief_complaint: Optional[str] = None


class SOAPNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str
    summary: str
    timestamp: str
    display_text: str = ""


# Claude API for AI-powered notes (optional)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")


async def fetch_fhir(endpoint: str) -> dict:
    """Fetch from Cerner FHIR API"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{CERNER_BASE_URL}/{endpoint}",
            headers=FHIR_HEADERS
        )
        if response.status_code == 200:
            return response.json()
        print(f"⚠️ FHIR fetch failed for {endpoint}: status={response.status_code}")
        return {}


def extract_patient_name(patient: dict) -> str:
    """Extract patient name from FHIR Patient resource"""
    names = patient.get("name", [])
    if names:
        return names[0].get("text", "Unknown")
    return "Unknown"


def extract_vitals(bundle: dict) -> List[VitalSign]:
    """Extract vitals from FHIR Observation bundle"""
    vitals = []
    for entry in bundle.get("entry", [])[:10]:
        obs = entry.get("resource", {})
        name = obs.get("code", {}).get("text", "Unknown")
        value_qty = obs.get("valueQuantity", {})
        value = str(value_qty.get("value", "?"))
        unit = value_qty.get("unit", "")
        vitals.append(VitalSign(name=name, value=value, unit=unit))
    return vitals


def extract_allergies(bundle: dict) -> List[str]:
    """Extract allergies from FHIR AllergyIntolerance bundle"""
    allergies = []
    for entry in bundle.get("entry", [])[:10]:
        allergy = entry.get("resource", {})
        name = allergy.get("code", {}).get("text", "Unknown")
        if name and name != "Unknown":
            allergies.append(name)
    return allergies


def extract_medications(bundle: dict) -> List[str]:
    """Extract medications from FHIR MedicationRequest bundle"""
    meds = []
    for entry in bundle.get("entry", [])[:10]:
        med = entry.get("resource", {})
        name = med.get("medicationCodeableConcept", {}).get("text", "Unknown")
        if name and name != "Unknown":
            meds.append(name)
    return meds


def extract_labs(bundle: dict) -> List[LabResult]:
    """Extract lab results from FHIR Observation bundle (laboratory category)"""
    labs = []
    for entry in bundle.get("entry", [])[:10]:
        obs = entry.get("resource", {})

        # Get lab name
        name = obs.get("code", {}).get("text", "")
        if not name:
            coding = obs.get("code", {}).get("coding", [])
            if coding:
                name = coding[0].get("display", "Unknown")

        # Get value
        value = "?"
        unit = ""
        if "valueQuantity" in obs:
            value = str(obs["valueQuantity"].get("value", "?"))
            unit = obs["valueQuantity"].get("unit", "")
        elif "valueString" in obs:
            value = obs["valueString"]
        elif "valueCodeableConcept" in obs:
            value = obs["valueCodeableConcept"].get("text", "?")

        # Get status and date
        status = obs.get("status", "")
        date = obs.get("effectiveDateTime", "")[:10] if obs.get("effectiveDateTime") else ""

        if name and name != "Unknown":
            labs.append(LabResult(
                name=name,
                value=value,
                unit=unit,
                status=status,
                date=date
            ))

    return labs


def extract_procedures(bundle: dict) -> List[Procedure]:
    """Extract procedures from FHIR Procedure bundle"""
    procedures = []
    for entry in bundle.get("entry", [])[:10]:
        proc = entry.get("resource", {})

        # Get procedure name
        name = proc.get("code", {}).get("text", "")
        if not name:
            coding = proc.get("code", {}).get("coding", [])
            if coding:
                name = coding[0].get("display", "Unknown")

        # Get date and status
        date = ""
        if "performedDateTime" in proc:
            date = proc["performedDateTime"][:10]
        elif "performedPeriod" in proc:
            date = proc["performedPeriod"].get("start", "")[:10]

        status = proc.get("status", "")

        if name and name != "Unknown":
            procedures.append(Procedure(
                name=name,
                date=date,
                status=status
            ))

    return procedures


def extract_immunizations(bundle: dict) -> List[Immunization]:
    """Extract immunizations from FHIR Immunization bundle"""
    immunizations = []
    for entry in bundle.get("entry", [])[:10]:
        imm = entry.get("resource", {})

        # Get vaccine name
        name = imm.get("vaccineCode", {}).get("text", "")
        if not name:
            coding = imm.get("vaccineCode", {}).get("coding", [])
            if coding:
                name = coding[0].get("display", "Unknown")

        # Get date
        date = ""
        if "occurrenceDateTime" in imm:
            date = imm["occurrenceDateTime"][:10]
        elif "date" in imm:
            date = imm["date"][:10]

        status = imm.get("status", "")

        if name and name != "Unknown":
            immunizations.append(Immunization(
                name=name,
                date=date,
                status=status
            ))

    return immunizations


def extract_conditions(bundle: dict) -> List[Condition]:
    """Extract conditions/problems from FHIR Condition bundle"""
    conditions = []
    for entry in bundle.get("entry", [])[:10]:
        cond = entry.get("resource", {})

        # Get condition name
        name = cond.get("code", {}).get("text", "")
        if not name:
            coding = cond.get("code", {}).get("coding", [])
            if coding:
                name = coding[0].get("display", "Unknown")

        # Get clinical status
        status = ""
        clinical_status = cond.get("clinicalStatus", {})
        if clinical_status:
            status_coding = clinical_status.get("coding", [])
            if status_coding:
                status = status_coding[0].get("code", "")

        # Get onset date
        onset = ""
        if "onsetDateTime" in cond:
            onset = cond["onsetDateTime"][:10]
        elif "onsetPeriod" in cond:
            onset = cond["onsetPeriod"].get("start", "")[:10] if cond["onsetPeriod"].get("start") else ""

        # Get category
        category = ""
        categories = cond.get("category", [])
        if categories:
            cat_coding = categories[0].get("coding", [])
            if cat_coding:
                category = cat_coding[0].get("display", cat_coding[0].get("code", ""))

        if name and name != "Unknown":
            conditions.append(Condition(
                name=name,
                status=status,
                onset=onset,
                category=category
            ))

    return conditions


def format_ar_display(summary: PatientSummary) -> str:
    """Format patient data for AR glasses display"""
    lines = [
        f"{summary.name} | {summary.gender.upper()} | DOB: {summary.date_of_birth}",
        "─" * 40,
    ]

    if summary.vitals:
        vital_str = " | ".join([f"{v.name}: {v.value}{v.unit}" for v in summary.vitals[:4]])
        lines.append(f"VITALS: {vital_str}")

    if summary.allergies:
        lines.append(f"⚠ ALLERGIES: {', '.join(summary.allergies[:5])}")

    if summary.medications:
        lines.append(f"💊 MEDS: {', '.join(summary.medications[:5])}")

    if summary.labs:
        lab_str = " | ".join([f"{l.name}: {l.value}{l.unit}" for l in summary.labs[:4]])
        lines.append(f"🔬 LABS: {lab_str}")

    if summary.procedures:
        proc_str = ", ".join([p.name for p in summary.procedures[:3]])
        lines.append(f"🏥 PROCEDURES: {proc_str}")

    if summary.immunizations:
        imm_str = ", ".join([i.name for i in summary.immunizations[:4]])
        lines.append(f"💉 IMMUNIZATIONS: {imm_str}")

    if summary.conditions:
        cond_str = ", ".join([c.name for c in summary.conditions[:4]])
        lines.append(f"📋 CONDITIONS: {cond_str}")

    return "\n".join(lines)


@app.get("/")
async def root():
    return {"service": "MDx Vision EHR Proxy", "status": "running", "ehr": "Cerner"}


@app.get("/api/v1/patient/{patient_id}", response_model=PatientSummary)
async def get_patient(patient_id: str):
    """Get patient summary by ID - optimized for AR glasses"""

    # Fetch patient demographics
    patient_data = await fetch_fhir(f"Patient/{patient_id}")
    if not patient_data or patient_data.get("resourceType") == "OperationOutcome":
        raise HTTPException(status_code=404, detail="Patient not found")

    # Extract basic info
    name = extract_patient_name(patient_data)
    dob = patient_data.get("birthDate", "Unknown")
    gender = patient_data.get("gender", "unknown")

    # Fetch vitals
    vitals_bundle = await fetch_fhir(f"Observation?patient={patient_id}&category=vital-signs&_count=10")
    vitals = extract_vitals(vitals_bundle)

    # Fetch allergies
    allergy_bundle = await fetch_fhir(f"AllergyIntolerance?patient={patient_id}&_count=10")
    allergies = extract_allergies(allergy_bundle)

    # Fetch medications
    med_bundle = await fetch_fhir(f"MedicationRequest?patient={patient_id}&_count=10")
    medications = extract_medications(med_bundle)

    # Fetch lab results
    lab_bundle = await fetch_fhir(f"Observation?patient={patient_id}&category=laboratory&_count=10")
    labs = extract_labs(lab_bundle)

    # Fetch procedures
    proc_bundle = await fetch_fhir(f"Procedure?patient={patient_id}&_count=10")
    procedures = extract_procedures(proc_bundle)

    # Fetch immunizations (may not be available in all sandboxes)
    try:
        imm_bundle = await fetch_fhir(f"Immunization?patient={patient_id}&_count=10")
        immunizations = extract_immunizations(imm_bundle)
    except Exception as e:
        print(f"⚠️ Could not fetch immunizations: {e}")
        immunizations = []

    # Fetch conditions/problems
    try:
        cond_bundle = await fetch_fhir(f"Condition?patient={patient_id}&_count=10")
        print(f"🔍 Condition bundle type: {cond_bundle.get('resourceType', 'N/A')}, entries: {len(cond_bundle.get('entry', []))}")
        conditions = extract_conditions(cond_bundle)
        print(f"✓ Fetched {len(conditions)} conditions")
    except Exception as e:
        print(f"⚠️ Could not fetch conditions: {e}")
        import traceback
        traceback.print_exc()
        conditions = []

    summary = PatientSummary(
        patient_id=patient_id,
        name=name,
        date_of_birth=dob,
        gender=gender,
        vitals=vitals,
        allergies=allergies,
        medications=medications,
        labs=labs,
        procedures=procedures,
        immunizations=immunizations,
        conditions=conditions
    )
    summary.display_text = format_ar_display(summary)

    return summary


@app.get("/api/v1/patient/{patient_id}/display")
async def get_patient_display(patient_id: str):
    """Get AR-optimized display text for patient"""
    summary = await get_patient(patient_id)
    return {"patient_id": patient_id, "display": summary.display_text}


@app.get("/api/v1/patient/search", response_model=List[SearchResult])
async def search_patients(name: str):
    """Search patients by name - for voice command 'Find patient...'"""
    bundle = await fetch_fhir(f"Patient?name={name}&_count=10")

    results = []
    for entry in bundle.get("entry", []):
        patient = entry.get("resource", {})
        results.append(SearchResult(
            patient_id=patient.get("id", ""),
            name=extract_patient_name(patient),
            date_of_birth=patient.get("birthDate", "Unknown"),
            gender=patient.get("gender", "unknown")
        ))

    return results


@app.get("/api/v1/patient/mrn/{mrn}", response_model=PatientSummary)
async def get_patient_by_mrn(mrn: str):
    """Get patient by MRN (wristband barcode scan)"""
    bundle = await fetch_fhir(f"Patient?identifier={mrn}&_count=1")

    entries = bundle.get("entry", [])
    if not entries:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_id = entries[0].get("resource", {}).get("id")
    return await get_patient(patient_id)


# ============ Clinical Notes API ============

async def generate_soap_with_claude(transcript: str, chief_complaint: str = None) -> dict:
    """Generate SOAP note using Claude API"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1024,
                "messages": [{
                    "role": "user",
                    "content": f"""Generate a SOAP note with ICD-10 and CPT codes from this clinical encounter transcript.

Chief Complaint: {chief_complaint or 'See transcript'}

Transcript:
{transcript}

Return a JSON object with these exact fields:
- subjective: Patient's reported symptoms and history
- objective: Observable findings, vitals, exam results
- assessment: Clinical assessment and diagnosis
- plan: Treatment plan and follow-up
- summary: 1-2 sentence summary
- icd10_codes: Array of objects with "code" and "description" for each suggested ICD-10 diagnosis code (max 5)
- cpt_codes: Array of objects with "code" and "description" for each suggested CPT procedure/service code (max 5)

Example formats:
icd10_codes: [{{"code": "J06.9", "description": "Acute upper respiratory infection"}}]
cpt_codes: [{{"code": "99213", "description": "Office visit, established patient, low complexity"}}]

Return ONLY valid JSON, no markdown or explanation."""
                }]
            }
        )

        if response.status_code == 200:
            result = response.json()
            content = result["content"][0]["text"]
            # Parse JSON from response
            import json
            # Clean up response if needed
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```json?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            return json.loads(content)
        else:
            raise Exception(f"Claude API error: {response.status_code}")


def generate_soap_template(transcript: str, chief_complaint: str = None) -> dict:
    """Generate SOAP note using template-based extraction (no AI required)"""

    # Simple keyword extraction for demo
    transcript_lower = transcript.lower()

    # Extract subjective (symptoms patient reports)
    symptom_keywords = ["pain", "ache", "hurt", "fever", "cough", "tired", "nausea",
                       "dizzy", "headache", "sore", "swelling", "bleeding"]
    symptoms = [kw for kw in symptom_keywords if kw in transcript_lower]

    subjective = f"Patient presents with: {', '.join(symptoms) if symptoms else 'symptoms as described'}. "
    subjective += f"Chief complaint: {chief_complaint or 'See transcript'}. "
    subjective += f"Patient states: \"{transcript[:200]}...\""

    # Extract objective (observable findings)
    vital_patterns = re.findall(r'(\d+/\d+|\d+\.\d+|\d+ degrees?|\d+ bpm)', transcript)
    objective = "Vital signs: " + (", ".join(vital_patterns) if vital_patterns else "To be recorded") + ". "
    objective += "Physical exam findings as documented."

    # Assessment
    assessment = f"Clinical presentation consistent with reported symptoms. "
    assessment += "Further evaluation may be needed."

    # Plan
    plan = "1. Continue current treatment\n"
    plan += "2. Monitor symptoms\n"
    plan += "3. Follow up as needed\n"
    plan += "4. Return if symptoms worsen"

    # Summary
    summary = f"Patient encounter documented. Primary concern: {chief_complaint or 'as described'}."

    # ICD-10 code suggestions based on keywords (60+ common codes)
    icd10_codes = []
    icd10_map = {
        # Symptoms - General
        "headache": {"code": "R51.9", "description": "Headache, unspecified"},
        "migraine": {"code": "G43.909", "description": "Migraine, unspecified"},
        "fever": {"code": "R50.9", "description": "Fever, unspecified"},
        "fatigue": {"code": "R53.83", "description": "Other fatigue"},
        "tired": {"code": "R53.83", "description": "Other fatigue"},
        "weakness": {"code": "R53.1", "description": "Weakness"},
        "malaise": {"code": "R53.81", "description": "Other malaise"},
        "dizzy": {"code": "R42", "description": "Dizziness and giddiness"},
        "vertigo": {"code": "R42", "description": "Dizziness and giddiness"},
        "syncope": {"code": "R55", "description": "Syncope and collapse"},
        "fainting": {"code": "R55", "description": "Syncope and collapse"},
        "weight loss": {"code": "R63.4", "description": "Abnormal weight loss"},
        "weight gain": {"code": "R63.5", "description": "Abnormal weight gain"},
        # Pain
        "pain": {"code": "R52", "description": "Pain, unspecified"},
        "chest pain": {"code": "R07.9", "description": "Chest pain, unspecified"},
        "abdominal pain": {"code": "R10.9", "description": "Abdominal pain, unspecified"},
        "stomach pain": {"code": "R10.9", "description": "Abdominal pain, unspecified"},
        "back pain": {"code": "M54.9", "description": "Dorsalgia, unspecified"},
        "lower back": {"code": "M54.5", "description": "Low back pain"},
        "neck pain": {"code": "M54.2", "description": "Cervicalgia"},
        "joint pain": {"code": "M25.50", "description": "Pain in unspecified joint"},
        "knee pain": {"code": "M25.569", "description": "Pain in unspecified knee"},
        "shoulder pain": {"code": "M25.519", "description": "Pain in unspecified shoulder"},
        "hip pain": {"code": "M25.559", "description": "Pain in unspecified hip"},
        # Respiratory
        "cough": {"code": "R05.9", "description": "Cough, unspecified"},
        "shortness of breath": {"code": "R06.02", "description": "Shortness of breath"},
        "dyspnea": {"code": "R06.00", "description": "Dyspnea, unspecified"},
        "wheezing": {"code": "R06.2", "description": "Wheezing"},
        "sore throat": {"code": "J02.9", "description": "Acute pharyngitis, unspecified"},
        "strep": {"code": "J02.0", "description": "Streptococcal pharyngitis"},
        "cold": {"code": "J00", "description": "Acute nasopharyngitis (common cold)"},
        "flu": {"code": "J11.1", "description": "Influenza with respiratory manifestations"},
        "influenza": {"code": "J11.1", "description": "Influenza with respiratory manifestations"},
        "bronchitis": {"code": "J20.9", "description": "Acute bronchitis, unspecified"},
        "pneumonia": {"code": "J18.9", "description": "Pneumonia, unspecified organism"},
        "asthma": {"code": "J45.909", "description": "Unspecified asthma, uncomplicated"},
        "copd": {"code": "J44.9", "description": "COPD, unspecified"},
        "sinusitis": {"code": "J32.9", "description": "Chronic sinusitis, unspecified"},
        "congestion": {"code": "R09.81", "description": "Nasal congestion"},
        # Gastrointestinal
        "nausea": {"code": "R11.0", "description": "Nausea"},
        "vomiting": {"code": "R11.10", "description": "Vomiting, unspecified"},
        "diarrhea": {"code": "R19.7", "description": "Diarrhea, unspecified"},
        "constipation": {"code": "K59.00", "description": "Constipation, unspecified"},
        "heartburn": {"code": "R12", "description": "Heartburn"},
        "gerd": {"code": "K21.0", "description": "GERD with esophagitis"},
        "reflux": {"code": "K21.9", "description": "GERD without esophagitis"},
        "gastritis": {"code": "K29.70", "description": "Gastritis, unspecified"},
        # Cardiovascular
        "hypertension": {"code": "I10", "description": "Essential (primary) hypertension"},
        "high blood pressure": {"code": "I10", "description": "Essential (primary) hypertension"},
        "palpitations": {"code": "R00.2", "description": "Palpitations"},
        "tachycardia": {"code": "R00.0", "description": "Tachycardia, unspecified"},
        "atrial fibrillation": {"code": "I48.91", "description": "Unspecified atrial fibrillation"},
        "afib": {"code": "I48.91", "description": "Unspecified atrial fibrillation"},
        "heart failure": {"code": "I50.9", "description": "Heart failure, unspecified"},
        "chf": {"code": "I50.9", "description": "Heart failure, unspecified"},
        # Endocrine/Metabolic
        "diabetes": {"code": "E11.9", "description": "Type 2 diabetes without complications"},
        "diabetic": {"code": "E11.9", "description": "Type 2 diabetes without complications"},
        "hypothyroid": {"code": "E03.9", "description": "Hypothyroidism, unspecified"},
        "hyperthyroid": {"code": "E05.90", "description": "Thyrotoxicosis, unspecified"},
        "obesity": {"code": "E66.9", "description": "Obesity, unspecified"},
        "hyperlipidemia": {"code": "E78.5", "description": "Hyperlipidemia, unspecified"},
        "high cholesterol": {"code": "E78.00", "description": "Pure hypercholesterolemia"},
        # Mental Health
        "anxiety": {"code": "F41.9", "description": "Anxiety disorder, unspecified"},
        "depression": {"code": "F32.9", "description": "Major depressive disorder, unspecified"},
        "insomnia": {"code": "G47.00", "description": "Insomnia, unspecified"},
        "sleep": {"code": "G47.9", "description": "Sleep disorder, unspecified"},
        "stress": {"code": "F43.9", "description": "Reaction to severe stress, unspecified"},
        "panic": {"code": "F41.0", "description": "Panic disorder"},
        # Musculoskeletal
        "arthritis": {"code": "M19.90", "description": "Unspecified osteoarthritis"},
        "sprain": {"code": "S93.409A", "description": "Sprain of unspecified ligament of ankle"},
        "strain": {"code": "S39.012A", "description": "Strain of muscle of lower back"},
        "fracture": {"code": "S52.509A", "description": "Unspecified fracture of forearm"},
        # Skin
        "rash": {"code": "R21", "description": "Rash and other nonspecific skin eruption"},
        "eczema": {"code": "L30.9", "description": "Dermatitis, unspecified"},
        "dermatitis": {"code": "L30.9", "description": "Dermatitis, unspecified"},
        "cellulitis": {"code": "L03.90", "description": "Cellulitis, unspecified"},
        "abscess": {"code": "L02.91", "description": "Cutaneous abscess, unspecified"},
        "laceration": {"code": "S01.80XA", "description": "Unspecified open wound of head"},
        "wound": {"code": "T14.8", "description": "Other injury of unspecified body region"},
        # Urinary
        "uti": {"code": "N39.0", "description": "Urinary tract infection, site not specified"},
        "urinary infection": {"code": "N39.0", "description": "Urinary tract infection"},
        "dysuria": {"code": "R30.0", "description": "Dysuria"},
        "burning urination": {"code": "R30.0", "description": "Dysuria"},
        "hematuria": {"code": "R31.9", "description": "Hematuria, unspecified"},
        # Eyes/ENT
        "ear pain": {"code": "H92.09", "description": "Otalgia, unspecified ear"},
        "ear infection": {"code": "H66.90", "description": "Otitis media, unspecified"},
        "otitis": {"code": "H66.90", "description": "Otitis media, unspecified"},
        "conjunctivitis": {"code": "H10.9", "description": "Unspecified conjunctivitis"},
        "pink eye": {"code": "H10.9", "description": "Unspecified conjunctivitis"},
        "blurry vision": {"code": "H53.8", "description": "Other visual disturbances"},
        # Allergies
        "allergic": {"code": "T78.40XA", "description": "Allergy, unspecified, initial encounter"},
        "allergies": {"code": "J30.9", "description": "Allergic rhinitis, unspecified"},
        "hay fever": {"code": "J30.1", "description": "Allergic rhinitis due to pollen"},
        "hives": {"code": "L50.9", "description": "Urticaria, unspecified"},
        "anaphylaxis": {"code": "T78.2XXA", "description": "Anaphylactic shock, unspecified"},
    }

    # First try JSON database keywords, then fall back to inline map
    icd10_keywords = ICD10_DB.get("keywords", {})
    icd10_all_codes = {}
    for category in ICD10_DB.get("codes", {}).values():
        icd10_all_codes.update(category)

    for keyword, code in icd10_keywords.items():
        if keyword in transcript_lower and len(icd10_codes) < 5:
            desc = icd10_all_codes.get(code, "")
            code_info = {"code": code, "description": desc}
            if code_info not in icd10_codes:
                icd10_codes.append(code_info)

    # Fall back to inline map if not enough codes found
    for keyword, code_info in icd10_map.items():
        if keyword in transcript_lower and code_info not in icd10_codes:
            icd10_codes.append(code_info)
        if len(icd10_codes) >= 5:
            break

    # Default code if none detected
    if not icd10_codes:
        icd10_codes.append({"code": "Z00.00", "description": "General adult medical examination"})

    # CPT code suggestions based on visit type and procedures (50+ common codes)
    cpt_codes = []
    cpt_map = {
        # E/M Office Visits - New Patient
        "new patient": {"code": "99203", "description": "Office visit, new patient, low complexity"},
        "new patient moderate": {"code": "99204", "description": "Office visit, new patient, moderate complexity"},
        "new patient high": {"code": "99205", "description": "Office visit, new patient, high complexity"},
        # E/M Office Visits - Established Patient
        "established": {"code": "99213", "description": "Office visit, established, low complexity"},
        "follow up": {"code": "99214", "description": "Office visit, established, moderate complexity"},
        "followup": {"code": "99214", "description": "Office visit, established, moderate complexity"},
        "comprehensive": {"code": "99215", "description": "Office visit, established, high complexity"},
        "complex": {"code": "99215", "description": "Office visit, established, high complexity"},
        # Preventive Visits
        "physical exam": {"code": "99395", "description": "Preventive visit, 18-39 years"},
        "annual": {"code": "99396", "description": "Preventive visit, 40-64 years"},
        "wellness": {"code": "99395", "description": "Preventive visit, 18-39 years"},
        "medicare wellness": {"code": "G0438", "description": "Annual wellness visit, initial"},
        # Imaging - X-rays
        "x-ray": {"code": "71046", "description": "Chest X-ray, 2 views"},
        "xray": {"code": "71046", "description": "Chest X-ray, 2 views"},
        "chest x-ray": {"code": "71046", "description": "Chest X-ray, 2 views"},
        "hand x-ray": {"code": "73130", "description": "Hand X-ray, minimum 3 views"},
        "foot x-ray": {"code": "73630", "description": "Foot X-ray, complete"},
        "knee x-ray": {"code": "73562", "description": "Knee X-ray, 3 views"},
        "ankle x-ray": {"code": "73610", "description": "Ankle X-ray, complete"},
        "spine x-ray": {"code": "72100", "description": "Spine X-ray, lumbosacral"},
        # Imaging - Advanced
        "ct scan": {"code": "71250", "description": "CT thorax without contrast"},
        "ct": {"code": "71250", "description": "CT thorax without contrast"},
        "mri": {"code": "73721", "description": "MRI lower extremity joint"},
        "ultrasound": {"code": "76700", "description": "Ultrasound, abdominal, complete"},
        "echo": {"code": "93306", "description": "Echocardiography, complete"},
        "echocardiogram": {"code": "93306", "description": "Echocardiography, complete"},
        # Cardiovascular
        "ekg": {"code": "93000", "description": "Electrocardiogram, complete"},
        "ecg": {"code": "93000", "description": "Electrocardiogram, complete"},
        "electrocardiogram": {"code": "93000", "description": "Electrocardiogram, complete"},
        "stress test": {"code": "93015", "description": "Cardiovascular stress test"},
        "holter": {"code": "93224", "description": "Holter monitor, 24-hour"},
        # Laboratory - Blood
        "blood draw": {"code": "36415", "description": "Venipuncture, routine"},
        "lab": {"code": "36415", "description": "Venipuncture, routine"},
        "labs": {"code": "36415", "description": "Venipuncture, routine"},
        "blood work": {"code": "36415", "description": "Venipuncture, routine"},
        "cbc": {"code": "85025", "description": "Complete blood count (CBC)"},
        "cmp": {"code": "80053", "description": "Comprehensive metabolic panel"},
        "bmp": {"code": "80048", "description": "Basic metabolic panel"},
        "lipid": {"code": "80061", "description": "Lipid panel"},
        "cholesterol": {"code": "80061", "description": "Lipid panel"},
        "glucose": {"code": "82947", "description": "Glucose, blood test"},
        "a1c": {"code": "83036", "description": "Hemoglobin A1c"},
        "hemoglobin a1c": {"code": "83036", "description": "Hemoglobin A1c"},
        "tsh": {"code": "84443", "description": "Thyroid stimulating hormone (TSH)"},
        "thyroid": {"code": "84443", "description": "Thyroid stimulating hormone (TSH)"},
        "psa": {"code": "84153", "description": "Prostate specific antigen (PSA)"},
        "vitamin d": {"code": "82306", "description": "Vitamin D, 25-Hydroxy"},
        "b12": {"code": "82607", "description": "Vitamin B-12"},
        "iron": {"code": "83540", "description": "Iron, serum"},
        "ferritin": {"code": "82728", "description": "Ferritin"},
        # Laboratory - Other
        "urinalysis": {"code": "81003", "description": "Urinalysis, automated"},
        "urine test": {"code": "81003", "description": "Urinalysis, automated"},
        "urine culture": {"code": "87086", "description": "Urine culture"},
        "strep test": {"code": "87880", "description": "Strep A test, rapid"},
        "rapid strep": {"code": "87880", "description": "Strep A test, rapid"},
        "flu test": {"code": "87804", "description": "Influenza assay"},
        "covid test": {"code": "87635", "description": "COVID-19 amplified probe"},
        "pregnancy test": {"code": "81025", "description": "Urine pregnancy test"},
        # Injections/Infusions
        "injection": {"code": "96372", "description": "Therapeutic injection, SC/IM"},
        "steroid injection": {"code": "20610", "description": "Joint injection, major joint"},
        "joint injection": {"code": "20610", "description": "Joint injection, major joint"},
        "trigger point": {"code": "20552", "description": "Trigger point injection"},
        "iv": {"code": "96360", "description": "IV infusion, hydration, initial"},
        "iv fluids": {"code": "96360", "description": "IV infusion, hydration, initial"},
        "infusion": {"code": "96365", "description": "IV infusion, therapeutic, initial"},
        # Vaccines
        "vaccine": {"code": "90471", "description": "Immunization administration"},
        "immunization": {"code": "90471", "description": "Immunization administration"},
        "flu shot": {"code": "90686", "description": "Influenza vaccine, quadrivalent"},
        "flu vaccine": {"code": "90686", "description": "Influenza vaccine, quadrivalent"},
        "pneumonia vaccine": {"code": "90670", "description": "Pneumococcal vaccine"},
        "tetanus": {"code": "90715", "description": "Tdap vaccine"},
        "tdap": {"code": "90715", "description": "Tdap vaccine"},
        "shingles": {"code": "90750", "description": "Zoster vaccine"},
        "covid vaccine": {"code": "91300", "description": "COVID-19 vaccine"},
        # Wound Care/Minor Procedures
        "suture": {"code": "12001", "description": "Simple wound repair, <=2.5cm"},
        "stitches": {"code": "12001", "description": "Simple wound repair, <=2.5cm"},
        "laceration repair": {"code": "12002", "description": "Simple wound repair, 2.6-7.5cm"},
        "wound care": {"code": "97597", "description": "Wound debridement"},
        "debridement": {"code": "97597", "description": "Wound debridement"},
        "i&d": {"code": "10060", "description": "Incision and drainage, abscess"},
        "incision and drainage": {"code": "10060", "description": "Incision and drainage, abscess"},
        "skin biopsy": {"code": "11102", "description": "Tangential biopsy of skin"},
        "biopsy": {"code": "11102", "description": "Tangential biopsy of skin"},
        "mole removal": {"code": "11300", "description": "Shave removal, benign lesion"},
        "cryotherapy": {"code": "17000", "description": "Destruction, benign lesion"},
        "wart removal": {"code": "17110", "description": "Destruction, benign lesions, up to 14"},
        # Orthopedic
        "splint": {"code": "29125", "description": "Application of short arm splint"},
        "cast": {"code": "29075", "description": "Application of elbow cast"},
        "cast removal": {"code": "29700", "description": "Removal of cast"},
        "joint aspiration": {"code": "20610", "description": "Arthrocentesis, major joint"},
        # Respiratory
        "nebulizer": {"code": "94640", "description": "Nebulizer treatment"},
        "breathing treatment": {"code": "94640", "description": "Nebulizer treatment"},
        "spirometry": {"code": "94010", "description": "Spirometry"},
        "pulmonary function": {"code": "94060", "description": "Bronchodilator response"},
        "oxygen": {"code": "94760", "description": "Pulse oximetry"},
        "pulse ox": {"code": "94760", "description": "Pulse oximetry"},
        # Other Common
        "ear lavage": {"code": "69210", "description": "Ear wax removal"},
        "ear wax": {"code": "69210", "description": "Ear wax removal"},
        "cerumen": {"code": "69210", "description": "Ear wax removal"},
        "foreign body removal": {"code": "10120", "description": "Foreign body removal, simple"},
    }

    # First try JSON database keywords for CPT
    cpt_keywords = CPT_DB.get("keywords", {})
    cpt_all_codes = {}
    for category in CPT_DB.get("codes", {}).values():
        cpt_all_codes.update(category)

    for keyword, code in cpt_keywords.items():
        if keyword in transcript_lower and len(cpt_codes) < 5:
            desc = cpt_all_codes.get(code, "")
            code_info = {"code": code, "description": desc}
            if code_info not in cpt_codes:
                cpt_codes.append(code_info)

    # Fall back to inline map if not enough codes found
    for keyword, code_info in cpt_map.items():
        if keyword in transcript_lower and code_info not in cpt_codes:
            cpt_codes.append(code_info)
        if len(cpt_codes) >= 5:
            break

    # Default E/M code if none detected
    if not cpt_codes:
        cpt_codes.append({"code": "99213", "description": "Office visit, established patient, low complexity"})

    return {
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
        "summary": summary,
        "icd10_codes": icd10_codes,
        "cpt_codes": cpt_codes
    }


def format_soap_display(note: dict) -> str:
    """Format SOAP note for AR display"""
    lines = [
        "═══ CLINICAL NOTE ═══",
        f"📝 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "─" * 25,
        "▸ SUBJECTIVE:",
        note["subjective"][:150] + "..." if len(note["subjective"]) > 150 else note["subjective"],
        "",
        "▸ OBJECTIVE:",
        note["objective"][:100] + "..." if len(note["objective"]) > 100 else note["objective"],
        "",
        "▸ ASSESSMENT:",
        note["assessment"][:100] + "..." if len(note["assessment"]) > 100 else note["assessment"],
        "",
        "▸ PLAN:",
        note["plan"][:150] + "..." if len(note["plan"]) > 150 else note["plan"],
    ]

    # Add ICD-10 codes if present
    icd10_codes = note.get("icd10_codes", [])
    if icd10_codes:
        lines.append("")
        lines.append("▸ ICD-10 CODES:")
        for code_info in icd10_codes[:5]:
            code = code_info.get("code", "")
            desc = code_info.get("description", "")
            lines.append(f"  • {code}: {desc[:40]}")

    # Add CPT codes if present
    cpt_codes = note.get("cpt_codes", [])
    if cpt_codes:
        lines.append("")
        lines.append("▸ CPT CODES:")
        for code_info in cpt_codes[:5]:
            code = code_info.get("code", "")
            desc = code_info.get("description", "")
            lines.append(f"  • {code}: {desc[:40]}")

    lines.append("─" * 25)
    lines.append(f"Summary: {note['summary'][:100]}")

    return "\n".join(lines)


@app.post("/api/v1/notes/generate", response_model=SOAPNote)
async def generate_clinical_note(request: NoteRequest):
    """Generate SOAP note from voice transcript - for AR documentation"""

    try:
        # Try Claude API if available
        if CLAUDE_API_KEY:
            note_data = await generate_soap_with_claude(
                request.transcript,
                request.chief_complaint
            )
        else:
            # Fallback to template-based generation
            note_data = generate_soap_template(
                request.transcript,
                request.chief_complaint
            )

        note = SOAPNote(
            subjective=note_data.get("subjective", ""),
            objective=note_data.get("objective", ""),
            assessment=note_data.get("assessment", ""),
            plan=note_data.get("plan", ""),
            summary=note_data.get("summary", ""),
            timestamp=datetime.now().isoformat()
        )
        note.display_text = format_soap_display(note_data)

        return note

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Note generation failed: {str(e)}")


@app.post("/api/v1/notes/quick")
async def quick_note(request: NoteRequest):
    """Quick note for AR display - returns just the formatted text"""
    note = await generate_clinical_note(request)
    return {
        "display_text": note.display_text,
        "summary": note.summary,
        "timestamp": note.timestamp
    }


# ============ Note Storage (Simulated - Cerner sandbox is read-only) ============

# In-memory storage for saved notes (in production, this would go to the EHR)
saved_notes: dict = {}


class SaveNoteRequest(BaseModel):
    patient_id: str
    note_type: str = "SOAP"
    display_text: str
    summary: str = ""
    transcript: str = ""
    timestamp: str = ""


@app.post("/api/v1/notes/save")
async def save_note(request: SaveNoteRequest):
    """
    Save a clinical note to the EHR (simulated)

    In production, this would:
    1. Create a FHIR DocumentReference resource
    2. POST to the EHR's DocumentReference endpoint
    3. Return the created resource ID

    For now (Cerner sandbox is read-only), we simulate by storing locally.
    """
    try:
        # Generate a unique note ID
        note_id = f"NOTE-{uuid.uuid4().hex[:8].upper()}"

        # Create note record
        note_record = {
            "id": note_id,
            "patient_id": request.patient_id,
            "note_type": request.note_type,
            "display_text": request.display_text,
            "summary": request.summary,
            "transcript": request.transcript,
            "timestamp": request.timestamp or datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "final"
        }

        # Store in memory (simulated EHR storage)
        saved_notes[note_id] = note_record

        print(f"📝 Note saved: {note_id} for patient {request.patient_id}")
        print(f"   Summary: {request.summary[:50]}..." if request.summary else "   (No summary)")

        return {
            "success": True,
            "note_id": note_id,
            "message": "Note saved successfully",
            "patient_id": request.patient_id,
            "timestamp": note_record["created_at"]
        }

    except Exception as e:
        print(f"❌ Save note error: {e}")
        return {
            "success": False,
            "message": f"Failed to save note: {str(e)}"
        }


@app.get("/api/v1/notes/{note_id}")
async def get_saved_note(note_id: str):
    """Retrieve a saved note by ID"""
    if note_id in saved_notes:
        return saved_notes[note_id]
    raise HTTPException(status_code=404, detail="Note not found")


@app.get("/api/v1/patient/{patient_id}/notes")
async def get_patient_notes(patient_id: str):
    """Get all saved notes for a patient"""
    patient_notes = [
        note for note in saved_notes.values()
        if note["patient_id"] == patient_id
    ]
    return {
        "patient_id": patient_id,
        "count": len(patient_notes),
        "notes": patient_notes
    }


# ============ Real-Time Transcription WebSocket ============

@app.get("/api/v1/transcription/status")
async def transcription_status():
    """Check transcription service status and configuration"""
    return {
        "provider": TRANSCRIPTION_PROVIDER,
        "status": "ready",
        "supported_providers": ["assemblyai", "deepgram"],
        "sample_rate": 16000,
        "encoding": "linear16"
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    Real-time transcription WebSocket endpoint

    Protocol:
    1. Client connects
    2. Server sends: {"type": "connected", "session_id": "...", "provider": "..."}
    3. Client sends audio chunks as binary data (16-bit PCM, 16kHz)
    4. Server sends transcription results:
       {"type": "transcript", "text": "...", "is_final": true/false}
    5. Client sends: {"type": "stop"} to end session
    6. Server sends: {"type": "ended", "full_transcript": "..."}
    """
    await websocket.accept()

    # Generate session ID
    session_id = str(uuid.uuid4())[:8]
    session = None

    try:
        # Create transcription session
        print(f"🎤 Creating session {session_id}...")
        session = await create_session(session_id)
        print(f"🎤 Session created, provider connected: {session.is_active}")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "provider": TRANSCRIPTION_PROVIDER
        })
        print(f"🎤 Transcription session started: {session_id} ({TRANSCRIPTION_PROVIDER})")

        # Task to forward transcriptions to client
        async def forward_transcriptions():
            try:
                async for result in session.get_transcriptions():
                    await websocket.send_json({
                        "type": "transcript",
                        "text": result.text,
                        "is_final": result.is_final,
                        "confidence": result.confidence,
                        "speaker": result.speaker
                    })
            except Exception as e:
                print(f"Transcription forward error: {e}")

        # Start forwarding task
        forward_task = asyncio.create_task(forward_transcriptions())

        # Receive audio from client
        while True:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if "bytes" in message:
                    # Binary audio data
                    await session.send_audio(message["bytes"])

                elif "text" in message:
                    # JSON control message
                    data = json.loads(message["text"])

                    if data.get("type") == "stop":
                        break
                    elif data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket receive error: {e}")
                break

        # Clean up
        forward_task.cancel()
        full_transcript = await end_session(session_id)

        # Send final transcript
        try:
            await websocket.send_json({
                "type": "ended",
                "session_id": session_id,
                "full_transcript": full_transcript
            })
        except:
            pass

        print(f"🎤 Transcription session ended: {session_id}")

    except Exception as e:
        print(f"Transcription session error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
        if session:
            await end_session(session_id)

    finally:
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/transcribe/{provider}")
async def websocket_transcribe_with_provider(websocket: WebSocket, provider: str):
    """
    Real-time transcription with specific provider
    Use: /ws/transcribe/deepgram or /ws/transcribe/assemblyai
    """
    await websocket.accept()

    if provider not in ["assemblyai", "deepgram"]:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown provider: {provider}. Use 'assemblyai' or 'deepgram'"
        })
        await websocket.close()
        return

    session_id = str(uuid.uuid4())[:8]
    session = None

    try:
        # Create session with specific provider
        from transcription import TranscriptionSession
        session = TranscriptionSession(session_id, provider)
        await session.start()

        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "provider": provider
        })
        print(f"🎤 Transcription session started: {session_id} ({provider})")

        async def forward_transcriptions():
            try:
                async for result in session.get_transcriptions():
                    await websocket.send_json({
                        "type": "transcript",
                        "text": result.text,
                        "is_final": result.is_final,
                        "confidence": result.confidence,
                        "speaker": result.speaker
                    })
            except Exception as e:
                print(f"Transcription forward error: {e}")

        forward_task = asyncio.create_task(forward_transcriptions())

        while True:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if "bytes" in message:
                    await session.send_audio(message["bytes"])
                elif "text" in message:
                    data = json.loads(message["text"])
                    if data.get("type") == "stop":
                        break

            except WebSocketDisconnect:
                break
            except Exception as e:
                break

        forward_task.cancel()
        full_transcript = session.get_full_transcript()
        await session.stop()

        try:
            await websocket.send_json({
                "type": "ended",
                "session_id": session_id,
                "full_transcript": full_transcript
            })
        except:
            pass

    except Exception as e:
        print(f"Transcription error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
        if session:
            await session.stop()
    finally:
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    print("🏥 MDx Vision EHR Proxy starting...")
    print("📡 Connected to: Cerner Open Sandbox")
    print("🔗 API: http://localhost:8002")
    print("📱 Android emulator: http://10.0.2.2:8002")
    print(f"🎤 Transcription: {TRANSCRIPTION_PROVIDER} (ws://localhost:8002/ws/transcribe)")
    uvicorn.run(app, host="0.0.0.0", port=8002)
