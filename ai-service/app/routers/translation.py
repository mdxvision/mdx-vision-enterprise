"""
Real-time translation router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import structlog

from app.services.translation_service import TranslationService

router = APIRouter()
logger = structlog.get_logger()

translation_service = TranslationService()


class TranslationRequest(BaseModel):
    text: str
    sourceLanguage: str = "auto"
    targetLanguage: str = "en"


class TranslationResponse(BaseModel):
    originalText: str
    translatedText: str
    sourceLanguage: str
    targetLanguage: str
    confidence: Optional[float] = None


@router.post("", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Translate text between languages"""
    try:
        logger.info("Translating text", 
                   source=request.sourceLanguage, 
                   target=request.targetLanguage)
        
        result = await translation_service.translate(
            text=request.text,
            source_language=request.sourceLanguage,
            target_language=request.targetLanguage
        )
        
        return TranslationResponse(
            originalText=request.text,
            translatedText=result["translated_text"],
            sourceLanguage=result.get("detected_language", request.sourceLanguage),
            targetLanguage=request.targetLanguage,
            confidence=result.get("confidence")
        )
        
    except Exception as e:
        logger.error("Translation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "zh", "name": "Chinese (Mandarin)"},
            {"code": "ar", "name": "Arabic"},
            {"code": "hi", "name": "Hindi"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "ru", "name": "Russian"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "it", "name": "Italian"},
            {"code": "vi", "name": "Vietnamese"},
            {"code": "tl", "name": "Tagalog"},
            {"code": "pl", "name": "Polish"},
            {"code": "uk", "name": "Ukrainian"},
            # Add more as needed - MDx supports 400+ languages
        ],
        "total": 400
    }
