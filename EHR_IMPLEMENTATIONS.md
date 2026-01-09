# EHR Implementations Status

> Tracks actual code implementation status for each EHR integration.
> **Last Updated:** January 8, 2026

---

## Implementation Status

| EHR | Status | FHIR Base URL | Client ID | Auth Type | Notes |
|-----|--------|---------------|-----------|-----------|-------|
| **Cerner/Oracle** | ✅ LIVE | `fhir-open.cerner.com/r4/ec2458f2...` | `0fab9b20-adc8...` | Open | Full read, demo write via HAPI |
| **Epic** | ✅ READY | `fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` | Configured | OAuth2 | Sandbox ready |
| **athenahealth** | ✅ READY | `api.platform.athenahealth.com/fhir/r4` | Configured | OAuth2 | Self-service sandbox |
| **NextGen** | ✅ READY | `fhir.nextgen.com/nge/fhir/r4` | Configured | OAuth2 | Developer program |
| **Veradigm** | ⏳ PENDING | `fhir.fhirpoint.open.allscripts.com/...` | - | OAuth2 | Needs credentials |
| **eClinicalWorks** | ✅ READY | `fhir.eclinicalworks.com/fhir/r4` | `576VCnKhhT1J...` | OAuth2 | Largest cloud EHR |
| **MEDITECH** | ✅ READY | `greenfield.meditech.com/fhir/r4` | `MDxVision@269e...` | OAuth2 | Greenfield Workspace |
| **DrChrono** | 📋 TODO | - | - | OAuth2 | Cloud EHR |
| **Elation** | 📋 TODO | - | - | OAuth2 | Primary care focused |
| **ModMed** | 📋 TODO | - | - | OAuth2 | Specialty focused |

---

## Code Locations

### Backend (`ehr-proxy/main.py`)

```python
# Environment Variables (lines ~302-332)
CERNER_CLIENT_ID = os.getenv("CERNER_CLIENT_ID", "0fab9b20-adc8-4940-bbf6-82034d1d39ab")
EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID", "")
VERADIGM_CLIENT_ID = os.getenv("VERADIGM_CLIENT_ID", "")
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
VERADIGM_CLIENT_ID=
VERADIGM_CLIENT_SECRET=

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

## Integration Platforms (Alternative to Direct)

| Platform | Status | Coverage | Notes |
|----------|--------|----------|-------|
| **Redox** | 📋 TODO | 50+ EHRs | Single API, free reads |
| **Health Gorilla** | 📋 TODO | 320M patients | Aggregated data |
| **Particle Health** | 📋 TODO | 90% EHR market | Single connection |
| **1upHealth** | 📋 TODO | 10,000+ health centers | FHIR-first |

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

- [x] Cerner/Oracle - Client ID configured
- [x] Epic - Credentials in place
- [x] athenahealth - Self-service sandbox
- [x] NextGen - Developer program
- [ ] Veradigm - Awaiting credentials
- [x] eClinicalWorks - Registered and configured
- [x] MEDITECH - Greenfield Workspace configured
- [ ] DrChrono - Need to register
- [ ] Redox - Consider for multi-EHR
- [ ] Particle Health - Consider for coverage

---

*See [EHR_ACCESS_GUIDE.md](EHR_ACCESS_GUIDE.md) for detailed registration instructions.*
