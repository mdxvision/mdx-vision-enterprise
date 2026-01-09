# EHR Implementations Status

> Tracks actual code implementation status for each EHR integration.
> **Last Updated:** January 8, 2026

---

## Market Coverage Summary

### Current Coverage

| Market | Coverage | Configured EHRs |
|--------|----------|-----------------|
| **Hospitals** | ~80-85% | Epic, Cerner, MEDITECH, Veradigm |
| **Ambulatory** | ~35% | athenahealth, NextGen, eClinicalWorks |

### To Reach 90%+ Coverage

| Market | Gap | EHRs Needed |
|--------|-----|-------------|
| **Hospitals** | ~10-15% | CPSI/TruBridge (rural), MEDHOST |
| **Ambulatory** | ~15%+ | DrChrono, Practice Fusion, Kareo |

---

## Implementation Status

### Hospital EHRs (Configured: 4)

| EHR | Status | Market Share | FHIR Base URL | Notes |
|-----|--------|--------------|---------------|-------|
| **Epic** | ✅ READY | ~35-38% | `fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` | Dominant in large hospitals |
| **Cerner/Oracle** | ✅ LIVE | ~25-28% | `fhir-open.cerner.com/r4/ec2458f2...` | Full read, demo write via HAPI |
| **MEDITECH** | ✅ READY | ~15-20% | `greenfield.meditech.com/fhir/r4` | Community/rural hospitals |
| **Veradigm** | ✅ READY | ~5-8% | `fhir.fhirpoint.open.allscripts.com/...` | Sunrise (hospital side) |

### Ambulatory EHRs (Configured: 3)

| EHR | Status | Market Share | FHIR Base URL | Notes |
|-----|--------|--------------|---------------|-------|
| **athenahealth** | ✅ READY | ~15% | `api.platform.athenahealth.com/fhir/r4` | Self-service sandbox |
| **eClinicalWorks** | ✅ READY | ~10% | `fhir.eclinicalworks.com/fhir/r4` | Largest cloud EHR |
| **NextGen** | ✅ READY | ~10% | `fhir.nextgen.com/nge/fhir/r4` | Developer program |

### Pending EHRs

| EHR | Market | Share | Status | Notes |
|-----|--------|-------|--------|-------|
| **DrChrono** | Ambulatory | ~5% | ⏳ PENDING | Have account (locked out) |
| **Practice Fusion** | Ambulatory | ~4% | ⏳ PENDING | Awaiting email (Veradigm-owned) |
| **CPSI/TruBridge** | Hospital | ~3-4% | 📋 TODO | Rural/critical access hospitals |
| **Kareo/Tebra** | Ambulatory | ~3% | 📋 TODO | Small practices |
| **MEDHOST** | Hospital | ~2% | 📋 TODO | Community hospitals |
| **Elation** | Ambulatory | ~2% | 📋 TODO | Primary care focused |
| **ModMed** | Ambulatory | ~3% | 📋 TODO | Specialty focused |

---

## Code Locations

### Backend (`ehr-proxy/main.py`)

```python
# Environment Variables (lines ~302-332)
CERNER_CLIENT_ID = os.getenv("CERNER_CLIENT_ID", "0fab9b20-adc8-4940-bbf6-82034d1d39ab")
EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID", "")
VERADIGM_CLIENT_ID = os.getenv("VERADIGM_CLIENT_ID", "11A47952-0F52-4936-A6A3-CF91FDFDDF14")
ATHENA_CLIENT_ID = os.getenv("ATHENA_CLIENT_ID", "")
NEXTGEN_CLIENT_ID = os.getenv("NEXTGEN_CLIENT_ID", "")
MEDITECH_CLIENT_ID = os.getenv("MEDITECH_CLIENT_ID", "MDxVision@269e2312bf404c8293bcfffca232b729")
ECLINICALWORKS_CLIENT_ID = os.getenv("ECLINICALWORKS_CLIENT_ID", "576VCnKhhT1JSru1lkHheokd-iCJjRUkIIc3RmrRf1Y")

# FHIR Base URLs
CERNER_BASE_URL = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
EPIC_BASE_URL = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
VERADIGM_BASE_URL = "https://fhir.fhirpoint.open.allscripts.com/fhirroute/open/sandbox/r4"
MEDITECH_BASE_URL = "https://greenfield.meditech.com/fhir/r4"
ECLINICALWORKS_BASE_URL = "https://fhir.eclinicalworks.com/fhir/r4"
```

### Environment File (`.env.example`)

```bash
# Cerner/Oracle Health
CERNER_CLIENT_ID=0fab9b20-adc8-4940-bbf6-82034d1d39ab
CERNER_CLIENT_SECRET=

# Epic
EPIC_CLIENT_ID=
EPIC_PRIVATE_KEY=

# athenahealth
ATHENA_CLIENT_ID=
ATHENA_CLIENT_SECRET=

# NextGen
NEXTGEN_CLIENT_ID=
NEXTGEN_CLIENT_SECRET=

# Veradigm/Allscripts
VERADIGM_CLIENT_ID=11A47952-0F52-4936-A6A3-CF91FDFDDF14
VERADIGM_CLIENT_SECRET=E32B4F39BA2F

# MEDITECH (Greenfield Workspace)
MEDITECH_CLIENT_ID=MDxVision@269e2312bf404c8293bcfffca232b729
MEDITECH_CLIENT_SECRET=ZCQi_K0MQqqSIGS35j5DNw==
MEDITECH_BASE_URL=https://greenfield.meditech.com/fhir/r4

# eClinicalWorks
ECLINICALWORKS_CLIENT_ID=576VCnKhhT1JSru1lkHheokd-iCJjRUkIIc3RmrRf1Y
ECLINICALWORKS_CLIENT_SECRET=tpxvpRqcgj8Fwa0O16Wf_dOMfQK1vtqew6Dv6-9cv3XI4JCmKy1AXMz5Xrt8mdtz
ECLINICALWORKS_BASE_URL=https://fhir.eclinicalworks.com/fhir/r4
```

---

## FHIR Resources Implemented

| Resource | Read | Create | Update | Delete | Notes |
|----------|------|--------|--------|--------|-------|
| Patient | ✅ | - | - | - | Demographics, photo |
| Observation | ✅ | ✅ | - | - | Vitals, labs |
| Condition | ✅ | - | - | - | Problems/diagnoses |
| MedicationRequest | ✅ | ✅ | ✅ | ✅* | Prescriptions |
| AllergyIntolerance | ✅ | ✅ | - | - | Drug/food allergies |
| CarePlan | ✅ | - | - | - | Treatment plans |
| DocumentReference | ✅ | ✅ | - | - | Clinical notes |
| ServiceRequest | ✅ | ✅ | - | - | Orders (labs, imaging) |
| Immunization | ✅ | - | - | - | Vaccines |
| Procedure | ✅ | - | - | - | Surgeries |
| DiagnosticReport | ✅ | - | - | - | Lab reports |
| Claim | - | ✅ | - | - | Billing claims |

*Soft delete (status change) for HIPAA compliance

---

## Aggregator Platforms (Single API → All EHRs)

> **Fastest path to 90%+ coverage**: One integration instead of dozens.
> See [EHR_AGGREGATOR_PLATFORMS.md](EHR_AGGREGATOR_PLATFORMS.md) for detailed research.

| Platform | Coverage | Best For | Pricing | Recommendation |
|----------|----------|----------|---------|----------------|
| **Redox** | 50+ EHRs, 12,200 orgs | EHR read/write | Free reads, paid writes | ⭐ PRIMARY |
| **Particle Health** | 320M patients, 90% US | Record retrieval | Per-query | ⭐ SECONDARY |
| **Health Gorilla** | TEFCA certified | Lab ordering | Subscription | Enterprise |
| **1upHealth** | 10,000+ facilities | Payer compliance | Per-connection | Payer-focused |

### Why Use Aggregators?

| Direct Integration | Aggregator |
|--------------------|------------|
| 7 EHRs = 14-28 weeks work | 2 platforms = 8-12 weeks |
| ~80% hospital coverage | ~95% hospital coverage |
| ~35% ambulatory coverage | ~90% ambulatory coverage |
| Maintain 7 integrations | Maintain 2 integrations |

### Recommended Strategy

1. **Keep**: Epic, Cerner, MEDITECH (major hospital EHRs)
2. **Add Redox**: For all other EHRs + write-back capability
3. **Add Particle**: For patient record retrieval across networks

---

## Demo/Test Server

| Server | Status | URL | Notes |
|--------|--------|-----|-------|
| **HAPI FHIR** | ✅ LIVE | `http://hapi.fhir.org/baseR4` | Full CRUD for demos |

---

## Adding a New EHR

### 1. Add environment variables
```python
# In main.py
NEW_EHR_CLIENT_ID = os.getenv("NEW_EHR_CLIENT_ID", "")
NEW_EHR_BASE_URL = "https://fhir.newehr.com/r4"
```

### 2. Add to EHR selector
```python
# In get_fhir_client() function
if ehr == "new_ehr":
    return FHIRClient(NEW_EHR_BASE_URL, NEW_EHR_CLIENT_ID, auth_type="oauth2")
```

### 3. Add to startup display
```python
print(f"   • NewEHR: {'✅ READY' if NEW_EHR_CLIENT_ID else '❌ Pending'}")
```

### 4. Test with sandbox patient
```bash
curl http://localhost:8002/api/v1/patient/{patient_id}?ehr=new_ehr
```

---

## Credentials Checklist

### Hospital EHRs
- [x] Epic - Credentials in place (~35-38%)
- [x] Cerner/Oracle - Client ID configured (~25-28%)
- [x] MEDITECH - Greenfield Workspace configured (~15-20%)
- [x] Veradigm - Provider FHIR App configured (~5-8%)
- [ ] CPSI/TruBridge - Rural hospitals (~3-4%)
- [ ] MEDHOST - Community hospitals (~2%)

### Ambulatory EHRs
- [x] athenahealth - Self-service sandbox (~15%)
- [x] eClinicalWorks - Registered and configured (~10%)
- [x] NextGen - Developer program (~10%)
- [ ] DrChrono - Account locked out (~5%)
- [ ] Practice Fusion - Awaiting email (~4%)
- [ ] Kareo/Tebra - Small practices (~3%)
- [ ] ModMed - Specialty focused (~3%)
- [ ] Elation - Primary care (~2%)

### Aggregator Platforms (Alternative)
- [ ] Redox - 50+ EHRs, single API
- [ ] Particle Health - 90% market coverage
- [ ] Health Gorilla - 320M patients

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [EHR_ACCESS_GUIDE.md](EHR_ACCESS_GUIDE.md) | Detailed EHR registration instructions |
| [EHR_AMBULATORY_RESEARCH.md](EHR_AMBULATORY_RESEARCH.md) | DrChrono, Practice Fusion, CPSI/TruBridge research |
| [EHR_AGGREGATOR_PLATFORMS.md](EHR_AGGREGATOR_PLATFORMS.md) | Redox, Particle Health, Health Gorilla, 1upHealth research |
