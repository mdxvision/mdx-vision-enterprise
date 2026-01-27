"""
MDx Vision - Differential Diagnosis with RAG (Issue #116)

"Minerva, what do you think?" - AI-assisted differential diagnosis generation
that considers the patient's specific clinical context using RAG to incorporate
relevant medical literature and guidelines.

Features:
- Analyzes patient context (symptoms, vitals, labs, history)
- Generates ranked differential diagnosis with likelihood estimates
- Uses RAG to cite relevant clinical guidelines and literature
- Provides supporting features and recommended next steps
- Highlights red flags and "can't miss" diagnoses
- Supports follow-up questions: "Why do you think that?", "What else?"

Usage:
    from differential_diagnosis import DifferentialDiagnosisEngine, get_differential_engine

    engine = await get_differential_engine()
    result = await engine.generate_differential(patient_context, chief_complaint)
"""

import os
import asyncio
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel

import httpx

logger = logging.getLogger(__name__)

# Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
DIFFERENTIAL_MODEL = os.getenv("DIFFERENTIAL_MODEL", "claude-3-haiku-20240307")
MAX_DIAGNOSES = int(os.getenv("MAX_DIFFERENTIAL_DIAGNOSES", "7"))
CONFIDENCE_THRESHOLD = float(os.getenv("DIFFERENTIAL_CONFIDENCE_THRESHOLD", "0.1"))


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class DiagnosisLikelihood(str, Enum):
    """Likelihood categories for differential diagnoses"""
    MOST_LIKELY = "most_likely"        # >70% likelihood
    LIKELY = "likely"                   # 40-70% likelihood
    POSSIBLE = "possible"               # 15-40% likelihood
    LESS_LIKELY = "less_likely"         # 5-15% likelihood
    UNLIKELY_BUT_IMPORTANT = "unlikely_but_important"  # <5% but "can't miss"


class DiagnosisSeverity(str, Enum):
    """Severity levels for diagnoses"""
    CRITICAL = "critical"      # Life-threatening if missed
    SERIOUS = "serious"        # Significant morbidity risk
    MODERATE = "moderate"      # Requires treatment
    MILD = "mild"              # Self-limiting or minor


@dataclass
class Diagnosis:
    """A single diagnosis in the differential"""
    name: str
    icd10_code: Optional[str]
    likelihood: DiagnosisLikelihood
    likelihood_percentage: float  # 0-100
    severity: DiagnosisSeverity
    supporting_features: List[str]
    against_features: List[str]
    distinguishing_tests: List[str]
    next_steps: List[str]
    red_flags: List[str]
    citations: List[Dict[str, str]]
    rationale: str
    is_cant_miss: bool = False  # True for "can't miss" diagnoses

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "likelihood": self.likelihood.value,
            "severity": self.severity.value,
        }


@dataclass
class DifferentialResult:
    """Complete differential diagnosis result"""
    patient_id: str
    chief_complaint: str
    diagnoses: List[Diagnosis]
    clinical_summary: str
    spoken_summary: str  # TTS-friendly summary for Minerva
    confidence: float
    rag_enhanced: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    follow_up_suggestions: List[str] = field(default_factory=list)
    red_flag_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "chief_complaint": self.chief_complaint,
            "diagnoses": [d.to_dict() for d in self.diagnoses],
            "clinical_summary": self.clinical_summary,
            "spoken_summary": self.spoken_summary,
            "confidence": self.confidence,
            "rag_enhanced": self.rag_enhanced,
            "timestamp": self.timestamp,
            "follow_up_suggestions": self.follow_up_suggestions,
            "red_flag_summary": self.red_flag_summary,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models for API
# ═══════════════════════════════════════════════════════════════════════════════

class PatientContext(BaseModel):
    """Patient clinical context for differential diagnosis"""
    patient_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaint: str
    symptoms: List[str] = []
    symptom_duration: Optional[str] = None
    vital_signs: Dict[str, Any] = {}
    lab_results: Dict[str, Any] = {}
    imaging_results: Optional[str] = None
    past_medical_history: List[str] = []
    medications: List[str] = []
    allergies: List[str] = []
    family_history: List[str] = []
    social_history: Optional[str] = None
    physical_exam_findings: List[str] = []


class DifferentialRequest(BaseModel):
    """Request to generate differential diagnosis"""
    patient_context: PatientContext
    include_citations: bool = True
    max_diagnoses: int = 7
    include_cant_miss: bool = True


class DifferentialResponse(BaseModel):
    """Response containing differential diagnosis"""
    patient_id: str
    chief_complaint: str
    diagnoses: List[Dict[str, Any]]
    clinical_summary: str
    spoken_summary: str
    confidence: float
    rag_enhanced: bool
    timestamp: str
    follow_up_suggestions: List[str]
    red_flag_summary: Optional[str] = None


class FollowUpRequest(BaseModel):
    """Request for follow-up question on differential"""
    patient_id: str
    question: str  # "Why do you think that?", "What else?", etc.
    previous_differential: Optional[Dict[str, Any]] = None


class FollowUpResponse(BaseModel):
    """Response to follow-up question"""
    patient_id: str
    question: str
    response: str
    spoken_response: str
    citations: List[Dict[str, str]]
    updated_differential: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════════════════════════════════════════

DIFFERENTIAL_SYSTEM_PROMPT = """You are Minerva, an AI clinical reasoning assistant for healthcare providers.
You are helping generate a differential diagnosis based on the patient's clinical presentation.

CLINICAL CONTEXT:
{patient_context}

RELEVANT GUIDELINES AND EVIDENCE:
{rag_context}

Your task is to generate a differential diagnosis that is:
1. COMPREHENSIVE - Include both common and important diagnoses
2. RANKED - Order by likelihood, with most likely first
3. EVIDENCE-BASED - Reference the provided guidelines when applicable
4. ACTIONABLE - Include specific next steps for each diagnosis
5. SAFETY-FOCUSED - Highlight "can't miss" diagnoses prominently

IMPORTANT:
- Always include "can't miss" diagnoses even if unlikely (e.g., MI for chest pain, PE for dyspnea)
- For each diagnosis, note supporting AND against features
- Suggest specific tests that would help distinguish between diagnoses
- Use likelihood percentages that sum approximately to 100%
- Be concise but complete - this will be read aloud

Format your response as a structured differential diagnosis list."""

DIFFERENTIAL_USER_PROMPT = """Generate a differential diagnosis for:

Chief Complaint: {chief_complaint}
Symptoms: {symptoms}
Duration: {duration}

Key Findings:
{key_findings}

Please provide:
1. Top {max_diagnoses} diagnoses ranked by likelihood
2. For each: likelihood %, supporting features, against features, next steps
3. Any red flags that require immediate attention
4. Specific tests to help distinguish between diagnoses

Start with a brief clinical summary, then list the differential."""

FOLLOW_UP_PROMPT_WHY = """The clinician asks: "Why do you think that?"

Referring to the differential diagnosis you provided, explain your clinical reasoning:
1. Why did you rank the diagnoses in this order?
2. What features most strongly support the top diagnoses?
3. What epidemiological factors influenced your assessment?

Be educational and cite relevant guidelines."""

FOLLOW_UP_PROMPT_WHAT_ELSE = """The clinician asks: "What else could this be?"

Consider additional diagnoses that weren't in your initial differential:
1. Are there less common conditions that could present this way?
2. Are there any atypical presentations to consider?
3. Should any of the initial diagnoses be re-ranked based on new thinking?

Be thorough but practical."""


# ═══════════════════════════════════════════════════════════════════════════════
# Differential Diagnosis Engine
# ═══════════════════════════════════════════════════════════════════════════════

class DifferentialDiagnosisEngine:
    """
    AI-powered differential diagnosis generator with RAG support.
    """

    def __init__(self):
        self._rag_engine = None
        self._session_cache: Dict[str, DifferentialResult] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the engine with RAG support"""
        try:
            # Import RAG engine
            from rag import rag_engine, RAG_AVAILABLE
            if RAG_AVAILABLE and rag_engine.initialized:
                self._rag_engine = rag_engine
            else:
                logger.warning("RAG not available for differential diagnosis")

            self._initialized = True
            logger.info("DifferentialDiagnosisEngine initialized")
            return True

        except ImportError:
            logger.warning("RAG module not available")
            self._initialized = True
            return True

    def _build_patient_context_string(self, ctx: PatientContext) -> str:
        """Build formatted patient context string"""
        parts = []

        # Demographics
        if ctx.name:
            parts.append(f"Patient: {ctx.name}")
        if ctx.age:
            parts.append(f"Age: {ctx.age} years")
        if ctx.gender:
            parts.append(f"Gender: {ctx.gender}")

        # Chief complaint and symptoms
        parts.append(f"\nChief Complaint: {ctx.chief_complaint}")
        if ctx.symptoms:
            parts.append(f"Symptoms: {', '.join(ctx.symptoms)}")
        if ctx.symptom_duration:
            parts.append(f"Duration: {ctx.symptom_duration}")

        # Vital signs
        if ctx.vital_signs:
            vitals = []
            for k, v in ctx.vital_signs.items():
                if isinstance(v, dict):
                    vitals.append(f"{k}: {v.get('value', v)} {v.get('unit', '')}")
                else:
                    vitals.append(f"{k}: {v}")
            parts.append(f"\nVital Signs: {', '.join(vitals)}")

        # Labs
        if ctx.lab_results:
            labs = []
            for k, v in ctx.lab_results.items():
                if isinstance(v, dict):
                    labs.append(f"{k}: {v.get('value', v)} {v.get('unit', '')}")
                else:
                    labs.append(f"{k}: {v}")
            parts.append(f"Lab Results: {', '.join(labs)}")

        # Imaging
        if ctx.imaging_results:
            parts.append(f"Imaging: {ctx.imaging_results}")

        # History
        if ctx.past_medical_history:
            parts.append(f"\nPast Medical History: {', '.join(ctx.past_medical_history)}")
        if ctx.medications:
            parts.append(f"Current Medications: {', '.join(ctx.medications)}")
        if ctx.allergies:
            parts.append(f"Allergies: {', '.join(ctx.allergies)}")
        if ctx.family_history:
            parts.append(f"Family History: {', '.join(ctx.family_history)}")
        if ctx.social_history:
            parts.append(f"Social History: {ctx.social_history}")

        # Physical exam
        if ctx.physical_exam_findings:
            parts.append(f"\nPhysical Exam: {', '.join(ctx.physical_exam_findings)}")

        return '\n'.join(parts)

    def _get_rag_context(self, query: str, specialty: Optional[str] = None) -> Tuple[str, List[Dict]]:
        """Get RAG context for the query"""
        if not self._rag_engine or not self._rag_engine.initialized:
            return "No guideline context available.", []

        try:
            from rag import get_augmented_prompt
            augmented_prompt, sources = get_augmented_prompt(query, n_results=5)

            if not sources:
                return "No specific guidelines found for this presentation.", []

            rag_context = ""
            citations = []

            for i, source in enumerate(sources, 1):
                rag_context += f"[{i}] {source.get('source_name', 'Unknown')}: {source.get('title', 'Unknown')}\n"
                content = source.get('content', '')[:400]
                rag_context += f"   {content}...\n\n"

                citations.append({
                    "index": str(i),
                    "source": source.get('source_name', 'Unknown'),
                    "title": source.get('title', 'Unknown'),
                    "url": source.get('source_url', '')
                })

            return rag_context, citations

        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            return "Error retrieving guidelines.", []

    async def generate_differential(
        self,
        patient_context: PatientContext,
        max_diagnoses: int = MAX_DIAGNOSES,
        include_citations: bool = True
    ) -> DifferentialResult:
        """
        Generate differential diagnosis for a patient.

        Args:
            patient_context: Patient clinical context
            max_diagnoses: Maximum number of diagnoses to generate
            include_citations: Whether to include RAG citations

        Returns:
            DifferentialResult with ranked diagnoses
        """
        if not CLAUDE_API_KEY:
            return DifferentialResult(
                patient_id=patient_context.patient_id,
                chief_complaint=patient_context.chief_complaint,
                diagnoses=[],
                clinical_summary="AI service not configured. Please consult clinical references.",
                spoken_summary="I'm sorry, I can't generate a differential diagnosis right now.",
                confidence=0.0,
                rag_enhanced=False,
            )

        # Build context strings
        patient_context_str = self._build_patient_context_string(patient_context)

        # Build query for RAG
        rag_query = f"{patient_context.chief_complaint} differential diagnosis "
        if patient_context.symptoms:
            rag_query += " ".join(patient_context.symptoms[:3])

        # Get RAG context
        rag_context, citations = self._get_rag_context(rag_query)
        rag_enhanced = bool(citations)

        # Build prompts
        system_prompt = DIFFERENTIAL_SYSTEM_PROMPT.format(
            patient_context=patient_context_str,
            rag_context=rag_context
        )

        # Build key findings for user prompt
        key_findings = []
        if patient_context.vital_signs:
            key_findings.append(f"Vitals: {patient_context.vital_signs}")
        if patient_context.lab_results:
            key_findings.append(f"Labs: {patient_context.lab_results}")
        if patient_context.physical_exam_findings:
            key_findings.append(f"Exam: {', '.join(patient_context.physical_exam_findings)}")

        user_prompt = DIFFERENTIAL_USER_PROMPT.format(
            chief_complaint=patient_context.chief_complaint,
            symptoms=', '.join(patient_context.symptoms) if patient_context.symptoms else 'Not specified',
            duration=patient_context.symptom_duration or 'Not specified',
            key_findings='\n'.join(key_findings) if key_findings else 'None specified',
            max_diagnoses=max_diagnoses
        )

        # Call Claude API
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": CLAUDE_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": DIFFERENTIAL_MODEL,
                        "max_tokens": 1500,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}]
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Claude API error: {response.status_code}")
                    return self._error_result(patient_context, "AI service error")

                result = response.json()
                ai_response = result.get("content", [{}])[0].get("text", "")

            except Exception as e:
                logger.error(f"API call failed: {e}")
                return self._error_result(patient_context, str(e))

        # Parse the response into structured diagnoses
        diagnoses = self._parse_differential_response(ai_response, citations)

        # Generate summaries
        clinical_summary = self._extract_clinical_summary(ai_response)
        spoken_summary = self._generate_spoken_summary(diagnoses, patient_context.chief_complaint)

        # Identify red flags
        red_flag_summary = self._extract_red_flags(ai_response, diagnoses)

        # Calculate confidence
        confidence = 0.5 + (0.3 if rag_enhanced else 0.0) + (0.1 if len(diagnoses) >= 3 else 0.0)

        result = DifferentialResult(
            patient_id=patient_context.patient_id,
            chief_complaint=patient_context.chief_complaint,
            diagnoses=diagnoses,
            clinical_summary=clinical_summary,
            spoken_summary=spoken_summary,
            confidence=min(confidence, 0.95),
            rag_enhanced=rag_enhanced,
            follow_up_suggestions=[
                "Say 'Why do you think that?' for my reasoning",
                "Say 'What else?' for additional considerations",
                f"Say 'Order {diagnoses[0].distinguishing_tests[0]}' to proceed" if diagnoses and diagnoses[0].distinguishing_tests else "Order tests to confirm"
            ],
            red_flag_summary=red_flag_summary
        )

        # Cache result
        self._session_cache[patient_context.patient_id] = result

        return result

    def _parse_differential_response(
        self,
        response: str,
        citations: List[Dict]
    ) -> List[Diagnosis]:
        """Parse AI response into structured diagnoses"""
        diagnoses = []

        # Simple parsing - look for numbered diagnoses
        # In production, use more sophisticated NLP or structured output
        lines = response.split('\n')

        current_diagnosis = None
        diagnosis_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for diagnosis headers (numbered items)
            match = re.match(r'^(\d+)[.)\s]+(.+?)(?:\s*[-–]\s*(\d+)%)?$', line)
            if match:
                if current_diagnosis:
                    diagnoses.append(current_diagnosis)

                diagnosis_count += 1
                name = match.group(2).strip()
                likelihood_pct = float(match.group(3)) if match.group(3) else (80 - diagnosis_count * 15)

                # Determine likelihood category
                if likelihood_pct >= 70:
                    likelihood = DiagnosisLikelihood.MOST_LIKELY
                elif likelihood_pct >= 40:
                    likelihood = DiagnosisLikelihood.LIKELY
                elif likelihood_pct >= 15:
                    likelihood = DiagnosisLikelihood.POSSIBLE
                else:
                    likelihood = DiagnosisLikelihood.LESS_LIKELY

                # Check for "can't miss" indicators
                is_cant_miss = any(term in line.lower() for term in [
                    "can't miss", "cannot miss", "rule out", "critical", "emergent"
                ])

                if is_cant_miss and likelihood_pct < 15:
                    likelihood = DiagnosisLikelihood.UNLIKELY_BUT_IMPORTANT

                current_diagnosis = Diagnosis(
                    name=name,
                    icd10_code=None,
                    likelihood=likelihood,
                    likelihood_percentage=likelihood_pct,
                    severity=DiagnosisSeverity.MODERATE,  # Default, could be parsed
                    supporting_features=[],
                    against_features=[],
                    distinguishing_tests=[],
                    next_steps=[],
                    red_flags=[],
                    citations=citations[:2] if citations else [],
                    rationale="",
                    is_cant_miss=is_cant_miss
                )

            # Parse supporting features
            elif current_diagnosis and 'support' in line.lower():
                features = re.findall(r'[-•]\s*(.+?)(?=[-•]|$)', line)
                if features:
                    current_diagnosis.supporting_features.extend(features)
                else:
                    # Single feature on line
                    feature = re.sub(r'^.*support[^\:]*:\s*', '', line, flags=re.IGNORECASE)
                    if feature:
                        current_diagnosis.supporting_features.append(feature)

            # Parse against features
            elif current_diagnosis and ('against' in line.lower() or 'atypical' in line.lower()):
                feature = re.sub(r'^.*against[^\:]*:\s*', '', line, flags=re.IGNORECASE)
                if feature:
                    current_diagnosis.against_features.append(feature)

            # Parse next steps/tests
            elif current_diagnosis and any(kw in line.lower() for kw in ['test', 'order', 'next', 'recommend']):
                step = re.sub(r'^.*(?:test|order|next|recommend)[^\:]*:\s*', '', line, flags=re.IGNORECASE)
                if step:
                    current_diagnosis.next_steps.append(step)
                    # Extract specific tests
                    test_patterns = ['ECG', 'EKG', 'CBC', 'BMP', 'CMP', 'troponin', 'CT', 'MRI',
                                    'X-ray', 'ultrasound', 'echo', 'D-dimer', 'BNP', 'lipase']
                    for test in test_patterns:
                        if test.lower() in step.lower():
                            current_diagnosis.distinguishing_tests.append(test)

            # Parse red flags
            elif current_diagnosis and 'red flag' in line.lower():
                flag = re.sub(r'^.*red flag[^\:]*:\s*', '', line, flags=re.IGNORECASE)
                if flag:
                    current_diagnosis.red_flags.append(flag)
                    current_diagnosis.severity = DiagnosisSeverity.SERIOUS

            # Parse rationale
            elif current_diagnosis and 'because' in line.lower():
                current_diagnosis.rationale = line

        # Don't forget the last diagnosis
        if current_diagnosis:
            diagnoses.append(current_diagnosis)

        # If parsing failed, create a generic result
        if not diagnoses:
            diagnoses.append(Diagnosis(
                name="Unable to parse specific diagnoses",
                icd10_code=None,
                likelihood=DiagnosisLikelihood.POSSIBLE,
                likelihood_percentage=50,
                severity=DiagnosisSeverity.MODERATE,
                supporting_features=["See full response for details"],
                against_features=[],
                distinguishing_tests=["Clinical correlation required"],
                next_steps=["Review full assessment"],
                red_flags=[],
                citations=citations,
                rationale="Please review the complete AI response for detailed assessment."
            ))

        return diagnoses[:MAX_DIAGNOSES]

    def _extract_clinical_summary(self, response: str) -> str:
        """Extract or generate clinical summary from response"""
        # Look for summary section
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if 'summary' in line.lower() or 'assessment' in line.lower():
                # Return next few non-empty lines
                summary_lines = []
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith(('1.', '2.', '3.')):
                        summary_lines.append(lines[j].strip())
                if summary_lines:
                    return ' '.join(summary_lines)[:500]

        # Return first non-empty paragraph
        for line in lines:
            if line.strip() and len(line.strip()) > 50:
                return line.strip()[:500]

        return "Clinical assessment pending detailed review."

    def _generate_spoken_summary(self, diagnoses: List[Diagnosis], chief_complaint: str) -> str:
        """Generate TTS-friendly summary for Minerva"""
        if not diagnoses:
            return "I need more information to generate a differential diagnosis."

        # Build spoken summary
        top_diagnosis = diagnoses[0]
        summary_parts = [f"For {chief_complaint}, "]

        # Lead with most likely
        summary_parts.append(
            f"the most likely diagnosis is {top_diagnosis.name} "
            f"at {top_diagnosis.likelihood_percentage:.0f}% likelihood. "
        )

        # Add "can't miss" if present
        cant_miss = [d for d in diagnoses if d.is_cant_miss or d.severity == DiagnosisSeverity.CRITICAL]
        if cant_miss and cant_miss[0] != top_diagnosis:
            summary_parts.append(
                f"Important to rule out {cant_miss[0].name}. "
            )

        # Add next step
        if top_diagnosis.distinguishing_tests:
            summary_parts.append(
                f"Say 'order {top_diagnosis.distinguishing_tests[0]}' to proceed. "
            )
        elif top_diagnosis.next_steps:
            summary_parts.append(
                f"Next step: {top_diagnosis.next_steps[0]}. "
            )

        # Add follow-up prompt
        summary_parts.append("Ask me 'why' for my reasoning.")

        return ''.join(summary_parts)

    def _extract_red_flags(self, response: str, diagnoses: List[Diagnosis]) -> Optional[str]:
        """Extract red flag summary from response"""
        all_red_flags = []

        # From diagnoses
        for d in diagnoses:
            all_red_flags.extend(d.red_flags)

        # From response text
        for line in response.split('\n'):
            if 'red flag' in line.lower() or 'urgent' in line.lower() or 'emergent' in line.lower():
                all_red_flags.append(line.strip())

        if all_red_flags:
            return "; ".join(set(all_red_flags[:3]))
        return None

    def _error_result(self, ctx: PatientContext, error: str) -> DifferentialResult:
        """Create error result"""
        return DifferentialResult(
            patient_id=ctx.patient_id,
            chief_complaint=ctx.chief_complaint,
            diagnoses=[],
            clinical_summary=f"Unable to generate differential: {error}",
            spoken_summary="I encountered an error. Please try again or consult clinical references.",
            confidence=0.0,
            rag_enhanced=False,
        )

    async def answer_follow_up(
        self,
        patient_id: str,
        question: str,
        previous_differential: Optional[DifferentialResult] = None
    ) -> FollowUpResponse:
        """
        Answer follow-up questions about the differential.

        Supports:
        - "Why do you think that?" - Explain reasoning
        - "What else?" - Consider additional diagnoses
        - Custom questions
        """
        # Get cached differential if not provided
        if not previous_differential:
            previous_differential = self._session_cache.get(patient_id)

        if not previous_differential:
            return FollowUpResponse(
                patient_id=patient_id,
                question=question,
                response="I don't have a previous differential to reference. Please ask 'What do you think?' first.",
                spoken_response="I need to generate a differential first. Say 'What do you think?' to get started.",
                citations=[]
            )

        # Determine follow-up type
        question_lower = question.lower()
        if 'why' in question_lower or 'think that' in question_lower:
            follow_up_prompt = FOLLOW_UP_PROMPT_WHY
        elif 'what else' in question_lower or 'else' in question_lower:
            follow_up_prompt = FOLLOW_UP_PROMPT_WHAT_ELSE
        else:
            follow_up_prompt = f"The clinician asks: \"{question}\"\n\nProvide a helpful response based on the differential diagnosis."

        # Build context
        differential_summary = f"""
Previous Differential Diagnosis:
Chief Complaint: {previous_differential.chief_complaint}

Top Diagnoses:
"""
        for i, d in enumerate(previous_differential.diagnoses[:5], 1):
            differential_summary += f"{i}. {d.name} ({d.likelihood_percentage:.0f}%)\n"

        # Call Claude API
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
                        "model": DIFFERENTIAL_MODEL,
                        "max_tokens": 800,
                        "system": f"You are Minerva, a clinical AI assistant. Reference this context:\n{differential_summary}",
                        "messages": [{"role": "user", "content": follow_up_prompt}]
                    }
                )

                if response.status_code != 200:
                    return FollowUpResponse(
                        patient_id=patient_id,
                        question=question,
                        response="I encountered an error processing your question.",
                        spoken_response="I had trouble processing that. Please try again.",
                        citations=[]
                    )

                result = response.json()
                ai_response = result.get("content", [{}])[0].get("text", "")

            except Exception as e:
                logger.error(f"Follow-up API error: {e}")
                return FollowUpResponse(
                    patient_id=patient_id,
                    question=question,
                    response=f"Error: {e}",
                    spoken_response="I encountered an error. Please try again.",
                    citations=[]
                )

        # Generate spoken version (first 2 sentences)
        sentences = ai_response.split('.')
        spoken = '. '.join(sentences[:2]) + '.' if sentences else ai_response[:200]

        return FollowUpResponse(
            patient_id=patient_id,
            question=question,
            response=ai_response,
            spoken_response=spoken,
            citations=[c for d in previous_differential.diagnoses for c in d.citations][:3]
        )

    def get_cached_differential(self, patient_id: str) -> Optional[DifferentialResult]:
        """Get cached differential for a patient"""
        return self._session_cache.get(patient_id)

    def clear_cache(self, patient_id: Optional[str] = None) -> None:
        """Clear cached differentials"""
        if patient_id:
            self._session_cache.pop(patient_id, None)
        else:
            self._session_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════

_differential_engine: Optional[DifferentialDiagnosisEngine] = None


async def get_differential_engine() -> DifferentialDiagnosisEngine:
    """Get or create the global differential diagnosis engine"""
    global _differential_engine

    if _differential_engine is None:
        _differential_engine = DifferentialDiagnosisEngine()
        await _differential_engine.initialize()

    return _differential_engine


async def shutdown_differential_engine() -> None:
    """Shutdown the global differential diagnosis engine"""
    global _differential_engine
    if _differential_engine:
        _differential_engine.clear_cache()
        _differential_engine = None
