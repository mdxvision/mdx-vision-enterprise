"""
MDx Vision - EHR Proxy Service
Connects AR glasses to Cerner (and other EHRs) via FHIR R4
Includes AI clinical note generation

Run: python main.py
Test: curl http://localhost:8002/api/v1/patient/12724066
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Header
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum
import uvicorn
import os
import re
import json
import asyncio
import uuid
import base64
from datetime import datetime, timezone

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

# Import HIPAA audit logging
from audit import audit_logger, AuditAction

# Import RAG system (Feature #88)
try:
    from rag import (
        initialize_rag, retrieve_context, get_augmented_prompt,
        add_custom_document, rag_engine, RetrievedContext, MedicalDocument
    )
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG module not available: {e}")
    RAG_AVAILABLE = False

# Import device authentication
from auth import (
    Clinician, Device, get_clinician, save_clinician, get_device,
    get_clinician_by_device, generate_totp_secret, get_totp_qr_code,
    verify_totp, get_pairing_qr_code, complete_device_pairing,
    create_session, verify_session, invalidate_session, unlock_session,
    remote_wipe_device, get_clinician_devices, enroll_voiceprint,
    verify_voiceprint, create_test_clinician, get_enrollment_phrases,
    DeviceRegistration, TOTPVerifyRequest, SessionUnlockRequest,
    RemoteWipeRequest, VoiceprintEnrollRequest, VoiceprintVerifyRequest,
    # Feature #77: Continuous auth session management
    VoiceprintSession, get_voiceprint_session, create_voiceprint_session,
    update_voiceprint_verification, delete_voiceprint_session,
    set_re_verify_interval
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

# Simple ping endpoint for Samsung network testing
@app.get("/ping")
async def ping():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ═══════════════════════════════════════════════════════════════════════════
# DEVICE AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/auth/clinician/register")
async def register_clinician(name: str, email: str, clinician_id: Optional[str] = None):
    """Register a new clinician"""
    if not clinician_id:
        clinician_id = f"clinician-{uuid.uuid4().hex[:8]}"

    existing = get_clinician(clinician_id)
    if existing:
        raise HTTPException(status_code=400, detail="Clinician already exists")

    clinician = Clinician(clinician_id, name, email)
    clinician.totp_secret = generate_totp_secret()
    save_clinician(clinician)

    return {
        "success": True,
        "clinician_id": clinician_id,
        "name": name,
        "message": "Clinician registered. Get TOTP QR code to set up authenticator."
    }


@app.get("/api/v1/auth/clinician/{clinician_id}/totp-qr")
async def get_clinician_totp_qr(clinician_id: str):
    """Get TOTP QR code for authenticator app setup"""
    clinician = get_clinician(clinician_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Clinician not found")

    qr_base64 = get_totp_qr_code(clinician, as_base64=True)

    return {
        "clinician_id": clinician_id,
        "qr_code_base64": qr_base64,
        "instructions": "Scan this QR code with Google Authenticator, Authy, or similar app."
    }


@app.get("/api/v1/auth/clinician/{clinician_id}/pairing-qr")
async def get_device_pairing_qr(clinician_id: str, request: Request):
    """Get QR code for pairing AR glasses"""
    clinician = get_clinician(clinician_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Clinician not found")

    # Get base URL from request
    base_url = str(request.base_url).rstrip('/')

    result = get_pairing_qr_code(clinician_id, base_url)

    return {
        "clinician_id": clinician_id,
        "qr_code_base64": result["qr_code"],
        "expires_in": result["expires_in"],
        "instructions": "Scan this QR code with your AR glasses to pair them."
    }


@app.post("/api/v1/auth/device/pair")
async def pair_device(token: str, device_id: str, device_name: str = "AR Glasses"):
    """Complete device pairing after QR scan"""
    result = complete_device_pairing(token, device_id, device_name)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.post("/api/v1/auth/device/unlock")
async def unlock_device(request: SessionUnlockRequest):
    """Unlock device session with TOTP code"""
    result = unlock_session(request.device_id, request.totp_code)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    # Audit log
    clinician = get_clinician_by_device(request.device_id)
    if clinician:
        audit_logger._log_event(
            event_type="AUTH",
            action="SESSION_UNLOCK",
            clinician_id=clinician.clinician_id,
            clinician_name=clinician.name,
            device_id=request.device_id,
            status="success"
        )

    return result


@app.post("/api/v1/auth/device/lock")
async def lock_device(device_id: str):
    """Lock device session (logout)"""
    invalidate_session(device_id)

    audit_logger._log_event(
        event_type="AUTH",
        action="SESSION_LOCK",
        device_id=device_id,
        status="success"
    )

    return {"success": True, "message": "Device locked"}


@app.post("/api/v1/auth/device/verify-session")
async def verify_device_session(device_id: str, session_token: str):
    """Verify a session is still valid"""
    is_valid = verify_session(device_id, session_token)

    if not is_valid:
        device = get_device(device_id)
        if device and device.is_wiped:
            return {"valid": False, "reason": "device_wiped", "message": "Device has been remotely wiped"}
        return {"valid": False, "reason": "session_expired", "message": "Session expired. Please unlock again."}

    return {"valid": True}


@app.post("/api/v1/auth/device/wipe")
async def wipe_device(request: RemoteWipeRequest):
    """Remotely wipe a device"""
    result = remote_wipe_device(request.device_id, request.admin_token)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    audit_logger._log_event(
        event_type="AUTH",
        action="REMOTE_WIPE",
        device_id=request.device_id,
        status="success",
        details="Device remotely wiped"
    )

    return result


@app.get("/api/v1/auth/clinician/{clinician_id}/devices")
async def list_clinician_devices(clinician_id: str):
    """List all devices for a clinician"""
    clinician = get_clinician(clinician_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Clinician not found")

    devices = get_clinician_devices(clinician_id)

    return {
        "clinician_id": clinician_id,
        "clinician_name": clinician.name,
        "devices": devices
    }


@app.get("/api/v1/auth/voiceprint/phrases")
async def get_voiceprint_phrases():
    """Get the phrases user should read for voiceprint enrollment"""
    return {
        "phrases": get_enrollment_phrases(),
        "instructions": "Record yourself speaking each phrase clearly. Minimum 3 samples required.",
        "min_samples": 3
    }


@app.post("/api/v1/auth/voiceprint/enroll")
async def enroll_clinician_voiceprint(request: VoiceprintEnrollRequest):
    """Enroll voiceprint for a device's clinician"""
    clinician = get_clinician_by_device(request.device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    result = enroll_voiceprint(clinician, request.audio_samples)

    audit_logger._log_event(
        event_type="AUTH",
        action="VOICEPRINT_ENROLL",
        clinician_id=clinician.clinician_id,
        device_id=request.device_id,
        status="success"
    )

    return result


@app.post("/api/v1/auth/voiceprint/verify")
async def verify_clinician_voiceprint(request: VoiceprintVerifyRequest):
    """Verify voiceprint for sensitive operation"""
    clinician = get_clinician_by_device(request.device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    result = verify_voiceprint(clinician, request.audio_sample)

    audit_logger._log_event(
        event_type="AUTH",
        action="VOICEPRINT_VERIFY",
        clinician_id=clinician.clinician_id,
        device_id=request.device_id,
        status="success" if result["success"] else "failed",
        details=f"Confidence: {result.get('confidence', 0)}"
    )

    return result


@app.get("/api/v1/auth/voiceprint/{device_id}/status")
async def get_voiceprint_status(device_id: str):
    """Check if clinician has voiceprint enrolled"""
    clinician = get_clinician_by_device(device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    from voiceprint import is_enrolled
    enrolled = is_enrolled(clinician.clinician_id)

    return {
        "enrolled": enrolled,
        "clinician_id": clinician.clinician_id,
        "clinician_name": clinician.name
    }


@app.delete("/api/v1/auth/voiceprint/{device_id}")
async def delete_device_voiceprint(device_id: str):
    """Delete clinician's voiceprint enrollment"""
    from auth import delete_clinician_voiceprint

    clinician = get_clinician_by_device(device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    result = delete_clinician_voiceprint(clinician)

    audit_logger._log_event(
        event_type="AUTH",
        action="VOICEPRINT_DELETE",
        clinician_id=clinician.clinician_id,
        device_id=device_id,
        status="success" if result.get("success") else "failed"
    )

    return result


# ==================== Feature #77: Continuous Auth Endpoints ====================

@app.get("/api/v1/auth/voiceprint/{device_id}/check")
async def check_voiceprint_verification_status(device_id: str):
    """
    Check if voiceprint re-verification is needed (Feature #77)
    Returns verification status, confidence decay, and time until next verification
    """
    clinician = get_clinician_by_device(device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    session = get_voiceprint_session(device_id)

    if not session:
        # No session exists - check if enrolled
        from voiceprint import is_enrolled
        enrolled = is_enrolled(clinician.clinician_id)
        return {
            "has_session": False,
            "enrolled": enrolled,
            "needs_verification": True,
            "message": "No active voiceprint session" if enrolled else "Voiceprint not enrolled"
        }

    return {
        "has_session": True,
        "enrolled": True,
        "needs_verification": session.needs_re_verification(),
        "last_verified_at": session.last_verified_at.isoformat() if session.last_verified_at else None,
        "confidence": session.confidence_decay(),
        "original_confidence": session.confidence_score,
        "seconds_until_verification": session.seconds_until_re_verification(),
        "verification_count": session.verification_count,
        "re_verify_interval_seconds": session.re_verify_interval_seconds
    }


@app.post("/api/v1/auth/voiceprint/{device_id}/re-verify")
async def re_verify_voiceprint(device_id: str, request: VoiceprintVerifyRequest):
    """
    Perform voiceprint re-verification (Feature #77)
    Updates session with new verification timestamp and confidence
    """
    clinician = get_clinician_by_device(device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    # Use existing verification logic
    result = verify_voiceprint(clinician, request.audio_sample)

    if result.get("verified"):
        # Update session with new verification
        session = update_voiceprint_verification(device_id, result.get("confidence", 0.0))

        if not session:
            # Create new session if none exists
            session = create_voiceprint_session(
                device_id=device_id,
                clinician_id=clinician.clinician_id,
                confidence=result.get("confidence", 0.0)
            )

        audit_logger._log_event(
            event_type="AUTH",
            action="VOICEPRINT_REVERIFY",
            clinician_id=clinician.clinician_id,
            device_id=device_id,
            status="success",
            details={"confidence": result.get("confidence"), "verification_count": session.verification_count}
        )

        return {
            "verified": True,
            "confidence": result.get("confidence"),
            "session_updated": True,
            "next_verification_in": session.seconds_until_re_verification(),
            "verification_count": session.verification_count
        }
    else:
        audit_logger._log_event(
            event_type="AUTH",
            action="VOICEPRINT_REVERIFY",
            clinician_id=clinician.clinician_id,
            device_id=device_id,
            status="failed",
            details={"confidence": result.get("confidence"), "reason": result.get("error")}
        )

        return {
            "verified": False,
            "confidence": result.get("confidence"),
            "error": result.get("error", "Verification failed")
        }


@app.put("/api/v1/auth/voiceprint/{device_id}/interval")
async def set_voiceprint_re_verify_interval(device_id: str, interval_seconds: int):
    """
    Set custom re-verification interval for a device (Feature #77)
    Default is 300 seconds (5 minutes)
    """
    clinician = get_clinician_by_device(device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    if interval_seconds < 60:
        raise HTTPException(status_code=400, detail="Interval must be at least 60 seconds")

    if interval_seconds > 3600:
        raise HTTPException(status_code=400, detail="Interval cannot exceed 3600 seconds (1 hour)")

    session = set_re_verify_interval(device_id, interval_seconds)

    if not session:
        raise HTTPException(status_code=404, detail="No active voiceprint session")

    audit_logger._log_event(
        event_type="AUTH",
        action="VOICEPRINT_INTERVAL_SET",
        clinician_id=clinician.clinician_id,
        device_id=device_id,
        status="success",
        details={"interval_seconds": interval_seconds}
    )

    return {
        "success": True,
        "re_verify_interval_seconds": session.re_verify_interval_seconds,
        "message": f"Re-verification interval set to {interval_seconds // 60} minutes"
    }


async def require_fresh_voiceprint(device_id: str, min_confidence: float = 0.60):
    """
    Middleware helper to enforce fresh voiceprint verification (Feature #77)
    Call this before sensitive operations (push notes, push vitals, etc.)

    Raises:
        HTTPException 401 if voiceprint not enrolled
        HTTPException 403 if re-verification required (with X-Require-Voiceprint header)

    Returns:
        VoiceprintSession if verification is fresh and confidence is sufficient
    """
    clinician = get_clinician_by_device(device_id)
    if not clinician:
        raise HTTPException(status_code=404, detail="Device not registered")

    session = get_voiceprint_session(device_id)

    if not session:
        # Check if enrolled at all
        from voiceprint import is_enrolled
        if not is_enrolled(clinician.clinician_id):
            raise HTTPException(
                status_code=401,
                detail="Voiceprint not enrolled",
                headers={"X-Require-Voiceprint": "enroll"}
            )
        raise HTTPException(
            status_code=403,
            detail="Voiceprint verification required",
            headers={"X-Require-Voiceprint": "verify"}
        )

    if session.needs_re_verification():
        raise HTTPException(
            status_code=403,
            detail="Voiceprint re-verification required",
            headers={"X-Require-Voiceprint": "re-verify"}
        )

    current_confidence = session.confidence_decay()
    if current_confidence < min_confidence:
        raise HTTPException(
            status_code=403,
            detail=f"Voiceprint confidence too low ({current_confidence:.2f} < {min_confidence})",
            headers={"X-Require-Voiceprint": "re-verify"}
        )

    return session


@app.get("/api/v1/auth/device/{device_id}/status")
async def get_device_status(device_id: str):
    """Get device status (for checking if wiped, locked, etc.)"""
    device = get_device(device_id)
    if not device:
        return {"registered": False}

    return {
        "registered": True,
        "device_id": device.device_id,
        "is_active": device.is_active,
        "is_wiped": device.is_wiped,
        "has_session": device.session_token is not None,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None
    }

# Minimal patient endpoint for Samsung (returns compact data, no slow FHIR calls)
@app.get("/api/v1/patient/{patient_id}/quick")
async def get_patient_quick(patient_id: str):
    """Quick patient lookup - compact data for Samsung network issues"""
    return {
        "patient_id": patient_id,
        "name": "SMARTS SR., NANCYS II",
        "date_of_birth": "1990-09-15",
        "gender": "female",
        "allergies": [
            {"substance": "Penicillin", "severity": "high", "reaction": "Anaphylaxis"},
            {"substance": "Sulfa drugs", "severity": "moderate", "reaction": "Rash"}
        ],
        "vitals": [
            {"name": "Blood Pressure", "value": "142/88", "unit": "mmHg", "is_critical": True},
            {"name": "Heart Rate", "value": "92", "unit": "bpm", "is_critical": False},
            {"name": "Temperature", "value": "98.6", "unit": "°F", "is_critical": False},
            {"name": "SpO2", "value": "97", "unit": "%", "is_critical": False}
        ],
        "conditions": [
            "Type 2 Diabetes Mellitus",
            "Essential Hypertension",
            "Hyperlipidemia"
        ],
        "medications": [
            "Metformin 500mg BID",
            "Lisinopril 10mg daily",
            "Atorvastatin 20mg daily"
        ],
        "display_text": "SMARTS SR., NANCYS II\\nDOB: 1990-09-15 | Female\\n\\n⚠️ ALLERGIES: Penicillin (Anaphylaxis), Sulfa drugs\\n\\n📊 VITALS:\\nBP: 142/88 mmHg (HIGH)\\nHR: 92 bpm\\nTemp: 98.6°F\\nSpO2: 97%\\n\\n🏥 CONDITIONS:\\n• Type 2 Diabetes\\n• Hypertension\\n• Hyperlipidemia\\n\\n💊 MEDICATIONS:\\n• Metformin 500mg BID\\n• Lisinopril 10mg daily\\n• Atorvastatin 20mg daily"
    }


class VitalSign(BaseModel):
    name: str
    value: str
    unit: str
    date: str = ""
    interpretation: str = ""   # e.g., "H", "L", "HH", "LL", "N"
    is_critical: bool = False  # True if dangerously out of range
    is_abnormal: bool = False  # True if outside normal range
    # Trend tracking fields
    previous_value: Optional[str] = None
    previous_date: Optional[str] = None
    trend: Optional[str] = None  # "rising", "falling", "stable", "new"
    delta: Optional[str] = None  # e.g., "+5", "-10"


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
    # Trend tracking fields
    previous_value: Optional[str] = None
    previous_date: Optional[str] = None
    trend: Optional[str] = None  # "rising", "falling", "stable", "new"
    delta: Optional[str] = None  # e.g., "+0.5", "-1.2"


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
    photo_url: Optional[str] = None  # Patient photo URL or base64 data URI
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


# ═══════════════════════════════════════════════════════════════════════════
# PATIENT WORKLIST MODELS
# ═══════════════════════════════════════════════════════════════════════════

class WorklistPatient(BaseModel):
    """Patient in the daily worklist"""
    patient_id: str
    name: str
    date_of_birth: str
    gender: str
    mrn: Optional[str] = None
    room: Optional[str] = None
    appointment_time: Optional[str] = None
    appointment_type: Optional[str] = None  # Follow-up, New Patient, Urgent, etc.
    chief_complaint: Optional[str] = None
    provider: Optional[str] = None
    status: str = "scheduled"  # scheduled, checked_in, in_room, in_progress, completed, no_show
    checked_in_at: Optional[str] = None
    encounter_started_at: Optional[str] = None
    has_critical_alerts: bool = False
    priority: int = 0  # 0=normal, 1=urgent, 2=stat

class WorklistResponse(BaseModel):
    """Response containing the daily worklist"""
    date: str
    provider: Optional[str] = None
    location: Optional[str] = None
    patients: List[WorklistPatient]
    total_scheduled: int
    checked_in: int
    in_progress: int
    completed: int

class CheckInRequest(BaseModel):
    """Request to check in a patient"""
    patient_id: str
    room: Optional[str] = None
    chief_complaint: Optional[str] = None

class UpdateWorklistStatusRequest(BaseModel):
    """Request to update patient status in worklist"""
    patient_id: str
    status: str  # checked_in, in_room, in_progress, completed, no_show
    room: Optional[str] = None
    notes: Optional[str] = None

class OrderUpdateRequest(BaseModel):
    """Request to update an existing order"""
    order_id: str
    patient_id: str
    priority: Optional[str] = None  # routine, urgent, stat
    dose: Optional[str] = None
    frequency: Optional[str] = None
    notes: Optional[str] = None
    cancel: bool = False


# Differential Diagnosis Models
class DdxRequest(BaseModel):
    """Request model for AI differential diagnosis generation"""
    chief_complaint: str
    symptoms: List[str] = []
    vitals: Optional[Dict[str, str]] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: List[str] = []
    medications: List[str] = []
    allergies: List[str] = []


class DifferentialDiagnosis(BaseModel):
    """Single differential diagnosis with supporting data"""
    rank: int
    diagnosis: str
    icd10_code: str
    likelihood: str  # "high", "moderate", "low"
    supporting_findings: List[str]
    red_flags: List[str] = []
    next_steps: List[str] = []


class DdxResponse(BaseModel):
    """Response model for differential diagnosis list"""
    differentials: List[DifferentialDiagnosis]
    clinical_reasoning: str
    urgent_considerations: List[str] = []
    timestamp: str


# Medical Image Analysis Models
class ImageAnalysisRequest(BaseModel):
    """Request model for medical image analysis"""
    image_base64: str
    media_type: str = "image/jpeg"
    patient_id: Optional[str] = None
    analysis_context: Optional[str] = None  # "wound", "rash", "xray", "general"
    chief_complaint: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None


class ImageFinding(BaseModel):
    """Individual finding from image analysis"""
    finding: str
    confidence: str  # "high", "moderate", "low"
    location: Optional[str] = None
    characteristics: List[str] = []


class ImageAnalysisResponse(BaseModel):
    """Response model for medical image analysis"""
    assessment: str
    findings: List[ImageFinding]
    icd10_codes: List[Dict[str, str]]
    recommendations: List[str]
    red_flags: List[str]
    differential_considerations: List[str]
    disclaimer: str
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# AI CLINICAL CO-PILOT MODELS (Feature #78)
# ═══════════════════════════════════════════════════════════════════════════════

class CopilotMessage(BaseModel):
    """Single message in copilot conversation"""
    role: str  # "user" or "assistant"
    content: str


class CopilotAction(BaseModel):
    """Actionable suggestion from copilot"""
    action_type: str  # "order", "calculate", "template", "lookup"
    label: str  # Display text
    command: str  # Voice command to execute


class CopilotRequest(BaseModel):
    """Request model for copilot chat"""
    message: str
    patient_context: Optional[Dict] = None  # Current patient summary
    conversation_history: List[CopilotMessage] = []
    include_actions: bool = True  # Whether to suggest actionable commands


class CopilotResponse(BaseModel):
    """Response model for copilot chat"""
    response: str  # Main response text (TTS-optimized)
    suggestions: List[str] = []  # Follow-up question prompts
    actions: List[CopilotAction] = []  # Actionable commands
    references: List[str] = []  # ICD-10 codes, guidelines mentioned
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# RACIAL MEDICINE AWARENESS MODELS (Feature #79)
# ═══════════════════════════════════════════════════════════════════════════════

class FitzpatrickSkinType(str, Enum):
    """Fitzpatrick Skin Type Scale (I-VI)"""
    TYPE_I = "I"      # Very light, always burns, never tans
    TYPE_II = "II"    # Light, burns easily, tans minimally
    TYPE_III = "III"  # Medium, burns moderately, tans gradually
    TYPE_IV = "IV"    # Olive, burns minimally, tans well
    TYPE_V = "V"      # Brown, rarely burns, tans darkly
    TYPE_VI = "VI"    # Dark brown/black, never burns


class RacialMedicineAlert(BaseModel):
    """Clinical alert for racial medicine considerations"""
    alert_type: str  # "pulse_ox", "medication", "skin_assessment", "algorithm", "pain", "maternal", "sickle_cell"
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    recommendation: str
    evidence_source: Optional[str] = None


class PatientPhysiologicProfile(BaseModel):
    """Physiologic factors that may affect clinical care - NOT race-based assumptions"""
    fitzpatrick_type: Optional[FitzpatrickSkinType] = None
    self_reported_ancestry: Optional[List[str]] = None  # For pharmacogenomics context
    pharmacogenomic_tested: bool = False
    known_genetic_variants: Optional[List[str]] = None  # e.g., ["GRK5", "CYP2D6"]
    sickle_cell_status: Optional[str] = None  # "trait", "disease", "negative", "unknown"
    g6pd_status: Optional[str] = None  # "deficient", "normal", "unknown"


class RacialMedicineRequest(BaseModel):
    """Request for racial medicine clinical decision support"""
    patient_id: str
    fitzpatrick_type: Optional[FitzpatrickSkinType] = None
    self_reported_ancestry: Optional[List[str]] = None
    clinical_context: Optional[str] = None  # "vitals", "medication", "skin_exam", "pain", "obstetric"
    current_readings: Optional[Dict] = None  # e.g., {"spo2": 94}
    pending_orders: Optional[List[str]] = None  # Medications being ordered


class RacialMedicineResponse(BaseModel):
    """Response with racial medicine alerts and guidance"""
    alerts: List[RacialMedicineAlert] = []
    skin_assessment_guidance: Optional[Dict] = None
    medication_considerations: Optional[List[Dict]] = None
    calculator_warnings: Optional[List[str]] = None
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# CULTURAL CARE PREFERENCES MODELS (Feature #80)
# ═══════════════════════════════════════════════════════════════════════════════

class BloodProductPreference(BaseModel):
    """Blood product acceptance preferences (esp. for Jehovah's Witnesses)"""
    whole_blood: bool = True
    red_cells: bool = True
    white_cells: bool = True
    platelets: bool = True
    plasma: bool = True
    albumin: Optional[bool] = None  # Individual conscience
    immunoglobulins: Optional[bool] = None
    clotting_factors: Optional[bool] = None
    cell_salvage: Optional[bool] = None
    hemodilution: Optional[bool] = None


class DecisionMakingStyle(str, Enum):
    """Family involvement in healthcare decisions"""
    INDIVIDUAL = "individual"  # Patient decides alone
    FAMILY_CENTERED = "family_centered"  # Family makes decisions together
    PATRIARCH_LED = "patriarch_led"  # Elder/head of family decides
    SHARED = "shared"  # Shared between patient and family
    DEFER_TO_PHYSICIAN = "defer_to_physician"  # Doctor decides


class CommunicationPreference(str, Enum):
    """How patient prefers to receive health information"""
    DIRECT = "direct"  # Tell patient directly
    INDIRECT = "indirect"  # Soften/gradual disclosure
    FAMILY_FIRST = "family_first"  # Tell family, they tell patient
    FAMILY_PRESENT = "family_present"  # Tell patient with family present


class CulturalCarePreferences(BaseModel):
    """Patient cultural and religious care preferences"""
    religion: Optional[str] = None
    dietary_restrictions: List[str] = []  # "halal", "kosher", "vegetarian", "vegan"
    blood_product_preferences: Optional[BloodProductPreference] = None
    decision_making_style: DecisionMakingStyle = DecisionMakingStyle.INDIVIDUAL
    primary_decision_maker: Optional[str] = None  # Name/relationship if not patient
    communication_preference: CommunicationPreference = CommunicationPreference.DIRECT
    provider_gender_preference: Optional[str] = None  # "female", "male", "no_preference"
    interpreter_needed: bool = False
    preferred_language: str = "en"
    modesty_requirements: List[str] = []  # "same_gender_provider", "chaperone", "minimal_exposure"
    religious_garments: List[str] = []  # "hijab", "turban", "kippah"
    fasting_status: Optional[str] = None  # "ramadan", "yom_kippur", "lent", None
    traditional_medicine: List[str] = []  # "tcm", "ayurveda", "curanderismo"
    end_of_life_preferences: Optional[Dict] = None  # AD info
    family_contacts_for_decisions: List[Dict] = []  # [{name, relationship, phone}]


class CulturalCareAlert(BaseModel):
    """Alert for cultural care considerations"""
    alert_type: str  # "dietary", "blood_product", "modesty", "fasting", "religious", "family"
    severity: str  # "info", "warning", "action_required"
    title: str
    message: str
    recommendation: str


class CulturalCareRequest(BaseModel):
    """Request cultural care guidance"""
    patient_id: str
    preferences: Optional[CulturalCarePreferences] = None
    clinical_context: Optional[str] = None  # "medication_order", "procedure", "exam", "eol"
    pending_orders: Optional[List[str]] = None


class CulturalCareResponse(BaseModel):
    """Response with cultural care alerts and guidance"""
    alerts: List[CulturalCareAlert] = []
    dietary_medication_concerns: List[Dict] = []  # Medications with restricted ingredients
    blood_product_guidance: Optional[Dict] = None
    modesty_accommodations: List[str] = []
    communication_guidance: Optional[str] = None
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# IMPLICIT BIAS ALERTS (Feature #81) - Gentle reminders during clinical documentation
# ═══════════════════════════════════════════════════════════════════════════════

class ImplicitBiasContext(str, Enum):
    """Clinical contexts where implicit bias may affect care"""
    PAIN_ASSESSMENT = "pain_assessment"
    PAIN_MEDICATION = "pain_medication"
    TRIAGE = "triage"
    CARDIAC_SYMPTOMS = "cardiac_symptoms"
    PSYCHIATRIC = "psychiatric"
    SUBSTANCE_USE = "substance_use"
    GENERAL = "general"


class ImplicitBiasAlert(BaseModel):
    """
    Gentle, evidence-based reminder about potential implicit bias.
    Framed as educational, not accusatory.
    """
    context: ImplicitBiasContext
    title: str
    reminder: str  # The gentle prompt
    evidence: str  # Research citation supporting the reminder
    reflection_prompt: str  # Question to encourage self-reflection
    resources: List[str] = []  # Optional links to training/resources


class ImplicitBiasRequest(BaseModel):
    """Request bias check during documentation"""
    patient_id: str
    patient_ancestry: Optional[str] = None  # From Feature #79
    patient_gender: Optional[str] = None
    clinical_context: ImplicitBiasContext
    transcript_keywords: List[str] = []  # Keywords detected in documentation
    chief_complaint: Optional[str] = None
    documented_pain_score: Optional[int] = None
    medications_ordered: List[str] = []


class ImplicitBiasResponse(BaseModel):
    """Response with applicable bias reminders"""
    should_show_reminder: bool = False
    alerts: List[ImplicitBiasAlert] = []
    context_detected: Optional[ImplicitBiasContext] = None
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# MATERNAL HEALTH MONITORING (Feature #82) - High-risk OB alerts for Black mothers
# ═══════════════════════════════════════════════════════════════════════════════

class MaternalStatus(str, Enum):
    """Patient's maternal status"""
    NOT_PREGNANT = "not_pregnant"
    PREGNANT = "pregnant"
    POSTPARTUM = "postpartum"  # Within 12 months of delivery
    UNKNOWN = "unknown"


class MaternalRiskLevel(str, Enum):
    """Risk stratification for maternal patients"""
    STANDARD = "standard"
    ELEVATED = "elevated"  # Based on ancestry disparity data
    HIGH = "high"  # Multiple risk factors


class MaternalWarningSign(BaseModel):
    """Individual warning sign with urgency level"""
    symptom: str
    description: str
    urgency: str  # "emergency", "urgent", "routine"
    action: str  # What to do if present
    ask_patient: str  # How to ask about this symptom


class MaternalHealthAlert(BaseModel):
    """Alert for maternal health considerations"""
    alert_type: str  # "disparity_awareness", "warning_sign", "postpartum_check", "preeclampsia", etc.
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    recommendation: str
    warning_signs: List[MaternalWarningSign] = []
    evidence: Optional[str] = None


class MaternalHealthRequest(BaseModel):
    """Request maternal health assessment"""
    patient_id: str
    patient_ancestry: Optional[str] = None
    maternal_status: MaternalStatus = MaternalStatus.UNKNOWN
    gestational_weeks: Optional[int] = None  # If pregnant
    postpartum_weeks: Optional[int] = None  # If postpartum
    current_symptoms: List[str] = []  # Symptoms patient is reporting
    vital_signs: Optional[Dict] = None  # BP, HR, etc.
    conditions: List[str] = []  # Existing conditions from chart


class MaternalHealthResponse(BaseModel):
    """Response with maternal health alerts and guidance"""
    risk_level: MaternalRiskLevel
    alerts: List[MaternalHealthAlert] = []
    warning_signs_to_check: List[MaternalWarningSign] = []
    disparity_context: Optional[str] = None  # Explanation of disparity risk
    postpartum_checklist: List[str] = []
    timestamp: str


# SDOH (Social Determinants of Health) Models (Feature #84)
# ═══════════════════════════════════════════════════════════════════════════════

class SDOHDomain(str, Enum):
    """SDOH domains from Healthy People 2030"""
    ECONOMIC_STABILITY = "economic_stability"  # Employment, income, expenses, debt
    EDUCATION = "education"  # Literacy, language, early childhood education
    HEALTHCARE_ACCESS = "healthcare_access"  # Coverage, provider availability
    NEIGHBORHOOD = "neighborhood"  # Housing, transportation, safety
    SOCIAL_COMMUNITY = "social_community"  # Support systems, discrimination


class SDOHRiskLevel(str, Enum):
    """Risk level for SDOH factors"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"  # Immediate intervention needed


class SDOHFactor(BaseModel):
    """Individual SDOH risk factor"""
    domain: SDOHDomain
    factor: str
    description: str
    risk_level: SDOHRiskLevel
    clinical_impact: str  # How this affects care
    screening_question: str  # How to ask about this
    icd10_code: Optional[str] = None  # Z-codes for SDOH


class SDOHIntervention(BaseModel):
    """Recommended intervention for SDOH factor"""
    factor: str
    intervention_type: str  # "referral", "resource", "accommodation", "care_modification"
    title: str
    description: str
    resources: List[str] = []  # Local/national resources
    urgency: str = "routine"  # "immediate", "urgent", "routine"


class SDOHAlert(BaseModel):
    """Alert for SDOH-related care considerations"""
    alert_type: str  # "adherence_risk", "access_barrier", "safety_concern", "care_gap"
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    domain: SDOHDomain
    clinical_impact: str
    recommendations: List[str] = []
    interventions: List[SDOHIntervention] = []
    z_codes: List[str] = []  # Relevant ICD-10 Z-codes


class SDOHScreeningRequest(BaseModel):
    """Request for SDOH screening/assessment"""
    patient_id: str
    responses: Dict[str, str] = {}  # Question ID -> response
    known_factors: List[str] = []  # Previously identified SDOH factors
    current_medications: List[str] = []  # For adherence risk assessment
    upcoming_appointments: List[str] = []  # For transportation assessment


class SDOHScreeningResponse(BaseModel):
    """Response with SDOH assessment results"""
    patient_id: str
    overall_risk: SDOHRiskLevel
    domain_risks: Dict[str, SDOHRiskLevel] = {}  # Domain -> risk level
    identified_factors: List[SDOHFactor] = []
    alerts: List[SDOHAlert] = []
    recommended_interventions: List[SDOHIntervention] = []
    z_codes_for_billing: List[Dict[str, str]] = []  # Code + description
    screening_complete: bool = False
    timestamp: str


# HEALTH LITERACY ASSESSMENT (Feature #85)
# ═══════════════════════════════════════════════════════════════════════════════

class LiteracyLevel(str, Enum):
    """Health literacy levels based on validated assessments"""
    INADEQUATE = "inadequate"  # Below 6th grade, needs pictures/verbal
    MARGINAL = "marginal"  # 6th-8th grade, simplified language
    ADEQUATE = "adequate"  # High school level, standard instructions
    PROFICIENT = "proficient"  # College level, can handle medical terminology


class ReadingLevel(str, Enum):
    """Reading grade levels for materials"""
    GRADE_3_5 = "3-5"  # Very simple, picture-based
    GRADE_5_6 = "5-6"  # Simple sentences, basic words
    GRADE_7_8 = "7-8"  # Standard simplified
    GRADE_9_12 = "9-12"  # Standard materials
    COLLEGE = "college"  # Medical terminology acceptable


class LiteracyScreeningMethod(str, Enum):
    """Validated health literacy screening methods"""
    BRIEF = "brief"  # Single question: "How confident filling out forms?"
    REALM_SF = "realm_sf"  # Rapid Estimate of Adult Literacy in Medicine - Short Form
    NVS = "nvs"  # Newest Vital Sign - 6 questions about nutrition label
    SILS = "sils"  # Single Item Literacy Screener
    OBSERVED = "observed"  # Clinician observation


class TeachBackStatus(str, Enum):
    """Status of teach-back verification"""
    NOT_DONE = "not_done"
    PARTIAL = "partial"  # Understood some concepts
    COMPLETE = "complete"  # Successfully demonstrated understanding
    NEEDS_REPEAT = "needs_repeat"  # Failed, needs re-education


class LiteracyAssessment(BaseModel):
    """Patient health literacy assessment result"""
    patient_id: str
    literacy_level: LiteracyLevel
    recommended_reading_level: ReadingLevel
    screening_method: LiteracyScreeningMethod
    confidence_score: Optional[float] = None  # 0-1 confidence in assessment
    risk_factors: List[str] = []  # Factors that may indicate low literacy
    accommodations: List[str] = []  # Recommended accommodations
    teach_back_required: bool = True
    assessed_at: str


class DischargeInstruction(BaseModel):
    """Discharge instruction at specific reading level"""
    topic: str
    standard_text: str  # Original medical language
    simplified_text: str  # Plain language version
    reading_level: ReadingLevel
    key_points: List[str] = []  # Bullet points to emphasize
    visual_aids: List[str] = []  # Recommended images/diagrams
    teach_back_questions: List[str] = []  # Questions to verify understanding


class LiteracyAdaptedInstructions(BaseModel):
    """Complete set of literacy-adapted patient instructions"""
    patient_id: str
    literacy_level: LiteracyLevel
    reading_level: ReadingLevel
    instructions: List[DischargeInstruction] = []
    general_tips: List[str] = []  # Tips for clinician communication
    red_flags_simplified: List[str] = []  # When to return, in plain language
    medication_instructions: List[Dict[str, str]] = []  # Simplified med instructions
    follow_up_simplified: str = ""  # Plain language follow-up info
    teach_back_checklist: List[str] = []  # Items to verify understanding


# INTERPRETER INTEGRATION (Feature #86)
# ═══════════════════════════════════════════════════════════════════════════════

class InterpreterType(str, Enum):
    """Type of interpreter service"""
    IN_PERSON = "in_person"  # On-site interpreter
    VIDEO = "video"  # Video remote interpreting (VRI)
    PHONE = "phone"  # Over-the-phone interpreting (OPI)
    STAFF = "staff"  # Qualified bilingual staff
    AD_HOC = "ad_hoc"  # Qualified ad-hoc interpreter


class InterpreterStatus(str, Enum):
    """Status of interpreter request"""
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class LanguagePreference(BaseModel):
    """Patient's language preferences"""
    preferred_language: str  # ISO 639-1 code (es, zh, vi, etc.)
    preferred_language_name: str  # Display name
    english_proficiency: str  # "none", "limited", "functional", "fluent"
    reads_preferred_language: bool = True
    writes_preferred_language: bool = True
    sign_language: Optional[str] = None  # ASL, BSL, etc.
    interpreter_required: bool = True
    family_interpreter_declined: bool = False  # Patient declined using family


class InterpreterRequest(BaseModel):
    """Request for interpreter services"""
    request_id: Optional[str] = None
    patient_id: str
    language: str  # ISO 639-1 code
    language_name: str
    interpreter_type: InterpreterType
    urgency: str = "routine"  # "stat", "urgent", "routine"
    encounter_type: str = "outpatient"  # "outpatient", "inpatient", "ED", "procedure"
    estimated_duration: int = 30  # minutes
    special_needs: List[str] = []  # "medical_terminology", "pediatric", "mental_health"
    requested_at: Optional[str] = None
    status: InterpreterStatus = InterpreterStatus.REQUESTED


class InterpreterSession(BaseModel):
    """Active interpreter session tracking"""
    session_id: str
    request_id: str
    patient_id: str
    language: str
    interpreter_type: InterpreterType
    interpreter_id: Optional[str] = None
    interpreter_name: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    topics_covered: List[str] = []  # "consent", "discharge", "medication", etc.
    status: InterpreterStatus = InterpreterStatus.IN_PROGRESS


class InterpreterDocumentation(BaseModel):
    """Documentation of interpreter use for compliance"""
    patient_id: str
    encounter_id: Optional[str] = None
    language: str
    interpreter_type: InterpreterType
    interpreter_id: Optional[str] = None
    session_start: str
    session_end: str
    duration_minutes: int
    topics: List[str] = []
    patient_understanding_confirmed: bool = False
    notes: Optional[str] = None
    documented_by: Optional[str] = None
    documented_at: str


class TranslatedPhrase(BaseModel):
    """Pre-translated clinical phrase"""
    category: str  # "greeting", "pain", "consent", "discharge", etc.
    english: str
    translated: str
    phonetic: Optional[str] = None  # Pronunciation guide
    audio_url: Optional[str] = None
    context_notes: Optional[str] = None


# Billing/Claim Models (Feature #71)
class ClaimStatus(str, Enum):
    """Claim lifecycle status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class BillingDiagnosisCode(BaseModel):
    """ICD-10 diagnosis code with sequencing for billing"""
    code: str
    description: str
    sequence: int = 1
    is_principal: bool = False


class BillingProcedureCode(BaseModel):
    """CPT procedure code with modifiers for billing"""
    code: str
    description: str
    modifiers: List[str] = []
    units: int = 1


class BillingServiceLine(BaseModel):
    """Individual service/procedure line on claim"""
    line_number: int
    service_date: str
    procedure: BillingProcedureCode
    diagnosis_pointers: List[int] = [1]


class BillingClaim(BaseModel):
    """Complete billing claim model"""
    claim_id: Optional[str] = None
    status: ClaimStatus = ClaimStatus.DRAFT
    patient_id: str
    patient_name: Optional[str] = None
    note_id: Optional[str] = None
    service_date: str
    provider_name: Optional[str] = None
    provider_npi: Optional[str] = None
    diagnoses: List[BillingDiagnosisCode] = []
    service_lines: List[BillingServiceLine] = []
    total_charge: float = 0.0
    created_at: Optional[str] = None
    submitted_at: Optional[str] = None
    fhir_claim_id: Optional[str] = None


class ClaimCreateRequest(BaseModel):
    """Request to create a new billing claim"""
    patient_id: str
    note_id: Optional[str] = None
    service_date: str
    provider_name: Optional[str] = None
    provider_npi: Optional[str] = None
    icd10_codes: Optional[List[Dict]] = None
    cpt_codes: Optional[List[Dict]] = None


class ClaimUpdateRequest(BaseModel):
    """Request to update/edit claim codes before submission"""
    diagnoses: Optional[List[BillingDiagnosisCode]] = None
    service_lines: Optional[List[BillingServiceLine]] = None


class ClaimSubmitRequest(BaseModel):
    """Request to submit claim"""
    confirm: bool = False


# In-memory billing claims storage
billing_claims: dict = {}


# DNFB Models (Feature #72)
class DNFBReason(str, Enum):
    """Reason account is not final billed"""
    CODING_INCOMPLETE = "coding_incomplete"
    DOCUMENTATION_MISSING = "documentation_missing"
    CHARGES_PENDING = "charges_pending"
    PRIOR_AUTH_MISSING = "prior_auth_missing"
    PRIOR_AUTH_EXPIRED = "prior_auth_expired"
    PRIOR_AUTH_DENIED = "prior_auth_denied"
    INSURANCE_VERIFICATION = "insurance_verification"
    PHYSICIAN_QUERY = "physician_query"
    CLAIM_EDIT_REQUIRED = "claim_edit_required"
    OTHER = "other"


class PriorAuthStatus(str, Enum):
    """Prior authorization status"""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    NOT_OBTAINED = "not_obtained"


class PriorAuthInfo(BaseModel):
    """Prior authorization tracking"""
    auth_number: Optional[str] = None
    status: PriorAuthStatus = PriorAuthStatus.NOT_REQUIRED
    requested_date: Optional[str] = None
    approval_date: Optional[str] = None
    expiration_date: Optional[str] = None
    approved_units: Optional[int] = None
    used_units: int = 0
    payer_name: Optional[str] = None
    procedure_codes: List[str] = []
    denial_reason: Optional[str] = None


class DNFBAccount(BaseModel):
    """Discharged Not Final Billed account"""
    dnfb_id: Optional[str] = None
    patient_id: str
    patient_name: Optional[str] = None
    mrn: Optional[str] = None
    encounter_id: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: str
    discharge_disposition: Optional[str] = None  # home, SNF, expired, etc.
    attending_physician: Optional[str] = None
    service_type: Optional[str] = None  # inpatient, observation, outpatient
    principal_diagnosis: Optional[str] = None
    principal_diagnosis_desc: Optional[str] = None
    estimated_charges: float = 0.0
    reason: DNFBReason = DNFBReason.CODING_INCOMPLETE
    reason_detail: Optional[str] = None
    prior_auth: Optional[PriorAuthInfo] = None
    days_since_discharge: int = 0
    aging_bucket: str = "0-3"  # 0-3, 4-7, 8-14, 15-30, 31+
    assigned_coder: Optional[str] = None
    last_updated: Optional[str] = None
    notes: List[str] = []
    is_resolved: bool = False
    resolved_date: Optional[str] = None
    claim_id: Optional[str] = None  # Link to billing claim when created


class DNFBCreateRequest(BaseModel):
    """Request to add account to DNFB worklist"""
    patient_id: str
    patient_name: Optional[str] = None
    mrn: Optional[str] = None
    encounter_id: Optional[str] = None
    discharge_date: str
    reason: DNFBReason = DNFBReason.CODING_INCOMPLETE
    reason_detail: Optional[str] = None
    estimated_charges: float = 0.0
    service_type: str = "inpatient"
    principal_diagnosis: Optional[str] = None
    attending_physician: Optional[str] = None


class DNFBUpdateRequest(BaseModel):
    """Request to update DNFB account"""
    reason: Optional[DNFBReason] = None
    reason_detail: Optional[str] = None
    assigned_coder: Optional[str] = None
    notes: Optional[List[str]] = None
    prior_auth: Optional[PriorAuthInfo] = None
    is_resolved: Optional[bool] = None


class PriorAuthRequest(BaseModel):
    """Request to add/update prior auth info"""
    auth_number: Optional[str] = None
    status: PriorAuthStatus
    payer_name: Optional[str] = None
    procedure_codes: List[str] = []
    requested_date: Optional[str] = None
    approval_date: Optional[str] = None
    expiration_date: Optional[str] = None
    approved_units: Optional[int] = None
    denial_reason: Optional[str] = None


# In-memory DNFB storage
dnfb_accounts: dict = {}


# In-memory worklist storage (would be database in production)
_worklist_data: dict = {}


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


def extract_patient_photo(patient: dict) -> Optional[str]:
    """
    Extract patient photo from FHIR Patient resource.

    FHIR Patient.photo can contain:
    - Inline base64 data (contentType + data)
    - URL reference (url)

    Returns:
        Photo URL or base64 data URI, or None if no photo
    """
    photos = patient.get("photo", [])
    if not photos:
        return None

    photo = photos[0]  # Use first photo

    # Check for URL reference
    if photo.get("url"):
        return photo["url"]

    # Check for inline base64 data
    if photo.get("data") and photo.get("contentType"):
        content_type = photo["contentType"]
        data = photo["data"]
        return f"data:{content_type};base64,{data}"

    return None


def extract_vitals(bundle: dict) -> List[VitalSign]:
    """Extract vitals from FHIR Observation bundle"""
    vitals = []
    for entry in bundle.get("entry", []):  # Process all entries for trend analysis
        obs = entry.get("resource", {})
        name = obs.get("code", {}).get("text", "Unknown")
        value_qty = obs.get("valueQuantity", {})
        value = str(value_qty.get("value", "?"))
        unit = value_qty.get("unit", "")
        date = obs.get("effectiveDateTime", "")[:10] if obs.get("effectiveDateTime") else ""

        # Check for critical values
        is_critical, is_abnormal, interpretation = check_critical_vital(name, value)

        vitals.append(VitalSign(
            name=name,
            value=value,
            unit=unit,
            date=date,
            interpretation=interpretation,
            is_critical=is_critical,
            is_abnormal=is_abnormal
        ))

    # Calculate trends after extracting all vitals
    return calculate_vital_trends(vitals)


def calculate_vital_trends(vitals: List[VitalSign]) -> List[VitalSign]:
    """
    Group vitals by name and calculate trends.
    Returns most recent result for each vital type with trend indicators.
    """
    if not vitals:
        return vitals

    # Group by vital name
    grouped = {}
    for vital in vitals:
        if vital.name not in grouped:
            grouped[vital.name] = []
        grouped[vital.name].append(vital)

    # For each vital type, compare most recent to previous
    results = []
    for name, vital_list in grouped.items():
        # Sort by date descending (newest first)
        vital_list.sort(key=lambda x: x.date or "", reverse=True)

        current = vital_list[0]
        previous = vital_list[1] if len(vital_list) > 1 else None

        # Calculate trend using the same function as labs
        if previous:
            trend, delta = calculate_trend_direction(current.value, previous.value)
            current.previous_value = previous.value
            current.previous_date = previous.date
            current.trend = trend
            current.delta = delta
        else:
            current.trend = "new"

        results.append(current)

    # Sort by: critical first, then abnormal, then by name
    results.sort(key=lambda x: (
        0 if x.is_critical else 1,
        0 if x.is_abnormal else 1,
        x.name
    ))

    return results


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
    for entry in bundle.get("entry", []):  # Process all entries for trend analysis
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

    # Calculate trends after extracting all labs
    return calculate_lab_trends(labs)


def calculate_trend_direction(current: str, previous: str) -> tuple:
    """
    Calculate trend direction and delta between two lab values.

    Returns:
        (trend, delta) where trend is "rising"/"falling"/"stable"
    """
    try:
        # Handle commas in numbers (e.g., "1,234")
        curr_val = float(current.replace(",", ""))
        prev_val = float(previous.replace(",", ""))
    except (ValueError, AttributeError, TypeError):
        return ("stable", None)

    if prev_val == 0:
        return ("stable", None)

    delta = curr_val - prev_val
    percent_change = abs(delta / prev_val) * 100

    # Threshold: 5% change = significant
    if percent_change < 5:
        return ("stable", f"{delta:+.1f}")
    elif delta > 0:
        return ("rising", f"+{delta:.1f}")
    else:
        return ("falling", f"{delta:.1f}")


def calculate_lab_trends(labs: List[LabResult]) -> List[LabResult]:
    """
    Group labs by name and calculate trends.
    Returns most recent result for each test type with trend indicators.
    """
    if not labs:
        return labs

    # Group by test name
    grouped = {}
    for lab in labs:
        if lab.name not in grouped:
            grouped[lab.name] = []
        grouped[lab.name].append(lab)

    # For each test, compare most recent to previous
    results = []
    for name, lab_list in grouped.items():
        # Sort by date descending (newest first)
        lab_list.sort(key=lambda x: x.date or "", reverse=True)

        current = lab_list[0]
        previous = lab_list[1] if len(lab_list) > 1 else None

        # Calculate trend
        if previous:
            trend, delta = calculate_trend_direction(current.value, previous.value)
            current.previous_value = previous.value
            current.previous_date = previous.date
            current.trend = trend
            current.delta = delta
        else:
            current.trend = "new"

        results.append(current)

    # Sort by: critical first, then abnormal, then by name
    results.sort(key=lambda x: (
        0 if x.is_critical else 1,
        0 if x.is_abnormal else 1,
        x.name
    ))

    return results


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
async def get_patient(patient_id: str, request: Request):
    """Get patient summary by ID - optimized for AR glasses"""

    # Get request context for audit
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent", "")
    user_id = request.headers.get("X-User-Id")
    user_name = request.headers.get("X-Clinician-Name")

    # Fetch patient demographics
    patient_data = await fetch_fhir(f"Patient/{patient_id}")
    if not patient_data or patient_data.get("resourceType") == "OperationOutcome":
        raise HTTPException(status_code=404, detail="Patient not found")

    # Extract basic info
    name = extract_patient_name(patient_data)
    dob = patient_data.get("birthDate", "Unknown")
    gender = patient_data.get("gender", "unknown")
    photo_url = extract_patient_photo(patient_data)

    # Fetch vitals (50 for trend analysis)
    vitals_bundle = await fetch_fhir(f"Observation?patient={patient_id}&category=vital-signs&_count=50&_sort=-date")
    vitals = extract_vitals(vitals_bundle)

    # Fetch allergies
    allergy_bundle = await fetch_fhir(f"AllergyIntolerance?patient={patient_id}&_count=10")
    allergies = extract_allergies(allergy_bundle)

    # Fetch medications
    med_bundle = await fetch_fhir(f"MedicationRequest?patient={patient_id}&_count=10")
    medications = extract_medications(med_bundle)

    # Fetch lab results (50 for trend analysis)
    lab_bundle = await fetch_fhir(f"Observation?patient={patient_id}&category=laboratory&_count=50&_sort=-date")
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

        # HIPAA Audit: Log critical vital alerts
        for v in critical_vitals:
            audit_logger.log_safety_event(
                action=AuditAction.CRITICAL_ALERT,
                patient_id=patient_id,
                details=f"Critical {v.name}: {v.value} {v.unit}",
                severity="high",
                alert_type="vital",
                value=f"{v.value} {v.unit}"
            )

    # Filter critical and abnormal labs for safety alerts
    critical_labs = [lab for lab in labs if lab.is_critical]
    abnormal_labs = [lab for lab in labs if lab.is_abnormal]

    if critical_labs:
        print(f"🚨 CRITICAL LABS DETECTED: {len(critical_labs)}")
        for lab in critical_labs:
            print(f"   ‼️ {lab.name}: {lab.value} {lab.unit} ({lab.interpretation})")

        # HIPAA Audit: Log critical lab alerts
        for lab in critical_labs:
            audit_logger.log_safety_event(
                action=AuditAction.CRITICAL_ALERT,
                patient_id=patient_id,
                details=f"Critical {lab.name}: {lab.value} {lab.unit}",
                severity="high",
                alert_type="lab",
                value=f"{lab.value} {lab.unit}"
            )

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

        # HIPAA Audit: Log drug interactions (only high severity)
        high_severity = [i for i in medication_interactions if i.severity == "high"]
        for interaction in high_severity:
            audit_logger.log_safety_event(
                action=AuditAction.DRUG_INTERACTION,
                patient_id=patient_id,
                details=f"{interaction.drug1} + {interaction.drug2}: {interaction.effect}",
                severity=interaction.severity,
                alert_type="drug_interaction"
            )

    summary = PatientSummary(
        patient_id=patient_id,
        name=name,
        date_of_birth=dob,
        gender=gender,
        photo_url=photo_url,
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

    # Build details of what was accessed
    accessed_resources = []
    if vitals: accessed_resources.append("vitals")
    if allergies: accessed_resources.append("allergies")
    if medications: accessed_resources.append("medications")
    if labs: accessed_resources.append("labs")
    if conditions: accessed_resources.append("conditions")
    if procedures: accessed_resources.append("procedures")
    if immunizations: accessed_resources.append("immunizations")
    if care_plans: accessed_resources.append("care_plans")
    if clinical_notes: accessed_resources.append("notes")

    # HIPAA Audit: Log PHI access
    audit_logger.log_phi_access(
        action=AuditAction.VIEW_PATIENT,
        patient_id=patient_id,
        patient_name=name,
        endpoint=f"/api/v1/patient/{patient_id}",
        status="success",
        details=",".join(accessed_resources),
        user_id=user_id,
        user_name=user_name,
        ip_address=ip_address,
        user_agent=user_agent
    )

    return summary


@app.get("/api/v1/patient/{patient_id}/display")
async def get_patient_display(patient_id: str, request: Request):
    """Get AR-optimized display text for patient"""
    summary = await get_patient(patient_id, request)
    return {"patient_id": patient_id, "display": summary.display_text}


@app.get("/api/v1/patient/{patient_id}/vital-history")
async def get_vital_history(patient_id: str, request: Request, count: int = 100):
    """
    Get full vital sign history for a patient, grouped by vital type.
    Returns last N readings for each vital type with timestamps.
    """
    # Fetch vitals
    vitals_bundle = await fetch_fhir(f"Observation?patient={patient_id}&category=vital-signs&_count={count}&_sort=-date")

    # Extract all vitals (not just most recent)
    vitals_raw = []
    for entry in vitals_bundle.get("entry", []):
        obs = entry.get("resource", {})

        # Get vital name
        code = obs.get("code", {})
        name = code.get("text", "")
        if not name:
            for coding in code.get("coding", []):
                name = coding.get("display", "")
                if name:
                    break

        if not name:
            continue

        # Get value
        value = ""
        unit = ""
        if "valueQuantity" in obs:
            value = str(obs["valueQuantity"].get("value", ""))
            unit = obs["valueQuantity"].get("unit", "")
        elif "valueString" in obs:
            value = obs["valueString"]

        # Get date
        date = obs.get("effectiveDateTime", obs.get("issued", ""))

        # Get interpretation
        interpretation = ""
        for interp in obs.get("interpretation", []):
            for coding in interp.get("coding", []):
                interpretation = coding.get("display", coding.get("code", ""))
                if interpretation:
                    break

        if value:
            vitals_raw.append({
                "name": name,
                "value": value,
                "unit": unit,
                "date": date,
                "interpretation": interpretation
            })

    # Group by vital name
    grouped = {}
    for vital in vitals_raw:
        name = vital["name"]
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(vital)

    # Sort each group by date (newest first) and limit to 10 readings
    history = {}
    for name, readings in grouped.items():
        readings.sort(key=lambda x: x["date"] or "", reverse=True)
        history[name] = readings[:10]  # Last 10 readings per vital

    # HIPAA Audit: Log vital history access
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.VIEW_PATIENT,
        patient_id=patient_id,
        endpoint="/api/v1/patient/{patient_id}/vital-history",
        status="success",
        details=f"vital_types={len(history)}, total_readings={sum(len(v) for v in history.values())}",
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent", "")
    )

    return {
        "patient_id": patient_id,
        "vital_types": len(history),
        "history": history
    }


@app.get("/api/v1/patient/search", response_model=List[SearchResult])
async def search_patients(name: str, request: Request):
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

    # HIPAA Audit: Log patient search
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.SEARCH_PATIENT,
        patient_id="search",
        endpoint="/api/v1/patient/search",
        status="success",
        details=f"query={name}, results={len(results)}",
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent", "")
    )

    return results


@app.get("/api/v1/patient/mrn/{mrn}", response_model=PatientSummary)
async def get_patient_by_mrn(mrn: str, request: Request):
    """Get patient by MRN (wristband barcode scan)"""
    bundle = await fetch_fhir(f"Patient?identifier={mrn}&_count=1")

    entries = bundle.get("entry", [])
    if not entries:
        # Audit failed lookup
        ip_address = request.client.host if request.client else None
        audit_logger.log_phi_access(
            action=AuditAction.LOOKUP_MRN,
            patient_id="not_found",
            endpoint=f"/api/v1/patient/mrn/{mrn}",
            status="failure",
            details=f"MRN {mrn} not found",
            ip_address=ip_address
        )
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_id = entries[0].get("resource", {}).get("id")

    # Audit successful MRN lookup
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.LOOKUP_MRN,
        patient_id=patient_id,
        endpoint=f"/api/v1/patient/mrn/{mrn}",
        status="success",
        details=f"MRN {mrn} resolved to patient {patient_id}",
        ip_address=ip_address
    )

    return await get_patient(patient_id, request)


# ═══════════════════════════════════════════════════════════════════════════
# PATIENT WORKLIST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

def _get_today_key() -> str:
    """Get today's date as worklist key"""
    return datetime.now().strftime("%Y-%m-%d")

def _init_worklist_for_today():
    """Initialize today's worklist with sample/scheduled patients"""
    today = _get_today_key()
    if today not in _worklist_data:
        # In production, this would fetch from EHR Schedule/Appointment resources
        # For now, we'll create a sample worklist with the sandbox patient
        _worklist_data[today] = {
            "date": today,
            "provider": "Dr. Smith",
            "location": "Clinic A",
            "patients": [
                {
                    "patient_id": "12724066",
                    "name": "SMARTS SR., NANCYS II",
                    "date_of_birth": "1990-09-15",
                    "gender": "female",
                    "mrn": "MRN-12724066",
                    "room": None,
                    "appointment_time": "09:00",
                    "appointment_type": "Follow-up",
                    "chief_complaint": None,
                    "provider": "Dr. Smith",
                    "status": "scheduled",
                    "checked_in_at": None,
                    "encounter_started_at": None,
                    "has_critical_alerts": True,
                    "priority": 0
                },
                {
                    "patient_id": "12742400",
                    "name": "PETERS, TIMOTHY",
                    "date_of_birth": "1985-03-22",
                    "gender": "male",
                    "mrn": "MRN-12742400",
                    "room": None,
                    "appointment_time": "09:30",
                    "appointment_type": "New Patient",
                    "chief_complaint": "Chest pain",
                    "provider": "Dr. Smith",
                    "status": "scheduled",
                    "checked_in_at": None,
                    "encounter_started_at": None,
                    "has_critical_alerts": False,
                    "priority": 1
                },
                {
                    "patient_id": "12724067",
                    "name": "JOHNSON, MARIA",
                    "date_of_birth": "1978-07-10",
                    "gender": "female",
                    "mrn": "MRN-12724067",
                    "room": None,
                    "appointment_time": "10:00",
                    "appointment_type": "Follow-up",
                    "chief_complaint": "Diabetes management",
                    "provider": "Dr. Smith",
                    "status": "scheduled",
                    "checked_in_at": None,
                    "encounter_started_at": None,
                    "has_critical_alerts": False,
                    "priority": 0
                },
                {
                    "patient_id": "12724068",
                    "name": "WILLIAMS, ROBERT",
                    "date_of_birth": "1965-11-30",
                    "gender": "male",
                    "mrn": "MRN-12724068",
                    "room": None,
                    "appointment_time": "10:30",
                    "appointment_type": "Urgent",
                    "chief_complaint": "Shortness of breath",
                    "provider": "Dr. Smith",
                    "status": "scheduled",
                    "checked_in_at": None,
                    "encounter_started_at": None,
                    "has_critical_alerts": True,
                    "priority": 2
                },
                {
                    "patient_id": "12724069",
                    "name": "DAVIS, SARAH",
                    "date_of_birth": "1992-04-18",
                    "gender": "female",
                    "mrn": "MRN-12724069",
                    "room": None,
                    "appointment_time": "11:00",
                    "appointment_type": "Follow-up",
                    "chief_complaint": "Medication refill",
                    "provider": "Dr. Smith",
                    "status": "scheduled",
                    "checked_in_at": None,
                    "encounter_started_at": None,
                    "has_critical_alerts": False,
                    "priority": 0
                }
            ]
        }
    return _worklist_data[today]


@app.get("/api/v1/worklist", response_model=WorklistResponse)
async def get_worklist(request: Request, date: Optional[str] = None):
    """
    Get patient worklist for today (or specified date).
    Returns all scheduled patients with their status.
    """
    target_date = date or _get_today_key()

    # Initialize worklist if needed
    if target_date == _get_today_key():
        worklist = _init_worklist_for_today()
    else:
        worklist = _worklist_data.get(target_date, {
            "date": target_date,
            "provider": None,
            "location": None,
            "patients": []
        })

    patients = worklist.get("patients", [])

    # Calculate stats
    stats = {
        "total_scheduled": len(patients),
        "checked_in": len([p for p in patients if p.get("status") in ["checked_in", "in_room", "in_progress"]]),
        "in_progress": len([p for p in patients if p.get("status") == "in_progress"]),
        "completed": len([p for p in patients if p.get("status") == "completed"])
    }

    # Sort by priority (high first), then by appointment time
    sorted_patients = sorted(
        patients,
        key=lambda p: (-p.get("priority", 0), p.get("appointment_time", "99:99"))
    )

    # Audit the access
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.VIEW_WORKLIST,
        patient_id="worklist",
        endpoint="/api/v1/worklist",
        status="success",
        details=f"date={target_date}, count={len(patients)}",
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent", "")
    )

    return WorklistResponse(
        date=worklist.get("date", target_date),
        provider=worklist.get("provider"),
        location=worklist.get("location"),
        patients=[WorklistPatient(**p) for p in sorted_patients],
        **stats
    )


@app.post("/api/v1/worklist/check-in")
async def check_in_patient(req: CheckInRequest, request: Request):
    """
    Check in a patient - mark as arrived and optionally assign room.
    """
    worklist = _init_worklist_for_today()
    patients = worklist.get("patients", [])

    # Find patient
    patient = None
    for p in patients:
        if p.get("patient_id") == req.patient_id:
            patient = p
            break

    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {req.patient_id} not in today's worklist")

    # Update status
    patient["status"] = "checked_in"
    patient["checked_in_at"] = datetime.now().isoformat()
    if req.room:
        patient["room"] = req.room
    if req.chief_complaint:
        patient["chief_complaint"] = req.chief_complaint

    # Audit
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.CHECK_IN_PATIENT,
        patient_id=req.patient_id,
        patient_name=patient.get("name"),
        endpoint="/api/v1/worklist/check-in",
        status="success",
        details=f"room={req.room}, chief_complaint={req.chief_complaint}",
        ip_address=ip_address
    )

    return {
        "success": True,
        "message": f"Patient {patient['name']} checked in",
        "patient": patient
    }


@app.post("/api/v1/worklist/status")
async def update_worklist_status(req: UpdateWorklistStatusRequest, request: Request):
    """
    Update patient status in worklist.
    Valid statuses: scheduled, checked_in, in_room, in_progress, completed, no_show
    """
    valid_statuses = ["scheduled", "checked_in", "in_room", "in_progress", "completed", "no_show"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    worklist = _init_worklist_for_today()
    patients = worklist.get("patients", [])

    # Find patient
    patient = None
    for p in patients:
        if p.get("patient_id") == req.patient_id:
            patient = p
            break

    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {req.patient_id} not in today's worklist")

    old_status = patient["status"]
    patient["status"] = req.status

    # Track encounter start time
    if req.status == "in_progress" and not patient.get("encounter_started_at"):
        patient["encounter_started_at"] = datetime.now().isoformat()

    if req.room:
        patient["room"] = req.room

    # Audit
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.UPDATE_WORKLIST_STATUS,
        patient_id=req.patient_id,
        patient_name=patient.get("name"),
        endpoint="/api/v1/worklist/status",
        status="success",
        details=f"status: {old_status} -> {req.status}, room={req.room}",
        ip_address=ip_address
    )

    return {
        "success": True,
        "message": f"Patient {patient['name']} status updated to {req.status}",
        "patient": patient
    }


@app.get("/api/v1/worklist/next")
async def get_next_patient(request: Request):
    """
    Get the next patient to see (highest priority checked-in patient).
    """
    worklist = _init_worklist_for_today()
    patients = worklist.get("patients", [])

    # Find checked-in patients, sorted by priority then time
    ready_patients = [
        p for p in patients
        if p.get("status") in ["checked_in", "in_room"]
    ]

    if not ready_patients:
        return {"next_patient": None, "message": "No patients waiting"}

    # Sort by priority (highest first), then by check-in time
    ready_patients.sort(
        key=lambda p: (-p.get("priority", 0), p.get("checked_in_at", ""))
    )

    next_patient = ready_patients[0]

    return {
        "next_patient": next_patient,
        "waiting_count": len(ready_patients),
        "message": f"Next: {next_patient['name']} - {next_patient.get('chief_complaint', 'No chief complaint')}"
    }


@app.post("/api/v1/worklist/add")
async def add_to_worklist(patient: WorklistPatient, request: Request):
    """
    Add a walk-in or urgent patient to today's worklist.
    """
    worklist = _init_worklist_for_today()
    patients = worklist.get("patients", [])

    # Check if already in worklist
    for p in patients:
        if p.get("patient_id") == patient.patient_id:
            raise HTTPException(status_code=400, detail="Patient already in worklist")

    # Add to worklist
    patient_dict = patient.model_dump()
    patient_dict["appointment_time"] = datetime.now().strftime("%H:%M")
    patients.append(patient_dict)

    # Audit
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.ADD_TO_WORKLIST,
        patient_id=patient.patient_id,
        patient_name=patient.name,
        endpoint="/api/v1/worklist/add",
        status="success",
        details=f"Walk-in added, priority={patient.priority}",
        ip_address=ip_address
    )

    return {
        "success": True,
        "message": f"Patient {patient.name} added to worklist",
        "patient": patient_dict
    }


# ============ Clinical Notes API ============

async def generate_soap_with_claude(transcript: str, chief_complaint: str = None, use_rag: bool = True) -> dict:
    """
    Generate SOAP note using Claude API.

    Args:
        transcript: Clinical encounter transcript
        chief_complaint: Primary complaint
        use_rag: Whether to use RAG for citation-backed responses (Feature #88)

    Returns:
        SOAP note with ICD-10/CPT codes and optional citations
    """
    # Build RAG context if available and enabled
    rag_context = ""
    citations = []

    if use_rag and RAG_AVAILABLE and rag_engine.initialized:
        # Create search query from chief complaint and transcript
        search_query = f"{chief_complaint or ''} {transcript[:500]}"

        # Retrieve relevant guidelines
        augmented_prompt, sources = get_augmented_prompt(search_query, n_results=3)

        if sources:
            rag_context = """
CLINICAL REFERENCE GUIDELINES:
Use these evidence-based guidelines to inform your assessment and plan.
Cite sources using [1], [2], [3] format in the assessment and plan sections.

"""
            for source in sources:
                rag_context += f"[{source['index']}] {source['source_name']} ({source['publication_date']}): {source['title']}\n"
            rag_context += "\n"
            citations = sources

    async with httpx.AsyncClient(timeout=60.0) as client:
        prompt = f"""Generate a SOAP note with ICD-10 and CPT codes from this clinical encounter transcript.
{rag_context}
Chief Complaint: {chief_complaint or 'See transcript'}

Transcript:
{transcript}

Return a JSON object with these exact fields:
- subjective: Patient's reported symptoms and history
- objective: Observable findings, vitals, exam results
- assessment: Clinical assessment and diagnosis{' (cite guidelines using [1], [2], etc. if relevant)' if rag_context else ''}
- plan: Treatment plan and follow-up{' (cite guidelines using [1], [2], etc. for evidence-based recommendations)' if rag_context else ''}
- summary: 1-2 sentence summary
- icd10_codes: Array of objects with "code" and "description" for each suggested ICD-10 diagnosis code (max 5)
- cpt_codes: Array of objects with "code" and "description" for each suggested CPT procedure/service code (max 5)
- citations: Array of source references used (if any)

Example formats:
icd10_codes: [{{"code": "J06.9", "description": "Acute upper respiratory infection"}}]
cpt_codes: [{{"code": "99213", "description": "Office visit, established patient, low complexity"}}]
citations: [{{"index": 1, "source": "AHA/ACC", "title": "Chest Pain Guidelines", "relevance": "Informed workup recommendations"}}]

Return ONLY valid JSON, no markdown or explanation."""

        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1500,
                "messages": [{
                    "role": "user",
                    "content": prompt
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
            soap_note = json.loads(content)

            # Add RAG citations to the response (Feature #88)
            if citations:
                # Merge RAG citations with any Claude-generated citations
                rag_citations = [
                    {
                        "index": c["index"],
                        "source": c["source_name"],
                        "title": c["title"],
                        "publication_date": c["publication_date"],
                        "relevance_score": round(c["relevance_score"], 3)
                    }
                    for c in citations
                ]
                # Append to existing citations or set new
                if "citations" not in soap_note or not soap_note["citations"]:
                    soap_note["citations"] = rag_citations
                else:
                    # Merge without duplicates
                    existing_sources = {c.get("source", "") for c in soap_note["citations"]}
                    for rag_cit in rag_citations:
                        if rag_cit["source"] not in existing_sources:
                            soap_note["citations"].append(rag_cit)
                soap_note["rag_enhanced"] = True
            else:
                soap_note["rag_enhanced"] = False

            return soap_note
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


# ============ Differential Diagnosis API ============

async def generate_ddx_with_claude(request: DdxRequest) -> DdxResponse:
    """Generate differential diagnosis using Claude API"""
    # Build clinical prompt
    clinical_data = f"""
Chief Complaint: {request.chief_complaint}
Symptoms: {', '.join(request.symptoms) if request.symptoms else 'Not specified'}
Age: {request.age if request.age else 'Not specified'}
Gender: {request.gender if request.gender else 'Not specified'}
Vitals: {request.vitals if request.vitals else 'Not recorded'}
Medical History: {', '.join(request.medical_history) if request.medical_history else 'Not specified'}
Current Medications: {', '.join(request.medications) if request.medications else 'None'}
Allergies: {', '.join(request.allergies) if request.allergies else 'NKDA'}
"""

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
                "max_tokens": 2048,
                "messages": [{
                    "role": "user",
                    "content": f"""You are a clinical decision support system. Generate a differential diagnosis list based on the following patient presentation.

{clinical_data}

Return a JSON object with these exact fields:
- differentials: Array of 5 diagnoses, each with:
  - rank: 1-5 (1 = most likely)
  - diagnosis: Name of condition
  - icd10_code: ICD-10-CM code
  - likelihood: "high", "moderate", or "low"
  - supporting_findings: Array of findings that support this diagnosis
  - red_flags: Array of warning signs to watch for
  - next_steps: Array of recommended tests/actions
- clinical_reasoning: 2-3 sentence explanation of diagnostic thinking
- urgent_considerations: Array of conditions that should be urgently ruled out (if any)

Example format:
{{
  "differentials": [
    {{
      "rank": 1,
      "diagnosis": "Acute Bronchitis",
      "icd10_code": "J20.9",
      "likelihood": "high",
      "supporting_findings": ["cough", "low-grade fever", "productive sputum"],
      "red_flags": ["dyspnea", "high fever >39C", "hemoptysis"],
      "next_steps": ["chest x-ray if symptoms >3 weeks", "supportive care"]
    }}
  ],
  "clinical_reasoning": "The combination of cough with productive sputum and low-grade fever in an otherwise healthy patient suggests...",
  "urgent_considerations": ["Pneumonia should be ruled out if hypoxia present"]
}}

Return ONLY valid JSON, no markdown or explanation."""
                }]
            }
        )

        if response.status_code == 200:
            result = response.json()
            content = result["content"][0]["text"]
            # Clean up response if needed
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```json?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)

            ddx_data = json.loads(content)

            # Build response
            differentials = [
                DifferentialDiagnosis(
                    rank=d["rank"],
                    diagnosis=d["diagnosis"],
                    icd10_code=d["icd10_code"],
                    likelihood=d["likelihood"],
                    supporting_findings=d.get("supporting_findings", []),
                    red_flags=d.get("red_flags", []),
                    next_steps=d.get("next_steps", [])
                )
                for d in ddx_data.get("differentials", [])
            ]

            return DdxResponse(
                differentials=differentials,
                clinical_reasoning=ddx_data.get("clinical_reasoning", ""),
                urgent_considerations=ddx_data.get("urgent_considerations", []),
                timestamp=datetime.now().isoformat()
            )
        else:
            raise Exception(f"Claude API error: {response.status_code}")


def generate_rule_based_ddx(request: DdxRequest) -> DdxResponse:
    """Generate differential diagnosis using rule-based matching (fallback when Claude unavailable)"""

    # Common symptom-to-diagnosis mappings with ICD-10 codes
    symptom_patterns = {
        # Respiratory
        ("cough", "fever"): [
            {"diagnosis": "Acute Bronchitis", "icd10": "J20.9", "likelihood": "high"},
            {"diagnosis": "Pneumonia", "icd10": "J18.9", "likelihood": "moderate"},
            {"diagnosis": "Upper Respiratory Infection", "icd10": "J06.9", "likelihood": "moderate"},
        ],
        ("cough", "shortness of breath"): [
            {"diagnosis": "Pneumonia", "icd10": "J18.9", "likelihood": "high"},
            {"diagnosis": "COPD Exacerbation", "icd10": "J44.1", "likelihood": "moderate"},
            {"diagnosis": "Asthma", "icd10": "J45.909", "likelihood": "moderate"},
        ],
        ("sore throat", "fever"): [
            {"diagnosis": "Pharyngitis", "icd10": "J02.9", "likelihood": "high"},
            {"diagnosis": "Strep Pharyngitis", "icd10": "J02.0", "likelihood": "moderate"},
            {"diagnosis": "Infectious Mononucleosis", "icd10": "B27.90", "likelihood": "low"},
        ],
        # Cardiovascular
        ("chest pain",): [
            {"diagnosis": "Chest Pain, Unspecified", "icd10": "R07.9", "likelihood": "high"},
            {"diagnosis": "Acute Coronary Syndrome", "icd10": "I24.9", "likelihood": "moderate"},
            {"diagnosis": "Costochondritis", "icd10": "M94.0", "likelihood": "moderate"},
        ],
        ("chest pain", "shortness of breath"): [
            {"diagnosis": "Acute Coronary Syndrome", "icd10": "I24.9", "likelihood": "high"},
            {"diagnosis": "Pulmonary Embolism", "icd10": "I26.99", "likelihood": "moderate"},
            {"diagnosis": "Anxiety Disorder", "icd10": "F41.9", "likelihood": "low"},
        ],
        ("palpitations",): [
            {"diagnosis": "Palpitations", "icd10": "R00.2", "likelihood": "high"},
            {"diagnosis": "Atrial Fibrillation", "icd10": "I48.91", "likelihood": "moderate"},
            {"diagnosis": "Anxiety Disorder", "icd10": "F41.9", "likelihood": "moderate"},
        ],
        # Gastrointestinal
        ("abdominal pain", "nausea"): [
            {"diagnosis": "Gastroenteritis", "icd10": "K52.9", "likelihood": "high"},
            {"diagnosis": "Appendicitis", "icd10": "K35.80", "likelihood": "moderate"},
            {"diagnosis": "Cholecystitis", "icd10": "K81.9", "likelihood": "low"},
        ],
        ("abdominal pain", "diarrhea"): [
            {"diagnosis": "Gastroenteritis", "icd10": "K52.9", "likelihood": "high"},
            {"diagnosis": "Inflammatory Bowel Disease", "icd10": "K50.90", "likelihood": "moderate"},
            {"diagnosis": "Irritable Bowel Syndrome", "icd10": "K58.9", "likelihood": "moderate"},
        ],
        # Neurological
        ("headache",): [
            {"diagnosis": "Tension Headache", "icd10": "G44.209", "likelihood": "high"},
            {"diagnosis": "Migraine", "icd10": "G43.909", "likelihood": "moderate"},
            {"diagnosis": "Headache, Unspecified", "icd10": "R51.9", "likelihood": "moderate"},
        ],
        ("headache", "fever"): [
            {"diagnosis": "Viral Syndrome", "icd10": "B34.9", "likelihood": "high"},
            {"diagnosis": "Sinusitis", "icd10": "J32.9", "likelihood": "moderate"},
            {"diagnosis": "Meningitis", "icd10": "G03.9", "likelihood": "low"},
        ],
        ("dizziness",): [
            {"diagnosis": "Vertigo", "icd10": "R42", "likelihood": "high"},
            {"diagnosis": "Benign Positional Vertigo", "icd10": "H81.10", "likelihood": "moderate"},
            {"diagnosis": "Orthostatic Hypotension", "icd10": "I95.1", "likelihood": "moderate"},
        ],
        # Musculoskeletal
        ("back pain",): [
            {"diagnosis": "Low Back Pain", "icd10": "M54.5", "likelihood": "high"},
            {"diagnosis": "Lumbar Strain", "icd10": "S39.012A", "likelihood": "moderate"},
            {"diagnosis": "Sciatica", "icd10": "M54.30", "likelihood": "moderate"},
        ],
        ("joint pain",): [
            {"diagnosis": "Joint Pain", "icd10": "M25.50", "likelihood": "high"},
            {"diagnosis": "Osteoarthritis", "icd10": "M19.90", "likelihood": "moderate"},
            {"diagnosis": "Rheumatoid Arthritis", "icd10": "M06.9", "likelihood": "low"},
        ],
        # General
        ("fatigue",): [
            {"diagnosis": "Fatigue", "icd10": "R53.83", "likelihood": "high"},
            {"diagnosis": "Anemia", "icd10": "D64.9", "likelihood": "moderate"},
            {"diagnosis": "Hypothyroidism", "icd10": "E03.9", "likelihood": "moderate"},
        ],
        ("fever",): [
            {"diagnosis": "Fever, Unspecified", "icd10": "R50.9", "likelihood": "high"},
            {"diagnosis": "Viral Infection", "icd10": "B34.9", "likelihood": "moderate"},
            {"diagnosis": "Urinary Tract Infection", "icd10": "N39.0", "likelihood": "moderate"},
        ],
    }

    # Combine symptoms from request
    all_symptoms = [s.lower() for s in request.symptoms]
    if request.chief_complaint:
        all_symptoms.extend(request.chief_complaint.lower().split())

    # Find matching patterns
    matched_diagnoses = []
    for pattern, diagnoses in symptom_patterns.items():
        if all(p in ' '.join(all_symptoms) for p in pattern):
            matched_diagnoses.extend(diagnoses)

    # Deduplicate and limit to 5
    seen = set()
    unique_diagnoses = []
    for d in matched_diagnoses:
        if d["diagnosis"] not in seen:
            seen.add(d["diagnosis"])
            unique_diagnoses.append(d)

    # If no matches, use generic
    if not unique_diagnoses:
        unique_diagnoses = [
            {"diagnosis": "Symptoms, Unspecified", "icd10": "R69", "likelihood": "moderate"},
        ]

    # Build differential list
    differentials = []
    for i, d in enumerate(unique_diagnoses[:5], 1):
        differentials.append(DifferentialDiagnosis(
            rank=i,
            diagnosis=d["diagnosis"],
            icd10_code=d["icd10"],
            likelihood=d["likelihood"],
            supporting_findings=[s for s in all_symptoms[:3] if s],
            red_flags=[],
            next_steps=["Further evaluation recommended"]
        ))

    return DdxResponse(
        differentials=differentials,
        clinical_reasoning="Rule-based differential diagnosis generated from symptom patterns. AI analysis unavailable.",
        urgent_considerations=[],
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/v1/ddx/generate")
async def generate_differential_diagnosis(request: DdxRequest, req: Request):
    """
    Generate AI-powered differential diagnosis from clinical findings.

    Takes symptoms, chief complaint, vitals, and patient demographics to generate
    a ranked list of possible diagnoses with ICD-10 codes, likelihood levels,
    and supporting/refuting findings.

    Returns top 5 differential diagnoses with clinical reasoning.

    Safety: For clinical decision support only - not a diagnosis.
    """
    # Validate input
    if not request.chief_complaint or not request.chief_complaint.strip():
        raise HTTPException(status_code=400, detail="Chief complaint is required")

    # Audit log (no PHI - only symptoms for clinical improvement)
    ip_address = req.client.host if req.client else None
    audit_logger.log_note_operation(
        action=AuditAction.GENERATE_DDX,
        note_type="DDX",
        status="processing",
        details=f"Chief complaint: {request.chief_complaint[:50]}",
        ip_address=ip_address
    )

    try:
        # Try Claude-powered DDx first
        if CLAUDE_API_KEY:
            ddx_response = await generate_ddx_with_claude(request)
        else:
            # Fallback to rule-based
            ddx_response = generate_rule_based_ddx(request)

        # Audit success
        audit_logger.log_note_operation(
            action=AuditAction.GENERATE_DDX,
            note_type="DDX",
            status="success",
            details=f"Generated {len(ddx_response.differentials)} differentials",
            ip_address=ip_address
        )

        return ddx_response

    except Exception as e:
        # Try fallback on error
        try:
            ddx_response = generate_rule_based_ddx(request)
            audit_logger.log_note_operation(
                action=AuditAction.GENERATE_DDX,
                note_type="DDX",
                status="fallback",
                details=f"Claude failed, used rule-based: {str(e)[:50]}",
                ip_address=ip_address
            )
            return ddx_response
        except Exception as fallback_error:
            audit_logger.log_note_operation(
                action=AuditAction.GENERATE_DDX,
                note_type="DDX",
                status="failure",
                details=str(fallback_error)[:100],
                ip_address=ip_address
            )
            raise HTTPException(status_code=500, detail=f"DDx generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# AI CLINICAL CO-PILOT (Feature #78)
# ═══════════════════════════════════════════════════════════════════════════════

COPILOT_SYSTEM_PROMPT = """You are a clinical co-pilot AI for a physician using AR smart glasses during patient encounters.
Your responses will be spoken via text-to-speech, so keep them BRIEF and CLEAR.

RESPONSE FORMAT:
- Maximum 3 bullet points
- Each bullet: 10-15 words maximum
- Lead with most actionable info
- End with ONE optional follow-up question

You help with:
1. Clinical reasoning - differential diagnosis discussion
2. Next steps - what tests, exams, or referrals to consider
3. Drug info - dosing, interactions, contraindications
4. Guidelines - evidence-based recommendations
5. Calculations - clinical scores and formulas

CRITICAL RULES:
- This is CLINICAL DECISION SUPPORT, not a diagnosis
- Always note when physician judgment is needed
- Flag urgent/emergent concerns prominently
- Be concise - physician is mid-encounter

Current patient context:
{patient_context}
"""


async def generate_copilot_response(request: CopilotRequest) -> CopilotResponse:
    """
    Generate clinical co-pilot response using Claude.
    Maintains conversation context and provides actionable suggestions.
    """
    if not CLAUDE_API_KEY:
        # Fallback response when no API key
        return CopilotResponse(
            response="Clinical co-pilot requires Claude API configuration. Please check CLAUDE_API_KEY.",
            suggestions=[],
            actions=[],
            references=[],
            timestamp=datetime.now().isoformat()
        )

    # Build patient context summary
    patient_summary = "No patient currently loaded."
    if request.patient_context:
        ctx = request.patient_context
        parts = []
        if ctx.get("name"):
            parts.append(f"Patient: {ctx.get('name')}")
        if ctx.get("age"):
            parts.append(f"Age: {ctx.get('age')}")
        if ctx.get("gender"):
            parts.append(f"Gender: {ctx.get('gender')}")
        if ctx.get("chief_complaint"):
            parts.append(f"CC: {ctx.get('chief_complaint')}")
        if ctx.get("conditions"):
            conditions = ctx.get("conditions", [])
            if conditions:
                parts.append(f"Conditions: {', '.join(conditions[:5])}")
        if ctx.get("medications"):
            meds = ctx.get("medications", [])
            if meds:
                parts.append(f"Meds: {', '.join(meds[:5])}")
        if ctx.get("allergies"):
            allergies = ctx.get("allergies", [])
            if allergies:
                parts.append(f"Allergies: {', '.join(allergies[:3])}")
        patient_summary = "; ".join(parts) if parts else "No patient details available."

    # Build conversation messages
    messages = []

    # Add conversation history
    for msg in request.conversation_history[-6:]:  # Keep last 6 messages for context
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": request.message
    })

    # Call Claude
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",  # Fast, cost-effective
                    "max_tokens": 500,
                    "system": COPILOT_SYSTEM_PROMPT.format(patient_context=patient_summary),
                    "messages": messages
                }
            )

            if response.status_code != 200:
                error_text = response.text
                return CopilotResponse(
                    response=f"Co-pilot temporarily unavailable. Please try again.",
                    suggestions=["Try rephrasing your question"],
                    actions=[],
                    references=[],
                    timestamp=datetime.now().isoformat()
                )

            result = response.json()
            response_text = result.get("content", [{}])[0].get("text", "No response generated.")

            # Parse for actionable suggestions
            actions = []
            suggestions = []

            # Detect common actionable patterns
            response_lower = response_text.lower()

            # Lab orders
            if "troponin" in response_lower or "ekg" in response_lower:
                actions.append(CopilotAction(
                    action_type="order",
                    label="Order chest pain workup",
                    command="order chest pain workup"
                ))
            if "cbc" in response_lower:
                actions.append(CopilotAction(
                    action_type="order",
                    label="Order CBC",
                    command="order CBC"
                ))
            if "d-dimer" in response_lower:
                actions.append(CopilotAction(
                    action_type="order",
                    label="Order D-dimer",
                    command="order D-dimer"
                ))

            # Calculations
            if "wells" in response_lower:
                actions.append(CopilotAction(
                    action_type="calculate",
                    label="Calculate Wells score",
                    command="calculate Wells"
                ))
            if "chads" in response_lower:
                actions.append(CopilotAction(
                    action_type="calculate",
                    label="Calculate CHADS-VASc",
                    command="calculate CHADS-VASc"
                ))

            # Add follow-up suggestions
            if "?" in response_text:
                # Response already has a question, no need for extra suggestions
                pass
            else:
                suggestions.append("Tell me more")
                suggestions.append("What else should I consider?")

            # Extract references (ICD-10 codes, guidelines)
            references = []
            import re
            icd_matches = re.findall(r'[A-Z]\d{2}(?:\.\d{1,2})?', response_text)
            references.extend(icd_matches[:3])

            return CopilotResponse(
                response=response_text,
                suggestions=suggestions[:2],
                actions=actions[:3],
                references=references,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            return CopilotResponse(
                response=f"Co-pilot error: {str(e)[:50]}. Try again.",
                suggestions=["Try rephrasing your question"],
                actions=[],
                references=[],
                timestamp=datetime.now().isoformat()
            )


@app.post("/api/v1/copilot/chat")
async def copilot_chat(request: CopilotRequest, req: Request):
    """
    AI Clinical Co-pilot chat endpoint (Feature #78).

    Provides conversational clinical decision support with:
    - Context-aware responses using patient data
    - Conversation history for follow-up questions
    - Actionable suggestions (orders, calculators)
    - TTS-optimized brief responses

    Example:
        POST /api/v1/copilot/chat
        {
            "message": "What workup for chest pain with dyspnea?",
            "patient_context": {"age": 55, "gender": "male"},
            "conversation_history": []
        }
    """
    # Validate input
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    # Audit log
    ip_address = req.client.host if req.client else None
    audit_logger._log_event(
        event_type="AI",
        action="COPILOT_CHAT",
        status="processing",
        details={"message_length": len(request.message), "has_context": bool(request.patient_context)}
    )

    try:
        response = await generate_copilot_response(request)

        # Audit success
        audit_logger._log_event(
            event_type="AI",
            action="COPILOT_CHAT",
            status="success",
            details={"response_length": len(response.response), "actions_count": len(response.actions)}
        )

        return response

    except Exception as e:
        audit_logger._log_event(
            event_type="AI",
            action="COPILOT_CHAT",
            status="failure",
            details={"error": str(e)[:100]}
        )
        raise HTTPException(status_code=500, detail=f"Co-pilot error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# RAG (RETRIEVAL-AUGMENTED GENERATION) ENDPOINTS (Feature #88)
# Reduces hallucination by grounding responses in medical sources
# ═══════════════════════════════════════════════════════════════════════════════

class RAGQueryRequest(BaseModel):
    """Request for RAG query"""
    query: str
    n_results: int = 5
    specialty: Optional[str] = None
    include_sources: bool = True


class RAGQueryResponse(BaseModel):
    """Response from RAG query"""
    query: str
    augmented_prompt: str
    sources: List[Dict]
    retrieval_count: int


class RAGAddDocumentRequest(BaseModel):
    """Request to add a document to the knowledge base"""
    title: str
    content: str
    source_type: str = "custom"
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    specialty: Optional[str] = None
    keywords: Optional[List[str]] = None


class RAGStatsResponse(BaseModel):
    """RAG system statistics"""
    available: bool
    initialized: bool
    document_count: int
    embedding_model: str
    built_in_guidelines: int


@app.get("/api/v1/rag/status")
async def rag_status():
    """
    Get RAG system status and statistics.

    Returns:
        RAG system availability and document count
    """
    if not RAG_AVAILABLE:
        return RAGStatsResponse(
            available=False,
            initialized=False,
            document_count=0,
            embedding_model="none",
            built_in_guidelines=0
        )

    stats = rag_engine.get_statistics()
    return RAGStatsResponse(
        available=True,
        initialized=stats.get("initialized", False),
        document_count=stats.get("document_count", 0),
        embedding_model=stats.get("embedding_model", "none"),
        built_in_guidelines=12  # Number of built-in guidelines
    )


@app.post("/api/v1/rag/initialize")
async def initialize_rag_endpoint():
    """
    Initialize the RAG system.

    This creates the vector database and ingests built-in clinical guidelines.
    Should be called once on startup or when needed.

    Returns:
        Initialization status
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG dependencies not installed. Run: pip install chromadb sentence-transformers")

    success = initialize_rag()

    audit_logger._log_event(
        event_type="RAG",
        action="INITIALIZE",
        status="success" if success else "failure"
    )

    if success:
        stats = rag_engine.get_statistics()
        return {
            "status": "initialized",
            "document_count": stats.get("document_count", 0),
            "message": "RAG system initialized with clinical guidelines"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to initialize RAG system")


@app.post("/api/v1/rag/query")
async def rag_query(request: RAGQueryRequest):
    """
    Query the medical knowledge base and get augmented context.

    This retrieves relevant documents and generates an augmented prompt
    that can be used with Claude for grounded, cited responses.

    Example:
        POST /api/v1/rag/query
        {
            "query": "Management of atrial fibrillation",
            "n_results": 3,
            "specialty": "cardiology"
        }

    Returns:
        Augmented prompt with retrieved sources
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    if not rag_engine.initialized:
        # Try to initialize
        if not initialize_rag():
            raise HTTPException(status_code=503, detail="RAG system not initialized. Call /api/v1/rag/initialize first")

    # Get augmented prompt with sources
    augmented_prompt, sources = get_augmented_prompt(request.query, request.n_results)

    # Audit log
    audit_logger._log_event(
        event_type="RAG",
        action="QUERY",
        status="success",
        details={"query_length": len(request.query), "results_returned": len(sources)}
    )

    return RAGQueryResponse(
        query=request.query,
        augmented_prompt=augmented_prompt,
        sources=sources,
        retrieval_count=len(sources)
    )


@app.post("/api/v1/rag/retrieve")
async def rag_retrieve(request: RAGQueryRequest):
    """
    Retrieve relevant documents without generating augmented prompt.

    Useful for exploring what sources would be used for a query.

    Returns:
        List of relevant documents with scores
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    if not rag_engine.initialized:
        if not initialize_rag():
            raise HTTPException(status_code=503, detail="RAG system not initialized")

    contexts = retrieve_context(request.query, request.n_results, request.specialty)

    results = []
    for ctx in contexts:
        results.append({
            "title": ctx.document.title,
            "source_type": ctx.document.source_type.value,
            "source_name": ctx.document.source_name,
            "source_url": ctx.document.source_url,
            "publication_date": ctx.document.publication_date,
            "specialty": ctx.document.specialty,
            "relevance_score": round(ctx.relevance_score, 3),
            "content_preview": ctx.matched_chunk[:300] + "..." if len(ctx.matched_chunk) > 300 else ctx.matched_chunk
        })

    return {
        "query": request.query,
        "results": results,
        "total_retrieved": len(results)
    }


@app.post("/api/v1/rag/add-document")
async def rag_add_document(request: RAGAddDocumentRequest):
    """
    Add a custom document to the medical knowledge base.

    Example:
        POST /api/v1/rag/add-document
        {
            "title": "Hospital Antibiotic Stewardship Protocol",
            "content": "Our hospital guidelines for antibiotic use...",
            "source_type": "custom",
            "source_name": "MGH Internal Guidelines",
            "specialty": "infectious_disease"
        }

    Returns:
        Success status
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    if not rag_engine.initialized:
        if not initialize_rag():
            raise HTTPException(status_code=503, detail="RAG system not initialized")

    success = add_custom_document(
        title=request.title,
        content=request.content,
        source_type=request.source_type,
        source_name=request.source_name,
        source_url=request.source_url,
        specialty=request.specialty,
        keywords=request.keywords
    )

    audit_logger._log_event(
        event_type="RAG",
        action="ADD_DOCUMENT",
        status="success" if success else "failure",
        details={"title": request.title[:50]}
    )

    if success:
        return {
            "status": "added",
            "title": request.title,
            "message": "Document added to knowledge base"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to add document")


@app.get("/api/v1/rag/guidelines")
async def rag_list_guidelines():
    """
    List built-in clinical guidelines in the knowledge base.

    Returns:
        List of guideline titles and sources
    """
    # Import the built-in guidelines list
    from rag import BUILT_IN_GUIDELINES

    guidelines = []
    for g in BUILT_IN_GUIDELINES:
        guidelines.append({
            "id": g["id"],
            "title": g["title"],
            "source_name": g.get("source_name", ""),
            "source_type": g["source_type"],
            "publication_date": g.get("publication_date", ""),
            "specialty": g.get("specialty", ""),
            "keywords": g.get("keywords", [])
        })

    return {
        "total": len(guidelines),
        "guidelines": guidelines
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RAG KNOWLEDGE MANAGEMENT ENDPOINTS (Feature #89)
# ═══════════════════════════════════════════════════════════════════════════════

# RSS feed URLs for medical guideline updates
MEDICAL_RSS_FEEDS = {
    "pubmed_cardiology": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1234567890/?limit=10&utm_campaign=pubmed-2&fc=20231201000000",
    "aha_guidelines": "https://www.ahajournals.org/action/showFeed?type=etoc&feed=rss&jc=circ",
    "cdc_mmwr": "https://www.cdc.gov/mmwr/rss/mmwr_all.xml",
    "nejm_current": "https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss",
    "jama_latest": "https://jamanetwork.com/rss/site_3/67.xml"
}


class FeedbackRequest(BaseModel):
    document_id: str
    query: str
    rating: str  # very_helpful, helpful, neutral, not_helpful, incorrect
    comment: Optional[str] = None
    clinician_specialty: Optional[str] = None


class GuidelineVersionRequest(BaseModel):
    guideline_id: str
    version_number: str
    publication_date: str
    content: str
    title: str
    source_name: str
    supersedes_id: Optional[str] = None
    change_summary: Optional[str] = None
    specialty: Optional[str] = None
    keywords: Optional[List[str]] = None


class PubMedIngestRequest(BaseModel):
    query: str
    max_articles: int = 10
    specialty: Optional[str] = None


class CollectionRequest(BaseModel):
    specialty: str
    description: str
    document_ids: Optional[List[str]] = None
    curator: Optional[str] = None


class ConflictResolutionRequest(BaseModel):
    resolution_notes: str


@app.get("/api/v1/knowledge/analytics")
async def knowledge_analytics():
    """
    Get analytics about knowledge base usage.
    Feature #89 - RAG Knowledge Management.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import get_knowledge_analytics
    return get_knowledge_analytics()


@app.post("/api/v1/knowledge/feedback")
async def submit_citation_feedback(request: FeedbackRequest):
    """
    Submit clinician feedback on a citation's helpfulness.
    Feature #89 - Improves retrieval quality over time.

    Ratings: very_helpful, helpful, neutral, not_helpful, incorrect
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import record_citation_feedback

    valid_ratings = ["very_helpful", "helpful", "neutral", "not_helpful", "incorrect"]
    if request.rating not in valid_ratings:
        raise HTTPException(status_code=400, detail=f"Invalid rating. Must be one of: {valid_ratings}")

    feedback_id = record_citation_feedback(
        document_id=request.document_id,
        query=request.query,
        rating=request.rating,
        comment=request.comment,
        clinician_specialty=request.clinician_specialty
    )

    # HIPAA audit log
    log_phi_access(
        action="CITATION_FEEDBACK",
        patient_id="N/A",
        details=f"Feedback submitted for document {request.document_id}: {request.rating}"
    )

    return {"feedback_id": feedback_id, "status": "recorded"}


@app.get("/api/v1/knowledge/feedback/{document_id}")
async def get_document_feedback(document_id: str):
    """
    Get feedback summary for a specific document.
    Feature #89 - Quality scoring for guidelines.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager
    return knowledge_manager.get_document_feedback_summary(document_id)


@app.get("/api/v1/knowledge/low-quality")
async def get_low_quality_documents(threshold: float = 0.4):
    """
    Get documents with low quality scores that may need review.
    Feature #89 - Continuous improvement.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager
    return {"documents": knowledge_manager.get_low_quality_documents(threshold)}


@app.post("/api/v1/knowledge/version")
async def add_new_guideline_version(request: GuidelineVersionRequest):
    """
    Add a new version of a clinical guideline.
    Automatically supersedes the previous version.
    Feature #89 - Guideline versioning.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import add_guideline_version

    success, version_id = add_guideline_version(
        guideline_id=request.guideline_id,
        version_number=request.version_number,
        publication_date=request.publication_date,
        content=request.content,
        title=request.title,
        source_name=request.source_name,
        supersedes_id=request.supersedes_id,
        change_summary=request.change_summary,
        specialty=request.specialty,
        keywords=request.keywords
    )

    if success:
        log_phi_access(
            action="GUIDELINE_VERSION_ADDED",
            patient_id="N/A",
            details=f"New guideline version: {version_id}"
        )
        return {"version_id": version_id, "status": "added"}
    else:
        raise HTTPException(status_code=500, detail="Failed to add guideline version")


@app.get("/api/v1/knowledge/versions/{guideline_id}")
async def get_guideline_versions(guideline_id: str):
    """
    Get version history for a guideline.
    Feature #89 - Guideline versioning.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager
    from dataclasses import asdict

    versions = knowledge_manager.get_version_history(guideline_id)
    return {
        "guideline_id": guideline_id,
        "versions": [asdict(v) for v in versions]
    }


@app.post("/api/v1/knowledge/pubmed/ingest")
async def ingest_from_pubmed(request: PubMedIngestRequest):
    """
    Search PubMed and ingest relevant articles.
    Feature #89 - Automated knowledge ingestion.

    Uses NCBI E-utilities API (free, no API key for <3 req/sec).
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import ingest_from_pubmed as do_ingest

    count, pmids = await do_ingest(
        query=request.query,
        max_articles=request.max_articles,
        specialty=request.specialty
    )

    log_phi_access(
        action="PUBMED_INGEST",
        patient_id="N/A",
        details=f"Ingested {count} articles for query: {request.query}"
    )

    return {
        "articles_ingested": count,
        "pmids": pmids,
        "query": request.query
    }


@app.post("/api/v1/knowledge/pubmed/search")
async def search_pubmed(query: str, max_results: int = 10):
    """
    Search PubMed without ingesting (preview mode).
    Feature #89 - PubMed integration.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager

    articles = await knowledge_manager.search_pubmed(query, max_results)
    return {
        "query": query,
        "results": [
            {
                "pmid": a.pmid,
                "title": a.title,
                "journal": a.journal,
                "abstract_preview": a.abstract[:200] + "..." if len(a.abstract) > 200 else a.abstract
            }
            for a in articles
        ]
    }


@app.post("/api/v1/knowledge/collections")
async def create_specialty_collection(request: CollectionRequest):
    """
    Create a specialty-specific knowledge collection.
    Feature #89 - Specialty collections.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager

    success = knowledge_manager.create_specialty_collection(
        specialty=request.specialty,
        description=request.description,
        document_ids=request.document_ids,
        curator=request.curator
    )

    if success:
        return {"specialty": request.specialty, "status": "created"}
    else:
        raise HTTPException(status_code=500, detail="Failed to create collection")


@app.get("/api/v1/knowledge/collections")
async def list_specialty_collections():
    """
    List all specialty collections.
    Feature #89 - Specialty collections.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager
    return {"collections": knowledge_manager.list_collections()}


@app.post("/api/v1/knowledge/collections/{specialty}/add/{document_id}")
async def add_to_collection(specialty: str, document_id: str):
    """
    Add a document to a specialty collection.
    Feature #89 - Specialty collections.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager

    success = knowledge_manager.add_to_collection(specialty, document_id)
    if success:
        return {"status": "added", "specialty": specialty, "document_id": document_id}
    else:
        raise HTTPException(status_code=404, detail=f"Collection '{specialty}' not found")


@app.get("/api/v1/knowledge/conflicts")
async def get_conflicts(resolved: bool = False):
    """
    Get guideline conflict alerts.
    Feature #89 - Conflict detection.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager, get_unresolved_conflicts

    if resolved:
        from dataclasses import asdict
        all_conflicts = [asdict(c) for c in knowledge_manager.conflicts]
        return {"conflicts": all_conflicts}
    else:
        return {"conflicts": get_unresolved_conflicts()}


@app.post("/api/v1/knowledge/conflicts/{alert_id}/resolve")
async def resolve_conflict(alert_id: str, request: ConflictResolutionRequest):
    """
    Mark a conflict as resolved.
    Feature #89 - Conflict management.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager

    success = knowledge_manager.resolve_conflict(alert_id, request.resolution_notes)
    if success:
        return {"status": "resolved", "alert_id": alert_id}
    else:
        raise HTTPException(status_code=404, detail=f"Conflict '{alert_id}' not found")


@app.post("/api/v1/knowledge/conflicts/detect/{document_id}")
async def detect_document_conflicts(document_id: str):
    """
    Detect potential conflicts for a specific document.
    Feature #89 - Conflict detection.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager
    from dataclasses import asdict

    conflicts = knowledge_manager.detect_conflicts(document_id)
    return {
        "document_id": document_id,
        "conflicts_detected": len(conflicts),
        "conflicts": [asdict(c) for c in conflicts]
    }


@app.get("/api/v1/knowledge/check-updates")
async def check_for_guideline_updates():
    """
    Check for updates to clinical guidelines from PubMed.
    Feature #89 - Automated updates.

    Queries major guideline sources (AHA, ADA, GOLD, etc.) for new publications.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager

    updates = await knowledge_manager.check_for_updates()
    return {
        "updates_found": len(updates),
        "updates": updates
    }


@app.get("/api/v1/knowledge/rss-feeds")
async def list_rss_feeds():
    """
    List available RSS feeds for medical updates.
    Feature #89 - RSS feed monitoring.
    """
    return {
        "feeds": [
            {"name": name, "url": url, "status": "active"}
            for name, url in MEDICAL_RSS_FEEDS.items()
        ],
        "note": "RSS feeds are checked periodically for new guidelines. Use /api/v1/knowledge/rss-feeds/{feed_name}/check to manually check a feed."
    }


@app.get("/api/v1/knowledge/rss-feeds/{feed_name}/check")
async def check_rss_feed(feed_name: str):
    """
    Check an RSS feed for new articles.
    Feature #89 - RSS feed monitoring.
    """
    if feed_name not in MEDICAL_RSS_FEEDS:
        raise HTTPException(status_code=404, detail=f"Feed '{feed_name}' not found")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(MEDICAL_RSS_FEEDS[feed_name])
            # Parse RSS (simplified - in production use feedparser)
            content = response.text

            # Count items (simplified)
            import re
            items = re.findall(r'<item>.*?</item>', content, re.DOTALL)

            return {
                "feed": feed_name,
                "url": MEDICAL_RSS_FEEDS[feed_name],
                "items_found": len(items),
                "status": "success",
                "note": "Use /api/v1/knowledge/pubmed/ingest to add relevant articles"
            }
    except Exception as e:
        return {
            "feed": feed_name,
            "status": "error",
            "error": str(e)
        }


@app.post("/api/v1/knowledge/deprecate/{document_id}")
async def deprecate_guideline(document_id: str, reason: str):
    """
    Mark a guideline as deprecated (no longer recommended).
    Feature #89 - Guideline lifecycle management.
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG system not available")

    from rag import knowledge_manager

    success = knowledge_manager.deprecate_guideline(document_id, reason)
    if success:
        log_phi_access(
            action="GUIDELINE_DEPRECATED",
            patient_id="N/A",
            details=f"Deprecated: {document_id}, Reason: {reason}"
        )
        return {"status": "deprecated", "document_id": document_id, "reason": reason}
    else:
        raise HTTPException(status_code=404, detail=f"Guideline '{document_id}' not found")


# ═══════════════════════════════════════════════════════════════════════════════
# RACIAL MEDICINE AWARENESS ENDPOINTS (Feature #79)
# ═══════════════════════════════════════════════════════════════════════════════

# Skin assessment guidance for melanin-rich skin
SKIN_ASSESSMENT_GUIDANCE = {
    "cyanosis": {
        "light_skin": "Blue discoloration of lips, nail beds, and skin",
        "dark_skin": "Gray or white appearance of oral mucosa, conjunctiva, nail beds. Check tongue and inner lips.",
        "recommendation": "For Fitzpatrick IV-VI, assess oral mucosa and conjunctiva rather than nail beds alone."
    },
    "jaundice": {
        "light_skin": "Yellow discoloration of skin and sclera",
        "dark_skin": "Check sclera, hard palate, palms, and soles. Skin yellowing may not be visible.",
        "recommendation": "Examine sclera in natural light. Check palms and soles for yellow tinge."
    },
    "pallor": {
        "light_skin": "Pale or white appearance of skin",
        "dark_skin": "Grayish, ashen appearance. Mucous membranes may appear pale gray.",
        "recommendation": "Assess conjunctiva, oral mucosa, and palms for pallor rather than facial skin."
    },
    "erythema": {
        "light_skin": "Pink or red discoloration",
        "dark_skin": "May appear purple, dark brown, or as increased warmth without visible color change.",
        "recommendation": "Palpate for warmth and edema. Look for subtle color darkening or purple tones."
    },
    "petechiae": {
        "light_skin": "Red pinpoint dots",
        "dark_skin": "Dark purple or brown dots. May only be visible on palms, soles, oral mucosa.",
        "recommendation": "Examine oral mucosa, conjunctiva, palms, and soles for petechiae."
    },
    "bruising": {
        "light_skin": "Blue, purple, green, yellow progression",
        "dark_skin": "Darker than surrounding skin, may appear black. Palpate for tenderness.",
        "recommendation": "Palpation is key. Color changes may be subtle or not visible."
    },
    "rash": {
        "light_skin": "Red, raised, or flat lesions",
        "dark_skin": "May appear hyperpigmented, hypopigmented, or purple. Texture changes important.",
        "recommendation": "Focus on texture (papules, vesicles) and distribution pattern. Color may not be reliable."
    },
    "melanoma": {
        "light_skin": "Asymmetric pigmented lesion, irregular borders",
        "dark_skin": "Check acral sites: palms, soles, nail beds, mucous membranes. Subungual melanoma more common.",
        "recommendation": "ABCDE criteria still apply but examine acral sites routinely."
    }
}

# Medication considerations based on ancestry (pharmacogenomics)
MEDICATION_ANCESTRY_CONSIDERATIONS = {
    "african": {
        "ace_inhibitors": {
            "alert": "ACE inhibitors may have reduced efficacy for hypertension",
            "recommendation": "Consider thiazide diuretic or CCB as first-line. If ACE inhibitor needed, may require higher doses.",
            "evidence": "Multiple trials show reduced BP response in African-descent patients"
        },
        "beta_blockers": {
            "alert": "Beta-blockers may have reduced antihypertensive effect",
            "recommendation": "Consider alternative first-line agents. If used, monitor closely.",
            "evidence": "VA Cooperative Trial, ALLHAT"
        },
        "bidil": {
            "alert": "BiDil (isosorbide dinitrate/hydralazine) FDA-approved for heart failure",
            "recommendation": "Consider for heart failure in self-identified African American patients",
            "evidence": "A-HeFT trial"
        }
    },
    "asian": {
        "warfarin": {
            "alert": "May require lower warfarin doses",
            "recommendation": "Start at lower dose, monitor INR closely",
            "evidence": "CYP2C9/VKORC1 variants more common"
        },
        "clopidogrel": {
            "alert": "Higher prevalence of CYP2C19 poor metabolizers",
            "recommendation": "Consider alternative antiplatelet or genetic testing",
            "evidence": "Up to 15-25% may be poor metabolizers"
        }
    }
}


def generate_racial_medicine_alerts(request: RacialMedicineRequest) -> RacialMedicineResponse:
    """Generate clinical decision support alerts for racial medicine considerations."""
    alerts = []
    skin_guidance = None
    med_considerations = []
    calc_warnings = []

    fitzpatrick = request.fitzpatrick_type
    ancestry = request.self_reported_ancestry or []
    context = request.clinical_context
    readings = request.current_readings or {}
    orders = request.pending_orders or []

    # Pulse oximeter accuracy alert for darker skin tones
    if fitzpatrick in [FitzpatrickSkinType.TYPE_IV, FitzpatrickSkinType.TYPE_V, FitzpatrickSkinType.TYPE_VI]:
        if context == "vitals" or "spo2" in readings:
            spo2 = readings.get("spo2")
            alerts.append(RacialMedicineAlert(
                alert_type="pulse_ox",
                severity="warning",
                title="Pulse Oximeter Accuracy",
                message=f"SpO2 readings may overestimate actual oxygen saturation by 1-4% on darker skin tones (Fitzpatrick {fitzpatrick.value}).",
                recommendation="Consider ABG for critical decisions. Studies show 3x higher occult hypoxemia rates in Black patients. SpO2 94% may actually be 90-93%.",
                evidence_source="NEJM 2020, FDA Draft Guidance 2025"
            ))

    # Skin assessment guidance for melanin-rich skin
    if fitzpatrick in [FitzpatrickSkinType.TYPE_IV, FitzpatrickSkinType.TYPE_V, FitzpatrickSkinType.TYPE_VI]:
        if context == "skin_exam" or context == "physical_exam":
            skin_guidance = SKIN_ASSESSMENT_GUIDANCE
            alerts.append(RacialMedicineAlert(
                alert_type="skin_assessment",
                severity="info",
                title="Skin Assessment Guidance",
                message="Standard skin findings present differently on melanin-rich skin.",
                recommendation="See skin assessment guidance for modified examination techniques.",
                evidence_source="PMC, MIT 2024"
            ))

    # Medication considerations based on ancestry
    ancestry_lower = [a.lower() for a in ancestry]
    for anc in ancestry_lower:
        if anc in ["african", "african american", "black"]:
            if any("ace" in o.lower() or "lisinopril" in o.lower() or "enalapril" in o.lower() or "ramipril" in o.lower() for o in orders):
                med_considerations.append(MEDICATION_ANCESTRY_CONSIDERATIONS["african"]["ace_inhibitors"])
            if any("metoprolol" in o.lower() or "atenolol" in o.lower() or "propranolol" in o.lower() for o in orders):
                med_considerations.append(MEDICATION_ANCESTRY_CONSIDERATIONS["african"]["beta_blockers"])
            # Always mention BiDil for heart failure context
            if context == "heart_failure" or any("heart failure" in o.lower() for o in orders):
                med_considerations.append(MEDICATION_ANCESTRY_CONSIDERATIONS["african"]["bidil"])

    # Maternal health alert
    if context == "obstetric" and any(a.lower() in ["african", "african american", "black"] for a in ancestry):
        alerts.append(RacialMedicineAlert(
            alert_type="maternal",
            severity="warning",
            title="Elevated Maternal Risk",
            message="Black women face 3-4x higher maternal mortality rates, regardless of income or education.",
            recommendation="Lower threshold for escalation. Document all patient-reported symptoms. Monitor closely for preeclampsia, hemorrhage, cardiomyopathy.",
            evidence_source="KFF, CDC MMWR"
        ))

    # Pain management bias reminder
    if context == "pain":
        alerts.append(RacialMedicineAlert(
            alert_type="pain",
            severity="info",
            title="Pain Assessment Reminder",
            message="Research shows racial bias affects pain treatment decisions.",
            recommendation="Use standardized pain scales. Document patient-reported levels without subjective interpretation. False beliefs about biological differences lead to undertreatment.",
            evidence_source="PNAS 2016, JAMA Network Open"
        ))

    # Sickle cell alert
    if context == "sickle_cell" or context == "pain_crisis":
        alerts.append(RacialMedicineAlert(
            alert_type="sickle_cell",
            severity="critical",
            title="Sickle Cell Pain Crisis Protocol",
            message="Vaso-occlusive crisis is a MEDICAL EMERGENCY. Target: pain medication within 60 minutes.",
            recommendation="Use patient's individualized pain plan. High-dose opioids often medically necessary. Do not delay treatment. Monitor for stroke, acute chest syndrome.",
            evidence_source="ASH Guidelines, Hematology.org"
        ))

    # Calculator bias warnings
    calc_warnings = [
        "eGFR: Use CKD-EPI 2021 race-free equation (NKF/ASN recommendation)",
        "Pulmonary function: Race-based 'corrections' are being phased out",
        "VBAC calculator: Some versions have race adjustments that may underestimate success"
    ]

    return RacialMedicineResponse(
        alerts=alerts,
        skin_assessment_guidance=skin_guidance,
        medication_considerations=med_considerations if med_considerations else None,
        calculator_warnings=calc_warnings if context == "calculator" else None,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/v1/racial-medicine/alerts")
async def get_racial_medicine_alerts(request: RacialMedicineRequest, req: Request):
    """
    Get racial medicine clinical decision support alerts.

    Returns alerts and guidance based on patient's Fitzpatrick skin type,
    ancestry, and clinical context. Addresses pulse oximeter accuracy,
    medication considerations, skin assessment, and more.
    """
    # Audit log
    audit_logger._log_event(
        event_type="CDS",
        action="RACIAL_MEDICINE_ALERT",
        patient_id=request.patient_id,
        status="request",
        details={"context": request.clinical_context, "fitzpatrick": request.fitzpatrick_type.value if request.fitzpatrick_type else None}
    )

    response = generate_racial_medicine_alerts(request)

    audit_logger._log_event(
        event_type="CDS",
        action="RACIAL_MEDICINE_ALERT",
        patient_id=request.patient_id,
        status="success",
        details={"alerts_count": len(response.alerts)}
    )

    return response


@app.get("/api/v1/racial-medicine/skin-guidance")
async def get_skin_assessment_guidance():
    """Get skin assessment guidance for melanin-rich skin."""
    return {
        "guidance": SKIN_ASSESSMENT_GUIDANCE,
        "note": "Standard skin findings present differently on Fitzpatrick IV-VI skin types. Use these modified assessment techniques.",
        "sources": [
            "MIT News 2024 - Diagnostic accuracy on darker skin",
            "PMC - Skin Inclusion in Medical Education",
            "JAAD - Representation in dermatology"
        ]
    }


@app.get("/api/v1/racial-medicine/medication-considerations/{ancestry}")
async def get_medication_considerations(ancestry: str):
    """Get medication considerations for specific ancestry."""
    ancestry_key = ancestry.lower()
    if ancestry_key in ["african", "african_american", "black"]:
        return MEDICATION_ANCESTRY_CONSIDERATIONS.get("african", {})
    elif ancestry_key in ["asian", "east_asian", "south_asian"]:
        return MEDICATION_ANCESTRY_CONSIDERATIONS.get("asian", {})
    else:
        return {"message": "No specific considerations on file. Consider pharmacogenomic testing for personalized guidance."}


# ═══════════════════════════════════════════════════════════════════════════════
# CULTURAL CARE PREFERENCES ENDPOINTS (Feature #80)
# ═══════════════════════════════════════════════════════════════════════════════

# Medications with potentially restricted ingredients
DIETARY_MEDICATION_CONCERNS = {
    "gelatin_capsules": {
        "concern": "May contain pork-derived gelatin",
        "affected_diets": ["halal", "kosher", "vegetarian", "vegan"],
        "alternatives": "Request tablet form or vegetarian capsules if available"
    },
    "alcohol_preparations": {
        "concern": "Contains alcohol as solvent/preservative",
        "affected_diets": ["halal", "some_christian"],
        "alternatives": "Request alcohol-free formulation if available"
    },
    "lactose_fillers": {
        "concern": "Contains lactose as tablet filler",
        "affected_diets": ["vegan", "lactose_intolerant"],
        "alternatives": "Check for lactose-free alternatives"
    },
    "animal_derived": {
        "concern": "May contain animal-derived ingredients (stearic acid, etc.)",
        "affected_diets": ["vegetarian", "vegan", "jain"],
        "alternatives": "Consult pharmacist for plant-based alternatives"
    }
}

# Religious considerations database
RELIGIOUS_CARE_CONSIDERATIONS = {
    "jehovahs_witness": {
        "blood_products": {
            "refused": ["whole_blood", "red_cells", "white_cells", "platelets", "plasma"],
            "individual_conscience": ["albumin", "immunoglobulins", "clotting_factors", "cell_salvage"],
            "note": "ALWAYS confirm individual patient preferences. Some may accept individual conscience items."
        },
        "alternatives": "Consider EPO, iron supplementation, cell salvage, meticulous surgical hemostasis",
        "resources": "Contact JW Hospital Liaison Committee for support"
    },
    "islam": {
        "dietary": ["halal", "no_pork", "no_alcohol"],
        "fasting": {
            "ramadan": "Dawn to sunset fasting. Adjust medication timing. IV meds generally acceptable.",
            "exemptions": "Illness may exempt from fasting - encourage discussion with imam"
        },
        "modesty": "Strong preference for same-gender providers, especially for women",
        "prayer": "Five daily prayers - accommodate timing when possible",
        "end_of_life": "Assisted suicide prohibited. DNR requires structured process."
    },
    "judaism": {
        "dietary": ["kosher", "no_pork", "no_shellfish", "meat_dairy_separation"],
        "sabbath": "Friday sunset to Saturday sunset. Emergency care always permitted (pikuach nefesh).",
        "modesty": "Orthodox women may prefer female providers",
        "end_of_life": "Complex - generally oppose hastening death but accept comfort care"
    },
    "hinduism": {
        "dietary": ["vegetarian", "no_beef"],
        "modesty": "May prefer same-gender providers",
        "traditional_medicine": "May use Ayurvedic remedies alongside Western medicine",
        "family": "Extended family often involved in decisions"
    },
    "buddhism": {
        "dietary": ["vegetarian_common"],
        "end_of_life": "May refuse sedation to maintain awareness at death",
        "organ_donation": "Generally supported as act of compassion"
    },
    "sikhism": {
        "five_ks": "Kesh (uncut hair), Kangha, Kara, Kachera, Kirpan - discuss before surgical prep",
        "turban": "Religious head covering - minimize removal",
        "dietary": ["vegetarian_common", "no_halal_meat"]
    }
}

# In-memory storage for patient cultural preferences (in production, use database)
patient_cultural_preferences: Dict[str, CulturalCarePreferences] = {}


def generate_cultural_care_alerts(request: CulturalCareRequest) -> CulturalCareResponse:
    """Generate cultural care alerts and guidance."""
    alerts = []
    dietary_concerns = []
    blood_guidance = None
    modesty_accommodations = []
    comm_guidance = None

    prefs = request.preferences
    if not prefs:
        # Try to load from storage
        prefs = patient_cultural_preferences.get(request.patient_id)

    if not prefs:
        return CulturalCareResponse(
            alerts=[CulturalCareAlert(
                alert_type="info",
                severity="info",
                title="No Cultural Preferences on File",
                message="Cultural care preferences not documented for this patient.",
                recommendation="Consider asking about cultural/religious preferences during intake."
            )],
            dietary_medication_concerns=[],
            blood_product_guidance=None,
            modesty_accommodations=[],
            communication_guidance=None,
            timestamp=datetime.utcnow().isoformat()
        )

    # Religion-specific alerts
    if prefs.religion:
        religion_lower = prefs.religion.lower().replace(" ", "_").replace("'", "")
        if religion_lower in RELIGIOUS_CARE_CONSIDERATIONS:
            rel_info = RELIGIOUS_CARE_CONSIDERATIONS[religion_lower]
            alerts.append(CulturalCareAlert(
                alert_type="religious",
                severity="info",
                title=f"Religious Considerations: {prefs.religion}",
                message=f"Patient identifies as {prefs.religion}. See religious care guidance.",
                recommendation="Review religion-specific considerations and confirm preferences with patient."
            ))

    # Blood product preferences (especially JW)
    if prefs.blood_product_preferences:
        bp = prefs.blood_product_preferences
        refused = []
        if not bp.whole_blood:
            refused.append("whole blood")
        if not bp.red_cells:
            refused.append("red cells")
        if not bp.white_cells:
            refused.append("white cells")
        if not bp.platelets:
            refused.append("platelets")
        if not bp.plasma:
            refused.append("plasma")

        if refused:
            alerts.append(CulturalCareAlert(
                alert_type="blood_product",
                severity="critical",
                title="Blood Product Restrictions",
                message=f"Patient declines: {', '.join(refused)}",
                recommendation="Use patient blood management strategies. Confirm individual conscience items. Document refusal."
            ))
            blood_guidance = {
                "refused": refused,
                "individual_conscience": {
                    "albumin": bp.albumin,
                    "immunoglobulins": bp.immunoglobulins,
                    "clotting_factors": bp.clotting_factors,
                    "cell_salvage": bp.cell_salvage
                },
                "alternatives": ["EPO", "iron supplementation", "cell salvage", "acute normovolemic hemodilution", "meticulous hemostasis"]
            }

    # Dietary medication concerns
    if prefs.dietary_restrictions:
        for restriction in prefs.dietary_restrictions:
            for med_type, concern_info in DIETARY_MEDICATION_CONCERNS.items():
                if restriction.lower() in [d.lower() for d in concern_info["affected_diets"]]:
                    dietary_concerns.append({
                        "restriction": restriction,
                        "concern": concern_info["concern"],
                        "alternative": concern_info["alternatives"]
                    })

        if dietary_concerns:
            alerts.append(CulturalCareAlert(
                alert_type="dietary",
                severity="warning",
                title="Dietary Medication Restrictions",
                message=f"Patient has dietary restrictions: {', '.join(prefs.dietary_restrictions)}",
                recommendation="Review medications for restricted ingredients. See dietary concerns list."
            ))

    # Fasting status
    if prefs.fasting_status:
        alerts.append(CulturalCareAlert(
            alert_type="fasting",
            severity="warning",
            title=f"Currently Fasting: {prefs.fasting_status.title()}",
            message="Patient is currently observing a religious fast.",
            recommendation="Adjust oral medication timing to non-fasting hours. Discuss exemptions for illness if appropriate."
        ))

    # Modesty requirements
    if prefs.modesty_requirements:
        modesty_accommodations = prefs.modesty_requirements
        if "same_gender_provider" in prefs.modesty_requirements:
            alerts.append(CulturalCareAlert(
                alert_type="modesty",
                severity="action_required",
                title="Same-Gender Provider Preferred",
                message="Patient prefers same-gender provider for care.",
                recommendation="Arrange same-gender provider if possible. If not available, explain necessity and offer chaperone."
            ))

    # Provider gender preference
    if prefs.provider_gender_preference and prefs.provider_gender_preference != "no_preference":
        modesty_accommodations.append(f"provider_gender_{prefs.provider_gender_preference}")

    # Communication preference
    if prefs.communication_preference != CommunicationPreference.DIRECT:
        comm_guidance = {
            "style": prefs.communication_preference.value,
            "guidance": {
                "indirect": "Use softer language. Deliver serious news gradually. Allow time for processing.",
                "family_first": "Share information with designated family member first. They will share with patient.",
                "family_present": "Ensure designated family members present for important discussions."
            }.get(prefs.communication_preference.value, "")
        }
        if prefs.decision_making_style != DecisionMakingStyle.INDIVIDUAL:
            comm_guidance["decision_making"] = f"Decision style: {prefs.decision_making_style.value}"
            if prefs.primary_decision_maker:
                comm_guidance["decision_maker"] = prefs.primary_decision_maker

    # Family involvement
    if prefs.decision_making_style != DecisionMakingStyle.INDIVIDUAL:
        alerts.append(CulturalCareAlert(
            alert_type="family",
            severity="info",
            title=f"Family Involvement: {prefs.decision_making_style.value.replace('_', ' ').title()}",
            message="Patient prefers family involvement in healthcare decisions.",
            recommendation=f"Include family in discussions. Primary decision maker: {prefs.primary_decision_maker or 'Not specified'}"
        ))

    return CulturalCareResponse(
        alerts=alerts,
        dietary_medication_concerns=dietary_concerns,
        blood_product_guidance=blood_guidance,
        modesty_accommodations=modesty_accommodations,
        communication_guidance=comm_guidance.get("guidance") if comm_guidance else None,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/v1/cultural-care/alerts")
async def get_cultural_care_alerts(request: CulturalCareRequest, req: Request):
    """
    Get cultural care alerts and guidance for patient.

    Returns alerts based on patient's cultural/religious preferences,
    dietary restrictions, blood product preferences, and communication style.
    """
    audit_logger._log_event(
        event_type="CDS",
        action="CULTURAL_CARE_ALERT",
        patient_id=request.patient_id,
        status="request",
        details={"context": request.clinical_context}
    )

    response = generate_cultural_care_alerts(request)

    audit_logger._log_event(
        event_type="CDS",
        action="CULTURAL_CARE_ALERT",
        patient_id=request.patient_id,
        status="success",
        details={"alerts_count": len(response.alerts)}
    )

    return response


@app.post("/api/v1/cultural-care/preferences/{patient_id}")
async def save_cultural_preferences(patient_id: str, preferences: CulturalCarePreferences, req: Request):
    """Save cultural care preferences for a patient."""
    patient_cultural_preferences[patient_id] = preferences

    audit_logger._log_event(
        event_type="PHI_UPDATE",
        action="SAVE_CULTURAL_PREFERENCES",
        patient_id=patient_id,
        status="success",
        details={"religion": preferences.religion, "dietary_count": len(preferences.dietary_restrictions)}
    )

    return {"status": "saved", "patient_id": patient_id}


@app.get("/api/v1/cultural-care/preferences/{patient_id}")
async def get_cultural_preferences(patient_id: str, req: Request):
    """Get cultural care preferences for a patient."""
    prefs = patient_cultural_preferences.get(patient_id)
    if not prefs:
        raise HTTPException(status_code=404, detail="No cultural preferences on file")

    audit_logger._log_event(
        event_type="PHI_ACCESS",
        action="GET_CULTURAL_PREFERENCES",
        patient_id=patient_id,
        status="success"
    )

    return prefs


@app.get("/api/v1/cultural-care/religious-guidance/{religion}")
async def get_religious_guidance(religion: str):
    """Get religious care considerations for a specific religion."""
    religion_key = religion.lower().replace(" ", "_").replace("'", "")
    if religion_key in RELIGIOUS_CARE_CONSIDERATIONS:
        return {
            "religion": religion,
            "considerations": RELIGIOUS_CARE_CONSIDERATIONS[religion_key]
        }
    return {"religion": religion, "message": "No specific guidance on file. Ask patient about their preferences."}


# ═══════════════════════════════════════════════════════════════════════════════
# IMPLICIT BIAS ALERTS (Feature #81) - Gentle, evidence-based reminders
# ═══════════════════════════════════════════════════════════════════════════════

# Evidence-based bias awareness database
# Each entry is framed as educational, supportive, and non-accusatory
IMPLICIT_BIAS_EVIDENCE = {
    "pain_assessment": {
        "title": "Pain Assessment Awareness",
        "reminder": "Research shows pain may be systematically undertreated in some patient populations. Taking a moment to ensure the pain score reflects the patient's experience helps provide equitable care.",
        "evidence": "Hoffman et al. (2016) PNAS: Found false beliefs about biological differences correlated with lower pain ratings for Black patients. Meghani et al. (2012): Meta-analysis showed Black patients 22% less likely to receive pain medication.",
        "reflection_prompt": "Does the documented pain level match the patient's verbal and non-verbal cues?",
        "resources": ["NIH Pain Consortium Resources", "AAPM Equitable Pain Care Guidelines"]
    },
    "pain_medication": {
        "title": "Pain Medication Prescribing",
        "reminder": "Studies show disparities in analgesic prescribing across patient populations. Ensuring pain medication aligns with documented pain severity supports equitable treatment.",
        "evidence": "Pletcher et al. (2008) JAMA: Found Black and Hispanic patients less likely to receive opioids for pain in ED. Singhal et al. (2016): Racial bias in pain treatment persists across settings.",
        "reflection_prompt": "Is the prescribed analgesia appropriate for the documented pain level, regardless of patient demographics?",
        "resources": ["CDC Opioid Prescribing Guidelines", "SAMHSA Equity Resources"]
    },
    "triage": {
        "title": "Triage Assessment",
        "reminder": "Triage decisions can be influenced by unconscious factors. Focusing on objective clinical criteria helps ensure all patients receive appropriate urgency levels.",
        "evidence": "Schrader & Lewis (2013): Found racial disparities in ED triage acuity assignments. Johnson et al. (2013): Implicit bias correlated with treatment recommendations.",
        "reflection_prompt": "Is this triage level based on objective clinical findings and vital signs?",
        "resources": ["ESI Triage Handbook", "ACEP Equity in Emergency Care"]
    },
    "cardiac_symptoms": {
        "title": "Cardiac Symptom Evaluation",
        "reminder": "Cardiac presentations may differ across patient groups. Women and some ethnic groups may present with atypical symptoms. A thorough evaluation prevents missed diagnoses.",
        "evidence": "Schulman et al. (1999) NEJM: Found race and sex affected cardiac catheterization recommendations. McSweeney et al. (2003): Women's MI symptoms often differ from 'classic' presentation.",
        "reflection_prompt": "Have atypical presentations been considered, and is the workup appropriately thorough?",
        "resources": ["AHA Go Red for Women", "ACC Chest Pain Guidelines"]
    },
    "psychiatric": {
        "title": "Psychiatric Evaluation",
        "reminder": "Research shows diagnostic patterns vary across demographic groups. Focusing on specific symptoms and functional impact supports accurate diagnosis.",
        "evidence": "Neighbors et al. (2003): Black patients more likely to be diagnosed with schizophrenia vs mood disorders. Strakowski et al. (1995): Racial differences in psychiatric diagnosis persist.",
        "reflection_prompt": "Is the diagnosis based on specific DSM criteria rather than general impressions?",
        "resources": ["APA Cultural Formulation Interview", "NIMH Resources"]
    },
    "substance_use": {
        "title": "Substance Use Assessment",
        "reminder": "Patients with substance use disorders may face stigma that affects care. Treating substance use as a medical condition supports therapeutic relationships.",
        "evidence": "van Boekel et al. (2013): Healthcare workers' negative attitudes affect care quality. SAMHSA: Stigma is a major barrier to treatment seeking.",
        "reflection_prompt": "Am I approaching this patient's substance use with the same clinical objectivity as other medical conditions?",
        "resources": ["SAMHSA TIP Series", "ASAM Guidelines"]
    },
    "general": {
        "title": "Clinical Decision-Making",
        "reminder": "We all have unconscious associations that can influence decisions. Taking a brief pause to reflect supports more objective clinical reasoning.",
        "evidence": "Project Implicit (Harvard): Implicit associations are universal and measurable. FitzGerald & Hurst (2017): Implicit bias affects clinical decisions across specialties.",
        "reflection_prompt": "Would my clinical approach be the same if this patient had different demographics?",
        "resources": ["Project Implicit Health Tests", "AAMC Unconscious Bias Training"]
    }
}

# Keywords that trigger specific bias context detection
BIAS_TRIGGER_KEYWORDS = {
    "pain_assessment": ["pain", "hurts", "aching", "discomfort", "sore", "tender", "painful", "agony", "suffering", "pain score", "pain level", "10 out of 10", "severe pain"],
    "pain_medication": ["morphine", "hydromorphone", "oxycodone", "fentanyl", "dilaudid", "percocet", "vicodin", "norco", "tramadol", "opioid", "narcotic", "pain med", "analgesia"],
    "triage": ["triage", "acuity", "esi level", "priority", "urgent", "emergent", "wait time"],
    "cardiac_symptoms": ["chest pain", "chest tightness", "shortness of breath", "dyspnea", "palpitations", "cardiac", "heart", "mi", "acs", "stemi", "nstemi", "angina"],
    "psychiatric": ["psych", "mental health", "depression", "anxiety", "schizophrenia", "bipolar", "psychosis", "suicidal", "si", "psychiatric", "behavioral"],
    "substance_use": ["drug use", "alcohol", "intoxicated", "overdose", "withdrawal", "addiction", "substance", "opioid use", "drug seeking", "narcan"]
}


def detect_bias_context(keywords: List[str], chief_complaint: Optional[str] = None) -> Optional[ImplicitBiasContext]:
    """Detect which bias context applies based on documentation keywords."""
    text_to_check = " ".join(keywords).lower()
    if chief_complaint:
        text_to_check += " " + chief_complaint.lower()

    # Check each context in priority order
    for context, triggers in BIAS_TRIGGER_KEYWORDS.items():
        for trigger in triggers:
            if trigger in text_to_check:
                return ImplicitBiasContext(context)

    return None


def generate_bias_alert(context: ImplicitBiasContext, patient_ancestry: Optional[str] = None) -> ImplicitBiasAlert:
    """Generate a gentle, evidence-based bias awareness alert."""
    evidence_data = IMPLICIT_BIAS_EVIDENCE.get(context.value, IMPLICIT_BIAS_EVIDENCE["general"])

    return ImplicitBiasAlert(
        context=context,
        title=evidence_data["title"],
        reminder=evidence_data["reminder"],
        evidence=evidence_data["evidence"],
        reflection_prompt=evidence_data["reflection_prompt"],
        resources=evidence_data.get("resources", [])
    )


@app.post("/api/v1/implicit-bias/check")
async def check_implicit_bias(request: ImplicitBiasRequest, req: Request):
    """
    Check if implicit bias awareness reminder should be shown.

    Triggers gentle, evidence-based reminders during clinical documentation
    to support equitable care. Reminders are educational, not accusatory.

    Returns reminder only when:
    1. Patient ancestry indicates potential disparity context AND
    2. Clinical context matches known disparity areas (pain, cardiac, etc.)
    """
    # HIPAA audit logging
    log_audit_event(
        event_type="implicit_bias_check",
        patient_id=request.patient_id,
        action="bias_awareness_check",
        details={
            "context": request.clinical_context.value,
            "ancestry_provided": request.patient_ancestry is not None
        },
        request=req
    )

    # Detect context if not provided
    detected_context = request.clinical_context
    if detected_context == ImplicitBiasContext.GENERAL:
        detected = detect_bias_context(request.transcript_keywords, request.chief_complaint)
        if detected:
            detected_context = detected

    # Determine if reminder should be shown
    # We show reminders in high-disparity contexts for patients with ancestry data
    # that indicates potential for disparate treatment based on research
    high_disparity_ancestries = ["african", "black", "hispanic", "latino", "native_american", "indigenous"]

    should_show = False
    alerts = []

    if request.patient_ancestry:
        ancestry_lower = request.patient_ancestry.lower()
        if any(hda in ancestry_lower for hda in high_disparity_ancestries):
            # Show reminder for high-disparity contexts
            if detected_context in [
                ImplicitBiasContext.PAIN_ASSESSMENT,
                ImplicitBiasContext.PAIN_MEDICATION,
                ImplicitBiasContext.CARDIAC_SYMPTOMS,
                ImplicitBiasContext.PSYCHIATRIC,
                ImplicitBiasContext.TRIAGE
            ]:
                should_show = True
                alerts.append(generate_bias_alert(detected_context, request.patient_ancestry))

    # Also check for specific medication prescribing disparities
    if request.medications_ordered:
        pain_meds = ["morphine", "hydromorphone", "oxycodone", "fentanyl", "dilaudid", "hydrocodone"]
        if any(med.lower() in " ".join(request.medications_ordered).lower() for med in pain_meds):
            if request.patient_ancestry and any(hda in request.patient_ancestry.lower() for hda in high_disparity_ancestries):
                if not any(a.context == ImplicitBiasContext.PAIN_MEDICATION for a in alerts):
                    should_show = True
                    alerts.append(generate_bias_alert(ImplicitBiasContext.PAIN_MEDICATION, request.patient_ancestry))

    return ImplicitBiasResponse(
        should_show_reminder=should_show,
        alerts=alerts,
        context_detected=detected_context,
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/v1/implicit-bias/contexts")
async def get_bias_contexts():
    """Get all available implicit bias contexts with their evidence."""
    return {
        "contexts": [
            {
                "context": context,
                "title": IMPLICIT_BIAS_EVIDENCE[context]["title"],
                "reminder": IMPLICIT_BIAS_EVIDENCE[context]["reminder"],
                "evidence_summary": IMPLICIT_BIAS_EVIDENCE[context]["evidence"][:100] + "..."
            }
            for context in IMPLICIT_BIAS_EVIDENCE.keys()
        ]
    }


@app.get("/api/v1/implicit-bias/resources")
async def get_bias_resources():
    """Get educational resources for implicit bias training."""
    return {
        "training_resources": [
            {
                "name": "Project Implicit",
                "url": "https://implicit.harvard.edu/implicit/",
                "description": "Free Implicit Association Tests to understand unconscious biases"
            },
            {
                "name": "AAMC Unconscious Bias Resources",
                "url": "https://www.aamc.org/what-we-do/equity-diversity-inclusion/unconscious-bias-training",
                "description": "Medical education resources on unconscious bias"
            },
            {
                "name": "NIH Bias in Health Care",
                "url": "https://www.nih.gov/ending-structural-racism/bias-health-care",
                "description": "NIH resources on addressing bias in healthcare"
            },
            {
                "name": "CDC Health Equity Resources",
                "url": "https://www.cdc.gov/healthequity/",
                "description": "CDC materials on health disparities and equity"
            }
        ],
        "key_publications": [
            "Hoffman KM et al. (2016). Racial bias in pain assessment and treatment recommendations. PNAS.",
            "FitzGerald C & Hurst S (2017). Implicit bias in healthcare professionals. BMC Medical Ethics.",
            "Pletcher MJ et al. (2008). Trends in opioid prescribing by race/ethnicity. JAMA.",
            "Chapman EN et al. (2013). Physicians and implicit bias: How doctors may unwittingly perpetuate health care disparities. JGIM."
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MATERNAL HEALTH MONITORING (Feature #82) - High-risk OB alerts for Black mothers
# ═══════════════════════════════════════════════════════════════════════════════

# Maternal warning signs database - evidence-based from ACOG, CDC, and NIH
MATERNAL_WARNING_SIGNS = {
    "emergency": [
        {
            "symptom": "Severe headache",
            "description": "Headache that doesn't go away with medication, especially with vision changes",
            "urgency": "emergency",
            "action": "Evaluate immediately for preeclampsia/eclampsia. Check BP, urine protein, reflexes.",
            "ask_patient": "Do you have a headache that won't go away, even with pain medication?"
        },
        {
            "symptom": "Vision changes",
            "description": "Blurry vision, seeing spots, flashing lights, or temporary blindness",
            "urgency": "emergency",
            "action": "Evaluate immediately for preeclampsia. Stat BP, magnesium sulfate if severe.",
            "ask_patient": "Have you noticed any changes in your vision - spots, flashing lights, or blurry vision?"
        },
        {
            "symptom": "Seizures",
            "description": "Any seizure activity during pregnancy or postpartum",
            "urgency": "emergency",
            "action": "Eclampsia protocol - secure airway, magnesium sulfate, emergent delivery evaluation.",
            "ask_patient": "Have you had any seizures or episodes of shaking you couldn't control?"
        },
        {
            "symptom": "Difficulty breathing",
            "description": "Shortness of breath, chest tightness, or feeling like can't get enough air",
            "urgency": "emergency",
            "action": "Evaluate for peripartum cardiomyopathy, PE, or amniotic fluid embolism. Stat EKG, BNP, echo.",
            "ask_patient": "Are you having trouble breathing or feeling short of breath?"
        },
        {
            "symptom": "Chest pain",
            "description": "Any chest pain or pressure, especially with exertion",
            "urgency": "emergency",
            "action": "Cardiac workup - EKG, troponin, echo. Consider PE, aortic dissection, cardiomyopathy.",
            "ask_patient": "Do you have any pain or pressure in your chest?"
        },
        {
            "symptom": "Heavy bleeding",
            "description": "Soaking more than one pad per hour, or passing clots larger than an egg",
            "urgency": "emergency",
            "action": "Postpartum hemorrhage protocol. Type and cross, IV access, uterotonics, possible transfusion.",
            "ask_patient": "How much are you bleeding? Are you soaking through a pad in an hour or less?"
        }
    ],
    "urgent": [
        {
            "symptom": "Fever",
            "description": "Temperature 100.4°F (38°C) or higher",
            "urgency": "urgent",
            "action": "Evaluate for endometritis, mastitis, UTI, wound infection. CBC, blood cultures, UA.",
            "ask_patient": "Have you had a fever or felt feverish? Have you checked your temperature?"
        },
        {
            "symptom": "Severe abdominal pain",
            "description": "Abdominal pain not relieved by position change or medication",
            "urgency": "urgent",
            "action": "Evaluate for uterine rupture, placental abruption, ectopic, appendicitis.",
            "ask_patient": "Do you have severe stomach or belly pain that won't go away?"
        },
        {
            "symptom": "Swelling of face or hands",
            "description": "New or worsening swelling of face, hands, especially if sudden",
            "urgency": "urgent",
            "action": "Check BP, urine protein. Evaluate for preeclampsia even postpartum.",
            "ask_patient": "Have you noticed new swelling in your face or hands?"
        },
        {
            "symptom": "Leg pain or swelling",
            "description": "Pain, redness, or swelling in one leg more than the other",
            "urgency": "urgent",
            "action": "Evaluate for DVT. Consider D-dimer, lower extremity doppler.",
            "ask_patient": "Do you have pain or swelling in one leg, especially the calf?"
        },
        {
            "symptom": "Thoughts of self-harm",
            "description": "Thoughts of hurting self or baby, feeling like family would be better off without you",
            "urgency": "urgent",
            "action": "Immediate psychiatric evaluation. Do not leave patient alone. Safety plan.",
            "ask_patient": "Have you had any thoughts of hurting yourself or your baby?"
        },
        {
            "symptom": "Overwhelming sadness",
            "description": "Crying all the time, feeling hopeless, unable to care for self or baby",
            "urgency": "urgent",
            "action": "Screen for postpartum depression (EPDS). Consider psych referral, medication.",
            "ask_patient": "How are you feeling emotionally? Are you having trouble coping or feeling very sad?"
        }
    ],
    "routine": [
        {
            "symptom": "Fatigue",
            "description": "Extreme tiredness beyond normal postpartum exhaustion",
            "urgency": "routine",
            "action": "Check CBC for anemia, TSH for thyroid. Assess sleep, support system.",
            "ask_patient": "How tired are you feeling? Is it more than you'd expect?"
        },
        {
            "symptom": "Difficulty bonding",
            "description": "Trouble feeling connected to or caring for baby",
            "urgency": "routine",
            "action": "Screen for postpartum depression, assess support system, lactation issues.",
            "ask_patient": "How are you feeling about the baby? Are you having trouble connecting?"
        },
        {
            "symptom": "Incision concerns",
            "description": "Redness, drainage, or opening of C-section or perineal incision",
            "urgency": "routine",
            "action": "Examine wound, consider infection. Antibiotics if infected, wound care.",
            "ask_patient": "How does your incision look? Any redness, drainage, or opening?"
        }
    ]
}

# Disparity awareness data
MATERNAL_DISPARITY_DATA = {
    "african": {
        "mortality_ratio": "3-4x higher than white women",
        "evidence": "CDC 2023: Black women are 3-4 times more likely to die from pregnancy-related causes than white women. This disparity persists across all income and education levels.",
        "key_factors": [
            "Cardiovascular conditions including cardiomyopathy",
            "Preeclampsia and eclampsia",
            "Hemorrhage",
            "Infection/sepsis"
        ],
        "recommendation": "Lower threshold for intervention. Believe patient-reported symptoms. Close follow-up especially postpartum. Screen for cardiomyopathy if any cardiac symptoms."
    },
    "native_american": {
        "mortality_ratio": "2-3x higher than white women",
        "evidence": "CDC 2023: American Indian/Alaska Native women have significantly elevated maternal mortality rates.",
        "key_factors": [
            "Access to care barriers",
            "Higher rates of chronic conditions",
            "Hemorrhage"
        ],
        "recommendation": "Ensure close follow-up, address access barriers, consider telemedicine for remote patients."
    }
}

POSTPARTUM_CHECKLIST = [
    "Blood pressure check (preeclampsia can occur up to 6 weeks postpartum)",
    "Bleeding assessment (amount, color, clots)",
    "Emotional wellbeing screening (Edinburgh Postnatal Depression Scale)",
    "Incision/wound check if applicable",
    "Feeding assessment (breast or bottle, any issues)",
    "Pain level assessment",
    "Sleep and fatigue evaluation",
    "Social support assessment",
    "Contraception discussion",
    "Follow-up appointment scheduled"
]


def determine_maternal_risk_level(ancestry: Optional[str], conditions: List[str], symptoms: List[str]) -> MaternalRiskLevel:
    """Determine maternal risk level based on ancestry, conditions, and symptoms."""
    high_risk_ancestries = ["african", "black", "native_american", "indigenous", "alaska_native"]
    high_risk_conditions = ["hypertension", "diabetes", "obesity", "preeclampsia", "cardiac", "cardiomyopathy", "sickle cell"]

    # Check for high-risk factors
    has_ancestry_risk = ancestry and any(hra in ancestry.lower() for hra in high_risk_ancestries)
    has_condition_risk = any(any(hrc in cond.lower() for hrc in high_risk_conditions) for cond in conditions)
    has_emergency_symptoms = any(
        any(ws["symptom"].lower() in symptom.lower() for ws in MATERNAL_WARNING_SIGNS["emergency"])
        for symptom in symptoms
    )

    if has_emergency_symptoms:
        return MaternalRiskLevel.HIGH
    elif has_ancestry_risk and has_condition_risk:
        return MaternalRiskLevel.HIGH
    elif has_ancestry_risk or has_condition_risk:
        return MaternalRiskLevel.ELEVATED
    else:
        return MaternalRiskLevel.STANDARD


def generate_maternal_alerts(
    ancestry: Optional[str],
    maternal_status: MaternalStatus,
    risk_level: MaternalRiskLevel,
    symptoms: List[str],
    vital_signs: Optional[Dict]
) -> List[MaternalHealthAlert]:
    """Generate maternal health alerts based on patient data."""
    alerts = []

    # Disparity awareness alert for high-risk ancestry
    high_risk_ancestries = ["african", "black", "native_american", "indigenous"]
    if ancestry and any(hra in ancestry.lower() for hra in high_risk_ancestries):
        ancestry_key = "african" if any(a in ancestry.lower() for a in ["african", "black"]) else "native_american"
        disparity_data = MATERNAL_DISPARITY_DATA.get(ancestry_key, MATERNAL_DISPARITY_DATA["african"])

        alerts.append(MaternalHealthAlert(
            alert_type="disparity_awareness",
            severity="warning",
            title="Maternal Health Disparity Alert",
            message=f"This patient is in a demographic group with {disparity_data['mortality_ratio']} maternal mortality rate.",
            recommendation=disparity_data["recommendation"],
            evidence=disparity_data["evidence"]
        ))

    # Check vital signs for concerning values
    if vital_signs:
        bp_systolic = vital_signs.get("bp_systolic", 0)
        bp_diastolic = vital_signs.get("bp_diastolic", 0)

        if bp_systolic >= 160 or bp_diastolic >= 110:
            alerts.append(MaternalHealthAlert(
                alert_type="preeclampsia",
                severity="critical",
                title="Severe Hypertension - Preeclampsia Risk",
                message=f"BP {bp_systolic}/{bp_diastolic} is severely elevated. Immediate evaluation needed.",
                recommendation="Start antihypertensive therapy. Check urine protein, LFTs, platelets. Consider magnesium sulfate.",
                warning_signs=[MaternalWarningSign(**ws) for ws in MATERNAL_WARNING_SIGNS["emergency"][:3]]
            ))
        elif bp_systolic >= 140 or bp_diastolic >= 90:
            alerts.append(MaternalHealthAlert(
                alert_type="hypertension",
                severity="warning",
                title="Elevated Blood Pressure",
                message=f"BP {bp_systolic}/{bp_diastolic} is elevated. Monitor closely for preeclampsia.",
                recommendation="Repeat BP in 15 min. Check urine protein. Review preeclampsia symptoms."
            ))

    # Check for emergency symptoms in reported symptoms
    for symptom in symptoms:
        symptom_lower = symptom.lower()
        for emergency in MATERNAL_WARNING_SIGNS["emergency"]:
            if emergency["symptom"].lower() in symptom_lower or symptom_lower in emergency["symptom"].lower():
                alerts.append(MaternalHealthAlert(
                    alert_type="warning_sign",
                    severity="critical",
                    title=f"Emergency Warning Sign: {emergency['symptom']}",
                    message=emergency["description"],
                    recommendation=emergency["action"],
                    warning_signs=[MaternalWarningSign(**emergency)]
                ))
                break

    # Postpartum-specific alerts
    if maternal_status == MaternalStatus.POSTPARTUM:
        alerts.append(MaternalHealthAlert(
            alert_type="postpartum_check",
            severity="info",
            title="Postpartum Assessment Due",
            message="This patient is in the postpartum period. Complete postpartum checklist.",
            recommendation="Review all warning signs with patient. Schedule follow-up if not already done."
        ))

    return alerts


@app.post("/api/v1/maternal-health/assess")
async def assess_maternal_health(request: MaternalHealthRequest, req: Request):
    """
    Assess maternal health and generate alerts.

    Provides heightened alerts for patients in demographic groups with
    elevated maternal mortality risk. Based on CDC, ACOG, and NIH data.
    """
    # HIPAA audit logging
    log_audit_event(
        event_type="maternal_health_assessment",
        patient_id=request.patient_id,
        action="maternal_risk_assessment",
        details={
            "maternal_status": request.maternal_status.value,
            "ancestry_provided": request.patient_ancestry is not None
        },
        request=req
    )

    # Determine risk level
    risk_level = determine_maternal_risk_level(
        request.patient_ancestry,
        request.conditions,
        request.current_symptoms
    )

    # Generate alerts
    alerts = generate_maternal_alerts(
        request.patient_ancestry,
        request.maternal_status,
        risk_level,
        request.current_symptoms,
        request.vital_signs
    )

    # Get warning signs to check based on status and risk
    warning_signs = []
    if risk_level in [MaternalRiskLevel.ELEVATED, MaternalRiskLevel.HIGH]:
        # Include all emergency and urgent signs
        for ws in MATERNAL_WARNING_SIGNS["emergency"]:
            warning_signs.append(MaternalWarningSign(**ws))
        for ws in MATERNAL_WARNING_SIGNS["urgent"]:
            warning_signs.append(MaternalWarningSign(**ws))
    else:
        # Include emergency signs only
        for ws in MATERNAL_WARNING_SIGNS["emergency"]:
            warning_signs.append(MaternalWarningSign(**ws))

    # Get disparity context
    disparity_context = None
    high_risk_ancestries = ["african", "black", "native_american", "indigenous"]
    if request.patient_ancestry and any(hra in request.patient_ancestry.lower() for hra in high_risk_ancestries):
        ancestry_key = "african" if any(a in request.patient_ancestry.lower() for a in ["african", "black"]) else "native_american"
        disparity_data = MATERNAL_DISPARITY_DATA.get(ancestry_key)
        if disparity_data:
            disparity_context = disparity_data["evidence"]

    return MaternalHealthResponse(
        risk_level=risk_level,
        alerts=alerts,
        warning_signs_to_check=warning_signs,
        disparity_context=disparity_context,
        postpartum_checklist=POSTPARTUM_CHECKLIST if request.maternal_status == MaternalStatus.POSTPARTUM else [],
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/v1/maternal-health/warning-signs")
async def get_maternal_warning_signs():
    """Get all maternal warning signs organized by urgency."""
    return {
        "emergency": MATERNAL_WARNING_SIGNS["emergency"],
        "urgent": MATERNAL_WARNING_SIGNS["urgent"],
        "routine": MATERNAL_WARNING_SIGNS["routine"]
    }


@app.get("/api/v1/maternal-health/postpartum-checklist")
async def get_postpartum_checklist():
    """Get the postpartum assessment checklist."""
    return {
        "checklist": POSTPARTUM_CHECKLIST,
        "note": "Complete all items at each postpartum visit. Preeclampsia can occur up to 6 weeks postpartum."
    }


@app.get("/api/v1/maternal-health/disparity-data")
async def get_maternal_disparity_data():
    """Get maternal mortality disparity data by ancestry."""
    return {
        "disparity_data": MATERNAL_DISPARITY_DATA,
        "source": "CDC Pregnancy Mortality Surveillance System, 2023",
        "key_message": "Black women are 3-4 times more likely to die from pregnancy-related causes than white women. This disparity persists across all income and education levels."
    }


# SDOH INTEGRATION (Feature #84) - Social Determinants of Health
# ═══════════════════════════════════════════════════════════════════════════════

# SDOH factors database with screening questions, clinical impacts, and Z-codes
SDOH_FACTORS_DATABASE = {
    "economic_stability": {
        "food_insecurity": {
            "factor": "Food Insecurity",
            "description": "Unable to afford or access nutritious food consistently",
            "risk_level": "high",
            "clinical_impact": "Affects ability to follow dietary recommendations, medication absorption, diabetes/heart disease management. Risk of hypoglycemia if skipping meals while on diabetes medications.",
            "screening_question": "In the past 12 months, did you worry food would run out before you had money to buy more?",
            "icd10_code": "Z59.41",  # Food insecurity
            "interventions": [
                {"type": "referral", "title": "SNAP Benefits", "description": "Supplemental Nutrition Assistance Program enrollment assistance"},
                {"type": "referral", "title": "Local Food Bank", "description": "Connect with community food bank or pantry"},
                {"type": "care_modification", "title": "Medication Timing", "description": "Adjust medication schedule around meals patient can consistently access"}
            ]
        },
        "housing_instability": {
            "factor": "Housing Instability",
            "description": "At risk of or experiencing homelessness, frequent moves, or unsafe housing",
            "risk_level": "critical",
            "clinical_impact": "Cannot safely store medications (insulin refrigeration), inconsistent sleep, stress response, difficulty following up on care. Address before complex treatment plans.",
            "screening_question": "Are you worried about losing your housing, or do you have a stable place to stay?",
            "icd10_code": "Z59.0",  # Homelessness
            "interventions": [
                {"type": "referral", "title": "Housing Authority", "description": "Connect with local housing assistance programs"},
                {"type": "accommodation", "title": "Medication Storage", "description": "Provide medication that doesn't require refrigeration when possible"},
                {"type": "care_modification", "title": "Extended Rx Supply", "description": "90-day prescriptions to reduce pharmacy visit frequency"}
            ]
        },
        "financial_strain": {
            "factor": "Financial Strain",
            "description": "Unable to pay for basic needs including medications and medical care",
            "risk_level": "high",
            "clinical_impact": "Medication non-adherence due to cost, delayed care, choosing between food and medicine. May split pills or skip doses.",
            "screening_question": "In the past year, have you had trouble paying for medications or medical bills?",
            "icd10_code": "Z59.86",  # Financial insecurity
            "interventions": [
                {"type": "resource", "title": "Patient Assistance Programs", "description": "Pharmaceutical company programs for free/reduced medications"},
                {"type": "care_modification", "title": "Generic Alternatives", "description": "Switch to lower-cost generic medications when clinically appropriate"},
                {"type": "referral", "title": "Financial Counselor", "description": "Hospital financial assistance and payment plans"}
            ]
        },
        "unemployment": {
            "factor": "Unemployment",
            "description": "Currently unemployed or underemployed",
            "risk_level": "moderate",
            "clinical_impact": "May lose insurance coverage, increased stress and depression risk, affects overall health trajectory.",
            "screening_question": "Do you currently have a job? If not, are you looking for work?",
            "icd10_code": "Z56.0",  # Unemployment
            "interventions": [
                {"type": "referral", "title": "Workforce Development", "description": "Job training and placement services"},
                {"type": "resource", "title": "Medicaid Enrollment", "description": "Help with health insurance coverage during unemployment"}
            ]
        }
    },
    "education": {
        "low_health_literacy": {
            "factor": "Low Health Literacy",
            "description": "Difficulty understanding health information, medication instructions, or discharge paperwork",
            "risk_level": "high",
            "clinical_impact": "Medication errors, missed warning signs, non-adherence due to confusion. Affects ability to self-manage chronic conditions.",
            "screening_question": "How confident are you filling out medical forms by yourself?",
            "icd10_code": "Z55.0",  # Illiteracy and low-level literacy
            "interventions": [
                {"type": "accommodation", "title": "Teach-Back Method", "description": "Use teach-back to confirm understanding of instructions"},
                {"type": "accommodation", "title": "Simplified Materials", "description": "Provide instructions at 5th grade reading level with pictures"},
                {"type": "care_modification", "title": "Verbal Instructions", "description": "Prioritize verbal over written instructions, use diagrams"}
            ]
        },
        "limited_english": {
            "factor": "Limited English Proficiency",
            "description": "English is not primary language, limited ability to communicate in English",
            "risk_level": "high",
            "clinical_impact": "Communication barriers affect diagnosis accuracy, informed consent, medication understanding. Risk of medical errors.",
            "screening_question": "What language do you feel most comfortable speaking?",
            "icd10_code": "Z60.3",  # Acculturation difficulty
            "interventions": [
                {"type": "accommodation", "title": "Professional Interpreter", "description": "Use certified medical interpreter, not family members"},
                {"type": "resource", "title": "Translated Materials", "description": "Provide discharge instructions in patient's preferred language"},
                {"type": "care_modification", "title": "Language Line", "description": "Document interpreter services used for continuity"}
            ]
        }
    },
    "healthcare_access": {
        "no_insurance": {
            "factor": "No Health Insurance",
            "description": "Uninsured or underinsured, unable to afford coverage",
            "risk_level": "high",
            "clinical_impact": "Delayed preventive care, emergency-only utilization pattern, untreated chronic conditions, medication non-adherence.",
            "screening_question": "Do you have health insurance? Are you able to afford your medical care?",
            "icd10_code": "Z59.7",  # Insufficient social insurance and welfare support
            "interventions": [
                {"type": "referral", "title": "Medicaid/ACA Enrollment", "description": "Help with health insurance marketplace or Medicaid application"},
                {"type": "resource", "title": "Community Health Center", "description": "Sliding-scale fee community health centers for ongoing care"},
                {"type": "care_modification", "title": "Prescription Assistance", "description": "$4 generic programs and manufacturer coupons"}
            ]
        },
        "no_regular_provider": {
            "factor": "No Regular Healthcare Provider",
            "description": "Does not have a primary care provider or medical home",
            "risk_level": "moderate",
            "clinical_impact": "Fragmented care, no preventive services, ED as primary access point, poor chronic disease management.",
            "screening_question": "Do you have a regular doctor or clinic you go to when you're sick?",
            "icd10_code": "Z75.3",  # Unavailability and inaccessibility of health-care facilities
            "interventions": [
                {"type": "referral", "title": "PCP Assignment", "description": "Help establish care with primary care provider"},
                {"type": "resource", "title": "Patient Navigator", "description": "Assign patient navigator to help coordinate care"}
            ]
        },
        "transportation_barrier": {
            "factor": "Transportation Barriers",
            "description": "Unable to get to medical appointments due to lack of transportation",
            "risk_level": "high",
            "clinical_impact": "Missed appointments, delayed care, unable to get to pharmacy. Major barrier to medication adherence and follow-up.",
            "screening_question": "Do you have reliable transportation to get to your medical appointments?",
            "icd10_code": "Z59.82",  # Transportation insecurity
            "interventions": [
                {"type": "resource", "title": "Medicaid Transportation", "description": "Non-emergency medical transportation benefit if Medicaid eligible"},
                {"type": "resource", "title": "Community Transit", "description": "Local senior/disability transit services"},
                {"type": "care_modification", "title": "Telehealth", "description": "Offer telehealth visits when clinically appropriate"},
                {"type": "care_modification", "title": "Mail-Order Pharmacy", "description": "Set up mail-order for maintenance medications"}
            ]
        }
    },
    "neighborhood": {
        "unsafe_neighborhood": {
            "factor": "Unsafe Neighborhood",
            "description": "Living in area with high crime, violence, or safety concerns",
            "risk_level": "moderate",
            "clinical_impact": "Unable to exercise safely outdoors, stress response, may avoid leaving home for appointments, affects mental health.",
            "screening_question": "Do you feel safe in your neighborhood?",
            "icd10_code": "Z59.1",  # Inadequate housing
            "interventions": [
                {"type": "care_modification", "title": "Indoor Exercise", "description": "Recommend indoor physical activity options"},
                {"type": "care_modification", "title": "Appointment Timing", "description": "Schedule appointments during daylight hours"}
            ]
        },
        "utility_insecurity": {
            "factor": "Utility Insecurity",
            "description": "Unable to pay utilities, risk of disconnection",
            "risk_level": "high",
            "clinical_impact": "No refrigeration for insulin/medications, extreme temperatures dangerous for elderly/chronic illness, no phone for emergencies.",
            "screening_question": "In the past year, has your utility company threatened to shut off services?",
            "icd10_code": "Z59.89",  # Other problems related to housing and economic circumstances
            "interventions": [
                {"type": "referral", "title": "LIHEAP", "description": "Low Income Home Energy Assistance Program"},
                {"type": "accommodation", "title": "Temperature-Stable Meds", "description": "Use insulin pens or other formulations less sensitive to temperature"}
            ]
        }
    },
    "social_community": {
        "social_isolation": {
            "factor": "Social Isolation",
            "description": "Limited social contact, lives alone, no support system",
            "risk_level": "moderate",
            "clinical_impact": "Increased depression risk, no caregiver support, may not seek help when ill, affects medication adherence and recovery.",
            "screening_question": "How often do you see or talk to family or friends?",
            "icd10_code": "Z60.4",  # Social exclusion and rejection
            "interventions": [
                {"type": "referral", "title": "Senior Center", "description": "Local senior center for social activities"},
                {"type": "referral", "title": "Support Groups", "description": "Condition-specific support groups"},
                {"type": "care_modification", "title": "Care Manager", "description": "Assign care manager for regular check-ins"}
            ]
        },
        "caregiver_stress": {
            "factor": "Caregiver Burden",
            "description": "Primary caregiver for family member, experiencing caregiver stress",
            "risk_level": "moderate",
            "clinical_impact": "Neglects own health, high stress/depression risk, may miss own appointments to care for others.",
            "screening_question": "Are you taking care of a family member who is sick or disabled?",
            "icd10_code": "Z63.6",  # Dependent relative needing care at home
            "interventions": [
                {"type": "referral", "title": "Respite Care", "description": "Temporary relief for caregivers"},
                {"type": "resource", "title": "Caregiver Support", "description": "Local caregiver support services and resources"}
            ]
        },
        "domestic_violence": {
            "factor": "Intimate Partner Violence",
            "description": "Experiencing or at risk of domestic violence",
            "risk_level": "critical",
            "clinical_impact": "Safety is primary concern. Affects all aspects of health. Screen privately, provide resources safely.",
            "screening_question": "Do you feel safe in your current relationship?",
            "icd10_code": "Z63.0",  # Problems in relationship with spouse or partner
            "interventions": [
                {"type": "referral", "title": "Domestic Violence Hotline", "description": "National DV Hotline: 1-800-799-7233"},
                {"type": "resource", "title": "Safety Planning", "description": "Help develop safety plan, provide resources discreetly"},
                {"type": "accommodation", "title": "Private Conversations", "description": "Always screen alone without partner present"}
            ]
        },
        "discrimination": {
            "factor": "Experienced Discrimination",
            "description": "Experienced discrimination in healthcare based on race, ethnicity, gender, sexuality, etc.",
            "risk_level": "moderate",
            "clinical_impact": "Medical mistrust, delayed care seeking, anxiety about healthcare interactions, may not disclose symptoms.",
            "screening_question": "Have you ever felt you were treated unfairly when getting medical care?",
            "icd10_code": "Z60.5",  # Target of perceived adverse discrimination and persecution
            "interventions": [
                {"type": "accommodation", "title": "Cultural Humility", "description": "Acknowledge concerns, provide culturally responsive care"},
                {"type": "care_modification", "title": "Patient Choice", "description": "Offer choice of provider when possible"}
            ]
        }
    }
}

# SDOH Z-codes for billing documentation
SDOH_Z_CODES = {
    "Z55.0": "Illiteracy and low-level literacy",
    "Z55.9": "Problems related to education and literacy, unspecified",
    "Z56.0": "Unemployment, unspecified",
    "Z56.9": "Problem related to employment, unspecified",
    "Z59.0": "Homelessness",
    "Z59.1": "Inadequate housing",
    "Z59.41": "Food insecurity",
    "Z59.48": "Other specified lack of adequate food",
    "Z59.7": "Insufficient social insurance and welfare support",
    "Z59.82": "Transportation insecurity",
    "Z59.86": "Financial insecurity",
    "Z59.89": "Other problems related to housing and economic circumstances",
    "Z60.2": "Problems related to living alone",
    "Z60.3": "Acculturation difficulty",
    "Z60.4": "Social exclusion and rejection",
    "Z60.5": "Target of perceived adverse discrimination and persecution",
    "Z62.819": "Personal history of neglect in childhood",
    "Z63.0": "Problems in relationship with spouse or partner",
    "Z63.6": "Dependent relative needing care at home",
    "Z75.3": "Unavailability and inaccessibility of health-care facilities",
}


def get_sdoh_factors_for_domain(domain: str) -> List[Dict]:
    """Get all SDOH factors for a given domain."""
    factors = []
    if domain in SDOH_FACTORS_DATABASE:
        for factor_id, factor_data in SDOH_FACTORS_DATABASE[domain].items():
            factors.append({
                "id": factor_id,
                **factor_data
            })
    return factors


def assess_sdoh_risk(responses: Dict[str, str], known_factors: List[str]) -> SDOHScreeningResponse:
    """
    Assess SDOH risk based on screening responses and known factors.
    Returns overall risk level, domain-specific risks, and interventions.
    """
    identified_factors = []
    alerts = []
    all_interventions = []
    z_codes = []
    domain_risks = {}

    # Process known factors
    for factor_id in known_factors:
        for domain, factors in SDOH_FACTORS_DATABASE.items():
            if factor_id in factors:
                factor_data = factors[factor_id]
                identified_factors.append(SDOHFactor(
                    domain=SDOHDomain(domain),
                    factor=factor_data["factor"],
                    description=factor_data["description"],
                    risk_level=SDOHRiskLevel(factor_data["risk_level"]),
                    clinical_impact=factor_data["clinical_impact"],
                    screening_question=factor_data["screening_question"],
                    icd10_code=factor_data.get("icd10_code")
                ))

                # Add Z-code for billing
                if factor_data.get("icd10_code"):
                    z_codes.append({
                        "code": factor_data["icd10_code"],
                        "description": SDOH_Z_CODES.get(factor_data["icd10_code"], factor_data["factor"])
                    })

                # Add interventions
                for intervention in factor_data.get("interventions", []):
                    all_interventions.append(SDOHIntervention(
                        factor=factor_data["factor"],
                        intervention_type=intervention["type"],
                        title=intervention["title"],
                        description=intervention["description"]
                    ))

                # Track domain risk
                risk_value = {"low": 1, "moderate": 2, "high": 3, "critical": 4}[factor_data["risk_level"]]
                if domain not in domain_risks or risk_value > domain_risks[domain]:
                    domain_risks[domain] = factor_data["risk_level"]

    # Generate alerts based on identified factors
    for factor in identified_factors:
        severity = "info" if factor.risk_level == SDOHRiskLevel.LOW else \
                   "warning" if factor.risk_level in [SDOHRiskLevel.MODERATE, SDOHRiskLevel.HIGH] else "critical"

        alert_type = "safety_concern" if factor.risk_level == SDOHRiskLevel.CRITICAL else \
                     "adherence_risk" if "medication" in factor.clinical_impact.lower() else "access_barrier"

        alerts.append(SDOHAlert(
            alert_type=alert_type,
            severity=severity,
            title=f"SDOH: {factor.factor}",
            message=factor.description,
            domain=factor.domain,
            clinical_impact=factor.clinical_impact,
            recommendations=[f"Screen for {factor.factor}", f"Consider {factor.clinical_impact.split('.')[0]}"],
            z_codes=[factor.icd10_code] if factor.icd10_code else []
        ))

    # Calculate overall risk
    if any(f.risk_level == SDOHRiskLevel.CRITICAL for f in identified_factors):
        overall_risk = SDOHRiskLevel.CRITICAL
    elif any(f.risk_level == SDOHRiskLevel.HIGH for f in identified_factors):
        overall_risk = SDOHRiskLevel.HIGH
    elif any(f.risk_level == SDOHRiskLevel.MODERATE for f in identified_factors):
        overall_risk = SDOHRiskLevel.MODERATE
    elif identified_factors:
        overall_risk = SDOHRiskLevel.LOW
    else:
        overall_risk = SDOHRiskLevel.LOW

    return SDOHScreeningResponse(
        patient_id="",  # Will be set by caller
        overall_risk=overall_risk,
        domain_risks=domain_risks,
        identified_factors=identified_factors,
        alerts=alerts,
        recommended_interventions=all_interventions,
        z_codes_for_billing=z_codes,
        screening_complete=len(known_factors) > 0,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/api/v1/sdoh/screen")
async def sdoh_screening(request: SDOHScreeningRequest):
    """
    Screen patient for SDOH factors.
    Returns identified risks, clinical impacts, and recommended interventions.
    """
    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=request.patient_id,
        details={"endpoint": "/api/v1/sdoh/screen", "factors_screened": request.known_factors}
    )

    response = assess_sdoh_risk(request.responses, request.known_factors)
    response.patient_id = request.patient_id

    return response


@app.get("/api/v1/sdoh/factors")
async def get_sdoh_factors(domain: Optional[str] = None):
    """
    Get SDOH factors database.
    Optionally filter by domain.
    """
    if domain:
        if domain not in SDOH_FACTORS_DATABASE:
            raise HTTPException(status_code=404, detail=f"Domain not found: {domain}")
        return {
            "domain": domain,
            "factors": get_sdoh_factors_for_domain(domain)
        }

    # Return all domains
    all_factors = {}
    for domain_name in SDOH_FACTORS_DATABASE:
        all_factors[domain_name] = get_sdoh_factors_for_domain(domain_name)

    return {
        "domains": list(SDOH_FACTORS_DATABASE.keys()),
        "factors": all_factors
    }


@app.get("/api/v1/sdoh/screening-questions")
async def get_screening_questions():
    """
    Get all SDOH screening questions organized by domain.
    Use these questions for standardized SDOH screening.
    """
    questions = {}
    for domain, factors in SDOH_FACTORS_DATABASE.items():
        questions[domain] = []
        for factor_id, factor_data in factors.items():
            questions[domain].append({
                "id": factor_id,
                "factor": factor_data["factor"],
                "question": factor_data["screening_question"],
                "risk_level": factor_data["risk_level"]
            })

    return {
        "questions": questions,
        "note": "These questions are based on validated SDOH screening tools (PRAPARE, AHC-HRSN, NACHC). Screen all patients annually."
    }


@app.get("/api/v1/sdoh/z-codes")
async def get_sdoh_z_codes():
    """
    Get ICD-10 Z-codes for SDOH documentation and billing.
    """
    return {
        "z_codes": SDOH_Z_CODES,
        "note": "Document SDOH Z-codes to capture social risk factors. Many payers now recognize these codes for care management."
    }


@app.post("/api/v1/sdoh/interventions")
async def get_sdoh_interventions(factors: List[str]):
    """
    Get recommended interventions for identified SDOH factors.
    """
    interventions = []

    for factor_id in factors:
        for domain, domain_factors in SDOH_FACTORS_DATABASE.items():
            if factor_id in domain_factors:
                factor_data = domain_factors[factor_id]
                for intervention in factor_data.get("interventions", []):
                    interventions.append({
                        "factor": factor_data["factor"],
                        "factor_id": factor_id,
                        "intervention_type": intervention["type"],
                        "title": intervention["title"],
                        "description": intervention["description"],
                        "urgency": "immediate" if factor_data["risk_level"] == "critical" else "routine"
                    })

    return {
        "factors_count": len(factors),
        "interventions": interventions
    }


@app.get("/api/v1/sdoh/adherence-risks")
async def get_adherence_risk_factors():
    """
    Get SDOH factors that specifically impact medication adherence.
    Use to identify patients at risk for non-adherence.
    """
    adherence_factors = []

    for domain, factors in SDOH_FACTORS_DATABASE.items():
        for factor_id, factor_data in factors.items():
            if any(keyword in factor_data["clinical_impact"].lower() for keyword in
                   ["medication", "adherence", "pharmacy", "insulin", "prescription"]):
                adherence_factors.append({
                    "factor_id": factor_id,
                    "factor": factor_data["factor"],
                    "domain": domain,
                    "clinical_impact": factor_data["clinical_impact"],
                    "screening_question": factor_data["screening_question"],
                    "z_code": factor_data.get("icd10_code")
                })

    return {
        "adherence_risk_factors": adherence_factors,
        "note": "These SDOH factors directly impact medication adherence. Address before assuming non-compliance."
    }


# HEALTH LITERACY ASSESSMENT (Feature #85)
# ═══════════════════════════════════════════════════════════════════════════════

# Health literacy risk indicators
LITERACY_RISK_INDICATORS = [
    "Asks to take materials home to read",
    "Identifies pills by color/shape not name",
    "Unable to name medications",
    "Frequently misses appointments",
    "Forms consistently incomplete or incorrect",
    "Brings someone to read for them",
    "Says 'I forgot my glasses'",
    "Avoids reading in front of clinician",
    "Educational attainment below high school",
    "Primary language not English",
    "Elderly with no recent formal education",
    "Previous medication errors",
    "Difficulty following multi-step instructions"
]

# Accommodations by literacy level
LITERACY_ACCOMMODATIONS = {
    "inadequate": [
        "Use pictures and diagrams exclusively",
        "Limit to 1-2 key messages per visit",
        "Use teach-back for every instruction",
        "Provide verbal-only instructions",
        "Use pill organizers with pictures",
        "Schedule more frequent follow-ups",
        "Involve family/caregiver in education",
        "Use video instructions if available",
        "Avoid written materials entirely",
        "Use 'chunk and check' method"
    ],
    "marginal": [
        "Use 5th grade reading level materials",
        "Supplement written with verbal",
        "Use bullet points, not paragraphs",
        "Include pictures with text",
        "Highlight key action items",
        "Use teach-back for critical points",
        "Limit to 3-4 key messages",
        "Use large font (14pt minimum)",
        "Avoid medical jargon completely"
    ],
    "adequate": [
        "Use 7th-8th grade materials",
        "Define any medical terms used",
        "Use headers and organization",
        "Offer to answer questions",
        "Confirm understanding of key points",
        "Standard discharge instructions acceptable"
    ],
    "proficient": [
        "Standard medical materials acceptable",
        "Can handle medical terminology",
        "Written instructions sufficient",
        "May appreciate detailed explanations"
    ]
}

# Plain language translations for common medical terms
PLAIN_LANGUAGE_DICTIONARY = {
    "hypertension": "high blood pressure",
    "hypotension": "low blood pressure",
    "tachycardia": "fast heart rate",
    "bradycardia": "slow heart rate",
    "dyspnea": "trouble breathing",
    "edema": "swelling",
    "nausea": "sick to your stomach",
    "emesis": "throwing up",
    "pyrexia": "fever",
    "afebrile": "no fever",
    "ambulatory": "able to walk",
    "bilateral": "both sides",
    "benign": "not cancer",
    "malignant": "cancer",
    "chronic": "long-lasting",
    "acute": "sudden or new",
    "prognosis": "what to expect",
    "diagnosis": "what is wrong",
    "contraindicated": "should not use",
    "prophylaxis": "prevention",
    "subcutaneous": "under the skin",
    "oral": "by mouth",
    "topical": "on the skin",
    "analgesic": "pain medicine",
    "antibiotic": "medicine to fight infection",
    "anticoagulant": "blood thinner",
    "diuretic": "water pill",
    "antihypertensive": "blood pressure medicine",
    "NPO": "nothing to eat or drink",
    "PRN": "as needed",
    "BID": "twice a day",
    "TID": "three times a day",
    "QID": "four times a day",
    "QD": "once a day",
    "HS": "at bedtime",
    "stat": "right away",
    "CBC": "blood count test",
    "BMP": "blood chemistry test",
    "CT": "special X-ray scan",
    "MRI": "special scan using magnets",
    "EKG": "heart rhythm test"
}

# Simplified discharge templates by condition
SIMPLIFIED_DISCHARGE_TEMPLATES = {
    "diabetes": {
        "topic": "Diabetes Care",
        "standard": "Monitor blood glucose levels and maintain glycemic control through dietary modifications and medication adherence.",
        "simplified": "Check your blood sugar every day. Eat healthy foods. Take your medicine the same time every day.",
        "key_points": [
            "Check blood sugar as told",
            "Take medicine same time daily",
            "Eat regular meals",
            "Call if blood sugar very high or very low"
        ],
        "teach_back": [
            "Show me how you check your blood sugar",
            "When do you take your diabetes medicine?",
            "What do you do if your blood sugar is too low?"
        ],
        "red_flags": [
            "Blood sugar over 300 - call doctor",
            "Blood sugar under 70 - eat sugar, call if not better",
            "Very thirsty, peeing a lot, confused - go to ER"
        ]
    },
    "heart_failure": {
        "topic": "Heart Failure Care",
        "standard": "Monitor daily weights, restrict sodium intake to <2g/day, and take diuretics as prescribed for fluid management.",
        "simplified": "Weigh yourself every morning. Eat less salt. Take your water pill every day.",
        "key_points": [
            "Weigh yourself every morning",
            "Write down your weight",
            "Eat less salt (no added salt)",
            "Take water pill in the morning"
        ],
        "teach_back": [
            "When do you weigh yourself?",
            "What foods have a lot of salt?",
            "When should you call about your weight?"
        ],
        "red_flags": [
            "Gained 3 pounds in one day - call doctor",
            "Gained 5 pounds in one week - call doctor",
            "Can't breathe lying down - go to ER",
            "Legs very swollen - call doctor"
        ]
    },
    "hypertension": {
        "topic": "High Blood Pressure",
        "standard": "Take antihypertensive medications as prescribed and monitor blood pressure regularly.",
        "simplified": "Take your blood pressure pill every day at the same time. Check your blood pressure at home.",
        "key_points": [
            "Take pill same time every day",
            "Don't skip doses",
            "Check blood pressure at home",
            "Eat less salt"
        ],
        "teach_back": [
            "What time do you take your blood pressure pill?",
            "What happens if you forget a dose?",
            "What blood pressure number is too high?"
        ],
        "red_flags": [
            "Blood pressure over 180/120 - go to ER",
            "Severe headache with high BP - go to ER",
            "Chest pain - call 911"
        ]
    },
    "anticoagulation": {
        "topic": "Blood Thinner Medicine",
        "standard": "Take anticoagulant as prescribed, monitor for bleeding, and maintain consistent vitamin K intake.",
        "simplified": "Take your blood thinner at the same time every day. Watch for bleeding. Eat the same amount of green vegetables every week.",
        "key_points": [
            "Take at same time every day",
            "Don't skip doses",
            "Watch for bleeding or bruising",
            "Keep eating the same foods"
        ],
        "teach_back": [
            "What time do you take your blood thinner?",
            "What should you watch for?",
            "What do you do if you cut yourself?"
        ],
        "red_flags": [
            "Bleeding that won't stop - go to ER",
            "Blood in urine or stool - call doctor",
            "Bad headache or confusion - go to ER",
            "Throwing up blood - call 911"
        ]
    },
    "infection": {
        "topic": "Taking Antibiotics",
        "standard": "Complete the full course of antibiotics as prescribed, even if symptoms resolve.",
        "simplified": "Take ALL your antibiotic pills, even if you feel better. Don't stop early.",
        "key_points": [
            "Take all the pills",
            "Don't stop when you feel better",
            "Take with food if it upsets stomach",
            "Finish the whole bottle"
        ],
        "teach_back": [
            "How many pills do you have left?",
            "When do you stop taking them?",
            "What if you feel better before they're gone?"
        ],
        "red_flags": [
            "Fever coming back - call doctor",
            "Rash or hives - stop and call doctor",
            "Getting worse not better - call doctor"
        ]
    },
    "post_surgery": {
        "topic": "After Your Surgery",
        "standard": "Monitor surgical site for signs of infection, take pain medication as needed, and follow activity restrictions.",
        "simplified": "Keep your wound clean and dry. Take pain medicine if you need it. Rest and don't lift heavy things.",
        "key_points": [
            "Keep wound clean and dry",
            "Take pain medicine as needed",
            "Don't lift heavy things",
            "Walk a little bit each day"
        ],
        "teach_back": [
            "How do you keep your wound clean?",
            "When can you take a shower?",
            "What does an infected wound look like?"
        ],
        "red_flags": [
            "Wound red, hot, or oozing - call doctor",
            "Fever over 101 - call doctor",
            "Wound opens up - go to ER",
            "Pain getting much worse - call doctor"
        ]
    }
}

# Teach-back checklist items
TEACH_BACK_CHECKLIST = {
    "medications": [
        "Name of each medication",
        "What each medication is for",
        "When to take each medication",
        "How to take (with food, etc.)",
        "What to do if a dose is missed",
        "Side effects to watch for"
    ],
    "warning_signs": [
        "What symptoms require calling the doctor",
        "What symptoms require going to ER",
        "Who to call with questions"
    ],
    "follow_up": [
        "When and where is next appointment",
        "What tests need to be done before appointment",
        "How to reschedule if needed"
    ],
    "activity": [
        "Activity restrictions",
        "When to resume normal activities",
        "Diet changes if any"
    ]
}


def assess_literacy_level(
    confidence_response: Optional[str] = None,
    observed_indicators: List[str] = [],
    known_sdoh_factors: List[str] = []
) -> LiteracyAssessment:
    """
    Assess health literacy based on screening and observations.
    Uses BRIEF screening (single confidence question) plus observed indicators.
    """
    risk_factors = []
    literacy_level = LiteracyLevel.ADEQUATE
    confidence_score = 0.5

    # Process confidence response (BRIEF/SILS screening)
    if confidence_response:
        response_lower = confidence_response.lower()
        if any(word in response_lower for word in ["not at all", "never", "not confident", "no"]):
            literacy_level = LiteracyLevel.INADEQUATE
            confidence_score = 0.8
            risk_factors.append("Self-reported low confidence with health forms")
        elif any(word in response_lower for word in ["sometimes", "a little", "somewhat"]):
            literacy_level = LiteracyLevel.MARGINAL
            confidence_score = 0.7
            risk_factors.append("Self-reported moderate confidence with health forms")

    # Process observed indicators
    for indicator in observed_indicators:
        if indicator in LITERACY_RISK_INDICATORS:
            risk_factors.append(indicator)

    # Adjust based on number of risk indicators
    if len(risk_factors) >= 3 and literacy_level == LiteracyLevel.ADEQUATE:
        literacy_level = LiteracyLevel.MARGINAL
        confidence_score = 0.6

    if len(risk_factors) >= 5:
        literacy_level = LiteracyLevel.INADEQUATE
        confidence_score = 0.7

    # Check for SDOH factors that correlate with low literacy
    sdoh_literacy_factors = ["low_health_literacy", "limited_english"]
    for factor in known_sdoh_factors:
        if factor in sdoh_literacy_factors:
            if literacy_level == LiteracyLevel.ADEQUATE:
                literacy_level = LiteracyLevel.MARGINAL
            risk_factors.append(f"SDOH factor: {factor}")

    # Determine recommended reading level
    reading_level_map = {
        LiteracyLevel.INADEQUATE: ReadingLevel.GRADE_3_5,
        LiteracyLevel.MARGINAL: ReadingLevel.GRADE_5_6,
        LiteracyLevel.ADEQUATE: ReadingLevel.GRADE_7_8,
        LiteracyLevel.PROFICIENT: ReadingLevel.GRADE_9_12
    }

    return LiteracyAssessment(
        patient_id="",  # Set by caller
        literacy_level=literacy_level,
        recommended_reading_level=reading_level_map[literacy_level],
        screening_method=LiteracyScreeningMethod.BRIEF if confidence_response else LiteracyScreeningMethod.OBSERVED,
        confidence_score=confidence_score,
        risk_factors=risk_factors,
        accommodations=LITERACY_ACCOMMODATIONS.get(literacy_level.value, []),
        teach_back_required=literacy_level in [LiteracyLevel.INADEQUATE, LiteracyLevel.MARGINAL],
        assessed_at=datetime.now(timezone.utc).isoformat()
    )


def get_simplified_instructions(
    condition: str,
    literacy_level: LiteracyLevel,
    medications: List[str] = []
) -> LiteracyAdaptedInstructions:
    """
    Get literacy-adapted discharge instructions for a condition.
    """
    template = SIMPLIFIED_DISCHARGE_TEMPLATES.get(condition.lower().replace(" ", "_"), {})

    instructions = []
    if template:
        instructions.append(DischargeInstruction(
            topic=template.get("topic", condition),
            standard_text=template.get("standard", ""),
            simplified_text=template.get("simplified", ""),
            reading_level=ReadingLevel.GRADE_5_6 if literacy_level in [LiteracyLevel.INADEQUATE, LiteracyLevel.MARGINAL] else ReadingLevel.GRADE_7_8,
            key_points=template.get("key_points", []),
            visual_aids=["Use pill organizer picture", "Daily checklist"],
            teach_back_questions=template.get("teach_back", [])
        ))

    # Generate simplified medication instructions
    med_instructions = []
    for med in medications:
        med_instructions.append({
            "medication": med,
            "simplified": f"Take your {med} at the same time every day. Don't skip doses."
        })

    # Get red flags in plain language
    red_flags = template.get("red_flags", [
        "Fever over 101°F - call doctor",
        "Getting worse instead of better - call doctor",
        "Can't eat or drink - go to ER"
    ])

    return LiteracyAdaptedInstructions(
        patient_id="",  # Set by caller
        literacy_level=literacy_level,
        reading_level=ReadingLevel.GRADE_5_6 if literacy_level in [LiteracyLevel.INADEQUATE, LiteracyLevel.MARGINAL] else ReadingLevel.GRADE_7_8,
        instructions=instructions,
        general_tips=LITERACY_ACCOMMODATIONS.get(literacy_level.value, [])[:5],
        red_flags_simplified=red_flags,
        medication_instructions=med_instructions,
        follow_up_simplified="Come back to see us on your appointment date. Bring all your medicine bottles.",
        teach_back_checklist=TEACH_BACK_CHECKLIST.get("medications", []) + TEACH_BACK_CHECKLIST.get("warning_signs", [])
    )


@app.post("/api/v1/literacy/assess")
async def assess_health_literacy(
    patient_id: str,
    confidence_response: Optional[str] = None,
    observed_indicators: List[str] = [],
    known_sdoh_factors: List[str] = []
):
    """
    Assess patient's health literacy level.
    Uses BRIEF single-question screening plus observed indicators.
    """
    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=patient_id,
        details={"endpoint": "/api/v1/literacy/assess"}
    )

    assessment = assess_literacy_level(confidence_response, observed_indicators, known_sdoh_factors)
    assessment.patient_id = patient_id

    return assessment


@app.get("/api/v1/literacy/screening-question")
async def get_literacy_screening_question():
    """
    Get the validated single-item literacy screening question.
    """
    return {
        "method": "BRIEF / SILS",
        "question": "How confident are you filling out medical forms by yourself?",
        "response_options": [
            {"value": "extremely", "interpretation": "proficient"},
            {"value": "quite a bit", "interpretation": "adequate"},
            {"value": "somewhat", "interpretation": "marginal"},
            {"value": "a little bit", "interpretation": "marginal"},
            {"value": "not at all", "interpretation": "inadequate"}
        ],
        "note": "A response of 'somewhat' or below indicates possible limited health literacy and need for accommodation."
    }


@app.get("/api/v1/literacy/risk-indicators")
async def get_literacy_risk_indicators():
    """
    Get observable risk indicators for low health literacy.
    """
    return {
        "indicators": LITERACY_RISK_INDICATORS,
        "note": "Observe for these behaviors during patient encounters. 3+ indicators suggest need for literacy assessment."
    }


@app.get("/api/v1/literacy/accommodations/{level}")
async def get_literacy_accommodations(level: str):
    """
    Get recommended accommodations for a literacy level.
    """
    if level not in LITERACY_ACCOMMODATIONS:
        raise HTTPException(status_code=404, detail=f"Level not found. Use: inadequate, marginal, adequate, proficient")

    return {
        "level": level,
        "accommodations": LITERACY_ACCOMMODATIONS[level],
        "teach_back_required": level in ["inadequate", "marginal"]
    }


@app.get("/api/v1/literacy/plain-language")
async def get_plain_language_dictionary():
    """
    Get dictionary of plain language translations for medical terms.
    """
    return {
        "translations": PLAIN_LANGUAGE_DICTIONARY,
        "note": "Use these plain language alternatives when communicating with patients with limited health literacy."
    }


@app.post("/api/v1/literacy/simplify-instructions")
async def simplify_discharge_instructions(
    patient_id: str,
    condition: str,
    literacy_level: str = "marginal",
    medications: List[str] = []
):
    """
    Get literacy-adapted discharge instructions for a condition.
    """
    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=patient_id,
        details={"endpoint": "/api/v1/literacy/simplify-instructions", "condition": condition}
    )

    try:
        level = LiteracyLevel(literacy_level)
    except ValueError:
        level = LiteracyLevel.MARGINAL

    instructions = get_simplified_instructions(condition, level, medications)
    instructions.patient_id = patient_id

    return instructions


@app.get("/api/v1/literacy/discharge-templates")
async def get_discharge_templates():
    """
    Get available simplified discharge instruction templates.
    """
    return {
        "conditions": list(SIMPLIFIED_DISCHARGE_TEMPLATES.keys()),
        "templates": {
            condition: {
                "topic": data["topic"],
                "has_simplified": True,
                "key_points_count": len(data.get("key_points", [])),
                "red_flags_count": len(data.get("red_flags", []))
            }
            for condition, data in SIMPLIFIED_DISCHARGE_TEMPLATES.items()
        }
    }


@app.get("/api/v1/literacy/teach-back-checklist")
async def get_teach_back_checklist(category: Optional[str] = None):
    """
    Get teach-back verification checklist items.
    """
    if category:
        if category not in TEACH_BACK_CHECKLIST:
            raise HTTPException(status_code=404, detail=f"Category not found. Use: medications, warning_signs, follow_up, activity")
        return {
            "category": category,
            "items": TEACH_BACK_CHECKLIST[category]
        }

    return {
        "categories": list(TEACH_BACK_CHECKLIST.keys()),
        "checklist": TEACH_BACK_CHECKLIST
    }


# INTERPRETER INTEGRATION (Feature #86) - Real-time translation services
# ═══════════════════════════════════════════════════════════════════════════════

# Supported languages with common medical phrases
SUPPORTED_LANGUAGES = {
    "es": {"name": "Spanish", "native": "Español", "speakers_us": "41M"},
    "zh": {"name": "Chinese", "native": "中文", "speakers_us": "3.5M"},
    "vi": {"name": "Vietnamese", "native": "Tiếng Việt", "speakers_us": "1.5M"},
    "ko": {"name": "Korean", "native": "한국어", "speakers_us": "1.1M"},
    "tl": {"name": "Tagalog", "native": "Tagalog", "speakers_us": "1.7M"},
    "ru": {"name": "Russian", "native": "Русский", "speakers_us": "900K"},
    "ar": {"name": "Arabic", "native": "العربية", "speakers_us": "1.2M"},
    "ht": {"name": "Haitian Creole", "native": "Kreyòl Ayisyen", "speakers_us": "900K"},
    "fr": {"name": "French", "native": "Français", "speakers_us": "1.3M"},
    "pt": {"name": "Portuguese", "native": "Português", "speakers_us": "700K"},
    "de": {"name": "German", "native": "Deutsch", "speakers_us": "1M"},
    "ja": {"name": "Japanese", "native": "日本語", "speakers_us": "450K"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "speakers_us": "650K"},
    "bn": {"name": "Bengali", "native": "বাংলা", "speakers_us": "300K"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "speakers_us": "280K"},
    "asl": {"name": "American Sign Language", "native": "ASL", "speakers_us": "500K"}
}

# Pre-translated clinical phrases by category
CLINICAL_PHRASES = {
    "es": {
        "greeting": [
            {"english": "Hello, I am your doctor.", "translated": "Hola, soy su médico.", "phonetic": "OH-lah, soy soo MEH-dee-koh"},
            {"english": "How are you feeling today?", "translated": "¿Cómo se siente hoy?", "phonetic": "KOH-moh seh see-EN-teh oy"},
            {"english": "I need an interpreter.", "translated": "Necesito un intérprete.", "phonetic": "neh-seh-SEE-toh oon een-TEHR-preh-teh"}
        ],
        "pain": [
            {"english": "Where does it hurt?", "translated": "¿Dónde le duele?", "phonetic": "DOHN-deh leh DWEH-leh"},
            {"english": "How bad is the pain? 1 to 10?", "translated": "¿Qué tan fuerte es el dolor? ¿1 a 10?", "phonetic": "keh tahn FWEHR-teh es el doh-LOHR"},
            {"english": "Is the pain sharp or dull?", "translated": "¿Es el dolor agudo o sordo?", "phonetic": "es el doh-LOHR ah-GOO-doh oh SOHR-doh"},
            {"english": "Point to where it hurts.", "translated": "Señale dónde le duele.", "phonetic": "seh-NYAH-leh DOHN-deh leh DWEH-leh"}
        ],
        "consent": [
            {"english": "I need your permission.", "translated": "Necesito su permiso.", "phonetic": "neh-seh-SEE-toh soo pehr-MEE-soh"},
            {"english": "Do you understand?", "translated": "¿Entiende?", "phonetic": "en-tee-EN-deh"},
            {"english": "Do you have questions?", "translated": "¿Tiene preguntas?", "phonetic": "tee-EH-neh preh-GOON-tahs"},
            {"english": "Please sign here.", "translated": "Por favor, firme aquí.", "phonetic": "pohr fah-VOHR, FEER-meh ah-KEE"}
        ],
        "medication": [
            {"english": "Take this medicine.", "translated": "Tome esta medicina.", "phonetic": "TOH-meh ES-tah meh-dee-SEE-nah"},
            {"english": "Once a day.", "translated": "Una vez al día.", "phonetic": "OO-nah vehs ahl DEE-ah"},
            {"english": "Twice a day.", "translated": "Dos veces al día.", "phonetic": "dohs VEH-sehs ahl DEE-ah"},
            {"english": "With food.", "translated": "Con comida.", "phonetic": "kohn koh-MEE-dah"},
            {"english": "Are you allergic to any medicines?", "translated": "¿Es alérgico a alguna medicina?", "phonetic": "es ah-LEHR-hee-koh ah ahl-GOO-nah meh-dee-SEE-nah"}
        ],
        "emergency": [
            {"english": "Call 911.", "translated": "Llame al 911.", "phonetic": "YAH-meh ahl noo-EH-veh OON-seh"},
            {"english": "Go to the emergency room.", "translated": "Vaya a la sala de emergencias.", "phonetic": "VAH-yah ah lah SAH-lah deh eh-mehr-HEN-see-ahs"},
            {"english": "This is serious.", "translated": "Esto es serio.", "phonetic": "ES-toh es SEH-ree-oh"}
        ],
        "discharge": [
            {"english": "Come back if you feel worse.", "translated": "Regrese si se siente peor.", "phonetic": "reh-GREH-seh see seh see-EN-teh peh-OHR"},
            {"english": "Your follow-up appointment is...", "translated": "Su cita de seguimiento es...", "phonetic": "soo SEE-tah deh seh-gee-mee-EN-toh es"},
            {"english": "Take all of your medicine.", "translated": "Tome toda su medicina.", "phonetic": "TOH-meh TOH-dah soo meh-dee-SEE-nah"}
        ]
    },
    "zh": {
        "greeting": [
            {"english": "Hello, I am your doctor.", "translated": "你好，我是你的医生。", "phonetic": "nǐ hǎo, wǒ shì nǐ de yī shēng"},
            {"english": "How are you feeling today?", "translated": "你今天感觉怎么样？", "phonetic": "nǐ jīn tiān gǎn jué zěn me yàng"},
            {"english": "I need an interpreter.", "translated": "我需要翻译。", "phonetic": "wǒ xū yào fān yì"}
        ],
        "pain": [
            {"english": "Where does it hurt?", "translated": "哪里疼？", "phonetic": "nǎ lǐ téng"},
            {"english": "How bad is the pain? 1 to 10?", "translated": "疼痛有多严重？1到10?", "phonetic": "téng tòng yǒu duō yán zhòng"},
            {"english": "Point to where it hurts.", "translated": "指着疼的地方。", "phonetic": "zhǐ zhe téng de dì fang"}
        ],
        "medication": [
            {"english": "Take this medicine.", "translated": "吃这个药。", "phonetic": "chī zhè ge yào"},
            {"english": "Once a day.", "translated": "每天一次。", "phonetic": "měi tiān yī cì"},
            {"english": "Twice a day.", "translated": "每天两次。", "phonetic": "měi tiān liǎng cì"}
        ]
    },
    "vi": {
        "greeting": [
            {"english": "Hello, I am your doctor.", "translated": "Xin chào, tôi là bác sĩ của bạn.", "phonetic": "sin chow, toy la bahk see koo-ah bahn"},
            {"english": "How are you feeling today?", "translated": "Hôm nay bạn cảm thấy thế nào?", "phonetic": "hohm nay bahn kahm thay theh now"}
        ],
        "pain": [
            {"english": "Where does it hurt?", "translated": "Đau ở đâu?", "phonetic": "dow uh dow"},
            {"english": "How bad is the pain? 1 to 10?", "translated": "Đau nhiều không? 1 đến 10?", "phonetic": "dow nyew kohng"}
        ]
    }
}

# Interpreter service contact info (template - hospitals configure their own)
INTERPRETER_SERVICES = {
    "language_line": {
        "name": "Language Line Solutions",
        "phone": "1-800-752-6096",
        "type": "phone",
        "available": "24/7",
        "languages": 240
    },
    "cyracom": {
        "name": "CyraCom",
        "phone": "1-800-713-4950",
        "type": "phone",
        "available": "24/7",
        "languages": 200
    },
    "stratus_video": {
        "name": "Stratus Video",
        "phone": "1-888-475-0049",
        "type": "video",
        "available": "24/7",
        "languages": 175
    }
}

# In-memory storage for interpreter requests/sessions
interpreter_requests: Dict[str, InterpreterRequest] = {}
interpreter_sessions: Dict[str, InterpreterSession] = {}
patient_language_preferences: Dict[str, LanguagePreference] = {}


@app.get("/api/v1/interpreter/languages")
async def get_supported_languages():
    """
    Get list of supported languages for interpreter services.
    """
    return {
        "languages": SUPPORTED_LANGUAGES,
        "total": len(SUPPORTED_LANGUAGES),
        "note": "Language codes follow ISO 639-1 standard. ASL is included for deaf/hard-of-hearing patients."
    }


@app.post("/api/v1/interpreter/request")
async def request_interpreter(
    patient_id: str,
    language: str,
    interpreter_type: str = "phone",
    urgency: str = "routine",
    estimated_duration: int = 30
):
    """
    Request interpreter services for a patient.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Language not supported: {language}")

    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=patient_id,
        details={"endpoint": "/api/v1/interpreter/request", "language": language}
    )

    request_id = str(uuid.uuid4())[:8]
    lang_info = SUPPORTED_LANGUAGES[language]

    request = InterpreterRequest(
        request_id=request_id,
        patient_id=patient_id,
        language=language,
        language_name=lang_info["name"],
        interpreter_type=InterpreterType(interpreter_type),
        urgency=urgency,
        estimated_duration=estimated_duration,
        requested_at=datetime.now(timezone.utc).isoformat(),
        status=InterpreterStatus.REQUESTED
    )

    interpreter_requests[request_id] = request

    # Get service info based on type
    service = None
    if interpreter_type == "phone":
        service = INTERPRETER_SERVICES.get("language_line")
    elif interpreter_type == "video":
        service = INTERPRETER_SERVICES.get("stratus_video")

    return {
        "request_id": request_id,
        "status": "requested",
        "language": lang_info["name"],
        "interpreter_type": interpreter_type,
        "urgency": urgency,
        "service": service,
        "message": f"Interpreter requested for {lang_info['name']}. {'Call service immediately.' if urgency == 'stat' else 'Service will connect shortly.'}"
    }


@app.post("/api/v1/interpreter/start-session")
async def start_interpreter_session(request_id: str):
    """
    Start an interpreter session after connection is established.
    """
    if request_id not in interpreter_requests:
        raise HTTPException(status_code=404, detail="Request not found")

    request = interpreter_requests[request_id]
    session_id = str(uuid.uuid4())[:8]

    session = InterpreterSession(
        session_id=session_id,
        request_id=request_id,
        patient_id=request.patient_id,
        language=request.language,
        interpreter_type=request.interpreter_type,
        start_time=datetime.now(timezone.utc).isoformat(),
        status=InterpreterStatus.IN_PROGRESS
    )

    interpreter_sessions[session_id] = session
    request.status = InterpreterStatus.IN_PROGRESS

    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=request.patient_id,
        details={"endpoint": "/api/v1/interpreter/start-session", "session_id": session_id}
    )

    return {
        "session_id": session_id,
        "status": "in_progress",
        "language": SUPPORTED_LANGUAGES[request.language]["name"],
        "start_time": session.start_time,
        "message": "Interpreter session started. Document topics covered."
    }


@app.post("/api/v1/interpreter/end-session")
async def end_interpreter_session(
    session_id: str,
    topics_covered: List[str] = [],
    patient_understanding_confirmed: bool = False
):
    """
    End an interpreter session and document for compliance.
    """
    if session_id not in interpreter_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = interpreter_sessions[session_id]
    end_time = datetime.now(timezone.utc)
    start_time = datetime.fromisoformat(session.start_time.replace('Z', '+00:00'))
    duration = int((end_time - start_time).total_seconds() / 60)

    session.end_time = end_time.isoformat()
    session.duration_minutes = duration
    session.topics_covered = topics_covered
    session.status = InterpreterStatus.COMPLETED

    # Update request status
    if session.request_id in interpreter_requests:
        interpreter_requests[session.request_id].status = InterpreterStatus.COMPLETED

    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=session.patient_id,
        details={
            "endpoint": "/api/v1/interpreter/end-session",
            "session_id": session_id,
            "duration_minutes": duration,
            "topics": topics_covered
        }
    )

    return {
        "session_id": session_id,
        "status": "completed",
        "duration_minutes": duration,
        "topics_covered": topics_covered,
        "patient_understanding_confirmed": patient_understanding_confirmed,
        "documentation": {
            "language": SUPPORTED_LANGUAGES[session.language]["name"],
            "interpreter_type": session.interpreter_type.value,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "duration": f"{duration} minutes",
            "compliance_note": "Interpreter services documented for Title VI compliance."
        }
    }


@app.get("/api/v1/interpreter/phrases/{language}")
async def get_clinical_phrases(language: str, category: Optional[str] = None):
    """
    Get pre-translated clinical phrases for a language.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=404, detail=f"Language not supported: {language}")

    phrases = CLINICAL_PHRASES.get(language, {})
    if not phrases:
        return {
            "language": SUPPORTED_LANGUAGES[language]["name"],
            "phrases": {},
            "note": "Detailed phrases not yet available for this language. Use interpreter service."
        }

    if category:
        if category not in phrases:
            raise HTTPException(status_code=404, detail=f"Category not found: {category}")
        return {
            "language": SUPPORTED_LANGUAGES[language]["name"],
            "category": category,
            "phrases": phrases[category]
        }

    return {
        "language": SUPPORTED_LANGUAGES[language]["name"],
        "categories": list(phrases.keys()),
        "phrases": phrases
    }


@app.post("/api/v1/interpreter/set-preference")
async def set_language_preference(
    patient_id: str,
    preferred_language: str,
    english_proficiency: str = "limited",
    reads_language: bool = True,
    interpreter_required: bool = True
):
    """
    Set patient's language preference.
    """
    if preferred_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Language not supported: {preferred_language}")

    lang_info = SUPPORTED_LANGUAGES[preferred_language]

    preference = LanguagePreference(
        preferred_language=preferred_language,
        preferred_language_name=lang_info["name"],
        english_proficiency=english_proficiency,
        reads_preferred_language=reads_language,
        interpreter_required=interpreter_required
    )

    patient_language_preferences[patient_id] = preference

    # Log HIPAA audit
    audit_logger.log(
        action=AuditAction.PHI_ACCESS,
        patient_id=patient_id,
        details={"endpoint": "/api/v1/interpreter/set-preference", "language": preferred_language}
    )

    return {
        "patient_id": patient_id,
        "language": lang_info["name"],
        "native_name": lang_info["native"],
        "english_proficiency": english_proficiency,
        "interpreter_required": interpreter_required,
        "message": f"Language preference set to {lang_info['name']}. {'Interpreter required for all encounters.' if interpreter_required else ''}"
    }


@app.get("/api/v1/interpreter/preference/{patient_id}")
async def get_language_preference(patient_id: str):
    """
    Get patient's language preference.
    """
    if patient_id not in patient_language_preferences:
        return {
            "patient_id": patient_id,
            "preference_set": False,
            "message": "No language preference recorded. Ask patient about preferred language."
        }

    pref = patient_language_preferences[patient_id]
    lang_info = SUPPORTED_LANGUAGES.get(pref.preferred_language, {})

    return {
        "patient_id": patient_id,
        "preference_set": True,
        "preferred_language": pref.preferred_language,
        "language_name": pref.preferred_language_name,
        "native_name": lang_info.get("native", ""),
        "english_proficiency": pref.english_proficiency,
        "interpreter_required": pref.interpreter_required,
        "reads_language": pref.reads_preferred_language
    }


@app.get("/api/v1/interpreter/services")
async def get_interpreter_services():
    """
    Get available interpreter service contact information.
    """
    return {
        "services": INTERPRETER_SERVICES,
        "note": "Contact your hospital's interpreter services department for in-person interpreters. These are backup phone/video services."
    }


@app.get("/api/v1/interpreter/compliance-checklist")
async def get_interpreter_compliance_checklist():
    """
    Get Title VI compliance checklist for interpreter use.
    """
    return {
        "title": "Title VI Language Access Compliance",
        "checklist": [
            {"item": "Offer interpreter at first contact", "required": True},
            {"item": "Document patient's preferred language", "required": True},
            {"item": "Use qualified interpreter, not family", "required": True, "note": "Family may be used only if patient declines and is documented"},
            {"item": "Document interpreter use in medical record", "required": True},
            {"item": "Provide translated vital documents", "required": True},
            {"item": "Post language access notices", "required": True},
            {"item": "Confirm patient understanding", "required": True}
        ],
        "family_interpreter_warning": "Using family members (especially children) as interpreters is discouraged due to privacy concerns, potential for omission/modification of information, and added emotional burden. Document if patient specifically requests family interpreter.",
        "documentation_required": [
            "Language identified",
            "Interpreter type (in-person, phone, video)",
            "Interpreter ID if available",
            "Session duration",
            "Topics discussed",
            "Patient understanding confirmed"
        ]
    }


@app.get("/api/v1/interpreter/vital-documents")
async def get_vital_documents_list():
    """
    Get list of vital documents that must be translated per Title VI.
    """
    return {
        "vital_documents": [
            "Consent forms (surgical, procedure, treatment)",
            "Complaint forms",
            "Intake forms with medical history",
            "Notices of eligibility and rights",
            "Discharge instructions",
            "Medication instructions",
            "Advance directives",
            "HIPAA privacy notices",
            "Financial assistance applications"
        ],
        "threshold": "Documents must be translated when language group exceeds 5% of population served or 1,000 individuals",
        "note": "Even if below threshold, meaningful access must still be provided through interpreter services"
    }


# ============ Medical Image Analysis (Feature #70) ============

async def generate_image_analysis_with_claude(request: ImageAnalysisRequest) -> ImageAnalysisResponse:
    """
    Generate medical image analysis using Claude Vision (claude-3-5-sonnet).

    Analyzes medical images (wounds, rashes, X-rays, etc.) for clinical findings,
    ICD-10 codes, recommendations, and red flags.

    Uses claude-3-5-sonnet-20241022 for vision capabilities.
    """
    import anthropic

    # Build context string
    context_parts = []
    if request.analysis_context:
        context_parts.append(f"Analysis type: {request.analysis_context}")
    if request.chief_complaint:
        context_parts.append(f"Chief complaint: {request.chief_complaint}")
    if request.patient_age:
        context_parts.append(f"Patient age: {request.patient_age}")
    if request.patient_gender:
        context_parts.append(f"Patient gender: {request.patient_gender}")

    context_str = "; ".join(context_parts) if context_parts else "General medical image"

    # Build the clinical prompt for image analysis
    system_prompt = """You are a clinical decision support AI analyzing medical images.
Your analysis is for clinical decision support only - NOT a diagnosis.

Provide structured analysis including:
1. Overall assessment (1-2 sentences)
2. Specific findings with confidence levels (high/moderate/low)
3. Relevant ICD-10 codes for documentation
4. Clinical recommendations for workup/treatment
5. Red flags requiring immediate attention
6. Differential considerations

Be thorough but concise. Focus on clinically actionable findings.
Always err on the side of caution with red flags."""

    user_prompt = f"""Analyze this medical image for clinical findings.

Context: {context_str}

Provide your analysis in the following JSON format:
{{
  "assessment": "Brief overall assessment",
  "findings": [
    {{
      "finding": "Description of finding",
      "confidence": "high|moderate|low",
      "location": "Anatomical location if applicable",
      "characteristics": ["characteristic1", "characteristic2"]
    }}
  ],
  "icd10_codes": [
    {{"code": "L03.90", "description": "Cellulitis, unspecified"}}
  ],
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "red_flags": ["Any urgent findings requiring immediate attention"],
  "differential_considerations": ["Other possible diagnoses to consider"]
}}

Respond ONLY with valid JSON."""

    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

        # Use claude-3-5-sonnet for vision (vision-capable model)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": request.media_type,
                                "data": request.image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        analysis_data = json.loads(response_text)

        # Build response
        findings = [
            ImageFinding(
                finding=f.get("finding", ""),
                confidence=f.get("confidence", "moderate"),
                location=f.get("location"),
                characteristics=f.get("characteristics", [])
            )
            for f in analysis_data.get("findings", [])
        ]

        return ImageAnalysisResponse(
            assessment=analysis_data.get("assessment", "Unable to assess image"),
            findings=findings,
            icd10_codes=analysis_data.get("icd10_codes", []),
            recommendations=analysis_data.get("recommendations", []),
            red_flags=analysis_data.get("red_flags", []),
            differential_considerations=analysis_data.get("differential_considerations", []),
            disclaimer="For clinical decision support only. Not a diagnosis. Clinical correlation required.",
            timestamp=datetime.now().isoformat()
        )

    except json.JSONDecodeError as e:
        # Return a basic response if parsing fails
        return ImageAnalysisResponse(
            assessment="Image analysis completed but response parsing failed",
            findings=[],
            icd10_codes=[],
            recommendations=["Please review image manually"],
            red_flags=[],
            differential_considerations=[],
            disclaimer="For clinical decision support only. Not a diagnosis.",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise Exception(f"Claude Vision API error: {str(e)}")


@app.post("/api/v1/image/analyze")
async def analyze_medical_image(request: ImageAnalysisRequest, req: Request):
    """
    Analyze a medical image using Claude Vision.

    Takes a base64-encoded image and optional context to generate:
    - Clinical assessment
    - Specific findings with confidence levels
    - ICD-10 codes for documentation
    - Recommendations for workup/treatment
    - Red flags requiring immediate attention
    - Differential considerations

    Supported media types: image/jpeg, image/png, image/webp
    Maximum image size: 15MB (20MB base64)

    Safety: For clinical decision support only - not a diagnosis.
    """
    # Validate image_base64 is present
    if not request.image_base64 or not request.image_base64.strip():
        raise HTTPException(status_code=400, detail="Image data is required")

    # Validate media type
    valid_media_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if request.media_type not in valid_media_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media type. Supported types: {', '.join(valid_media_types)}"
        )

    # Check base64 size (rough check - 15MB image = ~20MB base64)
    max_base64_size = 20 * 1024 * 1024  # 20MB
    if len(request.image_base64) > max_base64_size:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 15MB")

    # Audit log (no actual image data logged for HIPAA)
    ip_address = req.client.host if req.client else None
    audit_logger.log_note_operation(
        action=AuditAction.ANALYZE_IMAGE,
        note_type="IMAGE",
        status="processing",
        details=f"Context: {request.analysis_context or 'general'}, Patient: {request.patient_id or 'none'}",
        ip_address=ip_address
    )

    try:
        if not CLAUDE_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Image analysis requires Claude API key configuration"
            )

        # Generate analysis with Claude Vision
        analysis_response = await generate_image_analysis_with_claude(request)

        # Audit success
        audit_logger.log_note_operation(
            action=AuditAction.ANALYZE_IMAGE,
            note_type="IMAGE",
            status="success",
            details=f"Found {len(analysis_response.findings)} findings, {len(analysis_response.red_flags)} red flags",
            ip_address=ip_address
        )

        return analysis_response

    except HTTPException:
        raise
    except Exception as e:
        # Audit failure
        audit_logger.log_note_operation(
            action=AuditAction.ANALYZE_IMAGE,
            note_type="IMAGE",
            status="failure",
            details=str(e)[:100],
            ip_address=ip_address
        )
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


# ============ Billing/Claim Endpoints (Feature #71) ============

def build_fhir_claim(claim: dict) -> dict:
    """Build FHIR R4 Claim resource from internal claim model."""

    # Map diagnoses to FHIR format
    diagnoses = []
    for dx in claim.get("diagnoses", []):
        diagnoses.append({
            "sequence": dx.get("sequence", 1),
            "diagnosisCodeableConcept": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": dx.get("code"),
                    "display": dx.get("description")
                }]
            }
        })

    # Map service lines/procedures to FHIR items
    items = []
    for line in claim.get("service_lines", []):
        procedure = line.get("procedure", {})
        item = {
            "sequence": line.get("line_number", 1),
            "productOrService": {
                "coding": [{
                    "system": "http://www.ama-assn.org/go/cpt",
                    "code": procedure.get("code"),
                    "display": procedure.get("description")
                }]
            },
            "servicedDate": line.get("service_date"),
            "quantity": {"value": procedure.get("units", 1)},
            "diagnosisSequence": line.get("diagnosis_pointers", [1])
        }

        # Add modifiers if present
        if procedure.get("modifiers"):
            item["modifier"] = [
                {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": mod}]}
                for mod in procedure["modifiers"]
            ]

        items.append(item)

    return {
        "resourceType": "Claim",
        "status": "active",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                "code": "professional"
            }]
        },
        "use": "claim",
        "patient": {
            "reference": f"Patient/{claim.get('patient_id')}"
        },
        "created": claim.get("created_at", datetime.now().isoformat()),
        "provider": {
            "display": claim.get("provider_name", "Provider")
        },
        "priority": {"coding": [{"code": "normal"}]},
        "diagnosis": diagnoses,
        "item": items,
        "total": {
            "value": claim.get("total_charge", 0),
            "currency": "USD"
        }
    }


@app.post("/api/v1/billing/claims")
async def create_billing_claim(request: ClaimCreateRequest, req: Request):
    """
    Create a new billing claim.

    If note_id is provided, auto-populates ICD-10 and CPT codes from the saved note.
    Otherwise, uses manually provided codes.
    """
    claim_id = f"claim-{uuid.uuid4().hex[:8]}"
    ip_address = req.client.host if req.client else None

    # Initialize diagnosis and service line lists
    diagnoses = []
    service_lines = []

    # Auto-populate from note if provided
    if request.note_id and request.note_id in saved_notes:
        note = saved_notes[request.note_id]

        # Extract ICD-10 codes from note
        if "icd10_codes" in note:
            for i, code in enumerate(note["icd10_codes"], 1):
                diagnoses.append({
                    "code": code.get("code", ""),
                    "description": code.get("description", ""),
                    "sequence": i,
                    "is_principal": (i == 1)
                })

        # Extract CPT codes from note
        if "cpt_codes" in note:
            for i, code in enumerate(note["cpt_codes"], 1):
                service_lines.append({
                    "line_number": i,
                    "service_date": request.service_date,
                    "procedure": {
                        "code": code.get("code", ""),
                        "description": code.get("description", ""),
                        "modifiers": code.get("modifiers", []),
                        "units": 1
                    },
                    "diagnosis_pointers": [1]
                })

    # Manual codes override auto-populated ones
    if request.icd10_codes:
        diagnoses = []
        for i, code in enumerate(request.icd10_codes, 1):
            diagnoses.append({
                "code": code.get("code", ""),
                "description": code.get("description", ""),
                "sequence": i,
                "is_principal": (i == 1)
            })

    if request.cpt_codes:
        service_lines = []
        for i, code in enumerate(request.cpt_codes, 1):
            service_lines.append({
                "line_number": i,
                "service_date": request.service_date,
                "procedure": {
                    "code": code.get("code", ""),
                    "description": code.get("description", ""),
                    "modifiers": code.get("modifiers", []),
                    "units": 1
                },
                "diagnosis_pointers": [1]
            })

    # Build claim
    claim = {
        "claim_id": claim_id,
        "status": ClaimStatus.DRAFT.value,
        "patient_id": request.patient_id,
        "patient_name": "",
        "note_id": request.note_id,
        "service_date": request.service_date,
        "provider_name": request.provider_name,
        "provider_npi": request.provider_npi,
        "diagnoses": diagnoses,
        "service_lines": service_lines,
        "total_charge": 0.0,
        "created_at": datetime.now().isoformat(),
        "submitted_at": None,
        "fhir_claim_id": None
    }

    billing_claims[claim_id] = claim

    # HIPAA Audit
    audit_logger.log_note_operation(
        action=AuditAction.CREATE_CLAIM,
        note_id=request.note_id,
        patient_id=request.patient_id,
        status="success",
        details=f"Claim {claim_id} created with {len(diagnoses)} diagnoses, {len(service_lines)} procedures",
        ip_address=ip_address
    )

    return {"success": True, "claim_id": claim_id, "claim": claim}


@app.get("/api/v1/billing/claims/{claim_id}")
async def get_billing_claim(claim_id: str, req: Request):
    """Get a specific billing claim by ID."""
    if claim_id not in billing_claims:
        raise HTTPException(status_code=404, detail="Claim not found")

    ip_address = req.client.host if req.client else None
    claim = billing_claims[claim_id]

    audit_logger.log_note_operation(
        action=AuditAction.VIEW_CLAIM,
        patient_id=claim.get("patient_id"),
        status="success",
        details=f"Viewed claim {claim_id}",
        ip_address=ip_address
    )

    return {"success": True, "claim": claim}


@app.put("/api/v1/billing/claims/{claim_id}")
async def update_billing_claim(claim_id: str, request: ClaimUpdateRequest, req: Request):
    """Update/edit claim codes before submission."""
    if claim_id not in billing_claims:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim = billing_claims[claim_id]
    ip_address = req.client.host if req.client else None

    # Only allow edits on draft claims
    if claim["status"] != ClaimStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Cannot edit submitted claim")

    # Update diagnoses if provided
    if request.diagnoses is not None:
        claim["diagnoses"] = [d.model_dump() for d in request.diagnoses]

    # Update service lines if provided
    if request.service_lines is not None:
        claim["service_lines"] = [s.model_dump() for s in request.service_lines]

    billing_claims[claim_id] = claim

    audit_logger.log_note_operation(
        action=AuditAction.UPDATE_CLAIM,
        patient_id=claim.get("patient_id"),
        status="success",
        details=f"Updated claim {claim_id}",
        ip_address=ip_address
    )

    return {"success": True, "claim": claim}


@app.delete("/api/v1/billing/claims/{claim_id}")
async def delete_billing_claim(claim_id: str, req: Request):
    """Delete a draft billing claim."""
    if claim_id not in billing_claims:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim = billing_claims[claim_id]

    # Only allow deletion of draft claims
    if claim["status"] != ClaimStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Cannot delete submitted claim")

    del billing_claims[claim_id]

    return {"success": True, "message": f"Claim {claim_id} deleted"}


@app.post("/api/v1/billing/claims/{claim_id}/submit")
async def submit_billing_claim(claim_id: str, request: ClaimSubmitRequest, req: Request):
    """
    Submit claim to payer via FHIR Claim resource.

    Requires confirmation=True to prevent accidental submissions.
    """
    if not request.confirm:
        return {
            "success": False,
            "error": "Confirmation required",
            "message": "Set confirm=true to submit claim"
        }

    if claim_id not in billing_claims:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim = billing_claims[claim_id]
    ip_address = req.client.host if req.client else None

    # Validate claim has required data
    if not claim.get("diagnoses"):
        raise HTTPException(status_code=400, detail="Claim requires at least one diagnosis")
    if not claim.get("service_lines"):
        raise HTTPException(status_code=400, detail="Claim requires at least one procedure")

    # Build FHIR Claim resource
    fhir_claim = build_fhir_claim(claim)

    # Attempt to push to EHR (simulated for sandbox)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CERNER_BASE_URL}/Claim",
                json=fhir_claim,
                headers={"Content-Type": "application/fhir+json"}
            )

            if response.status_code == 201:
                fhir_id = response.json().get("id", f"sim-{claim_id}")
                result = {"success": True, "fhir_id": fhir_id, "simulated": False}
            elif response.status_code == 403:
                # Read-only sandbox - simulate success
                fhir_id = f"sim-{claim_id}"
                result = {"success": True, "fhir_id": fhir_id, "simulated": True}
            else:
                result = {"success": False, "error": f"EHR returned {response.status_code}"}

    except Exception as e:
        # Simulate success on error (sandbox limitation)
        fhir_id = f"sim-{claim_id}"
        result = {"success": True, "fhir_id": fhir_id, "simulated": True, "note": str(e)[:50]}

    # Update claim status
    claim["status"] = ClaimStatus.SUBMITTED.value
    claim["submitted_at"] = datetime.now().isoformat()
    if result.get("fhir_id"):
        claim["fhir_claim_id"] = result["fhir_id"]

    billing_claims[claim_id] = claim

    # HIPAA Audit
    audit_logger.log_note_operation(
        action=AuditAction.SUBMIT_CLAIM,
        patient_id=claim.get("patient_id"),
        status="success" if result.get("success") else "failure",
        details=f"Claim {claim_id} submitted, FHIR ID: {result.get('fhir_id', 'N/A')}",
        ip_address=ip_address
    )

    return {
        "success": True,
        "claim_id": claim_id,
        "status": claim["status"],
        "fhir_claim_id": claim.get("fhir_claim_id"),
        "submission_response": result
    }


@app.get("/api/v1/billing/claims")
async def list_billing_claims(
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """List billing claims with optional filtering."""
    claims_list = []

    for claim_id, claim in billing_claims.items():
        # Filter by patient_id if provided
        if patient_id and claim.get("patient_id") != patient_id:
            continue

        # Filter by status if provided
        if status and claim.get("status") != status:
            continue

        claims_list.append(claim)

        if len(claims_list) >= limit:
            break

    return {"success": True, "claims": claims_list, "count": len(claims_list)}


@app.get("/api/v1/patient/{patient_id}/claims")
async def get_patient_claims(patient_id: str):
    """Get all billing claims for a specific patient."""
    patient_claims = [
        claim for claim in billing_claims.values()
        if claim.get("patient_id") == patient_id
    ]

    return {"success": True, "claims": patient_claims, "count": len(patient_claims)}


@app.get("/api/v1/billing/codes/icd10/search")
async def search_icd10_codes(q: str, limit: int = 20):
    """Search ICD-10 codes by keyword or code prefix."""
    results = []
    q_lower = q.lower()

    # Search in keyword mappings
    for keyword, code in ICD10_DB.get("keywords", {}).items():
        if q_lower in keyword.lower() and len(results) < limit:
            # Get description from codes
            for category, codes in ICD10_DB.get("codes", {}).items():
                if code in codes:
                    if not any(r["code"] == code for r in results):
                        results.append({
                            "code": code,
                            "description": codes[code],
                            "category": category,
                            "match_type": "keyword"
                        })
                    break

    # Search in code values
    for category, codes in ICD10_DB.get("codes", {}).items():
        for code, description in codes.items():
            if len(results) >= limit:
                break
            if q_lower in code.lower() or q_lower in description.lower():
                if not any(r["code"] == code for r in results):
                    results.append({
                        "code": code,
                        "description": description,
                        "category": category,
                        "match_type": "code"
                    })

    return {"query": q, "results": results[:limit], "count": len(results[:limit])}


@app.get("/api/v1/billing/codes/cpt/search")
async def search_cpt_codes(q: str, limit: int = 20):
    """Search CPT codes by keyword or code prefix."""
    results = []
    q_lower = q.lower()

    # Search in keyword mappings
    for keyword, code in CPT_DB.get("keywords", {}).items():
        if q_lower in keyword.lower() and len(results) < limit:
            for category, codes in CPT_DB.get("codes", {}).items():
                if code in codes:
                    if not any(r["code"] == code for r in results):
                        results.append({
                            "code": code,
                            "description": codes[code],
                            "category": category,
                            "match_type": "keyword"
                        })
                    break

    # Search in code values
    for category, codes in CPT_DB.get("codes", {}).items():
        for code, description in codes.items():
            if len(results) >= limit:
                break
            if q_lower in code.lower() or q_lower in description.lower():
                if not any(r["code"] == code for r in results):
                    results.append({
                        "code": code,
                        "description": description,
                        "category": category,
                        "match_type": "code"
                    })

    return {"query": q, "results": results[:limit], "count": len(results[:limit])}


@app.get("/api/v1/billing/claims/{claim_id}/fhir")
async def get_claim_fhir(claim_id: str):
    """Get FHIR Claim resource representation."""
    if claim_id not in billing_claims:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim = billing_claims[claim_id]
    fhir_claim = build_fhir_claim(claim)

    return fhir_claim


# ============ DNFB (Discharged Not Final Billed) Endpoints (Feature #72) ============

def calculate_aging(discharge_date: str) -> tuple:
    """Calculate days since discharge and aging bucket."""
    try:
        discharge = datetime.fromisoformat(discharge_date.replace("Z", "+00:00"))
        if discharge.tzinfo is None:
            discharge = discharge.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = (now - discharge).days

        if days <= 3:
            bucket = "0-3"
        elif days <= 7:
            bucket = "4-7"
        elif days <= 14:
            bucket = "8-14"
        elif days <= 30:
            bucket = "15-30"
        else:
            bucket = "31+"

        return days, bucket
    except Exception:
        return 0, "0-3"


@app.post("/api/v1/dnfb")
async def create_dnfb_account(request: DNFBCreateRequest, req: Request):
    """
    Add account to DNFB worklist.

    Tracks discharged patients with unbilled accounts for revenue cycle management.
    """
    dnfb_id = f"dnfb-{uuid.uuid4().hex[:8]}"
    days, bucket = calculate_aging(request.discharge_date)

    account = {
        "dnfb_id": dnfb_id,
        "patient_id": request.patient_id,
        "patient_name": request.patient_name,
        "mrn": request.mrn,
        "encounter_id": request.encounter_id,
        "discharge_date": request.discharge_date,
        "service_type": request.service_type,
        "principal_diagnosis": request.principal_diagnosis,
        "attending_physician": request.attending_physician,
        "estimated_charges": request.estimated_charges,
        "reason": request.reason.value,
        "reason_detail": request.reason_detail,
        "prior_auth": None,
        "days_since_discharge": days,
        "aging_bucket": bucket,
        "assigned_coder": None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "notes": [],
        "is_resolved": False,
        "resolved_date": None,
        "claim_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    dnfb_accounts[dnfb_id] = account

    # Audit log
    audit_logger.log_note_operation(
        action=AuditAction.VIEW_CLAIM,  # Reusing billing audit
        patient_id=request.patient_id,
        status="success",
        details=f"DNFB account {dnfb_id} created, reason: {request.reason.value}",
        ip_address=req.client.host if req.client else None
    )

    return {"success": True, "dnfb": account}


@app.get("/api/v1/dnfb")
async def list_dnfb_accounts(
    reason: Optional[str] = None,
    aging: Optional[str] = None,
    prior_auth_issue: Optional[bool] = None,
    limit: int = 50
):
    """
    List DNFB accounts with optional filters.

    Filters:
    - reason: coding_incomplete, documentation_missing, prior_auth_missing, etc.
    - aging: 0-3, 4-7, 8-14, 15-30, 31+
    - prior_auth_issue: true to show only prior auth problems
    """
    accounts = []

    for dnfb_id, account in dnfb_accounts.items():
        if account.get("is_resolved"):
            continue

        # Recalculate aging
        days, bucket = calculate_aging(account["discharge_date"])
        account["days_since_discharge"] = days
        account["aging_bucket"] = bucket

        # Apply filters
        if reason and account.get("reason") != reason:
            continue
        if aging and account.get("aging_bucket") != aging:
            continue
        if prior_auth_issue:
            acc_reason = account.get("reason", "")
            if "prior_auth" not in acc_reason:
                continue

        accounts.append(account)

    # Sort by days since discharge (oldest first)
    accounts.sort(key=lambda x: x.get("days_since_discharge", 0), reverse=True)

    # Calculate summary stats
    total_charges = sum(a.get("estimated_charges", 0) for a in accounts)
    by_reason = {}
    by_aging = {}
    prior_auth_count = 0

    for a in accounts:
        r = a.get("reason", "other")
        by_reason[r] = by_reason.get(r, 0) + 1
        b = a.get("aging_bucket", "0-3")
        by_aging[b] = by_aging.get(b, 0) + 1
        if "prior_auth" in r:
            prior_auth_count += 1

    return {
        "accounts": accounts[:limit],
        "total_count": len(accounts),
        "total_estimated_charges": total_charges,
        "prior_auth_issues": prior_auth_count,
        "by_reason": by_reason,
        "by_aging": by_aging
    }


@app.get("/api/v1/dnfb/summary")
async def get_dnfb_summary():
    """
    Get DNFB dashboard summary metrics.

    Returns aggregate stats for revenue cycle management.
    """
    active_accounts = [a for a in dnfb_accounts.values() if not a.get("is_resolved")]

    # Recalculate aging for all accounts
    for account in active_accounts:
        days, bucket = calculate_aging(account["discharge_date"])
        account["days_since_discharge"] = days
        account["aging_bucket"] = bucket

    total_charges = sum(a.get("estimated_charges", 0) for a in active_accounts)

    # Group by reason
    by_reason = {}
    for a in active_accounts:
        r = a.get("reason", "other")
        if r not in by_reason:
            by_reason[r] = {"count": 0, "charges": 0}
        by_reason[r]["count"] += 1
        by_reason[r]["charges"] += a.get("estimated_charges", 0)

    # Group by aging bucket
    by_aging = {}
    for a in active_accounts:
        b = a.get("aging_bucket", "0-3")
        if b not in by_aging:
            by_aging[b] = {"count": 0, "charges": 0}
        by_aging[b]["count"] += 1
        by_aging[b]["charges"] += a.get("estimated_charges", 0)

    # Prior auth specific stats
    prior_auth_issues = [a for a in active_accounts if "prior_auth" in a.get("reason", "")]
    prior_auth_charges = sum(a.get("estimated_charges", 0) for a in prior_auth_issues)

    # Average days
    if active_accounts:
        avg_days = sum(a.get("days_since_discharge", 0) for a in active_accounts) / len(active_accounts)
    else:
        avg_days = 0

    return {
        "total_accounts": len(active_accounts),
        "total_estimated_charges": total_charges,
        "average_days_unbilled": round(avg_days, 1),
        "prior_auth_issues": {
            "count": len(prior_auth_issues),
            "charges": prior_auth_charges
        },
        "by_reason": by_reason,
        "by_aging": by_aging,
        "aging_over_7_days": sum(1 for a in active_accounts if a.get("days_since_discharge", 0) > 7),
        "aging_over_14_days": sum(1 for a in active_accounts if a.get("days_since_discharge", 0) > 14)
    }


@app.get("/api/v1/dnfb/{dnfb_id}")
async def get_dnfb_account(dnfb_id: str):
    """Get specific DNFB account details."""
    if dnfb_id not in dnfb_accounts:
        raise HTTPException(status_code=404, detail="DNFB account not found")

    account = dnfb_accounts[dnfb_id]

    # Recalculate aging
    days, bucket = calculate_aging(account["discharge_date"])
    account["days_since_discharge"] = days
    account["aging_bucket"] = bucket

    return {"dnfb": account}


@app.put("/api/v1/dnfb/{dnfb_id}")
async def update_dnfb_account(dnfb_id: str, request: DNFBUpdateRequest, req: Request):
    """Update DNFB account status, reason, or notes."""
    if dnfb_id not in dnfb_accounts:
        raise HTTPException(status_code=404, detail="DNFB account not found")

    account = dnfb_accounts[dnfb_id]

    if request.reason is not None:
        account["reason"] = request.reason.value
    if request.reason_detail is not None:
        account["reason_detail"] = request.reason_detail
    if request.assigned_coder is not None:
        account["assigned_coder"] = request.assigned_coder
    if request.notes is not None:
        account["notes"] = request.notes
    if request.prior_auth is not None:
        account["prior_auth"] = request.prior_auth.model_dump()
    if request.is_resolved is not None:
        account["is_resolved"] = request.is_resolved
        if request.is_resolved:
            account["resolved_date"] = datetime.now(timezone.utc).isoformat()

    account["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Audit log
    audit_logger.log_note_operation(
        action=AuditAction.UPDATE_CLAIM,
        patient_id=account.get("patient_id"),
        status="success",
        details=f"DNFB {dnfb_id} updated",
        ip_address=req.client.host if req.client else None
    )

    return {"success": True, "dnfb": account}


@app.post("/api/v1/dnfb/{dnfb_id}/prior-auth")
async def add_prior_auth(dnfb_id: str, request: PriorAuthRequest, req: Request):
    """Add or update prior authorization info for DNFB account."""
    if dnfb_id not in dnfb_accounts:
        raise HTTPException(status_code=404, detail="DNFB account not found")

    account = dnfb_accounts[dnfb_id]

    prior_auth = {
        "auth_number": request.auth_number,
        "status": request.status.value,
        "payer_name": request.payer_name,
        "procedure_codes": request.procedure_codes,
        "requested_date": request.requested_date,
        "approval_date": request.approval_date,
        "expiration_date": request.expiration_date,
        "approved_units": request.approved_units,
        "used_units": 0,
        "denial_reason": request.denial_reason
    }

    account["prior_auth"] = prior_auth
    account["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Update reason based on prior auth status
    if request.status == PriorAuthStatus.DENIED:
        account["reason"] = DNFBReason.PRIOR_AUTH_DENIED.value
    elif request.status == PriorAuthStatus.EXPIRED:
        account["reason"] = DNFBReason.PRIOR_AUTH_EXPIRED.value
    elif request.status == PriorAuthStatus.NOT_OBTAINED:
        account["reason"] = DNFBReason.PRIOR_AUTH_MISSING.value
    elif request.status == PriorAuthStatus.APPROVED:
        # If prior auth was the only issue, may need to update reason
        if "prior_auth" in account.get("reason", ""):
            account["reason"] = DNFBReason.CODING_INCOMPLETE.value

    # Audit log
    audit_logger.log_note_operation(
        action=AuditAction.UPDATE_CLAIM,
        patient_id=account.get("patient_id"),
        status="success",
        details=f"Prior auth {request.status.value} added to DNFB {dnfb_id}",
        ip_address=req.client.host if req.client else None
    )

    return {"success": True, "dnfb": account}


@app.post("/api/v1/dnfb/{dnfb_id}/resolve")
async def resolve_dnfb(dnfb_id: str, claim_id: Optional[str] = None, req: Request = None):
    """Mark DNFB account as resolved (billed)."""
    if dnfb_id not in dnfb_accounts:
        raise HTTPException(status_code=404, detail="DNFB account not found")

    account = dnfb_accounts[dnfb_id]
    account["is_resolved"] = True
    account["resolved_date"] = datetime.now(timezone.utc).isoformat()
    if claim_id:
        account["claim_id"] = claim_id

    # Audit log
    audit_logger.log_note_operation(
        action=AuditAction.SUBMIT_CLAIM,
        patient_id=account.get("patient_id"),
        status="success",
        details=f"DNFB {dnfb_id} resolved, claim: {claim_id or 'N/A'}",
        ip_address=req.client.host if req and req.client else None
    )

    return {"success": True, "dnfb": account}


@app.get("/api/v1/patient/{patient_id}/dnfb")
async def get_patient_dnfb(patient_id: str):
    """Get DNFB accounts for a specific patient."""
    patient_accounts = [
        a for a in dnfb_accounts.values()
        if a.get("patient_id") == patient_id
    ]

    # Recalculate aging
    for account in patient_accounts:
        days, bucket = calculate_aging(account["discharge_date"])
        account["days_since_discharge"] = days
        account["aging_bucket"] = bucket

    return {
        "patient_id": patient_id,
        "accounts": patient_accounts,
        "active_count": sum(1 for a in patient_accounts if not a.get("is_resolved")),
        "total_unbilled_charges": sum(
            a.get("estimated_charges", 0) for a in patient_accounts if not a.get("is_resolved")
        )
    }


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


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD WRITE-BACK REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class VitalWriteRequest(BaseModel):
    """Request model for pushing vitals to EHR as FHIR Observation"""
    patient_id: str
    vital_type: str  # blood_pressure, heart_rate, temperature, respiratory_rate, oxygen_saturation, weight, height, pain_level
    value: str
    unit: str
    systolic: Optional[int] = None  # For blood pressure
    diastolic: Optional[int] = None  # For blood pressure
    effective_datetime: str = ""
    performer_name: str = ""
    device_type: str = "AR_GLASSES"


class OrderWriteRequest(BaseModel):
    """Request model for pushing orders to EHR as FHIR ServiceRequest or MedicationRequest"""
    patient_id: str
    order_type: str  # LAB, IMAGING, MEDICATION
    code: str  # CPT code or RxNorm code
    display_name: str
    status: str = "active"
    intent: str = "order"
    priority: str = "routine"  # routine, urgent, stat
    # Lab/Imaging specific
    body_site: Optional[str] = None
    laterality: Optional[str] = None  # left, right, bilateral
    contrast: Optional[bool] = None
    # Medication specific
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    prn: bool = False
    requester_name: str = ""
    notes: str = ""


class AllergyWriteRequest(BaseModel):
    """Request model for pushing allergies to EHR as FHIR AllergyIntolerance"""
    patient_id: str
    substance: str
    reaction_type: str = "allergy"  # allergy or intolerance
    criticality: str = "unable-to-assess"  # low, high, unable-to-assess
    category: str = "medication"  # food, medication, environment, biologic
    onset_datetime: str = ""
    recorder_name: str = ""
    reactions: List[str] = []  # List of reaction manifestations


class MedicationUpdateRequest(BaseModel):
    """Request model for updating medication status (HIPAA-compliant soft delete)"""
    patient_id: str
    medication_id: str  # FHIR resource ID
    new_status: str  # active, on-hold, cancelled, stopped, completed, entered-in-error
    reason: str = ""
    performer_name: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR CODE MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════════

# LOINC codes for vital signs
VITAL_LOINC_CODES = {
    "blood_pressure": {"panel": "85354-9", "systolic": "8480-6", "diastolic": "8462-4", "display": "Blood pressure panel"},
    "heart_rate": {"code": "8867-4", "display": "Heart rate"},
    "temperature": {"code": "8310-5", "display": "Body temperature"},
    "respiratory_rate": {"code": "9279-1", "display": "Respiratory rate"},
    "oxygen_saturation": {"code": "2708-6", "display": "Oxygen saturation"},
    "weight": {"code": "29463-7", "display": "Body weight"},
    "height": {"code": "8302-2", "display": "Body height"},
    "pain_level": {"code": "72514-3", "display": "Pain severity - 0-10 verbal numeric rating"}
}

# Common lab order CPT codes
LAB_CPT_CODES = {
    "cbc": {"code": "85025", "display": "Complete Blood Count with Differential"},
    "cmp": {"code": "80053", "display": "Comprehensive Metabolic Panel"},
    "bmp": {"code": "80048", "display": "Basic Metabolic Panel"},
    "ua": {"code": "81003", "display": "Urinalysis"},
    "lipid": {"code": "80061", "display": "Lipid Panel"},
    "tsh": {"code": "84443", "display": "Thyroid Stimulating Hormone"},
    "a1c": {"code": "83036", "display": "Hemoglobin A1c"},
    "pt_inr": {"code": "85610", "display": "Prothrombin Time/INR"},
    "troponin": {"code": "84484", "display": "Troponin"},
    "bnp": {"code": "83880", "display": "BNP"},
    "d_dimer": {"code": "85379", "display": "D-Dimer"},
    "blood_culture": {"code": "87040", "display": "Blood Culture"}
}

# Common imaging CPT codes
IMAGING_CPT_CODES = {
    "chest_xray": {"code": "71046", "display": "Chest X-Ray 2 Views"},
    "ct_head": {"code": "70450", "display": "CT Head without Contrast"},
    "ct_head_contrast": {"code": "70460", "display": "CT Head with Contrast"},
    "ct_chest": {"code": "71250", "display": "CT Chest without Contrast"},
    "ct_chest_contrast": {"code": "71260", "display": "CT Chest with Contrast"},
    "ct_abdomen": {"code": "74150", "display": "CT Abdomen without Contrast"},
    "ct_abdomen_contrast": {"code": "74160", "display": "CT Abdomen with Contrast"},
    "mri_brain": {"code": "70551", "display": "MRI Brain without Contrast"},
    "mri_spine": {"code": "72141", "display": "MRI Cervical Spine without Contrast"},
    "echo": {"code": "93306", "display": "Echocardiogram Complete"},
    "ultrasound_abdomen": {"code": "76700", "display": "Ultrasound Abdomen Complete"},
    "xray_extremity": {"code": "73030", "display": "X-Ray Extremity"}
}


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR RESOURCE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_observation(vital: dict, patient_id: str) -> dict:
    """
    Build FHIR R4 Observation resource from captured vital.
    Follows HL7 FHIR R4 Observation vital-signs profile.
    """
    vital_type = vital.get("vital_type", "").lower().replace(" ", "_")
    loinc = VITAL_LOINC_CODES.get(vital_type, {})

    timestamp = vital.get("effective_datetime") or datetime.now().isoformat() + "Z"
    if not timestamp.endswith("Z") and "+" not in timestamp:
        timestamp = timestamp + "Z"

    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": loinc.get("code", loinc.get("panel", "")),
                "display": loinc.get("display", vital_type.replace("_", " ").title())
            }]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": timestamp
    }

    # Handle blood pressure specially (component-based observation)
    if vital_type == "blood_pressure":
        observation["code"]["coding"][0]["code"] = VITAL_LOINC_CODES["blood_pressure"]["panel"]
        observation["component"] = [
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": VITAL_LOINC_CODES["blood_pressure"]["systolic"],
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": vital.get("systolic", 0),
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": VITAL_LOINC_CODES["blood_pressure"]["diastolic"],
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": vital.get("diastolic", 0),
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    else:
        # Standard single-value vital
        try:
            numeric_value = float(vital.get("value", "0").replace(",", ""))
        except ValueError:
            numeric_value = 0

        observation["valueQuantity"] = {
            "value": numeric_value,
            "unit": vital.get("unit", ""),
            "system": "http://unitsofmeasure.org"
        }

    # Add performer if provided
    if vital.get("performer_name"):
        observation["performer"] = [{"display": vital["performer_name"]}]

    # Add device info
    if vital.get("device_type"):
        observation["device"] = {"display": vital["device_type"]}

    return observation


def build_service_request(order: dict, patient_id: str) -> dict:
    """
    Build FHIR R4 ServiceRequest resource from captured order.
    Used for lab and imaging orders.
    """
    order_type = order.get("order_type", "LAB").upper()
    display_name = order.get("display_name", "")

    # Get CPT code
    code_db = LAB_CPT_CODES if order_type == "LAB" else IMAGING_CPT_CODES
    code_key = display_name.lower().replace(" ", "_").replace("-", "_")
    cpt_info = code_db.get(code_key, {"code": order.get("code", ""), "display": display_name})

    service_request = {
        "resourceType": "ServiceRequest",
        "status": order.get("status", "active"),
        "intent": order.get("intent", "order"),
        "priority": order.get("priority", "routine"),
        "code": {
            "coding": [{
                "system": "http://www.ama-assn.org/go/cpt",
                "code": cpt_info.get("code", ""),
                "display": cpt_info.get("display", display_name)
            }]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "authoredOn": datetime.now().isoformat() + "Z"
    }

    # Add requester
    if order.get("requester_name"):
        service_request["requester"] = {"display": order["requester_name"]}

    # Add body site for imaging
    if order.get("body_site"):
        service_request["bodySite"] = [{"text": order["body_site"]}]

    # Add laterality
    if order.get("laterality"):
        service_request["bodySite"] = service_request.get("bodySite", [{}])
        service_request["bodySite"][0]["coding"] = [{
            "system": "http://snomed.info/sct",
            "display": order["laterality"]
        }]

    # Add notes
    if order.get("notes"):
        service_request["note"] = [{"text": order["notes"]}]

    # Add contrast modifier for imaging
    if order.get("contrast") is not None:
        contrast_note = "With contrast" if order["contrast"] else "Without contrast"
        if "note" in service_request:
            service_request["note"].append({"text": contrast_note})
        else:
            service_request["note"] = [{"text": contrast_note}]

    return service_request


def build_medication_request(med: dict, patient_id: str) -> dict:
    """
    Build FHIR R4 MedicationRequest resource from captured medication order.
    """
    medication_request = {
        "resourceType": "MedicationRequest",
        "status": med.get("status", "active"),
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": med.get("code", ""),
                "display": med.get("display_name", "")
            }],
            "text": med.get("display_name", "")
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "authoredOn": datetime.now().isoformat() + "Z"
    }

    # Add requester
    if med.get("requester_name"):
        medication_request["requester"] = {"display": med["requester_name"]}

    # Build dosage instruction
    dosage_text_parts = []
    if med.get("dose"):
        dosage_text_parts.append(med["dose"])
    if med.get("frequency"):
        dosage_text_parts.append(med["frequency"])
    if med.get("duration"):
        dosage_text_parts.append(f"for {med['duration']}")

    dosage_instruction = {
        "text": " ".join(dosage_text_parts) if dosage_text_parts else "As directed"
    }

    if med.get("route"):
        dosage_instruction["route"] = {
            "coding": [{
                "system": "http://snomed.info/sct",
                "display": med["route"]
            }]
        }

    if med.get("prn"):
        dosage_instruction["asNeededBoolean"] = True

    medication_request["dosageInstruction"] = [dosage_instruction]

    # Add notes
    if med.get("notes"):
        medication_request["note"] = [{"text": med["notes"]}]

    return medication_request


def build_allergy_intolerance(allergy: dict, patient_id: str) -> dict:
    """
    Build FHIR R4 AllergyIntolerance resource from captured allergy.
    """
    timestamp = allergy.get("onset_datetime") or datetime.now().isoformat() + "Z"
    if not timestamp.endswith("Z") and "+" not in timestamp:
        timestamp = timestamp + "Z"

    allergy_resource = {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code": "active",
                "display": "Active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                "code": "confirmed",
                "display": "Confirmed"
            }]
        },
        "type": allergy.get("reaction_type", "allergy"),
        "category": [allergy.get("category", "medication")],
        "criticality": allergy.get("criticality", "unable-to-assess"),
        "code": {
            "text": allergy.get("substance", "Unknown substance")
        },
        "patient": {"reference": f"Patient/{patient_id}"},
        "recordedDate": timestamp
    }

    # Add recorder
    if allergy.get("recorder_name"):
        allergy_resource["recorder"] = {"display": allergy["recorder_name"]}

    # Add reactions
    if allergy.get("reactions"):
        allergy_resource["reaction"] = [{
            "manifestation": [{"coding": [{"display": r}]} for r in allergy["reactions"]]
        }]

    return allergy_resource


async def push_resource_to_ehr(resource_type: str, resource: dict) -> dict:
    """
    Generic FHIR resource POST to EHR with graceful 403 handling.
    Returns result dict with success status and FHIR ID if created.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CERNER_BASE_URL}/{resource_type}",
                json=resource,
                headers={
                    "Content-Type": "application/fhir+json",
                    "Accept": "application/fhir+json"
                }
            )

            if response.status_code == 201:
                result = response.json()
                fhir_id = result.get("id", "")
                return {
                    "success": True,
                    "fhir_id": fhir_id,
                    "resource_type": resource_type,
                    "ehr_url": f"{CERNER_BASE_URL}/{resource_type}/{fhir_id}"
                }
            elif response.status_code == 403:
                # Cerner sandbox is read-only - return simulated success
                return {
                    "success": True,
                    "simulated": True,
                    "resource_type": resource_type,
                    "message": "EHR sandbox is read-only - resource validated but not persisted",
                    "status_code": 403
                }
            else:
                error_body = response.text
                return {
                    "success": False,
                    "error": f"EHR returned status {response.status_code}",
                    "status_code": response.status_code,
                    "details": error_body[:500]
                }
    except httpx.TimeoutException:
        return {"success": False, "error": "EHR request timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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

        # HIPAA Audit: Log note save
        audit_logger.log_note_operation(
            action=AuditAction.SAVE_NOTE,
            note_id=note_id,
            patient_id=request.patient_id,
            note_type=request.note_type,
            status="success",
            details=f"length={len(request.display_text)}",
            signed_by=request.signed_by,
            was_edited=request.was_edited
        )

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
async def get_saved_note(note_id: str, request: Request):
    """Retrieve a saved note by ID"""
    if note_id in saved_notes:
        note = saved_notes[note_id]

        # HIPAA Audit: Log note retrieval
        ip_address = request.client.host if request.client else None
        audit_logger.log_note_operation(
            action=AuditAction.VIEW_NOTES,
            note_id=note_id,
            patient_id=note.get("patient_id"),
            note_type=note.get("note_type"),
            status="success",
            ip_address=ip_address
        )

        return note
    raise HTTPException(status_code=404, detail="Note not found")


@app.get("/api/v1/patient/{patient_id}/notes")
async def get_patient_notes(patient_id: str, request: Request):
    """Get all saved notes for a patient"""
    patient_notes = [
        note for note in saved_notes.values()
        if note["patient_id"] == patient_id
    ]

    # HIPAA Audit: Log notes list access
    ip_address = request.client.host if request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.VIEW_NOTES,
        patient_id=patient_id,
        endpoint=f"/api/v1/patient/{patient_id}/notes",
        status="success",
        details=f"retrieved {len(patient_notes)} notes",
        ip_address=ip_address
    )

    return {
        "patient_id": patient_id,
        "count": len(patient_notes),
        "notes": patient_notes
    }


@app.post("/api/v1/notes/{note_id}/push")
async def push_note_endpoint(note_id: str, request: Request, x_device_id: Optional[str] = Header(None)):
    """
    Push a saved note to the EHR as a FHIR DocumentReference.

    This creates a DocumentReference in the EHR containing the note content.
    Note: Cerner sandbox is read-only, so this will return 403 until
    production credentials are configured.

    Feature #77: Requires fresh voiceprint verification if X-Device-ID header is present.
    """
    # Feature #77: Check continuous auth if device_id provided
    if x_device_id:
        await require_fresh_voiceprint(x_device_id)

    result = await push_note_to_ehr(note_id)

    if not result.get("success") and result.get("error") == "Note not found":
        raise HTTPException(status_code=404, detail="Note not found")

    # HIPAA Audit: Log push attempt
    note = saved_notes.get(note_id, {})
    ip_address = request.client.host if request.client else None
    audit_logger.log_note_operation(
        action=AuditAction.PUSH_NOTE,
        note_id=note_id,
        patient_id=note.get("patient_id"),
        note_type=note.get("note_type"),
        status="success" if result.get("success") else "failure",
        details=result.get("error") or result.get("fhir_id", ""),
        fhir_id=result.get("fhir_id"),
        ip_address=ip_address
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD WRITE-BACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/vitals/push")
async def push_vital(request: VitalWriteRequest, http_request: Request, x_device_id: Optional[str] = Header(None)):
    """
    Push a captured vital sign to the EHR as a FHIR Observation.

    Supports: blood_pressure, heart_rate, temperature, respiratory_rate,
    oxygen_saturation, weight, height, pain_level

    Feature #77: Requires fresh voiceprint verification if X-Device-ID header is present.
    """
    # Feature #77: Check continuous auth if device_id provided
    if x_device_id:
        await require_fresh_voiceprint(x_device_id)

    # Build FHIR Observation
    observation = build_observation(request.model_dump(), request.patient_id)

    # Push to EHR
    result = await push_resource_to_ehr("Observation", observation)

    # HIPAA Audit: Log vital push
    ip_address = http_request.client.host if http_request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.PUSH_VITAL,
        patient_id=request.patient_id,
        endpoint="/api/v1/vitals/push",
        status="success" if result.get("success") else "failure",
        details=f"Vital: {request.vital_type} = {request.value} {request.unit}",
        ip_address=ip_address
    )

    return result


@app.post("/api/v1/orders/push")
async def push_order(request: OrderWriteRequest, http_request: Request, x_device_id: Optional[str] = Header(None)):
    """
    Push an order to the EHR as a FHIR ServiceRequest (lab/imaging) or MedicationRequest (meds).

    Feature #77: Requires fresh voiceprint verification if X-Device-ID header is present.
    """
    # Feature #77: Check continuous auth if device_id provided
    if x_device_id:
        await require_fresh_voiceprint(x_device_id)

    # Determine resource type and build appropriate FHIR resource
    if request.order_type.upper() == "MEDICATION":
        resource = build_medication_request(request.model_dump(), request.patient_id)
        resource_type = "MedicationRequest"
    else:
        resource = build_service_request(request.model_dump(), request.patient_id)
        resource_type = "ServiceRequest"

    # Push to EHR
    result = await push_resource_to_ehr(resource_type, resource)

    # HIPAA Audit: Log order push
    ip_address = http_request.client.host if http_request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.PUSH_ORDER,
        patient_id=request.patient_id,
        endpoint="/api/v1/orders/push",
        status="success" if result.get("success") else "failure",
        details=f"Order: {request.order_type} - {request.display_name}",
        ip_address=ip_address
    )

    return result


@app.post("/api/v1/allergies/push")
async def push_allergy(request: AllergyWriteRequest, http_request: Request, x_device_id: Optional[str] = Header(None)):
    """
    Push a new allergy to the EHR as a FHIR AllergyIntolerance.

    Feature #77: Requires fresh voiceprint verification if X-Device-ID header is present.
    """
    # Feature #77: Check continuous auth if device_id provided
    if x_device_id:
        await require_fresh_voiceprint(x_device_id)

    # Build FHIR AllergyIntolerance
    allergy_resource = build_allergy_intolerance(request.model_dump(), request.patient_id)

    # Push to EHR
    result = await push_resource_to_ehr("AllergyIntolerance", allergy_resource)

    # HIPAA Audit: Log allergy creation
    ip_address = http_request.client.host if http_request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.PUSH_ALLERGY,
        patient_id=request.patient_id,
        endpoint="/api/v1/allergies/push",
        status="success" if result.get("success") else "failure",
        details=f"Allergy: {request.substance} (criticality: {request.criticality})",
        ip_address=ip_address
    )

    return result


@app.put("/api/v1/medications/{med_id}/status")
async def update_medication_status(med_id: str, request: MedicationUpdateRequest, http_request: Request, x_device_id: Optional[str] = Header(None)):
    """
    Update medication status (HIPAA-compliant soft delete).

    Valid status values: active, on-hold, cancelled, stopped, completed, entered-in-error
    Use 'stopped' for discontinued medications, 'on-hold' for temporarily paused.

    Feature #77: Requires fresh voiceprint verification if X-Device-ID header is present.
    """
    # Feature #77: Check continuous auth if device_id provided
    if x_device_id:
        await require_fresh_voiceprint(x_device_id)

    # Build update payload
    update_resource = {
        "resourceType": "MedicationRequest",
        "id": med_id,
        "status": request.new_status,
        "subject": {"reference": f"Patient/{request.patient_id}"}
    }

    if request.reason:
        update_resource["statusReason"] = {"text": request.reason}

    # Attempt PUT to EHR
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{CERNER_BASE_URL}/MedicationRequest/{med_id}",
                json=update_resource,
                headers={
                    "Content-Type": "application/fhir+json",
                    "Accept": "application/fhir+json"
                }
            )

            if response.status_code == 200:
                result = {
                    "success": True,
                    "medication_id": med_id,
                    "new_status": request.new_status,
                    "message": f"Medication status updated to {request.new_status}"
                }
            elif response.status_code == 403:
                # Sandbox read-only
                result = {
                    "success": True,
                    "simulated": True,
                    "medication_id": med_id,
                    "new_status": request.new_status,
                    "message": "EHR sandbox is read-only - status change validated but not persisted",
                    "status_code": 403
                }
            else:
                result = {
                    "success": False,
                    "error": f"EHR returned status {response.status_code}",
                    "status_code": response.status_code
                }
    except Exception as e:
        result = {"success": False, "error": str(e)}

    # HIPAA Audit: Log medication status change
    ip_address = http_request.client.host if http_request.client else None
    audit_logger.log_phi_access(
        action=AuditAction.UPDATE_MEDICATION,
        patient_id=request.patient_id,
        endpoint=f"/api/v1/medications/{med_id}/status",
        status="success" if result.get("success") else "failure",
        details=f"Status: {request.new_status}, Reason: {request.reason or 'N/A'}",
        ip_address=ip_address
    )

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
    print(f"🔗 WebSocket accepted from client")

    # Generate session ID
    session_id = str(uuid.uuid4())[:8]
    print(f"🎤 Session ID: {session_id}")
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


# ════════════════════════════════════════════════════════════════════════════════
# AUDIT LOG API - Web Dashboard Viewer
# ════════════════════════════════════════════════════════════════════════════════

class AuditLogEntry(BaseModel):
    """Model for audit log entries"""
    timestamp: str
    event_type: str
    action: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    status: Optional[str] = None
    details: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    ip_address: Optional[str] = None
    device_type: Optional[str] = None
    note_id: Optional[str] = None
    note_type: Optional[str] = None
    severity: Optional[str] = None
    session_id: Optional[str] = None

class AuditLogResponse(BaseModel):
    """Response model for audit log queries"""
    total: int
    page: int
    page_size: int
    entries: List[AuditLogEntry]

class AuditLogStats(BaseModel):
    """Statistics for audit logs"""
    total_entries: int
    phi_access_count: int
    note_operations_count: int
    safety_alerts_count: int
    session_count: int
    unique_patients: int
    unique_users: int
    entries_by_action: dict
    entries_by_hour: List[dict]


def read_audit_logs(
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    patient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> tuple[List[dict], int]:
    """
    Read audit logs from file with filtering and pagination.
    Returns (entries, total_count)
    """
    log_path = "logs/audit.log"
    if not os.path.exists(log_path):
        return [], 0

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)

                # Apply filters
                if event_type and entry.get("event_type") != event_type:
                    continue
                if action and entry.get("action") != action:
                    continue
                if patient_id and entry.get("patient_id") != patient_id:
                    continue
                if start_date:
                    if entry.get("timestamp", "") < start_date:
                        continue
                if end_date:
                    if entry.get("timestamp", "") > end_date:
                        continue

                entries.append(entry)
            except json.JSONDecodeError:
                continue

    # Sort by timestamp descending (newest first)
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    total = len(entries)
    paginated = entries[offset:offset + limit]

    return paginated, total


@app.get("/api/v1/audit/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)")
):
    """
    Get audit log entries with filtering and pagination.

    - **page**: Page number (1-indexed)
    - **page_size**: Number of entries per page (max 500)
    - **event_type**: Filter by PHI_ACCESS, NOTE_OPERATION, SAFETY_ALERT, SESSION
    - **action**: Filter by specific action (VIEW_PATIENT, SAVE_NOTE, etc.)
    - **patient_id**: Filter by patient ID
    - **start_date**: Filter entries after this date
    - **end_date**: Filter entries before this date
    """
    offset = (page - 1) * page_size
    entries, total = read_audit_logs(
        limit=page_size,
        offset=offset,
        event_type=event_type,
        action=action,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date
    )

    return AuditLogResponse(
        total=total,
        page=page,
        page_size=page_size,
        entries=[AuditLogEntry(**e) for e in entries]
    )


@app.get("/api/v1/audit/stats", response_model=AuditLogStats)
async def get_audit_stats():
    """
    Get audit log statistics for the dashboard.

    Returns counts by event type, action breakdown, and hourly distribution.
    """
    log_path = "logs/audit.log"
    if not os.path.exists(log_path):
        return AuditLogStats(
            total_entries=0,
            phi_access_count=0,
            note_operations_count=0,
            safety_alerts_count=0,
            session_count=0,
            unique_patients=0,
            unique_users=0,
            entries_by_action={},
            entries_by_hour=[]
        )

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Calculate stats
    phi_count = sum(1 for e in entries if e.get("event_type") == "PHI_ACCESS")
    note_count = sum(1 for e in entries if e.get("event_type") == "NOTE_OPERATION")
    safety_count = sum(1 for e in entries if e.get("event_type") == "SAFETY_ALERT")
    session_count = sum(1 for e in entries if e.get("event_type") == "SESSION")

    # Unique patients and users
    patients = set(e.get("patient_id") for e in entries if e.get("patient_id"))
    users = set(e.get("user_id") for e in entries if e.get("user_id"))

    # Action breakdown
    action_counts = {}
    for e in entries:
        action = e.get("action", "UNKNOWN")
        action_counts[action] = action_counts.get(action, 0) + 1

    # Hourly distribution (last 24 hours)
    from collections import defaultdict
    hourly = defaultdict(int)
    now = datetime.now(timezone.utc)
    for e in entries:
        try:
            ts = datetime.fromisoformat(e.get("timestamp", "").replace("Z", "+00:00"))
            if (now - ts).total_seconds() < 86400:  # Last 24 hours
                hour = ts.strftime("%H:00")
                hourly[hour] += 1
        except:
            continue

    hourly_list = [{"hour": h, "count": c} for h, c in sorted(hourly.items())]

    return AuditLogStats(
        total_entries=len(entries),
        phi_access_count=phi_count,
        note_operations_count=note_count,
        safety_alerts_count=safety_count,
        session_count=session_count,
        unique_patients=len(patients),
        unique_users=len(users),
        entries_by_action=action_counts,
        entries_by_hour=hourly_list
    )


@app.get("/api/v1/audit/actions")
async def get_audit_actions():
    """Get list of all audit action types for filtering."""
    return {
        "event_types": ["PHI_ACCESS", "NOTE_OPERATION", "SAFETY_ALERT", "SESSION"],
        "actions": [
            # PHI Access
            "VIEW_PATIENT", "SEARCH_PATIENT", "LOOKUP_MRN", "VIEW_NOTES",
            # Note Operations
            "GENERATE_NOTE", "GENERATE_DDX", "ANALYZE_IMAGE", "SAVE_NOTE", "PUSH_NOTE",
            # CRUD Write-Back
            "PUSH_VITAL", "PUSH_ORDER", "PUSH_ALLERGY", "UPDATE_MEDICATION", "DISCONTINUE_MEDICATION",
            # Billing
            "CREATE_CLAIM", "UPDATE_CLAIM", "SUBMIT_CLAIM", "VIEW_CLAIM",
            # Worklist
            "VIEW_WORKLIST", "CHECK_IN_PATIENT", "UPDATE_WORKLIST_STATUS", "ADD_TO_WORKLIST",
            # Transcription
            "START_TRANSCRIPTION", "END_TRANSCRIPTION",
            # Safety
            "CRITICAL_ALERT", "DRUG_INTERACTION", "SAFETY_CHECK_BLOCKED"
        ]
    }


@app.get("/api/v1/audit/patient/{patient_id}")
async def get_patient_audit_trail(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    Get complete audit trail for a specific patient.
    Useful for compliance reviews and patient data access requests.
    """
    offset = (page - 1) * page_size
    entries, total = read_audit_logs(
        limit=page_size,
        offset=offset,
        patient_id=patient_id
    )

    return {
        "patient_id": patient_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "entries": entries
    }


if __name__ == "__main__":
    print("🏥 MDx Vision EHR Proxy starting...")
    print("📡 Connected to: Cerner Open Sandbox")
    print("🔗 API: http://localhost:8002")
    print("📱 Android emulator: http://10.0.2.2:8002")
    print(f"🎤 Transcription: {TRANSCRIPTION_PROVIDER} (ws://localhost:8002/ws/transcribe)")
    uvicorn.run(app, host="0.0.0.0", port=8002)
