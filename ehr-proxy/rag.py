"""
MDx Vision - RAG (Retrieval-Augmented Generation) System
Feature #88 - Reduces hallucination by grounding responses in medical sources

Architecture:
    Query → Vector Search → Retrieve Top-K Docs → Augment Prompt → Claude → Cited Response

Components:
    1. ChromaDB - Local vector database (no API keys needed)
    2. Medical Knowledge Base - Guidelines, PubMed abstracts, drug info
    3. Retrieval Pipeline - Semantic search for relevant context
    4. Citation Generator - Adds source references to responses
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'MedicalDocument':
        data['source_type'] = SourceType(data['source_type'])
        return cls(**data)


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
