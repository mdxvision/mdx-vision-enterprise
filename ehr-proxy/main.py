"""
MDx Vision - EHR Proxy Service
Connects AR glasses to Cerner (and other EHRs) via FHIR R4

Run: python main.py
Test: curl http://localhost:8001/api/v1/patient/12724066
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

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


class PatientSummary(BaseModel):
    patient_id: str
    name: str
    date_of_birth: str
    gender: str
    mrn: Optional[str] = None
    vitals: List[VitalSign] = []
    allergies: List[str] = []
    medications: List[str] = []
    display_text: str = ""


class SearchResult(BaseModel):
    patient_id: str
    name: str
    date_of_birth: str
    gender: str


async def fetch_fhir(endpoint: str) -> dict:
    """Fetch from Cerner FHIR API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{CERNER_BASE_URL}/{endpoint}",
            headers=FHIR_HEADERS
        )
        if response.status_code == 200:
            return response.json()
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

    summary = PatientSummary(
        patient_id=patient_id,
        name=name,
        date_of_birth=dob,
        gender=gender,
        vitals=vitals,
        allergies=allergies,
        medications=medications
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


if __name__ == "__main__":
    print("🏥 MDx Vision EHR Proxy starting...")
    print("📡 Connected to: Cerner Open Sandbox")
    print("🔗 API: http://localhost:8002")
    print("📱 Android emulator: http://10.0.2.2:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)
