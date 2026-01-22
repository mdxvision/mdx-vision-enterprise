# EHR Developer Access Guide

> Quick reference for EHR sandbox/API access for MDx Vision integration testing.
> **Last Updated:** January 4, 2025

---

## Summary Table - EHR Vendors (Direct)

| EHR Platform | Cost | Self-Service | FHIR R4 | Sandbox | Notes |
|--------------|------|--------------|---------|---------|-------|
| **Cerner/Oracle** | FREE | Yes | Yes | Yes | Code Console - REGISTERED |
| **Epic** | FREE* | Yes | Yes | Yes | App Orchard ($500 listing fee for production) |
| **athenahealth** | FREE | Yes | Yes | Yes | Developer Portal self-service |
| **eClinicalWorks** | FREE | Yes | Yes | Yes | FHIR APIs with registration |
| **NextGen** | FREE | Yes | Yes | Yes | Developer Program |
| **MEDITECH** | FREE | Yes | Yes | Yes | Greenfield Workspace |
| **Veradigm/Allscripts** | FREE* | Yes | Yes | Yes | Anonymous sandbox + paid tiers |
| **Elation Health** | FREE | Yes | Yes | Yes | Primary care focused |
| **DrChrono** | FREE | Yes | Yes | Yes | Cloud-based EHR |
| **Practice Fusion** | FREE | Yes | Yes | Yes | Free EHR with FHIR APIs |
| **CareCloud** | FREE | Yes | Yes | Yes | Developer portal available |
| **ModMed** | FREE* | Apply | Yes | Yes | 2-week sandbox provisioning |
| **Greenway Health** | N/A | No | Yes | No | Sandbox coming soon |
| **AdvancedMD** | Paid | No | Yes | Yes | Requires agreement |
| **Tebra/Kareo** | Unknown | No | Yes | Yes | Contact required |
| **McKesson** | Unknown | No | Yes | Limited | Contact required |

## Summary Table - Integration Platforms & Data Networks

| Platform | Cost | Self-Service | FHIR R4 | Sandbox | Notes |
|----------|------|--------------|---------|---------|-------|
| **Redox** | FREE* | Yes | Yes | Yes | Free reads, paid writebacks |
| **Health Gorilla** | Contact | Yes | Yes | Yes | 320M+ patient records |
| **1upHealth** | FREE | Yes | Yes | Yes | 10,000+ health centers |
| **Particle Health** | Contact | Yes | Yes | Yes | 90% EHR coverage via single API |
| **Flexpa** | FREE | Yes | Yes | Yes | 300+ health plans, claims data |
| **Zus Health** | Contact | Yes | Yes | Yes | Aggregated patient data |

## Summary Table - Open Source & Test Servers

| Platform | Cost | Self-Service | FHIR R4 | Sandbox | Notes |
|----------|------|--------------|---------|---------|-------|
| **SMART Health IT** | FREE | Yes | Yes | Yes | Reference implementation |
| **Medplum** | FREE | Yes | Yes | Yes | Open source, self-host or cloud |
| **HAPI FHIR** | FREE | Yes | Yes | Yes | Open source Java server |
| **Aidbox** | FREE* | Yes | Yes | Yes | Free dev, paid scaling |
| **Firely Server** | FREE* | Yes | Yes | Yes | .NET-based |
| **HL7 Test Servers** | FREE | Yes | Yes | Yes | test.fhir.org |

---

## Cerner / Oracle Health (CREDENTIALS RECEIVED)

**Status:** READY TO INTEGRATE

### Credentials
| Field | Value |
|-------|-------|
| **Application ID** | `eb6c870b-63f6-43e8-b50c-2a4753507a59` |
| **Client ID** | `0fab9b20-adc8-4940-bbf6-82034d1d39ab` |

### Portal
- **URL:** https://code-console.cerner.com
- **Documentation:** https://fhir.cerner.com

### Access Type
- FREE sandbox access
- No subscription required for development
- Production requires organization partnership

### Sandbox Details
- **Base URL:** `https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d`
- **Test Patient ID:** 12724066 (SMARTS SR., NANCYS II)
- **Auth:** Open access (no OAuth for sandbox)

### FHIR Resources Available
- Patient, Condition, Observation, MedicationRequest
- AllergyIntolerance, CarePlan, DocumentReference
- ServiceRequest, DiagnosticReport, Immunization

### Registration Settings Used
| Field | Selection |
|-------|-----------|
| Application Type | Provider |
| Type of Access | Offline |
| Application Privacy | Confidential |
| SMART Version | v2 |
| Intended Users | Clinical Team, Healthcare Administrator/Executive |
| Intended Purposes | Clinical Tools, Administrative Tasks, Patient-Provider Communication |
| Redirect URI | http://localhost:8002/auth/cerner/callback |

---

## Epic

### Portal
- **URL:** https://fhir.epic.com
- **App Orchard:** https://appmarket.epic.com

### Access Type
- FREE sandbox access
- $500 one-time App Orchard listing fee (production only)
- Individual hospital connections require customer approval

### Sandbox Details
- **Base URL:** `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4`
- **Test Credentials:** Available after registration

### FHIR Resources Available
- All standard FHIR R4 resources
- Epic-specific extensions
- MyChart patient access APIs

### Setup Steps
1. Create account at https://fhir.epic.com
2. Register application
3. Download test patient credentials
4. Test with sandbox
5. Apply for App Orchard listing when ready for production

---

## athenahealth

### Portal
- **URL:** https://developer.api.athena.io
- **Documentation:** https://docs.api.athena.io

### Access Type
- FREE sandbox access
- Self-service registration
- No credit card required

### Sandbox Details
- Full FHIR R4 sandbox environment
- Mock patient data included
- OAuth 2.0 authentication

### Setup Steps
1. Register at https://developer.api.athena.io
2. Create application
3. Get client credentials
4. Test with sandbox environment
5. Apply for production access when ready

### API Features
- Patient demographics
- Clinical data (conditions, medications, allergies)
- Scheduling and appointments
- Billing and claims
- Document management

---

## eClinicalWorks (eCW)

### Portal
- **URL:** https://fhir.eclinicalworks.com
- **Developer Docs:** https://developers.eclinicalworks.com

### Access Type
- FREE FHIR API access
- ONC-compliant APIs
- Registration required

### Sandbox Details
- FHIR R4 compliant
- Bulk data export supported
- SMART on FHIR authentication

### Setup Steps
1. Register at developer portal
2. Complete API access agreement
3. Receive sandbox credentials
4. Test FHIR endpoints
5. Request production credentials

### API Features
- Patient Portal APIs
- Clinical Data APIs
- Interoperability APIs (USCDI)
- Bulk FHIR export

---

## NextGen Healthcare

### Portal
- **URL:** https://developer.nextgen.com
- **Documentation:** https://developer.nextgen.com/docs

### Access Type
- FREE developer program
- Self-service sandbox
- No upfront costs

### Sandbox Details
- Full FHIR R4 sandbox
- Synthetic patient data
- OAuth 2.0 / SMART on FHIR

### Setup Steps
1. Join developer program at https://developer.nextgen.com
2. Create application
3. Access sandbox environment
4. Test with synthetic data
5. Apply for production integration

### API Features
- EHR data APIs
- Practice Management APIs
- Population Health APIs
- Revenue Cycle APIs

---

## MEDITECH

### Portal
- **URL:** https://ehr.meditech.com/greenfield
- **Greenfield Workspace:** Developer testing environment

### Access Type
- FREE registration
- Greenfield Workspace for testing
- Production requires health system partnership

### Sandbox Details
- FHIR R4 APIs
- Expanse platform testing
- Cloud-based sandbox

### Setup Steps
1. Register at MEDITECH Greenfield
2. Complete developer agreement
3. Access testing workspace
4. Develop and test integration
5. Partner with health system for production

### API Features
- Clinical documentation
- Orders and results
- Medication management
- Patient demographics
- Interoperability (USCDI)

---

## Veradigm (Allscripts)

### Portal
- **URL:** https://developer.veradigm.com
- **FHIR:** https://fhir.fhirpoint.open.allscripts.com

### Access Type
- Free trial available
- Paid subscription tiers for extended access

### Pricing Tiers
| Plan | Monthly | API Calls | Best For |
|------|---------|-----------|----------|
| **Bronze** | $49 | Limited | Initial exploration |
| **Silver** | $99 | 10,000/mo | Sandbox testing (RECOMMENDED) |
| **Gold** | $499 | 100,000/mo | Pre-production |
| **Platinum** | $1,499 | Unlimited | Production |

### Sandbox Details
- **Base URL:** `https://fhir.fhirpoint.open.allscripts.com/fhirroute/open/sandbox/r4`
- Multiple EHR product sandboxes (TouchWorks, Pro, Sunrise)

### Recommendation
**Silver Plan ($99/mo)** is recommended for MDx Vision:
- Sufficient API calls for development
- Full sandbox access
- Production upgrade path available

---

## McKesson

### Portal
- **URL:** https://g2fhir.mckesson.com
- **iKnowMed:** Oncology-focused EHR

### Access Type
- Sandbox available
- Contact required for access
- Enterprise-focused

### Notes
- Primarily oncology/specialty focused
- May require partnership agreement
- Less self-service than other platforms

---

## Integration Checklist

### Before Starting
- [ ] Identify target EHR platforms
- [ ] Register at developer portals
- [ ] Review API documentation
- [ ] Understand OAuth/SMART flows

### Development
- [ ] Configure redirect URIs
- [ ] Implement OAuth 2.0 / SMART on FHIR
- [ ] Test with sandbox data
- [ ] Handle token refresh
- [ ] Implement error handling

### MDx Vision Specific
- [ ] Add EHR to `ehr-proxy/main.py`
- [ ] Configure in environment variables
- [ ] Test patient lookup
- [ ] Test CRUD operations
- [ ] Verify HIPAA audit logging

### Production
- [ ] Complete vendor agreements
- [ ] Security assessment
- [ ] Production credentials
- [ ] Health system partnerships
- [ ] Go-live testing

---

## Environment Variables

```bash
# Cerner
CERNER_CLIENT_ID=your_client_id
CERNER_CLIENT_SECRET=your_client_secret
CERNER_BASE_URL=https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d

# Epic
EPIC_CLIENT_ID=your_client_id
EPIC_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4

# Veradigm
VERADIGM_CLIENT_ID=your_client_id
VERADIGM_CLIENT_SECRET=your_client_secret
VERADIGM_BASE_URL=https://fhir.fhirpoint.open.allscripts.com/fhirroute/open/sandbox/r4

# athenahealth
ATHENA_CLIENT_ID=your_client_id
ATHENA_CLIENT_SECRET=your_client_secret
ATHENA_BASE_URL=https://api.athenahealth.com

# eClinicalWorks
ECW_CLIENT_ID=your_client_id
ECW_BASE_URL=https://fhir.eclinicalworks.com

# NextGen
NEXTGEN_CLIENT_ID=your_client_id
NEXTGEN_BASE_URL=https://api.nextgen.com

# MEDITECH
MEDITECH_CLIENT_ID=your_client_id
MEDITECH_BASE_URL=https://ehr.meditech.com/fhir/r4
```

---

## Quick Start Priority

### Recommended Order
1. **Cerner** - Already registered, FREE, excellent sandbox
2. **Epic** - User has credentials, largest market share
3. **athenahealth** - FREE, self-service, ambulatory focused
4. **Veradigm** - User has access, good multi-product coverage
5. **eClinicalWorks** - FREE, growing platform
6. **NextGen** - FREE, specialty practices
7. **MEDITECH** - FREE, hospital-focused

### Market Coverage
With Cerner + Epic + athenahealth + Veradigm integrated:
- ~70% of US hospital market
- ~60% of ambulatory market
- Major health system coverage

---

## Additional EHR Vendors

### Elation Health
- **Portal:** https://www.elationhealth.com/developer-platform/
- **Sandbox:** https://www.elationhealth.com/contact-us/sandbox/
- **Cost:** FREE sandbox access
- **Notes:** Primary care focused, form submission required, PHI-free test data

### DrChrono
- **Portal:** https://www.drchrono.com/api/
- **Docs:** https://app.drchrono.com/api-docs/
- **Cost:** FREE API access
- **Notes:** Cloud-based EHR, sandbox available, Apple Health Records integration

### Practice Fusion
- **Portal:** https://www.practicefusion.com/developer-center/
- **FHIR:** https://www.practicefusion.com/fhir/get-started/
- **Cost:** FREE (currently complimentary)
- **Notes:** Free EHR platform, Salesforce-based approval process

### CareCloud
- **Portal:** https://developer.carecloud.com/
- **Docs:** https://developer.carecloud.com/docs
- **Cost:** FREE registration
- **Notes:** Connector platform for multiple EHR products

### ModMed (Modernizing Medicine)
- **Portal:** https://portal.api.modmed.com/
- **Cost:** FREE sandbox (apply for access)
- **Notes:** Specialty-focused (dermatology, orthopedics), 2-week provisioning time

### Greenway Health
- **Portal:** https://developer.greenwayhealth.com/
- **Cost:** Registration free, no sandbox yet
- **Notes:** Sandbox "coming soon" - FHIR R4 APIs available, Intergy & Prime Suite products

### AdvancedMD
- **Portal:** https://developer.advancedmd.com/
- **FHIR:** https://fhir.advancedmd.com/
- **Cost:** Requires agreement/license
- **Notes:** 70,000+ providers, agreement required before sandbox access

### Tebra/Kareo
- **Portal:** https://helpme.kareo.com/01_Kareo_PM/12_API_and_Integration
- **API:** https://api.kareo.com/clinical/v1/swagger/
- **Cost:** Contact required
- **Notes:** SOAP and FHIR APIs available

---

## Integration Platforms (Multi-EHR Access)

### Redox
- **Portal:** https://developer.redoxengine.com/
- **Sandbox:** FREE account with immediate credentials
- **Cost:** Free reads/queries, paid for writebacks
- **Notes:** Healthcare middleware, translates HL7v2/CDA to FHIR, connects to 1000+ health systems
- **Key Feature:** Single API to reach multiple EHRs

### Health Gorilla
- **Portal:** https://developer.healthgorilla.com/
- **Sandbox:** Fully functional with synthetic data
- **Cost:** Contact for pricing
- **Notes:** Access to 320M+ patient records, nationwide networks
- **Key Feature:** Lab ordering, CCD retrieval, nationwide data aggregation

### 1upHealth
- **Portal:** https://developer.1up.health
- **Console:** https://1up.health/devconsole
- **Cost:** FREE developer tier
- **Notes:** 10,000+ health centers, FHIR-native, HIPAA compliant cloud
- **Key Feature:** Patient data from multiple sources via single API

### Particle Health
- **Portal:** https://docs.particlehealth.com/
- **Sandbox:** Synthetic patient data, fully functional
- **Cost:** Contact for pricing
- **Notes:** 90% of EHRs via single API, 320M+ FHIR records
- **Key Feature:** Instant nationwide patient record retrieval

### Flexpa
- **Portal:** https://www.flexpa.com/sandbox
- **Docs:** https://www.flexpa.com/docs/records
- **Cost:** FREE sandbox access
- **Notes:** 300+ health plans, claims data, payer Patient Access APIs
- **Key Feature:** Insurance claims data aggregation

### Zus Health
- **Portal:** https://docs.zushealth.com/
- **Cost:** Contact for sandbox access
- **Notes:** Aggregated patient data, de-duplicated records
- **Key Feature:** "Get up to speed" moment for providers

---

## Open Source FHIR Servers

### SMART Health IT
- **Sandbox:** https://launch.smarthealthit.org
- **GitHub:** https://github.com/smart-on-fhir/smart-dev-sandbox
- **Cost:** FREE
- **Notes:** Reference implementation, DSTU2/STU3/R4/R5 servers, Docker-based local dev
- **Key Feature:** ONC-certified SMART on FHIR testing

### Medplum
- **Portal:** https://www.medplum.com/
- **Cloud:** https://app.medplum.com (free tier)
- **GitHub:** https://github.com/medplum/medplum
- **Cost:** FREE (open source, Apache 2.0)
- **Notes:** Full healthcare platform, TypeScript, HIPAA/SOC2 compliant
- **Key Feature:** Build any healthcare app, self-host or cloud

### HAPI FHIR
- **GitHub:** https://github.com/hapifhir/hapi-fhir
- **Cost:** FREE (open source)
- **Notes:** Java-based, supports DSTU2-R5, most popular open source FHIR server
- **Key Feature:** JPA database support, full FHIR compliance

### Aidbox (Health Samurai)
- **Portal:** https://www.health-samurai.io/fhir-server
- **Cost:** FREE for development
- **Notes:** PostgreSQL-based, STU3/R4/R5/R6 support
- **Key Feature:** SDK and flat-rate monthly pricing

### HL7 Public Test Servers
- **R4:** http://test.fhir.org/r4
- **R3:** http://test.fhir.org/r3
- **Cost:** FREE
- **Notes:** Grahame's test server, all resource types and operations
- **Key Feature:** Quick testing without registration

---

## Quick Registration Links

### FREE Self-Service (No Approval Needed)
1. **SMART Health IT** - https://launch.smarthealthit.org
2. **Medplum** - https://app.medplum.com
3. **HL7 Test Server** - http://test.fhir.org/r4
4. **Veradigm Anonymous** - https://tw171.open.allscripts.com/FHIRanon
5. **1upHealth** - https://1up.health/devconsole
6. **Redox** - https://developer.redoxengine.com
7. **Flexpa** - https://www.flexpa.com/sandbox

### FREE with Registration
1. **Cerner** - https://code-console.cerner.com (REGISTERED)
2. **Epic** - https://fhir.epic.com
3. **athenahealth** - https://developer.api.athena.io
4. **eClinicalWorks** - https://fhir.eclinicalworks.com
5. **NextGen** - https://developer.nextgen.com
6. **MEDITECH** - https://ehr.meditech.com/greenfield
7. **Elation** - https://www.elationhealth.com/contact-us/sandbox/
8. **DrChrono** - https://www.drchrono.com/api/
9. **Practice Fusion** - https://www.practicefusion.com/fhir/get-started/
10. **CareCloud** - https://developer.carecloud.com/

### Contact/Apply Required
1. **Health Gorilla** - https://developer.healthgorilla.com
2. **Particle Health** - https://docs.particlehealth.com
3. **Zus Health** - https://docs.zushealth.com
4. **ModMed** - https://portal.api.modmed.com
5. **AdvancedMD** - https://developer.advancedmd.com

---

## Total Platform Count: 29

**Direct EHR Vendors:** 16
**Integration Platforms:** 6
**Open Source/Test Servers:** 7

With integrations to these platforms, MDx Vision can demonstrate connectivity to:
- **~95% of US hospital EHR market** (Epic + Cerner + MEDITECH)
- **~80% of ambulatory market** (athenahealth + NextGen + eCW + DrChrono)
- **Nationwide patient data** (via Health Gorilla, Particle Health, 1upHealth)
- **Payer/claims data** (via Flexpa)

---

*See [CONVERSATIONS.md](CONVERSATIONS.md) for integration progress tracking.*
