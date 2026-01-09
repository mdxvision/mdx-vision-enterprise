# Ambulatory EHR Deep Dive: DrChrono & Practice Fusion

> Research document for expanding MDx Vision ambulatory market coverage.
> **Last Updated:** January 8, 2026

---

## Executive Summary

| EHR | Market Share | Target | Pricing | API Access | Status |
|-----|--------------|--------|---------|------------|--------|
| **DrChrono** | ~5% ambulatory | Small-mid practices | $199-399/mo | OAuth2 + FHIR | Have account (locked out) |
| **Practice Fusion** | ~4% ambulatory | Solo/small practices | $149-199/mo | FHIR via Veradigm | Awaiting email response |

Combined potential: **~9% additional ambulatory market coverage**

---

## DrChrono

### Company Overview

| Attribute | Details |
|-----------|---------|
| **Full Name** | DrChrono (EverHealth Solutions Inc.) |
| **Founded** | 2009 |
| **Headquarters** | Sunnyvale, California |
| **Parent Company** | EverHealth Solutions Inc. |
| **Target Market** | Small to mid-size ambulatory practices |
| **Specialties** | 20+ medical specialties supported |
| **Notable Achievement** | First mobile EHR on iPad (2010) |
| **Recognition** | Black Book #1 Mobile EHR (2013-2022) |

### Market Position

- **User Base**: 30,000+ healthcare providers
- **Market Share**: ~5% of ambulatory EHR market
- **Primary Users**: Independent practices, specialty clinics
- **Geographic Focus**: United States
- **Key Differentiator**: Mobile-first, Apple ecosystem integration

### Product Features

#### Core EHR Capabilities
- Customizable clinical forms and templates
- Speech-to-text transcription (built-in)
- E-prescribing (eRx) with EPCS support
- Lab and imaging integrations
- Patient portal (OnPatient)
- Telehealth/video visits

#### Mobile Features (Key Differentiator)
- Native iPad app (flagship)
- iPhone app
- Mac app
- Apple Watch integration
- Official Apple Mobility Partner
- Offline mode with sync

#### Practice Management
- Appointment scheduling
- Patient check-in (kiosk mode)
- Insurance eligibility verification
- Claims management
- Revenue cycle management (RCM)

### Pricing

| Plan | Price | Features |
|------|-------|----------|
| **Prometheus** | $199/mo per provider | Basic EHR + PM |
| **Hippocrates** | $299/mo per provider | + Advanced features |
| **Apollo** | $399/mo per provider | + RCM, premium support |

- Annual commitment required
- Free trial available
- Implementation fees may apply

### API & Integration

#### API Type
- **Primary**: REST API with OAuth 2.0
- **FHIR**: R4 compliant (ONC certified)
- **Documentation**: Available at app.drchrono.com/api-docs

#### Available Endpoints (REST API)
```
/api/patients                 - Patient demographics
/api/appointments             - Scheduling
/api/clinical_notes           - Documentation
/api/prescriptions            - Medications
/api/lab_results              - Lab data
/api/billing                  - Claims/billing
/api/tasks                    - Task management
```

#### FHIR Resources (ONC Required)
- Patient
- AllergyIntolerance
- Condition
- DiagnosticReport
- DocumentReference
- Immunization
- MedicationRequest
- Observation
- Procedure

#### Developer Access
1. Register at DrChrono developer portal
2. Create application
3. Obtain OAuth2 credentials (Client ID, Secret)
4. Request sandbox access
5. Implement OAuth flow
6. Test with sandbox data

#### Rate Limits
- Varies by plan
- Typically 1000 requests/hour for standard plans
- Higher limits for enterprise

### Integration Strengths for MDx Vision

| Strength | Relevance |
|----------|-----------|
| Mobile-first design | AR glasses are mobile devices |
| Speech-to-text built-in | Complements our voice features |
| REST + FHIR APIs | Flexible integration options |
| Lab integrations | Real-time lab results |
| Telehealth | Potential for AR-enhanced visits |

### Potential Challenges

| Challenge | Mitigation |
|-----------|------------|
| Account lockout issues | Contact support, verify credentials |
| Rate limiting | Implement caching, batch requests |
| Sandbox limitations | Test thoroughly before production |
| OAuth token refresh | Implement proper token management |

### Registration Process

1. **Developer Portal**: https://app.drchrono.com/api-docs/
2. **Create Account**: Sign up for developer access
3. **Create Application**: Register MDx Vision
4. **OAuth Credentials**: Obtain Client ID and Secret
5. **Sandbox Testing**: Test with sample data
6. **Production Access**: Submit for review

### Contact Information

- **Sales**: (844) 569-8628
- **Support**: support@drchrono.com
- **Developer Support**: api@drchrono.com
- **Website**: https://www.drchrono.com

---

## Practice Fusion

### Company Overview

| Attribute | Details |
|-----------|---------|
| **Full Name** | Practice Fusion |
| **Founded** | 2005 |
| **Headquarters** | San Francisco, California |
| **Parent Company** | Veradigm (formerly Allscripts) - acquired 2018 |
| **Target Market** | Solo practitioners, small practices |
| **Original Model** | Free ad-supported EHR (discontinued 2018) |
| **Current Model** | Paid subscription |

### Market Position

- **User Base**: 30,000+ practices, 112,000+ providers (historical peak)
- **Market Share**: ~4% of ambulatory EHR market
- **Patient Records**: 100+ million patients
- **Primary Users**: Solo practitioners, very small practices
- **Geographic Focus**: United States
- **Key Differentiator**: Historically free, large user base

### History & Notable Events

| Year | Event |
|------|-------|
| 2005 | Founded in San Francisco |
| 2012 | Largest cloud-based EHR in US |
| 2013 | 100,000 providers on platform |
| 2018 | Acquired by Allscripts (now Veradigm) for $100M |
| 2018 | Transitioned from free to paid model |
| 2020 | $145M DOJ settlement (kickback scheme) |
| 2021 | Rebranded under Veradigm |

### DOJ Settlement Context

In 2020, Practice Fusion paid $145 million to settle allegations of accepting kickbacks from an opioid manufacturer to implement alerts that promoted opioid prescribing. This is important context for the company's history but doesn't affect current API capabilities.

### Product Features

#### Core EHR Capabilities
- Cloud-based charting
- E-prescribing (EPCS certified)
- Lab integrations (major labs)
- Patient portal
- Referral management
- Quality reporting

#### Practice Management
- Appointment scheduling
- Patient reminders (email, text, phone)
- Insurance eligibility
- Claims management
- Billing services option

#### Veradigm Network Integration
- Access to Veradigm marketplace (600+ apps)
- Data network connectivity
- Pharmacy connections
- Lab connectivity

### Pricing

| Plan | Price | Features |
|------|-------|----------|
| **EHR Only** | $149/mo per provider | Core EHR features |
| **EHR + Billing** | $199/mo per provider | + Integrated billing |

- Annual commitment required
- 2-week free trial available
- No credit card for trial

### API & Integration

#### API Access Path
Since Practice Fusion is owned by Veradigm, API access goes through the **Veradigm Developer Portal**:

1. Register at Veradigm Developer Portal
2. Select "Practice Fusion" as target EHR
3. Choose FHIR or Unity API
4. Obtain credentials

#### FHIR Support
- **Version**: R4 compliant
- **ONC Certified**: Yes
- **Access**: Via Veradigm FHIR endpoints

#### FHIR Resources Available
```
Patient              - Demographics
AllergyIntolerance   - Allergies
Condition            - Problems/diagnoses
MedicationRequest    - Prescriptions
Observation          - Vitals, labs
Immunization         - Vaccines
Procedure            - Procedures
DocumentReference    - Clinical notes
DiagnosticReport     - Lab reports
CarePlan             - Care plans
```

#### Veradigm Integration Advantage
Since we already have Veradigm credentials, Practice Fusion integration may be simpler:
- Same authentication infrastructure
- Familiar API patterns
- Potential for shared credentials

### Integration Strengths for MDx Vision

| Strength | Relevance |
|----------|-----------|
| Large user base | Significant market reach |
| Veradigm integration | We have Veradigm credentials already |
| Cloud-based | Easy connectivity |
| Small practice focus | Matches AR glasses use case |
| Lab integrations | Real-time results |

### Potential Challenges

| Challenge | Mitigation |
|-----------|------------|
| Email response delay | Follow up, try phone |
| Veradigm complexity | Leverage existing integration |
| Historical reputation | Focus on technical merits |
| Smaller practices = smaller budgets | Emphasize efficiency gains |

### Registration Process

**Option 1: Via Veradigm (Recommended)**
1. Use existing Veradigm developer account
2. Request Practice Fusion access
3. May use same or similar credentials

**Option 2: Direct Contact**
1. Email Practice Fusion API team
2. Request developer access
3. Specify FHIR API needs

### Contact Information

- **Sales**: (415) 993-4977
- **Website**: https://www.practicefusion.com
- **Parent Company**: https://www.veradigm.com
- **Developer Portal**: Via Veradigm

---

## Comparison Matrix

| Feature | DrChrono | Practice Fusion |
|---------|----------|-----------------|
| **Market Share** | ~5% | ~4% |
| **Target Practice Size** | Small-mid | Solo-small |
| **Pricing** | $199-399/mo | $149-199/mo |
| **Mobile App** | Excellent (native) | Basic (web) |
| **FHIR Support** | Direct | Via Veradigm |
| **API Documentation** | Good | Through Veradigm |
| **Developer Experience** | Self-service | May need approval |
| **Integration Complexity** | Medium | Low (if Veradigm works) |

---

## Integration Priority

### Recommended Order

1. **Practice Fusion** (if Veradigm credentials work)
   - Already have Veradigm integration
   - May be faster to implement
   - Large user base

2. **DrChrono** (once lockout resolved)
   - Better mobile platform
   - More modern API
   - Growing market share

### Combined Impact

| Metric | Current | After Integration |
|--------|---------|-------------------|
| **Ambulatory Coverage** | ~35% | ~44% |
| **Total EHRs** | 7 | 9 |
| **Practices Reachable** | ~200,000 | ~260,000 |

---

## Action Items

### DrChrono
- [ ] Resolve account lockout (contact support)
- [ ] Obtain new OAuth credentials
- [ ] Test sandbox connectivity
- [ ] Implement integration

### Practice Fusion
- [ ] Wait for email response
- [ ] Try Veradigm credentials for Practice Fusion access
- [ ] If needed, contact sales directly: (415) 993-4977
- [ ] Implement integration (may reuse Veradigm code)

---

## Technical Notes

### DrChrono OAuth Flow
```
Authorization URL: https://drchrono.com/o/authorize/
Token URL: https://drchrono.com/o/token/
Scopes: patients:read patients:write clinical:read clinical:write
```

### Practice Fusion (via Veradigm)
```
May use existing Veradigm credentials:
- Client ID: 11A47952-0F52-4936-A6A3-CF91FDFDDF14
- FHIR Base: Check Veradigm for Practice Fusion endpoint
```

---

## References

- DrChrono Website: https://www.drchrono.com
- Practice Fusion Website: https://www.practicefusion.com
- Veradigm Developer Portal: https://developer.veradigm.com
- ONC CHPL Database: https://chpl.healthit.gov
- 21st Century Cures Act FHIR Requirements

---

*This document will be updated as we gather more information and complete integrations.*
