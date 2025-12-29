"""
MDx Vision - Medical Vocabulary for Transcription Boost

These terms are used to improve transcription accuracy for medical terminology.
Both AssemblyAI (word_boost) and Deepgram (keywords) support custom vocabulary.
"""

# Common medical terms that are often misheard
MEDICAL_VOCABULARY = [
    # Vital Signs
    "blood pressure", "systolic", "diastolic", "pulse ox", "SpO2", "O2 sat",
    "heart rate", "respiratory rate", "temperature", "BMI", "weight", "height",

    # Common Symptoms
    "dyspnea", "tachycardia", "bradycardia", "syncope", "vertigo", "nausea",
    "emesis", "diarrhea", "constipation", "hematuria", "dysuria", "polyuria",
    "polydipsia", "diaphoresis", "edema", "cyanosis", "jaundice", "pruritus",
    "paresthesia", "numbness", "tingling", "weakness", "fatigue", "malaise",

    # Pain Terms
    "sharp pain", "dull pain", "radiating", "localized", "bilateral", "unilateral",
    "intermittent", "constant", "exacerbating", "alleviating", "throbbing",

    # Body Parts & Anatomy
    "abdomen", "thorax", "extremities", "cervical", "lumbar", "thoracic",
    "sacral", "cranial", "temporal", "occipital", "parietal", "frontal",
    "supraclavicular", "axillary", "inguinal", "popliteal", "femoral",

    # Cardiovascular
    "hypertension", "hypotension", "tachycardia", "bradycardia", "arrhythmia",
    "atrial fibrillation", "A-fib", "flutter", "murmur", "S1", "S2", "S3", "S4",
    "JVD", "jugular venous distension", "peripheral edema", "CHF", "MI",
    "myocardial infarction", "angina", "STEMI", "NSTEMI", "troponin",

    # Respiratory
    "COPD", "asthma", "pneumonia", "bronchitis", "emphysema", "pleurisy",
    "wheezing", "rales", "rhonchi", "stridor", "crackles", "diminished breath sounds",
    "dyspnea on exertion", "DOE", "orthopnea", "PND", "paroxysmal nocturnal dyspnea",

    # Gastrointestinal
    "GERD", "reflux", "dysphagia", "odynophagia", "hematemesis", "melena",
    "hematochezia", "bowel sounds", "rebound tenderness", "guarding", "rigidity",
    "hepatomegaly", "splenomegaly", "ascites", "Murphy's sign", "McBurney's point",

    # Neurological
    "oriented", "alert", "lethargic", "obtunded", "stuporous", "comatose",
    "GCS", "Glasgow Coma Scale", "cranial nerves", "CN", "pupils", "PERRLA",
    "nystagmus", "ataxia", "dysarthria", "aphasia", "hemiparesis", "hemiplegia",
    "Babinski", "Romberg", "pronator drift", "DTR", "deep tendon reflexes",

    # Musculoskeletal
    "ROM", "range of motion", "crepitus", "effusion", "tenderness", "swelling",
    "deformity", "ecchymosis", "erythema", "warmth", "Lachman", "McMurray",
    "drawer test", "straight leg raise", "FABER", "Patrick's test",

    # Endocrine
    "diabetes", "diabetic", "hyperglycemia", "hypoglycemia", "A1C", "hemoglobin A1C",
    "thyroid", "hypothyroid", "hyperthyroid", "TSH", "T3", "T4", "goiter",

    # Medications - Common Classes
    "beta blocker", "ACE inhibitor", "ARB", "calcium channel blocker", "diuretic",
    "statin", "anticoagulant", "antiplatelet", "NSAID", "opioid", "benzodiazepine",
    "SSRI", "SNRI", "PPI", "proton pump inhibitor", "H2 blocker", "antibiotic",
    "steroid", "corticosteroid", "insulin", "metformin", "prednisone",

    # Medications - Common Names
    "lisinopril", "metoprolol", "amlodipine", "atorvastatin", "omeprazole",
    "levothyroxine", "gabapentin", "losartan", "hydrochlorothiazide", "HCTZ",
    "furosemide", "Lasix", "warfarin", "Coumadin", "aspirin", "Plavix",
    "clopidogrel", "Eliquis", "apixaban", "Xarelto", "rivaroxaban",
    "amoxicillin", "azithromycin", "Z-pack", "ciprofloxacin", "doxycycline",

    # Lab Values
    "CBC", "complete blood count", "BMP", "basic metabolic panel", "CMP",
    "comprehensive metabolic panel", "hemoglobin", "hematocrit", "WBC", "platelets",
    "sodium", "potassium", "chloride", "bicarbonate", "BUN", "creatinine", "GFR",
    "glucose", "calcium", "magnesium", "phosphorus", "albumin", "bilirubin",
    "AST", "ALT", "alkaline phosphatase", "lipase", "amylase", "PT", "INR", "PTT",

    # Imaging
    "X-ray", "CT", "MRI", "ultrasound", "echocardiogram", "EKG", "ECG",
    "stress test", "nuclear", "PET scan", "bone scan", "mammogram", "colonoscopy",
    "endoscopy", "EGD", "ERCP", "bronchoscopy", "angiogram", "catheterization",

    # Procedures
    "intubation", "extubation", "IV", "intravenous", "IM", "intramuscular",
    "subcutaneous", "subQ", "central line", "PICC", "arterial line", "A-line",
    "Foley", "catheter", "NG tube", "nasogastric", "chest tube", "thoracentesis",
    "paracentesis", "lumbar puncture", "LP", "spinal tap",

    # Diagnoses - ICD-10 Common
    "essential hypertension", "type 2 diabetes", "hyperlipidemia", "hypothyroidism",
    "osteoarthritis", "chronic kidney disease", "CKD", "ESRD", "heart failure",
    "coronary artery disease", "CAD", "CABG", "peripheral vascular disease", "PVD",
    "cerebrovascular accident", "CVA", "stroke", "TIA", "transient ischemic attack",

    # Physical Exam Terms
    "inspection", "palpation", "percussion", "auscultation", "normal", "abnormal",
    "unremarkable", "within normal limits", "WNL", "no acute distress", "NAD",
    "well-appearing", "ill-appearing", "cooperative", "anxious", "agitated",

    # Documentation Terms
    "chief complaint", "history of present illness", "HPI", "past medical history",
    "PMH", "past surgical history", "PSH", "family history", "social history",
    "review of systems", "ROS", "physical exam", "assessment", "plan",
    "differential diagnosis", "DDx", "follow up", "return visit", "referral",

    # Time/Duration
    "onset", "duration", "frequency", "intermittent", "constant", "acute", "chronic",
    "subacute", "progressive", "stable", "worsening", "improving", "resolved",

    # Quantities
    "milligrams", "mg", "micrograms", "mcg", "grams", "kilograms", "kg", "pounds",
    "liters", "milliliters", "mL", "cc", "units", "international units", "IU",
    "twice daily", "BID", "three times daily", "TID", "four times daily", "QID",
    "daily", "QD", "every other day", "QOD", "as needed", "PRN", "at bedtime", "QHS",
]

# Specialty-specific vocabulary additions
CARDIOLOGY_VOCABULARY = [
    "ejection fraction", "EF", "LVEF", "diastolic dysfunction", "systolic dysfunction",
    "pericarditis", "endocarditis", "cardiomyopathy", "valvular disease", "stenosis",
    "regurgitation", "prolapse", "CABG", "PCI", "stent", "angioplasty", "pacemaker",
    "ICD", "defibrillator", "cardiac resynchronization", "CRT",
]

PULMONOLOGY_VOCABULARY = [
    "FEV1", "FVC", "DLCO", "pulmonary function test", "PFT", "spirometry",
    "bronchodilator", "nebulizer", "inhaler", "MDI", "spacer", "oxygen therapy",
    "BiPAP", "CPAP", "ventilator", "intubation", "tracheostomy", "pulmonary embolism",
    "PE", "DVT", "anticoagulation", "pulmonary hypertension", "interstitial lung disease",
]

ORTHOPEDICS_VOCABULARY = [
    "fracture", "dislocation", "subluxation", "sprain", "strain", "contusion",
    "laceration", "avulsion", "tendinitis", "bursitis", "arthritis", "osteoporosis",
    "ORIF", "arthroplasty", "arthroscopy", "meniscus", "ACL", "PCL", "MCL", "LCL",
    "rotator cuff", "labrum", "cartilage", "ligament", "tendon", "fascia",
]

NEUROLOGY_VOCABULARY = [
    "seizure", "epilepsy", "convulsion", "aura", "postictal", "tonic-clonic",
    "absence seizure", "focal seizure", "EEG", "electroencephalogram", "EMG",
    "nerve conduction", "multiple sclerosis", "MS", "Parkinson's", "tremor",
    "dementia", "Alzheimer's", "neuropathy", "radiculopathy", "myelopathy",
]

PEDIATRICS_VOCABULARY = [
    "pediatric", "infant", "toddler", "neonate", "newborn", "well child",
    "developmental milestones", "growth chart", "percentile", "immunizations",
    "vaccines", "DTaP", "MMR", "Hib", "rotavirus", "varicella", "hepatitis",
    "failure to thrive", "FTT", "croup", "bronchiolitis", "RSV", "otitis media",
]

# Specialty detection mappings
# ICD-10 code prefixes and keywords that indicate specific specialties
SPECIALTY_ICD10_PREFIXES = {
    "cardiology": [
        "I10", "I11", "I12", "I13",  # Hypertensive diseases
        "I20", "I21", "I22", "I23", "I24", "I25",  # Ischemic heart diseases
        "I26", "I27", "I28",  # Pulmonary heart disease (shared with pulm)
        "I30", "I31", "I32", "I33", "I34", "I35", "I36", "I37", "I38", "I39",  # Other heart diseases
        "I40", "I41", "I42", "I43", "I44", "I45", "I46", "I47", "I48", "I49", "I50", "I51", "I52",  # Cardiomyopathy, arrhythmia, heart failure
    ],
    "pulmonology": [
        "J00", "J01", "J02", "J03", "J04", "J05", "J06",  # Acute upper respiratory
        "J09", "J10", "J11", "J12", "J13", "J14", "J15", "J16", "J17", "J18",  # Influenza and pneumonia
        "J20", "J21", "J22",  # Acute lower respiratory
        "J30", "J31", "J32", "J33", "J34", "J35", "J36", "J37", "J38", "J39",  # Other upper respiratory
        "J40", "J41", "J42", "J43", "J44", "J45", "J46", "J47",  # Chronic lower respiratory (COPD, asthma)
        "J60", "J61", "J62", "J63", "J64", "J65", "J66", "J67", "J68", "J69", "J70",  # Lung diseases
        "J80", "J81", "J82", "J84", "J85", "J86",  # Other respiratory diseases
        "J90", "J91", "J92", "J93", "J94", "J95", "J96", "J98", "J99",  # Pleural, respiratory failure
    ],
    "orthopedics": [
        "M00", "M01", "M02",  # Infectious arthropathies
        "M05", "M06", "M07", "M08",  # Inflammatory polyarthropathies
        "M10", "M11", "M12", "M13", "M14",  # Arthropathies
        "M15", "M16", "M17", "M18", "M19",  # Arthrosis/osteoarthritis
        "M20", "M21", "M22", "M23", "M24", "M25",  # Joint disorders
        "M40", "M41", "M42", "M43",  # Deforming dorsopathies
        "M45", "M46", "M47", "M48", "M49",  # Spondylopathies
        "M50", "M51", "M53", "M54",  # Other dorsopathies
        "M60", "M61", "M62", "M63",  # Muscle disorders
        "M65", "M66", "M67",  # Synovium and tendon disorders
        "M70", "M71", "M72", "M75", "M76", "M77", "M79",  # Soft tissue disorders
        "M80", "M81", "M83", "M84", "M85",  # Bone density and structure
        "S42", "S52", "S62", "S72", "S82", "S92",  # Fractures
        "S43", "S53", "S63", "S73", "S83", "S93",  # Dislocations
    ],
    "neurology": [
        "G00", "G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09",  # CNS inflammatory diseases
        "G10", "G11", "G12", "G13",  # Systemic atrophies
        "G20", "G21", "G23", "G24", "G25", "G26",  # Extrapyramidal/movement disorders (Parkinson's)
        "G30", "G31", "G32",  # Other degenerative (Alzheimer's)
        "G35", "G36", "G37",  # Demyelinating diseases (MS)
        "G40", "G41", "G43", "G44", "G45", "G46", "G47",  # Episodic/paroxysmal (epilepsy, migraine, TIA)
        "G50", "G51", "G52", "G53", "G54", "G55", "G56", "G57", "G58", "G59",  # Nerve disorders
        "G60", "G61", "G62", "G63", "G64", "G65",  # Polyneuropathies
        "G70", "G71", "G72", "G73",  # Neuromuscular junction diseases
        "G80", "G81", "G82", "G83",  # Cerebral palsy and paralytic syndromes
        "G89", "G90", "G91", "G92", "G93", "G94", "G95", "G96", "G97", "G98", "G99",  # Other CNS disorders
        "I60", "I61", "I62", "I63", "I64", "I65", "I66", "I67", "I68", "I69",  # Cerebrovascular diseases (stroke)
    ],
    "pediatrics": [
        "P00", "P01", "P02", "P03", "P04", "P05", "P07", "P08",  # Perinatal conditions
        "P10", "P11", "P12", "P13", "P14", "P15",  # Birth trauma
        "P20", "P21", "P22", "P23", "P24", "P25", "P26", "P27", "P28", "P29",  # Respiratory/cardiovascular perinatal
        "P35", "P36", "P37", "P38", "P39",  # Perinatal infections
        "P50", "P51", "P52", "P53", "P54", "P55", "P56", "P57", "P58", "P59",  # Perinatal hemorrhagic/hematologic
        "P70", "P71", "P72", "P74", "P76", "P77", "P78",  # Perinatal endocrine/digestive
        "P80", "P81", "P83", "P84",  # Other perinatal conditions
        "P90", "P91", "P92", "P93", "P94", "P95", "P96",  # Other perinatal disorders
        "Q00", "Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q07",  # Congenital malformations CNS
        "Z00.1",  # Well child examination
    ],
}

# Keywords in condition names that indicate specialties
SPECIALTY_CONDITION_KEYWORDS = {
    "cardiology": [
        "heart", "cardiac", "coronary", "myocardial", "atrial", "ventricular",
        "arrhythmia", "fibrillation", "flutter", "hypertension", "hypotension",
        "angina", "infarction", "cardiomyopathy", "pericarditis", "endocarditis",
        "valve", "stenosis", "regurgitation", "murmur", "CHF", "heart failure",
        "CAD", "CABG", "stent", "pacemaker", "defibrillator", "ICD",
    ],
    "pulmonology": [
        "lung", "pulmonary", "respiratory", "bronch", "pneumonia", "asthma",
        "COPD", "emphysema", "pleural", "dyspnea", "hypoxia", "oxygen",
        "ventilator", "intubation", "tracheostomy", "sleep apnea", "OSA",
        "pulmonary embolism", "PE", "pneumothorax", "tuberculosis", "TB",
        "interstitial", "fibrosis", "bronchitis", "bronchiectasis",
    ],
    "orthopedics": [
        "fracture", "bone", "joint", "arthritis", "osteoarthritis", "arthroplasty",
        "hip", "knee", "shoulder", "spine", "spinal", "lumbar", "cervical",
        "disc", "herniation", "stenosis", "scoliosis", "kyphosis", "lordosis",
        "tendon", "ligament", "ACL", "MCL", "rotator cuff", "meniscus",
        "carpal tunnel", "osteoporosis", "dislocation", "sprain", "strain",
    ],
    "neurology": [
        "brain", "cerebral", "neurological", "seizure", "epilepsy", "stroke",
        "CVA", "TIA", "migraine", "headache", "dementia", "Alzheimer",
        "Parkinson", "multiple sclerosis", "MS", "neuropathy", "radiculopathy",
        "paralysis", "paresis", "tremor", "ataxia", "vertigo", "dizziness",
        "meningitis", "encephalitis", "nerve", "neuralgia", "sclerosis",
    ],
    "pediatrics": [
        "pediatric", "child", "infant", "newborn", "neonatal", "congenital",
        "developmental", "growth", "immunization", "vaccine", "well child",
        "failure to thrive", "FTT", "croup", "bronchiolitis", "RSV",
        "otitis media", "ear infection", "tonsillitis", "childhood",
    ],
}


def detect_specialty_from_icd10(icd10_code: str) -> list:
    """
    Detect medical specialties from an ICD-10 code.

    Args:
        icd10_code: ICD-10 diagnosis code (e.g., "I10", "J44.1")

    Returns:
        List of detected specialties
    """
    if not icd10_code:
        return []

    code_upper = icd10_code.upper().strip()
    detected = []

    for specialty, prefixes in SPECIALTY_ICD10_PREFIXES.items():
        for prefix in prefixes:
            if code_upper.startswith(prefix):
                if specialty not in detected:
                    detected.append(specialty)
                break

    return detected


def detect_specialty_from_condition(condition_name: str) -> list:
    """
    Detect medical specialties from a condition/diagnosis name.

    Args:
        condition_name: Name of the condition (e.g., "Essential hypertension")

    Returns:
        List of detected specialties
    """
    import re

    if not condition_name:
        return []

    name_lower = condition_name.lower()
    detected = []

    for specialty, keywords in SPECIALTY_CONDITION_KEYWORDS.items():
        for keyword in keywords:
            kw_lower = keyword.lower()
            # Use word boundary matching to avoid false positives
            # e.g., "PE" shouldn't match "hypertension"
            if len(kw_lower) <= 3:
                # For short keywords (abbreviations), require word boundaries
                pattern = r'\b' + re.escape(kw_lower) + r'\b'
                if re.search(pattern, name_lower):
                    if specialty not in detected:
                        detected.append(specialty)
                    break
            else:
                # For longer keywords, simple substring match is fine
                if kw_lower in name_lower:
                    if specialty not in detected:
                        detected.append(specialty)
                    break

    return detected


def detect_specialties_from_patient_conditions(conditions: list) -> list:
    """
    Detect relevant medical specialties from a list of patient conditions.

    Args:
        conditions: List of condition dicts with 'name' and optionally 'code' keys
                   e.g., [{"name": "Essential hypertension", "code": "I10"},
                          {"name": "Type 2 diabetes", "code": "E11"}]

    Returns:
        List of unique detected specialties, sorted by relevance (most matches first)
    """
    specialty_counts = {}

    for condition in conditions:
        # Try ICD-10 code first (more reliable)
        code = condition.get("code", "")
        if code:
            for specialty in detect_specialty_from_icd10(code):
                specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 2  # Weight code matches higher

        # Also check condition name
        name = condition.get("name", "")
        if name:
            for specialty in detect_specialty_from_condition(name):
                specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1

    # Sort by count (descending) and return specialty names
    sorted_specialties = sorted(specialty_counts.items(), key=lambda x: x[1], reverse=True)
    return [specialty for specialty, count in sorted_specialties]


def detect_specialty_from_transcript(transcript: str) -> list:
    """
    Detect relevant medical specialties from transcript text.

    Args:
        transcript: Transcribed conversation text

    Returns:
        List of detected specialties
    """
    import re

    if not transcript:
        return []

    text_lower = transcript.lower()
    specialty_counts = {}

    for specialty, keywords in SPECIALTY_CONDITION_KEYWORDS.items():
        count = 0
        for keyword in keywords:
            kw_lower = keyword.lower()
            # Use word boundary matching for short keywords
            if len(kw_lower) <= 3:
                pattern = r'\b' + re.escape(kw_lower) + r'\b'
                if re.search(pattern, text_lower):
                    count += 1
            else:
                if kw_lower in text_lower:
                    count += 1
        if count > 0:
            specialty_counts[specialty] = count

    # Only return specialties with at least 2 keyword matches
    sorted_specialties = sorted(specialty_counts.items(), key=lambda x: x[1], reverse=True)
    return [specialty for specialty, count in sorted_specialties if count >= 2]


def get_vocabulary(specialties: list = None) -> list:
    """
    Get combined medical vocabulary, optionally including specialty-specific terms.

    Args:
        specialties: List of specialties to include (e.g., ["cardiology", "pulmonology"])

    Returns:
        Combined list of medical terms
    """
    vocab = MEDICAL_VOCABULARY.copy()

    if specialties:
        specialty_map = {
            "cardiology": CARDIOLOGY_VOCABULARY,
            "pulmonology": PULMONOLOGY_VOCABULARY,
            "orthopedics": ORTHOPEDICS_VOCABULARY,
            "neurology": NEUROLOGY_VOCABULARY,
            "pediatrics": PEDIATRICS_VOCABULARY,
        }

        for specialty in specialties:
            if specialty.lower() in specialty_map:
                vocab.extend(specialty_map[specialty.lower()])

    return vocab


def get_vocabulary_for_patient(conditions: list) -> tuple:
    """
    Get vocabulary automatically tailored to a patient's conditions.

    Args:
        conditions: List of patient conditions with 'name' and optionally 'code'

    Returns:
        Tuple of (vocabulary_list, detected_specialties)
    """
    specialties = detect_specialties_from_patient_conditions(conditions)
    vocab = get_vocabulary(specialties)
    return vocab, specialties
