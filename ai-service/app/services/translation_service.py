"""
Translation Service using Azure OpenAI
"""

from openai import AzureOpenAI, OpenAI
from typing import Dict, Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


class TranslationService:
    """Real-time translation service"""
    
    def __init__(self):
        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )
            self.model = settings.azure_openai_deployment
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = "gpt-4-turbo-preview"
    
    async def translate(
        self,
        text: str,
        source_language: str = "auto",
        target_language: str = "en"
    ) -> Dict:
        """Translate text between languages"""
        
        system_prompt = f"""You are a medical translator. Translate the following text to {target_language}.
        
Rules:
- Preserve medical terminology accurately
- Maintain the clinical context
- If source language is 'auto', detect it first
- Return only the translation, no explanations"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            
            translated_text = response.choices[0].message.content
            
            return {
                "translated_text": translated_text,
                "detected_language": source_language if source_language != "auto" else "detected",
                "confidence": 0.95  # Placeholder - GPT doesn't provide confidence
            }
            
        except Exception as e:
            logger.error("Translation failed", error=str(e))
            raise
