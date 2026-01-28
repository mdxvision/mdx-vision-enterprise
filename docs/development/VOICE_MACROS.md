# Voice Macros - Nuance-Style Custom Shortcuts

**Feature Request:** Doctor-customizable voice macros for text expansion and action triggers
**Priority:** High (Demo Differentiator)
**Status:** Planning

---

## Overview

Inspired by Nuance Dragon's macro system, this feature allows doctors to create custom voice shortcuts that expand to text or trigger actions. Unlike static templates, these are fully customizable per clinician and specialty.

---

## Use Cases

### 1. Text Expansion Macros
Doctor says a trigger phrase, system expands to full text:

| Trigger Phrase | Expands To |
|----------------|------------|
| "normal heart" | "Heart: Regular rate and rhythm. No murmurs, rubs, or gallops. S1 and S2 normal. No JVD." |
| "normal lungs" | "Lungs: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi." |
| "normal abdomen" | "Abdomen: Soft, non-tender, non-distended. No masses or hepatosplenomegaly. Bowel sounds normoactive." |
| "my PE" | Full physical exam template with all normal findings |
| "chronic pain verbiage" | Standard chronic pain assessment and plan documentation |

### 2. Action Macros
Doctor says a trigger phrase, system executes commands:

| Trigger Phrase | Action |
|----------------|--------|
| "my cardio panel" | Orders: CBC, BMP, Lipid Panel, HbA1c, TSH |
| "chest pain workup" | Orders: EKG, Troponin x3, CXR, BNP |
| "sepsis bundle" | Orders: Lactate, Blood cultures x2, CBC, BMP, UA, CXR |
| "add my signature" | Inserts: "Dr. [Name], MD - Board Certified [Specialty]" |

### 3. Hybrid Macros (Text + Action)
| Trigger Phrase | Result |
|----------------|--------|
| "discharge diabetic" | Text: Discharge instructions for diabetes + Action: Orders follow-up appointment |
| "admit for observation" | Text: Admission note template + Action: Orders admission order set |

---

## Data Model

```python
class VoiceMacro(BaseModel):
    id: str                          # UUID
    clinician_id: str                # Who created it
    trigger_phrase: str              # What activates it (e.g., "normal heart")
    aliases: List[str] = []          # Alternative triggers (e.g., ["nrml heart", "heart normal"])
    macro_type: MacroType            # TEXT_EXPANSION, ACTION, HYBRID

    # For TEXT_EXPANSION
    expansion_text: Optional[str]    # The text to insert

    # For ACTION
    action_type: Optional[str]       # ORDER_SET, NAVIGATION, CUSTOM
    action_payload: Optional[dict]   # {"orders": ["CBC", "BMP"], "priority": "stat"}

    # Metadata
    specialty: Optional[str]         # cardiology, orthopedics, etc.
    category: str                    # physical_exam, orders, documentation
    is_system_default: bool = False  # True for built-in macros
    usage_count: int = 0             # Track popularity
    created_at: datetime
    updated_at: datetime

class MacroType(str, Enum):
    TEXT_EXPANSION = "text_expansion"
    ACTION = "action"
    HYBRID = "hybrid"
```

---

## API Endpoints

### Macro Management
```
POST   /api/v1/macros                    # Create new macro
GET    /api/v1/macros                    # List user's macros
GET    /api/v1/macros/{macro_id}         # Get specific macro
PUT    /api/v1/macros/{macro_id}         # Update macro
DELETE /api/v1/macros/{macro_id}         # Delete macro
```

### Macro Execution
```
POST   /api/v1/macros/expand             # Expand text from trigger phrase
GET    /api/v1/macros/match/{phrase}     # Find matching macro for phrase
```

### Default Macros
```
GET    /api/v1/macros/defaults           # Get system default macros
GET    /api/v1/macros/defaults/{specialty}  # Get specialty-specific defaults
POST   /api/v1/macros/import-defaults    # Import defaults to user's macros
```

---

## Voice Commands

### Creating Macros
- "Create macro [name]" → Starts macro creation flow
- "Save as macro [name]" → Saves current text as macro
- "Define shortcut [name]" → Creates new shortcut

### Using Macros
- Say the trigger phrase during dictation → Auto-expands
- "Expand [name]" → Explicitly expands macro
- "Run [name]" → Executes action macro

### Managing Macros
- "List my macros" → Shows all user macros
- "Edit macro [name]" → Opens macro editor
- "Delete macro [name]" → Removes macro

---

## Specialty Default Macros

### Cardiology
| Trigger | Type | Expansion/Action |
|---------|------|------------------|
| "normal cardiac exam" | TEXT | Full cardiac PE findings |
| "chest pain workup" | ACTION | EKG, Troponin, CXR, BNP |
| "afib assessment" | HYBRID | AFib documentation + Orders anticoagulation panel |

### Orthopedics
| Trigger | Type | Expansion/Action |
|---------|------|------------------|
| "normal MSK exam" | TEXT | Full musculoskeletal PE |
| "back pain workup" | ACTION | X-ray L-spine, MRI if needed |
| "fracture assessment" | TEXT | Fracture documentation template |

### Emergency Medicine
| Trigger | Type | Expansion/Action |
|---------|------|------------------|
| "trauma primary" | TEXT | Primary trauma survey |
| "sepsis workup" | ACTION | Sepsis bundle orders |
| "chest pain ED" | HYBRID | Chest pain protocol + Orders |

### Primary Care
| Trigger | Type | Expansion/Action |
|---------|------|------------------|
| "well visit complete" | TEXT | Complete wellness exam |
| "annual labs" | ACTION | CBC, CMP, Lipid, HbA1c, TSH |
| "diabetes followup" | HYBRID | Diabetes note + Orders HbA1c |

---

## Implementation Plan

### Phase 1: Core Infrastructure (M0)
- [ ] Add VoiceMacro model to main.py
- [ ] Create CRUD endpoints for macros
- [ ] Add in-memory macro storage (per-user)
- [ ] Implement `/api/v1/macros/expand` endpoint

### Phase 2: Voice Integration (M1)
- [ ] Add macro detection to transcription pipeline
- [ ] Implement real-time text expansion
- [ ] Add voice commands for macro management
- [ ] Android: Add macro expansion to VoiceCommandProcessor

### Phase 3: Defaults & Personalization (M2)
- [ ] Create 50+ default macros by specialty
- [ ] Add specialty auto-detection from user profile
- [ ] Implement macro import/export
- [ ] Add usage analytics

### Phase 4: Advanced Features (M3)
- [ ] Variable substitution: "patient presents with {chief_complaint}"
- [ ] Conditional macros: different expansion based on context
- [ ] Shared macros: team/practice-wide macros
- [ ] Macro marketplace: share across organization

---

## Demo Script

**Scenario:** Cardiologist documenting a routine visit

1. Doctor: "Hey MDx, load patient Williams"
2. Doctor: "Start dictation"
3. Doctor: "Chief complaint chest pain. History of present illness: 55-year-old male with **normal cardiac exam**..."
   - **System expands:** "...Heart: Regular rate and rhythm. No murmurs, rubs, or gallops. S1 and S2 normal. No JVD. No peripheral edema..."
4. Doctor: "Assessment and plan. **My cardio panel**"
   - **System:** "Ordering CBC, BMP, Lipid Panel, HbA1c, TSH for patient Williams"
5. Doctor: "Stop dictation"

---

## Comparison with Nuance

| Feature | Nuance Dragon | MDx Vision |
|---------|---------------|------------|
| Text expansion | ✅ | ✅ (Planned) |
| Custom shortcuts | ✅ | ✅ (Planned) |
| Action macros | ❌ | ✅ (Orders, navigation) |
| Voice-only creation | ❌ (keyboard) | ✅ (Fully voice) |
| Specialty defaults | ✅ | ✅ (Planned) |
| Real-time expansion | ❌ (post-process) | ✅ (Live) |
| EHR integration | Limited | ✅ (Native FHIR) |

---

## Success Metrics

- Macro creation rate: >3 macros per clinician
- Macro usage rate: >10 expansions per session
- Time saved: >2 minutes per patient encounter
- User satisfaction: >4.5/5 rating

---

## References

- Nuance Dragon Medical: https://www.nuance.com/healthcare/provider-solutions/speech-recognition.html
- Voice macro best practices from power users
- Specialty-specific documentation standards
