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
import base64
from datetime import datetime

# Import transcription service
from transcription import (
    create_session, get_session, end_session, set_session_speaker_context,
    TranscriptionSession, TRANSCRIPTION_PROVIDER
)

# Import specialty detection for auto-loading vocabulary
from medical_vocabulary import (
    detect_specialties_from_patient_conditions,
    detect_specialty_from_transcript,
    get_vocabulary_for_patient
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
DRUG_INTERACTIONS_DB = load_code_database("drug_interactions.json")

# Critical lab value thresholds for safety alerts
# Format: {lab_name_pattern: {"critical_low": val, "critical_high": val, "low": val, "high": val, "unit": str}}
CRITICAL_LAB_THRESHOLDS = {
    "potassium": {"critical_low": 2.5, "critical_high": 6.5, "low": 3.5, "high": 5.0, "unit": "mEq/L"},
    "sodium": {"critical_low": 120, "critical_high": 160, "low": 136, "high": 145, "unit": "mEq/L"},
    "glucose": {"critical_low": 50, "critical_high": 450, "low": 70, "high": 100, "unit": "mg/dL"},
    "creatinine": {"critical_high": 10.0, "high": 1.2, "unit": "mg/dL"},
    "hemoglobin": {"critical_low": 7.0, "low": 12.0, "high": 17.5, "unit": "g/dL"},
    "hematocrit": {"critical_low": 20, "low": 36, "high": 54, "unit": "%"},
    "platelets": {"critical_low": 50, "critical_high": 1000, "low": 150, "high": 400, "unit": "10*3/uL"},
    "wbc": {"critical_low": 2.0, "critical_high": 30.0, "low": 4.5, "high": 11.0, "unit": "10*3/uL"},
    "inr": {"critical_high": 5.0, "high": 1.1, "unit": ""},
    "troponin": {"critical_high": 0.04, "high": 0.01, "unit": "ng/mL"},
    "bun": {"critical_high": 100, "high": 20, "unit": "mg/dL"},
    "calcium": {"critical_low": 6.0, "critical_high": 13.0, "low": 8.5, "high": 10.5, "unit": "mg/dL"},
    "magnesium": {"critical_low": 1.0, "critical_high": 4.0, "low": 1.7, "high": 2.3, "unit": "mg/dL"},
    "phosphorus": {"critical_low": 1.0, "low": 2.5, "high": 4.5, "unit": "mg/dL"},
    "bilirubin": {"critical_high": 15.0, "high": 1.2, "unit": "mg/dL"},
    "lactate": {"critical_high": 4.0, "high": 2.0, "unit": "mmol/L"},
    "ph": {"critical_low": 7.2, "critical_high": 7.6, "low": 7.35, "high": 7.45, "unit": ""},
    "pco2": {"critical_low": 20, "critical_high": 70, "low": 35, "high": 45, "unit": "mmHg"},
    "po2": {"critical_low": 40, "low": 80, "high": 100, "unit": "mmHg"},
    "bicarbonate": {"critical_low": 10, "critical_high": 40, "low": 22, "high": 28, "unit": "mEq/L"},
}

def check_critical_value(lab_name: str, value_str: str) -> tuple:
    """
    Check if a lab value is critical or abnormal.
    Returns (is_critical, is_abnormal, interpretation)
    """
    # Try to extract numeric value
    try:
        # Handle values like "5.2", ">10", "<0.01", "5.2 H"
        clean_value = value_str.strip().replace(">", "").replace("<", "").split()[0]
        numeric_value = float(clean_value)
    except (ValueError, IndexError):
        return False, False, ""

    # Find matching threshold by checking if lab name contains the pattern
    lab_lower = lab_name.lower()
    for pattern, thresholds in CRITICAL_LAB_THRESHOLDS.items():
        if pattern in lab_lower:
            is_critical = False
            is_abnormal = False
            interpretation = "N"  # Normal

            # Check critical values first
            if "critical_low" in thresholds and numeric_value <= thresholds["critical_low"]:
                is_critical = True
                is_abnormal = True
                interpretation = "LL"  # Critically low
            elif "critical_high" in thresholds and numeric_value >= thresholds["critical_high"]:
                is_critical = True
                is_abnormal = True
                interpretation = "HH"  # Critically high
            # Check abnormal values
            elif "low" in thresholds and numeric_value < thresholds["low"]:
                is_abnormal = True
                interpretation = "L"  # Low
            elif "high" in thresholds and numeric_value > thresholds["high"]:
                is_abnormal = True
                interpretation = "H"  # High

            return is_critical, is_abnormal, interpretation

    return False, False, ""

# Critical vital sign thresholds for safety alerts
# Format: {vital_name_pattern: {"critical_low": val, "critical_high": val, "low": val, "high": val}}
CRITICAL_VITAL_THRESHOLDS = {
    # Blood Pressure - Systolic
    "systolic": {"critical_low": 70, "critical_high": 180, "low": 90, "high": 140},
    # Blood Pressure - Diastolic
    "diastolic": {"critical_low": 40, "critical_high": 120, "low": 60, "high": 90},
    # Heart Rate
    "heart rate": {"critical_low": 40, "critical_high": 150, "low": 60, "high": 100},
    "pulse": {"critical_low": 40, "critical_high": 150, "low": 60, "high": 100},
    # Respiratory Rate
    "respiratory": {"critical_low": 8, "critical_high": 30, "low": 12, "high": 20},
    # Oxygen Saturation
    "oxygen saturation": {"critical_low": 88, "low": 94},
    "spo2": {"critical_low": 88, "low": 94},
    "o2 sat": {"critical_low": 88, "low": 94},
    # Temperature (Fahrenheit)
    "temperature": {"critical_low": 95.0, "critical_high": 104.0, "low": 97.0, "high": 99.5},
    "temp": {"critical_low": 95.0, "critical_high": 104.0, "low": 97.0, "high": 99.5},
    # Blood Glucose (if measured as vital)
    "glucose": {"critical_low": 50, "critical_high": 400, "low": 70, "high": 180},
    # BMI (informational, not critical)
    "bmi": {"high": 30},
    # Pain Scale
    "pain": {"high": 7, "critical_high": 9},
}

def check_critical_vital(vital_name: str, value_str: str) -> tuple:
    """
    Check if a vital sign is critical or abnormal.
    Returns (is_critical, is_abnormal, interpretation)
    """
    # Try to extract numeric value
    try:
        # Handle values like "120/80", "98.6", ">100"
        clean_value = value_str.strip().replace(">", "").replace("<", "")
        # For BP, extract systolic (first number)
        if "/" in clean_value:
            clean_value = clean_value.split("/")[0]
        numeric_value = float(clean_value.split()[0])
    except (ValueError, IndexError):
        return False, False, ""

    # Find matching threshold by checking if vital name contains the pattern
    vital_lower = vital_name.lower()
    for pattern, thresholds in CRITICAL_VITAL_THRESHOLDS.items():
        if pattern in vital_lower:
            is_critical = False
            is_abnormal = False
            interpretation = "N"  # Normal

            # Check critical values first
            if "critical_low" in thresholds and numeric_value <= thresholds["critical_low"]:
                is_critical = True
                is_abnormal = True
                interpretation = "LL"  # Critically low
            elif "critical_high" in thresholds and numeric_value >= thresholds["critical_high"]:
                is_critical = True
                is_abnormal = True
                interpretation = "HH"  # Critically high
            # Check abnormal values
            elif "low" in thresholds and numeric_value < thresholds["low"]:
                is_abnormal = True
                interpretation = "L"  # Low
            elif "high" in thresholds and numeric_value > thresholds["high"]:
                is_abnormal = True
                interpretation = "H"  # High

            return is_critical, is_abnormal, interpretation

    return False, False, ""

def normalize_medication_name(med_name: str) -> str:
    """Normalize medication name to generic name using keywords database"""
    med_lower = med_name.lower().strip()
    keywords = DRUG_INTERACTIONS_DB.get("keywords", {})

    # Check if it matches a brand name keyword
    for brand, generic in keywords.items():
        if brand in med_lower:
            return generic

    # Return first word (often the drug name without strength/form)
    return med_lower.split()[0] if med_lower else med_lower

def check_medication_interactions(medications: list) -> list:
    """
    Check for drug-drug interactions in patient's medication list.
    Returns list of interaction dicts with drug1, drug2, severity, effect.
    """
    interactions = []
    interactions_db = DRUG_INTERACTIONS_DB.get("interactions", {})

    # Normalize all medication names
    normalized_meds = [(med, normalize_medication_name(med)) for med in medications]

    # Check each pair of medications
    checked_pairs = set()
    for i, (orig_med1, norm_med1) in enumerate(normalized_meds):
        if norm_med1 not in interactions_db:
            continue

        drug_info = interactions_db[norm_med1]
        interacts_with = drug_info.get("interacts_with", [])
        effects = drug_info.get("effects", {})
        severity = drug_info.get("severity", "moderate")

        for j, (orig_med2, norm_med2) in enumerate(normalized_meds):
            if i == j:
                continue

            # Check if this pair already checked (in either order)
            pair_key = tuple(sorted([norm_med1, norm_med2]))
            if pair_key in checked_pairs:
                continue

            # Check if norm_med2 or any keyword variant is in interacts_with
            for interacting_drug in interacts_with:
                if interacting_drug in norm_med2 or norm_med2 in interacting_drug:
                    effect = effects.get(interacting_drug, effects.get(norm_med2, "Potential interaction"))
                    interactions.append({
                        "drug1": orig_med1,
                        "drug2": orig_med2,
                        "severity": severity,
                        "effect": effect
                    })
                    checked_pairs.add(pair_key)
                    break

    # Sort by severity (high first)
    severity_order = {"high": 0, "moderate": 1, "low": 2}
    interactions.sort(key=lambda x: severity_order.get(x["severity"], 1))

    return interactions

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
    interpretation: str = ""   # e.g., "H", "L", "HH", "LL", "N"
    is_critical: bool = False  # True if dangerously out of range
    is_abnormal: bool = False  # True if outside normal range


class LabResult(BaseModel):
    name: str
    value: str
    unit: str
    status: str = ""
    date: str = ""
    reference_range: str = ""  # e.g., "70-100 mg/dL"
    interpretation: str = ""   # e.g., "H", "L", "HH", "LL", "N"
    is_critical: bool = False  # True if dangerously out of range
    is_abnormal: bool = False  # True if outside normal range


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


class CarePlan(BaseModel):
    title: str
    status: str = ""
    intent: str = ""
    category: str = ""
    period_start: str = ""
    period_end: str = ""
    description: str = ""


class ClinicalNote(BaseModel):
    title: str
    doc_type: str = ""  # e.g., "Progress Note", "Discharge Summary"
    date: str = ""
    author: str = ""
    status: str = ""
    content_preview: str = ""  # First 200 chars of content


class MedicationInteraction(BaseModel):
    drug1: str
    drug2: str
    severity: str = "moderate"  # high, moderate, low
    effect: str = ""


class PatientSummary(BaseModel):
    patient_id: str
    name: str
    date_of_birth: str
    gender: str
    mrn: Optional[str] = None
    vitals: List[VitalSign] = []
    critical_vitals: List[VitalSign] = []  # Vitals with is_critical=True
    abnormal_vitals: List[VitalSign] = []  # Vitals with is_abnormal=True
    has_critical_vitals: bool = False      # Quick check for safety alerts
    allergies: List[str] = []
    medications: List[str] = []
    medication_interactions: List[MedicationInteraction] = []  # Drug-drug interactions
    has_interactions: bool = False  # Quick check for interaction alerts
    labs: List[LabResult] = []
    critical_labs: List[LabResult] = []  # Labs with is_critical=True
    abnormal_labs: List[LabResult] = []  # Labs with is_abnormal=True (includes critical)
    has_critical_labs: bool = False      # Quick check for safety alerts
    procedures: List[Procedure] = []
    immunizations: List[Immunization] = []
    conditions: List[Condition] = []
    care_plans: List[CarePlan] = []
    clinical_notes: List[ClinicalNote] = []
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


# Supported note types
NOTE_TYPES = ["SOAP", "PROGRESS", "HP", "CONSULT"]


class ProgressNote(BaseModel):
    """Progress note for follow-up visits"""
    interval_history: str
    current_status: str
    physical_exam: str
    assessment: str
    plan: str
    summary: str
    timestamp: str
    display_text: str = ""


class HPNote(BaseModel):
    """History and Physical note for new patients/admissions"""
    chief_complaint: str
    history_present_illness: str
    past_medical_history: str
    medications: str
    allergies: str
    family_history: str
    social_history: str
    review_of_systems: str
    physical_exam: str
    assessment: str
    plan: str
    summary: str
    timestamp: str
    display_text: str = ""


class ConsultNote(BaseModel):
    """Consultation note for specialist referrals"""
    reason_for_consult: str
    history_present_illness: str
    relevant_history: str
    physical_exam: str
    diagnostic_findings: str
    impression: str
    recommendations: str
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

        # Check for critical values
        is_critical, is_abnormal, interpretation = check_critical_vital(name, value)

        vitals.append(VitalSign(
            name=name,
            value=value,
            unit=unit,
            interpretation=interpretation,
            is_critical=is_critical,
            is_abnormal=is_abnormal
        ))
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

        # Extract reference range from FHIR
        reference_range = ""
        ref_ranges = obs.get("referenceRange", [])
        if ref_ranges:
            ref = ref_ranges[0]
            # Try text first
            if ref.get("text"):
                reference_range = ref["text"]
            else:
                # Build from low/high values
                low = ref.get("low", {}).get("value")
                high = ref.get("high", {}).get("value")
                ref_unit = ref.get("low", {}).get("unit") or ref.get("high", {}).get("unit") or unit
                if low is not None and high is not None:
                    reference_range = f"{low}-{high} {ref_unit}".strip()
                elif low is not None:
                    reference_range = f">={low} {ref_unit}".strip()
                elif high is not None:
                    reference_range = f"<={high} {ref_unit}".strip()

        # Extract interpretation from FHIR (H, L, HH, LL, N, etc.)
        interpretation = ""
        fhir_interp = obs.get("interpretation", [])
        if fhir_interp:
            interp_coding = fhir_interp[0].get("coding", [])
            if interp_coding:
                interpretation = interp_coding[0].get("code", "")

        # Check for critical values using our thresholds
        is_critical, is_abnormal, calc_interpretation = check_critical_value(name, value)

        # Use FHIR interpretation if available, otherwise use calculated
        if not interpretation and calc_interpretation:
            interpretation = calc_interpretation

        # If FHIR says it's critical (HH/LL), trust it
        if interpretation in ("HH", "LL"):
            is_critical = True
            is_abnormal = True
        elif interpretation in ("H", "L"):
            is_abnormal = True

        if name and name != "Unknown":
            labs.append(LabResult(
                name=name,
                value=value,
                unit=unit,
                status=status,
                date=date,
                reference_range=reference_range,
                interpretation=interpretation,
                is_critical=is_critical,
                is_abnormal=is_abnormal
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


def extract_care_plans(bundle: dict) -> List[CarePlan]:
    """Extract care plans from FHIR CarePlan bundle"""
    care_plans = []
    for entry in bundle.get("entry", [])[:10]:
        plan = entry.get("resource", {})

        # Get care plan title
        title = plan.get("title", "")
        if not title:
            # Try to get from category or description
            categories = plan.get("category", [])
            if categories:
                cat_coding = categories[0].get("coding", [])
                if cat_coding:
                    title = cat_coding[0].get("display", cat_coding[0].get("code", ""))
            if not title:
                title = plan.get("description", "Care Plan")[:50]

        # Get status (draft, active, on-hold, revoked, completed, entered-in-error, unknown)
        status = plan.get("status", "")

        # Get intent (proposal, plan, order, option)
        intent = plan.get("intent", "")

        # Get category
        category = ""
        categories = plan.get("category", [])
        if categories:
            cat_coding = categories[0].get("coding", [])
            if cat_coding:
                category = cat_coding[0].get("display", cat_coding[0].get("code", ""))

        # Get period
        period_start = ""
        period_end = ""
        period = plan.get("period", {})
        if period:
            period_start = period.get("start", "")[:10] if period.get("start") else ""
            period_end = period.get("end", "")[:10] if period.get("end") else ""

        # Get description
        description = plan.get("description", "")

        if title:
            care_plans.append(CarePlan(
                title=title,
                status=status,
                intent=intent,
                category=category,
                period_start=period_start,
                period_end=period_end,
                description=description[:200] if description else ""  # Truncate long descriptions
            ))

    return care_plans


def extract_clinical_notes(bundle: dict) -> List[ClinicalNote]:
    """Extract clinical notes from FHIR DocumentReference bundle"""
    notes = []
    for entry in bundle.get("entry", [])[:10]:
        doc = entry.get("resource", {})

        # Get document title/description
        title = doc.get("description", "")
        if not title:
            # Try to get from type
            doc_type_obj = doc.get("type", {})
            if doc_type_obj:
                type_coding = doc_type_obj.get("coding", [])
                if type_coding:
                    title = type_coding[0].get("display", type_coding[0].get("code", "Clinical Note"))

        # Get document type/category
        doc_type = ""
        category = doc.get("category", [])
        if category:
            cat_coding = category[0].get("coding", [])
            if cat_coding:
                doc_type = cat_coding[0].get("display", cat_coding[0].get("code", ""))
        if not doc_type:
            # Fallback to type field
            doc_type_obj = doc.get("type", {})
            if doc_type_obj:
                type_coding = doc_type_obj.get("coding", [])
                if type_coding:
                    doc_type = type_coding[0].get("display", "Note")

        # Get date
        date = ""
        if "date" in doc:
            date = doc["date"][:10] if len(doc["date"]) >= 10 else doc["date"]
        elif "context" in doc and "period" in doc["context"]:
            period = doc["context"]["period"]
            date = period.get("start", "")[:10] if period.get("start") else ""

        # Get author
        author = ""
        authors = doc.get("author", [])
        if authors:
            author_ref = authors[0]
            if isinstance(author_ref, dict):
                author = author_ref.get("display", author_ref.get("reference", ""))

        # Get status
        status = doc.get("status", "")

        # Get content preview (from attachment or contained)
        content_preview = ""
        content = doc.get("content", [])
        if content:
            attachment = content[0].get("attachment", {})
            # Try to get data (base64 encoded) or title
            if "data" in attachment:
                import base64
                try:
                    decoded = base64.b64decode(attachment["data"]).decode("utf-8", errors="ignore")
                    content_preview = decoded[:200]
                except:
                    content_preview = ""
            elif "title" in attachment:
                content_preview = attachment["title"]

        if title or doc_type:
            notes.append(ClinicalNote(
                title=title or doc_type or "Clinical Note",
                doc_type=doc_type,
                date=date,
                author=author,
                status=status,
                content_preview=content_preview[:200] if content_preview else ""
            ))

    return notes


def format_ar_display(summary: PatientSummary) -> str:
    """Format patient data for AR glasses display"""
    lines = [
        f"{summary.name} | {summary.gender.upper()} | DOB: {summary.date_of_birth}",
        "─" * 40,
    ]

    # Show critical vitals warning FIRST (safety priority - before labs)
    if summary.critical_vitals:
        crit_lines = []
        for v in summary.critical_vitals[:3]:
            flag = "‼️" if v.interpretation in ("HH", "LL") else "⚠️"
            interp = f" [{v.interpretation}]" if v.interpretation else ""
            crit_lines.append(f"{flag} {v.name}: {v.value} {v.unit}{interp}")
        lines.append("🚨 CRITICAL VITALS:")
        lines.extend(crit_lines)
        lines.append("─" * 40)

    # Show critical labs warning (safety priority)
    if summary.critical_labs:
        crit_lines = []
        for lab in summary.critical_labs[:3]:
            flag = "‼️" if lab.interpretation in ("HH", "LL") else "⚠️"
            interp = f" [{lab.interpretation}]" if lab.interpretation else ""
            crit_lines.append(f"{flag} {lab.name}: {lab.value} {lab.unit}{interp}")
        lines.append("🚨 CRITICAL LABS:")
        lines.extend(crit_lines)
        lines.append("─" * 40)

    # Show medication interactions warning (safety priority)
    if summary.medication_interactions:
        int_lines = []
        for interaction in summary.medication_interactions[:3]:
            flag = "🚨" if interaction.severity == "high" else "⚠️"
            int_lines.append(f"{flag} {interaction.drug1} + {interaction.drug2}")
            int_lines.append(f"   → {interaction.effect}")
        lines.append("💊 DRUG INTERACTIONS:")
        lines.extend(int_lines)
        lines.append("─" * 40)

    if summary.vitals:
        # Format vitals with interpretation flags
        vital_parts = []
        for v in summary.vitals[:4]:
            flag = ""
            if v.interpretation in ("HH", "LL"):
                flag = "‼️"
            elif v.interpretation in ("H", "L"):
                flag = "↑" if v.interpretation == "H" else "↓"
            vital_parts.append(f"{v.name}: {v.value}{v.unit}{flag}")
        vital_str = " | ".join(vital_parts)
        lines.append(f"VITALS: {vital_str}")

    if summary.allergies:
        lines.append(f"⚠ ALLERGIES: {', '.join(summary.allergies[:5])}")

    if summary.medications:
        lines.append(f"💊 MEDS: {', '.join(summary.medications[:5])}")

    if summary.labs:
        # Format labs with interpretation flags
        lab_parts = []
        for lab in summary.labs[:4]:
            flag = ""
            if lab.interpretation in ("HH", "LL"):
                flag = "‼️"
            elif lab.interpretation in ("H", "L"):
                flag = "↑" if lab.interpretation == "H" else "↓"
            lab_parts.append(f"{lab.name}: {lab.value}{lab.unit}{flag}")
        lab_str = " | ".join(lab_parts)
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

    if summary.care_plans:
        plan_str = ", ".join([f"{p.title} [{p.status}]" for p in summary.care_plans[:3]])
        lines.append(f"📑 CARE PLANS: {plan_str}")

    if summary.clinical_notes:
        notes_str = ", ".join([f"{n.title} ({n.date})" for n in summary.clinical_notes[:3]])
        lines.append(f"📄 NOTES: {notes_str}")

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

    # Fetch care plans
    try:
        care_plan_bundle = await fetch_fhir(f"CarePlan?patient={patient_id}&_count=10")
        print(f"🔍 CarePlan bundle type: {care_plan_bundle.get('resourceType', 'N/A')}, entries: {len(care_plan_bundle.get('entry', []))}")
        care_plans = extract_care_plans(care_plan_bundle)
        print(f"✓ Fetched {len(care_plans)} care plans")
    except Exception as e:
        print(f"⚠️ Could not fetch care plans: {e}")
        care_plans = []

    # Fetch clinical notes (DocumentReference)
    try:
        doc_bundle = await fetch_fhir(f"DocumentReference?patient={patient_id}&_count=10")
        print(f"🔍 DocumentReference bundle type: {doc_bundle.get('resourceType', 'N/A')}, entries: {len(doc_bundle.get('entry', []))}")
        clinical_notes = extract_clinical_notes(doc_bundle)
        print(f"✓ Fetched {len(clinical_notes)} clinical notes")
    except Exception as e:
        print(f"⚠️ Could not fetch clinical notes: {e}")
        clinical_notes = []

    # Filter critical and abnormal vitals for safety alerts
    critical_vitals = [v for v in vitals if v.is_critical]
    abnormal_vitals = [v for v in vitals if v.is_abnormal]

    if critical_vitals:
        print(f"🚨 CRITICAL VITALS DETECTED: {len(critical_vitals)}")
        for v in critical_vitals:
            print(f"   ‼️ {v.name}: {v.value} {v.unit} ({v.interpretation})")

    # Filter critical and abnormal labs for safety alerts
    critical_labs = [lab for lab in labs if lab.is_critical]
    abnormal_labs = [lab for lab in labs if lab.is_abnormal]

    if critical_labs:
        print(f"🚨 CRITICAL LABS DETECTED: {len(critical_labs)}")
        for lab in critical_labs:
            print(f"   ‼️ {lab.name}: {lab.value} {lab.unit} ({lab.interpretation})")

    # Check for medication interactions
    interaction_dicts = check_medication_interactions(medications)
    medication_interactions = [
        MedicationInteraction(
            drug1=i["drug1"],
            drug2=i["drug2"],
            severity=i["severity"],
            effect=i["effect"]
        ) for i in interaction_dicts
    ]

    if medication_interactions:
        print(f"⚠️ MEDICATION INTERACTIONS DETECTED: {len(medication_interactions)}")
        for interaction in medication_interactions:
            severity_icon = "🚨" if interaction.severity == "high" else "⚠️"
            print(f"   {severity_icon} {interaction.drug1} + {interaction.drug2}: {interaction.effect}")

    summary = PatientSummary(
        patient_id=patient_id,
        name=name,
        date_of_birth=dob,
        gender=gender,
        vitals=vitals,
        critical_vitals=critical_vitals,
        abnormal_vitals=abnormal_vitals,
        has_critical_vitals=len(critical_vitals) > 0,
        allergies=allergies,
        medications=medications,
        medication_interactions=medication_interactions,
        has_interactions=len(medication_interactions) > 0,
        labs=labs,
        critical_labs=critical_labs,
        abnormal_labs=abnormal_labs,
        has_critical_labs=len(critical_labs) > 0,
        procedures=procedures,
        immunizations=immunizations,
        conditions=conditions,
        care_plans=care_plans,
        clinical_notes=clinical_notes
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

    # Extract CPT modifiers from transcript
    cpt_modifiers = []
    modifier_keywords = CPT_DB.get("modifier_keywords", {})
    modifiers_db = CPT_DB.get("modifiers", {})

    for keyword, modifier in modifier_keywords.items():
        if keyword in transcript_lower and len(cpt_modifiers) < 3:
            modifier_info = modifiers_db.get(modifier, {})
            mod_entry = {
                "modifier": modifier,
                "description": modifier_info.get("description", ""),
                "use_case": modifier_info.get("use_case", "")
            }
            if mod_entry not in cpt_modifiers:
                cpt_modifiers.append(mod_entry)

    # Auto-detect modifier -25 if E/M code AND procedure code detected
    has_em_code = any(c.get("code", "").startswith("99") for c in cpt_codes)
    has_procedure = any(not c.get("code", "").startswith("99") for c in cpt_codes)
    if has_em_code and has_procedure:
        mod_25 = {
            "modifier": "25",
            "description": "Significant, separately identifiable E/M service",
            "use_case": "E/M same day as procedure"
        }
        if mod_25 not in cpt_modifiers:
            cpt_modifiers.insert(0, mod_25)  # Priority modifier

    return {
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
        "summary": summary,
        "icd10_codes": icd10_codes,
        "cpt_codes": cpt_codes,
        "cpt_modifiers": cpt_modifiers
    }


def generate_progress_template(transcript: str, chief_complaint: str = None) -> dict:
    """Generate Progress Note using template-based extraction"""
    transcript_lower = transcript.lower()

    # Interval history - what's happened since last visit
    interval_history = f"Patient returns for follow-up. "
    if "better" in transcript_lower or "improved" in transcript_lower:
        interval_history += "Reports improvement in symptoms. "
    elif "worse" in transcript_lower or "no better" in transcript_lower:
        interval_history += "Reports worsening or no change in symptoms. "
    else:
        interval_history += "Interval history as discussed. "
    interval_history += f"Chief concern: {chief_complaint or 'Follow-up visit'}."

    # Current status
    symptom_keywords = ["pain", "ache", "fever", "cough", "tired", "nausea", "dizzy"]
    symptoms = [kw for kw in symptom_keywords if kw in transcript_lower]
    current_status = f"Current symptoms: {', '.join(symptoms) if symptoms else 'as described'}. "
    if "medication" in transcript_lower or "taking" in transcript_lower:
        current_status += "Medication compliance discussed. "

    # Physical exam
    vital_patterns = re.findall(r'(\d+/\d+|\d+\.\d+|\d+ degrees?|\d+ bpm)', transcript)
    physical_exam = "Vital signs: " + (", ".join(vital_patterns) if vital_patterns else "stable") + ". "
    physical_exam += "Exam findings as documented."

    # Assessment
    assessment = f"Patient progressing as expected. " if "better" in transcript_lower else "Condition stable, monitoring. "
    assessment += "Continue current treatment plan with modifications as noted."

    # Plan
    plan = "1. Continue current medications\n"
    plan += "2. Lifestyle modifications as discussed\n"
    plan += "3. Follow up in [timeframe]\n"
    plan += "4. Return sooner if symptoms worsen"

    summary = f"Progress note for {chief_complaint or 'follow-up'}. Patient is {('improving' if 'better' in transcript_lower else 'stable')}."

    return {
        "interval_history": interval_history,
        "current_status": current_status,
        "physical_exam": physical_exam,
        "assessment": assessment,
        "plan": plan,
        "summary": summary,
        "icd10_codes": [],  # Will be populated by caller
        "cpt_codes": []
    }


def generate_hp_template(transcript: str, chief_complaint: str = None) -> dict:
    """Generate History & Physical Note using template-based extraction"""
    transcript_lower = transcript.lower()

    # Chief complaint
    cc = chief_complaint or "See HPI"

    # History of Present Illness
    hpi = f"Patient presents with {cc}. "
    symptom_keywords = ["pain", "ache", "fever", "cough", "tired", "nausea", "dizzy", "swelling"]
    symptoms = [kw for kw in symptom_keywords if kw in transcript_lower]
    if symptoms:
        hpi += f"Associated symptoms include: {', '.join(symptoms)}. "
    hpi += "Details as discussed in encounter."

    # Past Medical History
    pmh = "See medical record for complete history. "
    conditions = ["diabetes", "hypertension", "asthma", "copd", "heart", "cancer"]
    found_conditions = [c for c in conditions if c in transcript_lower]
    if found_conditions:
        pmh += f"Notable: {', '.join(found_conditions)}."

    # Medications
    medications = "Current medications reviewed. " if "medication" in transcript_lower else "Medications as documented in chart."

    # Allergies
    allergies = "NKDA" if "no known" in transcript_lower or "no allergies" in transcript_lower else "See allergy list in chart."

    # Family History
    family_hx = "Family history reviewed. "
    if "family history" in transcript_lower:
        family_hx += "Notable findings discussed."

    # Social History
    social_hx = "Social history reviewed. "
    if "smok" in transcript_lower:
        social_hx += "Tobacco use discussed. "
    if "alcohol" in transcript_lower or "drink" in transcript_lower:
        social_hx += "Alcohol use discussed. "

    # Review of Systems
    ros = "Complete ROS performed. "
    ros += "Positive findings: " + (", ".join(symptoms) if symptoms else "as documented") + ". "
    ros += "All other systems reviewed and negative."

    # Physical Exam
    vital_patterns = re.findall(r'(\d+/\d+|\d+\.\d+|\d+ degrees?|\d+ bpm)', transcript)
    physical_exam = "VITAL SIGNS: " + (", ".join(vital_patterns) if vital_patterns else "See vitals") + "\n"
    physical_exam += "GENERAL: Alert, oriented, no acute distress\n"
    physical_exam += "Complete physical examination performed as documented."

    # Assessment
    assessment = f"New patient evaluation for {cc}. "
    assessment += "Clinical findings consistent with reported symptoms."

    # Plan
    plan = "1. Diagnostic workup as indicated\n"
    plan += "2. Initiate treatment as discussed\n"
    plan += "3. Patient education provided\n"
    plan += "4. Follow up for results/reassessment"

    summary = f"H&P completed for {cc}. New patient encounter documented."

    return {
        "chief_complaint": cc,
        "history_present_illness": hpi,
        "past_medical_history": pmh,
        "medications": medications,
        "allergies": allergies,
        "family_history": family_hx,
        "social_history": social_hx,
        "review_of_systems": ros,
        "physical_exam": physical_exam,
        "assessment": assessment,
        "plan": plan,
        "summary": summary,
        "icd10_codes": [],
        "cpt_codes": []
    }


def generate_consult_template(transcript: str, chief_complaint: str = None) -> dict:
    """Generate Consultation Note using template-based extraction"""
    transcript_lower = transcript.lower()

    # Reason for consult
    reason = chief_complaint or "Specialty evaluation requested"

    # HPI
    hpi = f"Thank you for this consultation regarding {reason}. "
    hpi += "Patient is a [age] [gender] referred for evaluation. "
    symptom_keywords = ["pain", "ache", "fever", "cough", "mass", "lesion", "abnormal"]
    symptoms = [kw for kw in symptom_keywords if kw in transcript_lower]
    if symptoms:
        hpi += f"Presenting symptoms: {', '.join(symptoms)}."

    # Relevant history
    relevant_hx = "Pertinent medical history reviewed. "
    conditions = ["diabetes", "hypertension", "surgery", "cancer", "heart"]
    found = [c for c in conditions if c in transcript_lower]
    if found:
        relevant_hx += f"Significant for: {', '.join(found)}."

    # Physical exam
    vital_patterns = re.findall(r'(\d+/\d+|\d+\.\d+|\d+ degrees?|\d+ bpm)', transcript)
    physical_exam = "Focused examination performed.\n"
    physical_exam += "Vital signs: " + (", ".join(vital_patterns) if vital_patterns else "stable") + "\n"
    physical_exam += "Pertinent findings as documented."

    # Diagnostic findings
    diagnostics = "Reviewed available studies and laboratory data. "
    if "lab" in transcript_lower or "test" in transcript_lower:
        diagnostics += "Results discussed with patient. "
    diagnostics += "Additional workup may be indicated."

    # Impression
    impression = f"Consultation for {reason}. "
    impression += "Clinical assessment and recommendations provided."

    # Recommendations
    recommendations = "RECOMMENDATIONS:\n"
    recommendations += "1. [Specific diagnostic/therapeutic recommendations]\n"
    recommendations += "2. [Follow-up plan]\n"
    recommendations += "3. [Referral considerations if any]\n"
    recommendations += "4. Will coordinate care with referring provider"

    summary = f"Consultation completed for {reason}. Recommendations provided to referring physician."

    return {
        "reason_for_consult": reason,
        "history_present_illness": hpi,
        "relevant_history": relevant_hx,
        "physical_exam": physical_exam,
        "diagnostic_findings": diagnostics,
        "impression": impression,
        "recommendations": recommendations,
        "summary": summary,
        "icd10_codes": [],
        "cpt_codes": []
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

    # Add CPT modifiers if present
    cpt_modifiers = note.get("cpt_modifiers", [])
    if cpt_modifiers:
        lines.append("")
        lines.append("▸ MODIFIERS:")
        for mod_info in cpt_modifiers[:3]:
            modifier = mod_info.get("modifier", "")
            desc = mod_info.get("description", "")
            lines.append(f"  • -{modifier}: {desc[:35]}")

    lines.append("─" * 25)
    lines.append(f"Summary: {note['summary'][:100]}")

    return "\n".join(lines)


def format_progress_display(note: dict) -> str:
    """Format Progress Note for AR display"""
    lines = [
        "═══ PROGRESS NOTE ═══",
        f"📝 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "─" * 25,
        "▸ INTERVAL HISTORY:",
        note.get("interval_history", "")[:150],
        "",
        "▸ CURRENT STATUS:",
        note.get("current_status", "")[:100],
        "",
        "▸ PHYSICAL EXAM:",
        note.get("physical_exam", "")[:100],
        "",
        "▸ ASSESSMENT:",
        note.get("assessment", "")[:100],
        "",
        "▸ PLAN:",
        note.get("plan", "")[:150],
    ]

    # Add ICD-10/CPT codes
    for code_type, label in [("icd10_codes", "ICD-10"), ("cpt_codes", "CPT")]:
        codes = note.get(code_type, [])
        if codes:
            lines.append("")
            lines.append(f"▸ {label} CODES:")
            for code_info in codes[:5]:
                lines.append(f"  • {code_info.get('code', '')}: {code_info.get('description', '')[:40]}")

    # Add CPT modifiers if present
    cpt_modifiers = note.get("cpt_modifiers", [])
    if cpt_modifiers:
        lines.append("")
        lines.append("▸ MODIFIERS:")
        for mod_info in cpt_modifiers[:3]:
            modifier = mod_info.get("modifier", "")
            desc = mod_info.get("description", "")
            lines.append(f"  • -{modifier}: {desc[:35]}")

    lines.append("─" * 25)
    lines.append(f"Summary: {note.get('summary', '')[:100]}")

    return "\n".join(lines)


def format_hp_display(note: dict) -> str:
    """Format H&P Note for AR display"""
    lines = [
        "═══ HISTORY & PHYSICAL ═══",
        f"📝 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "─" * 25,
        "▸ CHIEF COMPLAINT:",
        note.get("chief_complaint", "")[:100],
        "",
        "▸ HPI:",
        note.get("history_present_illness", "")[:150],
        "",
        "▸ PMH:",
        note.get("past_medical_history", "")[:80],
        "",
        "▸ MEDICATIONS:",
        note.get("medications", "")[:80],
        "",
        "▸ ALLERGIES:",
        note.get("allergies", "")[:50],
        "",
        "▸ SOCIAL HX:",
        note.get("social_history", "")[:60],
        "",
        "▸ ROS:",
        note.get("review_of_systems", "")[:80],
        "",
        "▸ PHYSICAL EXAM:",
        note.get("physical_exam", "")[:120],
        "",
        "▸ ASSESSMENT:",
        note.get("assessment", "")[:100],
        "",
        "▸ PLAN:",
        note.get("plan", "")[:150],
    ]

    # Add ICD-10/CPT codes
    for code_type, label in [("icd10_codes", "ICD-10"), ("cpt_codes", "CPT")]:
        codes = note.get(code_type, [])
        if codes:
            lines.append("")
            lines.append(f"▸ {label} CODES:")
            for code_info in codes[:5]:
                lines.append(f"  • {code_info.get('code', '')}: {code_info.get('description', '')[:40]}")

    # Add CPT modifiers if present
    cpt_modifiers = note.get("cpt_modifiers", [])
    if cpt_modifiers:
        lines.append("")
        lines.append("▸ MODIFIERS:")
        for mod_info in cpt_modifiers[:3]:
            modifier = mod_info.get("modifier", "")
            desc = mod_info.get("description", "")
            lines.append(f"  • -{modifier}: {desc[:35]}")

    lines.append("─" * 25)
    lines.append(f"Summary: {note.get('summary', '')[:100]}")

    return "\n".join(lines)


def format_consult_display(note: dict) -> str:
    """Format Consultation Note for AR display"""
    lines = [
        "═══ CONSULTATION NOTE ═══",
        f"📝 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "─" * 25,
        "▸ REASON FOR CONSULT:",
        note.get("reason_for_consult", "")[:100],
        "",
        "▸ HPI:",
        note.get("history_present_illness", "")[:150],
        "",
        "▸ RELEVANT HISTORY:",
        note.get("relevant_history", "")[:100],
        "",
        "▸ PHYSICAL EXAM:",
        note.get("physical_exam", "")[:100],
        "",
        "▸ DIAGNOSTIC FINDINGS:",
        note.get("diagnostic_findings", "")[:100],
        "",
        "▸ IMPRESSION:",
        note.get("impression", "")[:100],
        "",
        "▸ RECOMMENDATIONS:",
        note.get("recommendations", "")[:200],
    ]

    # Add ICD-10/CPT codes
    for code_type, label in [("icd10_codes", "ICD-10"), ("cpt_codes", "CPT")]:
        codes = note.get(code_type, [])
        if codes:
            lines.append("")
            lines.append(f"▸ {label} CODES:")
            for code_info in codes[:5]:
                lines.append(f"  • {code_info.get('code', '')}: {code_info.get('description', '')[:40]}")

    # Add CPT modifiers if present
    cpt_modifiers = note.get("cpt_modifiers", [])
    if cpt_modifiers:
        lines.append("")
        lines.append("▸ MODIFIERS:")
        for mod_info in cpt_modifiers[:3]:
            modifier = mod_info.get("modifier", "")
            desc = mod_info.get("description", "")
            lines.append(f"  • -{modifier}: {desc[:35]}")

    lines.append("─" * 25)
    lines.append(f"Summary: {note.get('summary', '')[:100]}")

    return "\n".join(lines)


def detect_note_type(transcript: str) -> tuple:
    """
    Auto-detect appropriate note type from transcript content.
    Returns (note_type, confidence, reason)
    """
    transcript_lower = transcript.lower()

    # Keywords that suggest specific note types
    progress_keywords = [
        "follow up", "follow-up", "followup", "returns for", "came back",
        "doing better", "feeling better", "no change", "still having",
        "since last visit", "medication refill", "recheck", "routine visit"
    ]

    hp_keywords = [
        "new patient", "initial visit", "first time", "never seen before",
        "admission", "admitted", "complete history", "full history",
        "new to the practice", "establishing care", "comprehensive exam"
    ]

    consult_keywords = [
        "consultation", "consult", "referred by", "referral from",
        "sent by dr", "sent by doctor", "second opinion", "specialist",
        "requesting evaluation", "thank you for the referral"
    ]

    # Count matches
    progress_score = sum(1 for kw in progress_keywords if kw in transcript_lower)
    hp_score = sum(1 for kw in hp_keywords if kw in transcript_lower)
    consult_score = sum(1 for kw in consult_keywords if kw in transcript_lower)

    # Determine best match
    scores = {
        "PROGRESS": (progress_score, "follow-up/returning patient language detected"),
        "HP": (hp_score, "new patient/comprehensive history language detected"),
        "CONSULT": (consult_score, "consultation/referral language detected")
    }

    # Find highest scoring type
    best_type = "SOAP"
    best_score = 0
    best_reason = "default - standard office visit"

    for note_type, (score, reason) in scores.items():
        if score > best_score:
            best_score = score
            best_type = note_type
            best_reason = reason

    # Calculate confidence (0-100)
    if best_score == 0:
        confidence = 50  # Default SOAP with medium confidence
    elif best_score == 1:
        confidence = 70
    elif best_score == 2:
        confidence = 85
    else:
        confidence = 95

    return best_type, confidence, best_reason


def generate_note_by_type(transcript: str, note_type: str, chief_complaint: str = None) -> tuple:
    """Generate note based on type, returns (note_data, format_function)"""
    note_type_upper = note_type.upper()

    if note_type_upper == "PROGRESS":
        note_data = generate_progress_template(transcript, chief_complaint)
        return note_data, format_progress_display
    elif note_type_upper == "HP":
        note_data = generate_hp_template(transcript, chief_complaint)
        return note_data, format_hp_display
    elif note_type_upper == "CONSULT":
        note_data = generate_consult_template(transcript, chief_complaint)
        return note_data, format_consult_display
    else:  # Default to SOAP
        note_data = generate_soap_template(transcript, chief_complaint)
        return note_data, format_soap_display


@app.post("/api/v1/notes/detect-type")
async def detect_note_type_endpoint(request: NoteRequest):
    """Detect appropriate note type from transcript content"""
    note_type, confidence, reason = detect_note_type(request.transcript)
    return {
        "suggested_type": note_type,
        "confidence": confidence,
        "reason": reason,
        "available_types": NOTE_TYPES
    }


@app.post("/api/v1/notes/generate")
async def generate_clinical_note(request: NoteRequest):
    """Generate clinical note from voice transcript - supports SOAP, PROGRESS, HP, CONSULT, AUTO"""

    try:
        note_type = request.note_type.upper()

        # AUTO mode: detect note type from transcript
        suggested_type = None
        detection_confidence = None
        detection_reason = None

        if note_type == "AUTO":
            suggested_type, detection_confidence, detection_reason = detect_note_type(request.transcript)
            note_type = suggested_type

        # Try Claude API if available (currently only supports SOAP)
        if CLAUDE_API_KEY and note_type == "SOAP":
            note_data = await generate_soap_with_claude(
                request.transcript,
                request.chief_complaint
            )
            format_func = format_soap_display
        else:
            # Use template-based generation for all note types
            note_data, format_func = generate_note_by_type(
                request.transcript,
                note_type,
                request.chief_complaint
            )

        # Add ICD-10 and CPT codes if not already present
        if not note_data.get("icd10_codes"):
            # Extract codes from SOAP template generator (reuse its logic)
            soap_data = generate_soap_template(request.transcript, request.chief_complaint)
            note_data["icd10_codes"] = soap_data.get("icd10_codes", [])
            note_data["cpt_codes"] = soap_data.get("cpt_codes", [])
            note_data["cpt_modifiers"] = soap_data.get("cpt_modifiers", [])

        # Build response
        display_text = format_func(note_data)
        timestamp = datetime.now().isoformat()

        response = {
            "note_type": note_type,
            "display_text": display_text,
            "summary": note_data.get("summary", ""),
            "timestamp": timestamp,
            "icd10_codes": note_data.get("icd10_codes", []),
            "cpt_codes": note_data.get("cpt_codes", []),
            "cpt_modifiers": note_data.get("cpt_modifiers", []),
            **note_data  # Include all note-specific fields
        }

        # Include detection info if AUTO mode was used
        if suggested_type:
            response["auto_detected"] = True
            response["detection_confidence"] = detection_confidence
            response["detection_reason"] = detection_reason

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Note generation failed: {str(e)}")


@app.post("/api/v1/notes/quick")
async def quick_note(request: NoteRequest):
    """Quick note for AR display - returns just the formatted text"""
    note = await generate_clinical_note(request)
    response = {
        "note_type": note.get("note_type", "SOAP"),
        "display_text": note.get("display_text", ""),
        "summary": note.get("summary", ""),
        "timestamp": note.get("timestamp", "")
    }

    # Include auto-detection info if present
    if note.get("auto_detected"):
        response["auto_detected"] = True
        response["detection_confidence"] = note.get("detection_confidence")
        response["detection_reason"] = note.get("detection_reason")

    return response


# ============ Note Storage (Simulated - Cerner sandbox is read-only) ============

# In-memory storage for saved notes (in production, this would go to the EHR)
saved_notes: dict = {}

# LOINC codes for clinical note types (FHIR DocumentReference.type)
NOTE_TYPE_LOINC = {
    "SOAP": {"code": "11506-3", "display": "Progress note"},
    "PROGRESS": {"code": "11506-3", "display": "Progress note"},
    "HP": {"code": "34117-2", "display": "History and physical note"},
    "CONSULT": {"code": "11488-4", "display": "Consultation note"},
}


def build_document_reference(note: dict) -> dict:
    """
    Build FHIR R4 DocumentReference from saved note.

    Maps internal note format to FHIR DocumentReference for EHR posting.
    """
    note_type = note.get("note_type", "SOAP").upper()
    loinc = NOTE_TYPE_LOINC.get(note_type, NOTE_TYPE_LOINC["SOAP"])

    # Get timestamp in ISO format
    timestamp = note.get("timestamp") or note.get("created_at") or datetime.now().isoformat()
    if not timestamp.endswith("Z") and "+" not in timestamp:
        timestamp = timestamp + "Z"

    # Base64 encode the note content
    content_text = note.get("display_text", "")
    content_b64 = base64.b64encode(content_text.encode("utf-8")).decode("utf-8")

    # Build author reference
    author = []
    if note.get("signed_by"):
        author.append({"display": note["signed_by"]})

    # Determine status
    status = "current" if note.get("signed_by") else "preliminary"

    # Build description
    description = f"{loinc['display']} - AI Generated"
    if note.get("was_edited"):
        description += " (Clinician Edited)"

    doc_ref = {
        "resourceType": "DocumentReference",
        "status": status,
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": loinc["code"],
                "display": loinc["display"]
            }]
        },
        "subject": {
            "reference": f"Patient/{note.get('patient_id', 'unknown')}"
        },
        "date": timestamp,
        "description": description,
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": content_b64
            }
        }]
    }

    if author:
        doc_ref["author"] = author

    return doc_ref


async def push_note_to_ehr(note_id: str) -> dict:
    """
    Push a saved note to the EHR as a FHIR DocumentReference.

    Returns success status and EHR document ID if successful.
    """
    # Get the saved note
    if note_id not in saved_notes:
        return {
            "success": False,
            "error": "Note not found",
            "note_id": note_id
        }

    note = saved_notes[note_id]

    # Check if already pushed
    if note.get("pushed_to_ehr") and note.get("fhir_document_id"):
        return {
            "success": True,
            "note_id": note_id,
            "fhir_id": note["fhir_document_id"],
            "message": "Note was already pushed to EHR",
            "already_pushed": True
        }

    # Build FHIR DocumentReference
    doc_ref = build_document_reference(note)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CERNER_BASE_URL}/DocumentReference",
                json=doc_ref,
                headers={
                    "Content-Type": "application/fhir+json",
                    "Accept": "application/fhir+json"
                }
            )

            if response.status_code == 201:
                # Success - extract FHIR ID from response
                result = response.json()
                fhir_id = result.get("id", "")

                # Update local note record
                note["pushed_to_ehr"] = True
                note["fhir_document_id"] = fhir_id
                note["pushed_at"] = datetime.now().isoformat()
                note["push_error"] = None

                print(f"✅ Note {note_id} pushed to EHR as DocumentReference/{fhir_id}")

                return {
                    "success": True,
                    "note_id": note_id,
                    "fhir_id": f"DocumentReference/{fhir_id}",
                    "ehr_url": f"{CERNER_BASE_URL}/DocumentReference/{fhir_id}",
                    "message": "Note pushed to EHR successfully"
                }

            elif response.status_code == 403:
                # Sandbox is read-only
                error_msg = "EHR sandbox is read-only - cannot create documents"
                note["push_error"] = error_msg
                print(f"⚠️ Note {note_id} push failed: {error_msg}")

                return {
                    "success": False,
                    "note_id": note_id,
                    "error": error_msg,
                    "status_code": 403
                }

            else:
                # Other error
                error_msg = f"EHR returned status {response.status_code}"
                try:
                    error_detail = response.json()
                    if "issue" in error_detail:
                        error_msg += f": {error_detail['issue'][0].get('diagnostics', '')}"
                except:
                    error_msg += f": {response.text[:200]}"

                note["push_error"] = error_msg
                print(f"❌ Note {note_id} push failed: {error_msg}")

                return {
                    "success": False,
                    "note_id": note_id,
                    "error": error_msg,
                    "status_code": response.status_code
                }

    except httpx.TimeoutException:
        error_msg = "Request timed out connecting to EHR"
        note["push_error"] = error_msg
        return {
            "success": False,
            "note_id": note_id,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Failed to connect to EHR: {str(e)}"
        note["push_error"] = error_msg
        return {
            "success": False,
            "note_id": note_id,
            "error": error_msg
        }


class SaveNoteRequest(BaseModel):
    patient_id: str
    note_type: str = "SOAP"
    display_text: str
    summary: str = ""
    transcript: str = ""
    timestamp: str = ""
    was_edited: bool = False  # True if note was manually edited before saving
    signed_by: str = ""  # Clinician who signed off on the note
    signed_at: str = ""  # Timestamp when note was signed
    push_to_ehr: bool = False  # If True, auto-push to EHR after saving


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
            "status": "signed" if request.signed_by else "final",
            "was_edited": request.was_edited,  # Track if clinician manually edited
            "signed_by": request.signed_by,  # Clinician who signed off
            "signed_at": request.signed_at or datetime.now().isoformat(),  # Sign-off timestamp
            # EHR push tracking
            "pushed_to_ehr": False,
            "fhir_document_id": None,
            "pushed_at": None,
            "push_error": None
        }

        # Store in memory (simulated EHR storage)
        saved_notes[note_id] = note_record

        edited_indicator = " (edited)" if request.was_edited else ""
        signed_indicator = f" by {request.signed_by}" if request.signed_by else ""
        print(f"📝 Note saved{edited_indicator}{signed_indicator}: {note_id} for patient {request.patient_id}")
        print(f"   Summary: {request.summary[:50]}..." if request.summary else "   (No summary)")

        # Auto-push to EHR if requested
        push_result = None
        if request.push_to_ehr:
            print(f"🚀 Auto-pushing note {note_id} to EHR...")
            push_result = await push_note_to_ehr(note_id)

        response = {
            "success": True,
            "note_id": note_id,
            "message": "Note saved successfully",
            "patient_id": request.patient_id,
            "timestamp": note_record["created_at"]
        }

        if push_result:
            response["push_result"] = push_result

        return response

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


@app.post("/api/v1/notes/{note_id}/push")
async def push_note_endpoint(note_id: str):
    """
    Push a saved note to the EHR as a FHIR DocumentReference.

    This creates a DocumentReference in the EHR containing the note content.
    Note: Cerner sandbox is read-only, so this will return 403 until
    production credentials are configured.
    """
    result = await push_note_to_ehr(note_id)

    if not result.get("success") and result.get("error") == "Note not found":
        raise HTTPException(status_code=404, detail="Note not found")

    return result


# ============ Real-Time Transcription WebSocket ============

@app.get("/api/v1/transcription/status")
async def transcription_status():
    """Check transcription service status and configuration"""
    return {
        "provider": TRANSCRIPTION_PROVIDER,
        "status": "ready",
        "supported_providers": ["assemblyai", "deepgram"],
        "sample_rate": 16000,
        "encoding": "linear16",
        "features": {
            "speaker_diarization": True,
            "medical_vocabulary": True,
            "specialty_auto_detection": True
        }
    }


class SpecialtyDetectionRequest(BaseModel):
    """Request for detecting medical specialties from patient conditions"""
    conditions: List[dict]  # List of {"name": "...", "code": "..."} objects


@app.post("/api/v1/transcription/detect-specialty")
async def detect_specialty(request: SpecialtyDetectionRequest):
    """
    Detect relevant medical specialties from patient conditions.

    Used to auto-load appropriate medical vocabulary for transcription.

    Request body:
    {
        "conditions": [
            {"name": "Essential hypertension", "code": "I10"},
            {"name": "Type 2 diabetes mellitus", "code": "E11.9"}
        ]
    }

    Returns detected specialties sorted by relevance.
    """
    specialties = detect_specialties_from_patient_conditions(request.conditions)

    return {
        "detected_specialties": specialties,
        "count": len(specialties),
        "vocabulary_terms_added": sum([
            21 if s == "cardiology" else
            24 if s == "pulmonology" else
            24 if s == "orthopedics" else
            20 if s == "neurology" else
            25 if s == "pediatrics" else 0
            for s in specialties
        ])
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket, specialties: str = None):
    """
    Real-time transcription WebSocket endpoint

    Query Parameters:
    - specialties: Comma-separated list of specialties (cardiology, pulmonology, orthopedics, neurology, pediatrics)
      Example: /ws/transcribe?specialties=cardiology,pulmonology

    Protocol:
    1. Client connects (optionally with ?specialties=cardiology,pulmonology)
    2. Server sends: {"type": "connected", "session_id": "...", "provider": "...", "specialties": [...]}
    3. Client optionally sends speaker context:
       {"type": "speaker_context", "clinician": "Dr. Smith", "patient": "John Doe", "others": [...]}
    4. Client optionally sends patient context for specialty detection (informational):
       {"type": "patient_context", "conditions": [{"name": "...", "code": "..."}]}
    5. Client sends audio chunks as binary data (16-bit PCM, 16kHz)
    6. Server sends transcription results:
       {"type": "transcript", "text": "...", "is_final": true/false, "speaker": "Dr. Smith"}
    7. Client sends: {"type": "stop"} to end session
    8. Server sends: {"type": "ended", "full_transcript": "..."}
    """
    await websocket.accept()

    # Generate session ID
    session_id = str(uuid.uuid4())[:8]
    session = None
    detected_specialties = []

    # Parse specialties from query parameter
    specialty_list = None
    if specialties:
        specialty_list = [s.strip().lower() for s in specialties.split(",") if s.strip()]
        valid_specialties = ["cardiology", "pulmonology", "orthopedics", "neurology", "pediatrics"]
        specialty_list = [s for s in specialty_list if s in valid_specialties]
        if specialty_list:
            print(f"📚 Specialty vocabulary requested: {specialty_list}")

    try:
        # Create transcription session with specialties
        print(f"🎤 Creating session {session_id}...")
        session = await create_session(session_id, specialties=specialty_list)
        print(f"🎤 Session created, provider connected: {session.is_active}")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "provider": TRANSCRIPTION_PROVIDER,
            "specialties": specialty_list or []
        })
        specialty_info = f" with specialties {specialty_list}" if specialty_list else ""
        print(f"🎤 Transcription session started: {session_id} ({TRANSCRIPTION_PROVIDER}){specialty_info}")

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
                    elif data.get("type") == "speaker_context":
                        # Set speaker names from client (patient chart, clinician session)
                        clinician = data.get("clinician")
                        patient = data.get("patient")
                        others = data.get("others", [])
                        session.set_speaker_context(clinician, patient, others)
                        await websocket.send_json({
                            "type": "speaker_context_set",
                            "clinician": clinician,
                            "patient": patient,
                            "others": others
                        })
                    elif data.get("type") == "patient_context":
                        # Auto-detect specialties from patient conditions
                        conditions = data.get("conditions", [])
                        if conditions:
                            detected_specialties = detect_specialties_from_patient_conditions(conditions)
                            if detected_specialties:
                                print(f"📚 Auto-detected specialties: {detected_specialties}")
                                # Note: Vocabulary is loaded at session creation time
                                # This message confirms detection for the client
                            await websocket.send_json({
                                "type": "specialties_detected",
                                "specialties": detected_specialties,
                                "count": len(detected_specialties)
                            })

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
