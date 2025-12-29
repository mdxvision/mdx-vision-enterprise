"""
Clinical NLP Service using Azure OpenAI
Generates SOAP notes, extracts ICD-10 codes, summarizes encounters
"""

from openai import AzureOpenAI, OpenAI
from typing import Dict, List, Optional, Any
import structlog
import json

from app.config import settings

logger = structlog.get_logger()


class ClinicalNLPService:
    """Clinical NLP processing using GPT-4"""
    
    def __init__(self):
        # Use Azure OpenAI if configured, otherwise use OpenAI directly
        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )
            self.model = settings.azure_openai_deployment
            self.is_azure = True
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = "gpt-4-turbo-preview"
            self.is_azure = False
        
        logger.info("ClinicalNLPService initialized", 
                   provider="azure" if self.is_azure else "openai")
    
    async def generate_soap_note(
        self,
        transcription_text: str,
        chief_complaint: Optional[str] = None,
        patient_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate a SOAP note from transcription"""
        
        system_prompt = """You are a medical documentation assistant. Generate a structured SOAP note from the provided clinical encounter transcription.

Output Format (JSON):
{
    "subjective": "Patient's reported symptoms, history, and concerns",
    "objective": "Observable findings, vital signs, physical exam results mentioned",
    "assessment": "Clinical assessment and differential diagnoses",
    "plan": "Treatment plan, medications, follow-up instructions",
    "summary": "Brief 2-3 sentence summary",
    "icd10Codes": ["Code1", "Code2"],
    "cptCodes": ["Code1"]
}

Guidelines:
- Use professional medical terminology
- Be concise but comprehensive
- Include all relevant clinical information
- Suggest appropriate ICD-10 codes based on documented conditions
- Format consistently"""

        user_prompt = f"""Generate a SOAP note from this clinical encounter:

Chief Complaint: {chief_complaint or 'Not specified'}

Transcription:
{transcription_text}

{f"Patient Context: {json.dumps(patient_context)}" if patient_context else ""}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info("SOAP note generated successfully")
            return result
            
        except Exception as e:
            logger.error("Failed to generate SOAP note", error=str(e))
            raise
    
    async def generate_nine_line(
        self,
        transcription_text: str,
        context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Generate a 9-Line Medevac report for military use"""
        
        system_prompt = """You are a military medical documentation assistant. Generate a 9-Line Medevac report from the provided information.

9-Line Format:
Line 1: Location (Grid coordinates)
Line 2: Radio frequency/call sign
Line 3: Number of patients by precedence (A-Urgent, B-Priority, C-Routine)
Line 4: Special equipment required
Line 5: Number of patients (Litter/Ambulatory)
Line 6: Security at pickup site (N-No enemy, P-Possible, E-Enemy, X-Armed escort)
Line 7: Method of marking pickup site
Line 8: Patient nationality and status
Line 9: NBC contamination (Nuclear, Biological, Chemical)

Extract available information from the transcription. Use "UNKNOWN" for unavailable fields."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate 9-Line report:\n{transcription_text}"}
                ],
                temperature=0.2
            )
            
            return {"report": response.choices[0].message.content}
            
        except Exception as e:
            logger.error("Failed to generate 9-Line report", error=str(e))
            raise
    
    async def extract_medical_codes(
        self,
        clinical_text: str
    ) -> Dict[str, List[str]]:
        """Extract ICD-10 and CPT codes from clinical text"""
        
        system_prompt = """Extract ICD-10 and CPT codes from the clinical text. Return JSON:
{
    "icd10": [{"code": "A00.0", "description": "Cholera due to Vibrio cholerae"}],
    "cpt": [{"code": "99213", "description": "Office visit, established patient"}]
}
Only include codes that are clearly supported by the documentation."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": clinical_text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error("Failed to extract codes", error=str(e))
            return {"icd10": [], "cpt": []}
    
    async def generate_summary(
        self,
        transcription_text: str,
        note_type: str = "SOAP"
    ) -> str:
        """Generate a brief summary of the encounter"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Generate a concise 2-3 sentence clinical summary."},
                    {"role": "user", "content": transcription_text}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("Failed to generate summary", error=str(e))
            raise
    
    async def generate_handoff_note(
        self,
        transcription_text: str,
        patient_context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Generate I-PASS or SBAR handoff note"""
        
        system_prompt = """Generate an I-PASS handoff note:
- I: Illness severity
- P: Patient summary
- A: Action list
- S: Situation awareness
- S: Synthesis by receiver

Format as clear, structured text suitable for verbal handoff."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Patient context: {patient_context}\n\nTranscription: {transcription_text}"}
                ],
                temperature=0.3
            )
            
            return {"handoff": response.choices[0].message.content}
            
        except Exception as e:
            logger.error("Failed to generate handoff note", error=str(e))
            raise
    
    async def generate_generic_note(
        self,
        transcription_text: str,
        note_type: str
    ) -> Dict[str, str]:
        """Generate a generic clinical note"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Generate a {note_type} clinical note from the transcription."},
                    {"role": "user", "content": transcription_text}
                ],
                temperature=0.3
            )
            
            return {"content": response.choices[0].message.content}
            
        except Exception as e:
            logger.error("Failed to generate note", error=str(e))
            raise
