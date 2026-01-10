# Minerva - MDx Vision AI Clinical Assistant

> *Named in honor of Minerva Diaz*
>
> Minerva: Roman goddess of wisdom, medicine, and strategic warfare.

## Vision

Minerva is the conversational AI assistant for MDx Vision - like Jarvis for Iron Man, but for clinicians. She provides:

- **Evidence-based clinical guidance** grounded in real guidelines (RAG)
- **Proactive alerts** before you ask
- **Natural conversation** - talk to her like a colleague
- **Zero hallucination** - citations for every clinical claim

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MINERVA CORE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Wake Word  │    │     NLU      │    │   Response   │       │
│  │ "Hey Minerva"│───▶│   Intent     │───▶│  Generator   │       │
│  │   Detection  │    │  Detection   │    │  (Claude +   │       │
│  └──────────────┘    └──────────────┘    │     RAG)     │       │
│                                          └──────────────┘       │
│                             │                    │               │
│                             ▼                    ▼               │
│                    ┌──────────────┐    ┌──────────────┐         │
│                    │   Patient    │    │     RAG      │         │
│                    │   Context    │    │  Knowledge   │         │
│                    │  (EHR Data)  │    │    Base      │         │
│                    └──────────────┘    └──────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT CHANNELS                             │
├─────────────────────────────────────────────────────────────────┤
│  • TTS (Text-to-Speech) - Spoken responses                      │
│  • AR HUD Display - Visual summaries                            │
│  • Action Execution - Orders, notes, alerts                     │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Checklist

### Phase 1: Foundation ✅
- [x] Create `/api/v1/minerva/chat` endpoint with RAG integration
- [x] Create `/api/v1/minerva/context` endpoint for patient context
- [x] Add conversation history management (multi-turn)
- [x] Implement citation injection from RAG
- [x] Add HIPAA audit logging for Minerva interactions

### Phase 2: Wake Word & Voice ✅
- [x] Add "Hey Minerva" wake word detection (Android)
- [x] Create Minerva voice activation mode
- [x] Add TTS response with Minerva persona
- [x] Implement conversation state management
- [x] Add "Minerva, stop" / "Thank you, Minerva" to end conversation

### Phase 3: Proactive Intelligence ✅
> **Completed:** January 9, 2025

- [x] Proactive alerts on patient load (extends Feature #92)
- [x] Critical value announcements via Minerva voice
- [x] Care gap reminders spoken proactively
- [x] Drug interaction warnings via Minerva
- [x] Shift handoff briefings
- [x] "Got it, Minerva" acknowledgment command
- [x] "Minerva is speaking" indicator
- [x] Vuzix HUD integration (extends Feature #73) - alerts displayed on AR glasses

### Phase 4: Clinical Reasoning ← NEXT
- [ ] "Minerva, what do you think?" - differential diagnosis
- [ ] "Minerva, explain..." - teaching mode with citations
- [ ] "Minerva, what am I missing?" - second opinion mode
- [ ] "Minerva, what questions should I ask?" - clarify mode
- [ ] Treatment recommendations with guideline citations

### Phase 5: Actions & Integration
- [ ] "Minerva, order..." - voice orders through Minerva
- [ ] "Minerva, document..." - note dictation
- [ ] "Minerva, remind me..." - clinical reminders
- [ ] "Minerva, page..." - communication integration
- [ ] "Minerva, calculate..." - medical calculators

### Phase 6: Learning & Personalization
- [ ] Clinician preference learning
- [ ] Specialty-specific responses
- [ ] Feedback loop for response quality
- [ ] Custom guideline ingestion per organization

---

## API Endpoints

### Core Minerva Endpoints

```
POST /api/v1/minerva/chat
  - Main conversational endpoint
  - Inputs: message, patient_id (optional), conversation_id
  - Uses RAG for grounded responses
  - Returns: response, citations, suggested_actions

GET /api/v1/minerva/context/{patient_id}
  - Get current patient context for Minerva
  - Returns: summary, conditions, meds, allergies, recent_labs

POST /api/v1/minerva/proactive/{patient_id}
  - Get proactive alerts for patient
  - Returns: alerts[], spoken_summary, priority

POST /api/v1/minerva/reason
  - Clinical reasoning request
  - Inputs: findings, mode (differential|teaching|challenge|clarify)
  - Returns: reasoning, citations, confidence

DELETE /api/v1/minerva/conversation/{conversation_id}
  - Clear conversation history
```

### Request/Response Examples

**Chat Request:**
```json
{
  "message": "What's the recommended treatment for afib with RVR?",
  "patient_id": "12724066",
  "conversation_id": "abc123"
}
```

**Chat Response:**
```json
{
  "response": "For AFib with RVR, the AHA 2023 guidelines recommend rate control as first-line therapy. Options include:\n\n1. **Beta-blockers** (metoprolol 5mg IV, may repeat) - preferred if no contraindications [1]\n2. **Diltiazem** (0.25 mg/kg IV over 2 min) - if beta-blockers contraindicated [1]\n3. **Digoxin** - for patients with HFrEF [2]\n\nGiven this patient's history of heart failure, diltiazem should be used with caution.",
  "citations": [
    {"id": 1, "source": "AHA 2023 AFib Guidelines", "section": "Rate Control"},
    {"id": 2, "source": "AHA 2023 AFib Guidelines", "section": "HF Considerations"}
  ],
  "suggested_actions": [
    {"type": "order", "command": "Order metoprolol 5mg IV"},
    {"type": "order", "command": "Order continuous telemetry"}
  ],
  "confidence": 0.94,
  "rag_enhanced": true
}
```

---

## Voice Commands

### Activation
| Command | Action |
|---------|--------|
| "Hey Minerva" | Activate Minerva listening mode |
| "Minerva, stop" | End Minerva conversation |
| "Thank you, Minerva" | End with acknowledgment |

### Clinical Questions
| Command | Action |
|---------|--------|
| "Minerva, what do you think?" | Get differential diagnosis |
| "Minerva, how do I treat [condition]?" | Treatment recommendations |
| "Minerva, what's the dose for [medication]?" | Dosing guidance |
| "Minerva, explain [topic]" | Teaching mode explanation |
| "Minerva, what am I missing?" | Second opinion / challenge |
| "Minerva, what should I ask?" | Suggested questions |

### Proactive Queries
| Command | Action |
|---------|--------|
| "Minerva, brief me" | Patient briefing with alerts |
| "Minerva, any concerns?" | Proactive alerts summary |
| "Minerva, what's urgent?" | Critical items only |

### Actions
| Command | Action |
|---------|--------|
| "Minerva, order [test/med]" | Place order |
| "Minerva, document [text]" | Add to note |
| "Minerva, remind me to [task]" | Set reminder |
| "Minerva, calculate [formula]" | Medical calculator |

---

## RAG Integration

### How Minerva Uses RAG

1. **Query Analysis**: Parse clinical question for key concepts
2. **Retrieval**: Query ChromaDB for relevant guidelines
3. **Context Assembly**: Combine patient data + retrieved guidelines
4. **Generation**: Claude generates response grounded in sources
5. **Citation Injection**: Add `[1]`, `[2]` references to claims
6. **Validation**: Ensure all clinical claims have citations

### Hallucination Prevention

```python
# Minerva's response generation with RAG
async def generate_minerva_response(message: str, patient_context: dict):
    # 1. Retrieve relevant guidelines
    guidelines = await rag_engine.retrieve(message, top_k=5)

    # 2. Build grounded prompt
    prompt = f"""You are Minerva, a clinical AI assistant.

CRITICAL: Every clinical claim MUST cite a source from the guidelines below.
If you don't have a source, say "I don't have guidelines on this."
NEVER make up drug doses, treatment protocols, or clinical recommendations.

Patient Context:
{format_patient_context(patient_context)}

Relevant Guidelines:
{format_guidelines(guidelines)}

Question: {message}

Respond with citations [1], [2], etc. for each clinical claim."""

    # 3. Generate with Claude
    response = await claude_generate(prompt)

    # 4. Validate citations present
    if not has_citations(response) and is_clinical_claim(response):
        response = add_uncertainty_disclaimer(response)

    return response
```

---

## Patient Context Integration

Minerva has access to the current patient's:

- **Demographics**: Name, age, gender
- **Conditions**: Active diagnoses with ICD-10
- **Medications**: Current meds with doses
- **Allergies**: With severity and reactions
- **Recent Labs**: Last 30 days with trends
- **Recent Vitals**: Last recorded values
- **Care Plans**: Active care plans
- **Recent Notes**: Last 5 clinical notes

This context is automatically included in Minerva's reasoning.

---

## Persona & Voice

### Minerva's Character
- **Professional but warm** - like a trusted colleague
- **Confident but humble** - admits uncertainty
- **Proactive but not intrusive** - alerts when important
- **Evidence-based** - always cites sources

### Speech Patterns
```
Good: "Based on the AHA guidelines, I'd recommend starting with metoprolol..."
Bad:  "You should give metoprolol."

Good: "I notice the potassium is trending up. The ADA suggests monitoring..."
Bad:  "The potassium is high."

Good: "I don't have specific guidelines on this, but generally..."
Bad:  "The treatment is..." (without citation)
```

### TTS Voice Settings
- Voice: Professional female (configurable)
- Speed: Slightly slower than default for clarity
- Emphasis: Key values and warnings emphasized

---

## Security & Compliance

### HIPAA Audit Logging
All Minerva interactions are logged:
```json
{
  "event_type": "MINERVA_CHAT",
  "timestamp": "2025-01-09T15:30:00Z",
  "user_id": "dr_smith",
  "patient_id": "12724066",
  "query_summary": "treatment_question",
  "rag_sources_used": ["AHA_AFib_2023"],
  "response_length": 342
}
```

### Data Handling
- Patient context never sent to external services without consent
- Conversation history cleared after session timeout
- No PHI stored in RAG knowledge base

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Citation rate | >95% of clinical claims cited |
| Response relevance | >90% rated helpful by clinicians |
| Hallucination rate | <1% false clinical claims |
| Response latency | <3 seconds |
| Wake word accuracy | >95% activation rate |
| False activation rate | <5% |

---

## Development Status

**Current Phase**: Phase 4 - Clinical Reasoning (next)

**Completed Phases**:
- ✅ Phase 1: Foundation (Jan 9, 2025) - RAG-integrated chat endpoint, patient context, conversation history
- ✅ Phase 2: Wake Word & Voice (Jan 9, 2025) - "Hey Minerva" activation, TTS persona, stop commands
- ✅ Phase 3: Proactive Intelligence (Jan 9, 2025) - Alerts on patient load, critical values, care gaps, briefings

**Last Updated**: January 9, 2025

**Next Steps**:
1. "Minerva, what do you think?" - differential diagnosis mode
2. Teaching mode with citations ("Minerva, explain...")
