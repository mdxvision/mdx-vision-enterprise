# MDx Vision Hospital Demo Checklist

> **Demo Duration:** 10 minutes
> **Target Audience:** Hospital administrators, CMIOs, clinical staff

---

## Pre-Demo Setup (1 hour before)

### Technical Setup

- [ ] **EHR Proxy Running**
  ```bash
  cd ehr-proxy
  source venv/bin/activate
  ASSEMBLYAI_API_KEY=your_key python3 main.py
  # Verify: http://localhost:8002/api/v1/health
  ```

- [ ] **Web Dashboard Running**
  ```bash
  cd web
  npm run dev
  # Verify: http://localhost:3000
  ```

- [ ] **Android Glasses Connected**
  - Vuzix Blade 2 paired via Bluetooth
  - MDx Vision app installed and running
  - Microphone enabled in settings
  - WiFi connected to same network

- [ ] **Test API Connectivity**
  ```bash
  # Test worklist (should return 7 patients)
  curl http://localhost:8002/api/v1/worklist | jq '.patients | length'

  # Test Minerva
  curl -X POST http://localhost:8002/api/v1/minerva/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello"}'
  ```

### Demo Environment

- [ ] Browser open to worklist page: `http://localhost:3000/dashboard/worklist`
- [ ] Glasses display visible on projector/screen
- [ ] Audio working (for Minerva TTS)
- [ ] Good lighting for AR glasses visibility

---

## 10-Minute Demo Script

### Part 1: Worklist Overview (2 min)

**On Web Dashboard:**

1. Show worklist page with 7 patients
2. Point out:
   - **Mixed EHR badges**: 5 Cerner (blue) + 2 Epic (purple)
   - **Priority indicators**: Red star for urgent patients
   - **Critical alerts**: Warning icon for patients needing attention
   - **Status flow**: Scheduled -> Checked-in -> In Progress -> Completed

**Say:**
> "This is our daily worklist showing patients from multiple EHR systems - both Cerner and Epic. Notice Mr. Williams has a critical alert and is marked urgent."

---

### Part 2: Glasses Patient Selection (2 min)

**On Vuzix Glasses:**

1. Say: **"Show worklist"**
   - Glasses display compact patient list

2. Say: **"Load 4"** (Robert Williams - urgent patient)
   - Patient context loads on glasses HUD
   - Web dashboard syncs to show same patient

3. Point out:
   - Hands-free patient lookup
   - Automatic sync between glasses and dashboard
   - Critical alerts appear immediately

**Say:**
> "With voice commands, I can browse my worklist and load any patient - completely hands-free. The web dashboard stays in sync so my team can see who I'm reviewing."

---

### Part 3: Minerva AI Briefing (3 min)

**On Vuzix Glasses:**

1. Say: **"Hey Minerva"** (activates Minerva)
   - Green indicator shows listening

2. Ask: **"What do you think about this patient?"**
   - Minerva provides differential diagnosis with citations
   - Suggested voice commands appear

3. Ask: **"What labs should I order?"**
   - Minerva recommends labs based on conditions
   - Citations from clinical guidelines shown

4. Say: **"Thank you, Minerva"** (ends session)

**Point out on web dashboard:**
- Real-time Minerva chat display
- RAG citations with source documents
- Confidence score for each response

**Say:**
> "Minerva is our AI clinical assistant - like Jarvis for healthcare. She uses RAG to ground every answer in real clinical guidelines. Notice she cites AHA and ADA guidelines for her recommendations."

---

### Part 4: CRUD Operations (2 min)

**On Vuzix Glasses:**

1. Say: **"Order CBC"**
   - Order created in Cerner sandbox
   - Confirmation displayed

2. Say: **"Order chest X-ray, stat"**
   - Stat priority order created
   - Shows on dashboard

3. Say: **"Add allergy penicillin, severe"**
   - Allergy added to patient chart
   - Web dashboard updates

**Say:**
> "Voice commands let me place orders and update the chart without touching a keyboard. Everything writes back to the EHR in real-time."

---

### Part 5: Switch to Epic (1 min)

**On Vuzix Glasses:**

1. Say: **"Show worklist"**
2. Say: **"Load 6"** (Jason Argonaut - Epic patient)
3. Point out Epic badge on glasses

**Say:**
> "We integrate with 29 EHR platforms through FHIR. Here I'm loading an Epic patient - same seamless experience, different EHR."

---

## Voice Commands Quick Reference

| Command | Action |
|---------|--------|
| "Show worklist" | Display patient list |
| "Load [number]" | Load patient from worklist |
| "Hey Minerva" | Activate AI assistant |
| "What do you think?" | Get differential diagnosis |
| "Order [test]" | Place lab/imaging order |
| "Order [test], stat" | Place urgent order |
| "Add allergy [name]" | Add allergy to chart |
| "Thank you, Minerva" | End Minerva session |
| "Summarize" | Get patient summary |

---

## Demo Patients

| # | Name | EHR | Chief Complaint | Notes |
|---|------|-----|-----------------|-------|
| 1 | SMARTS SR., NANCYS II | Cerner | Follow-up | Critical alerts |
| 2 | PETERS, TIMOTHY | Cerner | Chest pain | Urgent priority |
| 3 | JOHNSON, MARIA | Cerner | Diabetes management | - |
| 4 | WILLIAMS, ROBERT | Cerner | Shortness of breath | STAT, Critical |
| 5 | DAVIS, SARAH | Cerner | Medication refill | - |
| 6 | ARGONAUT, JASON | Epic | Wellness exam | Epic sandbox |
| 7 | LOPEZ, CAMILA | Epic | Diabetes management | Critical alerts |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Minerva not responding" | Check Claude API key is set |
| "Patient not loading" | Verify EHR proxy running on 8002 |
| "Voice not recognized" | Move to quieter area, speak clearly |
| "Dashboard not syncing" | Refresh browser, check network |
| "Glasses disconnected" | Re-pair Bluetooth, restart app |

---

## Key Talking Points

1. **HIPAA Compliant** - All data stays within hospital network
2. **Voice-First** - Hands-free for infection control
3. **EHR Agnostic** - Works with 29 EHR platforms
4. **AI with Citations** - Zero hallucination, always cites guidelines
5. **Real-Time CRUD** - Direct write-back to EHR
6. **US Patent Protected** - 15/237,980

---

## Post-Demo

- [ ] Answer questions
- [ ] Offer to repeat any feature
- [ ] Share contact for follow-up
- [ ] Collect feedback

---

*Last Updated: January 2025*
