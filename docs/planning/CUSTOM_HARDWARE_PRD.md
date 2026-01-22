# MDX Glasses - Product Requirements Document

**Document Version**: 1.0
**Created**: December 31, 2025
**Status**: Draft - Internal Planning
**Classification**: Confidential

---

## Executive Summary

MDX Glasses is a proprietary AR smart glasses platform purpose-built for healthcare workflows. Unlike repurposed consumer or industrial AR glasses, MDX Glasses is designed from the ground up for clinical environments, HIPAA compliance, and seamless EHR integration.

**Why Build Our Own Hardware:**
- No existing glasses optimized for healthcare
- Control the full stack (hardware + software + services)
- Higher margins vs licensing fees to Vuzix/others
- Competitive moat - competitors can't replicate quickly
- Custom sensors/features for clinical workflows

---

## Target Users

### Primary Users (Hospital Staff)
| Role | Use Case | Key Requirements |
|------|----------|------------------|
| Physicians | Documentation, orders, patient lookup | Voice-first, EHR integration |
| Nurses | Vitals, medication admin, assessments | Barcode scanning, alerts |
| Transporters | Patient ID verification, routing | Lightweight, durable |
| Phlebotomists | Patient ID, tube labeling | Barcode scanning |
| Pharmacists | Drug verification, interaction checks | Camera, database access |
| Technicians | Procedure checklists, documentation | Hands-free, voice |
| Environmental Services | Room status, cleaning protocols | Durable, easy clean |

### Environment Requirements
- 12+ hour shifts
- Frequent cleaning/sanitization
- Varied lighting (bright ORs, dim patient rooms)
- Noisy environments (alarms, conversations)
- Must not interfere with existing PPE (masks, face shields)

---

## Product Vision

### One-Line Vision
> "The first AR glasses built specifically for healthcare - as essential as a stethoscope."

### Design Principles
1. **Clinical-First**: Every feature designed for healthcare workflows
2. **Invisible Technology**: Disappears into the workflow, not a distraction
3. **Always Ready**: Instant-on, all-day battery, reliable connectivity
4. **HIPAA by Design**: Security and privacy built into hardware
5. **Universal Fit**: Works with PPE, prescription lenses, all head sizes

---

## Hardware Requirements

### Form Factor

| Spec | Target | Notes |
|------|--------|-------|
| Weight | < 45g | Lighter than Vuzix Blade 2 (55g) |
| Form | Standard eyeglass frames | Not industrial/bulky |
| Colors | Black, Navy, Tortoise | Professional appearance |
| Prescription | Rx-compatible lens inserts | Partner with optical labs |
| IPX Rating | IPX4 minimum | Splash resistant for cleaning |

### Display

| Spec | Target | Notes |
|------|--------|-------|
| Type | MicroLED waveguide | Best outdoor visibility |
| Resolution | 640x480 minimum | Readable text at arm's length |
| FOV | 25° diagonal minimum | Larger than Ray-Ban (20°) |
| Brightness | 3,000+ nits | Visible in bright OR lighting |
| Transparency | 85%+ | See patient clearly |
| Eye | Monocular (right, switchable) | Reduce cost, power |

### Audio

| Spec | Target | Notes |
|------|--------|-------|
| Speakers | Open-ear directional | Privacy, hear surroundings |
| Microphones | 4-mic array | Noise cancellation, beamforming |
| Wake Word | Hardware DSP | Always listening, low power |
| Voice Quality | Medical-grade clarity | Accurate transcription in noisy environments |

### Sensors

| Sensor | Purpose |
|--------|---------|
| Camera (8MP+) | Barcode scanning, document capture |
| Proximity | Auto-lock when removed from face |
| IMU (Accel/Gyro) | Head tracking, gesture detection |
| Ambient Light | Auto-brightness adjustment |
| Touch Pad | Temple-based controls |

### Connectivity

| Spec | Target |
|------|--------|
| WiFi | 802.11ax (WiFi 6E) |
| Bluetooth | 5.3 LE Audio |
| Companion App | Required (phone handles compute) |
| Standalone | Future version with on-device AI |

### Power

| Spec | Target | Notes |
|------|--------|-------|
| Battery Life | 8+ hours | Full shift coverage |
| Charging | USB-C magnetic | Easy dock connection |
| Quick Charge | 2 hours from 15 min charge | Lunch break top-up |
| Hot Swap | Optional battery pack | Extended procedures |

---

## Software Requirements

### Core Features (MVP)

| Feature | Priority | Description |
|---------|----------|-------------|
| Voice Commands | P0 | Full MDX Vision command set |
| Wake Word | P0 | "Hey MDx" always-on detection |
| Patient Lookup | P0 | Voice search, barcode scan |
| Vitals Display | P0 | Real-time HUD overlay |
| Alerts | P0 | Critical labs, allergies, interactions |
| Transcription | P0 | Real-time speech-to-text |
| EHR Push | P0 | Write notes, orders to EHR |

### Security Features (MVP)

| Feature | Priority | Description |
|---------|----------|-------------|
| Voiceprint Auth | P0 | Biometric unlock |
| Proximity Lock | P0 | Auto-lock when removed |
| TOTP Backup | P0 | 6-digit code fallback |
| Encryption | P0 | AES-256 all data at rest |
| Remote Wipe | P0 | MDM integration |
| Audit Logging | P0 | All PHI access logged |

### Future Features (Post-MVP)

| Feature | Priority | Description |
|---------|----------|-------------|
| AR Overlays | P1 | Patient info floating above bed |
| Vein Visualization | P1 | Camera + AI for IV placement |
| Wound Measurement | P1 | Computer vision wound assessment |
| Translation Overlay | P1 | Real-time subtitle translation |
| Navigation | P2 | Indoor hospital wayfinding |
| Training Mode | P2 | AR procedure guidance |

---

## Companion App Requirements

MDX Glasses require a smartphone companion app for compute-heavy processing.

### Supported Platforms
- Android 12+ (primary)
- iOS 16+ (secondary)

### Companion App Functions
| Function | Description |
|----------|-------------|
| Pairing | Bluetooth setup, authentication |
| Compute Offload | AI inference, transcription processing |
| Network Bridge | WiFi/cellular for cloud services |
| Settings | User preferences, display config |
| Updates | OTA firmware updates |
| Diagnostics | Battery, connectivity, logs |

---

## Manufacturing Considerations

### Bill of Materials (Target)

| Component | Estimated Cost | Supplier Options |
|-----------|---------------|------------------|
| MicroLED Display | $80-120 | JBD, Vuzix, Dispelix |
| Waveguide | $40-60 | Lumus, DigiLens, WaveOptics |
| Camera Module | $15-25 | Omnivision, Sony |
| Audio System | $20-30 | Knowles, Qualcomm |
| Processor | $25-40 | Qualcomm AR1/AR2 Gen 1 |
| Battery | $10-15 | Custom LiPo |
| Frame/Housing | $20-30 | Injection molded |
| PCB/Assembly | $30-50 | Flex Rigid |
| **Total BOM** | **$240-370** | Target < $300 |

### Target Pricing

| Model | BOM | MSRP | Margin |
|-------|-----|------|--------|
| MDX Glasses Standard | $300 | $799 | 62% |
| MDX Glasses Pro (standalone AI) | $450 | $1,299 | 65% |

### Manufacturing Partners (To Explore)
- Luxottica (frames, optical expertise)
- Flex (electronics manufacturing)
- Jabil (medical device experience)
- Vuzix (existing AR manufacturing)

---

## Regulatory Requirements

### Medical Device Classification
- **USA (FDA)**: Class I exempt or Class II 510(k)
  - If diagnostic/treatment: Class II
  - If documentation only: Likely exempt
- **EU (MDR)**: Class I or IIa depending on claims
- **UK (UKCA)**: Aligned with MDR

### Required Certifications
| Certification | Market | Timeline |
|--------------|--------|----------|
| FCC | USA | Required before sale |
| CE | EU | Required before sale |
| UKCA | UK | Required before sale |
| FDA (if Class II) | USA | 6-12 months |
| HIPAA Attestation | USA | Internal + third-party audit |
| SOC 2 Type II | USA | Recommended for enterprise |

### Safety Standards
- IEC 62471 (photobiological safety)
- EN 60950-1 (electrical safety)
- Laser Class 1 (eye safety)

---

## Competitive Positioning

### vs. Consumer AR (Ray-Ban Meta, Xreal)
| Aspect | Consumer | MDX Glasses |
|--------|----------|-------------|
| Target | General public | Healthcare workers |
| Security | Basic | HIPAA-compliant, voiceprint |
| EHR Integration | None | Native FHIR |
| Battery | 4-6 hours | 8+ hours |
| Durability | Consumer | Medical-grade |
| Support | Consumer warranty | Enterprise SLA |

### vs. Industrial AR (Vuzix, RealWear)
| Aspect | Industrial | MDX Glasses |
|--------|------------|-------------|
| Form Factor | Bulky, industrial | Sleek, eyeglass-like |
| Weight | 100-140g | < 45g |
| Clinical Features | Generic | Purpose-built |
| Price | $1,300-2,500 | $799 |
| EHR Integration | Requires custom dev | Native |

### vs. Competitors (Nuance, Abridge, Suki)
| Aspect | Competitors | MDX Glasses |
|--------|-------------|-------------|
| Hardware | None (phone/tablet app) | Dedicated AR glasses |
| Hands-Free | No | Yes |
| Eyes on Patient | No | Yes |
| Hospital-Wide | No (physicians only) | All staff |

---

## Roadmap

### Phase 1: Reference Design (Q1 2026)
- [ ] Component selection finalized
- [ ] Industrial design concepts (3 options)
- [ ] User research with 10+ clinicians
- [ ] Optical design validation
- [ ] Companion app architecture

### Phase 2: Prototype (Q2 2026)
- [ ] Functional prototype (3D printed + dev boards)
- [ ] Display/optics integration
- [ ] Software port from Vuzix
- [ ] Internal testing (50 hours wear time)
- [ ] Clinical workflow validation

### Phase 3: EVT (Engineering Validation Test) - Q3 2026
- [ ] First molded units
- [ ] Full feature software
- [ ] 100-unit pilot production
- [ ] Clinical pilot (3 sites, 50 users)
- [ ] FCC/CE pre-certification testing

### Phase 4: DVT/PVT (Q4 2026)
- [ ] Design validation testing
- [ ] Production validation testing
- [ ] Manufacturing line setup
- [ ] Certification submissions
- [ ] Pre-orders open

### Phase 5: Mass Production (Q1 2027)
- [ ] Production ramp
- [ ] Launch to pilot customers
- [ ] General availability

---

## Success Metrics

### Hardware KPIs
| Metric | Target |
|--------|--------|
| Weight | < 45g |
| Battery Life | > 8 hours |
| Display Brightness | > 3,000 nits |
| Boot Time | < 5 seconds |
| Defect Rate | < 2% |

### User KPIs
| Metric | Target |
|--------|--------|
| Daily Active Usage | > 6 hours |
| NPS Score | > 50 |
| Support Tickets | < 1 per user/month |
| Return Rate | < 5% |

### Business KPIs
| Metric | Target (Year 1) |
|--------|-----------------|
| Units Sold | 5,000 |
| Revenue | $4M |
| Gross Margin | > 60% |
| CAC | < $500 |

---

## Open Questions

1. **Build vs Partner**: Should we partner with an existing manufacturer (Vuzix, Luxottica) or build in-house?
2. **Standalone vs Companion**: Should MVP require phone, or invest in on-device AI?
3. **Prescription Strategy**: Partner with optical chains or direct-to-consumer?
4. **FDA Pathway**: Pursue medical device claims or stay exempt?
5. **Pricing Strategy**: Premium ($1,299) or accessible ($799)?

---

## Appendix

### A. User Research Questions
- How many hours per shift do you currently use a computer?
- What information do you need most frequently during patient care?
- What PPE do you wear that glasses must work with?
- What's the longest you'd be willing to wear AR glasses?
- What would make you stop using AR glasses?

### B. Competitor Teardowns Needed
- Vuzix Blade 2 (current platform)
- Ray-Ban Meta (consumer benchmark)
- XREAL Air 2 (low-cost benchmark)
- RealWear Navigator 520 (industrial benchmark)

### C. Key Vendor Contacts
- **Qualcomm**: AR platform (Snapdragon AR1/AR2)
- **JBD**: MicroLED displays
- **Lumus**: Waveguide optics
- **Flex**: Contract manufacturing

---

*This document should be reviewed weekly during active development.*
