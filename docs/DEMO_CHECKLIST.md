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

### 🏥 Core Value Propositions

| # | Talking Point | Key Message |
|---|---------------|-------------|
| 1 | **Voice-First Design** | "Hands-free means infection control. No touching keyboards between patients." |
| 2 | **EHR Agnostic** | "Works with 29 EHR platforms. Cerner, Epic, Veradigm, athenahealth - one interface for all." |
| 3 | **AI with Citations** | "Zero hallucination. Every Minerva recommendation cites NEJM, AHA, CDC, or FDA guidelines." |
| 4 | **Real-Time CRUD** | "Voice to EHR in seconds. Orders, allergies, notes - direct write-back, no re-keying." |
| 5 | **US Patent Protected** | "Patent 15/237,980 - we invented voice-activated AR for clinical documentation." |

### 🔒 Security & Compliance (For IT/Security Audiences)

| # | Talking Point | Detail |
|---|---------------|--------|
| 1 | **HIPAA Compliant** | "All PHI stays within your network. We don't store patient data in our cloud." |
| 2 | **AES-256 Encryption** | "Field-level encryption for all PHI - SSN, DOB, diagnoses. Even if breached, data is useless." |
| 3 | **OWASP Top 10 Mitigated** | "All 10 OWASP vulnerabilities addressed. No SQL injection, XSS, or CSRF possible." |
| 4 | **SOC 2 Type II Ready** | "Full audit trail. Every PHI access logged with user, timestamp, and reason." |
| 5 | **OAuth2 + Device Signing** | "Two-factor: OAuth2 tokens + HMAC device signatures. Lost glasses = no access." |
| 6 | **90-Day Key Rotation** | "Encryption keys auto-rotate. Even old keys expire - defense in depth." |
| 7 | **Rate Limiting** | "100 requests/min per device. Brute force attacks blocked automatically." |
| 8 | **No Hardcoded Secrets** | "Zero credentials in code. All secrets in environment variables, rotated regularly." |

**Security One-Liner:**
> "We built this for HIPAA audits. Every access logged, every field encrypted, every connection authenticated."

### 💰 ROI Talking Points (For Administrators)

| # | Talking Point | Detail |
|---|---------------|--------|
| 1 | **2 Hours/Day Saved** | "Providers spend 2 hours daily on documentation. We cut that by 50%." |
| 2 | **$150K/Provider/Year** | "Time savings translate to $150K in recaptured revenue per provider." |
| 3 | **Reduce Burnout** | "Documentation burden is #1 cause of physician burnout. Fix the cause, not the symptom." |
| 4 | **Faster Billing** | "Notes complete at discharge = faster coding = faster payment." |
| 5 | **Reduced DNFB** | "Real-time documentation reduces Discharged Not Final Billed accounts." |

### ⭐ Health Equity Differentiator - UNIQUE TO MDx

**Opening Line:**
> **"No EHR has this. Not Epic. Not Cerner. Not Meditech. None of them."**

**The Problem (Use for Context):**

| Disparity | Statistic | Source |
|-----------|-----------|--------|
| Black Maternal Mortality | 3-4x higher than white women | CDC MMWR 2023 |
| Pulse Oximeter Error | 1-4% higher reading on dark skin | NEJM 2020, FDA 2025 |
| Symptom Dismissal | Black patients' pain undertreated 22% more | PNAS 2016 |
| Heart Attack Diagnosis | Women 50% more likely to be misdiagnosed | AHA 2022 |

**What MDx Does:**

| Alert Type | What It Shows | Demo Patient |
|------------|---------------|--------------|
| **Maternal Mortality** | "Lower escalation threshold. Document ALL symptoms." | JACKSON (patient 4) |
| **Pulse Oximeter** | "SpO2 may read 1-4% HIGH. Consider ABG." | WILLIAMS, JACKSON |
| **Symptom Dismissal** | "Listen to ALL concerns, even if reassured." | JACKSON |
| **Medication Response** | "ACE inhibitors less effective. Consider ARBs." | WILLIAMS |
| **Religious Restrictions** | "Jehovah's Witness - no blood products" | ARGONAUT (patient 7) |
| **Cultural Preferences** | "Family-centered care, Spanish interpreter" | LOPEZ (patient 3) |

**The Serena Williams Story (Emotional Hook):**
> "Serena Williams almost died after childbirth because nurses dismissed her symptoms. She knew something was wrong - she has a history of blood clots - but they didn't listen. She had to advocate for herself while hemorrhaging.
>
> **Our AI would have flagged that risk before she walked in the door.** The provider would see: 'Elevated maternal risk. Lower threshold for escalation. Document ALL patient-reported symptoms.' That's the difference between life and death."

**Closing Line:**
> "This isn't a DEI checkbox. This is peer-reviewed clinical decision support citing NEJM, FDA, CDC, and AHA guidelines. Every alert has a citation. This saves lives."

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
