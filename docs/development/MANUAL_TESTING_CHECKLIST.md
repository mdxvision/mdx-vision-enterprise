# MDx Vision Manual Testing Checklist

> **Purpose:** Tests that require human interaction on Vuzix Blade 2 glasses.
> These cannot be automated - they need real voice input, visual verification, and audio confirmation.

**Last Updated:** 2025-01-12
**Device:** Vuzix Blade 2

---

## Pre-Test Setup

- [ ] EHR Proxy running (`cd ehr-proxy && python main.py`)
- [ ] ADB reverse port set (`adb reverse tcp:8002 tcp:8002`)
- [ ] App installed on Vuzix (`adb install -r app-debug.apk`)
- [ ] Vuzix connected to WiFi
- [ ] Glasses on head, powered on

---

## 1. Core Patient Commands

### Load Patient
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 1.1 | "Load patient" | Test patient loads, name displayed | [ ] |
| 1.2 | "Load 1" | First patient from history loads | [ ] |
| 1.3 | "Find patient Smith" | Search results shown | [ ] |

### Show Patient Data
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 1.4 | "Show vitals" | Vitals overlay appears | [ ] |
| 1.5 | "Show allergies" | Allergies displayed | [ ] |
| 1.6 | "Show meds" | Medications listed | [ ] |
| 1.7 | "Show labs" | Lab results shown | [ ] |
| 1.8 | "Show conditions" | Conditions displayed | [ ] |
| 1.9 | "Show procedures" | Procedures listed | [ ] |
| 1.10 | "Show immunizations" | Immunizations displayed | [ ] |

### Patient Summary
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 1.11 | "Patient summary" | Visual summary overlay | [ ] |
| 1.12 | "Brief me" | TTS speaks patient summary aloud | [ ] |

---

## 2. Transcription & Documentation

### Live Transcription
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 2.1 | "Live transcribe" | Transcription overlay appears | [ ] |
| 2.2 | Speak "Testing one two three" | Text appears in real-time | [ ] |
| 2.3 | "Stop transcription" | Transcription stops | [ ] |

### Ambient Mode
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 2.4 | "Start ambient" | Ambient mode activates | [ ] |
| 2.5 | "Stop ambient" | Ambient mode stops | [ ] |
| 2.6 | "Show entities" | Extracted entities displayed | [ ] |

### Note Generation
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 2.7 | "Generate note" | SOAP note generated | [ ] |
| 2.8 | "Start note" | Note editing mode | [ ] |
| 2.9 | "Save note" | Note saved confirmation | [ ] |

---

## 3. TTS (Text-to-Speech) Verification

> These tests verify audio output works on Vuzix (uses server-side TTS)

| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 3.1 | "Brief me" | Hear patient summary spoken | [ ] |
| 3.2 | Load patient with allergies | Hear "Warning: Patient allergic to..." | [ ] |
| 3.3 | Load patient with critical labs | Hear critical value alert | [ ] |
| 3.4 | "Read note" | Hear note content spoken | [ ] |

---

## 4. Wake Word Activation

| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 4.1 | "Hey MDx" | Wake word activates listening | [ ] |
| 4.2 | "Hey MDx, load patient" | Chained command works | [ ] |
| 4.3 | "Hey Minerva" | Minerva AI activates | [ ] |

---

## 5. Minerva AI Assistant

| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 5.1 | "Hey Minerva" | Minerva responds | [ ] |
| 5.2 | "Minerva, what should I check?" | Clinical suggestions | [ ] |
| 5.3 | "Minerva, differential diagnosis" | DDx provided | [ ] |
| 5.4 | "Got it Minerva" | Acknowledges and dismisses | [ ] |

---

## 6. Clinical Safety Alerts

| Test | Trigger | Expected Result | Pass |
|------|---------|-----------------|------|
| 6.1 | Load patient with critical BP | Vital alert spoken | [ ] |
| 6.2 | Load patient with drug interactions | Interaction alert | [ ] |
| 6.3 | Load patient with allergies | Allergy warning spoken | [ ] |

---

## 7. Orders & Billing

| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 7.1 | "Order CBC" | Lab order created | [ ] |
| 7.2 | "Order chest x-ray" | Imaging order created | [ ] |
| 7.3 | "Show orders" | Orders list displayed | [ ] |
| 7.4 | "Create claim" | Billing claim initiated | [ ] |

---

## 8. Worklist Management

| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 8.1 | "Show worklist" | Patient worklist displayed | [ ] |
| 8.2 | "Who's next" | Next patient shown | [ ] |
| 8.3 | "Check in 1" | First patient checked in | [ ] |

---

## 9. Display & HUD

| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 9.1 | "Show HUD" | Vuzix HUD overlay appears | [ ] |
| 9.2 | "Hide HUD" | HUD disappears | [ ] |
| 9.3 | "Expand HUD" | HUD shows full details | [ ] |
| 9.4 | Data overlay readable | Text is legible on AR display | [ ] |

---

## 10. Gesture Controls (Vuzix)

| Test | Gesture | Expected Result | Pass |
|------|---------|-----------------|------|
| 10.1 | Nod head (yes) | Confirms/approves action | [ ] |
| 10.2 | Shake head (no) | Cancels/dismisses | [ ] |
| 10.3 | Double nod | Toggles HUD | [ ] |
| 10.4 | Quick head dip (wink) | Quick select | [ ] |

---

## 11. Multi-Language Commands

### Language Switching
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 11.1 | "Switch to Spanish" | Language changes to Spanish | [ ] |
| 11.2 | "Switch to Russian" | Language changes to Russian | [ ] |
| 11.3 | "Switch to English" | Language changes back to English | [ ] |

### Spanish Full Phrases
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 11.4 | "Cargar paciente" | Loads test patient | [ ] |
| 11.5 | "Mostrar signos vitales" | Shows vitals | [ ] |
| 11.6 | "Mostrar alergias" | Shows allergies | [ ] |
| 11.7 | "Mostrar medicamentos" | Shows medications | [ ] |

### Spanish Single-Word Keywords (NEW)
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 11.8 | "Vitales" | Shows vitals (single word works) | [ ] |
| 11.9 | "Alergias" | Shows allergies | [ ] |
| 11.10 | "Medicamentos" | Shows medications | [ ] |
| 11.11 | "Laboratorios" | Shows labs | [ ] |
| 11.12 | "Ayuda" | Shows help | [ ] |

### Russian Full Phrases
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 11.13 | "Загрузить пациента" | Loads test patient | [ ] |
| 11.14 | "Показать витальные" | Shows vitals | [ ] |
| 11.15 | "Показать аллергии" | Shows allergies | [ ] |

### Russian Single-Word Keywords (NEW)
| Test | Voice Command | Expected Result | Pass |
|------|---------------|-----------------|------|
| 11.16 | "Витальные" | Shows vitals (single word works) | [ ] |
| 11.17 | "Аллергии" | Shows allergies | [ ] |
| 11.18 | "Лекарства" | Shows medications | [ ] |
| 11.19 | "Анализы" | Shows labs | [ ] |
| 11.20 | "Помощь" | Shows help | [ ] |

---

## 12. Error Handling

| Test | Scenario | Expected Result | Pass |
|------|----------|-----------------|------|
| 12.1 | Say unrecognized command | "Command not recognized" feedback | [ ] |
| 12.2 | No patient loaded, "Show vitals" | "Please load patient first" | [ ] |
| 12.3 | Network offline | Graceful error message | [ ] |

---

## Test Summary

| Category | Tests | Passed | Failed |
|----------|-------|--------|--------|
| Core Patient Commands | 12 | | |
| Transcription & Docs | 9 | | |
| TTS Verification | 4 | | |
| Wake Word | 3 | | |
| Minerva AI | 4 | | |
| Safety Alerts | 3 | | |
| Orders & Billing | 4 | | |
| Worklist | 3 | | |
| Display & HUD | 4 | | |
| Gestures | 4 | | |
| Multi-Language | 20 | | |
| Error Handling | 3 | | |
| **TOTAL** | **73** | | |

---

## Notes

_Record any issues, observations, or bugs found during testing:_

```
Date: ___________
Tester: ___________

Issues Found:
1.
2.
3.

```

---

## Automated Test Coverage (Reference)

These are already tested automatically:

| Test Type | Count | Status |
|-----------|-------|--------|
| Python API tests | 2,207 | ✅ PASS |
| Web dashboard tests | 106 | ✅ PASS |
| Android unit tests | 464 | ✅ PASS |
| Android E2E tests | 54/58 | ✅ PASS (4 network timeouts) |
| Voice command parsing | 247 | ✅ PASS |
| **Total Automated** | **3,078** | **✅** |

**Manual tests above:** 55 tests requiring human verification
