# MDx Vision Voice Commands Reference

Complete list of voice commands for MDx Vision AR glasses. Updated regularly as new features are added.

---

## Quick Reference

| Category | Example Command | What it Does |
|----------|-----------------|--------------|
| Patient | "find patient Smith" | Search for patient |
| Data | "show vitals" | Display vital signs |
| Notes | "start note" | Begin documentation |
| Orders | "order CBC" | Place lab order |
| Safety | "verify me" | Voiceprint verification |
| Co-pilot | "copilot what should I consider" | AI clinical assistant |

---

## Patient Management

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "load patient [ID]" | Load patient by ID | Say patient ID number |
| "find patient [name]" | Search by name | Say partial or full name |
| "scan wristband" | Open barcode scanner | Point camera at wristband |
| "patient summary" | Show quick summary | After loading patient |
| "brief me" / "tell me about patient" | Spoken patient summary | Reads aloud key info |
| "show history" | View recently viewed patients | Shows last 10 patients |
| "load [N]" | Load from history | "load 1" for most recent |

---

## Clinical Data Display

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "show vitals" | Display vital signs | After patient loaded |
| "show allergies" | Display allergies | After patient loaded |
| "show meds" / "show medications" | Display medications | After patient loaded |
| "show labs" | Display lab results | After patient loaded |
| "show conditions" | Display diagnoses | After patient loaded |
| "show procedures" | Display procedures | After patient loaded |
| "show immunizations" | Display vaccines | After patient loaded |
| "show notes" / "clinical notes" | Display documentation | After patient loaded |
| "show care plans" | Display care plans | After patient loaded |
| "vital history" / "past vitals" | Historical vital readings | Shows trends over time |

---

## Documentation & Notes

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "start note" | Begin documentation mode | Records conversation |
| "stop note" / "end note" | Stop recording | Ends documentation |
| "generate note" | Create AI SOAP note | After recording |
| "save note" | Save current note | After editing |
| "push note" / "send to EHR" | Push to EHR | Requires voiceprint |
| "edit note" | Open note editor | Modify before save |
| "reset note" | Undo all changes | Returns to original |

### Note Templates
| Command | What it Does |
|---------|--------------|
| "use SOAP template" | Standard SOAP format |
| "use progress note" | Progress note format |
| "use H&P template" | History & Physical |
| "use consult note" | Consultation format |
| "use diabetes template" | Diabetes follow-up |
| "use hypertension template" | HTN follow-up |
| "use chest pain template" | Chest pain workup |
| "specialty templates" | Show all templates |

### Note Editing (Voice)
| Command | What it Does |
|---------|--------------|
| "change [section] to [text]" | Replace section content |
| "add to [section] [text]" | Append to section |
| "delete last sentence" | Remove last sentence |
| "clear [section]" | Empty a section |
| "insert normal exam" | Add normal PE macro |
| "insert normal vitals" | Add normal vitals macro |
| "undo" | Undo last change |
| "dictate to [section]" | Direct dictation mode |
| "stop dictating" | End dictation |

---

## Live Transcription

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "live transcribe" | Start real-time transcription | Records continuously |
| "stop transcription" | Stop transcribing | Ends recording |
| "pause transcription" | Temporarily pause | Resume with "resume" |
| "resume transcription" | Resume paused | After pause |
| "close" | Close transcript overlay | During transcription |

---

## Ambient Mode (ACI)

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "ambient mode" / "start ambient" | Start passive listening | Records room audio |
| "stop ambient" | Stop and save | Keeps transcript |
| "cancel ambient" / "discard" | Stop and discard | Deletes transcript |
| "show entities" | Display extracted info | Shows symptoms, meds, etc. |
| "generate note" | Create note from ambient | AI processes transcript |

---

## Orders

### Lab Orders
| Command | What it Does |
|---------|--------------|
| "order CBC" | Complete blood count |
| "order BMP" / "order CMP" | Metabolic panel |
| "order lipid panel" | Cholesterol panel |
| "order A1c" | Hemoglobin A1c |
| "order TSH" | Thyroid function |
| "order urinalysis" | Urine analysis |
| "order troponin" | Cardiac marker |
| "order D-dimer" | Clotting marker |
| "order PT INR" | Coagulation |

### Imaging Orders
| Command | What it Does |
|---------|--------------|
| "order chest X-ray" | Chest radiograph |
| "CT head" / "CT head with contrast" | Head CT scan |
| "CT chest" / "CT chest PE protocol" | Chest CT scan |
| "MRI brain" | Brain MRI |
| "ultrasound abdomen" | Abdominal US |
| "echo" / "echocardiogram" | Heart ultrasound |

### Order Sets
| Command | What it Does |
|---------|--------------|
| "order chest pain workup" | EKG, troponin, CXR |
| "order sepsis workup" | CBC, lactate, cultures |
| "order stroke workup" | CT head, labs, EKG |
| "order CHF workup" | BNP, CXR, echo |
| "list order sets" | Show all bundles |
| "what's in [set]" | Preview order set |

### Order Management
| Command | What it Does |
|---------|--------------|
| "show orders" | Display pending orders |
| "update [N] to [dose]" | Modify order by number |
| "delete [N]" | Remove order |
| "cancel order" | Cancel pending |
| "push orders" | Send to EHR |

---

## Medications

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "prescribe [med] [dose] [frequency]" | Write prescription | "prescribe amoxicillin 500mg twice daily" |
| "discontinue [med]" | Stop medication | Requires confirmation |
| "hold [med]" | Temporarily pause | Requires confirmation |
| "med reconciliation" | Compare home vs EHR meds | Shows discrepancies |
| "add home med [name]" | Add to home med list | For reconciliation |

---

## Allergies

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "add allergy to [substance]" | Start allergy entry | Prompts for severity |
| "[severity]" (high/low/unknown) | Set criticality | After add allergy |
| "reaction [description]" | Add reaction details | After severity |
| "confirm allergy" | Save to EHR | Requires voiceprint |

---

## Clinical Calculators

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "calculate BMI" | Body mass index | Uses patient height/weight |
| "calculate eGFR" | Kidney function | Uses creatinine, age, gender |
| "calculate anion gap" | Metabolic status | Uses Na, Cl, HCO3 |
| "calculate CHADS-VASc" | Stroke risk in AFib | Uses patient history |
| "calculate Wells" | PE probability | Uses clinical criteria |
| "calculate corrected calcium" | Adjusted calcium | Uses albumin |

---

## AI Clinical Co-pilot (Feature #78)

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "hey copilot" / "ask copilot" | Activate copilot | Start AI assistant |
| "copilot [question]" | Ask clinical question | "copilot what workup for chest pain?" |
| "what should I..." | Natural question | Triggers copilot |
| "what do you think..." | Natural question | Triggers copilot |
| "tell me more" / "elaborate" | Follow-up | Expands on last topic |
| "suggest next" / "what next" | Get suggestions | Next steps |
| "clear copilot" | Reset conversation | Clears history |

---

## Differential Diagnosis

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "differential diagnosis" / "ddx" | Generate DDx list | Uses patient context |
| "what could this be" | Same as DDx | Natural trigger |
| "read differential" / "speak ddx" | Read DDx aloud | After DDx generated |

---

## Image Analysis

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "take photo" / "capture image" | Open camera | Captures for analysis |
| "analyze wound" | Wound assessment | After capture |
| "analyze rash" | Dermatology analysis | After capture |
| "analyze xray" | X-ray interpretation | After capture |
| "read analysis" / "image results" | Speak analysis | After analysis |

---

## Billing & Coding

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "create claim" / "bill this" | Start billing claim | After note saved |
| "add diagnosis [code]" | Add ICD-10 | "add diagnosis J06.9" |
| "add procedure [code]" | Add CPT code | "add procedure 99213" |
| "add modifier [mod] to [N]" | Add CPT modifier | "add modifier 25 to 1" |
| "remove diagnosis [N]" | Remove by number | "remove diagnosis 2" |
| "search icd [term]" | Search ICD-10 | "search icd hypertension" |
| "search cpt [term]" | Search CPT | "search cpt office visit" |
| "submit claim" | Submit to payer | Requires confirmation |
| "show claims" / "claim history" | View claims | Shows patient claims |

---

## DNFB / Revenue Cycle

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "show DNFB" | Display unbilled accounts | Shows aged list |
| "DNFB summary" | Summary metrics | Breakdown by reason |
| "prior auth issues" | Filter by auth status | Shows at-risk revenue |
| "over [N] days" | Filter by age | "over 7 days" |
| "resolve [N]" | Mark resolved | Links to billing |
| "patient DNFB" | Patient-specific status | After patient loaded |

---

## Handoff & Reports

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "handoff report" / "SBAR" | Generate handoff | Creates structured report |
| "speak handoff" | Read handoff aloud | After generated |
| "discharge summary" | Create DC instructions | After patient loaded |
| "read discharge" | Read DC aloud | For patient education |

---

## Referrals

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "refer to [specialty]" | Create referral | "refer to cardiology for chest pain" |
| "urgent referral to [specialty]" | Urgent referral | Priority flag |
| "show referrals" | View pending | After patient loaded |
| "mark referral [N] scheduled" | Update status | "mark referral 1 completed" |

---

## Procedure Checklists

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "show checklists" | List available | Shows all checklists |
| "start timeout checklist" | Surgical timeout | Safety workflow |
| "start central line checklist" | Line insertion | Safety workflow |
| "check [N]" | Complete item | "check 1", "check 2" |
| "check all" | Complete all items | Mark all done |
| "read checklist" | Read aloud | Speaks remaining |

---

## Vitals Entry

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "BP [systolic] over [diastolic]" | Record blood pressure | "BP 120 over 80" |
| "pulse [number]" / "heart rate [number]" | Record HR | "pulse 72" |
| "temp [number]" | Record temperature | "temp 98.6" |
| "O2 sat [number]" / "SpO2 [number]" | Record oxygen | "O2 sat 98" |
| "respiratory rate [number]" | Record RR | "respiratory rate 16" |
| "weight [number]" | Record weight | "weight 180 pounds" |
| "show captured vitals" | Display entered | Review before save |
| "add vitals to note" | Add to documentation | Include in note |
| "push vitals" | Send to EHR | Requires voiceprint |

---

## Navigation & Display

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "scroll down" / "page down" | Scroll content down | Navigate lists |
| "scroll up" / "page up" | Scroll content up | Navigate lists |
| "go to top" | Jump to beginning | Quick navigation |
| "go to bottom" | Jump to end | Quick navigation |
| "go to [section]" | Jump to section | "go to assessment" |
| "font size [size]" | Change text size | small/medium/large/extra-large |

---

## HUD Control (Vuzix)

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "show HUD" | Display HUD overlay | Shows patient info |
| "hide HUD" | Remove HUD | Clear display |
| "expand HUD" | Full HUD view | Detailed info |
| "minimize HUD" | Compact HUD | Basic info only |
| "toggle HUD" | Switch visibility | On/off |

---

## Worklist

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "show worklist" | Display patient schedule | Today's patients |
| "who's next" | Next patient | Queue management |
| "check in [N]" | Check in patient | "check in 1" |
| "check in [N] to room [X]" | Assign room | "check in 2 to room 5" |
| "mark [N] completed" | Complete visit | "mark 1 completed" |
| "start seeing [N]" | Mark in progress | "start seeing 2" |
| "load [N]" | Load from worklist | "load 1" |

---

## Gesture Control

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "enable gestures" | Turn on gesture control | Head gestures active |
| "disable gestures" | Turn off gesture control | Gestures ignored |
| "gesture status" | Check status | Shows enabled/disabled |
| "enable wink" | Enable wink gesture | Quick select |
| "disable wink" | Disable wink gesture | Wink ignored |
| "wink status" | Check wink status | Shows enabled/disabled |

**Gesture Actions:**
- **Nod (down-up)**: Confirm/approve action
- **Shake (left-right-left)**: Cancel/dismiss
- **Double nod**: Toggle HUD
- **Wink (quick dip)**: Quick select/dismiss

---

## Security & Authentication

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "pair device" | Start device pairing | Scans QR code |
| "device status" | Check pairing status | Shows device info |
| "enroll my voice" | Setup voiceprint | Security enrollment |
| "voiceprint status" | Check enrollment | Shows status |
| "delete voiceprint" | Remove voiceprint | Delete enrollment |
| "verify me" / "verify my voice" | Manual verification | Re-authenticate |
| "verification status" | Check auth status | Shows last verified |
| "set verify interval [N] minutes" | Configure interval | 1-60 minutes |
| "lock session" | Lock immediately | Requires unlock |
| "unlock" | Unlock session | Requires TOTP/voice |
| "timeout [N] minutes" | Set auto-lock time | Inactivity timeout |
| "wipe data" | Emergency wipe | Clears all data |
| "encryption status" | Check encryption | Shows status |

---

## Language

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "switch to English" | English mode | Commands & TTS |
| "switch to Spanish" / "español" | Spanish mode | Commands & TTS |
| "switch to Russian" / "русский" | Russian mode | Commands & TTS |
| "switch to Mandarin" / "中文" | Mandarin mode | Commands & TTS |
| "switch to Portuguese" / "português" | Portuguese mode | Commands & TTS |
| "language options" | Show available | Lists languages |

---

## System & Help

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "help" / "what can I say" | Show command help | Lists available commands |
| "enable speech feedback" | Turn on TTS | Confirms actions aloud |
| "disable speech feedback" | Turn off TTS | Silent mode |
| "auto scroll on" | Enable auto-scroll | Follows new text |
| "auto scroll off" | Disable auto-scroll | Manual scroll |
| "close" | Close current overlay | Dismiss display |
| "cancel" | Cancel current action | Abort operation |
| "stop" | Stop current task | End recording, etc. |

---

## Custom Commands

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "create command [name] that does [actions]" | Create macro | Chain commands |
| "when I say [phrase] do [action]" | Create alias | Alternative trigger |
| "teach [name] to [actions]" | Create command | Same as create |
| "my commands" | List custom commands | Shows all macros |
| "delete command [name]" | Remove custom | Delete macro |

---

## Encounter Timer

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "start timer" | Begin encounter timer | Tracks time |
| "stop timer" | Stop timing | Ends timer |
| "how long" | Report elapsed time | Speaks duration |
| "reset timer" | Clear timer | Start fresh |

---

## Racial Medicine Awareness (Feature #79)

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "skin assessment guidance" | Display melanin-specific exam tips | For Fitzpatrick IV-VI patients |
| "pulse ox warning" | Show SpO2 accuracy alert | Darker skin tones |
| "medication considerations" | Show ancestry-relevant drug info | Based on patient ancestry |
| "check calculator bias" | Verify race-free algorithms | eGFR, lung function |
| "sickle cell protocol" | Display rapid treatment protocol | Pain crisis management |
| "pain protocol" | Show bias-aware pain assessment | Any pain evaluation |
| "maternal risk" | Show elevated risk alerts | Obstetric patients |

---

## Cultural Care Preferences (Feature #80)

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "show cultural preferences" | Display patient's preferences | After loading patient |
| "dietary restrictions" | Show dietary/medication restrictions | Halal, Kosher, vegetarian |
| "blood product preferences" | Show blood acceptance/refusal | Jehovah's Witness, etc. |
| "religious considerations" | Display religious care guidance | Based on patient religion |
| "modesty preferences" | Show modesty requirements | Gender preferences, chaperone |
| "family involvement" | Show decision-making preferences | Who to include |
| "fasting status" | Check if patient is fasting | Ramadan, other fasts |
| "save cultural preferences" | Save patient's preferences | After collecting info |

---

## Implicit Bias Alerts (Feature #81)

Gentle, evidence-based reminders during clinical documentation. Non-accusatory, educational framing.

| Command | What it Does | How to Use |
|---------|--------------|------------|
| "bias check" | Manually trigger bias awareness check | During documentation |
| "bias alert" | Same as "bias check" | Alternative phrasing |
| "equity check" | Same as "bias check" | Alternative phrasing |
| "enable bias" | Turn on bias awareness reminders | Enable alerts |
| "bias alerts on" | Same as "enable bias" | Alternative phrasing |
| "disable bias" | Turn off bias awareness reminders | Disable alerts |
| "bias alerts off" | Same as "disable bias" | Alternative phrasing |
| "bias status" | Check if alerts are enabled/disabled | Current status |
| "bias resources" | Show educational resources & training | Harvard, AAMC, NIH links |
| "bias training" | Same as "bias resources" | Alternative phrasing |
| "acknowledge bias" | Dismiss the current bias alert | After reviewing alert |
| "noted" | Same as "acknowledge bias" (if alert showing) | Quick acknowledgment |

### Automatic Triggers

Bias alerts are automatically triggered (once per session) when:
- Patient ancestry indicates disparity risk (African, Hispanic, Native American)
- Clinical context matches known disparity areas:
  - Pain assessment/documentation
  - Pain medication prescribing
  - Triage decisions
  - Cardiac symptom evaluation
  - Psychiatric evaluation

### Example Alert Display

```
💭 Pain Assessment Awareness

Research shows pain may be systematically
undertreated in some patient populations.
Taking a moment to ensure the pain score
reflects the patient's experience helps
provide equitable care.

━━━ REFLECTION ━━━
Does the documented pain level match the
patient's verbal and non-verbal cues?

Say "acknowledge bias" when ready to continue.
Say "bias resources" for training materials.
```

---

*Last updated: Feature #81 (Implicit Bias Alerts)*
