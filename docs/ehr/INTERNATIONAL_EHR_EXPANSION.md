# MDx Vision - International EHR Expansion Guide

**Created**: December 31, 2025
**Purpose**: Roadmap for expanding EHR integrations beyond US Cerner

---

## Executive Summary

Our FHIR-first architecture means ~70% of code works internationally. The remaining 30% is:
- OAuth/auth flows (vendor-specific)
- Regional FHIR profiles (slightly different field mappings)
- Compliance/consent UI

**Key Insight**: FHIR is becoming the global standard. Europe mandates it by 2027 (EHDS), Asia is training on it now (AeHIN), and Australia/Canada already use it.

---

## Global FHIR Adoption Status

| Region | FHIR Status | Timeline |
|--------|-------------|----------|
| **USA** | Mandated (21st Century Cures Act) | Now |
| **Europe** | EHDS mandates FHIR | March 2027 |
| **UK** | NHS Digital promoting FHIR | Now |
| **Asia** | AeHIN training launched June 2025 | 2026-2028 |
| **Australia** | My Health Record uses FHIR | Now |
| **Canada** | Provincial adoption ongoing | Now |

---

## EHR Market Share by Region

### USA (Current Market)

| Vendor | Market Share | FHIR Support | Status |
|--------|--------------|--------------|--------|
| **Epic** | 41% | Excellent | Priority target |
| **Oracle Cerner** | 22% | Excellent | **Integrated** |
| Meditech | 13% | Good | Future |
| Evident | 9% | Limited | Low priority |
| Netsmart | 2% | Partial | Behavioral health |

### UK / NHS

| Vendor | Status | FHIR Support | Expansion Effort |
|--------|--------|--------------|------------------|
| **Oracle Cerner** | #1 by hospital beds | Same as US | LOW |
| Dedalus | Strong presence | FHIR R4 | MEDIUM |
| Epic | Growing (major trusts) | Same as US | LOW |

**Notes**:
- 90% of NHS trusts have electronic patient records
- NHS England investing $2.36B in EHR adoption
- Cerner APIs largely identical to US

### Germany

| Vendor | Status | FHIR Support | Expansion Effort |
|--------|--------|--------------|------------------|
| **Dedalus** | Market leader | FHIR R4 | MEDIUM |
| CompuGroup Medical | Strong regional | Partial | HIGH |
| SAP | Enterprise | FHIR R4 | MEDIUM |

**Notes**:
- ~80% of GPs use EHR systems
- ~70% hospital EHR adoption
- KZHG funding driving growth
- Gematik certification required

### France

| Vendor | Status | FHIR Support | Expansion Effort |
|--------|--------|--------------|------------------|
| Hopsis | Regional leader | Partial | HIGH |
| Softway Medical | Regional | Partial | HIGH |
| Dedalus | Growing | FHIR R4 | MEDIUM |

**Notes**:
- 88% EMR adoption among primary care
- More fragmented market than other EU countries
- HDS (Health Data Hosting) certification required

### Australia

| Vendor | Status | FHIR Support | Expansion Effort |
|--------|--------|--------------|------------------|
| **Epic** | 191 hospitals (NSW) | Same as US | LOW |
| My Health Record | National platform | FHIR native | LOW |
| Oracle Cerner | Strong presence | Same as US | LOW |

**Notes**:
- 90%+ GP practices use EHR
- 85%+ public hospitals have EHR
- My Health Record is national FHIR platform
- Must integrate opt-out checking

### Canada

| Vendor | Status | FHIR Support | Expansion Effort |
|--------|--------|--------------|------------------|
| **Meditech** | #1 in hospitals | Good | MEDIUM |
| Oracle Cerner | Strong | Same as US | LOW |
| Epic | Growing | Same as US | LOW |

**Notes**:
- 85%+ hospital EHR adoption
- CAD 2B+ invested in digital health
- Provincial health authority approvals required
- Consent models vary by province

### Middle East

| Vendor | Status | FHIR Support | Expansion Effort |
|--------|--------|--------------|------------------|
| **Oracle Cerner** | Dominant | Same as US | LOW |
| InterSystems | Growing | Good | MEDIUM |
| Epic | Select facilities | Same as US | LOW |

**Notes**:
- UAE, Saudi Arabia, Qatar leading adoption
- Arabic language support required
- Local data residency often required

---

## Technical Architecture

### Current State
```
MDx Vision App → EHR Proxy → Cerner FHIR API
```

### Target Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    MDx Vision Core                       │
│         (Voice, Display, Clinical Logic)                 │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  FHIR Abstraction Layer                  │
│    Normalized: Patient, Observation, MedicationRequest   │
└─────────────────────────────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cerner    │     │    Epic     │     │  Dedalus    │
│   Adapter   │     │   Adapter   │     │   Adapter   │
│  (US, UK,   │     │  (US, AU,   │     │  (EU)       │
│   CA, AU)   │     │   UK)       │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### EHR Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from models import FHIRPatient, Observation, MedicationRequest, DocumentReference

class EHRAdapter(ABC):
    """Abstract base class for EHR vendor integrations."""

    @abstractmethod
    def get_auth_url(self) -> str:
        """OAuth authorization URL (varies by vendor)."""
        pass

    @abstractmethod
    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange OAuth code for access token."""
        pass

    @abstractmethod
    def get_patient(self, patient_id: str) -> FHIRPatient:
        """Fetch patient demographics."""
        pass

    @abstractmethod
    def get_vitals(self, patient_id: str) -> List[Observation]:
        """Fetch patient vital signs."""
        pass

    @abstractmethod
    def get_medications(self, patient_id: str) -> List[MedicationRequest]:
        """Fetch active medications."""
        pass

    @abstractmethod
    def get_allergies(self, patient_id: str) -> List[dict]:
        """Fetch patient allergies."""
        pass

    @abstractmethod
    def push_note(self, patient_id: str, note: DocumentReference) -> bool:
        """Write clinical note to EHR."""
        pass

    @abstractmethod
    def push_vital(self, patient_id: str, observation: Observation) -> bool:
        """Write vital sign to EHR."""
        pass
```

### Vendor-Specific Adapters

| Adapter | Effort | Notes |
|---------|--------|-------|
| `CernerAdapter` | Done | Current implementation |
| `EpicAdapter` | 2 weeks | Different OAuth (MyChart), same FHIR |
| `DedalusAdapter` | 3 weeks | EU FHIR profiles, different auth |
| `MeditechAdapter` | 2 weeks | Slightly different FHIR mappings |
| `MyHealthRecordAdapter` | 1 week | Australia national platform |

---

## Regional Compliance Requirements

### European Union (GDPR + EHDS)

| Requirement | Details |
|-------------|---------|
| Consent | Explicit consent for data processing |
| Data Residency | May require EU-based servers |
| Right to Erasure | Must support deletion requests |
| Data Portability | Must export in standard format |
| DPO | Data Protection Officer required |
| EHDS Compliance | Full FHIR compliance by March 2027 |

### UK (GDPR + NHS)

| Requirement | Details |
|-------------|---------|
| NHS Digital Approval | Required for NHS integration |
| DTAC | Digital Technology Assessment Criteria |
| DCB0129 | Clinical safety standard |
| Data Residency | UK or adequate jurisdiction |

### Germany

| Requirement | Details |
|-------------|---------|
| Gematik Certification | Required for health data apps |
| GDPR | Full compliance |
| German Language | UI must support German |

### France

| Requirement | Details |
|-------------|---------|
| HDS Certification | Health Data Hosting certification |
| GDPR | Full compliance |
| French Language | UI must support French |

### Australia

| Requirement | Details |
|-------------|---------|
| My Health Record | Must check opt-out status |
| Privacy Act 1988 | Australian privacy compliance |
| State Health Depts | May need state-level approvals |

### Canada

| Requirement | Details |
|-------------|---------|
| PIPEDA | Federal privacy law |
| Provincial Laws | PHIPA (ON), HIA (AB), etc. |
| Provincial Approvals | Each province may require approval |
| French Language | Required for Quebec |

---

## Expansion Roadmap

### Phase 1: US Dominance (Now - Q1 2026)
- [x] Cerner integration (22% market)
- [ ] Epic integration (41% market)
- [ ] Meditech integration (13% market)

**Goal**: Cover 76% of US hospital market

### Phase 2: English-Speaking Markets (Q2 2026)
- [ ] UK (NHS Cerner/Epic sites)
- [ ] Australia (Epic + My Health Record)
- [ ] Canada (Cerner/Epic + Meditech)

**Why**: Same vendors, same language, similar regulations

### Phase 3: European Expansion (Q3-Q4 2026)
- [ ] Germany (Dedalus)
- [ ] France (Dedalus + regional)
- [ ] Netherlands, Belgium, Nordics

**Why**: EHDS deadline March 2027 creates urgency

### Phase 4: Growth Markets (2027)
- [ ] Middle East (Cerner-dominant)
- [ ] Southeast Asia (greenfield)
- [ ] Latin America (varied)

---

## Effort Estimates by Market

| Market | Primary EHR | Dev Effort | Compliance | Total |
|--------|-------------|------------|------------|-------|
| **US (Epic)** | Epic | 2 weeks | 2 weeks | 4 weeks |
| **UK** | Cerner/Epic | 1 week | 4 weeks | 5 weeks |
| **Australia** | Epic/Cerner | 2 weeks | 3 weeks | 5 weeks |
| **Canada** | Meditech/Cerner | 3 weeks | 4 weeks | 7 weeks |
| **Germany** | Dedalus | 4 weeks | 6 weeks | 10 weeks |
| **France** | Fragmented | 6 weeks | 6 weeks | 12 weeks |
| **Middle East** | Cerner | 2 weeks | 4 weeks | 6 weeks |

---

## Key Vendor Contacts

### Epic
- Developer Portal: https://fhir.epic.com/
- App Orchard: https://apporchard.epic.com/
- Certification: Required for production

### Oracle Cerner (Current)
- Developer Portal: https://code.cerner.com/
- Certification: Millennium App Gallery

### Dedalus
- Contact: partnerships@dedalus.com
- Markets: EU, UK, South America

### Meditech
- Developer Portal: https://ehr.meditech.com/
- Markets: US, Canada

---

## Sources

- [HL7 Europe FHIR for EHDS](https://www.hl7europe.org/new-hl7-europe-fhir-implementation-guides-to-support-the-european-health-data-space/)
- [Asia eHealth FHIR Training](https://www.asiaehealthinformationnetwork.org/2025/06/24/official-hl7-fhir-fundamentals-training-commences-for-the-asia-ehealth-information-network/)
- [Global EHR Market Share 2024](https://healthmanagement.org/c/healthmanagement/issuearticle/global-ehr-market-share-in-2024)
- [Top EHR Vendors Worldwide - Becker's](https://www.beckershospitalreview.com/ehrs/top-6-ehr-vendors-worldwide/)
- [Dedalus & Cerner in EMEA - Signify Research](https://www.signifyresearch.net/insights/dedalus-oracle-cerner-occupy-top-spot-for-2022-ehr-revenues-in-emea/)
- [EHR Industry Statistics 2025](https://media.market.us/ehr-industry-statistics/)

---

*This document should be reviewed quarterly and updated based on market changes and expansion progress.*
