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
  - Vuzix Blade 2 charged (>80%)
  - MDx Vision app installed and running
  - WiFi connected to **same network as Mac**
  - Server URL configured (see below)

- [ ] **Configure Glasses Server URL**
  ```bash
  # Find your Mac's IP address
  ifconfig | grep "inet " | grep -v 127.0.0.1
  # Example: 192.168.7.182
  ```
  On glasses: Settings → Server URL → `http://<YOUR_IP>:8002`

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
- [ ] **"Live sync" indicator** shows green WiFi icon (WebSocket connected)
- [ ] Glasses display visible on projector/screen
- [ ] Audio working (for Minerva TTS)
- [ ] Good lighting for AR glasses visibility

### Verify Real-Time Sync
```bash
# Test that WebSocket sync is working - run this and watch dashboard update instantly
curl -X POST http://localhost:8002/api/v1/worklist/check-in \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"12724068"}'
```
Dashboard should show green pulse: "check_in: WILLIAMS, ROBERT"

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

2. Say: **"Load 1"** (WILLIAMS, ROBERT - STAT patient)
   - Patient context loads on glasses HUD
   - Web dashboard shows real-time sync indicator flash

3. Point out:
   - Hands-free patient lookup
   - **Real-time sync** - dashboard updates instantly via WebSocket
   - STAT priority patient loads first

**Say:**
> "With voice commands, I can browse my worklist and load any patient - completely hands-free. Watch the dashboard - it updates instantly via WebSocket, no refresh needed."

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

### Part 5: Health Equity AI (3 min) ⭐ KEY DIFFERENTIATOR

**This is what separates us from every other platform. No EHR has this.**

---

**Load JACKSON (patient 4) - Black pregnant woman:**

1. Say: **"Load 4"** then **"Health equity alerts"**
   - **CRITICAL: Maternal mortality alert** - 3-4x higher death rate
   - Pulse oximeter warning
   - Symptom dismissal risk warning

**Say (this is the most powerful moment):**
> "Ms. Jackson is 32 weeks pregnant. Because she's a Black woman, she faces 3-4 times the maternal mortality rate of white women. Serena Williams almost died because nurses dismissed her symptoms after childbirth. Our AI alerts the provider BEFORE anything goes wrong - lower your escalation threshold, document every symptom, don't dismiss her concerns. No EHR does this. Not Epic. Not Cerner. None of them."

---

**Load WILLIAMS (patient 1):**

2. Say: **"Load 1"** then **"Health equity alerts"**
   - Pulse oximeter: SpO2 may read 1-4% high
   - Medication: ACE inhibitors less effective

**Say:**
> "Pulse oximeters were calibrated on white skin in the 1970s. The FDA just issued guidance in January 2025 requiring testing on diverse skin tones. Our AI warns providers NOW."

---

**Load ARGONAUT (patient 7) - Religious:**

3. Say: **"Load 7"** then **"Health equity alerts"**
   - Blood product restriction (Jehovah's Witness)

---

**Load LOPEZ (patient 3) - Cultural:**

4. Say: **"Load 3"** then **"Cultural preferences"**
   - Family-centered care (familismo)
   - Spanish interpreter needed

**Say:**
> "This isn't a DEI checkbox. This is peer-reviewed clinical decision support addressing documented disparities. Every alert cites NEJM, FDA, CDC, or AHA guidelines. This saves lives."

---

### Part 6: Switch to Epic (1 min)

**On Vuzix Glasses:**

1. Say: **"Show worklist"**
2. Say: **"Load 7"** (ARGONAUT, JASON - Epic patient)
3. Point out Epic badge on glasses and dashboard

**Say:**
> "We integrate with 29 EHR platforms through FHIR. Here I'm loading an Epic patient - same seamless experience, different EHR. Notice the purple Epic badge."

**Alternative:** Say **"Load 3"** for LOPEZ, CAMILA (Epic + Urgent priority)

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
| "Health equity alerts" | Show racial medicine/cultural alerts |
| "Cultural preferences" | Show cultural care preferences |
| "Interpreter needed" | Flag interpreter requirement |

---

## Demo Patients (sorted by priority)

| # | Name | EHR | Chief Complaint | Priority | Health Equity |
|---|------|-----|-----------------|----------|---------------|
| 1 | WILLIAMS, ROBERT | Cerner | Shortness of breath | **STAT** | Pulse ox warning, med response |
| 2 | PETERS, TIMOTHY | Cerner | Chest pain | Urgent | - |
| 3 | LOPEZ, CAMILA | **Epic** | Diabetes management | Urgent | Family-centered, Spanish interpreter |
| 4 | JACKSON, TANYA | Cerner | Prenatal visit - 32 weeks | Urgent | **⭐ MATERNAL MORTALITY (3-4x risk)** |
| 5 | SMARTS SR., NANCYS II | Cerner | Follow-up | Normal | - |
| 6 | DAVIS, SARAH | Cerner | Medication refill | Normal | - |
| 7 | ARGONAUT, JASON | **Epic** | Wellness exam | Normal | Jehovah's Witness - blood products |

**Key Demo Patients:**
- **JACKSON: `12724067`** - ⭐ Black pregnant woman with maternal mortality alerts (LEAD WITH THIS)
- WILLIAMS: `12724068` - Pulse ox + medication response
- LOPEZ: `erXuFYUfucBZaryVksYEcMg3` - Cultural preferences (Epic)
- ARGONAUT: `Tbt3KuCY0B5PSrJvCu2j-PlK.aiทRwdgmSAmH1U2D5rZ4` - Religious (Epic)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Minerva not responding" | Check ANTHROPIC_API_KEY is set in environment |
| "Patient not loading" | Verify EHR proxy running: `curl http://localhost:8002/health` |
| "Voice not recognized" | Move to quieter area, speak clearly, pause 1 sec before command |
| "Dashboard shows Offline" | WebSocket disconnected - refresh page, check ehr-proxy logs |
| "Dashboard not syncing" | Check "Live sync" indicator, refresh browser |
| "Glasses won't connect" | Check WiFi (same network), verify server URL matches Mac IP |
| "Glasses disconnected" | Restart MDx Vision app, check WiFi connection |

### Quick Diagnostic Commands
```bash
# Check EHR Proxy health
curl http://localhost:8002/health

# Test WebSocket manually (should connect)
websocat ws://localhost:8002/ws/sync

# Check what's running
lsof -i :8002
lsof -i :3000

# View EHR Proxy logs
tail -f /tmp/ehr-proxy.log
```

---

## Key Talking Points

1. **HIPAA Compliant** - All data stays within hospital network
2. **Voice-First** - Hands-free for infection control
3. **EHR Agnostic** - Works with 29 EHR platforms
4. **AI with Citations** - Zero hallucination, always cites guidelines
5. **Real-Time CRUD** - Direct write-back to EHR
6. **Health Equity AI** - Racial medicine awareness, cultural care preferences
7. **US Patent Protected** - 15/237,980

### Health Equity Differentiator ⭐ UNIQUE TO MDx

> **"No EHR has this. Not Epic. Not Cerner. Not Meditech. None of them."**
>
> MDx Vision is the ONLY clinical platform with health equity built into the workflow:
>
> - **Black Maternal Mortality** - 3-4x higher death rate. We alert providers to lower escalation thresholds and document ALL symptoms.
> - **Pulse Oximeter Warnings** - FDA 2025 guidance: SpO2 reads 1-4% HIGH on darker skin. Missed hypoxia kills.
> - **Medication Response** - ACE inhibitors less effective in African Americans. We suggest alternatives.
> - **Cultural Care** - Family decision-making, interpreter needs, religious restrictions (blood products).
>
> **"Serena Williams almost died after childbirth because nurses dismissed her symptoms. Our AI would have flagged that risk before she walked in the door. That's the difference."**
>
> This isn't a DEI checkbox. This is peer-reviewed clinical decision support that addresses documented disparities. No other platform does this.

---

## Post-Demo

- [ ] Answer questions
- [ ] Offer to repeat any feature
- [ ] Share contact for follow-up
- [ ] Collect feedback

---

*Last Updated: January 23, 2025*

---

## Simulate Demo Without Glasses

If glasses are unavailable, simulate voice commands with curl:

```bash
# Check in WILLIAMS (STAT patient)
curl -X POST http://localhost:8002/api/v1/worklist/check-in \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"12724068"}'

# Start visit
curl -X POST http://localhost:8002/api/v1/worklist/status \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"12724068","status":"in_progress"}'

# Ask Minerva
curl -X POST http://localhost:8002/api/v1/minerva/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What labs should I order for shortness of breath?","patient_id":"12724068"}'

# Complete visit
curl -X POST http://localhost:8002/api/v1/worklist/status \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"12724068","status":"completed"}'
```

Watch the dashboard update in real-time as you run each command!

### Test Health Equity Alerts

```bash
# ⭐ JACKSON - Black pregnant woman (MOST POWERFUL DEMO)
curl -s http://localhost:8002/api/v1/health-equity/12724067 | jq '.alerts'
# Shows: Maternal mortality (3-4x risk), pulse ox warning, symptom dismissal risk

# WILLIAMS - Pulse oximeter warning + medication response
curl -s http://localhost:8002/api/v1/health-equity/12724068 | jq '.alerts'

# ARGONAUT - Jehovah's Witness blood product restriction
curl -s "http://localhost:8002/api/v1/health-equity/Tbt3KuCY0B5PSrJvCu2j-PlK.aiทRwdgmSAmH1U2D5rZ4" | jq '.alerts'

# LOPEZ - Cultural preferences (family-centered, interpreter)
curl -s http://localhost:8002/api/v1/health-equity/erXuFYUfucBZaryVksYEcMg3 | jq '.cultural_preferences'
```
