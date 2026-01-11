# Task Plan: Minerva Phase 3 - Proactive Intelligence

> Started: 2025-01-09
> Status: COMPLETE ✅
> Related: MINERVA.md, CLAUDE.md Feature #97

## Goal

Make Minerva proactively speak alerts, warnings, and briefings WITHOUT the clinician having to ask. Currently Minerva only responds when called ("Hey Minerva"). Phase 3 makes her speak first when something important needs attention.

## Pre-Implementation Questions

- [ ] Should Minerva interrupt ambient transcription to speak alerts?
- [ ] How do we prevent alert fatigue (too many spoken alerts)?
- [ ] Should alerts be queued or immediate?
- [ ] What's the priority order when multiple alerts exist?

## Phases

### Phase 3.1: Proactive Alert Infrastructure ✅
- [x] Create `/api/v1/minerva/proactive/{patient_id}` endpoint ✅
- [x] Define alert priority levels (critical, warning, info) ✅
- [x] Create alert aggregation logic (don't repeat, batch related) ✅
- [x] Add TTS queue for spoken alerts (Android) ✅
- [x] Add "Minerva is speaking" indicator on Android ✅
- [x] Add "Got it, Minerva" acknowledgment command ✅

### Phase 3.2: Critical Value Announcements ✅
- [x] Hook into patient load flow (Feature #92 Pre-Visit Prep) ✅ (via fetchMinervaProactiveAlerts)
- [x] Trigger Minerva voice for critical labs (Feature #29) ✅ (K>6, Na<120, glucose<50/>400, etc.)
- [x] Trigger Minerva voice for critical vitals (Feature #30) ✅ (BP>180, HR<40/>150, SpO2<88%)
- [x] Use Minerva persona instead of generic TTS ✅ (spoken_summary with Minerva voice)
- [x] Add "Minerva, I heard you" acknowledgment ✅ ("Got it, Minerva" command)

### Phase 3.3: Care Gap Reminders ✅
- [x] Integrate with Care Gap Detection (Feature #96) ✅ (detect_care_gaps called)
- [x] Speak high-priority gaps on patient load ✅ (priority 5 alerts)
- [x] "This patient is overdue for [screening]" ✅ (spoken_message format)
- [x] Limit to top 2-3 most important gaps ✅ ([:2] limit)

### Phase 3.4: Drug Interaction Warnings ✅
- [x] Hook into medication interaction check (Feature #31) ✅ (high_risk_combos)
- [x] Speak high-severity interactions via Minerva ✅ (priority 7)
- [x] "Caution: [drug A] interacts with [drug B]" ✅ (spoken_message format)
- [ ] Only speak on NEW interactions (not repeat visits) - Future enhancement

### Phase 3.5: Shift Handoff Briefings ✅
- [x] Extend SBAR Handoff Report (Feature #50) ✅ (uses proactive alerts)
- [x] "Minerva, brief me on this patient" ✅ ("brief me", "any concerns" commands)
- [x] Spoken SBAR format with key concerns ✅ (Minerva spoken_summary)
- [x] Include pending orders, abnormal values ✅ (proactive alerts)

## Success Criteria

1. Minerva speaks automatically on patient load with critical findings
2. Alert fatigue managed - max 3-4 spoken items per patient
3. Clinician can interrupt/acknowledge ("Got it, Minerva")
4. All proactive speech uses Minerva persona voice
5. Alerts logged for HIPAA compliance

## Dependencies

- Feature #29: Critical Lab Alerts (exists)
- Feature #30: Critical Vital Alerts (exists)
- Feature #31: Medication Interaction Alerts (exists)
- Feature #50: SBAR Handoff Report (exists)
- Feature #92: Pre-Visit Prep Alert (exists)
- Feature #96: Care Gap Detection (exists)
- Feature #97: Minerva Phase 1-2 (exists)

## Risks

| Risk | Mitigation |
|------|------------|
| Alert fatigue | Priority system, max alerts per patient |
| Interrupting workflow | Non-blocking alerts, acknowledgment system |
| Missing critical alerts | Critical always spoken, others optional |
| TTS overlap | Queue system, wait for previous to finish |

## Errors Log

| Date | Error | Resolution |
|------|-------|------------|
| - | - | - |

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01-09 | Use Manus-style planning | Complex 5-phase feature |
| - | - | - |
