"""
MDx Vision - RAG (Retrieval-Augmented Generation) System
Feature #88 - Reduces hallucination by grounding responses in medical sources
Feature #89 - Knowledge Management for continuous improvement

Architecture:
    Query → Vector Search → Retrieve Top-K Docs → Augment Prompt → Claude → Cited Response

Components:
    1. ChromaDB - Local vector database (no API keys needed)
    2. Medical Knowledge Base - Guidelines, PubMed abstracts, drug info
    3. Retrieval Pipeline - Semantic search for relevant context
    4. Citation Generator - Adds source references to responses
    5. Knowledge Manager - Version control, updates, feedback loops (Feature #89)
"""

import os
import json
import hashlib
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

# HTTP client for external APIs
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: chromadb not installed. Run: pip install chromadb")

# Sentence transformers for embeddings (lighter than OpenAI)
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SourceType(str, Enum):
    """Types of medical knowledge sources"""
    CLINICAL_GUIDELINE = "clinical_guideline"
    PUBMED_ABSTRACT = "pubmed_abstract"
    DRUG_INFO = "drug_info"
    UPTODATE = "uptodate"
    CDC_GUIDELINE = "cdc_guideline"
    AHA_GUIDELINE = "aha_guideline"
    USPSTF = "uspstf"
    CUSTOM = "custom"
    OPENFDA = "openfda"
    CLINICAL_TRIAL = "clinical_trial"
    UMLS_TERMINOLOGY = "umls_terminology"


class GuidelineStatus(str, Enum):
    """Status of a clinical guideline (Feature #89)"""
    CURRENT = "current"           # Active, latest version
    SUPERSEDED = "superseded"     # Replaced by newer version
    DEPRECATED = "deprecated"     # No longer recommended
    DRAFT = "draft"               # Pending review
    ARCHIVED = "archived"         # Historical reference only


class FeedbackRating(str, Enum):
    """Clinician feedback ratings for citations (Feature #89)"""
    VERY_HELPFUL = "very_helpful"
    HELPFUL = "helpful"
    NEUTRAL = "neutral"
    NOT_HELPFUL = "not_helpful"
    INCORRECT = "incorrect"


@dataclass
class GuidelineVersion:
    """Tracks versions of clinical guidelines (Feature #89)"""
    version_id: str
    guideline_id: str
    version_number: str           # e.g., "2024.1", "2023.2"
    publication_date: str
    effective_date: str
    status: GuidelineStatus
    supersedes: Optional[str] = None     # ID of version this replaces
    superseded_by: Optional[str] = None  # ID of version that replaced this
    change_summary: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CitationFeedback:
    """Clinician feedback on citation quality (Feature #89)"""
    feedback_id: str
    document_id: str
    query: str
    rating: FeedbackRating
    comment: Optional[str] = None
    clinician_specialty: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SpecialtyCollection:
    """Specialty-specific knowledge collections (Feature #89)"""
    specialty: str
    document_ids: List[str]
    description: str
    curator: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConflictAlert:
    """Alert when guidelines conflict (Feature #89)"""
    alert_id: str
    document_id_1: str
    document_id_2: str
    conflict_type: str           # "dosing", "recommendation", "contraindication"
    description: str
    severity: str                # "high", "medium", "low"
    resolved: bool = False
    resolution_notes: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PubMedArticle:
    """PubMed article data structure (Feature #89)"""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_date: str
    mesh_terms: List[str]
    doi: Optional[str] = None


@dataclass
class MedicalDocument:
    """A document in the medical knowledge base"""
    id: str
    title: str
    content: str
    source_type: SourceType
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    publication_date: Optional[str] = None
    authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    specialty: Optional[str] = None
    last_updated: Optional[str] = None
    # Feature #89 - Knowledge Management fields
    version: Optional[str] = None                  # Version string (e.g., "2024.1")
    status: GuidelineStatus = GuidelineStatus.CURRENT
    supersedes_id: Optional[str] = None            # ID of document this replaces
    pmid: Optional[str] = None                     # PubMed ID if applicable
    usage_count: int = 0                           # Times retrieved
    helpful_count: int = 0                         # Positive feedback count
    not_helpful_count: int = 0                     # Negative feedback count

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'MedicalDocument':
        data['source_type'] = SourceType(data['source_type'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = GuidelineStatus(data['status'])
        return cls(**data)

    @property
    def quality_score(self) -> float:
        """Calculate quality score based on feedback (Feature #89)"""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0.5  # Neutral if no feedback
        return self.helpful_count / total


@dataclass
class RetrievedContext:
    """Context retrieved from the knowledge base"""
    document: MedicalDocument
    relevance_score: float
    matched_chunk: str

    def to_citation(self) -> str:
        """Generate a citation string"""
        citation = f"[{self.document.source_name or self.document.source_type.value}]"
        if self.document.publication_date:
            citation += f" ({self.document.publication_date})"
        if self.document.source_url:
            citation += f" {self.document.source_url}"
        return citation


@dataclass
class RAGResponse:
    """Response from RAG-augmented generation"""
    response: str
    citations: List[str]
    sources: List[Dict]
    confidence: float  # Based on retrieval scores
    retrieval_count: int


# ═══════════════════════════════════════════════════════════════════════════════
# MEDICAL KNOWLEDGE BASE - Built-in Clinical Guidelines
# ═══════════════════════════════════════════════════════════════════════════════

# These are condensed clinical guidelines that will be embedded
# In production, you'd ingest full PubMed/UpToDate content

BUILT_IN_GUIDELINES = [
    # Cardiovascular
    {
        "id": "aha-chest-pain-2021",
        "title": "AHA Chest Pain Evaluation Guidelines 2021",
        "content": """
        Acute Chest Pain Evaluation (AHA/ACC 2021):

        INITIAL ASSESSMENT:
        - ECG within 10 minutes of arrival
        - High-sensitivity troponin at presentation
        - If troponin negative, repeat at 1-3 hours
        - HEART score for risk stratification

        HIGH RISK FEATURES:
        - ST elevation → activate cath lab
        - Dynamic ST changes
        - Hemodynamic instability
        - Elevated troponin
        - HEART score ≥7

        DIFFERENTIAL DIAGNOSIS:
        - ACS (STEMI, NSTEMI, unstable angina)
        - Pulmonary embolism (Wells score, D-dimer)
        - Aortic dissection (if tearing pain radiating to back)
        - Pericarditis (pleuritic, positional)
        - Musculoskeletal (reproducible with palpation)

        DISPOSITION:
        - HEART score 0-3: Consider discharge with outpatient follow-up
        - HEART score 4-6: Observation, serial troponins
        - HEART score 7-10: Admission, cardiology consult
        """,
        "source_type": "aha_guideline",
        "source_name": "AHA/ACC",
        "source_url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001029",
        "publication_date": "2021",
        "keywords": ["chest pain", "ACS", "STEMI", "troponin", "HEART score", "cardiology"],
        "specialty": "cardiology"
    },
    {
        "id": "aha-heart-failure-2022",
        "title": "AHA Heart Failure Management Guidelines 2022",
        "content": """
        Heart Failure Management (AHA/ACC/HFSA 2022):

        CLASSIFICATION:
        - HFrEF: EF ≤40%
        - HFmrEF: EF 41-49%
        - HFpEF: EF ≥50%

        GUIDELINE-DIRECTED MEDICAL THERAPY (GDMT) for HFrEF:
        1. ACE-I/ARB/ARNI (sacubitril-valsartan preferred)
        2. Beta-blocker (carvedilol, metoprolol succinate, bisoprolol)
        3. MRA (spironolactone, eplerenone) if EF ≤35%
        4. SGLT2 inhibitor (dapagliflozin, empagliflozin) - NEW in 2022

        TARGET DOSES:
        - Sacubitril-valsartan: 97/103mg BID
        - Carvedilol: 25mg BID (50mg if >85kg)
        - Spironolactone: 25-50mg daily
        - Dapagliflozin: 10mg daily

        MONITORING:
        - BMP within 1-2 weeks of RAAS inhibitor changes
        - Weight daily, report 3lb gain in 1 day or 5lb in 1 week
        - BNP/NT-proBNP for prognostication

        DECOMPENSATED HF:
        - IV diuretics (furosemide 40-80mg IV)
        - Oxygen if SpO2 <90%
        - Consider inotropes if cardiogenic shock
        """,
        "source_type": "aha_guideline",
        "source_name": "AHA/ACC/HFSA",
        "source_url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001063",
        "publication_date": "2022",
        "keywords": ["heart failure", "HFrEF", "GDMT", "SGLT2", "carvedilol", "sacubitril"],
        "specialty": "cardiology"
    },
    {
        "id": "aha-afib-2023",
        "title": "AHA Atrial Fibrillation Guidelines 2023",
        "content": """
        Atrial Fibrillation Management (AHA/ACC/ACCP/HRS 2023):

        STROKE RISK (CHA2DS2-VASc):
        - C: CHF (1 point)
        - H: Hypertension (1 point)
        - A2: Age ≥75 (2 points)
        - D: Diabetes (1 point)
        - S2: Stroke/TIA history (2 points)
        - V: Vascular disease (1 point)
        - A: Age 65-74 (1 point)
        - Sc: Sex category female (1 point)

        ANTICOAGULATION:
        - Score 0 (men) or 1 (women): No anticoagulation
        - Score 1 (men) or 2 (women): Consider anticoagulation
        - Score ≥2 (men) or ≥3 (women): Anticoagulation recommended

        PREFERRED AGENTS (DOACs over warfarin):
        - Apixaban 5mg BID (2.5mg if 2 of: age ≥80, weight ≤60kg, Cr ≥1.5)
        - Rivaroxaban 20mg daily with food (15mg if CrCl 15-50)
        - Dabigatran 150mg BID (75mg if CrCl 15-30)

        RATE CONTROL:
        - Target HR <110 at rest (lenient) or <80 (strict)
        - Beta-blockers or diltiazem first line
        - Digoxin if HFrEF or inadequate response

        RHYTHM CONTROL:
        - Consider if symptomatic despite rate control
        - Cardioversion, antiarrhythmics, or ablation
        """,
        "source_type": "aha_guideline",
        "source_name": "AHA/ACC/HRS",
        "publication_date": "2023",
        "keywords": ["atrial fibrillation", "afib", "CHA2DS2-VASc", "anticoagulation", "DOAC", "rate control"],
        "specialty": "cardiology"
    },
    # Pulmonary
    {
        "id": "gold-copd-2024",
        "title": "GOLD COPD Guidelines 2024",
        "content": """
        COPD Management (GOLD 2024):

        DIAGNOSIS:
        - Spirometry: FEV1/FVC <0.70 post-bronchodilator
        - Symptoms: dyspnea, chronic cough, sputum production
        - Risk factors: smoking, occupational exposure

        SEVERITY (FEV1 % predicted):
        - GOLD 1 Mild: ≥80%
        - GOLD 2 Moderate: 50-79%
        - GOLD 3 Severe: 30-49%
        - GOLD 4 Very Severe: <30%

        INITIAL THERAPY (by group):
        - Group A (low symptoms, low risk): SABA PRN
        - Group B (more symptoms): LABA or LAMA
        - Group E (exacerbations): LABA + LAMA ± ICS if eos ≥300

        MAINTENANCE:
        - LAMA: tiotropium 18mcg daily
        - LABA: salmeterol, formoterol, olodaterol
        - LABA/LAMA: umeclidinium/vilanterol, tiotropium/olodaterol
        - Triple: fluticasone/umeclidinium/vilanterol (Trelegy)

        EXACERBATION TREATMENT:
        - Increase bronchodilators
        - Prednisone 40mg x 5 days
        - Antibiotics if purulent sputum (amoxicillin-clavulanate, azithromycin, or doxycycline)
        - Consider admission if severe distress, failure to respond, comorbidities
        """,
        "source_type": "clinical_guideline",
        "source_name": "GOLD",
        "source_url": "https://goldcopd.org/",
        "publication_date": "2024",
        "keywords": ["COPD", "FEV1", "bronchodilator", "LAMA", "LABA", "exacerbation"],
        "specialty": "pulmonology"
    },
    {
        "id": "ats-pneumonia-2019",
        "title": "ATS/IDSA Community-Acquired Pneumonia Guidelines 2019",
        "content": """
        Community-Acquired Pneumonia (ATS/IDSA 2019):

        DIAGNOSIS:
        - Clinical: cough, fever, dyspnea, pleuritic chest pain
        - Chest X-ray: infiltrate required for diagnosis
        - Consider CT if X-ray negative but high suspicion

        SEVERITY (CURB-65):
        - Confusion
        - Uremia (BUN >19)
        - Respiratory rate ≥30
        - Blood pressure (SBP <90 or DBP ≤60)
        - Age ≥65

        DISPOSITION by CURB-65:
        - 0-1: Outpatient
        - 2: Consider admission
        - 3-5: Admission, consider ICU if ≥4

        OUTPATIENT TREATMENT:
        - No comorbidities: amoxicillin 1g TID or doxycycline 100mg BID
        - With comorbidities: amoxicillin-clavulanate + macrolide OR respiratory fluoroquinolone

        INPATIENT (non-ICU):
        - Beta-lactam (ceftriaxone 1-2g daily) + macrolide (azithromycin 500mg daily)
        - OR respiratory fluoroquinolone alone (levofloxacin 750mg daily)

        ICU:
        - Beta-lactam + macrolide OR beta-lactam + fluoroquinolone
        - If MRSA risk: add vancomycin or linezolid
        - If Pseudomonas risk: piperacillin-tazobactam or cefepime

        DURATION: 5-7 days minimum, until afebrile 48-72 hours
        """,
        "source_type": "clinical_guideline",
        "source_name": "ATS/IDSA",
        "source_url": "https://www.atsjournals.org/doi/10.1164/rccm.201908-1581ST",
        "publication_date": "2019",
        "keywords": ["pneumonia", "CAP", "CURB-65", "antibiotics", "ceftriaxone", "azithromycin"],
        "specialty": "pulmonology"
    },
    # Diabetes/Endocrine
    {
        "id": "ada-diabetes-2024",
        "title": "ADA Standards of Care in Diabetes 2024",
        "content": """
        Diabetes Management (ADA 2024):

        DIAGNOSIS:
        - Fasting glucose ≥126 mg/dL
        - 2-hour OGTT ≥200 mg/dL
        - HbA1c ≥6.5%
        - Random glucose ≥200 mg/dL with symptoms

        A1C TARGETS:
        - General: <7%
        - Stringent (young, no hypoglycemia risk): <6.5%
        - Less stringent (elderly, comorbidities): <8%

        FIRST-LINE THERAPY:
        - Metformin 500mg daily, titrate to 1000mg BID
        - Plus lifestyle modification

        SECOND-LINE (based on comorbidities):
        - ASCVD or high risk: GLP-1 RA or SGLT2i with proven CV benefit
        - Heart failure: SGLT2i (dapagliflozin, empagliflozin)
        - CKD: SGLT2i (if eGFR ≥20), finerenone if albuminuria
        - Weight loss priority: GLP-1 RA (semaglutide, tirzepatide)

        GLP-1 RECEPTOR AGONISTS:
        - Semaglutide (Ozempic): 0.25mg weekly x4, then 0.5mg, then 1mg
        - Tirzepatide (Mounjaro): 2.5mg weekly, titrate to 15mg
        - Dulaglutide (Trulicity): 0.75mg weekly, up to 4.5mg

        MONITORING:
        - A1c every 3-6 months
        - Annual: lipids, urine albumin/creatinine, eGFR, eye exam, foot exam
        - Self-monitoring if on insulin or hypoglycemia risk
        """,
        "source_type": "clinical_guideline",
        "source_name": "ADA",
        "source_url": "https://diabetesjournals.org/care/issue/47/Supplement_1",
        "publication_date": "2024",
        "keywords": ["diabetes", "A1c", "metformin", "GLP-1", "SGLT2", "semaglutide"],
        "specialty": "endocrinology"
    },
    # Infectious Disease
    {
        "id": "idsa-uti-2010",
        "title": "IDSA Urinary Tract Infection Guidelines",
        "content": """
        Urinary Tract Infection Management (IDSA):

        UNCOMPLICATED CYSTITIS (women):
        First-line:
        - Nitrofurantoin 100mg BID x 5 days
        - TMP-SMX DS BID x 3 days (if local resistance <20%)
        - Fosfomycin 3g single dose

        Second-line:
        - Fluoroquinolone (avoid if possible due to resistance)

        COMPLICATED UTI (men, catheter, structural abnormality):
        - Fluoroquinolone 7-14 days
        - TMP-SMX if susceptible 7-14 days
        - Consider imaging if recurrent

        PYELONEPHRITIS:
        Outpatient (mild-moderate):
        - Fluoroquinolone 5-7 days
        - TMP-SMX 14 days if susceptible

        Inpatient (severe):
        - Ceftriaxone 1g daily
        - Fluoroquinolone IV
        - Broaden if ESBL risk (piperacillin-tazobactam, carbapenem)

        ASYMPTOMATIC BACTERIURIA:
        - Treat ONLY in pregnancy or pre-urologic procedure
        - Do NOT treat in elderly, diabetics, or catheterized patients

        RECURRENT UTI (≥3/year):
        - Consider prophylaxis: nitrofurantoin 50-100mg nightly
        - Post-coital prophylaxis if temporally related
        - Evaluate for structural abnormalities
        """,
        "source_type": "clinical_guideline",
        "source_name": "IDSA",
        "publication_date": "2010",
        "keywords": ["UTI", "cystitis", "pyelonephritis", "nitrofurantoin", "TMP-SMX"],
        "specialty": "infectious_disease"
    },
    # Emergency/Critical Care
    {
        "id": "ssc-sepsis-2021",
        "title": "Surviving Sepsis Campaign Guidelines 2021",
        "content": """
        Sepsis Management (Surviving Sepsis Campaign 2021):

        DEFINITIONS:
        - Sepsis: infection + organ dysfunction (SOFA ≥2)
        - Septic shock: sepsis + vasopressors + lactate >2 despite fluids

        HOUR-1 BUNDLE:
        1. Measure lactate (remeasure if >2)
        2. Obtain blood cultures before antibiotics
        3. Administer broad-spectrum antibiotics
        4. Begin 30mL/kg crystalloid for hypotension or lactate ≥4
        5. Vasopressors if hypotensive during/after resuscitation

        ANTIBIOTIC SELECTION:
        - Community-acquired: ceftriaxone + vancomycin ± metronidazole
        - Healthcare-associated: piperacillin-tazobactam + vancomycin
        - If MRSA risk: add vancomycin
        - If Pseudomonas risk: anti-pseudomonal beta-lactam

        VASOPRESSORS:
        - First-line: norepinephrine (target MAP ≥65)
        - Second-line: vasopressin 0.03 units/min
        - Third-line: epinephrine

        CORTICOSTEROIDS:
        - Consider hydrocortisone 200mg/day if ongoing vasopressor requirement

        SOURCE CONTROL:
        - Identify and control source within 6-12 hours
        - Drain abscesses, remove infected devices

        LACTATE-GUIDED RESUSCITATION:
        - Target lactate normalization
        - Reassess volume status, consider advanced monitoring
        """,
        "source_type": "clinical_guideline",
        "source_name": "Surviving Sepsis Campaign",
        "source_url": "https://www.sccm.org/SurvivingSepsisCampaign",
        "publication_date": "2021",
        "keywords": ["sepsis", "septic shock", "lactate", "norepinephrine", "antibiotics", "hour-1 bundle"],
        "specialty": "critical_care"
    },
    # Neurology
    {
        "id": "aha-stroke-2019",
        "title": "AHA Acute Ischemic Stroke Guidelines 2019",
        "content": """
        Acute Ischemic Stroke (AHA/ASA 2019):

        INITIAL ASSESSMENT:
        - Time of symptom onset (last known well)
        - NIHSS score
        - Non-contrast CT head immediately
        - Glucose, CBC, BMP, coagulation studies

        IV ALTEPLASE (tPA):
        Window: within 4.5 hours of last known well

        Inclusion:
        - Ischemic stroke with measurable deficit
        - Age ≥18

        Contraindications:
        - Active bleeding
        - Recent major surgery (14 days)
        - Recent stroke (3 months)
        - Platelet <100,000
        - INR >1.7
        - Uncontrolled BP (>185/110 despite treatment)

        Dosing: 0.9 mg/kg (max 90mg), 10% bolus, rest over 60 minutes

        MECHANICAL THROMBECTOMY:
        Window: up to 24 hours (with advanced imaging selection)

        Criteria:
        - Large vessel occlusion (ICA, M1, basilar)
        - NIHSS ≥6
        - Pre-stroke mRS 0-1
        - ASPECTS ≥6 on CT

        BLOOD PRESSURE:
        - If receiving tPA: <180/105 for 24 hours
        - No tPA: permissive hypertension (treat if >220/120)

        SECONDARY PREVENTION:
        - Antiplatelet within 24-48 hours (aspirin 325mg)
        - Statin (high-intensity)
        - Address risk factors: HTN, DM, smoking, afib
        """,
        "source_type": "aha_guideline",
        "source_name": "AHA/ASA",
        "source_url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000211",
        "publication_date": "2019",
        "keywords": ["stroke", "tPA", "alteplase", "thrombectomy", "NIHSS", "LVO"],
        "specialty": "neurology"
    },
    # Preventive Care
    {
        "id": "uspstf-screening-2024",
        "title": "USPSTF Preventive Screening Recommendations",
        "content": """
        USPSTF Screening Guidelines (Grade A and B):

        CANCER SCREENING:

        Breast Cancer:
        - Mammography every 2 years, ages 40-74 (Grade B)
        - Earlier/more frequent if high risk

        Cervical Cancer:
        - Pap smear every 3 years, ages 21-29
        - Pap + HPV co-testing every 5 years, ages 30-65
        - Can stop at 65 if adequate prior screening

        Colorectal Cancer:
        - Ages 45-75 (Grade A ages 50-75, Grade B ages 45-49)
        - Options: colonoscopy q10y, FIT annually, Cologuard q3y

        Lung Cancer:
        - Low-dose CT annually, ages 50-80
        - ≥20 pack-year history, current smoker or quit <15 years

        Prostate Cancer:
        - Shared decision-making ages 55-69
        - Not recommended after 70

        CARDIOVASCULAR:
        - Aspirin: No longer routinely recommended for primary prevention
        - Statin: If 10-year ASCVD risk ≥10% (ages 40-75)
        - BP screening: every 3-5 years (normal), annually if elevated

        INFECTIOUS DISEASE:
        - HIV: ages 15-65 (at least once)
        - Hepatitis C: ages 18-79 (once)
        - Hepatitis B: high-risk populations

        OTHER:
        - Depression screening: all adults
        - Diabetes screening: ages 35-70 if overweight/obese
        - Osteoporosis: women ≥65, or postmenopausal with risk factors
        """,
        "source_type": "uspstf",
        "source_name": "USPSTF",
        "source_url": "https://www.uspreventiveservicestaskforce.org/",
        "publication_date": "2024",
        "keywords": ["screening", "mammography", "colonoscopy", "LDCT", "preventive care"],
        "specialty": "primary_care"
    },
    # Drug Information
    {
        "id": "warfarin-management",
        "title": "Warfarin Management and INR Targets",
        "content": """
        Warfarin Anticoagulation Management:

        INR TARGETS:
        - Afib, DVT/PE, bioprosthetic valve: 2.0-3.0
        - Mechanical mitral valve: 2.5-3.5
        - Mechanical aortic valve: 2.0-3.0

        INITIATING WARFARIN:
        - Start 5mg daily (2.5mg if elderly, low weight, liver disease)
        - Check INR day 3-4
        - Typical maintenance: 2-10mg daily

        DOSE ADJUSTMENTS:
        INR 1.5-1.9: Increase weekly dose 5-10%
        INR 3.1-3.5: Decrease weekly dose 5-10%
        INR 3.6-4.0: Hold 1 dose, decrease weekly 10-15%
        INR >4.0: Hold, recheck in 1-2 days, consider vitamin K

        DRUG INTERACTIONS (increase INR):
        - Antibiotics: TMP-SMX, metronidazole, fluconazole
        - Amiodarone (reduce warfarin dose 30-50%)
        - NSAIDs, aspirin
        - Acetaminophen (high doses)

        DRUG INTERACTIONS (decrease INR):
        - Rifampin, carbamazepine, phenytoin
        - Vitamin K rich foods (consistent intake)

        REVERSAL:
        - Vitamin K 2.5-5mg PO for non-urgent
        - Vitamin K 10mg IV + 4-factor PCC for urgent
        - FFP if PCC unavailable

        BRIDGING:
        - High risk (mechanical valve, recent VTE): bridge with LMWH
        - Low risk (afib, remote VTE): usually no bridging needed
        """,
        "source_type": "drug_info",
        "source_name": "Clinical Pharmacology",
        "publication_date": "2023",
        "keywords": ["warfarin", "INR", "anticoagulation", "vitamin K", "reversal"],
        "specialty": "hematology"
    },
    {
        "id": "opioid-equivalents",
        "title": "Opioid Equianalgesic Dosing",
        "content": """
        Opioid Equivalency and Conversion:

        ORAL MORPHINE EQUIVALENTS (OME):
        Morphine PO: 30mg = 1 OME unit
        Morphine IV: 10mg = 30mg PO

        CONVERSION FACTORS (to oral morphine):
        - Oxycodone: 1.5x (20mg oxycodone = 30mg morphine)
        - Hydrocodone: 1x (30mg hydrocodone = 30mg morphine)
        - Hydromorphone: 4x (7.5mg PO = 30mg morphine)
        - Fentanyl patch: 25mcg/hr ≈ 60-90mg morphine daily
        - Tramadol: 0.1x (300mg tramadol = 30mg morphine)
        - Codeine: 0.15x (200mg codeine = 30mg morphine)
        - Methadone: Variable (use conversion tables)

        HIGH DOSE THRESHOLD:
        ≥50 MME/day: increased overdose risk
        ≥90 MME/day: avoid or carefully justify

        CONVERSION TIPS:
        - Reduce calculated dose by 25-50% for incomplete cross-tolerance
        - Start lower for elderly, renal/hepatic impairment
        - Use lower end of range when rotating opioids

        NALOXONE CO-PRESCRIBING:
        Indicated if:
        - ≥50 MME/day
        - Concurrent benzodiazepine
        - History of overdose
        - Substance use disorder
        - Renal/hepatic impairment
        """,
        "source_type": "drug_info",
        "source_name": "CDC Opioid Guidelines",
        "publication_date": "2022",
        "keywords": ["opioid", "morphine equivalent", "conversion", "naloxone", "pain management"],
        "specialty": "pain_management"
    }
]


# ═══════════════════════════════════════════════════════════════════════════════
# RAG ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class RAGEngine:
    """
    Retrieval-Augmented Generation engine for medical knowledge.
    Uses ChromaDB for vector storage and sentence-transformers for embeddings.
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.collection_name = "medical_knowledge"
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize the RAG engine with ChromaDB and embedding model."""
        if not CHROMADB_AVAILABLE:
            print("ChromaDB not available. RAG features disabled.")
            return False

        if not EMBEDDINGS_AVAILABLE:
            print("Sentence-transformers not available. RAG features disabled.")
            return False

        try:
            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(path=self.persist_directory)

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "MDx Vision Medical Knowledge Base"}
            )

            # Initialize embedding model (medical-optimized model)
            # Using all-MiniLM-L6-v2 for balance of speed and quality
            # For production, consider: pritamdeka/S-PubMedBert-MS-MARCO
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            self.initialized = True
            print(f"RAG engine initialized. Documents in collection: {self.collection.count()}")

            # Ingest built-in guidelines if collection is empty
            if self.collection.count() == 0:
                self._ingest_built_in_guidelines()

            return True

        except Exception as e:
            print(f"Failed to initialize RAG engine: {e}")
            return False

    def _ingest_built_in_guidelines(self):
        """Ingest the built-in clinical guidelines into the vector database."""
        print("Ingesting built-in clinical guidelines...")

        for guideline in BUILT_IN_GUIDELINES:
            doc = MedicalDocument(
                id=guideline["id"],
                title=guideline["title"],
                content=guideline["content"],
                source_type=SourceType(guideline["source_type"]),
                source_name=guideline.get("source_name"),
                source_url=guideline.get("source_url"),
                publication_date=guideline.get("publication_date"),
                keywords=guideline.get("keywords", []),
                specialty=guideline.get("specialty")
            )
            self.add_document(doc)

        print(f"Ingested {len(BUILT_IN_GUIDELINES)} guidelines. Total documents: {self.collection.count()}")

    def add_document(self, doc: MedicalDocument) -> bool:
        """Add a document to the knowledge base."""
        if not self.initialized:
            return False

        try:
            # Generate embedding
            embedding = self.embedding_model.encode(doc.content).tolist()

            # Prepare metadata
            metadata = {
                "title": doc.title,
                "source_type": doc.source_type.value,
                "source_name": doc.source_name or "",
                "source_url": doc.source_url or "",
                "publication_date": doc.publication_date or "",
                "specialty": doc.specialty or "",
                "keywords": ",".join(doc.keywords) if doc.keywords else ""
            }

            # Add to collection
            self.collection.upsert(
                ids=[doc.id],
                embeddings=[embedding],
                documents=[doc.content],
                metadatas=[metadata]
            )

            return True

        except Exception as e:
            print(f"Failed to add document: {e}")
            return False

    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        specialty_filter: Optional[str] = None,
        min_relevance: float = 0.3
    ) -> List[RetrievedContext]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: The search query
            n_results: Maximum number of results to return
            specialty_filter: Optional specialty to filter by
            min_relevance: Minimum relevance score (0-1)

        Returns:
            List of RetrievedContext objects
        """
        if not self.initialized:
            return []

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Build where filter
            where_filter = None
            if specialty_filter:
                where_filter = {"specialty": specialty_filter}

            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Process results
            contexts = []
            if results and results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    distance = results['distances'][0][i]
                    # Convert L2 distance to similarity (rough approximation)
                    similarity = 1 / (1 + distance)

                    if similarity < min_relevance:
                        continue

                    metadata = results['metadatas'][0][i]
                    content = results['documents'][0][i]

                    doc = MedicalDocument(
                        id=doc_id,
                        title=metadata.get('title', ''),
                        content=content,
                        source_type=SourceType(metadata.get('source_type', 'custom')),
                        source_name=metadata.get('source_name'),
                        source_url=metadata.get('source_url'),
                        publication_date=metadata.get('publication_date'),
                        keywords=metadata.get('keywords', '').split(',') if metadata.get('keywords') else None,
                        specialty=metadata.get('specialty')
                    )

                    contexts.append(RetrievedContext(
                        document=doc,
                        relevance_score=similarity,
                        matched_chunk=content[:500]  # First 500 chars as preview
                    ))

            # Sort by relevance
            contexts.sort(key=lambda x: x.relevance_score, reverse=True)
            return contexts

        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    def generate_augmented_prompt(
        self,
        query: str,
        retrieved_contexts: List[RetrievedContext],
        include_citations: bool = True
    ) -> str:
        """
        Generate an augmented prompt with retrieved context.

        Args:
            query: The original query
            retrieved_contexts: Retrieved documents
            include_citations: Whether to include citation instructions

        Returns:
            Augmented prompt string
        """
        if not retrieved_contexts:
            return query

        # Build context section
        context_parts = []
        for i, ctx in enumerate(retrieved_contexts, 1):
            source_info = f"[{i}] {ctx.document.source_name or ctx.document.source_type.value}"
            if ctx.document.publication_date:
                source_info += f" ({ctx.document.publication_date})"

            context_parts.append(f"""
{source_info}:
{ctx.document.content}
""")

        context_str = "\n---\n".join(context_parts)

        # Build augmented prompt
        augmented_prompt = f"""Use the following medical reference sources to inform your response.
Cite sources using [1], [2], etc. when referencing specific information.

REFERENCE SOURCES:
{context_str}

---

QUERY: {query}

Provide a clinically accurate response based on the reference sources above. Include citations."""

        return augmented_prompt

    def get_statistics(self) -> Dict:
        """Get statistics about the knowledge base."""
        if not self.initialized:
            return {"initialized": False}

        return {
            "initialized": True,
            "document_count": self.collection.count(),
            "persist_directory": self.persist_directory,
            "embedding_model": "all-MiniLM-L6-v2"
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL RAG ENGINE INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Initialize on import
rag_engine = RAGEngine()


def initialize_rag() -> bool:
    """Initialize the global RAG engine."""
    return rag_engine.initialize()


def retrieve_context(
    query: str,
    n_results: int = 5,
    specialty: Optional[str] = None
) -> List[RetrievedContext]:
    """Retrieve relevant context for a query."""
    return rag_engine.retrieve(query, n_results, specialty)


def get_augmented_prompt(query: str, n_results: int = 3) -> Tuple[str, List[Dict]]:
    """
    Get an augmented prompt with retrieved context.

    Returns:
        Tuple of (augmented_prompt, list of source dicts for citation)
    """
    contexts = rag_engine.retrieve(query, n_results)

    if not contexts:
        return query, []

    prompt = rag_engine.generate_augmented_prompt(query, contexts)

    sources = []
    for i, ctx in enumerate(contexts, 1):
        sources.append({
            "index": i,
            "title": ctx.document.title,
            "source_name": ctx.document.source_name,
            "source_url": ctx.document.source_url,
            "publication_date": ctx.document.publication_date,
            "relevance_score": round(ctx.relevance_score, 3)
        })

    return prompt, sources


def add_custom_document(
    title: str,
    content: str,
    source_type: str = "custom",
    source_name: Optional[str] = None,
    source_url: Optional[str] = None,
    specialty: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> bool:
    """Add a custom document to the knowledge base."""
    doc_id = hashlib.md5(f"{title}{content}".encode()).hexdigest()[:16]

    doc = MedicalDocument(
        id=doc_id,
        title=title,
        content=content,
        source_type=SourceType(source_type) if source_type in [e.value for e in SourceType] else SourceType.CUSTOM,
        source_name=source_name,
        source_url=source_url,
        specialty=specialty,
        keywords=keywords
    )

    return rag_engine.add_document(doc)


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE MANAGER (Feature #89)
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeManager:
    """
    Manages the medical knowledge base lifecycle:
    - Version control for guidelines
    - PubMed article ingestion
    - Citation feedback tracking
    - Specialty collections
    - Conflict detection
    """

    def __init__(self, rag_engine: RAGEngine, data_dir: str = "./data/knowledge"):
        self.rag_engine = rag_engine
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Storage files
        self.versions_file = self.data_dir / "versions.json"
        self.feedback_file = self.data_dir / "feedback.json"
        self.collections_file = self.data_dir / "collections.json"
        self.conflicts_file = self.data_dir / "conflicts.json"
        self.analytics_file = self.data_dir / "analytics.json"

        # Load existing data
        self.versions: Dict[str, GuidelineVersion] = self._load_versions()
        self.feedback: List[CitationFeedback] = self._load_feedback()
        self.collections: Dict[str, SpecialtyCollection] = self._load_collections()
        self.conflicts: List[ConflictAlert] = self._load_conflicts()
        self.analytics: Dict[str, Any] = self._load_analytics()

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────────

    def _load_versions(self) -> Dict[str, GuidelineVersion]:
        if self.versions_file.exists():
            with open(self.versions_file) as f:
                data = json.load(f)
                return {k: GuidelineVersion(**v) for k, v in data.items()}
        return {}

    def _save_versions(self):
        with open(self.versions_file, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.versions.items()}, f, indent=2)

    def _load_feedback(self) -> List[CitationFeedback]:
        if self.feedback_file.exists():
            with open(self.feedback_file) as f:
                return [CitationFeedback(**item) for item in json.load(f)]
        return []

    def _save_feedback(self):
        with open(self.feedback_file, 'w') as f:
            json.dump([asdict(fb) for fb in self.feedback], f, indent=2)

    def _load_collections(self) -> Dict[str, SpecialtyCollection]:
        if self.collections_file.exists():
            with open(self.collections_file) as f:
                data = json.load(f)
                return {k: SpecialtyCollection(**v) for k, v in data.items()}
        return {}

    def _save_collections(self):
        with open(self.collections_file, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.collections.items()}, f, indent=2)

    def _load_conflicts(self) -> List[ConflictAlert]:
        if self.conflicts_file.exists():
            with open(self.conflicts_file) as f:
                return [ConflictAlert(**item) for item in json.load(f)]
        return []

    def _save_conflicts(self):
        with open(self.conflicts_file, 'w') as f:
            json.dump([asdict(c) for c in self.conflicts], f, indent=2)

    def _load_analytics(self) -> Dict[str, Any]:
        if self.analytics_file.exists():
            with open(self.analytics_file) as f:
                return json.load(f)
        return {
            "total_queries": 0,
            "total_retrievals": 0,
            "feedback_count": 0,
            "top_documents": {},
            "specialty_usage": {},
            "last_updated": datetime.now().isoformat()
        }

    def _save_analytics(self):
        self.analytics["last_updated"] = datetime.now().isoformat()
        with open(self.analytics_file, 'w') as f:
            json.dump(self.analytics, f, indent=2)

    # ─────────────────────────────────────────────────────────────────────────────
    # GUIDELINE VERSIONING
    # ─────────────────────────────────────────────────────────────────────────────

    def add_guideline_version(
        self,
        guideline_id: str,
        version_number: str,
        publication_date: str,
        content: str,
        title: str,
        source_name: str,
        supersedes_id: Optional[str] = None,
        change_summary: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Add a new version of a clinical guideline.
        Automatically deprecates the previous version.
        """
        version_id = f"{guideline_id}-v{version_number}"

        # Mark previous version as superseded
        if supersedes_id and supersedes_id in self.versions:
            old_version = self.versions[supersedes_id]
            old_version.status = GuidelineStatus.SUPERSEDED
            old_version.superseded_by = version_id

        # Create new version
        new_version = GuidelineVersion(
            version_id=version_id,
            guideline_id=guideline_id,
            version_number=version_number,
            publication_date=publication_date,
            effective_date=datetime.now().strftime("%Y-%m-%d"),
            status=GuidelineStatus.CURRENT,
            supersedes=supersedes_id,
            change_summary=change_summary
        )

        self.versions[version_id] = new_version
        self._save_versions()

        # Add document to RAG with version info
        doc = MedicalDocument(
            id=version_id,
            title=f"{title} (v{version_number})",
            content=content,
            source_type=SourceType.CLINICAL_GUIDELINE,
            source_name=source_name,
            publication_date=publication_date,
            version=version_number,
            status=GuidelineStatus.CURRENT,
            supersedes_id=supersedes_id,
            **kwargs
        )

        success = self.rag_engine.add_document(doc)
        return success, version_id

    def deprecate_guideline(self, document_id: str, reason: str) -> bool:
        """Mark a guideline as deprecated (no longer recommended)."""
        if document_id in self.versions:
            self.versions[document_id].status = GuidelineStatus.DEPRECATED
            self._save_versions()
            return True
        return False

    def get_current_version(self, guideline_id: str) -> Optional[str]:
        """Get the current version ID for a guideline."""
        for version_id, version in self.versions.items():
            if version.guideline_id == guideline_id and version.status == GuidelineStatus.CURRENT:
                return version_id
        return None

    def get_version_history(self, guideline_id: str) -> List[GuidelineVersion]:
        """Get version history for a guideline."""
        return [
            v for v in self.versions.values()
            if v.guideline_id == guideline_id
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # PUBMED INGESTION
    # ─────────────────────────────────────────────────────────────────────────────

    async def search_pubmed(
        self,
        query: str,
        max_results: int = 10,
        min_date: Optional[str] = None
    ) -> List[PubMedArticle]:
        """
        Search PubMed for relevant articles.
        Uses NCBI E-utilities API (free, no API key required for <3 requests/sec).
        """
        if not HTTPX_AVAILABLE:
            print("httpx not available for PubMed API calls")
            return []

        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

        # Build date filter
        date_filter = ""
        if min_date:
            date_filter = f"&mindate={min_date}&datetype=pdat"

        # Search for PMIDs
        search_url = f"{base_url}/esearch.fcgi?db=pubmed&term={query}&retmax={max_results}&retmode=json{date_filter}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                search_response = await client.get(search_url)
                search_data = search_response.json()
                pmids = search_data.get("esearchresult", {}).get("idlist", [])

                if not pmids:
                    return []

                # Fetch article details
                fetch_url = f"{base_url}/efetch.fcgi?db=pubmed&id={','.join(pmids)}&retmode=xml"
                fetch_response = await client.get(fetch_url)

                # Parse XML (simplified - in production use proper XML parser)
                articles = self._parse_pubmed_xml(fetch_response.text, pmids)
                return articles

            except Exception as e:
                print(f"PubMed search error: {e}")
                return []

    def _parse_pubmed_xml(self, xml_text: str, pmids: List[str]) -> List[PubMedArticle]:
        """Parse PubMed XML response (simplified version)."""
        # For production, use xml.etree.ElementTree or lxml
        # This is a simplified regex-based parser for demo
        import re
        articles = []

        for pmid in pmids:
            try:
                # Extract title
                title_match = re.search(r'<ArticleTitle>([^<]+)</ArticleTitle>', xml_text)
                title = title_match.group(1) if title_match else "Unknown Title"

                # Extract abstract
                abstract_match = re.search(r'<AbstractText[^>]*>([^<]+)</AbstractText>', xml_text)
                abstract = abstract_match.group(1) if abstract_match else ""

                # Extract journal
                journal_match = re.search(r'<Title>([^<]+)</Title>', xml_text)
                journal = journal_match.group(1) if journal_match else "Unknown Journal"

                articles.append(PubMedArticle(
                    pmid=pmid,
                    title=title,
                    abstract=abstract,
                    authors=[],
                    journal=journal,
                    publication_date=datetime.now().strftime("%Y"),
                    mesh_terms=[]
                ))
            except Exception:
                continue

        return articles

    async def ingest_pubmed_articles(
        self,
        query: str,
        max_articles: int = 10,
        specialty: Optional[str] = None
    ) -> Tuple[int, List[str]]:
        """
        Search PubMed and ingest relevant articles into the knowledge base.

        Returns:
            Tuple of (count of articles ingested, list of PMIDs)
        """
        articles = await self.search_pubmed(query, max_articles)

        ingested_pmids = []
        for article in articles:
            if not article.abstract:
                continue

            doc = MedicalDocument(
                id=f"pubmed-{article.pmid}",
                title=article.title,
                content=f"{article.title}\n\n{article.abstract}",
                source_type=SourceType.PUBMED_ABSTRACT,
                source_name=article.journal,
                source_url=f"https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/",
                publication_date=article.publication_date,
                pmid=article.pmid,
                specialty=specialty,
                keywords=article.mesh_terms
            )

            if self.rag_engine.add_document(doc):
                ingested_pmids.append(article.pmid)

        return len(ingested_pmids), ingested_pmids

    # ─────────────────────────────────────────────────────────────────────────────
    # OPENFDA DRUG LABEL INGESTION (Tier 1)
    # ─────────────────────────────────────────────────────────────────────────────

    async def search_openfda(
        self,
        drug_name: str,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search OpenFDA for drug label information.
        Free API, no key required. https://api.fda.gov
        """
        if not HTTPX_AVAILABLE:
            print("httpx not available for OpenFDA API calls")
            return []

        base_url = "https://api.fda.gov/drug/label.json"
        # Search by generic or brand name
        search_query = f'(openfda.generic_name:"{drug_name}"+openfda.brand_name:"{drug_name}")'
        url = f"{base_url}?search={search_query}&limit={max_results}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    return []
                data = response.json()
                return data.get("results", [])
            except Exception as e:
                print(f"OpenFDA search error: {e}")
                return []

    async def ingest_openfda_drug(
        self,
        drug_name: str,
        max_labels: int = 3
    ) -> Tuple[int, List[str]]:
        """
        Search OpenFDA and ingest drug labels into the knowledge base.
        Extracts: indications, contraindications, warnings, dosing, interactions, adverse reactions.

        Returns:
            Tuple of (count ingested, list of drug label IDs)
        """
        results = await self.search_openfda(drug_name, max_labels)
        ingested_ids = []

        for result in results:
            try:
                # Extract OpenFDA metadata
                openfda = result.get("openfda", {})
                generic_names = openfda.get("generic_name", ["Unknown"])
                brand_names = openfda.get("brand_name", [])
                label_id = result.get("id", hashlib.md5(drug_name.encode()).hexdigest()[:12])

                # Build comprehensive drug content from label sections
                sections = []
                section_map = {
                    "indications_and_usage": "INDICATIONS AND USAGE",
                    "contraindications": "CONTRAINDICATIONS",
                    "warnings_and_cautions": "WARNINGS AND PRECAUTIONS",
                    "warnings": "WARNINGS",
                    "adverse_reactions": "ADVERSE REACTIONS",
                    "drug_interactions": "DRUG INTERACTIONS",
                    "dosage_and_administration": "DOSAGE AND ADMINISTRATION",
                    "boxed_warning": "BLACK BOX WARNING",
                    "pregnancy": "PREGNANCY",
                    "nursing_mothers": "NURSING MOTHERS",
                    "pediatric_use": "PEDIATRIC USE",
                    "geriatric_use": "GERIATRIC USE",
                    "overdosage": "OVERDOSAGE",
                    "clinical_pharmacology": "CLINICAL PHARMACOLOGY",
                }

                for key, heading in section_map.items():
                    value = result.get(key, [])
                    if value:
                        text = value[0] if isinstance(value, list) else value
                        # Truncate very long sections
                        if len(text) > 2000:
                            text = text[:2000] + "..."
                        sections.append(f"## {heading}\n{text}")

                if not sections:
                    continue

                generic = generic_names[0] if generic_names else drug_name
                brand = f" ({brand_names[0]})" if brand_names else ""
                title = f"FDA Drug Label: {generic}{brand}"
                content = f"# {title}\n\n" + "\n\n".join(sections)

                doc = MedicalDocument(
                    id=f"openfda-{label_id}",
                    title=title,
                    content=content,
                    source_type=SourceType.OPENFDA,
                    source_name="U.S. FDA / OpenFDA",
                    source_url=f"https://api.fda.gov/drug/label.json?search=id:{label_id}",
                    publication_date=result.get("effective_time", ""),
                    keywords=[generic] + brand_names,
                    specialty="pharmacology"
                )

                if self.rag_engine.add_document(doc):
                    ingested_ids.append(label_id)

            except Exception as e:
                print(f"OpenFDA ingestion error for {drug_name}: {e}")
                continue

        return len(ingested_ids), ingested_ids

    async def ingest_openfda_batch(
        self,
        drug_names: List[str]
    ) -> Dict[str, Tuple[int, List[str]]]:
        """Ingest multiple drugs from OpenFDA."""
        results = {}
        for drug in drug_names:
            count, ids = await self.ingest_openfda_drug(drug)
            results[drug] = (count, ids)
            # Rate limit: OpenFDA allows 240 requests/min without key
            await asyncio.sleep(0.3)
        return results

    # ─────────────────────────────────────────────────────────────────────────────
    # CLINICALTRIALS.GOV INGESTION (Tier 1)
    # ─────────────────────────────────────────────────────────────────────────────

    async def search_clinical_trials(
        self,
        condition: str,
        max_results: int = 10,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Search ClinicalTrials.gov API v2 for trials.
        Free API, no key required. https://clinicaltrials.gov/api/v2

        Args:
            condition: Disease/condition to search
            max_results: Max trials to return
            status: Filter by status (RECRUITING, COMPLETED, etc.)
        """
        if not HTTPX_AVAILABLE:
            print("httpx not available for ClinicalTrials.gov API calls")
            return []

        base_url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.cond": condition,
            "pageSize": max_results,
            "format": "json",
            "fields": "NCTId,BriefTitle,OfficialTitle,BriefSummary,Condition,InterventionName,Phase,OverallStatus,StartDate,PrimaryCompletionDate,LeadSponsorName,LocationFacility,LocationCity,LocationState,EligibilityCriteria",
        }
        if status:
            params["filter.overallStatus"] = status

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(base_url, params=params)
                if response.status_code != 200:
                    return []
                data = response.json()
                return data.get("studies", [])
            except Exception as e:
                print(f"ClinicalTrials.gov search error: {e}")
                return []

    async def ingest_clinical_trials(
        self,
        condition: str,
        max_trials: int = 10,
        status: Optional[str] = "RECRUITING",
        specialty: Optional[str] = None
    ) -> Tuple[int, List[str]]:
        """
        Search ClinicalTrials.gov and ingest trials into the knowledge base.

        Returns:
            Tuple of (count ingested, list of NCT IDs)
        """
        studies = await self.search_clinical_trials(condition, max_trials, status)
        ingested_ncts = []

        for study in studies:
            try:
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                desc_module = protocol.get("descriptionModule", {})
                status_module = protocol.get("statusModule", {})
                design_module = protocol.get("designModule", {})
                arms_module = protocol.get("armsInterventionsModule", {})
                eligibility_module = protocol.get("eligibilityModule", {})
                sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
                contacts_module = protocol.get("contactsLocationsModule", {})

                nct_id = id_module.get("nctId", "")
                if not nct_id:
                    continue

                title = id_module.get("officialTitle") or id_module.get("briefTitle", "Unknown Trial")
                summary = desc_module.get("briefSummary", "")
                overall_status = status_module.get("overallStatus", "")
                phases = design_module.get("phases", [])

                # Extract interventions
                interventions = []
                for arm in arms_module.get("interventions", []):
                    name = arm.get("name", "")
                    itype = arm.get("type", "")
                    if name:
                        interventions.append(f"{itype}: {name}" if itype else name)

                # Extract locations (first 5)
                locations = []
                for loc in (contacts_module.get("locations", []) or [])[:5]:
                    facility = loc.get("facility", "")
                    city = loc.get("city", "")
                    state = loc.get("state", "")
                    if facility:
                        locations.append(f"{facility}, {city}, {state}".strip(", "))

                # Extract sponsor
                lead_sponsor = sponsor_module.get("leadSponsor", {}).get("name", "")

                # Extract eligibility
                eligibility = eligibility_module.get("eligibilityCriteria", "")
                if len(eligibility) > 1500:
                    eligibility = eligibility[:1500] + "..."

                # Build content
                content_parts = [
                    f"# Clinical Trial: {title}",
                    f"**NCT ID:** {nct_id}",
                    f"**Status:** {overall_status}",
                    f"**Phase:** {', '.join(phases) if phases else 'N/A'}",
                    f"**Sponsor:** {lead_sponsor}",
                ]
                if interventions:
                    content_parts.append(f"**Interventions:** {'; '.join(interventions)}")
                if summary:
                    content_parts.append(f"\n## Summary\n{summary}")
                if locations:
                    content_parts.append(f"\n## Locations\n" + "\n".join(f"- {loc}" for loc in locations))
                if eligibility:
                    content_parts.append(f"\n## Eligibility Criteria\n{eligibility}")

                content = "\n".join(content_parts)

                conditions = protocol.get("conditionsModule", {}).get("conditions", [])

                doc = MedicalDocument(
                    id=f"trial-{nct_id}",
                    title=f"Clinical Trial {nct_id}: {title[:100]}",
                    content=content,
                    source_type=SourceType.CLINICAL_TRIAL,
                    source_name="ClinicalTrials.gov",
                    source_url=f"https://clinicaltrials.gov/study/{nct_id}",
                    publication_date=status_module.get("studyFirstPostDateStruct", {}).get("date", ""),
                    keywords=conditions,
                    specialty=specialty
                )

                if self.rag_engine.add_document(doc):
                    ingested_ncts.append(nct_id)

            except Exception as e:
                print(f"ClinicalTrials.gov ingestion error: {e}")
                continue

        return len(ingested_ncts), ingested_ncts

    # ─────────────────────────────────────────────────────────────────────────────
    # UMLS / RXNORM TERMINOLOGY INGESTION (Tier 1)
    # ─────────────────────────────────────────────────────────────────────────────

    async def search_rxnorm(
        self,
        drug_name: str
    ) -> List[Dict]:
        """
        Search RxNorm for drug information (free, no API key).
        https://rxnav.nlm.nih.gov/REST

        Returns drug concepts with RxCUI, name, and related info.
        """
        if not HTTPX_AVAILABLE:
            print("httpx not available for RxNorm API calls")
            return []

        base_url = "https://rxnav.nlm.nih.gov/REST"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get RxCUI for the drug
                approx_url = f"{base_url}/approximateTerm.json?term={drug_name}&maxEntries=3"
                response = await client.get(approx_url)
                if response.status_code != 200:
                    return []

                data = response.json()
                candidates = data.get("approximateGroup", {}).get("candidate", [])
                if not candidates:
                    return []

                results = []
                for candidate in candidates[:3]:
                    rxcui = candidate.get("rxcui", "")
                    if not rxcui:
                        continue

                    # Get drug properties
                    props_url = f"{base_url}/rxcui/{rxcui}/allProperties.json?prop=all"
                    props_response = await client.get(props_url)
                    properties = {}
                    if props_response.status_code == 200:
                        props_data = props_response.json()
                        for prop in props_data.get("propConceptGroup", {}).get("propConcept", []):
                            properties[prop.get("propName", "")] = prop.get("propValue", "")

                    # Get drug interactions
                    interactions_url = f"{base_url}/interaction/interaction.json?rxcui={rxcui}&sources=DrugBank"
                    interactions_response = await client.get(interactions_url)
                    interactions = []
                    if interactions_response.status_code == 200:
                        int_data = interactions_response.json()
                        for group in int_data.get("interactionTypeGroup", []):
                            for itype in group.get("interactionType", []):
                                for pair in itype.get("interactionPair", []):
                                    desc = pair.get("description", "")
                                    if desc:
                                        interactions.append(desc)

                    results.append({
                        "rxcui": rxcui,
                        "name": candidate.get("name", drug_name),
                        "score": candidate.get("score", ""),
                        "properties": properties,
                        "interactions": interactions[:20]  # Limit to 20
                    })

                    await asyncio.sleep(0.2)  # Rate limit

                return results

            except Exception as e:
                print(f"RxNorm search error: {e}")
                return []

    async def ingest_rxnorm_drug(
        self,
        drug_name: str
    ) -> Tuple[int, List[str]]:
        """
        Search RxNorm and ingest drug terminology + interactions into knowledge base.

        Returns:
            Tuple of (count ingested, list of RxCUI IDs)
        """
        results = await self.search_rxnorm(drug_name)
        ingested_ids = []

        for result in results:
            try:
                rxcui = result["rxcui"]
                name = result["name"]
                properties = result["properties"]
                interactions = result["interactions"]

                # Build content
                content_parts = [
                    f"# Drug: {name}",
                    f"**RxCUI:** {rxcui}",
                ]

                # Add properties
                useful_props = ["TTY", "RxNorm Name", "AVAILABLE_STRENGTH", "DOSE_FORM", "ROUTE"]
                for prop_name in useful_props:
                    if prop_name in properties:
                        content_parts.append(f"**{prop_name}:** {properties[prop_name]}")

                # Add all other properties
                for key, val in properties.items():
                    if key not in useful_props and val:
                        content_parts.append(f"**{key}:** {val}")

                # Add interactions
                if interactions:
                    content_parts.append(f"\n## Drug Interactions ({len(interactions)} found)")
                    for interaction in interactions:
                        content_parts.append(f"- {interaction}")

                content = "\n".join(content_parts)

                doc = MedicalDocument(
                    id=f"rxnorm-{rxcui}",
                    title=f"RxNorm Drug: {name} (RxCUI: {rxcui})",
                    content=content,
                    source_type=SourceType.UMLS_TERMINOLOGY,
                    source_name="NLM RxNorm / DrugBank",
                    source_url=f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}",
                    keywords=[name, drug_name],
                    specialty="pharmacology"
                )

                if self.rag_engine.add_document(doc):
                    ingested_ids.append(rxcui)

            except Exception as e:
                print(f"RxNorm ingestion error for {drug_name}: {e}")
                continue

        return len(ingested_ids), ingested_ids

    async def ingest_rxnorm_batch(
        self,
        drug_names: List[str]
    ) -> Dict[str, Tuple[int, List[str]]]:
        """Ingest multiple drugs from RxNorm."""
        results = {}
        for drug in drug_names:
            count, ids = await self.ingest_rxnorm_drug(drug)
            results[drug] = (count, ids)
            await asyncio.sleep(0.5)  # Rate limit for RxNorm
        return results

    # ─────────────────────────────────────────────────────────────────────────────
    # CITATION FEEDBACK
    # ─────────────────────────────────────────────────────────────────────────────

    def record_feedback(
        self,
        document_id: str,
        query: str,
        rating: str,
        comment: Optional[str] = None,
        clinician_specialty: Optional[str] = None
    ) -> str:
        """Record clinician feedback on a citation's helpfulness."""
        feedback_id = hashlib.md5(
            f"{document_id}{query}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        feedback = CitationFeedback(
            feedback_id=feedback_id,
            document_id=document_id,
            query=query,
            rating=FeedbackRating(rating),
            comment=comment,
            clinician_specialty=clinician_specialty
        )

        self.feedback.append(feedback)
        self._save_feedback()

        # Update analytics
        self.analytics["feedback_count"] = len(self.feedback)
        self._save_analytics()

        return feedback_id

    def get_document_feedback_summary(self, document_id: str) -> Dict:
        """Get feedback summary for a document."""
        doc_feedback = [f for f in self.feedback if f.document_id == document_id]

        ratings_count = {}
        for fb in doc_feedback:
            rating = fb.rating.value
            ratings_count[rating] = ratings_count.get(rating, 0) + 1

        helpful = ratings_count.get("very_helpful", 0) + ratings_count.get("helpful", 0)
        not_helpful = ratings_count.get("not_helpful", 0) + ratings_count.get("incorrect", 0)
        total = len(doc_feedback)

        return {
            "document_id": document_id,
            "total_feedback": total,
            "ratings_breakdown": ratings_count,
            "helpful_percentage": (helpful / total * 100) if total > 0 else 0,
            "quality_score": helpful / (helpful + not_helpful) if (helpful + not_helpful) > 0 else 0.5
        }

    def get_low_quality_documents(self, threshold: float = 0.4) -> List[Dict]:
        """Find documents with low quality scores that may need review."""
        # Group feedback by document
        doc_feedback = {}
        for fb in self.feedback:
            if fb.document_id not in doc_feedback:
                doc_feedback[fb.document_id] = []
            doc_feedback[fb.document_id].append(fb)

        low_quality = []
        for doc_id, feedbacks in doc_feedback.items():
            summary = self.get_document_feedback_summary(doc_id)
            if summary["quality_score"] < threshold and summary["total_feedback"] >= 3:
                low_quality.append(summary)

        return sorted(low_quality, key=lambda x: x["quality_score"])

    # ─────────────────────────────────────────────────────────────────────────────
    # SPECIALTY COLLECTIONS
    # ─────────────────────────────────────────────────────────────────────────────

    def create_specialty_collection(
        self,
        specialty: str,
        description: str,
        document_ids: Optional[List[str]] = None,
        curator: Optional[str] = None
    ) -> bool:
        """Create a specialty-specific knowledge collection."""
        collection = SpecialtyCollection(
            specialty=specialty,
            document_ids=document_ids or [],
            description=description,
            curator=curator
        )

        self.collections[specialty] = collection
        self._save_collections()
        return True

    def add_to_collection(self, specialty: str, document_id: str) -> bool:
        """Add a document to a specialty collection."""
        if specialty not in self.collections:
            return False

        if document_id not in self.collections[specialty].document_ids:
            self.collections[specialty].document_ids.append(document_id)
            self.collections[specialty].last_updated = datetime.now().isoformat()
            self._save_collections()

        return True

    def get_collection_documents(self, specialty: str) -> List[str]:
        """Get all document IDs in a specialty collection."""
        if specialty not in self.collections:
            return []
        return self.collections[specialty].document_ids

    def list_collections(self) -> List[Dict]:
        """List all specialty collections."""
        return [
            {
                "specialty": c.specialty,
                "document_count": len(c.document_ids),
                "description": c.description,
                "curator": c.curator,
                "last_updated": c.last_updated
            }
            for c in self.collections.values()
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # CONFLICT DETECTION
    # ─────────────────────────────────────────────────────────────────────────────

    def detect_conflicts(self, document_id: str) -> List[ConflictAlert]:
        """
        Detect potential conflicts between a document and existing guidelines.
        Uses keyword matching for common conflict patterns.
        """
        if not self.rag_engine.initialized:
            return []

        # Get the new document
        contexts = self.rag_engine.retrieve(document_id, n_results=1)
        if not contexts:
            return []

        new_doc = contexts[0].document

        # Conflict detection patterns (simplified)
        conflict_keywords = {
            "dosing": ["mg", "dose", "daily", "twice", "times a day", "loading dose"],
            "contraindication": ["contraindicated", "avoid", "do not use", "not recommended"],
            "recommendation": ["first-line", "preferred", "recommended", "should not", "should"]
        }

        new_conflicts = []

        # Get similar documents
        similar_docs = self.rag_engine.retrieve(new_doc.content[:500], n_results=5)

        for ctx in similar_docs:
            if ctx.document.id == document_id:
                continue

            # Check for potential conflicts
            for conflict_type, keywords in conflict_keywords.items():
                new_has_keyword = any(kw in new_doc.content.lower() for kw in keywords)
                old_has_keyword = any(kw in ctx.document.content.lower() for kw in keywords)

                if new_has_keyword and old_has_keyword:
                    # Potential conflict detected
                    alert = ConflictAlert(
                        alert_id=hashlib.md5(
                            f"{document_id}{ctx.document.id}{conflict_type}".encode()
                        ).hexdigest()[:12],
                        document_id_1=document_id,
                        document_id_2=ctx.document.id,
                        conflict_type=conflict_type,
                        description=f"Potential {conflict_type} conflict between {new_doc.title} and {ctx.document.title}",
                        severity="medium"
                    )
                    new_conflicts.append(alert)

        # Save detected conflicts
        self.conflicts.extend(new_conflicts)
        self._save_conflicts()

        return new_conflicts

    def get_unresolved_conflicts(self) -> List[ConflictAlert]:
        """Get all unresolved conflict alerts."""
        return [c for c in self.conflicts if not c.resolved]

    def resolve_conflict(self, alert_id: str, resolution_notes: str) -> bool:
        """Mark a conflict as resolved."""
        for conflict in self.conflicts:
            if conflict.alert_id == alert_id:
                conflict.resolved = True
                conflict.resolution_notes = resolution_notes
                self._save_conflicts()
                return True
        return False

    # ─────────────────────────────────────────────────────────────────────────────
    # ANALYTICS
    # ─────────────────────────────────────────────────────────────────────────────

    def record_retrieval(self, document_ids: List[str], specialty: Optional[str] = None):
        """Record document retrievals for analytics."""
        self.analytics["total_retrievals"] += 1

        for doc_id in document_ids:
            if doc_id not in self.analytics["top_documents"]:
                self.analytics["top_documents"][doc_id] = 0
            self.analytics["top_documents"][doc_id] += 1

        if specialty:
            if specialty not in self.analytics["specialty_usage"]:
                self.analytics["specialty_usage"][specialty] = 0
            self.analytics["specialty_usage"][specialty] += 1

        self._save_analytics()

    def get_analytics_summary(self) -> Dict:
        """Get analytics summary."""
        # Sort top documents by usage
        sorted_docs = sorted(
            self.analytics["top_documents"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_queries": self.analytics.get("total_queries", 0),
            "total_retrievals": self.analytics.get("total_retrievals", 0),
            "feedback_count": len(self.feedback),
            "top_10_documents": sorted_docs,
            "specialty_usage": self.analytics.get("specialty_usage", {}),
            "version_count": len(self.versions),
            "collection_count": len(self.collections),
            "unresolved_conflicts": len(self.get_unresolved_conflicts()),
            "last_updated": self.analytics.get("last_updated")
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # SCHEDULED UPDATES
    # ─────────────────────────────────────────────────────────────────────────────

    async def check_for_updates(self) -> List[Dict]:
        """
        Check for guideline updates from known sources.
        Returns list of potential updates found.
        """
        updates_found = []

        # Define update check queries for each major source
        update_queries = {
            "AHA": "AHA guidelines 2024 2025 cardiology",
            "ADA": "ADA diabetes standards of care 2024 2025",
            "GOLD": "GOLD COPD guidelines 2024 2025",
            "IDSA": "IDSA infectious disease guidelines 2024 2025",
            "USPSTF": "USPSTF recommendations 2024 2025"
        }

        for source, query in update_queries.items():
            articles = await self.search_pubmed(query, max_results=5)
            for article in articles:
                # Check if we already have this article
                existing = self.rag_engine.retrieve(article.title, n_results=1)
                if not existing or existing[0].relevance_score < 0.9:
                    updates_found.append({
                        "source": source,
                        "title": article.title,
                        "pmid": article.pmid,
                        "publication_date": article.publication_date,
                        "action_needed": "review_and_ingest"
                    })

        return updates_found


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL KNOWLEDGE MANAGER INSTANCE (Feature #89)
# ═══════════════════════════════════════════════════════════════════════════════

knowledge_manager = KnowledgeManager(rag_engine)


# Helper functions for API
def record_citation_feedback(
    document_id: str,
    query: str,
    rating: str,
    comment: Optional[str] = None,
    clinician_specialty: Optional[str] = None
) -> str:
    """Record feedback on a citation."""
    return knowledge_manager.record_feedback(
        document_id, query, rating, comment, clinician_specialty
    )


def add_guideline_version(
    guideline_id: str,
    version_number: str,
    publication_date: str,
    content: str,
    title: str,
    source_name: str,
    supersedes_id: Optional[str] = None,
    change_summary: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Add a new guideline version."""
    return knowledge_manager.add_guideline_version(
        guideline_id, version_number, publication_date, content,
        title, source_name, supersedes_id, change_summary, **kwargs
    )


async def ingest_from_pubmed(
    query: str,
    max_articles: int = 10,
    specialty: Optional[str] = None
) -> Tuple[int, List[str]]:
    """Ingest articles from PubMed."""
    return await knowledge_manager.ingest_pubmed_articles(query, max_articles, specialty)


async def ingest_from_openfda(
    drug_name: str,
    max_labels: int = 3
) -> Tuple[int, List[str]]:
    """Ingest drug labels from OpenFDA."""
    return await knowledge_manager.ingest_openfda_drug(drug_name, max_labels)


async def ingest_openfda_batch(
    drug_names: List[str]
) -> Dict[str, Tuple[int, List[str]]]:
    """Ingest multiple drugs from OpenFDA."""
    return await knowledge_manager.ingest_openfda_batch(drug_names)


async def ingest_from_clinical_trials(
    condition: str,
    max_trials: int = 10,
    status: Optional[str] = "RECRUITING",
    specialty: Optional[str] = None
) -> Tuple[int, List[str]]:
    """Ingest clinical trials from ClinicalTrials.gov."""
    return await knowledge_manager.ingest_clinical_trials(condition, max_trials, status, specialty)


async def ingest_from_rxnorm(
    drug_name: str
) -> Tuple[int, List[str]]:
    """Ingest drug terminology and interactions from RxNorm."""
    return await knowledge_manager.ingest_rxnorm_drug(drug_name)


async def ingest_rxnorm_batch(
    drug_names: List[str]
) -> Dict[str, Tuple[int, List[str]]]:
    """Ingest multiple drugs from RxNorm."""
    return await knowledge_manager.ingest_rxnorm_batch(drug_names)


def get_knowledge_analytics() -> Dict:
    """Get knowledge base analytics."""
    return knowledge_manager.get_analytics_summary()


def get_unresolved_conflicts() -> List[Dict]:
    """Get unresolved conflict alerts."""
    return [asdict(c) for c in knowledge_manager.get_unresolved_conflicts()]


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED UPDATES & CHECKLISTS (Feature #90)
# ═══════════════════════════════════════════════════════════════════════════════

class UpdateStatus(str, Enum):
    """Status of a pending update"""
    PENDING = "pending"           # Discovered, awaiting review
    APPROVED = "approved"         # Approved for ingestion
    INGESTED = "ingested"         # Successfully ingested
    REJECTED = "rejected"         # Rejected by reviewer
    FAILED = "failed"             # Ingestion failed
    SUPERSEDED = "superseded"     # Newer version found


class UpdatePriority(str, Enum):
    """Priority level for updates"""
    CRITICAL = "critical"         # Safety-related, immediate action
    HIGH = "high"                 # Major guideline change
    MEDIUM = "medium"             # Standard update
    LOW = "low"                   # Minor revision


class UpdateSource(str, Enum):
    """Source of the update"""
    PUBMED = "pubmed"
    RSS_AHA = "rss_aha"
    RSS_CDC = "rss_cdc"
    RSS_NEJM = "rss_nejm"
    RSS_JAMA = "rss_jama"
    MANUAL = "manual"
    SCHEDULED_CHECK = "scheduled_check"


@dataclass
class PendingUpdate:
    """A pending knowledge base update (Feature #90)"""
    update_id: str
    title: str
    source: UpdateSource
    source_url: Optional[str]
    pmid: Optional[str]
    abstract_preview: str
    specialty: Optional[str]
    status: UpdateStatus
    priority: UpdatePriority
    discovered_at: str
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    ingested_at: Optional[str] = None
    supersedes_guideline: Optional[str] = None  # ID of guideline this might replace
    tags: List[str] = field(default_factory=list)


@dataclass
class UpdateSchedule:
    """Schedule configuration for automatic updates (Feature #90)"""
    schedule_id: str
    name: str
    source_type: str              # "pubmed", "rss", "check_updates"
    query_or_feed: str            # PubMed query or RSS feed name
    specialty: Optional[str]
    enabled: bool
    frequency_hours: int          # How often to check
    last_run: Optional[str]
    next_run: Optional[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UpdateChecklistItem:
    """Checklist item for reviewing an update (Feature #90)"""
    item_id: str
    update_id: str
    description: str
    category: str                 # "clinical_review", "safety", "conflicts", "quality"
    required: bool
    completed: bool = False
    completed_by: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class ScheduledUpdateManager:
    """
    Manages scheduled knowledge base updates (Feature #90).

    Features:
    - Scheduled PubMed queries
    - RSS feed monitoring
    - Pending update queue with review checklists
    - Auto-ingest for approved updates
    - Priority-based ordering
    """

    def __init__(self, knowledge_manager: KnowledgeManager, data_dir: str = "./data/updates"):
        self.knowledge_manager = knowledge_manager
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Storage files
        self.pending_file = self.data_dir / "pending_updates.json"
        self.schedules_file = self.data_dir / "schedules.json"
        self.checklists_file = self.data_dir / "checklists.json"
        self.history_file = self.data_dir / "update_history.json"

        # Load data
        self.pending_updates: Dict[str, PendingUpdate] = self._load_pending()
        self.schedules: Dict[str, UpdateSchedule] = self._load_schedules()
        self.checklists: Dict[str, List[UpdateChecklistItem]] = self._load_checklists()
        self.history: List[Dict] = self._load_history()

        # Default review checklist template
        self.default_checklist_template = [
            {"description": "Content is from a reputable medical source", "category": "quality", "required": True},
            {"description": "Publication date is recent (within guideline validity period)", "category": "quality", "required": True},
            {"description": "No conflicts with existing guidelines detected", "category": "conflicts", "required": True},
            {"description": "Clinical accuracy verified by qualified reviewer", "category": "clinical_review", "required": True},
            {"description": "No patient safety concerns identified", "category": "safety", "required": True},
            {"description": "Appropriate specialty/category assigned", "category": "quality", "required": False},
            {"description": "Keywords and metadata complete", "category": "quality", "required": False},
        ]

        # Initialize default schedules if none exist
        if not self.schedules:
            self._create_default_schedules()

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────────

    def _load_pending(self) -> Dict[str, PendingUpdate]:
        if self.pending_file.exists():
            with open(self.pending_file) as f:
                data = json.load(f)
                return {k: PendingUpdate(**v) for k, v in data.items()}
        return {}

    def _save_pending(self):
        with open(self.pending_file, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.pending_updates.items()}, f, indent=2)

    def _load_schedules(self) -> Dict[str, UpdateSchedule]:
        if self.schedules_file.exists():
            with open(self.schedules_file) as f:
                data = json.load(f)
                return {k: UpdateSchedule(**v) for k, v in data.items()}
        return {}

    def _save_schedules(self):
        with open(self.schedules_file, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.schedules.items()}, f, indent=2)

    def _load_checklists(self) -> Dict[str, List[UpdateChecklistItem]]:
        if self.checklists_file.exists():
            with open(self.checklists_file) as f:
                data = json.load(f)
                return {k: [UpdateChecklistItem(**item) for item in v] for k, v in data.items()}
        return {}

    def _save_checklists(self):
        with open(self.checklists_file, 'w') as f:
            json.dump({k: [asdict(item) for item in v] for k, v in self.checklists.items()}, f, indent=2)

    def _load_history(self) -> List[Dict]:
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return []

    def _save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history[-1000:], f, indent=2)  # Keep last 1000 entries

    # ─────────────────────────────────────────────────────────────────────────────
    # DEFAULT SCHEDULES
    # ─────────────────────────────────────────────────────────────────────────────

    def _create_default_schedules(self):
        """Create default update schedules."""
        default_schedules = [
            {
                "schedule_id": "pubmed-cardiology-daily",
                "name": "Cardiology Guidelines (Daily)",
                "source_type": "pubmed",
                "query_or_feed": "cardiology guidelines 2024 2025 AHA ACC",
                "specialty": "cardiology",
                "enabled": True,
                "frequency_hours": 24
            },
            {
                "schedule_id": "pubmed-diabetes-daily",
                "name": "Diabetes Guidelines (Daily)",
                "source_type": "pubmed",
                "query_or_feed": "diabetes guidelines 2024 2025 ADA",
                "specialty": "endocrinology",
                "enabled": True,
                "frequency_hours": 24
            },
            {
                "schedule_id": "pubmed-infectious-daily",
                "name": "Infectious Disease (Daily)",
                "source_type": "pubmed",
                "query_or_feed": "IDSA guidelines 2024 2025 infectious disease",
                "specialty": "infectious_disease",
                "enabled": True,
                "frequency_hours": 24
            },
            {
                "schedule_id": "rss-cdc-hourly",
                "name": "CDC MMWR (Hourly)",
                "source_type": "rss",
                "query_or_feed": "cdc_mmwr",
                "specialty": "public_health",
                "enabled": True,
                "frequency_hours": 1
            },
            {
                "schedule_id": "check-updates-weekly",
                "name": "Major Sources Check (Weekly)",
                "source_type": "check_updates",
                "query_or_feed": "all",
                "specialty": None,
                "enabled": True,
                "frequency_hours": 168  # 7 days
            }
        ]

        for sched in default_schedules:
            schedule = UpdateSchedule(
                schedule_id=sched["schedule_id"],
                name=sched["name"],
                source_type=sched["source_type"],
                query_or_feed=sched["query_or_feed"],
                specialty=sched["specialty"],
                enabled=sched["enabled"],
                frequency_hours=sched["frequency_hours"],
                last_run=None,
                next_run=datetime.now().isoformat()
            )
            self.schedules[schedule.schedule_id] = schedule

        self._save_schedules()

    # ─────────────────────────────────────────────────────────────────────────────
    # SCHEDULE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────────

    def create_schedule(
        self,
        name: str,
        source_type: str,
        query_or_feed: str,
        frequency_hours: int,
        specialty: Optional[str] = None,
        enabled: bool = True
    ) -> str:
        """Create a new update schedule."""
        schedule_id = hashlib.md5(f"{name}{source_type}{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        schedule = UpdateSchedule(
            schedule_id=schedule_id,
            name=name,
            source_type=source_type,
            query_or_feed=query_or_feed,
            specialty=specialty,
            enabled=enabled,
            frequency_hours=frequency_hours,
            last_run=None,
            next_run=datetime.now().isoformat()
        )

        self.schedules[schedule_id] = schedule
        self._save_schedules()
        return schedule_id

    def toggle_schedule(self, schedule_id: str, enabled: bool) -> bool:
        """Enable or disable a schedule."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = enabled
            self._save_schedules()
            return True
        return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            self._save_schedules()
            return True
        return False

    def get_due_schedules(self) -> List[UpdateSchedule]:
        """Get schedules that are due to run."""
        now = datetime.now()
        due = []

        for schedule in self.schedules.values():
            if not schedule.enabled:
                continue

            if schedule.next_run is None:
                due.append(schedule)
            else:
                next_run = datetime.fromisoformat(schedule.next_run)
                if now >= next_run:
                    due.append(schedule)

        return due

    # ─────────────────────────────────────────────────────────────────────────────
    # RUN SCHEDULED UPDATES
    # ─────────────────────────────────────────────────────────────────────────────

    async def run_schedule(self, schedule_id: str) -> Dict:
        """Run a specific schedule and queue discovered updates."""
        if schedule_id not in self.schedules:
            return {"error": f"Schedule {schedule_id} not found"}

        schedule = self.schedules[schedule_id]
        updates_found = []

        try:
            if schedule.source_type == "pubmed":
                updates_found = await self._run_pubmed_schedule(schedule)
            elif schedule.source_type == "rss":
                updates_found = await self._run_rss_schedule(schedule)
            elif schedule.source_type == "check_updates":
                updates_found = await self._run_check_updates_schedule(schedule)

            # Update schedule timing
            schedule.last_run = datetime.now().isoformat()
            schedule.next_run = (datetime.now() + timedelta(hours=schedule.frequency_hours)).isoformat()
            self._save_schedules()

            # Log to history
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "schedule_id": schedule_id,
                "schedule_name": schedule.name,
                "updates_found": len(updates_found),
                "status": "success"
            })
            self._save_history()

            return {
                "schedule_id": schedule_id,
                "updates_found": len(updates_found),
                "update_ids": [u.update_id for u in updates_found]
            }

        except Exception as e:
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "schedule_id": schedule_id,
                "schedule_name": schedule.name,
                "status": "error",
                "error": str(e)
            })
            self._save_history()
            return {"error": str(e)}

    async def _run_pubmed_schedule(self, schedule: UpdateSchedule) -> List[PendingUpdate]:
        """Run a PubMed-based schedule."""
        articles = await self.knowledge_manager.search_pubmed(
            schedule.query_or_feed,
            max_results=10
        )

        updates = []
        for article in articles:
            if not article.abstract:
                continue

            # Check if already in pending or ingested
            existing_id = f"pubmed-{article.pmid}"
            if existing_id in self.pending_updates:
                continue

            # Check if already in knowledge base
            existing = self.knowledge_manager.rag_engine.retrieve(article.title, n_results=1)
            if existing and existing[0].relevance_score > 0.9:
                continue

            update = self._create_pending_update(
                title=article.title,
                source=UpdateSource.PUBMED,
                source_url=f"https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/",
                pmid=article.pmid,
                abstract_preview=article.abstract[:500],
                specialty=schedule.specialty,
                priority=UpdatePriority.MEDIUM
            )
            updates.append(update)

        return updates

    async def _run_rss_schedule(self, schedule: UpdateSchedule) -> List[PendingUpdate]:
        """Run an RSS feed-based schedule."""
        # Map feed names to sources
        feed_source_map = {
            "cdc_mmwr": UpdateSource.RSS_CDC,
            "aha_guidelines": UpdateSource.RSS_AHA,
            "nejm_current": UpdateSource.RSS_NEJM,
            "jama_latest": UpdateSource.RSS_JAMA
        }

        source = feed_source_map.get(schedule.query_or_feed, UpdateSource.MANUAL)

        # This would integrate with the RSS checking from main.py
        # For now, create placeholder that can be expanded
        return []

    async def _run_check_updates_schedule(self, schedule: UpdateSchedule) -> List[PendingUpdate]:
        """Run a comprehensive check for guideline updates."""
        all_updates = await self.knowledge_manager.check_for_updates()

        updates = []
        for update_info in all_updates:
            update = self._create_pending_update(
                title=update_info["title"],
                source=UpdateSource.SCHEDULED_CHECK,
                source_url=f"https://pubmed.ncbi.nlm.nih.gov/{update_info['pmid']}/",
                pmid=update_info["pmid"],
                abstract_preview=f"Update from {update_info['source']}",
                specialty=None,
                priority=UpdatePriority.HIGH
            )
            updates.append(update)

        return updates

    async def run_all_due_schedules(self) -> Dict:
        """Run all schedules that are due."""
        due_schedules = self.get_due_schedules()
        results = []

        for schedule in due_schedules:
            result = await self.run_schedule(schedule.schedule_id)
            results.append({
                "schedule_id": schedule.schedule_id,
                "name": schedule.name,
                **result
            })

        return {
            "schedules_run": len(results),
            "results": results
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # PENDING UPDATES MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────────

    def _create_pending_update(
        self,
        title: str,
        source: UpdateSource,
        source_url: Optional[str],
        pmid: Optional[str],
        abstract_preview: str,
        specialty: Optional[str],
        priority: UpdatePriority
    ) -> PendingUpdate:
        """Create a new pending update with checklist."""
        update_id = hashlib.md5(f"{title}{source}{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        update = PendingUpdate(
            update_id=update_id,
            title=title,
            source=source,
            source_url=source_url,
            pmid=pmid,
            abstract_preview=abstract_preview,
            specialty=specialty,
            status=UpdateStatus.PENDING,
            priority=priority,
            discovered_at=datetime.now().isoformat()
        )

        self.pending_updates[update_id] = update
        self._save_pending()

        # Create checklist for this update
        self._create_checklist(update_id)

        return update

    def get_pending_updates(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        specialty: Optional[str] = None
    ) -> List[Dict]:
        """Get pending updates with optional filters."""
        updates = []

        for update in self.pending_updates.values():
            if status and update.status.value != status:
                continue
            if priority and update.priority.value != priority:
                continue
            if specialty and update.specialty != specialty:
                continue

            # Get checklist completion status
            checklist = self.checklists.get(update.update_id, [])
            required_items = [c for c in checklist if c.required]
            completed_required = [c for c in required_items if c.completed]

            updates.append({
                **asdict(update),
                "checklist_progress": {
                    "total": len(checklist),
                    "completed": len([c for c in checklist if c.completed]),
                    "required_total": len(required_items),
                    "required_completed": len(completed_required),
                    "ready_for_approval": len(completed_required) == len(required_items)
                }
            })

        # Sort by priority and discovered date
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        updates.sort(key=lambda x: (priority_order.get(x["priority"], 4), x["discovered_at"]))

        return updates

    def get_update_details(self, update_id: str) -> Optional[Dict]:
        """Get full details of an update including checklist."""
        if update_id not in self.pending_updates:
            return None

        update = self.pending_updates[update_id]
        checklist = self.checklists.get(update_id, [])

        return {
            **asdict(update),
            "checklist": [asdict(item) for item in checklist]
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # CHECKLIST MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────────

    def _create_checklist(self, update_id: str):
        """Create a review checklist for an update."""
        checklist = []

        for i, template in enumerate(self.default_checklist_template):
            item = UpdateChecklistItem(
                item_id=f"{update_id}-{i}",
                update_id=update_id,
                description=template["description"],
                category=template["category"],
                required=template["required"]
            )
            checklist.append(item)

        self.checklists[update_id] = checklist
        self._save_checklists()

    def complete_checklist_item(
        self,
        update_id: str,
        item_id: str,
        completed_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """Mark a checklist item as completed."""
        if update_id not in self.checklists:
            return False

        for item in self.checklists[update_id]:
            if item.item_id == item_id:
                item.completed = True
                item.completed_by = completed_by
                item.completed_at = datetime.now().isoformat()
                item.notes = notes
                self._save_checklists()
                return True

        return False

    def uncomplete_checklist_item(self, update_id: str, item_id: str) -> bool:
        """Unmark a checklist item."""
        if update_id not in self.checklists:
            return False

        for item in self.checklists[update_id]:
            if item.item_id == item_id:
                item.completed = False
                item.completed_by = None
                item.completed_at = None
                item.notes = None
                self._save_checklists()
                return True

        return False

    def get_checklist(self, update_id: str) -> List[Dict]:
        """Get the checklist for an update."""
        if update_id not in self.checklists:
            return []
        return [asdict(item) for item in self.checklists[update_id]]

    def is_checklist_complete(self, update_id: str) -> bool:
        """Check if all required checklist items are complete."""
        if update_id not in self.checklists:
            return False

        for item in self.checklists[update_id]:
            if item.required and not item.completed:
                return False

        return True

    # ─────────────────────────────────────────────────────────────────────────────
    # REVIEW & APPROVAL
    # ─────────────────────────────────────────────────────────────────────────────

    def approve_update(
        self,
        update_id: str,
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> Dict:
        """Approve an update for ingestion."""
        if update_id not in self.pending_updates:
            return {"error": "Update not found"}

        # Check if checklist is complete
        if not self.is_checklist_complete(update_id):
            return {"error": "Required checklist items not complete"}

        update = self.pending_updates[update_id]
        update.status = UpdateStatus.APPROVED
        update.reviewed_at = datetime.now().isoformat()
        update.reviewed_by = reviewed_by
        update.review_notes = review_notes

        self._save_pending()

        return {"status": "approved", "update_id": update_id}

    def reject_update(
        self,
        update_id: str,
        reviewed_by: str,
        review_notes: str
    ) -> Dict:
        """Reject an update."""
        if update_id not in self.pending_updates:
            return {"error": "Update not found"}

        update = self.pending_updates[update_id]
        update.status = UpdateStatus.REJECTED
        update.reviewed_at = datetime.now().isoformat()
        update.reviewed_by = reviewed_by
        update.review_notes = review_notes

        self._save_pending()

        return {"status": "rejected", "update_id": update_id}

    async def ingest_approved_update(self, update_id: str) -> Dict:
        """Ingest an approved update into the knowledge base."""
        if update_id not in self.pending_updates:
            return {"error": "Update not found"}

        update = self.pending_updates[update_id]

        if update.status != UpdateStatus.APPROVED:
            return {"error": f"Update is not approved (status: {update.status.value})"}

        try:
            # Fetch full content from PubMed if we have a PMID
            if update.pmid:
                articles = await self.knowledge_manager.search_pubmed(
                    f"PMID:{update.pmid}",
                    max_results=1
                )

                if articles:
                    article = articles[0]
                    doc = MedicalDocument(
                        id=f"pubmed-{update.pmid}",
                        title=article.title,
                        content=f"{article.title}\n\n{article.abstract}",
                        source_type=SourceType.PUBMED_ABSTRACT,
                        source_name=article.journal,
                        source_url=update.source_url,
                        publication_date=article.publication_date,
                        pmid=update.pmid,
                        specialty=update.specialty
                    )

                    success = self.knowledge_manager.rag_engine.add_document(doc)

                    if success:
                        update.status = UpdateStatus.INGESTED
                        update.ingested_at = datetime.now().isoformat()
                        self._save_pending()

                        return {
                            "status": "ingested",
                            "update_id": update_id,
                            "document_id": f"pubmed-{update.pmid}"
                        }

            update.status = UpdateStatus.FAILED
            self._save_pending()
            return {"error": "Failed to ingest update"}

        except Exception as e:
            update.status = UpdateStatus.FAILED
            self._save_pending()
            return {"error": str(e)}

    async def ingest_all_approved(self) -> Dict:
        """Ingest all approved updates."""
        approved = [u for u in self.pending_updates.values() if u.status == UpdateStatus.APPROVED]

        results = []
        for update in approved:
            result = await self.ingest_approved_update(update.update_id)
            results.append({
                "update_id": update.update_id,
                **result
            })

        return {
            "processed": len(results),
            "results": results
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # DASHBOARD & STATS
    # ─────────────────────────────────────────────────────────────────────────────

    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics."""
        status_counts = {}
        priority_counts = {}
        specialty_counts = {}

        for update in self.pending_updates.values():
            status_val = update.status.value if hasattr(update.status, 'value') else update.status
            priority_val = update.priority.value if hasattr(update.priority, 'value') else update.priority
            status_counts[status_val] = status_counts.get(status_val, 0) + 1
            priority_counts[priority_val] = priority_counts.get(priority_val, 0) + 1
            if update.specialty:
                specialty_counts[update.specialty] = specialty_counts.get(update.specialty, 0) + 1

        # Get recent history
        recent_history = self.history[-10:] if self.history else []

        # Get next scheduled runs
        next_runs = []
        for schedule in sorted(self.schedules.values(), key=lambda s: s.next_run or ""):
            if schedule.enabled and schedule.next_run:
                next_runs.append({
                    "schedule_id": schedule.schedule_id,
                    "name": schedule.name,
                    "next_run": schedule.next_run
                })

        return {
            "total_pending": len(self.pending_updates),
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "specialty_breakdown": specialty_counts,
            "schedules_active": len([s for s in self.schedules.values() if s.enabled]),
            "schedules_total": len(self.schedules),
            "next_scheduled_runs": next_runs[:5],
            "recent_history": recent_history
        }

    def get_schedules(self) -> List[Dict]:
        """Get all schedules."""
        return [asdict(s) for s in self.schedules.values()]


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL SCHEDULED UPDATE MANAGER (Feature #90)
# ═══════════════════════════════════════════════════════════════════════════════

update_manager = ScheduledUpdateManager(knowledge_manager)


# Helper functions for API
def get_pending_updates_list(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    specialty: Optional[str] = None
) -> List[Dict]:
    """Get list of pending updates."""
    return update_manager.get_pending_updates(status, priority, specialty)


def get_update_dashboard() -> Dict:
    """Get update dashboard stats."""
    return update_manager.get_dashboard_stats()


async def run_due_schedules() -> Dict:
    """Run all due update schedules."""
    return await update_manager.run_all_due_schedules()
