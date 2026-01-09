# Healthcare Data Aggregator Platforms Research

> Deep dive into aggregator platforms that provide single-API access to multiple EHRs.
> **Last Updated:** January 8, 2026

---

## Executive Summary

Instead of integrating with each EHR individually, aggregator platforms provide a **single API** that connects to hundreds of EHRs and health data sources. This is the fastest path to 90%+ market coverage.

| Platform | Coverage | Best For | Pricing Model | Status |
|----------|----------|----------|---------------|--------|
| **Redox** | 50+ EHRs, 12,200+ orgs | EHR write-back, real-time | Free reads, paid writes | Recommended |
| **Particle Health** | 320M patients, 90% market | Patient record retrieval | Per-query | Strong option |
| **Health Gorilla** | TEFCA/QHIN certified | Lab orders, nationwide | Subscription | Enterprise |
| **1upHealth** | 10,000+ facilities | Payer compliance | Per-connection | Payer-focused |

### Recommendation for MDx Vision

**Primary: Redox** - Best for clinical apps needing EHR read/write
**Secondary: Particle Health** - Best for patient record retrieval across networks

---

## Redox

### Company Overview

| Attribute | Details |
|-----------|---------|
| **Full Name** | Redox, Inc. |
| **Founded** | 2014 |
| **Headquarters** | Madison, Wisconsin |
| **Funding** | $100M+ (Series D) |
| **Phone** | 608-535-9501 |
| **Website** | https://www.redoxengine.com |

### What Redox Does

Redox is a **healthcare integration platform** that acts as a universal translator between EHRs, clinical systems, and digital health applications. Instead of building separate integrations for Epic, Cerner, MEDITECH, etc., you build ONE integration with Redox.

```
[Your App] ←→ [Redox API] ←→ [Epic]
                          ←→ [Cerner]
                          ←→ [MEDITECH]
                          ←→ [50+ other EHRs]
```

### Key Stats

| Metric | Value |
|--------|-------|
| **EHR Connections** | 50+ EHR platforms |
| **Connected Organizations** | 12,200+ healthcare organizations |
| **Annual Transactions** | 20+ billion |
| **Uptime** | 99.95% |
| **Security** | HITRUST r2, SOC 2 Type 2 |

### How It Works

1. **Single API**: Build one integration using Redox's standardized data model
2. **EHR Agnostic**: Same API works for Epic, Cerner, MEDITECH, athena, etc.
3. **Bi-directional**: Read FROM and write TO EHRs
4. **Real-time**: Push/pull data in real-time, not batch
5. **Managed Connections**: Redox handles the EHR relationship, contracts, testing

### Data Model

Redox uses a **standardized data model** that normalizes data across EHRs:

| Category | Data Types |
|----------|------------|
| **Clinical** | Patient, Encounters, Observations, Problems, Medications, Allergies, Procedures, Results, Notes |
| **Scheduling** | Appointments, Availability, Resources |
| **Financial** | Claims, Coverage, Eligibility |
| **Administrative** | Providers, Locations, Organizations |

### FHIR Support

- **FHIR R4**: Full support
- **Bulk FHIR**: For large data exports
- **SMART on FHIR**: OAuth2 app launch
- **US Core**: Compliant profiles

### Pricing Model

| Tier | Reads | Writes | Notes |
|------|-------|--------|-------|
| **Development** | Free | Free | Sandbox testing |
| **Production Reads** | Free | - | Query patient data |
| **Production Writes** | - | Paid | Write back to EHR |
| **Enterprise** | Custom | Custom | High volume, SLA |

**Key Insight**: Reading patient data is FREE. You only pay when writing back to EHRs (pushing notes, orders, etc.).

### Integration Process

1. **Sign Up**: Create Redox account (free)
2. **Development**: Build integration in sandbox
3. **Testing**: Test with mock EHR data
4. **Certification**: Complete security review
5. **Go Live**: Connect to production EHRs

**Timeline**: 4-8 weeks for basic integration

### Supported EHRs (Partial List)

| Major Hospital | Ambulatory | Specialty |
|----------------|------------|-----------|
| Epic | athenahealth | Modernizing Medicine |
| Cerner | NextGen | AdvancedMD |
| MEDITECH | eClinicalWorks | Greenway |
| Allscripts | DrChrono | CureMD |
| CPSI | Practice Fusion | ChartLogic |

### Why Redox for MDx Vision

| Benefit | Impact |
|---------|--------|
| **Instant 50+ EHR coverage** | No more individual integrations |
| **Free reads** | Query patient data at no cost |
| **Write-back support** | Push notes, orders to EHR |
| **Real-time** | Matches AR glasses use case |
| **FHIR native** | Works with our existing code |

### Contact

- **Website**: https://www.redoxengine.com
- **Developer Docs**: https://developer.redoxengine.com
- **Sales**: Available on website

---

## Particle Health

### Company Overview

| Attribute | Details |
|-----------|---------|
| **Full Name** | Particle Health, Inc. |
| **Founded** | 2017 |
| **Headquarters** | New York, NY |
| **Funding** | $50M+ |
| **Website** | https://www.particlehealth.com |

### What Particle Health Does

Particle Health is a **patient record retrieval platform** that connects to nationwide health information networks (NHINs) to pull patient records from across the healthcare ecosystem.

```
[Your App] ←→ [Particle API] ←→ [Carequality]
                             ←→ [CommonWell]
                             ←→ [eHealth Exchange]
                             ←→ [State HIEs]
                             ←→ [Surescripts]
```

### Key Stats

| Metric | Value |
|--------|-------|
| **Patient Coverage** | 320+ million patients |
| **Market Reach** | ~90% of US patients |
| **Connected Sources** | 160,000+ health systems, practices, clinics |
| **Data Networks** | Carequality, CommonWell, eHealth Exchange |
| **Security** | HITRUST, SOC 2, HIPAA |

### How It Works

1. **Patient Query**: Submit patient demographics (name, DOB, etc.)
2. **Record Locator**: Particle finds where patient has records
3. **Data Retrieval**: Pulls records from all sources
4. **Normalization**: Standardizes data (FHIR R4 or C-CDA)
5. **Deduplication**: Removes redundant data (up to 90% reduction)
6. **Delivery**: Returns clean, unified patient record

### Products

| Product | Description | Use Case |
|---------|-------------|----------|
| **Core API** | Basic record retrieval | Developers |
| **Particle FOCUS** | Pre-curated clinical datasets | Quick integration |
| **ADT Feeds** | Admission/discharge alerts | Care coordination |
| **Pharmacy Data** | Prescription history | Medication reconciliation |
| **Snapshot** | AI-generated clinical summaries | Quick patient overview |

### Data Formats

- **FHIR R4**: Native support
- **C-CDA**: Clinical Document Architecture
- **Flat JSON**: Simplified format
- **Parquet**: For analytics
- **Tuva Schema**: Healthcare data warehouse format

### Pricing Model

| Model | Description |
|-------|-------------|
| **Per Query** | Pay per patient record retrieval |
| **Subscription** | Monthly/annual for volume |
| **Enterprise** | Custom pricing for large scale |

**Note**: Pricing not publicly disclosed - requires sales conversation.

### Integration Process

1. **Contact Sales**: Discuss use case
2. **Contract**: Sign agreement
3. **Development**: Access sandbox
4. **Testing**: Test with real-world data
5. **Go Live**: Production access

**Timeline**: ~12 weeks from contract to value

### Why Particle Health for MDx Vision

| Benefit | Impact |
|---------|--------|
| **90% patient coverage** | Find records anywhere |
| **Pre-visit prep** | Pull patient history before encounter |
| **Medication history** | Complete rx list from Surescripts |
| **Care coordination** | ADT alerts for admitted patients |
| **AI summaries** | Quick patient overview for AR display |

### Limitations

- **Read-only**: Cannot write back to source systems
- **Query-based**: Best for on-demand retrieval, not real-time sync
- **Pricing**: Can be expensive at scale

### Contact

- **Website**: https://www.particlehealth.com
- **Developer Docs**: https://docs.particlehealth.com

---

## Health Gorilla

### Company Overview

| Attribute | Details |
|-----------|---------|
| **Full Name** | Health Gorilla, Inc. |
| **Headquarters** | Sunnyvale, California |
| **Notable Status** | First dual-designated QHIN + QHIO in California |
| **Website** | https://www.healthgorilla.com |

### What Health Gorilla Does

Health Gorilla is a **healthcare data network** that enables secure patient data exchange. They are a **Qualified Health Information Network (QHIN)** under TEFCA, making them a trusted nationwide data exchange participant.

### Key Stats

| Metric | Value |
|--------|-------|
| **Lab Vendors** | 120+ electronic lab ordering |
| **TEFCA Status** | Qualified Health Information Network |
| **California DxF** | CalHHS Data Exchange Framework participant |
| **Security** | HITRUST r2, SOC 2 |

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Patient360** | Longitudinal patient record retrieval |
| **Lab Ordering** | Electronic orders to 120+ lab vendors |
| **Pharmacy Data** | Medication history |
| **ADT Alerts** | Real-time admission/discharge notifications |
| **SDOH Data** | Social determinants of health |
| **Claims Data** | Payer claims information |

### TEFCA Advantage

**TEFCA** (Trusted Exchange Framework and Common Agreement) is the federal framework for nationwide health data exchange. As a QHIN, Health Gorilla:

- Has direct access to TEFCA network
- Can exchange data with other QHINs
- Is trusted for nationwide data queries
- Meets federal interoperability requirements

### Products

| Product | Description |
|---------|-------------|
| **Patient360** | Comprehensive patient record |
| **Clinical Alerts** | Real-time notifications |
| **Lab Exchange** | Order and receive lab results |
| **Document Exchange** | C-CDA/FHIR document sharing |

### Integration

- **API**: RESTful FHIR R4 API
- **OAuth 2.0**: Standard authentication
- **Sandbox**: Available for testing
- **Documentation**: https://developer.healthgorilla.com

### Why Health Gorilla for MDx Vision

| Benefit | Impact |
|---------|--------|
| **TEFCA certified** | Federal trust framework |
| **Lab ordering** | Order labs from AR glasses |
| **Real-time alerts** | Know when patients admitted |
| **California focus** | Strong in CA market |

### Limitations

- **Enterprise focused**: May require larger commitment
- **Lab-centric**: Strongest in lab ordering use case
- **Regional strength**: Best coverage varies by region

### Contact

- **Website**: https://www.healthgorilla.com
- **Support**: support@healthgorilla.com

---

## 1upHealth

### Company Overview

| Attribute | Details |
|-----------|---------|
| **Full Name** | 1upHealth, Inc. |
| **Headquarters** | Boston, Massachusetts |
| **Phone** | +1 (888) 344-7187 |
| **Focus** | Payer interoperability compliance |
| **Website** | https://www.1up.health |

### What 1upHealth Does

1upHealth is a **payer interoperability platform** focused on helping health plans comply with CMS interoperability rules. While they have provider solutions, their primary market is payers.

### Key Stats

| Metric | Value |
|--------|-------|
| **Connected Facilities** | 10,000+ |
| **Primary Market** | Health plans/payers |
| **CMS Compliance** | Payer interoperability rules |
| **Recognition** | KLAS top performer 2025 |

### Products

| Product | Description | Target |
|---------|-------------|--------|
| **1up Platform** | Core data management | All |
| **Patient Access** | Member data access via apps | Payers |
| **Provider Access** | Share data with providers | Payers |
| **Prior Auth** | Electronic prior authorization | Payers |
| **Payer-to-Payer** | Bi-directional data exchange | Payers |

### Technical Foundation

- **FHIR R4**: Native support
- **Cloud-based**: API-powered architecture
- **Data Lakehouse**: Healthcare-specific data architecture

### Why 1upHealth May Not Be Best for MDx Vision

| Factor | Assessment |
|--------|------------|
| **Payer focus** | We're a provider app |
| **Compliance-driven** | We need clinical data |
| **Limited EHR write** | We need write-back |

### When to Consider 1upHealth

- If selling to health plans
- For prior authorization features
- For payer data access

---

## Comparison Matrix

| Feature | Redox | Particle | Health Gorilla | 1upHealth |
|---------|-------|----------|----------------|-----------|
| **EHR Write-back** | ✅ Yes | ❌ No | ⚠️ Limited | ❌ No |
| **Patient Record Query** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Real-time Data** | ✅ Yes | ⚠️ On-demand | ✅ Yes | ⚠️ Varies |
| **Free Tier** | ✅ Reads free | ❌ No | ❌ No | ❌ No |
| **FHIR R4** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Lab Ordering** | ⚠️ Via EHR | ❌ No | ✅ Yes | ❌ No |
| **Medication History** | ✅ Via EHR | ✅ Surescripts | ✅ Yes | ✅ Yes |
| **EHR Coverage** | 50+ EHRs | Via networks | Via TEFCA | 10K facilities |
| **Best For** | Clinical apps | Record retrieval | Enterprise | Payers |

---

## Integration Strategy for MDx Vision

### Recommended Approach

#### Phase 1: Redox (Primary)
**Why**: Best for clinical apps with EHR write-back needs

1. Sign up for Redox developer account
2. Build FHIR integration using existing code
3. Test with sandbox
4. Deploy for instant 50+ EHR coverage

**Cost**: Free for reads, paid for writes

#### Phase 2: Particle Health (Supplemental)
**Why**: Fill gaps where EHR integration doesn't exist

1. Use for patient record retrieval
2. Pre-visit patient history lookup
3. Medication reconciliation
4. Care coordination alerts

**Cost**: Per-query or subscription

### What This Means for Current Integrations

| Current EHR | Keep or Replace? | Reason |
|-------------|------------------|--------|
| Epic | Keep (production-ready) | Direct connection is fine |
| Cerner | Keep (production-ready) | Direct connection is fine |
| MEDITECH | Keep | Good direct integration |
| athenahealth | Optional | Redox can replace |
| NextGen | Optional | Redox can replace |
| eClinicalWorks | Optional | Redox can replace |
| Veradigm | Optional | Redox can replace |

**Strategy**: Keep direct integrations for major EHRs, use Redox for long-tail coverage.

---

## ROI Analysis

### Current Approach (Individual Integrations)

| Metric | Value |
|--------|-------|
| **EHRs integrated** | 7 |
| **Time per integration** | 2-4 weeks |
| **Total time** | 14-28 weeks |
| **Coverage** | ~80% hospital, ~35% ambulatory |

### Aggregator Approach (Redox + Particle)

| Metric | Value |
|--------|-------|
| **Integrations needed** | 2 (Redox + Particle) |
| **Time per integration** | 4-6 weeks |
| **Total time** | 8-12 weeks |
| **Coverage** | ~95% hospital, ~90% ambulatory |

### Break-Even Analysis

If you need to add **4+ more EHRs**, aggregator approach is faster and cheaper.

---

## Action Items

### Immediate (This Week)
- [ ] Sign up for Redox developer account (free)
- [ ] Review Redox documentation
- [ ] Contact Particle Health sales

### Short-term (Next 2 Weeks)
- [ ] Build Redox sandbox integration
- [ ] Test with mock EHR data
- [ ] Evaluate Particle Health pricing

### Medium-term (Next Month)
- [ ] Deploy Redox to production
- [ ] Add Particle Health for record retrieval
- [ ] Deprecate redundant direct integrations

---

## Contacts

| Platform | Contact |
|----------|---------|
| **Redox** | https://www.redoxengine.com/contact |
| **Particle Health** | https://www.particlehealth.com/contact |
| **Health Gorilla** | support@healthgorilla.com |
| **1upHealth** | +1 (888) 344-7187 |

---

## References

- Redox: https://www.redoxengine.com
- Redox Developer Docs: https://developer.redoxengine.com
- Particle Health: https://www.particlehealth.com
- Particle Health Docs: https://docs.particlehealth.com
- Health Gorilla: https://www.healthgorilla.com
- Health Gorilla Docs: https://developer.healthgorilla.com
- 1upHealth: https://www.1up.health
- TEFCA Info: https://www.healthit.gov/topic/interoperability/trusted-exchange-framework-and-common-agreement-tefca

---

*This document will be updated as we evaluate and integrate aggregator platforms.*
