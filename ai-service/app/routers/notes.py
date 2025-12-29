"""
Clinical note generation router using Azure OpenAI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import structlog

from app.services.clinical_nlp_service import ClinicalNLPService

router = APIRouter()
logger = structlog.get_logger()

# Initialize the clinical NLP service
nlp_service = ClinicalNLPService()


class NoteGenerationRequest(BaseModel):
    encounterId: str
    noteType: str = "SOAP"
    transcriptionText: Optional[str] = None
    chiefComplaint: Optional[str] = None
    patientContext: Optional[dict] = None


class SOAPNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str
    summary: Optional[str] = None
    icd10Codes: Optional[List[str]] = None
    cptCodes: Optional[List[str]] = None


class NineLineReport(BaseModel):
    """Military 9-Line Medevac Report"""
    line1_location: str  # Grid coordinates
    line2_frequency: str  # Radio frequency
    line3_patients: str  # Number and precedence
    line4_equipment: str  # Special equipment needed
    line5_patients_type: str  # Litter/ambulatory
    line6_security: str  # Enemy activity
    line7_marking: str  # Method of marking
    line8_nationality: str  # Patient nationality
    line9_terrain: str  # NBC contamination


@router.post("/generate", response_model=SOAPNote)
async def generate_clinical_note(request: NoteGenerationRequest):
    """Generate a clinical note from transcription"""
    try:
        logger.info("Generating clinical note", 
                   encounter_id=request.encounterId,
                   note_type=request.noteType)
        
        if request.noteType == "SOAP":
            result = await nlp_service.generate_soap_note(
                transcription_text=request.transcriptionText,
                chief_complaint=request.chiefComplaint,
                patient_context=request.patientContext
            )
        elif request.noteType == "NINE_LINE":
            result = await nlp_service.generate_nine_line(
                transcription_text=request.transcriptionText,
                context=request.patientContext
            )
        else:
            result = await nlp_service.generate_generic_note(
                transcription_text=request.transcriptionText,
                note_type=request.noteType
            )
        
        logger.info("Clinical note generated successfully", 
                   encounter_id=request.encounterId)
        
        return result
        
    except Exception as e:
        logger.error("Failed to generate clinical note", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-codes")
async def extract_medical_codes(request: NoteGenerationRequest):
    """Extract ICD-10 and CPT codes from clinical text"""
    try:
        codes = await nlp_service.extract_medical_codes(
            clinical_text=request.transcriptionText
        )
        
        return {
            "icd10Codes": codes.get("icd10", []),
            "cptCodes": codes.get("cpt", [])
        }
        
    except Exception as e:
        logger.error("Failed to extract codes", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_encounter(request: NoteGenerationRequest):
    """Generate a summary of the encounter"""
    try:
        summary = await nlp_service.generate_summary(
            transcription_text=request.transcriptionText,
            note_type=request.noteType
        )
        
        return {"summary": summary}
        
    except Exception as e:
        logger.error("Failed to generate summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/handoff")
async def generate_handoff_note(request: NoteGenerationRequest):
    """Generate a patient handoff note (I-PASS, SBAR format)"""
    try:
        handoff = await nlp_service.generate_handoff_note(
            transcription_text=request.transcriptionText,
            patient_context=request.patientContext
        )
        
        return handoff
        
    except Exception as e:
        logger.error("Failed to generate handoff note", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
