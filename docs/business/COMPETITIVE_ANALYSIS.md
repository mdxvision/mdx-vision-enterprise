# MDx Vision - Internal Competitive Analysis

**CONFIDENTIAL - INTERNAL USE ONLY**
**Created**: December 31, 2024
**Purpose**: Competitive intelligence and differentiation analysis

---

## Competitor Claimed Metrics (Verified Sources)

| Competitor | Time Saved | Burnout Reduction | Languages | Source |
|------------|------------|-------------------|-----------|--------|
| **Nuance DAX** | 50% reduction, 7 min/encounter | 70% | Not specified (English primary) | [PMC Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10990544/), [Nuance PR](https://news.nuance.com/2024-01-18-Nuance-Announces-General-Availability-of-DAX-Copilot-Embedded-in-Epic) |
| **Abridge** | 2 hours/day | 21% burnout reduction (84 days) | 28 languages | [Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/sharp-healthcare-mainhealth-other-large-systems-report-time-savings-strong), [Contrary Research](https://research.contrary.com/company/abridge) |
| **Suki** | 72% reduction, 3.3 hrs/week | 60% | 12+ languages | [AAFP](https://www.aafp.org/news/media-center/releases/suki-assistant.html), [Suki News](https://www.suki.ai/news/suki-assistant-significantly-reduces-primary-care-physician-documentation-burden/) |
| **DeepScribe** | 2 min/encounter | N/A | English primary | [DeepScribe](https://www.deepscribe.ai/resources/deepscore-measuring-the-performance-of-ambient-ai-clinical-documentation) |
| **Augmedix** | 1-2 hrs/day, 80% reduction | N/A | English primary | [Augmedix PR](https://augmedix.com/resources/news/press-release/augmedix-announces-new-positive-data-and-enhancements-to-its-ambient-ai-product-augmedix-go/) |

---

## Device Support Reality Check

### Current Competitors - ALL Screen-Based

| Competitor | Devices Supported | AR/HMD Support |
|------------|-------------------|----------------|
| Nuance DAX | Phone, Tablet, Desktop | **NO** |
| Abridge | Phone, Tablet, Desktop | **NO** |
| Suki | Phone, Tablet, Desktop | **NO** |
| DeepScribe | Phone, Tablet, Desktop | **NO** |
| Augmedix | Phone, Tablet, Desktop, Google Glass (legacy) | **Limited** |

### Ray-Ban Meta Glasses - Current Status

**Can we run MDx Vision on Ray-Bans today?**

**NO - and here's why:**

| Factor | Status | Details |
|--------|--------|---------|
| SDK Availability | Preview only | [Meta SDK](https://developers.meta.com/wearables/faq/) released Dec 2024 |
| App Distribution | Restricted | Only select partners can publish, open access expected 2026 |
| App Architecture | Phone-based | Apps run on phone, not on glasses |
| Third-party AI | Not supported | Can't use Meta AI, must use own models |
| Battery Impact | High | Continuous streaming drains battery |
| Display Access | Limited | Display API not fully exposed yet |

**Source**: [Road to VR](https://www.roadtovr.com/meta-ray-ban-smart-glasses-third-party-app-sdk-device-access-toolkit/), [UploadVR](https://www.uploadvr.com/meta-wearables-device-access-toolkit-public-preview/)

### MDx Vision Device Reality

**What we actually support TODAY:**
- Vuzix Blade 2 (native Android)
- RealWear Navigator 500/520 (native Android)
- Google Glass Enterprise Edition 2 (native Android)
- Any Android HMD running Android 10+

**What we could support with work:**
- Ray-Ban Meta (requires SDK integration, 2026+ for public distribution)
- Apple Vision Pro (requires visionOS development)
- Meta Quest Pro (requires Quest SDK)

---

## Language Support Comparison

| Platform | Languages | Dialects | Notes |
|----------|-----------|----------|-------|
| **Abridge** | 28 | Unknown | Best in class for competitors |
| **Suki** | 12+ | Unknown | Includes Spanish |
| **Nuance DAX** | English + few | Unknown | Focus on English |
| **DeepScribe** | English primary | Unknown | Limited |
| **Augmedix** | English primary | Unknown | Limited |
| **MDx Vision (Current)** | 5 | Limited | English, Spanish, Russian, Mandarin, Portuguese |
| **MDx Vision (Target)** | 500+ | 1000+ | See expansion plan below |

### Language Expansion Plan

To support 500+ languages, we need:

1. **Speech Recognition**: Partner with or integrate:
   - Google Cloud Speech-to-Text: 125+ languages
   - Azure Speech: 100+ languages
   - Whisper (OpenAI): 99 languages
   - AssemblyAI: 12 languages (current)
   - Deepgram: 36 languages

2. **Text-to-Speech**:
   - Google TTS: 50+ languages
   - Azure TTS: 140+ languages
   - Amazon Polly: 60+ languages

3. **Medical Terminology by Language**:
   - This is the hard part
   - Medical terms in 500+ languages don't exist in standard databases
   - Need: custom medical vocabulary per language

**Realistic Target**:
- Phase 1: 50 languages (top spoken globally)
- Phase 2: 150 languages (covers 95% of world population)
- Phase 3: 500+ (including dialects)

---

## Feature Comparison: What They Don't Have

### Features ONLY MDx Vision Has

| Feature | Nuance | Abridge | Suki | DeepScribe | Augmedix | MDx Vision |
|---------|--------|---------|------|------------|----------|------------|
| **AR Glasses / HMD Support** | ❌ | ❌ | ❌ | ❌ | ⚠️ Legacy | ✅ |
| **Hands-Free, Eyes on Patient** | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ |
| **Real-time HUD Display** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Voice Ordering (Labs/Imaging/Meds)** | ❌ | ❌ | ⚠️ Limited | ❌ | ❌ | ✅ |
| **Voice Vitals Entry** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Critical Alerts (Spoken Real-time)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Drug Interaction Alerts** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **FHIR Write-Back (Full CRUD)** | ⚠️ Read | ⚠️ Read | ⚠️ Limited | ⚠️ Read | ⚠️ Read | ✅ |
| **Voiceprint Biometric Auth** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Proximity Lock (Glasses Off = Lock)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Remote Device Wipe** | N/A | N/A | N/A | N/A | N/A | ✅ |
| **Offline Mode with Sync** | ❌ | ⚠️ Limited | ❌ | ❌ | ❌ | ✅ |
| **Procedure Safety Checklists** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Medical Calculators (Voice)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **SBAR Handoff Reports** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Encounter Timer** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Legend**: ✅ = Full support, ⚠️ = Partial/Limited, ❌ = Not available

---

## Projected Time Savings: Our Hypothesis

### Baseline: Competitor Average
Based on verified competitor data:
- **Documentation time reduction**: 50-72%
- **Time saved per encounter**: 7 minutes average
- **Daily savings**: 1-2 hours

### MDx Vision Differentiator Multipliers

| Differentiator | Time Impact | Reasoning |
|----------------|-------------|-----------|
| **No Screen Switching** | +15-25% efficiency | Competitors require looking at phone/tablet. We don't. |
| **Real-time Alerts** | +5-10% (error prevention) | Catching drug interactions/critical labs DURING encounter prevents rework |
| **Voice Ordering** | +10-15% | No navigating EHR menus to place orders |
| **Voice Vitals Entry** | +5% | No manual data entry |
| **Hands-Free Operation** | +10% | No picking up/putting down devices |
| **Offline Mode** | N/A (availability) | Works in dead zones, basement clinics |

### Projected MDx Vision Metrics (Hypothesis)

| Metric | Competitor Avg | MDx Vision Projected | Improvement |
|--------|----------------|---------------------|-------------|
| **Documentation Time Reduction** | 50-60% | **70-80%** | +20-30% |
| **Time Saved Per Encounter** | 7 min | **10-12 min** | +3-5 min |
| **Daily Time Savings** | 1.5 hrs | **2.5-3 hrs** | +1-1.5 hrs |
| **Burnout Reduction** | 60-70% | **75-85%** | +10-15% |
| **Same-Day Note Closure** | 70-80% | **90-95%** | +15-20% |
| **After-Hours Documentation** | -30% | **-50%** | Additional 20% reduction |

### Justification for Higher Numbers

1. **No Context Switching**: Studies show context switching costs 23% of productivity. We eliminate the phone/screen entirely.

2. **Eyes on Patient**: Better patient engagement = fewer follow-up questions = faster encounters.

3. **Real-time Data**: Patient data visible in HUD means no "let me check that" moments.

4. **Error Prevention**: Catching critical values and interactions during the encounter prevents callbacks and rework.

5. **Voice-First Design**: 100% hands-free vs competitors who still require some screen interaction.

---

## Pricing Intelligence (Estimated)

| Competitor | Pricing Model | Estimated Cost |
|------------|---------------|----------------|
| **Nuance DAX** | Per clinician/month | $300-500/mo per clinician |
| **Abridge** | Per clinician/month | $200-400/mo per clinician |
| **Suki** | Per clinician/month | $150-300/mo per clinician |
| **DeepScribe** | Per clinician/month | $250-400/mo per clinician |
| **Augmedix** | Per clinician/month | $300-500/mo per clinician |

**Note**: Hardware costs are separate for all. MDx Vision would include glasses cost or rental.

---

## Competitive Weaknesses to Exploit

### 1. All Competitors Are Screen-Dependent
**Their Problem**: Clinicians still look at phones/tablets, breaking eye contact with patients.
**Our Advantage**: True hands-free, eyes-on-patient experience.

### 2. Limited EHR Write Capability
**Their Problem**: Most are read-only or limited to notes. Can't place orders.
**Our Advantage**: Full CRUD - push notes, vitals, orders, allergies, medication changes.

### 3. No Real-Time Safety Alerts
**Their Problem**: Documentation happens post-encounter. Errors caught later.
**Our Advantage**: Critical labs, drug interactions, allergy warnings spoken in real-time.

### 4. No Biometric Security
**Their Problem**: Basic authentication. If device stolen, data exposed.
**Our Advantage**: TOTP + Voiceprint + Proximity lock + Remote wipe.

### 5. English-Centric
**Their Problem**: Abridge leads with 28 languages, but most are English-only.
**Our Advantage**: Path to 500+ languages with accent-insensitive recognition.

### 6. No Hardware Integration
**Their Problem**: Software only. Depend on user's existing devices.
**Our Advantage**: Purpose-built for medical AR glasses. Better optimization.

---

## Risks & Honest Assessment

### Where Competitors Are Stronger

| Area | Who Leads | Gap |
|------|-----------|-----|
| **EHR Integration Depth** | Nuance (Microsoft/Epic native) | Deep Epic integration |
| **Language Support (Today)** | Abridge (28 languages) | We have 5 |
| **Market Presence** | Nuance, Abridge | They have major health system deployments |
| **AI Model Quality** | All (larger training data) | They have more clinical data |
| **Specialty Coverage** | Augmedix (50+ specialties) | We need specialty templates |

### Our Honest Gaps

1. **Language**: 5 vs 28. Need to expand.
2. **EHR Integration**: No native Epic/Oracle integration yet.
3. **Clinical Validation**: No peer-reviewed studies on our platform.
4. **Market Proof**: No major health system deployments.
5. **Hardware Dependency**: Requires glasses (barrier to adoption).

---

## Strategic Recommendations

### Short-Term (Q1 2025)
1. Partner with one major health system for pilot study
2. Publish time savings data (even small study)
3. Expand to 25+ languages (match Abridge)
4. Get Epic App Orchard certification

### Medium-Term (Q2-Q3 2025)
1. Conduct peer-reviewed clinical study
2. Expand to 100+ languages
3. Oracle/Cerner native integration
4. Ray-Ban Meta SDK integration (when available)

### Long-Term (Q4 2025+)
1. 500+ languages
2. Apple Vision Pro support
3. Major health system deployments
4. Peer-reviewed publications in JAMIA, NEJM

---

## Summary: Our Positioning

**We are NOT competing on the same playing field.**

Competitors: "AI scribe that documents your visit"
MDx Vision: "AR platform that transforms how clinicians work"

| Dimension | Competitors | MDx Vision |
|-----------|-------------|------------|
| Core Product | Software | Hardware + Software |
| Interface | Phone/Tablet/Desktop | AR Glasses (HUD) |
| Interaction | Some voice + touch | 100% Voice |
| Workflow | Documentation | Documentation + Orders + Alerts + Safety |
| Security | Basic | Military-grade (biometrics) |

**We're not a better scribe. We're a different category.**

---

*This document is for internal strategic planning only. Do not distribute externally.*
