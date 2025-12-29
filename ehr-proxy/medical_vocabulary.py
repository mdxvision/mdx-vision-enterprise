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
