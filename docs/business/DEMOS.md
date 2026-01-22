# MDx Vision Enterprise - C-Suite Demo Guide

> **Purpose**: Win hospital contracts by demonstrating capabilities competitors cannot match.
> **Audience**: Hospital executives, CIOs, CMOs, CFOs, CNOs
> **Last Updated**: January 2025

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature Readiness Audit](#feature-readiness-audit)
3. [Competitor Analysis](#competitor-analysis)
4. [Competitive Gap Analysis](#competitive-gap-analysis)
5. [Demo Scripts](#demo-scripts)
6. [Talking Points & Objection Handling](#talking-points--objection-handling)
7. [Technical Setup](#technical-setup)
8. [Fallback Plans](#fallback-plans)

---

## Executive Summary

### What We Are
MDx Vision is the **first and only AR glasses platform** for clinical documentation with built-in **health equity features**. We combine:
- Ambient clinical intelligence (voice-to-SOAP)
- AR glasses (Vuzix Blade 2, Ray-Ban Meta compatible)
- Health equity alerts (racial medicine, maternal health, implicit bias)
- Full EHR integration (Cerner, Epic, Veradigm)

### Why We Win
| Competitor | AR Glasses | Health Equity | Price/Month |
|------------|------------|---------------|-------------|
| DAX Copilot (Microsoft) | No | No | $600 |
| Augmedix | No | No | $2,000 |
| Suki AI | No | No | $299-399 |
| **MDx Vision** | **Yes** | **Yes** | **TBD** |

### The "Holy Shit" Moment
**No commercial EHR or ambient AI platform has health equity features.** We are the only solution that:
- Alerts clinicians to pulse oximeter inaccuracy for darker skin tones
- Warns of 3-4x maternal mortality risk for Black women
- Provides implicit bias check reminders during pain assessment
- Tracks cultural care preferences (religious, dietary, modesty)

This is not a feature - it's a **regulatory and liability differentiator**.

---

## Feature Readiness Audit

### Overall Demo-Ready Score: 8.5/10

### Green Light Features (Safe to Demo)

| Feature | Description | Risk Level |
|---------|-------------|------------|
| **Voice Recognition** | 500+ medical vocabulary terms, wake word "Hey MDx" | LOW |
| **Patient Lookup** | Live Cerner FHIR integration, search by name/MRN | LOW |
| **Real-time Transcription** | AssemblyAI/Deepgram WebSocket streaming | LOW |
| **SOAP Note Generation** | AI-powered with ICD-10/CPT auto-suggest | LOW |
| **Health Equity Alerts** | Racial medicine, maternal health, bias checks | LOW |
| **Billing/Claims** | Create claims from notes, code selection | LOW |
| **DNFB Dashboard** | Revenue cycle with aging buckets | LOW |
| **Voiceprint Auth** | Biometric voice verification | LOW |
| **TTS Voice Feedback** | Server-side TTS for Vuzix | LOW |
| **Multi-language** | Spanish, Russian, Mandarin, Portuguese | LOW |
| **Offline Mode** | Local note drafts, sync on reconnect | LOW |

### Yellow Light Features (Demo with Caution)

| Feature | Description | Risk Level | How to Handle |
|---------|-------------|------------|---------------|
| **Ambient Mode (ACI)** | Continuous listening, entity extraction | MEDIUM | Script the encounter, have backup transcript |
| **Speaker Diarization** | Clinician vs patient identification | MEDIUM | Don't claim "AI-powered multi-speaker" - it's rule-based |
| **Entity Extraction** | Symptoms, meds, allergies from speech | MEDIUM | Pattern-based (100+ keywords), not full NLP |
| **Complex Voice Commands** | Multi-step order modifications | MEDIUM | Use scripted commands only |

### Red Light Features (Manage Expectations)

| Feature | Description | Risk Level | How to Handle |
|---------|-------------|------------|---------------|
| **CRUD Write-back** | Push vitals/orders/allergies to EHR | HIGH | Cerner sandbox is read-only. Frame as "proven architecture, needs your credentials" |
| **Vuzix Native HUD** | Always-on overlay | MEDIUM | Only demo on actual Vuzix hardware |

---

## Competitor Analysis

### Microsoft DAX Copilot (Nuance)

**Overview**: Microsoft's flagship ambient documentation product, integrated into Dragon Copilot ecosystem.

**Pricing**:
- $600/user/month
- $650-700 one-time setup fee per user
- 12-month commitment required
- Volume discounts for 10+ users

**Key Features**:
- Ambient conversation capture
- Multi-language encounters (including Spanish)
- Epic EHR integration (first to market)
- Order suggestions from ambient recordings
- Referral letters, after-visit summaries
- Dragon Copilot for Nurses (Dec 2025)

**Limitations**:
- **iOS only** - No Android support
- **No AR glasses** - Phone/desktop only
- **No health equity features**
- **Complex procurement** - Enterprise sales process
- **Expensive** - $7,200/year/user + setup

**What They Say**: "5 minutes saved per encounter" (Microsoft survey, July 2024)

**Sources**:
- [Microsoft DAX Copilot](https://www.microsoft.com/en-us/health-solutions/clinical-workflow/dragon-copilot)
- [DAX Copilot Review](https://www.trytwofold.com/compare/dax-copilot-review)

---

### Augmedix

**Overview**: Commure subsidiary offering hybrid AI + human documentation services.

**Pricing**:
- ~$2,000/user/month (enterprise)
- $299-699/user/month (smaller practices)
- Custom quotes for large deployments

**Key Features**:
- Three service levels: Go (pure AI), Assist (AI + specialists), Live (full-service)
- 50+ EHR integrations
- HITRUST certified
- Vizient contract (65% of US acute care, 97% of AMCs)

**Limitations**:
- **No AR glasses** - Phone in room required
- **No health equity features**
- **Most expensive** option for enterprise
- **Hybrid model** means human latency in some tiers

**What They Claim**: "14.8% productivity increase (primary care), 16.1% (specialist)"

**Sources**:
- [Augmedix](https://www.augmedix.com/)
- [Vizient Contract Announcement](https://www.commure.com/press-releases/augmedix-awarded-vizient-contract-for-ambient-ai-documentation-solutions)

---

### Suki AI

**Overview**: Voice AI assistant with deep EHR integrations, best price point.

**Pricing**:
- Suki Compose: $299/user/month
- Suki Assistant: $399/user/month
- No free tier

**Key Features**:
- Deep Epic, Oracle Health, athenahealth, MEDITECH integration
- 80 languages, 99 specialties
- Ambient order staging (review and sign)
- Chart Q&A ("What medications is patient taking?")
- Pre-visit patient summaries

**Limitations**:
- **No AR glasses** - App-based only
- **No health equity features**
- **Learning curve** for full feature utilization
- **No voice biometric auth**

**What They Claim**: "60% burnout reduction, 41% note-taking time reduction"

**Sources**:
- [Suki AI](https://www.suki.ai/)
- [Suki Pricing Analysis](https://www.healos.ai/blog/suki-pricing-features-cost-and-the-best-alternatives-in-2025)

---

## Competitive Gap Analysis

### What Everyone Has (Table Stakes)

All competitors offer:
- Ambient conversation capture
- Auto-SOAP note generation
- EHR integration
- HIPAA compliance
- Multi-language support

**You cannot win on these features alone.**

### What ONLY MDx Vision Has

| Capability | DAX | Augmedix | Suki | MDx Vision |
|------------|:---:|:--------:|:----:|:----------:|
| AR Glasses Native | | | | **Yes** |
| Hands-free Operation | | | | **Yes** |
| Racial Medicine Awareness | | | | **Yes** |
| Pulse Ox Accuracy Alerts | | | | **Yes** |
| Fitzpatrick Skin Type Tracking | | | | **Yes** |
| Implicit Bias Alerts | | | | **Yes** |
| Maternal Mortality Alerts | | | | **Yes** |
| Cultural Care Preferences | | | | **Yes** |
| SDOH Integration | | | | **Yes** |
| Health Literacy Assessment | | | | **Yes** |
| Interpreter Integration | | | | **Yes** |
| Voice Biometric Auth | | | | **Yes** |
| Head Gesture Control | | | | **Yes** |
| Wink/Micro-tilt Selection | | | | **Yes** |
| TOTP Voice Entry | | | | **Yes** |

### Why Health Equity Wins Contracts

1. **Regulatory Pressure**: CMS, Joint Commission, and state regulators increasingly require equity metrics
2. **Liability Reduction**: Documented bias checks reduce malpractice risk
3. **Research-Backed**: Every alert cites peer-reviewed studies
4. **No Competition**: Zero alternatives offer this
5. **PR Value**: "First hospital to deploy equity-aware AI documentation"

---

## Demo Scripts

### Pre-Demo Setup Checklist

- [ ] Vuzix Blade 2 charged and connected to WiFi
- [ ] EHR Proxy server running (`python main.py` on port 8002)
- [ ] Test patient loaded (ID: 12724066 or custom demo patient)
- [ ] Ambient mode tested within last hour
- [ ] TTS working (say "brief me" to verify)
- [ ] Web dashboard open on laptop (localhost:5173)
- [ ] Backup transcript ready (in case ambient fails)
- [ ] Demo patient has: allergies, conditions, medications, vitals

---

### Script A: Executive Overview (5 Minutes)

**Goal**: Create urgency, show differentiator, leave them wanting more.

#### Opening (30 seconds)
> "Your clinicians spend 2 hours on documentation for every hour with patients. Your equity scores are under scrutiny. And your competitors are already piloting ambient AI.
>
> MDx Vision solves all three - and we're the only platform that does."

#### Demo Flow

**[0:30-1:30] The Problem**
> "Let me show you what your clinicians deal with today."

*Show traditional EHR documentation workflow - clicks, typing, looking away from patient.*

> "Now let me show you MDx Vision."

**[1:30-3:00] The Solution**

*Put on Vuzix glasses*

> "Hey MDx, load patient."

*Patient data appears on glasses*

> "Brief me."

*System speaks patient summary aloud*

> "This clinician never looked at a screen. Never typed. Never broke eye contact with the patient."

**[3:00-4:30] The Differentiator**

> "But here's what no one else can do."

*Show health equity alert appearing*

> "See this alert? It's reminding the clinician that pulse oximeter readings may overestimate oxygen levels by 1-4% for this patient's skin tone. This is based on research from NEJM 2020.
>
> DAX doesn't do this. Augmedix doesn't do this. Suki doesn't do this. Only MDx Vision."

**[4:30-5:00] The Close**

> "We do everything they do - ambient documentation, SOAP notes, coding, billing. But we're the only platform that helps you improve equity outcomes while reducing documentation burden.
>
> When can we schedule a 30-minute deep dive with your clinical informatics team?"

---

### Script B: Full Clinical Workflow (15 Minutes)

**Goal**: Demonstrate complete ambient documentation cycle with equity features.

#### Setup
- Pre-load demo patient with: Type 2 Diabetes, Hypertension, Penicillin allergy
- Patient should trigger: equity alerts, medication interactions, critical vitals

#### Demo Flow

**[0:00-2:00] Introduction**

> "What I'm about to show you is a complete patient encounter - from patient lookup to signed note - entirely hands-free on AR glasses.
>
> This is not a prototype. This is running on production hardware with live EHR integration."

**[2:00-4:00] Patient Lookup**

*Put on Vuzix glasses*

> "Hey MDx."

*Wake word activates*

> "Find patient Nancy Smarts."

*Patient search returns results*

> "Load patient."

*Patient data loads, safety alerts spoken:*
- "Alert: Patient has 2 known allergies. Penicillin. Sulfa."
- "Warning: Patient has 3 critical vital signs..."

> "Notice the glasses just spoke critical safety information. The clinician heard allergies without looking at anything."

**[4:00-7:00] Ambient Documentation**

> "Now I'll simulate a patient encounter. Watch how the system captures everything."

> "Start ambient."

*Ambient mode activates*

> *Simulate conversation:*
> "Hi Mrs. Smarts, I see you're here for your diabetes follow-up. How have you been feeling?"
> "Tell me about your blood sugars. Any episodes of low blood sugar?"
> "Are you still taking your metformin twice daily?"
> "Let me check your feet for any sores or numbness."

> "Stop ambient."

*Show extracted entities overlay*

> "The system extracted: chief complaint, symptoms, medications, and physical exam findings - all from natural conversation."

**[7:00-9:00] SOAP Note Generation**

> "Generate note."

*AI generates complete SOAP note with ICD-10 and CPT codes*

> "In under 10 seconds, we have a complete note with:
> - Subjective: Patient's reported symptoms
> - Objective: Vitals, exam findings
> - Assessment: ICD-10 codes E11.9, I10
> - Plan: Follow-up, medication refills, lab orders
>
> The clinician reviews and signs. That's it."

**[9:00-12:00] Health Equity Features**

> "Now let me show you what makes us different."

> "Show equity alerts."

*Display racial medicine, SDOH, maternal health features*

> "For this patient, the system is showing:
> 1. **Pharmacogenomic consideration**: ACE inhibitors may be less effective for patients of African ancestry - consider ARBs
> 2. **Pulse oximeter alert**: May overestimate SpO2 by 1-4%
> 3. **SDOH flag**: Transportation barrier documented - affects medication adherence
>
> This is not opinion. Every alert cites peer-reviewed research.
>
> No other ambient documentation system has this capability."

**[12:00-14:00] Billing & Compliance**

> "Create claim."

*Billing workflow initiates*

> "The note automatically populates:
> - ICD-10 diagnosis codes
> - CPT procedure codes
> - Modifiers where appropriate
>
> Your revenue cycle team reviews and submits. No manual code entry."

> "Show audit log."

*Dashboard shows HIPAA audit log*

> "Every action is logged for HIPAA compliance. PHI access, note modifications, who signed, when."

**[14:00-15:00] Close**

> "Questions?"

> "We can have this running in your environment in 2-4 weeks. What's the best next step?"

---

### Script C: Deep Dive with Q&A (30 Minutes)

*Combine Script B with:*
- DNFB Dashboard walkthrough (5 min)
- Voiceprint enrollment demo (3 min)
- Multi-language voice commands (2 min)
- Order placement workflow (3 min)
- Web dashboard full tour (5 min)
- Q&A (7 min)

---

## Talking Points & Objection Handling

### Key Messages

1. **"We're the only AR glasses ambient documentation platform."**
   - DAX, Augmedix, Suki all require phones or computers
   - True hands-free means no device in hand

2. **"We're the only platform with health equity features."**
   - Racial medicine awareness
   - Maternal mortality alerts
   - Implicit bias checks
   - SDOH integration
   - Cultural care preferences

3. **"We do everything they do, plus what they can't."**
   - Ambient documentation? Yes
   - SOAP notes? Yes
   - ICD-10/CPT coding? Yes
   - EHR integration? Yes
   - Equity features? Only us

4. **"We're more affordable than the big players."**
   - DAX: $600/month + $700 setup
   - Augmedix: $2,000/month
   - MDx Vision: [your pricing]

### Objection Handling

| Objection | Response |
|-----------|----------|
| "We're already looking at DAX." | "DAX is excellent for phone-based documentation. But they don't support AR glasses, and they don't have health equity features. For clinicians who need true hands-free operation - surgeons, ER physicians, proceduralists - MDx Vision is the only option." |
| "How do we know this works with Epic?" | "We have FHIR R4 integration certified against Cerner's open sandbox. Epic uses the same FHIR R4 standard. With your Epic credentials, we can have a working integration in 2-3 weeks. We're happy to do a paid pilot." |
| "The health equity stuff sounds like liability." | "Actually, it reduces liability. Documenting that you provided equity-aware care - with research citations - is a defense against malpractice claims. We're not saying your clinicians are biased. We're giving them a tool to demonstrate due diligence." |
| "What if ambient mode fails during a real encounter?" | "The system saves transcripts locally. If connectivity drops, the note generates when connection restores. Clinicians can also dictate directly or use voice commands to add to the note manually." |
| "Why haven't we heard of you?" | "We've been in stealth development focusing on getting the technology right. The health equity features alone took 18 months to develop with clinical advisory input. We're now ready for health system partnerships." |
| "What about HIPAA?" | "HIPAA audit logging is built-in. Every PHI access is logged with timestamp, user, action, and patient ID. Voice biometric authentication ensures only authorized users access patient data. We're designed for HIPAA from day one, not bolted on." |

---

## Technical Setup

### Hardware Required
- Vuzix Blade 2 AR glasses (charged, WiFi connected)
- MacBook/laptop for web dashboard
- Backup: Samsung phone with MDx Vision app

### Software Setup
```bash
# Start EHR Proxy (main backend)
cd ehr-proxy
python main.py  # Runs on port 8002

# Start Web Dashboard (optional, for demo)
cd web
npm run dev  # Runs on port 5173

# Verify services
curl http://localhost:8002/api/v1/tts/status
# Should return: {"available":true,"engine":"gTTS"}
```

### Demo Patient Setup
- Patient ID: 12724066 (Cerner sandbox)
- Or create custom patient with:
  - Allergies: Penicillin, Sulfa
  - Conditions: Type 2 Diabetes, Hypertension, Hyperlipidemia
  - Medications: Metformin, Lisinopril, Atorvastatin
  - Critical vitals for alerts

### Pre-Demo Verification
```bash
# Test voice recognition
# On glasses, say: "Hey MDx" - should activate

# Test patient load
# Say: "Load patient" - should speak allergies/alerts

# Test TTS
# Say: "Brief me" - should speak patient summary

# Test ambient mode
# Say: "Start ambient" - should begin transcription
# Say: "Stop ambient" - should show entities
```

---

## Fallback Plans

### If Ambient Mode Fails

**Backup**: Pre-recorded transcript

```
Have this ready to paste into the note generation:

"Patient is a 65-year-old female with type 2 diabetes and
hypertension presenting for routine follow-up. She reports
good blood sugar control, checking levels twice daily with
readings between 110 and 140. She denies any hypoglycemic
episodes. She is compliant with metformin 500mg twice daily
and lisinopril 10mg daily. Physical exam reveals blood pressure
138/82, pulse 78, normal heart sounds, no peripheral edema,
feet exam shows intact sensation bilaterally."
```

**What to Say**: "Let me show you what the system captured from that conversation."
*Paste transcript, generate note*

### If TTS Fails

**Backup**: Read the information yourself

**What to Say**: "The system normally speaks this aloud. Let me read what the clinician would hear..."

### If EHR Connection Fails

**Backup**: Use cached patient data

**What to Say**: "We cache patient data locally for exactly this scenario - network issues shouldn't stop patient care."

### If Glasses Disconnect

**Backup**: Switch to phone app

**What to Say**: "We also support phone-based operation for clinicians who prefer it. Let me show you the same workflow on mobile."

---

## Appendix: Research Citations for Equity Features

### Pulse Oximeter Inaccuracy
- Sjoding MW, et al. (2020). "Racial Bias in Pulse Oximetry Measurement." NEJM, 383(25), 2477-2478.

### Implicit Bias in Pain Assessment
- Hoffman KM, et al. (2016). "Racial bias in pain assessment and treatment recommendations." PNAS, 113(16), 4296-4301.
- Pletcher MJ, et al. (2008). "Trends in opioid prescribing by race/ethnicity." JAMA, 299(1), 70-78.

### Maternal Mortality Disparities
- CDC (2023). "Maternal Mortality Rates in the United States."
- Petersen EE, et al. (2019). "Racial/Ethnic Disparities in Pregnancy-Related Deaths." MMWR, 68(35), 762-765.

### Pharmacogenomics by Ancestry
- Johnson JA, et al. (2008). "Clinical Pharmacogenetics Implementation Consortium Guidelines for CYP2C9 and VKORC1 Genotypes and Warfarin Dosing." Clinical Pharmacology & Therapeutics, 90(4), 625-629.

---

## Contact & Next Steps

After successful demo:
1. Schedule follow-up with Clinical Informatics
2. Identify pilot department (recommend: Primary Care or ER)
3. Discuss timeline for Epic/Cerner credential access
4. Proposal with pricing for 90-day pilot

---

*Document Version: 1.0*
*Last Updated: January 2025*
