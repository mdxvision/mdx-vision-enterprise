"""
Drug Interaction Service
"""

from openai import AzureOpenAI, OpenAI
from typing import List, Dict, Optional
import structlog
import json

from app.config import settings

logger = structlog.get_logger()


class DrugInteractionService:
    """Check for drug interactions using AI and reference databases"""
    
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
    
    async def extract_drugs_from_text(self, text: str) -> List[str]:
        """Extract medication names from clinical text"""
        
        system_prompt = """Extract all medication/drug names from the text.
Return as JSON array: ["medication1", "medication2"]
Include brand names and generic names. Only include actual medications."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("medications", result) if isinstance(result, dict) else result
            
        except Exception as e:
            logger.error("Drug extraction failed", error=str(e))
            return []
    
    async def check_interactions(self, drugs: List[str]) -> List[Dict]:
        """Check for interactions between a list of drugs"""
        
        system_prompt = """Analyze the drug list for potential interactions.
Return JSON array of interactions:
[{
    "drug1": "Drug A",
    "drug2": "Drug B", 
    "severity": "HIGH|MODERATE|LOW|CONTRAINDICATED",
    "description": "Brief description of interaction",
    "clinicalEffect": "What happens clinically",
    "recommendation": "Clinical recommendation"
}]
Only include clinically significant interactions. Return empty array if none."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Check interactions for: {', '.join(drugs)}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            interactions = result.get("interactions", result) if isinstance(result, dict) else result
            
            return interactions if isinstance(interactions, list) else []
            
        except Exception as e:
            logger.error("Interaction check failed", error=str(e))
            return []
    
    async def lookup_drug(self, drug_name: str) -> Dict:
        """Look up information about a specific drug"""
        
        system_prompt = """Provide drug information in JSON format:
{
    "name": "Drug name",
    "genericName": "Generic name",
    "drugClass": "Drug class",
    "indications": ["indication1"],
    "commonSideEffects": ["effect1"],
    "contraindications": ["contraindication1"],
    "blackBoxWarning": "Warning text or null"
}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Drug information for: {drug_name}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error("Drug lookup failed", error=str(e))
            raise
