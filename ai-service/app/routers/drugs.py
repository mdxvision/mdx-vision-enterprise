"""
Drug interaction checking router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import structlog

from app.services.drug_interaction_service import DrugInteractionService

router = APIRouter()
logger = structlog.get_logger()

drug_service = DrugInteractionService()


class DrugInteractionRequest(BaseModel):
    text: Optional[str] = None  # Extract drugs from text
    drugs: Optional[List[str]] = None  # Or provide drug list directly


class DrugInteraction(BaseModel):
    drug1: str
    drug1RxnormCode: Optional[str] = None
    drug2: str
    drug2RxnormCode: Optional[str] = None
    severity: str  # LOW, MODERATE, HIGH, CONTRAINDICATED
    description: str
    clinicalEffect: Optional[str] = None
    recommendation: Optional[str] = None


class DrugInteractionResponse(BaseModel):
    drugsIdentified: List[str]
    interactions: List[DrugInteraction]
    hasContraindications: bool


@router.post("/check-interactions", response_model=DrugInteractionResponse)
async def check_drug_interactions(request: DrugInteractionRequest):
    """Check for drug interactions"""
    try:
        drugs = request.drugs
        
        # If text provided, extract drug names first
        if request.text and not drugs:
            drugs = await drug_service.extract_drugs_from_text(request.text)
        
        if not drugs or len(drugs) < 2:
            return DrugInteractionResponse(
                drugsIdentified=drugs or [],
                interactions=[],
                hasContraindications=False
            )
        
        logger.info("Checking drug interactions", drugs=drugs)
        
        interactions = await drug_service.check_interactions(drugs)
        
        has_contraindications = any(
            i.severity == "CONTRAINDICATED" for i in interactions
        )
        
        return DrugInteractionResponse(
            drugsIdentified=drugs,
            interactions=interactions,
            hasContraindications=has_contraindications
        )
        
    except Exception as e:
        logger.error("Drug interaction check failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-medications")
async def extract_medications(request: DrugInteractionRequest):
    """Extract medication names from clinical text"""
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        drugs = await drug_service.extract_drugs_from_text(request.text)
        
        return {
            "medications": drugs,
            "count": len(drugs)
        }
        
    except Exception as e:
        logger.error("Medication extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lookup/{drug_name}")
async def lookup_drug(drug_name: str):
    """Look up drug information by name"""
    try:
        info = await drug_service.lookup_drug(drug_name)
        return info
        
    except Exception as e:
        logger.error("Drug lookup failed", error=str(e), drug=drug_name)
        raise HTTPException(status_code=500, detail=str(e))
