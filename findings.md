# Findings: Minerva Phase 3 - Proactive Intelligence

> Last Updated: 2025-01-09
> Related Plan: task_plan.md

## Research Summary

### Existing Alert Infrastructure

**Feature #92 (Pre-Visit Prep Alert)** - Already returns:
```json
{
  "alerts": [
    {"category": "critical", "type": "abnormal_lab", "message": "..."},
    {"category": "care_gap", "type": "screening_due", "message": "..."}
  ],
  "spoken_summary": "Heads up: 2 critical alerts...",
  "hud_summary": "..."
}
```
This is the foundation - we need to route `spoken_summary` through Minerva voice.

**Feature #29-30 (Critical Labs/Vitals)** - Already has TTS:
```kotlin
// MainActivity.kt - current implementation
speakCriticalAlert("Critical: Potassium 6.8, above normal range")
```
Need to replace generic TTS with Minerva persona.

**Feature #96 (Care Gap Detection)** - Returns:
```json
{
  "gaps": [...],
  "spoken_summary": "3 care gaps identified...",
  "priority_count": {"high": 1, "medium": 2}
}
```

### Android TTS Current State

```kotlin
// Current TTS initialization (MainActivity.kt)
private var textToSpeech: TextToSpeech? = null

// Used for alerts
private fun speakText(text: String) {
    textToSpeech?.speak(text, TextToSpeech.QUEUE_ADD, null, "utterance_id")
}
```

Need Minerva-specific voice settings (pitch, rate, persona prefix).

### API Endpoint Pattern

Existing Minerva endpoints:
- `POST /api/v1/minerva/chat` - Conversational (exists)
- `GET /api/v1/minerva/context/{patient_id}` - Patient context (exists)
- `POST /api/v1/minerva/proactive/{patient_id}` - **TO BUILD**

## Code Snippets

### Proactive Endpoint (Planned)

```python
@app.post("/api/v1/minerva/proactive/{patient_id}")
async def minerva_proactive_alerts(patient_id: str):
    """
    Get proactive Minerva alerts for a patient.
    Called on patient load to trigger spoken alerts.
    """
    alerts = []

    # 1. Get pre-visit prep alerts (Feature #92)
    prep = await get_patient_prep(patient_id)

    # 2. Get care gaps (Feature #96)
    gaps = await get_care_gaps(patient_id)

    # 3. Aggregate and prioritize
    # ...

    # 4. Generate Minerva-style spoken summary
    spoken = generate_minerva_speech(alerts)

    return {
        "alerts": alerts,
        "spoken_summary": spoken,
        "priority": "critical" if any_critical else "info"
    }
```

### Android Integration Point

```kotlin
// After patient load success in loadPatient()
private fun loadPatient(patientId: String) {
    // ... existing code ...

    // NEW: Trigger Minerva proactive alerts
    if (isMinervaEnabled) {
        fetchMinervaProactiveAlerts(patientId)
    }
}

private fun fetchMinervaProactiveAlerts(patientId: String) {
    // Call /api/v1/minerva/proactive/{patient_id}
    // Speak result with Minerva voice
}
```

## Technical Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Alert priority | 3 levels vs 5 levels | 3 (critical, warning, info) | Simpler, maps to existing |
| TTS queue | Replace vs Add | QUEUE_ADD | Don't interrupt previous |
| Max alerts spoken | 2, 3, 5 | 3 | Balance info vs fatigue |

## Open Questions

1. **Should Minerva introduce herself?**
   - Option A: "This is Minerva. Critical alert: ..."
   - Option B: Just speak the alert (user knows it's Minerva)
   - **Leaning toward A** for first alert only

2. **Acknowledgment mechanism?**
   - Option A: Voice ("Got it, Minerva")
   - Option B: Gesture (nod)
   - Option C: Tap to dismiss
   - **Need to decide**

3. **Alert persistence?**
   - Should unacknowledged alerts repeat?
   - After how long?

## Files to Modify

| File | Changes |
|------|---------|
| `ehr-proxy/main.py` | Add `/api/v1/minerva/proactive/{patient_id}` |
| `MainActivity.kt` | Add `fetchMinervaProactiveAlerts()`, Minerva TTS |
| `MINERVA.md` | Update Phase 3 checklist |
| `CLAUDE.md` | Document new endpoint |

## References

- MINERVA.md - Phase 3 checklist
- Feature #92 - Pre-Visit Prep Alert
- Feature #96 - Care Gap Detection
- Feature #29-30 - Critical Lab/Vital Alerts
